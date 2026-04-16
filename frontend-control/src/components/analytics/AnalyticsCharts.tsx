"use client";

import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend
} from "recharts";

interface ChartProps {
  data: any[];
}

export function YieldAreaChart({ data }: ChartProps) {
  return (
    <div className="h-full w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorGold" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorRaw" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.1} />
              <stop offset="95%" stopColor="#94a3b8" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
          <XAxis 
            dataKey="date" 
            stroke="#64748b" 
            fontSize={10} 
            tickLine={false} 
            axisLine={false}
            tickFormatter={(str) => str.split("-").slice(1).join("/")}
          />
          <YAxis 
            stroke="#64748b" 
            fontSize={10} 
            tickLine={false} 
            axisLine={false} 
          />
          <Tooltip 
            contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "12px" }}
            itemStyle={{ fontSize: "12px", fontWeight: "bold" }}
          />
          <Area
            type="monotone"
            dataKey="raw"
            stroke="#94a3b8"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorRaw)"
            name="Raw Capture"
          />
          <Area
            type="monotone"
            dataKey="gold"
            stroke="#6366f1"
            strokeWidth={3}
            fillOpacity={1}
            fill="url(#colorGold)"
            name="Gold Yield"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ModerationBarChart({ data }: ChartProps) {
  return (
    <div className="h-full w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
          <XAxis 
            dataKey="date" 
            stroke="#64748b" 
            fontSize={10} 
            tickLine={false} 
            axisLine={false}
            tickFormatter={(str) => str.split("-").slice(1).join("/")}
          />
          <YAxis stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
          <Tooltip 
            contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155", borderRadius: "12px" }}
            cursor={{ fill: "#1e293b", opacity: 0.4 }}
          />
          <Legend wrapperStyle={{ fontSize: "10px", marginTop: "10px" }} />
          <Bar dataKey="gold" fill="#6366f1" radius={[4, 4, 0, 0]} name="Approved" barSize={12} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
