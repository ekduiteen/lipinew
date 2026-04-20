"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { submitOnboarding, type OnboardingPayload } from "@/lib/api";
import Orb from "@/components/orb/Orb";

const LANGUAGES = [
  "Nepali", "English", "Maithili", "Bhojpuri", "Tharu", "Tamang", "Newar",
  "Bajjika", "Magar", "Doteli", "Urdu", "Avadhi", "Limbu", "Gurung",
  "Baitadeli", "Hindi", "Tibetan", "Rai", "Sherpa", "Sunuwar",
];

const NEPAL_CITIES = [
  "Kathmandu", "Pokhara", "Biratnagar", "Lalitpur", "Bhaktapur",
  "Janakpur", "Birgunj", "Nepalgunj", "Dharan", "Itahari",
  "Hetauda", "Gorkha", "Nuwakot", "Tansen", "Ilam",
  "Dhangadi", "Jumla", "Dhulikhel", "Narayanghat", "Jhapa",
  "Kakarvitta", "Godavari", "Kirtipur", "Sindhuli", "Makwanpur",
];

const EDUCATION_LEVELS = [
  { ne: "प्राथमिक", en: "Primary", db: "primary" },
  { ne: "माध्यमिक", en: "Secondary", db: "secondary" },
  { ne: "उच्च माध्यमिक", en: "Higher Secondary", db: "secondary" },
  { ne: "स्नातक", en: "Bachelor's", db: "bachelors" },
  { ne: "स्नातकोत्तर वा माथि", en: "Master's or above", db: "masters" },
];

interface Draft {
  first_name:      string;
  last_name:       string;
  age:             string;
  native_language: string;
  other_languages: string[];
  gender:          "male" | "female" | "other" | "";
  city_or_village: string;
  education_level: string;
}

const MONO: React.CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: "0.65rem",
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  color: "var(--fg-muted)",
};

export default function OnboardingPage() {
  const router = useRouter();
  const isMountedRef = useRef(true);
  const [step, setStep]         = useState(0);
  const [langSearch, setLangSearch] = useState("");
  const [citySearch, setCitySearch] = useState("");
  const [draft, setDraft]       = useState<Draft>({
    first_name: "", last_name: "", age: "",
    native_language: "", other_languages: [],
    gender: "", city_or_village: "", education_level: "",
  });
  const [submitting, setSubmitting] = useState(false);

  const TOTAL = 8;

  useEffect(() => {
    isMountedRef.current = true;
    return () => { isMountedRef.current = false; };
  }, []);

  function next() { if (step < TOTAL - 1) setStep((s) => s + 1); }
  function prev() { if (step > 0) setStep((s) => s - 1); }
  function set<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((d) => ({ ...d, [key]: value }));
  }

  async function finish() {
    if (!draft.education_level) return;
    setSubmitting(true);
    try {
      const eduLevel  = EDUCATION_LEVELS.find((e) => e.en === draft.education_level);
      const eduDbValue = eduLevel?.db || draft.education_level;
      await submitOnboarding({
        first_name: draft.first_name,
        last_name:  draft.last_name,
        age:        parseInt(draft.age),
        native_language: draft.native_language,
        other_languages: draft.other_languages,
        gender: draft.gender as OnboardingPayload["gender"],
        city_or_village: draft.city_or_village,
        education_level: eduDbValue,
      });
      if (draft.first_name) {
        try { localStorage.setItem("lipi.user_name", draft.first_name); } catch { /* */ }
      }
      router.push("/home");
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : "Unknown error";
      alert(`त्रुटि: ${msg}`);
      if (isMountedRef.current) setSubmitting(false);
    }
  }

  const filteredLangs  = LANGUAGES.filter((l) => l.toLowerCase().includes(langSearch.toLowerCase()));
  const filteredCities = NEPAL_CITIES.filter((c) => c.toLowerCase().includes(citySearch.toLowerCase()));

  const progress = step / (TOTAL - 1);

  // ── Step content ─────────────────────────────────────────────────────────
  const stepContent = [
    // 0 — Intro
    <div key="intro" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 28 }}>
      <Orb state="listening" size={140} />
      <div style={{ textAlign: "center", maxWidth: 300 }}>
        <div style={{ fontFamily: "var(--font-serif)", fontSize: 32, color: "var(--fg)", lineHeight: 1.2, letterSpacing: "-0.02em" }}>
          नमस्ते!<br />म LIPI हुँ।
        </div>
        <div style={{ fontFamily: "var(--font-sans)", fontSize: 15, color: "var(--fg-muted)", marginTop: 14, lineHeight: 1.5, fontStyle: "italic" }}>
          Hi — I&apos;m LIPI. I&apos;m learning languages from teachers like you.<br /><br />
          Before we begin, can I ask you a few things?
        </div>
      </div>
      <PillBtn onClick={next}>Begin · सुरु गर्नु ›</PillBtn>
    </div>,

    // 1 — First name
    <StepForm key="fn" mono="Q 01 · NAME" np="हजुरको पहिलो नाम के हो?" en="What should I call you?">
      <input
        autoFocus
        value={draft.first_name}
        onChange={(e) => set("first_name", e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && draft.first_name && next()}
        placeholder="पहिलो नाम…"
        style={inputStyle}
      />
      <BtnRow onBack={prev} onNext={next} disabled={!draft.first_name} />
    </StepForm>,

    // 2 — Last name
    <StepForm key="ln" mono="Q 02 · NAME" np="हजुरको अन्तिम नाम के हो?" en="Your last name?">
      <input
        autoFocus
        value={draft.last_name}
        onChange={(e) => set("last_name", e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && draft.last_name && next()}
        placeholder="अन्तिम नाम…"
        style={inputStyle}
      />
      <BtnRow onBack={prev} onNext={next} disabled={!draft.last_name} />
    </StepForm>,

    // 3 — Age
    <StepForm key="age" mono="Q 03 · AGE" np="हजुर कति वर्षको हुनुहुन्छ?" en="How many years young?">
      <div style={{ textAlign: "center" }}>
        <div style={{
          fontFamily: "var(--font-serif)",
          fontSize: 72,
          color: "var(--fg)",
          lineHeight: 1,
          letterSpacing: "-0.03em",
        }}>
          {draft.age || "—"}
        </div>
        <input
          type="range"
          min={13}
          max={90}
          value={draft.age || 25}
          onChange={(e) => set("age", e.target.value)}
          style={{ width: "100%", marginTop: 16, accentColor: "var(--accent)" }}
        />
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
          <span style={{ ...MONO }}>13</span>
          <span style={{ ...MONO }}>90</span>
        </div>
      </div>
      <BtnRow onBack={prev} onNext={next} disabled={!draft.age} />
    </StepForm>,

    // 4 — Primary language
    <StepForm key="lang" mono="Q 04 · PRIMARY" np="म कुन भाषा सिकूँ?" en="Which language will you teach me?">
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {LANGUAGES.slice(0, 12).map((l) => (
          <ChipBtn
            key={l}
            active={draft.native_language === l}
            onClick={() => { set("native_language", l); next(); }}
          >{l}</ChipBtn>
        ))}
      </div>
      <BtnRow onBack={prev} />
    </StepForm>,

    // 5 — Other languages
    <StepForm key="other" mono="Q 05 · OTHERS" np="अरू कुन भाषाहरू बोल्नुहुन्छ?" en="Which others do you speak?">
      <input
        placeholder="खोज्नुहोस् · Search…"
        value={langSearch}
        onChange={(e) => setLangSearch(e.target.value)}
        style={{ ...inputStyle, fontSize: 14, marginBottom: 8 }}
      />
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, maxHeight: 200, overflowY: "auto" }}>
        {filteredLangs.filter((l) => l !== draft.native_language).map((l) => (
          <ChipBtn
            key={l}
            active={draft.other_languages.includes(l)}
            onClick={() => set("other_languages",
              draft.other_languages.includes(l)
                ? draft.other_languages.filter((x) => x !== l)
                : [...draft.other_languages, l]
            )}
          >{l}</ChipBtn>
        ))}
      </div>
      <BtnRow onBack={prev} onNext={next} />
    </StepForm>,

    // 6 — Gender
    <StepForm key="gender" mono="Q 06 · GENDER" np="लिंग?" en="Gender?">
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {(["male", "female", "other"] as const).map((g) => {
          const labels = {
            male:   { ne: "पुरुष", en: "Male" },
            female: { ne: "महिला", en: "Female" },
            other:  { ne: "अन्य", en: "Other · prefer not to say" },
          };
          return (
            <button
              key={g}
              onClick={() => { set("gender", g); next(); }}
              style={{
                textAlign: "left",
                padding: "14px 18px",
                background: draft.gender === g ? "var(--accent)" : "transparent",
                color: draft.gender === g ? "var(--accent-fg)" : "var(--fg)",
                border: `1px solid ${draft.gender === g ? "var(--accent)" : "var(--rule)"}`,
                borderRadius: 16,
                cursor: "pointer",
                transition: "all 180ms ease",
              }}
            >
              <div style={{ fontFamily: "var(--font-nepali-ui)", fontSize: 16 }}>{labels[g].ne}</div>
              <div style={{ fontFamily: "var(--font-sans)", fontSize: 12, color: draft.gender === g ? "var(--accent-fg)" : "var(--fg-muted)", fontStyle: "italic", marginTop: 2 }}>{labels[g].en}</div>
            </button>
          );
        })}
      </div>
      <BtnRow onBack={prev} />
    </StepForm>,

    // 7 — City
    <StepForm key="city" mono="Q 07 · ROOTS" np="तपाईं कहाँ हुर्कनुभयो?" en="Where did you grow up?">
      <input
        autoFocus
        placeholder="Kathmandu, Pokhara…"
        value={citySearch}
        onChange={(e) => setCitySearch(e.target.value)}
        style={{ ...inputStyle, fontSize: 14, marginBottom: 8 }}
      />
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, maxHeight: 200, overflowY: "auto" }}>
        {filteredCities.map((city) => (
          <ChipBtn
            key={city}
            active={draft.city_or_village === city}
            onClick={() => { set("city_or_village", city); next(); }}
          >{city}</ChipBtn>
        ))}
      </div>
      <BtnRow onBack={prev} />
    </StepForm>,

    // 8 — Education
    <StepForm key="edu" mono="Q 08 · EDUCATION" np="शैक्षिक योग्यता?" en="Your education level?">
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {EDUCATION_LEVELS.map((e) => (
          <button
            key={e.en}
            onClick={() => set("education_level", e.en)}
            style={{
              textAlign: "left",
              padding: "14px 18px",
              background: draft.education_level === e.en ? "var(--accent)" : "transparent",
              color: draft.education_level === e.en ? "var(--accent-fg)" : "var(--fg)",
              border: `1px solid ${draft.education_level === e.en ? "var(--accent)" : "var(--rule)"}`,
              borderRadius: 16,
              cursor: "pointer",
              transition: "all 180ms ease",
            }}
          >
            <div style={{ fontFamily: "var(--font-nepali-ui)", fontSize: 15 }}>{e.ne}</div>
            <div style={{ fontFamily: "var(--font-sans)", fontSize: 12, color: draft.education_level === e.en ? "var(--accent-fg)" : "var(--fg-muted)", fontStyle: "italic", marginTop: 1 }}>{e.en}</div>
          </button>
        ))}
      </div>
      <BtnRow
        onBack={prev}
        onNext={finish}
        nextLabel={submitting ? "सुरु हुँदैछ…" : "Start teaching ›"}
        disabled={!draft.education_level || submitting}
      />
    </StepForm>,
  ];

  return (
    <div style={{
      position: "fixed",
      inset: 0,
      background: "var(--bg)",
      display: "flex",
      flexDirection: "column",
      padding: "64px 28px 40px",
      overflowY: "auto",
    }}>
      {/* Progress bar */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 32 }}>
        {step > 0 && (
          <button
            onClick={prev}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--fg-muted)",
              cursor: "pointer",
              padding: 0,
              flexShrink: 0,
            }}
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M11 4L6 9l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        )}
        <div style={{
          flex: 1,
          height: 2,
          background: "var(--rule)",
          borderRadius: "var(--radius-full)",
          overflow: "hidden",
        }}>
          <div style={{
            width: `${progress * 100}%`,
            height: "100%",
            background: "var(--fg)",
            borderRadius: "var(--radius-full)",
            transition: "width 400ms cubic-bezier(.4,0,.2,1)",
          }} />
        </div>
        <span style={{ ...MONO, flexShrink: 0 }}>
          {String(step).padStart(2, "0")} / {String(TOTAL - 1).padStart(2, "0")}
        </span>
      </div>

      {/* Step content */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        {stepContent[step]}
      </div>
    </div>
  );
}

// ── Shared UI atoms ───────────────────────────────────────────────────────────

function StepForm({
  mono, np, en, children
}: { mono: string; np: string; en: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <span style={{
          fontFamily: "var(--font-mono)",
          fontSize: "0.65rem",
          letterSpacing: "0.1em",
          textTransform: "uppercase" as const,
          color: "var(--fg-muted)",
        }}>⁄ {mono}</span>
        <div style={{ marginTop: 14 }}>
          <div style={{ fontFamily: "var(--font-nepali)", fontSize: "var(--text-h2)", fontWeight: 600, color: "var(--fg)", lineHeight: 1.3 }}>
            {np}
          </div>
          <div style={{ fontFamily: "var(--font-sans)", fontSize: "var(--text-body)", color: "var(--fg-muted)", fontStyle: "italic", marginTop: 4 }}>
            {en}
          </div>
        </div>
      </div>
      {children}
    </div>
  );
}

function ChipBtn({ children, active, onClick }: { children: React.ReactNode; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "8px 16px",
        borderRadius: "var(--radius-full)",
        background: active ? "var(--accent)" : "var(--bg-card)",
        color: active ? "var(--accent-fg)" : "var(--fg)",
        border: `1px solid ${active ? "var(--accent)" : "var(--rule)"}`,
        fontFamily: "var(--font-sans)",
        fontSize: 13,
        fontWeight: active ? 600 : 400,
        cursor: "pointer",
        transition: "all 180ms ease",
      }}
    >
      {children}
    </button>
  );
}

function PillBtn({ children, onClick, disabled }: { children: React.ReactNode; onClick: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        width: "100%",
        padding: "16px 24px",
        background: disabled ? "var(--rule)" : "var(--accent)",
        color: disabled ? "var(--fg-muted)" : "var(--accent-fg)",
        border: "none",
        borderRadius: "var(--radius-full)",
        fontFamily: "var(--font-sans)",
        fontSize: "var(--text-body)",
        fontWeight: 600,
        cursor: disabled ? "not-allowed" : "pointer",
        transition: "all 180ms ease",
      }}
    >
      {children}
    </button>
  );
}

function BtnRow({
  onBack, onNext, nextLabel = "Continue", disabled
}: {
  onBack?: () => void;
  onNext?: () => void;
  nextLabel?: string;
  disabled?: boolean;
}) {
  return (
    <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
      {onBack && (
        <button
          onClick={onBack}
          style={{
            padding: "14px 20px",
            background: "var(--bg-card)",
            color: "var(--fg)",
            border: "1px solid var(--rule)",
            borderRadius: "var(--radius-full)",
            fontFamily: "var(--font-sans)",
            fontSize: "var(--text-body)",
            fontWeight: 500,
            cursor: "pointer",
          }}
        >
          ‹ Back
        </button>
      )}
      {onNext && (
        <PillBtn onClick={onNext} disabled={disabled}>
          {nextLabel}
        </PillBtn>
      )}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  fontFamily: "var(--font-serif)",
  fontSize: 26,
  color: "var(--fg)",
  background: "transparent",
  border: "none",
  borderBottom: "1.5px solid var(--rule)",
  padding: "10px 0",
  outline: "none",
};
