/** @type {import('tailwindcss').Config} */
//
// The design system, expressed once so no component carries a raw hex.
//
// **Two naming layers, on purpose.** The `shell` / `surface` / `authority` /
// `blue` names below are the language the redesign speaks, and new code should
// use them. The `navy` / `signal` / `page` / `slate` names underneath them are
// the *previous* system's, kept as aliases pointing at the new values — around
// fifty screens reference them, and remapping the alias is what moves all of
// them onto the new palette in one step instead of leaving the product
// half-redesigned between commits. They are not deprecated decoration: they are
// the migration, and they get removed screen by screen as each is refactored.
//
// **Red is not the action colour.** The original system used the Red Cross red
// for every primary button and focus ring, which put a protected emblem's
// colour on every control in the product. Blue is the action colour and stays
// so. Red comes back under two names and neither of them is "button": `danger`
// for genuinely destructive things, and `red` for the approved concept's brand
// accents — the greeting's name, a plan card's band, one urgent deadline. The
// emblem itself is a society's uploaded asset and is never redrawn here.
export default {
	content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
	theme: {
		extend: {
			colors: {
				// ---------------------------------------------------- the ground
				// One continuous soft grey behind everything signed-in: the rail,
				// the top row and the gaps between panels are all this colour, so
				// they read as one surface with white panels floating on it rather
				// than as a sidebar bolted to a content pane.
				shell: "#ECECEC",
				// A second neutral, for surfaces that sit *inside* a white panel —
				// a stat tile, a map well, an inset list. One step off white, so it
				// separates without needing a border.
				surface: "#F5F5F5",
				// The dark feature surface. Used sparingly and with intent: the one
				// panel on a page that is being singled out (a deployment
				// invitation), and the collapsed console rail.
				authority: {
					DEFAULT: "#24272C",
					deep: "#1B1E22",
					soft: "#32373E",
				},
				// ----------------------------------------------------------- text
				// Navy-tinted, not neutral: the approved concept's ink and body
				// colours. One line each, and every screen in both shells moves
				// with them — the migration strategy this file already uses.
				ink: "#102033",
				muted: "#627083",
				// ------------------------------------------------------ the action
				// Selected navigation, focus, active tabs, primary actions. The only
				// hue in the product that means "act on this" or "you are here".
				blue: {
					DEFAULT: "#155EEF",
					hover: "#1150D0",
					press: "#0E42A8",
					// The selected-navigation wash and the focus halo.
					soft: "#EDF3FF",
					line: "#B9CDF8",
				},
				// ---------------------------------------------------------- status
				// Each of these is only ever *half* of a status: every badge also
				// carries text and a dot, because colour alone is not a state.
				danger: {
					DEFAULT: "#B4232C",
					soft: "#FFF1F2",
					line: "#EFAFB4",
					dot: "#D92D3A",
				},
				warning: {
					DEFAULT: "#8C5A00",
					soft: "#FFF8E8",
					line: "#E2C37F",
					dot: "#B97900",
				},
				success: {
					DEFAULT: "#1F6B45",
					soft: "#EAF6EF",
					line: "#A8D5BC",
					dot: "#2E8B57",
				},

				// ================================================================
				// Portal fork — the volunteer workspace's own ground.
				//
				// The portal is "one continuous workspace": a deep TRCS navy left
				// rail carrying white text, beside a cool paper-grey canvas and a
				// light header. White panels held by a 1px hairline rather than a
				// shadow. The console keeps `shell` / `surface` / borderless cards;
				// these names appear only under `portal/`. `blue` (#155EEF) stays
				// the interactive colour — primary buttons, links, focus, the
				// active-nav accent — and is never the rail's field.
				// ================================================================
				canvas: "#F4F7FA",
				rail: {
					// The sidebar field. Near-black navy; white text clears AA with
					// enormous headroom (~16:1).
					DEFAULT: "#011E41",
					// Light-side helpers, for controls that sit on the canvas — a
					// hairline, a hover wash, and the tracked micro-label colour
					// (dark enough to clear WCAG AA on canvas and white alike, which
					// #9AA0A8 did not). The rail's own text uses white-alpha inline.
					hover: "#E8EEF6",
					line: "#E2E7EE",
					label: "#5E6775",
					// The lighter navy the concept uses for a *feature* panel on the
					// light side — the deployment request's summary block. Never the
					// rail's own field.
					soft: "#082B56",
				},
				// The hairline a portal panel actually carries. One notch cooler and
				// lighter than the console's `hairline`, tuned to sit on `canvas`.
				"card-line": "#DFE6ED",
				// ------------------------------------------------- brand accents
				// The Red Cross red, back in the palette but not back as the action
				// colour: `blue` is still what "act on this" means. This is for
				// identity (the greeting's name, a plan card's band), for genuine
				// urgency (a response deadline), and for nothing else. `danger`
				// remains the destructive tone and is deliberately a separate name,
				// so a delete button can never quietly become brand decoration.
				red: {
					DEFAULT: "#D71920",
					// The readable weight of it, for words on a soft red ground.
					ink: "#9D2027",
					soft: "#FFF0F1",
					line: "#F0C8CA",
				},
				// The one cool highlight: a rule under a dark panel, the emphasis
				// word in a hero, a "ready" caption. Never a text colour on white —
				// it does not clear AA there and is never asked to.
				aqua: {
					DEFAULT: "#75D5D0",
					deep: "#16909A",
				},
				// The four calendar categories — dots on a day, chips in the day
				// panel. Recognition only; each is always paired with a text label
				// and a legend, never carrying meaning on colour alone.
				cal: {
					// Retoned to the approved concept's calendar: a deadline is red,
					// an event is the action blue, a deployment is the navy strip
					// that runs across its own days. Certification keeps the violet
					// the concept has no fourth colour for.
					task: "#B32530",
					deployment: "#011E41",
					event: "#155EEF",
					cert: "#6D4AA6",
					"cert-soft": "#F2EDFB",
				},

				// ================================================================
				// Migration aliases — the previous system's names, new values.
				// ================================================================

				// Was the brand navy. Now the authority charcoal, so every rail,
				// dark panel and strong link moves together.
				navy: {
					DEFAULT: "#24272C",
					deep: "#1B1E22",
				},
				// Was the Red Cross red, used for every primary action and focus
				// ring in the product. Now the action blue. This single line is
				// what takes the red out of ~50 screens at once.
				signal: {
					DEFAULT: "#155EEF",
					dark: "#1150D0",
				},
				// Retuned with `ink` and `muted` above: the same three weights of body
				// text, navy-tinted rather than neutral, so a paragraph in a card and
				// the heading over it belong to one family.
				slate: {
					body: "#627083",
					strong: "#3B4A5C",
					faint: "#8A96A5",
					mute: "#AEB9C5",
				},
				hairline: {
					DEFAULT: "#E1E3E6",
					soft: "#EDEEF0",
					strong: "#D5D8DC",
					pale: "#E4E5E7",
				},
				// Was the near-white page ground; now the shell grey itself, which
				// is what makes existing screens sit on the new continuous shell
				// without each one being touched.
				page: "#ECECEC",
				// The six tints a StatTile or a section icon may carry.
				//
				// **A hue here is decoration, never meaning** — unchanged as a rule,
				// but the set is retoned: desaturated, all at one lightness, and
				// with the rose no longer reading as the Red Cross red. Blue is
				// deliberately *not* among them, because blue means "act on this"
				// everywhere else and a decorative blue tile would dilute it.
				tint: {
					navy: "#3F4855",
					"navy-soft": "#EDEFF2",
					teal: "#16706A",
					"teal-soft": "#E6F2F1",
					violet: "#5B4E86",
					"violet-soft": "#EEECF6",
					amber: "#8A6410",
					"amber-soft": "#F7F0E1",
					rose: "#8C4A5E",
					"rose-soft": "#F4EBEE",
					sky: "#256B92",
					"sky-soft": "#E7F0F6",
				},
			},
			fontFamily: {
				// Unchanged strategy: a display face for things that carry weight, a
				// text face for reading, and a system stack behind both so a bench
				// with no network renders the same *layout* in a different face.
				// Nothing below depends on a web font having loaded.
				display: ["'Schibsted Grotesk'", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
				sans: ["'Public Sans'", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
				// The volunteer portal's own face. The portal is a forked visual
				// world (see PortalShell.tsx) — one continuous workspace in IBM Plex
				// Sans, quieter and flatter than the console's grey shell. The
				// console keeps `display` / `sans`; nothing under `admin/` uses this.
				plex: ["'IBM Plex Sans'", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
			},
			// Radius is chosen by a thing's *size*, not by what it is. A 32px chip
			// at a panel's radius reads as a lozenge; a 400px panel at a chip's
			// radius reads as a box with the corners filed off.
			//
			// Buttons and single-line fields are not on this scale at all — they
			// are `rounded-full`, which is the redesign's most consistent move.
			borderRadius: {
				// Compact page-local controls: a segmented control, a small select,
				// a date field that cannot be a pill without looking like a tablet.
				control: "12px",
				// A card of content.
				card: "18px",
				// A panel that contains panels, and the shell's own outer corner.
				panel: "24px",
				// Full-bleed things: a hero, a map well, a photo.
				feature: "26px",
			},
			boxShadow: {
				// A panel is told apart from the grey ground by *tone* first and
				// shadow second — restrained, wide and downward-biased. At rest you
				// should not be able to point at it; remove it and every panel on
				// the page flattens into the shell.
				card: "0 1px 2px rgba(26, 32, 44, 0.03), 0 8px 25px rgba(26, 32, 44, 0.05)",
				// The same panel with a pointer on it.
				lift: "0 1px 2px rgba(26, 32, 44, 0.04), 0 14px 34px rgba(26, 32, 44, 0.08)",
				// The shell's own outer edge, and anything that floats above the
				// page entirely — a drawer, a menu, a dialog.
				shell: "0 18px 55px rgba(25, 30, 38, 0.10)",
				pop: "0 12px 30px rgba(25, 30, 38, 0.16)",
				// The selected navigation pill: it sits on grey and needs to read
				// as lifted off it without a border.
				nav: "0 1px 2px rgba(26, 32, 44, 0.06), 0 4px 12px rgba(26, 32, 44, 0.06)",
				hero: "0 10px 34px rgba(25, 30, 38, 0.18)",
			},
			letterSpacing: {
				eyebrow: "0.14em",
			},
			maxWidth: {
				shell: "1248px",
			},
		},
	},
	plugins: [],
};
