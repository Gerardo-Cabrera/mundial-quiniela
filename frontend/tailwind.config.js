/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ucl: {
          navy:   "#0a1628",
          blue:   "#1a3a6b",
          gold:   "#c9a84c",
          silver: "#8a9bb0",
          white:  "#f0f4ff",
        },
      },
      fontFamily: {
        display: ["'Bebas Neue'", "sans-serif"],
        body:    ["'DM Sans'", "sans-serif"],
        mono:    ["'JetBrains Mono'", "monospace"],
      },
      backgroundImage: {
        "ucl-gradient": "linear-gradient(135deg, #0a1628 0%, #1a3a6b 50%, #0a1628 100%)",
        "gold-gradient": "linear-gradient(90deg, #c9a84c, #f0d080, #c9a84c)",
      },
      animation: {
        "fade-in":    "fadeIn 0.4s ease-out",
        "slide-up":   "slideUp 0.4s ease-out",
        "pulse-gold": "pulseGold 2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn:    { from: { opacity: "0" },                     to: { opacity: "1" } },
        slideUp:   { from: { opacity: "0", transform: "translateY(16px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        pulseGold: { "0%, 100%": { boxShadow: "0 0 0 0 rgba(201,168,76,0)" }, "50%": { boxShadow: "0 0 0 8px rgba(201,168,76,0.2)" } },
      },
    },
  },
  plugins: [],
};
