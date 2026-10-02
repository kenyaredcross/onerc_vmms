import { useContext, useState } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";
import { useSearchParams } from "react-router-dom";

import { errorMessage } from "../lib/api";
import { formatDate } from "../lib/format";
import { Field } from "../ui/form";
import { Button, Card, ErrorNote, Pill, SectionTitle, Spinner } from "../ui/primitives";
import { Drawer } from "../portal/ui/overlays";

const ROOT = "vmmsx.api.service_certificate";
export const CERTIFICATE_API = {
	options: `${ROOT}.request_options`, mine: `${ROOT}.my_requests`, submit: `${ROOT}.submit_request`,
	reviews: `${ROOT}.review_requests`, detail: `${ROOT}.get_request`, decide: `${ROOT}.decide`,
	generate: `${ROOT}.generate`, download: `${ROOT}.download`,
};
type Choice = { kind: "Volunteer" | "Member"; record: string; branch: string; joined_on: string };
type Options = { choices: Choice[]; applicant_name: string; today: string; custom_fields: { key: string; label: string; required: boolean }[] };
type Request = {
	name: string; applicant_name: string; applicant_kind: string; branch: string; request_date: string;
	service_from: string; service_to: string; position: string; service_summary: string; review_note: string;
	status: string; generation_status: string; can_review: boolean; can_generate: boolean; can_download: boolean;
	decisions: { decision: string; reason: string; decided_on: string }[];
};
type History = { requests: Request[]; has_more: boolean };
type Detail = Request & {
	service_history: { name: string; activity_date: string; hours: number; deployment: string | null; notes: string }[];
	service_hours: number; certificate_html: string; additional_answers: { label: string; value: string }[];
};
const downloadUrl = (name: string) => `/api/method/${CERTIFICATE_API.download}?name=${encodeURIComponent(name)}`;

/** An occasional action, deliberately contained within the person's record. */
export function ServiceCertificatePanel() {
	const [open, setOpen] = useState(false);
	const [history, setHistory] = useState(false);
	const [selected, setSelected] = useState<string | null>(null);
	const [offset, setOffset] = useState(0);
	const options = useFrappeGetCall<{ message: Options }>(CERTIFICATE_API.options, undefined, "certificate:options");
	const list = useFrappeGetCall<{ message: History }>(CERTIFICATE_API.mine, { offset }, `certificate:mine:${offset}`);
	const rows = list.data?.message?.requests ?? [];
	const latest = rows[0];
	const choices = options.data?.message?.choices ?? [];
	if (!choices.length && !rows.length && !options.error) return null;
	const pending = rows.some((r) => r.status === "Pending");
	return <>
		<Card>
			<div className="flex flex-wrap items-start justify-between gap-3">
				<div><SectionTitle>Certificate of Service</SectionTitle><p className="mt-1 text-[13px] text-muted">Request an official record of your service.</p></div>
				{latest?.can_download && <a className="text-[13px] font-semibold text-blue hover:underline" href={downloadUrl(latest.name)}>Download certificate</a>}
				{choices.length > 0 && !pending && <button type="button" onClick={() => setOpen(true)} className="text-[13px] font-semibold text-blue hover:underline">Request certificate</button>}
			</div>
			{options.error && <ErrorNote>{errorMessage(options.error)}</ErrorNote>}
			{list.error && <ErrorNote>{errorMessage(list.error)}</ErrorNote>}
			{latest && <div className="mt-3 flex flex-wrap items-center gap-3 text-[12px]">
				<Pill>{latest.status === "Pending" ? "Pending review" : latest.status}</Pill>
				<button type="button" className="underline" onClick={() => setSelected(latest.name)}>{latest.status === "Rejected" ? "View reason" : "View request"}</button>
				<button type="button" className="text-muted underline" onClick={() => setHistory(!history)}>Request history</button>
			</div>}
			{history && <div className="mt-4"><RequestRows rows={rows} onView={setSelected} /><Pages offset={offset} more={Boolean(list.data?.message?.has_more)} setOffset={setOffset} /></div>}
		</Card>
		{options.data?.message && <RequestForm open={open} options={options.data.message} onClose={() => setOpen(false)} onSubmitted={(name) => { setOpen(false); setOffset(0); void list.mutate(); setSelected(name); }} />}
		<RequestDetail name={selected} onClose={() => setSelected(null)} onChanged={() => void list.mutate()} />
	</>;
}

function RequestForm({ open, options, onClose, onSubmitted }: { open: boolean; options: Options; onClose: () => void; onSubmitted: (name: string) => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [choiceIndex, setChoiceIndex] = useState(0);
	const [from, setFrom] = useState("");
	const [to, setTo] = useState(options.today);
	const [position, setPosition] = useState("");
	const [summary, setSummary] = useState("");
	const [answers, setAnswers] = useState<Record<string, string>>({});
	const [busy, setBusy] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const choice = options.choices[choiceIndex];
	const submit = async () => {
		if (!choice) return;
		setBusy(true); setError(null);
		try {
			const result = await call.post(CERTIFICATE_API.submit, { kind: choice.kind, record: choice.record, service_from: from || choice.joined_on,
				service_to: to, position, service_summary: summary, custom_values: answers });
			onSubmitted((result.message as Request).name);
		} catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
	};
	return <Drawer open={open} onClose={() => { if (!busy) onClose(); }} title="Request a Certificate of Service"
		footer={<><Button variant="navy" onClick={onClose} disabled={busy}>Cancel</Button><Button onClick={() => void submit()} disabled={busy || !choice || !(from || choice.joined_on) || !to}>{busy ? "Submitting…" : "Submit request"}</Button></>}>
		<div className="space-y-5">
			<p className="text-[13px] text-muted">Your branch will review your service before issuing the certificate.</p>
			<Field label="Name" htmlFor="certificate-name"><input id="certificate-name" className="w-full rounded-lg border border-card-line px-3 py-2 text-[13px]" value={options.applicant_name} readOnly /></Field>
			<Field label="Registration and branch" htmlFor="certificate-registration"><select id="certificate-registration" className="w-full rounded-lg border border-card-line px-3 py-2 text-[13px]" value={String(choiceIndex)} onChange={(e) => { setChoiceIndex(Number(e.target.value)); setFrom(""); }}>
				{options.choices.map((c, i) => <option key={`${c.kind}:${c.record}`} value={i}>{c.kind} · {c.record} · {c.branch}</option>)}
			</select></Field>
			<Field label="Request date" htmlFor="certificate-date"><input id="certificate-date" className="w-full rounded-lg border border-card-line px-3 py-2 text-[13px]" value={formatDate(options.today)} readOnly /></Field>
			<div className="grid grid-cols-2 gap-4"><Field label="Service from" htmlFor="certificate-from"><input id="certificate-from" className="w-full rounded-lg border border-card-line px-3 py-2 text-[13px]" type="date" value={from || choice?.joined_on || ""} max={to} onChange={(e) => setFrom(e.target.value)} /></Field>
				<Field label="Service to" htmlFor="certificate-to"><input id="certificate-to" className="w-full rounded-lg border border-card-line px-3 py-2 text-[13px]" type="date" value={to} max={options.today} min={from || choice?.joined_on} onChange={(e) => setTo(e.target.value)} /></Field></div>
			<Field label="Position" htmlFor="certificate-position"><input id="certificate-position" className="w-full rounded-lg border border-card-line px-3 py-2 text-[13px]" value={position} maxLength={140} onChange={(e) => setPosition(e.target.value)} placeholder="Your role during this service" /></Field>
			<Field label="Service summary / supporting information" htmlFor="certificate-summary"><textarea id="certificate-summary" className="w-full rounded-lg border border-card-line p-3 text-[13px]" rows={4} maxLength={1000} value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="Describe your service and any records the coordinator can verify." /></Field>
			{options.custom_fields.map((f) => <Field key={f.key} htmlFor={`certificate-${f.key}`} label={`${f.label}${f.required ? " *" : ""}`}><input id={`certificate-${f.key}`} className="w-full rounded-lg border border-card-line px-3 py-2 text-[13px]" value={answers[f.key] ?? ""} maxLength={160} onChange={(e) => setAnswers({ ...answers, [f.key]: e.target.value })} /></Field>)}
			{error && <ErrorNote>{error}</ErrorNote>}
		</div>
	</Drawer>;
}

export function ServiceCertificateReviews({ volunteer, member }: { volunteer?: string; member?: string }) {
	const [params] = useSearchParams();
	const [selected, setSelected] = useState<string | null>(params.get("request"));
	const [status, setStatus] = useState("");
	const [offset, setOffset] = useState(0);
	const list = useFrappeGetCall<{ message: History }>(CERTIFICATE_API.reviews, { volunteer, member, status, offset }, `certificate:reviews:${volunteer}:${member}:${status}:${offset}`);
	return <Card className="mb-5">
		<div className="mb-4 flex flex-wrap items-center justify-between gap-3"><SectionTitle>Service certificate requests</SectionTitle>
			<div className="flex items-center gap-3"><label className="text-[12px]">Status <select className="ml-2 rounded border border-card-line p-2" value={status} onChange={(e) => { setStatus(e.target.value); setOffset(0); }}>
				<option value="">All</option><option>Pending</option><option>Approved</option><option>Rejected</option>
			</select></label><button type="button" className="text-[12px] underline" onClick={() => void list.mutate()}>Refresh</button></div>
		</div>
		{list.isLoading && <Spinner label="Loading certificate requests…" />}
		{list.error && <ErrorNote>{errorMessage(list.error)}</ErrorNote>}
		{!list.isLoading && !list.error && <RequestRows rows={list.data?.message?.requests ?? []} onView={setSelected} staff />}
		<Pages offset={offset} more={Boolean(list.data?.message?.has_more)} setOffset={setOffset} />
		<RequestDetail name={selected} onClose={() => setSelected(null)} onChanged={() => void list.mutate()} />
	</Card>;
}

function RequestRows({ rows, onView, staff = false }: { rows: Request[]; onView: (name: string) => void; staff?: boolean }) {
	if (!rows.length) return <p className="text-[13px] text-muted">No certificate requests.</p>;
	return <div className="overflow-x-auto"><table className="w-full text-left text-[12px]">
		<thead><tr className="border-b border-card-line text-muted">{[...(staff ? ["Applicant", "Branch"] : []), "Request date", "Service period", "Status", "Action", "Certificate"].map((h) => <th key={h} className="px-2 py-3 font-semibold">{h}</th>)}</tr></thead>
		<tbody>{rows.map((r) => <tr key={r.name} className="border-b border-card-line">
			{staff && <><td className="p-2">{r.applicant_name}<small className="block text-muted">{r.applicant_kind}</small></td><td className="p-2">{r.branch}</td></>}
			<td className="p-2">{formatDate(r.request_date)}</td><td className="p-2">{formatDate(r.service_from)} – {formatDate(r.service_to)}</td><td className="p-2">{r.status}</td>
			<td className="p-2"><button className="text-blue underline" type="button" onClick={() => onView(r.name)}>{r.can_review ? "View / Review" : "View"}</button></td>
			<td className="p-2">{r.can_download ? <a href={downloadUrl(r.name)} className="text-blue underline">Download</a> : r.can_generate ? <button type="button" className="text-blue underline" onClick={() => onView(r.name)}>Generate</button> : r.status === "Approved" ? "Preparing" : "—"}</td>
		</tr>)}</tbody>
	</table></div>;
}

function Pages({ offset, more, setOffset }: { offset: number; more: boolean; setOffset: (value: number) => void }) {
	if (!offset && !more) return null;
	return <div className="mt-3 flex justify-end gap-4 text-[12px]"><button type="button" disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 20))}>Previous</button><button type="button" disabled={!more} onClick={() => setOffset(offset + 20)}>Next</button></div>;
}

function RequestDetail({ name, onClose, onChanged }: { name: string | null; onClose: () => void; onChanged: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const detail = useFrappeGetCall<{ message: Detail }>(CERTIFICATE_API.detail, { name }, name ? `certificate:${name}` : null);
	const [note, setNote] = useState("");
	const [reason, setReason] = useState("");
	const [busy, setBusy] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [preview, setPreview] = useState(false);
	const doc = detail.data?.message;
	const act = async (decision?: string) => {
		setBusy(true); setError(null);
		try {
			await call.post(decision ? CERTIFICATE_API.decide : CERTIFICATE_API.generate, { name, ...(decision ? { decision, reason, review_note: note } : {}) });
			await detail.mutate(); onChanged(); setNote(""); setReason("");
		} catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
	};
	return <Drawer open={Boolean(name)} onClose={() => { if (!busy) { onClose(); setError(null); setNote(""); setReason(""); setPreview(false); } }} title="Certificate of Service" eyebrow={name}
		footer={doc && <>
			{doc.can_download && <a className="rounded-lg bg-blue px-4 py-2 text-[13px] font-semibold text-white" href={downloadUrl(doc.name)}>Download certificate</a>}
			{doc.can_generate && <Button disabled={busy} onClick={() => void act()}>{busy ? "Generating…" : "Generate certificate"}</Button>}
			{doc.can_review && <><Button variant="navy" disabled={busy || !reason.trim()} onClick={() => void act("Rejected")}>Reject</Button><Button disabled={busy || !note.trim()} onClick={() => void act("Approved")}>{busy ? "Saving…" : "Approve"}</Button></>}
		</>}>
		{detail.isLoading && <Spinner label="Loading request…" />}
		{detail.error && <ErrorNote>{errorMessage(detail.error)}</ErrorNote>}
		{doc && <div className="space-y-5 text-[13px]">
			<div><Pill>{doc.status}</Pill><h3 className="mt-3 font-semibold">{doc.applicant_name}</h3><p className="text-muted">{doc.applicant_kind} · {doc.branch}</p><p className="mt-2">{formatDate(doc.service_from)} – {formatDate(doc.service_to)}</p><p>{doc.position}</p></div>
			{doc.service_summary && <div><SectionTitle>Supporting information</SectionTitle><p className="mt-2 whitespace-pre-wrap">{doc.service_summary}</p></div>}
			{doc.additional_answers.map((r, i) => <div key={i}><strong>{r.label}</strong><p>{r.value || "—"}</p></div>)}
			<div><SectionTitle>Recorded service</SectionTitle><p className="mt-2 text-muted">{doc.service_hours} hours recorded in this branch during the requested period. Deployment hours are recorded on the date the service ended.</p>
				{doc.service_history.length ? <ul className="mt-3 divide-y divide-card-line">{doc.service_history.map((log) => <li key={log.name} className="py-2"><strong>{formatDate(log.activity_date)} · {log.hours} hours</strong><p>{log.deployment || "General service"}</p><p className="text-muted">{log.notes}</p></li>)}</ul> : <p className="mt-3">No service hours are recorded for this period. The reviewer must verify supporting information before approval.</p>}
			</div>
			{doc.review_note && <div><SectionTitle>Service verification</SectionTitle><p className="mt-2 whitespace-pre-wrap">{doc.review_note}</p></div>}
			{doc.decisions.map((d, i) => <div key={i} className="rounded-lg bg-surface p-3"><strong>{d.decision} · {formatDate(d.decided_on)}</strong>{d.reason && <p className="mt-1 whitespace-pre-wrap">{d.reason}</p>}</div>)}
			{doc.status === "Approved" && !doc.can_download && <p role="status">{doc.generation_status === "Failed" ? "Certificate generation needs to be retried by your reviewing office." : "Your certificate is being prepared."}<button className="ml-2 underline" type="button" onClick={() => { void detail.mutate(); onChanged(); }}>Refresh</button></p>}
			<button type="button" className="text-blue underline" onClick={() => setPreview(!preview)}>{preview ? "Hide preview" : doc.status === "Approved" ? "View certificate" : "Preview certificate layout"}</button>
			{preview && <div>{doc.status !== "Approved" && <p className="mb-2 font-semibold text-muted">Preview only — this certificate has not been issued.</p>}<iframe title="Certificate preview" sandbox="" srcDoc={doc.certificate_html} className="h-[420px] w-full rounded border border-card-line" /></div>}
			{doc.can_review && <><Field label="Service verification notes" htmlFor="certificate-review"><textarea id="certificate-review" className="w-full rounded-lg border border-card-line p-3" rows={3} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Explain which records or evidence you checked. Required for approval." /></Field>
				<Field label="Rejection reason" htmlFor="certificate-reason"><textarea id="certificate-reason" className="w-full rounded-lg border border-card-line p-3" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Required if rejecting; the applicant will see this." /></Field></>}
		</div>}
		{error && <div className="mt-4"><ErrorNote>{error}</ErrorNote></div>}
	</Drawer>;
}

export default function ServiceCertificateQueue() {
	return <><h1 className="mb-5 font-display text-2xl font-bold text-ink">Service certificates</h1><ServiceCertificateReviews /></>;
}
