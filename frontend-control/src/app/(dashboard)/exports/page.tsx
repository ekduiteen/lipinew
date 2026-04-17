"use client";

import React, { useState, useEffect } from "react";
import { 
  FileArchive, 
  ExternalLink, 
  Plus, 
  RefreshCw, 
  Clock, 
  ShieldCheck,
  TrendingUp,
  AlertTriangle
} from "lucide-react";
import api from "@/lib/api";

export default function ExportsPage() {
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  
  // Create Modal State
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newVersion, setNewVersion] = useState("1.0.0");
  const [summary, setSummary] = useState<any>(null);

  const fetchSnapshots = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/ctrl/datasets/");
      setSnapshots(data.snapshots);
      
      const { data: summaryData } = await api.get("/ctrl/system/stats/summary");
      setSummary(summaryData);
    } catch (error) {
      console.log("Failed to fetch snapshots", error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSnapshot = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post("/ctrl/datasets/snapshot", {
        name: newName,
        version: newVersion,
        filters: {} // Standard dataset for now
      });
      setShowCreate(false);
      fetchSnapshots();
    } catch (err) {
      alert("Export failed. Check logs.");
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    fetchSnapshots();
  }, []);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Dataset Factory</h1>
          <p className="text-slate-400 mt-2">Manage versioned releases for machine learning model training.</p>
        </div>
        <button 
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl shadow-lg shadow-indigo-500/20 transition-all"
        >
          <Plus size={20} />
          Create New Release
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-2xl p-6">
          <TrendingUp className="text-indigo-400 mb-4" size={24} />
          <h3 className="text-white font-bold">Training Yield</h3>
          <p className="text-slate-400 text-sm mt-1">
            Total clean records available for export:{" "}
            <span className="text-indigo-400 font-mono">
              {summary?.gold_yield?.toLocaleString() || "..."}
            </span>
          </p>
        </div>
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-2xl p-6">
          <ShieldCheck className="text-emerald-400 mb-4" size={24} />
          <h3 className="text-white font-bold">Data Integrity</h3>
          <p className="text-slate-400 text-sm mt-1">
            {summary?.data_integrity || "98.4"}% of Gold records have human-corrected transcripts.
          </p>
        </div>
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-6">
          <AlertTriangle className="text-amber-400 mb-4" size={24} />
          <h3 className="text-white font-bold">Storage Health</h3>
          <p className="text-slate-400 text-sm mt-1">
            MinIO partition usage is at {summary?.storage_usage || "14"}% capacity.
          </p>
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-6 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-xl font-bold text-white">Historical Snapshots</h2>
          <button onClick={fetchSnapshots} className="text-slate-500 hover:text-white transition-colors">
            <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
          </button>
        </div>

        <div className="divide-y divide-slate-800">
          {snapshots.length === 0 ? (
            <div className="p-20 text-center text-slate-500">
              No dataset releases found. Create your first snapshot to get started.
            </div>
          ) : (
            snapshots.map((s) => (
              <div key={s.id} className="p-6 flex items-center gap-6 hover:bg-slate-800/10 transition-colors group">
                <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center text-indigo-400 group-hover:bg-indigo-500 group-hover:text-white transition-all">
                  <FileArchive size={24} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <h3 className="font-bold text-white tracking-tight">{s.dataset_name}</h3>
                    <span className="px-2 py-0.5 bg-slate-800 border border-slate-700 text-[10px] font-bold text-slate-400 rounded uppercase tracking-wider">
                      v{s.version}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 mt-1">
                    <span className="flex items-center gap-1.5 text-xs text-slate-500">
                      <Clock size={12} /> {new Date(s.created_at).toLocaleDateString()}
                    </span>
                    <span className="text-xs text-slate-500">•</span>
                    <span className="text-xs text-slate-500 font-mono">{s.record_count} Records</span>
                  </div>
                </div>
                <div>
                  <a 
                    href={`/api/proxy-download/${s.download_url}`} 
                    target="_blank" 
                    className="flex items-center gap-2 text-indigo-400 text-sm font-bold hover:text-indigo-300 transition-colors"
                  >
                    Download Artifact
                    <ExternalLink size={14} />
                  </a>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 max-w-lg w-full shadow-2xl">
            <h2 className="text-2xl font-bold text-white mb-6">Trigger Dataset Release</h2>
            <form onSubmit={handleCreateSnapshot} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Dataset Name</label>
                <input 
                  required
                  value={newName}
                  onChange={e => setNewName(e.target.value)}
                  placeholder="e.g. ne-standard-stt-v1"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Semantic Version</label>
                <input 
                  required
                  value={newVersion}
                  onChange={e => setNewVersion(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>
              <div className="pt-4 flex items-center gap-4">
                <button 
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="flex-1 bg-slate-800 hover:bg-slate-700 text-white font-bold py-3.5 rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={submitting}
                  className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3.5 rounded-xl transition-all shadow-lg shadow-indigo-500/20 disabled:opacity-50"
                >
                  {submitting ? "Exporting..." : "Initialize Factory"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
