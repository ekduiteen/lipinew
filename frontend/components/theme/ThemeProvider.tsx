"use client";

import { createContext, useContext, useEffect, useState } from "react";

export type Theme = "pastel" | "warm" | "lavender" | "sage" | "dark";

const THEMES: Theme[] = ["pastel", "warm", "lavender", "sage", "dark"];
const THEME_LABELS: Record<Theme, { ne: string; en: string }> = {
  pastel:   { ne: "पेस्टल",   en: "Pastel Light" },
  warm:     { ne: "न्यानो",   en: "Warm Cream" },
  lavender: { ne: "बैजनी",    en: "Lavender Mist" },
  sage:     { ne: "हरियो",    en: "Sage Air" },
  dark:     { ne: "अँध्यारो", en: "Dark" },
};

const STORAGE_KEY = "lipi.theme";

type Ctx = {
  theme: Theme;
  setTheme: (t: Theme) => void;
  themes: Theme[];
  label: (t: Theme) => { ne: string; en: string };
};

const ThemeCtx = createContext<Ctx | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  // Read directly from the DOM attribute (already set by the blocking script)
  // so state is correct from the first render — no flash, no useEffect setState.
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window === "undefined") return "pastel";
    const attr = document.documentElement.getAttribute("data-theme") as Theme | null;
    return THEMES.includes(attr as Theme) ? (attr as Theme) : "pastel";
  });

  useEffect(() => {
    // Sync in case the blocking script missed (e.g., localStorage blocked)
    const stored = (localStorage.getItem(STORAGE_KEY) as Theme | null) ?? "pastel";
    if (stored !== theme) {
      setThemeState(stored);
      document.documentElement.setAttribute("data-theme", stored);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setTheme = (t: Theme) => {
    setThemeState(t);
    localStorage.setItem(STORAGE_KEY, t);
    document.documentElement.setAttribute("data-theme", t);
  };

  return (
    <ThemeCtx.Provider value={{ theme, setTheme, themes: THEMES, label: (t) => THEME_LABELS[t] }}>
      {children}
    </ThemeCtx.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeCtx);
  if (!ctx) throw new Error("useTheme must be used inside ThemeProvider");
  return ctx;
}
