import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Icon } from "./icons";

export function FolderIcon() {
	return (
		<span className="folder-icon" aria-hidden="true">
			<Icon.folder size={24} />
		</span>
	);
}

/** One folder style for project registers, archives and file libraries. */
export function FolderTile({
	to,
	title,
	kicker,
	summary,
	footer,
	badge,
}: {
	to: string;
	title: ReactNode;
	kicker?: ReactNode;
	summary?: ReactNode;
	footer?: ReactNode;
	badge?: ReactNode;
}) {
	return (
		<Link to={to} className="site-folder-card">
			<div className="site-folder-heading">
				<FolderIcon />
				<div className="min-w-0 flex-1">
					{kicker && <span className="site-folder-kicker">{kicker}</span>}
					<h3 className="site-folder-title">{title}</h3>
				</div>
				<Icon.arrow size={16} />
			</div>
			{summary && <div className="site-folder-summary">{summary}</div>}
			{(footer || badge) && (
				<div className="site-folder-footer">
					<span>{footer}</span>
					{badge}
				</div>
			)}
		</Link>
	);
}
