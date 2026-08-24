import type { DeploymentSummary } from "../portal/types";

/**
 * The arithmetic behind the deployment dashboard, as pure functions.
 *
 * **Extracted from the screen on purpose.** These four numbers are the ones a
 * coordinator plans staffing from, and the words attached to them are
 * load-bearing: "deployed now" and "invited" used to be added together on one
 * tile, which reported people as being somewhere they had not agreed to go. A
 * rule that matters that much should be testable without rendering a page, and
 * `tests/counts.test.ts` is what holds it still.
 *
 * The vocabulary, once, here:
 *
 *   deployed now       Assigned or Accepted, on an **Active** deployment
 *   coming up          Assigned or Accepted, on a **Planned** deployment
 *   awaiting response  **Pending** — asked, no answer. Never a deployed person.
 *   open positions     `places_left`, on a deployment that is still running
 *
 * `assignment_counts.on_deployment` is the server's own Assigned+Accepted sum,
 * so nothing here re-derives what statuses mean.
 */

/** Deployment statuses that mean the work has not finished. */
export const RUNNING_STATUSES = ["Planned", "Active"] as const;

/** Deployment statuses that mean it has. Cancelled is history, never hidden. */
export const CLOSED_STATUSES = ["Completed", "Cancelled"] as const;

export interface DeploymentFigures {
	deployedNow: number;
	comingUp: number;
	awaitingResponse: number;
	openPositions: number;
	/** Total the society asked for, across still-running deployments. */
	requested: number;
	activeCount: number;
	plannedCount: number;
	runningCount: number;
	/**
	 * How many rows these figures were computed from.
	 *
	 * Carried so the screen can say "the most recent N" rather than implying a
	 * register total: `branch_deployments` returns one capped page and its own
	 * `count` is that page's length. See the backend-gap note.
	 */
	sampled: number;
}

function total(rows: DeploymentSummary[], pick: (row: DeploymentSummary) => number): number {
	return rows.reduce((sum, row) => sum + pick(row), 0);
}

export function figuresFor(rows: DeploymentSummary[]): DeploymentFigures {
	const active = rows.filter((row) => row.status === "Active");
	const planned = rows.filter((row) => row.status === "Planned");
	// `is_open` is the server's own answer, not a status comparison here.
	const running = rows.filter((row) => row.is_open);

	return {
		deployedNow: total(active, (row) => row.assignment_counts?.on_deployment ?? 0),
		comingUp: total(planned, (row) => row.assignment_counts?.on_deployment ?? 0),
		awaitingResponse: total(running, (row) => row.assignment_counts?.Pending ?? 0),
		// `places_left` is null where the society never said how many it needs,
		// and a deployment that has not said is never short — so null adds
		// nothing rather than being read as zero.
		openPositions: total(running, (row) => row.places_left ?? 0),
		requested: total(running, (row) => row.volunteers_required ?? 0),
		activeCount: active.length,
		plannedCount: planned.length,
		runningCount: running.length,
		sampled: rows.length,
	};
}

export interface Exception {
	row: DeploymentSummary;
	text: string;
	tone: "warning" | "danger";
}

/** How close to starting counts as "soon", in days. */
export const SOON_DAYS = 7;

/**
 * What a coordinator has to do something about.
 *
 * Every item is a fact read off the row, never a guess: nobody on the roster,
 * invitations nobody answered, places still open on something starting within
 * the week. A deployment can raise more than one.
 *
 * `now` is injectable so the "starts soon" rule is testable without freezing
 * the clock.
 */
export function exceptionsFor(rows: DeploymentSummary[], now: number = Date.now()): Exception[] {
	return rows
		.filter((row) => row.is_open)
		.flatMap((row) => {
			const found: Exception[] = [];
			const pending = row.assignment_counts?.Pending ?? 0;
			const on = row.assignment_counts?.on_deployment ?? 0;
			const left = row.places_left ?? 0;
			const soon =
				Boolean(row.start_date) &&
				new Date(row.start_date as string).getTime() - now < SOON_DAYS * 86_400_000;

			if (on === 0) found.push({ row, text: "Nobody on the roster yet", tone: "danger" });

			if (pending > 0)
				found.push({
					row,
					text: `${pending} invitation${pending === 1 ? "" : "s"} unanswered`,
					tone: "warning",
				});

			if (soon && left > 0)
				found.push({
					row,
					text: `Starts within the week · ${left} position${left === 1 ? "" : "s"} open`,
					tone: "warning",
				});

			return found;
		});
}
