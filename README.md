# LIPI — Open-Source Nepali Language Learning Platform

Complete implementation + architectural design for LIPI's conversational AI platform. **Status: Phase 3 (Core chat, auth, leaderboards, points — ready for production deployment).**

**Version**: 1.0.0  
**Last Updated**: April 2026

---

## 🚀 Ready to Deploy?

The codebase is **fully functional** and ready to run on a remote server. See:

- **[DEPLOYMENT_QUICK_START.md](DEPLOYMENT_QUICK_START.md)** — 30-minute setup on Ubuntu 22.04 + 2× L40S
- **[OPERATIONS.md](OPERATIONS.md)** — Daily admin reference (logs, backups, scaling, monitoring)
- **[Makefile](Makefile)** — One-command operations: `make deploy`, `make health`, `make logs`

**Local development?** See [README_DEV.md](README_DEV.md).

---

## 📚 Architecture & Planning Documentation

Complete architectural design with implementation roadmap.

### Quick Navigation

### 🎯 Start Here
- **[LIPI_PHILOSOPHY.md](LIPI_PHILOSOPHY.md)** — Core principle: LIPI is the student, users are the teachers

### 🏗️ System Design
- **[SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)** — 10× L40S GPU allocation, 9 microservices, complete topology
- **[5_STEP_LEARNING_CYCLE.md](5_STEP_LEARNING_CYCLE.md)** — OBSERVE → PROCESS → REPEAT → EXTRACT → STORE detailed flow

### 🤖 ML Models & Services
- **[LLM_SELECTION.md](LLM_SELECTION.md)** — Comparing Qwen 3.5, Gemma 4, Llama 3.3 405B with benchmarking framework
- **[STT_ARCHITECTURE.md](STT_ARCHITECTURE.md)** — faster-whisper large-v3 with 30+ Nepali dialect LoRA adapters
- **[TTS_ARCHITECTURE.md](TTS_ARCHITECTURE.md)** — facebook/mms-tts-npi (Phase 1) → Custom VITS (Phase 2)
- **[NLP_LAYER.md](NLP_LAYER.md)** — IndicBERT, stanza, tokenization, POS tagging, NER

### 📊 Data & Learning
- **[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)** — conversation_sessions, messages, vocabulary_entries, grammar_entries, speaker_embeddings
- **[VOICE_TRAINING_PIPELINE.md](VOICE_TRAINING_PIPELINE.md)** — 6-week custom Nepali voice training (VITS multi-speaker)
- **[DIALECT_ADAPTATION.md](DIALECT_ADAPTATION.md)** — Speaker embedding k-NN clustering, dialect discovery, accent reproduction

### 🔐 Production & Operations
- **[DATA_PRIVACY.md](DATA_PRIVACY.md)** — Consent-first architecture, GDPR compliance, deletion rights, granular user controls
- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Docker Compose, GPU management, vLLM tensor parallelism, scaling
- **[PERFORMANCE_TARGETS.md](PERFORMANCE_TARGETS.md)** — Latency budgets, throughput, WER <12%, MOS >3.8

### 💡 Implementation Guides
- **[IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md)** — Phase 0-4 roadmap with dependencies
- **[CRITICAL_CHALLENGES.md](CRITICAL_CHALLENGES.md)** — 6 major implementation challenges with solutions

### 🎨 Design
- **[UI_UX_DESIGN.md](UI_UX_DESIGN.md)** — Complete screen map, brand identity, tone system, gamification, bilingual copy guidelines
- **[SYSTEM_PROMPTS.md](SYSTEM_PROMPTS.md)** — All prompt templates: hajur/tapai/timi/ta registers, dynamic assembly, correction handling, question banks
- **[GAMIFICATION_DATA_MODEL.md](GAMIFICATION_DATA_MODEL.md)** — PostgreSQL schema for points, badges, leaderboards, tone profiles, session tracking

### 📈 Roadmap
- **[PHASE_ROADMAP.md](PHASE_ROADMAP.md)** — Phase 0 (Foundation) → Phase 4 (Advanced features)

---

## Quick Facts

| Aspect | Details |
|--------|---------|
| **Hardware** | 10× NVIDIA L40S (48GB each = 480GB total VRAM) |
| **Primary Language** | Nepali (generalize to 200+ languages) |
| **Core Philosophy** | LIPI learns from users (teachers), not vice versa |
| **Learning Model** | 5-step cycle: OBSERVE → PROCESS → REPEAT → EXTRACT → STORE |
| **LLM Candidates** | Qwen 3.5 (201 languages), Gemma 4 (140 languages), Llama 3.3 405B (405B params) |
| **STT** | faster-whisper large-v3 (99 languages) + dialect-specific LoRA |
| **TTS** | facebook/mms-tts-npi (Phase 1) + Custom VITS (Phase 2) |
| **Microservices** | 9: Frontend, Backend ×3, ML, vLLM, PostgreSQL, MinIO, Redis |
| **Inference Latency** | <4s (chat), <12s (full cycle with training) |
| **Cost** | $0/month (self-hosted) vs $14k/month (API alternative) |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                   LIPI 10× L40S Production Cluster                  │
│                                                                      │
│  [Frontend: Next.js]  ←→  [Backend: FastAPI ×3 replicas]           │
│        :3001                      :8001-8003                        │
│                                                                      │
│                    ↓                                                 │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  GPU 0-4: vLLM (Qwen/Gemma/Llama)        |  Real-time chat  │  │
│  │  GPU 5:   STT (faster-whisper)           |  Fast path <4s   │  │
│  │  GPU 6:   TTS (mms-tts-npi/VITS)         |                  │  │
│  │  GPU 7:   NLP (IndicBERT, stanza)        |                  │  │
│  │  GPU 8-9: Training (VITS, Whisper LoRA)  |  Async learning  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  [PostgreSQL] [MinIO] [Redis] [nginx SSL/LB]                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

### 1. Role Reversal
- LIPI doesn't teach; it learns from user teachers
- System prompts position LIPI as curious student
- Corrections from users become primary learning signal

### 2. Dialect Intelligence
- Speaker embedding k-NN clustering (not geography-based)
- Acoustic similarity discovers natural dialect groups
- Dialect adapters trained incrementally from teacher contributions

### 3. Decoupled Learning
- Real-time chat: <4 seconds (STT → LLM → TTS)
- Learning extraction: async via Redis Streams
- Database persistence: batched writes, non-blocking

### 4. Multi-Language First
- STT: 99 languages (faster-whisper)
- LLM: 200+ languages (Qwen/Gemma)
- TTS: Custom voices per language/dialect
- Code-switching detection and response

### 5. Consent-First Data
- Granular user controls: audio archive, training use, public credit, data export, deletion
- 30-day grace period for data deletion requests
- Geographic storage compliance (not auto-exposed to training)

---

## Implementation Timeline

| Phase | Duration | Focus | Output |
|-------|----------|-------|--------|
| **Phase 0** | 2 weeks | Foundation | Docker infrastructure, ML service scaffolding |
| **Phase 1** | 4 weeks | Core chat | WebSocket, STT/TTS integration, basic learning |
| **Phase 2** | 6 weeks | Voice training | Custom VITS, dialect LoRA, teacher data collection |
| **Phase 3** | 4 weeks | Intelligence | Speaker embedding clustering, adaptive UI |
| **Phase 4** | Ongoing | Production | Monitoring, fine-tuning, user feedback loops |

**Total to MVP**: ~16 weeks (Q3 2026)

---

## Critical Implementation Challenges (Solved)

1. **STT Dialect Accuracy** — Geography-based LoRA fails; speaker embedding k-NN clustering works ✓
2. **Teacher Fatigue** — Adaptive confirmation strategy with learning dashboard ✓
3. **PostgreSQL Bottleneck** — Decouple real-time from async; Redis Streams for batching ✓
4. **Confidence Scoring** — Bayesian scoring with teacher credibility weighting ✓
5. **VITS Quality** — Tiered voice architecture: generic + speaker-specific + k-NN matching ✓
6. **Data Privacy** — Consent-first, granular controls, deletion with grace period ✓

See [CRITICAL_CHALLENGES.md](CRITICAL_CHALLENGES.md) for detailed solutions.

---

## Next Steps

### Immediate (This Week)
1. [ ] Finalize LLM benchmark framework → [LLM_SELECTION.md](LLM_SELECTION.md)
2. [ ] Review database schema → [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)
3. [ ] Approve deployment strategy → [DEPLOYMENT.md](DEPLOYMENT.md)

### Week 1-2
4. [ ] Create backend_ml microservice skeleton
5. [ ] Set up Docker Compose with GPU reservations
6. [ ] Initialize PostgreSQL schema

### Week 3-4
7. [ ] Implement WebSocket chat endpoint
8. [ ] Integrate faster-whisper and mms-tts-npi
9. [ ] Build 5-step learning cycle backend

### Week 5+
10. [ ] Start collecting teacher data
11. [ ] Train first dialect-specific Whisper LoRA
12. [ ] Launch custom VITS training pipeline

---

## How to Use This Architecture

1. **For Developers**: Start with [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) → implementation guides
2. **For Data Scientists**: Jump to [VOICE_TRAINING_PIPELINE.md](VOICE_TRAINING_PIPELINE.md) + [LLM_SELECTION.md](LLM_SELECTION.md)
3. **For DevOps**: Focus on [DEPLOYMENT.md](DEPLOYMENT.md) + [PERFORMANCE_TARGETS.md](PERFORMANCE_TARGETS.md)
4. **For Product**: Review [LIPI_PHILOSOPHY.md](LIPI_PHILOSOPHY.md) + [CRITICAL_CHALLENGES.md](CRITICAL_CHALLENGES.md)

---

## Document Status

**✅ COMPLETE (14 comprehensive documents, 22,000+ lines)**:

**Core Architecture (4 docs):**
- [x] LIPI_PHILOSOPHY.md — Core principle: LIPI as student, users as teachers
- [x] SYSTEM_ARCHITECTURE.md — 10× L40S, 9 microservices, GPU allocation
- [x] CRITICAL_CHALLENGES.md — 6 major challenges with production solutions
- [x] 5_STEP_LEARNING_CYCLE.md — Complete learning pipeline: OBSERVE→PROCESS→REPEAT→EXTRACT→STORE

**Model & Service Architecture (5 docs):**
- [x] LLM_SELECTION.md — Benchmark framework for Qwen/Gemma/Llama with benchmarking methodology
- [x] STT_ARCHITECTURE.md — faster-whisper + 30+ dialect LoRA + speaker embedding clustering
- [x] TTS_ARCHITECTURE.md — facebook/mms-tts-npi (Phase 1) + VITS (Phase 2) with full training pipeline
- [x] DATABASE_SCHEMA.md — 15+ PostgreSQL tables, complete learning tracking, GDPR compliance
- [x] VOICE_TRAINING_PIPELINE.md — 6-week VITS training process with 280+ hours of audio

**Operations & Deployment (4 docs):**
- [x] DEPLOYMENT.md — Docker Compose + Kubernetes with GPU reservations and auto-scaling
- [x] PERFORMANCE_TARGETS.md — SLOs, latency budgets, accuracy metrics, error budgets
- [x] PHASE_ROADMAP.md — 16-week MVP timeline with weekly milestones and critical path
- [x] API_COMPARISON.md — All API providers vs self-hosted, pricing, breakeven analysis, hybrid strategy

---

## Questions or Feedback?

All documents are living; update them as we learn and iterate. The philosophy is fixed, but implementation details evolve.

**Last commit**: 2026-04-13  
**Maintainers**: @athletiq-np
