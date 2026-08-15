import path from 'path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react'
import proxyOptions from './proxyOptions';

// https://vitejs.dev/config/
export default defineConfig({
	// Assets are served by Frappe from sites/assets/vmmsx -> vmmsx/public.
	base: '/assets/vmmsx/portal/',
	plugins: [react()],
	server: {
		port: 8080,
		host: '0.0.0.0',
		proxy: proxyOptions
	},
	resolve: {
		alias: {
			'@': path.resolve(__dirname, 'src')
		}
	},
	build: {
		outDir: '../vmmsx/public/portal',
		emptyOutDir: true,
		target: 'es2015',
		// Written to public/portal/.vite/manifest.json and read server-side by
		// vmmsx/spa.py, so the www page always points at the current hashed bundle.
		manifest: true,
		cssMinify: false, // Matches ans-hub: avoids lightningcss errors on modern CSS functions.
	},
});
