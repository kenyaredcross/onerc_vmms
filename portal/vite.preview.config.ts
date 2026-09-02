import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * A dev-only Vite config for the backend-free preview harness
 * (`preview.html` → `src/preview/main.tsx`), used for design iteration and
 * screenshots. Not part of the shipped build — `vite.config.ts` is.
 *
 *   node scripts/mock-api.mjs &
 *   npx vite --config vite.preview.config.ts --port 8123
 *   open http://localhost:8123/preview.html
 */
export default defineConfig({
	base: "/",
	plugins: [react()],
	server: { port: 8123, host: "0.0.0.0" },
	resolve: { alias: { "@": path.resolve(import.meta.dirname, "src") } },
});
