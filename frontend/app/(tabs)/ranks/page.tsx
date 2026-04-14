"use client";

import { useEffect, useState } from "react";
import { getLeaderboard, type LeaderboardEntry } from "@/lib/api";
import styles from "./ranks.module.css";

type Period = "weekly" | "monthly" | "all_time";

const PERIOD_LABELS: Record<Period, { ne: string; en: string }> = {
  weekly:   { ne: "साप्ताहिक", en: "Weekly" },
  monthly:  { ne: "मासिक",    en: "Monthly" },
  all_time: { ne: "सबै",      en: "All time" },
};

export default function RanksPage() {
  const [period, setPeriod] = useState<Period>("weekly");
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getLeaderboard(period)
      .then(setEntries)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [period]);

  return (
    <div className={styles.root}>
      <h1 className={styles.titleNe}>शीर्ष शिक्षकहरू</h1>
      <p className={styles.titleEn}>Top Teachers</p>

      <div className={styles.tabs}>
        {(Object.keys(PERIOD_LABELS) as Period[]).map((p) => (
          <button
            key={p}
            className={`${styles.tab} ${period === p ? styles.tabActive : ""}`}
            onClick={() => setPeriod(p)}
          >
            <span>{PERIOD_LABELS[p].ne}</span>
            <span className={styles.tabEn}>{PERIOD_LABELS[p].en}</span>
          </button>
        ))}
      </div>

      {loading ? (
        <p className={styles.loading}>लोड हुँदैछ…</p>
      ) : (
        <ol className={styles.list}>
          {entries.map((e) => (
            <li key={e.rank} className={`${styles.item} ${e.rank <= 3 ? styles.podium : ""}`}>
              <span className={styles.rank}>{e.rank <= 3 ? ["🥇","🥈","🥉"][e.rank - 1] : e.rank}</span>
              <span className={styles.avatar}>{e.avatar_initial}</span>
              <span className={styles.name}>{e.name}</span>
              <span className={styles.pts}>{e.points.toLocaleString()} pts</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
