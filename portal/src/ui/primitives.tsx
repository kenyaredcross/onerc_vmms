import { Link } from "react-router-dom";
import { useState, type ReactNode } from "react";

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
		<div className="mb-7">
			<div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
				<div className="min-w-0">
					{eyebrow && <div className="eyebrow mb-2">{eyebrow}</div>}

					<h1 className="font-display text-[30px] font-extrabold leading-[1.1] tracking-tight text-ink sm:text-[34px]">
						{title}
					</h1>

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
											<span aria-hidden="true" className="text-hairline-strong">
												/
											</span>
										)}
										{crumb.to ? (
											<Link
												to={crumb.to}
												className="font-medium transition hover:text-navy hover:underline"
											>
												{crumb.label}
											</Link>
										) : (
											<span aria-current="page" className="font-semibold text-slate-body">
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
				<p className="mt-3 max-w-2xl text-[13.5px] leading-relaxed text-slate-body">{lead}</p>
			)}
		</div>
	);
}

/**
 * A panel of content.
 *
 * **No border.** It is told apart from the ground by tone and a very soft
 * shadow, which is what lets a 16px radius read as a radius instead of as a
 * box with filed corners. `pad` exists for the two cases that must not have
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
				"card",
				pad && "p-5 sm:p-6",
				hover && "transition duration-200 hover:shadow-lift",
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
			className="chev whitespace-nowrap text-[12px] font-bold text-navy transition hover:text-signal"
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
		<h3 className="mb-3 font-display text-[14px] font-bold tracking-tight text-ink">{children}</h3>
	);
}

/** A hairline between parts of a card. */
export function Divide({ className }: { className?: string }) {
	return <div className={cx("h-px bg-hairline", className)} aria-hidden="true" />;
}

/* ------------------------------------------------------------------ atoms */

const TONES = {
	navy: "bg-navy text-white",
	signal: "bg-signal text-white",
	quiet: "border border-hairline-strong bg-white text-slate-strong",
	page: "bg-page text-slate-strong",
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
				"inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-3.5 py-1.5 text-[11.5px] font-semibold",
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
 * **Outlined, with a dot, rather than filled.** A page of filled badges is a
 * page of coloured blocks with the actual record in between them, and on a
 * register screen there is one on every row. The outline carries the same
 * colour at a fraction of the weight, and the dot means the state survives
 * being read by somebody who cannot tell the two greens apart.
 */
const STATE_TONES: Record<string, string> = {
	Approved: "border-emerald-300 text-emerald-700 bg-emerald-50/60",
	Active: "border-emerald-300 text-emerald-700 bg-emerald-50/60",
	Rejected: "border-signal/40 text-signal-dark bg-signal/[.06]",
	Expired: "border-amber-300 text-amber-700 bg-amber-50/60",
	Withdrawn: "border-hairline-strong text-slate-body bg-page",
	Draft: "border-hairline-strong text-slate-body bg-page",
};

export function StateBadge({ state }: { state?: string | null }) {
	if (!state) return null;

	const tone = STATE_TONES[state] ?? "border-navy/25 text-navy bg-navy/[.05]";

	return (
		<span
			className={cx(
				"inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-1 text-[11px] font-bold",
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
export function Avatar({
	name,
	size = 36,
	tone = "navy",
}: {
	name?: string | null;
	size?: number;
	tone?: "navy" | "signal" | "page";
}) {
	const letters = (name ?? "")
		.split(/\s+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((part) => part[0]?.toUpperCase() ?? "")
		.join("");

	const tones = {
		navy: "bg-navy/[.07] text-navy",
		signal: "bg-signal/[.10] text-signal-dark",
		page: "bg-page text-slate-body",
	} as const;

	return (
		<span
			aria-hidden="true"
			style={{ width: size, height: size, fontSize: Math.round(size * 0.36) }}
			className={cx(
				"grid flex-none place-items-center rounded-full font-display font-bold",
				tones[tone],
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
					<div className="truncate text-[11.5px] font-semibold text-slate-body">{label}</div>
					<div className="tabular mt-1.5 font-display text-[28px] font-extrabold leading-none tracking-tight text-ink">
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
				className="card block h-full p-5 transition duration-200 hover:shadow-lift focus-visible:shadow-lift"
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
			<div className="tabular font-display text-[26px] font-extrabold leading-none tracking-tight text-ink">
				{value}
			</div>
			<div className="mt-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-faint">
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
				className="h-1.5 w-full overflow-hidden rounded-full bg-page"
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

			<div className="tabular absolute inset-0 grid place-items-center font-display text-[12px] font-extrabold text-ink">
				{children ?? `${Math.round(pct * 100)}%`}
			</div>
		</div>
	);
}

/* ----------------------------------------------------------------- buttons */

const BUTTONS = {
	primary: "bg-signal text-white shadow-sm hover:bg-signal-dark active:translate-y-px",
	navy: "bg-navy text-white shadow-sm hover:bg-navy/90 active:translate-y-px",
	/**
	 * The secondary the reference set actually uses: a wash of the accent with
	 * the accent as the text. Louder than an outline and quieter than a fill,
	 * which is the register a "second thing you might do" wants.
	 */
	soft: "bg-navy/[.07] text-navy hover:bg-navy/[.12] active:translate-y-px",
	quiet:
		"border border-hairline-strong bg-white text-slate-strong hover:border-navy hover:text-navy",
	ghost: "text-navy hover:bg-navy/[.06]",
} as const;

const BUTTON_BASE =
	"inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 font-display text-[13px] font-bold transition disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0";

interface ButtonProps {
	variant?: keyof typeof BUTTONS;
	className?: string;
	children: ReactNode;
	onClick?: () => void;
	disabled?: boolean;
	type?: "button" | "submit";
}

export function Button({
	variant = "primary",
	className,
	children,
	onClick,
	disabled,
	type = "button",
}: ButtonProps) {
	return (
		<button
			type={type}
			onClick={onClick}
			disabled={disabled}
			className={cx(BUTTON_BASE, BUTTONS[variant], className)}
		>
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
				"grid h-9 w-9 flex-none place-items-center rounded-full text-slate-faint transition hover:bg-page hover:text-navy disabled:cursor-not-allowed disabled:opacity-40",
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
					"animate-spin rounded-full border-hairline-strong border-t-navy",
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
		<div className="flex items-start gap-3 rounded-card border border-signal/25 bg-signal/[.05] px-4 py-3.5 text-[13px] leading-relaxed text-signal-dark">
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
					? "rounded-card border border-dashed border-hairline-strong bg-page/40 px-6 py-10"
					: "px-2 py-6",
			)}
		>
			{icon && (
				<div
					className={cx(
						"mx-auto mb-3.5 grid h-11 w-11 place-items-center rounded-full text-slate-faint",
						framed ? "bg-white shadow-card" : "bg-page",
					)}
				>
					{icon({ size: 19 })}
				</div>
			)}
			<p className="font-display text-[14.5px] font-bold text-ink">{title}</p>
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
		<div className="rounded-panel border border-dashed border-hairline-strong bg-white px-8 py-14 text-center">
			<div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-full bg-page">
				<svg viewBox="0 0 24 24" width="20" height="20" fill="none" aria-hidden="true">
					<path
						d="M12 8v5m0 3.5v.5M12 3 2 20h20L12 3Z"
						stroke="#8A93A1"
						strokeWidth="1.8"
						strokeLinejoin="round"
					/>
				</svg>
			</div>
			<p className="font-display text-[17px] font-extrabold text-ink">{what} is not here yet</p>
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
					<div className="truncate font-display text-[13.5px] font-bold text-ink">{title}</div>
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
		(to || onClick) && "hover:bg-page",
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
		"grid h-9 w-9 place-items-center rounded-full border border-hairline-strong bg-white text-slate-body transition hover:border-navy hover:text-navy disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-hairline-strong disabled:hover:text-slate-body";

	return (
		<nav
			className="mt-10 flex flex-wrap items-center justify-between gap-4 border-t border-hairline pt-6"
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
							"h-9 min-w-9 rounded-full px-3 font-display text-[12.5px] font-bold transition",
							index === page
								? "bg-navy text-white"
								: "border border-hairline-strong bg-white text-slate-body hover:border-navy hover:text-navy",
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
export function Table({ head, children }: { head: ReactNode[]; children: ReactNode }) {
	return (
		<div className="card overflow-x-auto">
			<table className="w-full min-w-[640px] border-collapse text-left">
				<thead>
					<tr className="border-b border-hairline">
						{head.map((cell, index) => (
							<th
								key={index}
								className="whitespace-nowrap px-5 py-3.5 text-[11px] font-bold text-slate-faint"
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
		<tr className="border-b border-hairline-soft transition last:border-0 hover:bg-page/60">
			{children}
		</tr>
	);
}

export function Cell({ children, className }: { children: ReactNode; className?: string }) {
	return <td className={cx("px-5 py-3.5 align-middle text-[13px]", className)}>{children}</td>;
}
