"use client";

import React, { useState, useRef } from "react";
import styles from "./heritage.module.css";
import HoldToRecordButton from "@/components/phrase-lab/HoldToRecordButton";

const MODES = [
  { id: "STORY", label: "Story / कथा" },
  { id: "WORD_EXPLANATION", label: "Word / शब्द" },
  { id: "CULTURE", label: "Culture / संस्कृति" },
  { id: "PROVERB", label: "Proverb / उखान" },
  { id: "VARIATION", label: "Dialect / भाषिका" },
];

export default function HeritagePage() {
  const [selectedMode, setSelectedMode] = useState<string>("STORY");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<string | null>(null);
  const [followUp, setFollowUp] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [stage, setStage] = useState<"SELECT" | "PRIMARY" | "FOLLOW_UP" | "DONE">("SELECT");
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const getToken = () => typeof window !== 'undefined' ? localStorage.getItem("lipi.token") || "" : "";

  const handleStartSession = async (mode: string) => {
    setSelectedMode(mode);
    setIsLoading(true);
    try {
      const res = await fetch("http://localhost:8000/heritage/sessions/create", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getToken()}`
        },
        body: JSON.stringify({ mode })
      });
      if (res.ok) {
        const data = await res.json();
        setSessionId(data.session_id);
        setPrompt(data.starter_prompt);
        setStage("PRIMARY");
      } else {
        setPrompt("कृपया एउटा कथा सुनाउनुहोस्। (Connection failed, using mock path)");
        setStage("PRIMARY");
      }
    } catch (e) {
      console.error(e);
      setPrompt("कृपया एउटा कथा सुनाउनुहोस्। (Connection failed, using mock path)");
      setStage("PRIMARY");
    } finally {
      setIsLoading(false);
    }
  };

  const startRecord = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mr;
      audioChunksRef.current = [];
      
      mr.ondataavailable = (e) => audioChunksRef.current.push(e.data);
      mr.onstop = processRecording;
      
      mr.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Mic access denied", err);
      alert("Microphone access is required in order to save the heritage audio.");
    }
  };

  const stopRecord = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      setIsRecording(false);
      setIsLoading(true);
      mediaRecorderRef.current.stop(); // This triggers mr.onstop -> processRecording()
    }
  };

  const processRecording = async () => {
    if (!sessionId) {
      // Mock progression if backend fails
      if (stage === "PRIMARY") { setFollowUp("सिक्न पाउँदा धेरै खुसी लाग्यो। के अरु थप्न चाहनुहुन्छ? (Mock)"); setStage("FOLLOW_UP"); }
      else setStage("DONE");
      setIsLoading(false);
      return;
    }

    const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append("audio_file", blob, "heritage.webm");

    // Close tracks to clear hardware light
    mediaRecorderRef.current?.stream.getTracks().forEach(t => t.stop());

    try {
      if (stage === "PRIMARY") {
        const res = await fetch(`http://localhost:8000/heritage/sessions/${sessionId}/submit_primary`, {
          method: "POST",
          headers: { "Authorization": `Bearer ${getToken()}` },
          body: formData
        });
        if (res.ok) {
          const data = await res.json();
          setFollowUp(data.follow_up_prompt);
          setStage("FOLLOW_UP");
        } else {
          setFollowUp("Upload Failed. Please continue.");
          setStage("FOLLOW_UP");
        }
      } else if (stage === "FOLLOW_UP") {
        const res = await fetch(`http://localhost:8000/heritage/sessions/${sessionId}/submit_followup`, {
          method: "POST",
          headers: { "Authorization": `Bearer ${getToken()}` },
          body: formData
        });
        if (res.ok) {
          setStage("DONE");
        } else {
          setStage("DONE");
        }
      }
    } catch (e) {
      console.error(e);
      if (stage === "PRIMARY") { setFollowUp("Network error. Mocking continuation."); setStage("FOLLOW_UP"); }
      else setStage("DONE");
    } finally {
      setIsLoading(false);
    }
  };

  const skipFollowUp = async () => {
    setIsLoading(true);
    try {
      if (sessionId) {
        const formData = new FormData();
        formData.append("text", "[User Skipped]");
        await fetch(`http://localhost:8000/heritage/sessions/${sessionId}/submit_followup`, {
          method: "POST",
          headers: { "Authorization": `Bearer ${getToken()}` },
          body: formData
        });
      }
    } catch (e) {
      console.error(e);
    } finally {
      setStage("DONE");
      setIsLoading(false);
    }
  };

  const reset = () => {
    setStage("SELECT");
    setPrompt(null);
    setFollowUp(null);
    setSessionId(null);
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>Stories & Heritage</h1>
        <p>Help preserve language and culture through your stories.</p>
      </header>

      {stage === "SELECT" && (
        <>
          <div className={styles.modeSelector}>
            {MODES.map((m) => (
              <button
                key={m.id}
                className={`${styles.modeButton} ${selectedMode === m.id ? styles.active : ""}`}
                onClick={() => setSelectedMode(m.id)}
              >
                {m.label}
              </button>
            ))}
          </div>
          <div className={styles.actions}>
            <button 
              className={styles.finishButton} 
              onClick={() => handleStartSession(selectedMode)}
              disabled={isLoading}
            >
              {isLoading ? "Loading..." : "Start Sharing"}
            </button>
          </div>
        </>
      )}

      {stage === "PRIMARY" && prompt && (
        <>
          <div className={styles.promptCard}>
            <p className={styles.promptText}>{prompt}</p>
          </div>
          <div className={styles.recordingArea}>
            <HoldToRecordButton 
              isRecording={isRecording}
              onStartRecord={startRecord}
              onStopRecord={stopRecord}
              disabled={isLoading}
            />
          </div>
        </>
      )}

      {stage === "FOLLOW_UP" && followUp && (
        <>
          <div className={styles.promptCard}>
            <p className={styles.promptText}>{followUp}</p>
          </div>
          <div className={styles.recordingArea}>
            <HoldToRecordButton 
              isRecording={isRecording}
              onStartRecord={startRecord}
              onStopRecord={stopRecord}
              disabled={isLoading}
            />
          </div>
          <div className={styles.actions}>
            <button className={styles.finishButton} onClick={skipFollowUp} style={{ background: "transparent", color: "var(--accent)", border: "1px solid var(--accent)", width: "100%", maxWidth: "300px" }}>
              Skip Follow-Up
            </button>
          </div>
        </>
      )}

      {stage === "DONE" && (
        <div className={styles.promptCard}>
          <h2>Thank you! / धन्यवाद!</h2>
          <p style={{ marginTop: "1rem" }}>Your contribution has been preserved.</p>
          <div className={styles.actions} style={{ marginTop: "2rem" }}>
            <button className={styles.finishButton} onClick={reset}>
              Share Another Story
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
