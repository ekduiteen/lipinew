"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Orb, { type OrbState } from "@/components/orb/Orb";
import { BilingualText, FrostPill, Mono } from "@/components/ui/LipiPrimitives";
import { createSession } from "@/lib/api";
import { LipiWebSocket } from "@/lib/websocket";
import Link from "next/link";

// ─── VAD constants ────────────────────────────────────────────────────────────
const SILENCE_THRESHOLD  = 0.008;
const SILENCE_DURATION_MS = 650;
const MAX_UTTERANCE_MS   = 2400;
const SAMPLE_RATE        = 16000;

interface SubtitleEntry {
  id: number;
  text: string;
  who: "lipi" | "user";
  meta?: string;
}

function getClientCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export default function TeachPage() {
  const [orbState, setOrbState]         = useState<OrbState>("idle");
  const [amplitude, setAmplitude]       = useState(0);
  const [wsReady, setWsReady]           = useState(false);
  const [micReady, setMicReady]         = useState(false);
  const [micError, setMicError]         = useState<string | null>(null);
  const [statusText, setStatusText]     = useState("जोडिँदैछ… · Connecting…");
  const [sessionReady, setSessionReady] = useState(false);
  const [subtitles, setSubtitles]       = useState<SubtitleEntry[]>([]);
  const [learnedWord, setLearnedWord]   = useState<string | null>(null);
  const [elapsed, setElapsed]           = useState(0);

  const wsRef                 = useRef<LipiWebSocket | null>(null);
  const audioCtxRef           = useRef<AudioContext | null>(null);
  const workletNodeRef        = useRef<AudioWorkletNode | null>(null);
  const chunksRef             = useRef<Float32Array[]>([]);
  const silenceTimerRef       = useRef<ReturnType<typeof setTimeout> | null>(null);
  const maxUtteranceTimerRef  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const speakingRef           = useRef(false);
  const learnedTimerRef       = useRef<ReturnType<typeof setTimeout> | null>(null);
  const audioQueueRef         = useRef<ArrayBuffer[]>([]);
  const playingRef            = useRef(false);
  const ttsActiveRef          = useRef(false);
  const bootstrappedRef       = useRef(false);
  const streamRef             = useRef<MediaStream | null>(null);
  const socketOpenedRef       = useRef(false);
  const sessionIdRef          = useRef<string | null>(null);
  const userIdRef             = useRef<string | null>(null);
  const reconnectTimerRef     = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef  = useRef(0);

  // Elapsed timer
  useEffect(() => {
    const id = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const pushSubtitle = useCallback((text: string, who: "lipi" | "user", meta?: string) => {
    setSubtitles((prev) =>
      [{ id: Date.now() + Math.random(), text, who, meta }, ...prev].slice(0, 3)
    );
  }, []);

  const showLearned = useCallback((word: string) => {
    setLearnedWord(word);
    if (learnedTimerRef.current) clearTimeout(learnedTimerRef.current);
    learnedTimerRef.current = setTimeout(() => setLearnedWord(null), 3200);
  }, []);

  const flushCurrentAudio = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    if (silenceTimerRef.current) { clearTimeout(silenceTimerRef.current); silenceTimerRef.current = null; }
    if (maxUtteranceTimerRef.current) { clearTimeout(maxUtteranceTimerRef.current); maxUtteranceTimerRef.current = null; }
    speakingRef.current = false;
    setOrbState("thinking");
    setStatusText("पठाउँदैछ · Sending");
    flushAudio();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Bootstrap session + WebSocket ─────────────────────────────────────────
  useEffect(() => {
    if (bootstrappedRef.current) return;
    bootstrappedRef.current = true;

    let ws: LipiWebSocket | undefined;
    let cancelled = false;

    const makeCallbacks = (handleOpen: () => void) => ({
      onOpen: handleOpen,
      onTranscript: (text: string, language?: string, confidence?: number) => {
        const confText = typeof confidence === "number" ? ` · ${(confidence * 100).toFixed(0)}%` : "";
        pushSubtitle(text, "user", `${language ?? "?"}${confText}`);
        setStatusText("सोच्दैछ · Thinking");
      },
      onToken: (text: string) => {
        setSubtitles((prev) =>
          prev.length > 0 && prev[0].who === "lipi"
            ? [{ ...prev[0], text }, ...prev.slice(1)]
            : [{ id: Date.now(), text, who: "lipi" as const }, ...prev].slice(0, 3)
        );
      },
      onTTSStart: (_text: string, _turn: number) => {
        ttsActiveRef.current = true;
        chunksRef.current = [];
        speakingRef.current = false;
        setOrbState("speaking");
        setStatusText("उत्तर दिँदैछ · Speaking");
      },
      onAudio: (wav: ArrayBuffer) => {
        audioQueueRef.current.push(wav);
        if (!playingRef.current) drainQueue();
      },
      onTTSEnd: () => {
        ttsActiveRef.current = false;
        if (micReady) setStatusText("सुनिरहेको छ · Listening");
      },
      onEmptyAudio: () => {
        setOrbState("idle");
        setStatusText("अडियो आएन · No audio returned");
      },
      onError: (_err: Event) => {
        setOrbState("idle");
        setStatusText("लाइभ च्यानलमा समस्या आयो · Live channel error");
      },
      onClose: (_ev: CloseEvent) => {
        setWsReady(false);
        socketOpenedRef.current = false;
        if (cancelled) return;
        setOrbState("idle");
        const attempt = reconnectAttemptsRef.current;
        const delayMs = Math.min(1200 * Math.pow(2, attempt), 30000);
        reconnectAttemptsRef.current = attempt + 1;
        setStatusText(
          attempt < 3
            ? "लाइभ च्यानल फेरि जोड्दैछ… · Reconnecting…"
            : "लाइभ च्यानल जोड्न कठिन छ · Connection trouble — retrying…"
        );
        if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = setTimeout(() => {
          if (cancelled || !sessionIdRef.current || !userIdRef.current) return;
          const onReopen = () => {
            if (cancelled || socketOpenedRef.current) return;
            socketOpenedRef.current = true;
            reconnectAttemptsRef.current = 0;
            setWsReady(true);
            setOrbState("idle");
            setStatusText("माइक सुरु गर्न तयार · Ready to start voice");
          };
          wsRef.current = new LipiWebSocket(
            sessionIdRef.current!,
            userIdRef.current!,
            makeCallbacks(onReopen)
          );
        }, delayMs);
      },
    });

    (async () => {
      const storedUserId = localStorage.getItem("lipi.user_id");
      const cookieUserId = getClientCookie("lipi.user_id");
      const initialUserId = storedUserId ?? cookieUserId;

      if (initialUserId) {
        userIdRef.current = initialUserId;
        if (!storedUserId) {
          localStorage.setItem("lipi.user_id", initialUserId);
        }
      }

      let sessionId: string;
      try {
        const session = await createSession();
        sessionId = session.session_id;
        sessionIdRef.current = sessionId;
        userIdRef.current = session.user_id;
        localStorage.setItem("lipi.user_id", session.user_id);
        setSessionReady(true);
        setStatusText("सत्र तयार छ · Session ready");
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        if (message.includes("401")) {
          window.location.href = "/auth";
          return;
        }
        setStatusText("सत्र बनाउन सकिएन · Failed to create session — please reload");
        return;
      }

      setStatusText("लाइभ च्यानल जोड्दैछ… · Connecting live channel…");

      const handleSocketOpen = () => {
        if (cancelled || socketOpenedRef.current) return;
        socketOpenedRef.current = true;
        reconnectAttemptsRef.current = 0;
        setWsReady(true);
        setOrbState("idle");
        setStatusText("माइक सुरु गर्न तयार · Ready to start voice");
      };

      ws = new LipiWebSocket(sessionId, userIdRef.current ?? "", makeCallbacks(handleSocketOpen));
      wsRef.current = ws;

      const openPoll = setInterval(() => {
        if (cancelled) { clearInterval(openPoll); return; }
        if (ws?.readyState === WebSocket.OPEN) { clearInterval(openPoll); void handleSocketOpen(); }
        if (ws?.readyState === WebSocket.CLOSED) clearInterval(openPoll);
      }, 250);
      setTimeout(() => {
        if (!cancelled && ws?.readyState !== WebSocket.OPEN) {
          setStatusText("लाइभ च्यानल ढिलो छ · Live channel still connecting");
        }
      }, 5000);
    })();

    return () => {
      cancelled = true;
      socketOpenedRef.current = false;
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      if (maxUtteranceTimerRef.current) clearTimeout(maxUtteranceTimerRef.current);
      if (learnedTimerRef.current) clearTimeout(learnedTimerRef.current);
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      workletNodeRef.current?.disconnect();
      workletNodeRef.current = null;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      ws?.close();
      audioCtxRef.current?.close();
      audioCtxRef.current = null;
      setMicReady(false);
      setSessionReady(false);
      ttsActiveRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Audio playback queue ──────────────────────────────────────────────────
  async function drainQueue() {
    if (!audioCtxRef.current) return;
    const ctx = audioCtxRef.current;
    while (audioQueueRef.current.length > 0) {
      playingRef.current = true;
      const wav = audioQueueRef.current.shift()!;
      try {
        const decoded = await ctx.decodeAudioData(wav.slice(0));
        await new Promise<void>((resolve) => {
          const src = ctx.createBufferSource();
          src.buffer = decoded;
          src.connect(ctx.destination);
          src.onended = () => resolve();
          src.start();
        });
      } catch { /* skip corrupt frame */ }
    }
    playingRef.current = false;
    setOrbState("idle");
    if (micReady) setStatusText("सुनिरहेको छ · Listening");
  }

  // ── Microphone + VAD ──────────────────────────────────────────────────────
  async function startMic() {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: SAMPLE_RATE, channelCount: 1, echoCancellation: true },
    });
    streamRef.current = stream;
    const ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
    audioCtxRef.current = ctx;
    await ctx.resume();
    const source = ctx.createMediaStreamSource(stream);
    await ctx.audioWorklet.addModule("/workers/vocal-processor.js");
    const workletNode = new AudioWorkletNode(ctx, "vocal-processor");
    workletNodeRef.current = workletNode;
    const muteGain = ctx.createGain();
    muteGain.gain.value = 0;

    workletNode.port.onmessage = (event) => {
      const data = event.data as Float32Array;
      if (ttsActiveRef.current || playingRef.current) {
        chunksRef.current = [];
        speakingRef.current = false;
        if (silenceTimerRef.current) { clearTimeout(silenceTimerRef.current); silenceTimerRef.current = null; }
        if (maxUtteranceTimerRef.current) { clearTimeout(maxUtteranceTimerRef.current); maxUtteranceTimerRef.current = null; }
        return;
      }
      const rms = Math.sqrt(data.reduce((s, v) => s + v * v, 0) / data.length);
      setAmplitude(rms);
      if (rms > SILENCE_THRESHOLD) {
        if (!speakingRef.current) {
          speakingRef.current = true;
          setOrbState("listening");
          setStatusText("सुनिरहेको छ · Listening");
          chunksRef.current = [];
          maxUtteranceTimerRef.current = setTimeout(() => {
            speakingRef.current = false;
            maxUtteranceTimerRef.current = null;
            if (silenceTimerRef.current) { clearTimeout(silenceTimerRef.current); silenceTimerRef.current = null; }
            setOrbState("thinking");
            setStatusText("पठाउँदैछ · Sending");
            flushAudio();
          }, MAX_UTTERANCE_MS);
        }
        if (silenceTimerRef.current) { clearTimeout(silenceTimerRef.current); silenceTimerRef.current = null; }
        chunksRef.current.push(new Float32Array(data));
      } else if (speakingRef.current && !silenceTimerRef.current) {
        silenceTimerRef.current = setTimeout(() => {
          speakingRef.current = false;
          silenceTimerRef.current = null;
          if (maxUtteranceTimerRef.current) { clearTimeout(maxUtteranceTimerRef.current); maxUtteranceTimerRef.current = null; }
          setOrbState("thinking");
          setStatusText("सोच्दैछ · Thinking");
          flushAudio();
        }, SILENCE_DURATION_MS);
      }
    };

    source.connect(workletNode);
    workletNode.connect(muteGain);
    muteGain.connect(ctx.destination);
    setMicReady(true);
    setMicError(null);
    setStatusText("सुनिरहेको छ · Listening");
  }

  async function handleStartMic() {
    if (!wsRef.current) return;
    if (wsRef.current.readyState !== WebSocket.OPEN) {
      setMicError("Live channel is still connecting.");
      return;
    }
    try {
      await startMic();
    } catch {
      setMicReady(false);
      setMicError("Microphone access is required.");
      setStatusText("माइक अनुमति चाहिन्छ · Microphone permission required");
    }
  }

  function flushAudio() {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    if (chunksRef.current.length === 0) return;
    const total = chunksRef.current.reduce((s, c) => s + c.length, 0);
    const merged = new Float32Array(total);
    let off = 0;
    for (const c of chunksRef.current) { merged.set(c, off); off += c.length; }
    chunksRef.current = [];
    ws.sendAudio(encodeWav(merged, SAMPLE_RATE));
  }

  const min = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const sec = String(elapsed % 60).padStart(2, "0");

  const stateLabel =
    orbState === "listening" ? "LISTENING" :
    orbState === "thinking"  ? "THINKING"  :
    orbState === "speaking"  ? "SPEAKING"  : "READY";

  const promptCopy =
    orbState === "speaking"
      ? {
          np: "लिपि उत्तर दिँदैछ। ध्यान दिएर सुन्नुहोस्।",
          en: "LIPI is replying now. Listen for the next prompt.",
        }
      : orbState === "thinking"
      ? {
          np: "मैले सुनेको कुरा मिलाउँदैछु।",
          en: "I am aligning what I heard before responding.",
        }
      : orbState === "listening"
      ? {
          np: "अब बोल्नुहोस्। लिपिले ध्यान दिएर सुनिरहेको छ।",
          en: "Speak now. LIPI is actively listening to you.",
        }
      : {
          np: "दसैं नेपालको सबैभन्दा ठूलो पर्व हो, हैन?",
          en: "Dashain is Nepal's biggest festival, right?",
        };

  return (
    <div style={{
      position: "fixed",
      inset: 0,
      background: "var(--bg)",
      overflow: "hidden",
      display: "flex",
      flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 20px 120px",
    }}>

      {/* Top chrome */}
      <div style={{
        position: "absolute",
        top: 56,
        left: 20,
        right: 20,
        zIndex: 10,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}>
        {/* State + timer pill */}
        <FrostPill>
          <div style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: orbState === "listening" ? "#E85B5B" : "var(--fg-muted)",
          }} />
          <Mono color="var(--fg)">{stateLabel}</Mono>
          <span style={{ color: "var(--fg-subtle)" }}>·</span>
          <Mono>{min}:{sec}</Mono>
        </FrostPill>

        {/* Language indicator */}
        <FrostPill>
          <Mono>NE · ↔ · EN</Mono>
        </FrostPill>
      </div>

      <div
        style={{
          width: "100%",
          maxWidth: 640,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 32,
        }}
      >
        <Orb state={orbState} amplitude={amplitude} size={320} />

        <div
          style={{
            maxWidth: 560,
            textAlign: "center",
            display: "flex",
            flexDirection: "column",
            gap: 14,
          }}
        >
          <Mono>LIPI SAYS</Mono>
          <BilingualText
            np={promptCopy.np}
            en={promptCopy.en}
            align="center"
            size="lg"
          />
          <p
            style={{
              fontFamily: "var(--font-nepali-ui)",
              fontSize: "var(--text-sm)",
              color: "var(--fg-muted)",
              textAlign: "center",
              lineHeight: 1.6,
            }}
          >
            {statusText}
          </p>
        </div>
      </div>

      {/* LEARNED chip — rises when word captured */}
      {learnedWord && (
        <div style={{
          position: "absolute",
          top: "58%",
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "12px 18px",
          borderRadius: 16,
          background: "var(--bg-card)",
          border: "1px solid var(--rule)",
          boxShadow: "var(--shadow-float)",
          animation: "rise 300ms cubic-bezier(.4,0,.2,1) both",
        }}>
          <div style={{
            width: 28,
            height: 28,
            borderRadius: "50%",
            background: "var(--tint-sage)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 14,
          }}>
            ✓
          </div>
          <div>
            <Mono>LEARNED</Mono>
            <div style={{ fontFamily: "var(--font-nepali)", fontSize: 18, color: "var(--fg)", marginTop: 2 }}>
              {learnedWord}
            </div>
          </div>
        </div>
      )}

      {/* Subtitle stack */}
      {subtitles.length > 0 && (
        <div style={{
          position: "absolute",
          bottom: 140,
          left: 20,
          right: 20,
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}>
          {[...subtitles].reverse().map((s, i, arr) => {
            const isLatest = i === arr.length - 1;
            return (
              <div
                key={s.id}
                style={{
                  padding: "12px 16px",
                  borderRadius: 18,
                  background: s.who === "lipi" ? "var(--bg-card)" : "var(--tint-lavender)",
                  border: "1px solid var(--rule)",
                  backdropFilter: "blur(20px)",
                  opacity: isLatest ? 1 : 0.5,
                  transform: isLatest ? "scale(1)" : "scale(0.97)",
                  transition: "all 300ms ease",
                  animation: isLatest ? "rise 280ms cubic-bezier(.4,0,.2,1) both" : "none",
                  alignSelf: s.who === "lipi" ? "flex-start" : "flex-end",
                  maxWidth: "90%",
                }}
              >
                <Mono>
                  {s.who === "lipi" ? "LIPI" : "YOU"}
                  {s.meta ? ` · ${s.meta}` : ""}
                </Mono>
                <div style={{
                  fontFamily: "var(--font-nepali-ui)",
                  fontSize: 15,
                  color: "var(--fg)",
                  marginTop: 3,
                  lineHeight: 1.4,
                }}>
                  {s.text}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Bottom controls */}
      <div style={{
        position: "absolute",
        bottom: 80,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        gap: 12,
      }}>
        {/* Back */}
        <Link
          href="/home"
          style={{
            width: 48,
            height: 48,
            borderRadius: "50%",
            background: "var(--bg-card)",
            border: "1px solid var(--rule)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "var(--shadow-subtle)",
            textDecoration: "none",
            color: "var(--fg)",
          }}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M11 4L6 9l5 5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </Link>

        {/* Primary mic / stop button */}
        <button
          onClick={micReady ? flushCurrentAudio : handleStartMic}
          disabled={!sessionReady && !wsReady}
          style={{
            width: 64,
            height: 64,
            borderRadius: "50%",
            background: micReady ? "var(--accent)" : "var(--bg-card)",
            color: micReady ? "var(--accent-fg)" : "var(--fg)",
            border: micReady ? "none" : "1px solid var(--rule)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            boxShadow: micReady ? "var(--shadow-float)" : "var(--shadow-subtle)",
            transition: "all var(--duration-micro) var(--ease)",
          }}
        >
          {micReady ? (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <rect x="5" y="4" width="4" height="12" rx="1"/>
              <rect x="11" y="4" width="4" height="12" rx="1"/>
            </svg>
          ) : (
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <path d="M5 4l14 7-14 7V4z" fill="currentColor"/>
            </svg>
          )}
        </button>

        {/* Stop session */}
        <Link
          href="/home"
          style={{
            width: 48,
            height: 48,
            borderRadius: "50%",
            background: "var(--bg-card)",
            border: "1px solid var(--rule)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "var(--shadow-subtle)",
            textDecoration: "none",
            color: "var(--fg)",
          }}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <rect x="4" y="4" width="10" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.4"/>
          </svg>
        </Link>
      </div>

      {/* Mic error notice */}
      {micError && (
        <div style={{
          position: "absolute",
          bottom: 152,
          left: 20,
          right: 20,
          textAlign: "center",
          fontFamily: "var(--font-sans)",
          fontSize: "var(--text-sm)",
          color: "var(--fg-muted)",
        }}>
          {micError}
        </div>
      )}
    </div>
  );
}

// ─── WAV encoder (PCM float32 → 16-bit WAV) ──────────────────────────────────
function encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  function ws(off: number, str: string) {
    for (let i = 0; i < str.length; i++) view.setUint8(off + i, str.charCodeAt(i));
  }

  ws(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  ws(8, "WAVE");
  ws(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  ws(36, "data");
  view.setUint32(40, samples.length * 2, true);

  let off = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    off += 2;
  }

  return buffer;
}
