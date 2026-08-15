import { useContext, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage, myCertificateUrl } from "../lib/api";
import { formatDate, formatMoney, geoPath } from "../lib/format";
import { HolderCard } from "./Profile";
import { PlanCards } from "../ui/PlanCards";
import { Icon } from "../ui/icons";
import {
	Button,
	Card,
	Empty,
	ErrorNote,
	PageHeading,
	Pill,
	SectionLabel,
	Spinner,
	StateBadge,
} from "../ui/primitives";
import type { MembershipRow, PricedType } from "./types";

/**
 * Every membership this person holds, and every one they could hold.
 *
 * **The buttons follow the server's own flags, never a state comparison here.**
 * `certificate_available` is answered by the same gate the download uses, and
 * `renewable` by the same predicate the renewal service uses. A screen that
 * decided for itself when to show "Renew" would eventually show it a moment
 * before or after the server would accept it, and the person clicking would get
 * a refusal they could not explain. So this file compares no dates and no
 * statuses.
 *
 * **The plans are here because this is where somebody looks for them.** The type
 * a person holds and the types a society offers are the same subject, and the
 * membership tab was previously a page that said "you do not hold a membership
 * yet" and left them to find the join wizard for themselves. The grid is the
 * same `PlanCards` the wizard's plan step draws, from the same endpoint, so the
 * price on this page can never disagree with the price on the one that charges
 * it.
 */
export default function Membership() {
	const navigate = useNavigate();

	const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: MembershipRow[] }>(
		API.myMemberships,
		undefined,
		"portal:my_memberships",
	);

	const types = useFrappeGetCall<{ message: { types: PricedType[] } }>(
		API.membershipTypes,
		undefined,
		"portal:membership_types",
	);

	const rows = data?.message ?? [];
	const priced = types.data?.message?.types ?? [];
	const held = rows.map((row) => row.membership_type);

	return (
		<>
			<PageHeading
				title={<EditableText k="portal.membership.heading" fallback="Membership" />}
				trail={[{ label: "Home", to: "/dashboard" }, { label: "Membership" }]}
			/>

			{isLoading && <Spinner label="Loading your membership…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{rows.length > 0 && (
				<section className="mb-10">
					<SectionLabel>
						<EditableText k="portal.membership.section.held" fallback="What you hold" />
					</SectionLabel>

					<div className="space-y-4">
						{rows.map((row) => (
							<MembershipCard key={row.name} row={row} onChanged={() => void mutate()} />
						))}

						{/* The card itself, drawn only for a membership that is active:
						    the endpoint returns nothing for one still under review, and
						    this renders nothing when it does. */}
						<HolderCard kind="member" />
					</div>
				</section>
			)}

			{!isLoading && rows.length === 0 && (
				<div className="mb-10">
					<Empty
						icon={Icon.card}
						title={
							<EditableText
								k="portal.membership.empty"
								fallback="You do not hold a membership yet."
							/>
						}
					>
						Joining as a member is separate from volunteering, and you may do both. Choose a plan
						below to start.
					</Empty>
				</div>
			)}

			<section>
				<div className="mb-6 text-center">
					<p className="eyebrow">
						<EditableText k="portal.membership.plans.eyebrow" fallback="Membership types" />
					</p>
					<h2 className="mt-2 font-display text-[26px] font-extrabold tracking-tight text-ink">
						<EditableText
							k="portal.membership.plans.heading"
							fallback="Choose a plan to become a member"
						/>
					</h2>
					<p className="mx-auto mt-2.5 max-w-xl text-[13.5px] leading-relaxed text-slate-body">
						<EditableText
							k="portal.membership.plans.blurb"
							fallback="Every fee, benefit and eligibility note here is set by your society on the membership type itself."
						/>
					</p>
				</div>

				<PlanCards
					types={priced}
					loading={types.isLoading}
					held={held}
					actionLabel="Select plan"
					// Choosing here is choosing to *start* the registration, not to
					// register: the wizard still asks for a branch and still confirms
					// before anything is written. The type travels in the URL so the
					// plan step opens with it already selected.
					onSelect={(membershipType) =>
						navigate(`/join?path=member&type=${encodeURIComponent(membershipType)}`)
					}
					empty="Your society has not published any membership types yet. Ask your branch when they will be available."
				/>

				{types.error && (
					<div className="mt-4">
						<ErrorNote>{errorMessage(types.error)}</ErrorNote>
					</div>
				)}
			</section>
		</>
	);
}

function MembershipCard({ row, onChanged }: { row: MembershipRow; onChanged: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const renew = async () => {
		setBusy(true);
		setFailure(null);
		try {
			await call.post(API.renewMembership, { membership: row.name });
			onChanged();
		} catch (renewError) {
			setFailure(errorMessage(renewError, "That membership could not be renewed."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Card>
			<div className="flex flex-wrap items-start justify-between gap-4">
				<div className="flex min-w-0 items-center gap-4">
					<span
						className="grid h-12 w-12 flex-none place-items-center rounded-control bg-tint-violet-soft text-tint-violet"
						aria-hidden="true"
					>
						<Icon.card size={22} />
					</span>

					<div className="min-w-0">
						<div className="flex flex-wrap items-center gap-2.5">
							<h3 className="font-display text-[18px] font-extrabold tracking-tight text-ink">
								{row.membership_type_name || row.membership_type}
							</h3>
							<StateBadge state={row.membership_status} />
							{row.is_lifetime && <Pill tone="page">Lifetime</Pill>}
						</div>
						<p className="mt-1 text-[12.5px] text-slate-body">{geoPath(row.geo_path)}</p>
					</div>
				</div>

				<div className="flex flex-wrap items-center gap-2">
					{row.certificate_available && (
						<a
							href={myCertificateUrl(row.name)}
							className="inline-flex items-center gap-2 rounded-full border border-hairline-strong bg-white px-5 py-2.5 font-display text-[13px] font-bold text-slate-strong transition hover:border-navy hover:text-navy"
						>
							<Icon.award size={15} />
							Download certificate
						</a>
					)}
					{row.renewable && (
						<Button onClick={renew} disabled={busy}>
							{busy ? "Renewing…" : "Renew"}
						</Button>
					)}
				</div>
			</div>

			{failure && (
				<div className="mt-4">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			<dl className="mt-6 grid gap-5 border-t border-hairline-soft pt-5 sm:grid-cols-2 lg:grid-cols-4">
				<Field label="Valid from" value={formatDate(row.valid_from)} />
				<Field label="Valid to" value={row.is_lifetime ? "No expiry" : formatDate(row.valid_to)} />
				{/* The society's own currency travels with the amount, so a free type
				    reads "Free" rather than a bare zero in nobody's currency. */}
				<Field
					label="Fee"
					value={
						!row.fee || row.fee.amount === 0
							? "Free"
							: formatMoney(row.fee.amount, row.fee.currency)
					}
				/>
				<Field label="Membership ID" value={row.name} mono />
			</dl>

			{/* The two halves of activation, shown as they are: a person whose
			    payment cleared but whose approval has not is entitled to know
			    which of the two they are waiting on. */}
			<div className="mt-5 flex flex-wrap gap-2 border-t border-hairline-soft pt-5">
				<Progress done={row.payment_settled} label="Payment" />
				<Progress
					done={row.approval_settled}
					label={row.requires_approver ? "Approval" : "Approval not required"}
				/>
				{row.payment_receipt && <Pill tone="page">Receipt {row.payment_receipt}</Pill>}
			</div>
		</Card>
	);
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
	return (
		<div>
			<dt className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">{label}</dt>
			<dd
				className={
					mono
						? "mt-1.5 font-mono text-[12px] text-ink"
						: "mt-1.5 text-[13px] font-medium text-ink"
				}
			>
				{value}
			</dd>
		</div>
	);
}

function Progress({ done, label }: { done: boolean; label: string }) {
	return (
		<span
			className={
				done
					? "inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-[11.5px] font-semibold text-emerald-700"
					: "inline-flex items-center gap-1.5 rounded-full border border-hairline-strong bg-white px-3 py-1.5 text-[11.5px] font-semibold text-slate-body"
			}
		>
			<span
				className={done ? "h-1.5 w-1.5 rounded-full bg-emerald-500" : "h-1.5 w-1.5 rounded-full bg-slate-faint"}
				aria-hidden="true"
			/>
			{label}
			{done ? " settled" : " pending"}
		</span>
	);
}
