import { useContext, useState } from "react";
import { FrappeContext, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage } from "../../lib/api";
import { Button } from "../../ui/primitives";
import { INPUT } from "../Projects";
import { isShortMapLink, pointIn, type MapPoint } from "./mapLinks";
import { PinMap } from "./PinMap";
import { PlaceSearch } from "./PlaceSearch";

/**
 * Three free ways to put a pin on the map, none needing a paid account.
 *
 * Search for the place (where this site has a place search switched on), click
 * the map, or paste what Google Maps in the browser gives — the coordinates from
 * right-clicking the spot, the page's address, or a phone's share link, which
 * the server follows because the browser cannot.
 */
export function PinTools({
	value,
	center,
	label,
	busy = false,
	onPick,
}: {
	value: MapPoint | null;
	center: MapPoint | null;
	/** What is being pinned, for the map's accessible name: "the site". */
	label: string;
	busy?: boolean;
	onPick: (point: MapPoint, found?: string) => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [pasted, setPasted] = useState("");
	const [reading, setReading] = useState(false);
	const [note, setNote] = useState<string | null>(null);

	const read = async () => {
		const text = pasted.trim();
		if (!text) return;

		setNote(null);
		const found = pointIn(text);

		if (found) {
			onPick(found);
			setPasted("");
			return;
		}

		if (!isShortMapLink(text)) {
			setNote("No location found in that. Copy the coordinates from Google Maps and paste them here.");
			return;
		}

		setReading(true);

		try {
			const reply = await call.get<{ message: { point: MapPoint | null } }>(API.readMapLink, { url: text });

			if (reply.message.point) {
				onPick(reply.message.point);
				setPasted("");
			} else {
				setNote("That link could not be read. Copy the coordinates from Google Maps and paste them here.");
			}
		} catch (problem) {
			setNote(errorMessage(problem, "That link could not be read. Paste the coordinates instead."));
		} finally {
			setReading(false);
		}
	};

	return (
		<div className="space-y-3">
			<PlaceSearch
				busy={busy}
				near={center ?? value}
				onPick={(found) => onPick({ latitude: found.latitude, longitude: found.longitude }, found.label)}
			/>

			<div>
				<p className="mb-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-faint">
					Or click the map
				</p>
				<PinMap value={value} center={center} onPick={(point) => onPick(point)} label={label} />
			</div>

			<div>
				<label className="block">
					<span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-faint">
						Or paste from Google Maps
					</span>
					<span className="flex gap-2">
						<input
							className={INPUT}
							value={pasted}
							onChange={(event) => setPasted(event.target.value)}
							onKeyDown={(event) => {
								if (event.key === "Enter") {
									event.preventDefault();
									void read();
								}
							}}
							placeholder="-1.29207, 36.82195  or a Google Maps link"
						/>
						<Button variant="quiet" busy={reading} disabled={busy || !pasted.trim()} onClick={() => void read()}>
							Use
						</Button>
					</span>
				</label>
				<p className="mt-1.5 text-[11.5px] text-slate-faint">
					On{" "}
					<a
						href="https://www.google.com/maps"
						target="_blank"
						rel="noreferrer"
						className="font-semibold text-blue hover:text-blue-hover"
					>
						Google Maps
					</a>
					, right-click the spot and click the numbers at the top to copy them. On a phone, use Share and
					copy the link.
				</p>
				{note && <p className="mt-1.5 text-[11.5px] text-slate-strong">{note}</p>}
			</div>
		</div>
	);
}
