import type { Metadata, Viewport } from "next";
import { ThemeProvider } from "@/components/theme/ThemeProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "LIPI — लिपि",
  description: "You speak. LIPI learns. Language lives.",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  themeColor: "#0a0a0f",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ne" suppressHydrationWarning>
      <body>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
