import { useFrappeGetCall } from "frappe-react-sdk";

import { API, errorMessage } from "../lib/api";
import type { GeoLevel, GeoNode } from "../portal/types";
import { Field } from "./form";
import { ErrorNote, cx } from "./primitives";

/**
 * Choosing a place, as one select field per rung of the society's hierarchy.
 *
 * **How many fields there are is configuration, not a number in this file.**
 * `geo.ladder` returns the society's active levels top-down, and this draws one
 * control for each: four levels, four selects. The lower ones sit disabled until
 * the one above them is answered, and answering a rung clears everything below
 * it — the only behaviour that can keep the chain honest, since a county belongs
 * to the region above it and changing the region cannot leave the county
 * standing.
 *
 * **The options are never guessed from the ladder.** Each rung's list is a real
 * `geo.browse(parent)` call, so a branch of the tree that stops early stops the
 * form early too, and a rung is labelled from the nodes that actually came back.
 * The ladder decides how many controls to *draw*; the tree decides what is *in*
 * them.
 *
 * **The chain is the parent's state, not this component's.** A wizard step that
 * can be left and come back to has to remember what was chosen, and the tidiest
 * way to guarantee that is to own it one level up: this component holds nothing,
 * runs no effects, and cannot get out of step with the form around it.
 *
 * **Which rung may be submitted is the server's rule.** `allowedLevels` (ACC-03)
 * arrives from `member.geo_node_levels`, which intersects the two configuration
 * surfaces that will judge the save. `selectedNode` below applies it, so a
 * half-walked chain reads as "nothing chosen" rather than as a value the server
 * is about to refuse.
 */

/**
 * How many controls to draw, and what to call each one before it has options.
 *
 * **A rung is an `order`, not a level.** Two societies can share one site — core
 * says so out loud, and `hierarchy_overview`'s `shares_order_with` exists for
 * exactly this — and each numbers its own ladder from 1. Counting *levels* on
 * such a site would draw six dropdowns for a hierarchy three deep. Counting
 * distinct orders draws three, which is the depth of the deeper of the two.
 *
 * Where two societies name the same rung differently ("Region" and "County"),
 * both names are shown until the answer above settles which tree is being walked
 * and the real nodes say what they are. That is honest about an ambiguity the
 * site genuinely has, rather than silently picking one society's word for it.
 */
function rungsOf(levels: GeoLevel[]): string[] {
	const byOrder = new Map<number, string[]>();

	for (const level of levels) {
		const names = byOrder.get(level.order) ?? [];
		if (!names.includes(level.name)) names.push(level.name);
		byOrder.set(level.order, names);
	}

	return [...byOrder.entries()]
		.sort(([a], [b]) => a - b)
		.map(([, names]) => names.join(" / "));
}

/** The chosen node, or null while the chain does not yet satisfy `allowedLevels`. */
export function selectedNode(chain: GeoNode[], allowedLevels?: string[]): GeoNode | null {
	const deepest = chain.length > 0 ? chain[chain.length - 1] : null;

	if (!deepest) return null;
	if (!allowedLevels?.length) return deepest;

	return allowedLevels.includes(deepest.level) ? deepest : null;
}

export function GeoSelects({
	chain,
	onChain,
	allowedLevels,
	idPrefix = "geo",
	disabled = false,
}: {
	/** The answered rungs, root first. */
	chain: GeoNode[];
	onChain: (chain: GeoNode[]) => void;
	/** Level keys a selection is permitted at. Empty or absent means any. */
	allowedLevels?: string[];
	/** Prefixes the generated input ids, so two pickers can share a page. */
	idPrefix?: string;
	disabled?: boolean;
}) {
	const ladder = useFrappeGetCall<{ message: { levels: GeoLevel[] } }>(
		API.geoLadder,
		undefined,
		"geo:ladder",
	);

	const levels = ladder.data?.message?.levels ?? [];
	const rungs = rungsOf(levels);
	const chosen = selectedNode(chain, allowedLevels);

	// Every rung the society has, or one past what has been answered while the
	// ladder is still loading. Showing them all at once is the point: somebody
	// can see how far down the form is going to ask them to go before they
	// start, rather than discovering a fourth dropdown after the third.
	const count = Math.max(rungs.length, chain.length + 1);

	return (
		<div>
			<div className="grid gap-4 sm:grid-cols-2">
				{Array.from({ length: count }).map((_, index) => (
					<Rung
						key={index}
						index={index}
						id={`${idPrefix}-rung-${index}`}
						parent={index === 0 ? null : (chain[index - 1] ?? null)}
						chosen={chain[index] ?? null}
						fallbackLabel={rungs[index]}
						disabled={disabled || (index > 0 && !chain[index - 1])}
						onAnswer={(node) =>
							// Everything below the rung being answered is invalidated by
							// definition, so it goes rather than being left dangling.
							onChain(node ? [...chain.slice(0, index), node] : chain.slice(0, index))
						}
					/>
				))}
			</div>

			{ladder.error && (
				<div className="mt-3">
					<ErrorNote>{errorMessage(ladder.error)}</ErrorNote>
				</div>
			)}

			<Verdict chain={chain} chosen={chosen} allowedLevels={allowedLevels} levels={levels} />
		</div>
	);
}

/**
 * One select: the children of the rung above it.
 *
 * It fetches its own options rather than being handed them, so answering a rung
 * loads exactly one list instead of the whole chain again. `geo.browse` with no
 * parent is the top of the tree, which is why the first rung passes `null`
 * rather than being a special case anywhere else.
 */
function Rung({
	index,
	id,
	parent,
	chosen,
	fallbackLabel,
	disabled,
	onAnswer,
}: {
	index: number;
	id: string;
	parent: GeoNode | null;
	chosen: GeoNode | null;
	fallbackLabel?: string;
	disabled: boolean;
	onAnswer: (node: GeoNode | null) => void;
}) {
	const waiting = index > 0 && !parent;

	const { data, error, isLoading } = useFrappeGetCall<{ message: { nodes: GeoNode[] } }>(
		API.geoBrowse,
		parent ? { parent: parent.name } : undefined,
		// No key means no request: a rung whose parent is unanswered asks nothing.
		waiting ? null : `geo:${parent?.name ?? "root"}`,
	);

	const nodes = data?.message?.nodes ?? [];

	// The nodes' own level name is the truth about what this rung is; the
	// ladder's is what to call it before any of them have arrived.
	const label = nodes[0]?.level_name ?? fallbackLabel ?? "Area";

	// Nothing beneath the rung above means this is the bottom of this branch of
	// the tree — not an error, and not an empty dropdown to stare at.
	if (index > 0 && !waiting && !isLoading && !error && nodes.length === 0) return null;

	return (
		<Field label={label} htmlFor={id} required={index === 0}>
			<div className="relative">
				<select
					id={id}
					disabled={disabled || isLoading}
					value={chosen?.name ?? ""}
					onChange={(event) =>
						onAnswer(nodes.find((node) => node.name === event.target.value) ?? null)
					}
					className={cx(
						"w-full appearance-none rounded-card border border-hairline-strong bg-white px-3.5 py-2.5 pr-9 text-[13.5px] text-ink transition",
						"focus:border-navy disabled:cursor-not-allowed disabled:bg-page disabled:text-slate-faint",
					)}
				>
					<option value="">
						{isLoading
							? "Loading…"
							: waiting
								? "Choose the one above first"
								: `Select ${label.toLowerCase()}`}
					</option>
					{nodes.map((node) => (
						<option key={node.name} value={node.name}>
							{node.label}
						</option>
					))}
				</select>
				<svg
					viewBox="0 0 24 24"
					width="15"
					height="15"
					fill="none"
					aria-hidden="true"
					className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-faint"
				>
					<path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
				</svg>
			</div>
			{error && <p className="mt-1.5 text-[11.5px] text-signal-dark">{errorMessage(error)}</p>}
		</Field>
	);
}

/**
 * What has been chosen, or what is still needed to have chosen anything.
 *
 * The second half only ever names a level the *server* named. Nothing here
 * decides that a deeper answer is required; it reports that the one given is not
 * among the permitted ones.
 */
function Verdict({
	chain,
	chosen,
	allowedLevels,
	levels,
}: {
	chain: GeoNode[];
	chosen: GeoNode | null;
	allowedLevels?: string[];
	levels: GeoLevel[];
}) {
	if (chosen) {
		return (
			<p className="mt-4 flex items-center gap-2 rounded-card border border-navy/20 bg-navy/[0.04] px-3.5 py-2.5 text-[12.5px] text-navy">
				<span className="h-1.5 w-1.5 flex-none rounded-full bg-navy" aria-hidden="true" />
				<span className="min-w-0 truncate font-semibold">
					{chain.map((node) => node.label).join(" · ")}
				</span>
			</p>
		);
	}

	if (chain.length > 0 && allowedLevels?.length) {
		const wanted = allowedLevels
			.map((key) => levels.find((level) => level.key === key)?.name ?? key)
			.join(" or ");

		return (
			<p className="mt-4 rounded-card border border-amber-200 bg-amber-50 px-3.5 py-2.5 text-[12.5px] text-amber-800">
				Keep going down to a <b>{wanted}</b>. That is the level this society records at.
			</p>
		);
	}

	return null;
}
