/** @type {import('next').NextConfig} */
import { withSentryConfig } from "@sentry/nextjs";

const isProd = process.env.NODE_ENV === "production";
const csp = [
  "default-src 'self'",
  "img-src 'self' data: blob:",
  // unsafe-eval: dev-only (Next dev runtime needs it); never in production.
  `script-src 'self' 'unsafe-inline'${isProd ? "" : " 'unsafe-eval'"} https://plausible.io`,
  "style-src 'self' 'unsafe-inline'",
  "font-src 'self' data:",
  "connect-src 'self' https://plausible.io https://*.sentry.io",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");

const nextConfig = {
  reactStrictMode: true,
  eslint: {
    // Lint is run explicitly via `npm run lint`; don't block production builds on it.
    ignoreDuringBuilds: true,
  },
  async headers() {
    const base = [
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
      { key: "X-Frame-Options", value: "DENY" },
      { key: "Content-Security-Policy", value: csp },
    ];
    // HSTS only when serving HTTPS (Render/Vercel do; localhost doesn't).
    if (process.env.HTTPS === "1") {
      base.push({ key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" });
    }
    return [{ source: "/:path*", headers: base }];
  },
};

export default withSentryConfig(nextConfig, {
  // Source maps for readable stack traces; no behavior change.
  widenClientFileUpload: true,
  hideSourceMaps: true,
  disableLogger: true,
});
