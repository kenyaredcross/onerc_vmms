import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { AvailabilityEditor } from "./chrome/AvailabilityEditor";
import { Card, Empty, ErrorNote, PageHead, Spinner } from "./ui/kit";
import type { MyAvailability } from "./types";

/**
 * The `/availability` page.
 *
 * Availability is edited from the header in this portal — see
 * `chrome/AvailabilityControl`. This route stays because a coordinator asking
 * somebody to fill it in wants a link to send, and "open the availability
 * button in your header" is a worse sentence than an address. It renders the
 * same editor the modal does.
 */
export function Availability() {
	const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: MyAvailability | null }>(
		API.myAvailability,
		undefined,
		"portal:my_availability",
	);

	const answer = data?.message ?? null;

	return (
		<>
			<PageHead
				eyebrow="Your record"
				title={<EditableText k="portal.availability.heading" fallback="When you can serve" />}
				lead="Tell your branch which days and windows you can usually be asked about. It is a pattern, not a promise."
			/>

			{isLoading && <Spinner label="Loading your availability…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{data && !answer && (
				<Empty title="You do not have a volunteer record yet">
					Availability is something a volunteer sets. Once your application has been accepted, this is
					where you say which days and hours you can be asked about.
				</Empty>
			)}

			{answer && (
				<Card>
					<AvailabilityEditor answer={answer} onSaved={() => void mutate()} />
				</Card>
			)}
		</>
	);
}
