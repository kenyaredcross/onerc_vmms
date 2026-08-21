import { useContext, useEffect, useMemo, useState } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import {
	Button,
	Card,
	Empty,
	ErrorNote,
	PageHeading,
	SectionTitle,
	Spinner,
	cx,
} from "../ui/primitives";
import type { AvailabilityDay, MyAvailability } from "./types";

/**
 * When you can serve — a week of tick boxes.
 *
 * **Why this exists next to the availability already on the register.** A
 * volunteer picks named windows at intake — "Weekends", "On-call" — and a
 * coordinator can search on those. That is a *self-description*. It cannot
 * answer the question a deployment actually asks, which is "this runs from the
 * 3rd to the 10th of September — are you free then". This grid is that answer:
 * a weekly pattern the server turns into a yes, a no, or an honest "we do not
 * know" across a real span of dates.
 *
 * **Silence is not a no, and the copy says so.** Somebody who has not filled
 * this in is not excluded from anything — the matcher marks them unknown and
 * shows them anyway. Telling people that is what stops this feeling like a
 * gate, and it is also simply true.
 *
 * **The grid replaces rather than merges on save.** What arrives at the server
 * is the whole answer, because un-ticking has to be able to remove a row. That
 * is the one thing a grid must be able to do, so `set_my_availability` is
 * documented as replacing and this sends every ticked box each time.
 *
 * **Days down, windows across.** The society names its own windows and gives
 * them hours, so the column headers are its vocabulary rather than this app's;
 * only the seven days are fixed, because they are not a society's to extend.
 * A society that has not given a window its hours gets a column with no times
 * under it rather than a column that lies about them.
 */
export function Availability() {
	const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: MyAvailability | null }>(
		API.myAvailability,
		undefined,
		"portal:my_availability",
	);

	const answer = data?.message ?? null;

	return (
		<>
			<PageHeading
				title={<EditableText k="portal.availability.heading" fallback="When you can serve" />}
				trail={[{ label: "Home", to: "/dashboard" }, { label: "Availability" }]}
			/>

			{isLoading && <Spinner label="Loading your availability…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{data && !answer && (
				<Empty title="You do not have a volunteer record yet">
					Availability is something a volunteer sets. Once your application has been accepted, this
					page is where you say which days and hours you can be asked about.
				</Empty>
			)}

			{answer && <Grid answer={answer} onSaved={() => void mutate()} />}
		</>
	);
}

/** Monday first, matching the server's own list, which is indexed by weekday. */
const DAYS = [
	"Monday",
	"Tuesday",
	"Wednesday",
	"Thursday",
	"Friday",
	"Saturday",
	"Sunday",
] as const;

function Grid({ answer, onSaved }: { answer: MyAvailability; onSaved: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	// The ticked boxes as a set of "Day|slot" keys. A set rather than a nested
	// object because the only two operations this screen has are "is this ticked"
	// and "flip it", and both are one line against a set.
	const [ticked, setTicked] = useState<Set<string>>(new Set());
	const [holidays, setHolidays] = useState(false);
	const [validFrom, setValidFrom] = useState("");
	const [validTo, setValidTo] = useState("");
	const [busy, setBusy] = useState(false);
	const [saved, setSaved] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	// Seeded from the server's answer, and re-seeded whenever it changes — which
	// happens after a save. Deriving the state instead would make the grid
	// unusable, because a tick has to show before the round trip finishes.
	useEffect(() => {
		setTicked(new Set(answer.days.map((row) => key(row.day, row.availability_slot))));
		setHolidays(answer.available_on_holidays);
		setValidFrom(answer.valid_from ?? "");
		setValidTo(answer.valid_to ?? "");
	}, [answer]);

	const slots = answer.slots;

	const dirty = useMemo(() => {
		const original = new Set(answer.days.map((row) => key(row.day, row.availability_slot)));

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
			const entry = key(day, slot);

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
			<Empty title="Your society has not set up its availability windows yet">
				The windows you would tick — mornings, afternoons, evenings, whatever this society calls them
				— are its own to name. Somebody at the branch sets them up, and this page fills in once they
				have.
			</Empty>
		);
	}

	return (
		<div className="space-y-4">
			<Card>
				<SectionTitle>Your usual week</SectionTitle>
				<p className="mt-1 text-[12.5px] leading-relaxed text-slate-body">
					Tick the windows you could usually be asked about. This is not a promise — a coordinator
					still asks, and you still answer. Leaving it blank does not take you off anything: it
					simply means nobody knows, and you will be shown for deployments either way.
				</p>

				<div className="mt-4 overflow-x-auto">
					<table className="w-full min-w-[34rem] border-separate border-spacing-0">
						<thead>
							<tr>
								<th
									scope="col"
									className="sticky left-0 z-10 bg-white pb-2 pr-3 text-left text-[11px] font-bold uppercase tracking-wider text-slate-faint"
								>
									Day
								</th>
								{slots.map((slot) => (
									<th key={slot.name} scope="col" className="px-2 pb-2 text-center">
										<span className="block text-[12px] font-bold text-ink">{slot.slot_name}</span>
										{slot.start_time && slot.end_time && (
											<span className="block text-[10.5px] font-normal text-slate-faint">
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
										className="sticky left-0 z-10 border-t border-hairline bg-white py-2.5 pr-3 text-left text-[12.5px] font-semibold text-ink"
									>
										{day}
									</th>
									{slots.map((slot) => {
										const on = ticked.has(key(day, slot.name));

										return (
											<td
												key={slot.name}
												className="border-t border-hairline px-2 py-2.5 text-center"
											>
												<button
													type="button"
													role="checkbox"
													aria-checked={on}
													aria-label={`${day}, ${slot.slot_name}`}
													onClick={() => flip(day, slot.name)}
													className={cx(
														"h-7 w-7 rounded-control border transition",
														on
															? "border-navy bg-navy text-white"
															: "border-hairline-strong bg-white hover:border-navy",
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

				<div className="mt-4 flex flex-wrap gap-2">
					<Button
						variant="quiet"
						onClick={() => {
							setTicked(
								new Set(DAYS.flatMap((day) => slots.map((slot) => key(day, slot.name)))),
							);
							setSaved(false);
						}}
					>
						Tick everything
					</Button>
					<Button
						variant="quiet"
						onClick={() => {
							setTicked(new Set());
							setSaved(false);
						}}
					>
						Clear
					</Button>
				</div>
			</Card>

			<Card>
				<SectionTitle>The details</SectionTitle>

				<label className="mt-3 flex cursor-pointer items-start gap-2.5">
					<input
						type="checkbox"
						className="mt-0.5 h-4 w-4 accent-navy"
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
						<span className="block text-[11.5px] text-slate-faint">
							Recorded for whoever is mounting a response over a holiday. Nothing filters on it
							yet — which country's calendar to read is a question this app has not been asked.
						</span>
					</span>
				</label>

				<div className="mt-4 grid gap-3 sm:grid-cols-2">
					<label className="block">
						<span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-faint">
							This holds from
						</span>
						<input
							type="date"
							className={FIELD}
							value={validFrom}
							onChange={(event) => {
								setValidFrom(event.target.value);
								setSaved(false);
							}}
						/>
						<span className="mt-1 block text-[11.5px] text-slate-faint">
							Optional. Empty means from now on.
						</span>
					</label>

					<label className="block">
						<span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-faint">
							Until
						</span>
						<input
							type="date"
							className={FIELD}
							value={validTo}
							onChange={(event) => {
								setValidTo(event.target.value);
								setSaved(false);
							}}
						/>
						<span className="mt-1 block text-[11.5px] text-slate-faint">
							Optional — for a term, a season, or until you move. Empty means indefinitely.
						</span>
					</label>
				</div>

				{failure && (
					<div className="mt-4">
						<ErrorNote>{failure}</ErrorNote>
					</div>
				)}

				<div className="mt-5 flex flex-wrap items-center gap-3">
					<Button disabled={busy || !dirty} onClick={() => void save()}>
						{busy ? "Saving…" : "Save"}
					</Button>
					{saved && !dirty && (
						<span className="text-[12px] font-semibold text-navy">Saved.</span>
					)}
					{dirty && !busy && (
						<span className="text-[12px] text-slate-faint">You have unsaved changes.</span>
					)}
				</div>
			</Card>
		</div>
	);
}

const FIELD =
	"w-full rounded-card border border-hairline-strong px-3 py-2.5 text-[13px] outline-none focus:border-navy";

/** One ticked box, as a key a set can hold. */
function key(day: string, slot: string): string {
	return `${day}|${slot}`;
}
