import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
  },
  publicDir: "public",
  assetsInclude: ["**/*.json"],
  resolve: {
    alias: {
      '@shared': path.resolve(__dirname, '../shared')
    }
  }
});
