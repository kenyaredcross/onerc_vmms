import { useContext, useMemo, useState } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import type { Block } from "../content/ContentProvider";
import { API, errorMessage } from "../lib/api";
import { Card, Empty, ErrorNote, PageHeading, Pill, Spinner, cx } from "../ui/primitives";

interface Surface {
	key: string;
	label: string;
	is_public: boolean;
	blocks: Block[];
}

interface Catalogue {
	can_edit: boolean;
	surfaces: Surface[];
}

/**
 * The bulk editor for page wording.
 *
 * The pencil on the page itself is the primary way to change a sentence, and it
 * is the better one: you see the change where it lands. This screen exists for
 * the jobs the pencil is bad at — finding every slot that is still empty,
 * rewriting eight footer links in a row, editing a surface you cannot easily
 * navigate to.
 *
 * It deliberately does **not** sit inside a `ContentProvider`. The provider
 * loads the slots a page renders from; this screen loads the catalogue, which
 * is a different question with a different permission (read on the doctype,
 * never guests) and a different endpoint. Sharing the provider would have meant
 * teaching it to enumerate, which is exactly the capability the guest-readable
 * endpoint must not grow.
 */
export default function ContentAdmin() {
	const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: Catalogue }>(
		API.contentCatalogue,
		undefined,
		"admin:content_catalogue",
	);

	const [query, setQuery] = useState("");
	const [onlyEmpty, setOnlyEmpty] = useState(false);

	const catalogue = data?.message;
	const canEdit = Boolean(catalogue?.can_edit);

	const surfaces = useMemo(() => {
		if (!catalogue) return [];

		const needle = query.trim().toLowerCase();

		return catalogue.surfaces
			.map((surface) => ({
				...surface,
				blocks: surface.blocks.filter((block) => {
					if (onlyEmpty && (block.text || block.image)) return false;
					if (!needle) return true;
					return (
						block.key.toLowerCase().includes(needle) ||
						block.label.toLowerCase().includes(needle) ||
						block.text.toLowerCase().includes(needle)
					);
				}),
			}))
			.filter((surface) => surface.blocks.length > 0);
	}, [catalogue, query, onlyEmpty]);

	const total = surfaces.reduce((sum, surface) => sum + surface.blocks.length, 0);

	if (isLoading) return <Spinner label="Loading page content…" />;
	if (error) return <ErrorNote>{errorMessage(error)}</ErrorNote>;

	return (
		<>
			<PageHeading title="Page content" actions={<Pill tone="page">{total} slots</Pill>} />

			<p className="-mt-2 mb-6 max-w-2xl text-[13.5px] text-muted">
				Every heading, paragraph, button and photograph in this product is one of these. You
				can also edit any of them in place, on the page itself, with the pencil.
			</p>

			{!canEdit && (
				<div className="mb-5">
					<ErrorNote>
						You can read this but not change it. A society names its page-content editor
						role in National Society Settings, and only then does the pencil appear.
					</ErrorNote>
				</div>
			)}

			<div className="mb-6 flex flex-wrap items-center gap-3">
				<input
					className="min-w-[240px] flex-1 rounded-xl border border-card-line px-3.5 py-2.5 text-[13px] outline-none focus:border-blue"
					placeholder="Search by wording, label or key"
					value={query}
					onChange={(event) => setQuery(event.target.value)}
					aria-label="Search content"
				/>
				<button
					type="button"
					onClick={() => setOnlyEmpty(!onlyEmpty)}
					aria-pressed={onlyEmpty}
					className={cx(
						"whitespace-nowrap rounded-full px-4 py-2 text-[12px] font-semibold transition",
						onlyEmpty
							? "bg-ink text-white"
							: "border border-card-line bg-white text-slate-strong hover:border-blue",
					)}
				>
					Only empty
				</button>
			</div>

			{total === 0 && <Empty title="Nothing matches that" />}

			<div className="space-y-8">
				{surfaces.map((surface) => (
					<section key={surface.key}>
						<div className="mb-3 flex flex-wrap items-center gap-2.5">
							<h2 className="text-[16px] font-semibold tracking-tight text-ink">
								{surface.label}
							</h2>
							{surface.is_public && <Pill tone="page">Public</Pill>}
							<span className="font-mono text-[10.5px] text-slate-faint">{surface.key}</span>
						</div>

						<div className="space-y-2.5">
							{surface.blocks.map((block) => (
								<BlockRow
									key={block.key}
									block={block}
									canEdit={canEdit}
									onSaved={() => void mutate()}
								/>
							))}
						</div>
					</section>
				))}
			</div>
		</>
	);
}

function BlockRow({
	block,
	canEdit,
	onSaved,
}: {
	block: Block;
	canEdit: boolean;
	onSaved: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [value, setValue] = useState(block.text);
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);
	const [saved, setSaved] = useState(false);

	const dirty = value !== block.text;

	const commit = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.contentUpdate, { content_key: block.key, text_value: value });
			setSaved(true);
			window.setTimeout(() => setSaved(false), 1800);
			onSaved();
		} catch (saveError) {
			setFailure(errorMessage(saveError, "Not saved."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Card className="p-4">
			<div className="flex flex-wrap items-baseline justify-between gap-2">
				<span className="text-[12.5px] font-bold text-ink">{block.label}</span>
				<span className="font-mono text-[10.5px] text-slate-faint">{block.key}</span>
			</div>

			<div className="mt-2.5 flex flex-wrap items-start gap-2.5">
				{block.image && (
					<img
						src={block.image}
						alt=""
						className="h-12 w-20 flex-none rounded-xl border border-card-line object-cover"
					/>
				)}
				<textarea
					className="min-h-[42px] min-w-[220px] flex-1 resize-y rounded-xl border border-card-line px-3 py-2 text-[13px] outline-none focus:border-blue disabled:bg-surface"
					value={value}
					disabled={!canEdit}
					onChange={(event) => setValue(event.target.value)}
					aria-label={block.label}
				/>
				<button
					type="button"
					onClick={commit}
					disabled={!canEdit || !dirty || busy}
					className="flex-none rounded-xl bg-rail px-4 py-2 text-[12px] font-bold text-white transition hover:bg-rail/90 disabled:opacity-40"
				>
					{busy ? "Saving…" : saved ? "Saved" : "Save"}
				</button>
			</div>

			{/* Pictures are changed on the page itself, where you can see what the
			    crop does. Saying so beats an upload control that gives no preview
			    of the thing it is about to change. */}
			{block.image !== null && !block.text && (
				<p className="mt-2 text-[11px] text-slate-faint">
					This slot holds a picture. Change it with the pencil on the page it appears on.
				</p>
			)}

			{failure && <p className="mt-2 text-[11.5px] text-blue">{failure}</p>}
		</Card>
	);
}
