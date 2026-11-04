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
	if (!value) return "Not available";

	const date = new Date(value.length <= 10 ? `${value}T00:00:00` : value);
	if (Number.isNaN(date.getTime())) return "Not available";

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
	if (amount === null || amount === undefined) return "Not available";

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
 * A place, by its own name: "Baringo", not "Baringo · KRCS South Rift · Kenya
 * Red Cross Society".
 *
 * Core renders a path deepest-first and joined with em dashes, so the place a
 * record belongs to is the first rung. The region and the society above it are
 * the society's own structure, and everybody reading this already knows which
 * region a county sits in, so they are not shown anywhere on the site. A record
 * anchored at the society itself has a one-rung path, and that rung is shown.
 */
export function geoPath(path: string | null | undefined): string {
	return (path ?? "").split("—").map((part) => part.trim()).find(Boolean) ?? "";
}

/** The same rule. Kept as a name because sixty screens ask for a branch by it. */
export const branchPath = geoPath;
