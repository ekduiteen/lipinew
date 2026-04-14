"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { submitOnboarding, type OnboardingPayload } from "@/lib/api";
import styles from "./onboarding.module.css";

// ─── Question definitions ────────────────────────────────────────────────────

const LANGUAGES = [
  "Nepali", "English",
  "Maithili", "Bhojpuri", "Tharu", "Tamang", "Newar", "Bajjika",
  "Magar", "Doteli", "Urdu", "Avadhi", "Limbu", "Gurung", "Baitadeli",
  "Hindi", "Tibetan", "Rai", "Sherpa", "Sunuwar",
];

const NEPAL_CITIES = [
  "Kathmandu", "Pokhara", "Biratnagar", "Lalitpur", "Bhaktapur",
  "Janakpur", "Birgunj", "Nepalgunj", "Dharan", "Itahari",
  "Hetauda", "Gorkha", "Nuwakot", "Tansen", "Ilam",
  "Dhangadi", "Jumla", "Dhulikhel", "Nag", "Sindhupalchok",
  "Kakarvitta", "Godavari", "Narayanghat", "Jhapa", "Daman",
  "Kirtipur", "Nagarkot", "Chautara", "Sindhuli", "Makwanpur",
  "Okhaldunga", "Ramechhap", "Dolakha", "Shuklaphanta", "Lahan",
  "Bardia", "Surkhet", "Bajura", "Doti", "Achham",
  "Bajhang", "Dadeldhura", "Baitadi", "Kanchanpur", "Kailali",
];

const EDUCATION_LEVELS = [
  { ne: "प्राथमिक", en: "Primary", db: "primary" },
  { ne: "माध्यमिक", en: "Secondary", db: "secondary" },
  { ne: "उच्च माध्यमिक", en: "Higher Secondary", db: "secondary" }, // map to secondary for now
  { ne: "स्नातक", en: "Bachelor's", db: "bachelors" },
  { ne: "स्नातकोत्तर वा माथि", en: "Master's or above", db: "masters" },
];

// ─── State shape ─────────────────────────────────────────────────────────────

interface Draft {
  first_name: string;
  last_name: string;
  age: string;
  native_language: string;
  other_languages: string[];
  gender: "male" | "female" | "other" | "";
  city_or_village: string;
  education_level: string;
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function OnboardingPage() {
  const router = useRouter();
  const isMountedRef = useRef(true);
  const [step, setStep] = useState(0);
  const [langSearch, setLangSearch] = useState("");
  const [citySearch, setCitySearch] = useState("");
  const [draft, setDraft] = useState<Draft>({
    first_name: "",
    last_name: "",
    age: "",
    native_language: "",
    other_languages: [],
    gender: "",
    city_or_village: "",
    education_level: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [direction, setDirection] = useState<"forward" | "backward">("forward");

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  function next() {
    if (step < TOTAL - 1) {
      setDirection("forward");
      setStep((s) => s + 1);
    }
  }

  function prev() {
    if (step > 0) {
      setDirection("backward");
      setStep((s) => s - 1);
    }
  }

  function set<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((d) => ({ ...d, [key]: value }));
  }

  async function finish() {
    if (!draft.education_level) {
      alert("कृपया शिक्षा स्तर छनोट गर्नुहोस्");
      return;
    }
    setSubmitting(true);
    try {
      console.log("Submitting onboarding with data:", {
        first_name: draft.first_name,
        last_name: draft.last_name,
        age: draft.age,
        native_language: draft.native_language,
        other_languages: draft.other_languages,
        gender: draft.gender,
        city_or_village: draft.city_or_village,
        education_level: draft.education_level,
      });

      // Find the database value for the selected education level
      const eduLevel = EDUCATION_LEVELS.find(e => e.en === draft.education_level);
      const eduDbValue = eduLevel?.db || draft.education_level;

      const response = await submitOnboarding({
        first_name: draft.first_name,
        last_name: draft.last_name,
        age: parseInt(draft.age),
        native_language: draft.native_language,
        other_languages: draft.other_languages,
        gender: draft.gender as OnboardingPayload["gender"],
        city_or_village: draft.city_or_village,
        education_level: eduDbValue,
      });
      console.log("Onboarding completed:", response);
      router.push("/home");
    } catch (error: any) {
      console.error("Onboarding submission failed:", error);
      alert(`त्रुटि: ${error?.message || "अनजान त्रुटि"}`);
      setSubmitting(false);
    }
  }

  const filteredLangs = LANGUAGES.filter((l) =>
    l.toLowerCase().includes(langSearch.toLowerCase())
  );

  const filteredCities = NEPAL_CITIES.filter((c) =>
    c.toLowerCase().includes(citySearch.toLowerCase())
  );

  const TOTAL = 8;
  const questionNumber = step + 1;

  const steps = [
    // 0 — First Name
    <div key="first_name" className={`${styles.step} ${direction === "forward" ? styles.slideInForward : styles.slideInBackward}`}>
      <div className={styles.questionNumber}>{questionNumber}/{ TOTAL}</div>
      <p className={styles.ne}>हजुरको पहिलो नाम के हो?</p>
      <p className={styles.en}>What is your first name?</p>
      <input
        className={styles.input}
        autoFocus
        value={draft.first_name}
        onChange={(e) => set("first_name", e.target.value)}
        placeholder="पहिलो नाम…"
        onKeyDown={(e) => e.key === "Enter" && draft.first_name && next()}
      />
      <div className={styles.buttonGroup}>
        <button
          className={styles.btn}
          disabled={!draft.first_name}
          onClick={next}
        >
          अगाडि
        </button>
      </div>
    </div>,

    // 1 — Last Name
    <div key="last_name" className={`${styles.step} ${direction === "forward" ? styles.slideInForward : styles.slideInBackward}`}>
      <div className={styles.questionNumber}>{questionNumber}/{TOTAL}</div>
      <p className={styles.ne}>हजुरको अन्तिम नाम के हो?</p>
      <p className={styles.en}>What is your last name?</p>
      <input
        className={styles.input}
        autoFocus
        value={draft.last_name}
        onChange={(e) => set("last_name", e.target.value)}
        placeholder="अन्तिम नाम…"
        onKeyDown={(e) => e.key === "Enter" && draft.last_name && next()}
      />
      <div className={styles.buttonGroup}>
        <button className={styles.btnSecondary} onClick={prev}>पछाडि</button>
        <button
          className={styles.btn}
          disabled={!draft.last_name}
          onClick={next}
        >
          अगाडि
        </button>
      </div>
    </div>,

    // 2 — Age
    <div key="age" className={`${styles.step} ${direction === "forward" ? styles.slideInForward : styles.slideInBackward}`}>
      <div className={styles.questionNumber}>{questionNumber}/{TOTAL}</div>
      <p className={styles.ne}>हजुर कति बर्ष पुगनु भयो?</p>
      <p className={styles.en}>How old are you?</p>
      <input
        className={styles.input}
        autoFocus
        type="number"
        min={5}
        max={120}
        value={draft.age}
        onChange={(e) => set("age", e.target.value)}
        placeholder="उमेर…"
        onKeyDown={(e) => e.key === "Enter" && draft.age && next()}
      />
      <div className={styles.buttonGroup}>
        <button className={styles.btnSecondary} onClick={prev}>पछाडि</button>
        <button className={styles.btn} disabled={!draft.age} onClick={next}>
          अगाडि
        </button>
      </div>
    </div>,

    // 3 — Native language
    <div key="lang" className={`${styles.step} ${direction === "forward" ? styles.slideInForward : styles.slideInBackward}`}>
      <div className={styles.questionNumber}>{questionNumber}/{TOTAL}</div>
      <p className={styles.ne}>हजुरको मातृभाषा कुन हो?</p>
      <p className={styles.en}>What is your native language?</p>
      <div className={styles.langGrid}>
        {LANGUAGES.slice(0, 12).map((l) => (
          <button
            key={l}
            className={`${styles.chip} ${draft.native_language === l ? styles.chipActive : ""}`}
            onClick={() => { set("native_language", l); next(); }}
          >
            {l}
          </button>
        ))}
      </div>
      <div className={styles.buttonGroup}>
        <button className={styles.btnSecondary} onClick={prev}>पछाडि</button>
      </div>
    </div>,

    // 4 — Other languages
    <div key="other_langs" className={`${styles.step} ${direction === "forward" ? styles.slideInForward : styles.slideInBackward}`}>
      <div className={styles.questionNumber}>{questionNumber}/{TOTAL}</div>
      <p className={styles.ne}>हजुरलाई अरु कुन कुन भाषा आउँछ?</p>
      <p className={styles.en}>What other languages do you know? (optional)</p>
      <input
        className={styles.input}
        placeholder="खोज्नुहोस् · Search…"
        value={langSearch}
        onChange={(e) => setLangSearch(e.target.value)}
      />
      <div className={styles.langGrid}>
        {filteredLangs
          .filter((l) => l !== draft.native_language)
          .map((l) => (
            <button
              key={l}
              className={`${styles.chip} ${draft.other_languages.includes(l) ? styles.chipActive : ""}`}
              onClick={() =>
                set(
                  "other_languages",
                  draft.other_languages.includes(l)
                    ? draft.other_languages.filter((x) => x !== l)
                    : [...draft.other_languages, l]
                )
              }
            >
              {l}
            </button>
          ))}
      </div>
      <div className={styles.buttonGroup}>
        <button className={styles.btnSecondary} onClick={prev}>पछाडि</button>
        <button className={styles.btn} onClick={next}>
          अगाडि
        </button>
      </div>
    </div>,

    // 5 — Gender
    <div key="gender" className={`${styles.step} ${direction === "forward" ? styles.slideInForward : styles.slideInBackward}`}>
      <div className={styles.questionNumber}>{questionNumber}/{TOTAL}</div>
      <p className={styles.ne}>हजुरको लिंग के हो?</p>
      <p className={styles.en}>What is your gender?</p>
      <div className={styles.choiceGroup}>
        {(["male", "female", "other"] as const).map((g) => {
          const labels: Record<string, { ne: string; en: string }> = {
            male:   { ne: "पुरुष", en: "Male" },
            female: { ne: "महिला", en: "Female" },
            other:  { ne: "अन्य", en: "Other / prefer not to say" },
          };
          return (
            <button
              key={g}
              className={`${styles.choice} ${draft.gender === g ? styles.choiceActive : ""}`}
              onClick={() => { set("gender", g); next(); }}
            >
              <span className={styles.ne}>{labels[g].ne}</span>
              <span className={styles.en}>{labels[g].en}</span>
            </button>
          );
        })}
      </div>
      <div className={styles.buttonGroup}>
        <button className={styles.btnSecondary} onClick={prev}>पछाडि</button>
      </div>
    </div>,

    // 6 — City / village (searchable)
    <div key="city" className={`${styles.step} ${direction === "forward" ? styles.slideInForward : styles.slideInBackward}`}>
      <div className={styles.questionNumber}>{questionNumber}/{TOTAL}</div>
      <p className={styles.ne}>हजुर कुन ठाउँमा हुर्कनु भयो?</p>
      <p className={styles.en}>Which city or village did you grow up in?</p>
      <input
        className={styles.input}
        autoFocus
        placeholder="खोज्नुहोस्… Kathmandu, Pokhara, etc."
        value={citySearch}
        onChange={(e) => setCitySearch(e.target.value)}
      />
      <div className={styles.langGrid}>
        {filteredCities.map((city) => (
          <button
            key={city}
            className={`${styles.chip} ${draft.city_or_village === city ? styles.chipActive : ""}`}
            onClick={() => { set("city_or_village", city); next(); }}
          >
            {city}
          </button>
        ))}
      </div>
      <div className={styles.buttonGroup}>
        <button className={styles.btnSecondary} onClick={prev}>पछाडि</button>
      </div>
    </div>,

    // 7 — Education
    <div key="edu" className={`${styles.step} ${direction === "forward" ? styles.slideInForward : styles.slideInBackward}`}>
      <div className={styles.questionNumber}>{questionNumber}/{TOTAL}</div>
      <p className={styles.ne}>हजुरको शिक्षाको स्तर के हो?</p>
      <p className={styles.en}>What is your education level?</p>
      <div className={styles.choiceGroup}>
        {EDUCATION_LEVELS.map((e) => (
          <button
            key={e.en}
            className={`${styles.choice} ${draft.education_level === e.en ? styles.choiceActive : ""}`}
            onClick={() => { set("education_level", e.en); }}
          >
            <span className={styles.ne}>{e.ne}</span>
            <span className={styles.en}>{e.en}</span>
          </button>
        ))}
      </div>
      <div className={styles.buttonGroup}>
        <button className={styles.btnSecondary} onClick={prev}>पछाडि</button>
        <button
          className={styles.btn}
          disabled={!draft.education_level || submitting}
          onClick={() => {
            console.log("Submitting onboarding:", draft);
            finish();
          }}
        >
          {submitting ? "सुरु हुँदैछ…" : "सुरु गरौं"}
        </button>
      </div>
    </div>,
  ];

  return (
    <div className={styles.root}>
      <div className={styles.container}>
        <div className={styles.card}>{steps[step]}</div>
      </div>
    </div>
  );
}
