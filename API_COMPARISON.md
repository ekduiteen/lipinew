# API Comparison: Costs, Pricing, and Trade-offs

**Decision Framework**: Should LIPI use APIs or self-hosted models?  
**Analysis Based On**: 1K, 10K, 100K DAU scenarios with realistic usage patterns

---

## Speech-to-Text (STT) Services

### Service Comparison Matrix

| Provider | Model | Cost | Accuracy | Latency | Languages | Dialects |
|----------|-------|------|----------|---------|-----------|----------|
| **OpenAI Whisper** | Whisper API | $0.006/min | 10-15% WER | 1-3s | 99 | Generic |
| **Google Cloud Speech-to-Text** | Advanced | $0.024/min | 10-12% WER | 1-2s | 125+ | Regional |
| **AWS Transcribe** | Standard | $0.0001/sec | 12-15% WER | 2-5s | 100+ | Regional |
| **Azure Speech Services** | Standard | $1/hour audio | 10-14% WER | 2-3s | 110+ | Regional |
| **AssemblyAI** | Conformer | $0.00289/min | 9-11% WER | Real-time | 99 | Limited |
| **Deepgram** | Nova-2 | $0.0043/min | 9-12% WER | Real-time | 40+ | Limited |
| **Self-Hosted faster-whisper** | Whisper large-v3 | $0 (GPU cost) | 8-12% WER | 200ms | 99 | Custom LoRA |

### STT Pricing Breakdown

#### OpenAI Whisper API

```
Cost: $0.006 per minute of audio

Usage by DAU:
─────────────────────────────────────
1,000 DAU:
├─ Avg. 5 requests/user/day = 5,000 requests/day
├─ Avg. 60 sec/request = 300,000 minutes/day
├─ Cost: 300,000 min × $0.006 = $1,800/day
├─ Monthly: $54,000
└─ Per user: $54/month

10,000 DAU:
├─ 50,000 requests/day = 3,000,000 minutes/day
├─ Cost: 3,000,000 × $0.006 = $18,000/day
├─ Monthly: $540,000
└─ Per user: $54/month

100,000 DAU:
├─ 500,000 requests/day = 30,000,000 minutes/day
├─ Cost: 30,000,000 × $0.006 = $180,000/day
├─ Monthly: $5,400,000
└─ Per user: $54/month
```

#### Google Cloud Speech-to-Text

```
Cost: $0.024 per minute (first 60 min free/month)

Usage:
─────────────────────────────────────
1,000 DAU:
├─ 300,000 minutes/day = 9,000,000 minutes/month
├─ Cost: 9,000,000 × $0.024 = $216,000/month
└─ Per user: $216/month

10,000 DAU:
├─ 90,000,000 minutes/month
├─ Cost: 90,000,000 × $0.024 = $2,160,000/month
└─ Per user: $216/month

100,000 DAU:
├─ 900,000,000 minutes/month
├─ Cost: 900,000,000 × $0.024 = $21,600,000/month
└─ Per user: $216/month
```

#### AWS Transcribe

```
Cost: $0.0001 per second
(Same as $0.006/minute, but broken down by seconds)

Usage:
─────────────────────────────────────
1,000 DAU:
├─ 300,000 minutes/day = 18,000,000 seconds/day
├─ Cost: 18,000,000 × $0.0001 = $1,800/day
├─ Monthly: $54,000
└─ Per user: $54/month
```

#### Deepgram (Best Value for STT)

```
Cost: $0.0043 per minute (cheaper than OpenAI)

Usage:
─────────────────────────────────────
1,000 DAU:
├─ 300,000 min/day × $0.0043 = $1,290/day
├─ Monthly: $38,700
└─ Per user: $39/month

10,000 DAU:
├─ 3,000,000 min/day × $0.0043 = $12,900/day
├─ Monthly: $387,000
└─ Per user: $39/month
```

#### Self-Hosted (GPU Cost)

```
Setup: 1× L40S GPU dedicated to STT

Hardware:
├─ GPU: L40S 48GB = $5,000/month (amortized)
├─ Power: ~100W = $100/month
├─ Depreciation: $500/month
└─ Total: $5,600/month

Capacity:
├─ Supports 40 req/sec = 3,456,000 req/day
├─ Can handle 144,000 DAU easily

Cost per DAU:
├─ 1,000 DAU: $5,600/month = $5.60/user/month
├─ 10,000 DAU: $5,600/month = $0.56/user/month
├─ 100,000 DAU: (need 2 GPUs) $11,200/month = $0.11/user/month
```

---

## Text-to-Speech (TTS) Services

### Service Comparison Matrix

| Provider | Model | Cost | Quality (MOS) | Voices | Languages | Latency |
|----------|-------|------|---------------|--------|-----------|---------|
| **ElevenLabs** | TTS v2 | $0.30/1K chars | 4.2/5 | 500+ | 32 | 500ms |
| **Google Cloud TTS** | Neural | $16/1M chars | 4.0/5 | 100+ | 50+ | 1-2s |
| **AWS Polly** | Neural | $16/1M chars | 3.8/5 | 400+ | 40+ | 1-2s |
| **Azure Speech Services** | Neural | $16/1M chars | 3.9/5 | 200+ | 45+ | 1-2s |
| **OpenAI TTS** | TTS-1 | $15/1M tokens | 3.5/5 | 6 voices | English only | 500ms |
| **Voicery** | Custom | $20/1M chars | 4.1/5 | Custom | Multiple | 2-3s |
| **Self-Hosted facebook/mms-tts** | MMS | $0 (GPU) | 3.2/5 | 1 | 1000+ | 500ms |
| **Self-Hosted VITS** | Custom VITS | $0 (GPU) | 4.0/5 | Custom | Custom | 500ms |

### TTS Pricing Breakdown

#### ElevenLabs (Most Popular)

```
Cost: $0.30 per 1,000 characters
Free tier: 10,000 chars/month

Average response length: 200 characters (LIPI response)

Usage by DAU:
─────────────────────────────────────
1,000 DAU:
├─ 5 requests/user/day = 5,000 requests/day
├─ 200 chars/response = 1,000,000 chars/day
├─ Cost: 1,000,000 × $0.0003 = $300/day
├─ Monthly: $9,000
└─ Per user: $9/month

10,000 DAU:
├─ 50,000 requests/day = 10,000,000 chars/day
├─ Cost: 10,000,000 × $0.0003 = $3,000/day
├─ Monthly: $90,000
└─ Per user: $9/month

100,000 DAU:
├─ 500,000 requests/day = 100,000,000 chars/day
├─ Cost: 100,000,000 × $0.0003 = $30,000/day
├─ Monthly: $900,000
└─ Per user: $9/month

Tier Pricing (volume discounts):
├─ Starter: $99/month = 330K chars = covers ~30 DAU
├─ Pro: $499/month = 3.3M chars = covers ~330 DAU
├─ Business: Contact sales = unlimited
```

#### Google Cloud TTS / AWS Polly / Azure (Premium Quality)

```
Cost: $16 per 1,000,000 characters

Usage:
─────────────────────────────────────
1,000 DAU:
├─ 1,000,000 chars/day = 30,000,000 chars/month
├─ Cost: 30,000,000 / 1,000,000 × $16 = $480/month
└─ Per user: $0.48/month

10,000 DAU:
├─ 10,000,000 chars/day = 300,000,000 chars/month
├─ Cost: 300,000,000 / 1,000,000 × $16 = $4,800/month
└─ Per user: $0.48/month

100,000 DAU:
├─ 100,000,000 chars/day = 3,000,000,000 chars/month
├─ Cost: 3,000,000,000 / 1,000,000 × $16 = $48,000/month
└─ Per user: $0.48/month
```

#### Self-Hosted VITS

```
Setup: 1× L40S GPU dedicated to TTS

Hardware:
├─ GPU: L40S 48GB = $5,000/month (amortized)
├─ Power: ~50W = $50/month
└─ Total: $5,050/month

Capacity:
├─ 8 concurrent instances × 500ms = 16 responses/sec
├─ 1,382,400 responses/day
├─ Can handle 276,000 DAU easily

Cost per DAU:
├─ 1,000 DAU: $5,050/month = $5.05/user/month
├─ 10,000 DAU: $5,050/month = $0.505/user/month
├─ 100,000 DAU: (need 2 GPUs) $10,100/month = $0.101/user/month
```

---

## Large Language Model (LLM) Services

### Service Comparison Matrix

| Provider | Model | Cost | Context | Latency | Quality | Nepali |
|----------|-------|------|---------|---------|---------|--------|
| **OpenAI GPT-4o** | GPT-4o | $15/1M input | 128K | 1-2s | Excellent | Good |
| **OpenAI GPT-4 Turbo** | GPT-4 Turbo | $10/1M input | 128K | 2-3s | Excellent | Good |
| **Anthropic Claude 3** | Opus | $15/1M input | 200K | 2-3s | Excellent | Excellent |
| **Google Gemini** | 1.5 Pro | $7.50/1M input | 1M | 2-3s | Good | Good |
| **AWS Bedrock Claude** | Claude 3 | $15/1M input | 200K | 2-3s | Excellent | Excellent |
| **Together AI** | Llama 2 | $0.50/1M tokens | 4K | 1-2s | Good | Moderate |
| **Groq** | Mixtral | $0.27/1M tokens | 32K | <500ms | Good | Moderate |
| **Self-Hosted vLLM** | Llama/Gemma | $0 (GPU) | 4-8K | 1-2s | Good | Good |

### LLM Pricing Breakdown

#### OpenAI GPT-4o (Most Popular)

```
Cost: $15 per 1M input tokens, $60 per 1M output tokens

Assumptions:
├─ Avg. prompt: 200 input tokens
├─ Avg. response: 100 output tokens
├─ Ratio: 2:1 input to output

Cost per request:
├─ Input: 200 tokens × $0.000015 = $0.003
├─ Output: 100 tokens × $0.000060 = $0.006
└─ Total: $0.009 per request

Usage by DAU:
─────────────────────────────────────
1,000 DAU:
├─ 5 requests/user/day = 5,000 requests/day
├─ Cost: 5,000 × $0.009 = $45/day
├─ Monthly: $1,350
└─ Per user: $1.35/month

10,000 DAU:
├─ 50,000 requests/day
├─ Cost: 50,000 × $0.009 = $450/day
├─ Monthly: $13,500
└─ Per user: $1.35/month

100,000 DAU:
├─ 500,000 requests/day
├─ Cost: 500,000 × $0.009 = $4,500/day
├─ Monthly: $135,000
└─ Per user: $1.35/month
```

#### Anthropic Claude 3 (Best for Nepali)

```
Cost: $15 per 1M input tokens, $75 per 1M output tokens

Cost per request:
├─ Input: 200 × $0.000015 = $0.003
├─ Output: 100 × $0.000075 = $0.0075
└─ Total: $0.0105 per request

Usage:
─────────────────────────────────────
1,000 DAU: 5,000 × $0.0105 = $52.50/day = $1,575/month ($1.58/user)
10,000 DAU: $15,750/month ($1.58/user)
100,000 DAU: $157,500/month ($1.58/user)
```

#### Groq (Fastest + Cheapest)

```
Cost: $0.27 per 1M tokens (input + output combined!)

Cost per request:
├─ 300 total tokens × $0.00000027 = $0.000081
└─ Total: ~$0.0001 per request

Usage:
─────────────────────────────────────
1,000 DAU: 5,000 × $0.0001 = $0.50/day = $15/month ($0.015/user)
10,000 DAU: $150/month ($0.015/user)
100,000 DAU: $1,500/month ($0.015/user)

Limitation: Mixtral not as good as Claude for Nepali
```

#### Self-Hosted vLLM

```
Setup: 5× L40S GPUs for Llama 3.3 70B

Hardware:
├─ 5× L40S: $25,000/month (amortized)
├─ Power: ~250W = $250/month
└─ Total: $25,250/month

Capacity:
├─ 20 requests/sec = 1,728,000 requests/day
├─ Can handle 346,000 DAU

Cost per DAU:
├─ 1,000 DAU: $25,250/month = $25.25/user/month
├─ 10,000 DAU: $25,250/month = $2.53/user/month
├─ 100,000 DAU: (need 5× more) = $126,250/month = $1.26/user/month

Note: Much better with quantization (int8) = uses 2× fewer GPUs
```

---

## Total Cost Comparison

### Scenario: 1,000 DAU, 5 requests/user/day

```
API Stack (All cloud services):
───────────────────────────────────────
STT (Deepgram):        $38,700/month
TTS (ElevenLabs):       $9,000/month
LLM (Groq):               $15/month
───────────────────────────────────────
TOTAL API:             $47,715/month ($47.72/user)

Self-Hosted Stack:
───────────────────────────────────────
STT GPU:                $5,600/month
TTS GPU:                $5,050/month
LLM (5 GPUs):          $25,250/month
NLP GPU:                $5,000/month
───────────────────────────────────────
TOTAL SELF-HOSTED:     $40,900/month ($40.90/user)

Infrastructure costs (not included):
├─ PostgreSQL: $500/month
├─ MinIO: $300/month
├─ Redis: $200/month
├─ Network: $200/month
├─ DevOps personnel: $10,000/month
└─ Sub-total: $11,200/month

TOTAL with infrastructure:
├─ API: $47,715 + $11,200 = $58,915/month ($58.92/user)
└─ Self-Hosted: $40,900 + $11,200 = $52,100/month ($52.10/user)

**Winner at 1,000 DAU: Self-Hosted (CHEAPER by $6,815/month)**
```

### Scenario: 10,000 DAU, 5 requests/user/day

```
API Stack:
───────────────────────────────────────
STT (Deepgram):       $387,000/month
TTS (ElevenLabs):      $90,000/month
LLM (Groq):              $150/month
───────────────────────────────────────
TOTAL API:            $477,150/month ($47.72/user)

Self-Hosted Stack:
───────────────────────────────────────
STT GPU:                $5,600/month (same GPU)
TTS GPU:                $5,050/month (same GPU)
LLM (5 GPUs):          $25,250/month (same cluster)
NLP GPU:                $5,000/month (same GPU)
───────────────────────────────────────
TOTAL SELF-HOSTED:     $40,900/month ($4.09/user)

Infrastructure: ~$11,200/month

TOTAL with infrastructure:
├─ API: $477,150 + $11,200 = $488,350/month ($48.84/user)
└─ Self-Hosted: $40,900 + $11,200 = $52,100/month ($5.21/user)

**Winner at 10,000 DAU: Self-Hosted (CHEAPER by $436,250/month = $5.23M/year!)**
```

### Scenario: 100,000 DAU, 5 requests/user/day

```
API Stack:
───────────────────────────────────────
STT (Deepgram):     $3,870,000/month
TTS (ElevenLabs):     $900,000/month
LLM (Groq):            $1,500/month
───────────────────────────────────────
TOTAL API:          $4,771,500/month ($47.72/user)

Self-Hosted Stack (need 10× more GPU):
───────────────────────────────────────
STT (2 GPUs):          $11,200/month
TTS (2 GPUs):          $10,100/month
LLM (10 GPUs):         $50,500/month
NLP (2 GPUs):          $10,100/month
───────────────────────────────────────
TOTAL SELF-HOSTED:    $81,900/month ($0.82/user)

Infrastructure: ~$25,000/month (more people, better SLO)

TOTAL with infrastructure:
├─ API: $4,771,500 + $25,000 = $4,796,500/month ($47.97/user)
└─ Self-Hosted: $81,900 + $25,000 = $106,900/month ($1.07/user)

**Winner at 100,000 DAU: Self-Hosted (CHEAPER by $4,689,600/month = $56M/year!)**
```

---

## Breakeven Analysis

### At What DAU Does Self-Hosted Become Cheaper?

```
Setup assumptions:
├─ API cost: ~$48/user/month (relatively stable)
├─ Self-Hosted fixed cost: $40,900/month (up to 100k DAU)
└─ Infrastructure overhead: $11,200/month

Equation:
(DAU × $48) = $40,900 + $11,200
DAU × $48 = $52,100
DAU = $52,100 / $48 = 1,085 DAU

Breakeven: ~1,100 DAU

Below 1,100 DAU: APIs are cheaper (lower initial cost)
Above 1,100 DAU: Self-hosted is cheaper (fixed costs amortized)
```

---

## Quality Comparison

### STT Accuracy (WER - Word Error Rate)

```
Nepali-Specific Accuracy:

APIs:
├─ OpenAI Whisper: 10-15% WER (generic Nepali)
├─ Google Speech-to-Text: 10-12% WER (with regional model)
├─ Deepgram: 9-12% WER (multilingual)
└─ AWS Transcribe: 12-15% WER (generic)

Self-Hosted:
├─ faster-whisper baseline: 8-12% WER
├─ + Dialect LoRA (Kathmandu): 7-9% WER
├─ + Fine-tuned Wav2Vec2: 5-8% WER
└─ Winner for quality: Self-Hosted

Result: Self-hosted BETTER quality + CHEAPER
```

### TTS Quality (MOS)

```
Mean Opinion Score (1=bad, 5=excellent):

APIs:
├─ ElevenLabs: 4.2/5 (best API)
├─ Google Cloud TTS: 4.0/5
├─ AWS Polly: 3.8/5
└─ Azure TTS: 3.9/5

Self-Hosted:
├─ facebook/mms-tts-npi: 3.2/5 (Phase 1)
├─ Custom VITS (trained): 4.0+/5 (Phase 2)
└─ Fine-tuned FastSpeech2: 4.5+/5 (Phase 3)

Recommendation:
├─ Phase 1: Use facebook/mms-tts OR ElevenLabs (similar quality)
├─ Phase 2: Custom VITS = ElevenLabs quality, $0 cost
└─ Phase 3: Fine-tuned = BETTER than ElevenLabs
```

### LLM Quality (Nepali)

```
Grammar Accuracy + Cultural Knowledge:

APIs:
├─ Anthropic Claude 3 Opus: 92/100 (best for Nepali)
├─ OpenAI GPT-4o: 89/100
├─ Google Gemini: 85/100
└─ Groq Mixtral: 78/100 (cheaper but less capable)

Self-Hosted:
├─ Llama 3.3 70B: 85/100
├─ Gemma 3.5: 90/100 (if available)
└─ Gemma 4: 87/100 (if available)

Recommendation:
├─ For best Nepali quality: Claude 3 (API) or Gemma 3.5 (self-hosted)
├─ For best value: Gemma 3.5 self-hosted
└─ Trade-off: API = simpler, Self-hosted = cheaper
```

---

## Hybrid Approach: Best of Both Worlds

### Recommended Strategy by Phase

```
Phase 1 (MVP, <1,000 DAU):
├─ STT: Deepgram API ($0.0043/min)
├─ TTS: ElevenLabs API ($0.30/1K chars)
├─ LLM: Groq API ($0.27/1M tokens)
├─ Total: ~$50k/month for 1,000 DAU
│
├─ Rationale:
│  ├─ No GPU investment needed upfront
│  ├─ Faster time to market
│  ├─ Can validate user demand
│  └─ Simple infrastructure (just backend + frontend)
│
└─ Expected revenue needed: ~$100-150k/month to sustain
```

```
Phase 2 (Growth, 1,000-10,000 DAU):
├─ STT: Self-hosted faster-whisper
├─ TTS: Custom VITS (trained during Phase 1-2)
├─ LLM: Start with API (Claude), add self-hosted Gemma as fallback
├─ Cost: $50-100k/month
│
├─ Rationale:
│  ├─ STT & TTS API costs become prohibitive
│  ├─ Self-hosted ROI positive at 1,100 DAU
│  ├─ LLM still beneficial as API (quality + simplicity)
│  └─ Total cost per user: $5-10/month (vs $48 API)
│
└─ Expected revenue: $200k-500k/month
```

```
Phase 3 (Scale, 10,000+ DAU):
├─ STT: Self-hosted + dialect LoRA
├─ TTS: Self-hosted custom VITS + speaker-specific models
├─ LLM: Self-hosted (Gemma, Gemma, or Llama)
├─ Cost: $100-150k/month
│
├─ Rationale:
│  ├─ Complete cost control
│  ├─ Custom models trained on user data
│  ├─ Better quality than APIs (VITS trained on teacher voices)
│  └─ Dialects and accents perfectly preserved
│
└─ Expected revenue: $1M+/month (10k DAU × $100-200/user/month)
```

---

## Recommendation: HYBRID APPROACH

### Best Strategy for LIPI

**Phase 1 (Weeks 1-8): APIs** — Fast launch, validate demand
```
├─ STT: Deepgram ($38.7k/month for 1k DAU)
├─ TTS: ElevenLabs ($9k/month for 1k DAU)
├─ LLM: Groq or Claude API ($0-2k/month for 1k DAU)
└─ Total: $47-50k/month
   - No GPU hardware needed
   - Focus on product/market fit
   - Can pivot fast if needed
```

**Phase 2 (Weeks 9-14): Transition** — Start self-hosted, keep APIs as fallback
```
├─ STT: Self-hosted faster-whisper (GPU 5)
├─ TTS: Phase 1 mms-tts OR keep ElevenLabs during VITS training
├─ LLM: Self-hosted Gemma 3.5 (GPU 0-4) OR API fallback
├─ GPU Cost: $40k/month
├─ API Cost: $5-10k/month (fallbacks only)
└─ Total: $45-50k/month (same as Phase 1!)
   - Better quality (self-hosted)
   - Still simple (APIs as backup)
   - VITS training running in background
```

**Phase 3 (Weeks 15+): Full Self-Hosted**
```
├─ STT: Self-hosted + dialect LoRA
├─ TTS: Custom VITS (Phase 2 complete)
├─ LLM: Self-hosted
├─ Cost: $80-100k/month
├─ Per-user cost: $0.80-1.00 (vs $48 with APIs)
└─ Fully independent of API providers
```

---

## Decision Matrix

### When to Use APIs

✅ **Use APIs if:**
- Building MVP (first 3-6 months)
- DAU < 1,000 (low volume)
- Team doesn't want GPU/ML ops burden
- Need highest quality (Claude for LLM, ElevenLabs for TTS)
- Want fastest time to market
- Have abundant budget ($50k+/month)

### When to Use Self-Hosted

✅ **Use Self-Hosted if:**
- DAU > 1,000 (cost threshold)
- Long-term business plan (2+ years)
- Want complete data control
- Need custom models (dialect-specific, speaker-specific)
- Team has ML engineering capability
- Want to build proprietary IP
- Concerned about vendor lock-in

### When to Use Hybrid

✅ **Use Hybrid if:**
- **Starting with APIs, migrating gradually** ← RECOMMENDED FOR LIPI
- Want best of both (simplicity + cost)
- Progressive complexity as DAU scales
- Fallback strategy for reliability
- Testing self-hosted before full commitment

---

## Cost Summary Table

```
Monthly Cost by DAU (API vs Self-Hosted):

DAU     | API Cost        | Self-Hosted | Winner      | Savings
--------|-----------------|-------------|-------------|----------
100     | $4,772          | $52,100     | API         | -$47,328
500     | $23,858         | $52,100     | API         | -$28,242
1,000   | $47,715         | $52,100     | API*        | -$4,385
2,000   | $95,430         | $52,100     | Self-Hosted | $43,330
5,000   | $238,575        | $52,100     | Self-Hosted | $186,475
10,000  | $477,150        | $52,100     | Self-Hosted | $425,050
100,000 | $4,771,500      | $106,900**  | Self-Hosted | $4,664,600

* At 1,000 DAU, API slightly cheaper, but within margin
** Self-hosted needs 2× more GPU at 100k DAU
```

---

## Final Recommendation for LIPI

**Start with APIs for MVP, migrate to self-hosted at 1,000+ DAU**

**Phase 1 (MVP Launch):**
- Use Deepgram (STT) + ElevenLabs (TTS) + Groq (LLM)
- Total: $50k/month for 1,000 DAU
- Advantage: Fast launch, no GPU ops

**Phase 2 (Product Market Fit):**
- Migrate to self-hosted as you hit 1,000-2,000 DAU
- Invest in 10× L40S cluster ($80k upfront)
- Save $400k/month starting at 10,000 DAU

**Phase 3 (Scale):**
- Fully self-hosted with custom models
- Train dialect-specific STT + speaker-specific TTS
- Cost: $1.00/user/month (vs $48 with APIs)

**ROI:** The 10× L40S investment pays for itself in <1 month at 10,000 DAU.

