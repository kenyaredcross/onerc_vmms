import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate } from "../lib/format";
import { Icon } from "../ui/icons";
import { Empty, ErrorNote, Pager, Spinner, cx, usePaged } from "../ui/primitives";

/**
 * Stories and news, read from core's `Article` doctype.
 *
 * **The records are core's and so are the endpoints.** `onerc_core.api.article`
 * already serves published articles, their categories and a single article by
 * slug. Wrapping those in a vmmsx endpoint would be this app holding a second
 * answer to what an article is — the thing `CLAUDE.md` forbids about geo and Red
 * Profile, for the same reason. So `lib/api.ts` names core's methods and this
 * screen calls them.
 *
 * **Published is core's decision, not ours.** `get_articles` filters on
 * `status = "Published"` and `docstatus = 1`. This screen invents no second
 * notion of visibility; its two facets narrow, they do not reveal.
 *
 * **Two facets, and they are different questions.** The tabs across the top are
 * `article_type` — what *kind* of thing this is, which is a short list a society
 * configures and the coarsest cut. The pills below are `category` — what it is
 * *about*. Both are `Localisation` records, neither is named in this file, and a
 * society that configures neither gets a page with no facets rather than a page
 * with empty ones.
 *
 * **Visual first, because that is what a story is.** The two newest take a
 * full-width pair with their cover images large; the rest run as a dense grid.
 * Every image is a society's own upload and may be absent, so each slot falls
 * back to a drawn placeholder rather than a broken image or a stock photograph
 * this app invented.
 */

/** The fields `onerc_core.api.article.get_articles` returns that this screen reads. */
interface ArticleCard {
	name: string;
	title: string;
	slug: string;
	subtitle: string | null;
	summary: string | null;
	cover_image: string | null;
	article_type: string | null;
	category: string | null;
	published_on: string | null;
	read_time: number | null;
	is_featured: number;
	view_count: number | null;
	like_count: number | null;
}

interface Vocabulary {
	name: string;
	category_name?: string;
	type_name?: string;
	description: string | null;
}

/** Rows to a page: the pair at the top plus three full rows of the four-column
 *  grid underneath. */
const PAGE = 14;

export default function Stories() {
	const [type, setType] = useState("");
	const [category, setCategory] = useState("");

	const { data, error, isLoading } = useFrappeGetCall<{ message: ArticleCard[] }>(
		API.articles,
		{ article_type: type || undefined, category: category || undefined, limit: 120 },
		// The key carries both facets, so changing one refetches rather than
		// showing the previous answer under the new heading.
		`portal:articles:${type}:${category}`,
	);

	const categories = useFrappeGetCall<{ message: Vocabulary[] }>(
		API.articleCategories,
		undefined,
		"portal:article_categories",
	);

	const rows = data?.message ?? [];

	// The type tabs are derived from what is actually published rather than from
	// the full vocabulary: a tab that can only ever be empty reads as broken, and
	// core exposes no "types in use" endpoint to ask instead. Categories keep
	// their full list, because core does serve that and a society curates it.
	const types = useMemo(() => {
		const seen = new Set<string>();
		for (const row of rows) if (row.article_type) seen.add(row.article_type);
		return [...seen].sort();
	}, [rows]);

	// Recomputed from the unfiltered fetch, so the tabs do not vanish as soon as
	// somebody picks one.
	const [allTypes, setAllTypes] = useState<string[]>([]);
	if (!type && !category && types.length && types.join() !== allTypes.join()) {
		setAllTypes(types);
	}

	const paged = usePaged(rows, PAGE);

	// The pair at the top is a property of the *first* page: page two is a
	// continuation of the grid, not a second front page with its own feature.
	const feature = paged.page === 0;
	const [lead, rest] = feature
		? [paged.slice.slice(0, 2), paged.slice.slice(2)]
		: [[] as ArticleCard[], paged.slice];

	// `usePaged` resets itself when the row count changes, so changing a facet
	// only has to change the facet.
	const changeFacet = (next: () => void) => next();

	return (
		<>
			{/* The banded head. The palette is the society's navy rather than the
			    reference's blue; the layout is what was being borrowed. */}
			<div className="-mx-5 -mt-7 mb-0 overflow-hidden bg-gradient-to-br from-navy via-navy to-signal/70 px-5 pb-14 pt-12 text-white md:-mx-8 md:-mt-9 md:px-8">
				<div className="eyebrow text-white/55">
					<EditableText k="portal.stories.eyebrow" fallback="From the society" />
				</div>
				<h1 className="mt-3 font-display text-[34px] font-extrabold leading-none tracking-tight sm:text-[42px]">
					<EditableText k="portal.stories.heading" fallback="Stories" />
				</h1>
				<EditableText
					k="portal.stories.intro"
					as="p"
					className="relative mt-3 max-w-xl text-[13.5px] leading-relaxed text-white/70"
				/>
			</div>

			{/* The type tabs sit on the band's lower edge, as an underlined rail. */}
			<div className="-mx-5 border-b border-hairline bg-white px-5 md:-mx-8 md:px-8">
				<nav className="flex gap-6 overflow-x-auto" aria-label="Kind of story">
					<Tab label="All" on={type === ""} onClick={() => changeFacet(() => setType(""))} />
					{(allTypes.length ? allTypes : types).map((entry) => (
						<Tab
							key={entry}
							label={entry}
							on={type === entry}
							onClick={() => changeFacet(() => setType(entry))}
						/>
					))}
				</nav>
			</div>

			<div className="-mx-5 mb-8 border-b border-hairline bg-page/50 px-5 py-3.5 md:-mx-8 md:px-8">
				<Topics
					categories={categories.data?.message ?? []}
					value={category}
					onChange={(next) => changeFacet(() => setCategory(next))}
				/>
			</div>

			{isLoading && <Spinner label="Loading stories…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{!isLoading && !error && rows.length === 0 && (
				<Empty title="Nothing published here yet" icon={Icon.book}>
					Stories your society publishes appear here. An administrator writes them on the desk, as
					Article records.
				</Empty>
			)}

			{lead.length > 0 && (
				<div className="grid gap-6 md:grid-cols-2">
					{lead.map((article) => (
						<StoryCard key={article.name} article={article} size="lead" />
					))}
				</div>
			)}

			{rest.length > 0 && (
				<div className="mt-10 grid gap-x-5 gap-y-9 sm:grid-cols-2 lg:grid-cols-4">
					{rest.map((article) => (
						<StoryCard key={article.name} article={article} size="grid" />
					))}
				</div>
			)}

			<Pager
				page={paged.page}
				pageCount={paged.pageCount}
				onPage={paged.onPage}
				total={paged.total}
				noun="stories"
			/>
		</>
	);
}

/* ------------------------------------------------------------------ facets */

function Tab({ label, on, onClick }: { label: string; on: boolean; onClick: () => void }) {
	return (
		<button
			type="button"
			onClick={onClick}
			aria-pressed={on}
			className={cx(
				"relative whitespace-nowrap py-3.5 font-display text-[13px] font-bold transition",
				on ? "text-navy" : "text-slate-faint hover:text-slate-strong",
			)}
		>
			{label}
			{on && <span className="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-signal" />}
		</button>
	);
}

function Topics({
	categories,
	value,
	onChange,
}: {
	categories: Vocabulary[];
	value: string;
	onChange: (next: string) => void;
}) {
	if (categories.length === 0) return null;

	const pill = "whitespace-nowrap rounded-full px-3 py-1 text-[11.5px] font-bold transition";

	return (
		<div className="flex flex-wrap items-center gap-x-2 gap-y-2">
			<span className="mr-1 text-[10px] font-bold uppercase tracking-wider text-slate-faint">
				Topics
			</span>

			<button
				type="button"
				onClick={() => onChange("")}
				aria-pressed={value === ""}
				className={cx(pill, value === "" ? "bg-navy text-white" : "bg-white text-slate-body hover:text-navy")}
			>
				All
			</button>

			{categories.map((row) => {
				const label = row.category_name || row.name;

				return (
					<button
						key={row.name}
						type="button"
						onClick={() => onChange(row.name)}
						aria-pressed={value === row.name}
						title={row.description ?? undefined}
						className={cx(
							pill,
							value === row.name ? "bg-navy text-white" : "bg-white text-slate-body hover:text-navy",
						)}
					>
						{label}
					</button>
				);
			})}
		</div>
	);
}

/* ------------------------------------------------------------------- card */

/**
 * One story.
 *
 * `lead` and `grid` are the same card at two scales rather than two components,
 * because the reference's pair at the top and its dense rows below differ only
 * in how much room the image and the title get. Two components would drift.
 */
function StoryCard({ article, size }: { article: ArticleCard; size: "lead" | "grid" }) {
	const lead = size === "lead";

	return (
		<Link to={`/stories/${article.slug}`} className="group block">
			<div className="relative overflow-hidden rounded-card">
				{/* Both crops are shallower than the reference's. A 16/9 lead on a
				    half-width column was taller than the two paragraphs beside it,
				    which made the pair read as two posters rather than two stories. */}
				<Cover src={article.cover_image} className={lead ? "aspect-[2/1]" : "aspect-[3/2]"} />

				{article.article_type && (
					<span className="absolute left-2.5 top-2.5 rounded-full bg-white/95 px-2.5 py-0.5 text-[9.5px] font-bold text-navy shadow-card backdrop-blur">
						{article.article_type}
					</span>
				)}
			</div>

			<h3
				className={cx(
					"mt-3 font-display font-bold leading-snug tracking-tight text-ink transition group-hover:text-navy",
					lead ? "text-[17px]" : "text-[13.5px]",
				)}
			>
				{article.title}
			</h3>

			{lead && article.subtitle && (
				<p className="mt-1.5 line-clamp-2 text-[12.5px] leading-relaxed text-slate-body [overflow-wrap:anywhere]">
					{article.subtitle}
				</p>
			)}

			<p className="mt-1.5 text-[11px] text-slate-faint">
				{article.published_on ? formatDate(article.published_on) : ""}
				{article.read_time ? ` · ${article.read_time} min read` : ""}
			</p>
		</Link>
	);
}

/**
 * A cover image, or a drawn stand-in for one.
 *
 * Never a stock photograph and never a broken image: `cover_image` is a
 * society's own upload and is genuinely optional, so the absent case is a
 * designed state rather than an accident. Same rule the content blocks follow.
 */
function Cover({ src, className }: { src: string | null; className?: string }) {
	if (!src) {
		return (
			<div
				className={cx(
					"grid w-full place-items-center bg-gradient-to-br from-navy/[0.08] via-page to-signal/[0.08]",
					className,
				)}
				aria-hidden="true"
			>
				<svg viewBox="0 0 24 24" width="28" height="28" fill="none" className="text-slate-faint/60">
					<path
						d="M4 6h16v12H4zM4 15l4.5-4.5 4 4L16 11l4 4"
						stroke="currentColor"
						strokeWidth="1.6"
						strokeLinejoin="round"
					/>
					<circle cx="9" cy="9.5" r="1.3" fill="currentColor" />
				</svg>
			</div>
		);
	}

	return (
		<div className={cx("w-full overflow-hidden bg-page", className)}>
			<img
				src={src}
				alt=""
				loading="lazy"
				className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.04]"
			/>
		</div>
	);
}

/* ------------------------------------------------------------------ detail */

/**
 * One article's own page: banded head, overlapping cover, then the body.
 *
 * The left rail is share links and nothing else — deliberately no like or
 * comment control. Core carries `Article Like` and `Article Comment` and a
 * `toggle_like` endpoint, and adding either here would be this app taking on
 * moderation of a society's newsroom on a screen built for reading.
 */
export function Story() {
	const { slug = "" } = useParams();

	const { data, error, isLoading } = useFrappeGetCall<{
		message:
			| (ArticleCard & { body: string | null; source_name?: string; source_url?: string })
			| null;
	}>(API.article, { slug }, slug ? `portal:article:${slug}` : null);

	const article = data?.message ?? null;

	// Read more: the same category, so the suggestion is about something rather
	// than merely recent. Fetched only once the article is known, because its
	// category is the query.
	const related = useFrappeGetCall<{ message: ArticleCard[] }>(
		API.articles,
		{ category: article?.category ?? undefined, limit: 5 },
		article?.category ? `portal:related:${article.category}` : null,
	);

	const more = (related.data?.message ?? []).filter((row) => row.slug !== slug).slice(0, 4);

	return (
		<>
			<div className="-mx-5 -mt-7 overflow-hidden bg-gradient-to-br from-navy via-navy to-signal/70 px-5 pb-32 pt-8 text-white md:-mx-8 md:-mt-9 md:px-8">
				<Link
					to="/stories"
					className="inline-flex items-center gap-2 text-[12px] font-bold uppercase tracking-wider text-white/70 transition hover:text-white"
				>
					<Icon.back size={15} />
					Back
				</Link>

				{article && (
					<div className="mt-7 min-w-0 max-w-3xl [overflow-wrap:anywhere]">
						{article.article_type && (
							<span className="inline-block rounded-full bg-white/15 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-white/85 backdrop-blur">
								{article.article_type}
							</span>
						)}

						<h1 className="mt-3.5 font-display text-[30px] font-extrabold leading-tight tracking-tight sm:text-[40px]">
							{article.title}
						</h1>

						{article.subtitle && (
							<p className="mt-3 text-[15px] leading-relaxed text-white/75">{article.subtitle}</p>
						)}

						<p className="mt-4 text-[12.5px] text-white/60">
							{article.published_on ? `Published ${formatDate(article.published_on)}` : ""}
							{article.read_time ? ` · ${article.read_time} min read` : ""}
						</p>
					</div>
				)}
			</div>

			{isLoading && (
				<div className="mt-8">
					<Spinner label="Loading…" />
				</div>
			)}

			{error && (
				<div className="mt-8">
					<ErrorNote>{errorMessage(error)}</ErrorNote>
				</div>
			)}

			{!isLoading && !error && !article && (
				<div className="mt-8">
					<Empty title="That story is not here">
						It may have been unpublished, or the link may be wrong.
					</Empty>
				</div>
			)}

			{article && (
				<>
					{/* The cover overlaps the band, which is what the reference does and
					    what stops the head and the body reading as two pages. */}
					<div className="relative z-10 -mt-24 overflow-hidden rounded-panel shadow-hero">
						<Cover src={article.cover_image} className="aspect-[10/3]" />
					</div>

					<div className="mt-10 gap-10 lg:grid lg:grid-cols-[64px_minmax(0,1fr)]">
						<Share title={article.title} />

						{/* `min-w-0` so the article column can be narrower than its
						    content, and `overflow-wrap:anywhere` so an unbroken token
						    somebody pasted breaks mid-word rather than widening the
						    page. `break-words` only breaks *between* words. */}
						<article className="min-w-0 max-w-3xl [overflow-wrap:anywhere]">
							{article.summary && (
								<p className="text-[16.5px] font-medium leading-relaxed text-ink">
									{article.summary}
								</p>
							)}

							{/* `body` is core's Text Editor field, which is HTML by design and
							    written by a society's own administrators on the desk — the
							    same trust boundary Frappe's own web pages apply to it. This
							    is the one place in the portal that renders markup, and it
							    renders core's, never anything a portal user typed:
							    `link_href` and every content block stay plain text for
							    exactly that reason. */}
							{article.body && (
								<div
									className="article-body mt-6 text-[14.5px] leading-[1.8] text-slate-body"
									dangerouslySetInnerHTML={{ __html: article.body }}
								/>
							)}

							{article.category && (
								<div className="mt-10 border-t border-hairline pt-6">
									<p className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">
										Topics
									</p>
									<Link
										to="/stories"
										className="mt-2.5 inline-block rounded-full bg-navy/[0.07] px-3 py-1 text-[11.5px] font-bold text-navy transition hover:bg-navy hover:text-white"
									>
										{article.category}
									</Link>
								</div>
							)}

							{article.source_name && (
								<p className="mt-6 text-[12px] text-slate-faint">
									Source:{" "}
									{article.source_url ? (
										<a
											href={article.source_url}
											className="font-semibold text-navy hover:underline"
											rel="noreferrer noopener"
											target="_blank"
										>
											{article.source_name}
										</a>
									) : (
										article.source_name
									)}
								</p>
							)}
						</article>
					</div>

					{more.length > 0 && (
						<section className="-mx-5 mt-16 bg-page px-5 py-12 md:-mx-8 md:px-8">
							<h2 className="font-display text-[26px] font-extrabold tracking-tight text-ink">
								Read more
							</h2>

							<div className="mt-7 grid gap-x-5 gap-y-8 sm:grid-cols-2 lg:grid-cols-4">
								{more.map((row) => (
									<StoryCard key={row.name} article={row} size="grid" />
								))}
							</div>
						</section>
					)}
				</>
			)}
		</>
	);
}

/**
 * The share rail.
 *
 * Copy-link first, because it is the one that works everywhere and needs no
 * account. The two network links are plain `https` navigations built from the
 * current URL — no SDK, no tracking pixel, nothing loaded from another origin.
 */
function Share({ title }: { title: string }) {
	const [copied, setCopied] = useState(false);
	const url = typeof window === "undefined" ? "" : window.location.href;

	const copy = async () => {
		try {
			await navigator.clipboard.writeText(url);
			setCopied(true);
			window.setTimeout(() => setCopied(false), 2000);
		} catch {
			// A browser that refuses clipboard access is not an error worth a
			// dialogue; the address bar still has the link.
		}
	};

	const button =
		"grid h-9 w-9 place-items-center rounded-full border border-hairline-strong bg-white text-slate-body transition hover:border-navy hover:text-navy";

	return (
		<div className="mb-8 lg:sticky lg:top-24 lg:mb-0 lg:self-start">
			<p className="mb-3 text-[10px] font-bold uppercase tracking-wider text-slate-faint">Share</p>

			<div className="flex gap-2 lg:flex-col">
				<button type="button" onClick={copy} className={button} aria-label="Copy link">
					{copied ? <Icon.check size={15} /> : <Icon.tag size={15} />}
				</button>

				<a
					href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`}
					target="_blank"
					rel="noreferrer noopener"
					className={button}
					aria-label="Share on LinkedIn"
				>
					<span className="font-display text-[11px] font-extrabold">in</span>
				</a>

				<a
					href={`https://wa.me/?text=${encodeURIComponent(`${title} ${url}`)}`}
					target="_blank"
					rel="noreferrer noopener"
					className={button}
					aria-label="Share on WhatsApp"
				>
					<Icon.external size={14} />
				</a>
			</div>

			{copied && <p className="mt-2 text-[10.5px] text-emerald-700">Link copied</p>}
		</div>
	);
}
