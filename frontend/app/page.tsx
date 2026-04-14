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
        gap: "2rem",
        padding: "2rem",
      }}
    >
      <h1 style={{ fontSize: "4rem", fontWeight: 700, letterSpacing: "-0.02em" }}>
        लिपि
      </h1>
      <p style={{ fontSize: "1.25rem", textAlign: "center", maxWidth: "32rem" }}>
        तपाईं बोल्नुहोस्। लिपि सिक्छ। भाषा बाँच्छ।
      </p>
      <p
        className="text-latin"
        style={{ fontSize: "1rem", textAlign: "center", maxWidth: "32rem" }}
      >
        You speak. LIPI learns. Language lives.
      </p>
      <Link
        href="/auth"
        style={{
          background: "var(--accent)",
          color: "var(--bg)",
          padding: "0.875rem 2rem",
          borderRadius: "var(--radius-full)",
          fontWeight: 600,
          textDecoration: "none",
        }}
      >
        सुरु गर्नुहोस् · Get started
      </Link>
    </main>
  );
}
