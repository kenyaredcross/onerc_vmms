import { useMemo, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate, formatDayMonth } from "../lib/format";
import { Icon } from "../ui/icons";
import {
	Card as Panel,
	Empty,
	ErrorNote,
	List,
	ListRow,
	NotBuilt,
	Pager,
	SectionLabel,
	SectionLink,
	Skeleton,
	Spinner,
	cx,
	usePaged,
} from "../ui/primitives";
import { MonthGrid, markDays } from "../ui/MonthGrid";
import { useAttendance } from "./attendance";
import type { EventCard } from "./types";

/**
 * Events, read from Buzz and handed back to Buzz.
 *
 * **The events are real records.** `vmmsx.api.events.upcoming` reads what a
 * society has actually published in Buzz, through the seam in
 * `vmmsx/buzz/services/events.py`. Nothing on this screen is invented, and when
 * Buzz is not installed the screen says so rather than showing a plausible
 * grid of nothing.
 *
 * **Buying leaves; saying you are coming does not.** Tickets, coupons, payment
 * and check-in are Buzz's, so anything to do with acquiring a place is a full
 * navigation to Buzz's own event page. What stays here is the society's own
 * record of an intention — this volunteer means to be there — which is a fact
 * about somebody the society already holds a file on, and the thing a
 * coordinator plans a branch's week around. `events/services/attendance.py`
 * draws the line and `useAttendance` is the only way this screen crosses it.
 * **No control here may say a place is held.**
 *
 * **What the reader is going to comes first.** The section above the listing is
 * their own diary and the listing below it is the society's noticeboard, in that
 * order because somebody opening this screen with three events booked wants the
 * three before the sixty. It renders nothing at all when they have answered for
 * nothing, rather than an empty panel sitting on top of the very grid that would
 * fill it.
 *
 * **The filtering is server-side.** Search and category go back to the endpoint
 * rather than being applied to a page of rows in the browser, because a browser
 * filter over the first sixty events silently lies the moment a society has
 * sixty-one. The date facet is the exception and is honest about being a view
 * over what came back: it narrows a list already scoped to what has not
 * finished.
 */

/** "14 Aug", or "14 Aug to 17 Aug" when it runs over several days. */
function dateLine(row: EventCard): string {
	const start = formatDayMonth(row.start_date);

	if (!row.multi_day) return formatDate(row.start_date);

	return `${start} to ${formatDate(row.end_date)}`;
}

/* ------------------------------------------------------------- attending */

/**
 * The reader's own diary, above the society's noticeboard.
 *
 * **The nearest one is drawn large and the rest are a list**, because those are
 * two different questions and a uniform grid answers neither well. "What is next
 * and what do I need to know about it" wants a band with the date, the time and
 * the place on it. "What else have I got coming" wants three lines somebody
 * scans. Drawing all of them at the featured size would mean scrolling past a
 * month of banners to reach the listing.
 *
 * **Absent rather than empty.** Somebody attending nothing gets no section: the
 * grid immediately below is already the invitation, and a panel saying "you are
 * going to nothing" stacked on top of it is the same sentence twice.
 */
function Attending() {
	const { events, isLoading, pending, toggle } = useAttendance();

	// Hidden until asked for. A month grid is a large, quiet thing to put above
	// a listing somebody came to browse, and the answer it gives is one most
	// people want occasionally rather than every visit.
	const [calendarOpen, setCalendarOpen] = useState(false);

	// **The month is derived until somebody chooses one.** Opening on today would
	// show an empty grid to anybody whose next event is in three weeks' time,
	// which is the person this section exists for. Held as null rather than
	// initialised from the data because the data is not here on the first render
	// and `useState` would keep whatever it was given then.
	const [picked, setPicked] = useState<{ year: number; month: number } | null>(null);

	// Every event in this list is one the reader is going to, so the grid's two
	// treatments collapse into one here: `mine` is all of them. The full calendar
	// tab is where the society's other events are drawn beside these.
	const marks = useMemo(
		() => markDays(events, new Set(events.map((row) => row.event))),
		[events],
	);

	if (isLoading) {
		return (
			<section className="mt-9">
				<Skeleton className="mb-3 h-4 w-44" />
				<Skeleton className="h-32 rounded-2xl" />
			</section>
		);
	}

	if (events.length === 0) return null;

	const [next, ...rest] = events;

	// The soonest event's month, which is what `by_names` sorted to the front.
	const opensOn = next.start_date ? new Date(`${next.start_date}T00:00:00`) : new Date();
	const year = picked?.year ?? opensOn.getFullYear();
	const month = picked?.month ?? opensOn.getMonth();

	return (
		<section className="mt-9">
			<SectionLabel
				action={
					<>
						<button
							type="button"
							onClick={() => setCalendarOpen((open) => !open)}
							aria-expanded={calendarOpen}
							className="whitespace-nowrap text-[12px] font-bold text-ink transition hover:text-blue"
						>
							{calendarOpen ? (
								<EditableText k="portal.events.attending.hide_calendar" fallback="Hide calendar" />
							) : (
								<EditableText k="portal.events.attending.show_calendar" fallback="Show calendar" />
							)}
						</button>
						<SectionLink to="/calendar">
							<EditableText k="portal.events.attending.full" fallback="Full calendar" />
						</SectionLink>
					</>
				}
			>
				<EditableText
					k="portal.events.attending.label"
					fallback="Your events"
				/>
			</SectionLabel>

			<div
				className={cx(
					"grid items-start gap-5",
					calendarOpen && "lg:grid-cols-[minmax(0,1fr)_300px]",
				)}
			>
				<div className="min-w-0 space-y-4">
					<Featured
						row={next}
						busy={pending === next.event}
						onToggle={() => void toggle(next.event)}
					/>

					{rest.length > 0 && (
						<Panel pad={false}>
							<div className="p-2">
								<List>
									{rest.map((row) => (
										<ListRow
											key={row.event}
											lead={
												<span
													className="grid h-9 w-9 flex-none place-items-center rounded-lg bg-tint-navy-soft text-tint-navy"
													aria-hidden="true"
												>
													<Icon.calendar size={17} />
												</span>
											}
											title={
												<Link
													to={`/events/${encodeURIComponent(row.event)}`}
													className="transition hover:text-ink"
												>
													{row.title}
												</Link>
											}
											meta={
												<>
													{dateLine(row)}
													{row.start_time && ` · ${row.start_time.slice(0, 5)}`}
													{(row.venue || row.medium) && ` · ${row.venue || row.medium}`}
												</>
											}
											trailing={
												<Withdraw
													busy={pending === row.event}
													onClick={() => void toggle(row.event)}
												/>
											}
										/>
									))}
								</List>
							</div>
						</Panel>
					)}
				</div>

				{calendarOpen && (
					<Panel>
						<MonthGrid
							year={year}
							month={month}
							marks={marks}
							onMonth={(nextYear, nextMonth) => setPicked({ year: nextYear, month: nextMonth })}
							size="compact"
						/>
					</Panel>
				)}
			</div>
		</section>
	);
}

/**
 * The next thing the reader is going to, with what they need in order to get
 * there.
 *
 * The photograph is a wash behind the words rather than a picture beside them,
 * because at this size a society's own uploads vary too much to be trusted with
 * the composition. The gradient is tokens, not a hex: a band this large carrying
 * its own colours is how a screen starts to drift from the rest of the product.
 */
function Featured({ row, busy, onToggle }: { row: EventCard; busy: boolean; onToggle: () => void }) {
	return (
		<article className="relative overflow-hidden rounded-2xl bg-rail text-white shadow-hero">
			{row.image && (
				<>
					<img
						src={row.image}
						alt=""
						className="absolute inset-0 h-full w-full object-cover"
						loading="lazy"
					/>
					<div
						aria-hidden="true"
						className="absolute inset-0 bg-gradient-to-r from-rail via-rail/95 to-rail/60"
					/>
				</>
			)}

			<div className="relative flex flex-wrap items-center gap-5 p-5 sm:p-7">
				<DateChip date={row.start_date} />

				<div className="min-w-0 flex-1">
					<div className="flex flex-wrap items-center gap-2">
						<span className="rounded-full bg-blue px-2.5 py-1 text-[9.5px] font-semibold uppercase tracking-eyebrow text-white">
							<EditableText k="portal.events.attending.next" fallback="Next up" />
						</span>
						{row.category && (
							<span className="text-[10px] font-bold uppercase tracking-eyebrow text-white/60">
								{row.category}
							</span>
						)}
					</div>

					<h3 className="mt-2.5 text-[20px] font-semibold leading-tight tracking-tight [overflow-wrap:anywhere] sm:text-[26px]">
						{row.title}
					</h3>

					<p className="mt-2 text-[12.5px] text-white/75 [overflow-wrap:anywhere]">
						{[
							dateLine(row),
							row.start_time &&
								`${row.start_time.slice(0, 5)}${row.end_time ? ` to ${row.end_time.slice(0, 5)}` : ""}`,
							row.venue || row.medium,
						]
							.filter(Boolean)
							.join(" · ")}
					</p>
				</div>

				<div className="flex flex-none flex-wrap items-center gap-2.5">
					<Withdraw busy={busy} onClick={onToggle} onDark />
					<Link
						to={`/events/${encodeURIComponent(row.event)}`}
						className="whitespace-nowrap rounded-full bg-white/15 px-4 py-2.5 text-[12.5px] font-bold text-white backdrop-blur transition hover:bg-white/25"
					>
						<EditableText k="portal.events.attending.details" fallback="Details" />
					</Link>
				</div>
			</div>
		</article>
	);
}

/**
 * The control that takes the answer back.
 *
 * It reads as a confirmation first and a control second — "Going ✓" with the
 * withdrawal on hover and on focus — because the common case by far is somebody
 * glancing at the section to check they are expected, and a row of "cancel"
 * buttons is a section that looks like it is asking them to reconsider.
 */
function Withdraw({
	busy,
	onClick,
	onDark = false,
	className,
}: {
	busy: boolean;
	onClick: () => void;
	onDark?: boolean;
	className?: string;
}) {
	return (
		<button
			type="button"
			onClick={onClick}
			disabled={busy}
			// **The label says what pressing it does, not what it is showing.**
			// The visible text swaps on hover, which nobody arriving by keyboard
			// or screen reader ever sees: without this the control announces
			// "Going" and then withdraws the answer. The visible words stay as
			// they are, because for a pointer the confirmation is the useful
			// reading and the verb appears the moment it is reachable.
			aria-label="Say you can no longer come"
			className={cx(
				"group relative z-10 inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-3.5 py-2 text-[11.5px] font-bold transition disabled:opacity-50",
				onDark
					? "bg-white text-ink hover:bg-white/90"
					: "border border-card-line bg-white text-slate-strong hover:border-blue hover:text-blue",
				className,
			)}
		>
			{busy ? (
				<EditableText k="portal.events.attending.saving" fallback="Saving…" />
			) : (
				<>
					{/* Focus swaps them as well as hover, so somebody tabbing to the
					    control sees the verb rather than the confirmation. */}
					<Icon.check size={13} className="group-hover:hidden group-focus-visible:hidden" />
					<Icon.cross size={13} className="hidden group-hover:block group-focus-visible:block" />
					<span className="group-hover:hidden group-focus-visible:hidden">
						<EditableText k="portal.events.attending.going" fallback="Attending" />
					</span>
					<span className="hidden group-hover:block group-focus-visible:block">
						<EditableText k="portal.events.attending.withdraw" fallback="Cancel" />
					</span>
				</>
			)}
		</button>
	);
}

/**
 * The date block on the featured band: a small month over a large day.
 *
 * The two parts are asked for separately rather than split out of a formatted
 * string. `formatDayMonth` is locale-driven and correctly so, which means the
 * order of its two tokens is the *reader's*, and splitting on the space puts
 * the month in the big slot for anybody whose locale writes it first.
 */
function DateChip({ date }: { date: string }) {
	const parsed = date ? new Date(`${date}T00:00:00`) : null;
	const valid = parsed && !Number.isNaN(parsed.getTime()) ? parsed : null;

	const month = valid ? valid.toLocaleDateString(undefined, { month: "short" }) : "";
	const day = valid ? valid.toLocaleDateString(undefined, { day: "numeric" }) : "";

	return (
		<div className="flex-none rounded-lg bg-white px-4 py-3 text-center border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)]">
			<div className="text-[9.5px] font-semibold uppercase tracking-wider text-blue">
				{month || ""}
			</div>
			<div className="text-[26px] font-semibold leading-none text-ink">
				{day || "?"}
			</div>
		</div>
	);
}

export default function Events() {
	// What has been typed, and what has been asked. Kept apart so the endpoint is
	// called when somebody submits rather than on every keystroke: a search that
	// fires per character is a query per character, and the answer to a
	// half-typed word is noise on the screen.
	const [draft, setDraft] = useState("");
	const [search, setSearch] = useState("");
	const [category, setCategory] = useState("");
	const [venue, setVenue] = useState("");
	const [host, setHost] = useState("");
	// A real window rather than the "next 7 / next 30 days" facet this replaced.
	// That facet could only answer questions shaped like "soon"; somebody
	// planning around a fixed week could not ask for it at all.
	const [dateFrom, setDateFrom] = useState("");
	const [dateTo, setDateTo] = useState("");

	// The same hook `Attending` uses, and deliberately the same SWR key: both
	// read one cached answer, so a card marked "going" and the diary above it
	// cannot disagree, and pressing either updates both.
	const attendance = useAttendance();

	const filters = useFrappeGetCall<{
		message: {
			available: boolean;
			categories: Array<{ category: string; label: string }>;
			venues: Array<{ venue: string; label: string }>;
			hosts: Array<{ host: string; label: string }>;
		};
	}>(API.eventFilters, undefined, "portal:event_filters");

	const { data, error, isLoading } = useFrappeGetCall<{
		message: { available: boolean; events: EventCard[] };
	}>(
		API.eventsUpcoming,
		{
			search: search || undefined,
			category: category || undefined,
			venue: venue || undefined,
			host: host || undefined,
			date_from: dateFrom || undefined,
			date_to: dateTo || undefined,
		},
		// The key carries the whole query, so changing any facet refetches rather
		// than showing the previous answer under the new heading.
		`portal:events:${search}:${category}:${venue}:${host}:${dateFrom}:${dateTo}`,
	);

	const available = data?.message?.available ?? filters.data?.message?.available ?? true;
	const all = data?.message?.events ?? [];

	// Every facet is the server's now, including the dates. Narrowing here as
	// well would mean a page limit applied before the filter rather than after
	// it: the last event of a busy month would drop off the end silently.
	const rows = all;

	// Nine to a page: three full rows of the three-column grid at desktop width.
	const paged = usePaged(rows, 9);

	// Whether the reader narrowed anything, which is what decides between the two
	// empty states: "nothing matches what you asked for" and "nothing is
	// scheduled". Derived from every facet rather than a couple of them, so a
	// reader who filtered only by venue is not told the society has published
	// nothing. Listed here rather than inline at the point of use so that a facet
	// added to the query above has one obvious place to be added to as well.
	const narrowed = Boolean(search || category || venue || host || dateFrom || dateTo);

	if (!available) {
		return (
			<>
				<Hero
					draft={draft}
					setDraft={setDraft}
					onSearch={() => setSearch(draft.trim())}
					categories={[]}
					category={category}
					setCategory={setCategory}
					venues={filters.data?.message?.venues ?? []}
					venue={venue}
					setVenue={setVenue}
					hosts={filters.data?.message?.hosts ?? []}
					host={host}
					setHost={setHost}
					dateFrom={dateFrom}
					setDateFrom={setDateFrom}
					dateTo={dateTo}
					setDateTo={setDateTo}
					disabled
				/>
				<div className="mt-8">
					<NotBuilt
						what="Events"
						needs="Your society has not opened its events listing yet. When it does, everything your branches publish will appear here."
					/>
				</div>
			</>
		);
	}

	return (
		<>
			<Hero
				draft={draft}
				setDraft={setDraft}
				onSearch={() => setSearch(draft.trim())}
				categories={filters.data?.message?.categories ?? []}
				category={category}
				setCategory={setCategory}
				venues={filters.data?.message?.venues ?? []}
				venue={venue}
				setVenue={setVenue}
				hosts={filters.data?.message?.hosts ?? []}
				host={host}
				setHost={setHost}
				dateFrom={dateFrom}
				setDateFrom={setDateFrom}
				dateTo={dateTo}
				setDateTo={setDateTo}
			/>

			<Attending />

			<section className="mt-9">
				<div className="text-center">
					<div className="eyebrow text-blue">
						<EditableText k="portal.events.eyebrow" fallback="Upcoming events" />
					</div>
					<h2 className="mt-2 text-[26px] font-semibold tracking-tight text-ink">
						<EditableText k="portal.events.heading" fallback="Featured events" />
					</h2>
				</div>

				{isLoading && <Spinner label="Finding events…" />}
				{error && (
					<div className="mt-6">
						<ErrorNote>{errorMessage(error)}</ErrorNote>
					</div>
				)}

				{!isLoading && !error && rows.length === 0 && (
					<div className="mt-6">
						<Empty
							icon={Icon.calendar}
							title={narrowed ? "No events match" : "Nothing scheduled just yet"}
						>
							{narrowed
								? "No event matches what you are looking for. Try a wider search."
								: "When your society publishes an event, it appears here."}
						</Empty>
					</div>
				)}

				{rows.length > 0 && (
					<>
						<div className="mt-7 grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
							{paged.slice.map((row) => (
								<Card
									key={row.event}
									row={row}
									going={attendance.answered.has(row.event)}
									busy={attendance.pending === row.event}
									onToggle={() => void attendance.toggle(row.event)}
								/>
							))}
						</div>

						<Pager
							page={paged.page}
							pageCount={paged.pageCount}
							onPage={paged.onPage}
							total={paged.total}
							noun="events"
						/>
					</>
				)}
			</section>
		</>
	);
}

/* ------------------------------------------------------------------- hero */

/**
 * The banded hero and the filter bar sitting on its lower edge.
 *
 * The reference design puts the search bar half over the band, which is what
 * `-mb-*` plus a translated panel achieves here. The gradient is the brand navy
 * rather than the reference's purple: the palette is the society's, and the
 * layout is what was being borrowed.
 */
function Hero({
	draft,
	setDraft,
	onSearch,
	categories,
	category,
	setCategory,
	venues,
	venue,
	setVenue,
	hosts,
	host,
	setHost,
	dateFrom,
	setDateFrom,
	dateTo,
	setDateTo,
	disabled = false,
}: {
	draft: string;
	setDraft: (value: string) => void;
	onSearch: () => void;
	categories: Array<{ category: string; label: string }>;
	category: string;
	setCategory: (value: string) => void;
	venues: Array<{ venue: string; label: string }>;
	venue: string;
	setVenue: (value: string) => void;
	hosts: Array<{ host: string; label: string }>;
	host: string;
	setHost: (value: string) => void;
	dateFrom: string;
	setDateFrom: (value: string) => void;
	dateTo: string;
	setDateTo: (value: string) => void;
	disabled?: boolean;
}) {
	const field =
		"w-full bg-transparent text-[13px] text-ink outline-none placeholder:text-slate-faint disabled:cursor-not-allowed";

	return (
		<div className="relative">
			<div className="overflow-hidden rounded-2xl bg-gradient-to-br from-rail via-rail to-blue/80 px-7 pb-20 pt-12 text-center shadow-hero md:px-12 md:pb-24 md:pt-16">
				<div className="eyebrow text-white/60">
					<EditableText k="portal.events.hero.eyebrow" fallback="What's on" />
				</div>
				<h1 className="mx-auto mt-3 max-w-2xl text-[30px] font-semibold leading-tight tracking-tight text-white md:text-[38px]">
					<EditableText
						k="portal.events.hero.headline"
						fallback="Discover and join upcoming events"
					/>
				</h1>
				<p className="mx-auto mt-3 max-w-xl text-[13.5px] leading-relaxed text-white/70">
					<EditableText
						k="portal.events.hero.blurb"
						fallback="Training days, community drives and everything else your society has planned."
					/>
				</p>
			</div>

			<form
				onSubmit={(event) => {
					event.preventDefault();
					onSearch();
				}}
				className="relative z-10 mx-auto -mt-11 flex max-w-3xl flex-col gap-2 rounded-2xl bg-white p-2.5 shadow-pop"
			>
				{/* Two rows, because there are six controls here and a single row of
				    six is either six unreadably narrow cells or a row that wraps and
				    orphans the search button. The question comes first and the ways
				    of narrowing it sit underneath, which is also the order somebody
				    fills them in. */}
				<div className="flex gap-2">
					<label className="control flex-1">
						<Icon.search size={15} className="flex-none text-slate-faint" />
						<span className="sr-only">Search events</span>
						<input
							value={draft}
							onChange={(event) => setDraft(event.target.value)}
							disabled={disabled}
							placeholder="Search events"
							className={field}
						/>
					</label>

					<button
						type="submit"
						disabled={disabled}
						aria-label="Search"
						className="grid h-11 w-11 flex-none place-items-center rounded-full bg-blue text-white transition hover:bg-blue-press disabled:opacity-50"
					>
						<Icon.search size={16} />
					</button>
				</div>

				<div className="grid gap-2 border-t border-card-line pt-2 sm:grid-cols-2 lg:grid-cols-4">
					<label className="control">
						<Icon.tag size={15} className="flex-none text-slate-faint" />
						<span className="sr-only">Category</span>
						<select
							value={category}
							onChange={(event) => setCategory(event.target.value)}
							disabled={disabled || categories.length === 0}
							className={cx(field, "cursor-pointer")}
						>
							<option value="">All categories</option>
							{categories.map((row) => (
								<option key={row.category} value={row.category}>
									{row.label}
								</option>
							))}
						</select>
					</label>

					<label className="control">
						<Icon.pin size={15} className="flex-none text-slate-faint" />
						<span className="sr-only">Where</span>
						<select
							value={venue}
							onChange={(event) => setVenue(event.target.value)}
							disabled={disabled || venues.length === 0}
							className={cx(field, "cursor-pointer")}
						>
							<option value="">Anywhere</option>
							{venues.map((row) => (
								<option key={row.venue} value={row.venue}>
									{row.label}
								</option>
							))}
						</select>
					</label>

					{/* Drawn only when there is a choice to make. A society whose events
					    are all run by itself has one host, and offering a picker with a
					    single option in it is a control that cannot do anything. */}
					{hosts.length > 1 && (
						<label className="control">
							<Icon.people size={15} className="flex-none text-slate-faint" />
							<span className="sr-only">Organisation</span>
							<select
								value={host}
								onChange={(event) => setHost(event.target.value)}
								disabled={disabled}
								className={cx(field, "cursor-pointer")}
							>
								<option value="">Any organisation</option>
								{hosts.map((row) => (
									<option key={row.host} value={row.host}>
										{row.label}
									</option>
								))}
							</select>
						</label>
					)}

					<label className="control">
						<Icon.calendar size={15} className="flex-none text-slate-faint" />
						<span className="sr-only">From</span>
						<input
							type="date"
							value={dateFrom}
							onChange={(event) => setDateFrom(event.target.value)}
							disabled={disabled}
							className={cx(field, "cursor-pointer")}
							aria-label="Events from"
						/>
					</label>

					<label className="control">
						<span className="flex-none text-[12px] text-slate-faint">to</span>
						<input
							type="date"
							value={dateTo}
							onChange={(event) => setDateTo(event.target.value)}
							disabled={disabled}
							// An end before the start is a window with nothing in it, so the
							// control refuses it rather than the page reporting no events.
							min={dateFrom || undefined}
							className={cx(field, "cursor-pointer")}
							aria-label="Events until"
						/>
					</label>
				</div>
			</form>
		</div>
	);
}

/* ------------------------------------------------------------------- card */

/**
 * One event.
 *
 * **The whole card opens it, except the ticket button.** A stretched link over
 * the card body makes the obvious gesture work — clicking the picture, the
 * title, the dates — while "Get tickets" sits above it on the z-axis and keeps
 * its own destination, which is Buzz and not this app. The alternative, a link
 * on the title alone, meant the thing people actually click did nothing.
 *
 * The image is deliberately short. It was `h-40` on a three-column grid, which
 * left the picture taller than everything under it and pushed the dates below
 * the fold on a narrow screen; the text beside it now wraps rather than
 * truncating, because a venue somebody cannot read is not a venue.
 */
/**
 * Has the moment the society set for registrations already passed?
 *
 * Answered in the browser because it is a statement about *now* and a card
 * rendered at nine is still on the screen at ten. Nothing is decided by it —
 * booking is Buzz's and Buzz enforces its own closing time — so the worst a
 * clock a few minutes out can do is word one line early or late.
 */
function registrationClosed(row: EventCard): boolean {
	if (!row.registrations_close_at) return false;

	return new Date(row.registrations_close_at.replace(" ", "T")) < new Date();
}

function Card({
	row,
	going,
	busy,
	onToggle,
}: {
	row: EventCard;
	going: boolean;
	busy: boolean;
	onToggle: () => void;
}) {
	const href = `/events/${encodeURIComponent(row.event)}`;

	return (
		<article className="group relative flex flex-col overflow-hidden rounded-xl bg-white border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_2px_10px_rgba(30,50,73,0.07)]">
			<div className="relative h-20 flex-none overflow-hidden sm:h-24">
				{row.image ? (
					<img
						src={row.image}
						alt=""
						loading="lazy"
						className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.04]"
					/>
				) : (
					// No picture is ordinary: `card_image` and `banner_image` are both
					// optional in Buzz. A branded panel is better than a broken image
					// and better than a stock photograph this app invented.
					<div
						aria-hidden="true"
						className="h-full w-full bg-gradient-to-br from-rail via-rail to-blue/70"
					/>
				)}

				{/* Both overlays shrink with the band. At the previous size they took
				    a third of an 80px image between them, which reads as a picture of
				    two badges rather than a picture with two badges on it. */}
				<div className="absolute left-3 top-3 rounded-lg bg-white/95 px-2.5 py-1.5 text-center border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)] backdrop-blur">
					<div className="text-[13px] font-semibold leading-none text-ink">
						{formatDayMonth(row.start_date).split(" ")[0] || "?"}
					</div>
					<div className="text-[8px] font-bold uppercase tracking-wider text-blue">
						{formatDayMonth(row.start_date).split(" ")[1] || ""}
					</div>
				</div>

				{row.category && (
					<span className="absolute right-2.5 top-2.5 max-w-[60%] truncate rounded-full bg-rail/80 px-2 py-0.5 text-[9.5px] font-bold text-white backdrop-blur">
						{row.category}
					</span>
				)}

				{/* Only "Free", never a price. Whether a society is charging is the
				    first thing somebody wants to know and it is published on Buzz's
				    own page; what it costs is a ticket type, which is Buzz's and is
				    not re-implemented here. Bottom-left, so it does not collide with
				    the category chip opposite. */}
				{row.free && (
					<span className="absolute bottom-2.5 right-2.5 rounded-full bg-success-soft px-2 py-0.5 text-[9.5px] font-bold text-success">
						Free
					</span>
				)}
			</div>

			<div className="flex flex-1 flex-col p-4">
				<h3 className="text-[14px] font-bold leading-snug text-ink transition group-hover:text-ink [overflow-wrap:anywhere]">
					{/* The stretched link. `before:absolute inset-0` puts an invisible
					    hit area over the whole card while keeping the accessible name
					    on the title, which is what a screen reader should announce. */}
					<Link to={href} className="before:absolute before:inset-0 before:content-['']">
						{row.title}
					</Link>
				</h3>

				{row.summary && (
					<p className="mt-1.5 line-clamp-2 text-[11.5px] leading-relaxed text-muted [overflow-wrap:anywhere]">
						{row.summary}
					</p>
				)}

				{/* `items-start` and no `truncate`: a long venue name wraps onto a
				    second line rather than being cut off mid-word. */}
				<dl className="mt-3 space-y-1.5 text-[11.5px] text-muted">
					<div className="flex items-start gap-1.5">
						<Icon.calendar size={13} className="mt-0.5 flex-none text-slate-faint" />
						<dd className="min-w-0">
							{dateLine(row)}
							{row.start_time && ` · ${row.start_time.slice(0, 5)}`}
						</dd>
					</div>
					{(row.venue || row.medium) && (
						<div className="flex items-start gap-1.5">
							<Icon.pin size={13} className="mt-0.5 flex-none text-slate-faint" />
							<dd className="min-w-0 break-words">{row.venue || row.medium}</dd>
						</div>
					)}
					{/* Only where the society has said, and worded by which side of
					    the moment we are on. "Closes 4 March" is a prompt; "Closed 4
					    March" is the reason the button below does nothing for you —
					    and a card that showed neither sent somebody to a page they
					    could no longer book. */}
					{row.registrations_close_at && (
						<div className="flex items-start gap-1.5">
							<Icon.clock size={13} className="mt-0.5 flex-none text-slate-faint" />
							<dd
								className={cx(
									"min-w-0",
									registrationClosed(row) && "font-semibold text-danger",
								)}
							>
								{registrationClosed(row) ? "Registration closed " : "Register by "}
								{formatDate(row.registrations_close_at.slice(0, 10))}
							</dd>
						</div>
					)}

					{/* Drawn only once somebody is going. "Nobody yet" on every card in
					    a listing of a season's events is a grid of discouragement, and
					    it is what an event published this morning honestly says. */}
					{Boolean(row.going) && (
						<div className="flex items-start gap-1.5">
							<Icon.people size={13} className="mt-0.5 flex-none text-slate-faint" />
							<dd className="min-w-0">
								<GoingLine going={row.going} />
							</dd>
						</div>
					)}
				</dl>

				<div className="mt-3 flex-1" />

				{/* Telling the society you are coming, and it stops there: tickets,
				    payment, confirmation and check-in are all Buzz's, which is why
				    nothing on this card claims a place has been held. An event with
				    no route is one Buzz has not finished publishing, and answering
				    for one would leave somebody expected at something the society
				    has not finished announcing.

				    `relative z-10` lifts the control above the stretched link, so
				    pressing it answers rather than opening the detail page
				    underneath. */}
				{row.href ? (
					going ? (
						<Withdraw busy={busy} onClick={onToggle} className="self-start" />
					) : (
						<button
							type="button"
							onClick={onToggle}
							disabled={busy}
							className="relative z-10 inline-flex items-center justify-center self-start rounded-full bg-rail px-4 py-2 text-[12px] font-bold text-white transition hover:bg-blue disabled:opacity-50"
						>
							{busy ? (
								<EditableText k="portal.events.attending.saving" fallback="Saving…" />
							) : (
								<EditableText k="portal.events.card.action" fallback="Attend" />
							)}
						</button>
					)
				) : (
					<span className="text-[11px] italic text-slate-faint">
						Registration is not open yet.
					</span>
				)}
			</div>
		</article>
	);
}

/* ------------------------------------------------------------------ detail */

/**
 * One event's own page.
 *
 * **Same records, same boundary, more room.** `vmmsx.api.events.detail` re-asks
 * `is_published` rather than trusting the docname somebody arrived with, so a
 * link to an unpublished event answers with a sentence rather than a page.
 *
 * **Booking is still Buzz's**, and the call to action is the same full
 * navigation a card carries. What this screen adds is everything a card had no
 * room for: the banner at its real crop, the venue's address rather than its
 * name, and `about` — Buzz's own page copy for the event, written on the desk.
 * That field is HTML by design and by another app's authors, which is why it is
 * rendered through the same `.article-body` treatment a story's body gets and
 * why nothing a *portal user* types is ever rendered this way.
 */
export function Event() {
	const { name = "" } = useParams();

	const { data, error, isLoading } = useFrappeGetCall<{
		message: (EventCard & {
			banner: string;
			about: string;
			host: string;
			venue_address: string;
		}) | null;
	}>(API.eventDetail, { event: name }, name ? `portal:event:${name}` : null);

	const row = data?.message ?? null;

	return (
		<>
			<Link
				to="/events"
				className="mb-6 inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-ink hover:underline"
			>
				<Icon.back size={14} />
				All events
			</Link>

			{isLoading && <Spinner label="Loading…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{!isLoading && !error && !row && (
				<Empty title="That event is not here">
					It may have finished, or been unpublished. Everything currently on is on the events
					page.
				</Empty>
			)}

			{row && (
				<article>
					<div className="overflow-hidden rounded-2xl shadow-hero">
						{row.banner ? (
							<img
								src={row.banner}
								alt=""
								className="aspect-[10/3] w-full object-cover"
							/>
						) : (
							<div
								aria-hidden="true"
								className="aspect-[10/3] w-full bg-gradient-to-br from-rail via-rail to-blue/70"
							/>
						)}
					</div>

					{/* `min-w-0` on the panel and `overflow-wrap:anywhere` on every text
					    node inside it. `break-words` was not enough: it breaks between
					    words, and the field somebody actually pasted in was one
					    unbroken 400-character token with no space to break at, which
					    pushed the whole panel wider than the viewport. `anywhere` is
					    the only value that breaks mid-token, and it is applied to text
					    a *society* typed rather than to layout, so nothing that should
					    stay on one line is affected. */}
					<div className="mx-auto -mt-14 min-w-0 max-w-3xl rounded-2xl bg-white p-7 shadow-pop sm:p-9">
						{row.category && (
							<span className="inline-block rounded-full bg-blue/10 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-blue-press">
								{row.category}
							</span>
						)}

						<h1 className="mt-3 text-[28px] font-semibold leading-tight tracking-tight text-ink [overflow-wrap:anywhere] sm:text-[32px]">
							{row.title}
						</h1>

						{row.summary && (
							<p className="mt-3 text-[14.5px] leading-relaxed text-muted [overflow-wrap:anywhere]">
								{row.summary}
							</p>
						)}

						<dl className="mt-7 grid gap-4 border-y border-card-line py-6 sm:grid-cols-2">
							<Fact icon={<Icon.calendar size={16} />} label="When">
								{dateLine(row)}
								{row.start_time && (
									<span className="block text-slate-faint">
										{row.start_time.slice(0, 5)}
										{row.end_time && ` to ${row.end_time.slice(0, 5)}`}
										{row.time_zone && ` · ${row.time_zone}`}
									</span>
								)}
							</Fact>

							<Fact icon={<Icon.pin size={16} />} label="Where">
								{row.venue || row.medium || "To be confirmed"}
								{row.venue_address && (
									<span className="block text-slate-faint">{row.venue_address}</span>
								)}
							</Fact>

							{row.host && (
								<Fact icon={<Icon.people size={16} />} label="Hosted by">
									{row.host}
								</Fact>
							)}

							{/* The two facts a card has no room for and a detail page
							    owes somebody before they set off: whether the society
							    is charging, and by when they have to have registered.
							    Neither is a ticket — see `_as_card`. */}
							{row.registrations_close_at && (
								<Fact icon={<Icon.clock size={16} />} label="Registration">
									{registrationClosed(row) ? (
										<span className="font-semibold text-danger">
											Closed {formatDate(row.registrations_close_at.slice(0, 10))}
										</span>
									) : (
										<>
											Open until {formatDate(row.registrations_close_at.slice(0, 10))}
										</>
									)}
								</Fact>
							)}

							{row.free && (
								<Fact icon={<Icon.card size={16} />} label="Cost">
									Free to attend
								</Fact>
							)}

							{row.medium && (
								<Fact icon={<Icon.compass size={16} />} label="Format">
									{row.medium}
								</Fact>
							)}

							{/* The society's own count, not a ticket count. Everybody who
							    told their branch they mean to be there — which is the
							    number a coordinator plans transport around, and the
							    number a person deciding whether to go actually wants.
							    Names are deliberately not here: saying yes tells the
							    society, not every other volunteer. The full list lives
							    in Buzz, behind the link below. */}
							<Fact icon={<Icon.people size={16} />} label="Going">
								<GoingLine going={row.going} />
							</Fact>
						</dl>

						{/* Buzz's own page copy for the event. Another app's authors, on
						    the desk — the same trust boundary Frappe's own web pages
						    apply to a Text Editor field. */}
						{row.about && (
							<div
								className="article-body mt-7 text-[14.5px] leading-[1.75] text-muted [overflow-wrap:anywhere]"
								dangerouslySetInnerHTML={{ __html: row.about }}
							/>
						)}

						<div className="mt-8">
							{row.href ? (
								<Attend row={row} />
							) : (
								<p className="rounded-xl bg-surface px-4 py-3 text-[12.5px] italic text-slate-faint">
									Registration is not open yet.
								</p>
							)}
						</div>
					</div>
				</article>
			)}
		</>
	);
}

/**
 * How many people have said they will be there, in one sentence.
 *
 * **It is careful about what it claims.** These are people who told the society
 * they mean to come, through this portal — not tickets, not bookings, not
 * confirmed places. Buzz owns all three of those and the card's call to action
 * still goes there. So the wording is "going", never "registered" and never
 * "booked", and the two numbers are allowed to differ without either being
 * wrong.
 *
 * A society renames it like any other label; the count itself is a number and
 * is not content.
 */
function GoingLine({ going }: { going?: number }) {
	if (!going) {
		return (
			<span className="text-slate-faint">
				<EditableText k="portal.events.going.none" fallback="Nobody has said yet" />
			</span>
		);
	}

	return (
		<>
			<span className="font-semibold text-ink">{going}</span>{" "}
			{going === 1 ? (
				<EditableText k="portal.events.going.one" fallback="person is going" />
			) : (
				<EditableText k="portal.events.going.many" fallback="people are going" />
			)}
		</>
	);
}

/** One labelled fact in the detail panel's summary block. */
function Fact({
	icon,
	label,
	children,
}: {
	icon: ReactNode;
	label: string;
	children: ReactNode;
}) {
	return (
		<div className="flex min-w-0 gap-3">
			<span className="mt-0.5 flex-none text-ink" aria-hidden="true">
				{icon}
			</span>
			<div className="min-w-0">
				<dt className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">
					{label}
				</dt>
				{/* A venue name or a host somebody typed as one long token breaks
				    mid-token rather than stretching the grid column it sits in. */}
				<dd className="mt-1 text-[13.5px] leading-relaxed text-slate-strong [overflow-wrap:anywhere]">
					{children}
				</dd>
			</div>
		</div>
	);
}


/**
 * Saying you are coming, and everything you need in order to.
 *
 * The panel a person opens from an event, and it does the two things somebody
 * standing on a page about an event actually wants: it confirms the details
 * they will need on the day — where, when, how to get there — and it gives them
 * a way to keep those details rather than remembering them.
 *
 * **It is careful about what it claims.** It never says a place has been held
 * or a seat reserved, because that is a statement about the society's records
 * and this screen does not write one. What it says is what is true: this is the
 * event, this is where it is, this is when, and here is a way to carry that
 * with you. A person is never told something the system cannot back up.
 *
 * The calendar file is built here rather than fetched, because everything in it
 * is already on the page — and it is the one thing that genuinely puts the
 * event somewhere a person will see it again.
 *
 * **The answer used to live in `localStorage` and now lives on the society's
 * record.** The old note here said the browser key was the seam a doctype would
 * slot into; `VMMS Event Attendance` is that doctype, and what a person notices
 * is that saying yes on a laptop is still true on their phone, and that their
 * branch can see they are expected. The claim the panel makes is unchanged and
 * has to stay unchanged: it says the society has been told, never that a place
 * has been held.
 */
function Attend({ row }: { row: EventCard & { venue_address: string } }) {
	const { answered, pending, toggle } = useAttendance();

	const going = answered.has(row.event);
	const busy = pending === row.event;

	const when = row.multi_day
		? `${formatDate(row.start_date)} to ${formatDate(row.end_date)}`
		: formatDate(row.start_date);

	const time = row.start_time
		? `${row.start_time.slice(0, 5)}${row.end_time ? ` to ${row.end_time.slice(0, 5)}` : ""}`
		: "";

	const place = [row.venue, row.venue_address].filter(Boolean).join(", ");

	const calendar = () => {
		const stamp = (date: string, clock: string) =>
			`${date.replace(/-/g, "")}T${(clock || "09:00:00").replace(/:/g, "")}`;

		const ics = [
			"BEGIN:VCALENDAR",
			"VERSION:2.0",
			"BEGIN:VEVENT",
			`DTSTART:${stamp(row.start_date, row.start_time)}`,
			`DTEND:${stamp(row.end_date || row.start_date, row.end_time || row.start_time)}`,
			`SUMMARY:${row.title}`,
			place ? `LOCATION:${place}` : "",
			"END:VEVENT",
			"END:VCALENDAR",
		]
			.filter(Boolean)
			.join("\r\n");

		const url = URL.createObjectURL(new Blob([ics], { type: "text/calendar" }));
		const link = document.createElement("a");
		link.href = url;
		link.download = `${row.title.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.ics`;
		link.click();
		URL.revokeObjectURL(url);
	};

	if (!going) {
		return (
			<button
				type="button"
				onClick={() => void toggle(row.event)}
				disabled={busy}
				className="inline-flex items-center justify-center rounded-full bg-blue px-6 py-3 text-[13.5px] font-bold text-white transition hover:bg-blue-press disabled:opacity-50"
			>
				{busy ? (
					<EditableText k="portal.events.attending.saving" fallback="Saving…" />
				) : (
					<EditableText k="portal.events.card.action" fallback="Attend" />
				)}
			</button>
		);
	}

	return (
		<div className="rounded-xl border border-card-line bg-surface/60 p-5 sm:p-6">
			<div className="flex flex-wrap items-center gap-2">
				<span className="inline-flex items-center gap-1.5 rounded-full bg-blue/10 px-3 py-1 text-[11.5px] font-bold text-blue">
					<Icon.check size={13} />
					<EditableText k="portal.events.attend.confirmed" fallback="Attending" />
				</span>
			</div>

			<h3 className="mt-4 text-[15px] font-bold tracking-tight text-ink">
				<EditableText k="portal.events.attend.heading" fallback="What you need on the day" />
			</h3>

			<dl className="mt-4 grid gap-3 sm:grid-cols-2">
				<div>
					<dt className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">When</dt>
					<dd className="mt-1 text-[13.5px] font-semibold text-ink">
						{when}
						{time && <span className="block font-normal text-muted">{time}</span>}
						{row.time_zone && (
							<span className="block text-[12px] font-normal text-slate-faint">{row.time_zone}</span>
						)}
					</dd>
				</div>

				<div>
					<dt className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">Where</dt>
					<dd className="mt-1 text-[13.5px] font-semibold text-ink">
						{row.venue || row.medium || "To be confirmed"}
						{row.venue_address && (
							<span className="block font-normal text-muted">{row.venue_address}</span>
						)}
					</dd>
				</div>
			</dl>

			<div className="mt-5 flex flex-wrap gap-2.5">
				<button
					type="button"
					onClick={calendar}
					className="inline-flex items-center gap-2 rounded-full bg-rail px-4 py-2.5 text-[12.5px] font-bold text-white transition hover:bg-blue"
				>
					<Icon.calendar size={15} />
					<EditableText k="portal.events.attend.calendar" fallback="Add to calendar" />
				</button>

				{row.venue_address && (
					<a
						href={`https://www.openstreetmap.org/search?query=${encodeURIComponent(row.venue_address)}`}
						target="_blank"
						rel="noreferrer"
						className="inline-flex items-center gap-2 rounded-full border border-card-line bg-white px-4 py-2.5 text-[12.5px] font-bold text-slate-strong transition hover:border-blue hover:text-ink"
					>
						<Icon.pin size={15} />
						<EditableText k="portal.events.attend.directions" fallback="Find the venue" />
					</a>
				)}
			</div>

			{/* Taking it back, and set apart from the two controls above it because
			    it undoes what they are for. A branch that is expecting somebody
			    needs to be told when they cannot come, so this is as reachable as
			    saying yes was; it is quieter, not hidden. */}
			<div className="mt-5 flex flex-wrap items-center gap-3 border-t border-card-line pt-4">
				<button
					type="button"
					onClick={() => void toggle(row.event)}
					disabled={busy}
					className="text-[12px] font-bold text-slate-faint underline underline-offset-2 transition hover:text-blue disabled:opacity-50"
				>
					{busy ? (
						<EditableText k="portal.events.attending.saving" fallback="Saving…" />
					) : (
						<EditableText k="portal.events.attend.withdraw" fallback="Cancel" />
					)}
				</button>

				<span className="text-[11.5px] text-slate-faint">
					<EditableText
						k="portal.events.attend.claim"
						fallback="Your branch has been told to expect you. This does not hold a place."
					/>
				</span>
			</div>
		</div>
	);
}
