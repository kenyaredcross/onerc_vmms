import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { Icon } from "../../ui/icons";

/**
 * The volunteer portal's own component kit.
 *
 * **A fork, on purpose.** `ui/primitives.tsx` is the manager console's — the
 * grey shell, borderless cards, `rounded-full` everything, Schibsted Grotesk.
 * The portal is a separate visual world: one continuous IBM Plex workspace, a
 * cool paper-grey canvas, white panels held by a hairline, 10–12px radii, a
 * single restrained blue. Nothing here is imported by `admin/`, and nothing in
 * `admin/` is imported here except the shared icon set and the `cx` helper,
 * which carry no visual opinion.
 *
 * Everything composes the `.p-card` / `.portal-root` rules in `index.css`; no
 * component below owns a raw hex.
 */

export function cx(...parts: Array<string | false | null | undefined>): string {
	return parts.filter(Boolean).join(" ");
}

/* ------------------------------------------------------------------ layout */

/**
 * The greeting under the shell's page title.
 *
 * The *page* name ("Home") lives in the 56px header; this is the sentence a
 * person actually reads on arrival, with the one piece of context they use in
 * the morning — the date — above it. `actions` is the row's right side.
 */
export function PageHead({
	eyebrow,
	title,
	lead,
	actions,
}: {
	eyebrow?: ReactNode;
	title: ReactNode;
	lead?: ReactNode;
	actions?: ReactNode;
}) {
	return (
		<div className="mb-6 flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
			<div className="min-w-0">
				{eyebrow && (
					<div className="text-[10.5px] font-bold uppercase tracking-[0.14em] text-muted">
						{eyebrow}
					</div>
				)}
				<h1 className="mt-2 font-display text-[27px] font-bold leading-[1.15] tracking-[-0.025em] text-ink sm:text-[30px]">
					{title}
				</h1>
				{lead && (
					<p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-slate-body">{lead}</p>
				)}
			</div>
			{actions && (
				<div className="flex flex-wrap items-center gap-2 max-sm:self-start">{actions}</div>
			)}
		</div>
	);
}

/**
 * The chip on the right of a page head that says where this person stands —
 * "Active volunteer", "Application under review", "Action required".
 *
 * A *standing*, not an action, so it is never a button and never blue. Its tone
 * is chosen by the caller from what the server said, the same discipline
 * `StatusBadge` follows: nothing here reads a status string.
 */
export function StatusChip({
	tone = "neutral",
	children,
}: {
	tone?: "info" | "warning" | "danger" | "success" | "neutral";
	children: ReactNode;
}) {
	const tones = {
		info: "border-blue-line bg-blue-soft text-blue-press",
		warning: "border-warning-line bg-warning-soft text-warning",
		danger: "border-red-line bg-red-soft text-red-ink",
		success: "border-success-line bg-success-soft text-success",
		neutral: "border-card-line bg-white text-slate-strong",
	} as const;

	return (
		<span
			className={cx(
				"inline-flex flex-none items-center gap-2 whitespace-nowrap rounded-full border px-3 py-1.5 text-[12px] font-semibold",
				tones[tone],
			)}
		>
			<span className="h-[7px] w-[7px] flex-none rounded-full bg-current" aria-hidden="true" />
			{children}
		</span>
	);
}

/** The way back out of a detail page. Above the title, never beside it. */
export function BackLink({ to, children }: { to: string; children: ReactNode }) {
	return (
		<Link
			to={to}
			className="mb-5 inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-blue transition-colors hover:text-blue-hover"
		>
			<span aria-hidden="true">←</span>
			{children}
		</Link>
	);
}

/**
 * A panel of content.
 *
 * `pad` off for a card whose first child reaches the edge — a list with its
 * own row insets, a photograph, a table.
 */
export function Card({
	className,
	pad = true,
	as: As = "section",
	accent,
	children,
}: {
	className?: string;
	pad?: boolean;
	as?: "section" | "div" | "article";
	/**
	 * The one panel on a page carrying genuine attention — a deployment request
	 * waiting on an answer. It takes the danger hairline (a soft red replacing
	 * the neutral one) and pairs with a red "Action required" chip inside; the
	 * two together say "this needs you" without a coloured slab down one edge.
	 * Used at most once per screen, which is what keeps it meaning something.
	 */
	accent?: "danger";
	children: ReactNode;
}) {
	return (
		<As
			className={cx("p-card", pad && "p-5", accent === "danger" && "!border-danger/55", className)}
		>
			{children}
		</As>
	);
}

/**
 * The header strip inside a `pad={false}` card — a title on the left, a
 * "see all" link on the right. The link is a destination, never a verb.
 */
export function SectionHead({
	title,
	link,
}: {
	title: ReactNode;
	link?: { to: string; label: string };
}) {
	return (
		<div className="flex items-center justify-between gap-3 border-b p-divide px-[18px] py-4">
			<h2 className="text-[13.5px] font-semibold text-ink">{title}</h2>
			{link && (
				<Link
					to={link.to}
					className="shrink-0 text-[12px] font-semibold text-blue transition-colors hover:text-blue-hover"
				>
					{link.label}
				</Link>
			)}
		</div>
	);
}

/** The tracked label a form section or a card group sits under. */
export function GroupLabel({ children }: { children: ReactNode }) {
	return (
		<h2 className="mb-2.5 text-[11px] font-semibold uppercase tracking-[0.09em] text-rail-label">
			{children}
		</h2>
	);
}

/* ------------------------------------------------------------------ status */

/**
 * A state, as a soft-filled chip with a dot and a word.
 *
 * Colour is keyed off the shape of a closed state set — the approval engine's,
 * the task machine's, a membership's — never off a society's configurable
 * label. The dot and the word carry the state where colour cannot: greyscale,
 * a colour filter, `forced-colors`.
 */
type BadgeTone = "success" | "info" | "warning" | "danger" | "neutral";

const BADGE_TONES: Record<BadgeTone, string> = {
	success: "bg-success-soft text-success",
	info: "bg-blue-soft text-blue-press",
	warning: "bg-warning-soft text-warning",
	danger: "bg-danger-soft text-danger",
	neutral: "bg-surface text-slate-strong",
};

/** The closed sets this portal renders, mapped to a tone once. */
const STATE_TONE: Record<string, BadgeTone> = {
	// approval / volunteer / membership
	Approved: "success",
	Active: "success",
	Completed: "success",
	Accepted: "success",
	"In Review": "info",
	Submitted: "info",
	Assigned: "info",
	Pending: "warning",
	Expired: "warning",
	Draft: "warning",
	Rejected: "danger",
	Declined: "neutral",
	Withdrawn: "neutral",
	Cancelled: "neutral",
	Lapsed: "danger",
	// task machine (lower-case, from task/services/states.py)
	assigned: "warning",
	accepted: "info",
	submitted: "info",
	completed: "success",
	cancelled: "neutral",
};

export function StatusBadge({
	state,
	tone,
	children,
}: {
	/** A value from a closed state set. Its tone is looked up. */
	state?: string | null;
	/** Override the looked-up tone — for a chip that is not a state ("Action required"). */
	tone?: BadgeTone;
	/** Override the label — defaults to `state`. */
	children?: ReactNode;
}) {
	if (!state && !children) return null;

	const resolved = tone ?? (state ? (STATE_TONE[state] ?? "neutral") : "neutral");

	return (
		<span
			className={cx(
				"inline-flex flex-none items-center gap-1.5 whitespace-nowrap rounded-md px-2 py-1 text-[11px] font-semibold",
				BADGE_TONES[resolved],
			)}
		>
			<span className="h-1.5 w-1.5 flex-none rounded-full bg-current" aria-hidden="true" />
			{/* `state` values from the task machine arrive lower-case; a passed
			    `children` label is already written the way it should read. */}
			{children ?? <span className="capitalize">{state}</span>}
		</span>
	);
}

/* ------------------------------------------------------------------ buttons */

const BUTTON_TONES = {
	primary: "bg-blue text-white hover:bg-blue-hover active:bg-blue-press",
	quiet:
		"border border-rail-line bg-white text-slate-strong hover:border-slate-faint hover:text-ink",
	soft: "bg-blue-soft text-blue-press hover:bg-blue-line/50",
	danger: "border border-danger-line bg-white text-danger hover:bg-danger-soft",
} as const;

const BUTTON_BASE =
	"inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-[13px] font-semibold transition disabled:cursor-not-allowed disabled:opacity-45";

export type ButtonTone = keyof typeof BUTTON_TONES;

export function Button({
	tone = "primary",
	type = "button",
	busy,
	disabled,
	onClick,
	className,
	children,
}: {
	tone?: ButtonTone;
	type?: "button" | "submit";
	busy?: boolean;
	disabled?: boolean;
	onClick?: () => void;
	className?: string;
	children: ReactNode;
}) {
	return (
		<button
			type={type}
			onClick={onClick}
			disabled={disabled || busy}
			aria-busy={busy || undefined}
			className={cx(BUTTON_BASE, BUTTON_TONES[tone], className)}
		>
			{busy && (
				<span
					aria-hidden="true"
					className="h-3.5 w-3.5 flex-none animate-spin rounded-full border-2 border-current border-t-transparent motion-reduce:animate-none"
				/>
			)}
			{children}
		</button>
	);
}

export function ButtonLink({
	to,
	tone = "primary",
	className,
	children,
}: {
	to: string;
	tone?: ButtonTone;
	className?: string;
	children: ReactNode;
}) {
	const cls = cx(BUTTON_BASE, BUTTON_TONES[tone], className);

	// `/portal`-prefixed strings are the app's older internal convention; strip
	// it. Anything else site-level is a real navigation.
	if (to.startsWith("/portal")) {
		return (
			<Link to={to.replace(/^\/portal/, "") || "/"} className={cls}>
				{children}
			</Link>
		);
	}

	return to.startsWith("/") ? (
		<Link to={to} className={cls}>
			{children}
		</Link>
	) : (
		<a href={to} className={cls}>
			{children}
		</a>
	);
}

export function IconButton({
	label,
	onClick,
	className,
	children,
}: {
	label: string;
	onClick?: () => void;
	className?: string;
	children: ReactNode;
}) {
	return (
		<button
			type="button"
			aria-label={label}
			title={label}
			onClick={onClick}
			className={cx(
				"grid h-8 w-8 flex-none place-items-center rounded-lg text-slate-faint transition hover:bg-rail-hover hover:text-ink",
				className,
			)}
		>
			{children}
		</button>
	);
}

/* ------------------------------------------------------------------ avatar */

export function Avatar({
	name,
	photo,
	size = 32,
}: {
	name?: string | null;
	photo?: string | null;
	size?: number;
}) {
	const letters = (name ?? "")
		.split(/\s+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((part) => part[0]?.toUpperCase() ?? "")
		.join("");

	if (photo) {
		return (
			<img
				src={photo}
				alt=""
				aria-hidden="true"
				loading="lazy"
				style={{ width: size, height: size }}
				className="flex-none rounded-full object-cover"
			/>
		);
	}

	return (
		<span
			aria-hidden="true"
			style={{ width: size, height: size, fontSize: Math.round(size * 0.38) }}
			className="grid flex-none place-items-center rounded-full bg-blue/[0.1] font-semibold text-blue-press"
		>
			{letters || "·"}
		</span>
	);
}

/* ------------------------------------------------------------------- lists */

/**
 * One row of a list: a mark, what it is, what is true of it, what you may do.
 *
 * `to` makes the whole row the target. A row that carries its own controls
 * leaves `to` off so a click on a button is never a click on the row.
 */
export function ListRow({
	lead,
	title,
	meta,
	trailing,
	chevron = false,
	to,
	onClick,
}: {
	lead?: ReactNode;
	title: ReactNode;
	meta?: ReactNode;
	trailing?: ReactNode;
	/** The quiet `›` at the end of a row that navigates. */
	chevron?: boolean;
	to?: string;
	onClick?: () => void;
}) {
	const inner = (
		<div className="flex items-center gap-3">
			{lead}
			<div className="min-w-0 flex-1">
				<div className="line-clamp-2 text-[13px] font-semibold leading-snug text-ink">{title}</div>
				{meta && <div className="mt-0.5 truncate text-[11.5px] text-muted">{meta}</div>}
			</div>
			{trailing && (
				<div className="flex flex-none items-center gap-2 self-start pt-0.5">{trailing}</div>
			)}
			{chevron && (
				<span className="flex-none text-[18px] leading-none text-slate-faint" aria-hidden="true">
					›
				</span>
			)}
		</div>
	);

	const base = "block w-full px-[18px] py-3.5 text-left transition";

	if (to) {
		return (
			<Link to={to} className={cx(base, "hover:bg-canvas")}>
				{inner}
			</Link>
		);
	}
	if (onClick) {
		return (
			<button type="button" onClick={onClick} className={cx(base, "hover:bg-canvas")}>
				{inner}
			</button>
		);
	}
	return <div className={base}>{inner}</div>;
}

/** The container `ListRow`s sit in — a hairline drawn by the gap between them. */
export function List({ children }: { children: ReactNode }) {
	return <div className="divide-y divide-card-line">{children}</div>;
}

/** The square tint behind a list row's icon. */
export function RowIcon({
	icon,
	tone = "neutral",
}: {
	icon: (props: { size?: number }) => ReactNode;
	tone?: "neutral" | "info" | "warning" | "success";
}) {
	const tones = {
		neutral: "bg-surface text-slate-strong",
		info: "bg-blue-soft text-blue-press",
		warning: "bg-warning-soft text-warning",
		success: "bg-success-soft text-success",
	} as const;

	return (
		<span
			className={cx("grid h-9 w-9 flex-none place-items-center rounded-lg", tones[tone])}
			aria-hidden="true"
		>
			{icon({ size: 16 })}
		</span>
	);
}

/**
 * A dated row — the day block on the left, the thing on the right. `iso` makes
 * the date machine-readable.
 */
export function DatedRow({
	iso,
	day,
	month,
	title,
	meta,
	to,
}: {
	iso?: string;
	day: string;
	month: string;
	title: ReactNode;
	meta?: ReactNode;
	to?: string;
}) {
	const body = (
		<div className="flex items-start gap-3.5">
			<time
				dateTime={iso}
				className="grid h-10 w-[40px] flex-none place-content-center border-r border-card-line pr-3 text-center leading-none"
			>
				<span className="block text-[18px] font-semibold tracking-[-0.02em] text-ink">{day}</span>
				<span className="mt-1 block text-[9px] font-semibold uppercase tracking-[0.12em] text-rail-label">
					{month}
				</span>
			</time>
			<div className="min-w-0 flex-1 pt-0.5">
				<div className="line-clamp-2 text-[13px] font-semibold leading-snug text-ink">{title}</div>
				{meta && <div className="mt-0.5 truncate text-[11.5px] text-muted">{meta}</div>}
			</div>
			{to && (
				<span className="flex-none text-[18px] leading-none text-slate-faint" aria-hidden="true">
					›
				</span>
			)}
		</div>
	);

	if (to) {
		return (
			<Link to={to} className="block px-[18px] py-3 transition hover:bg-canvas">
				{body}
			</Link>
		);
	}
	return <div className="px-[18px] py-3">{body}</div>;
}

/* ------------------------------------------------------------------ states */

export function Spinner({ label = "Loading…", page = false }: { label?: string; page?: boolean }) {
	return (
		<div
			className={cx(
				"flex flex-col items-center justify-center gap-3 text-center",
				page ? "min-h-[70vh] py-16" : "py-10",
			)}
			role="status"
			aria-live="polite"
		>
			<span
				className={cx(
					"animate-spin rounded-full border-rail-line border-t-blue motion-reduce:animate-none",
					page ? "h-8 w-8 border-[3px]" : "h-4 w-4 border-2",
				)}
			/>
			<span
				className={cx("text-slate-strong", page ? "text-[13.5px] font-semibold" : "text-[13px]")}
			>
				{label}
			</span>
		</div>
	);
}

export function Skeleton({ className }: { className?: string }) {
	return (
		<div
			aria-hidden="true"
			className={cx(
				"animate-pulse rounded-lg bg-card-line/70 motion-reduce:animate-none",
				className,
			)}
		/>
	);
}

/**
 * A backend read that failed, said without machinery. The caller passes the
 * output of `errorMessage` from `lib/api`, which is the one place that decides
 * what a person may be shown.
 */
export function ErrorNote({ children }: { children: ReactNode }) {
	return (
		<div className="flex items-start gap-2.5 rounded-xl border border-danger-line bg-danger-soft px-4 py-3 text-[13px] leading-relaxed text-danger">
			<Icon.bell size={16} className="mt-px flex-none" />
			<div className="min-w-0">{children}</div>
		</div>
	);
}

/**
 * Nothing here yet, said without a box around the nothing when it sits inside
 * a card that already is one.
 */
export function Empty({
	title,
	icon,
	action,
	framed = true,
	children,
}: {
	title: ReactNode;
	icon?: (props: { size?: number }) => ReactNode;
	action?: ReactNode;
	framed?: boolean;
	children?: ReactNode;
}) {
	return (
		<div className={cx("text-center", framed ? "p-card px-6 py-11" : "px-3 py-6")}>
			{icon && (
				<span
					className="mx-auto mb-2.5 grid h-9 w-9 place-items-center rounded-lg bg-surface text-slate-strong"
					aria-hidden="true"
				>
					{icon({ size: 17 })}
				</span>
			)}
			<p className="text-[13.5px] font-semibold text-ink">{title}</p>
			{children && (
				<p className="mx-auto mt-1 max-w-sm text-[12px] leading-relaxed text-muted">{children}</p>
			)}
			{action && <div className="mt-4 flex flex-wrap justify-center gap-2">{action}</div>}
		</div>
	);
}

/* -------------------------------------------------------------------- tabs */

export interface TabDef {
	key: string;
	label: ReactNode;
	count?: number;
}

/**
 * Underline tabs — the reference set's shape. The active key is the caller's
 * state (and should be the URL's, for a page somebody links); this renders the
 * list it is given and holds nothing.
 */
export function Tabs({
	tabs,
	active,
	onSelect,
}: {
	tabs: TabDef[];
	active: string;
	onSelect: (key: string) => void;
}) {
	return (
		<div
			role="tablist"
			className="mb-5 flex gap-4 overflow-x-auto border-b p-divide sm:gap-6 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
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
							"flex flex-none items-center gap-1.5 whitespace-nowrap border-b-2 px-0.5 pb-2.5 pt-2 text-[13px] font-semibold transition-colors last:pr-1",
							selected ? "border-ink text-ink" : "border-transparent text-muted hover:text-ink",
						)}
					>
						{tab.label}
						{tab.count !== undefined && (
							<span className="text-[11px] font-semibold text-slate-faint">{tab.count}</span>
						)}
					</button>
				);
			})}
		</div>
	);
}

/* ------------------------------------------------------------------ facts */

/**
 * A block of label-and-value pairs — the concept's `<dl>`, which appears on a
 * deployment request, a mission record, a membership card and a task's detail.
 *
 * A real `dl`, so a screen reader reads "Role, Community Health Volunteer"
 * rather than two unrelated strings. `columns` is how many fit side by side on
 * a wide viewport; every layout collapses to one column on a phone, because a
 * two-column definition list at 390px is two columns of three characters.
 */
export function Facts({
	items,
	columns = 3,
	className,
}: {
	items: Array<{ label: ReactNode; value: ReactNode } | null | false | undefined>;
	columns?: 2 | 3 | 4;
	className?: string;
}) {
	const rows = items.filter(Boolean) as Array<{ label: ReactNode; value: ReactNode }>;
	if (rows.length === 0) return null;

	const grid = {
		2: "sm:grid-cols-2",
		3: "sm:grid-cols-2 lg:grid-cols-3",
		4: "sm:grid-cols-2 lg:grid-cols-4",
	} as const;

	return (
		<dl className={cx("grid gap-x-5 gap-y-4", grid[columns], className)}>
			{rows.map((row, index) => (
				<div key={index} className="min-w-0">
					<dt className="text-[10px] font-bold uppercase tracking-[0.09em] text-rail-label">
						{row.label}
					</dt>
					<dd className="mt-1.5 text-[12.5px] font-semibold leading-snug text-ink">{row.value}</dd>
				</div>
			))}
		</dl>
	);
}

/**
 * The narrow, stacked variant — a label above its value down one side panel,
 * which is what the concept's `record-facts` aside is.
 */
export function FactList({
	items,
}: {
	items: Array<{ label: ReactNode; value: ReactNode } | null | false | undefined>;
}) {
	const rows = items.filter(Boolean) as Array<{ label: ReactNode; value: ReactNode }>;
	if (rows.length === 0) return null;

	return (
		<dl className="space-y-3.5">
			{rows.map((row, index) => (
				<div key={index} className="min-w-0">
					<dt className="text-[10px] font-bold uppercase tracking-[0.09em] text-rail-label">
						{row.label}
					</dt>
					<dd className="mt-1 text-[12.5px] font-semibold leading-snug text-ink">{row.value}</dd>
				</div>
			))}
		</dl>
	);
}

/* ------------------------------------------------------------------- stats */

/**
 * One figure a volunteer scans on arrival: what it counts, the number, and the
 * page it leads to.
 *
 * **The link is not optional decoration.** A tile that states a number and
 * cannot be opened is a dead end, and the concept never draws one — every tile
 * on its home page carries the road to the thing it counted.
 */
export function StatTile({
	label,
	value,
	to,
	linkLabel,
	urgent = false,
}: {
	label: ReactNode;
	value: ReactNode;
	to: string;
	linkLabel: string;
	/** The one tile that is a demand rather than a fact — a request awaiting an answer. */
	urgent?: boolean;
}) {
	return (
		<div
			className={cx(
				"p-card flex flex-col gap-1.5 p-[18px]",
				urgent && "border-t-[3px] border-t-red",
			)}
		>
			<span className="text-[11.5px] text-slate-body">{label}</span>
			<strong className="font-display text-[27px] font-extrabold leading-none tracking-[-0.02em] text-ink tabular">
				{value}
			</strong>
			<Link
				to={to}
				className="mt-0.5 text-[11.5px] font-bold text-blue transition-colors hover:text-blue-hover"
			>
				{linkLabel} →
			</Link>
		</div>
	);
}

/**
 * A proportion, drawn. Always beside the figure it draws, never instead of it:
 * a bar on its own is a shape, and a person wants the number.
 */
export function Meter({
	value,
	label,
	tone = "blue",
}: {
	/** 0–100. Clamped here, because a server that sends 140 is not this bar's problem. */
	value: number;
	label?: string;
	tone?: "blue" | "success";
}) {
	const pct = Math.max(0, Math.min(100, Math.round(value)));

	return (
		<div className="flex items-center gap-2.5">
			<div
				className="h-[5px] min-w-0 flex-1 overflow-hidden rounded-full bg-card-line"
				role="progressbar"
				aria-valuenow={pct}
				aria-valuemin={0}
				aria-valuemax={100}
				aria-label={label ?? "Progress"}
			>
				<div
					className={cx("h-full rounded-full", tone === "success" ? "bg-success" : "bg-blue")}
					style={{ width: `${pct}%` }}
				/>
			</div>
			<span className="w-8 flex-none text-right text-[11px] font-semibold text-muted tabular">
				{pct}%
			</span>
		</div>
	);
}

/* ------------------------------------------------------------------ notice */

/**
 * The concept's side-ruled note — a standing explanation, never an error and
 * never dismissible. `ErrorNote` is the other thing and stays separate.
 */
export function Notice({
	tone = "info",
	children,
}: {
	tone?: "info" | "success";
	children: ReactNode;
}) {
	return (
		<div
			className={cx(
				"rounded-r-xl border-l-[3px] px-4 py-3 text-[12px] leading-relaxed",
				tone === "success"
					? "border-l-success bg-success-soft text-success"
					: "border-l-blue bg-blue-soft text-slate-strong",
			)}
		>
			{children}
		</div>
	);
}

/* ------------------------------------------------------------------ search */

/** The concept's search box: an icon, a field, and a count of what is showing. */
export function SearchField({
	value,
	onChange,
	placeholder,
	label,
	hint,
}: {
	value: string;
	onChange: (value: string) => void;
	placeholder: string;
	label: string;
	/** The result count, drawn as the concept's `kbd` at the right of the field. */
	hint?: ReactNode;
}) {
	return (
		<div className="flex h-[46px] w-full items-center gap-2.5 rounded-xl border border-rail-line bg-white px-3.5 transition focus-within:border-blue focus-within:ring-[3px] focus-within:ring-blue-soft">
			<Icon.search size={16} className="flex-none text-slate-faint" />
			<input
				type="search"
				value={value}
				onChange={(event) => onChange(event.target.value)}
				placeholder={placeholder}
				aria-label={label}
				autoComplete="off"
				className="min-w-0 flex-1 bg-transparent text-[13px] text-ink outline-none placeholder:text-slate-faint"
			/>
			{hint !== undefined && hint !== null && (
				<span className="flex-none rounded-md bg-surface px-2 py-1 text-[11px] font-medium text-muted">
					{hint}
				</span>
			)}
		</div>
	);
}

/* ------------------------------------------------------------------- pills */

export interface PillDef {
	key: string;
	label: string;
	count?: number;
}

/**
 * The concept's filter rail: a row of pills, the selected one filled navy.
 *
 * A `tablist` rather than a group of buttons, because that is what it is — one
 * of the set is always chosen and choosing swaps the panel underneath. Scrolls
 * sideways on a phone rather than wrapping into four rows.
 */
export function FilterPills({
	pills,
	active,
	onSelect,
	label,
}: {
	pills: PillDef[];
	active: string;
	onSelect: (key: string) => void;
	label: string;
}) {
	return (
		<div
			role="tablist"
			aria-label={label}
			// Scrolls sideways on a phone, wraps on a wide screen: seven filters do
			// not fit beside a search box at any desktop width, and a row that
			// silently clips its last two is a filter nobody finds.
			className="flex gap-2 overflow-x-auto pb-0.5 [scrollbar-width:none] lg:flex-wrap lg:overflow-visible lg:pb-0 [&::-webkit-scrollbar]:hidden"
		>
			{pills.map((pill) => {
				const selected = pill.key === active;
				return (
					<button
						key={pill.key}
						type="button"
						role="tab"
						aria-selected={selected}
						onClick={() => onSelect(pill.key)}
						className={cx(
							"flex flex-none items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1.5 text-[12px] font-semibold transition",
							selected
								? "border-rail bg-rail text-white"
								: "border-card-line bg-white text-slate-body hover:border-slate-faint hover:text-ink",
						)}
					>
						{pill.label}
						{pill.count !== undefined && (
							<span
								className={cx(
									"rounded-full px-1.5 text-[10.5px] font-bold tabular",
									selected ? "bg-white/20 text-white" : "bg-surface text-muted",
								)}
							>
								{pill.count}
							</span>
						)}
					</button>
				);
			})}
		</div>
	);
}

/* ------------------------------------------------------------------ folder */

/**
 * A closed record, drawn as a file in a drawer — the concept's archive card.
 *
 * A `Link`, not a button, so the whole card is one keyboard target with a real
 * address somebody can copy, open in a tab, or come back to.
 */
export function FolderCard({
	to,
	kicker,
	title,
	meta,
	foot,
}: {
	to: string;
	kicker: ReactNode;
	title: ReactNode;
	meta?: ReactNode;
	foot?: ReactNode;
}) {
	return (
		<Link
			to={to}
			className="p-card group flex min-h-[168px] flex-col p-5 transition hover:-translate-y-[3px] hover:border-slate-faint hover:shadow-[0_10px_24px_rgba(1,30,65,0.07)] motion-reduce:hover:translate-y-0"
		>
			<span className="mb-4 mt-1" aria-hidden="true">
				<svg viewBox="0 0 46 32" width="46" height="32" role="presentation">
					<path
						d="M2 6a3 3 0 0 1 3-3h14l4 4h18a3 3 0 0 1 3 3v17a3 3 0 0 1-3 3H5a3 3 0 0 1-3-3z"
						className="fill-[#4a98d5]"
					/>
					<path d="M2 11h42v16a3 3 0 0 1-3 3H5a3 3 0 0 1-3-3z" className="fill-[#2675b9]" />
				</svg>
			</span>
			<span className="text-[9.5px] font-bold uppercase tracking-[0.1em] text-muted">{kicker}</span>
			<strong className="mt-1.5 line-clamp-2 text-[13px] font-semibold leading-snug text-ink">
				{title}
			</strong>
			{meta && <span className="mt-1.5 text-[11.5px] text-slate-body">{meta}</span>}
			{foot && <span className="mt-auto pt-3 text-[11px] font-semibold text-blue">{foot}</span>}
		</Link>
	);
}
