import type { Metadata, Viewport } from "next";
import Script from "next/script";
import localFont from "next/font/local";
import { IBM_Plex_Mono, Nunito_Sans } from "next/font/google";
import { NavBar } from "@/components/NavBar";
import "./globals.css";

// Headers: BespokeStencil, self-hosted from src/fonts (Fontshare FFL license,
// free for commercial use). Variable file covers weights 300–800 in one 38KB
// download; display type defaults to bold (see .font-display in globals.css)
// to keep the poster's heavy feel that Anton used to give us.
const display = localFont({
  src: "../fonts/BespokeStencil-Variable.woff2",
  variable: "--font-display",
  weight: "300 800",
  display: "swap",
});

const mono = IBM_Plex_Mono({
  weight: ["400", "500", "600"],
  subsets: ["latin"],
  variable: "--font-mono",
});

const sans = Nunito_Sans({
  weight: ["400", "500", "600", "700"],
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
  width: "device-width",
  initialScale: 1,
  themeColor: "#2563EB",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${mono.variable} ${sans.variable}`}>
      <body className="pinstripes min-h-screen font-sans text-coal" suppressHydrationWarning>
        {process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN && (
          <Script
            defer
            data-domain={process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN}
            src="https://plausible.io/js/script.js"
          />
        )}
        <a
          href="#content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-coal focus:px-4 focus:py-2 focus:font-mono focus:text-xs focus:text-cream"
        >
          Skip to content
        </a>
        <div className="relative z-10 mx-auto max-w-6xl px-3 py-4 sm:px-6">
          <NavBar />
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
