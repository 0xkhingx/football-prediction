import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ember: "#E85A24",
        emberdark: "#C7481B",
        cream: "#FAF5EC",
        coal: "#161412",
        lime: "#E7EF45",
        home: "#1E9E4A",
        draw: "#E85A24",
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
