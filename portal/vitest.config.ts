import path from "path";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Kept separate from `vite.config.ts` so the build config carries no test
// concerns and `base`/`manifest`/`outDir` cannot affect a test run.
export default defineConfig({
	plugins: [react()],
	resolve: { alias: { "@": path.resolve(__dirname, "src") } },
	test: {
		environment: "jsdom",
		globals: true,
		setupFiles: ["./src/test/setup.ts"],
		include: ["src/**/*.test.{ts,tsx}"],
		css: false,
	},
});
