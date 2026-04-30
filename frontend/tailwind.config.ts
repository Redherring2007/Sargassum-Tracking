import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#08111f",
        panel: "#101c2d",
        panel2: "#13243a",
        cyanline: "#38bdf8",
        kelp: "#16a34a",
        coral: "#fb7185",
        amberline: "#f59e0b"
      },
      boxShadow: {
        command: "0 18px 60px rgba(0, 0, 0, 0.35)"
      }
    }
  },
  plugins: []
} satisfies Config;
