# LIPI Decisions: Checklist Before Phase 0

**Status**: Ready to Execute  
**Updated**: April 14, 2026  
**Focus**: Question generation & student behavior (NOT language accuracy)

---

## Decision 1: LLM Selection ✅ SIMPLIFIED

### Decision: Test Gemma 3.5 vs Gemma 4 (2-3 weeks)

| Item | Status | Blocker | Resolution |
|------|--------|---------|-----------|
| Models to test | ✓ Decided | — | Gemma 3.5 & Gemma 4 (skip Llama 3.3) |
| Test focus | ✓ Clarified | — | Question generation, not accuracy |
| Test cases | ✓ Created | — | 40 focused tests (15+10+8+1) |
| Test data (Nepali) | ✓ Ready | — | Nepali prompts in LLM_BENCHMARK_PLAN.md |
| Hardware needed | ✓ Reduced | — | Single GPU (not 10 GPUs) |
| Timeline | ✓ 2-3 weeks | — | Realistic execution schedule |
| Benchmark plan | ✓ Complete | — | See LLM_BENCHMARK_PLAN.md |

**✓ APPROVED. Start Week 1.**

---

## Decision 2: Database Schema ✅ READY (Minor additions)

### Current Status: 16 tables designed, GDPR-compliant

| Item | Status | Blocker | Resolution |
|------|--------|---------|-----------|
| Core schema | ✓ Complete | — | All 16 tables in DATABASE_SCHEMA.md |
| pgvector extension | ⚠️ Add to setup | **HIGH** | Add to init-db.sql & Dockerfile |
| Connection pooling | ✓ Default OK | — | SQLAlchemy default: pool_size=5, max_overflow=10 |
| Data retention | ✓ Designed | — | Python script in DATABASE_SCHEMA.md, run as cron job |
| Indexing | ✓ Complete | — | All critical indexes defined |
| Partitioning (Phase 2) | ✓ Planned | — | Schema ready, implement after MVP |

**Action Items**:
- [ ] Create init-db.sql (from DATABASE_SCHEMA.md + pgvector extension)
- [ ] Add pgvector extension to PostgreSQL Docker image
- [ ] Create data retention scheduler (cron job)

**✓ READY to implement. Start Week 1.**

---

## Decision 3: Deployment ✅ READY (Missing 3 files)

### Current Status: Docker Compose + K8s designed

| Item | Status | Blocker | Resolution |
|------|--------|---------|-----------|
| docker-compose.yml | ✓ Complete | — | All services defined in DEPLOYMENT.md |
| nginx.conf | ❌ Missing | **CRITICAL** | Create load balancer config |
| init-db.sql | ❌ Missing | **CRITICAL** | Generate from DATABASE_SCHEMA.md |
| LLM provider decision | ✓ Decided | — | Will choose Gemma/Gemma after benchmarking |
| vLLM setup | ✓ Simplified | — | Single GPU, no tensor parallelism needed |
| Ollama (optional) | ✓ Keep | — | Keep as fallback in docker-compose |
| GPU allocation | ✓ Updated | — | GPU 0: vLLM (Gemma/Gemma), GPU 1-2: ML (STT/TTS), GPU 3-9: Training |
| Health checks | ✓ Complete | — | All services have health endpoints |
| SSL/TLS | ⚠️ Incomplete | **HIGH** | Document certificate generation |
| Monitoring | ✓ Partial | **MEDIUM** | Expand Prometheus.yml config |

**Action Items** (in order):
1. [ ] **Create nginx.conf** — Load balance 3× backend replicas
2. [ ] **Create init-db.sql** — PostgreSQL schema + pgvector extension
3. [ ] **Document SSL/TLS process** — Self-signed (dev), Let's Encrypt (prod)
4. [ ] Expand Prometheus.yml — Add Redis, MinIO, Postgres configs
5. [ ] Test docker-compose.yml locally with GPU

**✓ READY to implement. Start Week 1.**

---

## Decision 4: LLM Infrastructure ✅ SIMPLIFIED

### Old Plan: 5 GPUs (0-4) for vLLM tensor parallelism ❌
### New Plan: 1 GPU for vLLM, rest for training ✓

| Component | Old | New | Reason |
|-----------|-----|-----|--------|
| vLLM GPUs | 5 (tensor parallel) | 1 | Gemma/Gemma 70B fits single GPU |
| ML Server (STT/TTS) | GPU 5-7 | GPU 1-2 | Reduced needed |
| Training (VITS/LoRA) | GPU 8-9 | GPU 3-9 | More capacity for learning |
| Ollama fallback | Optional | Keep | Backup LLM option |

**Benefits**:
- ✓ Cheaper inference (1 GPU vs 5)
- ✓ More resources for training (7 GPUs vs 2)
- ✓ Simpler deployment (no tensor parallelism config)
- ✓ Faster iteration (can experiment faster)

**GPU Allocation (Final)**:
```
GPU 0: vLLM (Gemma 3.5 or Gemma 4) — 70B model
GPU 1: STT (faster-whisper with LoRA adapters)
GPU 2: TTS (facebook/mms-tts-npi → custom VITS)
GPU 3-9: Training (VITS multi-speaker, Whisper LoRA)
```

**✓ APPROVED. Update docker-compose.yml.**

---

## Critical Path to Phase 0 Launch

```
WEEK 1 (Setup)
├─ [1.1] Create nginx.conf (Day 1)
├─ [1.2] Create init-db.sql (Day 2)
├─ [1.3] Setup LLM benchmarking environment (Day 3-5)
└─ [1.4] Prepare Nepali test prompts (Day 5)

WEEK 2 (Test & Decide)
├─ [2.1] Benchmark Gemma 3.5 (40 tests)
├─ [2.2] Benchmark Gemma 4 (40 tests)
├─ [2.3] Compare scores & select winner
└─ [2.4] Update docker-compose.yml with chosen model

WEEK 3 (Deploy)
├─ [3.1] Document SSL/TLS setup
├─ [3.2] Test docker-compose locally
├─ [3.3] Verify all health checks
├─ [3.4] Set up monitoring (Prometheus/Grafana)
└─ [3.5] Ready for Phase 0 launch
```

---

## Approvals Needed

- [ ] **Product**: Approve LLM benchmarking scope (question generation focus)?
- [ ] **DevOps**: Can provision single GPU for LLM testing?
- [ ] **Data/NLP**: Can review/create Nepali test prompts?
- [ ] **Engineering**: Approve GPU reallocation (1 GPU vLLM, 7 GPUs training)?

---

## Phase 0 Blockers (Must Resolve Before Coding)

| Blocker | Owner | Timeline |
|---------|-------|----------|
| Benchmark environment ready | DevOps | Day 3 |
| Nepali test prompts reviewed | NLP | Day 5 |
| nginx.conf template created | Backend | Day 1 |
| init-db.sql generated | Backend | Day 2 |
| LLM winner decided | ML/Product | End of Week 2 |

---

## Assumptions to Validate

✅ **LLM role**: Question generator, not learner  
✅ **Question quality** > language accuracy  
✅ **Student behavior** > cultural knowledge  
✅ **Single GPU** sufficient for inference  
✅ **Remaining GPUs** available for training  

If any assumption changes, update this document.

---

## Success Criteria for Phase 0

- [ ] docker-compose.yml runs without errors
- [ ] All 9 services start successfully
- [ ] PostgreSQL initialized with schema + pgvector
- [ ] Backend connects to all services
- [ ] LLM responds to test prompts in <2s
- [ ] WebSocket endpoint ready for testing
- [ ] Monitoring dashboards display metrics
- [ ] SSL/TLS configured for HTTPS
