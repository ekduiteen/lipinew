"use client";

import React, { useState, useEffect } from "react";
import { 
  Activity, 
  Database, 
  Cpu, 
  HardDrive, 
  Zap, 
  RefreshCw,
  Server,
  Cloud,
  CheckCircle,
  AlertCircle
} from "lucide-react";
import api from "@/lib/api";

export default function HealthPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/ctrl/system/health");
      setData(data);
    } catch (error) {
           console.error("Health check failed", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000); // Auto refresh every 30s
    return () => clearInterval(interval);
  }, []);

  if (loading && !data) {
    return (
      <div className="h-96 flex items-center justify-center">
        <Activity className="animate-pulse text-indigo-500" size={48} />
      </div>
    );
  }

  const services = data?.services || {};

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Infrastructure Observability</h1>
          <p className="text-slate-400 mt-2">Real-time health telemetry across the LIPI microservice graph.</p>
        </div>
        <button 
          onClick={fetchHealth}
          className="flex items-center gap-2 px-4 py-2 bg-slate-900 border border-slate-800 text-slate-300 text-sm font-bold rounded-xl hover:bg-slate-800 transition-all"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          Manual Polling
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <ServiceCard name="PostgreSQL" status={services.database} icon={Database} detail="Primary Engine" />
        <ServiceCard name="Valkey" status={services.valkey} icon={Zap} detail="Cache & Queue" />
        <ServiceCard name="MinIO" status={services.storage} icon={HardDrive} detail="Object Storage" />
        <ServiceCard name="ML Service" status={true} icon={Cpu} detail="Remote Signature" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8">
            <h2 className="text-xl font-bold text-white mb-8 flex items-center gap-3">
              <Server size={22} className="text-indigo-400" />
              Environment Specs
            </h2>
            <div className="grid grid-cols-2 gap-y-8">
              <div>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">Target Environment</p>
                <p className="text-white font-mono">{data?.config?.environment || "production"}</p>
              </div>
              <div>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">ML Service Endpoint</p>
                <p className="text-white font-mono break-all">{data?.config?.ml_service_url || "N/A"}</p>
              </div>
              <div>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">Curation Yield</p>
                <p className="text-white text-2xl font-bold">{data?.counts?.gold_records || 0} Records</p>
              </div>
              <div>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">Raw Capture Count</p>
                <p className="text-white text-2xl font-bold">{data?.counts?.raw_messages || 0} Turns</p>
              </div>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8">
            <h2 className="text-xl font-bold text-white mb-8 flex items-center gap-3">
              <Cloud size={22} className="text-indigo-400" />
              Service Facts
            </h2>
            <div className="space-y-4 text-sm text-slate-400">
              <div className="flex items-center justify-between">
                <span>Backend status</span>
                <span className="font-mono text-white">{data?.status || "unknown"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Gold records</span>
                <span className="font-mono text-white">{data?.counts?.gold_records || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Raw teacher turns</span>
                <span className="font-mono text-white">{data?.counts?.raw_messages || 0}</span>
              </div>
            </div>
            <p className="mt-8 text-xs text-slate-600 italic">This view shows live control-system health only. No synthetic log preview is rendered.</p>
          </div>
        </div>

        <div className="space-y-8">
           <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 text-center">
              <div className={`w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6 ${data?.status === "healthy" ? "bg-emerald-500/10" : "bg-amber-500/10"}`}>
                <CheckCircle size={40} className={data?.status === "healthy" ? "text-emerald-500" : "text-amber-500"} />
              </div>
              <h2 className="text-2xl font-bold text-white">{data?.status === "healthy" ? "System Healthy" : "System Degraded"}</h2>
              <p className="text-slate-500 mt-2 text-sm leading-relaxed">
                Status is derived from database, Valkey, and object-storage health checks.
              </p>
           </div>

           <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6">
              <h3 className="text-sm font-bold text-slate-500 uppercase tracking-widest mb-4">Uptime Overview</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                Historical uptime bars are disabled until the backend exposes real uptime history.
              </p>
           </div>
        </div>
      </div>
    </div>
  );
}

function ServiceCard({ name, status, icon: Icon, detail }: any) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="p-2.5 rounded-xl bg-slate-800 text-slate-400">
          <Icon size={20} />
        </div>
        <div className={`p-1.5 rounded-full ${status ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'}`}>
          {status ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
        </div>
      </div>
      <h3 className="text-slate-300 font-bold">{name}</h3>
      <p className="text-xs text-slate-500 mt-1">{detail}</p>
    </div>
  );
}
