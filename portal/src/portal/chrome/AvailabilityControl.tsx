import { useState } from "react";
import { useFrappeGetCall } from "frappe-react-sdk";

import { API } from "../../lib/api";
import { Icon } from "../../ui/icons";
import type { MyAvailability } from "../types";
import { Modal } from "../ui/overlays";
import { AvailabilityEditor } from "./AvailabilityEditor";

/**
 * The header's availability control — a button and the modal behind it.
 *
 * **Availability is not a page in this portal.** It is a weekly pattern a
 * coordinator reads when choosing people for a deployment, edited from wherever
 * you are rather than from a screen you navigate to. The `/availability` route
 * still resolves for a link somebody is sent, and renders the same editor.
 *
 * The button is drawn only for somebody with a volunteer record — a member who
 * does not volunteer has no availability to set, and `my_availability` answers
 * `null` for them. The SWR key is shared with the `/availability` page, so
 * opening one after the other costs no request.
 */
export function AvailabilityControl() {
	const [open, setOpen] = useState(false);

	const { data, mutate } = useFrappeGetCall<{ message: MyAvailability | null }>(
		API.myAvailability,
		undefined,
		"portal:my_availability",
	);

	const answer = data?.message ?? null;
	if (!answer) return null;

	const days = new Set(answer.days.map((row) => row.day)).size;
	const label = !answer.exists
		? "Availability not set"
		: days === 0
			? "No days set"
			: `Available ${days} ${days === 1 ? "day" : "days"}`;

	return (
		<>
			<button
				type="button"
				onClick={() => setOpen(true)}
				className="hidden h-8 items-center gap-2 rounded-lg border border-rail-line bg-white px-2.5 text-[12.5px] font-medium text-slate-strong transition hover:border-slate-faint hover:text-ink sm:flex"
			>
				<Icon.clock size={14} className="flex-none text-slate-faint" />
				{label}
			</button>

			<Modal
				open={open}
				onClose={() => setOpen(false)}
				size="lg"
				title="Your usual availability"
				description="This is not a confirmed commitment. A coordinator will confirm availability."
				footer={
					<button
						type="button"
						onClick={() => setOpen(false)}
						className="rounded-lg border border-rail-line bg-white px-4 py-2 text-[13px] font-semibold text-slate-strong transition hover:border-slate-faint hover:text-ink"
					>
						Done
					</button>
				}
			>
				<AvailabilityEditor answer={answer} onSaved={() => void mutate()} compact />
			</Modal>
		</>
	);
}
