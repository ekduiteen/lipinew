"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getMyStats, getLeaderboard, type TeacherStats, type LeaderboardEntry } from "@/lib/api";
import { BilingualText, FrostPill, Mono } from "@/components/ui/LipiPrimitives";

export default function HomePage() {
  const [stats, setStats]     = useState<TeacherStats | null>(null);
  const [leaders, setLeaders] = useState<LeaderboardEntry[]>([]);
  const [userName, setUserName] = useState("शिक्षक");

  useEffect(() => {
    getMyStats().then(setStats).catch(() => {});
    getLeaderboard("weekly").then((l) => setLeaders(l.slice(0, 4))).catch(() => {});
    try {
      const stored = localStorage.getItem("lipi.user_name");
      if (stored) setUserName(stored);
    } catch { /* */ }
  }, []);

  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? "शुभ प्रभात" : hour < 17 ? "शुभ दिन" : "शुभ साँझ";
  const greetingEn =
    hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

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
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", padding: "0 4px", gap: 16 }}>
        <div>
          <FrostPill style={{ marginBottom: 14 }}>
            <Mono color="var(--fg-muted)">⁄ {String(new Date().getDate()).padStart(3, "0")} · TODAY</Mono>
          </FrostPill>
          <div style={{ maxWidth: 320 }}>
            <BilingualText
              np={`${greeting}, ${userName}`}
              en={`${greetingEn}, ${userName}`}
              size="lg"
            />
          </div>
        </div>
        <div style={{
          width: 40,
          height: 40,
          borderRadius: "50%",
          background: "var(--tint-lavender)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "var(--font-serif)",
          fontSize: 16,
          color: "var(--fg)",
          border: "1px solid var(--rule)",
          flexShrink: 0,
        }}>
          {userName[0] ?? "श"}
        </div>
      </div>

      {/* LIPI HAS LEARNED — hero card */}
      <div style={{
        marginTop: 24,
        background: "var(--bg-card)",
        borderRadius: 24,
        border: "1px solid var(--rule)",
        boxShadow: "var(--shadow-card)",
        overflow: "hidden",
      }}>
        <div style={{ padding: "22px 22px 4px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Mono color="var(--fg-muted)">LIPI HAS LEARNED</Mono>
          <Mono color="var(--fg-muted)">↗ +23 today</Mono>
        </div>
        <div style={{ padding: "12px 22px 18px" }}>
          <div style={{ fontFamily: "var(--font-nepali)", fontSize: 15, color: "var(--fg-muted)", lineHeight: 1.4 }}>
            शब्दहरू{" "}
            <span style={{ fontFamily: "var(--font-sans)", fontSize: 12, fontStyle: "italic" }}>
              · words from you
            </span>
          </div>
          <div style={{
            fontFamily: "var(--font-serif)",
            fontSize: 88,
            lineHeight: 1,
            color: "var(--fg)",
            letterSpacing: "-0.04em",
            fontWeight: 400,
            marginTop: 8,
          }}>
            {stats ? stats.words_taught.toLocaleString() : "—"}
          </div>
        </div>

        {/* Sparkline */}
        <div style={{ position: "relative", height: 60, margin: "0 22px 18px", borderTop: "1px solid var(--rule)" }}>
          <svg viewBox="0 0 320 56" width="100%" height="56" preserveAspectRatio="none">
            <path
              d="M0,50 C40,40 60,30 90,32 C120,34 140,20 170,22 C200,24 230,10 260,14 C290,18 310,8 320,10"
              fill="none"
              stroke="var(--fg)"
              strokeWidth="1.2"
              opacity="0.5"
            />
            <path
              d="M0,50 C40,40 60,30 90,32 C120,34 140,20 170,22 C200,24 230,10 260,14 C290,18 310,8 320,10 L320,56 L0,56 Z"
              fill="var(--tint-lavender)"
            />
          </svg>
        </div>

        {/* Stat footer */}
        <div style={{ display: "flex", borderTop: "1px solid var(--rule)" }}>
          {[
            { val: stats ? `${Math.round((stats.total_points || 0) / 100 * 10) / 10}` : "—", unit: "hrs", label: "Taught" },
            { val: stats ? `${stats.current_streak}` : "—", unit: "day", label: "Streak" },
            { val: stats ? `${stats.total_points.toLocaleString()}` : "—", unit: "pts", label: "Points" },
          ].map((s, i, arr) => (
            <div
              key={s.label}
              style={{
                flex: 1,
                padding: "14px 18px",
                borderRight: i < arr.length - 1 ? "1px solid var(--rule)" : "none",
              }}
            >
              <Mono color="var(--fg-subtle)">{s.label}</Mono>
              <div style={{
                fontFamily: "var(--font-serif)",
                fontSize: 26,
                color: "var(--fg)",
                marginTop: 4,
                letterSpacing: "-0.02em",
              }}>
                {s.val}
                <span style={{
                  fontSize: 12,
                  fontFamily: "var(--font-mono)",
                  color: "var(--fg-muted)",
                  marginLeft: 4,
                }}>
                  {s.unit}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Teach CTA */}
      <Link
        href="/teach"
        style={{
          marginTop: 14,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "22px 22px",
          background: "var(--accent)",
          color: "var(--accent-fg)",
          borderRadius: 24,
          textDecoration: "none",
        }}
      >
        <div style={{ minWidth: 0 }}>
          <Mono color="rgba(250, 244, 233, 0.7)">NOW · READY · सिकाउनु</Mono>
          <div style={{
            fontFamily: "var(--font-serif)",
            fontSize: 26,
            marginTop: 8,
            letterSpacing: "-0.01em",
            lineHeight: 1.2,
          }}>
            Start teaching LIPI
          </div>
        </div>
        <div style={{
          width: 52,
          height: 52,
          borderRadius: "50%",
          background: "rgba(255,255,255,0.12)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}>
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M5 10h10m0 0l-5-5m5 5l-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      </Link>

      {/* Mini leaderboard */}
      {leaders.length > 0 && (
        <div style={{
          marginTop: 14,
          background: "var(--bg-card)",
          borderRadius: 24,
          border: "1px solid var(--rule)",
          boxShadow: "var(--shadow-card)",
          overflow: "hidden",
        }}>
          <div style={{ padding: "18px 22px 14px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Mono color="var(--fg-muted)">⁄ RANK · WEEKLY</Mono>
            <Link href="/ranks" style={{ textDecoration: "none" }}><Mono color="var(--fg-muted)">SEE ALL →</Mono></Link>
          </div>
          <div style={{ padding: "0 12px 14px", display: "flex", flexDirection: "column", gap: 4 }}>
            {leaders.map((r, i) => (
              <div
                key={r.rank}
                style={{
                  display: "grid",
                  gridTemplateColumns: "28px 1fr auto",
                  gap: 10,
                  alignItems: "center",
                  padding: "10px 10px",
                  borderRadius: 12,
                  background: i === 0 ? "var(--tint-butter)" : "transparent",
                  border: `1px solid ${i === 0 ? "var(--rule)" : "transparent"}`,
                }}
              >
                <Mono color="var(--fg-subtle)">
                  {String(r.rank).padStart(2, "0")}
                </Mono>
                <span style={{
                  fontFamily: "var(--font-sans)",
                  fontSize: 14,
                  color: "var(--fg)",
                }}>
                  {r.name}
                </span>
                <span style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 13,
                  color: "var(--fg)",
                  fontWeight: 500,
                }}>
                  {r.points.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TODAY LIPI LEARNED word feed */}
      <div style={{ marginTop: 24, padding: "0 4px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
          <Mono color="var(--fg-muted)">⁄ TODAY LIPI LEARNED</Mono>
          <FrostPill style={{ padding: "6px 10px" }}>
            <Mono color="var(--fg-muted)">LIVE ●</Mono>
          </FrostPill>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {[
            { word: "बिस्तारै", translation: "slowly", kind: "adverb" },
            { word: "घाम लाग्यो", translation: "it's sunny", kind: "phrase" },
            { word: "मिठो", translation: "sweet / delicious", kind: "adjective" },
          ].map((item) => (
            <div
              key={item.word}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "12px 16px",
                borderRadius: 14,
                background: "var(--bg-card)",
                border: "1px solid var(--rule-soft)",
              }}
            >
              <div style={{ flex: 1 }}>
                <BilingualText
                  np={item.word}
                  en={item.translation}
                  size="md"
                />
              </div>
              <span style={{
                color: "var(--fg-subtle)",
                background: "var(--tint-lavender)",
                padding: "3px 8px",
                borderRadius: "var(--radius-full)",
              }}>
                <Mono color="var(--fg-subtle)">{item.kind}</Mono>
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
