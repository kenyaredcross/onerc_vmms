import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { useFrappeGetCall, useFrappePostCall } from "frappe-react-sdk";

import { API, errorMessage } from "../lib/api";
import { PrivateUpload } from "../ui/form";
import { Empty, ErrorNote, Spinner } from "../ui/primitives";
import type { Opportunity } from "./types";

type Question = {
	question_id: string;
	question: string;
	question_type: string;
	is_required: boolean;
	help_text?: string;
	options: string[];
};

type FormAnswer = {
	opening: Opportunity | null;
	volunteering?: boolean;
	questions?: Question[];
	identity?: { full_name: string; email: string; phone: string };
	already_applied?: boolean;
	may_apply?: boolean;
	eligibility?: "approved" | "pending" | "inactive" | "not_registered";
};

const control = "mt-1.5 w-full rounded-lg border border-card-line bg-white px-3 py-2.5 text-[13px] text-ink focus:border-blue focus:outline-none focus:ring-2 focus:ring-blue/20";

export default function JobApplication() {
	const { name = "" } = useParams();
	const form = useFrappeGetCall<{ message: FormAnswer }>(
		API.jobApplicationForm,
		{ name },
		name ? `portal:job-application-form:${name}` : null,
	);
	const employment = useFrappePostCall<{ message: { name: string } }>(API.applyForJob);
	const volunteer = useFrappePostCall<{ message: { name: string } }>(API.applyToOpening);
	const [fullName, setFullName] = useState("");
	const [phone, setPhone] = useState("");
	const [coverLetter, setCoverLetter] = useState("");
	const [resume, setResume] = useState("");
	const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
	const [failure, setFailure] = useState<string | null>(null);
	const [submitted, setSubmitted] = useState<string | null>(null);
	const [busy, setBusy] = useState(false);
	const data = form.data?.message;
	const opening = data?.opening;
	const identity = data?.identity;
	const isVolunteer = Boolean(data?.volunteering);

	const submit = async (event: FormEvent) => {
		event.preventDefault();
		if (!opening || !data?.may_apply || busy) return;
		setFailure(null);
		setBusy(true);
		try {
			const result = isVolunteer
				? await volunteer.call({ name, answers, cover_letter: coverLetter })
				: await employment.call({
					name,
					full_name: fullName.trim() || identity?.full_name || "",
					phone: phone.trim() || identity?.phone || "",
					cover_letter: coverLetter,
					resume,
					answers,
				});
			setSubmitted(result.message.name);
		} catch (error) {
			setFailure(errorMessage(error, "Your application could not be sent."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<div className="mx-auto max-w-2xl">
			<Link to={`/opportunities/${encodeURIComponent(name)}`} className="text-[13px] font-semibold text-blue hover:underline">
				← Back to opening
			</Link>
			{form.isLoading && <Spinner label="Loading application…" />}
			{form.error && <ErrorNote>{errorMessage(form.error)}</ErrorNote>}
			{!form.isLoading && !form.error && !opening && <Empty title="This opening is no longer available">See current openings on the opportunities page.</Empty>}
			{opening && (
				<article className="mt-5 rounded-2xl border border-card-line bg-white p-6 shadow-sm sm:p-8">
					<p className="text-[11px] font-bold uppercase tracking-widest text-blue">Job application</p>
					<h1 className="mt-2 text-2xl font-bold text-ink">{opening.title}</h1>
					<p className="mt-2 text-[13px] text-muted">{[opening.department, opening.location, opening.employment_type].filter(Boolean).join(" · ")}</p>
					{submitted ? (
						<div className="mt-8 rounded-xl border border-green-200 bg-green-50 p-5 text-[13px] text-green-900" role="status">
							<h2 className="font-bold">Application received</h2>
							<p className="mt-1">Your reference is {submitted}. The recruitment team can now review your application.</p>
							<Link to="/opportunities" className="mt-3 inline-block font-semibold underline">All opportunities</Link>
						</div>
					) : !data.may_apply ? (
						<div className="mt-8 rounded-xl bg-surface p-5 text-[13px] text-ink" role="status">
							{data.eligibility === "pending" ? (
								<><h2 className="font-bold">Your volunteer approval is pending</h2><p className="mt-1">Your volunteer application must be fully approved before you can apply for an opportunity.</p><Link to="/join?path=volunteer" className="mt-3 inline-block font-semibold text-blue underline">View volunteer application</Link></>
							) : data.eligibility === "inactive" ? (
								<><h2 className="font-bold">Your volunteer record is not active</h2><p className="mt-1">Please contact your branch. Your volunteer record must be active before you can apply.</p></>
							) : (
								<><h2 className="font-bold">Register as a volunteer first</h2><p className="mt-1">You can apply for opportunities once your volunteer application has been fully approved.</p><Link to="/join?path=volunteer" className="mt-3 inline-block font-semibold text-blue underline">Register as a volunteer</Link></>
							)}
						</div>
					) : data.already_applied ? (
						<p className="mt-8 rounded-xl bg-blue/10 p-5 text-[13px] text-ink">You have already applied for this opening. Your application is with the recruitment team.</p>
					) : (
						<form className="mt-7 space-y-5" onSubmit={(event) => void submit(event)}>
							{isVolunteer ? (
								<p className="rounded-xl bg-blue/10 p-4 text-[13px] text-ink">Your name and contact details will be taken from your volunteer record.</p>
							) : (
								<>
									<label className="block text-[13px] font-semibold text-ink">Full name <span className="text-red-600">*</span>
										<input className={control} required value={fullName} placeholder={identity?.full_name || "Your full name"} onChange={(event) => setFullName(event.target.value)} />
									</label>
									<label className="block text-[13px] font-semibold text-ink">Email address
										<input className={control} value={identity?.email || ""} readOnly />
									</label>
									<label className="block text-[13px] font-semibold text-ink">Phone number
										<input className={control} type="tel" value={phone} placeholder={identity?.phone || "Optional"} onChange={(event) => setPhone(event.target.value)} />
									</label>
									<div className="text-[13px] font-semibold text-ink">CV or resume <span className="font-normal text-muted">(optional)</span>
										<div className="mt-2"><PrivateUpload id="job-resume" value={resume} onChange={setResume} choose="Upload CV or resume" /></div>
									</div>
								</>
							)}
							{(data.questions || []).map((question) => (
								<label key={question.question_id} className="block text-[13px] font-semibold text-ink">
									{question.question} {question.is_required && <span className="text-red-600">*</span>}
									{question.help_text && <span className="mt-1 block font-normal text-muted">{question.help_text}</span>}
									{question.question_type === "Upload" ? (
										<div className="mt-2"><PrivateUpload id={`question-${question.question_id}`} value={String(answers[question.question_id] || "")} onChange={(value) => setAnswers((old) => ({ ...old, [question.question_id]: value }))} /></div>
									) : question.question_type === "MultiSelect" ? (
										<div className="mt-2 flex flex-wrap gap-3">
											{question.options.map((option) => {
												const selected = Array.isArray(answers[question.question_id]) ? answers[question.question_id] as string[] : [];
												return <label key={option} className="inline-flex items-center gap-2 rounded-lg border border-card-line px-3 py-2 text-[12px] font-normal">
													<input type="checkbox" checked={selected.includes(option)} onChange={(event) => setAnswers((old) => ({ ...old, [question.question_id]: event.target.checked ? [...selected, option] : selected.filter((item) => item !== option) }))} />
													{option}
												</label>;
											})}
										</div>
									) : question.options.length || question.question_type === "Yes/No" ? (
										<select required={question.is_required} className={control} value={String(answers[question.question_id] || "")} onChange={(event) => setAnswers((old) => ({ ...old, [question.question_id]: event.target.value }))}>
											<option value="">Select an answer</option>
											{(question.question_type === "Yes/No" ? ["Yes", "No"] : question.options).map((option) => <option key={option} value={option}>{option}</option>)}
										</select>
									) : (
										<input required={question.is_required} className={control} type={question.question_type === "Date" ? "date" : question.question_type === "Number" ? "number" : question.question_type === "Email" ? "email" : "text"} value={String(answers[question.question_id] || "")} onChange={(event) => setAnswers((old) => ({ ...old, [question.question_id]: event.target.value }))} />
									)}
								</label>
							))}
							<label className="block text-[13px] font-semibold text-ink">Cover letter <span className="font-normal text-muted">(optional)</span>
								<textarea className={control} rows={5} value={coverLetter} onChange={(event) => setCoverLetter(event.target.value)} placeholder="Tell us why you are interested in this role" />
							</label>
							{failure && <ErrorNote>{failure}</ErrorNote>}
							<button type="submit" disabled={busy} className="rounded-xl bg-blue px-6 py-3 text-[13px] font-bold text-white hover:bg-blue-press disabled:opacity-50">{busy ? "Sending…" : "Submit application"}</button>
						</form>
					)}
				</article>
			)}
		</div>
	);
}
