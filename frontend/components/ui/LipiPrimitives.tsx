"use client";

import type { CSSProperties, ReactNode } from "react";

type MonoProps = {
  children: ReactNode;
  color?: string;
  style?: CSSProperties;
};

export function Mono({ children, color = "var(--fg-muted)", style }: MonoProps) {
  return (
    <span
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: "0.65rem",
        letterSpacing: "0.14em",
        textTransform: "uppercase",
        color,
        fontWeight: 500,
        ...style,
      }}
    >
      {children}
    </span>
  );
}

type BilingualProps = {
  np: string;
  en: string;
  align?: CSSProperties["textAlign"];
  size?: "md" | "lg" | "xl";
  nowrap?: boolean;
};

const SIZE_MAP = {
  md: { np: "1.5rem", en: "0.95rem", gap: 8 },
  lg: { np: "1.95rem", en: "1rem", gap: 10 },
  xl: { np: "2.45rem", en: "1.05rem", gap: 12 },
} as const;

export function BilingualText({
  np,
  en,
  align = "left",
  size = "lg",
  nowrap = false,
}: BilingualProps) {
  const spec = SIZE_MAP[size];
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: spec.gap,
        textAlign: align,
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-nepali)",
          fontSize: spec.np,
          color: "var(--fg)",
          lineHeight: 1.3,
          letterSpacing: "-0.02em",
          whiteSpace: nowrap ? "nowrap" : "normal",
        }}
      >
        {np}
      </div>
      <div
        style={{
          fontFamily: "var(--font-sans)",
          fontSize: spec.en,
          color: "var(--fg-muted)",
          lineHeight: 1.45,
          fontStyle: "italic",
        }}
      >
        {en}
      </div>
    </div>
  );
}

type FrostPillProps = {
  children: ReactNode;
  style?: CSSProperties;
};

export function FrostPill({ children, style }: FrostPillProps) {
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: "10px 16px",
        borderRadius: "var(--radius-full)",
        background: "var(--bg-frost)",
        border: "1px solid var(--rule)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        boxShadow: "var(--shadow-subtle)",
        ...style,
      }}
    >
      {children}
    </div>
  );
}
