"use client";
import React from "react";

interface HoldToRecordButtonProps {
  onStartRecord: () => void;
  onStopRecord: () => void;
  isRecording: boolean;
  disabled?: boolean;
}

export default function HoldToRecordButton({ onStartRecord, onStopRecord, isRecording, disabled }: HoldToRecordButtonProps) {
  // We use touch events for mobile readiness, and mouse events for desktop testing
  return (
    <div 
      style={{
        display: "flex", 
        flexDirection: "column", 
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
        userSelect: "none"
      }}
    >
      <button
        onPointerDown={(e) => {
          if (disabled) return;
          // Prevent default to stop scrolling or text selection on mobile hold
          e.currentTarget.setPointerCapture(e.pointerId);
          onStartRecord();
        }}
        onPointerUp={(e) => {
          if (disabled) return;
          e.currentTarget.releasePointerCapture(e.pointerId);
          onStopRecord();
        }}
        onPointerCancel={() => {
          if (disabled) return;
          onStopRecord();
        }}
        onContextMenu={(e) => e.preventDefault()} // Prevents right-click menu popping up on long press
        style={{
          width: "120px",
          height: "120px",
          borderRadius: "60px",
          backgroundColor: isRecording ? "var(--accent)" : "var(--bg)",
          border: `4px solid ${isRecording ? "var(--accent)" : "var(--fg)"}`,
          color: isRecording ? "var(--bg)" : "var(--fg)",
          fontSize: "3rem",
          cursor: disabled ? "not-allowed" : "pointer",
          transition: "all 0.2s ease",
          transform: isRecording ? "scale(1.1)" : "scale(1)",
          boxShadow: isRecording ? "0 0 20px var(--accent)" : "none",
          display: "flex",
          alignItems: "center", 
          justifyContent: "center",
          opacity: disabled ? 0.5 : 1
        }}
        disabled={disabled}
      >
        {isRecording ? "🎙️" : "🎤"}
      </button>
      <p style={{ marginTop: "1.5rem", opacity: 0.7, fontSize: "0.9rem", color: "var(--fg)" }}>
        {isRecording ? "Release to Send" : "Hold to Record"}
      </p>
    </div>
  );
}
