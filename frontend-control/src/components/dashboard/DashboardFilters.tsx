"use client";

import React from "react";
import { Filter } from "lucide-react";

interface FilterProps {
  dialect: string;
  setDialect: (val: string) => void;
  register: string;
  setRegister: (val: string) => void;
}

export function DashboardFilters({ dialect, setDialect, register, setRegister }: FilterProps) {
  return (
    <div className="flex flex-wrap items-center gap-4 bg-slate-900/50 backdrop-blur-md border border-slate-800 p-4 rounded-2xl">
      <div className="flex items-center gap-2 text-slate-400 mr-2">
        <Filter size={16} />
        <span className="text-xs font-bold uppercase tracking-wider">Linguistic Filters</span>
      </div>

      <div className="space-y-1">
        <label className="text-[10px] text-slate-500 font-bold uppercase ml-1">Dialect</label>
        <select 
          value={dialect}
          onChange={(e) => setDialect(e.target.value)}
          className="bg-slate-800 border border-slate-700 text-white text-sm rounded-lg block w-full p-2 px-4 focus:ring-indigo-500 focus:border-indigo-500 appearance-none min-w-[140px]"
        >
          <option value="">All Dialects</option>
          <option value="Kathmandu">Standard (Kathmandu)</option>
          <option value="Eastern">Eastern (Koshi/Mechi)</option>
          <option value="Western">Western (Gandaki/Karnali)</option>
          <option value="Lalitpur">Patan / Lalitpur</option>
        </select>
      </div>

      <div className="space-y-1">
        <label className="text-[10px] text-slate-500 font-bold uppercase ml-1">Register</label>
        <select 
          value={register}
          onChange={(e) => setRegister(e.target.value)}
          className="bg-slate-800 border border-slate-700 text-white text-sm rounded-lg block w-full p-2 px-4 focus:ring-indigo-500 focus:border-indigo-500 appearance-none min-w-[140px]"
        >
          <option value="">All Registers</option>
          <option value="Tapai">Polite (Tapai)</option>
          <option value="Timi">Informal (Timi)</option>
          <option value="Hajur">Formal (Hajur)</option>
          <option value="Ta">Low-Register (Ta)</option>
        </select>
      </div>

      <button 
        onClick={() => { setDialect(""); setRegister(""); }}
        className="mt-5 text-xs text-slate-500 hover:text-white underline underline-offset-4"
      >
        Reset Filters
      </button>
    </div>
  );
}
