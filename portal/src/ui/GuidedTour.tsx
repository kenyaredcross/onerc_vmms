import { useEffect, useLayoutEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

import { useSession } from "../lib/session";
import { Icon } from "./icons";

export interface TourStep {
	title: string;
	body: string;
	/** One or more possible targets. The first visible match is highlighted. */
	selector: string;
}

const START_EVENT = "vmms:start-tour";

export function startGuidedTour(id: string) {
	window.dispatchEvent(new CustomEvent(START_EVENT, { detail: { id } }));
}

/** Apply the signed-in workspace's compact desktop density at viewport level. */
export function useWorkspaceDensity() {
	useEffect(() => {
		document.documentElement.classList.add("workspace-density");
		return () => document.documentElement.classList.remove("workspace-density");
	}, []);
}

function stored(key: string): boolean {
	try {
		return window.localStorage.getItem(key) === "1";
	} catch {
		return false;
	}
}

function remember(key: string) {
	try {
		window.localStorage.setItem(key, "1");
	} catch {
		/* A tour may still run when private browsing refuses site storage. */
	}
}

/**
 * The document zoom this overlay is being drawn through, or 1 when there is none.
 *
 * `useWorkspaceDensity` zooms the whole document to 80% on desktop, and the
 * overlay is portalled into `document.body` — inside that zoom. Measurements do
 * not live in the same units as what is written back: `getBoundingClientRect`
 * and `window.innerWidth` answer in real viewport pixels, which the zoom has
 * already been applied to, while an inline `px` on a portalled element is a
 * pre-zoom length that gets scaled on the way to the screen. Handing the first
 * straight to the second scales it twice and draws a highlight at 80% of the
 * element it is pointing at. Dividing by this converts one into the other.
 */
function overlayZoom(): number {
	const zoom = Number(getComputedStyle(document.documentElement).zoom);

	return Number.isFinite(zoom) && zoom > 0 ? zoom : 1;
}

/** The card's own size, near enough to choose a side with. */
const CARD_WIDTH = 340;
const CARD_HEIGHT = 220;
const GAP = 14;
const EDGE = 16;

/**
 * Where to put the card so it explains the highlight instead of covering it.
 *
 * Below the target is the first choice and above it the second, which between
 * them cover an ordinary target. Neither fits when the target is a full-height
 * rail — the first step of both tours — and that is the case worth handling:
 * falling back to "above, clamped to the top edge" would drop the card straight
 * onto the navigation the step is asking the reader to look at. So a target too
 * tall to sit under or over gets the card beside it instead.
 */
function place(
	box: { left: number; top: number; width: number; height: number } | null,
	viewWidth: number,
	viewHeight: number,
): { top: number; left: number } {
	if (!box) {
		return {
			top: Math.max(EDGE, viewHeight / 2 - CARD_HEIGHT / 2),
			left: Math.max(EDGE, viewWidth / 2 - CARD_WIDTH / 2),
		};
	}

	const alignLeft = Math.min(Math.max(EDGE, box.left), Math.max(EDGE, viewWidth - CARD_WIDTH - EDGE));
	const alignTop = Math.min(Math.max(EDGE, box.top), Math.max(EDGE, viewHeight - CARD_HEIGHT - EDGE));

	if (box.top + box.height + GAP + CARD_HEIGHT < viewHeight) {
		return { top: box.top + box.height + GAP, left: alignLeft };
	}

	if (box.top - GAP - CARD_HEIGHT > EDGE) {
		return { top: box.top - GAP - CARD_HEIGHT, left: alignLeft };
	}

	const beside = box.left + box.width + GAP;
	if (beside + CARD_WIDTH + EDGE < viewWidth) return { top: alignTop, left: beside };

	const before = box.left - GAP - CARD_WIDTH;
	if (before > EDGE) return { top: alignTop, left: before };

	return { top: alignTop, left: alignLeft };
}

function visibleTarget(selector: string): HTMLElement | null {
	for (const node of document.querySelectorAll<HTMLElement>(selector)) {
		const rect = node.getBoundingClientRect();
		if (rect.width > 1 && rect.height > 1) return node;
	}
	return null;
}

/**
 * First-visit orientation for the two signed-in workspaces.
 *
 * The highlight is rendered into `document.body` so its fixed coordinates are
 * in the same viewport space as the element it points at, including after the
 * user changes browser zoom.
 */
export function GuidedTour({ id, steps }: { id: string; steps: TourStep[] }) {
	const { user } = useSession();
	const key = useMemo(() => `vmms.tour.${id}.${user || "user"}.v1`, [id, user]);
	const [open, setOpen] = useState(false);
	const [index, setIndex] = useState(0);
	const [rect, setRect] = useState<DOMRect | null>(null);

	useEffect(() => {
		if (stored(key)) return;
		const timer = window.setTimeout(() => setOpen(true), 650);
		return () => window.clearTimeout(timer);
	}, [key]);

	useEffect(() => {
		const start = (event: Event) => {
			const detail = (event as CustomEvent<{ id?: string }>).detail;
			if (!detail?.id || detail.id === id) {
				setIndex(0);
				setOpen(true);
			}
		};
		window.addEventListener(START_EVENT, start);
		return () => window.removeEventListener(START_EVENT, start);
	}, [id]);

	useLayoutEffect(() => {
		if (!open) return;

		const update = () => {
			const target = visibleTarget(steps[index]?.selector ?? "");
			setRect(target?.getBoundingClientRect() ?? null);
		};

		update();
		window.addEventListener("resize", update);
		window.addEventListener("scroll", update, true);
		return () => {
			window.removeEventListener("resize", update);
			window.removeEventListener("scroll", update, true);
		};
	}, [index, open, steps]);

	useEffect(() => {
		if (!open) return;
		const close = (event: KeyboardEvent) => {
			if (event.key === "Escape") {
				remember(key);
				setOpen(false);
			}
		};
		document.addEventListener("keydown", close);
		return () => document.removeEventListener("keydown", close);
	}, [key, open]);

	if (!open || steps.length === 0) return null;

	const step = steps[index];
	const pad = 7;
	// Measurements come back in real viewport pixels; everything below is written
	// back as inline `px` inside the zoomed document. Undo the zoom once, here,
	// and the rest of this arithmetic is in one set of units.
	const zoom = overlayZoom();
	const viewWidth = window.innerWidth / zoom;
	const viewHeight = window.innerHeight / zoom;
	const box = rect
		? {
			left: Math.max(0, rect.left / zoom - pad),
			top: Math.max(0, rect.top / zoom - pad),
			width: rect.width / zoom + pad * 2,
			height: rect.height / zoom + pad * 2,
		}
		: null;
	const { top: tooltipTop, left: tooltipLeft } = place(box, viewWidth, viewHeight);

	const finish = () => {
		remember(key);
		setOpen(false);
	};

	return createPortal(
		<div className="fixed inset-0 z-[1000] font-plex" aria-live="polite">
			{box ? (
				<div
					className="pointer-events-none fixed rounded-xl ring-2 ring-white"
					style={{
						...box,
						boxShadow: "0 0 0 9999px rgb(7 21 38 / 0.7), 0 0 0 4px rgb(21 94 239 / 0.9)",
					}}
				/>
			) : (
				<div className="fixed inset-0 bg-[#071526]/70" />
			)}

			<div
				role="dialog"
				aria-modal="true"
				aria-labelledby={`tour-${id}-title`}
				className="fixed w-[340px] max-w-[calc(100vw-32px)] rounded-xl border border-card-line bg-white p-5 text-ink shadow-[0_20px_60px_rgba(1,30,65,0.28)]"
				style={{ top: tooltipTop, left: tooltipLeft }}
			>
				<div className="mb-3 flex items-center justify-between gap-3">
					<span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-blue">
						Quick tour · {index + 1} of {steps.length}
					</span>
					<button
						type="button"
						onClick={finish}
						aria-label="Close tour"
						className="grid h-7 w-7 place-items-center rounded-lg text-muted hover:bg-canvas hover:text-ink"
					>
						<Icon.cross size={15} />
					</button>
				</div>
				<h2 id={`tour-${id}-title`} className="text-[18px] font-semibold tracking-[-0.015em]">
					{step.title}
				</h2>
				<p className="mt-2 text-[13px] leading-relaxed text-muted">{step.body}</p>
				<div className="mt-5 flex items-center gap-2">
					<button
						type="button"
						onClick={finish}
						className="mr-auto px-1 py-2 text-[12.5px] font-medium text-muted hover:text-ink"
					>
						Skip tour
					</button>
					{index > 0 && (
						<button
							type="button"
							onClick={() => setIndex(index - 1)}
							className="rounded-lg border border-card-line px-3.5 py-2 text-[12.5px] font-semibold text-slate-strong hover:bg-canvas"
						>
							Back
						</button>
					)}
					<button
						type="button"
						autoFocus
						onClick={() => (index === steps.length - 1 ? finish() : setIndex(index + 1))}
						className="rounded-lg bg-blue px-4 py-2 text-[12.5px] font-semibold text-white hover:bg-blue-hover"
					>
						{index === steps.length - 1 ? "Finish" : "Next"}
					</button>
				</div>
			</div>
		</div>,
		document.body,
	);
}
