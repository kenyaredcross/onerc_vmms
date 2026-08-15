/** @type {import('tailwindcss').Config} */
//
// The navy / signal-red system from the design canvas, expressed once here so no
// component carries a raw hex. Two greys are deliberately distinct: `page` is
// the ground behind cards in the signed-in app, `white` is the ground of the
// public landing page, and swapping them changes which surface reads as "app".
export default {
	content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
	theme: {
		extend: {
			colors: {
				ink: "#0B0C0E",
				navy: {
					DEFAULT: "#011E41",
					// The coordinator console's sidebar. Darker than the volunteer
					// portal's on purpose: the design uses depth to say "you are
					// acting on other people's records now".
					deep: "#06101F",
				},
				signal: {
					DEFAULT: "#F5333F",
					dark: "#C4242E",
				},
				slate: {
					body: "#5B6472",
					strong: "#3D4652",
					faint: "#8A93A1",
					// Quieter than `faint`, and used once: the copyright line in
					// the landing footer, which the design deliberately sets
					// below every other word on the page.
					mute: "#A6ADB8",
				},
				hairline: {
					DEFAULT: "#E7EAF0",
					soft: "#EDF0F5",
					strong: "#D8DEE9",
					// The rules between the statistics, on the `page` ground
					// rather than on white, so it is a shade cooler than the rest.
					pale: "#E2E7F0",
				},
				page: "#F4F6FA",
				// The six tints a `StatTile` or a section icon may carry.
				//
				// **A hue here is decoration, never meaning.** Navy and signal already
				// carry the two meanings this product has — "the society" and "act on
				// this" — and `STATE_TONES` owns the third, which is the shape of an
				// approval state. These exist so a row of four figures reads as four
				// things rather than as one thing repeated, and a screen picks them by
				// position in a list. Nothing branches on them.
				//
				// Each is the same lightness, so no tile shouts louder than its
				// neighbour, and each `-soft` is the 8%-ish wash the icon square sits
				// on. Kept off `signal` deliberately: a red tile beside a red button
				// makes the button stop meaning anything.
				tint: {
					navy: "#1F4E8C",
					"navy-soft": "#E8EFF9",
					teal: "#0E7C74",
					"teal-soft": "#E2F4F2",
					violet: "#6B4EA8",
					"violet-soft": "#EFEAFA",
					amber: "#9A6608",
					"amber-soft": "#FBF1DE",
					rose: "#A83E5B",
					"rose-soft": "#FAEAEF",
					sky: "#1C6E9E",
					"sky-soft": "#E4F1FA",
				},
			},
			fontFamily: {
				// Schibsted Grotesk for anything that carries weight, Public Sans
				// for reading. Both fall back to the system stack, so a bench with
				// no network still renders a coherent page.
				display: ["'Schibsted Grotesk'", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
				sans: ["'Public Sans'", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
			},
			// Four steps, and which one a thing gets is decided by its *size*, not
			// by what it is. A 32px chip at the card's radius reads as a lozenge; a
			// 400px panel at the chip's radius reads as a box with the corners
			// filed off. So: `control` for anything you click or type into,
			// `card` for a panel of content, `panel` for a panel of panels, and
			// `feature` for the few full-bleed things (a hero, a map, a photo).
			//
			// Buttons and single-line fields are not on this scale at all — they
			// are `rounded-full`, which is the reference set's most consistent
			// single move and the one that does the most work.
			borderRadius: {
				control: "10px",
				card: "16px",
				panel: "20px",
				feature: "26px",
			},
			boxShadow: {
				hero: "0 10px 34px rgba(1, 30, 65, 0.22)",
				// A card is separated from the ground by tone first and shadow
				// second. The second value is a wide, very soft, downward-biased
				// spread: at rest you cannot point at it, but remove it and every
				// card on the page flattens into the background.
				card: "0 1px 2px rgba(1, 30, 65, 0.04), 0 12px 28px -20px rgba(1, 30, 65, 0.35)",
				// The same card once somebody is pointing at it.
				lift: "0 1px 2px rgba(1, 30, 65, 0.05), 0 18px 38px -22px rgba(1, 30, 65, 0.45)",
				pop: "0 12px 30px rgba(1, 30, 65, 0.18)",
			},
			letterSpacing: {
				eyebrow: "0.16em",
			},
			maxWidth: {
				// The design's column is 1200px of *content*, and it gets there
				// with `max-width:1200px;padding:0 24px` on a content-box element,
				// where the padding sits outside the 1200. Tailwind's preflight
				// makes everything border-box, so the same two declarations give a
				// 1152px column instead — every section on the page 48px narrower
				// than it was drawn, which reads as "close but not it".
				//
				// 1248 = 1200 + the 24px of padding on each side.
				shell: "1248px",
			},
		},
	},
	plugins: [],
};
