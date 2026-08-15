import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { ContentProvider, useContent } from "../content/ContentProvider";
import { EditableImage, EditableLink, EditableText, useHasContent } from "../content/Editable";
import { EditToolbar } from "../content/EditToolbar";
import { BrandLockup } from "../ui/brand";
import { ErrorNote, Spinner } from "../ui/primitives";
import { useSession } from "../lib/session";

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
 * What lives here is the composition — which slot sits where, how the bands
 * stack, where the gradient falls across a photograph — and it is **option 7a of
 * the design canvas, followed to the measurement**: a 58px header, a 560px hero
 * under a left-weighted scrim with an overlay card, a four-up card row, photo
 * bands at 480 and 440 that alternate which edge the words sit against, a
 * divided statistics strip on `#F4F6FA`, a three-up events row, the navy closing
 * panel with the seven Fundamental Principles, and a single-row footer.
 *
 * The numbers below look arbitrary because they are: they are 7a's, and the
 * whole value of matching a design exactly is that nobody has to argue about
 * whether 18 pixels was meant to be 20.
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
		<div className="bg-white">
			<Header />
			<Hero />
			<CardRow />
			<OpportunitiesBand />
			<StatStrip />
			<MembershipBand />
			<EventsTeaser />
			<ClosingPanel />
			<Footer />
		</div>
	);
}

/* ------------------------------------------------------------------ header */

function Header() {
	const { isGuest, user } = useSession();

	return (
		<header className="sticky top-0 z-30 border-b border-hairline-soft bg-white/95 backdrop-blur">
			<div className="mx-auto flex h-[58px] max-w-shell items-center gap-[22px] px-6">
				<Link to="/" className="flex items-center">
					<BrandLockup />
				</Link>

				<nav aria-label="Main" className="hidden items-center lg:flex">
					{[1, 2, 3, 4, 5].map((index) => (
						<EditableLink
							key={index}
							k={`landing.nav.item${index}`}
							className="relative px-3 py-2 text-[12.5px] font-medium text-slate-strong hover:text-navy"
						/>
					))}
				</nav>

				<div className="ml-auto flex items-center gap-2">
					{isGuest ? (
						<>
							<EditableLink
								k="chrome.action.signin"
								fallback="Sign in"
								className="relative whitespace-nowrap px-3 py-2 text-[12.5px] font-semibold text-navy hover:underline"
							/>
							<Link
								to="/join"
								className="whitespace-nowrap rounded-[5px] bg-navy px-4 py-2 text-[12.5px] font-bold text-white transition hover:bg-navy/90"
							>
								<EditableText k="chrome.action.join" fallback="Join free" />
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
							className="whitespace-nowrap rounded-[5px] bg-navy px-4 py-2 text-[12.5px] font-bold text-white transition hover:bg-navy/90"
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
		<section className="relative h-[500px] overflow-hidden md:h-[560px]">
			<EditableImage
				k="landing.hero.image"
				fill
				objectPosition="center 24%"
				showCredit
				eager
			/>
			{/* Left-weighted scrim so the overlay card stays legible whatever
			    photograph a society uploads. Pointer-events off, or it would eat
			    the clicks meant for the pencil on the image beneath it. */}
			<div
				aria-hidden="true"
				className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,rgba(1,30,65,.55)_0%,rgba(1,30,65,.18)_44%,rgba(1,30,65,0)_68%)]"
			/>

			<div className="relative mx-auto flex h-full max-w-shell items-center px-6">
				<div className="max-w-[460px] rounded-[6px] bg-white/[.97] p-7 shadow-hero sm:px-[42px] sm:py-10">
					<EditableText k="landing.hero.eyebrow" as="div" className="eyebrow relative mb-3" />
					<EditableText
						k="landing.hero.headline"
						as="h1"
						className="relative mb-3.5 font-display text-[32px] font-extrabold leading-[1.05] tracking-[-.025em] text-ink sm:text-[40px]"
					/>
					<EditableText
						k="landing.hero.body"
						as="p"
						className="relative mb-6 text-pretty text-[14px] leading-[1.65] text-slate-body"
					/>
					<div className="flex flex-wrap items-center gap-2.5">
						<HeroPrimary />
						<EditableLink
							k="landing.hero.cta_secondary"
							chevron
							className="relative whitespace-nowrap px-2 text-[13px] font-bold text-navy hover:underline"
						/>
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
			className="whitespace-nowrap rounded-[5px] bg-signal px-[22px] py-3 font-display text-[13.5px] font-bold text-white transition hover:bg-signal-dark"
		>
			<EditableText k="landing.hero.cta_primary" fallback="Become a volunteer" />
		</Link>
	);
}

/* --------------------------------------------------------------- card row */

function CardRow() {
	return (
		<section className="mx-auto max-w-shell px-6 py-16">
			<div className="grid gap-[18px] sm:grid-cols-2 lg:grid-cols-4">
				{[1, 2, 3, 4].map((index) => (
					<article
						key={index}
						className="flex flex-col overflow-hidden rounded-[6px] border border-hairline bg-white transition hover:shadow-card"
					>
						<EditableImage k={`landing.card${index}.image`} className="h-[148px] w-full" />
						<div className="flex flex-1 flex-col px-[22px] pb-[22px] pt-5">
							<EditableText
								k={`landing.card${index}.title`}
								as="h3"
								className="relative mb-[7px] font-display text-[16px] font-bold text-ink"
							/>
							<EditableText
								k={`landing.card${index}.body`}
								as="p"
								className="relative flex-1 text-pretty text-[12.5px] leading-[1.6] text-slate-body"
							/>
							<EditableLink
								k={`landing.card${index}.link`}
								chevron
								className="relative mt-3.5 text-[12.5px] font-bold text-navy hover:underline"
							/>
						</div>
					</article>
				))}
			</div>
		</section>
	);
}

/* ------------------------------------------------------------- photo bands */

/**
 * A full-bleed photograph with a block of words held against one edge.
 *
 * Everything that differs between the two bands is a prop, because in 7a they
 * differ in more than which side the text is on: the heights, the focal points,
 * the falloff of the scrim and the shape of the buttons are all different, and a
 * single "align" flag would have quietly averaged them.
 *
 * The credit goes in the corner opposite the words. `showCredit` puts it there
 * whatever the society uploaded, which is the point of carrying a licence in an
 * editable field rather than burning it into the file.
 */
function PhotoBand({
	imageKey,
	eyebrowKey,
	headingKey,
	bodyKey,
	align,
	height,
	objectPosition,
	scrim,
	actions,
	anchor,
}: {
	imageKey: string;
	eyebrowKey: string;
	headingKey: string;
	bodyKey: string;
	align: "left" | "right";
	height: string;
	objectPosition: string;
	scrim: string;
	actions: ReactNode;
	/**
	 * The `id` the top navigation jumps to.
	 *
	 * The nav has always offered "Volunteering" and "Membership"; the sections
	 * they name had no `id` on them, so every one of those links did nothing at
	 * all. Naming the anchor at the call site rather than deriving it from the
	 * content key keeps it something a person chose: the key is `band1`, which
	 * is a position on the page, and `#volunteer` is what the band is about.
	 */
	anchor?: string;
}) {
	const right = align === "right";

	return (
		<section id={anchor} className={`relative overflow-hidden ${height}`}>
			<EditableImage
				k={imageKey}
				fill
				objectPosition={objectPosition}
				showCredit
				creditSide={right ? "left" : "right"}
			/>
			<div aria-hidden="true" className={`pointer-events-none absolute inset-0 ${scrim}`} />

			<div className="relative mx-auto flex h-full max-w-shell items-center px-6">
				<div className={right ? "ml-auto max-w-[420px] text-white" : "max-w-[420px] text-white"}>
					<EditableText
						k={eyebrowKey}
						as="div"
						className="relative mb-3 text-[10px] font-extrabold uppercase tracking-eyebrow text-white/75"
					/>
					<EditableText
						k={headingKey}
						as="h2"
						className="relative mb-3.5 font-display text-[28px] font-extrabold leading-[1.08] tracking-[-.02em] sm:text-[36px]"
					/>
					<EditableText
						k={bodyKey}
						as="p"
						className="relative mb-6 text-pretty text-[14px] leading-[1.65] text-white/85"
					/>
					<div className="flex flex-wrap items-center gap-2.5">{actions}</div>
				</div>
			</div>
		</section>
	);
}

/** The first band: words on the right, one solid white button. */
function OpportunitiesBand() {
	return (
		<PhotoBand
			anchor="volunteer"
			imageKey="landing.band1.image"
			eyebrowKey="landing.band1.eyebrow"
			headingKey="landing.band1.heading"
			bodyKey="landing.band1.body"
			align="right"
			height="h-[440px] md:h-[480px]"
			objectPosition="center 40%"
			scrim="bg-[linear-gradient(90deg,rgba(1,30,65,0)_40%,rgba(1,30,65,.42)_68%,rgba(1,30,65,.72))]"
			actions={
				<EditableLink
					k="landing.band1.cta"
					chevron
					className="relative inline-block whitespace-nowrap rounded-[5px] bg-white px-[22px] py-3 text-[13.5px] font-bold text-navy transition hover:bg-white/90"
				/>
			}
		/>
	);
}

/** The second band: words on the left, a signal button and an outlined one. */
function MembershipBand() {
	return (
		<PhotoBand
			anchor="membership"
			imageKey="landing.band2.image"
			eyebrowKey="landing.band2.eyebrow"
			headingKey="landing.band2.heading"
			bodyKey="landing.band2.body"
			align="left"
			height="h-[420px] md:h-[440px]"
			objectPosition="center 55%"
			scrim="bg-[linear-gradient(90deg,rgba(1,30,65,.72),rgba(1,30,65,.4)_38%,rgba(1,30,65,0)_62%)]"
			actions={
				<>
					<Link
						to="/join?path=member"
						className="whitespace-nowrap rounded-[5px] bg-signal px-[22px] py-3 font-display text-[13.5px] font-bold text-white transition hover:bg-signal-dark"
					>
						<EditableText k="landing.band2.cta_primary" />
					</Link>
					<EditableLink
						k="landing.band2.cta_secondary"
						chevron
						className="relative inline-block whitespace-nowrap rounded-[5px] border border-white/55 px-[22px] py-3 text-[13.5px] font-semibold text-white transition hover:bg-white/10"
					/>
				</>
			}
		/>
	);
}

/* -------------------------------------------------------------- statistics */

function StatStrip() {
	// Four slots, and a society fills in as many as it has numbers for. An
	// unfilled one is dropped rather than rendered as a gap, except while
	// editing, when it has to be visible to be fillable.
	const has = useHasContent();
	const shown = [1, 2, 3, 4].filter((index) => has(`landing.stat${index}.value`));

	if (shown.length === 0) return null;

	return (
		<section className="bg-page">
			<div className="mx-auto grid max-w-shell grid-cols-2 gap-y-10 px-6 py-[72px] text-center lg:grid-cols-4 lg:gap-y-0">
				{shown.map((index) => (
					<div
						key={index}
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
						className="border-r border-hairline-pale px-6 last:border-r-0 [&:nth-child(2n)]:border-r-0 lg:[&:nth-child(2n):not(:last-child)]:border-r"
					>
						<EditableText
							k={`landing.stat${index}.value`}
							as="div"
							className="relative font-display text-[34px] font-extrabold leading-none tracking-[-.03em] text-navy sm:text-[38px]"
						/>
						<EditableText
							k={`landing.stat${index}.label`}
							as="div"
							className="relative mt-2 text-[11px] font-bold uppercase tracking-[.12em] text-slate-faint"
						/>
					</div>
				))}
			</div>
		</section>
	);
}

/* ------------------------------------------------------------------ events */

/**
 * The public events teaser.
 *
 * Typed by an administrator, not queried, and that is deliberate: this app has
 * no event doctype. Three invented rows would be a lie on the front page of a
 * national society; three rows somebody wrote is a poster. If an events module
 * is built later, this section is what it replaces.
 */
function EventsTeaser() {
	const has = useHasContent();
	const shown = [1, 2, 3].filter((index) => has(`landing.event${index}.date`));

	if (shown.length === 0) return null;

	return (
		<section id="events" className="mx-auto max-w-shell px-6 py-16">
			<div className="mb-[26px] flex items-baseline justify-between gap-4">
				<EditableText
					k="landing.events.heading"
					as="h2"
					className="relative font-display text-[24px] font-extrabold tracking-[-.02em] text-ink sm:text-[28px]"
				/>
				<EditableLink
					k="landing.events.link"
					chevron
					className="relative whitespace-nowrap text-[13px] font-bold text-navy hover:underline"
				/>
			</div>

			<ul className="grid gap-[18px] md:grid-cols-3">
				{shown.map((index) => (
					<li
						key={index}
						className="flex items-start gap-4 rounded-[6px] border border-hairline bg-white px-[22px] py-5"
					>
						<EditableText
							k={`landing.event${index}.date`}
							as="div"
							className="relative flex-none text-center"
							// One field, two treatments: a small red month over a
							// large day. Anything after the first word is the day,
							// so "AUG 20" and "20 AUG" both read as somebody meant.
							render={(value) => {
								const [month, ...rest] = value.split(/\s+/);
								return (
									<>
										<span className="block text-[9.5px] font-extrabold text-signal">
											{month}
										</span>
										{rest.length > 0 && (
											<span className="block font-display text-[26px] font-extrabold leading-none text-ink">
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
								className="relative font-display text-[15px] font-bold text-ink"
							/>
							<EditableText
								k={`landing.event${index}.meta`}
								as="div"
								className="relative mt-1 text-[12px] text-slate-faint"
							/>
							<EditableLink
								k={`landing.event${index}.cta`}
								chevron
								className="relative mt-2.5 inline-block text-[12.5px] font-bold text-navy hover:underline"
							/>
						</div>
					</li>
				))}
			</ul>
		</section>
	);
}

/* ----------------------------------------------------------------- closing */

function ClosingPanel() {
	const principles = [1, 2, 3, 4, 5, 6, 7];

	return (
		<section className="bg-navy">
			<div className="mx-auto max-w-shell px-6 py-16 text-center">
				<EditableText
					k="landing.cta.heading"
					as="h2"
					className="relative mx-auto mb-2.5 font-display text-[27px] font-extrabold tracking-[-.02em] text-white sm:text-[32px]"
				/>
				<EditableText
					k="landing.cta.body"
					as="p"
					className="relative mx-auto mb-6 max-w-[420px] text-[14px] leading-[1.65] text-white/70"
				/>
				<Link
					to="/join"
					className="inline-block rounded-[5px] bg-signal px-[26px] py-[13px] font-display text-[14px] font-bold text-white transition hover:bg-signal-dark"
				>
					<EditableText k="landing.cta.button" fallback="Join free today" />
				</Link>

				<ul className="mt-11 flex flex-wrap items-center justify-center gap-x-[26px] gap-y-3 border-t border-white/[.14] pt-[22px]">
					{principles.map((index) => (
						<li key={index}>
							<EditableText
								k={`landing.principle${index}`}
								as="span"
								className="relative text-[10.5px] font-bold uppercase tracking-[.1em] text-white/50"
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
		<footer className="border-t border-hairline-soft bg-white">
			{/* One row of three at desktop, as the design draws it. It only stays
			    one row because the society's block is the one allowed to shrink:
			    an emergency number is longer in some societies than in others,
			    and the alternative to letting it wrap inside its own column was
			    the copyright dropping onto a line of its own. */}
			<div className="mx-auto flex max-w-shell flex-wrap items-start justify-between gap-x-10 gap-y-5 px-6 py-9 lg:flex-nowrap">
				<div className="flex min-w-0 items-center gap-[9px]">
					{/* The society's own mark and name, from National Society
					    Settings. The footer used to name the product beside a
					    generic cross, which put a vendor's name on a society's
					    page. Nothing in this app is branded but the society. */}
					<BrandLockup size="sm" />
					<EditableText
						k="landing.footer.emergency"
						as="span"
						className="relative border-l border-hairline-soft pl-2.5 text-[11px] leading-relaxed text-slate-faint"
					/>
				</div>

				<nav aria-label="Footer" className="flex flex-none flex-wrap gap-x-[22px] gap-y-2">
					{[1, 2, 3, 4, 5, 6].map((index) => (
						<EditableLink
							key={index}
							k={`landing.footer.link${index}`}
							className="relative text-[11.5px] text-slate-body hover:text-navy"
						/>
					))}
				</nav>

				<EditableText
					k="landing.footer.copyright"
					as="span"
					className="relative flex-none whitespace-nowrap text-[10.5px] text-slate-mute"
				/>
			</div>
		</footer>
	);
}
