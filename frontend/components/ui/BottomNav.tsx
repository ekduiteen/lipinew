"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./BottomNav.module.css";

const TABS = [
  { href: "/home",     labelNe: "गृह",    labelEn: "Home",     icon: "⌂" },
  { href: "/teach",    labelNe: "सिकाउ",  labelEn: "Teach",    icon: "◎" },
  { href: "/ranks",    labelNe: "रैंक",   labelEn: "Ranks",    icon: "⬡" },
  { href: "/settings", labelNe: "सेटिङ", labelEn: "Settings", icon: "⚙" },
] as const;

export default function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className={styles.nav}>
      {TABS.map((tab) => {
        const active = pathname.startsWith(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`${styles.tab} ${active ? styles.active : ""}`}
          >
            <span className={styles.icon}>{tab.icon}</span>
            <span className={styles.labelNe}>{tab.labelNe}</span>
            <span className={styles.labelEn}>{tab.labelEn}</span>
          </Link>
        );
      })}
    </nav>
  );
}
