import {
	type ReactNode,
	useCallback,
	useEffect,
	useId,
	useLayoutEffect,
	useRef,
	useState,
} from "react";

import { cx } from "./primitives";

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
 * **It never opens off the edge of the screen**, and that is the difference
 * between this and `HoverCard`, which places itself below-left and lets its
 * container worry about it. That is fine in a narrow column and wrong in a
 * register: the name column is at the left of a table that scrolls, the last
 * row is at the bottom of the viewport, and a card that opened below it would
 * put half of somebody's phone number under the fold. So the card measures
 * itself once it is open and flips above or left when there is not room —
 * measured rather than guessed, because the card's height depends on what
 * arrived in it.
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
	const [place, setPlace] = useState<{ above: boolean; right: boolean }>({
		above: false,
		right: false,
	});

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
			if (holder.current?.contains(event.target as Node)) return;

			close();
		};

		document.addEventListener("keydown", onKey);
		document.addEventListener("mousedown", onPointer);

		return () => {
			document.removeEventListener("keydown", onKey);
			document.removeEventListener("mousedown", onPointer);
		};
	}, [pinned, close]);

	// Measured after the card is in the DOM and before the browser paints, so it
	// never appears in the wrong place for a frame. `getBoundingClientRect` is
	// zero-everything in jsdom, which resolves to the default placement — the
	// same one a wide desktop viewport gets.
	useLayoutEffect(() => {
		if (!open || !trigger.current || !card.current) return;

		const anchor = trigger.current.getBoundingClientRect();
		const height = card.current.offsetHeight || 0;
		const room = {
			below: window.innerHeight - anchor.bottom,
			right: window.innerWidth - anchor.left,
		};

		setPlace({
			// Flip up only when there is genuinely more room up there: a card
			// that flipped whenever it was slightly short would jump about on a
			// short viewport where neither side fits.
			above: room.below < height + 16 && anchor.top > room.below,
			right: room.right < width + 16,
		});
	}, [open, width]);

	return (
		<div
			ref={holder}
			className={cx("relative inline-block", className)}
			onMouseEnter={() => setOpen(true)}
			onMouseLeave={() => !pinned && setOpen(false)}
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
					if (holder.current?.contains(event.relatedTarget as Node)) return;

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

			{open && (
				<div
					ref={card}
					id={id}
					role="dialog"
					aria-label="Person summary"
					style={{ width }}
					className={cx(
						"absolute z-40 rounded-xl border border-card-line bg-white p-4 text-left shadow-[0_18px_45px_rgba(16,32,51,0.16)]",
						place.above ? "bottom-full mb-1.5" : "top-full mt-1.5",
						place.right ? "right-0" : "left-0",
						cardClassName,
					)}
				>
					{children()}
				</div>
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
			<div className="flex items-start gap-3">
				<CardAvatar name={name} photo={photo} />

				<div className="min-w-0 flex-1">
					<div className="truncate text-[13.5px] font-semibold text-ink">{name}</div>
					{place && <div className="mt-0.5 truncate text-[11.5px] text-muted">{place}</div>}
					{status && <div className="mt-1.5">{status}</div>}
				</div>
			</div>

			{(phone || email) && (
				<div className="mt-3 flex flex-wrap gap-1.5">
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
				<p className="mt-3 border-t border-card-line pt-3 text-[11.5px] text-muted">{error}</p>
			) : (
				<dl className="mt-3 space-y-1.5 border-t border-card-line pt-3">
					{facts.map((fact) => (
						<div key={fact.label} className="flex items-baseline justify-between gap-3">
							<dt className="flex-none text-[11.5px] text-muted">{fact.label}</dt>
							<dd className="tabular min-w-0 truncate text-right text-[12px] font-semibold text-ink">
								{/* A dash, not a blank: see the note above on absent. While
								    the read is still in flight it is an ellipsis instead, so
								    "not known" and "not arrived yet" do not look alike. */}
								{fact.value ?? (loading ? "…" : "—")}
							</dd>
						</div>
					))}
				</dl>
			)}

			<a
				href={open.to}
				className="mt-3 block border-t border-card-line pt-3 text-[12px] font-semibold text-blue-press hover:underline"
			>
				{open.label} →
			</a>
		</>
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
