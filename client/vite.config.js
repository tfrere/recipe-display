import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
  },
  publicDir: "public",
  resolve: {
    alias: {
      "@shared":
        process.env.NODE_ENV === "production"
          ? path.resolve(__dirname, "./shared")
          : path.resolve(__dirname, "../shared-source"),
    },
  },
  optimizeDeps: {
    include: ["@shared/constants.json"],
  },
  build: {
    commonjsOptions: {
      include: [/@shared/, /node_modules/],
    },
    rollupOptions: {
      external: ["react"],
      output: {
        globals: {
          react: "React",
        },
      },
    },
  },
});
