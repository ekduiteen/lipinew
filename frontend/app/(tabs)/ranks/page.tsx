"use client";

import { useEffect, useState } from "react";
import { getLeaderboard, type LeaderboardEntry } from "@/lib/api";

type Period = "weekly" | "monthly" | "all_time";

const PERIODS: { id: Period; ne: string; en: string }[] = [
  { id: "weekly",   ne: "साप्ताहिक", en: "Weekly" },
  { id: "monthly",  ne: "मासिक",    en: "Monthly" },
  { id: "all_time", ne: "सबै",      en: "All time" },
];

export default function RanksPage() {
  const [period, setPeriod]   = useState<Period>("weekly");
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getLeaderboard(period)
      .then(setEntries)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [period]);

  return (
    <div className="page" style={{ padding: "var(--space-8) var(--space-6) var(--space-6)", gap: "var(--space-6)" }}>

      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
        <h1 style={{ fontFamily: "var(--font-nepali)", fontSize: "var(--text-h1)", fontWeight: 700, color: "var(--fg)" }}>
          शीर्ष शिक्षकहरू
        </h1>
        <p style={{ fontFamily: "var(--font-latin)", fontSize: "var(--text-sm)", color: "var(--fg-muted)" }}>
          Top Teachers
        </p>
      </div>

      {/* Period tabs */}
      <div style={{ display: "flex", gap: "var(--space-2)" }}>
        {PERIODS.map((p) => (
          <button
            key={p.id}
            className="btn-secondary"
            style={{
              flex: 1,
              padding: "var(--space-3) var(--space-2)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "2px",
              borderColor: period === p.id ? "var(--accent)" : undefined,
              color: period === p.id ? "var(--accent)" : undefined,
            }}
            onClick={() => setPeriod(p.id)}
          >
            <span style={{ fontFamily: "var(--font-nepali)" }}>{p.ne}</span>
            <span style={{ fontFamily: "var(--font-latin)", fontSize: "0.65rem", opacity: 0.7 }}>{p.en}</span>
          </button>
        ))}
      </div>

      {/* List */}
      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "var(--space-8)" }}>
          <div className="spinner" />
        </div>
      ) : (
        <ol style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          {entries.map((e) => (
            <li
              key={e.rank}
              className="card"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--space-4)",
                padding: "var(--space-4) var(--space-5)",
                borderColor: e.rank <= 3 ? "color-mix(in srgb, var(--accent) 40%, var(--border))" : undefined,
              }}
            >
              <span style={{ width: "2rem", textAlign: "center", fontWeight: 700, color: "var(--accent)", fontSize: "1.1rem" }}>
                {e.rank <= 3 ? ["🥇", "🥈", "🥉"][e.rank - 1] : e.rank}
              </span>
              <span
                style={{
                  width: "2.25rem", height: "2.25rem", borderRadius: "50%", flexShrink: 0,
                  background: "color-mix(in srgb, var(--accent) 20%, var(--bg-elev))",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "1rem", fontWeight: 700, color: "var(--accent)",
                }}
              >
                {e.avatar_initial}
              </span>
              <span style={{ flex: 1, color: "var(--fg)", fontSize: "var(--text-sm)" }}>{e.name}</span>
              <span style={{ color: "var(--fg-muted)", fontSize: "var(--text-sm)", fontFamily: "var(--font-latin)" }}>
                {e.points.toLocaleString()} pts
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
