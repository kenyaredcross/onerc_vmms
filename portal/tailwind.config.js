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
// Replica IFRC-inspired direction: brand red carries primary actions and
// selected navigation. Navy carries information and charts; neutrals carry
// surfaces. The danger palette remains separate from the brand/action palette.
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
				shell: "#F5F5F5",
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
				muted: "#525E6C",
				// ------------------------------------------------------ the action
				// Navy information palette; legacy blue utilities now resolve to navy.
				// Primary actions and selected states use the separate action palette.
				blue: {
					DEFAULT: "#011E41",
					hover: "#082B56",
					press: "#00152E",
					// The selected-navigation wash and the focus halo.
					soft: "#F0F3F6",
					line: "#C8D5E3",
				},
				// Brand action is distinct from navy information and danger.
				action: {
					DEFAULT: "#D71920",
					hover: "#B9151B",
					press: "#9D2027",
					soft: "#FFF0F1",
					line: "#F0C8CA",
					ink: "#9D2027",
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
				// Both workspaces share neutral surfaces and a navy rail. Red action
				// controls and active markers provide the Movement-inspired identity.
				canvas: "#EEF0F3",
				rail: {
					// The sidebar field. Near-black navy; white text clears AA with
					// enormous headroom (~16:1).
					DEFAULT: "#011E41",
					// Light-side helpers, for controls that sit on the canvas — a
					// hairline, a hover wash, and the tracked micro-label colour
					// (dark enough to clear WCAG AA on canvas and white alike, which
					// #9AA0A8 did not). The rail's own text uses white-alpha inline.
					hover: "#E8EEF6",
					line: "#C9D0D9",
					label: "#5E6775",
					// The lighter navy the concept uses for a *feature* panel on the
					// light side — the deployment request's summary block. Never the
					// rail's own field.
					soft: "#082B56",
				},
				// The hairline a portal panel actually carries. One notch cooler and
				// lighter than the console's `hairline`, tuned to sit on `canvas`.
				"card-line": "#E4E5E7",
				// ------------------------------------------------- brand accents
				// Brand red accents share their hue with semantic `action` controls.
				// Use this decorative palette for
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
				// Brand highlights use Red Cross red: rules under dark panels,
				// emphasis words in heroes, and compact readiness captions.
				aqua: {
					DEFAULT: "#D71920",
					deep: "#9D2027",
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
					event: "#45688D",
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
				// Legacy action alias: red matches the semantic action palette.
				signal: {
					DEFAULT: "#D71920",
					dark: "#B9151B",
				},
				// Retuned with `ink` and `muted` above: the same three weights of body
				// text, navy-tinted rather than neutral, so a paragraph in a card and
				// the heading over it belong to one family.
				slate: {
					body: "#525E6C",
					strong: "#3B4A5C",
					faint: "#657180",
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
