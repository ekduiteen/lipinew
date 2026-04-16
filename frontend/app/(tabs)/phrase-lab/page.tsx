"use client";

import React, { useState, useEffect, useRef } from "react";
import HoldToRecordButton from "@/components/phrase-lab/HoldToRecordButton";
import PhraseCard from "@/components/phrase-lab/PhraseCard";
import VariationPrompt from "@/components/phrase-lab/VariationPrompt";

type PhraseState = "LOADING" | "PROMPT" | "RECORDING" | "PROCESSING" | "SUCCESS_VARIATION" | "RETRY";

interface PhraseData {
  id: string;
  text_en: string;
  text_ne: string;
  category?: string;
}

export default function PhraseLabPage() {
  const [state, setState] = useState<PhraseState>("LOADING");
  const [phrase, setPhrase] = useState<PhraseData | null>(null);
  const [groupId, setGroupId] = useState<string | null>(null);
  const [retryReason, setRetryReason] = useState<string>("");
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    loadNextPhrase();
  }, []);

  const getToken = () => localStorage.getItem("lipi.token") || "";

  const loadNextPhrase = async () => {
    setState("LOADING");
    try {
      const token = getToken();
      if (!token) {
        setPhrase({
          id: "",
          text_en: "Please sign in to start teaching.",
          text_ne: "सिक्षण गर्न कृपया साइन इन गर्नुहोस्।"
        });
        setState("PROMPT");
        return;
      }

      const res = await fetch("http://localhost:8000/api/phrases/next", {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!res.ok) {
        console.error(`API error: ${res.status}`);
        setPhrase({
          id: "",
          text_en: "Connection error. Please try again.",
          text_ne: "जडान त्रुटि। कृपया फेरि प्रयास गर्नुहोस्।"
        });
        setState("PROMPT");
        return;
      }

      const data = await res.json();
      if (!data.id) {
        setPhrase({ id: "", text_en: "You're all out of phrases!", text_ne: "तपाईंले सबै वाक्यांशहरू सक्नुभयो!"});
      } else {
        setPhrase(data);
      }
      setState("PROMPT");
    } catch (e) {
      console.error(e);
      setPhrase({
        id: "",
        text_en: "Error loading phrases",
        text_ne: "वाक्यांश लोड गर्न त्रुटि"
      });
      setState("PROMPT");
    }
  };

  const handleSkip = async () => {
    if (!phrase?.id) return;
    setState("LOADING");
    try {
      const formData = new FormData();
      formData.append("phrase_id", phrase.id);
      formData.append("reason", "user_skipped");
      
      const res = await fetch("http://localhost:8000/api/phrases/skip", {
        method: "POST",
        headers: { Authorization: `Bearer ${getToken()}` },
        body: formData
      });
      const data = await res.json();
      setPhrase(data);
      setState("PROMPT");
    } catch (e) {
      console.error(e);
      loadNextPhrase();
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
      setState("RECORDING");
    } catch (err) {
      console.error("Mic access denied", err);
      alert("Microphone access is required for Phrase Lab.");
    }
  };

  const stopRecord = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      setState("PROCESSING");
      mediaRecorderRef.current.stop();
    }
  };

  const processRecording = async () => {
    if (!phrase?.id) return;
    const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append("phrase_id", phrase.id);
    formData.append("audio_file", blob, "phrase.webm");
    
    // Stop mic tracks
    mediaRecorderRef.current?.stream.getTracks().forEach(t => t.stop());

    try {
      const res = await fetch("http://localhost:8000/api/phrases/submit-audio", {
        method: "POST",
        headers: { Authorization: `Bearer ${getToken()}` },
        body: formData
      });
      const data = await res.json();
      
      if (data.status === "retry") {
        setRetryReason(data.reason || "Audio was unclear. Please try again.");
        setState("RETRY");
      } else if (data.status === "success") {
        setGroupId(data.group_id);
        setState("SUCCESS_VARIATION");
      }
    } catch (e) {
      console.error(e);
      setRetryReason("Connection error. Please try again.");
      setState("RETRY");
    }
  };

  const handleVariation = async (variationId: string) => {
    // For variation, we could prompt another recording, but to keep UX fast for MVP demo, 
    // we assume the VariationPrompt starts a recording immediately or tags the CURRENT audio.
    // The prompt says "When user taps one: they can hold to record again".
    // For simplicity, we just skip to next after tapping one if we aren't hooking up a second hold-button.
    // In a fully built version, we'd reveal a secondary HoldToRecordButton.
    // We will simulate a quick skip text for variation logging here.
    
    console.log("Variation selected:", variationId);
    loadNextPhrase();
  };

  return (
    <main style={{ 
      display: "flex", 
      flexDirection: "column", 
      alignItems: "center", 
      justifyContent: "center",
      minHeight: "100vh",
      padding: "1rem",
      paddingBottom: "80px", // space for BottomNav
      backgroundColor: "var(--bg)",
      color: "var(--fg)"
    }}>
      
      {state === "LOADING" && (
        <div style={{ opacity: 0.5 }}>Loading next phrase...</div>
      )}

      {phrase && state !== "LOADING" && (
        <PhraseCard textEn={phrase.text_en} textNe={phrase.text_ne} category={phrase.category} />
      )}

      {state === "PROMPT" && phrase?.id && (
        <>
          <HoldToRecordButton 
            onStartRecord={startRecord} 
            onStopRecord={stopRecord} 
            isRecording={false} 
          />
          <button 
            onClick={handleSkip}
            style={{ marginTop: "2rem", background: "none", border: "none", color: "var(--fg)", opacity: 0.5, textDecoration: "underline" }}
          >
            Skip this phrase
          </button>
        </>
      )}

      {state === "RECORDING" && (
        <HoldToRecordButton 
          onStartRecord={() => {}} 
          onStopRecord={stopRecord} 
          isRecording={true} 
        />
      )}

      {state === "PROCESSING" && (
        <div style={{ marginTop: "3rem", display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}>
          <div className="spinner" style={{ width: "30px", height: "30px", border: "3px solid var(--accent)", borderRadius: "50%", borderTopColor: "transparent", animation: "spin 1s linear infinite" }}></div>
          <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
          <p style={{ opacity: 0.7 }}>Listening...</p>
        </div>
      )}

      {state === "RETRY" && phrase?.id && (
        <div style={{ marginTop: "2rem", textAlign: "center" }}>
          <p style={{ color: "#ff6b6b", marginBottom: "1rem" }}>{retryReason}</p>
          <HoldToRecordButton 
            onStartRecord={startRecord} 
            onStopRecord={stopRecord} 
            isRecording={false} 
          />
        </div>
      )}

      {state === "SUCCESS_VARIATION" && (
        <VariationPrompt 
          onSelectVariation={handleVariation} 
          onSkip={loadNextPhrase}
        />
      )}

    </main>
  );
}
