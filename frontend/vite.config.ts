import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const proxy = {
  "/api": {
    target: process.env.TAPME_API_URL || "http://127.0.0.1:8000",
    changeOrigin: false,
  },
};

export default defineConfig(({ command, isPreview }) => ({
  base: command === "build" || isPreview ? "/crm-flowers/" : "/",
  plugins: [react()],
  server: { strictPort: true, proxy },
  preview: { strictPort: true, proxy },
}));
