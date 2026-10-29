import { RecordCollection } from "../../ui/RecordPagination";
import { FolderIcon } from "../../ui/FolderCard";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { TermsOfReference } from "../../portal/types";
import { termsPdfUrl } from "../../lib/api";
import { DocumentIcon } from "../../ui/DocumentIcon";
import { Icon } from "../../ui/icons";
import { Empty, StateBadge } from "../../ui/primitives";

export function ProjectDocuments({ terms }: { terms: TermsOfReference[] }) {
	const [query, setQuery] = useState("");
	const [view, setView] = useState("grid");
	const [sort, setSort] = useState("name");
	const [folder, setFolder] = useState(false);
	const rows = useMemo(
		() =>
			terms
				.filter((row) => `${row.tor_name} ${row.name}`.toLowerCase().includes(query.toLowerCase()))
				.sort((a, b) =>
					sort === "name" ? a.tor_name.localeCompare(b.tor_name) : a.name.localeCompare(b.name),
				),
		[terms, query, sort],
	);
	return (
		<section aria-label="Project documents" className="project-documents">
			<div className="flex flex-wrap items-start justify-between gap-3">
				<div>
					<h2 className="text-[20px] font-semibold text-ink">Documents</h2>
					<p className="mt-1 text-[12px] text-muted">Terms of reference for this project.</p>
				</div>
				<Link to="/admin/deployments/terms?new=1" className="project-document-button">
					Write terms of reference
				</Link>
			</div>
			<div className="project-files-toolbar">
				<label className="project-files-search">
					<Icon.search size={16} />
					<span className="sr-only">Search project documents</span>
					<input
						type="search"
						placeholder="Search files by name or reference…"
						value={query}
						onChange={(e) => setQuery(e.target.value)}
					/>
				</label>
				<label className="project-files-sort">
					<span className="sr-only">Sort project documents</span>
					<select value={sort} onChange={(e) => setSort(e.target.value)}>
						<option value="name">Name A–Z</option>
						<option value="reference">Reference</option>
					</select>
				</label>
			</div>
			<div className="flex items-center justify-between">
				<h3 className="text-[14px] font-semibold">Folders</h3>
				<span className="text-[12px] text-muted">1 folder</span>
			</div>
			<button
				type="button"
				className="project-folder"
				aria-pressed={folder}
				onClick={() => setFolder(!folder)}
			>
				<FolderIcon />
				<span className="min-w-0">
					<strong className="block text-[13px] font-semibold">Terms of reference</strong>
					<span className="text-[12px] text-muted">
						{terms.length} {terms.length === 1 ? "document" : "documents"}
					</span>
				</span>
				<Icon.arrow size={15} />
			</button>
			<div className="flex flex-wrap items-center justify-between gap-3">
				<h3 className="text-[14px] font-semibold">
					{folder ? "Terms of reference" : "All files"}{" "}
					<span className="ml-1 text-[12px] font-normal text-muted">({rows.length})</span>
				</h3>
				<div className="project-file-view" role="group" aria-label="Document view">
					{["grid", "list"].map((mode) => (
						<button key={mode} type="button" aria-pressed={view === mode} onClick={() => setView(mode)}>
							{mode === "grid" ? "Grid view" : "List view"}
						</button>
					))}
				</div>
			</div>
			{!rows.length ? (
				<Empty title={query ? "No documents match your search" : "No documents yet"} />
			) : (
				<RecordCollection as="ul" className={`project-file-${view}`}>
					{rows.map((row) => (
						<li key={row.name} className="project-file-card">
							<Link
								to={`/admin/deployments/terms/${encodeURIComponent(row.name)}`}
								className="project-file-preview"
								aria-label={`Open ${row.tor_name}`}
							>
								<DocumentIcon />
								<span>PDF</span>
								<StateBadge state={row.approval_state || (row.is_draft ? "Draft" : "Submitted")} />
							</Link>
							<div className="project-file-information">
								<Link
									className="project-file-name"
									to={`/admin/deployments/terms/${encodeURIComponent(row.name)}`}
								>
									{row.tor_name}
								</Link>
								<span className="project-file-reference">{row.name}</span>
							</div>
							<a
								href={termsPdfUrl(row.name)}
								className="project-file-download"
								aria-label={`Print or save ${row.tor_name} as PDF`}
								title="Print / save PDF"
							>
								<Icon.download size={18} />
							</a>
						</li>
					))}
				</RecordCollection>
			)}
		</section>
	);
}
