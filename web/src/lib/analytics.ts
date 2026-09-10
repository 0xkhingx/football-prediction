"use client";

/**
 * Privacy-friendly analytics wrapper (Plausible). No-ops unless
 * NEXT_PUBLIC_PLAUSIBLE_DOMAIN is set, so dev stays clean and no
 * cookie consent is needed. Events carry buckets/leagues only — never
 * personal data (there is none in this app).
 */

declare global {
  interface Window {
    plausible?: (event: string, options?: { props?: Record<string, string | number> }) => void;
  }
}

export function trackEvent(event: string, props?: Record<string, string | number>): void {
  try {
    window.plausible?.(event, props ? { props } : undefined);
  } catch {
    /* analytics must never break the app */
  }
}

/** Buckets a 0-1 confidence for privacy-lean event props. */
export function confBucket(confidence: number): string {
  if (confidence >= 0.7) return "70+";
  if (confidence >= 0.6) return "60-70";
  if (confidence >= 0.5) return "50-60";
  if (confidence >= 0.45) return "45-50";
  return "<45";
}
