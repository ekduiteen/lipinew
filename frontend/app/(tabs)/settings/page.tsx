"use client";

import Link from "next/link";
import { useTheme, type Theme } from "@/components/theme/ThemeProvider";
import Orb from "@/components/orb/Orb";
import styles from "./settings.module.css";

const THEME_META: Record<Theme, { ne: string; en: string }> = {
  dark:        { ne: "गाढा",       en: "Dark" },
  bright:      { ne: "उज्यालो",   en: "Bright" },
  cyberpunk:   { ne: "साइबरपंक", en: "Cyber Punk" },
  traditional: { ne: "परम्परागत", en: "Traditional" },
};

export default function SettingsPage() {
  const { theme, setTheme, themes } = useTheme();

  return (
    <div className={styles.root}>
      <h1 className={styles.titleNe}>सेटिङ</h1>
      <p className={styles.titleEn}>Settings</p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitleNe}>थिम</h2>
        <p className={styles.sectionTitleEn}>Theme</p>

        <div className={styles.themeGrid}>
          {themes.map((t) => (
            <button
              key={t}
              className={`${styles.themeCard} ${theme === t ? styles.themeActive : ""}`}
              data-theme={t}
              onClick={() => setTheme(t)}
            >
              {/* Live orb preview using that theme's CSS vars */}
              <div data-theme={t} className={styles.previewScope}>
                <Orb state="idle" size={60} />
              </div>
              <span className={styles.themeNe}>{THEME_META[t].ne}</span>
              <span className={styles.themeEn}>{THEME_META[t].en}</span>
              {theme === t && <span className={styles.checkmark}>✓</span>}
            </button>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitleNe}>सिस्टम ड्यासबोर्ड</h2>
        <p className={styles.sectionTitleEn}>System dashboard</p>

        <Link href="/settings/dashboard" className={styles.dashboardLink}>
          <span className={styles.dashboardNe}>स्थिति, डेटा, र प्रतिवेदन हेर्नुहोस्</span>
          <span className={styles.dashboardEn}>View status, data, and reports</span>
        </Link>
      </section>
    </div>
  );
}
