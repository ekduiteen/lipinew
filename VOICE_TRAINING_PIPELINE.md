# Custom Nepali Voice Training Pipeline

**Timeline**: 6 weeks to first production voice  
**GPU Allocation**: GPU 8-9 (96GB dedicated to training)  
**Target**: Custom VITS model with MOS > 4.0  
**Output**: Speaker-specific LoRA adapters for each high-quality teacher

---

## Timeline Overview

```
Week 1: Dataset Collection & Preparation
├─ Download Mozilla Common Voice Nepali
├─ Download Vakyansh dataset (Indian languages)
├─ Download FLEURS dataset
├─ Download OpenSLR datasets
└─ Export LIPI user-collected data from MinIO

Week 2-3: Audio Preprocessing & Cleaning
├─ Resample all to 22kHz
├─ Normalize loudness (-23 LUFS)
├─ Remove silence (Silero VAD)
├─ Quality filtering (SNR > 20dB)
├─ Duration filtering (3-30 second utterances)
└─ Artifact removal (clicks, pops)

Week 4: Phoneme Alignment
├─ Install Montreal Forced Aligner (MFA)
├─ Download/train Nepali phoneme model
├─ Align all audio to text
└─ Handle MFA failures (eSpeak-ng fallback)

Week 5: VITS Training
├─ Prepare multi-speaker dataset
├─ Train base VITS model (500k steps)
├─ Evaluate on validation set (MOS prediction)
├─ Quality gates check
└─ Save checkpoints

Week 6: Integration & Testing
├─ Load VITS into GPU 6
├─ Test synthesis pipeline
├─ Compare Phase 1 (mms-tts) vs Phase 2 (VITS)
├─ A/B testing with teachers
└─ Deploy to production
```

---

## Week 1: Dataset Collection

### Public Datasets

```python
async def download_public_datasets():
    """
    Download all available Nepali speech datasets
    """
    
    datasets = {
        "mozilla_cv": {
            "url": "https://commonvoice.mozilla.org/datasets",
            "language": "ne",
            "expected_hours": 50,
            "license": "CC0 (public domain)"
        },
        "vakyansh": {
            "url": "https://github.com/facebookresearch/Dakshina",
            "language": "ne",
            "expected_hours": 100,
            "license": "CC BY 4.0"
        },
        "fleurs": {
            "url": "https://research.google.com/fleurs/",
            "language": "ne",
            "expected_hours": 20,
            "license": "CC BY 4.0"
        },
        "openslr": {
            "url": "http://www.openslr.org/",
            "language": "ne (OpenSLR32 + others)",
            "expected_hours": 100,
            "license": "CC BY 4.0"
        }
    }
    
    total_hours = sum(d["expected_hours"] for d in datasets.values())
    print(f"Total public dataset: ~{total_hours} hours")
    
    # Download each dataset
    for name, info in datasets.items():
        print(f"Downloading {name}...")
        await download_dataset(info["url"], name)
```

### LIPI User Data

```python
async def export_lipi_collected_data():
    """
    Export all high-quality user audio from LIPI sessions
    """
    
    # Query high-quality recordings
    high_quality_messages = db.query(Message).filter(
        Message.sender == "user",
        Message.audio_quality >= 0.85,
        Message.audio_duration_ms > 3000,
        Message.audio_file_path != None
    ).all()
    
    print(f"Found {len(high_quality_messages)} high-quality user recordings")
    
    # Download from MinIO
    export_dir = "/data/lipi_training_audio"
    for msg in high_quality_messages:
        audio_bytes = minio.get_object("lipi-audio", msg.audio_file_path).data
        
        # Organize by speaker (teacher)
        speaker_dir = f"{export_dir}/speaker_{msg.sender_id}"
        os.makedirs(speaker_dir, exist_ok=True)
        
        with open(f"{speaker_dir}/{msg.id}.wav", 'wb') as f:
            f.write(audio_bytes)
        
        # Store transcription
        with open(f"{speaker_dir}/{msg.id}.txt", 'w', encoding='utf-8') as f:
            f.write(msg.text_nepali or msg.text_original)
    
    return export_dir
```

### Data Summary

```python
class DatasetSummary:
    """
    After Week 1, we should have:
    """
    
    stats = {
        "mozilla_cv": {"hours": 50, "speakers": 200, "utterances": 5000},
        "vakyansh": {"hours": 100, "speakers": 300, "utterances": 15000},
        "fleurs": {"hours": 20, "speakers": 100, "utterances": 2000},
        "openslr": {"hours": 100, "speakers": 200, "utterances": 10000},
        "lipi_user_data": {"hours": 50, "speakers": 100, "utterances": 3000},
        
        "TOTAL": {
            "hours": 320,
            "speakers": 900,
            "utterances": 35000,
            "combined_size_gb": 180
        }
    }
```

---

## Week 2-3: Audio Preprocessing

### Resample to 22kHz

```python
async def resample_audio(input_dir: str, output_dir: str):
    """
    All audio → 22kHz (VITS standard)
    """
    
    for audio_file in glob.glob(f"{input_dir}/**/*.wav", recursive=True):
        # Load at original rate
        y, sr = librosa.load(audio_file, sr=None)
        
        # Resample to 22kHz
        y_resampled = librosa.resample(y, orig_sr=sr, target_sr=22000)
        
        # Save
        output_path = audio_file.replace(input_dir, output_dir)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        sf.write(output_path, y_resampled, 22000)
```

### Normalize Loudness

```python
async def normalize_loudness(audio_file: str, target_loudness: float = -23):
    """
    Normalize to -23 LUFS (broadcast standard)
    Prevents loud speakers from drowning out quiet ones
    """
    
    import pyloudnorm as pyln
    
    meter = pyln.Meter(22000)
    
    # Load audio
    y, sr = librosa.load(audio_file, sr=22000)
    
    # Measure loudness
    loudness = meter.integrated_loudness(y)
    
    # Normalize
    if loudness != float('-inf'):
        y_normalized = pyln.normalize.loudness(y, target_loudness)
    else:
        y_normalized = y  # Silent audio, skip
    
    # Save
    sf.write(audio_file, y_normalized, sr)
```

### Silence Removal (Silero VAD)

```python
async def remove_silence(audio_file: str):
    """
    Remove leading/trailing silence and long pauses
    Keeps training data tight and meaningful
    """
    
    import torch
    from silero import load_silero_vad
    
    model, utils = load_silero_vad()
    (get_speech_timestamps, save_wav, read_wav) = utils
    
    # Load audio
    wav = read_wav(audio_file)
    
    # Detect speech
    speech_timestamps = get_speech_timestamps(wav, model)
    
    # Remove silence
    trimmed_wav = torch.cat([
        wav[timestamp['start']:timestamp['end']]
        for timestamp in speech_timestamps
    ])
    
    # Save
    sf.write(audio_file, trimmed_wav.numpy(), 22000)
```

### Quality Filtering

```python
async def assess_and_filter_quality(audio_dir: str):
    """
    Keep only audio that meets quality standards:
    - SNR (Signal-to-Noise Ratio) > 20dB
    - Duration 3-30 seconds
    - No clipping
    - No speech synthesis artifacts
    """
    
    qualified = []
    rejected = []
    
    for audio_file in glob.glob(f"{audio_dir}/**/*.wav", recursive=True):
        y, sr = librosa.load(audio_file, sr=22000)
        
        # Check 1: Duration
        duration = len(y) / sr
        if duration < 3 or duration > 30:
            rejected.append((audio_file, f"Duration {duration:.1f}s"))
            os.remove(audio_file)
            continue
        
        # Check 2: SNR (signal-to-noise ratio)
        # Estimate noise from quietest 20% of signal
        S = np.abs(librosa.stft(y))
        energy = np.sum(S ** 2, axis=0)
        noise_floor = np.percentile(energy, 20)
        signal_power = np.mean(energy)
        snr = 10 * np.log10(signal_power / (noise_floor + 1e-10))
        
        if snr < 20:
            rejected.append((audio_file, f"SNR {snr:.1f}dB"))
            os.remove(audio_file)
            continue
        
        # Check 3: Peak normalization (no clipping)
        if np.max(np.abs(y)) > 0.99:
            rejected.append((audio_file, "Clipped audio"))
            os.remove(audio_file)
            continue
        
        qualified.append(audio_file)
    
    print(f"Qualified: {len(qualified)} files")
    print(f"Rejected: {len(rejected)} files")
    for path, reason in rejected[:10]:
        print(f"  - {path}: {reason}")
```

### Result: ~280 hours of clean, normalized audio

---

## Week 4: Phoneme Alignment (Montreal Forced Aligner)

### MFA Installation

```bash
# Install MFA
pip install Montreal-Forced-Aligner

# Download Nepali model (if available)
mfa model download acoustic nepali
mfa model download g2p nepali

# If Nepali model unavailable, use eSpeak-ng fallback
apt-get install espeak-ng
```

### Alignment Process

```python
async def run_forced_alignment(audio_dir: str, text_dir: str):
    """
    Align text (at phoneme level) to audio
    Required for VITS to learn precise timing
    """
    
    import subprocess
    
    # Prepare directories
    # audio_dir/: *.wav files
    # text_dir/: *.txt files (same name, same order)
    
    # Run MFA
    result = subprocess.run([
        "mfa", "align",
        audio_dir,
        text_dir,
        "nepali",  # or "english" if unavailable
        "output_dir",
        "--clean",
        "--overwrite"
    ])
    
    if result.returncode != 0:
        print("MFA failed, using eSpeak-ng fallback")
        await run_espeak_fallback(audio_dir, text_dir)
    
    # Output: TextGrid files with phoneme boundaries
    # Each utterance has: word-level + phoneme-level timestamps
```

### eSpeak-ng Fallback (for Nepali without MFA model)

```python
async def run_espeak_fallback(audio_dir: str, text_dir: str):
    """
    If MFA unavailable, use eSpeak-ng phoneme prediction
    Less accurate but better than nothing
    """
    
    import subprocess
    
    for audio_file in glob.glob(f"{audio_dir}/*.wav"):
        base = os.path.basename(audio_file).replace(".wav", "")
        text_file = f"{text_dir}/{base}.txt"
        
        # Read text
        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        # Generate phonemes
        phoneme_output = subprocess.check_output([
            "espeak-ng", "-q", "-v", "ne", "-x", text
        ]).decode('utf-8')
        
        # Parse and create dummy alignment
        phonemes = phoneme_output.split()
        duration_per_phoneme = len(audio_file) / 22000 / len(phonemes)
        
        # Create simple alignment (uniform spacing)
        alignment = {
            "phonemes": [
                {
                    "text": ph,
                    "start": i * duration_per_phoneme,
                    "end": (i+1) * duration_per_phoneme
                }
                for i, ph in enumerate(phonemes)
            ]
        }
        
        # Save alignment
        json.dump(alignment, open(f"alignments/{base}.json", 'w'))
```

---

## Week 5: VITS Training

### Training Setup

```python
class VITSTrainingConfig:
    # Model architecture
    hidden_channels = 384
    filter_channels = 1536
    filter_channels_dp = 256
    encoder_type = "transformer"
    encoder_hidden_size = 384
    encoder_num_layers = 4
    encoder_num_heads = 2
    encoder_kernel_size = 3
    
    # Multi-speaker
    num_speakers = 900  # From our dataset
    global_channels = 512
    use_speaker_embedding = True
    
    # Training
    batch_size = 64  # Can fit on GPU 8
    num_epochs = 500
    learning_rate = 2e-3
    adam_betas = (0.8, 0.99)
    weight_decay = 1e-6
    
    # Data
    num_mels = 80
    n_fft = 1024
    hop_size = 256  # 22050 Hz / 256 = 86.1 ms frames
    f_min = 0
    f_max = 11025  # Nyquist frequency
    
    # Loss weights
    loss_kl = 0.5
    loss_duration = 1.0
    loss_l1 = 1.0
```

### Training Loop

```python
async def train_vits(
    train_dir: str,
    val_dir: str,
    config: VITSTrainingConfig,
    device: str = "cuda:8"
):
    """
    Train multi-speaker VITS model
    """
    
    # Load model
    model = VITSMultiSpeaker(config).to(device)
    discriminator = MultiPeriodDiscriminator(config).to(device)
    
    # Optimizers
    optimizer = torch.optim.AdamW(
        list(model.parameters()) + list(discriminator.parameters()),
        lr=config.learning_rate,
        betas=config.adam_betas,
        weight_decay=config.weight_decay
    )
    
    scheduler = torch.optim.lr_scheduler.ExponentialLR(
        optimizer,
        gamma=0.999
    )
    
    # Data loaders
    train_loader = create_vits_dataloader(train_dir, config, shuffle=True)
    val_loader = create_vits_dataloader(val_dir, config, shuffle=False)
    
    best_val_loss = float('inf')
    best_mos = 0.0
    
    for epoch in range(config.num_epochs):
        # Training epoch
        train_loss = 0
        for batch_idx, batch in enumerate(train_loader):
            # Forward pass
            loss = model.training_step(batch, discriminator)
            
            # Backward
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            
            train_loss += loss.item()
            
            if batch_idx % 100 == 0:
                logger.info(f"Epoch {epoch}, Batch {batch_idx}: {loss:.4f}")
        
        # Validation every 50 epochs
        if epoch % 50 == 0:
            val_loss = 0
            for batch in val_loader:
                val_loss += model.validation_step(batch).item()
            val_loss /= len(val_loader)
            
            # Evaluate MOS
            mos = await evaluate_model_mos(model)
            logger.info(f"Epoch {epoch}: Val Loss {val_loss:.4f}, MOS {mos:.2f}")
            
            # Save if improved
            if mos > best_mos:
                best_mos = mos
                torch.save(
                    model.state_dict(),
                    f"s3://lipi-models/vits_epoch_{epoch}_mos_{mos:.2f}.pth"
                )
        
        scheduler.step()
```

### Checkpointing Strategy

```python
# Save every 50 epochs
# Keep last 5 checkpoints
# Best checkpoint selected by MOS score
# Periodically export to MinIO

checkpoints = {
    "epoch_0": {"path": "s3://...", "mos": 1.8},
    "epoch_50": {"path": "s3://...", "mos": 2.4},
    "epoch_100": {"path": "s3://...", "mos": 3.1},
    "epoch_150": {"path": "s3://...", "mos": 3.8},
    "epoch_200": {"path": "s3://...", "mos": 4.1},  # BEST
    "epoch_250": {"path": "s3://...", "mos": 4.0},
    "epoch_300": {"path": "s3://...", "mos": 3.9},
}
```

---

## Week 6: Integration & Testing

### Load into Production (GPU 6)

```python
class ProductionVITS:
    def __init__(self):
        # Load Phase 2 model
        self.vits_model = load_vits_checkpoint(
            "s3://lipi-models/vits_epoch_200_mos_4.1.pth"
        ).to("cuda:6").eval()
        
        # Load vocoder
        self.vocoder = load_hifigan_vocoder().to("cuda:6").eval()
        
        # Fall back to Phase 1 if needed
        self.phase1_fallback = load_mms_tts_model()
```

### A/B Testing with Teachers

```python
async def run_ab_testing():
    """
    Compare Phase 1 (mms-tts) vs Phase 2 (VITS)
    Teachers rate quality on 1-5 scale
    """
    
    test_sentences = [
        "नमस्ते, मेरो नाम राज हो।",
        "नेपाल बहुत सुंदर देश है।",
        "आज कस्तो दिन हो?",
    ]
    
    results = {
        "phase1_mms": [],
        "phase2_vits": []
    }
    
    for sentence in test_sentences:
        # Phase 1
        audio_phase1 = phase1_tts.synthesize(sentence)
        
        # Phase 2
        audio_phase2 = phase2_vits.synthesize(sentence)
        
        # Present to teachers
        # Ask: "Which sounds more natural? (1=Phase1, 5=Phase2)"
        
        # Aggregate scores
        # If Phase 2 > Phase 1 by +1.0 MOS: deploy
```

### Deployment Decision

```python
if phase2_mos > phase1_mos + 0.3:
    print("Phase 2 PASSED quality gate. Deploying...")
    
    # Hot-swap
    redis.publish("tts_model_update", {
        "model": "vits_phase2",
        "checkpoint": "s3://lipi-models/vits_epoch_200.pth",
        "effective_immediately": True
    })
    
    # GPU 6 loads new model during next idle period
    # Existing connections finish with old model
    # New connections use new model
else:
    print("Phase 2 did not improve. Continue training or stick with Phase 1.")
    
    # Fallback: keep Phase 1 (mms-tts), plan Phase 3
```

---

## Monitoring During Training

### Key Metrics

```
Week 5 Training Progress:
├─ Epoch 0-50: Loss 3.2 → 1.8 (large improvement expected)
├─ Epoch 50-150: Loss 1.8 → 1.2 (slower improvement)
├─ Epoch 150-300: Loss 1.2 → 0.9 (fine-tuning)
├─ Epoch 300-500: Loss 0.9 → 0.85 (convergence)
└─
├─ MOS trajectory:
│  ├─ Epoch 0: 1.0 (random)
│  ├─ Epoch 50: 2.2
│  ├─ Epoch 100: 3.0
│  ├─ Epoch 150: 3.6
│  ├─ Epoch 200: 4.1 ← GOOD
│  ├─ Epoch 250: 4.0 (plateau)
│  └─ Epoch 300+: 3.9 (slight degradation - overfitting)
│
└─ GPU 8 memory: 45GB / 48GB
```

---

## Post-Training: Speaker-Specific LoRA

### Weekly Speaker LoRA Training

```python
async def train_speaker_lora_weekly():
    """
    Every Sunday, for each teacher with 50+ utterances:
    Train speaker-specific VITS LoRA adapter
    """
    
    for teacher in get_teachers_with_sufficient_data():
        # Collect teacher's audio
        audio_files = get_teacher_audio(teacher.id, min_quality=0.85)
        
        if len(audio_files) >= 50:
            # Train lightweight LoRA on top of base VITS
            checkpoint = await train_speaker_lora(
                teacher_id=teacher.id,
                audio_files=audio_files,
                lora_rank=8
            )
            
            # Evaluate
            mos = evaluate_mos(checkpoint)
            
            # Only deploy if improves base model
            if mos > base_vits_mos + 0.2:
                save_speaker_model(teacher.id, checkpoint)
```

---

## Success Criteria

✓ Phase 2 VITS trained and integrated  
✓ MOS score > 4.0 (acceptable quality)  
✓ Improves on Phase 1 (mms-tts) by >0.3 MOS  
✓ Inference <500ms per 3-second audio  
✓ 50+ speaker-specific LoRA models trained  
✓ Teachers prefer Phase 2 in A/B testing  

---

## Fallback Plan (if training fails)

```
If Phase 2 VITS quality < Phase 1:
├─ Option A: Continue training longer (Week 7-8)
├─ Option B: Try different architecture (Glow-TTS, FastSpeech2)
├─ Option C: Use Phase 1 permanently, plan Phase 3 with transfer learning
└─ Option D: Reduce dataset, use subset of highest-quality audio
```

Timeline remains aggressive but realistic for production voice synthesis.

