/**
 * Where a scanned card lands.
 *
 * **Built for somebody standing in front of the person whose card it is**, on a
 * phone, possibly outdoors, possibly on a bad connection, and almost certainly
 * without an account. So it answers one question in one word before anything
 * else loads: is this card current. Everything under that is the corroboration
 * a person actually uses — the name to compare with the face, the branch to
 * compare with the card, the number to compare with the print.
 *
 * **It shows exactly what `api/cards.py::verify` returns and asks for nothing
 * else.** There is no second call, no "see more", and no link into the portal:
 * the reader has no account and the boundary around what a stranger may know
 * about a volunteer is the whole design of that endpoint. A screen that offered
 * a way to ask for more would be undoing it in the browser.
 *
 * **A token that resolves to nothing says so plainly and says nothing more.**
 * Not "withdrawn", not "expired", not "no such card" — one answer, because
 * distinguishing them would turn this page into somewhere to test guesses.
 *
 * **The code can be typed as well as scanned, and that adds no exposure.** A
 * steward outdoors with a camera that will not focus, or a card whose QR has
 * worn through, still has the code printed on the front. `/verify` with no token
 * asks for it; `/verify/<token>` is what the QR encodes and what the form
 * navigates to, so both arrive at exactly the same read. It is worth being
 * explicit that this opens nothing: the endpoint already answers for any token
 * anybody types into the address bar, the boundary is the token's own
 * unguessability, and a miss says the same single thing however it was reached.
 */
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { BrandLockup } from "../ui/brand";
import { Button, Card, Spinner, cx } from "../ui/primitives";

interface Verified {
	found: boolean;
	kind?: string;
	holder_name?: string;
	record_id?: string;
	status?: string;
	is_current?: boolean;
	geo_path?: string;
	since?: string;
	valid_to?: string;
}

export default function Verify() {
	const { token = "" } = useParams();

	const { data, error, isLoading } = useFrappeGetCall<{ message: Verified }>(
		"vmmsx.api.cards.verify",
		{ token },
		// Not asked at all until there is something to ask about. A `null` key is
		// how this app disables a call it does not want yet; without it, somebody
		// who has typed nothing would be told their card is not recognised.
		token ? `verify:${token}` : null,
	);

	const result = data?.message;

	return (
		<main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-5 py-10">
			<div className="mb-7 flex justify-center">
				<BrandLockup />
			</div>

			{!token && <TokenEntry />}

			{token && isLoading && <Spinner label="Checking this card…" />}

			{/* A failed request is not a failed card. Saying "not valid" because the
			    network dropped would have a steward turn somebody away over a lost
			    packet, so the two are reported as the different things they are. */}
			{error && !isLoading && (
				<Card>
					<p className="text-[14px] font-semibold text-ink">This card could not be checked.</p>
					<p className="mt-1.5 text-[12.5px] leading-relaxed text-slate-body">
						Something went wrong reaching the society. That is not the same as the card being
						invalid. Try again in a moment.
					</p>
				</Card>
			)}

			{result && !result.found && (
				<Card>
					<Verdict current={false} word="Not recognised" />
					<p className="mt-3 text-[12.5px] leading-relaxed text-slate-body">
						This society has no card with that code.
					</p>
				</Card>
			)}

			{result?.found && (
				<Card>
					<Verdict
						current={Boolean(result.is_current)}
						word={result.is_current ? "Current" : "Not current"}
					/>

					<div className="mt-5 border-t border-hairline pt-5">
						<p className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">
							{result.kind}
						</p>
						<p className="mt-1 font-display text-[22px] font-extrabold leading-tight tracking-tight text-ink">
							{result.holder_name}
						</p>

						<dl className="mt-4 space-y-2.5">
							<Line label="Number" value={result.record_id} mono />
							<Line label="Branch" value={result.geo_path} />
							<Line label="Status" value={result.status} />
							<Line label="Since" value={result.since} />
							<Line label="Valid to" value={result.valid_to} />
						</dl>
					</div>
				</Card>
			)}

			{token && (
				<>
					<p className="mt-6 text-center text-[11.5px] leading-relaxed text-slate-faint">
						Checked against the society's own register just now.
					</p>
					{/* A steward on a gate checks one card after another, so the way
					    back to the box is on the answer rather than in the browser's
					    history. A plain link, because it goes to this same page. */}
					<p className="mt-3 text-center">
						<a
							href="/portal/verify"
							className="text-[12px] font-semibold text-navy hover:underline"
						>
							Check another card
						</a>
					</p>
				</>
			)}
		</main>
	);
}

/**
 * The box for a code that could not be scanned.
 *
 * Navigates to `/verify/<token>` rather than reading here, so a checked card has
 * a URL: the same one the QR encodes, shareable and reloadable, and one code
 * path for both ways in.
 *
 * The code is trimmed and nothing else is done to it. Guessing at case or
 * punctuation would be this screen deciding what a token looks like, which is
 * `cards/services/token.py`'s business — and a wrong guess would turn a real
 * card into "not recognised".
 */
function TokenEntry() {
	const navigate = useNavigate();
	const [typed, setTyped] = useState("");

	const code = typed.trim();

	return (
		<Card>
			<h1 className="font-display text-[19px] font-extrabold tracking-tight text-ink">
				Check a card
			</h1>
			<p className="mt-1.5 text-[12.5px] leading-relaxed text-slate-body">
				Scan the code on the card, or type the number printed beneath it.
			</p>

			<form
				className="mt-5"
				onSubmit={(event) => {
					event.preventDefault();

					if (code) {
						navigate(`/verify/${encodeURIComponent(code)}`);
					}
				}}
			>
				<label className="block">
					<span className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-slate-faint">
						Card number
					</span>
					<input
						value={typed}
						onChange={(event) => setTyped(event.target.value)}
						autoCapitalize="off"
						autoCorrect="off"
						spellCheck={false}
						className="w-full rounded-card border border-hairline-strong px-3 py-2.5 font-mono text-[14px]"
					/>
				</label>

				<Button type="submit" className="mt-4 w-full" disabled={!code}>
					Verify
				</Button>
			</form>
		</Card>
	);
}

/** The answer, first and largest, because it is the only thing being asked. */
function Verdict({ current, word }: { current: boolean; word: string }) {
	return (
		<div
			className={cx(
				"flex items-center gap-3 rounded-card px-4 py-3.5",
				current ? "bg-emerald-50" : "bg-surface",
			)}
		>
			<span
				className={cx(
					"flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[17px] font-bold text-white",
					current ? "bg-emerald-600" : "bg-slate-400",
				)}
				aria-hidden
			>
				{current ? "✓" : "!"}
			</span>
			<span className="font-display text-[17px] font-extrabold tracking-tight text-ink">{word}</span>
		</div>
	);
}

/** One corroborating fact, drawn only when there is one. */
function Line({ label, value, mono }: { label: string; value?: string; mono?: boolean }) {
	if (!value) return null;

	return (
		<div className="flex items-baseline justify-between gap-4">
			<dt className="shrink-0 text-[10px] font-bold uppercase tracking-wider text-slate-faint">
				{label}
			</dt>
			<dd className={cx("text-right text-[13px] text-ink", mono && "font-mono")}>{value}</dd>
		</div>
	);
}
