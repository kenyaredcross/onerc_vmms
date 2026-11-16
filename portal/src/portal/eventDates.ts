import { todayIso } from "../ui/MonthGrid";
import type { EventCard } from "./types";

/**
 * Is the event's last day behind us? The calendar shows past events, the old
 * site's among them, so the detail page they open must not offer to register
 * for one. `end_date` is already the day it actually ends (see `_as_card`), so
 * the ISO strings compare. The server refuses attending an ended event too.
 */
export function eventEnded(row: Pick<EventCard, "start_date" | "end_date">, today: string = todayIso()): boolean {
	const last = row.end_date || row.start_date;

	return !!last && last < today;
}
