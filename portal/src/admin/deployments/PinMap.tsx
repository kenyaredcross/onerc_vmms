import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import type { MapPoint } from "./mapLinks";

// Where the map opens with nothing to centre on: the middle of Kenya, far
// enough out to see the country.
const COUNTRY: MapPoint = { latitude: 0.0236, longitude: 37.9062 };

const PIN = L.divIcon({
	className: "",
	html: `<svg width="26" height="34" viewBox="0 0 26 34" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M13 0C5.8 0 0 5.8 0 13c0 9.2 13 21 13 21s13-11.8 13-21C26 5.8 20.2 0 13 0Z" fill="#011E41"/><circle cx="13" cy="13" r="5" fill="#fff"/></svg>`,
	iconSize: [26, 34],
	iconAnchor: [13, 34],
});

/** Six decimal places is about 10 cm; more is noise from where the mouse landed. */
function rounded(value: number): number {
	return Math.round(value * 1e6) / 1e6;
}

/**
 * A map you click to drop the pin, and drag the pin to move it.
 *
 * Needs no place search and no account: OpenStreetMap's own tiles, the same as
 * every other map in the console. Wheel zoom is off so the page still scrolls
 * over it. Opens on the pin, or on the county, or on the whole country.
 */
export function PinMap({
	value,
	center,
	onPick,
	label,
	height = 240,
}: {
	value: MapPoint | null;
	center?: MapPoint | null;
	onPick: (point: MapPoint) => void;
	label: string;
	height?: number;
}) {
	const host = useRef<HTMLDivElement | null>(null);
	const map = useRef<L.Map | null>(null);
	const marker = useRef<L.Marker | null>(null);
	const pick = useRef(onPick);
	pick.current = onPick;

	useEffect(() => {
		if (!host.current) return;

		const start = value ?? center ?? COUNTRY;
		const created = L.map(host.current, {
			center: [start.latitude, start.longitude],
			zoom: value ? 15 : center ? 11 : 6,
			scrollWheelZoom: false,
		});

		L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
			maxZoom: 19,
			attribution:
				'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
		}).addTo(created);

		created.on("click", (event: L.LeafletMouseEvent) =>
			pick.current({ latitude: rounded(event.latlng.lat), longitude: rounded(event.latlng.lng) }),
		);

		map.current = created;

		// A map laid out inside a card that was itself just laid out measures
		// 0×0 until told to look again.
		const settle = window.setTimeout(() => created.invalidateSize(), 60);

		return () => {
			window.clearTimeout(settle);
			created.remove();
			map.current = null;
			marker.current = null;
		};
		// Created once; the pin and the centre are moved by the effects below.
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	useEffect(() => {
		const current = map.current;
		if (!current) return;

		if (!value) {
			marker.current?.remove();
			marker.current = null;
			return;
		}

		const at: L.LatLngTuple = [value.latitude, value.longitude];

		if (marker.current) {
			marker.current.setLatLng(at);
		} else {
			marker.current = L.marker(at, { icon: PIN, draggable: true, keyboard: false })
				.on("dragend", (event) => {
					const moved = (event.target as L.Marker).getLatLng();
					pick.current({ latitude: rounded(moved.lat), longitude: rounded(moved.lng) });
				})
				.addTo(current);
		}

		if (!current.getBounds().contains(at)) current.setView(at, Math.max(current.getZoom(), 13));
	}, [value]);

	useEffect(() => {
		if (map.current && !value && center) map.current.setView([center.latitude, center.longitude], 11);
		// Only a new county recentres; the pin moving does not.
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [center?.latitude, center?.longitude]);

	return (
		<div className="relative overflow-hidden rounded-xl border border-card-line" style={{ height }}>
			<div
				ref={host}
				className="absolute inset-0"
				role="application"
				aria-label={`Map for ${label}. Click to drop the pin; drag the pin to move it.`}
			/>
		</div>
	);
}
