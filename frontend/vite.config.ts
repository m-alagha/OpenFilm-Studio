import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// The UI talks only to the local backend, through this same-origin proxy.
// No CORS is enabled anywhere; both servers bind to loopback only.
const backendPort = process.env.OPENFILM_PORT ?? "8765";
const frontendPort = Number(process.env.OPENFILM_UI_PORT ?? "5173");

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1",
    port: frontendPort,
    strictPort: true,
    proxy: {
      "/api": { target: `http://127.0.0.1:${backendPort}`, changeOrigin: false },
    },
  },
  preview: { host: "127.0.0.1", strictPort: true },
  build: { sourcemap: false },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    restoreMocks: true,
  },
});
