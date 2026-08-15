import { useContent } from "./ContentProvider";

/**
 * The floating "edit this page" switch.
 *
 * Drawn only for somebody the server said may edit, and off by default. Off by
 * default matters: a coordinator who also uses the portal as a volunteer should
 * see the page a volunteer sees until they deliberately ask to change it,
 * otherwise every heading on every screen carries a pencil forever.
 *
 * Deliberately not a route. Editing the page you are looking at, on the page
 * you are looking at, is the whole point; a separate admin screen for the same
 * job exists as well, at /portal/admin/content, for bulk work.
 */
export function EditToolbar() {
	const { canEdit, editing, setEditing } = useContent();

	if (!canEdit) return null;

	return (
		<div className="fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full border border-hairline bg-white/95 px-2 py-1.5 shadow-pop backdrop-blur">
			<span className="pl-2 text-[11px] font-bold uppercase tracking-wider text-slate-faint">
				{editing ? "Editing" : "Page"}
			</span>
			<button
				type="button"
				onClick={() => setEditing(!editing)}
				aria-pressed={editing}
				className={
					editing
						? "rounded-full bg-signal px-4 py-1.5 text-[12px] font-bold text-white transition hover:bg-signal-dark"
						: "rounded-full bg-navy px-4 py-1.5 text-[12px] font-bold text-white transition hover:bg-navy/90"
				}
			>
				{editing ? "Done" : "Edit content"}
			</button>
		</div>
	);
}
