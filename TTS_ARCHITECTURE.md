# TTS Architecture: Nepali Voice Synthesis

**Phase 1 Model**: facebook/mms-tts-npi (Immediate, zero training)  
**Phase 2 Model**: Custom VITS multi-speaker (6-week training)  
**GPU Allocation**: GPU 6 (48GB)  
**Latency Target**: <500ms per 3-second audio  
**Languages**: Nepali (primary), English, Newari, Maithili (expandable)

---

## Phase 1: Immediate Drop-In (facebook/mms-tts-npi)

### Why Start Here

```
Advantage: Zero training required
Model: Massively Multilingual Speech (Facebook Meta)
├─ Pre-trained on 1000+ hours per language
├─ 1100+ languages (includes Nepali)
├─ MOS score: 3.2/5 (good enough for v1)
└─ License: CC BY-NC 4.0 (acceptable for research/non-commercial)

Disadvantage: Doesn't sound like teachers
├─ Generic neutral voice
├─ No speaker-specific variations
└─ Can't reproduce individual teacher accents
```

### Deployment

```python
class MMSTTSModel:
    def __init__(self):
        from transformers import pipeline
        
        self.synthesizer = pipeline(
            "text-to-speech",
            model="facebook/mms-tts-npi",
            device=0  # GPU 6
        )
    
    async def synthesize(self, text: str, language: str = "ne") -> bytes:
        """
        Generate audio from text
        """
        
        # MMS TTS expects text in target language
        if language != "ne":
            # Load appropriate model variant
            model = f"facebook/mms-tts-{language}"
        
        # Generate speech
        output = self.synthesizer(text, forward_params={"speaker_id": 0})
        
        # Output format: {sampling_rate, audio}
        audio_bytes = convert_to_wav(
            output["audio"],
            sample_rate=output["sampling_rate"]
        )
        
        return audio_bytes
```

### Limitations & Timeline

```
Phase 1: facebook/mms-tts-npi
Duration: Week 1-2 (launch)
Quality: 3.2/5 MOS (acceptable)
User experience: "LIPI talks but doesn't sound like my teacher"

Action item: Start Phase 2 training immediately
├─ Collect high-quality teacher voice data (Week 1-2)
├─ Preprocessing & alignment (Week 3-4)
└─ VITS training on GPU 8-9 (Week 5-6)
```

---

## Phase 2: Custom VITS Multi-Speaker

### Model Architecture

```
VITS (Variational Inference Text-to-Speech)
├─ Text Encoder: Converts text to latent representation
│  ├─ Phoneme embedding
│  ├─ Speaker embedding injection
│  └─ Duration predictor
│
├─ Variational Autoencoder (VAE): Learns speech variation
│  ├─ Posterior encoder (audio → z)
│  ├─ Prior network
│  └─ Decoder (z → mel-spectrogram)
│
└─ HiFi-GAN Vocoder: Converts mel → waveform
   ├─ High-fidelity audio reconstruction
   ├─ Real-time capable
   └─ Supports speaker embedding conditioning
```

### Training Data Requirements

```
Per speaker (if training speaker-specific):
├─ Minimum: 30 minutes of clean speech
├─ Ideal: 3-10 hours
├─ Quality: 16+ bit, 22kHz or higher
├─ SNR: >20dB (signal-to-noise ratio)
└─ Variability: At least 300+ distinct utterances

For multi-speaker base model:
├─ 50+ diverse speakers
├─ 300+ hours total
├─ Representative dialects (Kathmandu, Eastern, Terai, Western)
└─ Age/gender diversity
```

### Data Collection & Preprocessing

```python
class VITSDataPipeline:
    async def prepare_training_data(self, teacher_ids: list[int]):
        """
        Collect and preprocess teacher audio for VITS training
        """
        
        training_data = {
            "speakers": {},
            "utterances": []
        }
        
        for teacher_id in teacher_ids:
            # Step 1: Collect high-quality audio from teacher
            messages = db.query(Message).filter(
                Message.sender_id == teacher_id,
                Message.audio_file_path != None,
                Message.language == "ne"  # Nepali only
            ).all()
            
            high_quality_audio = []
            for msg in messages:
                # Assess audio quality
                quality = await assess_audio_quality(msg.audio_file_path)
                
                if quality.snr > 20 and quality.duration > 3:  # >3 sec utterances
                    high_quality_audio.append(msg)
            
            # Need at least 50 high-quality utterances per speaker
            if len(high_quality_audio) < 50:
                continue
            
            # Step 2: Download from MinIO
            speaker_dir = f"/tmp/vits_training/{teacher_id}"
            os.makedirs(speaker_dir, exist_ok=True)
            
            for msg in high_quality_audio[:200]:  # Limit to 200 per speaker
                audio_bytes = minio.get_object("lipi-audio", msg.audio_file_path).data
                
                # Resample to 22kHz (VITS standard)
                audio = librosa.load(audio_bytes, sr=22000)[0]
                
                # Normalize loudness to -23 LUFS
                audio = pyln.Meter(22000).integrated_loudness(audio)
                audio = pyln.normalize.loudness(audio, -23)
                
                # Save
                output_path = f"{speaker_dir}/{uuid4()}.wav"
                sf.write(output_path, audio, 22000)
                
                # Store utterance info
                training_data["utterances"].append({
                    "speaker_id": teacher_id,
                    "audio_path": output_path,
                    "text": msg.text_nepali,
                    "duration": len(audio) / 22000
                })
            
            # Step 3: Phoneme alignment (Montreal Forced Aligner)
            training_data["speakers"][teacher_id] = {
                "utterance_count": len([u for u in training_data["utterances"]
                                       if u["speaker_id"] == teacher_id]),
                "total_duration": sum([u["duration"] for u in training_data["utterances"]
                                      if u["speaker_id"] == teacher_id])
            }
        
        # Step 4: Perform phoneme-level alignment
        await self.run_mfa_alignment(training_data)
        
        return training_data
    
    async def run_mfa_alignment(self, training_data: dict):
        """
        Montreal Forced Aligner: align text to speech at phoneme level
        Required for VITS to learn precise timing
        """
        
        # Download MFA models for Nepali
        # If not available, use eSpeak-ng phoneme fallback
        
        for utterance in training_data["utterances"]:
            # Run MFA
            alignment = run_forced_alignment(
                audio_path=utterance["audio_path"],
                text=utterance["text"],
                language="ne"
            )
            
            # Alignment format:
            # {
            #   "phonemes": [{"text": "n", "start": 0.0, "end": 0.1}, ...],
            #   "words": [{"text": "नमस्ते", "start": 0.0, "end": 0.3}, ...]
            # }
            
            utterance["alignment"] = alignment
```

### VITS Training

```python
class VITSTrainer:
    async def train_multi_speaker_vits(
        self,
        training_data: dict,
        epochs: int = 500,
        batch_size: int = 64
    ) -> str:
        """
        Train multi-speaker VITS on collected teacher data
        """
        
        # Step 1: Load pre-trained VITS (from Coqui or similar)
        model = VITSMultiSpeaker(
            num_speakers=len(training_data["speakers"]),
            num_mels=80,
            encoder_hidden_dim=384,
            decoder_hidden_dim=384,
            use_spectral_norm=False
        )
        
        # Step 2: Create speaker embeddings
        speaker_embedding_table = torch.nn.Embedding(
            num_embeddings=len(training_data["speakers"]),
            embedding_dim=192
        )
        
        # Initialize with speaker metadata
        for speaker_id, speaker_info in training_data["speakers"].items():
            embedding = extract_speaker_characteristics(speaker_id)
            speaker_embedding_table.weight.data[speaker_id] = embedding
        
        # Step 3: Prepare dataset
        dataset = VITSDataset(
            training_data=training_data,
            speaker_embedding_table=speaker_embedding_table
        )
        
        dataloader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=4,
            pin_memory=True
        )
        
        # Step 4: Training loop
        optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3)
        scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizer, gamma=0.999)
        
        for epoch in range(epochs):
            total_loss = 0
            
            for batch_idx, batch in enumerate(dataloader):
                # Forward pass
                mel_output, kl_loss, duration_loss = model(
                    x=batch["phonemes"],
                    speaker_embeddings=batch["speaker_embeds"],
                    lengths=batch["lengths"],
                    alignments=batch["alignments"]
                )
                
                # Compute losses
                l1_loss = F.l1_loss(mel_output, batch["mel_target"])
                total_loss = l1_loss + 0.5 * kl_loss + duration_loss
                
                # Backward
                optimizer.zero_grad()
                total_loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                
                # Logging
                if batch_idx % 100 == 0:
                    logger.info(f"Epoch {epoch}, Batch {batch_idx}: Loss {total_loss:.4f}")
            
            # Validation & save checkpoint every 50 epochs
            if epoch % 50 == 0:
                mos = await evaluate_model_mos(model)
                logger.info(f"Epoch {epoch}: MOS {mos:.2f}")
                
                checkpoint_path = f"s3://lipi-models/vits_checkpoint_epoch_{epoch}.pth"
                torch.save(model.state_dict(), checkpoint_path)
                
                # Track best model
                if mos > best_mos:
                    best_mos = mos
                    best_checkpoint = checkpoint_path
            
            scheduler.step()
        
        return best_checkpoint
```

### MOS (Mean Opinion Score) Evaluation

```python
async def evaluate_model_mos(model: VITSMultiSpeaker) -> float:
    """
    Evaluate synthesis quality using UTMOS neural predictor
    (No human raters needed)
    """
    
    # Generate test utterances
    test_prompts = [
        "नमस्ते, आज कस्तो दिन हो?",
        "मेरो नाम राज हो।",
        "नेपाल बहुत सुंदर देश है।",
        "तपाई कहाँबाट हुनुहुन्छ?",
        "मुझे नेपाली सिखाने में मदद करो।"
    ]
    
    mos_scores = []
    
    for prompt in test_prompts:
        # Synthesize with each speaker
        for speaker_id in range(model.num_speakers):
            audio = model.generate(
                text=prompt,
                speaker_id=speaker_id
            )
            
            # Evaluate MOS (UTMOS)
            mos = utmos_predictor(audio)
            mos_scores.append(mos)
    
    average_mos = mean(mos_scores)
    return average_mos
```

### Quality Gates

```python
class VITSQualityGate:
    def should_deploy(self, checkpoint: str) -> bool:
        """
        Only deploy if model meets quality criteria
        """
        
        mos = evaluate_model_mos(checkpoint)
        
        # Minimum quality bar
        if mos < 3.5:
            logger.warn(f"MOS {mos:.2f} below threshold 3.5")
            return False
        
        # Improvement over Phase 1
        phase1_mos = 3.2  # facebook/mms-tts-npi baseline
        if mos < phase1_mos + 0.3:  # Must improve by 0.3+ MOS points
            logger.warn(f"MOS {mos:.2f} doesn't improve enough over {phase1_mos}")
            return False
        
        # Speech similarity check (not copying training data)
        similarity_to_training = check_similarity_to_training_data(checkpoint)
        if similarity_to_training > 0.99:
            logger.warn("Model too similar to training data (overfitting)")
            return False
        
        return True
```

---

## Real-Time Inference

### Voice Model Selection

```python
async def select_tts_voice(
    teacher_id: int,
    speaker_embedding: np.ndarray = None
) -> dict:
    """
    Select the best TTS voice model for this teacher
    
    Priority:
    1. Teacher-specific VITS (if exists and high quality)
    2. Closest speaker (k-NN on embeddings)
    3. Generic base model (fallback)
    """
    
    # Option 1: Teacher-specific speaker model
    speaker_model = db.query(SpeakerVoiceModel).filter_by(
        teacher_id=teacher_id
    ).order_by(SpeakerVoiceModel.created_at.desc()).first()
    
    if speaker_model and speaker_model.mos_score > 3.8:
        return {
            "model_type": "speaker_specific",
            "checkpoint": speaker_model.vits_checkpoint,
            "speaker_id": teacher_id,
            "confidence": 0.98,
            "mos": speaker_model.mos_score
        }
    
    # Option 2: Find closest speaker via k-NN embedding matching
    if speaker_embedding is not None:
        all_speakers = db.query(SpeakerEmbedding).filter(
            SpeakerEmbedding.user_id != teacher_id
        ).all()
        
        if all_speakers:
            distances = [
                (euclidean_distance(speaker_embedding, s.embedding), s.user_id)
                for s in all_speakers
            ]
            
            _, closest_speaker_id = min(distances)
            
            # Get that speaker's model
            closest_model = db.query(SpeakerVoiceModel).filter_by(
                teacher_id=closest_speaker_id
            ).first()
            
            if closest_model:
                return {
                    "model_type": "knn_matched",
                    "checkpoint": closest_model.vits_checkpoint,
                    "speaker_id": closest_speaker_id,
                    "confidence": 0.80
                }
    
    # Option 3: Generic base model
    return {
        "model_type": "base_generic",
        "checkpoint": VITS_BASE_MODEL,
        "speaker_id": 0,
        "confidence": 0.70
    }
```

### Synthesis Pipeline

```python
async def synthesize_speech(
    text: str,
    teacher_id: int,
    speaker_embedding: np.ndarray = None,
    language: str = "ne"
) -> bytes:
    """
    Generate speech audio with appropriate voice
    """
    
    start_time = time.time()
    
    # Step 1: Select voice model (10ms)
    voice_selection = await select_tts_voice(
        teacher_id=teacher_id,
        speaker_embedding=speaker_embedding
    )
    
    # Step 2: Load model if needed (cached, <5ms)
    model = load_vits_model(voice_selection["checkpoint"])
    
    # Step 3: Phoneme conversion (15ms)
    phonemes = convert_text_to_phonemes(
        text=text,
        language=language
    )
    
    # Step 4: Generate mel-spectrogram (300ms)
    mel_spec = model.generate_mel(
        phonemes=phonemes,
        speaker_id=voice_selection["speaker_id"],
        duration_scale=1.0  # Normal speed
    )
    
    # Step 5: HiFi-GAN vocoding (150ms)
    waveform = vocoder.generate(mel_spec)
    
    # Step 6: Convert to WAV bytes (20ms)
    audio_bytes = convert_waveform_to_wav(
        waveform,
        sample_rate=22000
    )
    
    elapsed = time.time() - start_time
    
    return {
        "audio_data": audio_bytes,
        "mime_type": "audio/wav",
        "duration": len(waveform) / 22000,
        "sample_rate": 22000,
        "voice_model_used": voice_selection["model_type"],
        "inference_time_ms": elapsed * 1000
    }
```

### Latency Profile

```
Text input
    │
    ├─→ Voice selection: 10ms
    ├─→ Model loading (cached): 5ms
    ├─→ Text → Phonemes: 15ms
    ├─→ Phoneme → Mel: 300ms
    ├─→ Mel → Waveform (HiFi-GAN): 150ms
    ├─→ Waveform → WAV: 20ms
    │
    └─→ Total: ~500ms ✓
```

---

## Monitoring & Quality Metrics

```python
class TTSMetrics:
    avg_inference_time_ms: float       # Target: <500ms
    average_mos_score: float           # Target: >4.0
    speaker_matched_percent: float     # Target: >85%
    fallback_used_percent: float       # Target: <10%
    audio_quality_errors: int          # Target: 0 per hour
```

---

## Deployment Timeline

```
Week 1-2: Deploy facebook/mms-tts-npi
          MOS 3.2/5, immediate, no training

Week 3-4: Collect 300+ hours training data from teachers
          Preprocessing, phoneme alignment

Week 5-6: Train custom VITS on GPU 8-9
          Target MOS: 4.0+

Week 7: Integration testing
        Voice selection pipeline
        k-NN matching
        Quality gates

Week 8: Production deployment
        Phase 1 → Phase 2 switch
        Monitor MOS scores
        Adjust LoRA strategies
```

---

## Future: Speaker Cloning

```
Advanced feature (Phase 3):
- Extract speaker embedding from teacher's voice
- Train fast VITS adapter on that embedding
- LIPI responds using teacher's own voice accent

Timeline: Q3 2026
Requires: Zero-shot or few-shot VITS adaptation
Benefit: Maximum personalization
```

