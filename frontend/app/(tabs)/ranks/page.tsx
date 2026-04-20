"use client";

import { useEffect, useState } from "react";
import { getLeaderboard, type LeaderboardEntry } from "@/lib/api";

type Period = "weekly" | "monthly" | "all_time";

const PERIODS: { id: Period; ne: string; en: string }[] = [
  { id: "weekly",   ne: "साप्ताहिक", en: "Week" },
  { id: "monthly",  ne: "मासिक",    en: "Month" },
  { id: "all_time", ne: "सबै",      en: "All time" },
];

const MONO: React.CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: "0.65rem",
  letterSpacing: "0.1em",
  textTransform: "uppercase",
};

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

  const top3 = entries.slice(0, 3);
  const rest  = entries.slice(3);

  return (
    <div style={{
      minHeight: "100svh",
      background: "var(--bg)",
      padding: "60px 20px 120px",
      display: "flex",
      flexDirection: "column",
      gap: 0,
      overflowY: "auto",
    }}>

      {/* Header */}
      <div>
        <span style={{ ...MONO, color: "var(--fg-muted)" }}>⁄ 005 · RANKS</span>
        <div style={{ marginTop: 12 }}>
          <div style={{ fontFamily: "var(--font-nepali)", fontSize: "var(--text-h2)", fontWeight: 600, color: "var(--fg)" }}>
            शीर्ष शिक्षकहरू
          </div>
          <div style={{ fontFamily: "var(--font-sans)", fontSize: "var(--text-body)", color: "var(--fg-muted)", fontStyle: "italic" }}>
            Top Teachers
          </div>
        </div>
      </div>

      {/* Period tabs */}
      <div style={{ marginTop: 20, display: "flex", gap: 8 }}>
        {PERIODS.map((p) => (
          <button
            key={p.id}
            onClick={() => setPeriod(p.id)}
            style={{
              flex: 1,
              padding: "10px 4px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 3,
              background: period === p.id ? "var(--bg-card)" : "transparent",
              border: period === p.id ? "1.5px solid var(--accent)" : "1.5px solid var(--rule)",
              borderRadius: 12,
              cursor: "pointer",
              transition: "all var(--duration-micro) var(--ease)",
            }}
          >
            <span style={{ fontFamily: "var(--font-nepali-ui)", fontSize: 13, color: period === p.id ? "var(--fg)" : "var(--fg-muted)", fontWeight: period === p.id ? 600 : 400 }}>
              {p.ne}
            </span>
            <span style={{ ...MONO, color: "var(--fg-subtle)", letterSpacing: "0.06em" }}>{p.en}</span>
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "48px 0" }}>
          <div className="spinner" />
        </div>
      ) : (
        <>
          {/* Podium — top 3 */}
          {top3.length > 0 && (
            <div style={{ marginTop: 28, display: "flex", alignItems: "flex-end", justifyContent: "center", gap: 8, height: 180 }}>
              {[top3[1], top3[0], top3[2]].filter(Boolean).map((e, col) => {
                const heights   = [140, 176, 120];
                const isGold    = col === 1;
                return (
                  <div
                    key={e.rank}
                    style={{
                      flex: 1,
                      height: heights[col],
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "flex-end",
                      background: isGold ? "var(--tint-butter)" : "var(--bg-card)",
                      border: `1px solid ${isGold ? "var(--rule)" : "var(--rule-soft)"}`,
                      borderRadius: "14px 14px 0 0",
                      padding: "10px 6px",
                      position: "relative",
                    }}
                  >
                    <div style={{
                      position: "absolute",
                      top: -20,
                      width: 36,
                      height: 36,
                      borderRadius: "50%",
                      background: "var(--tint-lavender)",
                      border: `1.5px solid ${isGold ? "var(--accent)" : "var(--rule)"}`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontFamily: "var(--font-serif)",
                      fontSize: 14,
                      color: "var(--fg)",
                    }}>
                      {e.avatar_initial}
                    </div>
                    <span style={{ ...MONO, color: "var(--fg-subtle)" }}>
                      {String(e.rank).padStart(2, "0")}
                    </span>
                    <span style={{
                      fontFamily: "var(--font-sans)",
                      fontSize: 11,
                      color: "var(--fg)",
                      fontWeight: 500,
                      marginTop: 2,
                      textAlign: "center",
                      lineHeight: 1.2,
                    }}>
                      {e.name.split(" ")[0]}
                    </span>
                    <span style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 12,
                      color: "var(--fg-muted)",
                      marginTop: 2,
                    }}>
                      {e.points.toLocaleString()}
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {/* Full list */}
          <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 4 }}>
            {[...top3, ...rest].map((e, i) => (
              <div
                key={e.rank}
                style={{
                  display: "grid",
                  gridTemplateColumns: "32px 1fr auto",
                  gap: 12,
                  alignItems: "center",
                  padding: "12px 14px",
                  borderRadius: 14,
                  background: i < 3 ? "var(--bg-card)" : "transparent",
                  border: i < 3 ? "1px solid var(--rule-soft)" : "1px solid transparent",
                  boxShadow: i < 3 ? "var(--shadow-subtle)" : "none",
                }}
              >
                <span style={{ ...MONO, color: "var(--fg-subtle)", textAlign: "center" }}>
                  {String(e.rank).padStart(2, "0")}
                </span>
                <span style={{ fontFamily: "var(--font-sans)", fontSize: 14, color: "var(--fg)" }}>
                  {e.name}
                </span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--fg-muted)", fontWeight: 500 }}>
                  {e.points.toLocaleString()}
                </span>
              </div>
            ))}
          </div>

          {/* Weekly prize card */}
          <div style={{
            marginTop: 20,
            padding: "18px 20px",
            background: "var(--tint-lavender)",
            borderRadius: 18,
            border: "1px solid var(--rule-soft)",
          }}>
            <span style={{ ...MONO, color: "var(--fg-muted)" }}>⁄ WEEKLY PRIZE</span>
            <div style={{ marginTop: 8, fontFamily: "var(--font-serif)", fontSize: 20, color: "var(--fg)", letterSpacing: "-0.01em" }}>
              Top 3 teachers earn LIPI Credit
            </div>
            <div style={{ marginTop: 4, fontFamily: "var(--font-sans)", fontSize: 13, color: "var(--fg-muted)", fontStyle: "italic" }}>
              Resets every Sunday at midnight (NST)
            </div>
          </div>
        </>
      )}
    </div>
  );
}
