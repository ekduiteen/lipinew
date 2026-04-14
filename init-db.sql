-- ============================================================================
-- LIPI PostgreSQL Schema
-- Runs on first container start. Idempotent where possible.
-- ============================================================================

-- ─── Extensions ─────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================================
-- 1. USERS
-- ============================================================================
CREATE TABLE users (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Auth
    email               VARCHAR(255)    UNIQUE,
    phone               VARCHAR(20)     UNIQUE,
    auth_provider       VARCHAR(20)     NOT NULL CHECK (auth_provider IN ('google', 'phone')),
    auth_provider_id    VARCHAR(255),

    -- Profile (collected during onboarding)
    first_name          VARCHAR(100)    NOT NULL,
    last_name           VARCHAR(100),
    age                 INT             CHECK (age BETWEEN 1 AND 120),
    gender              VARCHAR(20)     CHECK (gender IN ('male', 'female', 'other', 'prefer_not_to_say')),
    primary_language    VARCHAR(50)     NOT NULL DEFAULT 'nepali',
    other_languages     JSONB           NOT NULL DEFAULT '[]',
    hometown            VARCHAR(255),
    education_level     VARCHAR(50)     CHECK (education_level IN
                            ('primary', 'secondary', 'bachelors', 'masters', 'phd', 'prefer_not_to_say')),

    -- Trust + moderation
    credibility_score   FLOAT           NOT NULL DEFAULT 0.5 CHECK (credibility_score BETWEEN 0 AND 1),
    troll_score         INT             NOT NULL DEFAULT 0,
    is_banned           BOOLEAN         NOT NULL DEFAULT FALSE,
    is_admin            BOOLEAN         NOT NULL DEFAULT FALSE,

    -- Consent (granular)
    consent_audio_training      BOOLEAN NOT NULL DEFAULT FALSE,
    consent_public_credit       BOOLEAN NOT NULL DEFAULT FALSE,
    consent_leaderboard_name    BOOLEAN NOT NULL DEFAULT TRUE,
    consent_dialect_training    BOOLEAN NOT NULL DEFAULT FALSE,

    -- Onboarding
    onboarding_completed_at     TIMESTAMPTZ,

    -- Metadata
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);

CREATE INDEX idx_users_email ON users(email) WHERE email IS NOT NULL;
CREATE INDEX idx_users_phone ON users(phone) WHERE phone IS NOT NULL;
CREATE INDEX idx_users_language ON users(primary_language);
CREATE INDEX idx_users_credibility ON users(credibility_score) WHERE NOT is_banned;

-- ============================================================================
-- 2. TEACHER TONE PROFILES (per-teacher communication style)
-- ============================================================================
CREATE TABLE teacher_tone_profiles (
    teacher_id              UUID            PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,

    register                VARCHAR(10)     NOT NULL DEFAULT 'tapai'
                                CHECK (register IN ('hajur', 'tapai', 'timi', 'ta')),
    override_set_by_user    BOOLEAN         NOT NULL DEFAULT FALSE,

    energy                  VARCHAR(10)     NOT NULL DEFAULT 'medium'
                                CHECK (energy IN ('high', 'medium', 'low')),
    humor_level             FLOAT           NOT NULL DEFAULT 0.3
                                CHECK (humor_level BETWEEN 0.0 AND 1.0),
    code_switch_ratio       FLOAT           NOT NULL DEFAULT 0.0
                                CHECK (code_switch_ratio BETWEEN 0.0 AND 1.0),

    avg_response_length     INT             NOT NULL DEFAULT 15,
    avg_session_minutes     FLOAT           NOT NULL DEFAULT 10.0,

    preferred_topics        JSONB           NOT NULL DEFAULT '[]',
    recent_topics           JSONB           NOT NULL DEFAULT '[]',

    sessions_analyzed       INT             NOT NULL DEFAULT 0,
    last_updated            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tone_profiles_register ON teacher_tone_profiles(register);

-- ============================================================================
-- 3. TEACHING SESSIONS
-- ============================================================================
CREATE TABLE teaching_sessions (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id              UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    started_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    ended_at                TIMESTAMPTZ,
    duration_seconds        INT,

    primary_language        VARCHAR(50)     NOT NULL,
    detected_languages      JSONB           NOT NULL DEFAULT '[]',

    message_count           INT             NOT NULL DEFAULT 0,
    teacher_turns           INT             NOT NULL DEFAULT 0,
    lipi_turns              INT             NOT NULL DEFAULT 0,
    words_taught            INT             NOT NULL DEFAULT 0,
    corrections_made        INT             NOT NULL DEFAULT 0,

    points_earned           INT             NOT NULL DEFAULT 0,

    avg_audio_quality       FLOAT,
    vad_false_positives     INT             NOT NULL DEFAULT 0,

    register_used           VARCHAR(10),
    register_overridden     BOOLEAN         NOT NULL DEFAULT FALSE,

    topics_covered          JSONB           NOT NULL DEFAULT '[]',
    consented_for_training  BOOLEAN         NOT NULL DEFAULT FALSE,

    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sessions_teacher ON teaching_sessions(teacher_id, started_at DESC);
CREATE INDEX idx_sessions_language ON teaching_sessions(primary_language, started_at DESC);
CREATE INDEX idx_sessions_active ON teaching_sessions(teacher_id) WHERE ended_at IS NULL;

-- ============================================================================
-- 4. POINTS TRANSACTIONS (immutable event log)
-- ============================================================================
CREATE TABLE points_transactions (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id          UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id          UUID            REFERENCES teaching_sessions(id) ON DELETE SET NULL,

    event_type          VARCHAR(50)     NOT NULL,

    base_points         INT             NOT NULL,
    multiplier          FLOAT           NOT NULL DEFAULT 1.0,
    final_points        INT             NOT NULL,

    context             JSONB           NOT NULL DEFAULT '{}',

    validated           BOOLEAN         NOT NULL DEFAULT FALSE,
    validation_method   VARCHAR(30),

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_points_teacher_created ON points_transactions(teacher_id, created_at DESC);
CREATE INDEX idx_points_created ON points_transactions(created_at DESC);
CREATE INDEX idx_points_event_type ON points_transactions(event_type);
CREATE INDEX idx_points_validated ON points_transactions(teacher_id, validated, created_at)
    WHERE validated = TRUE;

-- ============================================================================
-- 5. TEACHER POINTS SUMMARY (cached aggregates)
-- ============================================================================
CREATE TABLE teacher_points_summary (
    teacher_id              UUID            PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,

    total_points            INT             NOT NULL DEFAULT 0,
    total_words_taught      INT             NOT NULL DEFAULT 0,
    total_corrections       INT             NOT NULL DEFAULT 0,
    total_sessions          INT             NOT NULL DEFAULT 0,
    total_minutes           INT             NOT NULL DEFAULT 0,

    current_streak_days     INT             NOT NULL DEFAULT 0,
    longest_streak_days     INT             NOT NULL DEFAULT 0,
    last_session_date       DATE,

    points_this_week        INT             NOT NULL DEFAULT 0,
    points_this_month       INT             NOT NULL DEFAULT 0,

    week_start              DATE            NOT NULL DEFAULT CURRENT_DATE,
    month_start             DATE            NOT NULL DEFAULT DATE_TRUNC('month', CURRENT_DATE),

    last_rebuilt            TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_summary_weekly  ON teacher_points_summary(points_this_week DESC);
CREATE INDEX idx_summary_monthly ON teacher_points_summary(points_this_month DESC);
CREATE INDEX idx_summary_alltime ON teacher_points_summary(total_points DESC);

-- ============================================================================
-- 6. BADGES (definitions)
-- ============================================================================
CREATE TABLE badges (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    slug                VARCHAR(50)     UNIQUE NOT NULL,

    name_nepali         VARCHAR(100)    NOT NULL,
    name_english        VARCHAR(100)    NOT NULL,
    description_ne      TEXT            NOT NULL,
    description_en      TEXT            NOT NULL,

    icon_emoji          VARCHAR(10)     NOT NULL,

    trigger_type        VARCHAR(30)     NOT NULL,
    trigger_value       INT,

    bonus_points        INT             NOT NULL DEFAULT 0,
    unlocks_theme       VARCHAR(30),

    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ─── Badge seed data ────────────────────────────────────────────────────────
INSERT INTO badges (slug, name_nepali, name_english, description_ne, description_en, icon_emoji, trigger_type, trigger_value, bonus_points) VALUES
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

-- ============================================================================
-- 7. TEACHER BADGES (junction table)
-- ============================================================================
CREATE TABLE teacher_badges (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id          UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    badge_id            UUID            NOT NULL REFERENCES badges(id) ON DELETE CASCADE,

    earned_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    session_id          UUID            REFERENCES teaching_sessions(id) ON DELETE SET NULL,
    trigger_context     JSONB,

    notified            BOOLEAN         NOT NULL DEFAULT FALSE,

    UNIQUE (teacher_id, badge_id)
);

CREATE INDEX idx_teacher_badges_teacher ON teacher_badges(teacher_id);
CREATE INDEX idx_teacher_badges_earned  ON teacher_badges(earned_at DESC);

-- ============================================================================
-- 8. LEADERBOARD SNAPSHOTS (weekly + monthly)
-- ============================================================================
CREATE TABLE leaderboard_snapshots (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    period_type         VARCHAR(10)     NOT NULL CHECK (period_type IN ('weekly', 'monthly')),
    period_start        DATE            NOT NULL,
    period_end          DATE            NOT NULL,

    teacher_id          UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rank                INT             NOT NULL,
    points              INT             NOT NULL,

    category            VARCHAR(30),

    is_winner           BOOLEAN         NOT NULL DEFAULT FALSE,
    reward_claimed      BOOLEAN         NOT NULL DEFAULT FALSE,

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    UNIQUE (period_type, period_start, teacher_id, category)
);

CREATE INDEX idx_leaderboard_period
    ON leaderboard_snapshots(period_type, period_start, rank);
CREATE INDEX idx_leaderboard_teacher
    ON leaderboard_snapshots(teacher_id, period_type, period_start DESC);

-- ============================================================================
-- 9. SESSION CORRECTIONS (correction events log)
-- ============================================================================
CREATE TABLE session_corrections (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id              UUID            NOT NULL REFERENCES teaching_sessions(id) ON DELETE CASCADE,
    teacher_id              UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    lipi_original           TEXT            NOT NULL,
    lipi_turn_index         INT             NOT NULL,

    teacher_correction      TEXT            NOT NULL,
    correction_type         VARCHAR(30)     NOT NULL
                                CHECK (correction_type IN
                                    ('pronunciation', 'vocabulary', 'grammar', 'cultural', 'dialect')),

    accepted                BOOLEAN         NOT NULL DEFAULT FALSE,
    acceptance_confidence   FLOAT,
    rejection_reason        VARCHAR(50),

    audio_path              TEXT,
    points_awarded          INT             NOT NULL DEFAULT 0,

    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_corrections_session  ON session_corrections(session_id);
CREATE INDEX idx_corrections_teacher  ON session_corrections(teacher_id, created_at DESC);
CREATE INDEX idx_corrections_accepted ON session_corrections(accepted, created_at DESC);

-- ============================================================================
-- 10. SESSION PROMPT SNAPSHOTS (audit log)
-- ============================================================================
CREATE TABLE session_prompt_snapshots (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID            NOT NULL REFERENCES teaching_sessions(id) ON DELETE CASCADE,
    teacher_id      UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    prompt_hash     VARCHAR(64)     NOT NULL,
    prompt_text     TEXT            NOT NULL,

    register        VARCHAR(10)     NOT NULL,
    energy          VARCHAR(10)     NOT NULL,
    humor_level     FLOAT           NOT NULL,
    phase           INT             NOT NULL,

    model_name      VARCHAR(100)    NOT NULL,
    temperature     FLOAT           NOT NULL,
    max_tokens      INT             NOT NULL,

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_prompt_snapshots_session ON session_prompt_snapshots(session_id);

-- ============================================================================
-- 11. MESSAGES (conversation turns)
-- ============================================================================
CREATE TABLE messages (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID            NOT NULL REFERENCES teaching_sessions(id) ON DELETE CASCADE,
    teacher_id          UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    turn_index          INT             NOT NULL,
    role                VARCHAR(10)     NOT NULL CHECK (role IN ('teacher', 'lipi')),

    text                TEXT            NOT NULL,
    detected_language   VARCHAR(10),
    audio_path          TEXT,
    audio_duration_ms   INT,

    -- STT confidence
    stt_confidence      FLOAT,

    -- LLM metadata (if role='lipi')
    llm_model           VARCHAR(50),
    llm_tokens          INT,
    llm_latency_ms      INT,

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_session_turn ON messages(session_id, turn_index);
CREATE INDEX idx_messages_teacher ON messages(teacher_id, created_at DESC);

-- ============================================================================
-- 12. VOCABULARY ENTRIES (words LIPI has learned)
-- ============================================================================
CREATE TABLE vocabulary_entries (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    word                VARCHAR(255)    NOT NULL,
    language            VARCHAR(50)     NOT NULL,
    definition          TEXT,
    pronunciation_ipa   VARCHAR(255),

    -- Confidence + sourcing
    confidence          FLOAT           NOT NULL DEFAULT 0.5
                            CHECK (confidence BETWEEN 0 AND 1),
    times_taught        INT             NOT NULL DEFAULT 1,
    times_corrected     INT             NOT NULL DEFAULT 0,

    -- Pioneer (first to teach)
    pioneer_teacher_id  UUID            REFERENCES users(id),

    -- Flags for moderation
    flags               JSONB           NOT NULL DEFAULT '[]',

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    UNIQUE (word, language)
);

CREATE INDEX idx_vocab_word ON vocabulary_entries(word);
CREATE INDEX idx_vocab_language ON vocabulary_entries(language);
CREATE INDEX idx_vocab_pioneer ON vocabulary_entries(pioneer_teacher_id);
CREATE INDEX idx_vocab_word_trgm ON vocabulary_entries USING gin (word gin_trgm_ops);

-- ============================================================================
-- 13. VOCABULARY TEACHERS (which teachers contributed each word)
-- ============================================================================
CREATE TABLE vocabulary_teachers (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    vocabulary_id       UUID            NOT NULL REFERENCES vocabulary_entries(id) ON DELETE CASCADE,
    teacher_id          UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id          UUID            REFERENCES teaching_sessions(id) ON DELETE SET NULL,

    contribution_type   VARCHAR(20)     NOT NULL CHECK (contribution_type IN
                            ('first_teach', 'reinforcement', 'correction', 'definition')),
    confidence_added    FLOAT           NOT NULL DEFAULT 0.0,

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    UNIQUE (vocabulary_id, teacher_id, contribution_type)
);

CREATE INDEX idx_vocab_teachers_vocab ON vocabulary_teachers(vocabulary_id);
CREATE INDEX idx_vocab_teachers_teacher ON vocabulary_teachers(teacher_id);

-- ============================================================================
-- 14. SPEAKER EMBEDDINGS (for dialect clustering — pgvector)
-- ============================================================================
CREATE TABLE speaker_embeddings (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id          UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id          UUID            REFERENCES teaching_sessions(id) ON DELETE SET NULL,

    embedding           vector(512)     NOT NULL,

    audio_path          TEXT            NOT NULL,
    audio_duration_ms   INT             NOT NULL,
    detected_language   VARCHAR(10),

    -- Cluster assignment (k-NN dialect grouping)
    dialect_cluster_id  INT,

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_speaker_embeddings_teacher ON speaker_embeddings(teacher_id);
CREATE INDEX idx_speaker_embeddings_cluster ON speaker_embeddings(dialect_cluster_id);
-- HNSW index for fast nearest-neighbor search
CREATE INDEX idx_speaker_embeddings_vector ON speaker_embeddings
    USING hnsw (embedding vector_cosine_ops);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_vocab_updated_at
    BEFORE UPDATE ON vocabulary_entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Rebuild a teacher's points summary from transactions
CREATE OR REPLACE FUNCTION rebuild_teacher_summary(p_teacher_id UUID)
RETURNS VOID AS $$
DECLARE
    v_week_start  DATE := DATE_TRUNC('week', CURRENT_DATE);
    v_month_start DATE := DATE_TRUNC('month', CURRENT_DATE);
BEGIN
    INSERT INTO teacher_points_summary (
        teacher_id, total_points, total_words_taught, total_corrections,
        total_sessions, points_this_week, points_this_month,
        week_start, month_start, last_rebuilt
    )
    SELECT
        p_teacher_id,
        COALESCE(SUM(final_points) FILTER (WHERE validated), 0),
        COALESCE(COUNT(*) FILTER (WHERE event_type = 'word_learned' AND validated), 0),
        COALESCE(COUNT(*) FILTER (WHERE event_type = 'correction_accepted' AND validated), 0),
        COALESCE(COUNT(DISTINCT session_id), 0),
        COALESCE(SUM(final_points) FILTER (WHERE validated AND created_at >= v_week_start), 0),
        COALESCE(SUM(final_points) FILTER (WHERE validated AND created_at >= v_month_start), 0),
        v_week_start, v_month_start, NOW()
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

-- ============================================================================
-- DONE
-- ============================================================================
