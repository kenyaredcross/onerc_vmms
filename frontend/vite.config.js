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

		vue({
			script: {
				defineModel: true,
				propsDestructure: true,
			},
		}),

		VitePWA({
			registerType: "autoUpdate",
			devOptions: {
				enabled: false,
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

	css: {
		devSourcemap: false,
	},

	resolve: {
		alias: {
			"@": path.resolve(__dirname, "src"),
			"tailwind.config.js": path.resolve(__dirname, "tailwind.config.js"),
		},
	},

	optimizeDeps: {
		include: [
			"feather-icons",
			"showdown",
			"highlight.js/lib/core",
			"interactjs",
			"vue",
			"vue-router",
			"pinia",
			"frappe-ui",
			"dayjs",
			"date-fns",
			"apexcharts",
			"vue-chartjs",
			"chart.js",
			"socket.io-client",
			"markdown-it",
			"lucide-vue-next",
			"@heroicons/vue/24/outline",
			"@heroicons/vue/24/solid",
			"@vueuse/head",
			"@vueuse/router",
			"codemirror",
			"@codemirror/lang-html",
			"@codemirror/lang-javascript",
			"@codemirror/lang-json",
			"@codemirror/lang-python",
		],
		esbuildOptions: {
			define: {
				global: "globalThis",
			},
		},
	},

	server: {
		allowedHosts: true,
		port: 8081,
		open: false,
		hmr: {
			overlay: true,
			clientPort: 8081,
		},
		watch: {
			usePolling: true,
			interval: 150,
		},
	},

	define: {
		"process.env": {},
	},
});
