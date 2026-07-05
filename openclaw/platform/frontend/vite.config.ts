import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import type { ProxyOptions } from "vite";

// Minimal declaration so we can read an env override without @types/node.
declare const process: { env: Record<string, string | undefined> };

// Backend target — override with VITE_BACKEND if not on :8000.
const BACKEND = process.env.VITE_BACKEND || "http://127.0.0.1:8000";

// Log proxy connection failures clearly (e.g. backend not running).
const withLogging = (opts: ProxyOptions): ProxyOptions => ({
  ...opts,
  configure: (proxy) => {
    proxy.on("error", (err) => {
      // eslint-disable-next-line no-console
      console.error(
        `\n[proxy] Cannot reach backend at ${BACKEND} (${err.message}).` +
          `\n[proxy] Start it: cd platform/backend && uvicorn app.main:app --reload\n`
      );
    });
  },
});

// Dev server proxies /api and /ws to the FastAPI backend.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": withLogging({ target: BACKEND, changeOrigin: true }),
      "/ws": withLogging({ target: BACKEND.replace("http", "ws"), ws: true }),
      "/health": withLogging({ target: BACKEND, changeOrigin: true }),
    },
  },
});
