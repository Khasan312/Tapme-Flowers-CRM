import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    strictPort: true,
    proxy: {
      "/api": {
        target: process.env.TAPME_API_URL || "http://127.0.0.1:8000",
        changeOrigin: false,
      },
    },
  },
});
