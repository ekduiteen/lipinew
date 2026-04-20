// orb.jsx — LIPI's presence. WebGL-ish radial gradient blob + SVG displacement
// + canvas amplitude rings. Four states: idle, listening, thinking, speaking.

const { useEffect, useRef, useState } = React;

function useFakeAmplitude(state) {
  const [amp, setAmp] = useState(0.3);
  useEffect(() => {
    let raf;
    let t = 0;
    const tick = () => {
      t += 0.08;
      let target;
      if (state === 'speaking') {
        target = 0.55 + Math.sin(t * 1.7) * 0.2 + Math.sin(t * 4.2) * 0.15 + (Math.random() - 0.5) * 0.12;
      } else if (state === 'listening') {
        target = 0.32 + Math.sin(t * 0.8) * 0.06 + (Math.random() - 0.5) * 0.2;
      } else if (state === 'thinking') {
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

function Orb({ state = 'idle', size = 260, theme, subdued = false }) {
  const amp = useFakeAmplitude(state);
  const canvasRef = useRef(null);
  const id = useRef(`orb-${Math.random().toString(36).slice(2, 9)}`).current;

  // Rings canvas for speaking / listening
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);
    let raf, t = 0;
    const draw = () => {
      ctx.clearRect(0, 0, size, size);
      const cx = size / 2, cy = size / 2;

      if (state === 'listening') {
        // three expanding rings
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
      } else if (state === 'speaking') {
        // amplitude bars radiating outward (subtle)
        const bars = 56;
        for (let i = 0; i < bars; i++) {
          const a = (i / bars) * Math.PI * 2;
          const wave = Math.sin(t * 8 + i * 0.7) * 0.5 + 0.5;
          const len = 6 + wave * 18 * amp;
          const rIn = size / 2 - 4;
          const rOut = rIn + len;
          ctx.beginPath();
          ctx.moveTo(cx + Math.cos(a) * rIn, cy + Math.sin(a) * rIn);
          ctx.lineTo(cx + Math.cos(a) * rOut, cy + Math.sin(a) * rOut);
          ctx.strokeStyle = hexToRgba(theme.orbA, 0.3 + wave * 0.25);
          ctx.lineWidth = 1.5;
          ctx.lineCap = 'round';
          ctx.stroke();
        }
      } else if (state === 'thinking') {
        // single rotating arc
        ctx.beginPath();
        const startA = t * 2;
        ctx.arc(cx, cy, size / 2 - 4, startA, startA + Math.PI * 0.6);
        ctx.strokeStyle = hexToRgba(theme.orbA, 0.55);
        ctx.lineWidth = 1.8;
        ctx.lineCap = 'round';
        ctx.stroke();
      }
      t += 0.012;
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [state, size, theme, amp]);

  const scale = state === 'speaking' ? 1 + amp * 0.06
              : state === 'listening' ? 1 + amp * 0.03
              : state === 'thinking' ? 0.96
              : 1 + Math.sin(Date.now() / 1400) * 0.02;

  const glowOpacity = subdued ? 0.4 : 1;

  return (
    <div style={{
      position: 'relative', width: size, height: size,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      filter: subdued ? 'none' : `drop-shadow(0 0 ${40 + amp * 40}px ${theme.orbGlow})`,
      transition: 'filter 400ms ease',
    }}>
      <svg width="0" height="0" style={{ position: 'absolute' }}>
        <defs>
          <filter id={`${id}-noise`}>
            <feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="2" seed={state === 'thinking' ? 3 : 1}>
              <animate attributeName="baseFrequency" dur="22s" values="0.010;0.018;0.010" repeatCount="indefinite"/>
            </feTurbulence>
            <feDisplacementMap in="SourceGraphic" scale={state === 'speaking' ? 28 : state === 'thinking' ? 22 : 16}/>
          </filter>
          <radialGradient id={`${id}-grad`} cx="35%" cy="30%" r="70%">
            <stop offset="0%" stopColor={theme.orbC} stopOpacity="1"/>
            <stop offset="45%" stopColor={theme.orbA} stopOpacity="1"/>
            <stop offset="100%" stopColor={theme.orbB} stopOpacity="1"/>
          </radialGradient>
          <radialGradient id={`${id}-gloss`} cx="30%" cy="22%" r="40%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.65"/>
            <stop offset="60%" stopColor="#ffffff" stopOpacity="0.1"/>
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0"/>
          </radialGradient>
        </defs>
      </svg>

      {/* outer glow halo */}
      <div style={{
        position: 'absolute', inset: -size * 0.2,
        background: `radial-gradient(circle, ${hexToRgba(theme.orbA, 0.35 * glowOpacity)} 0%, transparent 55%)`,
        filter: 'blur(24px)',
        transition: 'opacity 400ms ease',
        opacity: state === 'idle' ? 0.7 : 1,
      }} />

      {/* rings canvas */}
      <canvas ref={canvasRef} style={{
        position: 'absolute', width: size, height: size,
        pointerEvents: 'none',
      }} />

      {/* the blob */}
      <div style={{
        width: size * 0.78, height: size * 0.78,
        borderRadius: '50%',
        transform: `scale(${scale}) rotate(${state === 'thinking' ? Date.now() / 40 : 0}deg)`,
        transition: 'transform 80ms linear',
      }}>
        <svg width="100%" height="100%" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="46" fill={`url(#${id}-grad)`} filter={`url(#${id}-noise)`}/>
          <circle cx="50" cy="50" r="46" fill={`url(#${id}-gloss)`}/>
        </svg>
      </div>
    </div>
  );
}

function hexToRgba(hex, a) {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
}

Object.assign(window, { Orb, useFakeAmplitude, hexToRgba });
