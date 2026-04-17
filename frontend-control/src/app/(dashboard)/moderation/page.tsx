"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Filter,
  Loader2,
  Microscope,
  Settings2,
  SkipForward,
  Tag,
  XCircle,
} from "lucide-react";
import api from "@/lib/api";
import { AudioWaveform } from "@/components/moderation/AudioWaveform";

interface ReviewItem {
  id: string;
  audio_url: string | null;
  transcript: string;
  extracted_claim: string;
  confidence: number;
  teacher_hometown?: string;
  teacher_credibility?: number;
  review_type: string;
  source_type: string;
  language_key: string;
  model_source: string;
  supporting_teacher_count: number;
}

interface QueueResponse {
  items: ReviewItem[];
  total: number;
}

export default function ModerationPage() {
  const [currentItem, setCurrentItem] = useState<ReviewItem | null>(null);
  const [claimedBuffer, setClaimedBuffer] = useState<ReviewItem[]>([]);
  const [queuePreview, setQueuePreview] = useState<ReviewItem[]>([]);
  const [queueTotal, setQueueTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const [correction, setCorrection] = useState("");
  const [dialect, setDialect] = useState("");
  const [register, setRegister] = useState("Tapai");

  const [reviewType, setReviewType] = useState("");
  const [source, setSource] = useState("");
  const [language, setLanguage] = useState("");
  const [age, setAge] = useState("oldest");
  const [confidenceMin, setConfidenceMin] = useState("");
  const [confidenceMax, setConfidenceMax] = useState("");

  const filterParams = useMemo(() => ({
    ...(reviewType ? { review_type: reviewType } : {}),
    ...(source ? { source } : {}),
    ...(language ? { language } : {}),
    ...(confidenceMin ? { confidence_min: Number(confidenceMin) } : {}),
    ...(confidenceMax ? { confidence_max: Number(confidenceMax) } : {}),
    age,
  }), [age, confidenceMax, confidenceMin, language, reviewType, source]);

  const fetchQueuePreview = useCallback(async () => {
    const { data } = await api.get<QueueResponse>("/ctrl/moderation/queue", {
      params: { ...filterParams, claimed: "unclaimed", limit: 8 },
    });
    setQueuePreview(data.items);
    setQueueTotal(data.total);
  }, [filterParams]);

  const fillClaimedBuffer = useCallback(async (count = 3) => {
    const { data } = await api.post<{ items: ReviewItem[] }>("/ctrl/moderation/claim-buffer", null, {
      params: { ...filterParams, limit: count },
    });
    return data.items;
  }, [filterParams]);

  const hydrateWorkload = useCallback(async () => {
    setLoading(true);
    try {
      const [claimedItems] = await Promise.all([
        fillClaimedBuffer(3),
        fetchQueuePreview(),
      ]);
      setCurrentItem(claimedItems[0] || null);
      setClaimedBuffer(claimedItems.slice(1));
      setCorrection(claimedItems[0]?.transcript || claimedItems[0]?.extracted_claim || "");
      setSelectedIds([]);
    } catch (error) {
      console.error("Failed to hydrate moderation workload", error);
    } finally {
      setLoading(false);
    }
  }, [fetchQueuePreview, fillClaimedBuffer]);

  const advanceToNextClaimed = useCallback(async () => {
    if (claimedBuffer.length > 0) {
      const [nextItem, ...rest] = claimedBuffer;
      setCurrentItem(nextItem);
      setClaimedBuffer(rest);
      setCorrection(nextItem.transcript || nextItem.extracted_claim || "");
      fillClaimedBuffer(1)
        .then((items) => {
          if (items.length > 0) {
            setClaimedBuffer((prev) => [...prev, ...items]);
          }
          return fetchQueuePreview();
        })
        .catch((error) => console.error("Failed to top up claimed buffer", error));
      return;
    }

    try {
      const items = await fillClaimedBuffer(1);
      const nextItem = items[0] || null;
      setCurrentItem(nextItem);
      setCorrection(nextItem?.transcript || nextItem?.extracted_claim || "");
      await fetchQueuePreview();
    } catch (error) {
      console.error("Failed to load next review item", error);
      setCurrentItem(null);
      setCorrection("");
    }
  }, [claimedBuffer, fetchQueuePreview, fillClaimedBuffer]);

  const handleApprove = async () => {
    if (!currentItem || submitting) return;
    setSubmitting(true);
    try {
      await api.post(`/ctrl/moderation/label/${currentItem.id}`, {
        corrected_transcript: correction,
        dialect: dialect || undefined,
        register: register || undefined,
        tags: ["human_verified"],
        audio_quality: 1.0,
      });
      await advanceToNextClaimed();
    } catch (error) {
      alert("Approval failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!currentItem || submitting) return;
    setSubmitting(true);
    try {
      await api.post(`/ctrl/moderation/reject/${currentItem.id}`, { reason: "Low quality / Inaudible" });
      await advanceToNextClaimed();
    } catch (error) {
      alert("Rejection failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleBatchApprove = async () => {
    if (selectedIds.length === 0 || submitting) return;
    setSubmitting(true);
    try {
      await api.post("/ctrl/moderation/batch/approve", {
        items: selectedIds.map((id) => ({ id, register, dialect })),
      });
      await hydrateWorkload();
    } catch (error) {
      alert("Batch approve failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleBatchReject = async () => {
    if (selectedIds.length === 0 || submitting) return;
    setSubmitting(true);
    try {
      await api.post("/ctrl/moderation/batch/reject", {
        ids: selectedIds,
        reason: "Batch rejection",
      });
      await hydrateWorkload();
    } catch (error) {
      alert("Batch reject failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleBatchSkip = async () => {
    if (selectedIds.length === 0 || submitting) return;
    setSubmitting(true);
    try {
      await api.post("/ctrl/moderation/batch/skip", { ids: selectedIds });
      await hydrateWorkload();
    } catch (error) {
      alert("Batch release failed");
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    hydrateWorkload();
  }, [hydrateWorkload]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      if (event.key === "a") handleApprove();
      if (event.key === "r") handleReject();
      if (event.key === "s") advanceToNextClaimed();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [advanceToNextClaimed, currentItem, correction, dialect, register, submitting]);

  const toggleSelected = (id: string) => {
    setSelectedIds((prev) => (
      prev.includes(id) ? prev.filter((value) => value !== id) : [...prev, id]
    ));
  };

  if (loading) {
    return (
      <div className="h-96 flex items-center justify-center">
        <Loader2 className="animate-spin text-indigo-500" size={40} />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Moderation Queue</h1>
          <p className="text-slate-500 text-sm mt-1">
            Claimed buffer: {1 + claimedBuffer.length} item(s) loaded, {queueTotal} pending in filtered queue
          </p>
        </div>
        <button
          onClick={hydrateWorkload}
          className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 text-sm font-medium hover:bg-slate-800 transition-colors"
        >
          Refresh Queue
        </button>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 grid grid-cols-1 md:grid-cols-6 gap-4">
        <div>
          <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Review Type</label>
          <select value={reviewType} onChange={(e) => setReviewType(e.target.value)} className="mt-2 w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white">
            <option value="">All</option>
            <option value="correction">Correction</option>
            <option value="low_trust_extraction">Low Trust</option>
          </select>
        </div>
        <div>
          <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Source</label>
          <select value={source} onChange={(e) => setSource(e.target.value)} className="mt-2 w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white">
            <option value="">All</option>
            <option value="human">Human</option>
            <option value="model">Model</option>
          </select>
        </div>
        <div>
          <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Language</label>
          <input value={language} onChange={(e) => setLanguage(e.target.value)} placeholder="ne" className="mt-2 w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white" />
        </div>
        <div>
          <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Conf Min</label>
          <input value={confidenceMin} onChange={(e) => setConfidenceMin(e.target.value)} placeholder="0.5" className="mt-2 w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white" />
        </div>
        <div>
          <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Conf Max</label>
          <input value={confidenceMax} onChange={(e) => setConfidenceMax(e.target.value)} placeholder="0.9" className="mt-2 w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white" />
        </div>
        <div>
          <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Age</label>
          <select value={age} onChange={(e) => setAge(e.target.value)} className="mt-2 w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white">
            <option value="oldest">Oldest First</option>
            <option value="newest">Newest First</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
        <div className="xl:col-span-3 space-y-6">
          {!currentItem ? (
            <div className="h-96 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 bg-slate-900 rounded-full flex items-center justify-center text-slate-600 mb-4">
                <CheckCircle2 size={32} />
              </div>
              <h2 className="text-xl font-bold text-white">Queue Clear</h2>
              <p className="text-slate-500 mt-2">No claimable items match the current filter.</p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white">Current Claimed Item</h2>
                  <p className="text-slate-500 text-sm mt-1">Reviewing turn {currentItem.id.slice(0, 8)}</p>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg">
                  <Settings2 size={16} className="text-slate-500" />
                  <span className="text-xs font-mono text-slate-400">
                    Confidence: {(currentItem.confidence * 100).toFixed(1)}%
                  </span>
                </div>
              </div>

              <AudioWaveform url={currentItem.audio_url || ""} />

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <SignalChip label="Type" value={currentItem.review_type} />
                <SignalChip label="Source" value={currentItem.source_type} />
                <SignalChip label="Language" value={currentItem.language_key} />
                <SignalChip label="Support" value={`${currentItem.supporting_teacher_count} teacher(s)`} />
              </div>

              <div className="space-y-4">
                <label className="block text-sm font-semibold text-slate-300">Ground Truth Transcript</label>
                <textarea
                  value={correction}
                  onChange={(e) => setCorrection(e.target.value)}
                  rows={4}
                  className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 text-xl leading-relaxed text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all font-medium"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-3">
                    <Tag size={16} className="text-indigo-400" /> Dialect
                  </label>
                  <select value={dialect} onChange={(e) => setDialect(e.target.value)} className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm">
                    <option value="">Keep Existing / Unknown</option>
                    <option value="Standard">Standard Nepali</option>
                    <option value="Kathmandu">Kathmandu Valley</option>
                    <option value="Eastern">Eastern</option>
                    <option value="Western">Western</option>
                  </select>
                </div>
                <div>
                  <label className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-3">
                    <Microscope size={16} className="text-indigo-400" /> Register
                  </label>
                  <select value={register} onChange={(e) => setRegister(e.target.value)} className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm">
                    <option value="Tapai">Tapai</option>
                    <option value="Timi">Timi</option>
                    <option value="Ta">Ta</option>
                    <option value="Hajur">Hajur</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <button onClick={handleApprove} disabled={submitting} className="h-12 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-bold flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-500/20 disabled:opacity-50">
                  <CheckCircle2 size={18} /> Approve [A]
                </button>
                <button onClick={handleReject} disabled={submitting} className="h-12 bg-slate-800 hover:bg-red-900/30 text-red-400 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-all disabled:opacity-50">
                  <XCircle size={16} /> Reject [R]
                </button>
                <button onClick={advanceToNextClaimed} disabled={submitting} className="h-12 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-all disabled:opacity-50">
                  <SkipForward size={16} /> Next [S]
                </button>
              </div>
            </>
          )}
        </div>

        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest">Filtered Queue</h3>
              <span className="text-xs font-mono text-slate-500">{selectedIds.length} selected</span>
            </div>
            <div className="space-y-3 max-h-[420px] overflow-auto pr-1">
              {queuePreview.map((item) => (
                <label key={item.id} className="block border border-slate-800 rounded-xl p-3 bg-slate-950/50">
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(item.id)}
                      onChange={() => toggleSelected(item.id)}
                      className="mt-1"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-xs font-bold text-white uppercase tracking-widest">{item.review_type}</span>
                        <span className="text-[10px] font-mono text-slate-500">{(item.confidence * 100).toFixed(0)}%</span>
                      </div>
                      <p className="text-sm text-slate-200 mt-2 line-clamp-2">{item.extracted_claim || item.transcript}</p>
                      <div className="mt-2 text-[10px] text-slate-500 flex gap-2 flex-wrap">
                        <span>{item.language_key}</span>
                        <span>{item.source_type}</span>
                        <span>{item.supporting_teacher_count} support</span>
                      </div>
                    </div>
                  </div>
                </label>
              ))}
              {queuePreview.length === 0 && (
                <div className="text-sm text-slate-600">No pending items for this filter.</div>
              )}
            </div>

            <div className="grid grid-cols-1 gap-3 mt-6">
              <button onClick={handleBatchApprove} disabled={selectedIds.length === 0 || submitting} className="h-11 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-bold disabled:opacity-50">
                Batch Approve
              </button>
              <button onClick={handleBatchReject} disabled={selectedIds.length === 0 || submitting} className="h-11 bg-slate-800 hover:bg-red-900/30 text-red-400 rounded-xl text-sm font-bold disabled:opacity-50">
                Batch Reject
              </button>
              <button onClick={handleBatchSkip} disabled={selectedIds.length === 0 || submitting} className="h-11 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-bold disabled:opacity-50">
                Release Selection
              </button>
            </div>
          </div>

          {currentItem && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Teacher Context</h3>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Hometown</span>
                <span className="text-sm font-medium text-white">{currentItem.teacher_hometown || "Unknown"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Credibility</span>
                <span className="text-xs font-mono text-indigo-400">
                  {((currentItem.teacher_credibility || 0) * 100).toFixed(0)}%
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Model Source</span>
                <span className="text-xs font-mono text-slate-400">{currentItem.model_source}</span>
              </div>
            </div>
          )}

          <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-4 flex gap-3">
            <AlertCircle size={20} className="text-amber-500 shrink-0" />
            <p className="text-xs text-amber-200/70 leading-relaxed">
              <strong>Queue Safety:</strong> current items are claimed for this moderator for a limited time.
              Batch actions are atomic and will fail if another moderator already owns a selected item.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function SignalChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3">
      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{label}</p>
      <p className="text-sm text-white mt-1">{value}</p>
    </div>
  );
}
