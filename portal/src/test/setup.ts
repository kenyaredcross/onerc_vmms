/**
 * What every test run needs before a component mounts.
 *
 * `matchMedia` is the one jsdom does not implement and several components ask
 * for — anything honouring `prefers-reduced-motion` among them. Stubbed to
 * "does not match", which is the honest default for a headless run: no reduced
 * motion, no dark mode preference.
 */
if (!window.matchMedia) {
	Object.defineProperty(window, "matchMedia", {
		writable: true,
		value: (query: string) => ({
			matches: false,
			media: query,
			onchange: null,
			addListener: () => {},
			removeListener: () => {},
			addEventListener: () => {},
			removeEventListener: () => {},
			dispatchEvent: () => false,
		}),
	});
}
