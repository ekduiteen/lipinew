# LIPI Documentation Index

**Last Updated**: 2026-04-25  
**Status**: Complete documentation map plus project wiki

---

## 📚 Quick Navigation

### For Getting Started
1. **[README.md](README.md)** — Start here: What LIPI is, current state, intelligence layer overview
2. **[docs/wiki/README.md](docs/wiki/README.md)** — Project wiki: connected map across product, backend, frontends, ML, data, APIs, testing, and ops
3. **[CLAUDE.md](CLAUDE.md)** — Engineering master brief: product vision, architecture, constraints, forbidden patterns
4. **[DEV_ONBOARDING.md](DEV_ONBOARDING.md)** — Complete developer guide: setup, codebase map (32 services), turn flow, patterns

### For Deployment & Operations
1. **[OPERATIONS.md](OPERATIONS.md)** — How to run LIPI: local setup, remote SSH, health checks, restart commands
2. **[HANDOVER_TO_CODEX.md](HANDOVER_TO_CODEX.md)** — Current state snapshot: what works, what's weak, next priorities
3. **[SYSTEM_STATUS_REPORT.md](SYSTEM_STATUS_REPORT.md)** — Comprehensive health check: all 5 phases, component matrix, verification checklist

### For Product & Design
1. **[LIPI_PHILOSOPHY.md](LIPI_PHILOSOPHY.md)** — Why LIPI exists: the student-teacher dynamic, what matters
2. **[UI_UX_DESIGN.md](UI_UX_DESIGN.md)** — All screens, brand identity, 4 themes, tone system, gamification (UPDATED: 6 tabs live)
3. **[STUDENT_CHARACTER_DESIGN.md](STUDENT_CHARACTER_DESIGN.md)** — LIPI's personality: persona, questions, moderation, evolution

### For Architecture & Data
1. **[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)** — All 25+ tables, ORM models, migrations (UPDATED: 6 migrations documented)
2. **[SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)** — System design: microservices, data flow, dependencies
3. **[SYSTEM_PROMPTS.md](SYSTEM_PROMPTS.md)** — Dynamic prompt assembly: register, energy, humor, phase-based questions

### For ML & Quality
1. **[STT_ARCHITECTURE.md](STT_ARCHITECTURE.md)** — faster-whisper large-v3: VAD, dialect LoRA, confidence thresholds
2. **[TTS_ARCHITECTURE.md](TTS_ARCHITECTURE.md)** — Piper voice routing: Nepali (ne_NP-google-medium), English (en_US)
3. **[LLM_SELECTION.md](LLM_SELECTION.md)** — Why Gemma 4 (UPDATED from Qwen): tradeoffs, quantization, performance
4. **[VOICE_TRAINING_PIPELINE.md](VOICE_TRAINING_PIPELINE.md)** — VITS fine-tuning, custom voice training, quality metrics
5. **[LLM_BENCHMARK_PLAN.md](LLM_BENCHMARK_PLAN.md)** — Evaluation framework: MOS, WER, latency targets

### For Features & Data Collection
1. **[5_STEP_LEARNING_CYCLE.md](5_STEP_LEARNING_CYCLE.md)** — OBSERVE → PROCESS → EXTRACT → STORE: vocabulary learning loop
2. **[GAMIFICATION_DATA_MODEL.md](GAMIFICATION_DATA_MODEL.md)** — Points, badges, leaderboards, streaks, multipliers (9 badges)
3. **[PERFORMANCE_TARGETS.md](PERFORMANCE_TARGETS.md)** — SLOs: STT <200ms, LLM first token <2s, end-to-end <3s, page load <1.5s

### For Decisions & Analysis
1. **[DECISION_CHECKLIST.md](DECISION_CHECKLIST.md)** — Design decisions: Valkey vs Redis, why Alembic, REST vs gRPC, etc.
2. **[API_COMPARISON.md](API_COMPARISON.md)** — Fallback APIs: Groq (Whisper + LLaMA), pricing, latency tradeoffs
3. **[CRITICAL_CHALLENGES.md](CRITICAL_CHALLENGES.md)** — Known issues: STT quality, voice tone, data cleanliness, multilingual struggles
4. **[STABILITY_REPORT.md](STABILITY_REPORT.md)** — Production readiness: risks, mitigations, monitoring

---

## 🚀 What Each Document Covers

| Document | Purpose | Audience | Update Frequency |
|----------|---------|----------|------------------|
| README.md | Project summary | Everyone | Per major feature |
| CLAUDE.md | Engineering north star | Engineers | Per architecture change |
| DEV_ONBOARDING.md | Developer guide | Developers | Per service added |
| OPERATIONS.md | How to run LIPI | DevOps + backend | Per deployment change |
| HANDOVER_TO_CODEX.md | Current state brief | Next engineer | Per 2-week cycle |
| SYSTEM_STATUS_REPORT.md | Health check | Leadership + DevOps | Per system change |
| LIPI_PHILOSOPHY.md | Why we exist | Product team | Per pivot |
| UI_UX_DESIGN.md | Visual + interaction | Designers + frontend | Per screen change |
| DATABASE_SCHEMA.md | Data model | Architects + backend | Per migration |
| SYSTEM_ARCHITECTURE.md | Tech design | Architects | Per major component |
| STT_ARCHITECTURE.md | Speech input | ML engineers | Per model change |
| TTS_ARCHITECTURE.md | Speech output | ML engineers | Per voice routing change |
| GAMIFICATION_DATA_MODEL.md | Points system | Product + backend | Per rule change |
| SYSTEM_PROMPTS.md | Conversation logic | Prompt engineer | Per prompt version |

---

## 📋 Documentation Checklist for Contributors

### Before committing code
- [ ] If you add a service: document in DEV_ONBOARDING.md section 2 (codebase map)
- [ ] If you add an ORM model: add table description to DATABASE_SCHEMA.md
- [ ] If you add a route/endpoint: update DEV_ONBOARDING.md section 10 (services reference)
- [ ] If you change architecture: update CLAUDE.md and SYSTEM_ARCHITECTURE.md
- [ ] If you change deployment: update OPERATIONS.md and HANDOVER_TO_CODEX.md
- [ ] If you add a feature: update PHASE_ROADMAP.md completion status
- [ ] If you change UI: update UI_UX_DESIGN.md screen map

### Before handover to next engineer
- [ ] Run SYSTEM_STATUS_REPORT.md (see SYSTEM_STATUS_REPORT.md for script)
- [ ] Update HANDOVER_TO_CODEX.md with current state + next priorities
- [ ] Ensure all references (Qwen → Gemma, OmniVoice → Piper, 4 tabs → 6 tabs) are updated

---

## 🔍 Key Searches

**Looking for...?** Use these documents:

- **"How do I authenticate?"** → DEV_ONBOARDING.md section 7b
- **"Where are the points calculated?"** → GAMIFICATION_DATA_MODEL.md + backend/services/points.py
- **"Why is STT quality weak for Newari?"** → STT_ARCHITECTURE.md + CRITICAL_CHALLENGES.md
- **"How does the WebSocket work?"** → DEV_ONBOARDING.md section 6 (architecture: How a Conversation Turn Works)
- **"Where's the learning queue?"** → DEV_ONBOARDING.md section 7c
- **"How do I deploy to remote?"** → OPERATIONS.md + HANDOVER_TO_CODEX.md
- **"What's the prompt strategy?"** → SYSTEM_PROMPTS.md + STUDENT_CHARACTER_DESIGN.md
- **"How are corrections handled?"** → DATABASE_SCHEMA.md `correction_events` table + GAMIFICATION_DATA_MODEL.md

---

## 📊 Status Summary

| Area | Status | Latest Docs |
|------|--------|-------------|
| **Backend** | ✅ Live | DEV_ONBOARDING.md (section 12: 32 services) |
| **Frontend** | ✅ Live | UI_UX_DESIGN.md (6 tabs implemented) |
| **Database** | ✅ Live | DATABASE_SCHEMA.md (25+ tables, 6 migrations) |
| **LLM** | ✅ Gemma 4 | CLAUDE.md + LLM_SELECTION.md (UPDATED) |
| **STT** | ✅ Live | STT_ARCHITECTURE.md (whisper large-v3) |
| **TTS** | ✅ Piper | TTS_ARCHITECTURE.md (UPDATED: Piper routing) |
| **Heritage** | ✅ NEW | README.md + DEV_ONBOARDING.md (section 13) |
| **Phrase Lab** | ✅ NEW | README.md + DEV_ONBOARDING.md (section 13) |
| **Deployment** | ✅ Remote | OPERATIONS.md + HANDOVER_TO_CODEX.md |
| **Tests** | ⚠️ Exist | backend/tests/ (16 test files, no CI yet) |
| **Pipeline** | 🔲 Phase 4 | PHASE_ROADMAP.md (unbuilt) |

---

## 🔄 Document Update History (2026-04-17)

**Major Updates in This Session:**
- ✅ Fixed all Qwen references → Gemma 4 (6 documents)
- ✅ Fixed all OmniVoice references → Piper (3 documents)
- ✅ Added Heritage documentation to README.md + PHASE_ROADMAP.md
- ✅ Updated DATABASE_SCHEMA.md with all 6 migrations
- ✅ Created SYSTEM_STATUS_REPORT.md (comprehensive health check)
- ✅ Updated DOCUMENTATION_INDEX.md (this file)
- ✅ Verified UI_UX_DESIGN.md already had 6 tabs documented
- ✅ Verified OPERATIONS.md already reflected current setup

**Still Accurate (No Changes Needed):**
- LIPI_PHILOSOPHY.md ✅
- STUDENT_CHARACTER_DESIGN.md ✅
- SYSTEM_PROMPTS.md ✅
- 5_STEP_LEARNING_CYCLE.md ✅
- PERFORMANCE_TARGETS.md ✅
- CRITICAL_CHALLENGES.md ✅
- DECISION_CHECKLIST.md ✅
- API_COMPARISON.md ✅ (with minor LLM updates)

---

## 📝 Notes for Next Engineer

1. **Canonical docs** — these 8 files are the source of truth:
   - CLAUDE.md, LIPI_PHILOSOPHY.md, DEV_ONBOARDING.md, DATABASE_SCHEMA.md
   - OPERATIONS.md, UI_UX_DESIGN.md, SYSTEM_PROMPTS.md, HANDOVER_TO_CODEX.md

2. **Don't create new status files** — update SYSTEM_STATUS_REPORT.md instead

3. **Keep docs in sync** — if you change code, update docs in the same PR

4. **References are correct** — all links use markdown format `[text](file.md)` for local navigation

---

**Questions?** Start with **[README.md](README.md)**, then refer to this index to find the right document for your needs.
