"use client";

import React, { useState, useRef } from "react";

const SAMPLE_RATE = 16000;

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

async function blobToWav(blob: Blob): Promise<Blob> {
  const arrayBuffer = await blob.arrayBuffer();
  const ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
  try {
    const decoded = await ctx.decodeAudioData(arrayBuffer);
    const mono = decoded.numberOfChannels > 1
      ? (() => {
          const out = new Float32Array(decoded.length);
          for (let ch = 0; ch < decoded.numberOfChannels; ch++) {
            const chan = decoded.getChannelData(ch);
            for (let i = 0; i < chan.length; i++) out[i] += chan[i];
          }
          for (let i = 0; i < out.length; i++) out[i] /= decoded.numberOfChannels;
          return out;
        })()
      : decoded.getChannelData(0);
    return new Blob([encodeWav(mono, SAMPLE_RATE)], { type: "audio/wav" });
  } finally {
    await ctx.close();
  }
}

const MODES = [
  { id: "STORY",            ne: "कथा",       en: "Story" },
  { id: "WORD_EXPLANATION", ne: "शब्द",       en: "Word / Phrase" },
  { id: "CULTURE",          ne: "संस्कृति",  en: "Culture" },
  { id: "PROVERB",          ne: "उखान",      en: "Proverb" },
  { id: "VARIATION",        ne: "भाषिका",    en: "Dialect" },
];

type Stage = "SELECT" | "PRIMARY" | "FOLLOW_UP" | "DONE";

export default function HeritagePage() {
  const [selectedMode, setSelectedMode] = useState<string>("STORY");
  const [sessionId, setSessionId]       = useState<string | null>(null);
  const [prompt, setPrompt]             = useState<string | null>(null);
  const [followUp, setFollowUp]         = useState<string | null>(null);
  const [isRecording, setIsRecording]   = useState(false);
  const [isLoading, setIsLoading]       = useState(false);
  const [stage, setStage]               = useState<Stage>("SELECT");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef   = useRef<Blob[]>([]);

  const handleStartSession = async (mode: string) => {
    setIsLoading(true);
    try {
      const res = await fetch("/api/heritage/sessions/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ mode }),
      });
      const data = await res.json();
      setSessionId(data.session_id ?? null);
      setPrompt(data.starter_prompt ?? defaultPrompt(mode));
      setStage("PRIMARY");
    } catch {
      setPrompt(defaultPrompt(mode));
      setStage("PRIMARY");
    } finally {
      setIsLoading(false);
    }
  };

  function defaultPrompt(mode: string) {
    const labels: Record<string, string> = {
      STORY:            "कृपया एउटा कथा सुनाउनुहोस्।",
      WORD_EXPLANATION: "कृपया एउटा शब्द वा वाक्यांश व्याख्या गर्नुहोस्।",
      CULTURE:          "कृपया एउटा सांस्कृतिक चलन वर्णन गर्नुहोस्।",
      PROVERB:          "कृपया एउटा उखान सुनाउनुहोस्।",
      VARIATION:        "कृपया यो वाक्य तपाईंको स्थानीय शैलीमा भन्नुहोस्।",
    };
    return labels[mode] ?? "कृपया सुरु गर्नुहोस्।";
  }

  const startRecord = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"]
        .find((m) => MediaRecorder.isTypeSupported(m)) ?? "";
      const mr = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = mr;
      audioChunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
      mr.onstop = processRecording;
      mr.start();
      setIsRecording(true);
    } catch {
      alert("माइक्रोफोन अनुमति आवश्यक छ। / Microphone access is required.");
    }
  };

  const stopRecord = () => {
    if (mediaRecorderRef.current?.state !== "inactive") {
      setIsRecording(false);
      setIsLoading(true);
      mediaRecorderRef.current?.stop();
    }
  };

  const processRecording = async () => {
    if (!sessionId) {
      if (stage === "PRIMARY") { setFollowUp("थप विवरण दिनुहोस्। / Please share more details."); setStage("FOLLOW_UP"); }
      else setStage("DONE");
      setIsLoading(false);
      return;
    }

    mediaRecorderRef.current?.stream.getTracks().forEach((t) => t.stop());

    // Convert browser recording (webm/ogg/mp4) → 16-bit PCM WAV
    // The ML service uses soundfile which does not support WebM
    const rawBlob = new Blob(audioChunksRef.current);
    const wavBlob = await blobToWav(rawBlob);
    const fd = new FormData();
    fd.append("audio_file", wavBlob, "heritage.wav");

    try {
      const endpoint = stage === "PRIMARY"
        ? `/api/heritage/sessions/${sessionId}/submit_primary`
        : `/api/heritage/sessions/${sessionId}/submit_followup`;

      const res = await fetch(endpoint, {
        method: "POST",
        credentials: "include",
        body: fd,
      });

      if (stage === "PRIMARY") {
        const data = res.ok ? await res.json() : {};
        setFollowUp(data.follow_up_prompt ?? "थप विवरण दिनुहोस्।");
        setStage("FOLLOW_UP");
      } else {
        setStage("DONE");
      }
    } catch {
      if (stage === "PRIMARY") { setFollowUp("नेटवर्क त्रुटि।"); setStage("FOLLOW_UP"); }
      else setStage("DONE");
    } finally {
      setIsLoading(false);
    }
  };

  const skipFollowUp = async () => {
    setIsLoading(true);
    if (sessionId) {
      const fd = new FormData();
      fd.append("text", "[User Skipped]");
      await fetch(`/api/heritage/sessions/${sessionId}/submit_followup`, {
        method: "POST",
        credentials: "include",
        body: fd,
      }).catch(() => {});
    }
    setStage("DONE");
    setIsLoading(false);
  };

  const reset = () => {
    setStage("SELECT");
    setPrompt(null);
    setFollowUp(null);
    setSessionId(null);
  };

  const currentMode = MODES.find((m) => m.id === selectedMode);

  return (
    <div className="page" style={{ alignItems: "center", justifyContent: "center", gap: "var(--space-8)" }}>

      {/* Header */}
      <div style={{ textAlign: "center" }}>
        <p style={{ fontFamily: "var(--font-latin)", fontSize: "var(--text-caption)", fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--fg-muted)" }}>
          Heritage
        </p>
        <p style={{ fontFamily: "var(--font-nepali)", fontSize: "var(--text-body)", color: "var(--fg)" }}>
          भाषा र संस्कृति जगाउनुस्
        </p>
        <p style={{ fontFamily: "var(--font-latin)", fontSize: "var(--text-sm)", color: "var(--fg-muted)" }}>
          Preserve language and culture through your voice
        </p>
      </div>

      {/* Mode selector */}
      {stage === "SELECT" && (
        <div style={{ width: "100%", maxWidth: 420, display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", justifyContent: "center" }}>
            {MODES.map((m) => (
              <button
                key={m.id}
                className={`btn-secondary${selectedMode === m.id ? " active" : ""}`}
                style={{
                  padding: "0.5rem 1.1rem",
                  fontSize: "var(--text-sm)",
                  borderColor: selectedMode === m.id ? "var(--accent)" : undefined,
                  color: selectedMode === m.id ? "var(--accent)" : undefined,
                }}
                onClick={() => setSelectedMode(m.id)}
              >
                <span style={{ fontFamily: "var(--font-nepali)" }}>{m.ne}</span>
                <span style={{ fontFamily: "var(--font-latin)", fontSize: "0.7rem", opacity: 0.7, marginLeft: "0.3rem" }}>· {m.en}</span>
              </button>
            ))}
          </div>

          <button
            className="btn-primary"
            disabled={isLoading}
            onClick={() => handleStartSession(selectedMode)}
          >
            {isLoading ? "लोड हुँदैछ…" : "सुरु गर्नुहोस् · Start sharing"}
          </button>
        </div>
      )}

      {/* Prompt card */}
      {(stage === "PRIMARY" || stage === "FOLLOW_UP") && (
        <div className="card fade-in" style={{ width: "100%", maxWidth: 420, textAlign: "center", padding: "var(--space-8) var(--space-6)" }}>
          {currentMode && (
            <div style={{ marginBottom: "var(--space-4)" }}>
              <span className="chip">{currentMode.ne} · {currentMode.en}</span>
            </div>
          )}
          <p style={{ fontFamily: "var(--font-nepali)", fontSize: "var(--text-body)", color: "var(--fg)", lineHeight: 1.7 }}>
            {stage === "PRIMARY" ? prompt : followUp}
          </p>
          {stage === "FOLLOW_UP" && (
            <p style={{ fontFamily: "var(--font-latin)", fontSize: "var(--text-sm)", color: "var(--fg-muted)", marginTop: "var(--space-2)" }}>
              Follow-up question
            </p>
          )}
        </div>
      )}

      {/* Mic control */}
      {(stage === "PRIMARY" || stage === "FOLLOW_UP") && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "var(--space-4)" }}>
          <button
            className={`btn-mic${isRecording ? " recording" : ""}`}
            disabled={isLoading}
            onPointerDown={(e) => { e.currentTarget.setPointerCapture(e.pointerId); startRecord(); }}
            onPointerUp={(e) => { e.currentTarget.releasePointerCapture(e.pointerId); stopRecord(); }}
            onPointerCancel={stopRecord}
            onContextMenu={(e) => e.preventDefault()}
          >
            {isLoading ? "⏳" : isRecording ? "🎙️" : "🎤"}
          </button>
          <p style={{ fontFamily: "var(--font-latin)", fontSize: "var(--text-sm)", color: "var(--fg-muted)" }}>
            {isLoading ? "पठाउँदैछ…" : isRecording ? "Release to send" : "Hold to record"}
          </p>

          {stage === "FOLLOW_UP" && !isRecording && !isLoading && (
            <button className="btn-text" onClick={skipFollowUp}>
              थप नसोध्नुस् · Skip follow-up
            </button>
          )}
        </div>
      )}

      {/* Done */}
      {stage === "DONE" && (
        <div className="card fade-in" style={{ width: "100%", maxWidth: 420, textAlign: "center", padding: "var(--space-8) var(--space-6)" }}>
          <p style={{ fontFamily: "var(--font-nepali)", fontSize: "var(--text-h2)", marginBottom: "var(--space-3)" }}>धन्यवाद!</p>
          <p style={{ fontFamily: "var(--font-latin)", fontSize: "var(--text-body)", color: "var(--fg-muted)", marginBottom: "var(--space-6)" }}>
            Your voice has been preserved for future generations.
          </p>
          <button className="btn-primary" onClick={reset}>
            अर्को सुनाउनुस् · Share another
          </button>
        </div>
      )}

    </div>
  );
}
