import { useCallback, useMemo, useState } from "react";
import { useFrappeGetCall, useFrappePostCall } from "frappe-react-sdk";

import { API } from "../lib/api";
import type { EventCard } from "./types";

/**
 * Whether the reader is going, and the one control that changes it.
 *
 * **A hook rather than a component, because three screens ask the same question
 * in three shapes.** The events page needs the list *and* the set, the calendar
 * needs only the set, and a card needs only the verb. What they must not have
 * is three notions of what "attending" means, which is what a copy of this
 * logic in each of them would produce.
 *
 * **It is an intention, not a ticket, and the wording everywhere it is used has
 * to keep saying so.** `vmmsx/events/services/attendance.py` sets the line out:
 * the events app owns registration, payment and check-in, this app owns the
 * society's own record that somebody said they mean to be there. A button here
 * may say "I'm going"; it may never say a place is held.
 *
 * The write is optimistic and then re-read. Pressing it is a person answering a
 * question they already know the answer to, so making them watch a round trip
 * before the tick appears is making them wait for their own decision. The
 * revalidate behind it is what keeps the optimism honest: if the server refused
 * — an event unpublished between the page loading and the press — the answer
 * comes back the way it really is.
 */
export function useAttendance(includeFinished = false) {
	const key = `portal:attending:${includeFinished}`;

	const { data, error, isLoading, mutate } = useFrappeGetCall<{
		message: { available: boolean; answered: string[]; events: EventCard[] };
	}>(API.eventsAttending, { include_finished: includeFinished ? 1 : 0 }, key);

	const attend = useFrappePostCall(API.attendEvent);
	const cancel = useFrappePostCall(API.cancelEventAttendance);

	// Which event is mid-flight, so its own control can show it and every other
	// control on the page stays live. A single boolean would freeze the whole
	// list while one card was saving.
	const [pending, setPending] = useState<string | null>(null);

	const answered = useMemo(
		() => new Set(data?.message?.answered ?? []),
		[data?.message?.answered],
	);

	const toggle = useCallback(
		async (event: string) => {
			if (!event || pending) return;

			const going = answered.has(event);
			setPending(event);

			// The optimistic half. `revalidate: false` so this does not race the
			// real answer being fetched a few lines below.
			const next = new Set(answered);
			if (going) next.delete(event);
			else next.add(event);

			await mutate(
				(current) =>
					current && {
						message: {
							...current.message,
							answered: Array.from(next),
						},
					},
				{ revalidate: false },
			);

			try {
				if (going) await cancel.call({ event });
				else await attend.call({ event });
			} finally {
				// Unconditional, and that is the point: a refusal has to put the
				// button back where it was, and only the server knows where that
				// is. The cards themselves arrive with it, so an event somebody
				// has just said yes to appears in the attending list without a
				// second request.
				await mutate();
				setPending(null);
			}
		},
		[answered, attend, cancel, mutate, pending],
	);

	return {
		/** The reader's own events, as cards, soonest first. */
		events: data?.message?.events ?? [],
		/** Every identifier they have answered for, including any since unpublished. */
		answered,
		available: data?.message?.available ?? true,
		isLoading,
		error,
		pending,
		toggle,
		mutate,
	};
}
