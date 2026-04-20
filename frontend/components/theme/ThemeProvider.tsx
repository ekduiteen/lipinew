"use client";

import { createContext, useContext, useEffect, useState } from "react";

export type Theme = "bone" | "lavender" | "sage" | "warm" | "ink";

const THEMES: Theme[] = ["bone", "lavender", "sage", "warm", "ink"];

const THEME_LABELS: Record<Theme, { ne: string; en: string }> = {
  bone:     { ne: "हड्डी",    en: "Bone" },
  lavender: { ne: "बैजनी",   en: "Lavender" },
  sage:     { ne: "हरियो",   en: "Sage" },
  warm:     { ne: "न्यानो",  en: "Warm" },
  ink:      { ne: "मसी",     en: "Ink" },
};

const THEME_ORB: Record<Theme, { a: string; b: string; c: string }> = {
  bone:     { a: "#C6B5F0", b: "#B6D6F5", c: "#F3DFA8" },
  lavender: { a: "#B49BF0", b: "#D6C8F8", c: "#C0DCC0" },
  sage:     { a: "#A8CCA8", b: "#C0DCC0", c: "#C8C0E0" },
  warm:     { a: "#E8C298", b: "#D4C8E8", c: "#C8DDB4" },
  ink:      { a: "#7B6CE8", b: "#8F59D8", c: "#E85B9A" },
};

const STORAGE_KEY = "lipi.theme";

const VALID_THEMES = new Set<string>(THEMES);

function resolveStoredTheme(stored: string | null): Theme {
  if (stored && VALID_THEMES.has(stored)) return stored as Theme;
  // Migrate legacy theme names
  if (stored === "pastel") return "bone";
  if (stored === "dark") return "ink";
  return "bone";
}

type Ctx = {
  theme: Theme;
  setTheme: (t: Theme) => void;
  themes: Theme[];
  label: (t: Theme) => { ne: string; en: string };
  orb: (t: Theme) => { a: string; b: string; c: string };
};

const ThemeCtx = createContext<Ctx | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window === "undefined") return "bone";
    const attr = document.documentElement.getAttribute("data-theme");
    return resolveStoredTheme(attr);
  });

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    const resolved = resolveStoredTheme(stored);
    if (resolved !== theme) {
      setThemeState(resolved);
      document.documentElement.setAttribute("data-theme", resolved);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setTheme = (t: Theme) => {
    setThemeState(t);
    localStorage.setItem(STORAGE_KEY, t);
    document.documentElement.setAttribute("data-theme", t);
  };

  return (
    <ThemeCtx.Provider
      value={{
        theme,
        setTheme,
        themes: THEMES,
        label: (t) => THEME_LABELS[t],
        orb: (t) => THEME_ORB[t],
      }}
    >
      {children}
    </ThemeCtx.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeCtx);
  if (!ctx) throw new Error("useTheme must be used inside ThemeProvider");
  return ctx;
}
