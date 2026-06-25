/** @type {import('tailwindcss').Config} */
//
// "Daylight" design system — a calm, hand-crafted light theme.
// Warm parchment canvas, paper-white cards, sage + clay accents, earthy status
// colors. We remap Tailwind's default scales (slate/emerald/red/...) to soothing,
// desaturated tones so the whole app inherits the palette cohesively. Type pairs
// an editorial serif (Fraunces) for display with a warm grotesque (Hanken) for UI.
//
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Fraunces"', "ui-serif", "Georgia", "serif"],
        sans: ['"Hanken Grotesk"', "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ['"Spline Sans Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      colors: {
        // Surfaces (component code uses these `ink` tokens for bg/border).
        ink: {
          900: "#f3eee4", // app canvas — warm parchment
          800: "#fffdf8", // card surface — warm white (raised on the canvas)
          700: "#ece4d4", // nested / hover surface
          600: "#e4dccb", // hairline border
        },
        accent: "#6f8f6a", // sage — primary accent
        "accent-deep": "#566f52",
        clay: "#c08457", // terracotta — secondary accent
        // Warm ink text scale (overrides Tailwind `slate`, inverted for light bg:
        // slate-100 = darkest heading ink … slate-500 = faintest).
        slate: {
          100: "#2b2922",
          200: "#3c382f",
          300: "#544f40",
          400: "#7c7560",
          500: "#9b927b",
          600: "#b4ab93",
          700: "#cabfa6",
          800: "#e4dccb",
          900: "#f1ebdf",
        },
        // Earthy status palettes (soft tints via /10–/30 read as pastel chips).
        emerald: { 300: "#4f6f4a", 400: "#6f8f6a", 500: "#7a9a6f" },
        red: { 300: "#a9534a", 400: "#b5524a", 500: "#b5524a" },
        orange: { 300: "#b06a3f", 400: "#c08457", 500: "#c08457" },
        amber: { 300: "#9a7528", 400: "#bf972f", 500: "#c59a3f" },
        yellow: { 300: "#937025", 400: "#bf972f", 500: "#c59a3f" },
        sky: { 300: "#557591", 400: "#5b7a99", 500: "#5b7a99" },
        violet: { 300: "#7a6790", 400: "#8a76a3", 500: "#8a76a3" },
      },
      borderRadius: {
        xl: "0.9rem",
        "2xl": "1.25rem",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(72,58,30,0.04), 0 1px 1px rgba(72,58,30,0.03)",
        card: "0 1px 2px rgba(72,58,30,0.04), 0 10px 28px -12px rgba(72,58,30,0.10)",
        lift: "0 2px 4px rgba(72,58,30,0.05), 0 18px 40px -16px rgba(72,58,30,0.16)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.55" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.5s cubic-bezier(0.22, 1, 0.36, 1) both",
        "fade-in": "fade-in 0.6s ease both",
        "pulse-soft": "pulse-soft 2.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
