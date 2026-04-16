"use client";
import React from "react";

interface VariationPromptProps {
  onSelectVariation: (variationId: string) => void;
  onSkip: () => void;
}

const VARIATIONS = [
  { id: "casual", label: "Casual" },
  { id: "friendly", label: "Friendly" },
  { id: "respectful", label: "Respectful" },
  { id: "elder", label: "Elder" },
  { id: "local", label: "Local way" },
];

export default function VariationPrompt({ onSelectVariation, onSkip }: VariationPromptProps) {
  return (
    <div style={{
      display: "flex", 
      flexDirection: "column", 
      alignItems: "center",
      width: "100%",
      maxWidth: "400px",
      padding: "1rem"
    }}>
      <h3 style={{ 
        color: "var(--fg)", 
        opacity: 0.8, 
        marginBottom: "1.5rem",
        textAlign: "center"
      }}>
        Any other way people say this?
      </h3>
      
      <div style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "0.8rem",
        justifyContent: "center",
        marginBottom: "2rem"
      }}>
        {VARIATIONS.map((vr) => (
          <button
            key={vr.id}
            onClick={() => onSelectVariation(vr.id)}
            style={{
              padding: "0.6rem 1.2rem",
              borderRadius: "20px",
              backgroundColor: "transparent",
              border: "1px solid var(--fg)",
              color: "var(--fg)",
              cursor: "pointer",
              fontSize: "0.9rem",
              opacity: 0.8,
              transition: "all 0.2s"
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.1)";
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = "transparent";
            }}
          >
            {vr.label}
          </button>
        ))}
      </div>
      
      <button 
        onClick={onSkip}
        style={{
          background: "none",
          border: "none",
          color: "var(--fg)",
          opacity: 0.5,
          textDecoration: "underline",
          cursor: "pointer",
          padding: "0.5rem"
        }}
      >
        Skip, next phrase
      </button>
    </div>
  );
}
