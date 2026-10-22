import { useEffect, useId, useRef, useState } from "react";
import { useFrappeGetCall } from "frappe-react-sdk";

import { API, errorMessage, myCertificateUrl } from "../../lib/api";
import { Icon } from "../../ui/icons";
import { ErrorNote, Skeleton } from "./kit";

/** Home shows compact links; the society's issued document is fetched on preview. */
type HomeDocumentProps =
	| { kind: "volunteer"; number: string; membership?: never }
	| { kind: "member"; number: string; membership: string };

export function HomeDocument({ kind, number, membership }: HomeDocumentProps) {
	const [hovered, setHovered] = useState(false);
	const [expanded, setExpanded] = useState(false);
	const dialog = useRef<HTMLDialogElement>(null);
	const heading = useId();
	const popup = useId();
	const modal = useId();
	const label = kind === "volunteer" ? "Volunteer ID" : "Membership certificate";
	const DocumentIcon = kind === "volunteer" ? Icon.card : Icon.award;
	const download = kind === "volunteer"
		? "/api/method/vmmsx.api.cards.download_my_card?kind=volunteer"
		: myCertificateUrl(membership);

	useEffect(() => {
		if (!hovered) return;
		const dismiss = (event: KeyboardEvent) => {
			if (event.key === "Escape") setHovered(false);
		};
		document.addEventListener("keydown", dismiss);
		return () => document.removeEventListener("keydown", dismiss);
	}, [hovered]);

	return (
		<div className="home-document-access"
			onMouseEnter={() => setHovered(true)}
			onMouseLeave={() => setHovered(false)}
			onFocus={() => { if (!expanded) setHovered(true); }}
			onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setHovered(false); }}
		>
			<button type="button" className="home-record-document"
				aria-label={`View ${label.toLowerCase()}`} aria-haspopup="dialog"
				aria-expanded={hovered || expanded} aria-controls={expanded ? modal : hovered ? popup : undefined}
				onClick={() => { setHovered(false); setExpanded(true); dialog.current?.showModal(); }}
			>
				<span className="home-record-document-icon"><DocumentIcon size={17} /></span>
				<span className="min-w-0 flex-1 text-left">
					<strong className="block text-[11.5px] font-semibold">{label}</strong>
					<span className="mt-0.5 block font-mono text-[10px] text-muted">{number}</span>
				</span>
				<span className="shrink-0 text-[11px] font-semibold">View <span aria-hidden="true">→</span></span>
			</button>
			{hovered && !expanded && (
				<div id={popup} role="region" aria-label={`${label} preview`} className="home-document-hover">
					<div className="home-document-hover-content">
						<DocumentBody kind={kind} membership={membership} label={label} />
					</div>
				</div>
			)}
			<dialog id={modal} ref={dialog} aria-labelledby={heading} className="home-document-dialog"
				onClose={() => { setExpanded(false); setHovered(false); }}
			>
				<div className="flex items-center justify-between gap-4 border-b border-card-line px-5 py-4">
					<h2 id={heading} className="text-[15px] font-semibold">{label}</h2>
					<form method="dialog"><button className="rounded-lg border border-card-line px-3 py-1.5 text-[12px] font-semibold">Close</button></form>
				</div>
				{expanded && <div className="p-5">
					<DocumentBody kind={kind} membership={membership} label={label} download={download} />
				</div>}
			</dialog>
		</div>
	);
}

function DocumentBody({ kind, membership, label, download }: { kind: "volunteer" | "member"; membership?: string; label: string; download?: string }) {
	const { data, error, isLoading } = useFrappeGetCall<{ message: { html?: string; body?: string } | null }>(
		kind === "volunteer" ? API.myVolunteerCard : API.memberCertificate,
		kind === "volunteer" ? undefined : { name: membership },
		kind === "volunteer" ? "portal:card:volunteer" : `portal:certificate:${membership}`,
	);
	if (isLoading) return <Skeleton className="h-48" />;
	if (error) return <ErrorNote>{errorMessage(error, "Your document could not be loaded. Please try again.")}</ErrorNote>;
	const html = kind === "volunteer" ? data?.message?.html : data?.message?.body;
	if (!html) return <p className="p-4 text-[12px] text-muted">Your document is not available yet.</p>;

	// Isolate the administrator-authored document's CSS and disable scripts,
	// forms and navigation. Names, branding and eligibility all come from the server.
	return <>
		<IssuedDocument html={html} label={label} />
		{download && <a href={download} className="mt-4 inline-block text-[12px] font-semibold text-red underline underline-offset-2">Download PDF</a>}
	</>;
}

/** Fit the issued layout into either preview without squeezing its table columns. */
function IssuedDocument({ html, label }: { html: string; label: string }) {
	const holder = useRef<HTMLDivElement>(null);
	const [width, setWidth] = useState(600);
	useEffect(() => {
		const element = holder.current;
		if (!element || typeof ResizeObserver === "undefined") return;
		const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
		observer.observe(element);
		return () => observer.disconnect();
	}, []);
	const scale = Math.min(width / 600, 1);
	return <div ref={holder} className="home-issued-viewport" style={{ height: 520 * scale }}>
		<iframe title={`${label} preview`} sandbox="" className="home-issued-document"
			style={{ transform: `scale(${scale})` }} srcDoc={html} />
	</div>;
}
