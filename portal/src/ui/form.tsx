import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from "react";
import { useFrappeFileUpload } from "frappe-react-sdk";

import { errorMessage } from "../lib/api";
import { cx } from "./primitives";

/**
 * The controls a registration form is built out of.
 *
 * **These exist because the desk gets them for free and a single-page app does
 * not.** A Frappe Web Form renders a Link field, a Table MultiSelect and a
 * conditional section from the doctype itself; a browser bundle has to draw
 * them. So each control here is the SPA's answer to one desk control, and it
 * takes its options as data rather than knowing what any of them mean: a
 * `MultiCombo` cannot tell a skill from a motivation, and a `Combo` cannot
 * tell a country from anything else.
 *
 * **One multi-select, whatever the length of the list.** `MultiCombo` is it.
 * This file used to carry a second — a grid of description-bearing cards for
 * short vocabularies — and picking between them by row count meant a society
 * with six skills and a society with sixty got visibly different questions on
 * the same step. The descriptions survived the merge: `MultiCombo` renders each
 * option's under its label, and every pick echoes through `TokenTray`.
 *
 * Nothing in this file names a society's configuration. Every list arrives as a
 * prop from `application_options` / `identity_options`.
 */

/**
 * Every control in the app, one declaration.
 *
 * **Fully rounded, and it is the single change that does the most work.** A
 * form of square-cornered boxes reads as a database table somebody put labels
 * on; the same fields as capsules read as questions. It is also what makes a
 * text field and a button obviously the same family, which matters on a wizard
 * where the two alternate down the page.
 *
 * `MULTILINE` is the exception, and it has to be: a capsule three lines tall is
 * a stadium with text in it, and the first character sits under the curve.
 */
// One control, everywhere somebody types.
//
// **It was a pill.** `rounded-full` was the previous system's most
// characteristic move and it is not this one's: a fully rounded single-line
// field beside a 12px card and an 8px button reads as a control borrowed from
// another product, and the concept's own registration sheet draws a rounded
// *rectangle* with a search glyph rather than a lozenge. The radius, the border
// colour and the focus halo are now identical to `admin/ui/kit.tsx`'s, so a
// coordinator writing a job opening and a member of the public filling in the
// registration wizard are operating the same field.
const CONTROL =
	"w-full rounded-lg border border-rail-line bg-white px-3 py-2 text-[13px] text-ink transition placeholder:text-slate-faint focus:border-blue focus:ring-[3px] focus:ring-blue-soft disabled:cursor-not-allowed disabled:bg-surface disabled:text-muted";

const MULTILINE =
	"w-full rounded-lg border border-rail-line bg-white px-3 py-2.5 text-[13px] leading-relaxed text-ink transition placeholder:text-slate-faint focus:border-blue focus:ring-[3px] focus:ring-blue-soft disabled:cursor-not-allowed disabled:bg-surface disabled:text-muted";

/* ------------------------------------------------------------------ layout */

export function Field({
	label,
	hint,
	required,
	htmlFor,
	className,
	children,
}: {
	label: ReactNode;
	hint?: ReactNode;
	required?: boolean;
	htmlFor?: string;
	/** For a field that spans its grid — `sm:col-span-2` on a two-column step. */
	className?: string;
	children: ReactNode;
}) {
	return (
		<div className={className}>
			{/* Sentence case at reading size, not a tracked-out micro-caption.
			    A 10px uppercase label is a caption for a figure; this is the
			    question somebody is being asked, and it should be as easy to read
			    as their answer. */}
			<label
				htmlFor={htmlFor}
				className="mb-1.5 flex items-center gap-1 text-[12px] font-semibold text-slate-strong"
			>
				{label}
				{/* Red, not blue. Blue means "act on this" everywhere in this
				    product, and a required marker is not an action; red asterisk is
				    also the one convention every form on the web already shares.
				    `label &&` because a marker with nothing to mark is an orphan
				    asterisk on a line of its own. */}
				{required && label && (
					<span className="text-danger" aria-hidden="true">
						*
					</span>
				)}
			</label>
			{children}
			{/* `muted`, not `slate-faint`: 11.5px at #9AA0A8 is about 2.5:1 on
			    white, which fails AA for the one line on a form that explains what
			    an answer is for. */}
			{hint && <p className="mt-1.5 text-[11.5px] leading-relaxed text-muted">{hint}</p>}
		</div>
	);
}

/** A titled block inside a step, mirroring a Section Break and its description. */
export function FieldSet({
	title,
	description,
	children,
}: {
	title: ReactNode;
	description?: ReactNode;
	children: ReactNode;
}) {
	return (
		<section>
			<h3 className="text-[16px] font-semibold tracking-tight text-ink">{title}</h3>
			{description && (
				<p className="mt-1.5 max-w-2xl text-[13px] leading-relaxed text-muted">
					{description}
				</p>
			)}
			<div className="mt-5">{children}</div>
		</section>
	);
}

/* ------------------------------------------------------------------ inputs */

export function TextInput({
	id,
	value,
	onChange,
	disabled,
	placeholder,
	type = "text",
	inputMode,
	min,
	max,
	step,
}: {
	id?: string;
	value: string;
	onChange: (value: string) => void;
	disabled?: boolean;
	placeholder?: string;
	/**
	 * The control's type, which is how a field's own kind reaches the browser.
	 * `email` and `number` are here because the record has fields of those
	 * kinds: a guardian's address is an `Email` and a society's numeric question
	 * is an `Int`, and typing them as text meant a phone keyboard nobody got and
	 * a validation nobody ran until the save refused it.
	 */
	type?: "text" | "tel" | "date" | "email" | "number";
	inputMode?: "text" | "tel" | "numeric";
	min?: string | number;
	max?: string;
	step?: string | number;
}) {
	return (
		<input
			id={id}
			type={type}
			inputMode={inputMode}
			min={min}
			max={max}
			step={step}
			className={CONTROL}
			value={value}
			disabled={disabled}
			placeholder={placeholder}
			onChange={(event) => onChange(event.target.value)}
		/>
	);
}

export function TextArea({
	id,
	value,
	onChange,
	placeholder,
	rows = 4,
}: {
	id?: string;
	value: string;
	onChange: (value: string) => void;
	placeholder?: string;
	rows?: number;
}) {
	return (
		<textarea
			id={id}
			rows={rows}
			className={cx(MULTILINE, "resize-y leading-relaxed")}
			value={value}
			placeholder={placeholder}
			onChange={(event) => onChange(event.target.value)}
		/>
	);
}

/** A short list of plain string options — the SPA's answer to a small Link field. */
export function SelectInput({
	id,
	value,
	onChange,
	options,
	placeholder = "Select…",
	disabled,
}: {
	id?: string;
	value: string;
	onChange: (value: string) => void;
	options: string[];
	placeholder?: string;
	disabled?: boolean;
}) {
	return (
		<div className="relative">
			<select
				id={id}
				className={cx(CONTROL, "appearance-none pr-9")}
				value={value}
				disabled={disabled}
				onChange={(event) => onChange(event.target.value)}
			>
				<option value="">{placeholder}</option>
				{options.map((option) => (
					<option key={option} value={option}>
						{option}
					</option>
				))}
			</select>
			<Chevron />
		</div>
	);
}

/** The same, over vocabulary rows whose stored key differs from their label. */
export function VocabularySelect({
	id,
	value,
	onChange,
	options,
	placeholder = "Select…",
}: {
	id?: string;
	value: string;
	onChange: (value: string) => void;
	options: Array<{ key: string; label: string }>;
	placeholder?: string;
}) {
	return (
		<div className="relative">
			<select
				id={id}
				className={cx(CONTROL, "appearance-none pr-9")}
				value={value}
				onChange={(event) => onChange(event.target.value)}
			>
				<option value="">{placeholder}</option>
				{options.map((option) => (
					<option key={option.key} value={option.key}>
						{option.label}
					</option>
				))}
			</select>
			<Chevron />
		</div>
	);
}

function Chevron() {
	return (
		<svg
			viewBox="0 0 24 24"
			width="15"
			height="15"
			fill="none"
			aria-hidden="true"
			className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-faint"
		>
			<path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
		</svg>
	);
}

/* --------------------------------------------------------------- combo box */

/**
 * A type-to-filter single select, for a list too long to scroll.
 *
 * **The value can only ever come from the list.** Typing filters; it never
 * sets. That matters because the field behind this is a Link, and a browser
 * that let somebody submit a country the doctype does not have would be
 * building a rejection the server has to explain later.
 */
export function Combo({
	id,
	value,
	onChange,
	options,
	placeholder = "Start typing…",
}: {
	id?: string;
	value: string;
	onChange: (value: string) => void;
	options: string[];
	placeholder?: string;
}) {
	const listId = useId();
	const [open, setOpen] = useState(false);
	const [query, setQuery] = useState("");
	const [active, setActive] = useState(0);
	const wrap = useRef<HTMLDivElement>(null);

	const matches = useMemo(() => {
		const needle = query.trim().toLowerCase();
		const pool = needle ? options.filter((o) => o.toLowerCase().includes(needle)) : options;
		return pool.slice(0, 60);
	}, [options, query]);

	// Clicking anywhere else closes the list and throws away the half-typed
	// filter, so re-opening starts from the whole list rather than from whatever
	// was abandoned last time.
	useEffect(() => {
		if (!open) return;

		const away = (event: MouseEvent) => {
			if (wrap.current && !wrap.current.contains(event.target as Node)) {
				setOpen(false);
				setQuery("");
			}
		};

		document.addEventListener("mousedown", away);
		return () => document.removeEventListener("mousedown", away);
	}, [open]);

	const choose = (option: string) => {
		onChange(option);
		setOpen(false);
		setQuery("");
	};

	return (
		<div className="relative" ref={wrap}>
			<input
				id={id}
				role="combobox"
				aria-expanded={open}
				aria-controls={listId}
				aria-autocomplete="list"
				className={cx(CONTROL, "pr-9")}
				value={open ? query : value}
				placeholder={value || placeholder}
				onFocus={() => setOpen(true)}
				onChange={(event) => {
					setQuery(event.target.value);
					setActive(0);
					setOpen(true);
				}}
				onKeyDown={(event) => {
					if (event.key === "ArrowDown") {
						event.preventDefault();
						setOpen(true);
						setActive((index) => Math.min(index + 1, matches.length - 1));
					} else if (event.key === "ArrowUp") {
						event.preventDefault();
						setActive((index) => Math.max(index - 1, 0));
					} else if (event.key === "Enter" && open && matches[active]) {
						event.preventDefault();
						choose(matches[active]);
					} else if (event.key === "Escape") {
						setOpen(false);
						setQuery("");
					}
				}}
			/>
			<Chevron />

			{open && (
				<ul
					id={listId}
					role="listbox"
					className="absolute z-20 mt-1.5 max-h-60 w-full overflow-y-auto rounded-xl border border-card-line bg-white py-1 shadow-pop"
				>
					{matches.length === 0 && (
						<li className="px-3.5 py-2.5 text-[12.5px] text-slate-faint">Nothing matches.</li>
					)}
					{matches.map((option, index) => (
						// The li carries no role of its own: a listbox's children must be
						// options, and an implicit listitem between them is exactly the
						// kind of thing a screen reader announces wrongly.
						<li key={option} role="none">
							<button
								type="button"
								role="option"
								aria-selected={option === value}
								onMouseEnter={() => setActive(index)}
								onClick={() => choose(option)}
								className={cx(
									"flex w-full items-center justify-between px-3.5 py-2 text-left text-[13px]",
									index === active ? "bg-surface text-ink" : "text-slate-strong",
									option === value && "font-bold text-ink",
								)}
							>
								{option}
								{option === value && <Tick className="text-ink" />}
							</button>
						</li>
					))}
				</ul>
			)}
		</div>
	);
}

/* --------------------------------------------------------------- selection */

/** A two-or-three way toggle. The SPA's answer to a short Select field. */
export function Segmented({
	value,
	onChange,
	options,
	label,
}: {
	value: string;
	onChange: (value: string) => void;
	options: string[];
	label: string;
}) {
	return (
		<div
			role="radiogroup"
			aria-label={label}
			className="inline-flex rounded-full border border-card-line bg-surface p-1"
		>
			{options.map((option) => (
				<button
					key={option}
					type="button"
					role="radio"
					aria-checked={value === option}
					onClick={() => onChange(option)}
					className={cx(
						"rounded-full px-4 py-1.5 text-[12.5px] font-bold transition",
						value === option
							? "bg-white text-ink border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)]"
							: "text-muted hover:text-slate-strong",
					)}
				>
					{option}
				</button>
			))}
		</div>
	);
}

/**
 * The picks, echoed as removable tokens above the control that made them.
 *
 * Shared by the two multi-select controls below, so "what did I answer" reads
 * the same whichever question asked it. Renders nothing at all when nothing is
 * chosen: an empty tray reserving space is a row of furniture explaining that
 * there is no furniture.
 */
export function TokenTray({
	tokens,
	onRemove,
	label,
}: {
	tokens: Array<{ key: string; label: string }>;
	onRemove: (key: string) => void;
	label: string;
}) {
	if (tokens.length === 0) return null;

	return (
		<ul className="mt-2.5 flex flex-wrap gap-1.5" aria-label={`${label} chosen`}>
			{tokens.map((token) => (
				<li key={token.key}>
					<button
						type="button"
						onClick={() => onRemove(token.key)}
						className="group inline-flex items-center gap-1.5 rounded-full border border-blue-line bg-blue-soft py-1 pl-3 pr-2 text-[12px] font-semibold text-blue-press transition hover:border-blue hover:bg-blue-line/40"
					>
						{token.label}
						<span
							aria-hidden="true"
							className="grid h-3.5 w-3.5 place-items-center rounded-full bg-blue/20 text-blue-press transition group-hover:bg-blue group-hover:text-white"
						>
							<svg viewBox="0 0 24 24" width="9" height="9" fill="none">
								<path
									d="M6 6l12 12M18 6L6 18"
									stroke="currentColor"
									strokeWidth="3.5"
									strokeLinecap="round"
								/>
							</svg>
						</span>
						<span className="sr-only">Remove</span>
					</button>
				</li>
			))}
		</ul>
	);
}

/**
 * A type-to-filter multi select over a vocabulary, for a list too long to read.
 *
 * `Combo`'s rule holds here too: **typing filters, it never sets.** Every value
 * comes from the list, because the field behind this is a table of Links and a
 * browser that let somebody submit a language the site does not have would be
 * building a rejection the server has to explain later. What a person cannot
 * find, an administrator adds as a record — the same way a skill is added.
 *
 * The chosen rows stay in the list rather than being removed from it, so the
 * position of everything else does not move under the pointer as you pick.
 */
export function MultiCombo({
	id,
	options,
	selected,
	onToggle,
	label,
	placeholder = "Type to search…",
	empty,
	required = false,
}: {
	id?: string;
	options: Array<{ key: string; label: string; description?: string | null }>;
	selected: string[];
	onToggle: (key: string) => void;
	label: string;
	placeholder?: string;
	empty?: ReactNode;
	required?: boolean;
}) {
	const listId = useId();
	const [open, setOpen] = useState(false);
	const [query, setQuery] = useState("");
	const [active, setActive] = useState(0);
	const wrap = useRef<HTMLDivElement>(null);

	const matches = useMemo(() => {
		const needle = query.trim().toLowerCase();
		if (!needle) return options;
		return options.filter((option) => option.label.toLowerCase().includes(needle));
	}, [options, query]);

	useEffect(() => {
		if (!open) return;

		const away = (event: MouseEvent) => {
			if (wrap.current && !wrap.current.contains(event.target as Node)) setOpen(false);
		};

		document.addEventListener("mousedown", away);
		return () => document.removeEventListener("mousedown", away);
	}, [open]);

	if (options.length === 0) {
		return (
			<div>
				<p className="mb-1.5 text-[12px] font-semibold text-slate-strong">
					{label}
					{required && (
						<span className="ml-1 text-danger" aria-hidden="true">
							*
						</span>
					)}
				</p>
				<p className="rounded-xl bg-surface px-4 py-3 text-[12.5px] text-muted">
					{empty ?? "This society has not configured any options here yet."}
				</p>
			</div>
		);
	}

	const chosen = selected
		.map((key) => options.find((option) => option.key === key))
		.filter((option): option is { key: string; label: string; description?: string | null } =>
			Boolean(option),
		);

	// Picking does not close the list and does not clear the filter: somebody
	// choosing three languages types once and ticks three rows.
	const pick = (key: string) => {
		onToggle(key);
		setOpen(true);
	};

	return (
		<div>
			{/* A visible label, not only an `aria-label`. This control sits in a
			    grid of `Field`s that all carry one, and the odd one out reads as a
			    stray search box rather than as an answer to a question. */}
			<label
				htmlFor={id}
				className="mb-1.5 block text-[12px] font-semibold text-slate-strong"
			>
				{label}
				{required && (
					<span className="ml-1 text-danger" aria-hidden="true">
						*
					</span>
				)}
			</label>

			<div className="relative" ref={wrap}>
				<span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-faint">
					<svg viewBox="0 0 24 24" width="15" height="15" fill="none" aria-hidden="true">
						<circle cx="11" cy="11" r="6.5" stroke="currentColor" strokeWidth="2" />
						<path d="m16 16 4.5 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
					</svg>
				</span>

				<input
					id={id}
					role="combobox"
					aria-expanded={open}
					aria-controls={listId}
					aria-autocomplete="list"
					aria-label={label}
					aria-required={required}
					className={cx(CONTROL, "pl-9")}
					value={query}
					placeholder={placeholder}
					onFocus={() => setOpen(true)}
					onChange={(event) => {
						setQuery(event.target.value);
						setActive(0);
						setOpen(true);
					}}
					onKeyDown={(event) => {
						if (event.key === "ArrowDown") {
							event.preventDefault();
							setOpen(true);
							setActive((index) => Math.min(index + 1, matches.length - 1));
						} else if (event.key === "ArrowUp") {
							event.preventDefault();
							setActive((index) => Math.max(index - 1, 0));
						} else if (event.key === "Enter" && open && matches[active]) {
							// Otherwise the wizard's form would submit and walk somebody
							// to the next step on the keystroke that chose a language.
							event.preventDefault();
							pick(matches[active].key);
						} else if (event.key === "Escape") {
							setOpen(false);
							setQuery("");
						}
					}}
				/>

				{open && (
					<ul
						id={listId}
						role="listbox"
						aria-multiselectable="true"
						className="absolute z-20 mt-1.5 max-h-64 w-full overflow-y-auto rounded-xl border border-card-line bg-white py-1 shadow-pop"
					>
						{matches.length === 0 && (
							<li className="px-3.5 py-3 text-[12.5px] leading-relaxed text-slate-faint">
								Nothing matches “{query.trim()}”. Your branch can add it to the list.
							</li>
						)}

						{matches.map((option, index) => {
							const on = selected.includes(option.key);

							return (
								<li key={option.key} role="none">
									<button
										type="button"
										role="option"
										aria-selected={on}
										onMouseEnter={() => setActive(index)}
										onClick={() => pick(option.key)}
										className={cx(
											"flex w-full items-start gap-2.5 px-3.5 py-2 text-left",
											index === active && "bg-surface",
										)}
									>
										<span
											className={cx(
												"mt-px grid h-4 w-4 flex-none place-items-center rounded-[4px] border transition",
												on ? "border-blue bg-blue" : "border-card-line bg-white",
											)}
											aria-hidden="true"
										>
											{on && <Tick className="text-white" size={10} />}
										</span>
										<span className="min-w-0">
											<span
												className={cx(
													"block text-[13px]",
													on ? "font-semibold text-ink" : "text-slate-strong",
												)}
											>
												{option.label}
											</span>
											{option.description && (
												<span className="mt-0.5 block text-[11.5px] leading-relaxed text-slate-faint">
													{option.description}
												</span>
											)}
										</span>
									</button>
								</li>
							);
						})}
					</ul>
				)}
			</div>

			{/* Below the field, the way the concept's registration sheet draws it:
			    the input is where you look to *add*, the tray is what you have
			    already said, and putting the tray above pushed the field down the
			    page every time somebody picked something. */}
			<TokenTray
				tokens={chosen.map((option) => ({ key: option.key, label: option.label }))}
				onRemove={onToggle}
				label={label}
			/>
		</div>
	);
}

/** A big radio card: a choice important enough to explain on the page. */
export function ChoiceCard({
	selected,
	onSelect,
	title,
	body,
	icon,
	aside,
}: {
	selected: boolean;
	onSelect: () => void;
	title: ReactNode;
	body?: ReactNode;
	icon?: ReactNode;
	aside?: ReactNode;
}) {
	return (
		<button
			type="button"
			role="radio"
			aria-checked={selected}
			onClick={onSelect}
			className={cx(
				"group relative flex w-full items-start gap-3.5 rounded-xl border p-5 text-left transition",
				selected
					? "border-blue bg-rail/[0.04] border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)] ring-1 ring-blue"
					: "border-card-line bg-white hover:-translate-y-0.5 hover:border-card-line hover:border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)]",
			)}
		>
			{icon && (
				<span
					className={cx(
						"grid h-10 w-10 flex-none place-items-center rounded-xl transition",
						selected ? "bg-rail text-white" : "bg-surface text-ink",
					)}
					aria-hidden="true"
				>
					{icon}
				</span>
			)}

			<span className="min-w-0 flex-1">
				<span className="flex items-baseline justify-between gap-3">
					<span className="text-[15px] font-bold text-ink">{title}</span>
					{aside}
				</span>
				{body && (
					<span className="mt-1.5 block text-[12.5px] leading-relaxed text-muted">{body}</span>
				)}
			</span>

			<span
				className={cx(
					"grid h-5 w-5 flex-none place-items-center rounded-full border transition",
					selected ? "border-blue bg-rail" : "border-card-line bg-white",
				)}
				aria-hidden="true"
			>
				{selected && <Tick className="text-white" size={11} />}
			</span>
		</button>
	);
}

export function Tick({ className, size = 12 }: { className?: string; size?: number }) {
	return (
		<svg
			viewBox="0 0 24 24"
			width={size}
			height={size}
			fill="none"
			aria-hidden="true"
			className={className}
		>
			<path d="m5 13 4 4L19 7" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
		</svg>
	);
}

/**
 * A file the applicant attaches, uploaded before the record it belongs to exists.
 *
 * It has to be: somebody picks their chief's letter, a copy of their national
 * card or their parent's signed form several steps before anything is filed. So
 * the file is created private and unattached, and the server anchors it at the
 * moment of insert — `questions.anchor_files()` for an answer,
 * `evidence.secure()` for an identity document's copy and for a guardian's
 * consent — which is what makes it readable by the approver and by nobody else.
 * Until then it belongs to the person who uploaded it, which is the right state
 * for a document not yet given to anybody.
 *
 * The framework's own uploader, the same one the content editor uses, rather
 * than a second one written here.
 */
export function PrivateUpload({
	id,
	value,
	onChange,
	choose = "Choose file",
	replace = "Replace file",
}: {
	id: string;
	value: string;
	onChange: (value: string) => void;
	/** What the button says. Named for the thing, so two on one screen differ. */
	choose?: string;
	replace?: string;
}) {
	const { upload, loading } = useFrappeFileUpload();
	const [failure, setFailure] = useState<string | null>(null);

	const pick = async (file: File | undefined) => {
		if (!file) return;
		setFailure(null);

		try {
			const uploaded = await upload(file, {
				// Private, and it stays private. A letter naming somebody's chief is
				// not a public asset, and the permission that governs it becomes the
				// application's own once the registration anchors it.
				isPrivate: true,
			});
			onChange(uploaded.file_url);
		} catch (uploadError) {
			setFailure(errorMessage(uploadError, "That file could not be uploaded."));
		}
	};

	return (
		<div>
			<div className="flex items-center gap-3">
				<label
					htmlFor={id}
					className="cursor-pointer rounded-lg border border-card-line bg-canvas px-3 py-2 text-[12px] font-semibold text-ink hover:border-brand"
				>
					{loading ? "Uploading…" : value ? replace : choose}
				</label>
				<input
					id={id}
					type="file"
					className="sr-only"
					disabled={loading}
					onChange={(event) => pick(event.target.files?.[0])}
				/>

				{value && !loading && (
					<span className="inline-flex items-center gap-1.5 text-[12px] text-slate-faint">
						<Tick className="text-brand" />
						Attached
					</span>
				)}
			</div>

			{failure && (
				<p className="mt-2 text-[11.5px] leading-relaxed text-danger">{failure}</p>
			)}
		</div>
	);
}
