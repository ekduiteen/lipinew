"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getDashboardOverview,
  type DashboardOverview,
} from "@/lib/api";
import styles from "./dashboard.module.css";

export default function DashboardPage() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboardOverview()
      .then(setOverview)
      .catch((err: Error) => setError(err.message));
  }, []);

  if (error) {
    return (
      <div className={styles.root}>
        <Link href="/settings" className={styles.backLink}>← Back</Link>
        <h1 className={styles.titleNe}>ड्यासबोर्ड</h1>
        <p className={styles.titleEn}>Dashboard</p>
        <div className={styles.errorBox}>{error}</div>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className={styles.root}>
        <Link href="/settings" className={styles.backLink}>← Back</Link>
        <h1 className={styles.titleNe}>ड्यासबोर्ड</h1>
        <p className={styles.titleEn}>Dashboard</p>
        <div className={styles.loading}>Loading live system report...</div>
      </div>
    );
  }

  const languageEntries = Object.entries(overview.quality.recent_teacher_language_counts);

  return (
    <div className={styles.root}>
      <Link href="/settings" className={styles.backLink}>← Back</Link>
      <h1 className={styles.titleNe}>ड्यासबोर्ड</h1>
      <p className={styles.titleEn}>System, data, and quality report</p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>System</h2>
        <div className={styles.statusGrid}>
          {Object.entries(overview.system).map(([key, value]) => (
            <div key={key} className={styles.card}>
              <div className={styles.cardTop}>
                <span className={styles.cardLabel}>{key}</span>
                <span className={`${styles.badge} ${value.ok ? styles.ok : styles.bad}`}>
                  {value.ok ? "OK" : "Issue"}
                </span>
              </div>
              <pre className={styles.detail}>
                {value.detail ? JSON.stringify(value.detail, null, 2) : "No extra details"}
              </pre>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Queues</h2>
        <div className={styles.metricGrid}>
          <Metric label="Pending" value={overview.queues.pending} />
          <Metric label="Processing" value={overview.queues.processing} />
          <Metric label="Dead letter" value={overview.queues.dead_letter} />
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Collection</h2>
        <div className={styles.metricGrid}>
          <Metric label="Sessions" value={overview.data.total_sessions} />
          <Metric label="Messages" value={overview.data.total_messages} />
          <Metric label="Teacher turns" value={overview.data.total_teacher_turns} />
          <Metric label="LIPI turns" value={overview.data.total_lipi_turns} />
          <Metric label="Vocabulary" value={overview.data.total_vocabulary_entries} />
          <Metric
            label="Avg STT conf"
            value={overview.data.avg_stt_confidence?.toFixed(3) ?? "n/a"}
          />
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Quality</h2>
        <div className={styles.metricGrid}>
          <Metric label="Low-conf turns" value={overview.quality.recent_low_confidence_turns} />
          <Metric label="Eligible turns" value={overview.quality.recent_learning_eligible_turns} />
          <Metric label="Confused replies" value={overview.quality.recent_confused_replies} />
          <Metric label="Hindi-mixed replies" value={overview.quality.recent_hindi_mixed_replies} />
        </div>
        <div className={styles.languageRow}>
          {languageEntries.map(([lang, count]) => (
            <span key={lang} className={styles.languageChip}>{lang}: {count}</span>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Recent Samples</h2>
        <div className={styles.sampleList}>
          {overview.recent_samples.map((sample, idx) => (
            <div key={`${sample.teacher_text}-${idx}`} className={styles.sampleCard}>
              <div className={styles.sampleMeta}>
                <span>{sample.teacher_language ?? "unknown"}</span>
                <span>{sample.stt_confidence?.toFixed(3) ?? "n/a"}</span>
              </div>
              <p className={styles.teacherText}>{sample.teacher_text}</p>
              <p className={styles.lipiText}>{sample.lipi_text}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className={styles.metricCard}>
      <span className={styles.metricValue}>{value}</span>
      <span className={styles.metricLabel}>{label}</span>
    </div>
  );
}
