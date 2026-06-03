/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          900: "#0a0e17",
          800: "#0f1523",
          700: "#161d2e",
          600: "#1e2740",
        },
        accent: "#5b8cff",
      },
    },
  },
  plugins: [],
};
