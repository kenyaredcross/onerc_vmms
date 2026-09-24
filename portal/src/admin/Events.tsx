import { useContext, useState } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate } from "../lib/format";
import type { EventAttendee, EventCard } from "../portal/types";
import type { GeoNode } from "../portal/types";
import { GeoSelects, selectedNode } from "../ui/GeoSelects";
import {
	Button,
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
 * Every event here is a Buzz Event. People with Buzz create permission can
 * fill in its details here; Buzz validates and stores the document. Publishing
 * uses Buzz's own `is_published` flag. Registration, ticket types, coupons,
 * payment and check-in stay in Buzz. Booking links open Buzz's registration
 * form, and the roster below reads only confirmed tickets from Buzz.
 *
 * Registration names are available to Buzz event managers; the separate
 * VMMS attendance response remains a planning signal and is labelled as such.
 *
 * **Buzz absent is an ordinary state, not an error.** vmmsx does not declare
 * `buzz` in `required_apps`, so the seam answers `available: false` on a site
 * without it and this screen says that plainly instead of spinning forever.
 */
export default function AdminEvents() {
	const [category, setCategory] = useState("");
	const [creating, setCreating] = useState(false);
	const [created, setCreated] = useState<string | null>(null);

	const { data, error, isLoading, mutate } = useFrappeGetCall<{
		message: { available: boolean; events: EventCard[] };
	}>(API.eventsUpcoming, category ? { category, limit: 60 } : { limit: 60 }, `admin:events:${category}`);

	const filters = useFrappeGetCall<{
		message: {
			available: boolean;
			categories: Array<{ category: string; label: string; description: string }>;
		};
	}>(API.eventFilters, undefined, "admin:event_filters");
	const management = useFrappeGetCall<{
		message: { available: boolean; can_create: boolean; categories: string[]; hosts: string[]; venues: string[] };
	}>(API.eventManagementOptions, undefined, "admin:event_management_options");
	const managed = useFrappeGetCall<{
		message: { events: Array<{ name: string; title: string; start_date: string; is_published: boolean }> };
	}>(API.managedEvents, undefined, "admin:managed_events");

	const answer = data?.message;
	const events = answer?.events ?? [];

	// Counted from the rows already fetched rather than by a second query, so the
	// figures and the list can never disagree.
	const today = new Date().toISOString().slice(0, 10);
	const runningNow = events.filter(
		(event) => event.start_date <= today && event.end_date >= today,
	).length;

	const categories = filters.data?.message?.categories ?? [];
	const drafts = managed.data?.message?.events.filter((event) => !event.is_published) ?? [];

	// Everybody who told the society they mean to be at one of these, summed from
	// the rows already fetched rather than by a second query — so the figure and
	// the cards under it can never disagree. It is *not* a booking total: Buzz
	// owns those and they are a different number. See `attendance.counts`.
	const saidTheyAreComing = events.reduce((total, event) => total + (event.going ?? 0), 0);

	return (
		<>
			<PageHeading title={<EditableText k="admin.nav.events" fallback="Events" />} />
			{management.data?.message?.can_create && (
				<div className="mb-5 flex flex-wrap items-center justify-between gap-3">
					<p className="text-[12.5px] text-muted">Create and publish events from this portal.</p>
					<Button onClick={() => setCreating((open) => !open)}>{creating ? "Close form" : "New event"}</Button>
				</div>
			)}
			{created && <div className="mb-5 rounded-xl bg-success-soft px-4 py-3 text-[12.5px] text-success">Event {created} was created. <a href={`/app/buzz-event/${encodeURIComponent(created)}`} className="font-semibold underline">Open its Desk record</a></div>}
			{creating && management.data?.message?.can_create && (
				<div className="mb-6">
					<EventForm
						options={management.data.message}
						onCreated={(name) => {
							setCreated(name);
							setCreating(false);
							void mutate();
							void managed.mutate();
						}}
					/>
				</div>
			)}

			{isLoading && <Spinner label="Loading events…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{answer && !answer.available && (
				<Empty title="Events are not available on this site">
					The events listing has not been set up here yet, so there is nothing to show. The
					events named on the public landing page are wording you can edit under Page content.
				</Empty>
			)}
			{answer?.available && management.data?.message && !management.data.message.can_create && (
				<p className="mb-5 text-[12.5px] text-muted">Your account can view events. An administrator can grant Buzz Event creation access to let you add them here.</p>
			)}

			{answer?.available && (
				<>
				{drafts.length > 0 && (
					<Card className="mb-5">
						<SectionTitle>Unpublished events</SectionTitle>
						<ul className="mt-3 divide-y divide-card-line">
							{drafts.map((event) => (
								<li key={event.name} className="flex flex-wrap items-center justify-between gap-3 py-3 text-[12.5px]">
									<span><strong className="text-ink">{event.title}</strong><span className="ml-2 text-muted">{formatDate(event.start_date)}</span></span>
									<a href={`/app/buzz-event/${encodeURIComponent(event.name)}`} className="font-semibold text-blue hover:underline">Finish in Desk →</a>
								</li>
							))}
						</ul>
					</Card>
				)}
					<div className="mb-6 grid gap-4 sm:grid-cols-3">
						<Card>
							<Stat value={events.length} label="Published and upcoming" />
						</Card>
						<Card>
							<Stat value={runningNow} label="Running today" />
						</Card>
						<Card>
							<Stat value={saidTheyAreComing} label="Planning to attend" />
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
											? "border-blue bg-rail text-white"
											: "border-card-line bg-white text-muted hover:border-blue hover:text-ink",
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
				 * live. Booking and check-in stay in Buzz; this page reads its confirmed roster.
			 */}
			<div className="mt-8 rounded-2xl border border-card-line bg-white px-6 py-5">
				<SectionTitle>Registration and check-in use Buzz</SectionTitle>
				<p className="max-w-2xl text-[12.5px] leading-relaxed text-muted">
					Attendees register on Buzz's booking page. Open a card's confirmed registrations
					to see their names here; use Buzz Desk for tickets, payment and check-in.
				</p>
			</div>
		</>
	);
}

type EventOptions = { categories: string[]; hosts: string[]; venues: string[] };
type EventValues = {
	title: string; category: string; host: string; venue: string; medium: string;
	start_date: string; end_date: string; start_time: string; end_time: string;
	time_zone: string; short_description: string; about: string;
	banner_image: string; card_image: string; registrations_close_at: string;
	registration_url: string; external_registration_page: boolean;
	free_event: boolean; is_published: boolean;
};

const EMPTY_EVENT: EventValues = {
	title: "", category: "", host: "", venue: "", medium: "In Person",
	start_date: "", end_date: "", start_time: "", end_time: "", time_zone: "",
	short_description: "", about: "", banner_image: "", card_image: "",
	registrations_close_at: "", registration_url: "", external_registration_page: false,
	free_event: true, is_published: false,
};

const INPUT = "mt-1 block w-full rounded-xl border border-card-line bg-white px-3 py-2.5 text-[13px] text-ink focus:border-blue focus:outline-none";
const LABEL = "block text-[12px] font-semibold text-ink";

function EventForm({ options, onCreated }: { options: EventOptions; onCreated: (name: string) => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [values, setValues] = useState<EventValues>(EMPTY_EVENT);
	const [chain, setChain] = useState<GeoNode[]>([]);
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);
	const field = (name: keyof EventValues, value: string | boolean) => setValues((old) => ({
		...old,
		[name]: value,
		...(name === "free_event" && value === false && !old.external_registration_page ? { is_published: false } : {}),
		...(name === "external_registration_page" && value === false && !old.free_event ? { is_published: false } : {}),
	}));

	const save = async () => {
		setBusy(true);
		setFailure(null);
		try {
			const response = await call.post<{ message: { name: string } }>(API.createEvent, {
				...values,
				geo_node: selectedNode(chain)?.name ?? "",
				is_published: values.is_published ? 1 : 0,
				free_event: values.free_event ? 1 : 0,
				external_registration_page: values.external_registration_page ? 1 : 0,
				registrations_close_at: values.registrations_close_at.replace("T", " "),
			});
			onCreated(response.message.name);
		} catch (problem) {
			setFailure(errorMessage(problem, "The event could not be created."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Card>
			<form onSubmit={(event) => { event.preventDefault(); void save(); }}>
				<div className="flex flex-wrap items-start justify-between gap-3">
				<div><SectionTitle>New event</SectionTitle><p className="mt-1 text-[12px] text-muted">Buzz creates a basic registration ticket with this event. Set up ticket prices in Buzz Desk before publishing a paid event.</p></div>
					<a href="/app/buzz-event" className="text-[12px] font-semibold text-blue hover:underline">Open Buzz Desk →</a>
				</div>

				<div className="mt-5 grid gap-4 sm:grid-cols-2">
					<label className={LABEL}>Title *<input className={INPUT} required value={values.title} onChange={(e) => field("title", e.target.value)} /></label>
					<label className={LABEL}>Category *<select className={INPUT} required value={values.category} onChange={(e) => field("category", e.target.value)}><option value="">Choose a category</option>{options.categories.map((name) => <option key={name}>{name}</option>)}</select></label>
					<label className={LABEL}>Host *<select className={INPUT} required value={values.host} onChange={(e) => field("host", e.target.value)}><option value="">Choose a host</option>{options.hosts.map((name) => <option key={name}>{name}</option>)}</select></label>
					<label className={LABEL}>Medium<select className={INPUT} value={values.medium} onChange={(e) => field("medium", e.target.value)}><option>In Person</option><option>Online</option></select></label>
					{values.medium !== "Online" && <label className={LABEL}>Venue<select className={INPUT} value={values.venue} onChange={(e) => field("venue", e.target.value)}><option value="">No venue selected</option>{options.venues.map((name) => <option key={name}>{name}</option>)}</select></label>}
					<label className={LABEL}>Time zone<input className={INPUT} placeholder="Africa/Nairobi" value={values.time_zone} onChange={(e) => field("time_zone", e.target.value)} /></label>
					<label className={LABEL}>Start date *<input className={INPUT} type="date" required value={values.start_date} onChange={(e) => field("start_date", e.target.value)} /></label>
					<label className={LABEL}>Start time *<input className={INPUT} type="time" required value={values.start_time} onChange={(e) => field("start_time", e.target.value)} /></label>
					<label className={LABEL}>End date<input className={INPUT} type="date" min={values.start_date || undefined} value={values.end_date} onChange={(e) => field("end_date", e.target.value)} /></label>
					<label className={LABEL}>End time *<input className={INPUT} type="time" required value={values.end_time} onChange={(e) => field("end_time", e.target.value)} /></label>
				</div>
				<div className="mt-4"><GeoSelects chain={chain} onChain={setChain} idPrefix="event-location" /></div>
				<label className={`${LABEL} mt-4`}>Short description<textarea className={INPUT} rows={2} value={values.short_description} onChange={(e) => field("short_description", e.target.value)} /></label>
				<label className={`${LABEL} mt-4`}>About<textarea className={INPUT} rows={5} value={values.about} onChange={(e) => field("about", e.target.value)} /></label>
				<div className="mt-4 grid gap-4 sm:grid-cols-2">
					<label className={LABEL}>Banner image URL<input className={INPUT} value={values.banner_image} onChange={(e) => field("banner_image", e.target.value)} /></label>
					<label className={LABEL}>Card image URL<input className={INPUT} value={values.card_image} onChange={(e) => field("card_image", e.target.value)} /></label>
					<label className={LABEL}>Registration closes at<input className={INPUT} type="datetime-local" value={values.registrations_close_at} onChange={(e) => field("registrations_close_at", e.target.value)} /></label>
				</div>
				<div className="mt-5 flex flex-wrap gap-5 text-[12.5px] font-semibold text-ink">
					<label><input className="mr-2" type="checkbox" checked={values.free_event} onChange={(e) => field("free_event", e.target.checked)} />Free event</label>
					<label><input className="mr-2" type="checkbox" checked={values.external_registration_page} onChange={(e) => field("external_registration_page", e.target.checked)} />External registration page</label>
					<label><input className="mr-2" type="checkbox" checked={values.is_published} disabled={!values.free_event && !values.external_registration_page} onChange={(e) => field("is_published", e.target.checked)} />Publish now</label>
				</div>
				{values.external_registration_page && <label className={`${LABEL} mt-4`}>Registration URL *<input className={INPUT} type="url" required value={values.registration_url} onChange={(e) => field("registration_url", e.target.value)} /></label>}
				{!values.free_event && !values.external_registration_page && <p className="mt-3 text-[12px] text-muted">Paid events start as drafts. Set ticket prices in Buzz Desk, then publish there.</p>}
				{options.hosts.length === 0 && <p className="mt-4 text-[12px] text-muted">Create an Event Host in Buzz Desk before saving this event.</p>}
				{failure && <div className="mt-4"><ErrorNote>{failure}</ErrorNote></div>}
				<div className="mt-5 flex items-center gap-3"><Button type="submit" busy={busy} disabled={options.categories.length === 0 || options.hosts.length === 0}>Create event</Button><span className="text-[11.5px] text-muted">Advanced schedule, tickets and payments can be set in Buzz Desk.</span></div>
			</form>
		</Card>
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

			<p className="text-[12px] text-muted">
				{event.start_date ? formatDate(event.start_date) : "No date"}
				{event.multi_day && event.end_date ? ` → ${formatDate(event.end_date)}` : ""}
				{event.start_time ? ` · ${event.start_time.slice(0, 5)}` : ""}
			</p>

			{event.venue && <p className="mt-0.5 text-[12px] text-slate-faint">{event.venue}</p>}

			{event.summary && (
				<p className="mt-2 line-clamp-3 text-[12.5px] text-muted">{event.summary}</p>
			)}

			<Registrations event={event} />
			<Roster event={event} />

			<div className="mt-3 flex flex-wrap items-center gap-3">
				<ButtonLink to={`/app/buzz-event/${encodeURIComponent(event.event)}`}>Manage in Buzz Desk</ButtonLink>
				{event.href && <a href={event.href} className="text-[12px] font-semibold text-blue hover:underline">View registration page →</a>}
			</div>
		</Card>
	);
}

/** Confirmed Buzz tickets, paged so every registration remains reachable. */
function Registrations({ event }: { event: EventCard }) {
	const [open, setOpen] = useState(false);
	const [start, setStart] = useState(0);
	const external = Boolean(event.href && !event.href.startsWith("/b/register/"));
	const { data, error, isLoading } = useFrappeGetCall<{
		message: { total: number; registrations: Array<{ ticket: string; name: string; email: string }> };
	}>(
		API.eventRegistrations,
		{ event: event.event, start, limit: 100 },
		open && !external ? `admin:event_registrations:${event.event}:${start}` : null,
	);
	const total = data?.message?.total ?? 0;
	const rows = data?.message?.registrations ?? [];

	if (external) {
		return <p className="mt-3 text-[12px] text-muted">Registration is managed on the external site.</p>;
	}
	return (
		<div className="mt-3 border-t border-card-line pt-3">
			<button type="button" onClick={() => setOpen((shown) => !shown)} className="text-[12px] font-semibold text-blue hover:underline">
				Confirmed registrations {open ? "· hide" : "· show"}
			</button>
			{open && (
				<div className="mt-3">
					{isLoading && <Spinner label="Loading registrations…" />}
					{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}
					{!isLoading && !error && (
						<>
							<p className="text-[11.5px] text-muted">{total} confirmed {total === 1 ? "registration" : "registrations"}</p>
							{rows.length === 0 && <p className="mt-2 text-[12px] italic text-slate-faint">No confirmed registrations yet.</p>}
							<ul className="mt-2 space-y-1.5">
								{rows.map((person) => (
									<li key={person.ticket} className="text-[12px] text-muted">
										<span className="font-semibold text-ink">{person.name}</span>
										{person.email && <span className="ml-2">{person.email}</span>}
									</li>
								))}
							</ul>
							<div className="mt-3 flex items-center gap-3 text-[12px]">
								{start > 0 && <button type="button" onClick={() => setStart(Math.max(0, start - 100))} className="font-semibold text-blue">Previous</button>}
								{start + rows.length < total && <button type="button" onClick={() => setStart(start + 100)} className="font-semibold text-blue">Next</button>}
							</div>
						</>
					)}
				</div>
			)}
		</div>
	);
}

/**
 * Who from the society said they are coming, on demand.
 *
 * **The count is always shown; the names are asked for.** The number rides on
 * the listing and costs nothing, and it is what a coordinator glances at. The
 * roster is a request per event, made only when somebody opens it, because a
 * page of twenty cards eagerly fetching twenty rosters is twenty queries to
 * draw a screen most of which nobody reads.
 *
 * **These are intentions, not bookings**, and the wording says so. Somebody who
 * told their branch they would be there is on this list whether or not they ever
 * took a ticket; Buzz holds the tickets, and "Manage in Buzz" below is still
 * where the registration list lives. The two lists answer different questions
 * and a coordinator planning transport wants this one.
 */
function Roster({ event }: { event: EventCard }) {
	const [open, setOpen] = useState(false);

	const { data, error, isLoading } = useFrappeGetCall<{
		message: { going: number; attendees: EventAttendee[] };
	}>(
		API.eventAttendees,
		{ event: event.event },
		// Null until asked for. `useFrappeGetCall` treats a null key as "do not
		// fetch", which is what keeps a listing to one request.
		open ? `admin:event_attendees:${event.event}` : null,
	);

	const attendees = data?.message?.attendees ?? [];

	return (
		<div className="mt-3 border-t border-card-line pt-3">
			<button
				type="button"
				onClick={() => setOpen((shown) => !shown)}
				className="text-[12px] font-semibold text-ink transition hover:text-blue"
			>
				{event.going ?? 0} said they are coming
				<span className="ml-1.5 text-slate-faint">{open ? "· hide" : "· show who"}</span>
			</button>

			{open && (
				<div className="mt-2">
					{isLoading && <Spinner label="Loading…" />}
					{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

					{!isLoading && !error && attendees.length === 0 && (
						<p className="text-[12px] italic text-slate-faint">
							Nobody has said they are coming yet.
						</p>
					)}

					<ul className="space-y-1">
						{attendees.map((person) => (
							<li key={person.red_profile} className="text-[12px] text-muted">
								<span className="font-semibold text-ink">{person.full_name}</span>
								{person.phone && <span className="ml-2 text-slate-faint">{person.phone}</span>}
							</li>
						))}
					</ul>
				</div>
			)}
		</div>
	);
}
