"use client";

import React, { useEffect, useState } from "react";
import { 
  MessageSquare, 
  CheckCircle2,
  Clock,
  ArrowUpRight,
  TrendingUp,
  Loader2,
  CheckCheck,
  Timer
} from "lucide-react";
import api from "@/lib/api";
import { YieldAreaChart, ModerationBarChart } from "@/components/analytics/AnalyticsCharts";
import { DashboardFilters } from "@/components/dashboard/DashboardFilters";

export default function DashboardPage() {
  const [stats, setStats] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialect, setDialect] = useState("");
  const [register, setRegister] = useState("");
  const [summary, setSummary] = useState<any>(null);
  const [intelligence, setIntelligence] = useState<any>(null);
  const [isDemo, setIsDemo] = useState(false);

  // Demo data for demonstration purposes
  const DEMO_STATS = [
    { date: "2026-04-14", raw: 145, gold: 89, language: "Nepali" },
    { date: "2026-04-15", raw: 178, gold: 112, language: "Nepali" },
    { date: "2026-04-16", raw: 162, gold: 98, language: "Newari" },
    { date: "2026-04-17", raw: 191, gold: 128, language: "Nepali" },
    { date: "2026-04-18", raw: 214, gold: 145, language: "Nepali" },
    { date: "2026-04-19", raw: 198, gold: 134, language: "Maithili" },
    { date: "2026-04-20", raw: 167, gold: 110, language: "Nepali" },
  ];

  const DEMO_SUMMARY = {
    pending_queue_size: 47,
    items_claimed: 12,
    approvals_today: 34,
    rejections_today: 5,
    avg_review_time_seconds: 240,
    low_trust_rate: 0.08,
  };

  const DEMO_INTELLIGENCE = {
    total_turns_analyzed: 1247,
    correction_intents: 156,
    teaching_intents: 342,
    avg_confidence: 0.82,
  };

  const fetchStats = async () => {
    setLoading(true);
    try {
      try {
        const { data } = await api.get("/ctrl/system/stats/timeseries", {
          params: { dialect, register }
        });
        setStats(data);
        setIsDemo(false);
      } catch (err: any) {
        // In demo mode or if endpoint not available, use demo data
        if (err?.response?.status === 401) {
          console.log("Demo mode: using sample data");
          setStats(DEMO_STATS);
          setIsDemo(true);
        } else {
          throw err;
        }
      }

      try {
        const { data: summaryData } = await api.get("/ctrl/system/stats/summary");
        setSummary(summaryData);
      } catch (err: any) {
        if (err?.response?.status === 401) {
          setSummary(DEMO_SUMMARY);
        } else if (err?.response?.status !== 401) {
          console.error("Failed to fetch summary", err);
        }
        setSummary(null);
      }

      try {
        const { data: intelligenceData } = await api.get("/ctrl/system/intelligence/overview");
        setIntelligence(intelligenceData);
      } catch (err: any) {
        if (err?.response?.status === 401) {
          setIntelligence(DEMO_INTELLIGENCE);
        } else if (err?.response?.status !== 404 && err?.response?.status !== 401) {
          console.error("Failed to fetch intelligence overview", err);
        }
        setIntelligence(null);
      }
    } catch (err) {
      console.error("Failed to fetch stats", err);
      if (stats.length === 0) {
        setStats(DEMO_STATS);
        setSummary(DEMO_SUMMARY);
        setIntelligence(DEMO_INTELLIGENCE);
        setIsDemo(true);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [dialect, register]);

  const totalRaw = stats.reduce((acc, curr) => acc + curr.raw, 0);
  const totalGold = stats.reduce((acc, curr) => acc + curr.gold, 0);

  const TOP_STATS = [
    { label: "Total Teacher Turns", value: totalRaw.toLocaleString(), icon: MessageSquare, trend: "+12%" },
    { label: "High Quality (Gold)", value: totalGold.toLocaleString(), icon: CheckCircle2, trend: "+8%" },
    { label: "Pending Review", value: summary?.pending_queue_size?.toLocaleString() || "...", icon: Clock, trend: `${summary?.items_claimed || 0} claimed` },
    { label: "Approvals Today", value: summary?.approvals_today?.toLocaleString() || "...", icon: CheckCheck, trend: `${summary?.rejections_today || 0} rejected` },
    { label: "Avg Review Time", value: summary?.avg_review_time_seconds ? `${summary.avg_review_time_seconds}s` : "...", icon: Timer, trend: `${((summary?.low_trust_rate || 0) * 100).toFixed(1)}% low-trust` },
  ];

  return (
    <div className="space-y-8">
      {stats.length === 0 && summary === null && (
        <div className="bg-amber-500/10 border border-amber-500/30 text-amber-300 px-6 py-4 rounded-xl text-sm flex items-center gap-3">
          <div className="w-2 h-2 bg-amber-500 rounded-full animate-pulse"></div>
          <span><strong>Demo Mode:</strong> Admin statistics are in read-only mode. Full analytics available with admin credentials.</span>
        </div>
      )}
      
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">System Overview</h1>
          <p className="text-slate-400 mt-2">Global data collection health and moderation throughput.</p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 text-emerald-500 rounded-xl border border-emerald-500/20 text-sm font-bold">
          <TrendingUp size={16} />
          Yield: {totalRaw > 0 ? ((totalGold / totalRaw) * 100).toFixed(1) : 0}%
        </div>
      </div>

      <DashboardFilters 
        dialect={dialect} 
        setDialect={setDialect} 
        register={register} 
        setRegister={setRegister} 
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        {TOP_STATS.map((stat) => (
          <div key={stat.label} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2.5 rounded-xl bg-slate-800 text-indigo-400">
                <stat.icon size={20} />
              </div>
              <span className={stat.trend.startsWith("+") ? "text-emerald-400 text-sm font-medium" : "text-amber-400 text-sm font-medium"}>
                {stat.trend}
              </span>
            </div>
            <h3 className="text-slate-400 text-sm font-medium">{stat.label}</h3>
            <p className="text-2xl font-bold text-white mt-1">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="min-w-0 bg-slate-900 border border-slate-800 rounded-3xl p-8">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-xl font-bold text-white">Daily Acquisition Yield</h2>
            <button className="text-indigo-400 text-sm font-medium flex items-center gap-1 hover:text-indigo-300">
              Full Report <ArrowUpRight size={14} />
            </button>
          </div>
          <div className="h-72 min-w-0">
            {loading ? (
              <div className="h-full flex items-center justify-center">
                <Loader2 className="animate-spin text-slate-800" size={32} />
              </div>
            ) : (
              <YieldAreaChart data={stats} />
            )}
          </div>
        </div>

        <div className="min-w-0 bg-slate-900 border border-slate-800 rounded-3xl p-8">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-xl font-bold text-white">Moderation Throughput</h2>
            <div className="px-3 py-1 bg-indigo-500/10 text-indigo-400 text-[10px] font-bold rounded-full uppercase tracking-widest">
              Live Feed
            </div>
          </div>
          <div className="h-72 min-w-0">
            {loading ? (
              <div className="h-full flex items-center justify-center">
                <Loader2 className="animate-spin text-slate-800" size={32} />
              </div>
            ) : (
              <ModerationBarChart data={stats} />
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8">
          <h2 className="text-xl font-bold text-white mb-6">Turn Intelligence Signals</h2>
          <div className="grid grid-cols-2 gap-4">
            <MiniMetric label="Analysed turns" value={intelligence?.analysis_count ?? "..."} />
            <MiniMetric label="Correction rate" value={intelligence ? `${(intelligence.correction_rate * 100).toFixed(1)}%` : "..."} />
            <MiniMetric label="Casual chat rate" value={intelligence ? `${(intelligence.casual_chat_rate * 100).toFixed(1)}%` : "..."} />
            <MiniMetric label="Low-signal rate" value={intelligence ? `${(intelligence.low_signal_rate * 100).toFixed(1)}%` : "..."} />
          </div>
          <div className="mt-6 text-sm text-slate-400 space-y-2">
            {intelligence?.recent_turns?.slice(0, 4).map((turn: any, index: number) => (
              <div key={`${turn.transcript}-${index}`} className="border border-slate-800 rounded-xl p-3">
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>{turn.intent_label}</span>
                  <span>{(turn.intent_confidence * 100).toFixed(0)}%</span>
                </div>
                <p className="text-slate-200 mt-2 line-clamp-2">{turn.transcript}</p>
                <p className="text-[11px] text-slate-500 mt-2">
                  keyterms: {turn.applied_keyterms?.join(", ") || "none"} | {turn.usable_for_learning ? "usable" : "blocked"}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8">
          <h2 className="text-xl font-bold text-white mb-6">Recent Entity Samples</h2>
          <div className="space-y-3 text-sm">
            {intelligence?.entity_samples?.slice(0, 8).map((entity: any, index: number) => (
              <div key={`${entity.normalized_text}-${index}`} className="border border-slate-800 rounded-xl p-3">
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>{entity.entity_type}</span>
                  <span>{((entity.confidence || 0) * 100).toFixed(0)}%</span>
                </div>
                <p className="text-slate-200 mt-2">{entity.normalized_text}</p>
                <p className="text-[11px] text-slate-500 mt-1">{entity.language || "unknown"}</p>
              </div>
            )) || <p className="text-slate-500">No entity samples yet.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

function MiniMetric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-slate-950/70 border border-slate-800 rounded-2xl p-4">
      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{label}</p>
      <p className="text-xl font-bold text-white mt-2">{value}</p>
    </div>
  );
}
