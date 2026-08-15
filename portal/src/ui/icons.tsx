/**
 * The icon set, drawn rather than imported.
 *
 * A library would be a dependency and a bundle for two dozen glyphs. Each is a
 * 24-grid stroke path so they sit together at any size, and every one is
 * `aria-hidden`: the label beside it is the accessible name, and a duplicate
 * would be read twice.
 */
type IconProps = { size?: number; className?: string };

function Glyph({ size = 17, className, d }: IconProps & { d: string }) {
	return (
		<svg
			width={size}
			height={size}
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			strokeWidth="1.8"
			strokeLinecap="round"
			strokeLinejoin="round"
			className={className}
			aria-hidden="true"
			focusable="false"
		>
			<path d={d} />
		</svg>
	);
}

export const Icon = {
	home: (p: IconProps) => <Glyph {...p} d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-9.5Z" />,
	compass: (p: IconProps) => <Glyph {...p} d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm3.5-12.5-2 5-5 2 2-5 5-2Z" />,
	calendar: (p: IconProps) => <Glyph {...p} d="M7 3v3m10-3v3M4 9h16M5 6h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1Z" />,
	book: (p: IconProps) => <Glyph {...p} d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2V5Zm2 14h13" />,
	card: (p: IconProps) => <Glyph {...p} d="M3 7a1 1 0 0 1 1-1h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7Zm0 4h18M7 15h4" />,
	clock: (p: IconProps) => <Glyph {...p} d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-13v5l3 2" />,
	user: (p: IconProps) => <Glyph {...p} d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 9a7 7 0 0 1 14 0" />,
	inbox: (p: IconProps) => <Glyph {...p} d="M4 13h4l1.5 3h5L16 13h4M4 13 6 5h12l2 8v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-6Z" />,
	people: (p: IconProps) => <Glyph {...p} d="M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm-7 9a7 7 0 0 1 14 0m1-15.5a3.5 3.5 0 0 1 0 7M18 20a6.5 6.5 0 0 0-2-4.7" />,
	truck: (p: IconProps) => <Glyph {...p} d="M3 7a1 1 0 0 1 1-1h9v10H4a1 1 0 0 1-1-1V7Zm10 2h4l3 3v4h-7V9Zm-6 9a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm10 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z" />,
	coins: (p: IconProps) => <Glyph {...p} d="M9 12a5 3 0 1 0 0-6 5 3 0 0 0 0 6Zm-5 2a5 3 0 1 0 10 0M4 9v8c0 1.7 2.2 3 5 3s5-1.3 5-3V9m1 1.5c2.4.3 4 1.4 4 2.7v4c0 1.6-2.2 2.8-5 2.8" />,
	chart: (p: IconProps) => <Glyph {...p} d="M4 20V4m0 16h16M8 17v-5m4 5V8m4 9v-7" />,
	pencil: (p: IconProps) => <Glyph {...p} d="M4 20h4L19 9l-4-4L4 16v4Z" />,
	back: (p: IconProps) => <Glyph {...p} d="M15 5l-7 7 7 7" />,
	check: (p: IconProps) => <Glyph {...p} d="m5 13 4 4L19 7" />,
	cross: (p: IconProps) => <Glyph {...p} d="M6 6l12 12M18 6 6 18" />,
	menu: (p: IconProps) => <Glyph {...p} d="M4 7h16M4 12h16M4 17h16" />,
	bell: (p: IconProps) => <Glyph {...p} d="M18 9a6 6 0 1 0-12 0c0 5-2 6-2 6h16s-2-1-2-6Zm-4.3 10a2 2 0 0 1-3.4 0" />,
	/** A tab that leaves the app. The arrow out of the box is the whole point. */
	external: (p: IconProps) => <Glyph {...p} d="M13 4h7v7M20 4l-9 9M17 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1h5" />,
	signout: (p: IconProps) => <Glyph {...p} d="M15 17v2a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v2m3 9 4-4-4-4M10 12h11" />,
	chevron: (p: IconProps) => <Glyph {...p} d="m6 9 6 6 6-6" />,
	search: (p: IconProps) => <Glyph {...p} d="M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Zm5-2 5 5" />,
	pin: (p: IconProps) => <Glyph {...p} d="M12 21s7-6.3 7-11a7 7 0 1 0-14 0c0 4.7 7 11 7 11Zm0-8.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z" />,
	tag: (p: IconProps) => <Glyph {...p} d="M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9-9-9Zm4.5-5.5v.01" />,
	/** Beside a field somebody may read and not write. The only one is the email. */
	lock: (p: IconProps) => <Glyph {...p} d="M8 10V7a4 4 0 1 1 8 0v3M5 10h14a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1Z" />,
	plus: (p: IconProps) => <Glyph {...p} d="M12 5v14M5 12h14" />,
	/** The overflow control at the end of a row. */
	dots: (p: IconProps) => <Glyph {...p} d="M12 6.5v.01M12 12v.01M12 17.5v.01" />,
	arrow: (p: IconProps) => <Glyph {...p} d="M5 12h14m-6-7 7 7-7 7" />,
	/** A certification, and the only place this product draws a medal. */
	award: (p: IconProps) => <Glyph {...p} d="M12 14a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm-3.5 3L7 22l5-2.5L17 22l-1.5-5" />,
	heart: (p: IconProps) => <Glyph {...p} d="M12 20s-7.5-4.7-7.5-10A4.5 4.5 0 0 1 12 7a4.5 4.5 0 0 1 7.5 3c0 5.3-7.5 10-7.5 10Z" />,
	/** Something new or highlighted. Never a decoration on its own. */
	sparkle: (p: IconProps) => <Glyph {...p} d="M12 3l1.8 4.9L18.7 9.7l-4.9 1.8L12 16.4l-1.8-4.9L5.3 9.7l4.9-1.8L12 3ZM18.5 16l.7 1.9 1.9.7-1.9.7-.7 1.9-.7-1.9-1.9-.7 1.9-.7.7-1.9Z" />,
	filter: (p: IconProps) => <Glyph {...p} d="M4 6h16M7 12h10m-7 6h4" />,
	/** Waiting on somebody else. Used where a state is neither done nor failed. */
	hourglass: (p: IconProps) => <Glyph {...p} d="M7 3h10M7 21h10M8 3v3.5c0 2 4 3.5 4 5.5s-4 3.5-4 5.5V21m8-18v3.5c0 2-4 3.5-4 5.5s4 3.5 4 5.5V21" />,
	mail: (p: IconProps) => <Glyph {...p} d="M4 6h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1Zm-.6.6 8.6 6.4 8.6-6.4" />,
	phone: (p: IconProps) => <Glyph {...p} d="M7 3h3l1.5 4.5-2 1.5a12 12 0 0 0 5.5 5.5l1.5-2L21 14v3a2 2 0 0 1-2 2A16 16 0 0 1 5 5a2 2 0 0 1 2-2Z" />,
	/** A photograph slot with nothing in it yet. */
	image: (p: IconProps) => <Glyph {...p} d="M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Zm-.5 12 5-5 3.5 3.5L15 12l5.5 5.5M9 9.5v.01" />,
	/** Somewhere else the person may be. Used on the placement selector. */
	globe: (p: IconProps) => <Glyph {...p} d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm-8.5-9h17M12 3c2.2 2.4 3.4 5.6 3.4 9S14.2 18.6 12 21c-2.2-2.4-3.4-5.6-3.4-9S9.8 5.4 12 3Z" />,
};
