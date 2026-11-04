import { useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { FrappeContext, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage } from "../lib/api";
import { formatMoney } from "../lib/format";
import type { PaymentProgress } from "../portal/types";
import { Field, TextInput } from "./form";
import { Icon } from "./icons";
import { Button, ErrorNote, cx } from "./primitives";

/** How often to ask whether the payment has arrived, and for how long. */
export const POLL_EVERY_MS = 5000;
export const POLL_FOR = 36;

const WAITING = ["Initiated", "Pending"];
const ENDED = ["Failed", "Cancelled"];

/**
 * A phone number as people read it: `0727 118 702`.
 *
 * The gateway hands numbers back in international form (`254727118702`), which
 * nobody recognises as their own at a glance. Anything that is not a Kenyan
 * mobile number in one of its usual spellings is shown as it came.
 */
export function spacedPhone(value: string | null | undefined): string {
	const raw = (value ?? "").replace(/[\s-]/g, "");
	const local = raw.replace(/^\+?254(?=[17]\d{8}$)/, "0");

	return /^0[17]\d{8}$/.test(local) ? `${local.slice(0, 4)} ${local.slice(4, 7)} ${local.slice(7)}` : (value ?? "");
}

/** The gateway's own mark, on white so a coloured logo reads on any card. */
export function PaymentLogo({ src, label, className }: { src: string; label: string; className?: string }) {
	return (
		<span className={cx("inline-flex items-center rounded-lg bg-white px-2.5 py-1.5 ring-1 ring-card-line", className)}>
			<img src={src} alt={label} className="h-6 w-auto" />
		</span>
	);
}

/**
 * A membership fee paid on the phone, from the prompt to the receipt.
 *
 * Asks the server every few seconds while the prompt is open. The server asks
 * the gateway, and once the payment has gone through it records it and sends
 * the membership to its branch, so the next answer already says so. A prompt
 * that was cancelled or timed out can be sent again, to the same phone or
 * another.
 *
 * Every state is the same card — the gateway's mark and the amount across the
 * top, what to do next below — so the person watching it sees one thing change
 * rather than one box replaced by another.
 */
export function PhonePayment({
	membership,
	phone,
	onSettled,
}: {
	membership: string;
	/** What the gateway said when the prompt went out. Kept for callers; the card says it in its own steps. */
	message?: string;
	/** The number the prompt went to, offered again if it has to be resent. */
	phone?: string | null;
	onSettled?: (progress: PaymentProgress) => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [progress, setProgress] = useState<PaymentProgress | null>(null);
	const [asked, setAsked] = useState(0);
	const [sentTo, setSentTo] = useState(phone ?? "");
	const [retryPhone, setRetryPhone] = useState(phone ?? "");
	const [sending, setSending] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);
	const settledOnce = useRef(false);

	const check = useCallback(async () => {
		try {
			const answer = await call.post<{ message: PaymentProgress }>(API.membershipPayment, { name: membership });
			setProgress(answer.message);
		} catch {
			// Asked again on the next tick. A missed check is not news for the payer.
		} finally {
			setAsked((count) => count + 1);
		}
	}, [call, membership]);

	useEffect(() => {
		void check();
	}, [check]);

	const waiting = !progress || (progress.status !== null && WAITING.includes(progress.status));
	const stillAsking = waiting && asked < POLL_FOR;

	useEffect(() => {
		if (!stillAsking || asked === 0) return;
		const timer = window.setTimeout(() => void check(), POLL_EVERY_MS);
		return () => window.clearTimeout(timer);
	}, [stillAsking, asked, check]);

	useEffect(() => {
		if (progress?.settled && !settledOnce.current) {
			settledOnce.current = true;
			onSettled?.(progress);
		}
	}, [progress, onSettled]);

	const sendAgain = async () => {
		setSending(true);
		setFailure(null);
		try {
			const answer = await call.post<{ message: PaymentProgress }>(API.payMembershipAgain, {
				name: membership,
				payer_phone: retryPhone.trim() || undefined,
			});
			setProgress(answer.message);
			if (retryPhone.trim()) setSentTo(retryPhone.trim());
			setAsked(1);
		} catch (sendError) {
			setFailure(errorMessage(sendError, "The payment request was not sent. Try again."));
		} finally {
			setSending(false);
		}
	};

	const amount =
		progress?.amount !== null && progress?.amount !== undefined
			? formatMoney(progress.amount, progress.currency)
			: null;

	const sendForm = (label: string) => (
		<div className="mt-4 space-y-3">
			<Field
				label="Phone number to pay from"
				hint={retryPhone.trim() ? undefined : "Leave this empty to use the number you gave before."}
				htmlFor={`pay-again-${membership}`}
			>
				<TextInput
					id={`pay-again-${membership}`}
					type="tel"
					inputMode="tel"
					placeholder="07XX XXX XXX"
					value={retryPhone}
					onChange={setRetryPhone}
				/>
			</Field>
			{failure && <ErrorNote>{failure}</ErrorNote>}
			<Button onClick={() => void sendAgain()} busy={sending}>
				<Icon.send size={14} />
				{label}
			</Button>
		</div>
	);

	const frame = (tone: Tone, children: ReactNode) => (
		<Frame tone={tone} logo={progress?.logo ?? null} amount={amount}>
			{children}
		</Frame>
	);

	if (progress?.settled) {
		return frame(
			"done",
			<>
				<Headline icon={<Icon.check size={18} />} tone="done" title="Payment received">
					{amount ? `${amount} paid` : "Paid"}
					{progress.paid_from ? ` from ${spacedPhone(progress.paid_from)}` : ""}.
				</Headline>
				{progress.receipt && (
					<p className="mt-4 flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-[12.5px] text-slate-body ring-1 ring-emerald-200">
						<Icon.receipt size={14} />
						Receipt <span className="font-mono font-semibold text-ink">{progress.receipt}</span>
					</p>
				)}
				<p className="mt-3 text-[12.5px] leading-relaxed text-slate-body">
					{progress.membership_status === "Active"
						? "Your membership is active."
						: "Your membership has gone to your branch for approval."}
				</p>
			</>,
		);
	}

	if (progress && progress.status !== null && ENDED.includes(progress.status)) {
		return frame(
			"problem",
			<>
				<Headline icon={<Icon.cross size={18} />} tone="problem" title="The payment did not go through">
					{progress.failure || "Nothing was taken from your account."}
				</Headline>
				{progress.can_retry && sendForm("Send the payment request again")}
			</>,
		);
	}

	// No request has gone to a phone yet: the prompt could not be sent when the
	// registration was filed. Waiting would wait for something nobody asked for.
	if (progress && progress.status === null && progress.can_retry) {
		return frame(
			"waiting",
			<>
				<Headline icon={<Icon.phone size={18} />} tone="waiting" title="Pay the membership fee on your phone">
					We will send a payment request to this number. Enter your PIN on your phone to pay.
				</Headline>
				{sendForm("Send the payment request")}
			</>,
		);
	}

	if (!stillAsking && progress) {
		return frame(
			"waiting",
			<>
				<Headline icon={<Icon.clock size={18} />} tone="waiting" title="We have not received your payment yet">
					If you entered your PIN, it can take a minute to arrive.
				</Headline>
				<div className="mt-4">
					<Button
						variant="quiet"
						onClick={() => {
							setAsked(0);
							void check();
						}}
					>
						Check again
					</Button>
				</div>
			</>,
		);
	}

	return frame(
		"waiting",
		<>
			<div className="flex items-start gap-3.5">
				<span className="relative grid h-11 w-11 flex-none place-items-center" aria-hidden="true">
					<span className="absolute inset-0 animate-ping rounded-full bg-emerald-400/25 motion-reduce:animate-none" />
					<span className="relative grid h-11 w-11 place-items-center rounded-full bg-emerald-600 text-white">
						<Icon.phone size={19} />
					</span>
				</span>
				<div className="min-w-0">
					<p className="font-display text-[16px] font-bold tracking-[-0.01em] text-ink">Check your phone</p>
					<p className="mt-1 text-[12.5px] leading-relaxed text-slate-body">
						{sentTo ? (
							<>
								A payment request has gone to <strong className="font-semibold text-ink">{spacedPhone(sentTo)}</strong>.
							</>
						) : (
							"A payment request has gone to your phone."
						)}
					</p>
				</div>
			</div>

			<ol className="mt-4 space-y-2 text-[12.5px] text-slate-body">
				{[
					"Unlock your phone and open the payment request.",
					amount ? `Check the amount is ${amount}.` : "Check the amount.",
					"Enter your PIN and confirm.",
				].map((step, index) => (
					<li key={step} className="flex items-center gap-2.5">
						<span className="grid h-5 w-5 flex-none place-items-center rounded-full bg-white text-[10.5px] font-bold text-ink ring-1 ring-card-line">
							{index + 1}
						</span>
						<span>{step}</span>
					</li>
				))}
			</ol>

			<p
				className="mt-4 flex items-center gap-2 border-t border-card-line pt-3 text-[12px] text-slate-faint"
				role="status"
				aria-live="polite"
			>
				<span
					aria-hidden="true"
					className="h-3.5 w-3.5 flex-none animate-spin rounded-full border-2 border-current border-t-transparent motion-reduce:animate-none"
				/>
				Waiting for your payment…
			</p>
		</>,
	);
}

type Tone = "waiting" | "done" | "problem";

const FRAME: Record<Tone, string> = {
	waiting: "border-card-line bg-surface",
	done: "border-emerald-200 bg-emerald-50",
	problem: "border-danger-line bg-danger-soft",
};

function Frame({
	tone,
	logo,
	amount,
	children,
}: {
	tone: Tone;
	logo: string | null;
	amount: string | null;
	children: ReactNode;
}) {
	return (
		<div className={cx("overflow-hidden rounded-2xl border", FRAME[tone])}>
			{(logo || amount) && (
				<div className="flex items-center justify-between gap-3 border-b border-black/5 bg-white/70 px-4 py-3">
					{logo ? <img src={logo} alt="" className="h-7 w-auto" /> : <span />}
					{amount && (
						<span className="text-right">
							<span className="block text-[10px] font-bold uppercase tracking-[0.1em] text-slate-faint">
								Membership fee
							</span>
							<span className="font-display text-[19px] font-extrabold tracking-[-0.02em] text-ink tabular">
								{amount}
							</span>
						</span>
					)}
				</div>
			)}
			<div className="px-4 py-4">{children}</div>
		</div>
	);
}

function Headline({
	icon,
	tone,
	title,
	children,
}: {
	icon: ReactNode;
	tone: Tone;
	title: string;
	children: ReactNode;
}) {
	return (
		<div className="flex items-start gap-3.5">
			<span
				className={cx(
					"grid h-10 w-10 flex-none place-items-center rounded-full",
					tone === "done" ? "bg-emerald-600 text-white" : tone === "problem" ? "bg-white text-danger ring-1 ring-danger-line" : "bg-white text-ink ring-1 ring-card-line",
				)}
				aria-hidden="true"
			>
				{icon}
			</span>
			<div className="min-w-0">
				<p className="font-display text-[16px] font-bold tracking-[-0.01em] text-ink">{title}</p>
				<p className="mt-1 text-[12.5px] leading-relaxed text-slate-body">{children}</p>
			</div>
		</div>
	);
}
