import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import { ContentProvider } from "../content/ContentProvider";
import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { BrandLockup } from "../ui/brand";
import { Card, Empty, ErrorNote, PageHeading, SectionTitle, Spinner, cx } from "../ui/primitives";
import type { BranchLocation } from "../portal/types";

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
 * **The map is drawn from real coordinates or not at all.** There is no default
 * centre and no fallback country: a society with no coordinates recorded gets
 * the list without the map, because a map centred on a guess is a map that says
 * something false. `bounds` comes from the server for the same reason, so this
 * file holds no opinion about where in the world anybody is.
 *
 * **Leaflet, bundled, with OpenStreetMap tiles.** The library is an npm
 * dependency compiled into the portal bundle rather than a script from a CDN.
 * The tiles themselves are fetched from openstreetmap.org at view time, which is
 * the one runtime dependency on anything outside this site, and the attribution
 * the licence requires is rendered with them. A site that cannot reach it shows
 * the pins on an empty canvas and the list below is unaffected, which is why the
 * list is the primary content and the map is beside it.
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
					</div>
				</header>

				<main className="mx-auto max-w-shell px-5 py-8">
					<Directory />
				</main>
			</div>
		</ContentProvider>
	);
}

/** The map and the list, which are two views of one answer. */
export function Directory() {
	const { data, error, isLoading } = useFrappeGetCall<{
		message: {
			count: number;
			locations: BranchLocation[];
			bounds: { south: number; north: number; west: number; east: number } | null;
		};
	}>(API.publishedLocations, undefined, "locations:published");

	const [focused, setFocused] = useState<string | null>(null);

	const answer = data?.message;
	const locations = answer?.locations ?? [];

	return (
		<>
			<PageHeading
				eyebrow={<EditableText k="locations.eyebrow" fallback="Find us" />}
				title={<EditableText k="locations.heading" fallback="Where to find us" />}
			/>

			{isLoading && <Spinner label="Loading locations…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{answer && locations.length === 0 && (
				<Empty title="No locations have been published yet">
					A coordinator adds an office, warehouse or training centre on the desk and ticks "show
					on public map" for it to appear here.
				</Empty>
			)}

			{locations.length > 0 && (
				<div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,380px)]">
					<MapPanel locations={locations} bounds={answer?.bounds ?? null} focused={focused} />

					<div className="space-y-3">
						<SectionTitle>
							{locations.length} {locations.length === 1 ? "place" : "places"}
						</SectionTitle>

						<ul className="space-y-3">
							{locations.map((location) => (
								<li key={location.name}>
									<LocationCard
										location={location}
										active={focused === location.name}
										onFocus={() => setFocused(location.name)}
									/>
								</li>
							))}
						</ul>
					</div>
				</div>
			)}
		</>
	);
}

/**
 * The map itself.
 *
 * Leaflet owns a DOM node this component hands it and React never touches
 * again, which is the ordinary way to host an imperative map library: the
 * effect creates it once, a second effect moves the view when the focused pin
 * changes, and teardown removes it so a route change does not leave a map
 * attached to a node that has gone.
 *
 * **Renders nothing when there is nothing to draw.** A society that has listed
 * its offices without coordinates gets the list alone rather than an empty grey
 * rectangle, which is a truthful outcome rather than a broken-looking one.
 */
function MapPanel({
	locations,
	bounds,
	focused,
}: {
	locations: BranchLocation[];
	bounds: { south: number; north: number; west: number; east: number } | null;
	focused: string | null;
}) {
	const host = useRef<HTMLDivElement | null>(null);
	const map = useRef<L.Map | null>(null);
	const markers = useRef<Map<string, L.Marker>>(new Map());

	// Memoised on the row set, not recomputed per render. Without this the array
	// identity changes on every keystroke of state above, the effect below sees
	// a new dependency, and the map is torn down and rebuilt each time.
	const pinned = useMemo(
		() => locations.filter((location) => location.has_point),
		[locations],
	);

	useEffect(() => {
		if (!host.current || pinned.length === 0) return;

		const instance = L.map(host.current, { scrollWheelZoom: false });

		L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
			maxZoom: 19,
			// Required by the tile provider's licence, and rendered by Leaflet
			// itself into the corner of the map rather than by this app.
			attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
		}).addTo(instance);

		for (const location of pinned) {
			const marker = L.marker([location.latitude as number, location.longitude as number])
				.addTo(instance)
				// Escaped by Leaflet? No: `bindPopup` takes HTML. So the values go
				// in as text nodes built here, never as an interpolated string,
				// because a location name is written by a coordinator and this
				// page is served to the public.
				.bindPopup(popupFor(location));

			markers.current.set(location.name, marker);
		}

		if (bounds) {
			instance.fitBounds(
				[
					[bounds.south, bounds.west],
					[bounds.north, bounds.east],
				],
				{ padding: [40, 40], maxZoom: 14 },
			);
		}

		map.current = instance;

		const drawn = markers.current;

		return () => {
			instance.remove();
			map.current = null;
			drawn.clear();
		};
	}, [pinned, bounds]);

	useEffect(() => {
		const marker = focused ? markers.current.get(focused) : null;

		if (!map.current || !marker) return;

		map.current.setView(marker.getLatLng(), Math.max(map.current.getZoom(), 13));
		marker.openPopup();
	}, [focused]);

	if (pinned.length === 0) return null;

	return (
		<div
			ref={host}
			className="h-[420px] w-full overflow-hidden rounded-2xl border border-card-line bg-white lg:h-full lg:min-h-[520px]"
			// No `role`: a Leaflet canvas is not operable by keyboard in any
			// meaningful way, and labelling it `application` would promise a
			// screen reader an interaction model it cannot deliver. The list
			// beside it is the accessible view of the same answer, which is why
			// it carries the addresses and the map carries only pins.
			aria-hidden="true"
		/>
	);
}

/**
 * A popup built as DOM rather than as an HTML string.
 *
 * `bindPopup` accepts HTML, so interpolating a location's name into a template
 * literal would put text a coordinator typed into the markup of a page served
 * to the public. Building nodes and setting `textContent` cannot do that, and it
 * is the same guarantee the content module gets by rendering `text_value` as a
 * string.
 */
function popupFor(location: BranchLocation): HTMLElement {
	const wrapper = document.createElement("div");

	const name = document.createElement("strong");
	name.textContent = location.location_name;
	wrapper.appendChild(name);

	if (location.address) {
		const address = document.createElement("div");
		address.textContent = location.address;
		wrapper.appendChild(address);
	}

	return wrapper;
}

function LocationCard({
	location,
	active,
	onFocus,
}: {
	location: BranchLocation;
	active: boolean;
	onFocus: () => void;
}) {
	return (
		<Card className={cx("transition", active && "border-blue border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)]")}>
			<button type="button" onClick={onFocus} className="w-full text-left">
				{location.photo && (
					<img
						src={location.photo}
						alt=""
						className="mb-3 h-32 w-full rounded-xl object-cover"
					/>
				)}

				<h3 className="text-[15px] font-semibold tracking-tight text-ink">
					{location.location_name}
				</h3>

				{location.address && (
					<p className="mt-1 whitespace-pre-wrap text-[12.5px] leading-relaxed text-muted">
						{location.address}
					</p>
				)}

				{!location.has_point && (
					<p className="mt-1 text-[11.5px] text-slate-faint">Not pinned on the map.</p>
				)}
			</button>

			<dl className="mt-3 space-y-1 text-[12.5px]">
				{location.opening_hours && (
					<div className="text-muted">{location.opening_hours}</div>
				)}
				{location.phone && (
					<div>
						<a className="font-semibold text-ink hover:underline" href={`tel:${location.phone}`}>
							{location.phone}
						</a>
					</div>
				)}
				{location.email && (
					<div>
						<a
							className="font-semibold text-ink hover:underline"
							href={`mailto:${location.email}`}
						>
							{location.email}
						</a>
					</div>
				)}
			</dl>
		</Card>
	);
}
