import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import { cx } from "./kit";
import { googleMapsUrl } from "../../lib/maps";

export type MapJourney = {
	start: { latitude: number; longitude: number; label: string };
	end: { latitude: number; longitude: number; label: string };
	position: number | null;
	status: string;
};

/**
 * A single point on a real OpenStreetMap.
 *
 * Leaflet with OSM's own tiles — no CSS drawing, no static image, no third
 * party. The same tile source and attribution the console's `DeploymentMap`
 * uses. A `divIcon` pin rather than Leaflet's default marker asset, which
 * breaks under a bundler and would need its PNGs copied into the build.
 *
 * A fixed preview can disable all map interaction. Exploration enables Leaflet's
 * keyboard pan/zoom controls; the address in words remains beside the map.
 * Wheel zoom stays off so the page still scrolls normally over it, and zoom
 * animation honours `prefers-reduced-motion`.
 */
export function OsmMap({
	latitude,
	longitude,
	label,
	zoom = 13,
	className,
	height = 220,
	interactive = true,
	journey,
}: {
	latitude: number;
	longitude: number;
	/** The place name, for the pin's tooltip. */
	label?: string;
	zoom?: number;
	className?: string;
	height?: number;
	/** Fixed preview until the deployment reader chooses to explore. */
	interactive?: boolean;
	journey?: MapJourney;
}) {
	const host = useRef<HTMLDivElement | null>(null);
	const [tileError, setTileError] = useState(false);

	useEffect(() => {
		if (!host.current) return;
		setTileError(false);

		const reduce =
			typeof window.matchMedia === "function" &&
			window.matchMedia("(prefers-reduced-motion: reduce)").matches;

		const map = L.map(host.current, {
			center: [latitude, longitude],
			zoom,
			scrollWheelZoom: false,
			dragging: interactive,
			touchZoom: interactive,
			doubleClickZoom: interactive,
			boxZoom: interactive,
			keyboard: interactive,
			zoomControl: interactive,
			zoomAnimation: !reduce,
			fadeAnimation: !reduce,
			attributionControl: true,
		});

		L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
			maxZoom: 19,
			keepBuffer: 0,
			updateWhenIdle: true,
			attribution:
				'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
		}).on("tileerror", () => setTileError(true)).addTo(map);

		const pin = L.divIcon({
			className: "",
			html: `<svg width="26" height="34" viewBox="0 0 26 34" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M13 0C5.8 0 0 5.8 0 13c0 9.2 13 21 13 21s13-11.8 13-21C26 5.8 20.2 0 13 0Z" fill="#011E41"/><circle cx="13" cy="13" r="5" fill="#fff"/></svg>`,
			iconSize: [26, 34],
			iconAnchor: [13, 34],
			tooltipAnchor: [0, -30],
		});

		if (journey) {
			const start: L.LatLngTuple = [journey.start.latitude, journey.start.longitude];
			const end: L.LatLngTuple = [journey.end.latitude, journey.end.longitude];
			L.polyline([start, end], { color: '#27272A', weight: 2, dashArray: '6 8', className: 'deployment-map-connection' }).addTo(map);
			const dot = L.divIcon({ className: 'deployment-map-endpoint', iconSize: [14, 14], iconAnchor: [7, 7] });
			for (const [index, point] of [journey.start, journey.end].entries()) {
				const text = document.createElement('span');
				text.textContent = `${index === 0 ? 'Meeting point' : 'Deployment site'} · ${point.label}`;
				L.marker([point.latitude, point.longitude], { icon: dot, keyboard: false }).addTo(map)
					.bindTooltip(text, { permanent: true, direction: 'bottom', className: 'deployment-map-label', offset: [0, 10] });
			}
			if (journey.position !== null) {
				const fraction = journey.position / 100;
				const truck = L.divIcon({ className: 'deployment-map-vehicle', iconSize: [28, 28], iconAnchor: [14, 32], html: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h10v10H3V6Zm10 3h4l4 4v3h-8V9ZM7 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm10 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z"/></svg>' });
				L.marker([start[0] + (end[0] - start[0]) * fraction, start[1] + (end[1] - start[1]) * fraction], { icon: truck, keyboard: false, title: `Mission status: ${journey.status}` }).addTo(map);
			}
			map.fitBounds(L.latLngBounds([start, end]), { padding: [60, 70], maxZoom: zoom, animate: false });
		} else {
			const marker = L.marker([latitude, longitude], { icon: pin, keyboard: false }).addTo(map);
			if (label) {
			const text = document.createElement("span");
			text.textContent = label;
			marker.bindTooltip(text, { direction: "top" });
			}
		}

		// After layout: a map created inside a card that was itself just laid out
		// measures its container as 0×0 and renders a grey square until told to
		// look again.
		const settle = window.setTimeout(() => {
			map.invalidateSize();
			if (journey) map.fitBounds([[journey.start.latitude, journey.start.longitude], [journey.end.latitude, journey.end.longitude]], { padding: [60, 70], maxZoom: zoom, animate: false });
		}, 60);

		return () => {
			window.clearTimeout(settle);
			map.remove();
		};
	}, [latitude, longitude, zoom, label, interactive, journey]);

	return (
		<div
			className={cx("relative overflow-hidden rounded-xl border border-card-line", className)}
			style={{ height }}
		>
			{/* Absolutely filled so Leaflet's tile buffer is strictly bounded by
			    the clipped wrapper rather than spilling its own bounding box. */}
			<div ref={host} className="absolute inset-0" aria-hidden={!interactive} aria-label={interactive ? `Map of ${label || 'destination'}. Use arrow keys to pan and plus or minus to zoom.` : undefined} />
			{tileError && <p role="status" className="pointer-events-none absolute bottom-7 left-2 right-2 z-[700] rounded bg-white/95 p-2 text-[12px] text-slate-strong">Map imagery could not load. You can still open Google Maps.</p>}
			<a
				href={googleMapsUrl(`${latitude},${longitude}`)}
				target="_blank"
				rel="noreferrer"
				className={interactive ? "absolute right-2 top-2 z-[700]" : "absolute inset-0 z-[650] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px]"}
			>
				<span className={`${interactive ? '' : 'absolute right-2 top-2'} rounded-lg border border-card-line bg-white/95 px-2.5 py-1 text-[11px] font-semibold text-slate-strong shadow-sm transition hover:text-ink`}>Open in Google Maps ↗</span>
			</a>
		</div>
	);
}
