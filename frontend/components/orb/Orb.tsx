"use client";

import { useEffect, useRef, useState } from "react";

export type OrbState = "idle" | "listening" | "thinking" | "speaking";

interface OrbProps {
  state?: OrbState;
  /** External amplitude 0–1; if omitted, uses internal fake-amplitude animation */
  amplitude?: number;
  size?: number;
  subdued?: boolean;
}

interface OrbTheme {
  orbA: string;
  orbB: string;
  orbC: string;
  orbGlow: string;
}

function hexToRgba(hex: string, a: number): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
}

function useOrbTheme(): OrbTheme {
  const [theme, setTheme] = useState<OrbTheme>({
    orbA: "#C6B5F0",
    orbB: "#B6D6F5",
    orbC: "#F3DFA8",
    orbGlow: "rgba(198,181,240,0.45)",
  });

  useEffect(() => {
    const read = () => {
      const s = getComputedStyle(document.documentElement);
      setTheme({
        orbA:    s.getPropertyValue("--orb-a").trim()    || "#C6B5F0",
        orbB:    s.getPropertyValue("--orb-b").trim()    || "#B6D6F5",
        orbC:    s.getPropertyValue("--orb-c").trim()    || "#F3DFA8",
        orbGlow: s.getPropertyValue("--orb-glow").trim() || "rgba(198,181,240,0.45)",
      });
    };
    read();
    const observer = new MutationObserver(read);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    return () => observer.disconnect();
  }, []);

  return theme;
}

function useFakeAmplitude(state: OrbState): number {
  const [amp, setAmp] = useState(0.3);

  useEffect(() => {
    let raf: number;
    let t = 0;
    const tick = () => {
      t += 0.08;
      let target: number;
      if (state === "speaking") {
        target =
          0.55 +
          Math.sin(t * 1.7) * 0.2 +
          Math.sin(t * 4.2) * 0.15 +
          (Math.random() - 0.5) * 0.12;
      } else if (state === "listening") {
        target = 0.32 + Math.sin(t * 0.8) * 0.06 + (Math.random() - 0.5) * 0.2;
      } else if (state === "thinking") {
        target = 0.25 + Math.sin(t * 0.4) * 0.05;
      } else {
        target = 0.22 + Math.sin(t * 0.3) * 0.04;
      }
      setAmp(Math.max(0.1, Math.min(1, target)));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [state]);

  return amp;
}

export default function Orb({
  state = "idle",
  amplitude,
  size = 260,
  subdued = false,
}: OrbProps) {
  const theme = useOrbTheme();
  const internalAmp = useFakeAmplitude(state);
  const amp = amplitude ?? internalAmp;

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const idRef = useRef(`orb-${Math.random().toString(36).slice(2, 9)}`);
  const id = idRef.current;

  // Canvas: rings (listening) · bars (speaking) · arc (thinking)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    let raf: number;
    let t = 0;

    const draw = () => {
      ctx.clearRect(0, 0, size, size);
      const cx = size / 2;
      const cy = size / 2;

      if (state === "listening") {
        for (let i = 0; i < 3; i++) {
          const phase = (t + i / 3) % 1;
          const r = (size / 2 - 6) * (0.55 + phase * 0.55);
          const alpha = (1 - phase) * 0.22;
          ctx.beginPath();
          ctx.arc(cx, cy, r, 0, Math.PI * 2);
          ctx.strokeStyle = hexToRgba(theme.orbA, alpha);
          ctx.lineWidth = 1.2;
          ctx.stroke();
        }
      } else if (state === "speaking") {
        const bars = 56;
        for (let i = 0; i < bars; i++) {
          const angle = (i / bars) * Math.PI * 2;
          const wave = Math.sin(t * 8 + i * 0.7) * 0.5 + 0.5;
          const len = 6 + wave * 18 * amp;
          const rIn = size / 2 - 4;
          const rOut = rIn + len;
          ctx.beginPath();
          ctx.moveTo(cx + Math.cos(angle) * rIn, cy + Math.sin(angle) * rIn);
          ctx.lineTo(cx + Math.cos(angle) * rOut, cy + Math.sin(angle) * rOut);
          ctx.strokeStyle = hexToRgba(theme.orbA, 0.3 + wave * 0.25);
          ctx.lineWidth = 1.5;
          ctx.lineCap = "round";
          ctx.stroke();
        }
      } else if (state === "thinking") {
        const startA = t * 2;
        ctx.beginPath();
        ctx.arc(cx, cy, size / 2 - 4, startA, startA + Math.PI * 0.6);
        ctx.strokeStyle = hexToRgba(theme.orbA, 0.55);
        ctx.lineWidth = 1.8;
        ctx.lineCap = "round";
        ctx.stroke();
      }

      t += 0.012;
      raf = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(raf);
  }, [state, size, theme, amp]);

  const scale =
    state === "speaking"
      ? 1 + amp * 0.06
      : state === "listening"
      ? 1 + amp * 0.03
      : state === "thinking"
      ? 0.96
      : 1;

  const glowOpacity = subdued ? 0.4 : 1;
  const glowBlur = 40 + amp * 40;

  return (
    <div
      style={{
        position: "relative",
        width: size,
        height: size,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        filter: subdued
          ? "none"
          : `drop-shadow(0 0 ${glowBlur}px ${theme.orbGlow})`,
        transition: "filter 400ms ease",
        flexShrink: 0,
      }}
    >
      {/* SVG filter + gradient defs */}
      <svg width="0" height="0" style={{ position: "absolute" }}>
        <defs>
          <filter id={`${id}-noise`}>
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.012"
              numOctaves={2}
              seed={state === "thinking" ? 3 : 1}
            >
              <animate
                attributeName="baseFrequency"
                dur="22s"
                values="0.010;0.018;0.010"
                repeatCount="indefinite"
              />
            </feTurbulence>
            <feDisplacementMap
              in="SourceGraphic"
              scale={state === "speaking" ? 28 : state === "thinking" ? 22 : 16}
            />
          </filter>
          <radialGradient id={`${id}-grad`} cx="35%" cy="30%" r="70%">
            <stop offset="0%"   stopColor={theme.orbC} stopOpacity={1} />
            <stop offset="45%"  stopColor={theme.orbA} stopOpacity={1} />
            <stop offset="100%" stopColor={theme.orbB} stopOpacity={1} />
          </radialGradient>
          <radialGradient id={`${id}-gloss`} cx="30%" cy="22%" r="40%">
            <stop offset="0%"   stopColor="#ffffff" stopOpacity={0.65} />
            <stop offset="60%"  stopColor="#ffffff" stopOpacity={0.1}  />
            <stop offset="100%" stopColor="#ffffff" stopOpacity={0}    />
          </radialGradient>
        </defs>
      </svg>

      {/* Glow halo */}
      <div
        style={{
          position: "absolute",
          inset: -size * 0.2,
          background: `radial-gradient(circle, ${hexToRgba(theme.orbA, 0.35 * glowOpacity)} 0%, transparent 55%)`,
          filter: "blur(24px)",
          transition: "opacity 400ms ease",
          opacity: state === "idle" ? 0.7 : 1,
          pointerEvents: "none",
        }}
      />

      {/* Canvas: state-dependent overlay rings/bars/arc */}
      <canvas
        ref={canvasRef}
        style={{
          position: "absolute",
          width: size,
          height: size,
          pointerEvents: "none",
        }}
      />

      {/* Blob */}
      <div
        style={{
          width: size * 0.78,
          height: size * 0.78,
          borderRadius: "50%",
          transform: `scale(${scale})`,
          transition: "transform 80ms linear",
          flexShrink: 0,
        }}
      >
        <svg width="100%" height="100%" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="46"
            fill={`url(#${id}-grad)`}
            filter={`url(#${id}-noise)`}
          />
          <circle cx="50" cy="50" r="46" fill={`url(#${id}-gloss)`} />
        </svg>
      </div>
    </div>
  );
}
