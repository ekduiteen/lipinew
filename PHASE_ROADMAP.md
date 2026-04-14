# 16-Week MVP Roadmap: From Planning to Production

**Target**: Production-ready LIPI for 1,000+ DAU by end of Q2 2026  
**Team Size**: 4-5 engineers (backend, ML, frontend, DevOps)  
**Definition of Done**: Real teachers can have 5+ minute conversations, LIPI learns from corrections, confidence scores tracked, all 6 challenges solved

---

## Phase 0: Foundation (Weeks 1-2)

### Infrastructure & DevOps

**Week 1:**
- [ ] Evaluate Hybrid API limits (Together AI, Groq) vs 10× L40S GPU cluster requirements
- [ ] Set up single-GPU generic VM for DB/STT backend (Hybrid start)
- [ ] Set up docker registries and CI/CD pipeline
- [ ] Deploy PostgreSQL 15 (standalone instance)
- [ ] Deploy MinIO object storage (local cluster)
- [ ] Deploy Redis 7 (session cache + Streams)
- [ ] Create docker-compose.gpu.yml
- [ ] Verify all services health checks passing

**Owner**: DevOps Engineer  
**Output**: 
- Running docker-compose environment
- All services reachable and responding
- Database migrations executed
- MinIO buckets created

**Week 2:**
- [ ] Set up monitoring (Prometheus + Grafana)
- [ ] Configure logging (centralized logs)
- [ ] Set up nginx reverse proxy with SSL
- [ ] Create automated backup strategy
- [ ] Document infrastructure as code
- [ ] Set up CI/CD for automated testing
- [ ] Create deployment playbook
- [ ] Team training on infrastructure

**Owner**: DevOps Engineer  
**Output**:
- Monitoring dashboard live
- Backup automation running
- CI/CD pipeline functional
- Infrastructure documentation complete

### Database Schema

**Week 1-2:**
- [ ] Implement all 15+ PostgreSQL tables (from DATABASE_SCHEMA.md)
- [ ] Create indexes (primary, foreign key, search)
- [ ] Write migration scripts (Alembic)
- [ ] Create seed data for testing
- [ ] Test connection pooling
- [ ] Verify constraints and triggers

**Owner**: Backend Engineer  
**Output**:
- Schema fully implemented
- Migrations tested
- Sample data loaded
- Ready for application code

---

## Phase 1: Core Chat (Weeks 3-6)

### Backend Chat Endpoint

**Week 3:**
- [ ] Implement FastAPI WebSocket endpoint (`/chat/ws/{session_token}`)
- [ ] Session creation and token management
- [ ] Message persistence to database
- [ ] Connection pooling and lifecycle management
- [ ] Error handling and reconnection logic
- [ ] Unit tests for WebSocket handling

**Owner**: Backend Engineer  
**Output**:
- WebSocket endpoint fully functional
- Multiple concurrent connections working
- Sessions survive disconnects + reconnects
- Tests passing

**Week 4:**
- [ ] Integrate faster-whisper (STT) via ml-server
- [ ] STT service returns {text, confidence, language}
- [ ] Speaker embedding extraction (concurrent with STT)
- [ ] Dialect LoRA selection (basic geography-based for now)
- [ ] Error handling + fallback to generic whisper
- [ ] STT latency <200ms verified

**Owner**: ML Engineer + Backend Engineer  
**Output**:
- STT integration complete
- Latency targets met
- Speaker embeddings extracted
- Error handling robust

**Week 5:**
- [ ] Integrate external Hybrid LLM API (Groq/Together AI) as primary for MVP to conserve CapEx
- [ ] Prepare vLLM server scaffolding for future self-hosting transition
- [ ] System prompts configured (student roleplay)
- [ ] Implement LLM Safety Pre-Filter (Guardrails) to drop hateful/toxic input
- [ ] Prompt construction + context management
- [ ] Response generation <2 sec verified
- [ ] Error recovery and retry logic

**Owner**: ML Engineer  
**Output**:
- LLM fully integrated and responding
- Student roleplay working as expected
- Latency targets met (p95 <2s)
- Fallbacks tested

**Week 6:**
- [ ] Integrate facebook/mms-tts-npi (TTS)
- [ ] Text → Phonemes → Mel → Waveform pipeline
- [ ] Audio quality normalization
- [ ] WebSocket binary frame transmission
- [ ] Client-side audio playback
- [ ] TTS latency <500ms verified

**Owner**: ML Engineer + Frontend Engineer  
**Output**:
- TTS fully working end-to-end
- Audio playback in browser
- Latency targets met
- Quality acceptable (MOS ~3.2)

### Frontend Chat Interface

**Week 3-4:**
- [ ] Create `/chat` page component
- [ ] WebSocket client setup (auto-connect, reconnect)
- [ ] Message display with animations (Framer Motion)
- [ ] Audio recording via Web Audio API
- [ ] Text input and submission
- [ ] Learning stats live updates

**Owner**: Frontend Engineer  
**Output**:
- Chat page fully functional
- Beautiful UI with animations
- Recording + text input working
- Stats display live

**Week 5-6:**
- [ ] Audio playback (receive LIPI responses)
- [ ] Correction interface (user corrects LIPI)
- [ ] Mobile responsive design
- [ ] Accessibility improvements
- [ ] Performance optimization (lazy loading)
- [ ] Error states and user feedback

**Owner**: Frontend Engineer  
**Output**:
- Chat experience complete and polished
- Mobile friendly
- Production-ready UI

### Learning Cycle (Basic)

**Week 4-5:**
- [ ] Implement 5-step learning cycle (OBSERVE → PROCESS → REPEAT → EXTRACT → STORE)
- [ ] OBSERVE: Capture STT confidence, audio quality
- [ ] PROCESS: Basic NLP using stanza (POS tagging, tokenization)
- [ ] REPEAT: Generate response confirming understanding
- [ ] EXTRACT: Extract vocabulary + grammar (simple rules)
- [ ] STORE: Persist to database synchronously

**Owner**: ML Engineer + Backend Engineer  
**Output**:
- Learning cycle fully implemented
- Vocabulary entries created for each conversation
- Confidence scores tracked
- Database persists all learning

**Week 6:**
- [ ] Implement message correction flow
- [ ] Corrections stored with original context
- [ ] Confidence updates from corrections
- [ ] Vocabulary entries updated
- [ ] Teaching moments highlighted

**Owner**: Backend Engineer  
**Output**:
- Correction system working
- Confidence updates applied
- Multi-teacher learning tracked

---

## Phase 2: Advanced Learning (Weeks 7-10)

### Speaker Embedding + Dialect Clustering

**Week 7:**
- [ ] Load multilingual-e5-large (GPU 7)
- [ ] Extract speaker embeddings for every user audio
- [ ] Store embeddings in PostgreSQL
- [ ] Implement HDBSCAN clustering algorithm
- [ ] Weekly re-clustering (Sunday night)
- [ ] Assign dialect IDs based on clustering

**Owner**: ML Engineer  
**Output**:
- Speaker embeddings extracted and stored
- Dialect clusters discovered dynamically
- Re-clustering automated
- Dialect IDs assigned to users

**Week 8:**
- [ ] Implement dialect-specific whisper LoRA loading
- [ ] Switch from geography-based to k-NN clustering
- [ ] Test with multiple speakers (different accents)
- [ ] Verify WER improvement with LoRA vs generic
- [ ] Implement fallback if LoRA unavailable
- [ ] Performance impact assessment

**Owner**: ML Engineer  
**Output**:
- Dialect-specific STT working
- WER improved for recognized dialects
- Fallback chain solid
- Performance acceptable

### Async Learning Extraction

**Week 8-9:**
- [ ] Implement Redis Streams queue (learning:queue)
- [ ] Backend publishes learning tasks asynchronously
- [ ] Worker processes queue in background
- [ ] Batch database writes (every 30 sec or 100 messages)
- [ ] Decouple real-time chat from learning extraction
- [ ] Verify chat latency unaffected by learning

**Owner**: Backend Engineer  
**Output**:
- Learning extraction fully async
- Chat latency unchanged (<3s)
- Learning still happens in background
- Queue monitoring implemented

**Week 9:**
- [ ] Implement Bayesian confidence scoring
- [ ] Calculate teacher credibility scores
- [ ] Conflict detection for contradictory teachings
- [ ] Confidence updates from multiple teachers
- [ ] Visualize learning progress
- [ ] Unit tests for confidence logic

**Owner**: ML Engineer + Backend Engineer  
**Output**:
- Confidence scoring sophisticated
- Teacher credibility tracked
- Contradictions detected
- Learning visualization working

### Data Privacy (GDPR)

**Week 9-10:**
- [ ] Implement ConsentProfile table
- [ ] Create onboarding consent flow (UI)
- [ ] Granular consent controls (audio, training, credit, deletion)
- [ ] Default: minimal data collection
- [ ] Automatic data retention policies
- [ ] Implement user data export (GDPR right to portability)
- [ ] Implement user data deletion (right to be forgotten)

**Owner**: Backend Engineer + Frontend Engineer  
**Output**:
- Consent architecture complete
- Privacy controls working
- Data deletion functional
- GDPR compliance verified

### Moderation & Admin Tools

**Week 9.5:**
- [ ] Implement Moderation Queue API for flagged interactions (shadowbanning)
- [ ] Build basic admin dashboard to review quarantined vocabulary
- [ ] Apply logic for issuing warnings and banning toxic teachers

**Owner**: Backend Engineer + Frontend Engineer  
**Output**:
- Trolls cleanly isolated from the core learning pool
- Admins safely review edge cases

### Teacher Dashboard

**Week 10:**
- [ ] Create `/teacher/impact` route
- [ ] Display teacher's contribution stats
- [ ] Words taught, corrections provided, dialects
- [ ] Monthly achievements and milestones
- [ ] Public credit option (if consented)
- [ ] Legacy tracking ("You taught LIPI नमस्ते")

**Owner**: Frontend Engineer + Backend Engineer  
**Output**:
- Teacher dashboard beautiful and informative
- Stats accurate and compelling
- Teachers feel valued

---

## Phase 3: Intelligence & Training (Weeks 11-14)

### Whisper Dialect LoRA Training

**Week 11:**
- [ ] Set up training infrastructure (GPU 8-9)
- [ ] Collect 100+ utterances per discovered dialect
- [ ] Implement phoneme alignment (Montreal Forced Aligner)
- [ ] Train first dialect LoRA (Kathmandu Valley)
- [ ] Evaluate WER improvement
- [ ] Save checkpoint to MinIO

**Owner**: ML Engineer  
**Output**:
- First dialect LoRA trained and evaluated
- WER improved (target: 8% WER)
- Checkpoint saved
- Training pipeline documented

**Week 11-12:**
- [ ] Implement weekly automatic retraining
- [ ] Train LoRA for all discovered dialects
- [ ] Hot-swap LoRA models (GPU 5 loads new ones mid-week)
- [ ] Monitor WER trends
- [ ] Prune underutilized dialects

**Owner**: ML Engineer  
**Output**:
- Automatic retraining pipeline operational
- Multiple dialects supported
- WER tracking working

### VITS Voice Training (Weeks 11-14 = 6 weeks)

**Week 11-12: Data Collection**
- [ ] Download Mozilla Common Voice Nepali
- [ ] Download Vakyansh dataset
- [ ] Download FLEURS dataset
- [ ] Download OpenSLR datasets
- [ ] Export LIPI user-collected audio
- [ ] Target: 280+ hours total

**Week 12-13: Preprocessing**
- [ ] Resample all audio to 22kHz
- [ ] Normalize loudness (-23 LUFS)
- [ ] Remove silence (Silero VAD)
- [ ] Quality filtering (SNR > 20dB)
- [ ] Phoneme alignment (MFA)
- [ ] Output: Clean, aligned dataset ready for training

**Week 13-14: VITS Training**
- [ ] Load pre-trained VITS base model
- [ ] Train multi-speaker model (500k steps)
- [ ] Checkpoint every 50 epochs
- [ ] Evaluate MOS with UTMOS predictor
- [ ] Monitor loss curve and convergence
- [ ] Select best checkpoint (MOS > 4.0)

**Owner**: ML Engineer (dedicated during weeks 13-14)  
**Output**:
- Custom VITS model trained
- MOS > 4.0 achieved
- Phase 1 → Phase 2 TTS upgrade ready
- Quality gates passed

### LLM Benchmarking

**Week 11:**
- [ ] Create benchmark framework (llm_nepali_eval.py)
- [ ] Implement 5 test suites:
  - Nepali grammar (20 cases)
  - Cultural knowledge (10 cases)
  - Student roleplay (5 multi-turn)
  - Language purity (30 cases)
  - Inference speed
- [ ] Document methodology

**Owner**: ML Engineer  
**Output**:
- Benchmarking framework complete
- All test suites ready
- Scoring methodology defined

**Week 12:**
- [ ] Benchmark baseline (Llama 3.3 70B)
- [ ] Benchmark Qwen 3.5 (if available)
- [ ] Benchmark Gemma 4 (if available)
- [ ] Compare results
- [ ] Select best model for production
- [ ] Document decision

**Owner**: ML Engineer  
**Output**:
- All models benchmarked
- Recommendation documented
- Winner selected

### Integration Testing

**Week 13-14:**
- [ ] Integration tests: user → STT → LLM → TTS → response
- [ ] Load testing: 100 concurrent users
- [ ] Long-running stability test (24 hours)
- [ ] End-to-end user journey test
- [ ] Error scenario testing
- [ ] Fallback chain verification

**Owner**: QA Engineer + Backend Engineer  
**Output**:
- All integration tests passing
- System stable under load
- Ready for production

---

## Phase 4: Production & Polish (Weeks 15-16)

### Deployment

**Week 15:**
- [ ] Deploy to production cluster (docker-compose.gpu.yml)
- [ ] Database migrations executed
- [ ] All services health checks passing
- [ ] SSL/TLS certificates configured
- [ ] CDN setup for frontend assets
- [ ] Load balancing verified

**Owner**: DevOps Engineer  
**Output**:
- Production deployment successful
- All services operational
- Monitoring dashboards live

**Week 15-16:**
- [ ] User acceptance testing with 100 beta teachers
- [ ] Gather feedback on UX, learning, etc.
- [ ] Fix critical bugs
- [ ] Optimize performance (if needed)
- [ ] Security audit
- [ ] Data privacy audit

**Owner**: QA Engineer + Product Manager  
**Output**:
- Beta testing complete
- Issues documented and triaged

### Documentation & Launch

**Week 16:**
- [ ] User documentation (how to teach LIPI)
- [ ] Teacher FAQ
- [ ] Data privacy policy
- [ ] Terms of service
- [ ] Blog post: "LIPI Launched!"
- [ ] Social media announcement
- [ ] Email to beta testers

**Owner**: Product Manager + Content Team  
**Output**:
- All documentation complete
- Launch announcement ready

**Week 16:**
- [ ] Production launch
- [ ] Monitor metrics closely (error rate, latency)
- [ ] On-call support for issues
- [ ] Celebrate! 🎉

---

## Milestones & Metrics

### Week-by-Week Deliverables

| Week | Deliverable | Success Criteria |
|------|-------------|-----------------|
| 1-2 | Infrastructure ready | All services running, health checks passing |
| 3 | WebSocket chat endpoint | Messages persisted, multiple connections work |
| 4 | STT + LLM integrated | Chat latency <3s |
| 5 | TTS integrated | Audio playback working |
| 6 | Frontend + Learning cycle | End-to-end conversation works |
| 7 | Speaker embeddings | Dialect clustering discovered |
| 8 | Async learning | Chat latency unaffected |
| 9 | Privacy + dashboard | GDPR compliance, teacher dashboard live |
| 10 | Teacher impact | Teachers see their contributions |
| 11 | Whisper LoRA + data collected | Dialects supported, VITS data ready |
| 12 | LoRA training automated + LLM benchmarked | Weekly retraining, model selected |
| 13 | VITS mid-training | Loss curve good, checkpoints saving |
| 14 | VITS complete + integration tests | MOS >4.0, system stable under load |
| 15 | Production deployed | Beta testing with 100 teachers |
| 16 | Launch | Production live, monitoring active |

---

## Critical Path (Cannot Slip)

```
Week 1-2: Infrastructure (blocks everything)
   ↓
Week 3-6: Core chat (customer-facing)
   ↓
Week 11-14: VITS training (long duration, start early)
   ↓
Week 15-16: Deployment + Launch
```

**Key insight**: VITS training (6 weeks) must start in Week 11.  
If delayed, Phase 2 completion pushed to Week 17+.

---

## Team Allocation

```
4-5 Person Team:

DevOps Engineer (1 FTE):
├─ Weeks 1-2: Infrastructure setup
├─ Week 3-14: Maintenance, monitoring, backups
└─ Week 15-16: Production deployment

Backend Engineer (1.5 FTE):
├─ Week 1-2: Database schema
├─ Week 3-6: WebSocket + learning cycle
├─ Week 7-10: Async extraction, GDPR, dashboard
└─ Week 11-16: Bug fixes, optimization

ML Engineer (1.5 FTE):
├─ Week 3-6: STT, LLM, TTS integration
├─ Week 7-12: Dialect clustering, Whisper LoRA
├─ Week 11-14: VITS training (primary focus)
└─ Week 15-16: Optimization, benchmarking

Frontend Engineer (1 FTE):
├─ Week 3-6: Chat UI, recording, animations
├─ Week 7-10: Correction interface, dashboard
├─ Week 11-16: Polish, mobile, accessibility

QA Engineer (0.5 FTE):
├─ Week 6-14: Testing, bug reporting
└─ Week 15-16: UAT, launch verification
```

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| VITS MOS < 4.0 | Phase 2 TTS fails | Fallback to mms-tts, extend training |
| Whisper LoRA WER > 12% | STT accuracy poor | Use fine-tuned Wav2Vec2 (Phase 2) |
| LLM inference too slow | Chat latency >3s | Quantize to int8, use smaller model |
| PostgreSQL bottleneck | DB becomes limiting factor | Implement caching, optimize queries |
| Teacher data quality poor | Learning extraction fails | Manual review, quality gates |
| Privacy compliance incomplete | Legal risk | External audit, strict testing |
| Production outage | Users locked out | Robust monitoring, fast incident response |

---

## Success Criteria (MVP Complete)

✅ **Technical:**
- Chat latency <3s (p95)
- STT WER <12% (generic), <10% (dialect-specific)
- TTS MOS >3.8 (Phase 2)
- LLM student roleplay convincing
- 1,000+ DAU supported
- 99.5% uptime
- GDPR compliant

✅ **Functional:**
- Users can have 5+ minute conversations
- LIPI learns 20+ words per session
- Teachers can correct LIPI
- Learning confidence tracked
- Teacher contributions visible

✅ **Philosophical:**
- LIPI genuinely a student (not teaching)
- Teachers feel valued
- Language preservation happening
- Multi-language support (not Nepali-only)

---

## What's Next (Phase 5, Q3 2026)

After MVP launch:
- [ ] Reach 10,000+ DAU
- [ ] Deploy multi-region (EU + Asia)
- [ ] Fine-tune Wav2Vec2 for <5% WER
- [ ] Implement speaker cloning (XTTS)
- [ ] Add gamification (badges, leaderboards)
- [ ] Mobile app (React Native)

Timeline is ambitious but achievable with focused team.

