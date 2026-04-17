"use client";

import React, { useState, useEffect } from "react";
import { 
  Filter, 
  Download,
  Calendar,
  Layers,
  Star,
  Loader2
} from "lucide-react";
import api from "@/lib/api";

export default function GoldRecordsPage() {
  const [records, setRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  
  // Filters
  const [dialect, setDialect] = useState("");
  const [qualityMin, setQualityMin] = useState(0.5);

  const fetchRecords = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/ctrl/moderation/gold", {
        params: { dialect, quality_min: qualityMin, page, page_size: 25 }
      });
      setRecords(data.records);
      setTotal(data.total);
    } catch (error) {
      console.error("Failed to fetch gold records", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecords();
  }, [page, dialect, qualityMin]);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Gold Records Browser</h1>
          <p className="text-slate-400 mt-2">Verified ground-truth training pairs for STT/TTS engine fine-tuning.</p>
        </div>
        <div className="flex items-center gap-3">
          <a href="/exports" className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold rounded-xl shadow-lg shadow-indigo-500/20 transition-all">
            <Download size={18} />
            Open Exports
          </a>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-xl px-3 py-1">
          <Filter size={16} className="text-slate-500" />
          <select 
            value={dialect}
            onChange={(e) => setDialect(e.target.value)}
            className="bg-transparent text-sm text-slate-300 focus:outline-none py-1"
          >
            <option value="">All Dialects</option>
            <option value="Standard">Standard</option>
            <option value="Kathmandu">Kathmandu</option>
            <option value="Eastern">Eastern</option>
          </select>
        </div>

        <div className="flex items-center gap-3 bg-slate-800 border border-slate-700 rounded-xl px-3 py-1">
          <Star size={16} className="text-amber-400" />
          <span className="text-xs font-bold text-slate-400">Min. Quality: {qualityMin}</span>
          <input 
            type="range" 
            min="0" 
            max="1" 
            step="0.1"
            value={qualityMin}
            onChange={(e) => setQualityMin(parseFloat(e.target.value))}
            className="w-20 accent-indigo-500"
          />
        </div>
      </div>

      {/* Records Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
        <table className="w-full text-left">
          <thead>
            <tr className="bg-slate-800/10 border-b border-slate-800">
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Training Pair</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Dialect</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Quality</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Finalized</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-right">Noise</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {loading ? (
              <tr>
                <td colSpan={5} className="px-6 py-20 text-center">
                  <Loader2 className="animate-spin text-indigo-500 mx-auto" size={32} />
                  <p className="text-slate-500 text-sm mt-4">Hydrating gold series...</p>
                </td>
              </tr>
            ) : records.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-20 text-center text-slate-600">
                  No gold records match your filters.
                </td>
              </tr>
            ) : (
              records.map((rec) => (
                <tr key={rec.id} className="hover:bg-slate-800/20 transition-colors group">
                  <td className="px-6 py-4">
                    <div className="max-w-md">
                      <p className="text-sm font-medium text-white line-clamp-2">{rec.corrected_transcript}</p>
                      <p className="text-[10px] font-mono text-slate-600 uppercase tracking-tighter mt-2">RAW STT: {rec.raw_transcript.slice(0, 30)}...</p>
                      <p className="text-[11px] text-slate-500 mt-2">Register: {rec.register || "Unknown"} • Language: {rec.primary_language}</p>
                      <p className="text-[11px] text-slate-500 mt-1">
                        Provenance: session {rec.provenance.session_id?.slice(0, 8) || "n/a"} • teacher {rec.provenance.teacher_id?.slice(0, 8) || "n/a"}
                      </p>
                      <div className="mt-2 text-[10px] text-slate-500">
                        Confidence: {rec.confidence_history?.length > 0
                          ? rec.confidence_history.map((entry: any) => `${entry.change_reason}:${Math.round(entry.new_confidence * 100)}%`).join(" • ")
                          : "no confidence history"}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2 px-2.5 py-1 bg-indigo-500/10 text-indigo-400 rounded-lg w-fit border border-indigo-500/20">
                      <Layers size={14} />
                      <span className="text-xs font-bold uppercase tracking-wide">{rec.dialect || "Unknown"}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1.5">
                      <div className="h-1.5 w-16 bg-slate-800 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-emerald-500" 
                          style={{ width: `${rec.audio_quality_score * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono text-slate-500">{(rec.audio_quality_score * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2 text-slate-500 text-xs">
                      <Calendar size={14} />
                      {new Date(rec.created_at).toLocaleDateString()}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right text-xs text-slate-500">
                    {rec.noise_level || "n/a"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Container (Simple) */}
      <div className="flex items-center justify-between text-sm text-slate-500 px-2 font-medium">
        <div>Showing {records.length} of {total} records</div>
        <div className="flex items-center gap-4">
          <button 
            disabled={page === 1}
            onClick={() => setPage(p => p - 1)}
            className="px-4 py-2 bg-slate-900 border border-slate-800 rounded-xl hover:bg-slate-800 disabled:opacity-50 transition-colors"
          >
            Previous
          </button>
          <span className="text-white font-bold">Page {page}</span>
          <button 
            disabled={records.length < 25}
            onClick={() => setPage(p => p + 1)}
            className="px-4 py-2 bg-slate-900 border border-slate-800 rounded-xl hover:bg-slate-800 disabled:opacity-50 transition-colors"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
