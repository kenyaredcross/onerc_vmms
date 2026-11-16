import { useContext, useEffect, useRef, useState } from "react";
import { FrappeContext, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage } from "../../lib/api";
import { INPUT, Labelled } from "../Projects";

/** One candidate from the site's geocoder: words a person recognises, and a point. */
export interface PlaceSuggestion {
	label: string;
	latitude: number;
	longitude: number;
}

/**
 * Type where it is; pick the one that is right; the coordinates write themselves.
 *
 * **Nobody types a latitude.** A coordinator has an address in their head and a
 * map in their pocket, and asking them for six decimal places was asking for
 * the one thing they do not have. This asks the site's configured geocoder what
 * the words might mean and shows the candidates; choosing one drops the pin.
 *
 * **It asks after a pause, not after a keystroke.** Every public geocoder rate
 * limits, and OSM's own usage policy asks specifically that nobody fire one
 * request per character. 400ms is long enough that a typed address is one
 * request rather than thirty, and short enough that it still feels like
 * typing. The request in flight is abandoned rather than cancelled: a late
 * answer to an old query is dropped by the sequence check, so a slow provider
 * cannot repaint the list with the results of a word somebody has finished
 * deleting.
 *
 * **A site with no provider configured says so once**, in the sentence the
 * server sends, and the coordinates below stay the way to get the job done.
 */
export function PlaceSearch({
	onPick,
	busy,
	near = null,
}: {
	onPick: (found: PlaceSuggestion) => void;
	busy: boolean;
	/** Where to look first — the county's centre. Results stay in the society's country either way. */
	near?: { latitude: number; longitude: number } | null;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [query, setQuery] = useState("");
	const [places, setPlaces] = useState<PlaceSuggestion[]>([]);
	const [note, setNote] = useState<string | null>(null);
	const [looking, setLooking] = useState(false);

	// The query this component last sent. A reply for anything else is stale by
	// definition and is dropped rather than rendered.
	const asked = useRef("");

	useEffect(() => {
		const text = query.trim();

		if (text.length < 3) {
			setPlaces([]);
			setNote(null);
			return;
		}

		const timer = window.setTimeout(async () => {
			asked.current = text;
			setLooking(true);

			try {
				const answer = await call.get<{
					message: { places: PlaceSuggestion[]; reason: string | null };
				}>(API.suggestPlaces, { query: text, latitude: near?.latitude, longitude: near?.longitude });

				if (asked.current !== text) return;

				setPlaces(answer.message.places);
				setNote(answer.message.reason);
			} catch (problem) {
				if (asked.current === text) setNote(errorMessage(problem));
			} finally {
				if (asked.current === text) setLooking(false);
			}
		}, 400);

		return () => window.clearTimeout(timer);
	}, [query, call, near?.latitude, near?.longitude]);

	return (
		<div>
			<Labelled
				label="Find the place"
				hint="Type the name or address, then choose the match. The coordinates are filled in for you."
			>
				<input
					className={INPUT}
					value={query}
					onChange={(event) => setQuery(event.target.value)}
					placeholder="Name or address"
					autoComplete="off"
				/>
			</Labelled>

			{looking && <p className="mt-2 text-[11.5px] text-muted">Looking…</p>}

			{places.length > 0 && (
				<ul className="mt-2 divide-y divide-card-line overflow-hidden rounded-xl border border-card-line">
					{places.map((found) => (
						<li key={`${found.latitude},${found.longitude},${found.label}`}>
							<button
								type="button"
								disabled={busy}
								onClick={() => onPick(found)}
								className="block w-full px-3 py-2.5 text-left text-[12px] leading-snug text-ink transition hover:bg-surface disabled:opacity-50"
							>
								{found.label}
								<span className="mt-0.5 block text-[11px] text-muted">
									{found.latitude}, {found.longitude}
								</span>
							</button>
						</li>
					))}
				</ul>
			)}

			{note && !looking && <p className="mt-2 text-[11.5px] leading-relaxed text-muted">{note}</p>}
		</div>
	);
}

