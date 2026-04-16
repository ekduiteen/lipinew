"use client";

import React, { useEffect, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";
import { Play, Pause, RotateCcw } from "lucide-react";

interface WaveformProps {
  url: string;
}

export function AudioWaveform({ url }: WaveformProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [wavesurfer, setWavesurfer] = useState<WaveSurfer | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;

    const ws = WaveSurfer.create({
      container: containerRef.current,
      waveColor: "#4f46e5",
      progressColor: "#818cf8",
      cursorColor: "#c7d2fe",
      barWidth: 2,
      barRadius: 3,
      responsive: true,
      height: 80,
      normalize: true,
    });

    ws.load(url);
    ws.on("play", () => setIsPlaying(true));
    ws.on("pause", () => setIsPlaying(false));
    ws.on("finish", () => setIsPlaying(false));

    setWavesurfer(ws);

    return () => ws.destroy();
  }, [url]);

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
      <div ref={containerRef} className="mb-4" />
      
      <div className="flex items-center gap-4">
        <button
          onClick={() => wavesurfer?.playPause()}
          className="w-10 h-10 rounded-full bg-indigo-600 text-white flex items-center justify-center hover:bg-indigo-500 transition-colors"
        >
          {isPlaying ? <Pause size={20} /> : <Play size={20} className="ml-1" />}
        </button>
        <button
          onClick={() => wavesurfer?.stop()}
          className="p-2 text-slate-400 hover:text-white transition-colors"
        >
          <RotateCcw size={20} />
        </button>
        <div className="text-xs font-mono text-slate-500">
          Space to Play/Pause
        </div>
      </div>
    </div>
  );
}
