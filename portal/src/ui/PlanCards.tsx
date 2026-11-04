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
 * file. **The one card that stands proud of the row is the one this person
 * already holds**, which is a fact about them rather than a recommendation this
 * app has invented on a society's behalf.
 *
 * **The price is the endpoint's too, including whether there is one.** `free` is
 * its own flag rather than a comparison with zero, so a society that charges
 * nothing renders "Free" instead of a currency symbol beside a nought, and the
 * lifetime types say so instead of rendering a number of days.
 *
 * **The fee and the way in are one panel**, because they are one decision. The
 * card that had its price at the top and its button at the foot, with a benefit
 * list in between, made a person read past the list twice to act on it.
 *
 * Used by the join wizard and by the membership tab, and it is genuinely one
 * implementation: they differ in what the card *is* — a radio somebody chooses
 * in the wizard, a panel with its own actions on the tab — which is `onSelect`,
 * `action` and `footer` and nothing else.
 */
export function PlanCards({
	types,
	loading,
	selected,
	onSelect,
	actionLabel = "Select plan",
	held,
	empty,
	columns = 3,
	action,
	footer,
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
	 * itself, and a society with four types (Kenya's youth in school, youth out
	 * of school, ordinary, life) wants them compared in one row, as its old
	 * system showed them. Four from `lg` (the cards tighten a
	 * little until `xl`); narrower screens wrap to two. The join wizard gives
	 * up a quarter of its width to the step rail, so it stays at two.
	 */
	columns?: 2 | 3 | 4;
	/** The act, inside the price panel, where the card is not itself the control. */
	action?: (plan: PricedType) => ReactNode;
	/** Quiet links under the card: the details panel, the claim on an old card. */
	footer?: (plan: PricedType) => ReactNode;
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
	const ordered = columns === 3 ? centreHeld(types, held ?? []) : types;

	return (
		<div
			role={choosing ? "radiogroup" : undefined}
			aria-label={choosing ? "Membership type" : undefined}
			// `items-start`, so the card somebody holds can stand a little proud
			// of the row without dragging its neighbours' tops down with it.
			//
			// **Four wide at most, and it wraps.** A society with six types gets
			// two rows of the same card rather than six narrower ones: the card is
			// read down — a fee, then a list — and the width that makes the list
			// legible does not divide six ways. The benefit lists are capped for
			// the same reason, so a second row starts where somebody can still see
			// it.
			className={cx(
				"grid items-start gap-4 sm:grid-cols-2",
				columns === 3 && types.length > 2 && "lg:grid-cols-3",
				columns === 4 && types.length === 3 && "lg:grid-cols-3",
				// From `lg`, not `xl`: the portal's sidebar takes 264px of the
				// window, and at `xl` a 1200px laptop still saw two rows of two.
				columns === 4 && types.length > 3 && "lg:grid-cols-4 lg:gap-3 xl:gap-4",
			)}
		>
			{ordered.map((row) => (
				<PlanCard
					key={row.membership_type}
					row={row}
					choosing={choosing}
					selected={selected === row.membership_type}
					onSelect={onSelect}
					actionLabel={actionLabel}
					held={held?.includes(row.membership_type) ?? false}
					action={action}
					footer={footer}
					dense={columns === 4 && types.length > 3}
				/>
			))}
		</div>
	);
}

/** The middle of a three-wide row, and the only slot that is a middle of anything. */
const CENTRE = 1;

/**
 * How many benefits a card shows before it says how many more there are.
 *
 * A cap rather than the whole list, because the list is what makes a card as
 * tall as it is: a society whose sixth type carries eleven benefits would push
 * the second row of a six-type grid off the screen, and a person comparing two
 * of them would be scrolling between them. The rest are in the details panel,
 * which is the place for reading one type rather than weighing six.
 */
const SHOWN_BENEFITS = 5;

/**
 * The row, with this person's own membership in the middle of the first one.
 *
 * **It is the one place the endpoint's order is not the order.** Types arrive
 * cheapest first and that is what everybody else sees; a person who already
 * holds one is not shopping, and the row is composed around the card that is
 * theirs so they find themselves in it at a glance rather than reading three
 * strangers first. Everything else keeps its relative order, so the prices
 * either side of the middle still climb.
 *
 * Only with three or more, because two cards have no middle — and only where
 * the grid is three wide, which is the membership tab. The wizard is somebody
 * choosing, and cards that moved as they chose would be a row that shuffles
 * itself under the cursor.
 *
 * Somebody holding two types centres the cheaper: a second branch membership is
 * a second record, not a second row to compose around.
 */
function centreHeld(types: PricedType[], held: string[]): PricedType[] {
	if (types.length < 3 || held.length === 0) return types;

	const mine = types.findIndex((row) => held.includes(row.membership_type));

	if (mine === -1 || mine === CENTRE) return types;

	const rest = [...types];
	const [theirs] = rest.splice(mine, 1);
	rest.splice(CENTRE, 0, theirs);

	return rest;
}

function PlanCard({
	row,
	choosing,
	selected,
	onSelect,
	actionLabel,
	held,
	action,
	footer,
	dense = false,
}: {
	row: PricedType;
	/** Four in a row: a little less padding and a smaller figure until `xl`. */
	dense?: boolean;
	choosing: boolean;
	selected: boolean;
	onSelect?: (membershipType: string) => void;
	actionLabel: string;
	held: boolean;
	action?: (plan: PricedType) => ReactNode;
	footer?: (plan: PricedType) => ReactNode;
}) {
	// The whole card is the control when there is one, so the target is the card
	// rather than a button at the bottom of it. Where there is nothing to do with
	// a plan it is a plain div, because nothing should be focusable that does not
	// do anything.
	const Wrapper = onSelect ? "button" : "div";
	const { amount, period } = planPrice(row);

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
				"group relative flex min-w-0 flex-col rounded-2xl border bg-white p-5 text-left transition",
				dense && "lg:p-4 xl:p-5",
				// One column has no middle, so the card that would have been in it
				// goes first: a person scrolling a phone should meet their own
				// membership before four they could switch to.
				held && "max-lg:order-first",
				selected
					? "border-blue shadow-pop ring-1 ring-blue"
					: held
						? "border-rail shadow-[0_16px_40px_rgba(1,30,65,0.12)] lg:-mt-3 lg:pb-7"
						: "border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)]",
				onSelect && !selected && "hover:-translate-y-0.5 hover:shadow-pop",
			)}
		>
			{held && (
				<span className="absolute -top-[11px] left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full bg-rail px-3 py-1 text-[9.5px] font-bold uppercase tracking-[0.1em] text-white">
					Current plan
				</span>
			)}

			{/* A fixed height and a clamped line, so the price panels line up across
			    the row. Three cards whose figures sit at three different heights are
			    three cards nobody can compare, and the society's own words for a
			    type are not a length this app can predict. */}
			<header className={cx("min-h-[58px]", held && "mt-1")}>
				<h3 className="text-[16px] font-semibold leading-snug tracking-tight text-ink">
					{row.membership_type_name || row.membership_type}
				</h3>
				{row.description && (
					<p className="mt-1 line-clamp-2 text-[12px] leading-relaxed text-slate-body">
						{row.description}
					</p>
				)}
			</header>

			<div className={cx("mt-4 rounded-xl bg-surface p-4", dense && "lg:p-3 xl:p-4")}>
				<div className="flex flex-wrap items-baseline gap-x-2">
					<span
						className={cx(
							"text-[27px] font-semibold leading-none tracking-tight text-ink",
							dense && "lg:text-[22px] xl:text-[27px]",
						)}
					>
						{amount}
					</span>
					{period && <span className="text-[12px] text-slate-body">{period}</span>}
				</div>


				<p className="mt-1.5 text-[11.5px] leading-relaxed text-slate-body">
					{row.is_lifetime
						? "Paid once. It does not expire."
						: row.duration_days
							? `Runs for ${row.duration_days} days, then renews.`
							: "Renewable."}{" "}
					{row.requires_approver
						? "Your branch approves it first."
						: "Active as soon as the fee is settled."}
				</p>

				{onSelect && (
					<span
						className={cx(
							"mt-4 inline-flex w-full items-center justify-center gap-1.5 rounded-lg px-4 py-2.5 text-[12.5px] font-bold transition",
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

				{action && <div className="mt-4">{action(row)}</div>}
			</div>

			{row.benefits.length > 0 && (
				<div className="mt-5">
					<p className="text-[9.5px] font-bold uppercase tracking-[0.1em] text-rail-label">
						Benefits
					</p>
					<ul className="mt-3 space-y-2.5">
						{row.benefits.slice(0, SHOWN_BENEFITS).map((benefit) => (
							<li key={benefit.key} className="flex gap-2.5">
								<span
									className="mt-[3px] grid h-3.5 w-3.5 flex-none place-items-center rounded-full bg-success-soft text-success"
									aria-hidden="true"
								>
									<Tick size={9} />
								</span>
								<span
									className="text-[12.5px] leading-snug text-ink"
									title={benefit.description ?? undefined}
								>
									{benefit.label}
								</span>
							</li>
						))}
					</ul>
					{row.benefits.length > SHOWN_BENEFITS && (
						<p className="mt-2.5 pl-6 text-[11.5px] text-muted">
							and {row.benefits.length - SHOWN_BENEFITS} more
						</p>
					)}
				</div>
			)}

			{footer && (
				<div className="mt-auto flex flex-wrap items-center gap-x-4 gap-y-1.5 pt-5">
					{footer(row)}
				</div>
			)}
		{row.requires_age_requirement && <p className="mt-3 text-xs text-muted">Ages {row.lower_age_limit ?? 0}–{row.upper_age_limit ?? 0}, inclusive.</p>}
		</Wrapper>
	);
}

/**
 * How a type's price reads: the headline and its period.
 *
 * No monthly breakdown. A society sets one fee for one period, and a
 * "about Ksh 1 a month" line restated it in a unit nobody is charged in.
 *
 * Exported because the membership tab's details panel says the same thing, and
 * two screens quoting one fee must not arrive at two figures.
 */
export function planPrice(plan: PricedType): {
	amount: string;
	period: string;
} {
	return {
		amount: plan.free ? "Free" : formatMoney(plan.amount, plan.currency),
		period: plan.is_lifetime ? "once" : plan.billing_cycle === "Yearly" ? "a year" : plan.billing_cycle === "Monthly" ? "a month" : periodLabel(plan.duration_days),
	};
}

/**
 * "a year" where a duration is one, "every 90 days" where it is not.
 *
 * A society sets `duration_days` and nothing constrains it to a year, so the
 * common case is named and everything else is stated in the unit the record
 * actually holds. No calendar arithmetic: 365 is the only number worth a word.
 */
function periodLabel(days: number): string {
	if (days === 365 || days === 366) return "a year";
	if (days === 30 || days === 31) return "a month";
	return days ? `every ${days} days` : "";
}
