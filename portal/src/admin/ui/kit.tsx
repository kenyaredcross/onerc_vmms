/*
 * The manager console's component kit.
 *
 * **The console is not a separate visual world any more.** It used to be: a
 * grey shell, borderless shadow cards, `rounded-full` everything, Schibsted
 * Grotesk — `ui/primitives.tsx`, which the portal was deliberately forked away
 * from. The fork has been folded back the other way. Everything below either
 * re-exports the portal's own kit verbatim or is built out of the same tokens,
 * so a coordinator moving between their portal and their console is moving
 * between two parts of one product rather than two products.
 *
 * **What is here that is not in `portal/ui/kit.tsx`** is the density a console
 * needs and a self-service portal does not: a table somebody scans two hundred
 * rows of, a filter toolbar above it, a record laid out beside a decision
 * panel, a board of columns, a figure with a trend under it. None of it invents
 * a colour or a radius — every one comes from `tailwind.config.js` through the
 * same names the portal uses.
 *
 * **Nothing here holds state or fetches.** A component that decided when to
 * refetch would be a component two screens could disagree with.
 */

import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { formatMoney } from "../../lib/format";
import { Icon } from "../../ui/icons";
import { cx } from "../../portal/ui/kit";

/* ------------------------------------------------------------ the portal's own

   Re-exported rather than wrapped: a wrapper that only forwards props is a
   place for the two to drift apart, and the console genuinely wants these
   unchanged. `import { Card } from "./ui/kit"` in a console screen and
   `import { Card } from "./ui/kit"` in a portal screen are the same component.
*/
export {
	cx,
	PageHead,
	Card,
	SectionHead,
	GroupLabel,
	StatusBadge,
	Button,
	ButtonLink,
	IconButton,
	Avatar,
	ListRow,
	List,
	RowIcon,
	DatedRow,
	Spinner,
	Skeleton,
	ErrorNote,
	Empty,
	Tabs,
} from "../../portal/ui/kit";
export type { ButtonTone, TabDef } from "../../portal/ui/kit";
export { Modal, ConfirmModal, Drawer, ToastProvider, useToast } from "../../portal/ui/overlays";

/* ------------------------------------------------------------------ figures */

/**
 * One headline number, with what it counts under it.
 *
 * **The label is above the figure, not below.** A column of tiles is read by
 * its labels — somebody is looking for "waiting on you", not for "12" — and a
 * grid that puts four large numerals first makes the reader match each one back
 * to its caption.
 *
 * `note` is the line underneath: a comparison, a currency, a caveat. It is not
 * coloured green or red on its own, because a figure moving is not by itself
 * good or bad — a `tone` says so explicitly where the screen genuinely knows.
 */
export function Metric({
	label,
	value,
	note,
	tone,
	to,
	icon,
}: {
	label: ReactNode;
	value: ReactNode;
	note?: ReactNode;
	tone?: "positive" | "negative" | "muted";
	/** Makes the whole tile the target for the list it summarises. */
	to?: string;
	icon?: (props: { size?: number }) => ReactNode;
}) {
	const tones = {
		positive: "text-success",
		negative: "text-danger",
		muted: "text-muted",
	} as const;

	const body = (
		<>
			<div className="flex items-start justify-between gap-3">
				<span className="text-[12px] font-medium leading-snug text-muted">{label}</span>
				{icon && (
					<span className="flex-none text-slate-faint" aria-hidden="true">
						{icon({ size: 16 })}
					</span>
				)}
			</div>
			<div className="tabular mt-2 text-[26px] font-semibold leading-none tracking-[-0.025em] text-ink">
				{value}
			</div>
			{note && (
				<div className={cx("mt-2 text-[11.5px] font-medium", tone ? tones[tone] : "text-muted")}>
					{note}
				</div>
			)}
		</>
	);

	if (to) {
		return (
			<Link to={to} className="p-card block p-4 transition hover:border-blue-line">
				{body}
			</Link>
		);
	}

	return <div className="p-card p-4">{body}</div>;
}

/** The row `Metric`s sit in. Four across, collapsing to two and then one. */
export function MetricGrid({ children, columns = 4 }: { children: ReactNode; columns?: 3 | 4 }) {
	return (
		<div
			className={cx(
				"mb-5 grid gap-3 sm:grid-cols-2",
				columns === 4 ? "lg:grid-cols-4" : "lg:grid-cols-3",
			)}
		>
			{children}
		</div>
	);
}

/**
 * A proportion, as a bar under a figure.
 *
 * Always paired with the number it draws — a bar on its own is a shape, not a
 * measurement — and it carries the ARIA meter roles so the value is available
 * to somebody who is not looking at the shape at all.
 */
export function Bar({
	value,
	max,
	label,
	tone = "blue",
}: {
	value: number;
	max: number;
	label: string;
	/**
	 * `in` and `out` are the two chart series, named the same way here on
	 * purpose: a breakdown under a chart that used a different colour for the
	 * same quantity would be two answers to one question. Their hexes live in
	 * `ui/chart.tsx`, which is where the palette was validated.
	 */
	tone?: "blue" | "success" | "warning" | "danger" | "in" | "out";
}) {
	const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
	const tones = {
		blue: "bg-blue",
		success: "bg-success",
		warning: "bg-warning-dot",
		danger: "bg-danger-dot",
		in: "bg-[#6B4FA8]",
		out: "bg-[#A9640F]",
	} as const;

	return (
		<div
			role="meter"
			aria-valuenow={value}
			aria-valuemin={0}
			aria-valuemax={max}
			aria-label={label}
			className="h-1.5 w-full overflow-hidden rounded-full bg-surface"
		>
			<div className={cx("h-full rounded-full transition-[width]", tones[tone])} style={{ width: `${pct}%` }} />
		</div>
	);
}

/**
 * An amount with its currency, at the size a total is read at.
 *
 * A component rather than a call to `formatMoney` at each site, because a total
 * and the figures underneath it have to line up in a column — `tabular` here
 * once is what stops a table of money jittering as it updates.
 */
export function Money({
	amount,
	currency,
	size = "md",
	className,
}: {
	amount: number | null | undefined;
	currency?: string | null;
	size?: "sm" | "md" | "lg";
	className?: string;
}) {
	// A seven-figure total in a four-across grid is the widest thing on a
	// finance page, so the headline step is 22px rather than the 26px a count
	// gets: "TZS 20,153,204" has to stay on one line in a 260px tile.
	const sizes = {
		sm: "text-[13px]",
		md: "text-[15px] font-semibold",
		lg: "text-[22px] font-semibold leading-none tracking-[-0.02em]",
	} as const;

	return (
		<span className={cx("tabular text-ink", sizes[size], className)}>
			{formatMoney(amount, currency)}
		</span>
	);
}

/* ------------------------------------------------------------------ toolbar */

/** The row of filters above a table. Wraps rather than scrolls on a narrow screen. */
export function Toolbar({ children }: { children: ReactNode }) {
	return <div className="mb-4 flex flex-wrap items-center gap-2">{children}</div>;
}

/**
 * The search box in a toolbar.
 *
 * The icon sits *inside* the field and the whole box takes the focus ring, so
 * focus never draws a rectangle around part of a control — the mistake
 * `.control` in `index.css` exists to record.
 */
export function SearchBox({
	value,
	onChange,
	placeholder = "Search",
	className,
}: {
	value: string;
	onChange: (value: string) => void;
	placeholder?: string;
	className?: string;
}) {
	return (
		<div
			className={cx(
				"flex min-w-[200px] flex-1 items-center gap-2 rounded-lg border border-rail-line bg-white px-3 focus-within:border-blue focus-within:ring-[3px] focus-within:ring-blue-soft sm:max-w-xs",
				className,
			)}
		>
			<Icon.search size={15} className="flex-none text-slate-faint" />
			<input
				type="search"
				value={value}
				onChange={(event) => onChange(event.target.value)}
				placeholder={placeholder}
				aria-label={placeholder}
				className="w-full bg-transparent py-2 text-[13px] text-ink outline-none placeholder:text-slate-faint focus-visible:ring-0"
			/>
		</div>
	);
}

/** A select in a toolbar — same height and hairline as the search beside it. */
export function FilterSelect({
	value,
	onChange,
	label,
	options,
	allLabel = "All",
}: {
	value: string;
	onChange: (value: string) => void;
	label: string;
	options: { value: string; label: string }[];
	/** The empty-value row. Pass `null` for a select that must have an answer. */
	allLabel?: string | null;
}) {
	return (
		<select
			value={value}
			onChange={(event) => onChange(event.target.value)}
			aria-label={label}
			className="rounded-lg border border-rail-line bg-white px-3 py-2 text-[13px] text-ink outline-none focus:border-blue focus:ring-[3px] focus:ring-blue-soft"
		>
			{allLabel !== null && <option value="">{allLabel}</option>}
			{options.map((option) => (
				<option key={option.value} value={option.value}>
					{option.label}
				</option>
			))}
		</select>
	);
}

/* -------------------------------------------------------------------- table */

/**
 * A table of records.
 *
 * **It scrolls inside itself.** A console table is wide by nature and the page
 * body must never scroll sideways, so the overflow lives here rather than being
 * remembered at each of a dozen call sites.
 *
 * The head is a tinted strip rather than a ruled line, which is what lets the
 * body rows carry a hairline each without the whole thing reading as a grid.
 */
export function Table({
	head,
	children,
	minWidth = 720,
}: {
	head: ReactNode[];
	children: ReactNode;
	/** Below this the table scrolls rather than crushing its columns. */
	minWidth?: number;
}) {
	return (
		<div className="overflow-x-auto">
			<table className="w-full border-collapse text-left" style={{ minWidth }}>
				<thead>
					<tr className="border-b p-divide bg-canvas">
						{head.map((cell, index) => (
							<th
								key={index}
								scope="col"
								className="whitespace-nowrap px-4 py-2.5 text-[10.5px] font-semibold uppercase tracking-[0.07em] text-rail-label"
							>
								{cell}
							</th>
						))}
					</tr>
				</thead>
				<tbody className="divide-y divide-card-line">{children}</tbody>
			</table>
		</div>
	);
}

/** One record. `to` makes the whole row navigable without nesting a link in a link. */
export function Row({ children, to, onClick }: { children: ReactNode; to?: string; onClick?: () => void }) {
	const interactive = Boolean(to || onClick);

	return (
		<tr
			className={cx("align-middle transition", interactive && "cursor-pointer hover:bg-canvas")}
			onClick={onClick}
		>
			{children}
		</tr>
	);
}

export function Cell({
	children,
	className,
	nowrap,
}: {
	children: ReactNode;
	className?: string;
	nowrap?: boolean;
}) {
	return (
		<td className={cx("px-4 py-3 text-[13px] text-slate-strong", nowrap && "whitespace-nowrap", className)}>
			{children}
		</td>
	);
}

/**
 * The first cell of a row: the thing's name, with what tells it apart under it.
 *
 * A component rather than markup at each site because it is the one cell whose
 * shape must be identical across every table in the console — it is what the
 * eye tracks down the left edge.
 */
export function NameCell({
	title,
	meta,
	to,
	lead,
}: {
	title: ReactNode;
	meta?: ReactNode;
	to?: string;
	lead?: ReactNode;
}) {
	const inner = (
		<>
			<div className="truncate text-[13px] font-semibold text-ink">{title}</div>
			{meta && <div className="mt-0.5 truncate text-[11.5px] text-muted">{meta}</div>}
		</>
	);

	return (
		<td className="px-4 py-3">
			<div className="flex min-w-0 items-center gap-3">
				{lead}
				<div className="min-w-0">
					{to ? (
						<Link to={to} className="block min-w-0 hover:[&>div:first-child]:text-blue">
							{inner}
						</Link>
					) : (
						inner
					)}
				</div>
			</div>
		</td>
	);
}

/* ------------------------------------------------------------------- record */

/**
 * A record page: the document on the left, what you may do about it on the
 * right, and the right column sticks as the left one scrolls.
 *
 * The proportion is deliberate and matches the deployment and review screens:
 * a decision panel wide enough for a reason field and no wider, because the
 * document is what is being read.
 */
export function RecordLayout({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
	return (
		<div className={cx("grid gap-5", aside ? "lg:grid-cols-[minmax(0,1fr)_320px]" : undefined)}>
			<div className="min-w-0 space-y-4">{children}</div>
			{aside && <div className="space-y-4 lg:sticky lg:top-[76px] lg:self-start">{aside}</div>}
		</div>
	);
}

/**
 * The identity strip at the top of a record — who or what this is, and the one
 * state that governs everything below.
 *
 * Navy rather than white, and the only dark surface on a console page. It is
 * the same move `Card accent="danger"` is in the portal: used once per screen,
 * which is what keeps it meaning "this is the thing you opened".
 */
export function RecordBanner({
	title,
	meta,
	lead,
	trailing,
}: {
	title: ReactNode;
	meta?: ReactNode;
	lead?: ReactNode;
	trailing?: ReactNode;
}) {
	return (
		<div className="flex flex-wrap items-center gap-4 rounded-xl bg-rail px-5 py-4 text-white">
			{lead}
			<div className="min-w-0 flex-1">
				<h2 className="truncate text-[17px] font-semibold tracking-[-0.015em]">{title}</h2>
				{meta && <p className="mt-1 truncate text-[12.5px] text-white/65">{meta}</p>}
			</div>
			{trailing && <div className="flex flex-none flex-wrap items-center gap-2">{trailing}</div>}
		</div>
	);
}

/**
 * The fields of a record, as a definition list.
 *
 * A real `dl`, so a screen reader announces "Branch: Ubungo" rather than two
 * unrelated pieces of text. Two columns on a wide screen, stacked below —
 * label over value is the only shape that survives a narrow viewport without
 * either half being truncated to nothing.
 */
export function DetailList({ children }: { children: ReactNode }) {
	return <dl className="grid gap-x-6 gap-y-3.5 sm:grid-cols-[minmax(120px,150px)_minmax(0,1fr)]">{children}</dl>;
}

export function Detail({ label, children }: { label: ReactNode; children: ReactNode }) {
	return (
		<div className="contents">
			<dt className="text-[12px] font-medium text-muted sm:py-0.5">{label}</dt>
			<dd className="m-0 min-w-0 text-[13px] text-ink sm:py-0.5">{children ?? "—"}</dd>
		</div>
	);
}

/**
 * The panel a decision is made in — what is being asked, a reason field, and
 * the two or three buttons that end it.
 *
 * `question` is a heading, not a sentence explaining the screen. The rule from
 * the portal holds here too: a panel that narrates what the reader can already
 * see is copy to delete.
 */
export function DecisionCard({
	eyebrow,
	title,
	children,
	actions,
}: {
	eyebrow?: ReactNode;
	title: ReactNode;
	children?: ReactNode;
	actions?: ReactNode;
}) {
	return (
		<section className="p-card p-5">
			{eyebrow && (
				<div className="text-[10.5px] font-semibold uppercase tracking-[0.09em] text-rail-label">
					{eyebrow}
				</div>
			)}
			<h2 className="mt-1.5 text-[15px] font-semibold tracking-[-0.01em] text-ink">{title}</h2>
			{children && <div className="mt-3.5 space-y-3">{children}</div>}
			{actions && <div className="mt-4 grid gap-2">{actions}</div>}
		</section>
	);
}

/* -------------------------------------------------------------------- board */

/** A board of stages — the shape a pipeline is actually read in. */
export function Board({ children }: { children: ReactNode }) {
	return (
		<div className="-mx-1 flex gap-3 overflow-x-auto px-1 pb-2">
			{children}
		</div>
	);
}

export function BoardColumn({
	title,
	count,
	tone,
	children,
}: {
	title: ReactNode;
	count: number;
	/** The dot beside the heading. A stage's colour, never its only signal. */
	tone?: "neutral" | "info" | "warning" | "success" | "danger";
	children: ReactNode;
}) {
	const dots = {
		neutral: "bg-slate-faint",
		info: "bg-blue",
		warning: "bg-warning-dot",
		success: "bg-success-dot",
		danger: "bg-danger-dot",
	} as const;

	return (
		<section className="flex w-[248px] flex-none flex-col rounded-xl bg-surface p-2.5">
			<header className="mb-2 flex items-center gap-2 px-1.5">
				<span className={cx("h-1.5 w-1.5 flex-none rounded-full", dots[tone ?? "neutral"])} aria-hidden="true" />
				<h3 className="min-w-0 flex-1 truncate text-[12.5px] font-semibold text-ink">{title}</h3>
				<span className="tabular text-[12px] font-semibold text-muted">{count}</span>
			</header>
			<div className="space-y-2">{children}</div>
		</section>
	);
}

export function BoardCard({
	title,
	meta,
	footer,
	to,
}: {
	title: ReactNode;
	meta?: ReactNode;
	footer?: ReactNode;
	to?: string;
}) {
	const body = (
		<>
			<div className="line-clamp-2 text-[13px] font-semibold leading-snug text-ink">{title}</div>
			{meta && <div className="mt-1 line-clamp-2 text-[11.5px] leading-relaxed text-muted">{meta}</div>}
			{footer && <div className="mt-2 flex flex-wrap items-center gap-2">{footer}</div>}
		</>
	);

	if (to) {
		return (
			<Link to={to} className="p-card block p-3 transition hover:border-blue-line">
				{body}
			</Link>
		);
	}

	return <div className="p-card p-3">{body}</div>;
}

/* -------------------------------------------------------------------- forms */

/**
 * One labelled control.
 *
 * The label is a real `label` wrapping its control, so clicking it focuses the
 * field and no `htmlFor`/`id` pair can be got wrong. `hint` sits under the
 * control and `error` replaces it — never both, because a field that shows
 * advice and a failure at once is a field somebody reads neither line of.
 */
export function Field({
	label,
	hint,
	error,
	required,
	className,
	children,
}: {
	label: ReactNode;
	hint?: ReactNode;
	error?: ReactNode;
	required?: boolean;
	className?: string;
	children: ReactNode;
}) {
	return (
		<label className={cx("block", className)}>
			<span className="mb-1.5 block text-[12px] font-semibold text-slate-strong">
				{label}
				{required && (
					<span className="ml-1 text-danger" aria-hidden="true">
						*
					</span>
				)}
			</span>
			{children}
			{error ? (
				<span className="mt-1.5 block text-[11.5px] font-medium text-danger">{error}</span>
			) : (
				hint && <span className="mt-1.5 block text-[11.5px] text-muted">{hint}</span>
			)}
		</label>
	);
}

/** The two-column grid a form's fields sit in. `Field className="sm:col-span-2"` spans. */
export function FieldGrid({ children }: { children: ReactNode }) {
	return <div className="grid gap-4 sm:grid-cols-2">{children}</div>;
}

/** A heading inside a long form, so the thing has sections rather than a scroll. */
export function FormSection({
	title,
	hint,
	children,
}: {
	title: ReactNode;
	hint?: ReactNode;
	children: ReactNode;
}) {
	return (
		<section className="border-t p-divide pt-5 first:border-t-0 first:pt-0">
			<h3 className="text-[13.5px] font-semibold text-ink">{title}</h3>
			{hint && <p className="mt-1 max-w-prose text-[12px] leading-relaxed text-muted">{hint}</p>}
			<div className="mt-4">{children}</div>
		</section>
	);
}

/** The control every text field in the console uses. */
const CONTROL =
	"w-full rounded-lg border border-rail-line bg-white px-3 py-2 text-[13px] text-ink outline-none transition placeholder:text-slate-faint focus:border-blue focus:ring-[3px] focus:ring-blue-soft disabled:cursor-not-allowed disabled:bg-surface disabled:text-muted";

export function TextInput({
	value,
	onChange,
	type = "text",
	placeholder,
	disabled,
	min,
	max,
}: {
	value: string;
	onChange: (value: string) => void;
	type?: "text" | "date" | "number" | "email" | "tel" | "datetime-local";
	placeholder?: string;
	disabled?: boolean;
	min?: string | number;
	max?: string | number;
}) {
	return (
		<input
			type={type}
			value={value}
			min={min}
			max={max}
			disabled={disabled}
			placeholder={placeholder}
			onChange={(event) => onChange(event.target.value)}
			className={CONTROL}
		/>
	);
}

export function TextArea({
	value,
	onChange,
	rows = 5,
	placeholder,
	disabled,
}: {
	value: string;
	onChange: (value: string) => void;
	rows?: number;
	placeholder?: string;
	disabled?: boolean;
}) {
	return (
		<textarea
			value={value}
			rows={rows}
			disabled={disabled}
			placeholder={placeholder}
			onChange={(event) => onChange(event.target.value)}
			className={cx(CONTROL, "resize-y leading-relaxed")}
		/>
	);
}

export function Select({
	value,
	onChange,
	options,
	placeholder,
	disabled,
}: {
	value: string;
	onChange: (value: string) => void;
	options: { value: string; label: string }[];
	/** The unselected row. Omit for a select that always has an answer. */
	placeholder?: string;
	disabled?: boolean;
}) {
	return (
		<select
			value={value}
			disabled={disabled}
			onChange={(event) => onChange(event.target.value)}
			className={CONTROL}
		>
			{placeholder !== undefined && <option value="">{placeholder}</option>}
			{options.map((option) => (
				<option key={option.value} value={option.value}>
					{option.label}
				</option>
			))}
		</select>
	);
}

/** A checkbox with its sentence beside it, aligned to the first line of text. */
export function Check({
	checked,
	onChange,
	label,
	hint,
	disabled,
}: {
	checked: boolean;
	onChange: (checked: boolean) => void;
	label: ReactNode;
	hint?: ReactNode;
	disabled?: boolean;
}) {
	return (
		<label className="flex cursor-pointer items-start gap-2.5">
			<input
				type="checkbox"
				checked={checked}
				disabled={disabled}
				onChange={(event) => onChange(event.target.checked)}
				className="mt-0.5 h-4 w-4 flex-none rounded border-rail-line text-blue accent-blue"
			/>
			<span className="min-w-0">
				<span className="block text-[13px] font-medium text-ink">{label}</span>
				{hint && <span className="mt-0.5 block text-[11.5px] leading-relaxed text-muted">{hint}</span>}
			</span>
		</label>
	);
}

/* -------------------------------------------------------------------- misc */

/**
 * A short, quiet sentence that qualifies the figures above it.
 *
 * The one kind of explanatory copy this product keeps: not narration of the
 * screen, but a statement about what the numbers on it are and are not — "at
 * the published fee", "stipend payments only". Without it a reader would take a
 * derived figure for a receipt.
 */
export function Caveat({ children }: { children: ReactNode }) {
	return (
		<p className="flex items-start gap-2 text-[11.5px] leading-relaxed text-muted">
			<Icon.file size={13} className="mt-0.5 flex-none text-slate-faint" />
			<span className="min-w-0">{children}</span>
		</p>
	);
}

/** A breadcrumb back to the list a record came from. */
export function BackLink({ to, children }: { to: string; children: ReactNode }) {
	return (
		<Link
			to={to}
			className="mb-4 inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-muted transition hover:text-ink"
		>
			<Icon.back size={14} />
			{children}
		</Link>
	);
}
