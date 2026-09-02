import { useEffect, useMemo, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import { cx } from "../ui/primitives";
import type { DeploymentSite } from "../portal/types";

/**
 * The operations map: every deployment in scope as a point you can select.
 *
 * **The counterpart of `DeploymentMap`, not a replacement for it.** That one
 * draws a proportional circle per *area* and answers "where are most of our
 * people"; a circle over a county cannot be selected, and selecting one
 * deployment to read its site, its meeting point, its coordinator and how ready
 * its roster is is the whole of what an operations map is for. So this plots
 * the deployments themselves.
 *
 * **The coordinates are each deployment's own.** `deployment_sites` reads the
 * two places on the record — the site and the meeting point — through the
 * geocoding service that owns those fields. Nothing here holds a coordinate, and
 * a deployment nobody has located yet is not drawn and *is* counted, because the
 * panel around this says how many it could not plot. A map that quietly showed
 * eight pins for eleven deployments would under-report exactly the gap it exists
 * to reveal.
 *
 * **Selecting is a controlled prop, not internal state**, so the detail panel
 * beside the map and the accessible list beneath it select the same thing the
 * pins do. The list is not a fallback: a Leaflet canvas is not operable by
 * keyboard in any meaningful way, so the map is `aria-hidden` and the list is
 * the real control for anybody not using a mouse.
 */
export function OperationsMap({
	deployments,
	selected,
	onSelect,
	className,
}: {
	deployments: DeploymentSite[];
	selected: string | null;
	onSelect: (name: string) => void;
	className?: string;
}) {
	const host = useRef<HTMLDivElement | null>(null);
	const instance = useRef<L.Map | null>(null);
	const markers = useRef<Map<string, L.CircleMarker>>(new Map());
	// The click handler as a ref, so re-rendering the page above does not tear
	// the whole map down to rebind one callback.
	const select = useRef(onSelect);
	select.current = onSelect;

	// Memoised on the row set: without it the array identity changes on every
	// render, the effect sees a new dependency, and the map is destroyed and
	// rebuilt each time — which resets the reader's pan and zoom mid-scan.
	const plotted = useMemo(
		() => deployments.filter((row) => row.where.site.has_point),
		[deployments],
	);

	useEffect(() => {
		if (!host.current || plotted.length === 0) return;

		const map = L.map(host.current, { scrollWheelZoom: false });
		instance.current = map;

		L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
			maxZoom: 19,
			// Required by the tile provider's licence, and rendered by Leaflet
			// itself into the corner of the map rather than by this app.
			attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
		}).addTo(map);

		markers.current = new Map();

		for (const row of plotted) {
			const point: L.LatLngExpression = [
				row.where.site.latitude as number,
				row.where.site.longitude as number,
			];

			const marker = L.circleMarker(point, {
				radius: 9,
				weight: 2,
				...toneFor(row.status),
			})
				.addTo(map)
				// Built as DOM rather than as an interpolated HTML string: a
				// deployment's name and its terms are written by a coordinator,
				// and this is the same rule the public locations map follows.
				.bindTooltip(tooltipFor(row), { direction: "top", offset: [0, -10] })
				.on("click", () => select.current(row.name));

			markers.current.set(row.name, marker);
		}

		map.fitBounds(
			L.latLngBounds(
				plotted.map((row) => [
					row.where.site.latitude as number,
					row.where.site.longitude as number,
				]),
			),
			{ padding: [40, 40], maxZoom: 11 },
		);

		// Braced: `remove()` returns the map, and an effect cleanup must return
		// nothing.
		return () => {
			map.remove();
			instance.current = null;
			markers.current = new Map();
		};
	}, [plotted]);

	// Selection is drawn by restyling the existing markers rather than by
	// rebuilding the layer, so choosing a row in the list does not throw away
	// the reader's pan and zoom.
	useEffect(() => {
		for (const [name, marker] of markers.current) {
			const row = plotted.find((entry) => entry.name === name);
			if (!row) continue;

			const chosen = name === selected;

			marker.setStyle({ ...toneFor(row.status), weight: chosen ? 4 : 2 });
			marker.setRadius(chosen ? 12 : 9);

			if (chosen) marker.bringToFront();
		}

		if (!selected || !instance.current) return;

		const chosen = markers.current.get(selected);
		if (chosen) instance.current.panTo(chosen.getLatLng(), { animate: true });
	}, [selected, plotted]);

	if (plotted.length === 0) return null;

	return (
		<div
			ref={host}
			className={cx(
				"h-[380px] w-full overflow-hidden rounded-xl border border-card-line bg-white",
				className,
			)}
			// No `role`: a Leaflet canvas is not operable by keyboard in any
			// meaningful way, and labelling it `application` would promise a
			// screen reader an interaction model it cannot deliver. The list
			// beside it is the accessible view of the same answer.
			aria-hidden="true"
		/>
	);
}

/**
 * How a status is drawn.
 *
 * A closed set defined in the deployment module's own code — not society
 * configuration, and not an approval stage — so naming the six here is naming
 * what the doctype has. An unknown value gets the neutral tone rather than
 * disappearing, because a pin that vanished would hide a deployment.
 */
const TONES: Record<string, { color: string; fillColor: string }> = {
	Planned: { color: "#0E42A8", fillColor: "#155EEF" },
	Active: { color: "#1F6B45", fillColor: "#2E8B57" },
	Suspended: { color: "#8C5A00", fillColor: "#B97900" },
	Completed: { color: "#5E6775", fillColor: "#8A93A2" },
	"Closed Out": { color: "#5E6775", fillColor: "#B6BDC8" },
	Cancelled: { color: "#B4232C", fillColor: "#D92D3A" },
};

function toneFor(status: string) {
	const tone = TONES[status] ?? { color: "#5E6775", fillColor: "#8A93A2" };

	return { ...tone, fillOpacity: 0.85 };
}

/** A tooltip built as DOM rather than as an HTML string. */
function tooltipFor(row: DeploymentSite): HTMLElement {
	const holder = document.createElement("div");

	const title = document.createElement("strong");
	title.textContent = row.terms_of_reference || row.name;
	holder.appendChild(title);

	const line = document.createElement("div");
	line.textContent = `${row.status} · ${row.participant_count} assigned`;
	holder.appendChild(line);

	return holder;
}

/** The map's legend, and the same closed set the pins are drawn from. */
export function MapLegend({ statuses }: { statuses: string[] }) {
	return (
		<ul className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
			{statuses.map((status) => (
				<li key={status} className="flex items-center gap-1.5 text-[11px] text-muted">
					<span
						aria-hidden="true"
						className="h-2.5 w-2.5 flex-none rounded-full"
						style={{ background: toneFor(status).fillColor }}
					/>
					{status}
				</li>
			))}
		</ul>
	);
}
