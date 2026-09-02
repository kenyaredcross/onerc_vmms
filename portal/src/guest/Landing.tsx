import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { ContentProvider, useContent } from "../content/ContentProvider";
import { EditableImage, EditableLink, EditableText, useHasContent } from "../content/Editable";
import { EditToolbar } from "../content/EditToolbar";
import { API } from "../lib/api";
import { dateTile, formatClock } from "../lib/format";
import { BrandLockup } from "../ui/brand";
import { Icon } from "../ui/icons";
import { ErrorNote, Spinner } from "../ui/primitives";
import { useSession } from "../lib/session";
import type { EventCard } from "../portal/types";

/**
 * The public landing page, and the site's front door.
 *
 * **Not one sentence of it is in this file.** Every heading, paragraph, button
 * label, statistic, photograph and photo credit is a `VMMS Content Block` read
 * through the provider, and an administrator rewrites any of them in place with
 * the pencil. The society's name and mark are not even that: they come from
 * National Society Settings through `BrandLockup`, because identity has one home
 * and a page holding a second copy of it goes stale the day somebody uploads a
 * logo.
 *
 * What lives here is the composition: a focused editorial hero, live proof,
 * two prominent participation paths, two supporting paths, compact feature
 * stories, public events and one closing invitation. Photography is contained
 * rather than used as a full-width backdrop, so words never depend on a society
 * uploading an image with a convenient empty third. The same structure stacks
 * without horizontal movement from a small phone through desktop.
 */
export default function Landing() {
	// Two surfaces in one request: the page's own slots and the shared chrome
	// that the header and footer draw from.
	return (
		<ContentProvider surface="chrome,landing">
			<LandingBody />
			<EditToolbar />
		</ContentProvider>
	);
}

function LandingBody() {
	const { isLoading, error } = useContent();

	if (isLoading) {
		return (
			<div className="mx-auto max-w-shell px-6">
				<Spinner label="Loading page…" />
			</div>
		);
	}

	if (error) {
		return (
			<div className="mx-auto max-w-shell px-6 py-16">
				<ErrorNote>{error}</ErrorNote>
			</div>
		);
	}

	return (
		<div className="min-h-screen overflow-x-clip bg-white text-ink">
			<Header />
			<main>
				<Hero />
				<StatStrip />
				<CardRow />
				<FeatureGrid />
				<EventsTeaser />
				<ClosingPanel />
			</main>
			<Footer />
		</div>
	);
}

/* ------------------------------------------------------------------ header */

function Header() {
	const { isGuest, user } = useSession();

	return (
		<header className="absolute inset-x-0 top-0 z-30 border-b border-white/20 text-white">
			<div className="mx-auto flex h-[88px] max-w-[1320px] items-center gap-2 px-4 sm:gap-8 sm:px-6">
				<Link to="/" className="flex min-w-0 items-center">
					<BrandLockup tone="dark" />
				</Link>

				<nav
					aria-label="Main"
					className="ml-auto hidden items-center gap-8 lg:flex"
				>
					{[1, 2, 3, 4, 5].map((index) => (
						<EditableLink
							key={index}
							k={`landing.nav.item${index}`}
							className="relative py-2 text-[14px] font-semibold text-white/90 transition hover:text-white"
						/>
					))}
				</nav>

				<div className="ml-auto flex flex-none items-center gap-6">
					{isGuest ? (
						<>
							<EditableLink
								k="chrome.action.signin"
								fallback="Sign in"
								className="relative whitespace-nowrap py-2 text-[14px] font-semibold text-white transition hover:text-white/75"
							/>
							<Link
								to="/join"
								className="inline-flex min-h-[42px] items-center whitespace-nowrap bg-white px-5 text-[14px] font-bold text-rail transition hover:bg-white/90"
							>
								<EditableText k="chrome.action.join" fallback="Join us" />
							</Link>
						</>
					) : (
						// Signed in, so neither control in the design applies: there
						// is nothing to sign into and nothing to join. One button
						// out to the part of the site that is theirs, and the page
						// itself is unchanged — this is still what the society says
						// about itself, and a member is allowed to read it.
						<Link
							to="/dashboard"
							className="whitespace-nowrap rounded-full bg-blue px-4 py-2.5 text-[12.5px] font-bold text-white transition hover:bg-blue-hover"
							title={user ?? undefined}
						>
							Go to dashboard
						</Link>
					)}
				</div>
			</div>
		</header>
	);
}

/* -------------------------------------------------------------------- hero */

function Hero() {
	return (
		<section className="relative flex min-h-[810px] items-center overflow-hidden bg-rail text-white">
			<EditableImage
				k="landing.hero.image"
				className="h-full w-full"
				imgClassName="h-full w-full object-cover"
				objectPosition="center 45%"
				showCredit
				eager
				fill
			/>
			<div aria-hidden="true" className="absolute inset-0 bg-[linear-gradient(90deg,rgba(1,30,65,.98)_0%,rgba(1,30,65,.88)_38%,rgba(1,30,65,.25)_76%,rgba(1,30,65,.18)_100%),linear-gradient(0deg,rgba(1,20,46,.35),transparent_50%)]" />
			<div className="relative z-10 mx-auto w-full max-w-[1200px] px-4 pt-[82px] sm:px-6">
				<div className="max-w-[800px]">
					<div className="mb-5 flex items-center gap-3">
						<span aria-hidden="true" className="h-0.5 w-7 bg-aqua" />
						<EditableText
							k="landing.hero.eyebrow"
							as="div"
							className="relative text-[12px] font-bold uppercase tracking-[.16em] text-white/70"
						/>
					</div>
					<EditableText
						k="landing.hero.headline"
						as="h1"
					className="relative max-w-[9ch] font-display text-[52px] font-bold leading-[.97] tracking-[-.05em] text-white sm:text-[72px] lg:text-[94px]"
					/>
					<EditableText
						k="landing.hero.body"
						as="p"
					className="relative mt-7 max-w-[575px] text-pretty text-[17px] leading-[1.65] text-white/80 sm:text-[19px]"
					/>
					<div className="mt-8 flex flex-wrap items-center gap-3">
						<HeroPrimary />
						<Link
							to="/join?path=member"
							className="inline-flex min-h-[52px] items-center gap-2 whitespace-nowrap border border-white/65 px-6 text-[14px] font-bold text-white transition hover:bg-white/10"
						>
							<EditableText k="landing.hero.cta_secondary" fallback="Explore membership" />
							<Icon.arrow size={15} />
						</Link>
					</div>
				</div>

			</div>
		</section>
	);
}

/**
 * The hero's main call to action.
 *
 * Routed through the client router rather than an anchor, because it lands on
 * the join wizard inside this same app and a full page reload between the two
 * would throw away the prefill the wizard is about to fetch.
 */
function HeroPrimary() {
	return (
		<Link
			to="/join?path=volunteer"
			className="inline-flex min-h-[52px] items-center gap-7 whitespace-nowrap bg-white px-6 text-[14px] font-bold text-rail transition hover:-translate-y-0.5"
		>
			<EditableText k="landing.hero.cta_primary" fallback="Become a volunteer" />
			<Icon.arrow size={15} />
		</Link>
	);
}

/* --------------------------------------------------------------- card row */

function CardRow() {
	return (
		<section id="volunteer" aria-label="Ways to participate" className="bg-surface py-14 sm:py-20">
			<div className="mx-auto max-w-shell px-4 sm:px-6">
				<div className="grid gap-5 lg:grid-cols-2">
					{[1, 2].map((index) => (
						<ParticipationCard key={index} index={index} featured />
					))}
				</div>
				<div className="mt-5 grid gap-5 md:grid-cols-2">
					{[3, 4].map((index) => (
						<ParticipationCard key={index} index={index} />
					))}
				</div>
			</div>
		</section>
	);
}

function ParticipationCard({ index, featured = false }: { index: number; featured?: boolean }) {
	return (
		<article
			id={index === 2 ? "membership" : undefined}
			className={
				featured
					? "group overflow-hidden rounded-2xl bg-white border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)] transition hover:shadow-[0_2px_10px_rgba(30,50,73,0.07)]"
					: "group grid grid-cols-[118px_1fr] overflow-hidden rounded-xl border border-card-line bg-white border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)] transition hover:shadow-[0_2px_10px_rgba(30,50,73,0.07)] sm:grid-cols-[210px_1fr]"
			}
		>
			<EditableImage
				k={`landing.card${index}.image`}
				className={featured ? "h-[220px] w-full sm:h-[310px]" : "h-full min-h-[220px] w-full"}
				imgClassName="transition duration-500 group-hover:scale-[1.02]"
			/>
			<div
				className={
					featured
						? "flex min-h-[215px] flex-col p-6 sm:min-h-[250px] sm:p-9"
						: "flex min-w-0 flex-col p-5 sm:p-7"
				}
			>
				<EditableText
					k={`landing.card${index}.title`}
					as="h2"
					className={
						featured
							? "relative text-[28px] font-semibold leading-tight tracking-[-.025em] text-ink sm:text-[32px]"
							: "relative text-[18px] font-semibold leading-tight tracking-[-.02em] text-ink sm:text-[21px]"
					}
				/>
				<EditableText
					k={`landing.card${index}.body`}
					as="p"
					className="relative mt-3 flex-1 text-pretty text-[13.5px] leading-[1.7] text-muted"
				/>
				<EditableLink
					k={`landing.card${index}.link`}
					chevron
					className="relative mt-6 inline-flex self-start rounded-full bg-blue-soft px-4 py-2.5 text-[12.5px] font-bold text-blue transition hover:bg-blue hover:text-white"
				/>
			</div>
		</article>
	);
}

/* --------------------------------------------------------- feature stories */

function FeatureGrid() {
	return (
		<section className="bg-white py-14 sm:py-20">
			<div className="mx-auto grid max-w-shell gap-5 px-4 sm:px-6 lg:grid-cols-2">
				<StoryCard
					imageKey="landing.band1.image"
					eyebrowKey="landing.band1.eyebrow"
					headingKey="landing.band1.heading"
					bodyKey="landing.band1.body"
					objectPosition="center 40%"
					dark
					actions={
						<EditableLink
							k="landing.band1.cta"
							chevron
							className="relative inline-flex rounded-full bg-white px-5 py-3 text-[13px] font-bold text-ink transition hover:bg-blue-soft"
						/>
					}
				/>
				<StoryCard
					imageKey="landing.band2.image"
					eyebrowKey="landing.band2.eyebrow"
					headingKey="landing.band2.heading"
					bodyKey="landing.band2.body"
					objectPosition="center 55%"
					actions={
						<>
							<Link
								to="/join?path=member"
								className="rounded-full bg-blue px-5 py-3 text-[13px] font-bold text-white transition hover:bg-blue-hover"
							>
								<EditableText k="landing.band2.cta_primary" />
							</Link>
							<EditableLink
								k="landing.band2.cta_secondary"
								chevron
								className="relative inline-flex rounded-full border border-card-line px-5 py-3 text-[13px] font-bold text-ink transition hover:border-blue-line hover:bg-blue-soft"
							/>
						</>
					}
				/>
			</div>
		</section>
	);
}

function StoryCard({
	imageKey,
	eyebrowKey,
	headingKey,
	bodyKey,
	objectPosition,
	actions,
	dark = false,
}: {
	imageKey: string;
	eyebrowKey: string;
	headingKey: string;
	bodyKey: string;
	objectPosition: string;
	actions: ReactNode;
	dark?: boolean;
}) {
	return (
		<article
			className={
				dark
					? "group overflow-hidden rounded-2xl bg-rail text-white border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)]"
					: "group overflow-hidden rounded-2xl border border-card-line bg-white border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)]"
			}
		>
			<EditableImage
				k={imageKey}
				className="h-[210px] w-full overflow-hidden sm:h-[300px]"
				imgClassName="transition duration-500 group-hover:scale-[1.02]"
				objectPosition={objectPosition}
				showCredit
			/>
			<div className="flex min-h-[270px] flex-col p-6 sm:min-h-[310px] sm:p-9">
				<EditableText
					k={eyebrowKey}
					as="div"
					className={
						dark
							? "relative text-[10.5px] font-semibold uppercase tracking-eyebrow text-white/55"
							: "relative text-[10.5px] font-semibold uppercase tracking-eyebrow text-blue"
					}
				/>
				<EditableText
					k={headingKey}
					as="h2"
					className={
						dark
							? "relative mt-3 max-w-[18ch] text-[29px] font-semibold leading-[1.08] tracking-[-.03em] text-white sm:text-[36px]"
							: "relative mt-3 max-w-[18ch] text-[29px] font-semibold leading-[1.08] tracking-[-.03em] text-ink sm:text-[36px]"
					}
				/>
				<EditableText
					k={bodyKey}
					as="p"
					className={
						dark
							? "relative mt-4 flex-1 text-pretty text-[13.5px] leading-[1.75] text-white/65"
							: "relative mt-4 flex-1 text-pretty text-[13.5px] leading-[1.75] text-muted"
					}
				/>
				<div className="mt-7 flex flex-wrap items-center gap-3">{actions}</div>
			</div>
		</article>
	);
}

/* -------------------------------------------------------------- statistics */

/**
 * Four figures, and the first of them nobody types.
 *
 * **Statistic one is the register's own count of volunteers**, from
 * `api/society.py::figures`, and there is no content block behind it — the
 * pencil is absent because there is nothing to edit. A society used to type
 * that number onto the page, which meant it was correct on the day somebody
 * typed it and wrong the day after: every application a branch verifies moves
 * it. The endpoint rounds it down and suffixes it, so the claim on the page
 * stays true between one volunteer and the next; see its docstring for why the
 * rounding is on that side and not this one.
 *
 * Its *caption* is still a block, because what a society calls its volunteers
 * is a society's own word.
 *
 * The other three are unchanged: a society fills in as many as it has numbers
 * for, and an unfilled one is dropped rather than rendered as a gap.
 */
function StatStrip() {
	const has = useHasContent();
	const { editing } = useContent();

	const figures = useFrappeGetCall<{ message: { volunteers: string } }>(
		API.societyFigures,
		undefined,
		"landing:figures",
	);
	const volunteers = figures.data?.message?.volunteers ?? "";

	// The strip waits for the count rather than drawing three figures and then
	// growing a fourth: at four columns that is the whole row re-laying itself
	// under somebody's eyes a moment after the page settles.
	if (figures.isLoading) return null;

	// A society with nobody on the register yet shows no volunteer figure rather
	// than a nought on its own front page — the same rule an unfilled statistic
	// follows. While editing it is drawn regardless, or the caption beside it
	// could never be reworded.
	const shown: Array<{ key: string; live?: string; labelKey: string }> = [];

	if (volunteers || editing) {
		shown.push({ key: "stat1", live: volunteers || "—", labelKey: "landing.stat1.label" });
	}

	for (const index of [2, 3, 4]) {
		if (has(`landing.stat${index}.value`)) {
			shown.push({ key: `stat${index}`, labelKey: `landing.stat${index}.label` });
		}
	}

	if (shown.length === 0) return null;

	return (
		<section className="bg-white px-4 py-8 sm:px-6 sm:py-10">
			<div className="mx-auto grid max-w-shell grid-cols-2 overflow-hidden rounded-2xl bg-rail py-7 text-center border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)] lg:grid-cols-4 lg:py-9">
				{shown.map((entry) => (
					<div
						key={entry.key}
						// Hairlines between the figures rather than around them, so
						// the strip reads as one row of four and not as four cards.
						// Whichever figure ends a row carries none, and that is a
						// different one at two columns than at four.
						//
						// The `:not(:last-child)` is load-bearing. Without it the
						// four-column rule re-drew the border on the second of
						// every pair, which at four columns is also the last
						// figure on the page, and it won on source order rather
						// than on meaning: it left one rule hanging off the right
						// of the strip with nothing after it.
						className="border-r border-white/10 px-3 py-4 last:border-r-0 [&:nth-child(2n)]:border-r-0 lg:py-0 lg:[&:nth-child(2n):not(:last-child)]:border-r"
					>
						{entry.live === undefined ? (
							<EditableText
								k={`landing.${entry.key}.value`}
								as="div"
								className="relative text-[30px] font-semibold leading-none tracking-[-.04em] text-white sm:text-[38px]"
							/>
						) : (
							<div className="text-[30px] font-semibold leading-none tracking-[-.04em] text-white sm:text-[38px]">
								{entry.live}
							</div>
						)}
						<EditableText
							k={entry.labelKey}
							as="div"
							className="relative mt-2 text-[9.5px] font-bold uppercase tracking-[.14em] text-white/45 sm:text-[10.5px]"
						/>
					</div>
				))}
			</div>
		</section>
	);
}

/* ------------------------------------------------------------------ events */

/**
 * The public events teaser: the society's next three, as the society published
 * them.
 *
 * **It is a query now.** It was three rows an administrator typed, with a note
 * in this file saying that was honest because the app had no events. The app has
 * events: `api/events.py::teaser` returns the next three Buzz events with
 * `is_published` set, which is the same flag Buzz's own public pages read, so
 * nothing appears here that the society has not already published to the world.
 * A society that schedules something has it on its front page without opening
 * the content editor.
 *
 * **The typed rows are still the fallback**, drawn only when there is nothing
 * live: a site without Buzz, or a season with nothing in it. A society that has
 * always kept a hand-written teaser keeps it, and one that has not gets a band
 * that hides itself rather than a heading over an empty row.
 *
 * **Three, and then the way in.** A signed-out visitor sees what is open to
 * everybody and then a line saying the rest of the calendar — and saying you
 * mean to be there — belongs to people who have joined. That is not a paywall
 * dressed up: `api/events.py` genuinely refuses a guest everything except these
 * three, and the portal's events screen is where the rest of it lives. The
 * "all events" link is the signed-in half of the same slot, so a visitor is
 * never offered a link to a page that would only bounce them to a login.
 */
function EventsTeaser() {
	const has = useHasContent();
	const { editing } = useContent();
	const { isGuest } = useSession();

	const live = useFrappeGetCall<{ message: { available: boolean; events: EventCard[] } }>(
		API.eventsTeaser,
		undefined,
		"landing:events",
	);

	const events = live.data?.message?.events ?? [];
	const typed = [1, 2, 3].filter((index) => has(`landing.event${index}.date`));

	// Nothing at all until the answer is in. Drawing the typed fallback first and
	// swapping it for live rows a moment later would show a visitor two different
	// sets of events on one visit, and the second would look like a correction.
	if (live.isLoading) return null;
	if (events.length === 0 && typed.length === 0) return null;

	const heading = (
		<div className="mb-8 flex items-end justify-between gap-4">
			<EditableText
				k="landing.events.heading"
				as="h2"
				className="relative max-w-[18ch] text-[30px] font-semibold leading-tight tracking-[-.03em] text-ink sm:text-[38px]"
			/>
			{(!isGuest || editing) && (
				<EditableLink
					k="landing.events.link"
					chevron
					className="relative whitespace-nowrap rounded-full border border-card-line bg-white px-4 py-2.5 text-[12.5px] font-bold text-ink transition hover:border-blue-line hover:bg-blue-soft"
				/>
			)}
		</div>
	);

	if (events.length > 0) {
		return (
			<section id="events" className="bg-surface py-14 sm:py-20">
				<div className="mx-auto max-w-shell px-4 sm:px-6">
					{heading}

					<ul className="grid gap-5 md:grid-cols-3">
						{events.map((row) => (
							<LiveEvent key={row.event} row={row} />
						))}
					</ul>

					{(isGuest || editing) && (
						<p className="mt-7 flex flex-wrap items-baseline gap-x-2 gap-y-1 text-[12.5px] leading-relaxed text-muted">
							<EditableText k="landing.events.more" as="span" className="relative" />
							<Link to="/join?path=volunteer" className="chev font-bold text-blue hover:underline">
								<EditableText k="landing.events.join" fallback="Become a volunteer" />
							</Link>
						</p>
					)}
				</div>
			</section>
		);
	}

	return (
		<section id="events" className="bg-surface py-14 sm:py-20">
			<div className="mx-auto max-w-shell px-4 sm:px-6">
				{heading}

				<ul className="grid gap-5 md:grid-cols-3">
					{typed.map((index) => (
						<li
							key={index}
							className="flex min-h-[185px] items-start gap-4 rounded-xl border border-card-line bg-white p-6 border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)]"
						>
						<EditableText
							k={`landing.event${index}.date`}
							as="div"
							className="relative flex h-14 w-14 flex-none flex-col items-center justify-center rounded-lg bg-blue-soft text-center"
							// One field, two treatments: a small red month over a
							// large day. Anything after the first word is the day,
							// so "AUG 20" and "20 AUG" both read as somebody meant.
							render={(value) => {
								const [month, ...rest] = value.split(/\s+/);
								return (
									<>
									<span className="block text-[9.5px] font-semibold text-blue">
											{month}
										</span>
										{rest.length > 0 && (
											<span className="block text-[26px] font-semibold leading-none text-ink">
												{rest.join(" ")}
											</span>
										)}
									</>
								);
							}}
						/>
						<div className="min-w-0 flex-1">
							<EditableText
								k={`landing.event${index}.title`}
								as="div"
								className="relative text-[15px] font-semibold leading-snug text-ink"
							/>
							<EditableText
								k={`landing.event${index}.meta`}
								as="div"
								className="relative mt-1 text-[12px] text-slate-faint"
							/>
							<EditableLink
								k={`landing.event${index}.cta`}
								chevron
								className="relative mt-4 inline-block text-[12.5px] font-bold text-blue hover:underline"
							/>
						</div>
						</li>
					))}
				</ul>
			</div>
		</section>
	);
}

/**
 * One published event, in the tile the typed rows were designed as.
 *
 * The same card the row above draws, so a society that switches from typed rows
 * to real ones sees its page keep its shape. Only the words are different, and
 * only the label on the link is editable — the date, the title, the time and
 * the place are the event's own, and the destination is Buzz's public page for
 * it, because booking, tickets and check-in are Buzz's and this app does not
 * re-implement one of them.
 *
 * An event Buzz has not finished publishing has no route and therefore no
 * `href`, and the card renders without its link rather than with one to a 404.
 */
function LiveEvent({ row }: { row: EventCard }) {
	const { month, day } = dateTile(row.start_date);
	const place = row.venue || row.medium;
	const meta = [formatClock(row.start_time), place].filter(Boolean).join(" · ");

	return (
		<li className="flex min-h-[185px] items-start gap-4 rounded-xl border border-card-line bg-white p-6 border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)]">
			<div className="flex h-14 w-14 flex-none flex-col items-center justify-center rounded-lg bg-blue-soft text-center">
				<span className="block text-[9.5px] font-semibold text-blue">{month}</span>
				<span className="block text-[26px] font-semibold leading-none text-ink">
					{day}
				</span>
			</div>
			<div className="min-w-0 flex-1">
				<div className="text-[15px] font-semibold leading-snug text-ink">{row.title}</div>
				{meta && <div className="mt-1 text-[12px] text-slate-faint">{meta}</div>}
				{row.href && (
					<a
						href={row.href}
						className="chev mt-4 inline-block text-[12.5px] font-bold text-blue hover:underline"
					>
						<EditableText k="landing.events.action" fallback="Details" />
					</a>
				)}
			</div>
		</li>
	);
}

/* ----------------------------------------------------------------- closing */

function ClosingPanel() {
	const principles = [1, 2, 3, 4, 5, 6, 7];

	return (
		<section className="bg-white px-4 py-14 sm:px-6 sm:py-20">
			<div className="relative mx-auto max-w-shell overflow-hidden rounded-2xl bg-rail px-7 py-10 shadow-shell sm:px-12 sm:py-14 lg:px-16">
				<div
					aria-hidden="true"
					className="pointer-events-none absolute -right-24 -top-36 h-80 w-80 rounded-full border-[54px] border-blue/20"
				/>
				<div className="relative grid items-center gap-8 lg:grid-cols-[1fr_auto] lg:gap-16">
					<div>
						<EditableText
							k="landing.cta.heading"
							as="h2"
							className="relative max-w-[16ch] text-[34px] font-semibold leading-[1.05] tracking-[-.035em] text-white sm:text-[46px]"
						/>
						<EditableText
							k="landing.cta.body"
							as="p"
							className="relative mt-4 max-w-[570px] text-[14px] leading-[1.75] text-white/65 sm:text-[15px]"
						/>
					</div>
					<Link
						to="/join"
						className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full bg-blue px-6 py-3.5 text-[14px] font-bold text-white transition hover:bg-blue-hover"
					>
						<EditableText k="landing.cta.button" fallback="Join us today" />
						<Icon.arrow size={16} />
					</Link>
				</div>

				<ul className="relative mt-10 flex flex-wrap items-center gap-x-6 gap-y-3 border-t border-white/10 pt-6">
					{principles.map((index) => (
						<li key={index}>
							<EditableText
								k={`landing.principle${index}`}
								as="span"
								className="relative text-[9.5px] font-bold uppercase tracking-[.12em] text-white/40"
							/>
						</li>
					))}
				</ul>
			</div>
		</section>
	);
}

/* ------------------------------------------------------------------ footer */

function Footer() {
	return (
		<footer className="border-t border-white/10 bg-rail text-white">
			{/* One row of three at desktop, as the design draws it. It only stays
			    one row because the society's block is the one allowed to shrink:
			    an emergency number is longer in some societies than in others,
			    and the alternative to letting it wrap inside its own column was
			    the copyright dropping onto a line of its own. */}
			<div className="mx-auto flex max-w-shell flex-wrap items-start justify-between gap-x-10 gap-y-7 px-4 py-10 sm:px-6 lg:flex-nowrap">
				<div className="flex min-w-0 items-center gap-[9px]">
					{/* The society's own mark and name, from National Society
					    Settings. The footer used to name the product beside a
					    generic cross, which put a vendor's name on a society's
					    page. Nothing in this app is branded but the society. */}
					<BrandLockup size="sm" tone="dark" />
					<EditableText
						k="landing.footer.emergency"
						as="span"
						className="relative border-l border-white/10 pl-2.5 text-[11px] leading-relaxed text-white/45"
					/>
				</div>

				<nav
					aria-label="Footer"
					className="flex w-full min-w-0 flex-wrap gap-x-[22px] gap-y-2 lg:w-auto lg:flex-none"
				>
					{[1, 2, 3, 4, 5, 6].map((index) => (
						<EditableLink
							key={index}
							k={`landing.footer.link${index}`}
							className="relative text-[11.5px] text-white/55 transition hover:text-white"
						/>
					))}
				</nav>

				<EditableText
					k="landing.footer.copyright"
					as="span"
					className="relative flex-none whitespace-nowrap text-[10.5px] text-white/30"
				/>
			</div>
		</footer>
	);
}
