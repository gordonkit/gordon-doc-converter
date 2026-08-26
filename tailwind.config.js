/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./docs-src/**/*.{html,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17202e",
        signal: "#c64b2b",
        mist: "#f6f7f8",
        leaf: "#19715b",
      },
      fontFamily: {
        sans: ["Bahnschrift", "Noto Sans TC", "Noto Sans JP", "Segoe UI", "sans-serif"],
        mono: ["IBM Plex Mono", "Cascadia Code", "Consolas", "monospace"],
      },
    },
  },
  darkMode: "class",
  plugins: [],
};
