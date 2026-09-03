import { useState } from "react";
import { useFrappeGetCall } from "frappe-react-sdk";

import { API } from "../../lib/api";
import type { MyAvailability } from "../types";
import { Button } from "../ui/kit";
import { Modal } from "../ui/overlays";
import { AvailabilityEditor } from "./AvailabilityEditor";

/**
 * The dashboard's prompt to set availability, for somebody who has not.
 *
 * It renders nothing once availability exists, and nothing for a person with
 * no volunteer record. The editor it opens is the same one the header control
 * and the `/availability` page use.
 */
export function AvailabilityNudge() {
	const [open, setOpen] = useState(false);
	const { data, mutate } = useFrappeGetCall<{ message: MyAvailability | null }>(
		API.myAvailability,
		undefined,
		"portal:my_availability",
	);

	const answer = data?.message ?? null;
	if (!answer || answer.exists) return null;

	return (
		<>
			<div className="rounded-xl border border-card-line bg-[#F4F7FB] p-4">
				<h3 className="text-[13px] font-semibold text-ink">Set your usual availability</h3>
				<p className="mt-1 text-[12px] leading-relaxed text-muted">
					Coordinators use it when choosing people for a deployment. It is not a commitment.
				</p>
				<Button tone="soft" onClick={() => setOpen(true)} className="mt-3">
					Set availability
				</Button>
			</div>

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
