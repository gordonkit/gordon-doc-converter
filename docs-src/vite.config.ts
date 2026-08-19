import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { seoPagesPlugin } from "./seo";

export default defineConfig({
  root: resolve(__dirname),
  base: "/",
  plugins: [react(), seoPagesPlugin(resolve(__dirname, "../docs"))],
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