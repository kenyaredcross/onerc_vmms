import { Link } from "react-router-dom";

import { initials, useSession } from "../../lib/session";
import { Icon } from "../../ui/icons";
import { Avatar, cx } from "../ui/kit";
import { usePopover } from "./popover";

/**
 * The account button and its menu.
 *
 * **The console switch is drawn only when it was passed a route**, and the
 * shell passes one only when `console.sections` said the person may open it.
 * This component never decides who may go there and never writes down where it
 * is.
 *
 * Sign out clears Frappe's session cookie and then hard-navigates to the
 * landing page, so nothing stale survives in memory.
 */
export function AccountMenu({
	name,
	email,
	console: consolePath,
}: {
	name: string | null;
	email: string | null;
	console: string | null;
}) {
	const { user, logout } = useSession();
	const { open, setOpen, holder, trigger } = usePopover();

	const display = name?.trim() || user || "You";

	const item =
		"flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] text-slate-strong transition hover:bg-canvas hover:text-ink";

	return (
		<div ref={holder} className="relative">
			<button
				ref={trigger}
				type="button"
				onClick={() => setOpen((was) => !was)}
				aria-haspopup="menu"
				aria-expanded={open}
				className={cx(
					"flex h-8 items-center gap-2 rounded-lg pl-1 pr-1.5 transition sm:pr-2",
					open ? "bg-rail-hover" : "hover:bg-rail-hover",
				)}
			>
				<Avatar name={display} size={26} />
				<span className="hidden max-w-[150px] truncate text-[12.5px] font-medium text-ink sm:block">
					{display}
				</span>
				<Icon.chevron
					size={13}
					className={cx("hidden flex-none text-slate-faint transition sm:block", open && "rotate-180")}
				/>
			</button>

			{open && (
				<div
					role="menu"
					className="absolute right-0 top-full z-50 mt-2 w-[248px] overflow-hidden rounded-xl border border-card-line bg-white p-1.5 shadow-[0_16px_40px_rgba(20,32,46,0.16)]"
				>
					<div className="border-b border-card-line px-3 pb-2.5 pt-1.5">
						<div className="truncate text-[13px] font-semibold text-ink">{display}</div>
						{email && <div className="truncate text-[11.5px] text-muted">{email}</div>}
					</div>

					<div className="py-1">
						<Link to="/profile" role="menuitem" onClick={() => setOpen(false)} className={item}>
							<Icon.user size={15} className="flex-none text-slate-faint" />
							View profile
						</Link>
						<Link
							to="/profile#account"
							role="menuitem"
							onClick={() => setOpen(false)}
							className={item}
						>
							<Icon.lock size={15} className="flex-none text-slate-faint" />
							Account and privacy
						</Link>
						<Link
							to="/profile#notifications"
							role="menuitem"
							onClick={() => setOpen(false)}
							className={item}
						>
							<Icon.bell size={15} className="flex-none text-slate-faint" />
							Notification preferences
						</Link>

						{consolePath && (
							<Link
								to={consolePath}
								role="menuitem"
								onClick={() => setOpen(false)}
								className={cx(item, "mt-1 border-t border-card-line pt-2.5")}
							>
								<Icon.external size={15} className="flex-none text-slate-faint" />
								Switch to manager console
							</Link>
						)}
					</div>

					<button
						type="button"
						role="menuitem"
						onClick={() => {
							void logout().then(() => {
								window.location.href = "/";
							});
						}}
						className="flex w-full items-center gap-3 rounded-lg border-t border-card-line px-3 py-2 text-[13px] text-danger transition hover:bg-danger-soft"
					>
						<Icon.signout size={15} className="flex-none" />
						Sign out
					</button>
				</div>
			)}
		</div>
	);
}

/** Re-exported so `PortalShell` can build the mobile-drawer avatar the same way. */
export { initials };
