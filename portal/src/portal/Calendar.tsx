import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatClock, formatDate } from "../lib/format";
import { Icon } from "../ui/icons";
import { isoDate, todayIso } from "../ui/MonthGrid";
import { CAL_META, CalendarGrid, type CalEntry } from "./ui/CalendarGrid";
import { Card, Empty, ErrorNote, Facts, PageHead, Spinner, cx } from "./ui/kit";
import type { DeploymentInvitation, EventCard, MyCertifications, TaskSummary } from "./types";

/**
 * A month at a time, and what the reader is doing in it.
 *
 * Four categories are layered onto one grid — tasks with a due date, accepted
 * deployments, events the person is attending, and certifications about to
 * lapse. Each is a separate possessive read, merged in the browser: there is no
 * combined endpoint and building one would be a fifth DTO to keep in step with
 * four that already exist.
 *
 * **Only the reader's own things.** The events tab is where somebody browses
 * what is on; this shows what is on *for them*, so events are filtered to the
 * ones they said they would attend.
 *
 * **One thing is selected and its detail sits beside the grid**, which is the
 * approved concept's shape and a better one than a day panel: a person clicks a
 * mission that runs for twelve days, not the eighth of those days, and what
 * they want next is the mission.
 */
export default function Calendar() {
	const now = new Date();
	const [year, setYear] = useState(now.getFullYear());
	const [month, setMonth] = useState(now.getMonth());
	const [selected, setSelected] = useState<string | null>(null);
	const detail = useRef<HTMLDivElement>(null);

	const range = useMemo(() => {
		const first = new Date(year, month, 1);
		const start = new Date(first);
		start.setDate(first.getDate() - ((first.getDay() + 6) % 7));
		const end = new Date(start);
		end.setDate(start.getDate() + 41);
		return { from: isoDate(start), to: isoDate(end) };
	}, [year, month]);

	const calendar = useFrappeGetCall<{
		message: { available: boolean; events: EventCard[]; attending: string[] };
	}>(
		API.eventsCalendar,
		{ date_from: range.from, date_to: range.to },
		`portal:calendar:${range.from}:${range.to}`,
	);
	const tasks = useFrappeGetCall<{
		message: { volunteer: string; tasks: TaskSummary[] } | null;
	}>(API.myTasks, { include_closed: 1 }, "portal:my_tasks:true");
	const invitations = useFrappeGetCall<{
		message: {
			volunteer: string;
			waiting: DeploymentInvitation[];
			answered: DeploymentInvitation[];
		} | null;
	}>(API.myInvitations, undefined, "portal:my_invitations");
	const certs = useFrappeGetCall<{ message: MyCertifications | null }>(
		API.myCertifications,
		undefined,
		"portal:my_certifications",
	);

	const loading = calendar.isLoading && tasks.isLoading && invitations.isLoading && certs.isLoading;

	const entries = useMemo<CalEntry[]>(() => {
		const out: CalEntry[] = [];

		const attending = new Set(calendar.data?.message?.attending ?? []);
		for (const event of calendar.data?.message?.events ?? []) {
			if (!event.start_date || !attending.has(event.event)) continue;
			out.push({
				id: `event-${event.event}`,
				kind: "event",
				title: event.title,
				start: event.start_date,
				end: event.end_date || event.start_date,
				time: formatClock(event.start_time),
				meta: event.venue || event.medium,
				metaLabel: "Where",
				summary: "You said you would be there.",
				to: `/events/${encodeURIComponent(event.event)}`,
				actionLabel: "View event",
			});
		}

		for (const task of tasks.data?.message?.tasks ?? []) {
			if (!task.due_on || task.status === "cancelled") continue;
			out.push({
				id: `task-${task.name}`,
				kind: "task",
				title: task.subject,
				start: task.due_on,
				end: task.due_on,
				meta: task.status === "completed" ? "Completed" : undefined,
				metaLabel: "State",
				summary:
					task.status === "completed"
						? "This task is done and signed off."
						: task.open_question
							? "A question of yours on this task is still unanswered."
							: "Work a coordinator has asked you to do.",
				to: `/tasks/${encodeURIComponent(task.name)}`,
				actionLabel: "Open task",
			});
		}

		for (const dep of invitations.data?.message?.answered ?? []) {
			if (dep.response !== "Accepted" || !dep.start_date) continue;
			out.push({
				id: `dep-${dep.assignment}`,
				kind: "deployment",
				title: dep.title ?? dep.deployment,
				start: dep.start_date,
				end: dep.end_date || dep.start_date,
				time: "Full-day deployment",
				meta: dep.role || dep.geo_node,
				metaLabel: dep.role ? "Role" : "Where",
				summary: "A mission you have accepted.",
				to: `/deployments/${encodeURIComponent(dep.deployment)}`,
				actionLabel: "Open deployment",
			});
		}

		// "Relevant" deadlines only — a certification lapsing within the season, or
		// already lapsed. One expiring in two years is not a calendar entry.
		const soon = new Date();
		soon.setDate(soon.getDate() + 120);
		const horizon = isoDate(soon);
		for (const cert of certs.data?.message?.certifications ?? []) {
			if (!cert.expiry_date) continue;
			if (!cert.lapsed && cert.expiry_date > horizon) continue;
			out.push({
				id: `cert-${cert.name}`,
				kind: "certification",
				title: `${cert.certification_type_name || cert.certification_type} ${
					cert.lapsed ? "lapsed" : "expires"
				}`,
				start: cert.expiry_date,
				end: cert.expiry_date,
				meta: cert.blocks_deployment ? "Required for deployment" : undefined,
				metaLabel: "Note",
				summary: cert.blocks_deployment
					? "You cannot be deployed while this is out of date."
					: "Part of your readiness record.",
				to: "/training",
				actionLabel: "Open training",
			});
		}

		return out;
	}, [calendar.data, tasks.data, invitations.data, certs.data]);

	// The entries in view this month, which is what the grid draws and what the
	// selection has to stay inside.
	const inMonth = useMemo(
		() => entries.filter((entry) => entry.end >= range.from && entry.start <= range.to),
		[entries, range],
	);

	const current = useMemo(
		() => inMonth.find((entry) => entry.id === selected) ?? null,
		[inMonth, selected],
	);

	// A month with nothing selected opens on the next thing in it, so the panel
	// beside the grid is never an empty box on arrival.
	useEffect(() => {
		if (current || inMonth.length === 0) return;
		const today = todayIso();
		const next =
			[...inMonth].sort((a, b) => a.start.localeCompare(b.start)).find((e) => e.end >= today) ??
			[...inMonth].sort((a, b) => a.start.localeCompare(b.start))[0];
		setSelected(next?.id ?? null);
	}, [current, inMonth]);

	const agenda = useMemo(() => {
		const from = todayIso();
		return [...entries]
			.filter((e) => e.end >= from && e.id !== selected)
			.sort((a, b) => a.start.localeCompare(b.start) || (a.time || "").localeCompare(b.time || ""))
			.slice(0, 6);
	}, [entries, selected]);

	const goToday = () => {
		const t = new Date();
		setYear(t.getFullYear());
		setMonth(t.getMonth());
		setSelected(null);
	};

	// Choosing something on a narrow screen puts the detail panel below the
	// grid, off-screen. Bring it into view rather than leaving the press with
	// no visible effect.
	const choose = (id: string) => {
		setSelected(id);
		if (typeof window !== "undefined" && window.matchMedia?.("(max-width: 1023px)").matches) {
			detail.current?.scrollIntoView({ behavior: "smooth", block: "start" });
		}
	};

	return (
		<>
			<PageHead
				eyebrow="Schedule"
				title={<EditableText k="portal.calendar.heading" fallback="Your calendar" />}
				lead="Your dated tasks, accepted deployments, the events you are attending, and any certification about to lapse. Hover an item for a preview; select it to open the full details alongside the calendar."
				actions={
					<button
						type="button"
						onClick={goToday}
						className="rounded-lg border border-card-line bg-white px-3.5 py-2 text-[12.5px] font-semibold text-slate-strong transition hover:border-slate-faint hover:text-ink"
					>
						Today
					</button>
				}
			/>

			{(calendar.error || tasks.error) && (
				<div className="mb-5">
					<ErrorNote>{errorMessage(calendar.error || tasks.error)}</ErrorNote>
				</div>
			)}

			<div className="grid grid-cols-1 items-start gap-[18px] lg:grid-cols-[minmax(0,1fr)_340px]">
				<Card className="p-5 sm:p-[22px]" pad={false}>
					{loading ? (
						<Spinner label="Loading your month…" />
					) : (
						<CalendarGrid
							year={year}
							month={month}
							entries={inMonth}
							selected={selected}
							onSelect={choose}
							onMonth={(y, m) => {
								setYear(y);
								setMonth(m);
								setSelected(null);
							}}
						/>
					)}
				</Card>

				<div ref={detail} className="lg:sticky lg:top-[72px]">
					<Card className="p-[22px]" pad={false}>
						<div aria-live="polite">
							{current ? (
								<Detail entry={current} />
							) : (
								<Empty framed={false} icon={Icon.calendar} title="Nothing on this month">
									Your dated tasks, deployments, registered events and certification deadlines
									appear here as they are set.
								</Empty>
							)}
						</div>

						<div className="my-5 h-px bg-card-line" />

						<h3 className="mb-1 text-[10.5px] font-bold uppercase tracking-[0.09em] text-rail-label">
							Coming up next
						</h3>
						{agenda.length === 0 ? (
							<p className="py-3 text-[12px] text-muted">Nothing else is scheduled.</p>
						) : (
							<div className="-mx-2">
								{agenda.map((entry) => (
									<button
										key={entry.id}
										type="button"
										onClick={() => choose(entry.id)}
										className="flex w-full items-start gap-3 border-t border-card-line px-2 py-3 text-left transition first:border-t-0 hover:bg-canvas"
									>
										<span
											className={cx(
												"mt-0.5 h-[30px] w-[4px] flex-none rounded-full",
												CAL_META[entry.kind].dot,
											)}
											aria-hidden="true"
										/>
										<span className="min-w-0 flex-1">
											<span className="block truncate text-[12.5px] font-semibold text-ink">
												{entry.title}
											</span>
											<span className="mt-0.5 block truncate text-[11.5px] text-slate-body">
												{[formatDate(entry.start), entry.meta].filter(Boolean).join(" · ")}
											</span>
										</span>
									</button>
								))}
							</div>
						)}
					</Card>
				</div>
			</div>
		</>
	);
}

/* ------------------------------------------------------------------ detail */

function Detail({ entry }: { entry: CalEntry }) {
	const dates =
		entry.start === entry.end
			? formatDate(entry.start)
			: `${formatDate(entry.start)} – ${formatDate(entry.end)}`;

	return (
		<div>
			<span
				className={cx(
					"inline-flex rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.08em]",
					entry.kind === "deployment"
						? "bg-rail text-white"
						: cx("bg-blue-soft", CAL_META[entry.kind].text),
				)}
			>
				{CAL_META[entry.kind].label}
			</span>

			<h2 className="mt-3.5 font-display text-[19px] font-bold leading-snug tracking-[-0.02em] text-ink">
				{entry.title}
			</h2>
			<p className="mt-1.5 text-[12px] text-slate-body">{dates}</p>

			<div className="my-4 border-y border-card-line py-4">
				<Facts
					columns={2}
					items={[
						{ label: "When", value: entry.time || "All day" },
						entry.meta ? { label: entry.metaLabel ?? "Where", value: entry.meta } : null,
					]}
				/>
			</div>

			{entry.summary && (
				<p className="text-[12.5px] leading-relaxed text-slate-body">{entry.summary}</p>
			)}

			<Link
				to={entry.to}
				className="mt-4 flex min-h-[42px] w-full items-center justify-center rounded-lg bg-rail px-4 text-[12.5px] font-bold text-white transition hover:bg-rail-soft"
			>
				{entry.actionLabel} →
			</Link>
		</div>
	);
}
