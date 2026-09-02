import { Link } from "react-router-dom";
import { useEffect, useRef, useState, type ReactNode } from "react";

export function cx(...parts: Array<string | false | null | undefined>): string {
	return parts.filter(Boolean).join(" ");
}

/* ------------------------------------------------------------------ layout */

/**
 * One step of the trail above a page title.
 *
 * `to` is optional and its absence is meaningful: the last crumb is where you
 * already are, so it is not a link. A trail whose final step is clickable
 * invites somebody to navigate to the page they are on.
 */
export interface Crumb {
	label: ReactNode;
	to?: string;
}

/**
 * The head of every screen: what this is, where it sits, and what you may do
 * to it.
 *
 * **The trail goes under the title, not over it.** Above, it competes with the
 * navigation for the top of the page and pushes the title down; below, the
 * title lands where the eye arrives and the trail answers the follow-up
 * question. That is the reference set's arrangement and it is the right way
 * round.
 *
 * `eyebrow` predates the trail — the small tracked-out red line the landing
 * page uses above a section title. It is deliberately *not* what a signed-in
 * screen should use to carry a person's placement: a four-rung geo path set in
 * the signal colour at full uppercase is 80 characters of the loudest thing on
 * the page, sitting above the one word that matters. `meta` is that slot done
 * quietly, and it takes an icon so it reads as a location rather than as a
 * second heading.
 */
export function PageHeading({
	eyebrow,
	title,
	trail,
	meta,
	lead,
	actions,
}: {
	eyebrow?: ReactNode;
	title: ReactNode;
	trail?: Crumb[];
	/** A quiet line under the title: where this person is, what this record is. */
	meta?: ReactNode;
	/** One sentence under the trail. Longer than that belongs in a card. */
	lead?: ReactNode;
	actions?: ReactNode;
}) {
	return (
		<div className="mb-6">
			<div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
				<div className="min-w-0">
					{eyebrow && <div className="eyebrow mb-2">{eyebrow}</div>}

					{/* The *page* title is in the top row of the shell; this is the
					    heading of the content beneath it — "Welcome back, Amina",
					    "Deployment dashboard". So it is an h2, and it is set in the
					    redesign's medium weight rather than the previous system's
					    extrabold. Rendered as an h2 so the document has exactly one
					    h1 (the shell's) and the outline stays honest. */}
					<h2 className="text-[26px] font-semibold leading-[1.15] tracking-[-0.02em] text-ink sm:text-[28px]">
						{title}
					</h2>

					{meta && (
						<div className="mt-2 flex items-start gap-1.5 text-[12.5px] leading-snug text-slate-body">
							<svg
								viewBox="0 0 24 24"
								width="14"
								height="14"
								fill="none"
								aria-hidden="true"
								className="mt-[3px] flex-none text-slate-faint"
							>
								<path
									d="M12 21s7-6.3 7-11a7 7 0 1 0-14 0c0 4.7 7 11 7 11Zm0-8.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z"
									stroke="currentColor"
									strokeWidth="1.8"
									strokeLinejoin="round"
								/>
							</svg>
							<span className="min-w-0">{meta}</span>
						</div>
					)}

					{trail && trail.length > 0 && (
						<nav aria-label="Breadcrumb" className="mt-2">
							<ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[12.5px] text-slate-faint">
								{trail.map((crumb, index) => (
									<li key={index} className="flex items-center gap-2">
										{index > 0 && (
											<span aria-hidden="true" className="text-card-line">
												/
											</span>
										)}
										{crumb.to ? (
											<Link
												to={crumb.to}
												className="font-medium transition hover:text-blue hover:underline"
											>
												{crumb.label}
											</Link>
										) : (
											<span aria-current="page" className="font-medium text-slate-body">
												{crumb.label}
											</span>
										)}
									</li>
								))}
							</ol>
						</nav>
					)}
				</div>

				{actions && (
					<div className="flex flex-wrap items-center gap-2 pt-1">{actions}</div>
				)}
			</div>

			{lead && (
				<p className="mt-2.5 max-w-2xl text-[13.5px] leading-relaxed text-slate-body">{lead}</p>
			)}
		</div>
	);
}

/**
 * A panel of content.
 *
 * **A 1px cool hairline and the faintest lift** — `.p-card`, the same panel the
 * volunteer portal draws. It used to be borderless with a wide soft shadow, on
 * a grey ground; on the portal's near-white canvas that read as a smudge rather
 * than as an edge, so the hairline does the separating now and the shadow only
 * stops it looking printed. `pad` exists for the two cases that must not have
 * the default inset: a card whose first child is a table (the rule has to
 * reach both edges) and a card whose first child is a photograph.
 */
export function Card({
	className,
	pad = true,
	hover,
	children,
}: {
	className?: string;
	pad?: boolean;
	/** Lifts on pointer. Only for a card that is itself a link or a button. */
	hover?: boolean;
	children: ReactNode;
}) {
	return (
		<div
			className={cx(
				"p-card",
				pad && "p-5",
				hover && "transition duration-200 hover:border-blue-line",
				className,
			)}
		>
			{children}
		</div>
	);
}

/**
 * The label above a card, outside it.
 *
 * This is the move that makes a dashboard scan in one pass. Nine cards each
 * carrying their own heading means nine headings at nine different heights,
 * and the eye has to enter every card to find out what it is. A column of
 * short labels down the left of the page can be read without entering
 * anything.
 *
 * `action` is the "View all ›" on the right — a destination, not a verb. A
 * button that changes something belongs inside the card it changes.
 */
export function SectionLabel({
	children,
	action,
	className,
}: {
	children: ReactNode;
	action?: ReactNode;
	className?: string;
}) {
	return (
		<div className={cx("mb-3 flex items-end justify-between gap-4", className)}>
			<h2 className="section-label">{children}</h2>
			{action && <div className="flex items-center gap-3">{action}</div>}
		</div>
	);
}

/** The "View all ›" beside a `SectionLabel`. */
export function SectionLink({ to, children }: { to: string; children: ReactNode }) {
	return (
		<Link
			to={to}
			className="whitespace-nowrap text-[12px] font-semibold text-blue transition hover:text-blue-hover"
		>
			{children}
		</Link>
	);
}

/**
 * A heading *inside* a card.
 *
 * Distinct from `SectionLabel`, which sits outside one. Both exist because a
 * card sometimes needs to name a part of itself, and that heading must be
 * quieter than the label naming the whole card or the hierarchy inverts.
 */
export function SectionTitle({ children }: { children: ReactNode }) {
	return (
		<h3 className="mb-3 text-[13.5px] font-semibold tracking-[-0.01em] text-ink">{children}</h3>
	);
}

/** A hairline between parts of a card. */
export function Divide({ className }: { className?: string }) {
	return <div className={cx("h-px bg-card-line", className)} aria-hidden="true" />;
}

/* ------------------------------------------------------------------ atoms */

const TONES = {
	navy: "bg-rail text-white",
	// A wash rather than a fill. Every caller in the console uses this for a
	// *count* beside a heading — "12 overdue", "3 still running" — and a page
	// of solid blue chips reads as a page of buttons. The soft pair says the
	// same thing at the weight a count deserves.
	signal: "bg-blue-soft text-blue-press",
	quiet: "border border-card-line bg-white text-slate-strong",
	// `page` used to be the near-white page ground. That ground is the shell
	// grey now, which is too dark to sit a chip on inside a white panel, so this
	// takes the inset surface instead — the same one every other in-panel
	// surface uses.
	page: "bg-surface text-slate-strong",
} as const;

export function Pill({
	tone = "quiet",
	children,
}: {
	tone?: keyof typeof TONES;
	children: ReactNode;
}) {
	return (
		<span
			className={cx(
				"inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-3.5 py-1.5 text-[11.5px] font-medium",
				TONES[tone],
			)}
		>
			{children}
		</span>
	);
}

/**
 * A state badge whose colour is chosen from the *shape* of the state, never
 * from a stage label.
 *
 * The approval engine's states are a closed set defined in `approvals/states.py`
 * and it is safe to key colour off them. Stage labels are society configuration
 * and are never compared, here or anywhere else, which is the rule
 * `tests/test_no_stage_branching.py` enforces on the Python side.
 *
 * **A soft fill with a dot, and no outline.** It was an outlined pill; on the
 * portal's near-white canvas an outline plus a fill plus a dot was three
 * signals for one fact, and a register screen carries one of these on every
 * row. The tint alone separates it from the panel, and the dot means the state
 * survives being read by somebody who cannot tell the two greens apart — which
 * is the part that was actually doing the work.
 */
const NEUTRAL = "bg-surface text-slate-strong";

const STATE_TONES: Record<string, string> = {
	Approved: "bg-success-soft text-success",
	Active: "bg-success-soft text-success",
	Rejected: "bg-danger-soft text-danger",
	Expired: "bg-warning-soft text-warning",
	Withdrawn: NEUTRAL,
	Draft: "bg-warning-soft text-warning",
	Planned: NEUTRAL,
	Cancelled: NEUTRAL,
	Completed: "bg-success-soft text-success",
	Pending: "bg-warning-soft text-warning",
	Accepted: "bg-success-soft text-success",
	Assigned: "bg-blue-soft text-blue-press",
	Declined: NEUTRAL,
	Submitted: "bg-blue-soft text-blue-press",
	"In Review": "bg-blue-soft text-blue-press",
	Shortlisted: "bg-warning-soft text-warning",
	Hold: NEUTRAL,
	Closed: NEUTRAL,
	Open: "bg-blue-soft text-blue-press",
};

export function StateBadge({ state }: { state?: string | null }) {
	if (!state) return null;

	const tone = STATE_TONES[state] ?? NEUTRAL;

	return (
		<span
			className={cx(
				"inline-flex flex-none items-center gap-1.5 whitespace-nowrap rounded-md px-2 py-1 text-[11px] font-semibold",
				tone,
			)}
		>
			<span className="h-1.5 w-1.5 flex-none rounded-full bg-current" aria-hidden="true" />
			{state}
		</span>
	);
}

/**
 * Somebody's initials in a circle, where a photograph would go.
 *
 * The register screens show a person per row and a row with nothing at its
 * start reads as a spreadsheet. This app holds no avatars — identity lives on
 * core's Red Profile and a photograph is not one of its fields — so initials
 * on the brand navy is the honest version of the same shape.
 */
/**
 * Somebody's face, or their initials when there is no face to show.
 *
 * **`photo` is optional and falling back is the ordinary case**, not an error
 * one. Most registers have photographs for some people and not others — a
 * volunteer registered at a branch desk on paper has none — and a screen that
 * drew a broken image or a grey silhouette for them would make an absence look
 * like a fault. Initials read as a person either way.
 *
 * `aria-hidden` throughout: the name is always beside this in the markup that
 * uses it, and announcing it twice is worse than not announcing it at all.
 */
export function Avatar({
	name,
	photo,
	size = 36,
	tone = "navy",
	ring = false,
}: {
	name?: string | null;
	photo?: string | null;
	size?: number;
	tone?: "navy" | "signal" | "page";
	/**
	 * A hairline around the circle, for the one place an avatar is the largest
	 * thing on the page rather than a 34px marker in a table row. A photograph
	 * with a pale background bleeds into a white card at 88px in a way it never
	 * does at 34px, and the ring is what stops the face looking like a cut-out.
	 * Off by default: in a list it would draw a second grid the eye has to
	 * ignore.
	 */
	ring?: boolean;
}) {
	const letters = (name ?? "")
		.split(/\s+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((part) => part[0]?.toUpperCase() ?? "")
		.join("");

	const tones = {
		navy: "bg-navy/[.07] text-navy",
		signal: "bg-blue/[.10] text-blue-press",
		page: "bg-surface text-slate-body",
	} as const;

	const ringed = ring ? "ring-1 ring-card-line ring-offset-2 ring-offset-white" : "";

	if (photo) {
		return (
			<img
				src={photo}
				alt=""
				aria-hidden="true"
				loading="lazy"
				style={{ width: size, height: size }}
				className={cx("flex-none rounded-full object-cover", ringed)}
			/>
		);
	}

	return (
		<span
			aria-hidden="true"
			style={{ width: size, height: size, fontSize: Math.round(size * 0.36) }}
			className={cx(
				"grid flex-none place-items-center rounded-full font-semibold",
				tones[tone],
				ringed,
			)}
		>
			{letters || "·"}
		</span>
	);
}

/* ------------------------------------------------------------------- stats */

/**
 * The six tints a tile may carry, in the order a screen should use them.
 *
 * A row of figures wants to read as several things rather than one thing
 * repeated, and that is the whole job here. **Nothing means anything**: a
 * screen takes them by position (`TINTS[index % TINTS.length]`) or names one
 * because it looks right beside its neighbours, and no code anywhere branches
 * on which it got. Meaning is navy, signal and `STATE_TONES`.
 */
export const TINTS = ["navy", "teal", "violet", "amber", "sky", "rose"] as const;

export type Tint = (typeof TINTS)[number];

const TINT_CLASS: Record<Tint, string> = {
	navy: "bg-tint-navy-soft text-tint-navy",
	teal: "bg-tint-teal-soft text-tint-teal",
	violet: "bg-tint-violet-soft text-tint-violet",
	amber: "bg-tint-amber-soft text-tint-amber",
	sky: "bg-tint-sky-soft text-tint-sky",
	rose: "bg-tint-rose-soft text-tint-rose",
};

/**
 * One figure, with its icon and what it is called.
 *
 * **The label goes above the number.** Underneath, the eye reads a bare
 * number first and has to go back for what it counted; above, the two are read
 * once in the order they make sense. `hint` is the small line under the figure
 * for the thing a label cannot carry — a date, a denominator, a comparison.
 *
 * The tile is a link when `to` is given, and the whole tile is the target
 * rather than a "view" control tucked in a corner: a figure a person wants to
 * act on is a figure they will click.
 */
export function StatTile({
	label,
	value,
	hint,
	icon,
	tint = "navy",
	to,
}: {
	label: ReactNode;
	value: ReactNode;
	hint?: ReactNode;
	icon?: (props: { size?: number; className?: string }) => ReactNode;
	tint?: Tint;
	to?: string;
}) {
	const body = (
		<>
			<div className="flex items-start justify-between gap-3">
				<div className="min-w-0">
					<div className="truncate text-[11.5px] font-normal text-muted">{label}</div>
					<div className="tabular mt-2 text-[28px] font-semibold leading-none tracking-[-0.025em] text-ink">
						{value}
					</div>
				</div>

				{icon && (
					<span
						className={cx(
							"grid h-11 w-11 flex-none place-items-center rounded-control",
							TINT_CLASS[tint],
						)}
						aria-hidden="true"
					>
						{icon({ size: 20 })}
					</span>
				)}
			</div>

			{hint && <div className="mt-2.5 text-[11.5px] leading-snug text-slate-faint">{hint}</div>}
		</>
	);

	// `h-full` so a row of tiles beside a taller card squares off with it rather
	// than leaving a ragged shelf of white halfway down the row.
	if (to) {
		return (
			<Link
				to={to}
				className="p-card block h-full p-5 transition duration-200 hover:border-blue-line focus-visible:border-blue-line"
			>
				{body}
			</Link>
		);
	}

	return <div className="card h-full p-5">{body}</div>;
}

/**
 * The grid a row of `StatTile`s sits in, so every screen spaces them alike.
 *
 * Two across as soon as there is room for two, rather than waiting for the `sm`
 * breakpoint: four figures stacked one per row is most of a phone screen spent
 * on four numbers, and the reader has to scroll past their own summary to reach
 * the page. The arbitrary 420px is where a tile still fits its icon beside a
 * four-digit figure.
 */
export function StatGrid({ children, className }: { children: ReactNode; className?: string }) {
	return (
		<div className={cx("grid gap-4 min-[420px]:grid-cols-2 xl:grid-cols-4", className)}>
			{children}
		</div>
	);
}

/** A figure with no tile around it, for use inside a card that has its own. */
export function Stat({ value, label }: { value: ReactNode; label: ReactNode }) {
	return (
		<div>
			<div className="tabular text-[24px] font-semibold leading-none tracking-[-0.025em] text-ink">
				{value}
			</div>
			<div className="mt-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-faint">
				{label}
			</div>
		</div>
	);
}

/**
 * A labelled bar with its figure on the right.
 *
 * The reference set uses this shape for anything that is "so far, out of a
 * total", and it is the honest way to draw a proportion: the bar is the
 * comparison and the number is the fact, so neither has to be inferred from
 * the other.
 *
 * `value` and `total` are numbers rather than a percentage, because a screen
 * that has already divided cannot show you what it divided.
 *
 * **`figure` exists because `total` is not always a total.** Where the bars are
 * scaled against the largest of a set rather than against a sum — which is the
 * right scaling when you want the *shape* of a breakdown — printing
 * "value / total" beside the largest one reads as "88 out of 88", which is a
 * completeness claim nobody made. A caller in that position passes the figure
 * it actually means and the denominator stays where it belongs, in the bar.
 */
export function Meter({
	label,
	value,
	total,
	figure,
	tint = "navy",
	caption,
}: {
	label: ReactNode;
	value: number;
	total: number;
	/** Replaces the "value / total" figure on the right. */
	figure?: ReactNode;
	tint?: Tint;
	caption?: ReactNode;
}) {
	const pct = total > 0 ? Math.min(100, Math.max(0, (value / total) * 100)) : 0;

	const bar: Record<Tint, string> = {
		navy: "bg-tint-navy",
		teal: "bg-tint-teal",
		violet: "bg-tint-violet",
		amber: "bg-tint-amber",
		sky: "bg-tint-sky",
		rose: "bg-tint-rose",
	};

	return (
		<div>
			<div className="mb-2 flex items-baseline justify-between gap-3">
				<span className="truncate text-[12.5px] font-semibold text-slate-strong">{label}</span>
				<span className="tabular flex-none text-[12px] font-bold text-ink">
					{figure ?? (
						<>
							{value}
							<span className="font-semibold text-slate-faint"> / {total}</span>
						</>
					)}
				</span>
			</div>

			<div
				className="h-1.5 w-full overflow-hidden rounded-full bg-surface"
				role="progressbar"
				aria-valuenow={value}
				aria-valuemin={0}
				aria-valuemax={total}
			>
				<div
					className={cx("h-full rounded-full transition-[width] duration-500", bar[tint])}
					style={{ width: `${pct}%` }}
				/>
			</div>

			{caption && <div className="mt-1.5 text-[11px] text-slate-faint">{caption}</div>}
		</div>
	);
}

/**
 * A proportion drawn as a ring, for the one-figure case.
 *
 * A `Meter` needs a row; this needs a square, so it is what goes beside a
 * label in a tight card. Pure SVG, no library: two circles and a dash offset.
 */
export function Ring({
	value,
	total,
	size = 56,
	tint = "navy",
	children,
}: {
	value: number;
	total: number;
	size?: number;
	tint?: Tint;
	/** What sits in the middle. Defaults to the rounded percentage. */
	children?: ReactNode;
}) {
	const pct = total > 0 ? Math.min(1, Math.max(0, value / total)) : 0;
	const stroke = Math.max(4, Math.round(size * 0.1));
	const r = (size - stroke) / 2;
	const circumference = 2 * Math.PI * r;

	const colour: Record<Tint, string> = {
		navy: "#1F4E8C",
		teal: "#0E7C74",
		violet: "#6B4EA8",
		amber: "#9A6608",
		sky: "#1C6E9E",
		rose: "#A83E5B",
	};

	return (
		<div className="relative flex-none" style={{ width: size, height: size }}>
			<svg width={size} height={size} className="-rotate-90" aria-hidden="true">
				<circle
					cx={size / 2}
					cy={size / 2}
					r={r}
					fill="none"
					stroke="#EDF0F5"
					strokeWidth={stroke}
				/>
				<circle
					cx={size / 2}
					cy={size / 2}
					r={r}
					fill="none"
					stroke={colour[tint]}
					strokeWidth={stroke}
					strokeLinecap="round"
					strokeDasharray={circumference}
					strokeDashoffset={circumference * (1 - pct)}
					className="transition-[stroke-dashoffset] duration-700"
				/>
			</svg>

			<div className="tabular absolute inset-0 grid place-items-center text-[12px] font-bold text-ink">
				{children ?? `${Math.round(pct * 100)}%`}
			</div>
		</div>
	);
}

/* ----------------------------------------------------------------- buttons */

const BUTTONS = {
	/** The one thing this screen is for. Blue, and only ever one per view. */
	primary: "bg-blue text-white hover:bg-blue-hover active:bg-blue-press",
	/** The authority charcoal — a strong second action, or a dark-surface action. */
	navy: "bg-rail text-white hover:bg-rail/90",
	/**
	 * A wash of the accent with the accent as the text. Louder than an outline
	 * and quieter than a fill, which is the register a "second thing you might
	 * do" wants.
	 */
	soft: "bg-blue-soft text-blue-press hover:bg-blue-line/50",
	quiet:
		"border border-rail-line bg-white text-slate-strong hover:border-slate-faint hover:text-ink",
	ghost: "text-blue hover:bg-blue-soft",
	/**
	 * Destructive, and never carried by colour alone.
	 *
	 * The border and the warning glyph do the work a red fill used to do on its
	 * own, so the control is still distinguishable in greyscale, under a colour
	 * filter, and in Windows high-contrast mode where backgrounds are dropped.
	 * The *label* is the real signal and callers are expected to say what will
	 * be destroyed — "Delete draft", not "Delete".
	 */
	danger:
		"border border-danger-line bg-white text-danger hover:bg-danger-soft",
} as const;

// 8px, not a pill, and the app's own face rather than the display one. Both
// changed when the console moved into the portal's language: `rounded-full` was
// the old system's most characteristic move and it is not this one's.
const BUTTON_BASE =
	"inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-[13px] font-semibold transition disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:bg-inherit";

interface ButtonProps {
	variant?: keyof typeof BUTTONS;
	className?: string;
	children: ReactNode;
	onClick?: () => void;
	disabled?: boolean;
	type?: "button" | "submit";
	/**
	 * The action is in flight.
	 *
	 * Disables the control and shows a spinner *in place of* the icon slot while
	 * keeping the label, so the button does not change width mid-click and the
	 * label still says what is happening. `aria-busy` carries the same fact to a
	 * screen reader, which a spinner alone does not.
	 */
	busy?: boolean;
	/** Accessible name, when the label alone is not specific enough. */
	label?: string;
}

export function Button({
	variant = "primary",
	className,
	children,
	onClick,
	disabled,
	type = "button",
	busy = false,
	label,
}: ButtonProps) {
	return (
		<button
			type={type}
			onClick={onClick}
			disabled={disabled || busy}
			aria-busy={busy || undefined}
			aria-label={label}
			className={cx(BUTTON_BASE, BUTTONS[variant], className)}
		>
			{busy && (
				<span
					aria-hidden="true"
					className="h-3.5 w-3.5 flex-none animate-spin rounded-full border-2 border-current border-t-transparent motion-reduce:animate-none"
				/>
			)}
			{variant === "danger" && !busy && (
				// The shape that survives greyscale. Paired with the label, which is
				// where the real warning lives.
				<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" className="flex-none">
					<path
						d="M12 4 2.5 20h19L12 4Zm0 6v4m0 3v.5"
						fill="none"
						stroke="currentColor"
						strokeWidth="1.9"
						strokeLinecap="round"
						strokeLinejoin="round"
					/>
				</svg>
			)}
			{children}
		</button>
	);
}

export function ButtonLink({
	to,
	variant = "primary",
	className,
	children,
}: {
	to: string;
	variant?: keyof typeof BUTTONS;
	className?: string;
	children: ReactNode;
}) {
	const cls = cx(BUTTON_BASE, BUTTONS[variant], className);

	// An external or site-level destination is a real navigation; a route inside
	// the SPA is not. Getting this wrong means a full page reload on every
	// internal link, or a route the router cannot match on every external one.
	return to.startsWith("/portal") ? (
		<Link to={to.replace(/^\/portal/, "") || "/"} className={cls}>
			{children}
		</Link>
	) : (
		<a href={to} className={cls}>
			{children}
		</a>
	);
}

/**
 * A round icon-only control — the "⋮", the close, the step arrows.
 *
 * `label` is required and becomes the accessible name, because an icon button
 * with no text is silent to a screen reader and this is the shape that most
 * often ships that way.
 */
export function IconButton({
	label,
	onClick,
	disabled,
	className,
	children,
}: {
	label: string;
	onClick?: () => void;
	disabled?: boolean;
	className?: string;
	children: ReactNode;
}) {
	return (
		<button
			type="button"
			aria-label={label}
			title={label}
			onClick={onClick}
			disabled={disabled}
			className={cx(
				"grid h-8 w-8 flex-none place-items-center rounded-lg text-slate-faint transition hover:bg-canvas hover:text-ink disabled:cursor-not-allowed disabled:opacity-40",
				className,
			)}
		>
			{children}
		</button>
	);
}

/* ------------------------------------------------------------------ states */

/**
 * Waiting, said once and the same way everywhere.
 *
 * **Centred, not tucked into the top-left.** A spinner pinned to the start of a
 * column reads as a broken row rather than as the screen thinking, and the eye
 * has to go looking for it. Centring it in whatever space it was given puts it
 * where somebody is already looking.
 *
 * `page` is the whole-screen variant, for a route whose code has not arrived
 * yet: there is no layout to sit inside, so it takes the viewport and names the
 * screen it is fetching. Naming it matters more than it looks — "Loading" alone
 * cannot tell a slow page from a wrong link.
 */
export function Spinner({ label = "Loading…", page = false }: { label?: string; page?: boolean }) {
	return (
		<div
			className={cx(
				"flex flex-col items-center justify-center gap-3 text-center",
				page ? "min-h-[70vh] w-full py-16" : "w-full py-10",
			)}
			role="status"
			aria-live="polite"
		>
			<span
				className={cx(
					"animate-spin rounded-full border-rail-line border-t-blue",
					page ? "h-8 w-8 border-[3px]" : "h-4 w-4 border-2",
				)}
			/>
			<span className={cx("text-slate-body", page ? "text-[13.5px] font-semibold" : "text-[13px]")}>
				{label}
			</span>
		</div>
	);
}

/**
 * A card-shaped placeholder for one that has not arrived.
 *
 * Used where a spinner would be worse: a dashboard of six cards that each pop
 * in at their own moment reflows under the reader's eye, and a spinner per card
 * is six things spinning. A block of the right size holds the layout still.
 */
export function Skeleton({ className }: { className?: string }) {
	return (
		<div
			aria-hidden="true"
			className={cx("animate-pulse rounded-control bg-hairline-soft", className)}
		/>
	);
}

export function ErrorNote({ children }: { children: ReactNode }) {
	return (
		<div className="flex items-start gap-3 rounded-xl border border-danger-line bg-danger-soft px-4 py-3 text-[13px] leading-relaxed text-danger">
			<svg
				viewBox="0 0 24 24"
				width="17"
				height="17"
				fill="none"
				aria-hidden="true"
				className="mt-px flex-none"
			>
				<path
					d="M12 8v5m0 3.5v.5M12 3 2 20h20L12 3Z"
					stroke="currentColor"
					strokeWidth="1.8"
					strokeLinejoin="round"
				/>
			</svg>
			<div className="min-w-0">{children}</div>
		</div>
	);
}

/**
 * Nothing here, said without drawing a box around the nothing.
 *
 * **`framed` is about where it is standing.** On the page ground a dashed
 * outline is what says "this is a region that would have had rows in it";
 * *inside* a card the same outline is a box drawn inside a box, and the two
 * borders 20px apart are the single ugliest thing an empty dashboard can do.
 * So every call site inside a `Card` passes `framed={false}` and gets the words
 * alone, which is all they needed.
 */
export function Empty({
	title,
	icon,
	action,
	framed = true,
	children,
}: {
	title: ReactNode;
	icon?: (props: { size?: number; className?: string }) => ReactNode;
	action?: ReactNode;
	framed?: boolean;
	children?: ReactNode;
}) {
	return (
		<div
			className={cx(
				"text-center",
				framed
					? "rounded-xl border border-dashed border-card-line bg-surface/40 px-6 py-10"
					: "px-2 py-6",
			)}
		>
			{icon && (
				<div
					className={cx(
						"mx-auto mb-3.5 grid h-11 w-11 place-items-center rounded-full text-slate-faint",
						framed ? "bg-white shadow-card" : "bg-surface",
					)}
				>
					{icon({ size: 19 })}
				</div>
			)}
			<p className="text-[13.5px] font-semibold text-ink">{title}</p>
			{children && (
				<p className="mx-auto mt-2 max-w-md text-[12.5px] leading-relaxed text-slate-body">
					{children}
				</p>
			)}
			{action && <div className="mt-4 flex flex-wrap justify-center gap-2">{action}</div>}
		</div>
	);
}

/**
 * A screen the design shows but the backend cannot yet serve.
 *
 * Says so plainly and does not invent a single row. The walkthrough rule in
 * `CLAUDE.md` puts it well: something that reads as though everything works is
 * worse than nothing, because somebody will follow it in front of an audience.
 * The same is true of a screen.
 *
 * **`needs` is written for the person looking at it, not for us.** It used to
 * carry the explanation a developer would want — the app the data lives in, the
 * source file the seam is in — and a volunteer opening the events tab was told
 * to go and read `vmmsx/buzz/services/events.py`. Somebody who cannot act on a
 * sentence should not be shown it: say what is not here yet in the society's
 * terms, and leave the internals to the code that has them.
 */
export function NotBuilt({
	what,
	needs,
	children,
}: {
	what: string;
	needs: string;
	children?: ReactNode;
}) {
	return (
		<div className="rounded-xl border border-dashed border-card-line bg-white px-8 py-12 text-center">
			<div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-full bg-surface">
				<svg viewBox="0 0 24 24" width="20" height="20" fill="none" aria-hidden="true">
					<path
						d="M12 8v5m0 3.5v.5M12 3 2 20h20L12 3Z"
						stroke="#8A93A1"
						strokeWidth="1.8"
						strokeLinejoin="round"
					/>
				</svg>
			</div>
			<p className="text-[15px] font-semibold text-ink">{what} is not here yet</p>
			<p className="mx-auto mt-2 max-w-lg text-[13px] leading-relaxed text-slate-body">{needs}</p>
			{children && <div className="mt-5">{children}</div>}
		</div>
	);
}

/* ------------------------------------------------------------------- lists */

/**
 * One row of a list of records: a mark, what it is, what is true of it, and
 * what you may do.
 *
 * **The reference set's list rows, and the reason its screens do not all look
 * like tables.** A table is right when a reader compares the same field down a
 * column; a list row is right when each entry is a thing in its own right and
 * the fields are its attributes. Most of this product is the second — an event,
 * a task, a membership — and drawing them as tables was most of what made the
 * screens feel like a database front end.
 *
 * `to` makes the whole row the target. Where a row carries its own controls,
 * leave `to` off and put a link in `title`, so a click on "Decline" is never a
 * click on the row.
 */
export function ListRow({
	lead,
	title,
	meta,
	trailing,
	to,
	onClick,
	className,
	children,
}: {
	/** The avatar, thumbnail or icon at the start. */
	lead?: ReactNode;
	title: ReactNode;
	/** The quiet line under the title. */
	meta?: ReactNode;
	/** Badges and controls at the end. */
	trailing?: ReactNode;
	to?: string;
	onClick?: () => void;
	className?: string;
	/** Anything that belongs under the whole row rather than beside the title. */
	children?: ReactNode;
}) {
	const inner = (
		<>
			<div className="flex items-center gap-3.5">
				{lead}

				<div className="min-w-0 flex-1">
					<div className="truncate text-[13px] font-semibold text-ink">{title}</div>
					{meta && <div className="mt-0.5 truncate text-[11.5px] text-slate-body">{meta}</div>}
				</div>

				{trailing && (
					<div className="flex flex-none items-center gap-2 sm:gap-2.5">{trailing}</div>
				)}
			</div>

			{children && <div className="mt-3">{children}</div>}
		</>
	);

	const base = cx(
		"block w-full rounded-control px-3 py-3 text-left transition",
		(to || onClick) && "hover:bg-surface",
		className,
	);

	if (to) {
		return (
			<Link to={to} className={base}>
				{inner}
			</Link>
		);
	}

	if (onClick) {
		return (
			<button type="button" onClick={onClick} className={base}>
				{inner}
			</button>
		);
	}

	return <div className={base}>{inner}</div>;
}

/**
 * The container `ListRow`s sit in, with a hairline between them.
 *
 * The rule is drawn by the *gap* rather than by a border on each row, so the
 * hover tint of a row is a solid block instead of a block with a line through
 * its bottom edge.
 */
export function List({ children, className }: { children: ReactNode; className?: string }) {
	return (
		<div className={cx("divide-y divide-hairline-soft", className)}>{children}</div>
	);
}

/* -------------------------------------------------------------- pagination */

/**
 * A pager over rows already in hand.
 *
 * **Client-side, and that is a decision rather than a shortcut.** Every listing
 * endpoint in this app is bounded at the server — `opportunities.PAGE` is 60,
 * `events.MAX_ROWS` is 60, the article call asks for a fixed limit — so the
 * browser is never paging through an unbounded set, and the row count shown is
 * the true count of what was returned rather than a guess at a total. Making
 * these offset queries would mean a round trip per page for a set that already
 * arrived whole, and a "page 4 of ?" nobody can answer.
 *
 * Renders nothing when everything fits on one page: a pager under a grid of
 * three cards is furniture explaining that there is no furniture.
 */
export function Pager({
	page,
	pageCount,
	onPage,
	total,
	noun = "results",
}: {
	page: number;
	pageCount: number;
	onPage: (next: number) => void;
	total: number;
	noun?: string;
}) {
	if (pageCount <= 1) return null;

	const step =
		"grid h-8 w-8 place-items-center rounded-lg border border-rail-line bg-white text-muted transition hover:border-blue hover:text-blue disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-rail-line disabled:hover:text-muted";

	return (
		<nav
			className="mt-8 flex flex-wrap items-center justify-between gap-4 border-t p-divide pt-5"
			aria-label="Pagination"
		>
			<p className="text-[12px] text-slate-faint" aria-live="polite">
				Page {page + 1} of {pageCount} · {total} {noun}
			</p>

			<div className="flex items-center gap-1.5">
				<button
					type="button"
					onClick={() => onPage(page - 1)}
					disabled={page === 0}
					className={step}
					aria-label="Previous page"
				>
					<svg viewBox="0 0 24 24" width="15" height="15" fill="none" aria-hidden="true">
						<path d="M15 5l-7 7 7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
					</svg>
				</button>

				{Array.from({ length: pageCount }, (_, index) => index).map((index) => (
					<button
						key={index}
						type="button"
						onClick={() => onPage(index)}
						aria-current={index === page ? "page" : undefined}
						className={cx(
							"h-8 min-w-8 rounded-lg px-2.5 text-[12.5px] font-semibold transition",
							index === page
								? "bg-navy text-white"
								: "border border-rail-line bg-white text-muted hover:border-blue hover:text-blue",
						)}
					>
						{index + 1}
					</button>
				))}

				<button
					type="button"
					onClick={() => onPage(page + 1)}
					disabled={page >= pageCount - 1}
					className={step}
					aria-label="Next page"
				>
					<svg viewBox="0 0 24 24" width="15" height="15" fill="none" aria-hidden="true">
						<path d="m9 5 7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
					</svg>
				</button>
			</div>
		</nav>
	);
}

/**
 * The state a `Pager` drives: which slice to render, and how many pages there
 * are.
 *
 * Takes the rows and hands back the page's worth, so a screen never does the
 * arithmetic itself. **The page resets whenever the row set changes** — a
 * person on page three who narrows a filter to four results must not be left
 * staring at an empty page three, which is the bug every hand-rolled pager
 * eventually has.
 */
export function usePaged<T>(rows: T[], size: number) {
	const [page, setPage] = useState(0);
	const pageCount = Math.max(1, Math.ceil(rows.length / size));
	const safe = Math.min(page, pageCount - 1);

	// Derived during render rather than in an effect: an effect would paint the
	// empty page once before correcting it.
	if (safe !== page) setPage(safe);

	return {
		page: safe,
		pageCount,
		total: rows.length,
		slice: rows.slice(safe * size, safe * size + size),
		onPage: (next: number) => {
			setPage(Math.max(0, Math.min(next, pageCount - 1)));
			window.scrollTo({ top: 0, behavior: "smooth" });
		},
		reset: () => setPage(0),
	};
}

/* ------------------------------------------------------------------ tables */

/**
 * A table, for the case a table is actually right: the same field compared
 * down a column.
 *
 * **No vertical rules and no outer box.** The columns are held apart by
 * alignment, and the only lines are the ones between rows — which is what lets
 * a reader's eye run down a column without being cut across by furniture. The
 * header is quiet on purpose: it is read once and then never again.
 */
/**
 * A register, a queue or a roster.
 *
 * **A real `<table>`, always.** The console is mostly data, and a grid of divs
 * loses the row/column relationships a screen reader needs to read a cell back
 * with its heading. Wide tables scroll inside their own panel rather than
 * pushing the page sideways.
 *
 * `sticky` keeps the header visible while a long register scrolls under it.
 * Off by default because it only helps where the table is the tallest thing on
 * the page — on a short table it produces a header that detaches for no reason.
 *
 * `align` lets a caller right-align the columns that hold figures. Dates,
 * totals and counts read as a column when their digits line up and as a mess
 * when they do not; `tabular` on the cell does the rest.
 */
export function Table({
	head,
	children,
	sticky = false,
	minWidth = 640,
	align = [],
	caption,
}: {
	head: ReactNode[];
	children: ReactNode;
	sticky?: boolean;
	minWidth?: number;
	align?: ("left" | "right" | "center")[];
	/**
	 * What this table is, for somebody who cannot see it. Visually hidden —
	 * a sighted reader already has the section heading above it.
	 */
	caption?: string;
}) {
	return (
		<div className={cx("p-card overflow-x-auto", sticky && "max-h-[70vh] overflow-y-auto")}>
			<table className="w-full border-collapse text-left" style={{ minWidth }}>
				{caption && <caption className="sr-only">{caption}</caption>}
				<thead className={cx(sticky && "sticky top-0 z-10")}>
					<tr className={cx("border-b p-divide bg-canvas", sticky && "bg-white")}>
						{head.map((cell, index) => (
							<th
								key={index}
								scope="col"
								className={cx(
									"whitespace-nowrap px-4 py-2.5 text-[10.5px] font-semibold uppercase tracking-[0.07em] text-rail-label",
									align[index] === "right" && "text-right",
									align[index] === "center" && "text-center",
								)}
							>
								{cell}
							</th>
						))}
					</tr>
				</thead>
				<tbody>{children}</tbody>
			</table>
		</div>
	);
}

export function Row({ children }: { children: ReactNode }) {
	return (
		<tr className="border-b border-card-line transition last:border-0 hover:bg-canvas">
			{children}
		</tr>
	);
}

export function Cell({ children, className }: { children: ReactNode; className?: string }) {
	return <td className={cx("px-5 py-3.5 align-middle text-[13px]", className)}>{children}</td>;
}

/* -------------------------------------------------------------------- tabs */

export interface TabDef {
	/** What this tab is, in the URL and in `active`. Never shown. */
	key: string;
	label: ReactNode;
	/** A count beside the label — answers, deployments, whatever the tab holds. */
	count?: number;
}

/**
 * One record, several faces.
 *
 * **A record too long to read is not made shorter by a tab bar; it is made
 * findable.** That is the whole of what this is for: an application carries an
 * identity, a set of declarations, a society's own questionnaire and a decision
 * trail, and an approver going back to check one of them should not scroll past
 * the other three. A screen with two short sections does not want this — it
 * wants two sections.
 *
 * **The active tab is the caller's state, and it should be the URL's.** This
 * component holds nothing. A tab held in local state is lost on every reload
 * and cannot be linked to, which is exactly wrong for a page somebody sends a
 * colleague ("look at the health answers on this one"). Every caller in this
 * app puts it in a search param.
 *
 * **A tab with nothing behind it is not drawn**, and that decision belongs to
 * the caller too: this renders the list it is given. A society that asks no
 * questions should see no questionnaire tab, not an empty one — the same rule
 * `Rung` in `GeoSelects.tsx` follows about a choice between one thing.
 */
export function Tabs({
	tabs,
	active,
	onSelect,
	className,
}: {
	tabs: TabDef[];
	active: string;
	onSelect: (key: string) => void;
	className?: string;
}) {
	return (
		<div
			role="tablist"
			className={cx(
				// Scrolls rather than wraps: a second row of tabs reads as a second
				// bar, and on a phone six tabs would take a third of the screen
				// before any of the record showed.
				"-mx-1 flex gap-1 overflow-x-auto rounded-xl bg-surface p-1",
				className,
			)}
		>
			{tabs.map((tab) => {
				const selected = tab.key === active;

				return (
					<button
						key={tab.key}
						type="button"
						role="tab"
						aria-selected={selected}
						onClick={() => onSelect(tab.key)}
						className={cx(
							"flex flex-none items-center gap-2 rounded-lg px-3.5 py-1.5 text-[12.5px] font-semibold transition",
							selected
								? "bg-white text-ink shadow-[0_1px_2px_rgba(30,50,73,0.06)]"
								: "text-muted hover:text-ink",
						)}
					>
						{tab.label}
						{tab.count !== undefined && (
							<span
								className={cx(
									"tabular rounded-full px-1.5 py-0.5 text-[10px] font-bold leading-none",
									selected ? "bg-blue-soft text-blue-press" : "bg-white text-slate-faint",
								)}
							>
								{tab.count}
							</span>
						)}
					</button>
				);
			})}
		</div>
	);
}

/* ------------------------------------------------------------- action menu */

export interface MenuAction {
	key: string;
	label: ReactNode;
	/** One line under the label, for an act whose consequence is not obvious. */
	hint?: ReactNode;
	icon?: (props: { size?: number; className?: string }) => ReactNode;
	/** Draws it as the destructive one. Never decides anything. */
	tone?: "default" | "danger";
	disabled?: boolean;
}

/**
 * A row of verbs, collapsed into one control.
 *
 * **Three buttons in a row say "these are three things"; a menu says "this is
 * one decision".** Approve, decline and ask-for-more are not three independent
 * acts an approver might do — they are the three answers to one question, and
 * only one of them will ever be pressed. Laid out as buttons they also read as
 * equally weighted, which puts Decline the same distance from a stray click as
 * Approve.
 *
 * **It closes on outside click and on Escape**, because a menu that stays open
 * behind whatever you clicked next is a menu that eventually gets clicked by
 * accident.
 */
export function ActionMenu({
	label,
	actions,
	onAction,
	variant = "navy",
	disabled,
	align = "right",
}: {
	label: ReactNode;
	actions: MenuAction[];
	onAction: (key: string) => void;
	variant?: keyof typeof BUTTONS;
	disabled?: boolean;
	align?: "left" | "right";
}) {
	const [open, setOpen] = useState(false);
	const holder = useRef<HTMLDivElement>(null);

	// Both listeners in one effect and only while open: a document-level
	// handler per menu on a list of twenty rows is twenty handlers running on
	// every click in the app.
	useEffect(() => {
		if (!open) return;

		const away = (event: MouseEvent) => {
			if (!holder.current?.contains(event.target as Node)) setOpen(false);
		};
		const escape = (event: KeyboardEvent) => {
			if (event.key === "Escape") setOpen(false);
		};

		document.addEventListener("mousedown", away);
		document.addEventListener("keydown", escape);

		return () => {
			document.removeEventListener("mousedown", away);
			document.removeEventListener("keydown", escape);
		};
	}, [open]);

	return (
		<div ref={holder} className="relative inline-block">
			<button
				type="button"
				aria-haspopup="menu"
				aria-expanded={open}
				disabled={disabled}
				onClick={() => setOpen((was) => !was)}
				className={cx(BUTTON_BASE, BUTTONS[variant])}
			>
				{label}
				<svg viewBox="0 0 24 24" width="14" height="14" fill="none" aria-hidden="true">
					<path
						d="m6 9 6 6 6-6"
						stroke="currentColor"
						strokeWidth="2.2"
						strokeLinecap="round"
					/>
				</svg>
			</button>

			{open && (
				<div
					role="menu"
					className={cx(
						"absolute z-30 mt-1.5 w-[268px] overflow-hidden rounded-xl border border-card-line bg-white p-1.5 shadow-pop",
						align === "right" ? "right-0" : "left-0",
					)}
				>
					{actions.map((action) => (
						<button
							key={action.key}
							type="button"
							role="menuitem"
							disabled={action.disabled}
							onClick={() => {
								setOpen(false);
								onAction(action.key);
							}}
							className={cx(
								"flex w-full items-start gap-2.5 rounded-lg px-3 py-2 text-left transition disabled:cursor-not-allowed disabled:opacity-40",
								action.tone === "danger"
									? "text-blue-press hover:bg-blue-soft"
									: "text-ink hover:bg-surface",
							)}
						>
							{action.icon && (
								<span className="mt-0.5 flex-none text-slate-faint">
									<action.icon size={15} />
								</span>
							)}
							<span className="min-w-0">
								<span className="block text-[13px] font-semibold">{action.label}</span>
								{action.hint && (
									<span className="mt-0.5 block text-[11.5px] leading-relaxed text-slate-faint">
										{action.hint}
									</span>
								)}
							</span>
						</button>
					))}
				</div>
			)}
		</div>
	);
}

/* --------------------------------------------------------------- confirming */

/**
 * The second press, for an act that cannot be taken back.
 *
 * **Naming what is about to happen, not asking "are you sure".** A dialog that
 * asks whether you are sure is dismissed without being read; one that says
 * "Approve Grace Mushi as a volunteer at Arusha" is read, because it contains
 * the one thing the reader can check. So `title` and `children` are required
 * and the confirm label is the verb rather than "OK".
 *
 * **It is a real dialog**: Escape closes it, the backdrop closes it, and the
 * confirm button takes focus on open so a keyboard user is not stranded. It is
 * deliberately not a `<dialog>` element — the top layer would sit above the
 * console's own chrome in a way this app's shell does not otherwise use, and
 * nothing here needs it.
 */
export function ConfirmDialog({
	open,
	title,
	confirmLabel,
	tone = "navy",
	busy,
	onConfirm,
	onCancel,
	children,
}: {
	open: boolean;
	title: ReactNode;
	confirmLabel: string;
	tone?: keyof typeof BUTTONS;
	busy?: boolean;
	onConfirm: () => void;
	onCancel: () => void;
	children: ReactNode;
}) {
	const confirm = useRef<HTMLButtonElement>(null);

	useEffect(() => {
		if (!open) return;

		confirm.current?.focus();

		const escape = (event: KeyboardEvent) => {
			if (event.key === "Escape") onCancel();
		};

		document.addEventListener("keydown", escape);

		return () => document.removeEventListener("keydown", escape);
		// `onCancel` is an inline closure in every caller and changes each
		// render; depending on it would tear the listener down and rebuild it on
		// every keystroke behind the dialog.
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [open]);

	if (!open) return null;

	return (
		<div className="fixed inset-0 z-50 grid place-items-center p-4">
			{/* The backdrop is a button so that dismissing by clicking away is
			    reachable from a keyboard too, and so it announces itself. */}
			<button
				type="button"
				aria-label="Cancel"
				onClick={onCancel}
				className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]"
			/>

			<div
				role="dialog"
				aria-modal="true"
				className="relative w-full max-w-[440px] rounded-xl border border-card-line bg-white p-6 shadow-pop"
			>
				<h2 className="text-[16px] font-semibold tracking-[-0.01em] text-ink">
					{title}
				</h2>

				<div className="mt-2.5 text-[13px] leading-relaxed text-slate-body">{children}</div>

				<div className="mt-6 flex flex-wrap justify-end gap-2.5">
					<Button variant="quiet" onClick={onCancel} disabled={busy}>
						Go back
					</Button>
					<button
						ref={confirm}
						type="button"
						onClick={onConfirm}
						disabled={busy}
						className={cx(BUTTON_BASE, BUTTONS[tone])}
					>
						{busy ? "Working…" : confirmLabel}
					</button>
				</div>
			</div>
		</div>
	);
}
