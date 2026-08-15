import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate } from "../lib/format";
import { Icon } from "../ui/icons";
import {
	Card,
	Empty,
	ErrorNote,
	List,
	ListRow,
	NotBuilt,
	PageHeading,
	SectionLabel,
	Spinner,
} from "../ui/primitives";
import type { MyCertifications } from "./types";
import { Invitations } from "./Invitations";
import { MyDeployments } from "./Opportunities";

/**
 * The screens where the design runs ahead of the backend, and the one beside
 * them that does not.
 *
 * They are together in one file because they are the same shape: whatever this
 * app can genuinely answer, rendered from a real endpoint, followed by a plain
 * statement of what is missing and what would have to be built. None of them
 * fabricates a row.
 *
 * **Events and Opportunities are no longer among them.** Both have their own
 * files now and both read real records — Events out of Buzz, Opportunities out
 * of the deployment requests a society has chosen to advertise. What used to be
 * here in each case was a `NotBuilt`, true when it was written and not any more.
 */

/* ------------------------------------------------------------- deployments */

/**
 * What this volunteer has been deployed on, as the sidebar's own tab.
 *
 * The list itself lives in `Opportunities.tsx` and is rendered by both: the
 * board's second tab answers "what came of it" beside "what is open", and this
 * route is the same answer reached directly. One implementation, because two
 * would eventually disagree.
 */
export function Deployments() {
	return (
		<>
			<PageHeading
				title={<EditableText k="portal.deployments.heading" fallback="Deployments" />}
				trail={[{ label: "Home", to: "/dashboard" }, { label: "Deployments" }]}
			/>
			{/* What you are being asked to do, above what you have done. The same
			    subject a day apart, and an unanswered invitation is the only thing
			    on this screen that needs somebody to act. Renders nothing at all
			    when there are no invitations either way. */}
			<Invitations />
			<MyDeployments />
		</>
	);
}

/* ---------------------------------------------------------------- training */

/**
 * Training is half built, and the halves are worth separating.
 *
 * What a person *holds* is real and derived live. What a person could *enrol
 * in* is not: courses live in a separate learning app that vmmsx deliberately
 * does not depend on, reached only through the one-way seam in
 * `volunteer/services/learning.py` that turns a completed course into a
 * certification. There is no catalogue endpoint and no enrolment endpoint here.
 */
export function Training() {
	const { data, error, isLoading } = useFrappeGetCall<{ message: MyCertifications | null }>(
		API.myCertifications,
		undefined,
		"portal:my_certifications",
	);

	const training = data?.message ?? null;

	return (
		<>
			<PageHeading
				title={<EditableText k="portal.training.heading" fallback="Training" />}
				trail={[{ label: "Home", to: "/dashboard" }, { label: "Training" }]}
			/>

			{isLoading && <Spinner label="Loading training…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{training && (
				<section className="mb-8">
					<SectionLabel>What you hold</SectionLabel>

					{training.certifications.length === 0 ? (
						<Card>
							<Empty framed={false} title="No certifications recorded" icon={Icon.award}>
								A certification a coordinator records against your name, or one the learning app
								awards you, appears here.
							</Empty>
						</Card>
					) : (
						<Card pad={false}>
							<div className="p-2">
								<List>
									{training.certifications.map((row) => (
										<ListRow
											key={row.name}
											lead={
												<span
													className={
														row.lapsed
															? "grid h-9 w-9 flex-none place-items-center rounded-control bg-signal/[.08] text-signal-dark"
															: "grid h-9 w-9 flex-none place-items-center rounded-control bg-tint-teal-soft text-tint-teal"
													}
													aria-hidden="true"
												>
													<Icon.award size={17} />
												</span>
											}
											title={row.certification_type_name || row.certification_type}
											meta={
												row.expiry_date ? `Expires ${formatDate(row.expiry_date)}` : "No expiry"
											}
											trailing={
												row.lapsed ? (
													<span className="inline-flex items-center gap-1.5 rounded-full border border-signal/40 bg-signal/[.06] px-2.5 py-1 text-[11px] font-bold text-signal-dark">
														<span
															className="h-1.5 w-1.5 rounded-full bg-current"
															aria-hidden="true"
														/>
														Lapsed
													</span>
												) : (
													<span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-300 bg-emerald-50/60 px-2.5 py-1 text-[11px] font-bold text-emerald-700">
														<span
															className="h-1.5 w-1.5 rounded-full bg-current"
															aria-hidden="true"
														/>
														Current
													</span>
												)
											}
										/>
									))}
								</List>
							</div>
						</Card>
					)}
				</section>
			)}

			<NotBuilt
				what="Course browsing and enrolment"
				needs="Courses are not yet browsable here. Your training record and any certifications you have earned are on your profile, and stay up to date on their own."
			/>
		</>
	);
}
