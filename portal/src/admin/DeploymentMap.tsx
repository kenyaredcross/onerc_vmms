import { useEffect, useMemo, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import type { DeploymentArea } from "../portal/types";
import { cx } from "../ui/primitives";

/**
 * Where this society's people are, drawn on a map.
 *
 * **A proportional-circle map, not a heat map, and the difference is honest
 * rather than pedantic.** A heat map shades *regions*, which needs a boundary
 * polygon per geo node — a dataset nobody has, and one this app would have to
 * source per country and keep in step with every branch reorganisation. What the
 * geo tree now carries is a *point* per node, so what can be drawn faithfully is
 * a circle at that point sized by how many people are there. It answers the same
 * question — where are our people, and where are most of them — without
 * pretending to know where one county stops and the next begins.
 *
 * **Area is proportional to the count, not radius.** A circle whose radius
 * doubles has four times the area, so sizing by radius makes ten people look
 * like a hundred. Taking the square root is what makes two circles compare the
 * way somebody reading them assumes they do.
 *
 * **It renders nothing when nothing can be drawn**, and the panel around it says
 * how many areas were left off. A geo tree is filled in from the top down over
 * months, so a map showing four pins when there are eleven areas is the ordinary
 * early state — and saying so is what stops it reading as "we only work in four
 * places".
 */
export function DeploymentMap({ areas, className }: { areas: DeploymentArea[]; className?: string }) {
	const host = useRef<HTMLDivElement | null>(null);

	// Memoised on the row set, not recomputed per render: without this the array
	// identity changes on every render of the page above, the effect sees a new
	// dependency, and the map is torn down and rebuilt each time.
	const plotted = useMemo(
		() =>
			areas.filter(
				(area) =>
					typeof area.latitude === "number" &&
					typeof area.longitude === "number" &&
					area.people > 0,
			),
		[areas],
	);

	const most = useMemo(
		() => plotted.reduce((top, area) => Math.max(top, area.people), 0),
		[plotted],
	);

	useEffect(() => {
		if (!host.current || plotted.length === 0) return;

		const instance = L.map(host.current, { scrollWheelZoom: false });

		L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
			maxZoom: 19,
			// Required by the tile provider's licence, and rendered by Leaflet
			// itself into the corner of the map rather than by this app.
			attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
		}).addTo(instance);

		for (const area of plotted) {
			L.circleMarker([area.latitude as number, area.longitude as number], {
				radius: radiusFor(area.people, most),
				color: "#7f1d1d",
				weight: 1.5,
				fillColor: "#dc2626",
				fillOpacity: 0.45,
			})
				.addTo(instance)
				// `bindPopup` takes HTML, so the values go in as text nodes built
				// here rather than as an interpolated string: a geo node's name is
				// written by a coordinator, and this is the same rule the public
				// locations map follows.
				.bindPopup(popupFor(area));
		}

		instance.fitBounds(
			L.latLngBounds(
				plotted.map((area) => [area.latitude as number, area.longitude as number]),
			),
			{ padding: [40, 40], maxZoom: 11 },
		);

		// Braced: `remove()` returns the map, and an effect cleanup must return
		// nothing.
		return () => {
			instance.remove();
		};
	}, [plotted, most]);

	if (plotted.length === 0) return null;

	return (
		<div
			ref={host}
			className={cx(
				"h-[340px] w-full overflow-hidden rounded-card border border-hairline bg-white",
				className,
			)}
			// No `role`: a Leaflet canvas is not operable by keyboard in any
			// meaningful way, and labelling it `application` would promise a screen
			// reader an interaction model it cannot deliver. The ranked list beside
			// it is the accessible view of the same answer, which is why that list
			// carries every area and the map carries only the ones with a point.
			aria-hidden="true"
		/>
	);
}

/**
 * How big to draw a circle holding `people`, against the busiest area.
 *
 * By **area**, not radius: a circle whose radius doubles has four times the
 * area, so sizing by radius directly would make ten people look like a hundred.
 * The floor keeps a one-person area visible rather than a dot nobody can hit,
 * and the ceiling keeps the busiest one from swallowing its neighbours.
 */
function radiusFor(people: number, most: number): number {
	const MIN = 7;
	const MAX = 30;

	if (most <= 0) return MIN;

	return MIN + (MAX - MIN) * Math.sqrt(people / most);
}

/** A popup built as DOM rather than as an HTML string. */
function popupFor(area: DeploymentArea): HTMLElement {
	const holder = document.createElement("div");

	const where = document.createElement("strong");
	where.textContent = area.geo_path ?? area.geo_node;
	holder.appendChild(where);

	const count = document.createElement("div");
	count.textContent = `${area.people} on ${area.deployments} ${
		area.deployments === 1 ? "deployment" : "deployments"
	}`;
	holder.appendChild(count);

	if (area.waiting > 0) {
		const waiting = document.createElement("div");
		waiting.textContent = `${area.waiting} still to answer`;
		holder.appendChild(waiting);
	}

	return holder;
}
