# LIPI Gamification & Tone Data Model
## PostgreSQL Schema for Points, Badges, Leaderboards & Teacher Tone Profiles

**Version**: 1.0  
**Status**: Design Phase  
**Last Updated**: April 14, 2026  
**Covers**: All gamification tables, tone profile, session tracking, leaderboard cache

---

## Overview

This document covers the data model for everything that is NOT the core language learning (vocabulary, grammar, audio). See DATABASE_SCHEMA.md for those tables.

**Tables in this document:**
```
teacher_tone_profiles        — per-teacher communication style
points_transactions          — every point event, immutable log
teacher_points_summary       — cached totals (updated on write)
badges                       — badge definitions
teacher_badges               — which teachers earned which badges
leaderboard_snapshots        — weekly/monthly snapshots
teaching_sessions            — session metadata + summary
session_corrections          — correction events per session
session_prompt_snapshots     — prompt used per session (audit)
```

---

## 1. teacher_tone_profiles

Stores the evolving communication style LIPI has learned for each teacher.

```sql
CREATE TABLE teacher_tone_profiles (
    teacher_id          UUID        PRIMARY KEY REFERENCES users(id),
    
    -- Address register
    register            VARCHAR(10) NOT NULL DEFAULT 'tapai'
                            CHECK (register IN ('hajur', 'tapai', 'timi', 'ta')),
    override_set_by_user BOOLEAN    NOT NULL DEFAULT FALSE,
    -- If TRUE: teacher explicitly requested this register
    -- If FALSE: auto-detected from age at onboarding
    
    -- Communication style (auto-detected over sessions)
    energy              VARCHAR(10) NOT NULL DEFAULT 'medium'
                            CHECK (energy IN ('high', 'medium', 'low')),
    humor_level         FLOAT       NOT NULL DEFAULT 0.3
                            CHECK (humor_level BETWEEN 0.0 AND 1.0),
    
    -- Language mixing ratio
    -- 0.0 = pure primary language, 1.0 = pure secondary language
    code_switch_ratio   FLOAT       NOT NULL DEFAULT 0.0
                            CHECK (code_switch_ratio BETWEEN 0.0 AND 1.0),
    
    -- Response patterns
    avg_response_length INT         NOT NULL DEFAULT 15,  -- words
    avg_session_minutes FLOAT       NOT NULL DEFAULT 10.0,
    
    -- Topics (jsonb array of topic strings, most recent first)
    preferred_topics    JSONB       NOT NULL DEFAULT '[]',
    recent_topics       JSONB       NOT NULL DEFAULT '[]', -- last 5 sessions
    
    -- Metadata
    sessions_analyzed   INT         NOT NULL DEFAULT 0,
    last_updated        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast lookup
CREATE INDEX idx_tone_profiles_teacher ON teacher_tone_profiles(teacher_id);
```

**Tone detection logic** (runs after each session, async):
```python
async def update_tone_profile(teacher_id: UUID, session: Session):
    profile = await get_tone_profile(teacher_id)
    
    # Rolling averages — weight recent sessions more
    ALPHA = 0.3  # 30% new, 70% existing

    profile.energy = blend(
        profile.energy,
        detect_energy(session.messages),
        alpha=ALPHA
    )
    profile.humor_level = blend(
        profile.humor_level,
        detect_humor(session.messages),
        alpha=ALPHA
    )
    profile.code_switch_ratio = blend(
        profile.code_switch_ratio,
        detect_code_switch_ratio(session.messages),
        alpha=ALPHA
    )
    profile.avg_response_length = blend(
        profile.avg_response_length,
        session.avg_teacher_response_length,
        alpha=ALPHA
    )

    # Topics: merge new topics in, keep top 10
    new_topics = extract_topics(session.messages)
    profile.preferred_topics = merge_topics(
        profile.preferred_topics,
        new_topics,
        max_topics=10
    )
    profile.recent_topics = new_topics[:5]
    profile.sessions_analyzed += 1
    profile.last_updated = now()

    await save_tone_profile(profile)
```

---

## 2. points_transactions

Immutable event log. Every point ever earned or spent.
Never update — only insert. Source of truth for all point calculations.

```sql
CREATE TABLE points_transactions (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id      UUID        NOT NULL REFERENCES users(id),
    session_id      UUID        REFERENCES teaching_sessions(id),
    
    -- Event type
    event_type      VARCHAR(50) NOT NULL,
    -- Values:
    -- 'session_base'       — base points for completing a session
    -- 'word_learned'       — LIPI learned a word from teacher
    -- 'correction_accepted'— teacher's correction was accepted
    -- 'streak_bonus'       — daily streak multiplier bonus
    -- 'dialect_bonus'      — rare dialect/language multiplier
    -- 'audio_quality'      — clear audio bonus
    -- 'pioneer_word'       — first teacher of a new word
    -- 'milestone_bonus'    — badge milestone reached
    
    -- Points
    base_points     INT         NOT NULL,  -- points before multipliers
    multiplier      FLOAT       NOT NULL DEFAULT 1.0,
    final_points    INT         NOT NULL,  -- base_points * multiplier (rounded)
    
    -- Context (what triggered this event)
    context         JSONB       NOT NULL DEFAULT '{}',
    -- Examples:
    -- word_learned:       {"word": "नमस्ते", "confidence": 0.85}
    -- correction_accepted:{"original": "जल", "correction": "पानी"}
    -- pioneer_word:       {"word": "खिचडी", "word_id": "uuid"}
    -- streak_bonus:       {"streak_days": 12, "multiplier": 5.0}
    
    -- Anti-gaming: was this validated?
    validated       BOOLEAN     NOT NULL DEFAULT FALSE,
    validation_method VARCHAR(30),
    -- 'auto_quality_check'  — passed audio quality threshold
    -- 'lipi_accepted'       — LLM accepted the teaching
    -- 'community_upvote'    — other teachers confirmed
    -- 'human_review'        — manually approved
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for leaderboard queries
CREATE INDEX idx_points_teacher_created
    ON points_transactions(teacher_id, created_at DESC);

CREATE INDEX idx_points_created
    ON points_transactions(created_at DESC);

CREATE INDEX idx_points_event_type
    ON points_transactions(event_type);

-- Only count validated points in leaderboards
CREATE INDEX idx_points_validated
    ON points_transactions(teacher_id, validated, created_at)
    WHERE validated = TRUE;
```

**Point values (constants):**
```python
POINT_VALUES = {
    "session_base":         10,   # per 5-min session
    "word_learned":          5,   # per word LIPI learns
    "correction_accepted":  15,   # corrections worth most
    "audio_quality":         2,   # per clear utterance
    "pioneer_word":         25,   # first teacher of a new word
    "milestone_bonus":      50,   # when a badge is earned
}

MULTIPLIERS = {
    "streak_7_days":    2.0,
    "streak_30_days":   3.0,
    "streak_100_days":  5.0,
    "rare_dialect":     3.0,  # < 100 speakers in DB
    "minority_language": 2.0, # < 500 total sessions for that language
}
```

---

## 3. teacher_points_summary

Cached aggregates. Rebuilt from points_transactions on a schedule.
DO NOT use for source of truth — use points_transactions for that.

```sql
CREATE TABLE teacher_points_summary (
    teacher_id          UUID    PRIMARY KEY REFERENCES users(id),
    
    -- All-time totals (validated only)
    total_points        INT     NOT NULL DEFAULT 0,
    total_words_taught  INT     NOT NULL DEFAULT 0,
    total_corrections   INT     NOT NULL DEFAULT 0,
    total_sessions      INT     NOT NULL DEFAULT 0,
    total_minutes       INT     NOT NULL DEFAULT 0,
    
    -- Current streak
    current_streak_days INT     NOT NULL DEFAULT 0,
    longest_streak_days INT     NOT NULL DEFAULT 0,
    last_session_date   DATE,
    
    -- Period totals (for leaderboards)
    points_this_week    INT     NOT NULL DEFAULT 0,
    points_this_month   INT     NOT NULL DEFAULT 0,
    
    -- Period boundaries (when was last reset)
    week_start          DATE    NOT NULL DEFAULT CURRENT_DATE,
    month_start         DATE    NOT NULL DEFAULT DATE_TRUNC('month', CURRENT_DATE),
    
    last_rebuilt        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_summary_weekly  ON teacher_points_summary(points_this_week DESC);
CREATE INDEX idx_summary_monthly ON teacher_points_summary(points_this_month DESC);
CREATE INDEX idx_summary_alltime ON teacher_points_summary(total_points DESC);
```

**Rebuild function** (runs via cron every 5 minutes):
```sql
-- Rebuild a single teacher's summary from transactions
CREATE OR REPLACE FUNCTION rebuild_teacher_summary(p_teacher_id UUID)
RETURNS VOID AS $$
DECLARE
    v_week_start  DATE := DATE_TRUNC('week', CURRENT_DATE);
    v_month_start DATE := DATE_TRUNC('month', CURRENT_DATE);
BEGIN
    INSERT INTO teacher_points_summary (
        teacher_id,
        total_points,
        total_words_taught,
        total_corrections,
        total_sessions,
        points_this_week,
        points_this_month,
        week_start,
        month_start,
        last_rebuilt
    )
    SELECT
        p_teacher_id,
        COALESCE(SUM(final_points) FILTER (WHERE validated), 0),
        COALESCE(COUNT(*) FILTER (WHERE event_type = 'word_learned' AND validated), 0),
        COALESCE(COUNT(*) FILTER (WHERE event_type = 'correction_accepted' AND validated), 0),
        COALESCE(COUNT(DISTINCT session_id), 0),
        COALESCE(SUM(final_points) FILTER (WHERE validated AND created_at >= v_week_start), 0),
        COALESCE(SUM(final_points) FILTER (WHERE validated AND created_at >= v_month_start), 0),
        v_week_start,
        v_month_start,
        NOW()
    FROM points_transactions
    WHERE teacher_id = p_teacher_id
    ON CONFLICT (teacher_id) DO UPDATE SET
        total_points        = EXCLUDED.total_points,
        total_words_taught  = EXCLUDED.total_words_taught,
        total_corrections   = EXCLUDED.total_corrections,
        total_sessions      = EXCLUDED.total_sessions,
        points_this_week    = EXCLUDED.points_this_week,
        points_this_month   = EXCLUDED.points_this_month,
        week_start          = EXCLUDED.week_start,
        month_start         = EXCLUDED.month_start,
        last_rebuilt        = NOW();
END;
$$ LANGUAGE plpgsql;
```

---

## 4. badges

Badge definitions. Static — rarely changes.

```sql
CREATE TABLE badges (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            VARCHAR(50) UNIQUE NOT NULL,
    -- Examples: 'bronze_teacher', 'gold_teacher', 'pioneer',
    --           'correction_master', 'streak_7', 'lipi_legend'
    
    name_nepali     VARCHAR(100) NOT NULL,
    name_english    VARCHAR(100) NOT NULL,
    description_ne  TEXT        NOT NULL,
    description_en  TEXT        NOT NULL,
    
    icon_emoji      VARCHAR(10) NOT NULL,
    
    -- What triggers this badge
    trigger_type    VARCHAR(30) NOT NULL,
    -- 'words_taught'      — total word count threshold
    -- 'corrections_made'  — total corrections threshold
    -- 'streak_days'       — consecutive days threshold
    -- 'total_sessions'    — session count threshold
    -- 'pioneer'           — first to teach a word
    -- 'manual'            — manually awarded by admins
    
    trigger_value   INT,        -- threshold for count-based triggers
    
    -- Reward
    bonus_points    INT         NOT NULL DEFAULT 0,
    unlocks_theme   VARCHAR(30),  -- theme slug if this unlocks a theme
    
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed data
INSERT INTO badges (slug, name_nepali, name_english, description_ne, description_en,
                    icon_emoji, trigger_type, trigger_value, bonus_points) VALUES
('bronze_teacher',    'कांस्य शिक्षक',  'Bronze Teacher',
 'LIPI लाई १०० शब्द सिकाउनुभयो', 'Taught LIPI 100 words',
 '🥉', 'words_taught', 100, 50),

('silver_teacher',    'रजत शिक्षक',    'Silver Teacher',
 'LIPI लाई ५०० शब्द सिकाउनुभयो', 'Taught LIPI 500 words',
 '🥈', 'words_taught', 500, 100),

('gold_teacher',      'स्वर्ण शिक्षक',  'Gold Teacher',
 'LIPI लाई १,००० शब्द सिकाउनुभयो', 'Taught LIPI 1,000 words',
 '🥇', 'words_taught', 1000, 200),

('lipi_legend',       'LIPI लेजेन्ड',  'LIPI Legend',
 'LIPI लाई ५,००० शब्द सिकाउनुभयो', 'Taught LIPI 5,000 words',
 '⭐', 'words_taught', 5000, 500),

('correction_master', 'सुधार मास्टर',  'Correction Master',
 '५० सुधारहरू स्वीकार भए', '50 corrections accepted by LIPI',
 '✏️', 'corrections_made', 50, 100),

('streak_7',          '७ दिनको लय',    'On Fire',
 '७ दिन लगातार सिकाए', '7-day teaching streak',
 '🔥', 'streak_days', 7, 0),

('streak_30',         'समर्पित',       'Dedicated',
 '३० दिन लगातार सिकाए', '30-day teaching streak',
 '💎', 'streak_days', 30, 0),

('streak_100',        'LIPI वडा',     'LIPI Elder',
 '१०० दिन लगातार सिकाए', '100-day teaching streak',
 '🎖️', 'streak_days', 100, 0),

('pioneer',           'अग्रगामी',     'Pioneer',
 'नयाँ शब्द पहिलो पटक सिकाउनुभयो', 'First to teach LIPI a new word',
 '🏴', 'pioneer', NULL, 25);
```

---

## 5. teacher_badges

Junction table — which teachers earned which badges.

```sql
CREATE TABLE teacher_badges (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id      UUID        NOT NULL REFERENCES users(id),
    badge_id        UUID        NOT NULL REFERENCES badges(id),
    
    -- Context of earning
    earned_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_id      UUID        REFERENCES teaching_sessions(id),
    trigger_context JSONB,
    -- e.g. {"word": "नमस्ते", "word_id": "uuid"} for pioneer
    -- e.g. {"streak_days": 7} for streak badges
    -- e.g. {"total_words": 100} for milestone badges
    
    -- Notification sent?
    notified        BOOLEAN     NOT NULL DEFAULT FALSE,
    
    UNIQUE (teacher_id, badge_id)
    -- A teacher can only earn each badge once
);

CREATE INDEX idx_teacher_badges_teacher ON teacher_badges(teacher_id);
CREATE INDEX idx_teacher_badges_earned  ON teacher_badges(earned_at DESC);
```

**Badge award function:**
```python
async def check_and_award_badges(teacher_id: UUID, session_id: UUID):
    summary = await get_teacher_summary(teacher_id)
    existing_badges = await get_teacher_badge_slugs(teacher_id)

    awards = []

    # Check word milestones
    for slug, threshold in [
        ('bronze_teacher', 100),
        ('silver_teacher', 500),
        ('gold_teacher',   1000),
        ('lipi_legend',    5000),
    ]:
        if (slug not in existing_badges and
                summary.total_words_taught >= threshold):
            awards.append(slug)

    # Check correction milestone
    if ('correction_master' not in existing_badges and
            summary.total_corrections >= 50):
        awards.append('correction_master')

    # Check streak milestones
    for slug, days in [('streak_7', 7), ('streak_30', 30), ('streak_100', 100)]:
        if (slug not in existing_badges and
                summary.current_streak_days >= days):
            awards.append(slug)

    # Award each
    for slug in awards:
        badge = await get_badge_by_slug(slug)
        await insert_teacher_badge(teacher_id, badge.id, session_id)
        await add_points_transaction(
            teacher_id=teacher_id,
            session_id=session_id,
            event_type='milestone_bonus',
            base_points=badge.bonus_points,
            context={"badge_slug": slug}
        )
        await notify_teacher_badge(teacher_id, badge)
```

---

## 6. leaderboard_snapshots

Weekly and monthly snapshots. Used for:
- Historical leaderboards ("you were #3 last month")
- Winner determination at period end
- Preventing retroactive score changes affecting past winners

```sql
CREATE TABLE leaderboard_snapshots (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    
    period_type     VARCHAR(10) NOT NULL CHECK (period_type IN ('weekly', 'monthly')),
    period_start    DATE        NOT NULL,
    period_end      DATE        NOT NULL,
    
    teacher_id      UUID        NOT NULL REFERENCES users(id),
    rank            INT         NOT NULL,
    points          INT         NOT NULL,
    
    -- Category (NULL = overall)
    category        VARCHAR(30),
    -- NULL = overall ranking
    -- 'nepali', 'maithili', etc. = language-specific
    -- 'corrections', 'words', 'streak' = category-specific
    
    -- Winner flag
    is_winner       BOOLEAN     NOT NULL DEFAULT FALSE,
    reward_claimed  BOOLEAN     NOT NULL DEFAULT FALSE,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE (period_type, period_start, teacher_id, category)
);

CREATE INDEX idx_leaderboard_period
    ON leaderboard_snapshots(period_type, period_start, rank);

CREATE INDEX idx_leaderboard_teacher
    ON leaderboard_snapshots(teacher_id, period_type, period_start DESC);
```

**Snapshot creation** (cron job, runs Sunday night for weekly, 1st of month for monthly):
```sql
-- Create weekly snapshot
INSERT INTO leaderboard_snapshots (
    period_type, period_start, period_end,
    teacher_id, rank, points, category
)
SELECT
    'weekly',
    DATE_TRUNC('week', CURRENT_DATE - INTERVAL '1 day'),
    DATE_TRUNC('week', CURRENT_DATE - INTERVAL '1 day') + INTERVAL '6 days',
    teacher_id,
    ROW_NUMBER() OVER (ORDER BY points_this_week DESC),
    points_this_week,
    NULL  -- overall
FROM teacher_points_summary
WHERE points_this_week > 0
ON CONFLICT DO NOTHING;

-- Mark weekly winner
UPDATE leaderboard_snapshots
SET is_winner = TRUE
WHERE period_type = 'weekly'
  AND period_start = DATE_TRUNC('week', CURRENT_DATE - INTERVAL '1 day')
  AND rank = 1
  AND category IS NULL;
```

---

## 7. teaching_sessions

Core session tracking. One row per conversation session.

```sql
CREATE TABLE teaching_sessions (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id      UUID        NOT NULL REFERENCES users(id),
    
    -- Session lifecycle
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    duration_seconds INT,        -- computed on end
    
    -- Language
    primary_language VARCHAR(50) NOT NULL,
    detected_languages JSONB    NOT NULL DEFAULT '[]',
    -- e.g. ["ne", "en"] — languages detected in this session
    
    -- Session stats (computed at end)
    message_count   INT         NOT NULL DEFAULT 0,
    teacher_turns   INT         NOT NULL DEFAULT 0,
    lipi_turns      INT         NOT NULL DEFAULT 0,
    words_taught    INT         NOT NULL DEFAULT 0,
    corrections_made INT        NOT NULL DEFAULT 0,
    
    -- Points awarded this session
    points_earned   INT         NOT NULL DEFAULT 0,
    
    -- Quality signals
    avg_audio_quality FLOAT,    -- 0.0 to 1.0
    vad_false_positives INT     NOT NULL DEFAULT 0,
    
    -- Tone profile snapshot at session start
    register_used   VARCHAR(10),
    register_overridden BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Topics covered (extracted async)
    topics_covered  JSONB       NOT NULL DEFAULT '[]',
    
    -- Data consent
    consented_for_training BOOLEAN NOT NULL DEFAULT FALSE,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sessions_teacher
    ON teaching_sessions(teacher_id, started_at DESC);

CREATE INDEX idx_sessions_language
    ON teaching_sessions(primary_language, started_at DESC);
```

---

## 8. session_corrections

Every correction event in every session. Immutable log.

```sql
CREATE TABLE session_corrections (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID        NOT NULL REFERENCES teaching_sessions(id),
    teacher_id      UUID        NOT NULL REFERENCES users(id),
    
    -- What LIPI said (wrong)
    lipi_original   TEXT        NOT NULL,
    lipi_turn_index INT         NOT NULL,  -- which turn in the session
    
    -- What teacher corrected it to
    teacher_correction TEXT     NOT NULL,
    correction_type VARCHAR(30) NOT NULL,
    -- 'pronunciation'  — how to say it
    -- 'vocabulary'     — wrong word used
    -- 'grammar'        — wrong verb form / structure
    -- 'cultural'       — wrong cultural context
    -- 'dialect'        — regional variant
    
    -- Was the correction accepted into LIPI's learning?
    accepted        BOOLEAN     NOT NULL DEFAULT FALSE,
    acceptance_confidence FLOAT,
    rejection_reason VARCHAR(50),  -- if not accepted: 'low_credibility', 'contradiction', etc.
    
    -- Audio evidence
    audio_path      TEXT,       -- MinIO path to correction audio
    
    -- Points awarded for this correction
    points_awarded  INT         NOT NULL DEFAULT 0,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_corrections_session  ON session_corrections(session_id);
CREATE INDEX idx_corrections_teacher  ON session_corrections(teacher_id, created_at DESC);
CREATE INDEX idx_corrections_accepted ON session_corrections(accepted, created_at DESC);
```

---

## 9. session_prompt_snapshots

Audit log — what system prompt LIPI used in each session.
Important for debugging tone issues and reproducibility.

```sql
CREATE TABLE session_prompt_snapshots (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID        NOT NULL REFERENCES teaching_sessions(id),
    teacher_id  UUID        NOT NULL REFERENCES users(id),
    
    -- The assembled prompt (truncated for storage)
    prompt_hash VARCHAR(64) NOT NULL,  -- SHA-256 of full prompt
    prompt_text TEXT        NOT NULL,  -- full prompt text
    
    -- Which variables were used
    register    VARCHAR(10) NOT NULL,
    energy      VARCHAR(10) NOT NULL,
    humor_level FLOAT       NOT NULL,
    phase       INT         NOT NULL,  -- 1, 2, or 3
    
    -- LLM config
    model_name  VARCHAR(100) NOT NULL,
    temperature FLOAT        NOT NULL,
    max_tokens  INT          NOT NULL,
    
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_prompt_snapshots_session
    ON session_prompt_snapshots(session_id);
```

---

## Complete Schema Relationships

```
users
  │
  ├─── teacher_tone_profiles (1:1)
  │
  ├─── teacher_points_summary (1:1, cached)
  │
  ├─── points_transactions (1:many)
  │         │
  │         └─── linked to teaching_sessions
  │
  ├─── teacher_badges (1:many)
  │         │
  │         └─── badges (many:1)
  │
  ├─── leaderboard_snapshots (1:many)
  │
  └─── teaching_sessions (1:many)
            │
            ├─── session_corrections (1:many)
            │
            └─── session_prompt_snapshots (1:1)
```

---

## API Endpoints (FastAPI)

### Points & Leaderboard

```python
# Get teacher's current stats
GET /api/teachers/{teacher_id}/stats
→ {
    total_points, points_this_week, points_this_month,
    rank_this_week, rank_this_month, rank_alltime,
    current_streak, longest_streak,
    total_words, total_corrections, total_sessions
  }

# Get leaderboard
GET /api/leaderboard?period=weekly&category=null&limit=10&offset=0
→ {
    period: "weekly",
    period_start: "2026-04-07",
    period_end: "2026-04-13",
    entries: [
        {rank: 1, teacher_id, name, points, badge},
        ...
    ],
    teacher_rank: {rank: 3, points: 2450}  # calling teacher's position
  }

# Get teacher's badges
GET /api/teachers/{teacher_id}/badges
→ {badges: [{slug, name_ne, name_en, icon, earned_at}, ...]}

# Get session summary
GET /api/sessions/{session_id}/summary
→ {
    duration_seconds, words_taught, corrections_made,
    points_earned, badges_earned, new_rank
  }
```

### Tone Profile

```python
# Get teacher's tone profile
GET /api/teachers/{teacher_id}/tone
→ {register, energy, humor_level, code_switch_ratio, preferred_topics}

# Update register (called when teacher says "तँ भनेर बोल")
PATCH /api/teachers/{teacher_id}/tone
→ body: {register: "ta", override_set_by_user: true}

# Get session prompt (for debugging)
GET /api/sessions/{session_id}/prompt
→ {prompt_text, register, energy, phase, model_name}
```

---

## Valkey (Redis) Caching Layer

Hot data cached in Valkey for leaderboard speed:

```python
# Cache keys
LEADERBOARD_WEEKLY  = "leaderboard:weekly:v1"      # TTL: 60s
LEADERBOARD_MONTHLY = "leaderboard:monthly:v1"     # TTL: 300s
TEACHER_RANK_WEEKLY = "teacher:{id}:rank:weekly"   # TTL: 60s
TEACHER_STATS       = "teacher:{id}:stats"         # TTL: 30s

# On points_transaction insert:
# 1. Insert to PostgreSQL (source of truth)
# 2. Invalidate teacher's cached stats
# 3. Leaderboard cache rebuilds on next request (lazy)

# On session end:
# 1. Compute session summary
# 2. Update teacher_points_summary (PostgreSQL)
# 3. Check and award badges
# 4. Invalidate all teacher caches
# 5. Emit to community feed stream
```

---

## Streak Calculation

```python
def calculate_streak(teacher_id: UUID) -> tuple[int, int]:
    """
    Returns (current_streak, longest_streak) in days.
    A day counts if teacher had at least 1 session.
    """
    # Get all session dates, most recent first
    session_dates = db.query("""
        SELECT DISTINCT DATE(started_at) as session_date
        FROM teaching_sessions
        WHERE teacher_id = :tid
        ORDER BY session_date DESC
    """, tid=teacher_id)

    if not session_dates:
        return 0, 0

    today = date.today()
    current_streak = 0
    longest_streak = 0
    temp_streak = 1

    # Check if streaks are still active (taught today or yesterday)
    if session_dates[0] < today - timedelta(days=1):
        current_streak = 0  # streak broken
    else:
        # Count consecutive days backwards
        for i in range(1, len(session_dates)):
            if session_dates[i] == session_dates[i-1] - timedelta(days=1):
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                current_streak = temp_streak
                temp_streak = 1

        current_streak = temp_streak
        longest_streak = max(longest_streak, current_streak)

    return current_streak, longest_streak
```

---

## Migration Script

```sql
-- Run in order after core DATABASE_SCHEMA.md migrations

-- 001
CREATE TABLE teacher_tone_profiles (...);

-- 002
CREATE TABLE points_transactions (...);

-- 003
CREATE TABLE teacher_points_summary (...);

-- 004
CREATE TABLE badges (...);
INSERT INTO badges VALUES (...);  -- seed data above

-- 005
CREATE TABLE teacher_badges (...);

-- 006
CREATE TABLE leaderboard_snapshots (...);

-- 007
CREATE TABLE teaching_sessions (...);

-- 008
CREATE TABLE session_corrections (...);

-- 009
CREATE TABLE session_prompt_snapshots (...);

-- 010: Cron jobs
SELECT cron.schedule('rebuild-summaries', '*/5 * * * *',
    'SELECT rebuild_teacher_summary(teacher_id) FROM users');

SELECT cron.schedule('weekly-snapshot', '0 23 * * 0',
    'SELECT create_weekly_leaderboard_snapshot()');

SELECT cron.schedule('monthly-snapshot', '0 23 28-31 * *',
    'SELECT create_monthly_leaderboard_snapshot() WHERE EXTRACT(day FROM NOW()+1) = 1');
```
