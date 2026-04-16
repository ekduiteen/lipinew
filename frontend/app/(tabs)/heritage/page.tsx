"use client";

import React, { useState, useRef } from "react";

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
      const res = await fetch("http://localhost:8000/heritage/sessions/create", {
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
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorderRef.current = mr;
      audioChunksRef.current = [];
      mr.ondataavailable = (e) => audioChunksRef.current.push(e.data);
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

    const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
    const fd = new FormData();
    fd.append("audio_file", blob, "heritage.webm");
    mediaRecorderRef.current?.stream.getTracks().forEach((t) => t.stop());

    try {
      const endpoint = stage === "PRIMARY"
        ? `http://localhost:8000/heritage/sessions/${sessionId}/submit_primary`
        : `http://localhost:8000/heritage/sessions/${sessionId}/submit_followup`;

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
      await fetch(`http://localhost:8000/heritage/sessions/${sessionId}/submit_followup`, {
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
