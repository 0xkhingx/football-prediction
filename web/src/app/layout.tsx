import type { Metadata, Viewport } from "next";
import { Anton, IBM_Plex_Mono, Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const display = Anton({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-display",
});

const mono = IBM_Plex_Mono({
  weight: ["400", "500", "600"],
  subsets: ["latin"],
  variable: "--font-mono",
});

const sans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: {
    default: "Matchday Fate — fair-play football predictor",
    template: "%s · Matchday Fate",
  },
  description:
    "Every fixture has a fate. Fair-play XGBoost reads 23 pre-match signals — no odds. Research demo, not betting advice.",
};

export const viewport: Viewport = {
  themeColor: "#E85A24",
};

const NAV_LINK = "font-mono text-[11px] tracking-[0.2em] text-ember hover:text-coal";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${mono.variable} ${sans.variable}`}>
      <body className="pinstripes min-h-screen font-sans text-coal" suppressHydrationWarning>
        <a
          href="#content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-coal focus:px-4 focus:py-2 focus:font-mono focus:text-xs focus:text-cream"
        >
          Skip to content
        </a>
        <div className="relative z-10 mx-auto max-w-6xl px-3 py-4 sm:px-6">
          <nav className="flex items-center justify-between rounded-full bg-cream px-5 py-3 sm:px-8">
            <div className="flex gap-4 sm:gap-8">
              <Link href="/" className={NAV_LINK}>
                Fixtures
              </Link>
              <Link href="/predict" className={NAV_LINK}>
                Predict
              </Link>
            </div>
            <Link href="/" className="font-display text-sm tracking-wide text-ember sm:text-lg">
              MATCHDAY FATE
            </Link>
            <div className="flex gap-4 sm:gap-8">
              <Link href="/simulator" className={NAV_LINK}>
                Simulator
              </Link>
              <Link href="/model" className={NAV_LINK}>
                Model
              </Link>
            </div>
          </nav>
          <main id="content" className="mt-3">{children}</main>
          <footer>
            <p className="py-6 text-center font-mono text-[10px] tracking-[0.3em] text-cream/90">
              MATCHDAY FATE — FAIR-PLAY XGB · NO ODDS · NOT BETTING ADVICE
            </p>
          </footer>
        </div>
      </body>
    </html>
  );
}
