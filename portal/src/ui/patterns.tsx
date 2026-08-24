import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { Icon } from "./icons";
import { StateBadge, cx } from "./primitives";

/**
 * The screen-level patterns the redesign adds, on top of `primitives`.
 *
 * Everything here composes what is already there rather than restating it: a
 * `FolderCard` is a `card` with a lid drawn on it, a `FilterBar` is a row of
 * the same `.control` cells `index.css` defines. Nothing in this file owns a
 * colour or a radius of its own.
 */

/* -------------------------------------------------------------- discovery */

/**
 * A search field, pill-shaped like every other control.
 *
 * A real `<input type="search">` inside a `<label>`, so the icon is part of the
 * control rather than a decoration beside it and clicking anywhere in the pill
 * focuses the field. The visible label is optional because a filter bar's
 * fields are usually self-evident from their placeholder — but an accessible
 * name never is, so `label` is required and is visually hidden when not shown.
 */
export function SearchField({
	value,
	onChange,
	label,
	placeholder,
	showLabel = false,
	className,
	id,
}: {
	value: string;
	onChange: (value: string) => void;
	label: string;
	placeholder?: string;
	showLabel?: boolean;
	className?: string;
	id?: string;
}) {
	return (
		<div className={cx("min-w-0", className)}>
			{showLabel && (
				<label htmlFor={id} className="mb-1.5 block px-1 text-[11px] text-muted">
					{label}
				</label>
			)}

			<div className="control border border-hairline-strong bg-white">
				<Icon.search size={15} className="flex-none text-slate-faint" />
				<input
					id={id}
					type="search"
					value={value}
					onChange={(event) => onChange(event.target.value)}
					placeholder={placeholder}
					aria-label={showLabel ? undefined : label}
					className="min-w-0 flex-1 border-0 bg-transparent p-0 text-[13px] text-ink outline-none placeholder:text-slate-faint"
				/>
			</div>
		</div>
	);
}

/**
 * A labelled `<select>` in the filter bar's pill shape.
 *
 * A native select, deliberately. It is keyboard-navigable, it uses the
 * platform's own picker on a phone, and it needs no ARIA to be understood —
 * none of which a styled listbox gets for free.
 */
export function FilterSelect({
	value,
	onChange,
	label,
	options,
	showLabel = false,
	id,
	className,
}: {
	value: string;
	onChange: (value: string) => void;
	label: string;
	options: { value: string; label: string }[];
	showLabel?: boolean;
	id?: string;
	className?: string;
}) {
	return (
		<div className={cx("min-w-0", className)}>
			{showLabel && (
				<label htmlFor={id} className="mb-1.5 block px-1 text-[11px] text-muted">
					{label}
				</label>
			)}

			<select
				id={id}
				value={value}
				onChange={(event) => onChange(event.target.value)}
				aria-label={showLabel ? undefined : label}
				className="w-full rounded-full border border-hairline-strong bg-white px-4 py-2.5 text-[13px] text-ink outline-none"
			>
				{options.map((option) => (
					<option key={option.value} value={option.value}>
						{option.label}
					</option>
				))}
			</select>
		</div>
	);
}

/**
 * The row of controls above a register or a discovery grid.
 *
 * On a phone the whole bar collapses behind one "Filters" button rather than
 * stacking five full-width pills down the screen — see `collapsible`. The
 * search field stays out of the collapse, because searching is the one thing
 * somebody arriving on a small screen most often wants.
 */
export function FilterBar({
	children,
	search,
	className,
	count,
}: {
	children?: ReactNode;
	/** Kept visible on every screen size. */
	search?: ReactNode;
	className?: string;
	/** How many filters are currently set, for the mobile summary control. */
	count?: number;
}) {
	return (
		<div className={cx("card mb-5 p-3 sm:p-4", className)}>
			<div className="flex flex-col gap-3 lg:flex-row lg:items-end">
				{search && <div className="min-w-0 flex-1">{search}</div>}

				{children && (
					<details className="group min-w-0 lg:hidden">
						<summary className="flex cursor-pointer list-none items-center justify-center gap-2 rounded-full border border-hairline-strong bg-white px-4 py-2.5 text-[13px] font-medium text-slate-strong">
							<Icon.filter size={15} className="flex-none text-slate-faint" />
							Filters
							{count !== undefined && count > 0 && (
								<span className="rounded-full bg-blue px-1.5 py-0.5 text-[10px] font-semibold leading-none text-white">
									{count}
								</span>
							)}
							<Icon.chevron
								size={14}
								className="flex-none text-slate-faint transition group-open:rotate-180"
							/>
						</summary>

						<div className="mt-3 grid gap-3 sm:grid-cols-2">{children}</div>
					</details>
				)}

				{children && (
					<div className="hidden min-w-0 gap-3 lg:flex lg:flex-none lg:items-end">{children}</div>
				)}
			</div>
		</div>
	);
}

/* ---------------------------------------------------------------- folders */

/**
 * A project, drawn as a folder.
 *
 * **The shape carries the idea.** A project is a container — it holds terms of
 * reference, and those hold deployments — and a folder says that before a word
 * is read. The lid is a wash of the shell tone with a tab drawn on it rather
 * than an illustration, so it costs nothing and inherits the theme.
 *
 * The whole card is one `<Link>`, not a div with a click handler, so it is
 * reachable by keyboard, opens in a new tab on a middle click and announces
 * itself as a link.
 */
export function FolderCard({
	to,
	name,
	summary,
	status,
	counts,
}: {
	to: string;
	name: ReactNode;
	summary?: ReactNode;
	status?: string | null;
	/** The short facts on the folder's foot — "3 TORs · 6 deployments". */
	counts?: ReactNode;
}) {
	return (
		<Link
			to={to}
			className="card group flex h-full flex-col overflow-hidden transition duration-200 hover:shadow-lift focus-visible:shadow-lift"
		>
			<div className="grid h-[128px] place-items-center bg-surface">
				<svg
					viewBox="0 0 96 76"
					width="78"
					height="62"
					aria-hidden="true"
					className="text-blue-soft transition-transform duration-200 group-hover:-translate-y-0.5"
				>
					<path
						d="M4 14a8 8 0 0 1 8-8h22l8 9h42a8 8 0 0 1 8 8v45a8 8 0 0 1-8 8H12a8 8 0 0 1-8-8z"
						fill="currentColor"
					/>
					<path
						d="M4 26h88v40a8 8 0 0 1-8 8H12a8 8 0 0 1-8-8z"
						fill="currentColor"
						className="text-blue-line/45"
					/>
				</svg>
			</div>

			<div className="flex flex-1 flex-col gap-1.5 px-5 pb-4 pt-4">
				<h3 className="font-display text-[14.5px] font-medium leading-snug tracking-tight text-ink">
					{name}
				</h3>
				{summary && (
					<p className="line-clamp-2 text-[12px] leading-relaxed text-muted">{summary}</p>
				)}
			</div>

			<div className="flex items-center justify-between gap-3 border-t border-hairline-soft px-5 py-3">
				<span className="tabular min-w-0 truncate text-[11.5px] text-muted">{counts}</span>
				{status && <StateBadge state={status} />}
			</div>
		</Link>
	);
}

/* ------------------------------------------------------------- record rows */

/**
 * One related record in a list on a workspace page — a TOR under a project, a
 * deployment under a TOR.
 *
 * A link row rather than a card: these appear in runs of five and twenty, and
 * twenty cards is a page somebody scrolls past rather than reads.
 */
export function RelatedRecordRow({
	to,
	title,
	meta,
	status,
	trailing,
}: {
	to: string;
	title: ReactNode;
	meta?: ReactNode;
	status?: string | null;
	trailing?: ReactNode;
}) {
	return (
		<Link
			to={to}
			className="flex items-center gap-4 px-5 py-3.5 transition hover:bg-surface focus-visible:bg-surface"
		>
			<div className="min-w-0 flex-1">
				<div className="truncate text-[13px] font-medium text-ink">{title}</div>
				{meta && <div className="mt-0.5 truncate text-[11.5px] text-muted">{meta}</div>}
			</div>

			{trailing && <div className="tabular flex-none text-[12px] text-muted">{trailing}</div>}
			{status && <StateBadge state={status} />}

			<Icon.chevron size={14} className="-rotate-90 flex-none text-slate-faint" aria-hidden="true" />
		</Link>
	);
}

/* ------------------------------------------------------------------ heroes */

/**
 * The centred discovery hero on Events and Opportunities.
 *
 * **A charcoal panel, not a red gradient.** The previous version used the
 * society's protected emblem colour as a full-bleed decorative wash across the
 * top of a public-facing page, which is exactly what the emblem rules exist to
 * prevent. The authority tone does the same compositional job — a dark band the
 * white search panel overlaps — without borrowing that meaning.
 *
 * `overlap` leaves room at the foot of the hero for a panel to sit across its
 * edge, which is what `children` is for.
 */
export function DiscoveryHero({
	eyebrow,
	title,
	lead,
	children,
}: {
	eyebrow?: ReactNode;
	title: ReactNode;
	lead?: ReactNode;
	/** The search and filter panel, overlapping the hero's lower edge. */
	children?: ReactNode;
}) {
	return (
		<div className="mb-6">
			<div
				className={cx(
					"rounded-feature bg-authority px-6 text-center text-white sm:px-10",
					children ? "pb-20 pt-12 sm:pb-24 sm:pt-16" : "py-12 sm:py-16",
				)}
			>
				{eyebrow && (
					<p className="mb-3 text-[10px] font-semibold uppercase tracking-eyebrow text-white/55">
						{eyebrow}
					</p>
				)}

				<h2 className="mx-auto max-w-2xl text-balance font-display text-[28px] font-medium leading-[1.15] tracking-tight sm:text-[36px]">
					{title}
				</h2>

				{lead && (
					<p className="mx-auto mt-3 max-w-xl text-[13.5px] leading-relaxed text-white/70">{lead}</p>
				)}
			</div>

			{children && <div className="-mt-14 px-2 sm:-mt-16 sm:px-6">{children}</div>}
		</div>
	);
}

/* ------------------------------------------------------------- dashboards */

/**
 * One figure inside an activity panel.
 *
 * **An inset, not a card.** The approved dashboard groups four figures inside
 * one white panel rather than scattering four white cards on the grey — the
 * panel is the unit ("Your activity"), and the figures are its contents. A
 * `StatTile` is the other shape and is still right where four figures really
 * are four separate destinations; this one is for a set that reads together.
 *
 * `to` is optional. A figure somebody can act on should be a link; a figure
 * that is just context should not pretend to be one.
 */
export function ActivityTile({
	label,
	value,
	hint,
	icon,
	to,
	selected = false,
}: {
	label: ReactNode;
	value: ReactNode;
	hint?: ReactNode;
	icon?: (props: { size?: number; className?: string }) => ReactNode;
	to?: string;
	/** Draws the tile in the blue wash — for the one figure that wants attention. */
	selected?: boolean;
}) {
	const body = (
		<>
			<div className="flex items-start justify-between gap-2">
				<span className="truncate text-[11.5px] text-muted">{label}</span>
				{icon && (
					<span
						className={cx(
							"grid h-6 w-6 flex-none place-items-center rounded-full",
							selected ? "bg-blue text-white" : "bg-white text-slate-faint",
						)}
						aria-hidden="true"
					>
						{icon({ size: 13 })}
					</span>
				)}
			</div>

			<div className="tabular mt-3 font-display text-[26px] font-medium leading-none tracking-tight text-ink">
				{value}
			</div>

			{hint && <div className="mt-1.5 truncate text-[11px] text-muted">{hint}</div>}
		</>
	);

	const shell = cx(
		"block rounded-control px-4 py-3.5 transition",
		selected ? "bg-blue-soft" : "bg-surface",
	);

	if (to) {
		return (
			<Link to={to} className={cx(shell, "hover:bg-blue-soft")}>
				{body}
			</Link>
		);
	}

	return <div className={shell}>{body}</div>;
}

/**
 * The one panel on a page that is being singled out — a deployment invitation
 * waiting on an answer, an exception that has to be dealt with today.
 *
 * The authority charcoal, used sparingly and never more than once per screen.
 * Its whole job is to be the thing the eye lands on first; two of them on a
 * page is none of them.
 */
export function FeaturePanel({
	eyebrow,
	title,
	children,
	actions,
	meta,
	link,
}: {
	eyebrow?: ReactNode;
	title: ReactNode;
	children?: ReactNode;
	actions?: ReactNode;
	/** Short facts along the foot — dates, times, where. */
	meta?: ReactNode[];
	/** A quiet "View details →" in the top-right. */
	link?: { to: string; label: string };
}) {
	return (
		<section className="relative overflow-hidden rounded-card bg-authority p-6 text-white">
			{/* The soft arc in the approved design. Decorative, drawn with a
			    border rather than an image so it costs nothing and inherits
			    nothing that could fail to load. */}
			<div
				aria-hidden="true"
				className="pointer-events-none absolute -right-16 -top-10 h-56 w-56 rounded-full border-[28px] border-white/[.04]"
			/>

			<div className="relative">
				<div className="flex items-start justify-between gap-4">
					{eyebrow && <p className="text-[12px] font-medium text-white/70">{eyebrow}</p>}
					{link && (
						<Link
							to={link.to}
							className="flex-none text-[11.5px] font-medium text-white/70 underline-offset-2 hover:text-white hover:underline"
						>
							{link.label} →
						</Link>
					)}
				</div>

				<h3 className="mt-2 font-display text-[19px] font-medium tracking-tight">{title}</h3>

				{children && (
					<div className="mt-2 max-w-xl text-[12.5px] leading-relaxed text-white/70">{children}</div>
				)}

				<div className="mt-5 flex flex-wrap items-center justify-between gap-4">
					{meta && meta.length > 0 && (
						<ul className="flex flex-wrap items-center gap-x-5 gap-y-1 text-[11.5px] text-white/60">
							{meta.map((item, index) => (
								<li key={index}>{item}</li>
							))}
						</ul>
					)}

					{actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
				</div>
			</div>
		</section>
	);
}

/**
 * A dated row in a "Coming up" list — the day block on the left, the thing on
 * the right.
 *
 * The date is a `<time>` with a machine-readable `dateTime`, so the row is not
 * only legible but parseable.
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
		<>
			<time
				dateTime={iso}
				className="grid h-11 w-11 flex-none place-content-center rounded-control bg-surface text-center leading-none"
			>
				<span className="tabular block text-[14px] font-medium text-ink">{day}</span>
				<span className="mt-0.5 block text-[9px] font-semibold uppercase tracking-wider text-muted">
					{month}
				</span>
			</time>

			<div className="min-w-0 flex-1">
				<div className="truncate text-[12.5px] font-medium text-ink">{title}</div>
				{meta && <div className="mt-0.5 truncate text-[11px] text-muted">{meta}</div>}
			</div>
		</>
	);

	if (to) {
		return (
			<Link to={to} className="flex items-center gap-3 rounded-control p-1 transition hover:bg-surface">
				{body}
			</Link>
		);
	}

	return <div className="flex items-center gap-3 p-1">{body}</div>;
}
