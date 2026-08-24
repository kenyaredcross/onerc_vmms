import {
	createElement,
	useCallback,
	useEffect,
	useId,
	useRef,
	useState,
	type ElementType,
	type ReactNode,
} from "react";
import { useFrappeFileUpload } from "frappe-react-sdk";

import { errorMessage } from "../lib/api";
import { useContent, type Block, type BlockPatch } from "./ContentProvider";

/** Which controls the dialog offers for a given slot. */
type EditableField = "text" | "href" | "image" | "alt" | "credit";

function cx(...parts: Array<string | false | null | undefined>): string {
	return parts.filter(Boolean).join(" ");
}

/* ------------------------------------------------------------------ pencil */

/**
 * The pencil, and the two things that make it safe to put anywhere.
 *
 * **It is a `span`, not a `button`.** Half the editable slots in this app are
 * the label inside a link or a nav item, and a `button` inside an `a` is
 * invalid HTML: `a` excludes interactive content. A span carrying
 * `role="button"` and a tab stop is valid phrasing content, reads the same to a
 * screen reader, and can sit inside anything.
 *
 * **It stops the event dead.** Without this, clicking the pencil on the hero's
 * call to action would follow the link it is attached to and navigate away from
 * the page somebody was trying to edit.
 */
function Pencil({ label, onClick }: { label: string; onClick: () => void }) {
	const fire = (event: { preventDefault: () => void; stopPropagation: () => void }) => {
		event.preventDefault();
		event.stopPropagation();
		onClick();
	};

	return (
		<span
			role="button"
			tabIndex={0}
			onClick={fire}
			onKeyDown={(event) => {
				if (event.key === "Enter" || event.key === " ") fire(event);
			}}
			title={`Edit: ${label}`}
			aria-label={`Edit: ${label}`}
			className="absolute -right-2 -top-2 z-20 grid h-6 w-6 cursor-pointer place-items-center rounded-full bg-signal text-white shadow-pop transition hover:bg-signal-dark"
		>
			<svg viewBox="0 0 24 24" width="12" height="12" fill="none" aria-hidden="true">
				<path
					d="M4 20h4L19 9l-4-4L4 16v4Z"
					stroke="currentColor"
					strokeWidth="2.2"
					strokeLinejoin="round"
				/>
			</svg>
		</span>
	);
}

/* ------------------------------------------------------------------ dialog */

/**
 * The editor itself: one dialog for every kind of slot.
 *
 * A dialog rather than a popover anchored to the slot, because half the
 * editable things on the landing page sit inside a band with `overflow: hidden`
 * and an anchored panel would be clipped by the photograph it is editing.
 */
function BlockEditor({
	block,
	fields,
	onClose,
}: {
	block: Block;
	fields: EditableField[];
	onClose: () => void;
}) {
	const { save } = useContent();
	const { upload, progress, loading: uploading } = useFrappeFileUpload();
	const titleId = useId();

	const [text, setText] = useState(block.text);
	const [href, setHref] = useState(block.href);
	const [image, setImage] = useState(block.image ?? "");
	const [alt, setAlt] = useState(block.image_alt);
	const [credit, setCredit] = useState(block.image_credit);
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const firstFieldRef = useRef<HTMLTextAreaElement | HTMLInputElement | null>(null);

	useEffect(() => {
		firstFieldRef.current?.focus();
	}, []);

	useEffect(() => {
		const onKey = (event: KeyboardEvent) => {
			if (event.key === "Escape") onClose();
		};
		document.addEventListener("keydown", onKey);
		return () => document.removeEventListener("keydown", onKey);
	}, [onClose]);

	const pickFile = useCallback(
		async (file: File) => {
			setFailure(null);
			try {
				const uploaded = await upload(file, {
					doctype: "VMMS Content Block",
					docname: block.key,
					fieldname: "image",
					// Public, and it has to be: this picture is served to
					// signed-out visitors on the landing page. A private file
					// would render as a broken image for everybody but the
					// person who uploaded it.
					isPrivate: false,
				});
				setImage(uploaded.file_url);
			} catch (uploadError) {
				setFailure(errorMessage(uploadError, "That file could not be uploaded."));
			}
		},
		[block.key, upload],
	);

	const submit = async () => {
		setBusy(true);
		setFailure(null);

		const patch: BlockPatch = {};
		if (fields.includes("text")) patch.text = text;
		if (fields.includes("href")) patch.href = href;
		if (fields.includes("image")) patch.image = image;
		if (fields.includes("alt")) patch.image_alt = alt;
		if (fields.includes("credit")) patch.image_credit = credit;

		try {
			await save(block.key, patch);
			onClose();
		} catch (saveError) {
			setFailure(errorMessage(saveError, "That change could not be saved."));
			setBusy(false);
		}
	};

	const field = "w-full rounded-card border border-hairline-strong px-3 py-2 text-[13px] outline-none focus:border-navy";
	const labelCls = "mb-1 block text-[11px] font-bold uppercase tracking-wider text-slate-faint";

	return (
		<div
			className="fixed inset-0 z-50 grid place-items-center bg-navy/40 p-4"
			role="presentation"
			onMouseDown={(event) => {
				if (event.target === event.currentTarget) onClose();
			}}
		>
			<div
				role="dialog"
				aria-modal="true"
				aria-labelledby={titleId}
				className="max-h-[88vh] w-full max-w-lg overflow-y-auto rounded-panel bg-white p-6 shadow-pop"
			>
				<div className="mb-1 flex items-start justify-between gap-4">
					<h2 id={titleId} className="font-display text-lg font-extrabold text-ink">
						{block.label || "Edit content"}
					</h2>
					<button
						type="button"
						onClick={onClose}
						aria-label="Close"
						className="-mr-1 -mt-1 grid h-7 w-7 place-items-center rounded-full text-slate-faint hover:bg-surface hover:text-ink"
					>
						×
					</button>
				</div>
				<p className="mb-5 font-mono text-[10px] text-slate-faint">{block.key}</p>

				{failure && (
					<p className="mb-4 rounded-card border border-signal/30 bg-signal/5 px-3 py-2 text-[12px] text-signal-dark">
						{failure}
					</p>
				)}

				<div className="space-y-4">
					{fields.includes("text") && (
						<div>
							<label className={labelCls} htmlFor={`${titleId}-text`}>
								Wording
							</label>
							<textarea
								id={`${titleId}-text`}
								ref={firstFieldRef as React.RefObject<HTMLTextAreaElement>}
								className={cx(field, "min-h-[92px] resize-y leading-relaxed")}
								value={text}
								onChange={(event) => setText(event.target.value)}
							/>
							<p className="mt-1 text-[11px] text-slate-faint">
								Plain text. Line breaks are kept; markup is shown as characters rather
								than rendered.
							</p>
						</div>
					)}

					{fields.includes("image") && (
						<div>
							<span className={labelCls}>Picture</span>
							<div className="flex items-center gap-3">
								<div className="h-16 w-24 flex-none overflow-hidden rounded-card border border-hairline bg-surface">
									{image ? (
										<img src={image} alt="" className="h-full w-full object-cover" />
									) : (
										<div className="grid h-full w-full place-items-center text-[10px] text-slate-faint">
											none
										</div>
									)}
								</div>
								<div className="min-w-0 flex-1">
									<input
										type="file"
										accept="image/*"
										className="block w-full text-[12px] file:mr-3 file:rounded-card file:border-0 file:bg-navy file:px-3 file:py-1.5 file:text-[12px] file:font-bold file:text-white"
										onChange={(event) => {
											const file = event.target.files?.[0];
											if (file) void pickFile(file);
										}}
									/>
									{uploading && (
										<p className="mt-1 text-[11px] text-slate-body">Uploading… {progress}%</p>
									)}
									{image && !uploading && (
										<button
											type="button"
											onClick={() => setImage("")}
											className="mt-1 text-[11px] font-semibold text-signal hover:underline"
										>
											Remove picture
										</button>
									)}
								</div>
							</div>
						</div>
					)}

					{fields.includes("alt") && (
						<div>
							<label className={labelCls} htmlFor={`${titleId}-alt`}>
								Alt text
							</label>
							<input
								id={`${titleId}-alt`}
								className={field}
								value={alt}
								onChange={(event) => setAlt(event.target.value)}
								placeholder="What the picture shows"
							/>
						</div>
					)}

					{fields.includes("credit") && (
						<div>
							<label className={labelCls} htmlFor={`${titleId}-credit`}>
								Photo credit
							</label>
							<input
								id={`${titleId}-credit`}
								className={field}
								value={credit}
								onChange={(event) => setCredit(event.target.value)}
								placeholder="Photographer · licence"
							/>
						</div>
					)}

					{fields.includes("href") && (
						<div>
							<label className={labelCls} htmlFor={`${titleId}-href`}>
								Link
							</label>
							<input
								id={`${titleId}-href`}
								className={field}
								value={href}
								onChange={(event) => setHref(event.target.value)}
								placeholder="/portal/join"
							/>
							<p className="mt-1 text-[11px] text-slate-faint">
								A path beginning with /, or an http, https, mailto or tel address.
								Anything else is refused when you save.
							</p>
						</div>
					)}
				</div>

				<div className="mt-6 flex justify-end gap-2">
					<button
						type="button"
						onClick={onClose}
						className="rounded-card px-4 py-2 text-[13px] font-bold text-slate-strong hover:bg-surface"
					>
						Cancel
					</button>
					<button
						type="button"
						onClick={submit}
						disabled={busy || uploading}
						className="rounded-card bg-navy px-5 py-2 text-[13px] font-bold text-white transition hover:bg-navy/90 disabled:opacity-50"
					>
						{busy ? "Saving…" : "Save"}
					</button>
				</div>
			</div>
		</div>
	);
}

/* ------------------------------------------------------- the slot wrappers */

/**
 * Shared plumbing: resolve the block, and decide whether to draw a pencil.
 *
 * A key nobody seeded renders `fallback` and no pencil. That is the right
 * failure: a component asking for a slot that does not exist is a bug in a
 * release, and it should show the default text rather than a hole in the page
 * or an editor for something that cannot be saved.
 */
function useSlot(key: string) {
	const { get, editing } = useContent();
	const [open, setOpen] = useState(false);
	const block = get(key);

	return { block, editing: editing && Boolean(block), open, setOpen };
}

interface TextProps {
	/** The content key. Short name because it appears on nearly every line. */
	k: string;
	as?: ElementType;
	className?: string;
	fallback?: string;
	/** Rendered instead of nothing when the slot is empty and not being edited. */
	placeholder?: ReactNode;
	/** Offer the link field too, for slots that are a label plus a destination. */
	withHref?: boolean;
	/**
	 * Lay the slot's own words out as something other than a run of text, while
	 * keeping the pencil and the single editable field behind them.
	 *
	 * The events teaser is the case this exists for: the design draws a date as a
	 * small red month over a large day, which is two typographic treatments of
	 * one thing an administrator typed as "AUG 20". Splitting it into two content
	 * blocks would make somebody fill in two fields to write one date, and the
	 * second would be the one they forgot.
	 */
	render?: (value: string) => ReactNode;
}

/** A heading, paragraph, button label or caption that an administrator owns. */
export function EditableText({
	k,
	as = "span",
	className,
	fallback = "",
	placeholder = null,
	withHref = false,
	render,
}: TextProps) {
	const { block, editing, open, setOpen } = useSlot(k);
	const value = block?.text || fallback;

	if (!value && !editing) return <>{placeholder}</>;

	const fields: EditableField[] = withHref ? ["text", "href"] : ["text"];
	const shown = value || (editing ? "Empty" : "");

	return (
		<>
			{createElement(
				as,
				{
					className: cx(className, editing && "relative editable-on"),
					// Line breaks an editor typed are line breaks on the page.
					// A custom layout brings its own, so the rule is dropped there.
					style: render ? undefined : { whiteSpace: "pre-line" },
				},
				render ? render(shown) : shown,
				editing && block ? <Pencil label={block.label} onClick={() => setOpen(true)} /> : null,
			)}
			{open && block && (
				<BlockEditor block={block} fields={fields} onClose={() => setOpen(false)} />
			)}
		</>
	);
}

/**
 * A link whose words *and* destination are both configuration.
 *
 * An empty destination renders a span rather than an anchor: a link to nowhere
 * is worse than plain text, because it looks clickable.
 */
export function EditableLink({
	k,
	className,
	fallback = "",
	chevron = false,
}: {
	k: string;
	className?: string;
	fallback?: string;
	chevron?: boolean;
}) {
	const { block, editing, open, setOpen } = useSlot(k);
	const value = block?.text || fallback;
	const href = block?.href;

	if (!value && !editing) return null;

	const inner = (
		<>
			{value || (editing ? "Empty" : "")}
			{editing && block ? <Pencil label={block.label} onClick={() => setOpen(true)} /> : null}
		</>
	);

	const cls = cx(className, chevron && "chev", editing && "relative editable-on");

	// While editing, the label stops being a link. Somebody rewording the footer
	// should not be navigated off the page by a stray click on the text they are
	// about to change, and the destination is editable in the dialog anyway.
	return (
		<>
			{href && !editing ? (
				<a href={href} className={cls}>
					{inner}
				</a>
			) : (
				<span className={cls}>{inner}</span>
			)}
			{open && block && (
				<BlockEditor block={block} fields={["text", "href"]} onClose={() => setOpen(false)} />
			)}
		</>
	);
}

/**
 * A photograph, its alt text and its credit, as one editable unit.
 *
 * An empty slot draws a branded placeholder rather than a broken image, so a
 * society that has uploaded nothing still has a page that looks finished. The
 * pencil sits on the placeholder, which is how somebody discovers they can put
 * a picture there.
 */
export function EditableImage({
	k,
	className,
	imgClassName,
	objectPosition,
	showCredit = false,
	creditSide = "right",
	eager = false,
	fill = false,
}: {
	k: string;
	className?: string;
	imgClassName?: string;
	objectPosition?: string;
	showCredit?: boolean;
	/**
	 * Which bottom corner the credit sits in. It goes opposite the words: the
	 * design puts it left on the band whose text is on the right, so a caption
	 * never sits under the paragraph it has nothing to do with.
	 */
	creditSide?: "left" | "right";
	/**
	 * Load without waiting for layout. True for the hero only: a lazy hero is a
	 * navy rectangle for the first moment of every visit, which is the one image
	 * on the page that is certainly in view.
	 */
	eager?: boolean;
	/**
	 * Stretch to the nearest positioned ancestor instead of sitting in the flow.
	 * What the full-bleed hero and the photo bands want.
	 *
	 * **A prop rather than `className="absolute inset-0"` from the caller**, and
	 * that distinction cost this page its hero. The wrapper needs a positioning
	 * context for the credit and the pencil, so it used to append `relative`
	 * unconditionally — which produced `class="absolute inset-0 relative"`, and
	 * Tailwind emits `.relative` after `.absolute`, so the *later rule won* and
	 * the photograph quietly became an in-flow block. It filled the band, looked
	 * entirely correct, and pushed the headline and the buttons below it, where
	 * the band's own `overflow-hidden` clipped them away. The class order in the
	 * string says nothing; only the order in the stylesheet does.
	 */
	fill?: boolean;
}) {
	const { block, editing, open, setOpen } = useSlot(k);
	const src = block?.image;

	return (
		<div
			className={cx(
				// Absolute is itself a positioning context, so the credit and the
				// pencil still have something to hang off. Only one of these two
				// classes is ever emitted.
				fill ? "absolute inset-0" : "relative",
				className,
				editing && "editable-on",
			)}
		>
			{src ? (
				<img
					src={src}
					alt={block?.image_alt ?? ""}
					loading={eager ? "eager" : "lazy"}
					fetchPriority={eager ? "high" : undefined}
					className={cx("h-full w-full object-cover", imgClassName)}
					style={objectPosition ? { objectPosition } : undefined}
				/>
			) : (
				<div
					aria-hidden="true"
					className="h-full w-full bg-gradient-to-br from-navy via-navy to-signal/70"
				/>
			)}

			{showCredit && block?.image_credit && (
				<span
					className={cx(
						"absolute bottom-2.5 rounded-[4px] bg-navy/50 px-2 py-[3px] text-[9.5px] leading-none text-white/75",
						creditSide === "left" ? "left-3" : "right-3",
					)}
				>
					{block.image_credit}
				</span>
			)}

			{editing && block && (
				<div className="absolute right-4 top-4">
					<Pencil label={block.label} onClick={() => setOpen(true)} />
				</div>
			)}

			{open && block && (
				<BlockEditor
					block={block}
					fields={["image", "alt", "credit"]}
					onClose={() => setOpen(false)}
				/>
			)}
		</div>
	);
}

/**
 * A predicate for sections that hide themselves when their slots are empty.
 *
 * Returns a function rather than taking a key, so a caller can test four
 * statistics in a `.filter()` without calling a hook inside a loop. The
 * statistics row and the events teaser both use it: a society that fills in two
 * of four statistics gets a row of two rather than two numbers and two gaps.
 *
 * In edit mode everything reports as present, because an empty slot that is
 * hidden could never be filled in.
 */
export function useHasContent(): (key: string) => boolean {
	const { get, editing } = useContent();

	return useCallback(
		(key: string) => {
			const block = get(key);
			return editing || Boolean(block?.text || block?.image);
		},
		[get, editing],
	);
}
