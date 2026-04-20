# LIPI's 5-Step Learning Cycle

LIPI learns from teachers through a repeatable 5-step cycle: **OBSERVE → PROCESS → REPEAT → EXTRACT → STORE**.

As of `2026-04-18`, this cycle includes a production turn-intelligence layer:
- session-aware keyterm preparation before STT
- transcript repair for low-confidence critical words
- per-turn intent recognition
- structured entity extraction
- code-switch analysis
- learning usability / weighting
- normalized storage in `message_analysis` and `message_entities`

This cycle runs for every user message and represents LIPI's complete learning journey from raw input to persistent knowledge.

---

## Overview: The Complete Cycle

```
┌──────────────────────────────────────────────────────────────────┐
│                     User Teaches LIPI                            │
│                   (Expert native speaker)                        │
└──────────────────┬───────────────────────────────────────────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │  STEP 1: OBSERVE    │ (Listen and capture)
         │  ├─ Audio recording │
         │  ├─ STT transcription
         │  └─ Confidence score│
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  STEP 2: PROCESS    │ (Understand)
         │  ├─ Intent labeling │
         │  ├─ Entity extraction
         │  └─ Code-switch scan│
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  STEP 3: REPEAT     │ (Confirm understanding)
         │  ├─ Generate response
         │  ├─ Ask for validation
         │  └─ TTS synthesis   │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  STEP 4: EXTRACT    │ (Learn from correction)
         │  ├─ Async enrichment│
         │  ├─ Weight by intent
         │  └─ Update confidence│
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  STEP 5: STORE      │ (Remember forever)
         │  ├─ Save to DB      │
         │  ├─ Archive audio   │
         │  └─ Index for search│
         └──────────────────────┘
```

---

## Step 1: OBSERVE — "Listening"

**Goal**: Capture exactly what the teacher said (preserve their voice, accent, pronunciation)

### Input
```python
{
  "type": "user_audio",           # Either audio or text
  "content": bytes,                # Raw WAV/MP3 audio
  "teacher_id": 42,
  "session_id": "abc123",
  "timestamp": "2026-04-13T14:32:00Z",
  "device": "web_microphone",
  "audio_quality": 16000           # 16kHz sample rate
}
```

### Processing (GPU 5: STT)

**Production update: keyterm-aware STT**
```python
keyterms = prepare_turn_keyterms(
    session_memory=session_memory,
    teacher_history=teacher_history,
    admin_seed_lists=admin_keyterm_seeds,
)

stt_result = stt.transcribe(
    audio_bytes,
    prompt=keyterms.prompt_hint,
    language_hint=selected_language,
)

repair = repair_transcript(
    transcript=stt_result.text,
    stt_confidence=stt_result.confidence,
    keyterms=keyterms,
)
```

**faster-whisper large-v3 inference:**
```python
audio_bytes → Whisper encoder → Speech features
                ↓
            Whisper decoder → Text tokens → Decode text

Output confidence = attention_score(best_5_alternatives)
```

**Dialect-specific transcription:**
```python
# Option 1: Language detection first (always)
if whisper_lang_detect(audio) == "ne":
    # Option 2: Load dialect LoRA based on teacher region
    if teacher.district in kathmandu_districts:
        load_whisper_lora_kathmandu()
    elif teacher.district in eastern_districts:
        load_whisper_lora_eastern()
    else:
        use_generic_whisper()
```

**Speaker embedding extraction (concurrent):**
```python
# Extract 512-dim speaker embedding for dialect clustering
speaker_embedding = e5_model.encode(audio_features)
# This embedding is used in Step 4 for voice selection
```

### Output
```python
{
  "observed_text": "नमस्ते, मेरो नाम राज हो।",
  "confidence": 0.92,             # STT confidence (0-1)
  "language": "ne",               # Detected language
  "duration": 2.5,                # Audio duration in seconds
  "speaker_embedding": [...],     # 512-dim vector
  "audio_path": "s3://lipi-audio/abc123.wav",
  "transcription_model": "whisper-large-v3-kathmandu-lora",
  "alternatives": [
    {"text": "नमस्ते, मेरो नाम राज हो।", "confidence": 0.92},
    {"text": "नमस्ते, मेरो नाम राज हुँ।", "confidence": 0.06},
    {"text": "नमस्ते, मेरो नाम राज हुन।", "confidence": 0.02}
  ]
}
```

### Latency Target: <200ms
- Audio capture: 100ms
- Whisper inference: 150ms (averaged over 60s audio)
- Speaker embedding: 50ms (parallel)
- Network: 50ms
- **Total**: ~200ms

---

## Step 2: PROCESS — "Understanding"

**Goal**: Extract what the teacher taught (vocabulary, grammar, concepts)

### Input
```python
# From Step 1 OBSERVE
observed_text = "नमस्ते, मेरो नाम राज हो।"
confidence = 0.92
language = "ne"
```

### Processing (GPU 7: NLP + CPU: stanza)

**Production update: turn intelligence**
```python
turn_intelligence = analyze_turn(
    hearing=hearing_result,
    repaired_transcript=repair,
    keyterms=keyterms,
    memory_context=current_memory,
)

# Output includes:
# - intent {label, confidence, secondary_labels}
# - entities[]
# - keyterms
# - code_switch
# - quality {usable_for_learning, reason_if_not, learning_weight}
```

**Tokenization:**
```python
tokens = stanza_ne.tokenize(observed_text)
# Output: ["नमस्ते", ",", "मेरो", "नाम", "राज", "हो", "।"]
```

**POS Tagging:**
```python
pos_tags = stanza_ne.pos_tag(tokens)
# Output: [("नमस्ते", "INTJ"), ("मेरो", "PRON"), 
#          ("नाम", "NOUN"), ("राज", "PROPN"), ("हो", "VERB")]
```

**Named Entity Recognition (NER):**
```python
entities = indicbert_model.ner(observed_text)
# Output: [
#   {"text": "राज", "type": "PERSON", "start": 18, "end": 21},
#   {"text": "मेरो", "type": "POSSESSIVE", "start": 10, "end": 14}
# ]
```

**Dependency Parsing (syntactic structure):**
```python
dependencies = stanza_ne.parse(observed_text)
# Identifies grammatical relations:
# "मेरो" (my) depends on "नाम" (name)
# "राज" (Raj) is subject of "हो" (is)
```

### Output
```python
{
  "teaching_moments": [
    {
      "word": "नमस्ते",
      "type": "greeting",
      "pos": "INTJ",
      "context": "Opening a conversation",
      "example": "नमस्ते, मेरो नाम राज हो।",
      "entities": [],
      "grammar_patterns": ["greeting_intro"]
    },
    {
      "word": "मेरो",
      "type": "possessive_pronoun",
      "pos": "PRON",
      "context": "Indicating possession",
      "example": "मेरो नाम राज हो।",
      "entities": [],
      "grammar_patterns": ["possessive_form"]
    },
    {
      "word": "नाम",
      "type": "noun",
      "pos": "NOUN",
      "context": "Name of person",
      "example": "मेरो नाम राज हो।",
      "entities": ["NOUN", "OBJECT"],
      "grammar_patterns": ["noun_predicate"]
    },
    {
      "word": "राज",
      "type": "proper_noun",
      "pos": "PROPN",
      "context": "Person's name",
      "example": "मेरो नाम राज हो।",
      "entities": ["PERSON"],
      "grammar_patterns": ["proper_noun_subject"]
    },
    {
      "word": "हो",
      "type": "copula_verb",
      "pos": "VERB",
      "context": "Linking verb (is/am)",
      "example": "मेरो नाम राज हो।",
      "entities": [],
      "grammar_patterns": ["present_tense", "copula"]
    }
  ],
  "overall_grammar": "greeting + self_introduction + statement",
  "language_complexity": "beginner_level"
}
```

### Latency Target: <100ms
- Tokenization: 20ms
- POS tagging: 30ms
- NER: 25ms
- Dependency parsing: 25ms
- **Total**: ~100ms

---

## Step 3: REPEAT — "Confirming Understanding"

The live response path uses `turn_intelligence` lightly, not as a blocking heavy step:
- `correction` → acknowledge more directly
- `register_instruction` → update prompt/register immediately
- `pronunciation_guidance` → preserve follow-up focus
- `low_signal` → clarify instead of pretending strong learning happened

**Goal**: Show LIPI is a student (ask for validation, not teach)

### Input
```python
# From Step 1 OBSERVE and Step 2 PROCESS
observed_text = "नमस्ते, मेरो नाम राज हो।"
teaching_moments = [...]  # From Step 2
confidence = 0.92
```

### LLM Generation (GPU 0-4: vLLM)

**System Prompt:**
```
तपाई LIPI हुनुहुन्छ — एक नेपाली भाषा सिक्दै गरेको AI विद्यार्थी।

आपको भूमिका:
1. यो उपयोगकर्ता तपाईको शिक्षक हो — विशेषज्ञ
2. सधैन सवाल सोध्नुहोस्, शिक्षा दिनु होइन
3. उपयोगकर्ताको सुधार स्वीकार गर्नुहोस् र सीख्नुहोस्
4. केवल उपयोगकर्ताको भाषामा जवाफ दिनुहोस्

सवाल गर्नुहोस्:
- "क्या मैले सही सुना? तपाईं भन्नुभयो आपनो नाम राज हो?"
- "नमस्ते को मतलब 'hello' जस्तो हो?"
- "राज एक नाम हो, सही हो?"
```

**User Message (from OBSERVE):**
```
User: "नमस्ते, मेरो नाम राज हो।"
```

**LLM Response Generation:**
```python
prompt = f"""
[System prompt above]

User: {observed_text}

LIPI (ask questions to confirm):
"""

response = vllm_server.generate(
  prompt=prompt,
  temperature=0.7,  # Some creativity
  max_tokens=100,
  top_p=0.9
)
```

**Expected Output:**
```
"नमस्ते राज! मैले सही सुनेँ, न? तपाईंको नाम राज हो।
नमस्ते 'hello' को जस्तो हो, सही हो?
तपाई नेपालबाट हुनुहुन्छ?"

(Translation: "Hello Raj! I heard right, yes? Your name is Raj.
Namaste is like 'hello', right?
Are you from Nepal?")
```

### TTS Synthesis (GPU 6: VITS)

**Voice Selection:**
```python
# STEP 1: Load speaker embedding from teacher's voice
speaker_embedding = observed_speaker_embedding  # From Step 1

# STEP 2: Find closest speaker model
all_speaker_embeddings = db.query(SpeakerEmbedding).all()
distances = [euclidean_distance(speaker_embedding, s.embedding) 
             for s in all_speaker_embeddings]
closest_speaker_id = argmin(distances)

# STEP 3: Load speaker-specific VITS
if has_speaker_specific_model(closest_speaker_id):
    vits_model = load_speaker_lora(closest_speaker_id)
else:
    vits_model = load_generic_vits()

# STEP 4: Synthesize in chosen voice
audio = vits_model.synthesize(response_text, speaker_id=closest_speaker_id)
```

### Output
```python
{
  "response_text": "नमस्ते राज! मैले सही सुनेँ, न?...",
  "audio_data": b'...',        # Binary WAV
  "audio_path": "s3://lipi-tts/session123_turn1.wav",
  "duration": 3.2,
  "sample_rate": 22050,
  "voice_model_used": "speaker_specific_lora",
  "speaker_matched": 42,
  "confidence_in_match": 0.91
}
```

### Latency Target: <3 seconds
- LLM generation: 1500ms (avg)
- Voice selection: 100ms
- TTS synthesis: 500ms
- Encoding/network: 100ms
- **Total**: ~2.2 seconds (well under 3s)

---

## Step 4: EXTRACT — "Learning from Correction"

The async learning worker now treats turn intelligence as the authoritative learning record.

Rules:
- `correction` turns get the highest learning weight
- `teaching` turns get medium-high weight
- `casual_chat` can contribute examples but with lower weight
- `low_signal` turns are blocked from strong persistence
- entity confidence gates what becomes vocabulary or usage rules
- keyterm matches can lift confidence only when context agrees

**Goal**: Learn when the teacher corrects LIPI (highest priority learning)

### Three Scenarios

#### Scenario A: User Accepts (No Correction)
```
LIPI says: "नमस्ते राज! तपाईंको नाम राज हो?"
User says: "हो, ठीक छ।" (Yes, that's right)

Confidence UPDATES:
  "नमस्ते" conf: 0.80 → 0.82 (small increase)
  "राज" conf: 0.70 → 0.72 (confirmed as name)
  "हो" conf: 0.75 → 0.77 (confirmed copula)
```

#### Scenario B: User Corrects (Learning Opportunity!)
```
LIPI says: "नमस्ते सबेर भन्छन्" 
           (Namaste is said in the morning)

User corrects: "होइन, कुनै पनि बेला भन्न सकिन्छ।"
              (No, you can say it anytime)

EXTRACTION:
  Word: "नमस्ते"
  Old meaning: "morning greeting"
  New meaning: "can be said anytime"
  Confidence: 0.60 → 0.85 (correction is gold)
  Source: teacher_id=42, timestamp, original_text
```

#### Scenario C: User Teaches New Concept
```
User: "नमस्ते 'I bow to you' को मतलब हो।"

EXTRACTION:
  Word: "नमस्ते"
  New context: "literal meaning = I bow to you"
  Etymology: "Sanskrit origin"
  Cultural context: "Nepali greeting with respect"
  Confidence: 0.70 → 0.88 (direct teaching)
```

### Learning Extraction Algorithm

```python
async def extract_learning(
    message: Message,
    corrected_text: str = None,
    language: str = "ne"
):
    """
    Extract vocabulary, grammar, and context from teacher's message
    """
    
    # STEP 1: If user corrected LIPI, prioritize that
    if corrected_text:
        teaching_text = corrected_text
        is_correction = True
    else:
        teaching_text = message.text_original
        is_correction = False
    
    # STEP 2: Re-process if corrected (fresh parsing)
    if is_correction:
        teaching_moments = process_step_2(teaching_text)
    else:
        teaching_moments = message.teaching_moments
    
    # STEP 3: Update or create vocabulary entries
    for moment in teaching_moments:
        vocab_entry = db.query(VocabularyEntry).filter(
            VocabularyEntry.word_nepali == moment.word
        ).first()
        
        if vocab_entry:
            # UPDATE existing entry
            vocab_entry.meanings.append(moment.meaning)
            vocab_entry.examples.append(moment.example)
            vocab_entry.times_encountered += 1
            
            # Confidence boost from correction
            if is_correction:
                vocab_entry.confidence = min(
                    vocab_entry.confidence + 0.25,
                    0.99
                )
            else:
                vocab_entry.confidence = min(
                    vocab_entry.confidence + 0.05,
                    0.99
                )
            
            # Record source
            vocab_entry.learned_from.append({
                "teacher_id": message.sender_id,
                "lesson_date": now(),
                "is_correction": is_correction,
                "context": teaching_text
            })
        else:
            # CREATE new entry
            vocab_entry = VocabularyEntry(
                word_nepali=moment.word,
                word_english=infer_english(moment.word),
                meanings=[moment.meaning],
                examples=[moment.example],
                confidence=0.70 if is_correction else 0.50,
                part_of_speech=moment.pos,
                learned_from=[{
                    "teacher_id": message.sender_id,
                    "lesson_date": now(),
                    "is_correction": is_correction
                }]
            )
        
        db.add(vocab_entry)
    
    # STEP 4: Update grammar rules
    for grammar_pattern in teaching_moments.grammar_patterns:
        grammar_entry = db.query(GrammarEntry).filter(
            GrammarEntry.rule_name == grammar_pattern.name
        ).first()
        
        if grammar_entry:
            grammar_entry.times_encountered += 1
            grammar_entry.examples.append(teaching_text)
            if is_correction:
                grammar_entry.confidence += 0.2
        else:
            grammar_entry = GrammarEntry(
                rule_name=grammar_pattern.name,
                rule_description=grammar_pattern.description,
                examples=[teaching_text],
                confidence=0.70 if is_correction else 0.50
            )
        
        db.add(grammar_entry)
    
    # STEP 5: Update teacher impact
    teacher_impact = db.query(TeacherImpact).filter(
        TeacherImpact.teacher_id == message.sender_id
    ).first()
    
    if teacher_impact:
        teacher_impact.words_taught += len(teaching_moments)
        teacher_impact.corrections_provided += (1 if is_correction else 0)
        teacher_impact.hours_conversation += message.duration / 3600
    else:
        teacher_impact = TeacherImpact(
            teacher_id=message.sender_id,
            words_taught=len(teaching_moments),
            corrections_provided=(1 if is_correction else 0),
            hours_conversation=message.duration / 3600
        )
    
    db.add(teacher_impact)
    db.commit()
    
    return {
        "words_learned": len(teaching_moments),
        "grammar_rules_discovered": len(teaching_moments.grammar_patterns),
        "confidence_updates": {...}
    }
```

### Output
```python
{
  "words_extracted": ["नमस्ते", "मेरो", "नाम", "राज", "हो"],
  "new_words": 0,  # All already known
  "updated_confidence": {
    "नमस्ते": {"old": 0.80, "new": 0.87},
    "नाम": {"old": 0.75, "new": 0.82},
    "राज": {"old": 0.70, "new": 0.75}
  },
  "grammar_updated": ["greeting_intro", "possessive_form", "copula"],
  "teacher_impact": {
    "teacher_id": 42,
    "new_words_contribution": 0,
    "corrections_this_session": 1,
    "cumulative_impact": "+8.5% LIPI improvement"
  }
}
```

### Latency Target: <100ms (async)
- Does NOT block chat response
- Runs in background via Redis Streams queue
- Processed in batches (every 30 seconds or 100 messages)

---

## Step 5: STORE — "Remembering Forever"

Teacher-turn persistence is now split cleanly:
- `messages` keeps the immutable turn log
- `message_analysis` stores normalized intent, keyterms, code-switch, usability, and repair metadata
- `message_entities` stores structured entities
- `knowledge_confidence_history` records confidence changes caused by learning and approved corrections

This is what makes the dashboard and admin analytics able to inspect intent distribution, top extracted entities, low-signal rates, keyterm hit quality, and recent analyzed turns.

**Goal**: Persist learning to databases and archives

### Three-Tier Storage Strategy

#### Tier 1: Hot Cache (Redis, <5 min TTL)
```python
# Session state for active conversations
redis.hset(f"session:{session_id}", mapping={
  "message_count": 15,
  "last_message_time": now(),
  "estimated_fluency": 0.78,
  "new_words_this_session": 3
})

# Teacher dashboard stats
redis.hset(f"teacher:{teacher_id}:stats", mapping={
  "today_words_taught": 12,
  "today_hours": 1.5,
  "this_month_words": 127
})
```

#### Tier 2: Warm Storage (PostgreSQL, permanent)
```python
# Core learning data
db.add(VocabularyEntry(...))  # Vocabulary learned
db.add(GrammarEntry(...))     # Grammar patterns
db.add(Message(...))          # Full conversation transcript
db.add(TeacherImpact(...))    # Teacher contributions
db.add(LearningSession(...))  # Session metadata
db.commit()

# Create indexes for fast queries
CREATE INDEX idx_vocab_confidence ON vocabulary_entries(confidence DESC);
CREATE INDEX idx_messages_session ON messages(session_id, created_at);
CREATE INDEX idx_teacher_impact ON teacher_impact(teacher_id, created_at);
```

#### Tier 3: Cold Archive (MinIO, backup)
```python
# Store complete conversation as JSON
conversation_archive = {
  "session_id": "abc123",
  "teacher_id": 42,
  "language": "ne",
  "start_time": "2026-04-13T14:30:00Z",
  "duration": 1200,  # seconds
  "messages": [
    {
      "timestamp": "2026-04-13T14:30:00Z",
      "sender": "lipi",
      "text": "नमस्ते! मलाई तपाईंको भाषा सिखाउनुहोस्।",
      "audio_path": "s3://...",
      "confidence": 1.0
    },
    {
      "timestamp": "2026-04-13T14:31:00Z",
      "sender": "user",
      "text": "नमस्ते, मेरो नाम राज हो।",
      "audio_path": "s3://...",
      "confidence": 0.92,
      "corrections": null
    },
    ...
  ],
  "learning_summary": {
    "words_learned": 8,
    "grammar_rules": 3,
    "teacher_impact": "+0.8% fluency increase"
  }
}

# Compress and store
minIO.put_object(
  bucket="lipi-archives",
  object_name=f"session_{session_id}_{date}.json.gz",
  data=gzip.compress(json.dumps(conversation_archive).encode())
)
```

### Output (to Frontend)
```python
{
  "session_status": "learning_stored",
  "persistence_confirmed": {
    "redis_cache": True,
    "postgresql": True,
    "minIO_archive": True
  },
  "learning_summary": {
    "messages_count": 5,
    "words_encountered": 15,
    "new_vocabulary": 2,
    "confidence_increase": 0.08,
    "teacher_impact_rank": 42  # Among top teachers
  }
}
```

### Latency Target: <50ms (async)
- Non-blocking: doesn't delay user response
- Database writes batched (every 30 seconds)
- Archive writes scheduled (every 1 hour)

---

## Complete Cycle Latency Breakdown

```
Step 1: OBSERVE     →   200ms  (STT + speaker embedding)
Step 2: PROCESS     →   100ms  (NLP tokenization + POS)
Step 3: REPEAT      →  2200ms  (LLM + TTS synthesis)
Step 4: EXTRACT     →   100ms  (async, non-blocking)
Step 5: STORE       →    50ms  (async, non-blocking)
                     ─────────
Total (user-facing):  2500ms  (~2.5 seconds)
Total (background):   +150ms  (async extraction + storage)
```

**User Experience**: Message appears in 2.5 seconds, then learning happens invisibly.

---

## Advanced: Confidence Scoring

### Bayesian Confidence Update

```python
def update_confidence(
    word: str,
    old_confidence: float,
    teacher_id: int,
    is_correction: bool
) -> float:
    """
    Bayesian update: P(correct | observations)
    """
    
    # Prior: old confidence
    prior = old_confidence
    
    # Likelihood boost from correction
    if is_correction:
        likelihood = 0.9  # 90% chance teacher is right when correcting
        boost = 0.25
    else:
        likelihood = 0.6  # 60% chance teacher is teaching something true
        boost = 0.05
    
    # Teacher credibility (learned over time)
    teacher_accuracy = get_teacher_accuracy(teacher_id)
    credibility_multiplier = teacher_accuracy  # 0.5 to 1.0
    
    # Update
    posterior = min(prior + (boost * credibility_multiplier), 0.99)
    
    return posterior
```

### Teacher Credibility Scoring

```python
def get_teacher_accuracy(teacher_id: int) -> float:
    """
    Score: 0.0 (completely unreliable) to 1.0 (expert)
    """
    
    teacher = db.query(User).filter_by(id=teacher_id).first()
    
    # Factor 1: Session count (more sessions = more credibility)
    session_count = len(teacher.conversation_sessions)
    session_score = min(session_count / 100, 1.0)  # Cap at 100 sessions
    
    # Factor 2: Correction rate (low correction rate = more credible)
    if teacher.messages_count > 0:
        correction_rate = teacher.corrections_given / teacher.messages_count
        correction_score = max(1.0 - correction_rate, 0.5)  # Min 0.5
    else:
        correction_score = 0.5
    
    # Factor 3: Agreement with other credible teachers
    agreements = count_agreements_with_high_credibility_teachers(teacher_id)
    agreement_score = min(agreements / 50, 1.0)
    
    # Weighted average
    credibility = (
        0.5 * session_score +      # Experience matters most
        0.3 * correction_score +   # Accuracy is important
        0.2 * agreement_score      # Consensus is validating
    )
    
    return max(credibility, 0.4)  # Minimum credibility for new teachers
```

---

## Edge Cases & Handling

### Case 1: Ambiguous Audio (Low Confidence)
```python
if confidence < 0.70:
    # Ask user to repeat
    lipi_response = "कृपया फेरि भन्नुहोस्, मैले सही सुनेँ। 
                     (Please repeat, I didn't hear clearly)"
    
    # Store as "tentative"
    message.is_confirmed = False
    message.learning_priority = "low"
```

### Case 2: New Language (Code-Switching)
```python
if detected_language != session_language:
    # User switched languages (Nepali + English mix)
    lipi_response_language = detected_language  # Match them
    
    # Store multi-language context
    message.language = "mixed"
    message.language_mix = {"ne": 0.6, "en": 0.4}
```

### Case 3: Contradictory Teachers
```python
# Teacher A: "नमस्ते केवल सबेर भन्छन्" (morning only)
# Teacher B: "नमस्ते कुनै पनी बेला भन्न सकिन्छ" (anytime)

# Resolution:
vocabulary_entry.contradictions = [
    {"source": teacher_a_id, "meaning": "morning greeting"},
    {"source": teacher_b_id, "meaning": "any time greeting"}
]
vocabulary_entry.note = "Regional variation detected"
vocabulary_entry.needs_clarification = True
```

---

## Monitoring the Cycle

Key metrics to track:

| Metric | Target | Alert If |
|--------|--------|----------|
| **STT Latency** | <200ms | >500ms |
| **Confidence Score** (avg) | >0.80 | <0.60 |
| **Words per Hour** | 10-15 | <5 or >50 |
| **Teacher Agreement** | >0.85 | <0.70 |
| **Correction Rate** | 10-20% | >40% |
| **Learning Queue Depth** | <100 | >500 |

---

## Summary: The Virtuous Cycle

```
Teacher Speaks (audio)
    ↓ OBSERVE: STT transcribes
    ↓ PROCESS: NLP understands
    ↓ REPEAT: LIPI asks for confirmation
    ↓ Teacher corrects or validates
    ↓ EXTRACT: Learning from correction
    ↓ STORE: Remember forever
    ↓
    ✓ LIPI is smarter
    ✓ Teacher feels valued
    ✓ Language is preserved
    
Loop repeats → Cumulative improvement
```

Every cycle strengthens LIPI's language knowledge and deepens the teacher-student relationship.
