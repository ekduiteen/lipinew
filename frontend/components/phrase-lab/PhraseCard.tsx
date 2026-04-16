"use client";
import React from "react";

interface PhraseCardProps {
  textEn: string;
  textNe: string;
  category?: string;
}

export default function PhraseCard({ textEn, textNe, category }: PhraseCardProps) {
  return (
    <div 
      style={{
        display: "flex", 
        flexDirection: "column", 
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
        backgroundColor: "var(--bg)",
        border: "1px solid rgba(255, 255, 255, 0.1)",
        borderRadius: "16px",
        margin: "1rem",
        boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
        textAlign: "center"
      }}
    >
      {category && (
        <span style={{
          fontSize: "0.8rem",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          color: "var(--accent)",
          marginBottom: "1rem",
          opacity: 0.8
        }}>
          {category}
        </span>
      )}
      
      <h1 className="text-nepali" style={{
        fontSize: "2.5rem",
        color: "var(--fg)",
        marginBottom: "0.5rem",
        lineHeight: 1.3
      }}>
        {textNe}
      </h1>
      
      <h2 className="text-latin" style={{
        fontSize: "1.2rem",
        color: "var(--fg)",
        opacity: 0.7,
        fontWeight: "normal"
      }}>
        {textEn}
      </h2>
    </div>
  );
}
