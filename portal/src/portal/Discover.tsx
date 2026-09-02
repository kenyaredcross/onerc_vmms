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

/**
 * Training — half built, and the halves are worth separating.
 *
 * Deployments moved to its own file (`portal/Deployments.tsx`) in the Phase 2
 * rebuild; what is left here is the training link-out.
 */

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
															? "grid h-9 w-9 flex-none place-items-center rounded-lg bg-blue/[.08] text-blue-press"
															: "grid h-9 w-9 flex-none place-items-center rounded-lg bg-tint-teal-soft text-tint-teal"
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
													<span className="inline-flex items-center gap-1.5 rounded-full border border-blue/40 bg-blue/[.06] px-2.5 py-1 text-[11px] font-bold text-blue-press">
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
