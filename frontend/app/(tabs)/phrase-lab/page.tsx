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
  { id: "formal",     ne: "औपचारिक",  en: "More formal" },
  { id: "casual",     ne: "आकस्मिक",  en: "More casual" },
  { id: "elder",      ne: "बुज्रुकहरू",en: "Elder way" },
  { id: "local",      ne: "स्थानीय",  en: "Local way" },
  { id: "friendly",   ne: "मित्रवत्",  en: "Friendly tone" },
];

export default function PhraseLabPage() {
  const [state, setState] = useState<PhraseState>("LOADING");
  const [phrase, setPhrase] = useState<PhraseData | null>(null);
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
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorderRef.current = mr;
      audioChunksRef.current = [];
      mr.ondataavailable = (e) => audioChunksRef.current.push(e.data);
      mr.onstop = processRecording;
      mr.start();
      setIsRecording(true);
      setState("RECORDING");
    } catch {
      alert("Microphone access required.");
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
    const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
    const fd = new FormData();
    fd.append("phrase_id", phrase.id);
    fd.append("audio_file", blob, "phrase.webm");
    mediaRecorderRef.current?.stream.getTracks().forEach((t) => t.stop());

    try {
      const res = await fetch("http://localhost:8000/api/phrases/submit-audio", {
        method: "POST",
        credentials: "include",
        body: fd,
      });
      const data = await res.json();
      if (data.status === "retry") {
        setRetryReason(data.reason || "Audio unclear. Please try again.");
        setState("RETRY");
      } else {
        setState("SUCCESS_VARIATION");
      }
    } catch {
      setRetryReason("Connection error. Please try again.");
      setState("RETRY");
    }
  };

  const handleVariation = () => loadNextPhrase();

  return (
    <div className="page" style={{ alignItems: "center", justifyContent: "center", gap: "var(--space-8)" }}>

      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: "-var(--space-4)" }}>
        <p style={{ fontFamily: "var(--font-latin)", fontSize: "var(--text-caption)", fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--fg-muted)" }}>
          Phrase Lab
        </p>
      </div>

      {/* Loading state */}
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
            <p className="lang-primary" style={{ fontSize: "var(--text-h1)" }}>
              {phrase.text_ne}
            </p>
            <p className="lang-secondary">{phrase.text_en}</p>
          </div>
        </div>
      )}

      {/* Retry message */}
      {state === "RETRY" && (
        <p style={{ color: "var(--error)", fontFamily: "var(--font-latin)", fontSize: "var(--text-sm)", textAlign: "center", maxWidth: 300 }}>
          {retryReason}
        </p>
      )}

      {/* Processing */}
      {state === "PROCESSING" && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "var(--space-3)" }}>
          <div className="spinner" />
          <p style={{ color: "var(--fg-muted)", fontFamily: "var(--font-latin)", fontSize: "var(--text-sm)" }}>
            Listening…
          </p>
        </div>
      )}

      {/* Mic button */}
      {(state === "PROMPT" || state === "RECORDING" || state === "RETRY") && phrase?.id && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "var(--space-4)" }}>
          <button
            className={`btn-mic${isRecording ? " recording" : ""}`}
            onPointerDown={(e) => {
              e.currentTarget.setPointerCapture(e.pointerId);
              startRecord();
            }}
            onPointerUp={(e) => {
              e.currentTarget.releasePointerCapture(e.pointerId);
              stopRecord();
            }}
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
        <div className="card fade-in" style={{ width: "100%", maxWidth: 420, textAlign: "center" }}>
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
