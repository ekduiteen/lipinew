"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Orb, { type OrbState } from "@/components/orb/Orb";
import { createSession } from "@/lib/api";
import { LipiWebSocket } from "@/lib/websocket";
import styles from "./teach.module.css";

// ─── VAD constants ────────────────────────────────────────────────────────────
const SILENCE_THRESHOLD = 0.015;   // RMS below this = silence
const SILENCE_DURATION_MS = 900;   // hold silence this long before sending
const SAMPLE_RATE = 16000;
const CHUNK_SIZE = 4096;

export default function TeachPage() {
  const [orbState, setOrbState] = useState<OrbState>("idle");
  const [amplitude, setAmplitude] = useState(0);
  const [correction, setCorrection] = useState<string | null>(null);
  const [wsReady, setWsReady] = useState(false);
  const [micReady, setMicReady] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);
  const [statusText, setStatusText] = useState("जोडिँदैछ… · Connecting…");
  const [sessionReady, setSessionReady] = useState(false);
  const [teacherSubtitle, setTeacherSubtitle] = useState("");
  const [lipiSubtitle, setLipiSubtitle] = useState("");
  const [subtitleMeta, setSubtitleMeta] = useState<string | null>(null);

  const wsRef = useRef<LipiWebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const chunksRef = useRef<Float32Array[]>([]);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const speakingRef = useRef(false);
  const correctionTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const audioQueueRef = useRef<ArrayBuffer[]>([]);
  const playingRef = useRef(false);
  const ttsActiveRef = useRef(false);
  const bootstrappedRef = useRef(false);
  const streamRef = useRef<MediaStream | null>(null);
  const socketOpenedRef = useRef(false);

  // ── Bootstrap session + WebSocket ─────────────────────────────────────────
  useEffect(() => {
    if (bootstrappedRef.current) return;
    bootstrappedRef.current = true;

    let ws: LipiWebSocket | undefined;
    let cancelled = false;

    (async () => {
      const userId = localStorage.getItem("lipi.user_id") ?? "guest";
      let sessionId: string;
      try {
        console.log("Creating session for user:", userId);
        const session = await createSession();
        console.log("Session created:", session);
        sessionId = session.session_id;
        setSessionReady(true);
        setStatusText("सत्र तयार छ · Session ready");
      } catch (error) {
        console.error("Failed to create session:", error);
        alert("Failed to create session. Please reload the page.");
        setStatusText("सत्र बनाउन सकिएन · Failed to create session");
        return;
      }

      console.log("Connecting WebSocket for session:", sessionId);
      setStatusText("लाइभ च्यानल जोड्दैछ… · Connecting live channel…");
      const handleSocketOpen = async () => {
        if (cancelled || socketOpenedRef.current) return;
        socketOpenedRef.current = true;
        console.log("WebSocket connected!");
        setWsReady(true);
        setOrbState("idle");
        setStatusText("माइक सुरु गर्न तयार · Ready to start voice");
      };

      ws = new LipiWebSocket(sessionId, userId, {
        onOpen: handleSocketOpen,
        onTranscript: (text, language, confidence) => {
          setTeacherSubtitle(text);
          const confText =
            typeof confidence === "number" ? ` · ${(confidence * 100).toFixed(0)}%` : "";
          setSubtitleMeta(`${language ?? "unknown"}${confText}`);
        },
        onToken: (text) => {
          setLipiSubtitle(text);
        },
        onTTSStart: (_text, _turn) => {
          ttsActiveRef.current = true;
          chunksRef.current = [];
          speakingRef.current = false;
          setOrbState("speaking");
          setStatusText("उत्तर दिँदैछ · Speaking");
        },
        onAudio: (wav) => {
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
        onError: (err) => {
          console.error("WebSocket error:", err);
          setOrbState("idle");
          setStatusText("लाइभ च्यानलमा समस्या आयो · Live channel error");
        },
        onClose: () => {
          console.log("WebSocket closed");
          setWsReady(false);
          if (!cancelled) setOrbState("idle");
          if (!cancelled) setStatusText("लाइभ च्यानल बन्द भयो · Live channel closed");
        },
      });

      wsRef.current = ws;
      const openPoll = setInterval(() => {
        if (cancelled) {
          clearInterval(openPoll);
          return;
        }
        if (ws?.readyState === WebSocket.OPEN) {
          clearInterval(openPoll);
          void handleSocketOpen();
        }
        if (ws?.readyState === WebSocket.CLOSED) {
          clearInterval(openPoll);
        }
      }, 250);
      setTimeout(() => {
        if (!cancelled && ws?.readyState !== WebSocket.OPEN) {
          console.error("WebSocket failed to connect after 5 seconds");
          setStatusText("लाइभ च्यानल ढिलो छ · Live channel still connecting");
        }
      }, 5000);
    })();

    return () => {
      cancelled = true;
      socketOpenedRef.current = false;
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      if (correctionTimerRef.current) clearTimeout(correctionTimerRef.current);
      processorRef.current?.disconnect();
      processorRef.current = null;
      streamRef.current?.getTracks().forEach((track) => track.stop());
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
      } catch {
        // skip corrupt frame
      }
    }
    playingRef.current = false;
    setOrbState("idle");
    if (micReady) setStatusText("सुनिरहेको छ · Listening");
  }

  // ── Microphone + VAD ──────────────────────────────────────────────────────
  async function startMic(ws: LipiWebSocket) {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: SAMPLE_RATE, channelCount: 1, echoCancellation: true },
    });
    streamRef.current = stream;

    const ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
    audioCtxRef.current = ctx;

    const source = ctx.createMediaStreamSource(stream);
    const processor = ctx.createScriptProcessor(CHUNK_SIZE, 1, 1);
    processorRef.current = processor;

    processor.onaudioprocess = (e) => {
      if (ttsActiveRef.current || playingRef.current) {
        chunksRef.current = [];
        speakingRef.current = false;
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = null;
        }
        return;
      }

      const data = e.inputBuffer.getChannelData(0);
      const rms = Math.sqrt(data.reduce((s, v) => s + v * v, 0) / data.length);

      setAmplitude(rms);

      if (rms > SILENCE_THRESHOLD) {
        // Voice detected
        if (!speakingRef.current) {
          speakingRef.current = true;
          setOrbState("listening");
          setStatusText("सुनिरहेको छ · Listening");
          chunksRef.current = [];
        }
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = null;
        }
        chunksRef.current.push(new Float32Array(data));
      } else if (speakingRef.current && !silenceTimerRef.current) {
        // Trailing silence — start countdown
        silenceTimerRef.current = setTimeout(() => {
          speakingRef.current = false;
          silenceTimerRef.current = null;
          setOrbState("thinking");
          setStatusText("सोच्दैछ · Thinking");
          flushAudio(ws);
        }, SILENCE_DURATION_MS);
      }
    };

    source.connect(processor);
    processor.connect(ctx.destination);
    setMicReady(true);
    setMicError(null);
    setStatusText("सुनिरहेको छ · Listening");
  }

  async function handleStartMic() {
    if (!wsRef.current) return;
    if (wsRef.current.readyState !== WebSocket.OPEN) {
      setMicError("Live channel is still connecting. Please try again in a moment.");
      setStatusText("लाइभ च्यानल अझै जोडिँदैछ · Live channel still connecting");
      return;
    }
    try {
      await startMic(wsRef.current);
    } catch (error) {
      console.error("Microphone startup failed:", error);
      setMicReady(false);
      setMicError("Microphone access is required for Teach mode.");
      setStatusText("माइक अनुमति चाहिन्छ · Microphone permission required");
    }
  }

  function flushAudio(ws: LipiWebSocket) {
    if (chunksRef.current.length === 0) return;
    const total = chunksRef.current.reduce((s, c) => s + c.length, 0);
    const merged = new Float32Array(total);
    let off = 0;
    for (const c of chunksRef.current) { merged.set(c, off); off += c.length; }
    chunksRef.current = [];
    // Encode as 16-bit PCM WAV and send
    ws.sendAudio(encodeWav(merged, SAMPLE_RATE));
  }

  // ── Correction overlay ────────────────────────────────────────────────────
  const showCorrection = useCallback((text: string) => {
    setCorrection(text);
    if (correctionTimerRef.current) clearTimeout(correctionTimerRef.current);
    correctionTimerRef.current = setTimeout(() => setCorrection(null), 3000);
  }, []);

  return (
    <div className={styles.root}>
      <div className={styles.orbWrap}>
        <Orb state={orbState} amplitude={amplitude} size={220} />
        <p className={styles.connecting}>{statusText}</p>
        {sessionReady && !micReady && (
          <>
            <button className={styles.startBtn} onClick={handleStartMic}>
              माइक सुरु गर्नुहोस् · Start Voice
            </button>
            {micError && <p className={styles.connecting}>{micError}</p>}
          </>
        )}
      </div>

      {/* Correction card — slides up, fades out */}
      {correction && (
        <div className={styles.correctionCard}>
          <p className={styles.correctionText}>{correction}</p>
        </div>
      )}

      <section className={styles.subtitlePanel}>
        <div className={styles.subtitleBlock}>
          <span className={styles.subtitleLabel}>तपाईं · You</span>
          <p className={styles.subtitleText}>
            {teacherSubtitle || "तपाईंको बोली यहाँ देखिनेछ · Your speech will appear here"}
          </p>
          {subtitleMeta && <span className={styles.subtitleMeta}>{subtitleMeta}</span>}
        </div>

        <div className={styles.subtitleBlock}>
          <span className={styles.subtitleLabel}>लिपि · LIPI</span>
          <p className={styles.subtitleText}>
            {lipiSubtitle || "लिपिको उत्तर यहाँ देखिनेछ · LIPI reply will appear here"}
          </p>
        </div>
      </section>
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
  view.setUint16(20, 1, true);          // PCM
  view.setUint16(22, 1, true);          // mono
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
