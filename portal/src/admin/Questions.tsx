import { useContext, useEffect, useId, useState } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import {
	Button,
	Card,
	Empty,
	ErrorNote,
	PageHeading,
	Pill,
	SectionTitle,
	Spinner,
	cx,
} from "../ui/primitives";
import type { BuilderQuestion, QuestionCatalogue, QuestionTargets } from "../portal/types";

/**
 * The form builder: what this society asks applicants, beyond the standard form.
 *
 * `VMMS Application Question` has always been editable on the desk. What it had
 * no way to be was editable by somebody who never opens the desk — and the one
 * screen in this product that exists so a branch can ask a new question *without
 * a deploy* still meant opening a Link-to-DocType field and knowing which
 * doctype meant "the volunteer form".
 *
 * **This screen names no registration.** The tabs come from
 * `questions.targets`, which derives them from whichever doctypes carry the
 * answer table. A third registration that opts in gets a tab here on its own,
 * and nothing in this file has to learn its name.
 *
 * **It names no role either.** The tab is drawn only when `console.sections`
 * includes it, and that section is gated on write permission for the question
 * doctype — which no configurable scope role is granted, so it resolves to the
 * administrator. `can_edit` from the endpoint decides whether the controls are
 * drawn, and every write is re-checked server-side regardless.
 *
 * **Retire, never delete.** There is no delete control because there is no
 * delete endpoint: an answer already given was part of an application somebody
 * decided, and removing the question would take evidence out from under it. The
 * answer count on each row is there to make that make sense at the moment
 * somebody goes looking for a bin icon.
 */
export default function Questions() {
	const [target, setTarget] = useState<string | null>(null);

	const targets = useFrappeGetCall<{ message: QuestionTargets }>(
		API.questionTargets,
		undefined,
		"admin:question_targets",
	);

	const rows = targets.data?.message.targets ?? [];

	// The first registration, once we know what they are. Chosen here rather than
	// defaulted to a name, because this file does not know one.
	useEffect(() => {
		if (!target && rows.length > 0) {
			setTarget(rows[0].doctype);
		}
	}, [rows, target]);

	if (targets.isLoading) {
		return <Spinner page label="Loading the form builder…" />;
	}

	if (targets.error) {
		return <ErrorNote>{errorMessage(targets.error)}</ErrorNote>;
	}

	return (
		<>
			<PageHeading
				title={<EditableText k="admin.questions.heading" fallback="Form questions" />}
				actions={
					<div className="flex flex-wrap gap-2">
						{rows.map((row) => (
							<button
								key={row.doctype}
								type="button"
								onClick={() => setTarget(row.doctype)}
								className={cx(
									"whitespace-nowrap rounded-full px-4 py-2 text-[12px] font-semibold transition",
									target === row.doctype
										? "bg-ink text-white"
										: "border border-hairline-strong bg-white text-slate-strong hover:border-navy",
								)}
							>
								{/* The `VMMS ` prefix is dropped for display the same way
								    `ReviewQueue.tsx` drops it, rather than a label being
								    invented server-side. */}
								{row.label.replace(/^VMMS /, "")}
								<span className="ml-2 opacity-60">{row.count}</span>
							</button>
						))}
					</div>
				}
			/>

			<p className="mb-6 max-w-2xl text-[13px] text-slate-body">
				<EditableText
					k="admin.questions.intro"
					fallback="Questions added here are asked on the registration form and shown to whoever approves the application. Applications already in are not changed."
				/>
			</p>

			{rows.length === 0 ? (
				<Empty title="No registration accepts questions">
					A registration opts in by carrying an answer table. None on this site does.
				</Empty>
			) : (
				target && (
					<Builder
						key={target}
						askedOn={target}
						fieldTypes={targets.data?.message.field_types ?? []}
						groups={targets.data?.message.groups ?? []}
						onChanged={() => void targets.mutate()}
					/>
				)
			)}
		</>
	);
}

/* ----------------------------------------------------------------- builder */

function Builder({
	askedOn,
	fieldTypes,
	groups,
	onChanged,
}: {
	askedOn: string;
	fieldTypes: string[];
	groups: string[];
	onChanged: () => void;
}) {
	const [editing, setEditing] = useState<BuilderQuestion | "new" | null>(null);

	const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: QuestionCatalogue }>(
		API.questionCatalogue,
		{ asked_on: askedOn },
		`admin:questions:${askedOn}`,
	);

	const catalogue = data?.message;
	const questions = catalogue?.questions ?? [];
	const canEdit = catalogue?.can_edit ?? false;

	const refresh = () => {
		void mutate();
		onChanged();
	};

	if (isLoading) {
		return <Spinner label="Loading the questions…" />;
	}

	if (error) {
		return <ErrorNote>{errorMessage(error)}</ErrorNote>;
	}

	return (
		<>
			{canEdit && editing === null && (
				<div className="mb-5">
					<Button onClick={() => setEditing("new")}>Add a question</Button>
				</div>
			)}

			{editing !== null && (
				<QuestionForm
					askedOn={askedOn}
					fieldTypes={fieldTypes}
					groups={groups}
					question={editing === "new" ? null : editing}
					onDone={() => {
						setEditing(null);
						refresh();
					}}
					onCancel={() => setEditing(null)}
				/>
			)}

			{questions.length === 0 ? (
				<Empty title="No questions yet">
					The registration form asks only the standard questions. Anything you add here
					appears on it immediately.
				</Empty>
			) : (
				<div className="space-y-3">
					{questions.map((question, index) => (
						<QuestionRow
							key={question.name}
							question={question}
							canEdit={canEdit}
							isFirst={index === 0}
							isLast={index === questions.length - 1}
							onEdit={() => setEditing(question)}
							onChanged={refresh}
							order={questions.map((row) => row.name)}
							askedOn={askedOn}
						/>
					))}
				</div>
			)}
		</>
	);
}

/* --------------------------------------------------------------- one row */

function QuestionRow({
	question,
	canEdit,
	isFirst,
	isLast,
	onEdit,
	onChanged,
	order,
	askedOn,
}: {
	question: BuilderQuestion;
	canEdit: boolean;
	isFirst: boolean;
	isLast: boolean;
	onEdit: () => void;
	onChanged: () => void;
	order: string[];
	askedOn: string;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const act = async (method: string, args: Record<string, unknown>) => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(method, args);
			onChanged();
		} catch (actError) {
			setFailure(errorMessage(actError, "That change was not saved."));
		} finally {
			setBusy(false);
		}
	};

	/** Move one place, by sending the whole order rather than a single move.
	 *
	 * The server takes the list and numbers it, so the result cannot depend on
	 * what this screen believed the previous sequence was. */
	const move = (by: number) => {
		const next = [...order];
		const at = next.indexOf(question.name);

		if (at < 0) return;

		next.splice(at + by, 0, ...next.splice(at, 1));

		return act(API.reorderQuestions, { asked_on: askedOn, order: next });
	};

	return (
		<Card className={cx(!question.is_active && "opacity-60")}>
			<div className="flex flex-wrap items-start justify-between gap-3">
				<div className="min-w-0">
					<p className="font-display text-[15px] font-bold text-ink">
						{question.label}
						{question.is_required && <span className="ml-1 text-signal">*</span>}
					</p>
					<div className="mt-1.5 flex flex-wrap gap-1.5">
						{/* First, because it is what says where on the form this
						    question appears — the field type only matters once you
						    know that. */}
						{question.group && <Pill tone="navy">{question.group}</Pill>}
						<Pill tone="page">{question.field_type}</Pill>
						{!question.is_active && <Pill tone="page">Retired</Pill>}
						{question.answer_count > 0 && (
							<Pill tone="page">{question.answer_count} answered</Pill>
						)}
					</div>
					{question.help_text && (
						<p className="mt-2 text-[13px] text-slate-body">{question.help_text}</p>
					)}
					{question.choices.length > 0 && (
						<p className="mt-2 text-[12px] text-slate-faint">
							Choices: {question.choices.join(" · ")}
						</p>
					)}
				</div>

				{canEdit && (
					<div className="flex flex-none flex-wrap items-center gap-1.5">
						<button
							type="button"
							onClick={() => void move(-1)}
							disabled={busy || isFirst}
							aria-label="Move up"
							className="grid h-8 w-8 place-items-center rounded-card border border-hairline-strong text-slate-body transition hover:border-navy hover:text-navy disabled:opacity-30"
						>
							↑
						</button>
						<button
							type="button"
							onClick={() => void move(1)}
							disabled={busy || isLast}
							aria-label="Move down"
							className="grid h-8 w-8 place-items-center rounded-card border border-hairline-strong text-slate-body transition hover:border-navy hover:text-navy disabled:opacity-30"
						>
							↓
						</button>
						<Button variant="quiet" onClick={onEdit} disabled={busy}>
							Edit
						</Button>
						<Button
							variant="quiet"
							disabled={busy}
							onClick={() =>
								void act(API.setQuestionActive, {
									name: question.name,
									is_active: !question.is_active,
								})
							}
						>
							{question.is_active ? "Retire" : "Ask again"}
						</Button>
					</div>
				)}
			</div>

			{failure && (
				<div className="mt-3">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			{/* Said on the row that has answers, because it is the moment somebody
			    wonders why there is no delete. */}
			{canEdit && question.answer_count > 0 && (
				<p className="mt-3 border-t border-hairline pt-3 text-[12px] text-slate-faint">
					Retiring stops this being asked. The {question.answer_count} answers already given
					stay on the applications they were part of.
				</p>
			)}
		</Card>
	);
}

/* ------------------------------------------------------------- the editor */

const NEEDS_CHOICES = "Select";

function QuestionForm({
	askedOn,
	fieldTypes,
	groups,
	question,
	onDone,
	onCancel,
}: {
	askedOn: string;
	fieldTypes: string[];
	/** Groups already in use on this site, offered rather than retyped. */
	groups: string[];
	question: BuilderQuestion | null;
	onDone: () => void;
	onCancel: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const groupListId = useId();
	const [label, setLabel] = useState(question?.label ?? "");
	const [group, setGroup] = useState(question?.group ?? "");
	const [fieldType, setFieldType] = useState(question?.field_type ?? fieldTypes[0] ?? "Data");
	const [options, setOptions] = useState(question?.options ?? "");
	const [helpText, setHelpText] = useState(question?.help_text ?? "");
	const [isRequired, setIsRequired] = useState(question?.is_required ?? false);
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const choicesNeeded = fieldType === NEEDS_CHOICES;
	const choices = options.split("\n").map((line) => line.trim()).filter(Boolean);

	const save = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.saveQuestion, {
				name: question?.name,
				asked_on: askedOn,
				question_label: label,
				question_group: group,
				field_type: fieldType,
				options,
				help_text: helpText,
				is_required: isRequired,
			});
			onDone();
		} catch (saveError) {
			// The server refuses a Select with no choices through the doctype's own
			// validate(), so its sentence is the one worth showing.
			setFailure(errorMessage(saveError, "That question was not saved."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Card className="mb-5">
			<SectionTitle>{question ? "Edit question" : "New question"}</SectionTitle>

			<div className="grid gap-4 sm:grid-cols-2">
				<label className="block sm:col-span-2">
					<span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-faint">
						What are you asking?
					</span>
					<input
						value={label}
						onChange={(event) => setLabel(event.target.value)}
						placeholder="Letter from the area chief"
						className="w-full rounded-card border border-hairline-strong px-3 py-2 text-[14px]"
					/>
				</label>

				{/* The tab this question is drawn under, and the whole of how a
				    society builds a section of its own — "Health information",
				    "Next of kin". A free-text field with a suggestion list rather
				    than a closed set: what a national society groups its questions
				    under is its own vocabulary, and a list of options here would be
				    this app deciding what a form may ask about. */}
				<label className="block sm:col-span-2">
					<span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-faint">
						Group it under (optional)
					</span>
					<input
						value={group}
						list={groupListId}
						onChange={(event) => setGroup(event.target.value)}
						placeholder="Health information"
						className="w-full rounded-card border border-hairline-strong px-3 py-2 text-[14px]"
					/>
					<datalist id={groupListId}>
						{groups.map((option) => (
							<option key={option} value={option} />
						))}
					</datalist>
					<span className="mt-1 block text-[12px] text-slate-faint">
						Questions sharing a group are asked together and become one tab on the
						approver's screen. Left empty, this sits with the ungrouped ones.
					</span>
				</label>

				<label className="block">
					<span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-faint">
						Kind of answer
					</span>
					<select
						value={fieldType}
						onChange={(event) => setFieldType(event.target.value)}
						className="w-full rounded-card border border-hairline-strong px-3 py-2 text-[14px]"
					>
						{fieldTypes.map((type) => (
							<option key={type} value={type}>
								{type}
							</option>
						))}
					</select>
				</label>

				<label className="flex items-end gap-2 pb-2 text-[13px] text-slate-body">
					<input
						type="checkbox"
						checked={isRequired}
						onChange={(event) => setIsRequired(event.target.checked)}
					/>
					An applicant must answer this
				</label>

				{choicesNeeded && (
					<label className="block sm:col-span-2">
						<span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-faint">
							Choices, one per line
						</span>
						<textarea
							value={options}
							onChange={(event) => setOptions(event.target.value)}
							rows={4}
							className="w-full rounded-card border border-hairline-strong px-3 py-2 text-[14px]"
						/>
						<span className="mt-1 block text-[12px] text-slate-faint">
							{choices.length === 0
								? "A question answered from a list needs at least one choice."
								: `${choices.length} choices: ${choices.join(" · ")}`}
						</span>
					</label>
				)}

				<label className="block sm:col-span-2">
					<span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-faint">
						Guidance beneath the question (optional)
					</span>
					<textarea
						value={helpText}
						onChange={(event) => setHelpText(event.target.value)}
						rows={2}
						className="w-full rounded-card border border-hairline-strong px-3 py-2 text-[14px]"
					/>
				</label>
			</div>

			{question && (
				<p className="mt-4 text-[12px] text-slate-faint">
					Rewording this does not change what anybody was already asked: an answer keeps a
					snapshot of the question as it stood when it was given.
				</p>
			)}

			{failure && (
				<div className="mt-3">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			<div className="mt-5 flex gap-2">
				<Button
					onClick={() => void save()}
					disabled={busy || !label.trim() || (choicesNeeded && choices.length === 0)}
				>
					{busy ? "Saving…" : question ? "Save changes" : "Add question"}
				</Button>
				<Button variant="ghost" onClick={onCancel} disabled={busy}>
					Cancel
				</Button>
			</div>
		</Card>
	);
}
