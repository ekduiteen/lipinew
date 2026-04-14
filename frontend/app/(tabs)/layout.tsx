import BottomNav from "@/components/ui/BottomNav";
import styles from "./tabs.module.css";

export default function TabsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className={styles.root}>
      <main className={styles.main}>{children}</main>
      <BottomNav />
    </div>
  );
}
