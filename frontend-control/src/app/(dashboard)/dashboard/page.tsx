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

  const fetchStats = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/ctrl/system/stats/timeseries", {
        params: { dialect, register }
      });
      setStats(data);
      
      const { data: summaryData } = await api.get("/ctrl/system/stats/summary");
      setSummary(summaryData);
    } catch (err) {
      console.error("Failed to fetch stats", err);
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
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-xl font-bold text-white">Daily Acquisition Yield</h2>
            <button className="text-indigo-400 text-sm font-medium flex items-center gap-1 hover:text-indigo-300">
              Full Report <ArrowUpRight size={14} />
            </button>
          </div>
          <div className="h-72">
            {loading ? (
              <div className="h-full flex items-center justify-center">
                <Loader2 className="animate-spin text-slate-800" size={32} />
              </div>
            ) : (
              <YieldAreaChart data={stats} />
            )}
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-xl font-bold text-white">Moderation Throughput</h2>
            <div className="px-3 py-1 bg-indigo-500/10 text-indigo-400 text-[10px] font-bold rounded-full uppercase tracking-widest">
              Live Feed
            </div>
          </div>
          <div className="h-72">
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
    </div>
  );
}
