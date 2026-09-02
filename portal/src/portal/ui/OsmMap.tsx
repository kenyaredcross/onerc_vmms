import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import { cx } from "./kit";

/**
 * A single point on a real OpenStreetMap.
 *
 * Leaflet with OSM's own tiles — no CSS drawing, no static image, no third
 * party. The same tile source and attribution the console's `DeploymentMap`
 * uses. A `divIcon` pin rather than Leaflet's default marker asset, which
 * breaks under a bundler and would need its PNGs copied into the build.
 *
 * **Not keyboard-operable, and it does not pretend to be.** A Leaflet canvas
 * has no meaningful keyboard model; the address in words always sits beside it,
 * which is the accessible reading of the same fact. `scrollWheelZoom` is off so
 * the page still scrolls over it, and zoom animation is dropped under
 * `prefers-reduced-motion`.
 */
export function OsmMap({
	latitude,
	longitude,
	label,
	zoom = 13,
	className,
	height = 220,
}: {
	latitude: number;
	longitude: number;
	/** The place name, for the pin's tooltip. */
	label?: string;
	zoom?: number;
	className?: string;
	height?: number;
}) {
	const host = useRef<HTMLDivElement | null>(null);

	useEffect(() => {
		if (!host.current) return;

		const reduce =
			typeof window.matchMedia === "function" &&
			window.matchMedia("(prefers-reduced-motion: reduce)").matches;

		const map = L.map(host.current, {
			center: [latitude, longitude],
			zoom,
			scrollWheelZoom: false,
			zoomAnimation: !reduce,
			fadeAnimation: !reduce,
			attributionControl: true,
		});

		L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
			maxZoom: 19,
			attribution:
				'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
		}).addTo(map);

		const pin = L.divIcon({
			className: "",
			html: `<svg width="26" height="34" viewBox="0 0 26 34" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M13 0C5.8 0 0 5.8 0 13c0 9.2 13 21 13 21s13-11.8 13-21C26 5.8 20.2 0 13 0Z" fill="#155EEF"/><circle cx="13" cy="13" r="5" fill="#fff"/></svg>`,
			iconSize: [26, 34],
			iconAnchor: [13, 34],
			tooltipAnchor: [0, -30],
		});

		const marker = L.marker([latitude, longitude], { icon: pin, keyboard: false }).addTo(map);
		if (label) marker.bindTooltip(label, { direction: "top" });

		// After layout: a map created inside a card that was itself just laid out
		// measures its container as 0×0 and renders a grey square until told to
		// look again.
		const settle = window.setTimeout(() => map.invalidateSize(), 60);

		return () => {
			window.clearTimeout(settle);
			map.remove();
		};
	}, [latitude, longitude, zoom, label]);

	return (
		<div
			className={cx("relative overflow-hidden rounded-xl border border-card-line", className)}
			style={{ height }}
		>
			{/* Absolutely filled so Leaflet's tile buffer is strictly bounded by
			    the clipped wrapper rather than spilling its own bounding box. */}
			<div ref={host} className="absolute inset-0" aria-hidden="true" />
			<a
				href={`https://www.openstreetmap.org/?mlat=${latitude}&mlon=${longitude}#map=${zoom}/${latitude}/${longitude}`}
				target="_blank"
				rel="noreferrer"
				className="absolute right-2 top-2 z-[700] rounded-lg border border-card-line bg-white/95 px-2.5 py-1 text-[11px] font-semibold text-slate-strong shadow-sm transition hover:text-ink"
			>
				Open larger map ↗
			</a>
		</div>
	);
}
