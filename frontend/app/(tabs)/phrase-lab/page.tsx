"use client";

import React, { useState, useEffect, useRef } from "react";

type PhraseState = "LOADING" | "PROMPT" | "RECORDING" | "PROCESSING" | "SUCCESS_VARIATION" | "RETRY";

interface PhraseData {
  id: string;
  text_en: string;
  text_ne: string;
  category?: string;
}

const VARIATIONS = [
  { id: "formal",   ne: "औपचारिक",   en: "More formal" },
  { id: "casual",   ne: "आकस्मिक",   en: "More casual" },
  { id: "elder",    ne: "बुज्रुकहरू", en: "Elder way" },
  { id: "local",    ne: "स्थानीय",   en: "Local way" },
  { id: "friendly", ne: "मित्रवत्",   en: "Friendly tone" },
];

const SAMPLE_RATE = 16000;

/** Encode Float32Array PCM samples → 16-bit PCM WAV ArrayBuffer */
function encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buf);
  const str = (off: number, s: string) => { for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i)); };
  str(0, "RIFF"); view.setUint32(4, 36 + samples.length * 2, true);
  str(8, "WAVE"); str(12, "fmt ");
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  str(36, "data"); view.setUint32(40, samples.length * 2, true);
  let off = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    off += 2;
  }
  return buf;
}

/** Decode any browser audio blob → 16-bit PCM WAV Blob via Web Audio API */
async function blobToWav(blob: Blob): Promise<Blob> {
  const arrayBuffer = await blob.arrayBuffer();
  const ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
  try {
    const decoded = await ctx.decodeAudioData(arrayBuffer);
    // Downmix to mono
    const mono = decoded.numberOfChannels > 1
      ? (() => {
          const out = new Float32Array(decoded.length);
          for (let ch = 0; ch < decoded.numberOfChannels; ch++) {
            const chan = decoded.getChannelData(ch);
            for (let i = 0; i < chan.length; i++) out[i] += chan[i];
          }
          const n = decoded.numberOfChannels;
          for (let i = 0; i < out.length; i++) out[i] /= n;
          return out;
        })()
      : decoded.getChannelData(0);
    const wavBuf = encodeWav(mono, SAMPLE_RATE);
    return new Blob([wavBuf], { type: "audio/wav" });
  } finally {
    await ctx.close();
  }
}

export default function PhraseLabPage() {
  const [state, setState]           = useState<PhraseState>("LOADING");
  const [phrase, setPhrase]         = useState<PhraseData | null>(null);
  const [retryReason, setRetryReason] = useState("");
  const [isRecording, setIsRecording] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef   = useRef<Blob[]>([]);

  useEffect(() => { loadNextPhrase(); }, []);

  const loadNextPhrase = async () => {
    setState("LOADING");
    try {
      const res = await fetch("http://localhost:8000/api/phrases/next", {
        credentials: "include",
      });
      const data = await res.json();
      setPhrase(data.id ? data : { id: "", text_ne: "सबै वाक्यांश सकियो", text_en: "You've taught all phrases!" });
      setState("PROMPT");
    } catch {
      setPhrase({ id: "", text_ne: "जडान भएन", text_en: "Could not connect" });
      setState("PROMPT");
    }
  };

  const handleSkip = async () => {
    if (!phrase?.id) return;
    setState("LOADING");
    try {
      const fd = new FormData();
      fd.append("phrase_id", phrase.id);
      fd.append("reason", "user_skipped");
      const res = await fetch("http://localhost:8000/api/phrases/skip", {
        method: "POST",
        credentials: "include",
        body: fd,
      });
      const data = await res.json();
      setPhrase(data);
      setState("PROMPT");
    } catch {
      loadNextPhrase();
    }
  };

  const startRecord = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Pick the best supported MIME type
      const mimeType = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"]
        .find((m) => MediaRecorder.isTypeSupported(m)) ?? "";
      const mr = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = mr;
      audioChunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
      mr.onstop = processRecording;
      mr.start();
      setIsRecording(true);
      setState("RECORDING");
    } catch {
      alert("माइक्रोफोन अनुमति आवश्यक छ। / Microphone access required.");
    }
  };

  const stopRecord = () => {
    if (mediaRecorderRef.current?.state !== "inactive") {
      setIsRecording(false);
      setState("PROCESSING");
      mediaRecorderRef.current?.stop();
    }
  };

  const processRecording = async () => {
    if (!phrase?.id) return;

    // Stop all mic tracks
    mediaRecorderRef.current?.stream.getTracks().forEach((t) => t.stop());

    const rawBlob = new Blob(audioChunksRef.current);

    try {
      // Convert whatever the browser recorded (webm/ogg/mp4) → 16-bit PCM WAV
      // soundfile on the ML service only accepts WAV/FLAC/OGG/AIFF — not WebM
      const wavBlob = await blobToWav(rawBlob);

      const fd = new FormData();
      fd.append("phrase_id", phrase.id);
      fd.append("audio_file", wavBlob, "phrase.wav");

      const res = await fetch("http://localhost:8000/api/phrases/submit-audio", {
        method: "POST",
        credentials: "include",
        body: fd,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setRetryReason(err.detail || "Server error. Please try again.");
        setState("RETRY");
        return;
      }

      const data = await res.json();
      if (data.status === "retry") {
        setRetryReason(data.reason || "Audio unclear. Please try again.");
        setState("RETRY");
      } else {
        setState("SUCCESS_VARIATION");
      }
    } catch (e) {
      console.error("processRecording error:", e);
      setRetryReason("जडान त्रुटि। कृपया फेरि प्रयास गर्नुहोस्। / Connection error. Please try again.");
      setState("RETRY");
    }
  };

  const handleVariation = () => loadNextPhrase();

  return (
    <div className="page" style={{ alignItems: "center", justifyContent: "center", gap: "var(--space-8)" }}>

      {/* Header */}
      <div style={{ textAlign: "center" }}>
        <p style={{ fontFamily: "var(--font-latin)", fontSize: "var(--text-caption)", fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--fg-muted)" }}>
          Phrase Lab
        </p>
      </div>

      {/* Loading */}
      {state === "LOADING" && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "var(--space-4)" }}>
          <div className="spinner" />
          <p style={{ color: "var(--fg-muted)", fontFamily: "var(--font-latin)", fontSize: "var(--text-sm)" }}>
            Loading next phrase…
          </p>
        </div>
      )}

      {/* Phrase card */}
      {phrase && state !== "LOADING" && (
        <div className="card fade-in" style={{ width: "100%", maxWidth: 420, textAlign: "center", padding: "var(--space-8) var(--space-6)" }}>
          {phrase.category && (
            <div style={{ marginBottom: "var(--space-5)" }}>
              <span className="chip">{phrase.category}</span>
            </div>
          )}
          <div className="bilingual">
            <p className="lang-primary" style={{ fontSize: "var(--text-h1)" }}>{phrase.text_ne}</p>
            <p className="lang-secondary">{phrase.text_en}</p>
          </div>
        </div>
      )}

      {/* Retry reason */}
      {state === "RETRY" && (
        <p style={{ color: "var(--error)", fontFamily: "var(--font-latin)", fontSize: "var(--text-sm)", textAlign: "center", maxWidth: 300 }}>
          {retryReason}
        </p>
      )}

      {/* Processing spinner */}
      {state === "PROCESSING" && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "var(--space-3)" }}>
          <div className="spinner" />
          <p style={{ color: "var(--fg-muted)", fontFamily: "var(--font-latin)", fontSize: "var(--text-sm)" }}>
            Processing…
          </p>
        </div>
      )}

      {/* Mic button */}
      {(state === "PROMPT" || state === "RECORDING" || state === "RETRY") && phrase?.id && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "var(--space-4)" }}>
          <button
            className={`btn-mic${isRecording ? " recording" : ""}`}
            onPointerDown={(e) => { e.currentTarget.setPointerCapture(e.pointerId); startRecord(); }}
            onPointerUp={(e) => { e.currentTarget.releasePointerCapture(e.pointerId); stopRecord(); }}
            onPointerCancel={stopRecord}
            onContextMenu={(e) => e.preventDefault()}
          >
            {isRecording ? "🎙️" : "🎤"}
          </button>
          <p style={{ fontFamily: "var(--font-latin)", fontSize: "var(--text-sm)", color: "var(--fg-muted)" }}>
            {isRecording ? "Release to send" : "Hold to record"}
          </p>
        </div>
      )}

      {/* Variation prompt */}
      {state === "SUCCESS_VARIATION" && (
        <div className="card fade-in" style={{ width: "100%", maxWidth: 420, textAlign: "center", padding: "var(--space-6)" }}>
          <p style={{ fontFamily: "var(--font-nepali)", fontSize: "var(--text-body)", color: "var(--fg-muted)", marginBottom: "var(--space-5)" }}>
            अर्को तरिकाले भन्न सक्नुहुन्छ?<br />
            <span style={{ fontFamily: "var(--font-latin)", fontSize: "var(--text-sm)" }}>Another way to say this?</span>
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", justifyContent: "center" }}>
            {VARIATIONS.map((v) => (
              <button
                key={v.id}
                className="btn-secondary"
                style={{ padding: "0.5rem 1rem", fontSize: "var(--text-sm)" }}
                onClick={handleVariation}
              >
                {v.ne}
              </button>
            ))}
          </div>
          <button className="btn-text" style={{ marginTop: "var(--space-5)" }} onClick={loadNextPhrase}>
            Next phrase →
          </button>
        </div>
      )}

      {/* Skip */}
      {state === "PROMPT" && phrase?.id && (
        <button className="btn-text" onClick={handleSkip}>
          Skip this phrase
        </button>
      )}

    </div>
  );
}
