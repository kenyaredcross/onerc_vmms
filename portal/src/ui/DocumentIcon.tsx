export function fileType(extension: string) {
	const ext = extension.toUpperCase();
	if (["DOC", "DOCX", "ODT", "RTF"].includes(ext)) return "Word";
	if (["XLS", "XLSX", "ODS"].includes(ext)) return "Excel";
	if (["PPT", "PPTX", "ODP"].includes(ext)) return "PowerPoint";
	if (["JPG", "JPEG", "PNG", "GIF", "WEBP", "SVG"].includes(ext)) return "Image";
	if (["ZIP", "RAR", "7Z", "TAR", "GZ"].includes(ext)) return "Archive";
	if (["JSON", "XML", "HTML", "JS", "TS"].includes(ext)) return "Code";
	if (ext === "CSV") return "CSV";
	if (ext === "PDF") return "PDF";
	if (["TXT", "MD"].includes(ext)) return "Text";
	return "File";
}

/** Distinct file-type symbols in the site's navy and red palette. */
export function DocumentIcon({ size = 48, type = "PDF" }: { size?: number; type?: string }) {
	const kind = fileType(type);
	const text = (value: string, x = 21, y = 38, fontSize = 15) => (
		<text
			x={x}
			y={y}
			textAnchor="middle"
			fill="currentColor"
			stroke="none"
			fontFamily="system-ui,sans-serif"
			fontSize={fontSize}
			fontWeight="700"
		>
			{value}
		</text>
	);
	return (
		<svg
			width={size}
			height={size}
			viewBox="0 0 48 56"
			fill="none"
			aria-hidden="true"
			data-file-icon={kind}
			className={`document-type-icon ${kind === "PDF" ? "document-type-pdf" : ""}`}
		>
			<path
				d="M28 3H10a5 5 0 0 0-5 5v40a5 5 0 0 0 5 5h28a5 5 0 0 0 5-5V18L28 3Z"
				stroke="currentColor"
				strokeWidth="2.5"
				strokeLinejoin="round"
			/>
			<path d="M28 3v12a3 3 0 0 0 3 3h12" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" />
			<g stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
				{kind === "PDF" && (
					<>
						<path d="M18 43c4-8 9-22 7-25-3-4-3 8 2 15 4 5 11 5 9 2-3-4-21 1-23 6-1 3 3 4 5 2Z" />
						<path d="M12 47h23" strokeWidth="1" />
					</>
				)}
				{kind === "Word" && (
					<>
						<path d="M29 28h7M29 34h7M29 40h7" />
						{text("W", 18, 39, 19)}
					</>
				)}
				{(kind === "Excel" || kind === "CSV") && (
					<>
						<path d="M29 27h7v16h-7M29 32h7M29 38h7M33 27v16" />
						{text(kind === "CSV" ? "," : "X", 18, 39, 20)}
					</>
				)}
				{kind === "PowerPoint" && (
					<>
						<path d="M31 29v9h8M34 26a9 9 0 0 1 6 9h-6v-9Z" />
						{text("P", 17, 40, 21)}
					</>
				)}
				{kind === "Image" && (
					<>
						<circle cx="17" cy="28" r="3" />
						<path d="M11 44l9-10 6 6 5-6 7 10H11Z" />
					</>
				)}
				{kind === "Archive" && (
					<>
						<path d="M21 20h5m-5 6h5m-5 6h5m-5 6h5" />
						<rect x="20" y="42" width="7" height="7" rx="2" />
					</>
				)}
				{kind === "Code" && (
					<>
						<path d="m18 29-6 6 6 6m12-12 6 6-6 6m-4-15-4 21" />
					</>
				)}
				{(kind === "Text" || kind === "File") && <path d="M13 28h22M13 34h22M13 40h15" />}
			</g>
		</svg>
	);
}
