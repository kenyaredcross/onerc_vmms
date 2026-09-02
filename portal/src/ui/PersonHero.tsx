import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import type { RegisterEntry, Registers } from "../portal/types";
import { Avatar, Card, StateBadge, cx } from "./primitives";

/**
 * One person, at the top of every screen that is about them.
 *
 * **Why this is a component and not a pattern.** A volunteer's record, a
 * member's record, an application waiting on an approver and the portal's own
 * profile page are four screens about a human being, and each of them had grown
 * its own header: one drew a photograph, one drew initials, one drew neither and
 * opened with a docname. A coordinator moving between them was being asked to
 * re-learn where the name is on every hop, and the one screen that showed no
 * face was the one where getting the wrong person costs the most — an approval.
 * So there is exactly one header for a person now, and these four call it.
 *
 * **The face is the point, not the decoration.** Everything else on these pages
 * is a claim about somebody; the photograph is the only element that answers
 * "is this the person in front of me", which is the question actually being
 * asked at a branch counter. It is therefore the largest thing in the block and
 * it comes first. `photo` is a file URL on this site or null, and null is
 * entirely ordinary — most people registered from a paper form have never
 * uploaded one, so `Avatar` draws their initials rather than a stock silhouette
 * or a broken image.
 *
 * **The facts panel is deliberately shallow.** Four to six pairs, the ones
 * somebody needs to *act*: how to reach this person, what their record is
 * called, where they are. Everything else belongs to the cards below, and a
 * header that tries to carry the whole record stops being a header. Callers pass
 * what matters for their surface, so the volunteer page leads with a serving
 * branch and the membership office leads with a date of birth, without either
 * screen re-implementing the block.
 *
 * **Nothing here decides anything.** No permission is read, no status compared;
 * badges and facts are rendered as given. Every screen using this already knows
 * what its own server told it.
 */
export interface PersonFact {
	label: string;
	value: ReactNode;
}

export function PersonHero({
	name,
	photo,
	docname,
	subtitle,
	status,
	badges,
	facts,
	actions,
	className,
}: {
	/** What to call them. Falls back to the docname rather than rendering blank. */
	name?: string | null;
	photo?: string | null;
	/**
	 * The opaque record number, kept visible and copyable: it is what an audit
	 * trail, a report and a support conversation refer to.
	 */
	docname?: string | null;
	/** Their standing in words — a role, a membership type, a branch. */
	subtitle?: ReactNode;
	/** The register's own status word. Passed to `StateBadge`, never compared here. */
	status?: string | null;
	/** Anything else that belongs beside the status — cross-register links, flags. */
	badges?: ReactNode;
	facts?: PersonFact[];
	/** Buttons that act on this person, kept out of the facts panel. */
	actions?: ReactNode;
	className?: string;
}) {
	// A header shows what is known. An empty pair here would be four characters
	// of "Not recorded" in the most prominent block on the page, which is the
	// opposite of what a header is for — the cards below are where a screen
	// says out loud that something is missing, because down there the *absence*
	// is the finding.
	const rows = (facts ?? []).filter((fact) => fact.value !== undefined && fact.value !== null && fact.value !== "");

	return (
		<Card className={cx("mb-5", className)}>
			<div
				className={cx(
					"grid gap-6",
					// The facts panel takes slightly more room than the face, because
					// it holds two columns of pairs and the face holds one name. Below
					// `lg` they stack and the divider becomes a rule above, which is
					// the only thing that changes.
					rows.length > 0 && "lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] lg:gap-8",
				)}
			>
				<div className="flex min-w-0 items-center gap-5">
					<Avatar name={name} photo={photo} size={84} ring />

					<div className="min-w-0">
						<h2 className="text-[21px] font-semibold leading-tight tracking-tight text-ink">
							{name || docname || "Unnamed"}
						</h2>

						{subtitle && (
							<p className="mt-1 text-[13px] leading-snug text-muted">{subtitle}</p>
						)}

						{(status || badges) && (
							<div className="mt-2.5 flex flex-wrap items-center gap-2">
								{status && <StateBadge state={status} />}
								{badges}
							</div>
						)}

						{docname && (
							<p className="tabular mt-2 font-mono text-[11.5px] text-slate-faint">
								{docname}
							</p>
						)}
					</div>
				</div>

				{rows.length > 0 && (
					<dl className="grid content-start gap-x-8 gap-y-3 border-t border-card-line pt-5 sm:grid-cols-2 lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0">
						{rows.map((fact) => (
							<div key={fact.label} className="flex items-baseline gap-2">
								<dt className="w-[96px] flex-none text-[11.5px] leading-snug text-slate-faint">
									{fact.label}
								</dt>
								<dd className="min-w-0 break-words text-[13px] font-semibold leading-snug text-ink">
									{fact.value}
								</dd>
							</div>
						))}
					</dl>
				)}
			</div>

			{actions && (
				<div className="mt-5 flex flex-wrap gap-2 border-t border-card-line pt-5">{actions}</div>
			)}
		</Card>
	);
}

/**
 * The other registers this person is in, as links.
 *
 * **The question this answers is asked at every counter.** Somebody opening a
 * volunteer is immediately asked whether that person is also a member, and the
 * only way to find out used to be to leave the page and search the other
 * register by name. One hop through the shared Red Profile answers it, and the
 * answer belongs beside the person's name rather than in a card three screens
 * down.
 *
 * **The register the reader is already on is not drawn.** Telling somebody
 * looking at `VOL-00042` that this person is a volunteer is a chip that says
 * nothing, and it takes the place of the one that says something.
 *
 * **Absent is ordinary.** Most people are in exactly one register, and so is
 * anyone whose other record sits at a branch this reader may not see — the
 * server does not distinguish the two and neither does this. Nothing is drawn,
 * rather than an empty state explaining that nothing was found.
 */
export function RegisterLinks({ registers, except }: { registers?: Registers; except?: string }) {
	const entries = (["volunteer", "member"] as const)
		.map((kind) => registers?.[kind])
		.filter((entry): entry is RegisterEntry => !!entry && entry.kind !== except);

	if (entries.length === 0) {
		return null;
	}

	return (
		<>
			{entries.map((entry) => (
				<Link
					key={entry.kind}
					to={`/admin/registry/${entry.kind}/${encodeURIComponent(entry.name)}`}
					className="inline-flex items-center gap-1.5 rounded-full border border-blue/20 bg-rail/[.05] px-3 py-1 text-[11.5px] font-bold text-ink transition hover:border-blue hover:bg-rail/10"
				>
					Also a {entry.label.toLowerCase()}
					{/* The other register's own status word, passed through. It is a
					    different vocabulary from this page's and is never compared
					    with it — see `api/person.py`. */}
					{entry.status && (
						<span className="font-semibold text-ink/70">· {entry.status}</span>
					)}
				</Link>
			))}
		</>
	);
}
