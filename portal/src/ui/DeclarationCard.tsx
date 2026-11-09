import type { Declaration } from "../portal/types";
import { cx } from "./primitives";

/**
 * One declaration as a person reads and accepts it: title, version, the
 * society's wording (or a link to its own page) and a tick box.
 *
 * Shared by the registration form's declarations step and the portal's terms
 * panel, so the same declaration looks the same in both places. The wording is
 * HTML an administrator wrote on the desk, never an applicant.
 */
export function DeclarationCard({
	declaration,
	ticked,
	onToggle,
	badge,
}: {
	declaration: Declaration;
	ticked: boolean;
	onToggle: (yes: boolean) => void;
	/** A short word before the version, such as "Updated". */
	badge?: string;
}) {
	const id = `declaration-${declaration.name}`;

	return (
		<section
			className={cx(
				"overflow-hidden rounded-xl border transition",
				ticked ? "border-blue bg-rail/[0.03]" : "border-card-line bg-white",
			)}
		>
			<header className="flex items-baseline justify-between gap-4 border-b border-card-line px-5 py-3">
				<h3 className="text-[14.5px] font-bold text-ink">
					{declaration.title}
					{declaration.is_required && (
						<span className="ml-1 text-blue" aria-hidden="true">
							*
						</span>
					)}
				</h3>
				{/* Shown because it is stored. A person who asks later what
				    they agreed to gets an answer that names a version. */}
				<span className="flex-none text-[10.5px] font-semibold uppercase tracking-wider text-slate-faint">
					{badge ? `${badge} · ` : ""}Version {declaration.version}
				</span>
			</header>

			{/* Two ways a society publishes a policy, and the second one
			    is not a degraded first. A society whose legal team owns
			    the privacy notice on its own website is asked to link to
			    it rather than to keep a second copy here, so the form
			    sends the applicant to the page it names instead of
			    reprinting words it does not have. */}
			{declaration.source === "Link" ? (
				<div className="px-5 py-4">
					<a
						href={declaration.external_url ?? undefined}
						target="_blank"
						rel="noreferrer noopener"
						className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-ink underline"
					>
						Read {declaration.title.toLowerCase()}
						<span aria-hidden="true">↗</span>
					</a>
					<p className="mt-2 text-[12px] leading-relaxed text-slate-faint">
						Opens in a new tab.
					</p>
				</div>
			) : (
				<div
					className="space-y-2.5 px-5 py-4 text-[13px] leading-relaxed text-muted [&_a]:font-semibold [&_a]:text-ink [&_a]:underline"
					dangerouslySetInnerHTML={{ __html: declaration.body ?? "" }}
				/>
			)}

			<label
				htmlFor={id}
				className="flex cursor-pointer items-center gap-3 border-t border-card-line bg-surface/60 px-5 py-3.5"
			>
				<input
					id={id}
					type="checkbox"
					className="h-4 w-4 shrink-0 accent-brand"
					checked={ticked}
					onChange={(event) => onToggle(event.target.checked)}
				/>
				<span className="text-[13px] font-semibold text-ink">
					I have read and agree to this declaration
				</span>
			</label>
		</section>
	);
}
