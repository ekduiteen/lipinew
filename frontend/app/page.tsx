import Link from "next/link";

export default function LandingPage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "var(--space-6)",
        padding: "var(--space-8) var(--space-6)",
        background: "var(--bg)",
      }}
    >
      <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
        <h1
          style={{
            fontFamily: "var(--font-nepali)",
            fontSize: "clamp(3rem, 12vw, 5.5rem)",
            fontWeight: 700,
            letterSpacing: "-0.02em",
            color: "var(--fg)",
            lineHeight: 1,
          }}
        >
          लिपि
        </h1>
        <p
          style={{
            fontFamily: "var(--font-nepali)",
            fontSize: "var(--text-body)",
            color: "var(--fg)",
          }}
        >
          तपाईं बोल्नुहोस्। लिपि सिक्छ। भाषा बाँच्छ।
        </p>
        <p
          style={{
            fontFamily: "var(--font-latin)",
            fontSize: "var(--text-sm)",
            color: "var(--fg-muted)",
          }}
        >
          You speak. LIPI learns. Language lives.
        </p>
      </div>

      <Link
        href="/auth"
        className="btn-primary"
        style={{ textDecoration: "none", marginTop: "var(--space-4)" }}
      >
        सुरु गर्नुहोस् · Get started
      </Link>
    </main>
  );
}
