/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["three"],
  eslint: {
    // Lint is run explicitly via `npm run lint`; don't block production builds on it.
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
