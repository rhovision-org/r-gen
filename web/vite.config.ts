import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Relative base so the app works from a subpath (GitHub Pages, a static host).
  base: "./",
  server: { port: 5173 },
  optimizeDeps: { exclude: ["rgen_wasm"] },
});
