import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // NOTE: token names predate the blue rebrand; ember/emberdark now hold blues.
        ember: "#2563EB",
        emberdark: "#1E40AF",
        cream: "#FAF5EC",
        coal: "#161412",
        lime: "#E7EF45",
        home: "#1E9E4A",
        draw: "#F59E0B",
        away: "#D92D20",
      },
      fontFamily: {
        display: ["var(--font-display)", "Impact", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
        sans: ["var(--font-sans)", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
