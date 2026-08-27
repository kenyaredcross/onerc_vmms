/**
 * What every test run needs before a component mounts.
 *
 * `matchMedia` is the one jsdom does not implement and several components ask
 * for — anything honouring `prefers-reduced-motion` among them. Stubbed to
 * "does not match", which is the honest default for a headless run: no reduced
 * motion, no dark mode preference.
 *
 * `scrollTo` is the other. jsdom does not implement it either and warns on every
 * call; anything that moves somebody between screens uses it, and the warnings
 * are noise between a run and the failure worth reading in it.
 */
// Unconditionally: jsdom *does* define `scrollTo`, as a stub whose whole
// behaviour is to log "Not implemented". Guarding on its absence never replaces
// it, which is why the warnings kept coming.
Object.defineProperty(window, "scrollTo", { writable: true, value: () => {} });

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
