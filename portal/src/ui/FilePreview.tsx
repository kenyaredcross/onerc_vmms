import { useState } from "react";

import { Icon } from "./icons";
import { cx } from "./primitives";

/** What a file is, from its name: a picture, a PDF, or anything else. */
export function fileKind(name: string): "image" | "pdf" | "other" {
	const extension = name.split("?")[0].split(".").pop()?.toLowerCase() ?? "";
	if (["png", "jpg", "jpeg", "gif", "webp", "bmp", "svg"].includes(extension)) return "image";
	if (extension === "pdf") return "pdf";
	return "other";
}

/** The name a person gave a file, from its URL. */
export function fileNameOf(url: string): string {
	const last = url.split("?")[0].split("/").pop() ?? "";
	try {
		return decodeURIComponent(last) || "File";
	} catch {
		return last || "File";
	}
}

/** The address that shows a file in the page instead of downloading it. */
export function inlineUrl(url: string): string {
	return url.includes("download_evidence") ? `${url}${url.includes("?") ? "&" : "?"}inline=1` : url;
}

/**
 * A file shown as itself: a picture as a thumbnail, a PDF as a small page,
 * anything else as its name. Opens full size in a new tab.
 */
export function FilePreview({
	url,
	name,
	label,
	className,
}: {
	url: string;
	name?: string;
	/** What the file is, e.g. "Good Conduct". The file name is shown under it. */
	label?: string;
	className?: string;
}) {
	const fileName = name || fileNameOf(url);
	const kind = fileKind(fileName);
	const shown = inlineUrl(url);
	const [failed, setFailed] = useState(false);

	return (
		<figure className={cx("overflow-hidden rounded-xl border border-card-line bg-white", className)}>
			<a
				href={shown}
				target="_blank"
				rel="noreferrer"
				className="block bg-surface"
				aria-label={`Open ${label ?? fileName}`}
			>
				{kind === "image" && !failed ? (
					<img
						src={shown}
						alt={label ?? fileName}
						loading="lazy"
						onError={() => setFailed(true)}
						className="h-40 w-full object-contain"
					/>
				) : kind === "pdf" && !failed ? (
					<object data={shown} type="application/pdf" className="pointer-events-none h-40 w-full" aria-hidden="true">
						<FileIcon />
					</object>
				) : (
					<FileIcon />
				)}
			</a>
			<figcaption className="flex items-start justify-between gap-2 border-t border-card-line px-3 py-2.5">
				<span className="min-w-0">
					{label && <span className="block truncate text-[12.5px] font-semibold text-ink">{label}</span>}
					<span className="block truncate text-[11.5px] text-muted">{fileName}</span>
				</span>
				<span className="flex flex-none items-center gap-2">
					<a
						href={shown}
						target="_blank"
						rel="noreferrer"
						className="text-[12px] font-bold text-ink hover:underline"
					>
						View
					</a>
					<a href={url} download className="text-muted hover:text-ink" aria-label={`Download ${fileName}`}>
						<Icon.download size={14} />
					</a>
				</span>
			</figcaption>
		</figure>
	);
}

function FileIcon() {
	return (
		<span className="grid h-40 w-full place-items-center text-slate-faint">
			<Icon.file size={34} />
		</span>
	);
}

/** A file named in a sentence or a table cell: its name, opening it in a new tab. */
export function FileLink({ url, name, className }: { url: string; name?: string; className?: string }) {
	const fileName = name || fileNameOf(url);
	return (
		<a
			href={inlineUrl(url)}
			target="_blank"
			rel="noreferrer"
			className={cx(
				"inline-flex max-w-full items-center gap-1.5 font-semibold text-ink underline underline-offset-2",
				className,
			)}
		>
			{fileKind(fileName) === "image" ? <Icon.image size={13} /> : <Icon.file size={13} />}
			<span className="truncate">{fileName}</span>
		</a>
	);
}
