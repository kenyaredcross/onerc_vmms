import { type ReactNode, useEffect, useId, useRef, useState } from "react";

import { cx } from "./primitives";

/**
 * A card that opens beside something when you point at it — or focus it, or tap
 * it.
 *
 * **Hover is the nickname, not the contract.** A card that only opened on
 * `mouseenter` would be invisible to anybody on a phone and unreachable by
 * keyboard, which on a screen a coordinator uses to decide who gets deployed is
 * not a rough edge but a whole class of user shut out. So the trigger is a real
 * `<button>` and the card opens on hover, on focus, and on click. Click also
 * *pins* it: pointing at a row and reading four lines about somebody is a
 * different act from moving the mouse across the list, and the second must not
 * close what the first opened.
 *
 * **It closes on Escape and on a click outside**, the two things a person
 * already knows how to do with a popover, and it is `aria-expanded` +
 * `aria-controls` so a screen reader is told the button reveals something
 * rather than left to guess.
 *
 * **The content is a render prop, and it is only called while open.** That is
 * what lets a caller fetch on open — the candidate card asks for one
 * volunteer's deployment history the moment somebody looks at them, rather than
 * every row of a search paying for it up front. The search was deliberately made
 * cheap; fattening its payload to fill a card most rows never show would undo
 * that.
 *
 * **Placement is deliberately dumb.** The card sits below-left of the trigger
 * and the trigger's container is what decides whether that fits. A floating
 * library that measured the viewport would be a dependency and a scroll
 * listener to solve a problem this app does not have: these cards appear in a
 * list, in a column, with room beneath every row but the last.
 */
export function HoverCard({
	label,
	children,
	className,
	cardClassName,
	align = "left",
}: {
	/** The trigger. Rendered inside a button, so keep it to text and spans. */
	label: ReactNode;
	/** Called only while the card is open, which is what makes fetch-on-open work. */
	children: () => ReactNode;
	className?: string;
	cardClassName?: string;
	align?: "left" | "right";
}) {
	const [open, setOpen] = useState(false);
	const [pinned, setPinned] = useState(false);
	const holder = useRef<HTMLDivElement>(null);
	const id = useId();

	// Pinned cards are dismissed the way every popover is: Escape, or a click
	// somewhere else. Both listeners are only attached while one is pinned, so a
	// list of fifty candidates is not fifty document listeners.
	useEffect(() => {
		if (!pinned) return;

		const onKey = (event: KeyboardEvent) => {
			if (event.key !== "Escape") return;

			setPinned(false);
			setOpen(false);
		};

		const onClick = (event: MouseEvent) => {
			if (holder.current?.contains(event.target as Node)) return;

			setPinned(false);
			setOpen(false);
		};

		document.addEventListener("keydown", onKey);
		document.addEventListener("mousedown", onClick);

		return () => {
			document.removeEventListener("keydown", onKey);
			document.removeEventListener("mousedown", onClick);
		};
	}, [pinned]);

	return (
		<div
			ref={holder}
			className={cx("relative inline-block", className)}
			onMouseEnter={() => setOpen(true)}
			onMouseLeave={() => !pinned && setOpen(false)}
		>
			<button
				type="button"
				aria-expanded={open}
				aria-controls={open ? id : undefined}
				onFocus={() => setOpen(true)}
				onBlur={() => !pinned && setOpen(false)}
				onClick={() => {
					setPinned((was) => !was);
					setOpen(true);
				}}
				className="cursor-help text-left underline decoration-hairline-strong decoration-dotted underline-offset-[3px] outline-none focus-visible:decoration-navy"
			>
				{label}
			</button>

			{open && (
				<div
					id={id}
					role="dialog"
					className={cx(
						"absolute top-full z-30 mt-1.5 w-[19rem] rounded-xl border border-card-line bg-white p-3.5 text-left shadow-lg",
						align === "right" ? "right-0" : "left-0",
						cardClassName,
					)}
				>
					{children()}
				</div>
			)}
		</div>
	);
}
