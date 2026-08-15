import { useState } from "react";
import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate } from "../lib/format";
import type { EventCard } from "../portal/types";
import {
	ButtonLink,
	Card,
	Empty,
	ErrorNote,
	PageHeading,
	Pill,
	SectionTitle,
	Spinner,
	Stat,
	cx,
} from "../ui/primitives";

/**
 * The events console — what the society has published, and where it is run from.
 *
 * **This screen browses; Buzz manages.** Every event here is a `Buzz Event`,
 * read through `vmmsx/buzz/services/events.py`, and the boundary is Buzz's own
 * `is_published`. vmmsx invents no second notion of visibility and no approval
 * step of its own. Registration, ticket types, coupons, payment, guest
 * verification and check-in are all Buzz's, each a flow with money or identity
 * in it, so every call to action on this page is a full navigation to Buzz's
 * page for that event rather than a vmmsx endpoint wrapping one of them. There
 * is deliberately no booking or check-in method to call.
 *
 * That is the whole of what this screen claims. The design's pipeline, roster
 * and check-in panels are not drawn here even as empty shells, and the note at
 * the foot of the page says where they actually live — a screen that reads as
 * though everything works is worse than none. It is deliberately *not* a
 * `NotBuilt`: that component states nothing on the page is real data, which
 * would be false here, and "another app owns this" is a different sentence from
 * "nobody built this".
 *
 * **Buzz absent is an ordinary state, not an error.** vmmsx does not declare
 * `buzz` in `required_apps`, so the seam answers `available: false` on a site
 * without it and this screen says that plainly instead of spinning forever.
 */
export default function AdminEvents() {
	const [category, setCategory] = useState("");

	const { data, error, isLoading } = useFrappeGetCall<{
		message: { available: boolean; events: EventCard[] };
	}>(API.eventsUpcoming, category ? { category, limit: 60 } : { limit: 60 }, `admin:events:${category}`);

	const filters = useFrappeGetCall<{
		message: {
			available: boolean;
			categories: Array<{ category: string; label: string; description: string }>;
		};
	}>(API.eventFilters, undefined, "admin:event_filters");

	const answer = data?.message;
	const events = answer?.events ?? [];

	// Counted from the rows already fetched rather than by a second query, so the
	// figures and the list can never disagree.
	const today = new Date().toISOString().slice(0, 10);
	const runningNow = events.filter(
		(event) => event.start_date <= today && event.end_date >= today,
	).length;

	const categories = filters.data?.message?.categories ?? [];

	return (
		<>
			<PageHeading title={<EditableText k="admin.nav.events" fallback="Events" />} />

			{isLoading && <Spinner label="Loading events…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{answer && !answer.available && (
				<Empty title="Events are not available on this site">
					The events listing has not been set up here yet, so there is nothing to show. The
					events named on the public landing page are wording you can edit under Page content.
				</Empty>
			)}

			{answer?.available && (
				<>
					<div className="mb-6 grid gap-4 sm:grid-cols-3">
						<Card>
							<Stat value={events.length} label="Published and upcoming" />
						</Card>
						<Card>
							<Stat value={runningNow} label="Running today" />
						</Card>
						<Card>
							<Stat value={categories.length || "—"} label="Categories" />
						</Card>
					</div>

					{categories.length > 0 && (
						<div className="mb-4 flex flex-wrap gap-2">
							{[{ category: "", label: "All" }, ...categories].map((option) => (
								<button
									key={option.category || "all"}
									type="button"
									onClick={() => setCategory(option.category)}
									className={cx(
										"rounded-full border px-3.5 py-1.5 text-[12px] font-semibold transition",
										category === option.category
											? "border-navy bg-navy text-white"
											: "border-hairline-strong bg-white text-slate-body hover:border-navy hover:text-navy",
									)}
								>
									{option.label}
								</button>
							))}
						</div>
					)}

					{events.length === 0 ? (
						<Empty title="Nothing published">
							No published event is still to come. An event appears here once it is published
							in Buzz — publishing is Buzz's decision, and this screen shows what that
							decision produced rather than holding a second flag of its own.
						</Empty>
					) : (
						<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
							{events.map((event) => (
								<EventTile key={event.event} event={event} />
							))}
						</div>
					)}
				</>
			)}

			{/*
			 * Not a `NotBuilt`, deliberately. That component says "nothing on this
			 * page is real data", which would be a lie here: the listing above is
			 * live. Rosters and check-in are not missing from this app — they are
			 * another app's records, which is a different sentence and gets its own.
			 */}
			<div className="mt-8 rounded-panel border border-hairline bg-white px-6 py-5">
				<SectionTitle>Rosters, RSVPs and check-in are managed in Buzz</SectionTitle>
				<p className="max-w-2xl text-[12.5px] leading-relaxed text-slate-body">
					Buzz owns registration, ticket types, coupons, payment, guest verification and
					check-in. vmmsx deliberately does not re-implement any of them: a second copy of a
					booking rule would have to stay in step with Buzz's forever, and the first time the
					two disagreed somebody would be charged the wrong amount. Every card above links to
					that event's own Buzz page, which is where its attendees are managed.
				</p>
			</div>
		</>
	);
}

/** One published event, and the one thing this app does with it: send you to Buzz. */
function EventTile({ event }: { event: EventCard }) {
	return (
		<Card>
			<div className="flex items-start justify-between gap-2">
				<SectionTitle>{event.title}</SectionTitle>
				{event.category && <Pill tone="page">{event.category}</Pill>}
			</div>

			<p className="text-[12px] text-slate-body">
				{event.start_date ? formatDate(event.start_date) : "No date"}
				{event.multi_day && event.end_date ? ` → ${formatDate(event.end_date)}` : ""}
				{event.start_time ? ` · ${event.start_time.slice(0, 5)}` : ""}
			</p>

			{event.venue && <p className="mt-0.5 text-[12px] text-slate-faint">{event.venue}</p>}

			{event.summary && (
				<p className="mt-2 line-clamp-3 text-[12.5px] text-slate-body">{event.summary}</p>
			)}

			{event.href && (
				<div className="mt-3">
					<ButtonLink to={event.href}>Manage in Buzz</ButtonLink>
				</div>
			)}
		</Card>
	);
}
