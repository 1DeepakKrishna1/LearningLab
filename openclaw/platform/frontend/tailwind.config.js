/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#6366F1",
          dark: "#4F46E5",
        },
      },
    },
  },
  // MUI also injects styles; disable Tailwind's preflight to avoid clashes.
  corePlugins: { preflight: false },
  plugins: [],
};
