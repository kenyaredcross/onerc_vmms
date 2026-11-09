import { useFrappeGetCall } from "frappe-react-sdk";
import type { ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import { API, errorMessage } from "../lib/api";
import { formatDate, formatMoney } from "../lib/format";
import { BrandLockup } from "../ui/brand";
import { Button, ErrorNote, Spinner } from "../ui/primitives";
import type { MembershipReceipt } from "./types";

/**
 * A membership fee's payment receipt, laid out to print on one page.
 *
 * Standalone, outside the portal chrome, so what prints is the receipt and
 * nothing else. The member opens it from their membership; staff open it from
 * the membership in the console. `api/member.py::membership_receipt` decides
 * who may read which, so the page itself asks nothing of its reader.
 *
 * Printing is the browser's: "Print or save as PDF" opens its dialog, where
 * saving as a PDF is one of the destinations.
 */
export default function Receipt() {
	const { name = "" } = useParams();
	const read = useFrappeGetCall<{ message: MembershipReceipt }>(
		API.membershipReceipt,
		{ name },
		name ? `receipt:${name}` : null,
	);
	const receipt = read.data?.message;

	return (
		<div className="min-h-[var(--screen,100vh)] bg-surface px-4 py-8 print:bg-white print:p-0">
			<div className="mx-auto flex max-w-[720px] items-center justify-between gap-3 pb-4 print:hidden">
				<Link to="/membership" className="text-[13px] font-semibold text-blue hover:text-blue-hover">
					← Back to memberships
				</Link>
				{receipt && <Button onClick={() => window.print()}>Print or save as PDF</Button>}
			</div>

			{read.isLoading && <Spinner page label="Loading your receipt…" />}
			{read.error && (
				<div className="mx-auto max-w-[720px]">
					<ErrorNote>{errorMessage(read.error, "This receipt could not be opened.")}</ErrorNote>
				</div>
			)}
			{receipt && <ReceiptSheet receipt={receipt} />}
		</div>
	);
}

export function ReceiptSheet({ receipt }: { receipt: MembershipReceipt }) {
	const paid = formatMoney(receipt.amount, receipt.currency, true);
	const { member, membership } = receipt;
	const codeLabel = receipt.by_phone && receipt.method ? `${receipt.method} code` : "Payment code";

	return (
		<article
			aria-label={`Receipt ${receipt.receipt_number}`}
			className="relative mx-auto max-w-[720px] overflow-hidden rounded-2xl border border-card-line bg-white shadow-[0_18px_50px_rgba(10,18,27,0.08)] print:max-w-none print:rounded-none print:border-0 print:shadow-none"
		>
			{/* The brand's band across the top: the one splash of colour, and it prints. */}
			<div aria-hidden="true" className="h-1.5 bg-action [print-color-adjust:exact]" />

			<header className="flex flex-wrap items-start justify-between gap-6 px-8 pb-6 pt-7">
				<div className="flex min-w-0 items-center gap-3">
					{receipt.logo ? (
						<img src={receipt.logo} alt="" className="h-14 w-auto max-w-[160px] object-contain" />
					) : (
						<BrandLockup />
					)}
					{receipt.logo && (
						<p className="max-w-[220px] text-[15px] font-semibold leading-snug text-ink">{receipt.society}</p>
					)}
				</div>
				<div className="text-right">
					<p className="text-[10.5px] font-bold uppercase tracking-[0.14em] text-slate-faint">Payment receipt</p>
					<p className="mt-1 font-mono text-[17px] font-semibold text-ink">{receipt.receipt_number}</p>
					<p className="mt-1.5 text-[12.5px] text-muted">{formatDate(receipt.paid_on)}</p>
				</div>
			</header>

			<section className="mx-8 flex flex-wrap items-end justify-between gap-4 rounded-xl bg-surface px-6 py-5 [print-color-adjust:exact]">
				<div>
					<p className="text-[11px] font-bold uppercase tracking-wider text-slate-faint">Amount received</p>
					<p className="mt-1 text-[30px] font-semibold leading-none tracking-tight text-ink">{paid}</p>
				</div>
				<span className="inline-flex items-center gap-1.5 rounded-full border border-success-line bg-white px-3 py-1 text-[12px] font-bold text-success">
					<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
						<path d="m5 12.5 4.5 4.5L19 7.5" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
					</svg>
					Paid
				</span>
			</section>

			<div className="px-8 py-7">
				<Block title="Member">
					<div className="grid gap-x-10 gap-y-1.5 sm:grid-cols-2">
						<Line label="Name" value={member.name} strong />
						<Line label="Membership" value={membership.type} strong />
						<Line label="Member number" value={member.member_number} mono />
						<Line label="Branch" value={membership.branch} />
						<Line label="Membership ID" value={membership.name} mono />
						<Line
							label="Valid"
							value={
								membership.valid_from
									? `${formatDate(membership.valid_from)} – ${membership.valid_to ? formatDate(membership.valid_to) : "no end date"}`
									: "From the payment date"
							}
						/>
					</div>
				</Block>
			</div>

			<div className="mx-8 border-t border-dashed border-card-line" />

			<div className="px-8 py-6">
				<Block title="Payment">
					<div className="grid gap-x-10 gap-y-1.5 sm:grid-cols-2">
						<Line label="Method" value={receipt.method} />
						<Line label="Phone number" value={receipt.phone} mono />
						{receipt.gateway_receipt ? (
							<Line label={codeLabel} value={receipt.gateway_receipt} mono highlight />
						) : (
							receipt.by_phone && <Line label={codeLabel} value="Not received yet" muted />
						)}
						<Line label="Transaction" value={receipt.transaction} mono />
						{receipt.sales_invoice && <Line label="Invoice" value={receipt.sales_invoice} mono />}
						{receipt.payment_entry && <Line label="Payment entry" value={receipt.payment_entry} mono />}
					</div>
				</Block>
			</div>

			<footer className="border-t border-card-line bg-surface/60 px-8 py-4 text-[11.5px] leading-relaxed text-muted [print-color-adjust:exact]">
				Thank you for your membership of {receipt.society || "the society"}. Keep this receipt as proof of payment.
			</footer>
		</article>
	);
}

function Block({ title, children }: { title: string; children: ReactNode }) {
	return (
		<section>
			<h2 className="mb-2.5 text-[10.5px] font-bold uppercase tracking-[0.12em] text-slate-faint">{title}</h2>
			<dl>{children}</dl>
		</section>
	);
}

function Line({
	label,
	value,
	mono = false,
	strong = false,
	highlight = false,
	muted = false,
}: {
	label: string;
	value: string | null | undefined;
	mono?: boolean;
	strong?: boolean;
	highlight?: boolean;
	muted?: boolean;
}) {
	if (!value) return null;
	return (
		<div className="flex items-baseline justify-between gap-4 text-[13px]">
			<dt className="flex-none text-muted">{label}</dt>
			<dd
				className={[
					"min-w-0 text-right text-ink",
					mono ? "font-mono text-[12.5px]" : "",
					strong ? "font-semibold" : "",
					highlight ? "rounded bg-blue-soft px-1.5 py-0.5 font-semibold text-blue-press [print-color-adjust:exact]" : "",
					muted ? "italic text-muted" : "",
				].join(" ")}
			>
				{value}
			</dd>
		</div>
	);
}
