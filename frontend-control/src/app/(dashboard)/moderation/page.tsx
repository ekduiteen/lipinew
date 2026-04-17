"use client";

import React, { useState, useEffect, useCallback } from "react";
import { 
  CheckCircle2, 
  XCircle, 
  SkipForward, 
  Tag, 
  AlertCircle,
  Loader2,
  Settings2,
  Microscope
} from "lucide-react";
import api from "@/lib/api";
import { AudioWaveform } from "@/components/moderation/AudioWaveform";

interface ReviewItem {
  id: string;
  audio_url: string;
  transcript: string;
  extracted_claim: string;
  confidence: number;
  teacher_hometown?: string;
  teacher_credibility?: number;
}

export default function ModerationPage() {
  const [item, setItem] = useState<ReviewItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  
  // Labeling State
  const [correction, setCorrection] = useState("");
  const [dialect, setDialect] = useState("");
  const [register, setRegister] = useState("");

  const fetchNext = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/ctrl/moderation/next");
      if (data.item) {
        setItem(data.item);
        setCorrection(data.item.transcript || data.item.extracted_claim);
      } else {
        setItem(null);
      }
    } catch (error) {
      console.error("Failed to fetch next item", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleApprove = async () => {
    if (!item || submitting) return;
    setSubmitting(true);
    try {
      await api.post(`/ctrl/moderation/label/${item.id}`, {
        corrected_transcript: correction,
        dialect: dialect || "Standard",
        register: register || "Tapai",
        tags: ["human_verified"],
        audio_quality: 1.0,
      });
      fetchNext();
    } catch (error) {
      alert("Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!item || submitting) return;
    setSubmitting(true);
    try {
      await api.post(`/ctrl/moderation/reject/${item.id}`, { reason: "Low quality / Inaudible" });
      fetchNext();
    } catch (error) {
      alert("Rejection failed");
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    fetchNext();
  }, [fetchNext]);

  // Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      
      if (e.key === "a") handleApprove();
      if (e.key === "r") handleReject();
      if (e.key === "s") fetchNext();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [item, correction, dialect, register, submitting]);

  if (loading) {
    return (
      <div className="h-96 flex items-center justify-center">
        <Loader2 className="animate-spin text-indigo-500" size={40} />
      </div>
    );
  }

  if (!item) {
    return (
      <div className="h-96 flex flex-col items-center justify-center text-center">
        <div className="w-16 h-16 bg-slate-900 rounded-full flex items-center justify-center text-slate-600 mb-4">
          <CheckCircle2 size={32} />
        </div>
        <h2 className="text-xl font-bold text-white">Queue Clear</h2>
        <p className="text-slate-500 mt-2">All pending turns have been moderated. Good job!</p>
        <button onClick={fetchNext} className="mt-6 text-indigo-400 font-medium hover:underline">Refresh Queue</button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Lead Moderation Catcher</h1>
          <p className="text-slate-500 text-sm mt-1">Reviewing turn {item.id.slice(0, 8)}</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg">
          <Settings2 size={16} className="text-slate-500" />
          <span className="text-xs font-mono text-slate-400">Confidence: {(item.confidence * 100).toFixed(1)}%</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <AudioWaveform url={item.audio_url} />

          <div className="space-y-4">
            <label className="block text-sm font-semibold text-slate-300">Ground Truth Transcript</label>
            <textarea
              value={correction}
              onChange={(e) => setCorrection(e.target.value)}
              rows={4}
              className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 text-xl leading-relaxed text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all font-medium"
            />
            <div className="flex gap-2">
              <span className="px-2 py-1 bg-slate-800 rounded text-[10px] font-mono text-slate-500">ESC: Cancel</span>
              <span className="px-2 py-1 bg-slate-800 rounded text-[10px] font-mono text-slate-500">CTRL+ENTER: Submit</span>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
            <div>
              <label className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-3">
                <Tag size={16} className="text-indigo-400" /> Dialect Label
              </label>
              <select 
                value={dialect}
                onChange={(e) => setDialect(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm"
              >
                <option value="">Auto-detected</option>
                <option value="Standard">Standard Nepali</option>
                <option value="Kathmandu">Kathmandu Valley</option>
                <option value="Eastern">Eastern (Purba)</option>
                <option value="Western">Western (Pashchim)</option>
              </select>
            </div>

            <div>
              <label className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-3">
                <Microscope size={16} className="text-indigo-400" /> Register
              </label>
              <select 
                value={register}
                onChange={(e) => setRegister(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm"
              >
                <option value="Tapai">Tapai (Respectful)</option>
                <option value="Timi">Timi (Casual)</option>
                <option value="Ta">Ta (Low)</option>
                <option value="Hajur">Hajur (High)</option>
              </select>
            </div>

            <div className="pt-4 border-t border-slate-800 space-y-3">
              <button 
                onClick={handleApprove}
                disabled={submitting}
                className="w-full h-12 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-bold flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-500/20"
              >
                <CheckCircle2 size={18} />
                Promote to Gold [A]
              </button>
              
              <div className="grid grid-cols-2 gap-3">
                <button 
                   onClick={handleReject}
                   disabled={submitting}
                   className="h-11 bg-slate-800 hover:bg-red-900/30 text-red-400 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-all"
                >
                  <XCircle size={16} />
                  Reject [R]
                </button>
                <button 
                  onClick={fetchNext}
                  disabled={submitting}
                  className="h-11 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-all"
                >
                  <SkipForward size={16} />
                  Skip [S]
                </button>
              </div>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Teacher Context</h3>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">Hometown</span>
              <span className="text-sm font-medium text-white">{item.teacher_hometown || "Unknown"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">Credibility</span>
              <div className="flex items-center gap-2">
                <div className="h-1.5 w-12 bg-slate-800 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-indigo-500" 
                    style={{ width: `${(item.teacher_credibility || 0) * 100}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-indigo-400">{((item.teacher_credibility || 0) * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>

          <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-4 flex gap-3">
            <AlertCircle size={20} className="text-amber-500 shrink-0" />
            <p className="text-xs text-amber-200/70 leading-relaxed">
              <strong>Ground Truth Note:</strong> Corrected transcripts here will directly impact the future 
              fine-tuning of the Whispered STT engine. Precision is mandatory.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
