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
 * An amount with the society's currency, when there is one.
 *
 * `currency` comes from configuration and may be absent on a site nobody has
 * finished setting up. Absent means the number is shown bare, which is honest,
 * rather than a symbol this app picked.
 */
export function formatMoney(amount: number | null | undefined, currency?: string | null): string {
	if (amount === null || amount === undefined) return "—";

	if (currency) {
		try {
			return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(amount);
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
