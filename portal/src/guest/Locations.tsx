import { useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { ContentProvider } from "../content/ContentProvider";
import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { BrandLockup } from "../ui/brand";
import { CountyMap, MAP_NAVY, type CountyShapes } from "../ui/CountyMap";
import { Icon } from "../ui/icons";
import { JoinLink } from "../ui/JoinLink";
import { Card, Empty, ErrorNote, PageHeading, Spinner, cx } from "../ui/primitives";
import { useSession } from "../lib/session";
import type { BranchLocation, Standing } from "../portal/types";
import { LanguageSwitcher } from "../i18n/LanguageSwitcher";

/**
 * Where the society can be found.
 *
 * **A public page, and that is the reason it exists.** `api/locations.py::
 * published` is guest-readable, like `content.surface` and `society.branding`
 * before it, because somebody looking for their nearest office does not have an
 * account yet and quite often is looking in order to come and get one. The
 * boundary is `is_published` on each location, ticked by a coordinator on a
 * form, and nothing in this file decides what is shown.
 *
 * **One branch at a time, found by county.** The question is "where is the
 * office near me", so the page is a map of the counties and a search box, and
 * it shows the branch for the county chosen. Headquarters (a location placed
 * at the top of the society's tree) is shown until somebody chooses. A list of
 * every branch is what a reader would have to scroll to answer the same
 * question, so there is none.
 *
 * **The map is the society's own boundary file**, the same drawing as the
 * console's Region and National tabs, served without figures. Where no file is
 * attached each county is a dot; where no places are set up there is no map
 * and the search still works.
 *
 * The chosen county is in the address, so a branch can be sent as a link.
 */
export default function Locations() {
	return (
		<ContentProvider surface="chrome,locations">
			<div className="min-h-screen bg-canvas">
				<header className="sticky top-0 z-30 border-b border-card-line bg-white/95 backdrop-blur">
					<div className="mx-auto flex max-w-shell items-center justify-between gap-4 px-5 py-3">
						<Link to="/">
							<BrandLockup />
						</Link>
						<LanguageSwitcher />
					</div>
				</header>

				<main className="mx-auto max-w-shell px-5 py-8">
					<Directory />
				</main>
			</div>
		</ContentProvider>
	);
}

type Published = { count: number; locations: BranchLocation[] };
type Shapes = CountyShapes & { labels?: Record<string, string>; regions?: Record<string, string> };

const WITH_BRANCH = "#F2A0A8";
const WITH_BRANCH_HOVER = "#E2606D";
const WITHOUT = "#E8EDF2";

export function Directory() {
	const published = useFrappeGetCall<{ message: Published }>(API.publishedLocations, undefined, "locations:published");
	const map = useFrappeGetCall<{ message: Shapes }>(API.countyMap, undefined, "locations:county_map");
	// Where somebody signed in already belongs, so a card says "Your branch"
	// rather than offering a form they have no reason to fill in.
	const { isGuest } = useSession();
	const standing = useFrappeGetCall<{ message: Standing }>(
		API.myStanding,
		undefined,
		isGuest ? null : "locations:my_standing",
	).data?.message ?? null;
	const [params, setParams] = useSearchParams();
	const county = params.get("county");

	const locations = useMemo(() => published.data?.message?.locations ?? [], [published.data]);
	const shapes = map.data?.message;
	const labels = useMemo(() => shapes?.labels ?? {}, [shapes]);

	const byCounty = useMemo(() => group(locations.filter(isBranch), (location) => location.county), [locations]);
	const byRegion = useMemo(
		() => group(locations.filter((location) => location.is_regional), (location) => location.region),
		[locations],
	);

	const headquarters = locations.filter((location) => location.is_headquarters);

	const choose = (name: string | null) => {
		const next = new URLSearchParams(params);
		if (name) next.set("county", name);
		else next.delete("county");
		setParams(next, { replace: true });
	};

	if (published.isLoading) return <Spinner label="Loading locations…" />;
	if (published.error) return <ErrorNote>{errorMessage(published.error)}</ErrorNote>;

	const countyLabel = county ? labels[county] ?? byCounty.get(county)?.[0]?.county_label ?? "" : "";
	const shown = county ? byCounty.get(county) ?? [] : headquarters;
	// The regional office for the chosen county, shown under its own branch.
	const regional = county ? byRegion.get(shapes?.regions?.[county] ?? "") ?? [] : [];

	return (
		<>
			<PageHeading
				eyebrow={<EditableText k="locations.eyebrow" fallback="Find us" />}
				title={<EditableText k="locations.heading" fallback="Where to find us" />}
			/>

			{locations.length === 0 ? (
				<Empty title="No locations have been published yet">
					Offices appear here once they are added and marked to show on the public map.
				</Empty>
			) : (
				<div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,420px)]">
					<Card>
						{shapes && shapes.shapes.length > 0 ? (
							<>
								<CountyMap
									shapes={shapes}
									label="Map of the counties. Choose one to see its branch."
									interactive={() => true}
									onSelect={(name) => choose(name === county ? null : name)}
									fill={(name, hovered) => {
										if (name === county) return MAP_NAVY;
										if (!byCounty.has(name)) return hovered ? "#CBD5DF" : WITHOUT;
										return hovered ? WITH_BRANCH_HOVER : WITH_BRANCH;
									}}
									describe={(name) => `${labels[name] ?? name}: ${branchNames(byCounty.get(name))}`}
									readOut={(name) => (
										<>
											<div className="text-[13px] font-semibold">{labels[name] ?? name}</div>
											<div className="text-white/75">{branchNames(byCounty.get(name))}</div>
										</>
									)}
								/>
								<div className="mt-4 flex flex-wrap gap-x-5 gap-y-1.5 text-[12px] text-muted">
									<Swatch colour={WITH_BRANCH} label="Has a branch office" />
									<Swatch colour={MAP_NAVY} label="Chosen" />
								</div>
								{shapes.credit && <p className="mt-2 text-[11px] text-slate-faint">{shapes.credit}</p>}
							</>
						) : map.isLoading ? (
							<Spinner label="Drawing the map…" />
						) : (
							<p className="py-10 text-center text-[13px] text-muted">Search for your county to find its branch.</p>
						)}
					</Card>

					{/* First on a phone: somebody looking for a branch wants the search
					    box and the answer, and the map is below them there. Beside the
					    map from the large breakpoint up. */}
					<div className="order-first space-y-4 lg:order-none">
						<Search
							locations={locations}
							labels={labels}
							onChoose={(name) => choose(name)}
						/>

						<NearMe branches={locations.filter(isBranch)} onFound={(name) => choose(name)} />

						<div>
							<div className="mb-2 flex items-baseline justify-between gap-3">
								<h3 className="text-[13px] font-semibold uppercase tracking-[0.07em] text-rail-label">
									{county ? countyLabel : "Headquarters"}
								</h3>
								{county && (
									<button
										type="button"
										className="text-[12.5px] font-semibold text-ink underline underline-offset-2"
										onClick={() => choose(null)}
									>
										Show headquarters
									</button>
								)}
							</div>

							{shown.length > 0 ? (
								<ul className="space-y-3">
									{shown.map((location) => (
										<li key={location.name}>
											<LocationCard location={location} join standing={standing} />
										</li>
									))}
								</ul>
							) : (
								<Card>
									<p className="text-[13px] text-muted">
										{county
											? `No branch office is listed for ${countyLabel} yet.`
											: "Choose a county on the map, or search for it, to see its branch office."}
									</p>
								</Card>
							)}
						</div>

						{regional.length > 0 && (
							<div>
								<h3 className="mb-2 text-[13px] font-semibold uppercase tracking-[0.07em] text-rail-label">
									Regional office · {regional[0].region_label}
								</h3>
								<ul className="space-y-3">
									{regional.map((location) => (
										<li key={location.name}>
											<LocationCard location={location} />
										</li>
									))}
								</ul>
							</div>
						)}
					</div>
				</div>
			)}
		</>
	);
}

/**
 * "Find my nearest branch", from where the phone says it is.
 *
 * The position is used in the browser and goes nowhere else: the nearest
 * branch is worked out here from the pins the page already has. Drawn only
 * when the browser can locate and at least one branch is pinned. A refusal or
 * a failure says so plainly and leaves the search box to do the job.
 */
function NearMe({ branches, onFound }: { branches: BranchLocation[]; onFound: (county: string) => void }) {
	const [state, setState] = useState<"idle" | "locating" | "failed">("idle");
	const [found, setFound] = useState<{ name: string; km: number } | null>(null);
	const pinned = branches.filter((branch) => branch.has_point && branch.county);

	if (!pinned.length || typeof navigator === "undefined" || !navigator.geolocation) return null;

	const locate = () => {
		setState("locating");
		setFound(null);
		navigator.geolocation.getCurrentPosition(
			(position) => {
				const here = { latitude: position.coords.latitude, longitude: position.coords.longitude };
				let best: { branch: BranchLocation; km: number } | null = null;

				for (const branch of pinned) {
					const km = distanceKm(here, { latitude: branch.latitude ?? 0, longitude: branch.longitude ?? 0 });
					if (!best || km < best.km) best = { branch, km };
				}

				if (best?.branch.county) {
					onFound(best.branch.county);
					setFound({ name: best.branch.location_name, km: best.km });
				}
				setState("idle");
			},
			() => setState("failed"),
			{ enableHighAccuracy: false, timeout: 15000, maximumAge: 600000 },
		);
	};

	return (
		<div className="text-[13px]">
			<button
				type="button"
				onClick={locate}
				disabled={state === "locating"}
				className="inline-flex items-center gap-1.5 font-semibold text-ink underline-offset-2 hover:underline disabled:opacity-60"
			>
				<Icon.compass size={16} />
				{state === "locating" ? "Finding where you are…" : "Find my nearest branch"}
			</button>
			{found && (
				<p className="mt-1 text-muted" role="status">
					Nearest to you: {found.name}, about {found.km < 1 ? "1" : Math.round(found.km)} km away.
				</p>
			)}
			{state === "failed" && (
				<p className="mt-1 text-muted" role="status">
					We couldn't tell where you are. Search for your county instead.
				</p>
			)}
		</div>
	);
}

/** Straight-line distance, which is what "nearest" can honestly mean here. */
function distanceKm(a: { latitude: number; longitude: number }, b: { latitude: number; longitude: number }): number {
	const radians = (degrees: number) => (degrees * Math.PI) / 180;
	const dLat = radians(b.latitude - a.latitude);
	const dLon = radians(b.longitude - a.longitude);
	const h =
		Math.sin(dLat / 2) ** 2 + Math.cos(radians(a.latitude)) * Math.cos(radians(b.latitude)) * Math.sin(dLon / 2) ** 2;
	return 6371 * 2 * Math.asin(Math.sqrt(h));
}

/** A county's own branch: not headquarters, not a regional office. */
function isBranch(location: BranchLocation): boolean {
	return Boolean(location.county) && !location.is_headquarters && !location.is_regional;
}

function group(rows: BranchLocation[], key: (row: BranchLocation) => string | undefined): Map<string, BranchLocation[]> {
	const grouped = new Map<string, BranchLocation[]>();
	for (const row of rows) {
		const value = key(row);
		if (value) grouped.set(value, [...(grouped.get(value) ?? []), row]);
	}
	return grouped;
}

/**
 * Finding a branch by typing.
 *
 * Matches a county's name or a branch's own name, and offers at most eight.
 * A combobox in the ARIA sense: the arrow keys move through the suggestions,
 * Enter chooses, Escape closes.
 */
function Search({
	locations,
	labels,
	onChoose,
}: {
	locations: BranchLocation[];
	labels: Record<string, string>;
	onChoose: (county: string) => void;
}) {
	const [text, setText] = useState("");
	const [open, setOpen] = useState(false);
	const [active, setActive] = useState(0);
	const input = useRef<HTMLInputElement>(null);

	const options = useMemo(() => {
		const query = text.trim().toLowerCase();
		if (!query) return [];

		const seen = new Set<string>();
		const found: Array<{ county: string; label: string; detail: string }> = [];

		// Counties first, then branches whose name matches but whose county did not.
		for (const [name, label] of Object.entries(labels)) {
			if (label.toLowerCase().includes(query)) {
				const branch = locations.find((location) => location.county === name && isBranch(location));
				found.push({ county: name, label, detail: branch?.location_name ?? "No branch office listed" });
				seen.add(name);
			}
		}

		for (const location of locations) {
			if (!isBranch(location) || seen.has(location.county ?? "")) continue;
			if (location.location_name.toLowerCase().includes(query)) {
				found.push({ county: location.county ?? "", label: location.location_name, detail: location.county_label ?? "" });
				seen.add(location.county ?? "");
			}
		}

		return found.sort((a, b) => a.label.localeCompare(b.label)).slice(0, 8);
	}, [text, labels, locations]);

	const pick = (index: number) => {
		const option = options[index];
		if (!option) return;
		onChoose(option.county);
		setText("");
		setOpen(false);
		input.current?.blur();
	};

	const keys = (event: KeyboardEvent<HTMLInputElement>) => {
		if (event.key === "ArrowDown") {
			event.preventDefault();
			setOpen(true);
			setActive((index) => Math.min(index + 1, options.length - 1));
		} else if (event.key === "ArrowUp") {
			event.preventDefault();
			setActive((index) => Math.max(index - 1, 0));
		} else if (event.key === "Enter") {
			event.preventDefault();
			pick(active);
		} else if (event.key === "Escape") {
			setOpen(false);
		}
	};

	const showing = open && options.length > 0;

	return (
		<div className="relative">
			<label className="sr-only" htmlFor="location-search">
				Search for a county or branch
			</label>
			<div className="flex items-center gap-2 rounded-xl border border-card-line bg-white px-3.5 py-2.5 focus-within:border-blue">
				<Icon.search size={17} className="text-slate-faint" />
				<input
					ref={input}
					id="location-search"
					type="search"
					role="combobox"
					aria-expanded={showing}
					aria-controls="location-search-options"
					aria-activedescendant={showing ? `location-option-${active}` : undefined}
					autoComplete="off"
					placeholder="Search for your county or branch"
					className="w-full bg-transparent text-[14px] text-ink outline-none placeholder:text-slate-faint"
					value={text}
					onChange={(event) => {
						setText(event.target.value);
						setActive(0);
						setOpen(true);
					}}
					onFocus={() => setOpen(true)}
					onBlur={() => setTimeout(() => setOpen(false), 120)}
					onKeyDown={keys}
				/>
			</div>

			{showing && (
				<ul
					id="location-search-options"
					role="listbox"
					className="absolute z-20 mt-1.5 w-full overflow-hidden rounded-xl border border-card-line bg-white py-1 shadow-lg"
				>
					{options.map((option, index) => (
						<li
							key={`${option.county}-${option.label}`}
							id={`location-option-${index}`}
							role="option"
							aria-selected={index === active}
							className={cx("cursor-pointer px-3.5 py-2", index === active && "bg-blue-soft")}
							onMouseDown={(event) => {
								event.preventDefault();
								pick(index);
							}}
							onMouseEnter={() => setActive(index)}
						>
							<div className="text-[13.5px] font-semibold text-ink">{option.label}</div>
							<div className="text-[12px] text-muted">{option.detail}</div>
						</li>
					))}
				</ul>
			)}

			{open && text.trim() && options.length === 0 && (
				<p className="mt-1.5 px-1 text-[12.5px] text-muted">No county or branch matches "{text.trim()}".</p>
			)}
		</div>
	);
}

function LocationCard({
	location,
	join = false,
	standing = null,
}: {
	location: BranchLocation;
	join?: boolean;
	standing?: Standing | null;
}) {
	const directions = location.has_point
		? `https://www.google.com/maps/dir/?api=1&destination=${location.latitude},${location.longitude}`
		: null;

	return (
		<Card>
			{location.photo && <img src={location.photo} alt="" className="mb-3 h-36 w-full rounded-xl object-cover" />}

			<h4 className="text-[16px] font-semibold tracking-tight text-ink">{location.location_name}</h4>

			{location.address && (
				<p className="mt-1 whitespace-pre-wrap text-[13px] leading-relaxed text-muted">{location.address}</p>
			)}

			<dl className="mt-3 space-y-2 text-[13px]">
				{location.opening_hours && (
					<Detail icon={<Icon.clock size={15} />} label="Opening hours">
						{location.opening_hours}
					</Detail>
				)}
				{location.phone && (
					<Detail icon={<Icon.phone size={15} />} label="Phone">
						<a className="font-semibold text-ink hover:underline" href={`tel:${location.phone.replace(/\s+/g, "")}`}>
							{location.phone}
						</a>
					</Detail>
				)}
				{location.email && (
					<Detail icon={<Icon.mail size={15} />} label="Email">
						<a className="break-all font-semibold text-ink hover:underline" href={`mailto:${location.email}`}>
							{location.email}
						</a>
					</Detail>
				)}
			</dl>

			{directions && (
				<a
					href={directions}
					target="_blank"
					rel="noreferrer"
					className="mt-4 inline-flex items-center gap-1.5 text-[13px] font-semibold text-action hover:underline"
				>
					<Icon.pin size={15} /> Get directions
				</a>
			)}

			{/* Somebody who looked up a branch has often come to join it. The
			    branch goes with them, and the form opens with it chosen. A guest
			    goes to sign up first, carrying the same address. */}
			{join && (
				<JoinActions location={location} standing={standing} />
			)}
		</Card>
	);
}

/**
 * The two ways to join a branch, or what the person already is there.
 *
 * A volunteer the society already has is not offered "Volunteer here" on any
 * card: a second application never moves anybody, so it would be a form for
 * nothing. Their own branch says so instead, and every other card names where
 * they volunteer. A membership is held per branch, so only the branch they hold
 * one at, or are joining, stops offering it.
 */
function JoinActions({ location, standing }: { location: BranchLocation; standing: Standing | null }) {
	const volunteer = standing?.volunteer ?? null;
	const volunteersHere = Boolean(volunteer && volunteer.branch === location.geo_node);
	const membership = standing?.memberships.find((held) => held.branch === location.geo_node) ?? null;

	return (
		<div className="mt-4 border-t border-card-line pt-4">
			<div className="flex flex-wrap items-center gap-2">
				{volunteersHere ? (
					<Held>Your branch</Held>
				) : (
					!volunteer && (
						<JoinLink
							to={joinLink("volunteer", location)}
							className="movement-primary inline-flex items-center rounded-lg bg-action px-4 py-2 text-[13px] font-semibold text-white transition hover:bg-action-hover"
						>
							Volunteer here
						</JoinLink>
					)
				)}
				{membership ? (
					<Held>{membership.status === "Active" ? "You're a member here" : "Your membership here is being processed"}</Held>
				) : (
					<JoinLink
						to={joinLink("member", location)}
						className="inline-flex items-center rounded-lg border border-card-line bg-white px-4 py-2 text-[13px] font-semibold text-ink transition hover:border-blue"
					>
						Become a member
					</JoinLink>
				)}
			</div>
			{/* A volunteer elsewhere is not offered a second application — it
			    would move nobody — but they may ask to move here, which their
			    own branch and this one then decide. */}
			{volunteer && !volunteersHere && (
				<p className="mt-2.5 text-[12.5px] text-muted">
					You volunteer with {volunteer.branch_label || "another branch"}.{" "}
					{volunteer.can_request_transfer && location.county && !location.is_headquarters && (
						<Link
							to={`/profile?transfer=${encodeURIComponent(location.geo_node)}`}
							className="font-semibold text-ink underline underline-offset-2"
						>
							Ask to move here
						</Link>
					)}
				</p>
			)}
		</div>
	);
}

function Held({ children }: { children: React.ReactNode }) {
	return (
		<span className="inline-flex items-center gap-1.5 rounded-lg bg-rail/[0.07] px-3 py-2 text-[13px] font-semibold text-ink">
			<Icon.check size={15} /> {children}
		</span>
	);
}

function joinLink(path: "volunteer" | "member", location: BranchLocation): string {
	const params = new URLSearchParams({ path });
	if (!location.is_headquarters) params.set("branch", location.geo_node);
	return `/join?${params.toString()}`;
}

function Detail({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
	return (
		<div className="flex items-start gap-2">
			<span className="mt-0.5 text-slate-faint" aria-hidden="true">
				{icon}
			</span>
			<dt className="sr-only">{label}</dt>
			<dd className="text-ink">{children}</dd>
		</div>
	);
}

function Swatch({ colour, label }: { colour: string; label: string }) {
	return (
		<span className="flex items-center gap-1.5">
			<span aria-hidden="true" className="inline-block h-3 w-3 rounded-[3px]" style={{ background: colour }} />
			{label}
		</span>
	);
}

function branchNames(rows: BranchLocation[] | undefined): string {
	if (!rows?.length) return "No branch office listed";
	return rows.map((row) => row.location_name).join(", ");
}
