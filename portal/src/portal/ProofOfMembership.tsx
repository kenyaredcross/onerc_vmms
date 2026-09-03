import { useContext, useMemo, useState } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage } from "../lib/api";
import { formatMoney } from "../lib/format";
import { Field, PrivateUpload, TextInput } from "../ui/form";
import { GeoSelects, selectedNode } from "../ui/GeoSelects";
import type { Declaration, GeoNode, PricedType, RedProfile } from "./types";
import { Button, ErrorNote, Notice, cx } from "./ui/kit";

/**
 * Asking the society to recognise a membership somebody already holds.
 *
 * **The third door, and the only one that starts from a document.** Joining is
 * the wizard; renewing is a button on a card. This is the person who paid at a
 * branch counter in 2019, holds a card or a receipt, and has an account here for
 * the first time. `register_existing_membership` has existed on the server since
 * the feature was specified — with the claimed fields, the proof, the
 * declarations and the reviewer's separate verified half — and nothing anywhere
 * called it. A person in that position had no way through the portal at all.
 *
 * **Everything they type is a claim, and the form says so.** None of these
 * fields decides anything: `proof.assert_verified` refuses the approval until
 * somebody at the society has read the evidence and recorded the dates
 * themselves, and `membership.activate` reads only what the reviewer recorded.
 * So the copy here is careful never to imply that filling this in makes somebody
 * a member — it asks the society to check, which is what it does.
 *
 * **Identity is shown, never asked.** The endpoint takes no name, no phone and
 * no date of birth: the caller is signed in and already known, and a form that
 * collected identity here would be a second place to correct it. The block at
 * the top is read from `my_profile` and is not editable; correcting it is the
 * profile page's job.
 *
 * **Expiry follows the plan, not a preference.** A lifetime type has no expiry
 * to claim and the field is not drawn; a term type has one and it is required,
 * because a claimed period with no end is a claim the reviewer cannot check.
 */
export function ProofOfMembership({
	plan,
	profile,
	declarations,
	onDone,
	onCancel,
}: {
	plan: PricedType;
	profile: RedProfile | null;
	/** `member.membership_types().declarations` — the society's own wording. */
	declarations: Declaration[];
	onDone: () => void;
	onCancel: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const levels = useFrappeGetCall<{ message: { levels: string[]; unconstrained: boolean } }>(
		API.memberGeoLevels,
		undefined,
		"proof:member_geo_levels",
	);

	const [chain, setChain] = useState<GeoNode[]>([]);
	const [startDate, setStartDate] = useState("");
	const [expiryDate, setExpiryDate] = useState("");
	const [membershipNumber, setMembershipNumber] = useState("");
	const [registeredAt, setRegisteredAt] = useState("");
	const [reference, setReference] = useState("");
	const [attachment, setAttachment] = useState("");
	const [accepted, setAccepted] = useState<string[]>([]);

	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const allowedLevels =
		levels.data?.message && !levels.data.message.unconstrained
			? levels.data.message.levels
			: undefined;

	const node = selectedNode(chain, allowedLevels);

	// A term membership that expired before it started is not a period anybody
	// can verify. Checked here so the sentence names the problem, rather than at
	// the server where it would arrive as a refused submission.
	const periodIsBackwards = Boolean(
		!plan.is_lifetime && startDate && expiryDate && expiryDate < startDate,
	);

	const outstanding = useMemo(
		() => declarations.filter((row) => row.is_required && !accepted.includes(row.name)),
		[declarations, accepted],
	);

	const ready =
		Boolean(node) &&
		Boolean(startDate) &&
		Boolean(attachment) &&
		(plan.is_lifetime || Boolean(expiryDate)) &&
		!periodIsBackwards &&
		outstanding.length === 0;

	const submit = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.registerExistingMembership, {
				membership_type: plan.membership_type,
				geo_node: node?.name,
				proof_attachment: attachment,
				proof_claimed_start_date: startDate,
				// Never sent for a lifetime plan. The field is not drawn, so any
				// value in it would be one left behind by somebody who changed
				// their mind about which plan they were claiming.
				proof_claimed_expiry_date: plan.is_lifetime ? undefined : expiryDate || undefined,
				proof_membership_number: membershipNumber.trim() || undefined,
				proof_registered_at: registeredAt.trim() || undefined,
				proof_reference_number: reference.trim() || undefined,
				declarations_accepted: accepted,
			});
			onDone();
		} catch (problem) {
			setFailure(errorMessage(problem, "That could not be sent. Try again in a moment."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<div className="space-y-6">
			{failure && <ErrorNote>{failure}</ErrorNote>}

			<Notice>
				<strong className="font-semibold text-ink">Nothing is charged here.</strong> Someone at your
				branch reads what you upload and records the dates themselves. Your membership starts
				counting from what they confirm, not from what is typed below.
			</Notice>

			{/* ------------------------------------------------------------ who */}
			<section>
				<h3 className="text-[13px] font-bold text-ink">Your details</h3>
				<p className="mt-1 text-[11.5px] leading-relaxed text-slate-body">
					From your account. Change these on your profile if anything is wrong.
				</p>

				<dl className="mt-3 grid gap-x-6 gap-y-2.5 rounded-xl bg-surface px-4 py-3.5 sm:grid-cols-2">
					<Held label="Name" value={profile?.full_name} />
					<Held label="Email" value={profile?.email} />
					<Held label="Phone" value={profile?.phone} />
				</dl>
			</section>

			{/* ----------------------------------------------------------- plan */}
			<section>
				<h3 className="text-[13px] font-bold text-ink">The membership you are claiming</h3>

				<dl className="mt-3 grid gap-x-6 gap-y-2.5 rounded-xl bg-surface px-4 py-3.5 sm:grid-cols-2">
					<Held label="Membership" value={plan.membership_type_name} />
					<Held
						label="Runs for"
						value={plan.is_lifetime ? "Lifetime" : plan.duration_days ? `${plan.duration_days} days` : "Not available"}
					/>
					<Held
						label="Fee"
						value={plan.free ? "Free" : formatMoney(plan.amount, plan.currency)}
					/>
				</dl>

				<p className="mt-2 text-[11px] text-muted">
					To claim a different one, go back and choose it from the list.
				</p>
			</section>

			{/* --------------------------------------------------------- branch */}
			<section>
				<h3 className="text-[13px] font-bold text-ink">Where you joined</h3>
				<p className="mt-1 text-[11.5px] leading-relaxed text-slate-body">
					The branch that will check this. Choose the one you registered with if it is still here.
				</p>

				<div className="mt-3">
					<GeoSelects
						chain={chain}
						onChain={setChain}
						allowedLevels={allowedLevels}
						idPrefix="proof"
					/>
				</div>
			</section>

			{/* ---------------------------------------------------- the history */}
			<section>
				<h3 className="text-[13px] font-bold text-ink">What the document says</h3>
				<p className="mt-1 text-[11.5px] leading-relaxed text-slate-body">
					Copy these from the card, certificate or receipt you are about to upload.
				</p>

				<div className="mt-3 grid gap-5 sm:grid-cols-2">
					<Field
						label="When you originally joined"
						required
						htmlFor="proof-start"
						hint="The date on the document, not the date you paid."
					>
						<TextInput
							id="proof-start"
							type="date"
							value={startDate}
							max={new Date().toISOString().slice(0, 10)}
							onChange={setStartDate}
						/>
					</Field>

					{/* A lifetime membership has no expiry to claim, and drawing the
					    field would invite somebody to invent one. `valid_to` stays
					    empty on it by design — see the membership service. */}
					{!plan.is_lifetime && (
						<Field
							label="When it runs out"
							required
							htmlFor="proof-expiry"
							hint={
								periodIsBackwards
									? "This is before the date you joined. Check both dates."
									: "As printed on the document."
							}
						>
							<TextInput
								id="proof-expiry"
								type="date"
								value={expiryDate}
								min={startDate || undefined}
								onChange={setExpiryDate}
							/>
						</Field>
					)}

					<Field label="Membership number" htmlFor="proof-number" hint="If it has one.">
						<TextInput
							id="proof-number"
							value={membershipNumber}
							onChange={setMembershipNumber}
							placeholder="Optional"
						/>
					</Field>

					<Field
						label="Where you registered"
						htmlFor="proof-where"
						hint="The branch or office named on the document."
					>
						<TextInput
							id="proof-where"
							value={registeredAt}
							onChange={setRegisteredAt}
							placeholder="Optional"
						/>
					</Field>

					<Field
						label="Certificate or receipt number"
						htmlFor="proof-reference"
						className="sm:col-span-2"
						hint="If the document carries one. It helps your branch find the original record."
					>
						<TextInput
							id="proof-reference"
							value={reference}
							onChange={setReference}
							placeholder="Optional"
						/>
					</Field>
				</div>
			</section>

			{/* ---------------------------------------------------------- proof */}
			<section>
				<h3 className="text-[13px] font-bold text-ink">The document itself</h3>
				<p className="mt-1 text-[11.5px] leading-relaxed text-slate-body">
					Upload a photograph of the receipt, certificate, or membership card. Only your branch
					can access it.
				</p>

				<div className="mt-3">
					<Field label="Proof of your membership" required htmlFor="proof-file">
						<PrivateUpload
							id="proof-file"
							value={attachment}
							onChange={setAttachment}
							choose="Choose the document"
							replace="Replace the document"
						/>
					</Field>
				</div>
			</section>

			{/* --------------------------------------------------- declarations */}
			{declarations.length > 0 && (
				<section>
					<h3 className="text-[13px] font-bold text-ink">What you are confirming</h3>

					<div className="mt-3 space-y-2.5">
						{declarations.map((declaration) => (
							<label
								key={declaration.name}
								htmlFor={`proof-dec-${declaration.name}`}
								className="flex cursor-pointer items-start gap-3 rounded-xl border border-card-line bg-white p-4"
							>
								<input
									id={`proof-dec-${declaration.name}`}
									type="checkbox"
									className="mt-0.5 h-4 w-4 shrink-0 accent-blue"
									checked={accepted.includes(declaration.name)}
									onChange={(event) =>
										setAccepted(
											event.target.checked
												? [...accepted, declaration.name]
												: accepted.filter((key) => key !== declaration.name),
										)
									}
								/>
								<span className="min-w-0">
									<span className="block text-[12.5px] font-semibold leading-snug text-ink">
										{declaration.title}
										{declaration.is_required && <span className="ml-1 text-red">*</span>}
									</span>
									{declaration.body && (
										<span
											className="mt-1.5 block text-[11.5px] leading-relaxed text-slate-body [&_p]:mb-1.5"
											// The society's own wording, stored as a Text Editor
											// field and rendered as written. What is recorded on
											// the membership is this exact text at this exact
											// version — see `registration/services/declarations.py`.
											dangerouslySetInnerHTML={{ __html: declaration.body }}
										/>
									)}
									{declaration.external_url && (
										<a
											href={declaration.external_url}
											target="_blank"
											rel="noreferrer"
											className="mt-1.5 inline-block text-[11.5px] font-semibold text-blue underline-offset-2 hover:underline"
										>
											Read it in full
										</a>
									)}
								</span>
							</label>
						))}
					</div>
				</section>
			)}

			<div className="flex flex-wrap items-center justify-end gap-2 border-t border-card-line pt-4">
				<Button tone="quiet" onClick={onCancel} disabled={busy}>
					Cancel
				</Button>
				<Button onClick={() => void submit()} disabled={!ready || busy}>
					{busy ? "Sending…" : "Send this to my branch"}
				</Button>
			</div>
		</div>
	);
}

/** One fact the account already knows, shown rather than asked. */
function Held({ label, value }: { label: string; value?: string | null }) {
	return (
		<div className="min-w-0">
			<dt className="text-[10px] font-bold uppercase tracking-[0.1em] text-muted">{label}</dt>
			<dd className={cx("mt-0.5 truncate text-[12.5px] font-semibold", value ? "text-ink" : "text-muted")}>
				{value || "Not on file"}
			</dd>
		</div>
	);
}
