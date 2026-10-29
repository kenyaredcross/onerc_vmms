import { RecordCollection } from "../../ui/RecordPagination";
import { FolderIcon } from "../../ui/FolderCard";
import { useMemo, useState } from "react";
import type { OperationsDocumentsAnswer } from "../../portal/types";
import { formatDate } from "../../lib/format";
import { DocumentIcon, fileType } from "../../ui/DocumentIcon";
import { Icon } from "../../ui/icons";
import { Empty } from "../../ui/primitives";

export function OperationsFileLibrary({ answer, onSearch, onFolder }: { answer?: OperationsDocumentsAnswer; onSearch: (value:string)=>void; onFolder:(value:string)=>void }) {
	const [query, setQuery] = useState("");
	const [folder, setFolder] = useState("");
	const [view, setView] = useState("grid");
	const [sort, setSort] = useState("name");
	const rows = useMemo(
		() =>
			(answer?.files ?? [])
				.filter(
					(file) =>
						(!folder || file.attached_to_doctype === folder) &&
						`${file.file_name} ${file.attached_to_name}`.toLowerCase().includes(query.toLowerCase()),
				)
				.sort((a, b) =>
					sort === "name"
						? a.file_name.localeCompare(b.file_name)
						: (b.modified || b.creation).localeCompare(a.modified || a.creation),
				),
		[answer, query, folder, sort],
	);
	const types = answer?.record_types ?? [];
	return (
		<section className="project-documents" aria-label="Operations file library">
			<div className="project-files-toolbar">
				<label className="project-files-search">
					<Icon.search size={16} />
					<span className="sr-only">Search files and records</span>
					<input
						type="search"
						placeholder="Search files and records…"
						value={query}
						onChange={(e) => {setQuery(e.target.value);onSearch(e.target.value);}}
					/>
				</label>
				<label className="project-files-sort">
					<span className="sr-only">Sort files</span>
					<select value={sort} onChange={(e) => setSort(e.target.value)}>
						<option value="name">Name A–Z</option>
						<option value="modified">Recently updated</option>
					</select>
				</label>
			</div>
			<div className="flex items-center justify-between">
				<h2 className="text-[16px] font-semibold">Folders</h2>
				<span className="text-[12px] text-muted">{types.length} folders</span>
			</div>
			<div className="operations-folder-grid">
				{types.map((type) => (
					<button
						key={type}
						type="button"
						className="project-folder"
						aria-pressed={folder === type}
						onClick={() => {const next=folder === type ? "" : type;setFolder(next);onFolder(next);}}
					>
						<FolderIcon />
						<span className="min-w-0">
							<strong className="block text-[13px] font-semibold">{type.replace(/^VMMS /, "")}</strong>
							<span className="text-[12px] text-muted">
								{answer?.files.filter((file) => file.attached_to_doctype === type).length ?? 0} files
							</span>
						</span>
						<Icon.arrow size={15} />
					</button>
				))}
			</div>
			<div className="flex flex-wrap items-center justify-between gap-3">
				<div className="flex flex-wrap items-center gap-3">
					<h2 className="text-[16px] font-semibold">
						{folder ? folder.replace(/^VMMS /, "") : "All files"}{" "}
						<span className="text-[12px] font-normal text-muted">({rows.length})</span>
					</h2>
					{folder && (
						<button
							type="button"
							className="text-[12px] font-semibold underline"
							onClick={() => {setFolder("");onFolder("");}}
						>
							All folders
						</button>
					)}
				</div>
				<div className="project-file-view" role="group" aria-label="File view">
					{["grid", "list"].map((mode) => (
						<button key={mode} type="button" aria-pressed={view === mode} onClick={() => setView(mode)}>
							{mode === "grid" ? "Grid view" : "List view"}
						</button>
					))}
				</div>
			</div>
			{!rows.length ? (
				<Empty title={query || folder ? "No files match your filters" : "No files yet"} />
			) : (
				<RecordCollection as="ul" className={`project-file-${view} operations-files`}>
					{rows.map((file) => {
						const type = file.file_name.split(".").at(-1)?.toUpperCase() || "FILE";
						const size =
							file.file_size == null
								? ""
								: file.file_size < 1024
									? `${file.file_size} B`
									: file.file_size < 1024 * 1024
										? `${Math.round(file.file_size / 1024)} KB`
										: `${(file.file_size / (1024 * 1024)).toFixed(1)} MB`;
						return (
							<li key={file.name} className="project-file-card">
								<a
									href={file.file_url}
									target="_blank"
									rel="noreferrer"
									className="project-file-preview"
									aria-label={`Open ${file.file_name}`}
								>
									<DocumentIcon type={type} />
									<span>{fileType(type).toUpperCase() === type ? type : `${fileType(type)} · ${type}`}</span>
									{size && <span>{size}</span>}
								</a>
								<div className="project-file-information">
									<a href={file.file_url} target="_blank" rel="noreferrer" className="project-file-name">
										{file.file_name}
									</a>
									<span className="project-file-reference">
										<span>{file.attached_to_name}</span> · {file.is_private ? "Private" : "Shared"}
									</span>
									{file.modified && (
										<span className="project-file-reference">Updated {formatDate(file.modified)}</span>
									)}
								</div>
								<a
									href={file.file_url}
									download={file.file_name}
									className="project-file-download"
									aria-label={`Download ${file.file_name}`}
									title="Download"
								>
									<Icon.download size={18} />
								</a>
							</li>
						);
					})}
				</RecordCollection>
			)}
		</section>
	);
}
