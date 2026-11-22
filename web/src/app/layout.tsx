import type { Metadata, Viewport } from "next";
import { Atkinson_Hyperlegible_Next, IBM_Plex_Mono } from "next/font/google";

import { AppHeader } from "@/components/app-header";
import { ServiceWorkerRegistration } from "@/components/service-worker-registration";

import "./globals.css";
import { Providers } from "./providers";

// Atkinson Hyperlegible: drawn for legibility, with distinct diacritics,
// for long cataloguing sessions. Self-hosted by next/font at build time.
const atkinson = Atkinson_Hyperlegible_Next({
  variable: "--font-atkinson",
  subsets: ["latin", "latin-ext"],
  weight: ["400", "600", "700"],
  // Next.js has no metric overrides for this newer family, so it cannot build
  // a size-adjusted fallback; the system sans-serif stands in while it loads.
  adjustFontFallback: false,
  fallback: ["system-ui", "sans-serif"],
});

// Only for MARC fields, where tags, indicators and subfields must align.
const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin", "latin-ext"],
  weight: ["400", "600", "700"],
});

export const metadata: Metadata = {
  title: { default: "Faísca", template: "%s – Faísca" },
  description: "Pesquisa de registos bibliográficos em UNIMARC e de cópias digitais.",
  applicationName: "Faísca",
  appleWebApp: { capable: true, title: "Faísca", statusBarStyle: "default" },
  icons: { icon: "/icon.svg", apple: "/icons/apple-touch-icon.png" },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#2341a8" },
    { media: "(prefers-color-scheme: dark)", color: "#0f1626" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-PT" className={`${atkinson.variable} ${plexMono.variable}`}>
      <body className="min-h-dvh antialiased">
        <Providers>
          <AppHeader />
          <main className="mx-auto w-full max-w-6xl px-4 pb-16 pt-6 sm:px-6">{children}</main>
        </Providers>
        <ServiceWorkerRegistration />
      </body>
    </html>
  );
}
