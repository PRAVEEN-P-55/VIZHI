import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    // PDF export is lazy-loaded; its isolated vendor chunk is intentionally larger.
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/leaflet") || id.includes("node_modules/react-leaflet")) return "maps";
          if (id.includes("node_modules/recharts")) return "charts";
          if (id.includes("node_modules/d3")) return "d3";
          if (id.includes("node_modules/jspdf") || id.includes("node_modules/html2canvas")) return "pdf";
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      // proxy API + websocket to the FastAPI backend during dev
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
        ws: true,
      },
    },
  },
});
