import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import path from "node:path";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
	plugins: [
		frappeui({
			frappeProxy: true,
			jinjaBootData: true,
			lucideIcons: true,
			buildConfig: {
				indexHtmlPath: "../onerc_vmms/www/vmms.html",
				emptyOutDir: true,
				sourcemap: true,
			},
		}),

		vue(),

		VitePWA({
			registerType: "autoUpdate",
			devOptions: {
				enabled: true,
			},
			workbox: {
				cleanupOutdatedCaches: true,
				maximumFileSizeToCacheInBytes: 5 * 1024 * 1024,
			},
			manifest: false,
		}),
	],

	build: {
		outDir: "../onerc_vmms/public/frontend",
		emptyOutDir: true,
		target: "es2015",
		sourcemap: true,
		chunkSizeWarningLimit: 1500,
	},

	resolve: {
		alias: {
			"@": path.resolve(__dirname, "src"),
			"tailwind.config.js": path.resolve(__dirname, "tailwind.config.js"),
		},
	},

	optimizeDeps: {
		include: ["feather-icons", "showdown", "highlight.js/lib/core", "interactjs"],

		esbuildOptions: {
			define: {
				global: "globalThis",
			},
		},
	},

	server: {
		allowedHosts: true,
		port: 8080,
		open: true,
	},

	define: {
		"process.env": {},
	},
});
