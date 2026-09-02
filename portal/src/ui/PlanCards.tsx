import type { ReactNode } from "react";

import { formatMoney } from "../lib/format";
import type { PricedType } from "../portal/types";
import { Tick } from "./form";
import { Empty, Spinner, cx } from "./primitives";

/**
 * The society's membership types, side by side, as a person choosing between
 * them needs to see them.
 *
 * **Every word on a card is the society's.** The name, the eligibility line and
 * each benefit are fields on `VMMS Membership Type` and its benefits table,
 * served by `member.membership_type_pricing`. No tier, no ordering rule and no
 * "most popular" badge is decided here — the order is the endpoint's (cheapest
 * first) and a society that wants a different one changes its fees, not this
 * file.
 *
 * **The price is the endpoint's too, including whether there is one.** `free` is
 * its own flag rather than a comparison with zero, so a society that charges
 * nothing renders "Free" instead of a currency symbol beside a nought, and the
 * lifetime types say so instead of rendering a number of days.
 *
 * Used by the join wizard and by the membership tab. The two differ only in what
 * the button says and what it does, which is why that is a prop.
 */
export function PlanCards({
	types,
	loading,
	selected,
	onSelect,
	actionLabel = "Select plan",
	held,
	empty,
	columns = 4,
}: {
	types: PricedType[];
	loading?: boolean;
	/** The chosen type's key, when this grid is being used to choose. */
	selected?: string | null;
	onSelect?: (membershipType: string) => void;
	actionLabel?: string;
	/** Type keys this person already holds, marked rather than hidden. */
	held?: string[];
	empty?: ReactNode;
	/**
	 * How wide the grid is allowed to get. The membership tab has the page to
	 * itself and can stand four plans side by side; the join wizard gives up a
	 * quarter of its width to the step rail, and four columns in what is left
	 * squeezes a benefit list into two words a line.
	 */
	columns?: 2 | 4;
}) {
	if (loading) return <Spinner label="Loading membership types…" />;

	if (types.length === 0) {
		return (
			<Empty title="No membership types published">
				{empty ?? "This society has not published any membership types yet."}
			</Empty>
		);
	}

	// Choosing and starting are different acts, and they need different roles.
	// The wizard's plan step tracks a selection, so its cards are radios in a
	// radiogroup. The membership tab tracks none — clicking a plan leaves for the
	// wizard — so its cards are ordinary buttons, because a radiogroup nothing is
	// ever checked in announces a state that does not exist.
	const choosing = selected !== undefined;

	return (
		<div
			role={choosing ? "radiogroup" : undefined}
			aria-label={choosing ? "Membership type" : undefined}
			className={cx(
				"grid gap-4 sm:grid-cols-2",
				columns === 4 && types.length > 2 && "xl:grid-cols-4",
			)}
		>
			{types.map((row) => (
				<PlanCard
					key={row.membership_type}
					row={row}
					choosing={choosing}
					selected={selected === row.membership_type}
					onSelect={onSelect}
					actionLabel={actionLabel}
					held={held?.includes(row.membership_type) ?? false}
				/>
			))}
		</div>
	);
}

function PlanCard({
	row,
	choosing,
	selected,
	onSelect,
	actionLabel,
	held,
}: {
	row: PricedType;
	choosing: boolean;
	selected: boolean;
	onSelect?: (membershipType: string) => void;
	actionLabel: string;
	held: boolean;
}) {
	// The whole card is the control when there is one, so the target is the card
	// rather than a button at the bottom of it. Where there is nothing to do with
	// a plan it is a plain div, because nothing should be focusable that does not
	// do anything.
	const Wrapper = onSelect ? "button" : "div";

	return (
		<Wrapper
			{...(onSelect
				? {
						type: "button" as const,
						...(choosing ? { role: "radio", "aria-checked": selected } : {}),
						onClick: () => onSelect(row.membership_type),
					}
				: {})}
			className={cx(
				"group relative flex flex-col overflow-hidden rounded-2xl border bg-white text-left transition",
				selected
					? "border-blue shadow-pop ring-1 ring-blue"
					: "border-card-line border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)]",
				onSelect && !selected && "hover:-translate-y-0.5 hover:border-card-line hover:shadow-pop",
			)}
		>
			{/* The band across the top is what makes a column read as a plan rather
			    than as another card in a list. It turns brand-red on the chosen one,
			    which is the only signal the design needs for selection. */}
			<span
				aria-hidden="true"
				className={cx(
					"h-1 w-full flex-none transition-colors",
					selected ? "bg-blue" : "bg-rail/15 group-hover:bg-rail/40",
				)}
			/>

			<div className="flex flex-1 flex-col p-5">
				<div className="flex items-start justify-between gap-3">
					<h3 className="text-[15.5px] font-semibold leading-tight tracking-tight text-ink">
						{row.membership_type_name || row.membership_type}
					</h3>
					{held && (
						<span className="flex-none rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
							You hold this
						</span>
					)}
				</div>

				<div className="mt-4 border-t border-card-line pt-4">
					<div className="flex items-baseline gap-1.5">
						<span className="text-[26px] font-semibold leading-none tracking-tight text-ink">
							{row.free ? "Free" : formatMoney(row.amount, row.currency)}
						</span>
						{!row.free && !row.is_lifetime && (
							<span className="text-[12px] font-semibold text-slate-faint">
								{periodLabel(row.duration_days)}
							</span>
						)}
					</div>

					<p className="mt-1.5 text-[11.5px] leading-relaxed text-muted">
						{row.is_lifetime
							? "One payment. Lifetime membership, never renewed."
							: `Runs for ${row.duration_days} days, then renews.`}
					</p>
				</div>

				{row.benefits.length > 0 && (
					<div className="mt-4">
						<p className="text-[10px] font-semibold uppercase tracking-wider text-blue">
							What is included
						</p>
						<ul className="mt-2.5 space-y-2">
							{row.benefits.map((benefit) => (
								<li key={benefit.key} className="flex gap-2">
									<span
										className="mt-[3px] grid h-3.5 w-3.5 flex-none place-items-center rounded-full bg-blue/10 text-blue"
										aria-hidden="true"
									>
										<Tick size={9} />
									</span>
									<span
										className="text-[12px] leading-relaxed text-slate-strong"
										title={benefit.description ?? undefined}
									>
										{benefit.label}
									</span>
								</li>
							))}
						</ul>
					</div>
				)}

				<div className="flex-1" />

				{row.description && (
					<p className="mt-4 rounded-xl bg-surface px-3 py-2.5 text-[11.5px] font-semibold leading-relaxed text-slate-strong">
						{row.description}
					</p>
				)}

				<p className="mt-3 text-[11px] leading-relaxed text-slate-faint">
					{row.requires_approver
						? "Reviewed by the branch before it becomes active."
						: "Active as soon as the fee is settled."}
				</p>

				{onSelect && (
					<span
						className={cx(
							"mt-4 inline-flex items-center justify-center gap-1.5 rounded-xl px-4 py-2.5 text-[12.5px] font-bold transition",
							selected
								? "bg-blue text-white"
								: "border border-card-line bg-white text-slate-strong group-hover:border-blue group-hover:text-ink",
						)}
					>
						{selected ? (
							<>
								<Tick size={12} /> Selected
							</>
						) : (
							<>
								{actionLabel} <span aria-hidden="true">→</span>
							</>
						)}
					</span>
				)}
			</div>
		</Wrapper>
	);
}

/**
 * "/year" where a duration is one, "/ 90 days" where it is not.
 *
 * A society sets `duration_days` and nothing constrains it to a year, so the
 * common case is named and everything else is stated in the unit the record
 * actually holds. No calendar arithmetic: 365 is the only number worth a word.
 */
function periodLabel(days: number): string {
	if (days === 365 || days === 366) return "/ year";
	if (days === 30 || days === 31) return "/ month";
	return `/ ${days} days`;
}
