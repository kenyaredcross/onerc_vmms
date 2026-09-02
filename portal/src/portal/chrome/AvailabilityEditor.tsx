import { useContext, useEffect, useMemo, useState } from "react";
import { FrappeContext, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage } from "../../lib/api";
import type { AvailabilityDay, MyAvailability } from "../types";
import { Button, Empty, ErrorNote, cx } from "../ui/kit";

/**
 * When a volunteer can serve — a week of tick boxes, days down and the
 * society's own windows across.
 *
 * **One editor, two homes.** It is the body of the header's availability modal
 * and of the `/availability` page a coordinator links somebody to. The
 * behaviour is unchanged from the screen it replaces: the grid *replaces* on
 * save (un-ticking has to be able to remove a row, so every ticked box is sent
 * each time), silence is never a no, and a society that has not named its
 * windows gets told so rather than an empty grid.
 */

const DAYS = [
	"Monday",
	"Tuesday",
	"Wednesday",
	"Thursday",
	"Friday",
	"Saturday",
	"Sunday",
] as const;

const keyOf = (day: string, slot: string) => `${day}|${slot}`;

export function AvailabilityEditor({
	answer,
	onSaved,
	compact = false,
}: {
	answer: MyAvailability;
	onSaved: () => void;
	/** Tightens spacing for the modal, where vertical room is scarcer. */
	compact?: boolean;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [ticked, setTicked] = useState<Set<string>>(new Set());
	const [holidays, setHolidays] = useState(false);
	const [validFrom, setValidFrom] = useState("");
	const [validTo, setValidTo] = useState("");
	const [busy, setBusy] = useState(false);
	const [saved, setSaved] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	useEffect(() => {
		setTicked(new Set(answer.days.map((row) => keyOf(row.day, row.availability_slot))));
		setHolidays(answer.available_on_holidays);
		setValidFrom(answer.valid_from ?? "");
		setValidTo(answer.valid_to ?? "");
	}, [answer]);

	const slots = answer.slots;

	const dirty = useMemo(() => {
		const original = new Set(answer.days.map((row) => keyOf(row.day, row.availability_slot)));
		return (
			original.size !== ticked.size ||
			[...ticked].some((entry) => !original.has(entry)) ||
			holidays !== answer.available_on_holidays ||
			validFrom !== (answer.valid_from ?? "") ||
			validTo !== (answer.valid_to ?? "")
		);
	}, [answer, ticked, holidays, validFrom, validTo]);

	const flip = (day: string, slot: string) =>
		setTicked((current) => {
			const next = new Set(current);
			const entry = keyOf(day, slot);
			next.has(entry) ? next.delete(entry) : next.add(entry);
			setSaved(false);
			return next;
		});

	const save = async () => {
		setBusy(true);
		setFailure(null);
		setSaved(false);
		try {
			await call.post(API.setMyAvailability, {
				days: [...ticked].map((entry) => {
					const [day, slot] = entry.split("|");
					return { day, availability_slot: slot } satisfies AvailabilityDay;
				}),
				available_on_holidays: holidays ? 1 : 0,
				valid_from: validFrom || undefined,
				valid_to: validTo || undefined,
			});
			setSaved(true);
			onSaved();
		} catch (problem) {
			setFailure(errorMessage(problem, "Your availability was not saved."));
		} finally {
			setBusy(false);
		}
	};

	if (slots.length === 0) {
		return (
			<Empty framed={false} title="Your society has not set up its availability windows yet">
				The windows you would tick — mornings, afternoons, evenings, whatever this society calls them —
				are its own to name. Somebody at the branch sets them up, and this fills in once they have.
			</Empty>
		);
	}

	const field =
		"w-full rounded-lg border border-rail-line px-3 py-2 text-[13px] text-ink outline-none focus:border-blue";

	return (
		<div className={compact ? "space-y-5" : "space-y-6"}>
			<div>
				<p className="text-[12.5px] leading-relaxed text-slate-strong">
					Tick the windows you could usually be asked about. This is not a promise — a coordinator
					still asks, and you still answer. Leaving it blank does not take you off anything; it means
					nobody knows, and you are shown for deployments either way.
				</p>

				<div className="mt-4 overflow-x-auto">
					<table className="w-full min-w-[32rem] border-separate border-spacing-0">
						<thead>
							<tr>
								<th
									scope="col"
									className="sticky left-0 z-10 bg-white pb-2 pr-3 text-left text-[11px] font-semibold uppercase tracking-[0.08em] text-rail-label"
								>
									Day
								</th>
								{slots.map((slot) => (
									<th key={slot.name} scope="col" className="px-2 pb-2 text-center">
										<span className="block text-[12px] font-semibold text-ink">
											{slot.slot_name}
										</span>
										{slot.start_time && slot.end_time && (
											<span className="block text-[10.5px] font-normal text-muted">
												{slot.start_time.slice(0, 5)}–{slot.end_time.slice(0, 5)}
											</span>
										)}
									</th>
								))}
							</tr>
						</thead>
						<tbody>
							{DAYS.map((day) => (
								<tr key={day}>
									<th
										scope="row"
										className="sticky left-0 z-10 border-t border-card-line bg-white py-2.5 pr-3 text-left text-[12.5px] font-semibold text-ink"
									>
										{day}
									</th>
									{slots.map((slot) => {
										const on = ticked.has(keyOf(day, slot.name));
										return (
											<td
												key={slot.name}
												className="border-t border-card-line px-2 py-2.5 text-center"
											>
												<button
													type="button"
													role="checkbox"
													aria-checked={on}
													aria-label={`${day}, ${slot.slot_name}`}
													onClick={() => flip(day, slot.name)}
													className={cx(
														"h-7 w-7 rounded-lg border transition",
														on
															? "border-blue bg-blue text-white"
															: "border-rail-line bg-white hover:border-blue",
													)}
												>
													{on && (
														<svg
															viewBox="0 0 16 16"
															className="mx-auto h-3.5 w-3.5"
															aria-hidden="true"
														>
															<path
																d="M3 8.5l3.2 3.2L13 5"
																fill="none"
																stroke="currentColor"
																strokeWidth="2.2"
																strokeLinecap="round"
																strokeLinejoin="round"
															/>
														</svg>
													)}
												</button>
											</td>
										);
									})}
								</tr>
							))}
						</tbody>
					</table>
				</div>

				<div className="mt-3 flex flex-wrap gap-2">
					<Button
						tone="quiet"
						onClick={() => {
							setTicked(new Set(DAYS.flatMap((day) => slots.map((slot) => keyOf(day, slot.name)))));
							setSaved(false);
						}}
					>
						Tick everything
					</Button>
					<Button
						tone="quiet"
						onClick={() => {
							setTicked(new Set());
							setSaved(false);
						}}
					>
						Clear
					</Button>
				</div>
			</div>

			<div className="border-t border-card-line pt-5">
				<label className="flex cursor-pointer items-start gap-2.5">
					<input
						type="checkbox"
						className="mt-0.5 h-4 w-4 accent-blue"
						checked={holidays}
						onChange={(event) => {
							setHolidays(event.target.checked);
							setSaved(false);
						}}
					/>
					<span>
						<span className="block text-[13px] font-semibold text-ink">
							I can be asked on public holidays
						</span>
						<span className="block text-[11.5px] text-muted">
							Recorded for whoever is mounting a response over a holiday.
						</span>
					</span>
				</label>

				<div className="mt-4 grid gap-3 sm:grid-cols-2">
					<label className="block">
						<span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[0.08em] text-rail-label">
							This holds from
						</span>
						<input
							type="date"
							className={field}
							value={validFrom}
							onChange={(event) => {
								setValidFrom(event.target.value);
								setSaved(false);
							}}
						/>
						<span className="mt-1 block text-[11px] text-muted">Empty means from now on.</span>
					</label>
					<label className="block">
						<span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[0.08em] text-rail-label">
							Until
						</span>
						<input
							type="date"
							className={field}
							value={validTo}
							onChange={(event) => {
								setValidTo(event.target.value);
								setSaved(false);
							}}
						/>
						<span className="mt-1 block text-[11px] text-muted">
							Empty means indefinitely.
						</span>
					</label>
				</div>
			</div>

			{failure && <ErrorNote>{failure}</ErrorNote>}

			<div className="flex flex-wrap items-center gap-3">
				<Button disabled={!dirty} busy={busy} onClick={() => void save()}>
					Save availability
				</Button>
				{saved && !dirty && <span className="text-[12px] font-semibold text-blue">Saved.</span>}
				{dirty && !busy && (
					<span className="text-[12px] text-muted">You have unsaved changes.</span>
				)}
			</div>
		</div>
	);
}
