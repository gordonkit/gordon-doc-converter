import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  root: resolve(__dirname),
  base: "./",
  plugins: [react()],
  build: {
    outDir: resolve(__dirname, "../docs"),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        docs: resolve(__dirname, "index.html"),
        swagger: resolve(__dirname, "swagger/index.html"),
      },
    },
  },
});