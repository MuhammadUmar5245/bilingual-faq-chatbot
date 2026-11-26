import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Builds a single self-contained file (dist/widget.js) that any college website can load with
// one <script> tag (FR-08). CSS is inlined and injected into a Shadow DOM, so the host page's
// styles cannot break the widget and the widget cannot break the host page.
export default defineConfig({
  plugins: [react()],
  define: { "process.env.NODE_ENV": JSON.stringify("production") },
  server: { port: 5173, proxy: { "/api": "http://localhost:5000" } },
  build: {
    lib: { entry: "src/embed.jsx", name: "CollegeFaqWidget", formats: ["iife"], fileName: () => "widget.js" },
    outDir: "dist",
    emptyOutDir: true,
  },
});
