# LIPI System Architecture: 10× NVIDIA L40S

## Hardware Overview

### GPU Cluster Specification
```
Total: 10× NVIDIA L40S GPUs
├─ Memory per GPU: 48GB (GDDR6)
├─ Total VRAM: 480GB
├─ Total Compute: 450 TFLOPS
├─ Memory Bandwidth: 960 GB/s (per GPU)
└─ CUDA Compute Capability: 8.9 (Ada Lovelace)
```

### CPU/RAM/Storage (per host)
```
Assuming 2× hosts (5 GPUs each):
├─ CPU: 64-core EPYC 7003 (256GB RAM per host)
├─ NVMe Storage: 4TB (for model checkpoints)
├─ Network: 100Gbps (InfiniBand or Ethernet)
└─ OS: Ubuntu 22.04 + CUDA 12.1
```

---

## GPU Allocation Strategy

### Tier 1: Real-Time Chat (GPUs 0-4)
```
GPUs 0-4 (240GB): vLLM Inference Server
├─ Model: Qwen 3.5 or Gemma 4 (201+ languages)
├─ Tensor Parallelism: 5-way split (48GB per GPU)
├─ Batch Size: 64 concurrent requests
├─ Inference Latency: <2 seconds per response
├─ Throughput: 256 tokens/sec aggregate
└─ Purpose: LLM responses in user's language
```

**Deployment**: vLLM server with OpenAI-compatible API
```bash
python -m vllm.entrypoints.openai_api_server \
  --model meta-llama/Llama-3.3-70B-Instruct \
  --tensor-parallel-size 5 \
  --dtype float16 \
  --gpu-memory-utilization 0.95 \
  --port 8080
```

> [!TIP]
> **Phase 1 Hybrid API Start**: To mitigate initial CapEx risks before reaching 10,000 DAU, the FastAPI backend will be configured to route LLM requests to an external provider (e.g., Together AI or Groq) using the same OpenAI-compatible API format. This decouples the software from the hardware until user scale necessitates the 10x L40S allocation.

### Tier 2: Speech & Language Processing (GPUs 5-7)
```
GPU 5 (48GB): Speech-to-Text (STT)
├─ Model: faster-whisper large-v3
├─ Instances: 8 concurrent (6GB each, with sharing)
├─ Inference: 200ms per 60-second audio
├─ Languages: 99 languages baseline
├─ Dialect Adapters: 30+ Nepali LoRA models loaded on-demand
└─ Features: Speaker embedding extraction, language detection

GPU 6 (48GB): Text-to-Speech (TTS)
├─ Phase 1: facebook/mms-tts-npi (immediate)
├─ Phase 2: Custom VITS (multi-speaker, trained on GPU 8-9)
├─ Instances: 4 concurrent (8GB base model)
├─ Inference: 500ms per 3-second audio
├─ Voices: 1 generic + speaker-specific LoRA models
├─ Features: Speaker embedding k-NN voice selection, real-time synthesis
└─ Language Support: Nepali, English, Newari, Maithili, etc.

GPU 7 (48GB): NLP & Embeddings
├─ Model A: IndicBERT (12+ Indic languages)
│   ├─ Purpose: NER, POS tagging, tokenization
│   ├─ Memory: 2GB
│   └─ Latency: 100ms per sentence
├─ Model B: multilingual-e5-large (speaker embeddings)
│   ├─ Purpose: Dialect clustering, speaker similarity
│   ├─ Memory: 2GB
│   └─ Output: 512-dim embedding vectors
└─ Model C: stanza pipeline (Nepali)
    ├─ Purpose: Grammatical analysis, POS, dependency parsing
    ├─ Memory: CPU-based (not GPU)
    └─ Latency: 50ms per sentence
```

**Deployment**: FastAPI microservice (backend_ml)
```python
# All 3 services in single container with load balancing
# STT endpoint: POST /stt
# TTS endpoint: POST /tts
# Embeddings endpoint: POST /embed
```

### Tier 3: Training (GPUs 8-9)
```
GPU 8 (48GB): VITS Voice Training
├─ Model: VITS multi-speaker (Glow-TTS variant)
├─ Training: 300-hour corpus per voice
├─ Batch Size: 64 utterances (22kHz WAV)
├─ Training Duration: 3-4 weeks per voice
├─ Checkpoint Saving: Every 2 hours
└─ Output: Speaker-specific TTS models + LoRA

GPU 9 (48GB): Whisper Fine-Tuning (LoRA)
├─ Model: Whisper large (1.5B params) with LoRA adapters
├─ Fine-Tuning Data: 100h per dialect
├─ Training Duration: 1 week per dialect
├─ Batch Size: 128 audio samples
├─ LoRA Rank: 8 (low rank for efficiency)
├─ Learning Rate: 1e-4 (slow adaptation)
└─ Output: Dialect-specific Whisper LoRA checkpoints
```

**Deployment**: Training server (separate from inference)
- Non-blocking: doesn't interrupt real-time services
- Weekly retraining: automatic LoRA updates from accumulated teacher data
- Results: Hot-swap into GPU 5 during idle periods

---

## Microservice Architecture

### Service Topology

```
┌──────────────────────────────────────────────────────────────────┐
│                    Internet (Users)                              │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  nginx (SSL/LB)            [:80, :443]                          │
│  ├─ HTTP → HTTPS redirect                                        │
│  ├─ Load balance across 3 backend replicas                       │
│  ├─ WebSocket upgrade (for /chat/ws)                             │
│  └─ Rate limiting (1000 req/min per user)                       │
└───────────────┬──────────────┬──────────────┬────────────────────┘
                │              │              │
    ┌───────────▼──┐  ┌────────▼──┐  ┌──────▼────┐
    │  Backend #1  │  │ Backend #2 │  │ Backend #3 │
    │  [:8001]     │  │  [:8002]   │  │  [:8003]   │
    └─────┬────────┘  └────────────┘  └────────────┘
          │
          ├─────── (all 3 replicas connect to same backends)
          │
    ┌─────┴──────────────────────────┬────────────────┬──────────┐
    │                                │                │          │
    ▼                                ▼                ▼          ▼
[PostgreSQL]              [Redis Streams]         [MinIO]    [ML Server]
  :5432                      :6379               :9000         :5001
  (Sessions, Messages,    (Learning queue,    (Audio files)   (STT, TTS,
   Vocabulary, Grammar)   batching, caching)                  Embeddings,
                                                               NLP)
    │
    └─────────────────────┐
                          ▼
            [vLLM Server] [:8080]
            (LLM Inference - GPUs 0-4)
```

### Service Details

#### 1. Frontend Service
```yaml
Service: Next.js Application
Port: 3000 (development) / 3001 (production)
Replicas: 1 (static, behind CDN in production)
Framework: Next.js 14 with App Router
Technologies:
  - React 18 + TypeScript
  - Framer Motion (animations)
  - Web Audio API (microphone recording)
  - WebSocket client
Dependencies:
  - Backend: http://backend:8000 (via nginx)
  - Auth: NextAuth.js with Google OAuth
Memory: 512MB
CPU: 1 core (minimal, mostly static assets)
```

#### 2. Backend Service (FastAPI)
```yaml
Service: FastAPI Application
Port: 8001-8003 (3 replicas)
Framework: FastAPI 0.109.0
Key Endpoints:
  - POST /chat/sessions/create
  - WS /chat/ws/{session_token}
  - GET /chat/sessions/{session_token}/stats
  - GET /vocabulary (user's learned words)
  - GET /teacher-impact (contribution dashboard)
Dependencies:
  - PostgreSQL (synchronous)
  - Redis (async queues)
  - ML Server (STT, TTS, embeddings)
  - vLLM Server (LLM inference)
  - MinIO (audio storage)
Memory: 2GB per replica
CPU: 2 cores per replica
Scaling: Horizontal (add replicas with load balancer)
Health Check: /health → {status, version, dependencies}
```

#### 3. ML Server (GPU 5-7)
```yaml
Service: FastAPI + GPU Models
Port: 5001
GPU Allocation: GPUs 5, 6, 7 (48GB each)
Key Endpoints:
  - POST /stt (speech-to-text)
  - POST /tts (text-to-speech)
  - POST /embed (speaker embeddings)
  - POST /detect-language (language detection)
  - GET /models/info (loaded models status)
Models Loaded:
  - faster-whisper large-v3 (GPU 5, 6GB)
  - facebook/mms-tts-npi (GPU 6, 2GB)
  - multilingual-e5-large (GPU 7, 2GB)
  - stanza (CPU, not GPU)
  - IndicBERT (GPU 7, 2GB)
Memory: 15GB active + 33GB reserved for batch processing
Concurrency: 8 STT + 4 TTS instances
Latency Targets: STT <200ms, TTS <500ms
Health Check: /health → {cuda_available, models_ready}
```

#### 4. vLLM Server (GPUs 0-4)
```yaml
Service: vLLM OpenAI API Server
Port: 8080
GPU Allocation: GPUs 0-4 (240GB total, tensor parallel)
Model: Qwen 3.5 70B or Gemma 4 (configurable)
Deployment:
  python -m vllm.entrypoints.openai_api_server \
    --model {{SELECTED_MODEL}} \
    --tensor-parallel-size 5 \
    --dtype float16
Key Endpoints:
  - POST /v1/completions (text generation)
  - POST /v1/chat/completions (chat API)
Batch Size: 64 concurrent requests
Latency: <2 seconds per response
Throughput: 256 tokens/sec (aggregate)
Context Window: 4K (Qwen) or 8K (Gemma)
Temperature: 0.7 (creative but coherent)
Health Check: GET /v1/models → {available_models}
```

#### 5. PostgreSQL Database
```yaml
Service: PostgreSQL 15
Port: 5432
Storage: 500GB SSD (initial), scales with user base
Replication: Single instance (Phase 1), multi-master (Phase 2)
Backup: Daily snapshots to MinIO
Connection Pool: 50 connections (via pgbouncer)
Tables:
  - users, teacher_profiles
  - conversation_sessions
  - messages
  - vocabulary_entries
  - grammar_entries
  - speaker_embeddings
  - learning_stats
  - teacher_impact_logs
Indexing:
  - session_token (fast lookup)
  - teacher_id + created_at (time-series queries)
  - word (full-text search for vocabulary)
Memory: 64GB (buffer pool)
CPU: 16 cores
Scaling: Partitioning by date for messages table
```

#### 6. Redis Server
```yaml
Service: Redis 7.2 (Streams backend)
Port: 6379
Memory: 32GB
Purpose:
  - Session cache (< 5 min window)
  - Learning queue (Redis Streams)
  - Rate limiting counters
  - Teacher dashboard caching
Persistence: RDB snapshots every 6 hours + AOF
Replication: Read replicas for monitoring dashboard
Key Structures:
  - session:{token} → JSON session state (TTL: 5 min)
  - learning:queue → Stream of extraction tasks
  - teacher:impact:{user_id} → Cached contribution stats
  - rate_limit:{user_id}:{hour} → Request counter
Scaling: Cluster mode for sharding (Phase 2+)
```

#### 7. MinIO Object Storage
```yaml
Service: MinIO S3-Compatible
Port: 9000 (API), 9001 (Console)
Storage: 2TB initial (expandable)
Buckets:
  - lipi-audio: Raw WAV files from users
  - lipi-tts: Synthesized speech files
  - lipi-archives: Full conversation archives (compressed)
Replication: Local + cloud backup (AWS S3, GCS, or Backblaze)
Retention:
  - Raw audio: 90 days (delete after learning extracted)
  - TTS output: 7 days (delete after played)
  - Archives: Forever (encrypted, compliance backup)
Lifecycle Policies:
  - Transition old audio to cold storage
  - Delete temporary files after expiry
Encryption: At-rest (server-side) + in-transit (TLS)
```

#### 8. Training Server (GPUs 8-9)
```yaml
Service: Training Worker (Jupyter or standalone)
Port: 5002 (Jupyter) / none (batch)
GPU Allocation: GPUs 8, 9 (96GB for training)
Purpose:
  - VITS fine-tuning (GPU 8)
  - Whisper LoRA adaptation (GPU 9)
Schedule:
  - Weekly batch (Sunday night)
  - Triggered after collecting 100+ new utterances per dialect
Input:
  - Audio from PostgreSQL + MinIO
  - Speaker metadata from speaker_embeddings table
Output:
  - .pth checkpoint files (saved to MinIO)
  - LoRA weights (hot-swappable on GPU 5/6)
  - Evaluation metrics (WER, MOS stored in PostgreSQL)
Non-blocking: Doesn't interrupt real-time services
```

#### 9. Monitoring & Observability
```yaml
Service: Optional (Prometheus + Grafana)
Port: 9090 (Prometheus), 3000 (Grafana)
Metrics Collected:
  - GPU utilization, memory, temperature (nvidia-ml-tools)
  - Request latency (p50, p95, p99)
  - Model inference latency per service
  - Database query latency and slow logs
  - Cache hit rates (Redis)
  - Queue depth (learning extraction backlog)
Alerts:
  - GPU temperature > 80°C
  - OOM risk (VRAM usage > 95%)
  - STT latency > 500ms (dialect loading too slow)
  - LLM queue depth > 100 (capacity issue)
Retention: 30 days metrics
```

---

## Service Communication

### Synchronous (HTTP/gRPC)
```
Frontend → Backend (REST API)
Backend → ML Server (HTTP POST)
Backend → vLLM Server (HTTP POST, OpenAI API format)
Backend → PostgreSQL (psycopg2 driver)
Backend → MinIO (boto3 client)
```

### Asynchronous (Redis Streams)
```
Backend writes to Redis Streams: learning:queue
┌─────────────────────────────────────────┐
│  Message: {message_id, user_id, text,  │
│            audio_path, language}        │
└──────────┬──────────────────────────────┘
           │
           ▼ (batched every 30 seconds or 100 messages)
┌──────────────────────────────────────┐
│  Learning Extractor (async worker)   │
│  ├─ Run NLP on batch                 │
│  ├─ Extract vocabulary + grammar     │
│  └─ Bulk insert to PostgreSQL        │
└──────────────────────────────────────┘
```

---

## Real-Time Chat Flow (Latency Budget)

```
User presses record → Microphone capture (100ms)
                     ↓
                     Send audio to backend (WebSocket, 50ms)
                     ↓
STT (Speech-to-Text) → faster-whisper on GPU 5 (200ms)
                     ↓
LLM Generation       → vLLM on GPU 0-4 (1500ms avg, max 3s)
                     ↓
TTS (Text-to-Speech) → VITS on GPU 6 (500ms)
                     ↓
Send audio + transcript → Backend to client (50ms)
                     ↓
Total end-to-end latency: ~2.4 seconds
(Acceptable for conversational AI)

Async learning extraction (happens in background):
- NLP processing: 100ms
- Database insertion: 50ms
- Does NOT block chat
```

---

## Scaling Strategy

### Phase 1: Single Cluster (Current Architecture)
- 10× L40S in one location
- Suitable for: 1,000-10,000 daily active users
- Bottleneck: PostgreSQL write throughput

### Phase 2: Multi-Region (Q4 2026)
```
Region 1 (Asia):  5× L40S (primary)
Region 2 (EU):    5× L40S (read replicas)
├─ Database replication (PostgreSQL streaming)
├─ MinIO federation (cross-region sync)
└─ CDN for static assets (Cloudflare)
```

### Phase 3: Kubernetes (2027)
```
- Horizontally scale backend replicas (10→50)
- Auto-scale GPU services based on queue depth
- Multi-tenant isolation (per-user namespace)
- Zero-downtime deployments
```

---

## Cost Analysis (Hybrid MVP vs Fully Self-Hosted)

| Component | MVP Hybrid API (Phase 1) | Fully Self-Hosted (Phase 2+) |
|-----------|------------------------|---------------------------|
| **Hardware** (L40S Cluster) | $0 (Cloud GPUs on-demand for training) | $8,000/mo (amortized/leased) |
| **Electricity/Network** | $100/mo | $2,500/mo |
| **Personnel** | $15,000/mo | $15,000/mo |
| **STT API** | $0 (Self-hosted Whisper on 1x shared GPU) | $0 (Self-hosted on L40S) |
| **TTS API (Fallback)** | $200/mo (ElevenLabs tier) | $0 (Custom VITS) |
| **LLM Inference API** | $500/mo (Together AI/Groq pay-as-you-go) | $0 (Self-hosted Qwen/Gemma) |
| **Total Estimated (1k DAU)** | **$15,800/month** | **$25,500/month** |

**Key insight**: The Hybrid API approach explicitly derisks the MVP by allowing the project to function at <1,000 DAU without committing to $10,000+/mo in fixed infrastructure costs. Fully self-hosted breaks even at ~10,000 DAU, at which point the 10x L40S cluster should be procured.

---

## Resilience & Failover

### Single-Point Failures
```
GPU Failure (GPU 5):
  - STT requests fail
  - But other GPUs (0-4, 6-7) continue
  - User is notified: "Audio temporarily unavailable"
  - LoRA adapters from backup GPU 6 until repaired

Backend Service Down (Backend #1):
  - nginx routes to Backend #2 or #3
  - Active sessions migrate to new backend via Redis
  - Zero downtime for other users

PostgreSQL Failure:
  - All writes blocked (not ideal)
  - Phase 2: Deploy read replica, promote to primary
  - Current mitigation: Hourly backups to MinIO
```

### Circuit Breakers
```python
# If STT latency > 1s, queue requests
# If LLM queue depth > 100, return "LIPI is thinking"
# If PostgreSQL is offline, cache to Redis temporarily
```

---

## Network & Connectivity

### Bandwidth Requirements
```
Estimated per 1000 concurrent users:
├─ Audio upload: 1000 × 64kbps = 64 Mbps
├─ Audio download: 1000 × 64kbps = 64 Mbps
├─ WebSocket chat: 1000 × 10kbps = 10 Mbps
├─ Model weights (initial): 50 GB (one-time)
└─ Total sustained: ~140 Mbps

Provisioning: 1 Gbps uplink (future-proof to 100k users)
Redundancy: Dual ISPs with automatic failover
```

---

## Security Hardening

### Network Layer
```
- TLS 1.3 for all external communication
- Mutual TLS between services (internal)
- VPC isolation (no internet exposure except via nginx)
- DDoS mitigation (Cloudflare or similar)
```

### Application Layer
```
- JWT auth on all API endpoints
- WebSocket validation (CSRF tokens)
- SQL injection prevention (SQLAlchemy ORM)
- XSS protection (React escaping)
- Rate limiting (1000 req/min per user)
```

### Data Layer
```
- Encryption at rest (MinIO)
- Encryption in transit (TLS)
- Column-level encryption for sensitive fields (PostgreSQL pgcrypto)
- Audit logging (all access to PII)
```

---

## Summary: Critical Dependencies

**For Real-Time Chat to Work:**
1. ✓ Frontend (Next.js) — low resource requirements
2. ✓ Backend (FastAPI) — 3 replicas for HA
3. ✓ ML Server (STT, TTS) — critical path (200+500ms)
4. ✓ vLLM Server (LLM) — critical path (1500ms)
5. ✓ PostgreSQL — persistent sessions (allows reconnect)
6. ✓ Redis — session caching (fast failover)

**For Learning to Work (Async):**
- MinIO (audio storage)
- Redis Streams (learning queue)
- PostgreSQL (final persistence)

**Graceful Degradation:**
- STT down → text input only
- TTS down → text output only
- LLM down → fallback to generic response
- PostgreSQL down → sessions cached in Redis (temporary)

