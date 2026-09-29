/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // VIZHI technical command-center design tokens
        bg: "#090A08",
        surface: "#111210",
        surface2: "#171816",
        accent: "#84E600",
        danger: "#FF6B6B",
        safe: "#9BEA63",
        text: "#F4F4F0",
        muted: "#A3A39D",
        // severity scale (LOW -> CRITICAL)
        sev: {
          low: "#9BEA63",
          medium: "#F5C451",
          high: "#FF8A5B",
          critical: "#FF6B6B",
        },
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "system-ui", "sans-serif"],
        mono: ["Fira Code", "Cascadia Code", "Consolas", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(255,255,255,0.01), 0 18px 42px rgba(0,0,0,0.28)",
      },
    },
  },
  plugins: [],
};
