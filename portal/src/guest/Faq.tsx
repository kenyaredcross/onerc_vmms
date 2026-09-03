import { useState } from "react";
import { Link } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { ContentProvider } from "../content/ContentProvider";
import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { BrandLockup } from "../ui/brand";
import { Icon } from "../ui/icons";
import { Empty, ErrorNote, PageHeading, Spinner, cx } from "../ui/primitives";

/** One published answer, as `api/faq.py::published` shapes it. */
interface FaqEntry {
	name: string;
	question: string;
	/** Sanitised on the server. See `api/faq.py::_answer`. */
	answer: string;
}

interface FaqCategory {
	name: string;
	label: string;
	description: string;
	questions: FaqEntry[];
}

/**
 * The answers a society keeps having to give, at a public address.
 *
 * **The content is core's, not this app's.** `FAQ` and `FAQ Category` are
 * onerc_core's doctypes; a society writes an answer once and it appears here,
 * in the desk, and in any sibling product on the site. Nothing in this file
 * holds a question, an answer or a category name — see `api/faq.py` for why the
 * endpoint exists at all when core already has one.
 *
 * **Public for the same reason the locations directory is.** Somebody reading
 * "what does volunteering actually involve" has not signed in and quite often is
 * reading in order to decide whether to. The same page is drawn inside the
 * portal at `/help` — one body, two chromes, so the two cannot drift apart.
 *
 * **Disclosures, not a wall.** Twenty questions rendered open is a page nobody
 * scans. `<details>` is the browser's own control: it is keyboard-operable, it
 * is searchable with the browser's own find on modern engines, and it needs no
 * state container.
 */
export default function Faq() {
	return (
		<ContentProvider surface="chrome,faq">
			<div className="min-h-screen bg-canvas">
				<header className="sticky top-0 z-30 border-b border-card-line bg-white/95 backdrop-blur">
					<div className="mx-auto flex max-w-shell items-center justify-between gap-4 px-5 py-3">
						<Link to="/">
							<BrandLockup />
						</Link>
					</div>
				</header>

				<main className="mx-auto max-w-shell px-5 py-8">
					<FaqBody />
				</main>
			</div>
		</ContentProvider>
	);
}

/**
 * The questions themselves, without any chrome.
 *
 * Exported because the portal draws the same thing inside its own shell — the
 * split `Locations`/`Directory` already makes, for the same reason.
 */
export function FaqBody({ heading = true }: { heading?: boolean }) {
	const [search, setSearch] = useState("");

	// Searched on the server, because core's reader already matches on the
	// question *and* the answer — a filter in the browser would only find what
	// is written in a heading. Keyed on the term so each search is cached.
	const { data, error, isLoading } = useFrappeGetCall<{
		message: { categories: FaqCategory[]; count: number };
	}>(API.faq, search ? { search } : undefined, `faq:${search}`);

	const categories = data?.message?.categories ?? [];

	return (
		<>
			{heading && (
				<PageHeading
					eyebrow={<EditableText k="faq.eyebrow" fallback="Help" />}
					title={<EditableText k="faq.heading" fallback="Questions we are asked" />}
				/>
			)}

			<div className="mb-6 flex max-w-md items-center gap-2 rounded-xl border border-card-line bg-white px-3.5 py-2.5">
				<span className="flex-none text-slate-faint">
					<Icon.search size={16} />
				</span>
				<input
					type="search"
					value={search}
					onChange={(event) => setSearch(event.target.value)}
					placeholder="Search the answers"
					aria-label="Search the answers"
					className="min-w-0 flex-1 bg-transparent text-[13.5px] text-ink outline-none placeholder:text-slate-faint"
				/>
			</div>

			{isLoading && <Spinner label="Loading answers…" />}
			{error && <ErrorNote>{errorMessage(error, "The answers could not be loaded.")}</ErrorNote>}

			{!isLoading && !error && categories.length === 0 && (
				<Empty title={search ? "Nothing matched that" : "No answers published yet"}>
					{search
						? "Try a different search term or contact your branch."
						: "When the society publishes its answers, they appear here."}
				</Empty>
			)}

			<div className="space-y-8">
				{categories.map((category) => (
					<section key={category.name || "uncategorised"}>
						{category.label && (
							<h2 className="text-[15px] font-semibold text-ink">{category.label}</h2>
						)}
						{category.description && (
							<p className="mt-1 text-[13px] leading-relaxed text-muted">
								{category.description}
							</p>
						)}

						<div
							className={cx(
								"overflow-hidden rounded-xl border border-card-line bg-white",
								(category.label || category.description) && "mt-3",
							)}
						>
							{category.questions.map((entry, index) => (
								<details
									key={entry.name}
									className={cx("group px-4", index > 0 && "border-t border-card-line")}
								>
									<summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-3.5 text-[13.5px] font-semibold text-ink marker:hidden">
										{entry.question}
										<span className="flex-none text-slate-faint transition-transform group-open:rotate-180">
											<Icon.chevron size={15} />
										</span>
									</summary>

									{/* Sanitised on the server — see `api/faq.py::_answer` — and
									    rendered as markup because a society writes its answers in
									    a rich text editor and a paragraph break is part of the
									    answer. */}
									<div
										className="prose-answer pb-4 text-[13px] leading-relaxed text-muted"
										dangerouslySetInnerHTML={{ __html: entry.answer }}
									/>
								</details>
							))}
						</div>
					</section>
				))}
			</div>
		</>
	);
}
