# Database Schema: Recording the Teaching Moments

**Database**: PostgreSQL 15  
**ORM**: SQLAlchemy 2.0  
**Backup**: Daily snapshots to MinIO  
**Replication**: Single instance (Phase 1), read replicas (Phase 2)

---

## Core Tables

### users

```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Profile
    profile_picture_url TEXT,
    bio TEXT,
    
    -- Preferences
    preferred_language VARCHAR(10) DEFAULT 'ne',  -- Language to teach/learn
    timezone VARCHAR(50),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMP,
    
    -- Indexing
    INDEX idx_email (email),
    INDEX idx_created_at (created_at)
);
```

### language_profiles

Tracks user's relationship with each language they teach/learn:

```sql
CREATE TABLE language_profiles (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    language_id INT NOT NULL,  -- 'ne', 'en', 'nwl', etc.
    
    -- Teaching
    role VARCHAR(50),  -- 'native_speaker', 'fluent', 'learning'
    proficiency_level VARCHAR(50),  -- 'beginner', 'intermediate', 'advanced', 'native'
    
    -- Stats
    hours_taught FLOAT DEFAULT 0,
    sessions_count INT DEFAULT 0,
    words_taught INT DEFAULT 0,
    last_session_at TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY (user_id, language_id),
    INDEX idx_language_id (language_id)
);
```

### teacher_profiles

Teacher-specific contribution tracking:

```sql
CREATE TABLE teacher_profiles (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL REFERENCES users(id),
    
    -- District/Region (for eventual geographic analysis)
    district_id INT,  -- e.g., Kathmandu=1, Jhapa=2
    region VARCHAR(100),
    
    -- Credentials
    credibility_score FLOAT DEFAULT 0.5,  -- 0.0-1.0
    total_sessions INT DEFAULT 0,
    total_teaching_hours FLOAT DEFAULT 0,
    average_correction_rate FLOAT DEFAULT 0,
    
    -- Ranking
    teacher_rank VARCHAR(50),  -- 'beginner', 'experienced', 'expert'
    public_credit_enabled BOOLEAN DEFAULT FALSE,
    
    -- Audio quality stats
    average_audio_quality FLOAT DEFAULT 0,
    high_quality_utterances INT DEFAULT 0,
    
    -- Moderation
    warnings_issued INT DEFAULT 0,
    is_banned BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_credibility_score (credibility_score DESC),
    INDEX idx_teacher_rank (teacher_rank)
);
```

### consent_profiles

GDPR-compliant consent management:

```sql
CREATE TABLE consent_profiles (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL REFERENCES users(id),
    
    -- Granular consent
    audio_archive BOOLEAN DEFAULT FALSE,
    training_use BOOLEAN DEFAULT FALSE,
    public_credit BOOLEAN DEFAULT FALSE,
    data_export BOOLEAN DEFAULT TRUE,
    
    -- Training use specifics (JSON)
    training_use_models JSON DEFAULT NULL,  -- {"vits": false, "whisper": false}
    
    -- Data location
    data_location VARCHAR(50) DEFAULT 'default',  -- 'eu', 'us', 'nepal', 'default'
    
    -- Deletion preferences
    deletion_timeline VARCHAR(50) DEFAULT 'immediate',
    deletion_scheduled_for TIMESTAMP,
    deletion_reason TEXT,
    
    -- Audit trail
    consent_changes JSON DEFAULT '[]',  -- [{timestamp, field, old_value, new_value, ip}]
    
    created_at TIMESTAMP DEFAULT NOW(),
    last_updated_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_deletion_scheduled_for (deletion_scheduled_for)
);
```

### conversation_sessions

High-level session metadata:

```sql
CREATE TABLE conversation_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_token VARCHAR(255) UNIQUE NOT NULL,  -- WebSocket token
    
    -- Participant
    contributor_id BIGINT NOT NULL REFERENCES users(id),
    language_id INT,  -- What language being taught
    
    -- Metadata
    title VARCHAR(500),
    topic VARCHAR(255),
    
    -- Stats
    total_messages INT DEFAULT 0,
    total_words_exchanged INT DEFAULT 0,
    duration_seconds INT DEFAULT 0,
    
    -- Progress tracking
    user_fluency_score FLOAT DEFAULT 0,  -- 0-100%
    lipi_learning_progress FLOAT DEFAULT 0,  -- 0-100%
    
    -- Session status
    is_active BOOLEAN DEFAULT TRUE,
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    
    -- Quality
    average_confidence FLOAT,
    corrections_count INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (contributor_id) REFERENCES users(id),
    INDEX idx_session_token (session_token),
    INDEX idx_contributor_id (contributor_id),
    INDEX idx_created_at (created_at),
    INDEX idx_is_active (is_active)
);
```

### messages

Individual message records:

```sql
CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGSERIAL NOT NULL REFERENCES conversation_sessions(id),
    
    -- Sender identification
    sender VARCHAR(20),  -- 'user' or 'lipi'
    sender_id BIGINT,  -- If user, who sent it
    
    -- Text content (multiple representations)
    text_original VARCHAR(2000),  -- Raw from STT or user input
    text_nepali VARCHAR(2000),    -- Normalized/cleaned Nepali
    text_english VARCHAR(2000),   -- English translation (optional)
    
    -- Audio
    audio_file_path TEXT,         -- MinIO path to audio
    audio_duration_ms INT,
    audio_quality FLOAT,          -- 0-1 quality score
    
    -- STT metadata
    stt_confidence FLOAT,         -- 0-1
    stt_model_used VARCHAR(100),  -- 'whisper_lora_kathmandu', etc.
    
    -- TTS metadata (if LIPI sent)
    tts_voice_model VARCHAR(100), -- 'vits_speaker_123', 'generic_base'
    
    -- Teacher corrections
    is_corrected_by_user BOOLEAN DEFAULT FALSE,
    correction_text VARCHAR(2000),
    correction_timestamp TIMESTAMP,
    
    -- Processing
    processing_time_ms INT,       -- How long to generate response
    confidence_score FLOAT,       -- Overall message confidence
    
    -- Moderation
    is_flagged BOOLEAN DEFAULT FALSE,
    moderation_status VARCHAR(50) DEFAULT 'unreviewed', -- 'unreviewed', 'pending', 'approved', 'rejected'
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (session_id) REFERENCES conversation_sessions(id),
    INDEX idx_session_id (session_id),
    INDEX idx_sender (sender),
    INDEX idx_created_at (created_at),
    INDEX idx_is_corrected_by_user (is_corrected_by_user)
);
```

### vocabulary_entries

Core learning: words LIPI learns:

```sql
CREATE TABLE vocabulary_entries (
    id BIGSERIAL PRIMARY KEY,
    
    -- Word identity
    word_nepali VARCHAR(255) UNIQUE NOT NULL,
    word_english VARCHAR(255),
    word_phonetic VARCHAR(255),  -- IPA or similar
    
    -- Part of speech
    part_of_speech VARCHAR(50),  -- 'noun', 'verb', 'adjective', etc.
    
    -- Meaning
    definition TEXT,
    multiple_meanings JSON,  -- [{"meaning": "...", "context": "...", "source": teacher_id}]
    
    -- Learning confidence
    confidence FLOAT DEFAULT 0.5,  -- 0-1, increases with corrections
    
    -- Teaching history
    first_taught_by BIGINT REFERENCES users(id),
    first_taught_at TIMESTAMP,
    taught_by_count INT DEFAULT 0,  -- How many teachers taught this
    
    -- Usage stats
    times_encountered INT DEFAULT 0,
    times_used_correctly INT DEFAULT 0,
    last_used_at TIMESTAMP,
    
    -- Contextual examples
    example_sentences JSON,  -- [{"text": "...", "source": teacher_id}]
    context_tags JSON,       -- ["greeting", "casual", "formal"]
    
    -- Regional variations
    regional_pronunciations JSON,  -- {"kathmandu": "...", "eastern": "..."}
    accents_heard JSON,            -- {"kathmandu": 8, "eastern": 4}
    
    -- Quality metrics
    average_teacher_credibility FLOAT,  -- Avg credibility of all teachers
    contradiction_detected BOOLEAN DEFAULT FALSE,
    contradiction_note TEXT,
    requires_user_clarification BOOLEAN DEFAULT FALSE,
    
    -- Training use consent
    training_blocked BOOLEAN DEFAULT FALSE,  -- User didn't consent
    
    -- Troll Prevention
    is_flagged BOOLEAN DEFAULT FALSE,
    moderation_status VARCHAR(50) DEFAULT 'unreviewed',
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (first_taught_by) REFERENCES users(id),
    INDEX idx_word_nepali (word_nepali),
    INDEX idx_confidence (confidence DESC),
    INDEX idx_times_encountered (times_encountered DESC),
    INDEX idx_created_at (created_at),
    INDEX idx_taught_by_count (taught_by_count DESC)
);
```

### vocabulary_teaching_history

Track which teacher taught which word:

```sql
CREATE TABLE vocabulary_teaching_history (
    id BIGSERIAL PRIMARY KEY,
    vocab_id BIGINT NOT NULL REFERENCES vocabulary_entries(id),
    teacher_id BIGINT NOT NULL REFERENCES users(id),
    
    -- Teaching event
    lesson_date TIMESTAMP,
    is_correction BOOLEAN DEFAULT FALSE,
    context TEXT,  -- Original sentence where word appeared
    
    -- Teacher's credentials at time of teaching
    teacher_credibility_at_time FLOAT,
    teacher_rank_at_time VARCHAR(50),
    
    -- Outcome
    lipi_confidence_before FLOAT,
    lipi_confidence_after FLOAT,
    confidence_change FLOAT,
    
    -- Message reference
    message_id BIGINT REFERENCES messages(id),
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (vocab_id) REFERENCES vocabulary_entries(id),
    FOREIGN KEY (teacher_id) REFERENCES users(id),
    INDEX idx_vocab_id (vocab_id),
    INDEX idx_teacher_id (teacher_id),
    INDEX idx_lesson_date (lesson_date)
);
```

### grammar_entries

Grammar rules LIPI learns:

```sql
CREATE TABLE grammar_entries (
    id BIGSERIAL PRIMARY KEY,
    
    -- Rule identity
    rule_name VARCHAR(255) UNIQUE NOT NULL,
    rule_category VARCHAR(100),  -- 'tense', 'agreement', 'case', etc.
    rule_description TEXT,
    
    -- Learning confidence
    confidence FLOAT DEFAULT 0.5,
    
    -- Examples (correct and incorrect)
    examples_correct JSON,  -- [{"text": "...", "source": teacher_id}]
    examples_incorrect JSON,  -- [{"text": "...", "source": teacher_id}]
    
    -- Usage stats
    times_encountered INT DEFAULT 0,
    times_applied_correctly INT DEFAULT 0,
    
    -- Teaching history
    first_taught_by BIGINT REFERENCES users(id),
    first_taught_at TIMESTAMP,
    taught_by_count INT DEFAULT 0,
    
    -- Complexity assessment
    complexity_level VARCHAR(50),  -- 'beginner', 'intermediate', 'advanced'
    related_grammar_rules JSON,   -- [rule_id1, rule_id2]
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (first_taught_by) REFERENCES users(id),
    INDEX idx_rule_name (rule_name),
    INDEX idx_confidence (confidence DESC),
    INDEX idx_times_encountered (times_encountered DESC)
);
```

### speaker_embeddings

Speaker identification and dialect clustering:

```sql
CREATE TABLE speaker_embeddings (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    
    -- Embedding vector (512-dimensional)
    embedding VECTOR(512),  -- Using pgvector extension
    
    -- Audio source
    audio_hash VARCHAR(64) NOT NULL,
    message_id BIGINT REFERENCES messages(id),
    
    -- Metadata
    language_detected VARCHAR(10),
    audio_duration_seconds FLOAT,
    audio_quality_score FLOAT,
    
    -- Dialect assignment
    assigned_dialect_cluster INT,  -- Which cluster this speaker belongs to
    confidence_in_cluster FLOAT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_id (user_id),
    INDEX idx_assigned_dialect_cluster (assigned_dialect_cluster),
    INDEX idx_created_at (created_at)
);
```

### dialect_profiles

Discovered dialect clusters:

```sql
CREATE TABLE dialect_profiles (
    id SERIAL PRIMARY KEY,
    
    -- Cluster info
    cluster_id INT UNIQUE,
    name VARCHAR(100),  -- "Kathmandu", "Eastern", "Terai"
    
    -- Statistics
    speaker_count INT DEFAULT 0,
    total_utterances INT DEFAULT 0,
    average_embedding VECTOR(512),
    
    -- Geographic distribution
    primary_districts JSON,  -- {"Kathmandu": 50, "Bhaktapur": 40}
    
    -- Model info
    whisper_lora_path TEXT,     -- Path to LoRA checkpoint
    whisper_lora_wer FLOAT,     -- WER score
    vits_lora_path TEXT,        -- Path to voice LoRA
    vits_lora_mos FLOAT,        -- MOS score
    
    -- Last training
    last_trained_at TIMESTAMP,
    samples_since_last_training INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_cluster_id (cluster_id),
    INDEX idx_speaker_count (speaker_count DESC),
    INDEX idx_last_trained_at (last_trained_at)
);
```

### speaker_voice_models

Speaker-specific TTS voice models:

```sql
CREATE TABLE speaker_voice_models (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    
    -- Model info
    vits_checkpoint TEXT,  -- MinIO path
    mos_score FLOAT,       -- Mean Opinion Score
    
    -- Training data
    utterances_used INT,
    total_duration_hours FLOAT,
    
    -- Quality gate
    quality_gate_passed BOOLEAN DEFAULT FALSE,
    quality_gate_notes TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE KEY (user_id, created_at),
    INDEX idx_user_id (user_id),
    INDEX idx_mos_score (mos_score DESC)
);
```

### teacher_impact

High-level teacher contribution tracking:

```sql
CREATE TABLE teacher_impact (
    id BIGSERIAL PRIMARY KEY,
    teacher_id BIGINT UNIQUE NOT NULL REFERENCES users(id),
    
    -- Contribution metrics
    words_taught INT DEFAULT 0,
    unique_words_taught INT DEFAULT 0,
    corrections_provided INT DEFAULT 0,
    grammar_rules_taught INT DEFAULT 0,
    dialects_represented INT DEFAULT 0,
    
    -- Time investment
    sessions_count INT DEFAULT 0,
    hours_conversation FLOAT DEFAULT 0,
    average_session_duration_minutes FLOAT DEFAULT 0,
    
    -- Impact
    lipi_improvement_percent FLOAT DEFAULT 0,  -- +X% fluency from this teacher
    avg_confidence_increase FLOAT DEFAULT 0,
    
    -- Recognition
    teacher_rank VARCHAR(50),
    top_teacher_ranking INT,
    
    -- Monthly stats
    this_month_words INT DEFAULT 0,
    this_month_hours FLOAT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (teacher_id) REFERENCES users(id),
    INDEX idx_lipi_improvement_percent (lipi_improvement_percent DESC),
    INDEX idx_teacher_rank (teacher_rank),
    INDEX idx_hours_conversation (hours_conversation DESC)
);
```

### learning_stats

Aggregate session learning statistics:

```sql
CREATE TABLE learning_stats (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT UNIQUE NOT NULL REFERENCES conversation_sessions(id),
    
    -- Learning outcomes
    new_vocabulary INT,
    unique_vocabulary INT,
    new_grammar_rules INT,
    
    -- Confidence changes
    avg_confidence_before FLOAT,
    avg_confidence_after FLOAT,
    confidence_improvement FLOAT,
    
    -- Fluency estimate
    lipi_fluency_estimate FLOAT,  -- 0-100%
    user_fluency_estimate FLOAT,
    
    -- Word frequency distribution
    high_frequency_words JSON,  -- Top 10 words learned
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (session_id) REFERENCES conversation_sessions(id),
    INDEX idx_session_id (session_id)
);
```

### moderation_logs

Tracking quarantined teachings and admin review actions:

```sql
CREATE TABLE moderation_logs (
    id BIGSERIAL PRIMARY KEY,
    
    -- Entity logged
    message_id BIGINT REFERENCES messages(id),
    vocab_id BIGINT REFERENCES vocabulary_entries(id),
    teacher_id BIGINT NOT NULL REFERENCES users(id),
    
    -- Incident details
    reason VARCHAR(100),  -- 'anomaly_detected', 'community_flag', 'hate_speech_pre_filter'
    context_text TEXT,
    severity INT DEFAULT 1,  -- 1 (low) to 5 (high)
    
    -- Resolution
    status VARCHAR(50) DEFAULT 'pending_review',
    reviewed_by BIGINT REFERENCES users(id),  -- Admin who reviewed
    reviewed_at TIMESTAMP,
    admin_notes TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (teacher_id) REFERENCES users(id),
    INDEX idx_status (status),
    INDEX idx_teacher_id (teacher_id)
);
```

---

## Indexes for Performance

### Most Critical Indexes

```sql
-- Real-time chat queries
CREATE INDEX idx_session_active ON conversation_sessions(is_active, created_at DESC);
CREATE INDEX idx_message_session ON messages(session_id, created_at);
CREATE INDEX idx_user_sessions ON conversation_sessions(contributor_id, created_at DESC);

-- Learning queries (async workers)
CREATE INDEX idx_vocab_confidence ON vocabulary_entries(confidence DESC, times_encountered DESC);
CREATE INDEX idx_grammar_confidence ON grammar_entries(confidence DESC);

-- Teacher ranking
CREATE INDEX idx_teacher_hours ON teacher_impact(hours_conversation DESC);
CREATE INDEX idx_teacher_rank ON teacher_profiles(credibility_score DESC);

-- Dialect clustering
CREATE INDEX idx_dialect_cluster ON speaker_embeddings(assigned_dialect_cluster);

-- Deletion/GDPR compliance
CREATE INDEX idx_deletion_scheduled ON consent_profiles(deletion_scheduled_for);
```

### Full-Text Search (Optional, Phase 2)

```sql
-- For searching vocabulary by definition
ALTER TABLE vocabulary_entries ADD COLUMN search_vector tsvector;
CREATE INDEX idx_vocab_search ON vocabulary_entries USING GIN(search_vector);

-- Update vector on changes
CREATE TRIGGER trg_vocab_search_update
BEFORE INSERT OR UPDATE ON vocabulary_entries
FOR EACH ROW EXECUTE FUNCTION
tsvector_update_trigger(search_vector, 'english', definition, word_nepali);
```

---

## Data Retention Policies

```python
async def enforce_retention_policies():
    """
    Run daily to clean up expired data
    """
    
    # Rule 1: Delete raw audio after 90 days (if not archived)
    old_messages = db.query(Message).filter(
        Message.audio_file_path != None,
        Message.created_at < now() - timedelta(days=90)
    )
    for msg in old_messages:
        minio.remove_object("lipi-audio", msg.audio_file_path)
        msg.audio_file_path = None
    
    # Rule 2: Archive conversations older than 1 year
    old_sessions = db.query(ConversationSession).filter(
        ConversationSession.created_at < now() - timedelta(days=365)
    )
    for session in old_sessions:
        await archive_session_to_minIO(session)
    
    # Rule 3: Process scheduled deletions
    scheduled_deletions = db.query(ConsentProfile).filter(
        ConsentProfile.deletion_scheduled_for <= now(),
        ConsentProfile.deletion_status == "scheduled_with_grace"
    )
    for consent in scheduled_deletions:
        await delete_user_data(consent.user_id)
    
    db.commit()
```

---

## Scalability: Partitioning Strategy (Phase 2)

```sql
-- Partition messages by month (reduces query time for recent data)
CREATE TABLE messages_2026_04 PARTITION OF messages
  FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

CREATE TABLE messages_2026_05 PARTITION OF messages
  FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

-- Partition vocabulary_teaching_history by teacher_id (1000 partitions)
-- Reduces contention when logging teaching events
```

This structure enables:
- Fast real-time chat queries
- Efficient learning extraction (async workers)
- GDPR compliance (granular consent, deletion)
- Teacher attribution (every word knows who taught it)
- Multi-teacher learning (conflicting teachings tracked)
- Dialect discovery (speaker embedding clustering)

