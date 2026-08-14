/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./docs/**/*.html"],
  theme: {
    extend: {
      colors: {
        ink: "#14213D",
        signal: "#E86A33",
        mist: "#F4F7F5",
        leaf: "#2F6B57",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "Segoe UI", "sans-serif"],
        mono: ["Cascadia Code", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
