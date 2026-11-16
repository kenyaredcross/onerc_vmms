/**
 * A point from what a coordinator pastes: coordinates, or a Google Maps page.
 *
 * The society has no paid map account, so when the free place search cannot
 * find somewhere, the coordinator finds it on Google Maps in their browser and
 * pastes what it gives them — the coordinates from right-clicking the spot, or
 * the page's address. Both are read here. A phone's share link
 * (`maps.app.goo.gl/…`) says nothing until it is followed, which only the server
 * can do: `isShortMapLink` tells the caller to ask `read_map_link`.
 *
 * The same patterns as `vmmsx/deployment/services/map_links.py`, most specific
 * first: a place's own pin (`!3d…!4d…`) before the map view's centre (`@…`).
 */

export interface MapPoint {
	latitude: number;
	longitude: number;
}

const NUMBER = String.raw`(-?\d{1,3}(?:\.\d+)?)`;

const PATTERNS = [
	new RegExp(String.raw`!3d${NUMBER}!4d${NUMBER}`),
	new RegExp(String.raw`@${NUMBER},${NUMBER}`),
	new RegExp(String.raw`[?&](?:q|query|ll|destination|center)=${NUMBER}\s*,\s*${NUMBER}`),
	new RegExp(String.raw`/place/${NUMBER}\s*,\s*${NUMBER}`),
	new RegExp(String.raw`^\s*${NUMBER}\s*[, ]\s*${NUMBER}\s*$`),
];

export function pointIn(text: string): MapPoint | null {
	let decoded = text;

	try {
		decoded = decodeURIComponent(text);
	} catch {
		// A half-typed "%" is not a reason to stop reading.
	}

	for (const pattern of PATTERNS) {
		const found = pattern.exec(decoded);

		if (found) {
			const latitude = Number(found[1]);
			const longitude = Number(found[2]);

			if (Math.abs(latitude) <= 90 && Math.abs(longitude) <= 180 && (latitude || longitude)) {
				return { latitude, longitude };
			}
		}
	}

	return null;
}

export function isShortMapLink(text: string): boolean {
	try {
		const host = new URL(text.trim()).hostname;
		return host === "maps.app.goo.gl" || host === "goo.gl";
	} catch {
		return false;
	}
}
