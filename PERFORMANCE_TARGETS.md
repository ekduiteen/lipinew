# Performance Targets & SLOs

**SLO (Service Level Objective)**: 99.5% uptime  
**SLI (Service Level Indicator)**: Measured via automated monitoring  
**Error Budget**: 43.2 minutes downtime per month

---

## Real-Time Chat Latency (Critical Path)

### Target: <3 seconds end-to-end

```
User speaks (0ms)
    │
    ├─→ Audio capture: 100ms
    │   └─ Microphone records user voice
    │
    ├─→ WebSocket transmission: 50ms
    │   └─ Send to backend
    │
    ├─→ STT (faster-whisper): 200ms
    │   ├─ Audio preprocessing: 20ms
    │   ├─ Whisper encoder: 80ms
    │   ├─ Decoder: 40ms
    │   └─ Post-processing: 10ms
    │
    ├─→ LLM Generation: 1500ms (avg, max 2000ms)
    │   ├─ Prompt construction: 50ms
    │   ├─ Token generation (50 tokens @ 30 tokens/sec): 1500ms
    │   └─ Post-processing: 10ms
    │
    ├─→ TTS (VITS): 500ms
    │   ├─ Text → Phonemes: 15ms
    │   ├─ Phoneme → Mel: 300ms
    │   ├─ Mel → Waveform: 150ms
    │   └─ WAV encoding: 20ms
    │
    ├─→ WebSocket transmission: 50ms
    │   └─ Send audio + text to client
    │
    └─→ TOTAL: ~2.45 seconds ✓
```

### Latency Budget Breakdown

| Component | Budget | Typical | p95 | p99 |
|-----------|--------|---------|-----|-----|
| **STT** | 200ms | 180ms | 250ms | 350ms |
| **LLM** | 1500ms | 1200ms | 1800ms | 2500ms |
| **TTS** | 500ms | 450ms | 600ms | 800ms |
| **Network** | 100ms | 50ms | 80ms | 150ms |
| **Total** | 3000ms | 2450ms | 3200ms | 4300ms |

**Alert Thresholds:**
- p50 latency > 2.5s → warning
- p95 latency > 3.5s → critical
- p99 latency > 5s → page on-call

---

## Throughput Targets

### Concurrent Users

```
1× L40S cluster:
├─ STT (faster-whisper): 8 concurrent instances × 200ms = 40 messages/sec
├─ LLM (vLLM, 5 GPUs): batch_size=64 × 3 sec = 20 requests/sec
└─ TTS (VITS): 4 concurrent instances × 500ms = 8 responses/sec

Limited by: LLM at 20 req/sec = 72,000 requests/hour

With 5 requests/user/hour average:
└─ Supports: ~14,400 daily active users

At 10× L40S (same model):
└─ Supports: 144,000 daily active users (very conservative)
```

### Learning Extraction Throughput

```
Backend learning queue (Redis Streams):
├─ Max batch size: 100 messages
├─ Processing time: 1-2 seconds per message
└─ Throughput: 50-100 messages/sec (async, non-blocking)

Database writes (batched):
├─ Batch size: 100 messages
├─ Write latency: 500-1000ms per batch
└─ Throughput: 100-200 vocabulary updates/sec
```

---

## Accuracy & Quality Metrics

### STT Accuracy (WER - Word Error Rate)

```
Target by Phase:

Phase 1 (Initial, using faster-whisper baseline):
├─ Nepali (generic): < 15% WER
├─ Kathmandu dialect: < 12% WER
├─ Eastern dialect: < 14% WER
└─ Terai dialect: < 13% WER

Phase 2 (After dialect LoRA training):
├─ Nepali (generic): < 10% WER
├─ Kathmandu dialect: < 8% WER
├─ Eastern dialect: < 9% WER
└─ Terai dialect: < 9% WER

Phase 3 (Fine-tuned Wav2Vec2):
├─ Nepali (generic): < 5% WER
├─ All dialects: < 6% WER
└─ Code-switching: < 8% WER

Measurement: Test on 1000-utterance gold standard
```

### TTS Quality (MOS - Mean Opinion Score)

```
1-5 scale (5 = natural human speech, 1 = robotic)

Phase 1 (facebook/mms-tts-npi):
├─ Target MOS: 3.2/5
├─ Naturalness: "Clearly synthetic, but understandable"
└─ Measurement: UTMOS neural predictor (no human raters)

Phase 2 (Custom VITS):
├─ Target MOS: 4.0+/5
├─ Naturalness: "Good quality, minor artifacts"
├─ Speaker variation: Yes (speaker-specific models)
└─ Measurement: UTMOS + human evaluation

Phase 3 (Fine-tuned FastSpeech2):
├─ Target MOS: 4.5+/5
├─ Naturalness: "High quality, natural sounding"
└─ Speaker variation: Excellent
```

### LLM Quality (Task-Specific)

```
Nepali Grammar Correctness (20 test cases):
├─ Target accuracy: > 85%
├─ Scoring: 1 point correct, 0.5 partial, 0 wrong
└─ Measured: Automated scoring + human review

Cultural Knowledge (10 questions):
├─ Target accuracy: > 80%
├─ Scoring: Factual correctness vs Nepali sources
└─ Measured: Manual verification

Student Roleplay Quality (5 conversations):
├─ Target: "Convincingly a curious student"
├─ Scoring: 1-5 scale (1=student-like, 5=teacher-like)
├─ Target score: < 1.5 average
└─ Measured: Human evaluation by teachers

Language Purity (Nepali-only, no Hindi/Sanskrit blend):
├─ Target: > 92% pure Nepali
├─ Scoring: Manual review of responses
└─ Measured: Percentage of responses without contamination
```

### Learning Metrics

```
Vocabulary Confidence (per word):
├─ New word: 0.5 starting confidence
├─ Correction by teacher: +0.25 (cap at 0.99)
├─ Confirmation by teacher: +0.05
└─ Target: Average confidence > 0.80 after 3 teachers

Teacher Impact:
├─ Average words taught per session: 10-15
├─ Average confidence increase per session: +0.08
├─ LIPI improvement per teacher: +0.5% fluency per hour
└─ Measured: Database aggregation queries
```

---

## Reliability & Error Rates

### Target Error Rates

```
HTTP Errors:
├─ 4xx (client errors): < 2% of requests
├─ 5xx (server errors): < 0.5% of requests
└─ Combined SLO: > 99.5% successful requests

STT Errors:
├─ Timeout (>2s): < 1% of requests
├─ Confidence < 0.6: < 5% of requests
└─ Unintelligible audio: < 3% of requests

LLM Errors:
├─ Generation timeout (>3s): < 0.1% of requests
├─ Empty response: < 0.01% of requests
└─ CUDA out of memory: < 0.01% of requests

TTS Errors:
├─ Synthesis timeout (>1s): < 1% of requests
├─ Audio encoding errors: < 0.1% of requests
└─ Model loading failures: 0% (health checked)
```

### Fallback Success Rates

```
STT Fallback Chain:
└─ If dialect LoRA timeout:
   └─ Use generic Whisper (success: 99%)

TTS Fallback Chain:
├─ If speaker-specific model unavailable:
│  └─ Use k-NN matched voice (success: 95%)
└─ If k-NN fails:
   └─ Use generic base VITS (success: 99%)

LLM Fallback Chain:
├─ If vLLM timeout:
│  └─ Use Ollama fallback (success: 95%)
└─ If both fail:
   └─ Return generic response (success: 100%)
```

---

## Resource Utilization Targets

### GPU Utilization

```
Ideal state (peak load):

GPU 0-4 (vLLM):
├─ Utilization: 85-95%
├─ Memory: 45-47GB / 48GB
├─ Temperature: <80°C
└─ Power: 250-280W

GPU 5 (STT):
├─ Utilization: 70-80%
├─ Memory: 15-18GB / 48GB
├─ Temperature: <75°C
└─ Power: 150-180W

GPU 6 (TTS):
├─ Utilization: 50-70%
├─ Memory: 12-15GB / 48GB
├─ Temperature: <70°C
└─ Power: 100-150W

GPU 7 (NLP):
├─ Utilization: 30-50%
├─ Memory: 8-12GB / 48GB
├─ Temperature: <65°C
└─ Power: 50-100W

GPU 8-9 (Training, off-peak):
├─ Utilization: 100% (when training)
├─ Memory: 40-48GB / 48GB (when training)
└─ Power: 280W (when training)

Alert thresholds:
├─ GPU memory > 95%: critical
├─ Temperature > 85°C: critical
├─ Power per GPU > 320W: warning
└─ Sustained idle >5min: investigate
```

### Network Bandwidth

```
Estimated per 10,000 concurrent users:

Download (to users):
├─ Audio (response): 10,000 × 64kbps = 640 Mbps
└─ Text + WebSocket overhead: 10 Mbps
└─ Total downstream: 650 Mbps

Upload (from users):
├─ Audio (user recording): 10,000 × 64kbps = 640 Mbps
└─ WebSocket messages: 10 Mbps
└─ Total upstream: 650 Mbps

Total: ~1.3 Gbps
Provisioning: 2 Gbps (1.5× headroom)

Target: <75% utilization at peak
└─ Maintain 0.5 Gbps headroom for burst
```

### Database Performance

```
PostgreSQL targets:

Queries:
├─ p50 latency: < 10ms
├─ p95 latency: < 50ms
├─ p99 latency: < 200ms

Slow queries (>100ms):
├─ Target: < 1% of queries
├─ Log and analyze: All queries >500ms

Connection pool:
├─ Max connections: 50
├─ Active connections: 20-35 (peak)
├─ Queue depth: < 5 queries

Write throughput:
├─ Target: > 1000 inserts/sec
├─ Batch size: 100 records
├─ Commit latency: < 100ms

Replication (if multi-region):
├─ Lag: < 1 second
├─ Alert if: > 5 seconds
```

---

## Monitoring & Alerting

### Alert Severity Levels

```
CRITICAL (Page on-call immediately):
├─ Service unavailable (all 3 backends down)
├─ STT completely non-functional
├─ LLM queue depth > 500
├─ Database unavailable
├─ GPU out of memory errors (>10 per hour)
└─ Error rate > 5%

WARNING (Create incident, notify team):
├─ Single backend down (2 of 3 remaining)
├─ STT latency p95 > 350ms
├─ LLM latency p95 > 2500ms
├─ TTS latency p95 > 700ms
├─ Error rate > 2%
├─ GPU temperature > 85°C
└─ Database replication lag > 5 seconds

INFO (Log and monitor):
├─ STT confidence average < 0.75
├─ LLM token generation rate < 20 tokens/sec
├─ TTS model load > 100ms
├─ Database slow queries > 1%
├─ Redis memory > 25GB
└─ Fallback chain used > 5% of requests
```

### Key Metrics to Track

```
Real-time dashboard (updated every 10 seconds):
├─ Current concurrent WebSocket connections
├─ STT latency (p50, p95, p99)
├─ LLM latency (p50, p95, p99)
├─ TTS latency (p50, p95, p99)
├─ Error rate (4xx, 5xx)
├─ GPU utilization (all 10 GPUs)
├─ GPU memory (all 10 GPUs)
├─ Database connection pool status
├─ Redis memory usage
└─ Learning queue depth

Daily summary (aggregated):
├─ Total DAU
├─ Total messages processed
├─ Average confidence by language
├─ WER by dialect
├─ MOS trend
├─ Vocabulary items learned
├─ Teacher impact rankings
└─ System health score
```

### Data Retention for Metrics

```
Prometheus:
├─ Detailed metrics: 15 days
├─ Downsampled (1hr): 1 year
├─ Alerts: All-time

CloudWatch/Datadog:
├─ Raw logs: 7 days
├─ Indexed logs: 30 days
├─ Metrics: 1 year

Database (PostgreSQL):
├─ Learning data: All-time (compliance)
├─ Message history: 1 year + archive
├─ Performance logs: 30 days
```

---

## Scalability Limits (Current Hardware)

```
10× L40S hard limits:

Max concurrent WebSocket connections:
├─ Network: 10k (bandwidth limited)
├─ Backend: 5k (connection limit)
├─ Actual: 5k concurrent
└─ Queue: 50k waiting

Max request throughput:
├─ Backend: 100 requests/sec
├─ LLM: 20 requests/sec
├─ Learning queue: 100 messages/sec
└─ Actual bottleneck: LLM at 20 req/sec

Max daily active users (realistic):
├─ With 5 req/user/hour: 14,400 DAU
├─ With 10 req/user/hour: 7,200 DAU
├─ With 20 req/user/hour: 3,600 DAU

To support 100k DAU:
├─ Need: 10× more GPU capacity (100× L40S)
├─ Or: Distribute across 10 clusters
├─ Or: More efficient models (quantization, distillation)
```

---

## Success Criteria (MVP)

✓ Chat latency < 3s (p95)  
✓ STT WER < 12% (generic) < 10% (dialect-specific)  
✓ TTS MOS > 3.5  
✓ LLM response appropriate > 90% of time  
✓ Learning extractions > 90% accurate  
✓ Error rate < 1%  
✓ Uptime > 99.5%  
✓ Support 1,000+ DAU  
✓ All 6 critical challenges solved  
✓ GDPR compliant  

---

## Optimization Roadmap

**Phase 2 (Q3 2026):**
- Implement quantization (int8) to reduce GPU memory
- Deploy knowledge distillation (smaller, faster LLM)
- Add Redis caching for frequently-used responses
- Multi-GPU inference parallelism

**Phase 3 (Q4 2026):**
- Implement speculative decoding (2× LLM speedup)
- Deploy Wav2Vec2 for 5-8% WER improvement
- Add voice cloning via XTTS fine-tuning
- Implement request batching for 3× throughput

**Phase 4 (2027):**
- Deploy on-device inference (reduce latency)
- Implement federated learning (privacy-preserving)
- Multi-node distributed inference
- Real-time streaming STT

