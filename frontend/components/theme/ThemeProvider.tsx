"use client";

import { createContext, useContext, useEffect, useState } from "react";

export type Theme = "dark" | "bright" | "cyberpunk" | "traditional";

const THEMES: Theme[] = ["dark", "bright", "cyberpunk", "traditional"];
const STORAGE_KEY = "lipi.theme";

type Ctx = { theme: Theme; setTheme: (t: Theme) => void; themes: Theme[] };
const ThemeCtx = createContext<Ctx | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("dark");

  useEffect(() => {
    const stored = (localStorage.getItem(STORAGE_KEY) as Theme | null) ?? "dark";
    setThemeState(stored);
    document.documentElement.setAttribute("data-theme", stored);
  }, []);

  const setTheme = (t: Theme) => {
    setThemeState(t);
    localStorage.setItem(STORAGE_KEY, t);
    document.documentElement.setAttribute("data-theme", t);
  };

  return (
    <ThemeCtx.Provider value={{ theme, setTheme, themes: THEMES }}>
      {children}
    </ThemeCtx.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeCtx);
  if (!ctx) throw new Error("useTheme must be used inside ThemeProvider");
  return ctx;
}
