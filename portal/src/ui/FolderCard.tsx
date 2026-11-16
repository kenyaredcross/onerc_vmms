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

/**
 * A folder drawn the way the file library draws a file: a grey panel with the
 * folder in it, then the name and its facts underneath.
 *
 * **Every tile in a row is the same shape whatever was written.** The summary
 * is held to two lines and the name to two, so a programme somebody described
 * at length sits beside one described in four words without stretching the
 * row; the full text is one click away on the project itself.
 */
export function FolderPreviewTile({
	to,
	title,
	kicker,
	meta,
	summary,
	badge,
}: {
	to: string;
	title: ReactNode;
	/** Bottom left of the panel, where a file says "Word · DOCX". */
	kicker?: ReactNode;
	/** The facts line under the name: place and period. */
	meta?: ReactNode;
	summary?: ReactNode;
	/** Bottom right of the panel, where a file gives its size. */
	badge?: ReactNode;
}) {
	return (
		<Link to={to} className="folder-preview-card">
			<div className="folder-preview">
				<Icon.folder size={44} />
				{kicker && <span className="folder-preview-kicker">{kicker}</span>}
				{badge && <span className="folder-preview-badge">{badge}</span>}
			</div>
			<div className="folder-preview-information">
				<h3 className="folder-preview-title">{title}</h3>
				{meta && <span className="folder-preview-meta">{meta}</span>}
				{summary && <span className="folder-preview-summary">{summary}</span>}
			</div>
			<span className="folder-preview-arrow" aria-hidden="true">
				<Icon.arrow size={16} />
			</span>
		</Link>
	);
}
