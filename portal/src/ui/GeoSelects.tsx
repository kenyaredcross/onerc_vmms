import { useEffect, useState } from "react";
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
 *
 * **A rung with one possible answer answers itself and is not drawn.** The top
 * of a single-society ladder is the society, and every form in this product was
 * opening with a dropdown whose only option was the national society — a control
 * that exists to be dismissed, in front of the branch that is the real question.
 * The rule is not "hide National": it is that a *choice between one thing* is not
 * a choice, so it is taken rather than asked, at whatever rung it occurs. The
 * chosen node still appears in the summary line below the selects, so nothing is
 * decided out of sight.
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

/**
 * The chosen node, or null while the chain does not yet satisfy `allowedLevels`.
 *
 * **The deepest node the society records at, not the deepest node answered.**
 * These are the same thing whenever the permitted rung is the last one in the
 * tree, and they stop being the same the moment a society keeps geography below
 * the level it records at — Kenya's 47 counties with 290 sub-counties under
 * them, where `allowed_anchor_levels` names the county and the sub-counties are
 * there to be recognised rather than recorded at.
 *
 * On that tree, `browse` returns children for a county, so the picker draws a
 * Sub-County rung — correctly; it is a real part of the tree. Reading only the
 * last answer meant that answering that optional rung *un-chose* a perfectly
 * valid county: the step's guard saw null, Continue went dead, and the note
 * underneath said "keep going down to a County" to somebody who was already
 * below one. The only way out was to blank a dropdown, which is not a thing
 * anybody thinks to do.
 *
 * So the chain is searched from the bottom for the deepest rung that *is*
 * permitted. A chain with no permitted rung in it still reads as nothing chosen,
 * which is the half-walked case this has always been here to catch.
 */
export function selectedNode(chain: GeoNode[], allowedLevels?: string[]): GeoNode | null {
	const deepest = chain.length > 0 ? chain[chain.length - 1] : null;

	if (!deepest) return null;
	if (!allowedLevels?.length) return deepest;

	for (let index = chain.length - 1; index >= 0; index -= 1) {
		if (allowedLevels.includes(chain[index].level)) return chain[index];
	}

	return null;
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

	// Which rungs turned out to have exactly one answer and took it. Reported up
	// from each rung because only the rung knows — its options are its own fetch
	// — and held here because the *asterisk* is a property of the list: the first
	// question a person is actually asked is the one that is required, and that
	// is no longer index 0 once the top of the ladder answers itself.
	const [settled, setSettled] = useState<Record<number, boolean>>({});

	// Every rung the society has, or one past what has been answered while the
	// ladder is still loading. Showing them all at once is the point: somebody
	// can see how far down the form is going to ask them to go before they
	// start, rather than discovering a fourth dropdown after the third.
	const count = Math.max(rungs.length, chain.length + 1);

	const firstAsked = Array.from({ length: count }).findIndex((_, index) => !settled[index]);

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
						required={index === firstAsked}
						disabled={disabled || (index > 0 && !chain[index - 1])}
						onSettled={(only) =>
							setSettled((current) =>
								Boolean(current[index]) === only ? current : { ...current, [index]: only },
							)
						}
						onAnswer={(node) =>
							// Everything below the rung being answered is invalidated by
							// definition, so it goes rather than being left dangling.
							onChain(node ? [...chain.slice(0, index), node] : chain.slice(0, index))
						}
					/>
				))}
			</div>

			{/* One note for the whole picker, never one per rung. Four selects
			    that each fetch their own options each rendered their own copy of
			    the same failure, so a single expired session read as four
			    paragraphs of red under a form somebody had come to fill in. The
			    rungs now say "Unavailable" in the control itself and this says
			    the rest, once. */}
			{ladder.error && (
				<div className="mt-3">
					<ErrorNote>
						{errorMessage(ladder.error, "The list of branches could not be loaded.")}
					</ErrorNote>
				</div>
			)}

			<Verdict
				chain={chain}
				chosen={chosen}
				answered={chain.length > Math.max(firstAsked, 0)}
				// The rungs that answered themselves are not part of what anybody
				// chose, so the summary does not read them back. On a single-society
				// ladder that is the society's own name — "Tanzania Red Cross
				// Society · Arusha · Arusha City", where two thirds of the line is
				// the same on every screen in the product and the branch is the part
				// being confirmed. Sliced rather than filtered on the name: the rule
				// is "what you were not asked", which the list already knows, and it
				// holds at whatever rung it happens to occur.
				from={Math.max(firstAsked, 0)}
				allowedLevels={allowedLevels}
				levels={levels}
			/>
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
 *
 * **One option is not a choice.** When the tree offers exactly one node here,
 * this answers with it and draws nothing, so the form asks the next real
 * question instead. It reports that upward through `onSettled` so the list can
 * mark the first rung somebody is genuinely asked as the required one.
 */
function Rung({
	index,
	id,
	parent,
	chosen,
	fallbackLabel,
	required,
	disabled,
	onAnswer,
	onSettled,
}: {
	index: number;
	id: string;
	parent: GeoNode | null;
	chosen: GeoNode | null;
	fallbackLabel?: string;
	required: boolean;
	disabled: boolean;
	onAnswer: (node: GeoNode | null) => void;
	/** Called with whether this rung answered itself for want of an alternative. */
	onSettled: (only: boolean) => void;
}) {
	const waiting = index > 0 && !parent;

	const { data, error, isLoading } = useFrappeGetCall<{ message: { nodes: GeoNode[] } }>(
		API.geoBrowse,
		parent ? { parent: parent.name } : undefined,
		// No key means no request: a rung whose parent is unanswered asks nothing.
		waiting ? null : `geo:${parent?.name ?? "root"}`,
	);

	const nodes = data?.message?.nodes ?? [];

	// Settled once the options are known and there is only one of them. Held apart
	// from the effect below so the render can use it too: this is what decides
	// whether a control is drawn at all.
	const only = !waiting && !isLoading && !error && nodes.length === 1 ? nodes[0] : null;

	// In an effect rather than in the render body, because answering is a write
	// into the parent's chain and the render may be thrown away. Keyed on the
	// node's *name* rather than on the array, so a revalidation that returns the
	// same single node does not re-answer.
	useEffect(() => {
		onSettled(Boolean(only));
		if (only && !disabled && chosen?.name !== only.name) onAnswer(only);
		// `onAnswer` and `onSettled` are inline closures over the parent's current
		// chain and change on every render; depending on them would loop.
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [only?.name, chosen?.name, disabled]);

	// The nodes' own level name is the truth about what this rung is; the
	// ladder's is what to call it before any of them have arrived.
	const label = nodes[0]?.level_name ?? fallbackLabel ?? "Area";

	// Nothing beneath the rung above means this is the bottom of this branch of
	// the tree — not an error, and not an empty dropdown to stare at.
	if (index > 0 && !waiting && !isLoading && !error && nodes.length === 0) return null;

	// The single-answer case, taken above and not asked about here.
	if (only) return null;

	return (
		<Field label={label} htmlFor={id} required={required}>
			<div className="relative">
				<select
					id={id}
					disabled={disabled || isLoading}
					value={chosen?.name ?? ""}
					onChange={(event) =>
						onAnswer(nodes.find((node) => node.name === event.target.value) ?? null)
					}
					className={cx(
						"w-full appearance-none rounded-xl border border-card-line bg-white px-3.5 py-2.5 pr-9 text-[13.5px] text-ink transition",
						"focus:border-blue disabled:cursor-not-allowed disabled:bg-surface disabled:text-slate-faint",
					)}
				>
					<option value="">
						{isLoading
							? "Loading…"
							: error
								? "Unavailable"
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
	answered,
	from,
	allowedLevels,
	levels,
}: {
	chain: GeoNode[];
	chosen: GeoNode | null;
	/**
	 * The first rung this person was actually asked. Everything above it
	 * answered itself for want of an alternative and is not read back — see the
	 * call site.
	 */
	from: number;
	/**
	 * Whether the person has answered a rung they were actually asked. A rung
	 * that answered itself for want of an alternative fills the chain without
	 * anybody doing anything, and telling them to "keep going down" before they
	 * have been offered a single choice is scolding them for the form's own
	 * first move.
	 */
	answered: boolean;
	allowedLevels?: string[];
	levels: GeoLevel[];
}) {
	if (chosen) {
		return (
			<p className="mt-4 flex items-center gap-2 rounded-xl border border-blue/20 bg-rail/[0.04] px-3.5 py-2.5 text-[12.5px] text-ink">
				<span className="h-1.5 w-1.5 flex-none rounded-full bg-rail" aria-hidden="true" />
				<span className="min-w-0 truncate font-semibold">
					{(chain.length > from ? chain.slice(from) : chain)
						.map((node) => node.label)
						.join(" · ")}
				</span>
			</p>
		);
	}

	if (answered && chain.length > 0 && allowedLevels?.length) {
		const wanted = allowedLevels
			.map((key) => levels.find((level) => level.key === key)?.name ?? key)
			.join(" or ");

		return (
			<p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-2.5 text-[12.5px] text-amber-800">
				Keep going down to a <b>{wanted}</b>. That is the level this society records at.
			</p>
		);
	}

	return null;
}
