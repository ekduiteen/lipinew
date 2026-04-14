"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getMyStats, getLeaderboard, type TeacherStats, type LeaderboardEntry } from "@/lib/api";
import styles from "./home.module.css";

export default function HomePage() {
  const [stats, setStats] = useState<TeacherStats | null>(null);
  const [leaders, setLeaders] = useState<LeaderboardEntry[]>([]);

  useEffect(() => {
    getMyStats().then(setStats).catch(() => {});
    getLeaderboard("weekly").then((l) => setLeaders(l.slice(0, 3))).catch(() => {});
  }, []);

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <h1 className={styles.logo}>लिपि</h1>
        <p className={styles.tagline}>You speak. LIPI learns. Language lives.</p>
      </header>

      {/* Stats row */}
      {stats && (
        <div className={styles.statsRow}>
          <Stat ne="अंक" en="Points" value={stats.total_points.toLocaleString()} />
          <Stat ne="दिन" en="Streak" value={`${stats.current_streak}🔥`} />
          <Stat ne="शब्द" en="Words" value={stats.words_taught.toLocaleString()} />
          <Stat ne="रैंक" en="Rank" value={`#${stats.rank}`} />
        </div>
      )}

      {/* CTA */}
      <Link href="/teach" className={styles.cta}>
        <span className={styles.ctaNe}>सिकाउन सुरु गर्नुहोस्</span>
        <span className={styles.ctaEn}>Start teaching</span>
      </Link>

      {/* Mini leaderboard */}
      {leaders.length > 0 && (
        <section className={styles.leaderSection}>
          <div className={styles.leaderHeader}>
            <span className={styles.leaderTitleNe}>शीर्ष शिक्षकहरू</span>
            <Link href="/ranks" className={styles.leaderLink}>सबै हेर्नुहोस् · See all</Link>
          </div>
          <ol className={styles.leaderList}>
            {leaders.map((l) => (
              <li key={l.rank} className={styles.leaderItem}>
                <span className={styles.leaderRank}>{l.rank}</span>
                <span className={styles.leaderAvatar}>{l.avatar_initial}</span>
                <span className={styles.leaderName}>{l.name}</span>
                <span className={styles.leaderPts}>{l.points.toLocaleString()} pts</span>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}

function Stat({ ne, en, value }: { ne: string; en: string; value: string }) {
  return (
    <div className={styles.stat}>
      <span className={styles.statValue}>{value}</span>
      <span className={styles.statNe}>{ne}</span>
      <span className={styles.statEn}>{en}</span>
    </div>
  );
}
