/**
 * Formatting helpers, all of them locale-neutral by construction.
 *
 * No currency symbol is hardcoded and no country's date order is assumed: the
 * browser's own locale drives both, and where an amount needs a currency the
 * caller passes the code the society configured. The same rule the Python side
 * follows, for the same reason.
 */

/** A date as a person reads it. Invalid or missing input renders as an em dash. */
export function formatDate(value: string | null | undefined): string {
	if (!value) return "—";

	const date = new Date(value.length <= 10 ? `${value}T00:00:00` : value);
	if (Number.isNaN(date.getTime())) return "—";

	return date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

/** A short date for a tile: "14 Aug". */
export function formatDayMonth(value: string | null | undefined): string {
	if (!value) return "";

	const date = new Date(value.length <= 10 ? `${value}T00:00:00` : value);
	if (Number.isNaN(date.getTime())) return "";

	return date.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

/**
 * A date split for a calendar tile: a short month over a day.
 *
 * Two fields rather than a string, because the tile draws them at two sizes and
 * in two colours. Both are the browser's own locale, like every other date in
 * this file — the month is upper-cased here rather than in CSS so the tile can
 * be measured in the design and read the same in a language whose short month
 * has no capital form.
 */
export function dateTile(value: string | null | undefined): { month: string; day: string } {
	if (!value) return { month: "", day: "" };

	const date = new Date(value.length <= 10 ? `${value}T00:00:00` : value);
	if (Number.isNaN(date.getTime())) return { month: "", day: "" };

	return {
		month: date.toLocaleDateString(undefined, { month: "short" }).toUpperCase(),
		day: date.toLocaleDateString(undefined, { day: "numeric" }),
	};
}

/**
 * A time of day, from whatever a `Time` field stringifies to.
 *
 * Frappe stores a Time as a `timedelta`, and `str()` on one does **not** pad
 * the hour: half past eight arrives as `"8:30:00"`, not `"08:30:00"`. Taking the
 * first five characters of that — the obvious way to drop the seconds — leaves
 * `"8:30:"`, a trailing colon on a card. Splitting on the colon is the only way
 * that is right for both shapes.
 *
 * Anything that is not a time is returned untouched rather than mangled.
 */
export function formatClock(value: string | null | undefined): string {
	if (!value) return "";

	const [hour, minute] = value.split(":");
	if (hour === undefined || minute === undefined) return value;

	return `${hour.padStart(2, "0")}:${minute}`;
}

/**
 * An amount with the society's currency, when there is one.
 *
 * `currency` comes from configuration and may be absent on a site nobody has
 * finished setting up. Absent means the number is shown bare, which is honest,
 * rather than a symbol this app picked.
 */
export function formatMoney(
	amount: number | null | undefined,
	currency?: string | null,
	/**
	 * Show the minor unit.
	 *
	 * Off by default, and that is the interesting half. `Intl` decides how many
	 * fraction digits a currency has from the currency *code*, and it does not
	 * know that a society reporting in Tanzanian shillings never quotes cents —
	 * so a headline figure came out as "TZS 20,153,204.00", four characters of
	 * pure noise on the widest number on the page. A report reads in whole
	 * units; a receipt, where the minor unit is the point, passes `true`.
	 */
	cents = false,
): string {
	if (amount === null || amount === undefined) return "—";

	if (currency) {
		try {
			return new Intl.NumberFormat(undefined, {
				style: "currency",
				currency,
				...(cents ? {} : { maximumFractionDigits: 0 }),
			}).format(amount);
		} catch {
			// An unrecognised currency code is a configuration problem, not a
			// reason to render nothing. Fall through to code plus number.
			return `${currency} ${amount.toLocaleString()}`;
		}
	}

	return amount.toLocaleString();
}

/** Hours, to one decimal only when it has one. */
export function formatHours(hours: number | null | undefined): string {
	if (!hours) return "0";
	return Number.isInteger(hours) ? String(hours) : hours.toFixed(1);
}

/**
 * Core renders a geo path joined with em dashes. Reversed here so the branch a
 * record belongs to reads first and the nation last, which is the order the
 * design shows and the order a person scanning a list needs.
 */
export function geoPath(path: string | null | undefined): string {
	if (!path) return "";
	return path.split("—").map((part) => part.trim()).filter(Boolean).join(" · ");
}

/**
 * The same path without the crown — the society's own name at the end of it.
 *
 * **A value that is identical on every row carries no information and costs the
 * width of a column.** Inside this console every record belongs to the same
 * society, so "Ubungo · Dar es Salaam · Tanzania Red Cross Society" says one
 * thing and spends forty characters saying three. The branch is the part
 * somebody is reading for, and in a table cell or a filter chip it should be
 * the part they see.
 *
 * **The last rung, not the first**, and getting that backwards is easy: core
 * renders `get_full_path` deepest-first — `Ubungo — Dar es Salaam — Tanzania
 * Red Cross Society` — so the society is at the *end*. `geoPath` above keeps
 * that order, and this drops the tail rather than the head. (A cascading
 * picker's `chain` is the other way round, root-first, which is why the screens
 * that trim one of those slice from the front instead.)
 *
 * **Only when there is something under it.** A record anchored at the society
 * itself — a national announcement, a headquarters posting — has a one-rung
 * path, and dropping that rung would leave an empty cell where the answer is
 * "the whole society". So the crown comes off a path that has a branch beneath
 * it, and stays on one that does not.
 *
 * Deliberately a second function rather than a flag on `geoPath`: a public page
 * naming where an office is *should* say which society's office it is, and that
 * caller should not have to remember to ask for it.
 */
export function branchPath(path: string | null | undefined): string {
	const rungs = (path ?? "")
		.split("—")
		.map((part) => part.trim())
		.filter(Boolean);

	return (rungs.length > 1 ? rungs.slice(0, -1) : rungs).join(" · ");
}
