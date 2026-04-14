"use client";

/**
 * Orb — the animated presence of LIPI.
 *
 * 4 states:
 *   idle      → slow breathing pulse, muted glow
 *   listening → rapid ring ripples, bright outer glow
 *   thinking  → rotating gradient, amber/purple blend
 *   speaking  → synchronized amplitude waves around the orb
 *
 * All animation is CSS + a tiny JS loop for the speaking waveform.
 * Colors come entirely from CSS variables (--orb-a/b/c) so themes work for free.
 */

import { useEffect, useRef } from "react";
import styles from "./Orb.module.css";

export type OrbState = "idle" | "listening" | "thinking" | "speaking";

interface OrbProps {
  state: OrbState;
  /** 0–1, only used in speaking state to scale wave amplitude */
  amplitude?: number;
  size?: number;
}

export default function Orb({ state, amplitude = 0.5, size = 200 }: OrbProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);
  const tRef = useRef(0);

  // Speaking waveform on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const r = size / 2;
    const dpr = window.devicePixelRatio ?? 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    function draw() {
      if (!ctx) return;
      ctx.clearRect(0, 0, size, size);

      if (state !== "speaking") {
        rafRef.current = requestAnimationFrame(draw);
        return;
      }

      tRef.current += 0.04;
      const rings = 3;
      for (let i = 0; i < rings; i++) {
        const phase = tRef.current + (i * Math.PI * 2) / rings;
        const radiusOffset = 18 + i * 12 + Math.sin(phase) * 8 * amplitude;
        const alpha = 0.15 + 0.2 * Math.sin(phase + 1);

        ctx.beginPath();
        ctx.arc(r, r, r - 10 + radiusOffset, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(var(--orb-a-raw, 99,102,241), ${alpha})`;
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      rafRef.current = requestAnimationFrame(draw);
    }

    draw();
    return () => cancelAnimationFrame(rafRef.current);
  }, [state, amplitude, size]);

  return (
    <div
      className={styles.wrapper}
      style={{ width: size, height: size }}
      data-state={state}
    >
      {/* Canvas for speaking rings */}
      <canvas
        ref={canvasRef}
        className={styles.canvas}
        style={{ width: size, height: size }}
      />

      {/* Core orb */}
      <div className={styles.orb} data-state={state}>
        <div className={styles.gradient} data-state={state} />
        <div className={styles.gloss} />
      </div>

      {/* Listening ripple rings */}
      {state === "listening" && (
        <>
          <div className={`${styles.ring} ${styles.ring1}`} />
          <div className={`${styles.ring} ${styles.ring2}`} />
          <div className={`${styles.ring} ${styles.ring3}`} />
        </>
      )}
    </div>
  );
}
