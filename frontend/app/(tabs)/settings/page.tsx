"use client";

import Link from "next/link";
import { useTheme, type Theme } from "@/components/theme/ThemeProvider";
import Orb from "@/components/orb/Orb";

const MONO: React.CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: "0.65rem",
  letterSpacing: "0.1em",
  textTransform: "uppercase",
};

const REGISTERS = [
  { id: "tapai", ne: "तपाई", sub: "formal · ≥ 30" },
  { id: "timi",  ne: "तिमी", sub: "casual · < 30" },
  { id: "hajur", ne: "हजुर", sub: "respectful · ≥ 60" },
] as const;

const PRIVACY_TOGGLES = [
  { ne: "अडियो संकलन गर्नुहोस्", en: "Capture audio for training" },
  { ne: "भाषा पहिचानलाई योगदान गर्नुहोस्", en: "Contribute dialect signals" },
  { ne: "समुदाय फिडमा देखाउनुहोस्", en: "Show in community feed" },
  { ne: "अनुसन्धानमा प्रयोग गर्नुहोस्", en: "Use for research" },
];

const NOTIF_TOGGLES = [
  { ne: "दैनिक अनुस्मारक", en: "Daily reminder" },
  { ne: "साप्ताहिक प्रगति", en: "Weekly progress" },
  { ne: "समुदाय अपडेटहरू", en: "Community updates" },
];

export default function SettingsPage() {
  const { theme, setTheme, themes, label, orb } = useTheme();

  return (
    <div style={{
      minHeight: "100svh",
      background: "var(--bg)",
      padding: "60px 20px 120px",
      display: "flex",
      flexDirection: "column",
      gap: 28,
      overflowY: "auto",
    }}>

      {/* Header */}
      <div>
        <span style={{ ...MONO, color: "var(--fg-muted)" }}>⁄ 006 · Settings</span>
        <div style={{ marginTop: 12 }}>
          <div style={{
            fontFamily: "var(--font-nepali)",
            fontSize: "var(--text-h2)",
            fontWeight: 600,
            color: "var(--fg)",
          }}>सेटिङ</div>
          <div style={{
            fontFamily: "var(--font-sans)",
            fontSize: "var(--text-body)",
            color: "var(--fg-muted)",
            fontStyle: "italic",
          }}>Settings</div>
        </div>
      </div>

      {/* Theme picker */}
      <section>
        <span style={{ ...MONO, color: "var(--fg-muted)" }}>⁄ APPEARANCE · थिम</span>
        <div style={{
          marginTop: 14,
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gap: 8,
        }}>
          {(themes as Theme[]).map((t) => {
            const { a, b, c } = orb(t);
            const active = theme === t;
            return (
              <button
                key={t}
                onClick={() => setTheme(t)}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 6,
                  padding: "12px 4px 10px",
                  background: active ? "var(--bg-card)" : "transparent",
                  border: active ? "1.5px solid var(--accent)" : "1.5px solid var(--rule)",
                  borderRadius: 16,
                  cursor: "pointer",
                  transition: "all var(--duration-micro) var(--ease)",
                }}
              >
                {/* Orb gradient preview swatch */}
                <div style={{
                  width: 40,
                  height: 40,
                  borderRadius: "50%",
                  background: `radial-gradient(circle at 35% 30%, ${c}, ${a} 50%, ${b})`,
                  boxShadow: active ? `0 0 12px ${a}80` : "none",
                  transition: "box-shadow var(--duration-micro) var(--ease)",
                }} />
                <span style={{
                  fontFamily: "var(--font-nepali-ui)",
                  fontSize: "0.6rem",
                  color: active ? "var(--fg)" : "var(--fg-muted)",
                  lineHeight: 1,
                }}>
                  {label(t).ne}
                </span>
              </button>
            );
          })}
        </div>

        {/* Full Orb preview */}
        <div style={{
          marginTop: 18,
          padding: "28px 0",
          display: "flex",
          justifyContent: "center",
          background: "var(--bg-card)",
          borderRadius: 20,
          border: "1px solid var(--rule)",
        }}>
          <Orb state="idle" size={100} subdued />
        </div>
      </section>

      {/* Register picker */}
      <section>
        <span style={{ ...MONO, color: "var(--fg-muted)" }}>⁄ REGISTER · बोली शैली</span>
        <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 8 }}>
          {REGISTERS.map((r) => (
            <button
              key={r.id}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "16px 18px",
                background: "var(--bg-card)",
                border: "1px solid var(--rule)",
                borderRadius: 16,
                cursor: "pointer",
                textAlign: "left",
              }}
            >
              <div>
                <div style={{
                  fontFamily: "var(--font-nepali)",
                  fontSize: 17,
                  color: "var(--fg)",
                  fontWeight: 500,
                }}>
                  {r.ne}
                </div>
                <div style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.6rem",
                  letterSpacing: "0.08em",
                  color: "var(--fg-muted)",
                  marginTop: 2,
                }}>
                  {r.sub}
                </div>
              </div>
              <div style={{
                width: 20,
                height: 20,
                borderRadius: "50%",
                border: "1.5px solid var(--rule)",
                background: "var(--bg)",
              }} />
            </button>
          ))}
        </div>
      </section>

      {/* Privacy toggles */}
      <section>
        <span style={{ ...MONO, color: "var(--fg-muted)" }}>⁄ PRIVACY · गोपनीयता</span>
        <div style={{
          marginTop: 14,
          background: "var(--bg-card)",
          borderRadius: 20,
          border: "1px solid var(--rule)",
          overflow: "hidden",
        }}>
          {PRIVACY_TOGGLES.map((item, i) => (
            <ToggleRow
              key={i}
              ne={item.ne}
              en={item.en}
              defaultOn={i < 2}
              last={i === PRIVACY_TOGGLES.length - 1}
            />
          ))}
        </div>
      </section>

      {/* Notification toggles */}
      <section>
        <span style={{ ...MONO, color: "var(--fg-muted)" }}>⁄ NOTIFICATIONS · सूचनाहरू</span>
        <div style={{
          marginTop: 14,
          background: "var(--bg-card)",
          borderRadius: 20,
          border: "1px solid var(--rule)",
          overflow: "hidden",
        }}>
          {NOTIF_TOGGLES.map((item, i) => (
            <ToggleRow
              key={i}
              ne={item.ne}
              en={item.en}
              defaultOn={i === 0}
              last={i === NOTIF_TOGGLES.length - 1}
            />
          ))}
        </div>
      </section>

      {/* System dashboard link */}
      <section>
        <span style={{ ...MONO, color: "var(--fg-muted)" }}>⁄ SYSTEM</span>
        <Link
          href="/settings/dashboard"
          style={{
            marginTop: 14,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "18px 20px",
            background: "var(--bg-card)",
            border: "1px solid var(--rule)",
            borderRadius: 16,
            textDecoration: "none",
          }}
        >
          <div>
            <div style={{ fontFamily: "var(--font-nepali-ui)", fontSize: 15, color: "var(--fg)", fontWeight: 500 }}>
              प्रणाली ड्यासबोर्ड
            </div>
            <div style={{ fontFamily: "var(--font-sans)", fontSize: 12, color: "var(--fg-muted)", fontStyle: "italic", marginTop: 2 }}>
              System dashboard · status, data &amp; reports
            </div>
          </div>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ color: "var(--fg-subtle)", flexShrink: 0 }}>
            <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </Link>
      </section>
    </div>
  );
}

function ToggleRow({
  ne, en, defaultOn, last
}: { ne: string; en: string; defaultOn?: boolean; last?: boolean }) {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "14px 18px",
      borderBottom: last ? "none" : "1px solid var(--rule-soft)",
    }}>
      <div>
        <div style={{ fontFamily: "var(--font-nepali-ui)", fontSize: 14, color: "var(--fg)", fontWeight: 500 }}>
          {ne}
        </div>
        <div style={{ fontFamily: "var(--font-sans)", fontSize: 11, color: "var(--fg-muted)", fontStyle: "italic", marginTop: 1 }}>
          {en}
        </div>
      </div>
      {/* Toggle pill */}
      <div style={{
        width: 44,
        height: 26,
        borderRadius: 13,
        background: defaultOn ? "var(--accent)" : "var(--rule)",
        position: "relative",
        flexShrink: 0,
        transition: "background var(--duration-micro) var(--ease)",
      }}>
        <div style={{
          position: "absolute",
          top: 3,
          left: defaultOn ? 21 : 3,
          width: 20,
          height: 20,
          borderRadius: "50%",
          background: "var(--bg-elev)",
          boxShadow: "0 1px 4px rgba(0,0,0,0.12)",
          transition: "left var(--duration-micro) var(--ease)",
        }} />
      </div>
    </div>
  );
}
