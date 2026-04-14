# STT Architecture: Nepali Speech Recognition at Scale

**Model**: faster-whisper large-v3  
**GPU Allocation**: GPU 5 (48GB)  
**Latency Target**: <200ms per 60-second audio  
**Languages**: 99 languages baseline + 30+ Nepali dialect-specific LoRA

---

## Model Selection: Why faster-whisper large-v3

| Feature | faster-whisper | OpenAI Whisper | Wav2Vec2 |
|---------|-----------------|-----------------|----------|
| **WER (Nepali)** | 8-12% | 10-14% | 5-8% (when fine-tuned) |
| **Speed** | 4× faster | 1× baseline | 2× faster |
| **Inference** | Local GPU | API call | Local GPU |
| **Cost** | $0/month | $5k+/month | $0/month |
| **Languages** | 99 | 99 | Limited |
| **Real-time capable** | ✓ Yes | ✗ No | ✓ Yes |
| **Maturity** | Production-ready | Production | Research |

**Decision**: faster-whisper large-v3 (best balance of speed, accuracy, cost)

---

## Inference Architecture

### GPU Memory Layout (GPU 5)

```
GPU 5 (48GB total)
├─ Whisper model (float16): 6.0GB
│  ├─ Encoder: 3.0GB
│  ├─ Decoder: 2.5GB
│  └─ Weights: 0.5GB
│
├─ 8 concurrent instances: 0.5GB each (4GB total)
│  └─ Shared with model
│
├─ LoRA adapters (loaded on demand): 0.2GB each
│  ├─ kathmandu_lora.pth
│  ├─ eastern_lora.pth
│  ├─ terai_lora.pth
│  └─ ... (30+ dialects)
│
├─ Speaker embeddings cache: 1GB
│  └─ e5-large model for clustering
│
└─ Headroom for batch processing: ~36GB
```

### Concurrent Instance Management

```python
class WhisperPool:
    def __init__(self, n_workers: int = 8):
        self.n_workers = n_workers
        self.workers = [WhisperWorker() for _ in range(n_workers)]
        self.queue = asyncio.Queue()
        self.active_jobs = {}
    
    async def transcribe(self, audio_bytes: bytes, language: str = "ne"):
        """
        Queue audio for transcription
        Returns: {text, confidence, language}
        """
        job_id = uuid4()
        
        # Enqueue
        await self.queue.put({
            "job_id": job_id,
            "audio": audio_bytes,
            "language": language
        })
        
        # Wait for result
        result = await self.active_jobs[job_id].wait()
        return result
    
    async def _worker_loop(self, worker_id: int):
        """
        Each worker processes jobs sequentially
        """
        while True:
            job = await self.queue.get()
            
            try:
                # Select appropriate LoRA
                lora = await select_whisper_lora(job["language"])
                
                # Transcribe
                result = worker.transcribe(
                    audio=job["audio"],
                    language=job["language"],
                    lora_path=lora
                )
                
                # Store result
                self.active_jobs[job["job_id"]].set_result(result)
            
            except Exception as e:
                self.active_jobs[job["job_id"]].set_exception(e)
            finally:
                self.queue.task_done()
```

---

## Dialect-Specific LoRA Strategy

### The 30+ Nepali Dialects

Based on speaker clustering, we support:

```
Tier 1 - Major (100k+ speakers each, high priority)
├─ Kathmandu Valley (Standard Nepali)
├─ Eastern (Jhapa, Morang, Sunsari) — Rai/Limbu influence
├─ Terai (Parsa, Bara, Rautahat) — Maithili influence
├─ Western (Pokhara, Lamjung) — Gurung/Magar influence
└─ Far-Western (Kailali, Kanchanpur) — Tharu/Awadhi influence

Tier 2 - Regional (10k-100k speakers each)
├─ Dolakha (Newari influence)
├─ Gorkhaland (Indian border, Hindi influence)
├─ Mustang (Tibetan influence)
├─ Illam (Eastern hill, Rai accent)
└─ ... 15 more

Tier 3 - Emerging (1k-10k speakers, discovered via clustering)
├─ Dynamically identified as teachers contribute
├─ Automatically trained weekly
├─ Pruned if <100 speakers
```

### Training LoRA Adapters

```python
async def train_whisper_lora(
    dialect_id: str,
    audio_samples: list[str],  # MinIO paths
    min_samples: int = 100
) -> str:
    """
    Train dialect-specific LoRA adapter
    """
    
    # Step 1: Validate data
    if len(audio_samples) < min_samples:
        raise InsufficientDataError(f"Need {min_samples}, got {len(audio_samples)}")
    
    # Step 2: Download audio from MinIO
    local_audio_dir = f"/tmp/whisper_train/{dialect_id}"
    for audio_path in audio_samples:
        audio_bytes = minio.get_object("lipi-audio", audio_path).data
        local_path = f"{local_audio_dir}/{uuid4()}.wav"
        with open(local_path, 'wb') as f:
            f.write(audio_bytes)
    
    # Step 3: Load base Whisper model
    base_model = WhisperModel(
        model_size="large",
        device="cuda:8",  # GPU 8 for training
        compute_type="float16"
    )
    
    # Step 4: Prepare LoRA
    from peft import get_peft_model, LoraConfig
    
    lora_config = LoraConfig(
        r=8,                          # LoRA rank
        lora_alpha=32,                # Scaling factor
        target_modules=["attention"], # Which layers to adapt
        bias="none",
        task_type="seq2seq_lm"
    )
    
    model_with_lora = get_peft_model(base_model, lora_config)
    
    # Step 5: Train on dialect audio
    trainer = transformers.Trainer(
        model=model_with_lora,
        train_dataset=load_audio_dataset(local_audio_dir),
        args=transformers.TrainingArguments(
            output_dir=f"/tmp/whisper_lora_{dialect_id}",
            num_train_epochs=3,
            per_device_train_batch_size=8,
            learning_rate=1e-4,
            logging_steps=100,
            save_steps=500,
            eval_strategy="steps",
            eval_steps=500,
            metric_for_best_model="wer",
            load_best_model_at_end=True,
        ),
        callbacks=[
            transformers.EarlyStoppingCallback(
                early_stopping_patience=3,
                early_stopping_threshold=0.01
            )
        ]
    )
    
    trainer.train()
    
    # Step 6: Evaluate WER (Word Error Rate)
    wer = evaluate_wer(model_with_lora, test_audio_path)
    
    # Step 7: Save checkpoint
    checkpoint_path = f"s3://lipi-models/whisper_lora_{dialect_id}.pth"
    model_with_lora.save_pretrained(checkpoint_path)
    
    # Step 8: Log metrics
    db.add(DialectModelMetrics(
        dialect_id=dialect_id,
        wer_score=wer,
        training_samples=len(audio_samples),
        checkpoint_path=checkpoint_path,
        created_at=now()
    ))
    db.commit()
    
    return checkpoint_path
```

### Weekly Retraining Schedule

```python
async def weekly_whisper_retraining():
    """
    Every Sunday 2AM (minimal traffic)
    Re-cluster speakers and retrain all dialect LoRAs
    """
    
    # Step 1: Re-cluster (dialects may shift)
    new_dialects = await discover_dialects()
    
    # Step 2: For each dialect with 100+ new samples since last training
    for dialect in new_dialects:
        new_audio_count = count_new_audio_since_last_training(dialect)
        
        if new_audio_count >= 100:
            old_wer = dialect.last_wer or 0.15
            
            # Retrain
            new_wer = await train_whisper_lora(
                dialect.id,
                audio_samples=get_dialect_audio(dialect)
            )
            
            # Only deploy if >0.5% WER improvement
            if (old_wer - new_wer) / old_wer > 0.005:
                # Publish event: new LoRA available
                redis.publish("whisper_model_updated", dialect.id)
                
                logger.info(f"Whisper {dialect.name}: {old_wer:.1%} → {new_wer:.1%} WER")
    
    # Step 3: Hot-swap at next idle moment
    # (GPU 5 loads new LoRA during low-traffic period)
```

---

## Real-Time Inference Flow

```python
async def transcribe_audio(
    audio_bytes: bytes,
    speaker_embedding: np.ndarray,
    teacher_id: int,
    language: str = "ne"
) -> dict:
    """
    Complete STT pipeline
    """
    
    start_time = time.time()
    
    # Step 1: Select appropriate dialect LoRA (10ms)
    if language == "ne":
        lora_path = await select_whisper_lora(
            speaker_embedding=speaker_embedding,
            teacher_id=teacher_id
        )
    else:
        lora_path = None  # Use generic for non-Nepali
    
    # Step 2: Load LoRA if not already cached (5ms cached, 50ms fresh)
    if lora_path not in cache:
        cache[lora_path] = load_whisper_lora(lora_path)
    
    # Step 3: Run Whisper inference (150ms)
    result = whisper_pool.transcribe(
        audio=audio_bytes,
        lora=cache[lora_path],
        language=language
    )
    
    # Step 4: Post-process
    text = result.text
    confidence = result.confidence
    
    # Extract speaker embedding (concurrent with steps 1-3)
    speaker_emb = extract_speaker_embedding(audio_bytes)
    
    # Step 5: Return results
    elapsed = time.time() - start_time
    
    return {
        "text": text,
        "confidence": confidence,
        "language": language,
        "duration": len(audio_bytes) / (16000 * 2),  # seconds
        "inference_time_ms": elapsed * 1000,
        "speaker_embedding": speaker_emb,
        "dialect_lora_used": lora_path,
        "alternatives": result.alternatives
    }
```

### Latency Profile

```
Audio input (typically 60 seconds)
    │
    ├─→ LoRA selection + loading: 15ms
    │
    ├─→ Whisper inference: 150ms
    │   ├─ Audio preprocessing: 20ms
    │   ├─ Encoder: 80ms
    │   ├─ Decoder: 40ms
    │   └─ Post-processing: 10ms
    │
    ├─→ Speaker embedding (parallel): 50ms
    │
    └─→ Total (user-facing): 200ms ✓
    
    Target met: <200ms for 60s audio
```

---

## Language Detection

```python
async def detect_language(audio_bytes: bytes) -> dict:
    """
    Detect language from audio using multiple methods
    """
    
    # Method 1: Whisper's built-in language detection
    whisper_lang = whisper_model.detect_language(audio_bytes)
    
    # Method 2: LangID on the transcribed text
    text = whisper_model.transcribe(audio_bytes, language="auto")
    langid_lang = langid.classify(text)[0]
    
    # Method 3: Consensus or fallback
    if whisper_lang == langid_lang:
        detected = whisper_lang
        confidence = 0.95
    else:
        # Disagreement; use audio-based (more reliable)
        detected = whisper_lang
        confidence = 0.70
    
    # Special case: Code-switching detection
    if detect_code_switching(text):
        detected = "mixed"
        language_mix = estimate_language_mix(text)
    
    return {
        "language": detected,
        "confidence": confidence,
        "alternatives": [
            {"language": langid_lang, "confidence": 0.20},
            {"language": "hi", "confidence": 0.05}
        ],
        "is_code_switching": detected == "mixed",
        "language_mix": language_mix if detected == "mixed" else None
    }
```

---

## Error Handling & Fallbacks

```python
async def transcribe_with_fallback(
    audio_bytes: bytes,
    teacher_id: int,
    language: str = "ne"
) -> dict:
    """
    Graceful degradation: try best model, fallback if needed
    """
    
    try:
        # Try dialect-specific LoRA
        result = await transcribe_audio(
            audio_bytes=audio_bytes,
            teacher_id=teacher_id,
            language=language,
            timeout=2.0  # 2 second timeout
        )
        
        if result.confidence < 0.6:
            logger.warn(f"Low confidence: {result.confidence}")
        
        return result
    
    except TimeoutError:
        logger.warn("STT timeout, using generic model")
        
        # Fallback: use generic Whisper without LoRA
        result = await transcribe_audio(
            audio_bytes=audio_bytes,
            teacher_id=None,
            language=language,
            lora=None
        )
        
        result["model_used"] = "generic"
        return result
    
    except LoRALoadError:
        logger.error(f"LoRA load failed, using generic")
        
        # LoRA checkpoint corrupted? Use base model
        result = await transcribe_audio(
            audio_bytes=audio_bytes,
            lora=None,
            language=language
        )
        
        result["model_used"] = "generic"
        return result
    
    except Exception as e:
        logger.error(f"STT failed: {e}")
        
        # Last resort: return error, tell user to try again
        raise STTError(f"Speech recognition failed: {str(e)}")
```

---

## Monitoring & Metrics

### Key Metrics

```python
class STTMetrics:
    # Performance
    avg_inference_time_ms: float  # Target: <200ms
    p95_inference_time_ms: float  # Target: <300ms
    
    # Accuracy
    avg_confidence: float          # Target: >0.85
    wer_by_dialect: dict          # Target: <12% WER
    
    # Resource
    gpu_memory_used_gb: float      # Target: <20GB active
    queue_depth: int              # Target: <100
    
    # Errors
    timeout_errors_per_hour: int  # Target: 0
    fallback_used_percent: float  # Target: <5%
```

### Alerting

```python
async def monitor_stt_health():
    """
    Real-time health checks
    """
    
    while True:
        metrics = get_stt_metrics()
        
        # Alert on degradation
        if metrics.avg_inference_time_ms > 400:
            alert("STT Latency degraded", severity="warning")
        
        if metrics.avg_confidence < 0.80:
            alert("STT Confidence dropping", severity="warning")
        
        if metrics.queue_depth > 200:
            alert("STT Queue full, possible bottleneck", severity="critical")
        
        if metrics.timeout_errors_per_hour > 10:
            alert("STT timeouts increasing", severity="critical")
        
        await asyncio.sleep(60)  # Check every minute
```

---

## Future Enhancements

### Phase 2: Fine-Tuned Wav2Vec2 (Better Accuracy)
```
Current: faster-whisper (8-12% WER)
Phase 2: Fine-tuned Wav2Vec2 (5-8% WER)
Effort: 4 weeks, 100h+ Nepali audio

Benefits:
- Better accuracy for quality users
- Smaller model (can run on GPU 5 with more concurrency)
- Faster inference (100ms instead of 150ms)
```

### Phase 3: Speaker Diarization
```
Detect multiple speakers in group conversations
- "Who said नमस्ते? That was Ramesh, not Sita."
- Separate speaker contributions in transcript
- Train speaker-specific STT adapters
```

### Phase 4: Real-Time Streaming
```
Instead of: wait for user to finish speaking
Implement: streaming ASR (return results as they speak)
Benefit: Perceived latency <100ms
```

---

## Deployment Checklist

- [ ] Faster-whisper 1.0.3 installed on GPU 5
- [ ] 30+ Nepali dialect LoRA checkpoints trained
- [ ] Speaker embedding extractor running
- [ ] Redis Streams queue for transcription
- [ ] Metrics exported to Prometheus
- [ ] Fallback chain tested
- [ ] End-to-end latency <200ms verified
- [ ] WER evaluated on test set
- [ ] Load test: 64 concurrent users
- [ ] Monitoring alerts configured

