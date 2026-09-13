import {
	type ReactNode,
	useCallback,
	useEffect,
	useId,
	useLayoutEffect,
	useRef,
	useState,
} from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";

import { appRoute, cx } from "./primitives";

/** How close to the edge of the window the card is allowed to come. */
const EDGE = 16;

/**
 * The floating summary that opens beside somebody's name in a register.
 *
 * **Hover is the nickname, not the contract.** A card that only answered
 * `mouseenter` would be invisible on a phone and unreachable from a keyboard,
 * which on the screen a coordinator picks people from is not a rough edge but a
 * whole class of user shut out. So the trigger is a real `<button>`, the card
 * opens on hover *and* on focus *and* on click, and click **pins** it — reading
 * five facts about somebody is a different act from sweeping a mouse down a
 * column, and the second must not close what the first opened.
 *
 * It closes on Escape and on a click outside, the two things everybody already
 * knows how to do with a popover, and Escape returns focus to the trigger it
 * came from rather than dropping it on the document.
 *
 * **It is drawn in a portal at the top of the document, not inside the row.**
 * A register lives in a panel that scrolls sideways, and `overflow-x: auto`
 * clips the other axis too — the browser has no way to scroll one axis and let
 * the other overflow. A card positioned inside that panel is therefore sliced
 * off at the table's own edge, which is how this looked before: a row near the
 * top of a register opened a card and a coordinator saw a sliver of it. So the
 * card is a child of `<body>`, positioned against the trigger's measured rect,
 * and no ancestor's overflow can reach it.
 *
 * **It never opens off the edge of the screen.** The card measures itself once
 * it is open and flips above or left when there is not room — measured rather
 * than guessed, because the card's height depends on what arrived in it, and
 * re-measured when the dossier lands or the page moves under it.
 *
 * **The body is a render prop and is only called while open.** That is what
 * makes fetch-on-open work: a register of two hundred rows must not pay for two
 * hundred dossiers to fill a card that will be shown for four of them. The
 * caller starts its own read the first time this calls it, and the SWR key
 * keeps the answer for the second hover.
 */
export function PersonCard({
	label,
	children,
	className,
	cardClassName,
	/** How wide the card is. One number, because the flip arithmetic needs it. */
	width = 300,
}: {
	label: ReactNode;
	children: () => ReactNode;
	className?: string;
	cardClassName?: string;
	width?: number;
}) {
	const [open, setOpen] = useState(false);
	const [pinned, setPinned] = useState(false);
	/**
	 * Where the card sits. `top` and `left` are in the card's own units, which
	 * are not the window's — see the placement effect. `above` flips it onto its
	 * own bottom edge rather than moving it.
	 */
	const [at, setAt] = useState<{ above: boolean; top: number; left: number } | null>(null);

	const holder = useRef<HTMLDivElement>(null);
	const trigger = useRef<HTMLButtonElement>(null);
	const card = useRef<HTMLDivElement>(null);
	const id = useId();

	/**
	 * One focus event to ignore, after a dismissal that moves focus itself.
	 *
	 * **Escape has to return focus to the trigger, and the trigger opens on
	 * focus.** Those two rules are each correct and together they are a loop: the
	 * card closes, focus lands, `onFocus` reopens it, and Escape appears to do
	 * nothing at all. So a dismissal that moves focus deliberately says "not this
	 * one", and the very next focus clears the flag rather than leaving it set —
	 * tabbing away and back must open the card again, because that is a person
	 * asking for it a second time.
	 */
	const ignoreNextFocus = useRef(false);

	const close = useCallback(() => {
		setPinned(false);
		setOpen(false);
	}, []);

	/**
	 * Is this node part of the card's world?
	 *
	 * The card is no longer a descendant of the trigger, so "inside" is two
	 * elements rather than one. Every dismissal asks this, and a check that
	 * forgot the card would close it the moment somebody reached for the Call
	 * link it exists to offer.
	 */
	const within = useCallback(
		(node: Node | null) =>
			Boolean(node && (holder.current?.contains(node) || card.current?.contains(node))),
		[],
	);

	// Escape and a click elsewhere dismiss a pinned card. Both listeners are
	// attached only while one is pinned, so a register of fifty rows is not
	// fifty document listeners waiting for a key nobody pressed.
	useEffect(() => {
		if (!pinned) return;

		const onKey = (event: KeyboardEvent) => {
			if (event.key !== "Escape") return;

			close();
			// Back to where it came from. Focus left on the document is focus
			// somebody has to find again with the Tab key — and the flag is what
			// stops the trigger's own `onFocus` undoing the dismissal.
			ignoreNextFocus.current = true;
			trigger.current?.focus();
		};

		const onPointer = (event: MouseEvent) => {
			if (within(event.target as Node)) return;

			close();
		};

		document.addEventListener("keydown", onKey);
		document.addEventListener("mousedown", onPointer);

		return () => {
			document.removeEventListener("keydown", onKey);
			document.removeEventListener("mousedown", onPointer);
		};
	}, [pinned, close, within]);

	/**
	 * Put the card against the name it belongs to, and keep it there.
	 *
	 * **Re-measured every frame it is open, not on scroll and resize.** A card
	 * placed once drifts off the name it belongs to, because the row moves under
	 * it: the summary tiles and the page's own description arrive after the
	 * register does and push every row down together. That is not a scroll, not a
	 * resize and not a change in the card's own size, so the three obvious
	 * listeners all miss it — and the card ends up hanging in the air a hundred
	 * pixels above the person it describes. A frame loop sees all of it, costs one
	 * `getBoundingClientRect` per frame for the single card that is open, and
	 * stops the moment it closes.
	 *
	 * It only writes state when the answer actually changed, so a card sitting
	 * still is a comparison per frame and no React render at all.
	 *
	 * `getBoundingClientRect` is zero-everything in jsdom, which resolves to the
	 * default placement: below and left-aligned, the same one a wide desktop
	 * viewport gets.
	 */
	useLayoutEffect(() => {
		if (!open) return;

		let frame = 0;

		const place = () => {
			frame = requestAnimationFrame(place);

			if (!trigger.current || !card.current) return;

			const anchor = trigger.current.getBoundingClientRect();
			const box = card.current.getBoundingClientRect();

			/**
			 * **The signed-in shells run at `zoom: 0.8`, and that splits the
			 * page into two coordinate systems.** `getBoundingClientRect` answers
			 * in window pixels, with the zoom already applied; `offsetHeight` and
			 * every length this component writes into `style` answer in the
			 * zoomed subtree's own units, which are 1/0.8 as large. Mixing the
			 * two is what put the card a hundred pixels off the name — the
			 * measured height was a quarter too big, and later the window's own
			 * height was compared against a distance that was not in its units.
			 *
			 * So: every comparison below happens in window pixels, and the two
			 * numbers that leave for `style` are converted back at the end. The
			 * card measures its own scale, which is exact and needs no knowledge
			 * of which shell it opened in.
			 */
			const scale = card.current.offsetWidth ? box.width / card.current.offsetWidth : 1;
			const span = width * scale;

			const fitsBelow = anchor.bottom + box.height <= window.innerHeight - EDGE;
			const fitsAbove = anchor.top - box.height >= EDGE;

			// Below is the default and above is the fallback — a card that
			// flipped whenever it was slightly short would jump about on a short
			// viewport. When neither side fits it stays below and is clamped onto
			// the screen, rather than flipping into a position just as cut off.
			const above = !fitsBelow && fitsAbove;

			// Above is `anchor.top` and not `anchor.top - height`, because the
			// card is flipped onto its own bottom edge with a transform rather
			// than moved up by a height this has to be right about. The browser
			// does that arithmetic as it paints, so the foot of the card meets
			// the name whatever arrived inside it.
			const y = above
				? anchor.top
				: Math.min(
						Math.max(EDGE, anchor.bottom),
						Math.max(EDGE, window.innerHeight - EDGE - box.height),
					);

			// Never off the left edge either: a right-flipped card beside a name
			// near the start of a narrow window would go negative.
			const x = Math.max(
				EDGE,
				window.innerWidth - anchor.left < span + EDGE ? anchor.right - span : anchor.left,
			);

			const next = { above, top: y / scale, left: x / scale };

			setAt((was) =>
				was && was.top === next.top && was.left === next.left && was.above === next.above
					? was
					: next,
			);
		};

		place();

		return () => cancelAnimationFrame(frame);
	}, [open, width]);

	// A fresh open measures itself from scratch rather than flashing up wherever
	// the last one sat.
	useEffect(() => {
		if (!open) setAt(null);
	}, [open]);

	/** Mouse leaving for somewhere that is not the card's world closes it. */
	const onLeave = (next: Node | null) => {
		if (pinned) return;
		if (within(next)) return;

		setOpen(false);
	};

	return (
		<div
			ref={holder}
			className={cx("relative inline-block", className)}
			onMouseEnter={() => setOpen(true)}
			onMouseLeave={(event) => onLeave(event.relatedTarget as Node)}
		>
			<button
				ref={trigger}
				type="button"
				aria-expanded={open}
				aria-controls={open ? id : undefined}
				aria-haspopup="dialog"
				onFocus={() => {
					if (ignoreNextFocus.current) {
						ignoreNextFocus.current = false;
						return;
					}

					setOpen(true);
				}}
				onBlur={(event) => {
					// Focus moving *into* the card is not focus leaving. Without
					// this a keyboard reader could never reach the call or email
					// action the card exists to offer.
					if (pinned) return;
					if (within(event.relatedTarget as Node)) return;

					setOpen(false);
				}}
				onClick={() => {
					setPinned((was) => !was);
					setOpen(true);
				}}
				className="max-w-full rounded-md text-left outline-none focus-visible:ring-2 focus-visible:ring-blue/40"
			>
				{label}
			</button>

			{open &&
				createPortal(
					<div
						ref={card}
						style={{
							top: at?.top ?? 0,
							left: at?.left ?? 0,
							// Flipped onto its own foot, in its own units, by the
							// browser — the one measurement nothing here can get wrong.
							transform: at?.above ? "translateY(-100%)" : "none",
							width,
							// One frame where the height is unknown and the flip has
							// not been decided. Hidden rather than moved off-screen,
							// so it still measures.
							visibility: at ? "visible" : "hidden",
						}}
						// Above the console's own chrome — a sticky table header, an
						// account menu — and deliberately below the modals and drawers at
						// 60, which are the only things allowed to cover a card outright.
						className="fixed z-[55]"
						onMouseEnter={() => setOpen(true)}
						onMouseLeave={(event) => onLeave(event.relatedTarget as Node)}
					>
						{/* The gap is padding on the portal rather than empty space,
						    so a mouse crossing from the name into the card never
						    passes over the row underneath and closes what it was
						    reaching for. */}
						<div className={at?.above ? "pb-1.5" : "pt-1.5"}>
							<div
								id={id}
								role="dialog"
								aria-label="Person summary"
								className={cx(
									"overflow-hidden rounded-2xl border border-card-line bg-white p-0 text-left shadow-[0_20px_50px_rgba(1,30,65,0.22)]",
									cardClassName,
								)}
							>
								{children()}
							</div>
						</div>
					</div>,
					document.body,
				)}
		</div>
	);
}

/** One fact on a summary card: a label, and what is known — or nothing. */
export interface SummaryFact {
	label: string;
	value: ReactNode;
}

/**
 * The body every person-summary card shares, whichever register it opened from.
 *
 * One component rather than two, because the two registers ask the same
 * question — *who is this, and how do I reach them* — and two bodies would
 * drift the first time somebody added a line to one of them.
 *
 * **Absent is ordinary and is drawn as absent.** Most people a branch registers
 * from a paper form have no photograph and many have no email; a card that hid
 * the row would make the reader wonder whether it had failed to load, and one
 * that invented a placeholder would be lying. A dash in the value column is the
 * honest render. The call and email actions are the exception: a `tel:` link
 * with no number goes nowhere, so those are drawn only when there is something
 * behind them.
 */
export function PersonSummaryBody({
	name,
	photo,
	status,
	place,
	facts,
	phone,
	email,
	open,
	loading,
	error,
}: {
	name: string;
	photo?: string | null;
	/** Their standing, in the register's own word. Never compared, only shown. */
	status?: ReactNode;
	/** Where they serve or hold their membership. */
	place?: string | null;
	facts: SummaryFact[];
	phone?: string | null;
	email?: string | null;
	/** Where the full record is. Always drawn: it is the card's whole purpose. */
	open: { to: string; label: string };
	loading?: boolean;
	error?: ReactNode;
}) {
	return (
		<>
			<div className="flex items-start gap-3 bg-rail px-4 py-4 text-white">
				<CardAvatar name={name} photo={photo} />

				<div className="min-w-0 flex-1">
					<div className="truncate text-[14px] font-bold text-white">{name}</div>
					{place && <div className="mt-0.5 truncate text-[11.5px] text-white/60">{place}</div>}
					{status && <div className="mt-1.5">{status}</div>}
				</div>
			</div>

			{(phone || email) && (
				<div className="flex flex-wrap gap-1.5 border-b border-card-line px-4 py-3">
					{phone && (
						<CardAction href={`tel:${phone}`} label={`Call ${name}`}>
							Call
						</CardAction>
					)}
					{email && (
						<CardAction href={`mailto:${email}`} label={`Email ${name}`}>
							Email
						</CardAction>
					)}
				</div>
			)}

			{error ? (
				<p className="px-4 py-3 text-[11.5px] text-muted">{error}</p>
			) : (
				<dl className="space-y-2 px-4 py-3">
					{facts.map((fact) => (
						<div key={fact.label} className="flex items-baseline justify-between gap-3">
							<dt className="flex-none text-[11.5px] text-muted">{fact.label}</dt>
							<dd className="tabular min-w-0 truncate text-right text-[12px] font-semibold text-ink">
								{/* A dash, not a blank: see the note above on absent. While
								    the read is still in flight it is an ellipsis instead, so
								    "not known" and "not arrived yet" do not look alike. */}
								{fact.value ?? (loading ? "…" : "Not available")}
							</dd>
						</div>
					))}
				</dl>
			)}

			<OpenRecord {...open} />
		</>
	);
}

/**
 * The way out of the card and into the record.
 *
 * **Through the router, not a bare `<a href>`.** The router is mounted under a
 * basename and an anchor carries none of it, so `/admin/registry/volunteer/…`
 * went to the site rather than to this app and Frappe answered with its own
 * "Page not found" — the same failure `appRoute` was written for, arriving in
 * the one link on this card that exists to be followed.
 */
function OpenRecord({ to, label }: { to: string; label: string }) {
	const style =
		"block border-t border-card-line bg-surface px-4 py-3 text-[12px] font-bold text-blue-press hover:bg-blue-soft";
	const route = appRoute(to);

	return route === null ? (
		<a href={to} className={style}>
			{label} →
		</a>
	) : (
		<Link to={route} className={style}>
			{label} →
		</Link>
	);
}

/** The face, or the initials the society has instead. */
function CardAvatar({ name, photo }: { name: string; photo?: string | null }) {
	if (photo) {
		return (
			<img
				src={photo}
				alt=""
				className="h-11 w-11 flex-none rounded-full object-cover ring-1 ring-card-line"
			/>
		);
	}

	const letters = name
		.split(/\s+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((part) => part[0]?.toUpperCase() ?? "")
		.join("");

	return (
		<span
			aria-hidden="true"
			className="grid h-11 w-11 flex-none place-items-center rounded-full bg-blue-soft text-[13px] font-bold text-blue-press"
		>
			{letters || "?"}
		</span>
	);
}

/** A call or email link, sized to be pressed on a phone. */
function CardAction({
	href,
	label,
	children,
}: {
	href: string;
	label: string;
	children: ReactNode;
}) {
	return (
		<a
			href={href}
			aria-label={label}
			className="inline-flex min-h-[30px] items-center rounded-full border border-card-line px-3 text-[11.5px] font-semibold text-slate-strong transition hover:border-blue hover:text-blue-press"
		>
			{children}
		</a>
	);
}
