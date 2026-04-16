"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getMyStats, getLeaderboard, type TeacherStats, type LeaderboardEntry } from "@/lib/api";

export default function HomePage() {
  const [stats, setStats]     = useState<TeacherStats | null>(null);
  const [leaders, setLeaders] = useState<LeaderboardEntry[]>([]);

  useEffect(() => {
    getMyStats().then(setStats).catch(() => {});
    getLeaderboard("weekly").then((l) => setLeaders(l.slice(0, 3))).catch(() => {});
  }, []);

  return (
    <div className="page" style={{ padding: "var(--space-8) var(--space-6) var(--space-6)", gap: "var(--space-8)" }}>

      {/* Logo */}
      <header style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
        <h1
          style={{
            fontFamily: "var(--font-nepali)",
            fontSize: "var(--text-h1)",
            fontWeight: 700,
            color: "var(--fg)",
            letterSpacing: "-0.02em",
          }}
        >
          लिपि
        </h1>
        <p style={{ fontFamily: "var(--font-latin)", fontSize: "var(--text-sm)", color: "var(--fg-muted)" }}>
          You speak. LIPI learns. Language lives.
        </p>
      </header>

      {/* Stats row */}
      {stats && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "var(--space-3)" }}>
          <StatCard ne="अंक"  en="Points" value={stats.total_points.toLocaleString()} />
          <StatCard ne="दिन"  en="Streak" value={`${stats.current_streak}🔥`} />
          <StatCard ne="शब्द" en="Words"  value={stats.words_taught.toLocaleString()} />
          <StatCard ne="रैंक" en="Rank"   value={`#${stats.rank}`} />
        </div>
      )}

      {/* Primary CTA */}
      <Link
        href="/teach"
        className="btn-primary"
        style={{ textDecoration: "none", display: "flex", flexDirection: "column", alignItems: "center", gap: "var(--space-1)", padding: "var(--space-5)" }}
      >
        <span style={{ fontFamily: "var(--font-nepali)", fontSize: "var(--text-body)", fontWeight: 600 }}>
          सिकाउन सुरु गर्नुहोस्
        </span>
        <span style={{ fontFamily: "var(--font-latin)", fontSize: "var(--text-sm)", opacity: 0.75 }}>
          Start teaching
        </span>
      </Link>

      {/* Mini leaderboard */}
      {leaders.length > 0 && (
        <section style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontWeight: 600, color: "var(--fg)", fontFamily: "var(--font-nepali)" }}>
              शीर्ष शिक्षकहरू
            </span>
            <Link
              href="/ranks"
              style={{ fontSize: "var(--text-sm)", color: "var(--accent)", textDecoration: "none", fontFamily: "var(--font-latin)" }}
            >
              सबै हेर्नुस् · See all
            </Link>
          </div>

          <ol style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
            {leaders.map((l) => (
              <li
                key={l.rank}
                className="card"
                style={{ display: "flex", alignItems: "center", gap: "var(--space-4)", padding: "var(--space-4) var(--space-5)" }}
              >
                <span style={{ fontWeight: 700, color: "var(--accent)", width: "1.5rem", textAlign: "center" }}>
                  {l.rank}
                </span>
                <span
                  style={{
                    width: "2rem", height: "2rem", borderRadius: "50%",
                    background: "color-mix(in srgb, var(--accent) 20%, var(--bg-elev))",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: "0.9rem", fontWeight: 600, color: "var(--accent)", flexShrink: 0,
                  }}
                >
                  {l.avatar_initial}
                </span>
                <span style={{ flex: 1, color: "var(--fg)", fontSize: "var(--text-sm)" }}>{l.name}</span>
                <span style={{ color: "var(--fg-muted)", fontSize: "var(--text-sm)", fontFamily: "var(--font-latin)" }}>
                  {l.points.toLocaleString()} pts
                </span>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}

function StatCard({ ne, en, value }: { ne: string; en: string; value: string }) {
  return (
    <div className="stat-card">
      <span style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--accent)" }}>{value}</span>
      <span style={{ fontSize: "0.75rem", fontFamily: "var(--font-nepali)", color: "var(--fg)" }}>{ne}</span>
      <span style={{ fontSize: "0.6rem", fontFamily: "var(--font-latin)", color: "var(--fg-muted)" }}>{en}</span>
    </div>
  );
}
