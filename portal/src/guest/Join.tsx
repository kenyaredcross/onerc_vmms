import { Fragment, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
	FrappeContext,
	useFrappeFileUpload,
	useFrappeGetCall,
	type FrappeConfig,
} from "frappe-react-sdk";

import { ContentProvider } from "../content/ContentProvider";
import { API, errorMessage } from "../lib/api";
import { formatDate, formatMoney } from "../lib/format";
import { loginUrl, signupUrl, useSession } from "../lib/session";
import { BrandLockup } from "../ui/brand";
import { GeoSelects, selectedNode } from "../ui/GeoSelects";
import { PlanCards } from "../ui/PlanCards";
import {
	ChoiceCard,
	Combo,
	Field,
	FieldSet,
	MultiCombo,
	Segmented,
	SelectInput,
	TextArea,
	TextInput,
	Tick,
	VocabularySelect,
} from "../ui/form";
import { Icon } from "../ui/icons";
import { Button, Card, ErrorNote, Spinner, StateBadge, cx } from "../ui/primitives";
import type {
	ApplicationOptions,
	Declaration,
	EmergencyContact,
	GeoNode,
	GuardianConsent,
	IdentityOptions,
	OpenRegistration,
	PaymentMethod,
	PricedType,
	RedProfile,
	SocietyQuestion,
} from "../portal/types";

type Path = "volunteer" | "member";

/**
 * What the payments app said when the fee was requested — `membership.submit`'s
 * `payment` key, present only when a fee was actually asked for.
 *
 * `message` is the *driver's* own sentence and this app neither writes it nor
 * reads inside it: an M-Pesa prompt, a bank account and a reference, an office
 * to call at. Rendered verbatim.
 */
type PaymentAsked = { transaction: string | null; status: string | null; message: string };

/** The applicant-owned fields served back when a saved/returned draft resumes. */
type DraftRegistration = OpenRegistration & {
	can_edit: boolean;
	geo_node: string;
	answers: Record<string, string>;
	membership_type?: string;
	membership_status?: string;
	payment_method?: string;
	skills?: string[];
	languages?: string[];
	availability?: string[];
	motivation?: string[];
	prior_experience?: string;
	/** Keys of the declarations already accepted, ready to re-tick on resume. */
	declarations?: string[];
	emergency_contacts?: EmergencyContact[];
	guardian_consents?: GuardianConsent[];
	is_minor?: boolean;
};

/**
 * The steps this wizard can show, as a closed set.
 *
 * Ids rather than indices, because the two paths do not walk the same road: a
 * volunteer answers citizenship, identification and a declaration that a member
 * is never asked for, and a member chooses a plan that a volunteer is not.
 * Composing the list per path and addressing steps by id keeps every "which step
 * am I on" question out of index arithmetic.
 */
/**
 * **`declaration` is not the consent step**, and the two must not be confused.
 * It predates the consents and it is "About your volunteering" — the skills,
 * languages, availability and motivation somebody *declares* about themselves.
 * What the applicant legally agrees to is `consents`, and it is a separate id
 * for exactly that reason.
 */
type StepId =
	| "path"
	| "identity"
	| "plan"
	| "payment"
	| "placement"
	| "identification"
	| "declaration"
	| "emergency"
	| "questions"
	| "consents"
	| "confirm";

/**
 * The residency branch, spelled exactly as `Red Profile` spells it and as
 * `volunteer/services/application.py::_assert_residency_complete` compares it.
 *
 * **This wizard no longer asks the question.** "Where do you live" was a
 * segmented control, a tickbox reading "I live in the area I want to serve" and
 * a second cascading picker behind it — three controls and most of a screen, to
 * confirm the answer already given two steps earlier on all but a handful of
 * registrations. A volunteer says where they want to volunteer; that is where
 * they live unless somebody says otherwise, and a desk clerk can say otherwise
 * on the profile itself.
 *
 * So `Local` travels with the serving branch, and `Abroad` survives here for one
 * reason: a profile that already says Abroad, with an address behind it, must
 * not be quietly rewritten to Local by somebody filling in a form that never
 * asked. See `persistDraft`.
 */
const LOCAL = "Local";
const ABROAD = "Abroad";

/**
 * The three answers to the disability question, spelled as the field spells
 * them.
 *
 * A closed list on both sides — `patches/install_disability_fields.py` holds the
 * same three — because it is a `Select` and a fourth word here would be an
 * answer the server refuses. "Prefer not to say" is one of them and not an
 * absence: declining is a real answer and it satisfies the requirement.
 */
const DISABILITY_ANSWERS = ["No", "Yes", "Prefer not to say"];

/* --------------------------------------------------------- identification */

/**
 * One identity document, as this form holds it.
 *
 * Deliberately narrower than the row `Red Profile` stores: `is_primary` is not
 * here because position says it — the first document somebody lists is their
 * main one — and `attachment` is not here because this form does not collect
 * files. A scan a branch attached on the desk survives a correction made here;
 * see `registration._identification_rows`.
 */
type Identification = { id_type: string; id_number: string };

function blankIdentification(): Identification {
	return { id_type: "", id_number: "" };
}

/** Enough of a document to be worth sending: a kind, and the number on it. */
function identificationIsUsable(row: Identification): boolean {
	return Boolean(row.id_type && row.id_number.trim());
}

/**
 * Not half-filled. Either the row is untouched, or it is complete.
 *
 * The same bargain `contactIsCoherent` strikes, for the same reason: a passport
 * with no number is not a document anybody can check, and the server refuses
 * the pair rather than storing half of it.
 */
function identificationIsCoherent(row: Identification): boolean {
	const touched = Boolean(row.id_type || row.id_number.trim());

	return !touched || identificationIsUsable(row);
}

/**
 * The same kind of document listed twice.
 *
 * A person has one national card. The server refuses the set — the required
 * documents check keys by type, so a repeat is a row nobody can see — and this
 * says so on the step rather than at submission.
 */
function repeatedIdentification(rows: Identification[]): boolean {
	const kinds = rows.filter(identificationIsUsable).map((row) => row.id_type);

	return new Set(kinds).size !== kinds.length;
}

/* ------------------------------------------------- emergency and guardian */

function blankContact(): EmergencyContact {
	return {
		contact_name: "",
		relationship: "",
		primary_phone: "",
		alternative_phone: "",
		// Ticked to begin with, because somebody who names an emergency contact
		// means us to call them. Unticking is the deliberate act.
		may_contact_in_emergency: true,
	};
}

function blankGuardian(): GuardianConsent {
	return {
		guardian_name: "",
		relationship: "",
		phone: "",
		email: "",
		consent_given: false,
		consent_date: "",
		verification_method: null,
		consent_evidence: null,
	};
}

/**
 * Whole years old today, by the same arithmetic the server uses.
 *
 * Local rather than fetched, because the answer has to change while somebody is
 * still typing their date of birth — but it decides nothing on its own: it only
 * chooses whether to *draw* the guardian block. The rule that actually governs
 * an approval is `application.is_minor`, on the server, and this cannot widen
 * or narrow it.
 */
function ageOn(dateOfBirth: string): number {
	const born = new Date(dateOfBirth);
	if (Number.isNaN(born.getTime())) return Number.POSITIVE_INFINITY;

	const now = new Date();
	const hadBirthday =
		now.getMonth() > born.getMonth() ||
		(now.getMonth() === born.getMonth() && now.getDate() >= born.getDate());

	return now.getFullYear() - born.getFullYear() - (hadBirthday ? 0 : 1);
}

/** Enough of a contact to be worth storing: somebody to call, and a number. */
function contactIsUsable(contact: EmergencyContact): boolean {
	return Boolean(contact.contact_name.trim() && contact.primary_phone.trim());
}

/**
 * Not half-filled. Either nothing has been entered, or enough has.
 *
 * A name with no number is not somebody anybody can call, and letting it through
 * would store a contact that satisfies nothing and looks like it does.
 */
function contactIsCoherent(contact: EmergencyContact): boolean {
	const touched = Boolean(
		contact.contact_name.trim() || contact.relationship.trim() || contact.primary_phone.trim(),
	);

	return !touched || contactIsUsable(contact);
}

function guardianIsUsable(guardian: GuardianConsent): boolean {
	return Boolean(guardian.guardian_name.trim() && guardian.phone.trim());
}

function guardianIsCoherent(guardian: GuardianConsent): boolean {
	const touched = Boolean(
		guardian.guardian_name.trim() || guardian.relationship.trim() || guardian.phone.trim(),
	);

	return !touched || guardianIsUsable(guardian);
}

/**
 * Registering yourself, in the single-page app.
 *
 * **It asks for what the server will insist on, and not for more.** The floor is
 * `application.assert_ready()`: a country of citizenship, an identification, a
 * date of birth, one complete residence shape and every required society
 * question. A wizard that collected less was not a simpler wizard, it was one
 * whose applications were refused at submission for want of an ID.
 *
 * The ceiling is the same rule read the other way. Where the server will accept
 * an answer this form can *derive*, it derives it rather than drawing a screen:
 * a residence is `Local`, at the branch somebody just said they want to
 * volunteer with, so "where do you live" is not asked. Six short pages for a
 * volunteer, five for a member, each with its own heading and its own reason to
 * exist, and a rail showing where in the road somebody is. A form that asks
 * thirty questions at once is the thing this replaced; a form that asks a
 * seventh page's worth of question it can answer itself is the same mistake with
 * better manners.
 *
 * **Leaving a step saves, and does not say so.** Every move between screens
 * writes the draft — see `goTo` — so nothing typed lives only in a browser tab.
 * It is silent about it: an applicant did not ask for the save and has nothing
 * to do with the answer. The "Save draft" button remains for anybody who wants
 * to press something before walking away, and that press is answered.
 *
 * **The identity rules are the server's, and this wizard does not re-implement
 * one of them.** It posts the identity buffer with the registration, which is
 * `intake.for_user` under a whitelist, so one login still gets exactly one Red
 * Profile forever, a login-less profile with the same email is still adopted,
 * and a profile bound to somebody else is still refused. The email is never a
 * field on this form, because the login is the identity.
 *
 * **Sign-in comes first, always.** A wizard that collected six screens of
 * answers and then discovered the person was not signed in would have to either
 * throw the answers away or stash identity in the browser. Frappe's own signup
 * and login already exist, so the first step sends them there and back.
 *
 * **Every list on these screens is configuration**, fetched from
 * `application_options`, `identity_options`, `membership_types` and
 * `geo.ladder`. No skill, language, ID type, country, gender, membership type
 * or hierarchy level is named in this file.
 */
export default function Join() {
	return (
		<ContentProvider surface="chrome,landing">
			<JoinBody />
		</ContentProvider>
	);
}

function JoinBody() {
	const [params, setParams] = useSearchParams();
	const { isGuest, isLoading: sessionLoading } = useSession();
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const requested = params.get("path");
	const [path, setPath] = useState<Path>(requested === "member" ? "member" : "volunteer");
	// Did they say what they are here for before arriving? "Become a volunteer"
	// and a plan card both do. Only a bare `/join` has not been answered, and it
	// is the only case that gets asked. Read once from the URL the wizard was
	// opened with: switching path later must not make the step reappear
	// underneath somebody, which would renumber every rung mid-registration.
	const [declared, setDeclared] = useState(
		() => requested === "member" || requested === "volunteer",
	);

	const [cursor, setCursor] = useState(0);
	const [furthest, setFurthest] = useState(0);
	const [direction, setDirection] = useState<"forward" | "back">("forward");

	// --- identity, which lands on the Red Profile and never on the satellite
	const [profile, setProfile] = useState<RedProfile | null>(null);
	const [firstName, setFirstName] = useState("");
	const [lastName, setLastName] = useState("");
	const [phone, setPhone] = useState("");
	const [gender, setGender] = useState("");
	const [dateOfBirth, setDateOfBirth] = useState("");
	// A file URL from the framework's own uploader, never the file. Optional, and
	// it is the one thing on the identity step nobody has to answer.
	const [photo, setPhoto] = useState("");

	// --- placement. The *chain* is the state, not the node: the wizard owns what
	// was answered at every rung so leaving the step and coming back to it shows
	// the selects as they were left. `selectedNode` derives the node from it.
	const [servingChain, setServingChain] = useState<GeoNode[]>([]);
	// Arriving from a plan card on the membership tab, the plan is already
	// chosen. It is a docname, and it travels with the person into the wizard.
	const [membershipType, setMembershipType] = useState(params.get("type") ?? "");

	/**
	 * Was the plan chosen *before* this wizard opened?
	 *
	 * Somebody who arrives here has already read the plans, compared what each
	 * covers and pressed the one they wanted; a step that asks them to choose
	 * again is the same question twice, and the second time it is asked in a
	 * worse place — a wizard rail, without the comparison that made the choice.
	 * So the step is not drawn for them at all.
	 *
	 * Read once from the URL the wizard was opened with, exactly like
	 * `declared`. Changing `membershipType` later must not make a step appear
	 * underneath somebody, which would renumber every rung mid-registration.
	 */
	const [planPreselected, setPlanPreselected] = useState(() => Boolean(params.get("type")));

	/**
	 * How this applicant wants to pay.
	 *
	 * A gateway name from `api/member.py::payment_methods` — the society's own
	 * list, which is what it ticked in its settings intersected with what the
	 * payments app currently has active. It travels with the registration and is
	 * re-checked on the server before any money is asked for, because a draft can
	 * sit for a fortnight and a society can stop taking M-Pesa in that time.
	 *
	 * Empty is a real state and not a failure: a free membership asks nothing, a
	 * society with no gateways configured offers nothing, and both mean the fee —
	 * if there is one — goes through whatever the payments app has active, which
	 * is what happened before anybody was asked.
	 */
	const [paymentMethod, setPaymentMethod] = useState("");

	/**
	 * Whether this person has a disability, and what would help.
	 *
	 * On the Red Profile like the name and the date of birth, and asked of a
	 * volunteer only: the society has to know what adjustments to make before it
	 * sends somebody anywhere, and a membership does not turn on it.
	 *
	 * **Answering is required; disclosing is not.** "Prefer not to say" is one of
	 * the three answers and it satisfies the step — the same rule
	 * `application._assert_disability_answered` applies on the server. The free
	 * text beside it is optional whatever was answered: a form that demanded a
	 * description would punish the disclosure it just asked for.
	 */
	const [disability, setDisability] = useState("");
	const [disabilityNeeds, setDisabilityNeeds] = useState("");

	// --- nationality, which the identity step asks
	const [citizenship, setCitizenship] = useState("");
	// The yes/no half of the citizenship question, which the country alone cannot
	// carry: "not a citizen, and has not said of where yet" and "has not been
	// asked" are both an empty country, and only one of them should be drawing a
	// picker. It lives here rather than in the step because the step is remounted
	// on every visit — see the `key={step.id}` the entrance animation needs — and
	// an answer that disappeared on the way back from the next screen would be
	// worse than the picker it replaced. Starts at yes, which is what the
	// society's own default already assumes.
	const [isCitizen, setIsCitizen] = useState(true);

	// --- identification
	//
	// A list, because `Red Profile` has always held one and a society can insist
	// on two: a national card *and* a driving licence is a real requirement, and
	// a form that took a single pair could not satisfy it. One blank row to
	// begin with, so the step opens as a form rather than as an empty state with
	// a button on it.
	const [identifications, setIdentifications] = useState<Identification[]>(() => [
		blankIdentification(),
	]);

	// --- who to call, and — for a minor — who says they may volunteer
	//
	// Contacts are a list for the same reason documents are: `VMMS Emergency
	// Contact` is a table, a household has more than one number worth holding,
	// and the branch that has to reach somebody at three in the morning should
	// not be down to whichever one fitted on the form. The guardian stays
	// singular — a consent is given by one person, and a second would be a
	// second answer to whether a minor may volunteer.
	const [contacts, setContacts] = useState<EmergencyContact[]>(() => [blankContact()]);
	const [guardian, setGuardian] = useState<GuardianConsent>(() => blankGuardian());

	// Keys of the declarations ticked so far. A set rather than a per-declaration
	// boolean, so a society adding a fifth needs no new state container.
	const [accepted, setAccepted] = useState<string[]>([]);

	// --- the declaration
	const [skills, setSkills] = useState<string[]>([]);
	const [languages, setLanguages] = useState<string[]>([]);
	const [availability, setAvailability] = useState<string[]>([]);
	const [motivations, setMotivations] = useState<string[]>([]);
	const [experience, setExperience] = useState("");

	/**
	 * The society's own answers, keyed by the opaque question name.
	 *
	 * Every value is a string, including a tick ("1" / "0") and an uploaded
	 * file (its URL), because that is exactly what `VMMS Application Answer`
	 * stores and what `questions.apply` re-checks on arrival. One shape here
	 * means the step below can draw a question type it has never seen without a
	 * second state container to keep in step.
	 */
	const [answers, setAnswers] = useState<Record<string, string>>({});

	const [busy, setBusy] = useState(false);
	const [busyAction, setBusyAction] = useState<"save" | "submit" | null>(null);
	const [failure, setFailure] = useState<string | null>(null);
	const [done, setDone] = useState(false);
	// What the gateway said when the fee was requested, if one was. Held so the
	// success screen can repeat it; nothing in this file reads inside it.
	const [payment, setPayment] = useState<PaymentAsked | null>(null);
	const [saved, setSaved] = useState<string | null>(null);

	// What core already knows, so the identity step prefills rather than asking a
	// returning person who they are for a second time.
	const existing = useFrappeGetCall<{ message: RedProfile | null }>(
		API.myProfile,
		undefined,
		isGuest ? null : "join:my_profile",
	);

	// Has this person already applied and not been answered? Asked before a step
	// is drawn. Both registration endpoints refuse a second application anyway;
	// this is so nobody finds that out at the end of a form.
	//
	// **One answer per road, and only the road they are on can block them.** The
	// two registrations are independent — the server's refusal asks about one
	// doctype, so an undecided volunteer application has nothing to say about a
	// membership — and this screen used to read a single "is anything open"
	// answer, which turned somebody halfway through one registration away from
	// the other one entirely.
	const openRegistrations = useFrappeGetCall<{
		message: Record<Path, OpenRegistration | null>
	}>(API.myOpenRegistrations, undefined, isGuest ? null : "join:open_registrations");

	const other: Path = path === "volunteer" ? "member" : "volunteer";
	const openApplication = openRegistrations.data?.message?.[path] ?? null;
	const otherOpen = Boolean(openRegistrations.data?.message?.[other]);
	const resumable = openApplication?.state === "Draft";

	const draft = useFrappeGetCall<{ message: DraftRegistration | null }>(
		API.myRegistration,
		{ path },
		isGuest || !resumable ? null : `join:registration:${path}:${openApplication?.name}`,
	);

	const resumeNode = draft.data?.message?.geo_node ?? null;
	const resumeChain = useFrappeGetCall<{ message: { chain: GeoNode[] } }>(
		API.geoChain,
		resumeNode ? { node: resumeNode } : undefined,
		isGuest || !resumeNode ? null : `join:resume_path:${resumeNode}`,
	);

	const [restoredDraft, setRestoredDraft] = useState<string | null>(null);

	useEffect(() => {
		const remembered = draft.data?.message;
		if (!remembered || restoredDraft === remembered.name) return;

		setMembershipType((current) => remembered.membership_type ?? current);
		setPaymentMethod((current) => remembered.payment_method ?? current);
		setSkills(remembered.skills ?? []);
		setLanguages(remembered.languages ?? []);
		setAvailability(remembered.availability ?? []);
		setMotivations(remembered.motivation ?? []);
		setExperience(remembered.prior_experience ?? "");
		setAnswers(remembered.answers ?? {});
		setAccepted(remembered.declarations ?? []);
		// A draft with no contacts on it still gets one empty row to type into.
		setContacts(
			remembered.emergency_contacts?.length
				? remembered.emergency_contacts
				: [blankContact()],
		);
		setGuardian(remembered.guardian_consents?.[0] ?? blankGuardian());
		setRestoredDraft(remembered.name);
	}, [draft.data, restoredDraft]);

	useEffect(() => {
		const known = existing.data?.message;
		if (!known) return;

		setProfile(known);
		setFirstName(known.first_name ?? "");
		setLastName(known.last_name ?? "");
		setPhone(known.phone ?? "");
		setGender(known.gender ?? "");
		setDateOfBirth(known.date_of_birth ?? "");
		setPhoto(known.profile_photo ?? "");
		setCitizenship(known.country_of_citizenship ?? "");
		setDisability(known.disability_status ?? "");
		setDisabilityNeeds(known.disability_needs ?? "");

		// Everything core already holds, primary first — `my_profile` orders it —
		// rather than only the main one. A returning applicant who produced two
		// documents last time sees both, and correcting one does not silently
		// drop the other.
		setIdentifications(
			known.identifications?.length
				? known.identifications.map((row) => ({
						id_type: row.id_type,
						id_number: row.id_number,
					}))
				: [blankIdentification()],
		);
	}, [existing.data]);

	const identityOptions = useFrappeGetCall<{ message: IdentityOptions }>(
		API.identityOptions,
		undefined,
		isGuest ? null : "join:identity_options",
	);

	// The volunteer vocabularies. Not fetched on the member path, which asks for
	// none of them.
	const applicationOptions = useFrappeGetCall<{ message: ApplicationOptions }>(
		API.applicationOptions,
		undefined,
		isGuest || path !== "volunteer" ? null : "join:application_options",
	);

	// ACC-03, and each path has its own answer. Both endpoints intersect the two
	// configuration surfaces that will judge the anchor, so a level offered here
	// is one both of them accept. Asking the wrong path's endpoint would be a
	// picker enforcing somebody else's rule.
	const levels = useFrappeGetCall<{ message: { levels: string[]; unconstrained: boolean } }>(
		path === "member" ? API.memberGeoLevels : API.volunteerGeoLevels,
		undefined,
		isGuest ? null : `join:geo_levels:${path}`,
	);

	const types = useFrappeGetCall<{
		message: {
			types: PricedType[];
			questions: SocietyQuestion[];
			payment_methods: PaymentMethod[];
		};
	}>(
		API.membershipTypes,
		undefined,
		isGuest || path !== "member" ? null : "join:membership_types",
	);

	const options = applicationOptions.data?.message;
	const genders = identityOptions.data?.message?.genders ?? [];
	const priced = types.data?.message?.types ?? [];
	const memberQuestions = types.data?.message?.questions;
	const paymentMethods = types.data?.message?.payment_methods ?? [];
	const chosenType = priced.find((row) => row.membership_type === membershipType) ?? null;

	/**
	 * A `type` that names nothing puts the step back.
	 *
	 * The docname arrives in a URL, and a URL can be stale, hand-typed, or point
	 * at a membership the society has since retired. Skipping the step on the
	 * strength of it alone would strand somebody on a registration carrying a
	 * plan they can neither see nor change. Held until the types have actually
	 * loaded, because "not fetched yet" and "not offered" are both an empty list
	 * and only one of them should redraw the rail.
	 */
	useEffect(() => {
		if (!planPreselected || !types.data) return;
		if (!chosenType) setPlanPreselected(false);
	}, [planPreselected, types.data, chosenType]);

	// Citizenship starts where the society's own configuration says it starts —
	// the same society default the registration endpoint uses, shown on the form
	// instead of filled in silently afterwards.
	useEffect(() => {
		const suggested = options?.default_country_of_citizenship;
		const recorded = existing.data?.message?.country_of_citizenship;

		if (recorded && suggested) {
			setIsCitizen(recorded === suggested);
			return;
		}

		if (suggested && !citizenship) setCitizenship(suggested);
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [options?.default_country_of_citizenship, existing.data]);

	/**
	 * Answering "are you a citizen of X".
	 *
	 * Yes fills in the society's own country; no empties the field, so the step's
	 * completion rule — which has always required a country — stops somebody at
	 * the picker rather than letting the default travel under an answer that
	 * contradicts it.
	 */
	const answerCitizenship = (yes: boolean) => {
		setIsCitizen(yes);
		setCitizenship(yes ? (options?.default_country_of_citizenship ?? "") : "");
	};

	const allowedLevels =
		levels.data?.message && !levels.data.message.unconstrained
			? levels.data.message.levels
			: undefined;

	/**
	 * Opening the residence and placement steps with the recorded Home Area.
	 *
	 * A person who registered as a volunteer in March and comes back in August to
	 * take out a membership was being asked to walk the cascading picker back down
	 * to the area they already recorded as home — a question the society can
	 * answer from its own records. `Red Profile.home_geo_node` is where that
	 * person-owned residence answer lives and `my_profile` returns it here.
	 *
	 * **A suggestion, not a decision.** Every rung is drawn as normal and every one
	 * of them can be changed; this fills them in rather than locking them, and it
	 * runs once so somebody who deliberately picks a different branch does not have
	 * their answer put back by a revalidation.
	 */
	const recordedHome = existing.data?.message?.home_geo_node ?? null;

	const suggestion = useFrappeGetCall<{ message: { chain: GeoNode[] } }>(
		API.geoChain,
		recordedHome ? { node: recordedHome } : undefined,
		isGuest || !recordedHome ? null : `join:geo_path:${recordedHome}`,
	);

	const [prefilled, setPrefilled] = useState(false);

	useEffect(() => {
		// `levels` decides how much of the chain is usable, so prefilling before it
		// has answered could fill in a rung this path is not recorded at and then
		// have to take it away again.
		if (prefilled || !levels.data || resumable) return;

		const chain = suggestion.data?.message?.chain;
		if (!chain?.length) return;

		setServingChain(usableChain(chain, allowedLevels));
		setPrefilled(true);
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [suggestion.data, levels.data, prefilled, resumable]);

	useEffect(() => {
		if (!resumable || !levels.data) return;

		const chain = resumeChain.data?.message?.chain;
		if (!chain?.length) return;

		setServingChain(usableChain(chain, allowedLevels));
		setPrefilled(true);
	}, [resumeChain.data, levels.data, resumable, allowedLevels]);

	const node = selectedNode(servingChain, allowedLevels);

	/**
	 * Where this person lives, which this wizard no longer asks and still has to
	 * send: `assert_ready` wants one complete residence shape before it will
	 * accept a submission.
	 *
	 * **It fills in a blank; it never corrects an answer.** Somebody registering
	 * for the first time has nothing on their profile, and the truthful default
	 * for them is Local, at the branch they have just said they want to volunteer
	 * with — that is what the deleted screen's tickbox was preselected to anyway.
	 * Somebody who already has an answer recorded has it because a desk clerk or
	 * an earlier registration put it there, and a form that never asked the
	 * question has no business overwriting it:
	 *
	 * - **Abroad** carries a country and an address this form cannot supply, so
	 *   it sends neither field and leaves the pair intact.
	 * - **A recorded home area** stands, even where it is not the branch being
	 *   applied to. People do volunteer away from home.
	 */
	const recordedResidency = existing.data?.message?.residency_type ?? "";

	const residence =
		recordedResidency === ABROAD
			? {}
			: {
					residency_type: recordedResidency || LOCAL,
					home_geo_node: recordedHome ?? node?.name,
				};

	/**
	 * The society's own questions for whichever registration this is.
	 *
	 * Two sources because the two wizards already load two different option
	 * calls, and adding a third round trip for a list that is usually empty
	 * would be a spinner for nothing. Neither endpoint knows what the questions
	 * are about; both just carry what `questions.asked_on` returned.
	 */
	const questions = useMemo(
		() => (path === "member" ? memberQuestions : options?.questions) ?? [],
		[path, memberQuestions, options?.questions],
	);

	// What this society asks people to agree to. Empty on the member path, which
	// has no declarations of its own yet, and empty on a site whose settings have
	// never been saved — in both cases the step is simply not drawn.
	const declarations = useMemo(
		() => (path === "volunteer" ? (options?.declarations ?? []) : []),
		[path, options?.declarations],
	);

	/**
	 * Is the person filling this in a minor, by this society's own reckoning?
	 *
	 * Derived from the date of birth on the form and the age the server served,
	 * so the guardian block appears while somebody is still typing rather than
	 * after a refused approval. **Both halves come from the server** — the
	 * threshold from `application_options.minor_age` and the rule itself from
	 * `application.is_minor` — so this is the same question asked in the same
	 * terms, not a second opinion. `null` means the society has not configured an
	 * age of majority, and nothing about guardians is ever shown.
	 */
	const minorAge = options?.minor_age ?? null;
	const isMinor = useMemo(() => {
		if (!minorAge || !dateOfBirth) return false;

		return ageOn(dateOfBirth) < minorAge;
	}, [minorAge, dateOfBirth]);

	/**
	 * Is there a fee to collect, and a choice to make about how?
	 *
	 * Both halves, and both are needed. A free membership has nothing to pay, so
	 * asking how would be a form collecting an answer nobody will use. A society
	 * with one way of paying has nothing to choose between, so the step would be
	 * a screen with a single option on it — the server falls back to that
	 * society's own first method anyway, which is the same answer without the
	 * page.
	 */
	const asksHowToPay = Boolean(chosenType && !chosenType.free && paymentMethods.length > 1);

	const steps = useMemo(
		() => stepsFor(path, declared, questions, declarations, planPreselected, asksHowToPay),
		[path, declared, questions, declarations, planPreselected, asksHowToPay],
	);

	// A tick that was never touched still has to be sent, because not sending it
	// is indistinguishable from not answering and a required one would be
	// refused. Seeded once the questions arrive, and never overwritten after.
	useEffect(() => {
		const ticks = questions.filter((question) => question.field_type === "Check");
		if (!ticks.length) return;

		setAnswers((current) => {
			const missing = ticks.filter((question) => current[question.name] === undefined);
			if (!missing.length) return current;

			const seeded = { ...current };
			for (const question of missing) seeded[question.name] = "0";
			return seeded;
		});
	}, [questions]);
	const step = steps[Math.min(cursor, steps.length - 1)];

	const complete = (id: StepId): boolean => {
		// Date of birth is required of a volunteer and not of a member, which is
		// the same split `application.assert_ready` makes on the server: age governs
		// what somebody may be sent to do and what safeguarding applies to them, and
		// that question is only asked of the people a society deploys. Asked here so
		// the button says so, rather than the submission failing six steps later.
		if (id === "identity")
			return Boolean(
				firstName.trim() &&
					lastName.trim() &&
					// Nationality joined this step when the citizenship screen was
					// dropped, and it is required of a volunteer for the same reason
					// `assert_ready` requires it: a country of citizenship, not a
					// screen, is what the society actually needs.
					(path !== "volunteer" || (dateOfBirth && citizenship && disability)),
			);
		if (id === "plan") return Boolean(membershipType);
		if (id === "payment") return Boolean(paymentMethod);
		if (id === "placement") return Boolean(node);
		// One complete document at least, nothing half-filled, and no kind listed
		// twice — which is exactly what the server will accept.
		if (id === "identification")
			return (
				identifications.some(identificationIsUsable) &&
				identifications.every(identificationIsCoherent) &&
				!repeatedIdentification(identifications)
			);

		// An emergency contact is a condition of *approval*, not of submission —
		// `assert_approvable`, not `assert_ready` — so this step can be walked
		// past. What it does insist on is that a half-filled contact is not sent:
		// a name with no number is not somebody anyone can call.
		//
		// The guardian block is the same bargain, and deliberately so. A minor
		// whose parent has not signed anything yet should be able to send the
		// application and let the branch chase the form.
		if (id === "emergency")
			return contacts.every(contactIsCoherent) && guardianIsCoherent(guardian);

		// Every required declaration, which is `declarations.assert_accepted`
		// asked here so the button says so rather than the submission failing.
		if (id === "consents") {
			return declarations
				.filter((row) => row.is_required)
				.every((row) => accepted.includes(row.name));
		}

		// The same rule `questions.assert_answered` applies server-side, asked
		// here so the button says so rather than the submission failing. A tick is
		// always answered — "no" is an answer — which is why it is not tested for
		// truth, only for presence.
		if (id === "questions") {
			return questions
				.filter((question) => question.is_required)
				.every((question) => Boolean(answers[question.name]));
		}

		// The last step gates on all the others, not on itself. Steps can be
		// jumped back to, so "I reached Submit" is not the same statement as
		// "everything behind me is answered" — and the difference is a request
		// the server would only refuse.
		if (id === "confirm") return steps.slice(0, -1).every((entry) => complete(entry.id));

		return true;
	};

	/**
	 * Switching path rewinds how far this wizard counts as having been walked.
	 *
	 * The two paths ask different questions, so answers given on one are not
	 * progress through the other. Without this, somebody who filled in five
	 * volunteer steps, went back and switched to Member could jump straight to
	 * Submit past a membership type they never chose.
	 */
	const choosePath = (next: Path) => {
		setPath(next);
		setFurthest(cursor);
	};

	/**
	 * Taking the other road, from the screen that says this one is closed.
	 *
	 * Back to the start of it rather than to wherever the blocked path had got
	 * to, because nothing on the road behind was walked: the wizard never drew a
	 * step. The URL follows so a refresh lands on the same road, and it is
	 * amended rather than replaced so a plan chosen on the way in survives.
	 */
	const switchPath = (next: Path) => {
		const url = new URLSearchParams(params);
		url.set("path", next);
		setParams(url, { replace: true });

		setPath(next);
		setCursor(0);
		setFurthest(0);
		setDirection("forward");
		window.scrollTo({ top: 0, behavior: "smooth" });
	};

	/**
	 * Declaring a path before authentication.
	 *
	 * A bare `/join` has no intent to preserve yet, so it asks this one question
	 * before sending a guest through Frappe. The answer goes into the URL before
	 * any hand-off: login, account creation and the password email can then all
	 * return to the same volunteer or member registration rather than to an
	 * ambiguous form.
	 */
	const declarePath = (next: Path) => {
		const url = new URLSearchParams(params);
		url.set("path", next);
		setParams(url, { replace: true });

		setPath(next);
		setDeclared(true);
	};

	/**
	 * Moving between steps, which is also when the draft is written.
	 *
	 * **Leaving a screen is the save.** There was a "Save draft" button and
	 * nothing else, so everything typed between one press and the next lived in
	 * a browser tab: a closed laptop, an expired session or a stray refresh took
	 * six screens of answers with it. Every step change now persists what has
	 * been answered so far, and the button remains for anybody who wants to press
	 * something before walking away.
	 *
	 * **It never blocks the move.** The step changes first and the write goes off
	 * on its own; a slow network must not make Continue feel broken, and a failed
	 * autosave must not strand somebody on a screen they have finished. The
	 * button is still there and still reports properly if it fails.
	 *
	 * **Backwards counts too.** Going back to correct an answer and then leaving
	 * is exactly the case a save-on-forward-only rule would lose.
	 */
	const goTo = (index: number) => {
		const target = Math.max(0, Math.min(index, steps.length - 1));
		if (target !== cursor) void autosave();
		setDirection(target >= cursor ? "forward" : "back");
		setCursor(target);
		setFurthest((seen) => Math.max(seen, target));
		window.scrollTo({ top: 0, behavior: "smooth" });
	};

	const advance = () => {
		if (!complete(step.id)) return;
		if (step.id === "confirm") {
			void submit();
			return;
		}
		goTo(cursor + 1);
	};

	const identity = {
		first_name: firstName.trim(),
		last_name: lastName.trim(),
		phone: phone.trim(),
		gender,
		date_of_birth: dateOfBirth,
		profile_photo: photo,
	};

	const persistDraft = async (): Promise<void> => {
		const endpoint =
			path === "volunteer" ? API.saveMyVolunteerDraft : API.saveMyMemberDraft;
		const payload =
			path === "volunteer"
				? {
						...identity,
						geo_node: node?.name,
						country_of_citizenship: citizenship,
						disability_status: disability,
						// Sent as an empty string rather than omitted when it is
						// blank, so clearing a description somebody no longer wants
						// on file actually clears it. `None` means "leave alone" on
						// the server; "" means "cleared".
						disability_needs: disabilityNeeds,
						// Not collected on any screen — derived, or left alone. See
						// `residence`.
						...residence,
						// The whole set, not the first of it. Half-filled rows are
						// dropped rather than sent: the server refuses a document
						// with a type and no number, and a spare row at the bottom
						// of a form is a browser artefact rather than an answer.
						identifications: identifications.filter(identificationIsUsable),
						skills,
						languages,
						availability,
						motivation: motivations,
						prior_experience: experience,
						answers,
						declarations_accepted: accepted,
						// Every contact somebody actually filled in. Half-filled
						// rows are dropped rather than stored, because the server
						// counts contacts and a nameless one would count.
						emergency_contacts: contacts.filter(contactIsUsable),
						// Only ever sent for a minor. An applicant who turns out to
						// be an adult must not leave a guardian record behind them,
						// and one who was a minor when they started the form and is
						// not now has no guardian rule to satisfy.
						guardian_consents: isMinor && guardianIsUsable(guardian) ? [guardian] : [],
					}
				: {
						...identity,
						membership_type: membershipType,
						geo_node: node?.name,
						// Always sent, including empty — the server reads `null` as
						// "leave the draft alone" and "" as a choice not yet made,
						// and a form that omitted it could never clear one.
						payment_method: paymentMethod,
						answers,
					};

		await call.post<{ message: DraftRegistration }>(endpoint, payload);
		void existing.mutate();
	};

	/**
	 * One write at a time, whoever asked for it.
	 *
	 * The first save is an insert and every save after it is an update of the
	 * row that insert created — the server finds the caller's open draft and
	 * writes into it. Two writes in flight together would both find no draft and
	 * both insert one, and the second registration would then be refused as a
	 * duplicate of the first. Autosave fires on a keystroke's worth of notice, so
	 * that race is not theoretical: the writes are chained through this instead.
	 */
	const inFlight = useRef<Promise<unknown>>(Promise.resolve());

	const enqueue = <T,>(work: () => Promise<T>): Promise<T> => {
		// Both arms, so one failed save does not strand every write behind it.
		const next = inFlight.current.then(
			() => work(),
			() => work(),
		);

		inFlight.current = next.catch(() => undefined);

		return next;
	};

	/**
	 * The quiet save, on leaving a step.
	 *
	 * Silent, including about having worked. A tick reading "Draft saved" on
	 * every step change is the form reporting on itself: nobody asked for the
	 * save, so nobody is waiting to hear that it happened, and the answers being
	 * there on the next visit is the only proof of it anybody needs. It also does
	 * not take the busy flag, because that disables the buttons and a person
	 * moving between screens has not asked to be stopped; it does not raise a
	 * failure, because the screen it would appear on is one they have already
	 * left; and it does nothing at all until there is enough answered to make a
	 * draft, which is a name and a branch.
	 */
	const autosave = async () => {
		if (!canSaveDraft || busy) return;

		try {
			await enqueue(persistDraft);
		} catch {
			// The button is still there, and it says so properly when pressed.
		}
	};

	const saveDraft = async () => {
		setBusy(true);
		setBusyAction("save");
		setFailure(null);
		setSaved(null);

		try {
			await enqueue(persistDraft);
			// Not the document name. "Draft VAPP-00017 saved. You can sign out and
			// continue later." told a member of the public a naming series they
			// will never type, and offered them a workflow — sign out, come back —
			// that nobody chooses. Their draft is on the dashboard when they
			// return, which is where they would look anyway.
			setSaved("Draft saved");
		} catch (saveError) {
			setFailure(errorMessage(saveError, "Your draft could not be saved."));
		} finally {
			setBusy(false);
			setBusyAction(null);
		}
	};

	const submit = async () => {
		setBusy(true);
		setBusyAction("submit");
		setFailure(null);
		setSaved(null);

		try {
			await enqueue(persistDraft);
			const answer = await call.post<{ message?: { payment?: PaymentAsked } }>(
				API.submitMyRegistration,
				{ path },
			);
			setPayment(answer?.message?.payment ?? null);
			setDone(true);
		} catch (submitError) {
			setFailure(errorMessage(submitError, "Your registration was not accepted."));
		} finally {
			setBusy(false);
			setBusyAction(null);
		}
	};

	// "Draft saved" reports that something happened, not something that is true
	// from now on, so it leaves of its own accord rather than sitting under the
	// form for the rest of the registration.
	useEffect(() => {
		if (!saved) return;

		const timer = window.setTimeout(() => setSaved(null), 4000);
		return () => window.clearTimeout(timer);
	}, [saved]);

	/**
	 * What the rail says about identification, in one line.
	 *
	 * The society's own word for the document rather than its docname, and a
	 * count when there is more than one — "National ID +1" is what somebody
	 * scanning a rail can read, and the full list is on the last step.
	 */
	const usableIdentifications = identifications.filter(identificationIsUsable);
	const identificationSummary =
		usableIdentifications.length === 0
			? null
			: [
					options?.id_types.find((row) => row.key === usableIdentifications[0].id_type)?.label ??
						usableIdentifications[0].id_type,
					usableIdentifications.length > 1 ? `+${usableIdentifications.length - 1}` : "",
				]
					.filter(Boolean)
					.join(" ");

	const ready = complete(step.id);
	const canSaveDraft = Boolean(
		firstName.trim() &&
			lastName.trim() &&
			node &&
			(path !== "member" || membershipType) &&
			(path !== "volunteer" || identifications.every(identificationIsCoherent)),
	);

	return (
		<div className="min-h-screen bg-canvas">
			{/* The concept's own top bar: the society's navy, edge to edge, with the
			    journey named beside the mark and one way out of it. A registration
			    is not a page of the site with a header on it — it is a room you are
			    in — and the dark bar is what says so. */}
			<header className="sticky top-0 z-30 flex h-[72px] items-center border-b border-white/[0.13] bg-rail px-5 sm:px-[34px]">
				<Link to="/" className="min-w-0">
					<BrandLockup tone="dark" />
				</Link>

				{!isGuest && (
					<p className="ml-[30px] hidden border-l border-white/[0.22] pl-[30px] text-[12px] text-white/[0.58] sm:block">
						{path === "member" ? "Membership registration" : "Volunteer registration"}
					</p>
				)}

				{/* Never `/` for somebody signed in — that is the public landing page,
				    and leaving a half-finished application through it reads as having
				    been signed out. A guest has no portal to be sent back to. */}
				<Link
					to={isGuest ? "/" : "/dashboard"}
					className="ml-auto flex-none rounded-full border border-white/30 px-3.5 py-[9px] text-[11px] font-bold text-white transition hover:bg-white/10"
				>
					{isGuest ? "Back to site" : "Save & exit"}
				</Link>
			</header>

			<div className="mx-auto w-[min(1180px,calc(100%-28px))] py-7 sm:w-[min(1180px,calc(100%-48px))] lg:pb-[70px] lg:pt-[34px]">
				{sessionLoading && <Spinner label="Checking your session…" />}

				{!sessionLoading && isGuest && (
					<div className="mx-auto max-w-2xl">
						{declared ? (
							<SignInFirst path={path} />
						) : (
							<ChoosePathFirst onChoose={declarePath} />
						)}
					</div>
				)}

				{!sessionLoading && !isGuest && done && (
					<div className="mx-auto max-w-2xl">
						<Success path={path} payment={payment} />
					</div>
				)}

				{/* Already applied *for this*, and it has not been decided. The server
				    refuses a second one either way — `registration._assert_nothing_open`
				    before the insert and `engine.assert_single_open` at submission —
				    so this is not the check. It is the difference between finding that
				    out on the last step of a wizard you filled in twice, and being
				    told on the first. `openApplication` is the open registration of
				    *this path's* kind, so the other road stays open, which is what the
				    two server checks have always said. */}
				{!sessionLoading && !isGuest && !done && resumable && draft.isLoading && (
					<Spinner label="Loading your saved draft…" />
				)}

				{!sessionLoading && !isGuest && !done && openApplication && !resumable && (
					<div className="mx-auto max-w-2xl">
						<AlreadyApplied
							// The entry *is* this path's entry — it was read out of the
							// answer by it — so the wizard's own is the narrower spelling.
							path={path}
							state={openApplication.state}
							otherOpen={otherOpen}
							onSwitch={() => switchPath(other)}
						/>
					</div>
				)}

				{!sessionLoading &&
					!isGuest &&
					!done &&
					(!openApplication || resumable) &&
					!draft.isLoading && (
					<div className="grid gap-6 lg:grid-cols-[270px_minmax(0,1fr)] lg:gap-[26px]">
						{resumable && openApplication?.reason && (
							<div className="lg:col-span-2">
								<DraftNotice reason={openApplication.reason} />
							</div>
						)}
						<Rail
							steps={steps}
							cursor={cursor}
							furthest={furthest}
							onJump={goTo}
							summary={
								<Summary
									path={path}
									name={`${firstName} ${lastName}`.trim()}
									node={node}
									type={chosenType}
									citizenship={citizenship}
									idType={identificationSummary}
									chips={skills.length + languages.length + availability.length + motivations.length}
								/>
							}
						/>

						<div className="min-w-0">
							<form
								onSubmit={(event) => {
									event.preventDefault();
									advance();
								}}
							>
								{/* Keyed on the step so React remounts it, which is what
								    replays the entrance animation. */}
								<div
									key={step.id}
									className={cx(
										"overflow-hidden rounded-2xl border border-card-line bg-white shadow-[0_9px_26px_rgba(1,30,65,0.035)]",
										direction === "forward" ? "step-forward" : "step-back",
									)}
								>
									{/* The concept's step head: where you are, how much is
									    left, and a bar that shows it. The count and the bar
									    say the same thing twice on purpose — one of them is
									    readable, the other is glanceable. */}
									<header className="border-b border-card-line px-6 pb-6 pt-7 sm:px-9 sm:pb-[25px] sm:pt-[30px]">
										<div className="mb-3.5 flex items-center justify-between gap-5 text-[10px] font-bold uppercase tracking-[0.1em] text-slate-body">
											<span>
												Step {cursor + 1} of {steps.length}
											</span>
											<strong className="text-blue">
												{Math.round(((cursor + 1) / steps.length) * 100)}% complete
												{steps.length - cursor - 1 > 0 &&
													` · ${steps.length - cursor - 1} ${
														steps.length - cursor - 1 === 1 ? "step" : "steps"
													} left`}
											</strong>
										</div>

										<div className="mb-[22px] h-[5px] overflow-hidden rounded-full bg-[#E7ECF2]">
											<div
												className="h-full rounded-full bg-gradient-to-r from-blue to-[#49A7DD] transition-[width] duration-500 ease-out"
												style={{ width: `${((cursor + 1) / steps.length) * 100}%` }}
											/>
										</div>

										<h1 className="font-display text-[26px] font-bold leading-[1.2] tracking-[-0.035em] text-ink sm:text-[30px]">
											{step.title}
										</h1>

										{step.blurb && (
											<p className="mt-2.5 max-w-[650px] text-[13px] leading-[1.55] text-slate-body">
												{step.blurb}
											</p>
										)}
										{/* The choice the path step would have asked, kept
										    reversible without a screen of its own. Drawn only on
										    the first step, and only when the answer arrived with
										    the person: further in, they have answered questions
										    that belong to this path and switching would discard
										    them, which is what the rail's own back-navigation is
										    for. */}
										{declared && cursor === 0 && (
											<PathSwitch path={path} onChange={choosePath} />
										)}
									</header>

									<div className="px-6 py-7 sm:px-9 sm:py-8">
										{step.id === "path" && <PathStep path={path} onChange={choosePath} />}

										{step.id === "identity" && (
											<IdentityStep
												profile={profile}
												genders={genders}
												path={path}
												options={options}
												citizenship={citizenship}
												onCitizenship={setCitizenship}
												isCitizen={isCitizen}
												onIsCitizen={answerCitizenship}
												firstName={firstName}
												lastName={lastName}
												phone={phone}
												gender={gender}
												dateOfBirth={dateOfBirth}
												photo={photo}
												onFirstName={setFirstName}
												onLastName={setLastName}
												onPhone={setPhone}
												onGender={setGender}
												onDateOfBirth={setDateOfBirth}
												onPhoto={setPhoto}
												disability={disability}
												onDisability={setDisability}
												disabilityNeeds={disabilityNeeds}
												onDisabilityNeeds={setDisabilityNeeds}
											/>
										)}

										{step.id === "plan" && (
											<PlanCards
												types={priced}
												loading={types.isLoading}
												selected={membershipType}
												onSelect={setMembershipType}
												columns={2}
											/>
										)}

										{step.id === "payment" && (
											<PaymentStep
												methods={paymentMethods}
												selected={paymentMethod}
												onSelect={setPaymentMethod}
												type={chosenType}
											/>
										)}

										{step.id === "placement" && (
											<PlacementStep
												path={path}
												chain={servingChain}
												onChain={setServingChain}
												allowedLevels={allowedLevels}
											/>
										)}

										{step.id === "identification" && (
											<IdentificationStep
												options={options}
												loading={applicationOptions.isLoading}
												rows={identifications}
												onRows={setIdentifications}
											/>
										)}

										{step.id === "declaration" && (
											<DeclarationStep
												options={options}
												loading={applicationOptions.isLoading}
												skills={skills}
												onSkills={setSkills}
												languages={languages}
												onLanguages={setLanguages}
												availability={availability}
												onAvailability={setAvailability}
												motivations={motivations}
												onMotivations={setMotivations}
												experience={experience}
												onExperience={setExperience}
											/>
										)}

										{step.id === "emergency" && (
											<EmergencyStep
												contacts={contacts}
												onContacts={setContacts}
												isMinor={isMinor}
												minorAge={minorAge}
												guardian={guardian}
												onGuardian={setGuardian}
											/>
										)}

										{step.id === "questions" && (
											<QuestionsStep
												questions={questions}
												answers={answers}
												onAnswer={(question, value) =>
													setAnswers((current) => ({ ...current, [question]: value }))
												}
											/>
										)}

										{step.id === "consents" && (
											<ConsentsStep
												declarations={declarations}
												accepted={accepted}
												onToggle={(name, yes) =>
													setAccepted((current) =>
														yes
															? current.includes(name)
																? current
																: [...current, name]
															: current.filter((key) => key !== name),
													)
												}
											/>
										)}

										{step.id === "confirm" && (
											<ConfirmStep
												path={path}
												steps={steps}
												onEdit={goTo}
												name={`${firstName} ${lastName}`.trim()}
												email={profile?.email ?? null}
												phone={phone}
												gender={gender}
												dateOfBirth={dateOfBirth}
												photo={photo}
												node={node}
												chain={servingChain}
												type={chosenType}
												citizenship={citizenship}
												disability={disability}
												paymentLabel={
													paymentMethods.find((row) => row.gateway === paymentMethod)?.label ??
													null
												}
												identifications={usableIdentifications.map((row) => ({
													label:
														options?.id_types.find((entry) => entry.key === row.id_type)
															?.label ?? row.id_type,
													number: row.id_number,
												}))}
												declared={{
													skills: labelsFor(options?.skills, skills),
													languages: labelsFor(options?.languages, languages),
													availability: labelsFor(options?.availability, availability),
													motivations: labelsFor(options?.motivations, motivations),
												}}
												experience={experience}
												societyAnswers={questions
													.filter((question) => answers[question.name])
													.map((question) => ({
														label: question.label,
														// A tick reads as a word, a file as the fact that one
														// arrived. Neither is useful to a person as "1" or as a
														// path into the site's private files.
														shown:
															question.field_type === "Check"
																? answers[question.name] === "1"
																	? "Yes"
																	: "No"
																: question.field_type === "Attach"
																	? "File attached"
																	: answers[question.name],
													}))}
												contacts={contacts.filter(contactIsUsable)}
												isMinor={isMinor}
												guardian={guardian}
												consents={declarations.map((declaration) => ({
													name: declaration.name,
													title: declaration.title,
													version: declaration.version,
													accepted: accepted.includes(declaration.name),
												}))}
											/>
										)}

										{failure && (
											<div className="mt-6">
												<ErrorNote>{failure}</ErrorNote>
											</div>
										)}
									</div>

									{/* The concept's action bar: a tinted foot to the card
									    rather than a rule across it, so the controls read as
									    belonging to the whole step and not to the last field
									    above them. */}
									<div className="flex flex-wrap items-center gap-3 border-t border-card-line bg-[#FBFCFD] px-6 py-5 sm:px-9">
										{/* Only ever an answer to the button beside it. The
										    autosave is silent — see `autosave` — so this is
										    shown to somebody who pressed something and is
										    waiting to hear, never on a step change. */}
										<span className="order-last w-full text-[11px] text-slate-faint sm:order-none sm:mr-auto sm:w-auto">
											{saved && !busy ? (
												<span className="flex items-center gap-1.5 font-semibold text-success">
													<Icon.check size={13} />
													{saved}
												</span>
											) : !ready && step.needs ? (
												step.needs
											) : (
												"Your draft is saved whenever you continue."
											)}
										</span>

										<Button
											type="button"
											variant="ghost"
											onClick={() => void saveDraft()}
											disabled={!canSaveDraft || busy}
										>
											{busyAction === "save" ? "Saving…" : "Save draft"}
										</Button>

										<Button
											variant="quiet"
											onClick={() => goTo(cursor - 1)}
											disabled={cursor === 0 || busy}
										>
											<span aria-hidden="true">←</span> Back
										</Button>

										<Button
											type="submit"
											variant="primary"
											disabled={!ready || busy}
										>
											{step.id === "confirm" ? (
												busyAction === "submit" ? (
													"Submitting…"
												) : (
													"Submit registration"
												)
											) : (
												<>
													Continue <span aria-hidden="true">→</span>
												</>
											)}
										</Button>
									</div>
								</div>
							</form>
						</div>
					</div>
				)}
			</div>
		</div>
	);
}

/* ------------------------------------------------------------- step tables */

interface StepDef {
	id: StepId;
	rail: string;
	eyebrow: string;
	/**
	 * The whole of what a step says for itself.
	 *
	 * There was a line of explanation under it — "Answer each field in turn, the
	 * one below narrows to what sits inside your answer" — and every one of them
	 * was the page describing the controls already on it, in a voice nobody uses.
	 * A screen headed "Where would you volunteer?" above three selects has said
	 * everything it has to say. What a field genuinely needs explaining goes on
	 * the field, as its hint.
	 */
	title: string;
	/**
	 * One line under the title, and only where it carries a fact the controls
	 * do not. Not a description of the screen — see the note on `title` — but
	 * the thing a person would otherwise have to ask: who reads this, what is
	 * already known about them, whether an answer can still be changed.
	 */
	blurb: string;
	/** Shown beside a disabled Continue, so "why can't I go on" is answered. */
	needs: string;
}

/**
 * Which steps a path walks.
 *
 * The two paths genuinely differ — a member is not asked for citizenship,
 * identification or a volunteering declaration, and a volunteer chooses no plan
 * — and the desk's two Web Forms differ in exactly the same way. Composing the
 * list here keeps that difference in one readable place instead of a conditional
 * on every screen.
 *
 * **`asked` is whether the person has already answered "which of these am I".**
 * Somebody who pressed "Become a volunteer" has answered it, and showing them a
 * screen that asks again — with their answer preselected, so the only move is to
 * press Continue — is a step that exists to be dismissed. It also reads as
 * though the button they pressed did not register. So the step is dropped, and
 * the choice stays reversible through the line on the step that follows rather
 * than through a rung of the ladder. Somebody who arrived at `/join` with
 * nothing declared genuinely has not answered, and for them it is the first
 * question.
 *
 * The eyebrow is derived rather than written, because a step's number is a
 * property of the list it is in: moving one used to mean renumbering the rest by
 * hand, and the first time that was missed the page said "Step four" twice.
 * Dropping the first step renumbers the rest for the same reason, with no
 * arithmetic anywhere.
 */
function stepsFor(
	path: Path,
	asked: boolean,
	questions: SocietyQuestion[],
	declarations: Declaration[],
	planChosen: boolean = false,
	asksHowToPay: boolean = false,
): StepDef[] {
	const shared: Record<"path" | "identity" | "questions" | "consents" | "confirm", StepDef> = {
		path: {
			id: "path",
			rail: "Your path",
			eyebrow: "Registration",
			title: "What are you here to do?",
			blurb: "Both start the same way, and you can change your mind on the next step.",
			needs: "",
		},
		identity: {
			id: "identity",
			rail: "About you",
			eyebrow: "",
			title: "About you",
			blurb:
				"What your account already knows is filled in. Correct anything that has changed.",
			needs: "A first and last name are needed",
		},
		/**
		 * The society's own step, and the only one whose *content* is not in this
		 * file. Everything on it comes from `VMMS Application Question`, so a
		 * branch that starts asking for a letter from the area chief gets a step
		 * here with no deploy. Drawn only when there is something to ask: a
		 * society with no questions never sees an empty page between the last
		 * answer and Submit.
		 */
		questions: {
			id: "questions",
			rail: "Their questions",
			eyebrow: "",
			title: "What your society asks",
			blurb: "Questions this society asks every applicant, set by its own branches.",
			needs: "Answer everything marked required",
		},
		/**
		 * What the applicant agrees to, drawn from `VMMS Declaration` and not
		 * written in this file. Placed immediately before Submit on purpose: a
		 * consent read at the point of committing is a consent; the same words
		 * four screens earlier are something somebody clicked past.
		 *
		 * Volunteer-only for now, and drawn only where a society has declarations
		 * pointed at the registration being filled in.
		 */
		consents: {
			id: "consents",
			rail: "What you agree to",
			eyebrow: "",
			title: "Before you send this",
			blurb: "Read each one. What you accept is recorded against the version shown.",
			needs: "Accept everything marked required",
		},
		confirm: {
			id: "confirm",
			rail: "Check and submit",
			eyebrow: "Last step",
			title: "Check and submit",
			blurb: "Nothing is sent until you press submit. Anything here can still be changed.",
			needs: "",
		},
	};

	const steps: StepDef[] =
		path === "member"
			? [
					shared.path,
					shared.identity,
					{
						id: "plan",
						rail: "Your plan",
						eyebrow: "",
						title: "Choose your membership",
						blurb: "What you pay and what it covers. You can change this before you submit.",
						needs: "Choose a membership type",
					},
					{
						id: "payment",
						rail: "How you'll pay",
						eyebrow: "",
						title: "How would you like to pay?",
						blurb:
							"Nothing is taken now. We ask for the fee once your application has been sent.",
						needs: "Choose how you would like to pay",
					},
					{
						id: "placement",
						rail: "Your branch",
						eyebrow: "",
						title: "Which branch are you joining through?",
						blurb: "The branch you choose holds your membership and reviews this application.",
						needs: "Choose a branch",
					},
					shared.questions,
					shared.confirm,
				]
			: [
					shared.path,
					shared.identity,
					{
						id: "placement",
						rail: "Where you'd volunteer",
						eyebrow: "",
						title: "Where would you volunteer?",
						blurb: "Where you serve decides who reviews this and who you hear from.",
						needs: "Choose a branch or area",
					},
					{
						id: "identification",
						rail: "Identification",
						eyebrow: "",
						title: "Identification",
						blurb: "One government identification, so your branch can confirm who you are.",
						needs: "An ID type and number are needed",
					},
					{
						id: "declaration",
						rail: "Your volunteering",
						eyebrow: "",
						title: "About your volunteering",
						blurb: "What you can do and when. This is what your branch matches you against.",
						needs: "",
					},
					{
						id: "emergency",
						rail: "In an emergency",
						eyebrow: "",
						title: "If something happens",
						blurb: "Somebody we can reach while you are on duty. Only your branch sees this.",
						needs: "",
					},
					shared.questions,
					shared.consents,
					shared.confirm,
				];

	const ordinals = [
		"one",
		"two",
		"three",
		"four",
		"five",
		"six",
		"seven",
		"eight",
		"nine",
		"ten",
	];

	return steps
		.filter((entry) => entry.id !== "path" || !asked)
		// A plan chosen on the way in is a question already answered. See
		// `planPreselected`: asking it a second time, in a worse place than the
		// one it was answered in, is not a confirmation — it is a form doubting
		// somebody. What they picked is still on the last step to check.
		.filter((entry) => entry.id !== "plan" || !planChosen)
		// Nothing to pay, or nothing to choose between. See `asksHowToPay`: a
		// step offering one option is a screen that only slows somebody down,
		// and a free membership has no question here at all.
		.filter((entry) => entry.id !== "payment" || asksHowToPay)
		// A society that asks nothing extra gets no step for it, rather than an
		// empty page between the last answer and Submit.
		.filter((entry) => entry.id !== "questions" || questions.length > 0)
		// Same rule for the consents: a society with no declarations pointed at
		// this registration gets no page telling somebody there is nothing to
		// agree to.
		.filter((entry) => entry.id !== "consents" || declarations.length > 0)
		.map((entry, index) => ({
			...entry,
			eyebrow: entry.eyebrow || `Step ${ordinals[index] ?? index + 1}`,
		}));
}

/**
 * As much of a remembered placement as *this* path is allowed to record at.
 *
 * The two paths are not recorded at the same rung — ACC-03 is per doctype, which
 * is why the wizard asks two different endpoints for `allowedLevels` — so a
 * volunteer placed at a sub-branch may be joining as a member at the branch above
 * it. Handing the whole chain over would leave the picker showing an answer
 * `selectedNode` reads as nothing chosen, with the amber "keep going down" note
 * pointing *up* the ladder. Cut to the deepest rung this path accepts instead.
 *
 * A chain with no acceptable rung in it is passed through whole: the person is
 * placed higher than this path records at, and the remaining selects are where
 * they go from here.
 */
function usableChain(chain: GeoNode[], allowedLevels?: string[]): GeoNode[] {
	if (!allowedLevels?.length) return chain;

	const deepest = chain.reduce(
		(best, entry, index) => (allowedLevels.includes(entry.level) ? index : best),
		-1,
	);

	return deepest === -1 ? chain : chain.slice(0, deepest + 1);
}

function labelsFor(
	vocabulary: Array<{ key: string; label: string }> | undefined,
	chosen: string[],
): string[] {
	return chosen.map((key) => vocabulary?.find((row) => row.key === key)?.label ?? key);
}

/* -------------------------------------------------------------------- rail */

/**
 * The ladder down the side, as the approved concept draws it: a white card with
 * a navy head that counts the steps, numbered rungs inside it, and a way to ask
 * for help under the last one.
 *
 * The rungs are not the concept's plain anchors. A step already walked shows a
 * tick rather than its number, and a step not yet reached is not a link at all —
 * `furthest` is the wizard's own record of how far the answers go, and offering
 * somebody a jump to a screen whose prerequisites are blank is offering them a
 * dead end.
 */
function Rail({
	steps,
	cursor,
	furthest,
	onJump,
	summary,
}: {
	steps: StepDef[];
	cursor: number;
	furthest: number;
	onJump: (index: number) => void;
	summary: React.ReactNode;
}) {
	return (
		<div className="lg:sticky lg:top-[92px] lg:self-start">
			{/* Small screens get a bar and a count; an eight-rung ladder down the
			    side of a phone would push the form itself below the fold. */}
			<div className="lg:hidden">
				<div className="flex items-baseline justify-between">
					<span className="text-[13px] font-bold text-ink">{steps[cursor]?.rail}</span>
					<span className="text-[11.5px] text-slate-faint">
						{cursor + 1} / {steps.length}
					</span>
				</div>
				<div className="mt-2 h-1 overflow-hidden rounded-full bg-card-line">
					<div
						className="h-full rounded-full bg-blue transition-[width] duration-500 ease-out"
						style={{ width: `${((cursor + 1) / steps.length) * 100}%` }}
					/>
				</div>
			</div>

			<aside className="hidden overflow-hidden rounded-2xl border border-card-line bg-white lg:block">
				<div className="bg-rail-soft px-[23px] py-[22px]">
					<p className="text-[9px] font-extrabold uppercase tracking-[0.15em] text-aqua">
						Your application
					</p>
					<h2 className="mt-1.5 font-display text-[17px] font-bold leading-tight text-white">
						{steps.length} short steps
					</h2>
					<span className="mt-2 block text-[10px] leading-[1.45] text-white/60">
						Your draft is saved whenever you move to another step.
					</span>
				</div>

				<nav aria-label="Application progress" className="grid p-2.5">
					{steps.map((entry, index) => {
						const isDone = index < cursor;
						const isNow = index === cursor;
						const reachable = index <= furthest;

						return (
							<button
								key={entry.id}
								type="button"
								disabled={!reachable}
								onClick={() => onJump(index)}
								aria-current={isNow ? "step" : undefined}
								className={cx(
									"grid min-h-[49px] grid-cols-[27px_minmax(0,1fr)] items-center gap-2.5 rounded-[9px] px-[9px] py-1.5 text-left text-[11.5px] font-semibold transition",
									isNow
										? "bg-blue-soft text-ink"
										: reachable
											? "text-slate-body hover:bg-blue-soft/60 hover:text-ink"
											: "cursor-default text-slate-faint",
								)}
							>
								<span
									className={cx(
										"grid h-[25px] w-[25px] place-items-center rounded-full text-[9.5px] font-bold transition",
										isNow
											? "bg-rail text-white"
											: isDone
												? "bg-rail/85 text-white"
												: "bg-[#EEF2F6] text-slate-faint",
									)}
								>
									{isDone ? <Tick className="text-white" size={11} /> : index + 1}
								</span>
								<span className="truncate">{entry.rail}</span>
							</button>
						);
					})}
				</nav>

				<div className="mx-[18px] mb-5 border-t border-card-line pt-4">
					{summary}

					<p className="mt-4 border-t border-card-line pt-3.5 text-[10.5px] leading-[1.5] text-slate-body">
						Stuck on something?{" "}
						<Link to="/locations" className="font-bold text-blue hover:underline">
							Contact your branch →
						</Link>
					</p>
				</div>
			</aside>
		</div>
	);
}

/** What the wizard has collected so far, kept in view while it is collected. */
function Summary({
	path,
	name,
	node,
	type,
	citizenship,
	idType,
	chips,
}: {
	path: Path;
	name: string;
	node: GeoNode | null;
	type: PricedType | null;
	citizenship: string;
	idType: string | null;
	chips: number;
}) {
	const rows: Array<[string, string | null]> = [
		["Registering as", path === "volunteer" ? "Volunteer" : "Member"],
		["Name", name || null],
	];

	if (path === "member") {
		rows.push(["Membership", type?.membership_type_name ?? null]);
		rows.push(["Branch", node?.label ?? null]);
	} else {
		rows.push(["Branch", node?.label ?? null]);
		rows.push(["Nationality", citizenship || null]);
		rows.push(["Identification", idType]);
		rows.push(["Declared", chips > 0 ? `${chips} selected` : null]);
	}

	return (
		<div>
			<p className="mb-3 text-[10px] font-bold uppercase tracking-wider text-slate-faint">
				So far
			</p>
			<dl className="space-y-2.5">
				{rows.map(([label, value]) => (
					<div key={label} className="rise-in">
						<dt className="text-[10.5px] uppercase tracking-wide text-slate-faint">{label}</dt>
						<dd
							className={cx(
								"truncate text-[12.5px]",
								value ? "font-semibold text-ink" : "text-slate-faint",
							)}
							title={value ?? undefined}
						>
							{value ?? "—"}
						</dd>
					</div>
				))}
			</dl>
		</div>
	);
}

/* ------------------------------------------------------------------- steps */

/**
 * The only question a bare guest entry needs before authentication.
 *
 * The cards advance immediately because neither answer needs a separate
 * confirmation button. A declared landing-page CTA skips this screen entirely.
 */
function ChoosePathFirst({ onChoose }: { onChoose: (path: Path) => void }) {
	return (
		<Card className="p-7 sm:p-9">
			<p className="eyebrow">Registration</p>
			<h1 className="mt-2 text-[26px] font-semibold leading-tight tracking-tight text-ink">
				How would you like to join?
			</h1>
			<p className="mt-3 max-w-lg text-[13.5px] leading-relaxed text-muted">
				Choose a path first. We will keep your choice through account creation and bring you back
				to the right registration.
			</p>

			<div
				className="mt-7 grid gap-3 sm:grid-cols-2"
				role="radiogroup"
				aria-label="How would you like to join?"
			>
				<ChoiceCard
					selected={false}
					onSelect={() => onChoose("volunteer")}
					icon={<Icon.people size={20} />}
					title="Volunteer"
					body="Give time and skills. Your branch verifies your record before you can take part in volunteer work."
				/>
				<ChoiceCard
					selected={false}
					onSelect={() => onChoose("member")}
					icon={<Icon.card size={20} />}
					title="Member"
					body="Join the Society formally. Membership carries a place on the register and may carry a fee."
				/>
			</div>
		</Card>
	);
}

function SignInFirst({ path }: { path: Path }) {
	const volunteering = path === "volunteer";
	const registration = volunteering ? "Volunteer registration" : "Member registration";

	return (
		<Card className="p-7 sm:p-9">
			<p className="eyebrow">{registration}</p>
			<nav className="mt-3" aria-label={`${registration} progress`}>
				<ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11.5px] text-slate-faint">
					<li className="font-bold text-ink" aria-current="step">
						Account
					</li>
					<li aria-hidden="true">→</li>
					<li>Your details</li>
					<li aria-hidden="true">→</li>
					<li>Branch review</li>
				</ol>
			</nav>

			<div className="mb-4 mt-7 grid h-11 w-11 place-items-center rounded-xl bg-rail/5 text-ink">
				<Icon.user size={21} />
			</div>
			<h1 className="text-[24px] font-semibold tracking-tight text-ink">
				Sign in to continue
			</h1>
			<p className="mt-2.5 max-w-lg text-[13.5px] leading-relaxed text-muted">
				You chose to register as {volunteering ? "a volunteer" : "a member"}. Sign in and you
				will come straight back to this registration.
			</p>
			{/* Said plainly, because it is the step people are surprised by. Creating
			    an account does not sign anybody in: Frappe mails a link to set a
			    password, and the account cannot be used until it is opened. A screen
			    that promised "you will come straight back here" and then sent
				    somebody to their inbox was the reason that felt like being thrown
				    out. `signupUrl` is what makes the sentence below true. */}
			<p className="mb-6 mt-3 max-w-lg text-[12.5px] leading-relaxed text-muted">
				New here? Creating an account sends you an email to set your password. Open that link and
				you will return to your {volunteering ? "volunteer" : "member"} registration.
			</p>
			<div className="flex flex-wrap gap-2.5">
				<a
					href={loginUrl(here())}
					className="inline-flex items-center rounded-xl bg-blue px-5 py-2.5 text-[13px] font-bold text-white transition hover:bg-blue-press"
				>
					Sign in
				</a>
				<a
					href={signupUrl(here())}
					className="inline-flex items-center rounded-xl border border-card-line bg-white px-5 py-2.5 text-[13px] font-bold text-slate-strong transition hover:border-blue hover:text-ink"
				>
					Create an account
				</a>
			</div>
		</Card>
	);
}

/** This exact page, path and query, so the way back is the way they came. */
function here(): string {
	return window.location.pathname + window.location.search;
}

function PathStep({ path, onChange }: { path: Path; onChange: (p: Path) => void }) {
	return (
		<div className="grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label="What are you here to do?">
			<ChoiceCard
				selected={path === "volunteer"}
				onSelect={() => onChange("volunteer")}
				icon={<Icon.people size={20} />}
				title="Volunteer"
				body="Give time and skills. Your branch verifies your record, then you can be deployed and log the hours you give."
			/>
			<ChoiceCard
				selected={path === "member"}
				onSelect={() => onChange("member")}
				icon={<Icon.card size={20} />}
				title="Member"
				body="Join the Society formally. Membership carries a certificate and a place on the register, and may carry a fee."
			/>
		</div>
	);
}

/**
 * What is being registered, stated rather than asked, with a way back.
 *
 * Replaces the path step for somebody who already pressed "Become a volunteer".
 * It is a sentence and a link, not a control: the answer is not in question, so
 * drawing two radio cards with one of them lit would put the question back on
 * the page in a smaller font. The link is there because a landing page button is
 * an easy thing to press by mistake, and a wizard with no way out of the wrong
 * branch is the thing people abandon.
 */
function PathSwitch({ path, onChange }: { path: Path; onChange: (p: Path) => void }) {
	const volunteering = path === "volunteer";

	return (
		<p className="mt-4 inline-flex flex-wrap items-center gap-x-2 gap-y-1 rounded-xl border border-card-line bg-surface px-3.5 py-2 text-[12.5px] text-muted">
			<span className="inline-flex items-center gap-1.5 font-semibold text-ink">
				{volunteering ? <Icon.people size={15} /> : <Icon.card size={15} />}
				Registering as {volunteering ? "a volunteer" : "a member"}
			</span>
			<span aria-hidden="true" className="text-slate-faint">
				·
			</span>
			<button
				type="button"
				onClick={() => onChange(volunteering ? "member" : "volunteer")}
				className="font-semibold text-ink underline decoration-navy/30 underline-offset-2 transition hover:decoration-navy"
			>
				{volunteering ? "Join as a member instead" : "Volunteer instead"}
			</button>
		</p>
	);
}

/**
 * Who this person is — and, for a volunteer, where they are a national of.
 *
 * **Nationality arrived here when its own screen was deleted.** It had a step
 * to itself titled "Citizenship and where you live", and the pair was wrong in
 * both halves. Citizenship is one question with one answer for all but a
 * handful of people, and a whole rung of the ladder for it announced a
 * seriousness it does not have. "Where you live" was three controls asking the
 * form to repeat the branch chosen on the screen before it. So the second
 * question is gone entirely and the first sits with date of birth and gender,
 * which is what it is: a fact about the person, on the page about the person.
 */
function IdentityStep({
	profile,
	genders,
	path,
	options,
	firstName,
	lastName,
	phone,
	gender,
	dateOfBirth,
	photo,
	citizenship,
	onCitizenship,
	isCitizen,
	onIsCitizen,
	onFirstName,
	onLastName,
	onPhone,
	onGender,
	onDateOfBirth,
	onPhoto,
	disability,
	onDisability,
	disabilityNeeds,
	onDisabilityNeeds,
}: {
	profile: RedProfile | null;
	genders: string[];
	path: Path;
	options?: ApplicationOptions;
	firstName: string;
	lastName: string;
	phone: string;
	gender: string;
	dateOfBirth: string;
	photo: string;
	citizenship: string;
	onCitizenship: (v: string) => void;
	isCitizen: boolean;
	onIsCitizen: (yes: boolean) => void;
	onFirstName: (v: string) => void;
	onLastName: (v: string) => void;
	onPhone: (v: string) => void;
	onGender: (v: string) => void;
	onDateOfBirth: (v: string) => void;
	onPhoto: (v: string) => void;
	disability: string;
	onDisability: (v: string) => void;
	disabilityNeeds: string;
	onDisabilityNeeds: (v: string) => void;
}) {
	return (
		<div className="space-y-5">
			<div className="grid gap-5 sm:grid-cols-2">
				<Field label="First name" required htmlFor="join-first">
					<TextInput id="join-first" value={firstName} onChange={onFirstName} />
				</Field>

				<Field label="Last name" required htmlFor="join-last">
					<TextInput id="join-last" value={lastName} onChange={onLastName} />
				</Field>

				<Field label="Phone" htmlFor="join-phone" hint="The number we reach you on.">
					<TextInput
						id="join-phone"
						type="tel"
						inputMode="tel"
						value={phone}
						onChange={onPhone}
					/>
				</Field>

				<Field label="Email" hint="The account you signed in with.">
					{/* Never an input, on either path. The login is the identity: a
					    form field here would let anybody claim anybody's record, and
					    `update_my_profile` does not accept one for the same reason. */}
					<div className="flex items-center gap-2 rounded-xl border border-card-line bg-surface px-3.5 py-2.5 text-[13.5px] text-muted">
						<span className="flex-none text-slate-faint">
							<Icon.lock size={14} />
						</span>
						<span className="min-w-0 truncate">{profile?.email ?? "Taken from your account"}</span>
					</div>
				</Field>

				<Field label="Gender" htmlFor="join-gender">
					<SelectInput
						id="join-gender"
						value={gender}
						options={genders}
						onChange={onGender}
						placeholder="Prefer not to say"
					/>
				</Field>

				<Field
					label="Date of birth"
					required={path === "volunteer"}
					htmlFor="join-dob"
					hint={
						path === "volunteer"
							? "Needed for safeguarding, and to know what you can be asked to do."
							: undefined
					}
				>
					<TextInput
						id="join-dob"
						type="date"
						max={new Date().toISOString().slice(0, 10)}
						value={dateOfBirth}
						onChange={onDateOfBirth}
					/>
				</Field>
			</div>

			{/* Only a volunteer is asked. A membership does not depend on it and
			    `assert_ready` does not check it, so putting it on both paths would
			    be this screen collecting something nobody needs. Drawn only once
			    the vocabularies are in, because the yes/no form of the question is
			    unanswerable without the society's own country. */}
			{path === "volunteer" && options && (
				<FieldSet title="Nationality">
					<CitizenshipQuestion
						countries={options.countries}
						home={options.default_country_of_citizenship}
						value={citizenship}
						onChange={onCitizenship}
						isCitizen={isCitizen}
						onIsCitizen={onIsCitizen}
					/>
				</FieldSet>
			)}

			{/* Volunteers only, for the same reason nationality is: a society has
			    to know what adjustments to make before it sends somebody
			    anywhere, and a membership does not turn on it. */}
			{path === "volunteer" && (
				<FieldSet
					title="Access and support"
					description="So your branch knows what to arrange. Answering is required; saying more is not."
				>
					<div className="grid gap-5 sm:grid-cols-2">
						<Field label="Do you have a disability?" required htmlFor="join-disability">
							<SelectInput
								id="join-disability"
								value={disability}
								options={DISABILITY_ANSWERS}
								onChange={onDisability}
								placeholder="Choose an answer"
							/>
						</Field>

						{/* Drawn only on "Yes". A description box under "No" is a form
						    asking a question it has already been answered, and under
						    "Prefer not to say" it is a form arguing with somebody. */}
						{disability === "Yes" && (
							<Field
								label="Anything that would help"
								htmlFor="join-disability-needs"
								hint="Access, equipment, the kind of task. Optional — leave it blank and your branch will ask."
							>
								<TextArea
									id="join-disability-needs"
									value={disabilityNeeds}
									onChange={onDisabilityNeeds}
									rows={3}
								/>
							</Field>
						)}
					</div>
				</FieldSet>
			)}

			<PhotoField id="join-photo" value={photo} onChange={onPhoto} />
		</div>
	);
}

/**
 * A photograph, which is optional and says so.
 *
 * **It goes on the Red Profile, not on either application.** A portrait is a
 * fact about the person in the same way a date of birth is, which is why
 * `SELF_EDITABLE_FIELDS` already carries `profile_photo` and why this control
 * posts through `update_my_profile` rather than travelling with a registration.
 * It is the picture that ends up on a membership card and beside this person's
 * name on every screen a coordinator reads.
 *
 * **Public, unlike an answer's attachment.** `AnswerUpload` uploads privately
 * because a letter naming somebody's chief is evidence for one approver. A
 * portrait is shown on the person's own card to anybody who scans it, so a
 * private file would be a broken image everywhere it is drawn.
 *
 * **Nobody is blocked by it.** No registration checks it, the step's completion
 * rule does not mention it, and a failed upload leaves a message and an
 * otherwise working form. That is what "not mandatory" has to mean to be true.
 */
function PhotoField({
	id,
	value,
	onChange,
}: {
	id: string;
	value: string;
	onChange: (value: string) => void;
}) {
	const { upload, loading } = useFrappeFileUpload();
	const [failure, setFailure] = useState<string | null>(null);

	const pick = async (file: File | undefined) => {
		if (!file) return;
		setFailure(null);

		try {
			const uploaded = await upload(file, { isPrivate: false });
			onChange(uploaded.file_url);
		} catch (uploadError) {
			setFailure(errorMessage(uploadError, "That picture could not be uploaded."));
		}
	};

	return (
		<Field
			label="Photograph"
			htmlFor={id}
			hint="Optional. It goes on your card and beside your name."
		>
			<div className="flex flex-wrap items-center gap-4">
				<div className="grid h-[72px] w-[72px] flex-none place-items-center overflow-hidden rounded-xl border border-card-line bg-surface text-slate-faint">
					{value ? (
						<img src={value} alt="" className="h-full w-full object-cover" />
					) : (
						<Icon.user size={26} />
					)}
				</div>

				<div>
					<div className="flex items-center gap-2.5">
						<label
							htmlFor={id}
							className="cursor-pointer rounded-xl border border-card-line bg-white px-3.5 py-2 text-[12.5px] font-bold text-slate-strong transition hover:border-blue hover:text-ink"
						>
							{loading ? "Uploading…" : value ? "Replace picture" : "Choose a picture"}
						</label>
						<input
							id={id}
							type="file"
							accept="image/*"
							className="sr-only"
							disabled={loading}
							onChange={(event) => pick(event.target.files?.[0])}
						/>

						{value && !loading && (
							<button
								type="button"
								onClick={() => {
									setFailure(null);
									onChange("");
								}}
								className="text-[11.5px] font-semibold text-muted hover:text-danger hover:underline"
							>
								Remove
							</button>
						)}
					</div>

					{failure && (
						<p className="mt-2 text-[11.5px] leading-relaxed text-danger">{failure}</p>
					)}
				</div>
			</div>
		</Field>
	);
}

function PlacementStep({
	path,
	chain,
	onChain,
	allowedLevels,
}: {
	path: Path;
	chain: GeoNode[];
	onChain: (chain: GeoNode[]) => void;
	allowedLevels?: string[];
}) {
	return (
		<FieldSet title={path === "member" ? "Branch or area" : "Serving branch"}>
			<GeoSelects
				chain={chain}
				onChain={onChain}
				allowedLevels={allowedLevels}
				idPrefix="serving"
			/>
		</FieldSet>
	);
}

/**
 * Citizenship, asked the way a clerk at a branch counter would ask it.
 *
 * **The overwhelming majority answer "yes", so that is the question.** This was
 * a country picker two hundred entries long, opened on the society's own country
 * and correct for almost everybody who saw it — a control whose only job, nearly
 * every time, was to be scrolled past. A person who is a citizen now answers one
 * button, and the list is drawn for the minority it was actually there for.
 *
 * **The society's own country is the society's own configuration.** It is
 * `application.default_country_of_citizenship`, the same value the field would
 * be filled with on insert, arriving through `application_options`. Nothing here
 * names a country, and a society that has not set one gets the plain picker
 * back — the yes/no question is unanswerable without knowing what "citizen"
 * means here, and guessing would be this file inventing a citizenship country.
 *
 * **"No" clears the answer rather than leaving the default standing.** The step
 * cannot be completed without a country, so somebody who says they are not a
 * citizen is stopped at an empty required field instead of carrying the
 * society's country forward under an answer that contradicts it.
 */
function CitizenshipQuestion({
	countries,
	home,
	value,
	onChange,
	isCitizen,
	onIsCitizen,
}: {
	countries: string[];
	home: string | null;
	value: string;
	onChange: (value: string) => void;
	isCitizen: boolean;
	onIsCitizen: (yes: boolean) => void;
}) {
	if (!home) {
		return (
			<div className="max-w-sm">
				<Field label="Country of citizenship" required htmlFor="join-citizenship">
					<Combo id="join-citizenship" value={value} onChange={onChange} options={countries} />
				</Field>
			</div>
		);
	}

	return (
		<div>
			<p className="mb-2.5 text-[13px] font-semibold text-slate-strong">
				Are you a citizen of <span className="text-ink">{home}</span>?
			</p>
			<Segmented
				label={`Are you a citizen of ${home}?`}
				value={isCitizen ? "Yes" : "No"}
				onChange={(answer) => onIsCitizen(answer === "Yes")}
				options={["Yes", "No"]}
			/>

			{!isCitizen && (
				<div className="rise-in mt-5 max-w-sm">
					<Field label="Country of citizenship" required htmlFor="join-citizenship">
						<Combo id="join-citizenship" value={value} onChange={onChange} options={countries} />
					</Field>
				</div>
			)}
		</div>
	);
}

/**
 * How the applicant would like to pay, out of what the society takes.
 *
 * **The list is the society's, and this file holds none of it.** Every option
 * comes from `api/member.py::payment_methods`, which is what a society ticked in
 * its settings intersected with what `onerc_payments` currently has active. So
 * there is no "M-Pesa" in here, no bank transfer, and no branch on which one is
 * configured: a society that adds a card processor next year gets a third option
 * on this screen with no deploy.
 *
 * **Nothing is charged here and the screen says so.** Choosing is a statement of
 * intent that travels with the registration; the fee is requested when the
 * application is submitted, and what happens then belongs to the gateway — a
 * prompt on a phone for mobile money, an account number and a reference for a
 * transfer. Putting a card form on this page would be this app collecting
 * payment details, which is exactly what the payments seam exists to prevent.
 *
 * **What the society wants said is said.** `instructions` is a field on the
 * society's own settings row, so a branch that needs to tell people which office
 * to pay at writes it there rather than asking for a deploy.
 */
function PaymentStep({
	methods,
	selected,
	onSelect,
	type,
}: {
	methods: PaymentMethod[];
	selected: string;
	onSelect: (gateway: string) => void;
	type: PricedType | null;
}) {
	return (
		<div className="max-w-xl space-y-4">
			{type && !type.free && (
				<p className="rounded-xl bg-surface px-4 py-3 text-[12.5px] leading-relaxed text-muted">
					This membership costs{" "}
					<strong className="font-semibold text-ink">
						{formatMoney(type.amount, type.currency)}
					</strong>
					. We will ask for it once your application has been sent — nothing is taken now.
				</p>
			)}

			<div className="space-y-3" role="radiogroup" aria-label="How would you like to pay?">
				{methods.map((method) => (
					<ChoiceCard
						key={method.gateway}
						selected={selected === method.gateway}
						onSelect={() => onSelect(method.gateway)}
						icon={<Icon.card size={20} />}
						title={method.label}
						body={method.instructions || method.description || ""}
					/>
				))}
			</div>
		</div>
	);
}

/**
 * The documents somebody produces, however many that is.
 *
 * **One was never the model.** `Red Profile` has held a *table* of
 * identifications since it was written, the coordinator's view has always shown
 * all of them, and a society can mark two different types required at once —
 * which made this step, asking for a single pair, a form that could not satisfy
 * the configuration sitting next to it. So the step lists documents and the
 * person adds the ones they hold.
 *
 * **The first row is the main one, and nothing says so on screen.** Order is
 * the whole statement — the server reads position and sets the flag — because a
 * "primary" radio beside two rows is a control asking somebody to rank their own
 * passport, which is a question nobody has an opinion about.
 *
 * **Removing is only offered when there is something to remove.** A single row
 * has no remove button: emptying the step is not a thing anybody wants, and a
 * control that would leave a required step blank is a trap rather than a
 * choice.
 */
function IdentificationStep({
	options,
	loading,
	rows,
	onRows,
}: {
	options?: ApplicationOptions;
	loading: boolean;
	rows: Identification[];
	onRows: (next: Identification[]) => void;
}) {
	if (loading || !options) return <Spinner label="Loading…" />;

	if (options.id_types.length === 0) {
		return (
			<p className="rounded-xl bg-surface px-4 py-3 text-[12.5px] leading-relaxed text-muted">
				This society has not configured any identification types yet, and an application cannot be
				submitted without one. Ask your branch to add them before registering.
			</p>
		);
	}

	const set = (index: number, key: keyof Identification, value: string) =>
		onRows(rows.map((row, at) => (at === index ? { ...row, [key]: value } : row)));

	const remove = (index: number) => onRows(rows.filter((_row, at) => at !== index));

	// A kind already listed is not offered again in the other rows' pickers, so
	// the repeat this step refuses cannot be chosen in the first place. The row's
	// own current value always stays in its own list, or choosing it would
	// remove it from under the person who chose it.
	const taken = new Set(rows.map((row) => row.id_type).filter(Boolean));

	return (
		<div className="max-w-xl space-y-4">
			{rows.map((row, index) => (
				<div
					key={index}
					className={cx(
						"grid gap-5 sm:grid-cols-2",
						index > 0 && "border-t border-card-line pt-4",
					)}
				>
					<Field
						label={index === 0 ? "ID type" : "Another ID type"}
						required={index === 0}
						htmlFor={`join-id-type-${index}`}
					>
						<VocabularySelect
							id={`join-id-type-${index}`}
							value={row.id_type}
							onChange={(value) => set(index, "id_type", value)}
							options={options.id_types.filter(
								(entry) => entry.key === row.id_type || !taken.has(entry.key),
							)}
						/>
					</Field>

					<Field
						label="ID number"
						required={index === 0}
						htmlFor={`join-id-number-${index}`}
					>
						<TextInput
							id={`join-id-number-${index}`}
							value={row.id_number}
							onChange={(value) => set(index, "id_number", value)}
						/>
					</Field>

					{rows.length > 1 && (
						<div className="sm:col-span-2">
							<button
								type="button"
								onClick={() => remove(index)}
								className="text-[11.5px] font-semibold text-slate-faint underline-offset-2 hover:text-danger hover:underline"
							>
								Remove this document
							</button>
						</div>
					)}
				</div>
			))}

			{/* Offered only when the society actually recognises another kind, so
			    a society with one document type gets no button that adds a row
			    with nothing to put in it. */}
			{rows.length < options.id_types.length && (
				<Button
					variant="navy"
					onClick={() => onRows([...rows, blankIdentification()])}
					disabled={!rows.every(identificationIsCoherent)}
				>
					Add another document
				</Button>
			)}

			<p className="text-[11.5px] leading-relaxed text-slate-faint">
				One is enough for most people. Add more if your branch has asked for them.
			</p>
		</div>
	);
}

/**
 * The society's own step, drawn entirely from configuration.
 *
 * **No question in here is written down anywhere in this file.** Label, help
 * text, whether it is required and what it may be answered with all arrive from
 * `VMMS Application Question`, which is the whole point: a branch that decides
 * it needs a letter from the area chief adds a record and this step grows a
 * field, with no deploy and nobody editing a bundle.
 *
 * **A type this build does not recognise is not drawn.** Same rule as
 * `<NotBuilt>`: rendering an unknown question as a text box would collect an
 * answer the server is going to refuse, and the applicant would have no way to
 * tell why. The list is closed on the server too, so this is a guard against a
 * bundle that is older than the site rather than against a society.
 */
function QuestionsStep({
	questions,
	answers,
	onAnswer,
}: {
	questions: SocietyQuestion[];
	answers: Record<string, string>;
	onAnswer: (question: string, value: string) => void;
}) {
	const DRAWN = ["Data", "Small Text", "Select", "Check", "Date", "Int", "Attach"];

	// The society's own headings, in the order the form asks them. A society
	// that grouped nothing gets one unnamed group, which draws exactly the flat
	// list this step has always drawn — the heading is only rendered when there
	// is a word to render.
	const groups: Array<{ name: string; questions: SocietyQuestion[] }> = [];

	for (const question of questions.filter((entry) => DRAWN.includes(entry.field_type))) {
		const name = question.group?.trim() ?? "";
		const existing = groups.find((group) => group.name === name);

		if (existing) existing.questions.push(question);
		else groups.push({ name, questions: [question] });
	}

	return (
		<div className="space-y-7">
			{groups.map((group) => (
				<div key={group.name || "ungrouped"}>
					{group.name && (
						<h3 className="mb-3 text-[14px] font-bold text-ink">
							{group.name}
						</h3>
					)}

					<div className="grid gap-5 sm:grid-cols-2">
						{group.questions.map((question) => (
							<div
								key={question.name}
								className={
									question.field_type === "Small Text" || question.field_type === "Check"
										? "sm:col-span-2"
										: undefined
								}
							>
								<QuestionField
									question={question}
									value={answers[question.name] ?? ""}
									onChange={(value) => onAnswer(question.name, value)}
								/>
							</div>
						))}
					</div>
				</div>
			))}
		</div>
	);
}

/** One question, drawn as whatever its `field_type` says it is. */
function QuestionField({
	question,
	value,
	onChange,
}: {
	question: SocietyQuestion;
	value: string;
	onChange: (value: string) => void;
}) {
	const id = `question-${question.name}`;

	// A tick is its own control and carries its label beside it rather than
	// above, so it reads as a statement somebody agrees to instead of a field
	// with a blank-looking answer.
	if (question.field_type === "Check") {
		return (
			<label
				htmlFor={id}
				className="flex cursor-pointer items-start gap-3 rounded-xl border border-card-line bg-canvas-soft p-4"
			>
				<input
					id={id}
					type="checkbox"
					className="mt-0.5 h-4 w-4 shrink-0 accent-brand"
					checked={value === "1"}
					onChange={(event) => onChange(event.target.checked ? "1" : "0")}
				/>
				<span>
					<span className="block text-[13px] font-semibold leading-snug text-ink">
						{question.label}
						{question.is_required && <span className="ml-1 text-brand">*</span>}
					</span>
					{question.help_text && (
						<span className="mt-1 block text-[11.5px] leading-relaxed text-slate-faint">
							{question.help_text}
						</span>
					)}
				</span>
			</label>
		);
	}

	return (
		<Field label={question.label} hint={question.help_text || undefined} required={question.is_required} htmlFor={id}>
			{question.field_type === "Select" && (
				<SelectInput id={id} value={value} onChange={onChange} options={question.choices} />
			)}

			{question.field_type === "Small Text" && (
				<TextArea id={id} value={value} onChange={onChange} rows={4} />
			)}

			{question.field_type === "Date" && (
				<TextInput id={id} value={value} onChange={onChange} type="date" />
			)}

			{question.field_type === "Int" && (
				<TextInput id={id} value={value} onChange={onChange} inputMode="numeric" />
			)}

			{question.field_type === "Data" && <TextInput id={id} value={value} onChange={onChange} />}

			{question.field_type === "Attach" && (
				<AnswerUpload id={id} value={value} onChange={onChange} />
			)}
		</Field>
	);
}

/**
 * The file half of a question, uploaded before the application exists.
 *
 * It has to be: somebody picks their chief's letter several steps before
 * anything is filed. So the file is created private and unattached, and
 * `questions.anchor_files()` ties it to the application at the moment of
 * insert — which is what makes it readable by the approver and by nobody else.
 * Until then it belongs to the person who uploaded it, which is the right state
 * for a document not yet submitted to anybody.
 *
 * The framework's own uploader, the same one the content editor uses, rather
 * than a second one written here.
 */
function AnswerUpload({
	id,
	value,
	onChange,
}: {
	id: string;
	value: string;
	onChange: (value: string) => void;
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
					{loading ? "Uploading…" : value ? "Replace file" : "Choose file"}
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

function DeclarationStep({
	options,
	loading,
	skills,
	onSkills,
	languages,
	onLanguages,
	availability,
	onAvailability,
	motivations,
	onMotivations,
	experience,
	onExperience,
}: {
	options?: ApplicationOptions;
	loading: boolean;
	skills: string[];
	onSkills: (v: string[]) => void;
	languages: string[];
	onLanguages: (v: string[]) => void;
	availability: string[];
	onAvailability: (v: string[]) => void;
	motivations: string[];
	onMotivations: (v: string[]) => void;
	experience: string;
	onExperience: (v: string) => void;
}) {
	if (loading || !options) return <Spinner label="Loading…" />;

	const toggle = (current: string[], set: (v: string[]) => void) => (key: string) =>
		set(current.includes(key) ? current.filter((entry) => entry !== key) : [...current, key]);

	return (
		<div className="space-y-8">
			{/* One control for all four questions, and it is the search box. These
			    are a society's own vocabularies and a society may configure any of
			    them to any length, so a step built out of two different controls
			    reads as two different kinds of question for a reason that is really
			    only "how many rows Kenya happens to have". The descriptions a
			    society wrote are not lost — `MultiCombo` renders them under each
			    row — and the picks echo through the same `TokenTray` either way. */}
			<FieldSet title="What you can do">
				<MultiCombo
					id="join-skills"
					label="Skills"
					options={options.skills}
					selected={skills}
					onToggle={toggle(skills, onSkills)}
					placeholder="Type a skill…"
					empty="This society has not configured any skills yet."
				/>
			</FieldSet>

			<FieldSet title="Languages you speak">
				<MultiCombo
					id="join-languages"
					label="Languages"
					options={options.languages}
					selected={languages}
					onToggle={toggle(languages, onLanguages)}
					placeholder="Type a language…"
					empty="This site has no languages configured yet."
				/>
			</FieldSet>

			<FieldSet title="When you are available">
				<MultiCombo
					id="join-availability"
					label="Availability"
					options={options.availability}
					selected={availability}
					onToggle={toggle(availability, onAvailability)}
					placeholder="Type a slot…"
					empty="This society has not configured any availability slots yet."
				/>
			</FieldSet>

			<FieldSet title="Why you want to volunteer">
				<MultiCombo
					id="join-motivations"
					label="Motivation"
					options={options.motivations}
					selected={motivations}
					onToggle={toggle(motivations, onMotivations)}
					placeholder="Type a reason…"
					empty="This society has not configured any motivations yet."
				/>
			</FieldSet>

			<FieldSet title="Anything you have done before">
				<Field label="In your own words" htmlFor="join-experience">
					<TextArea
						id="join-experience"
						value={experience}
						onChange={onExperience}
						placeholder="Previous volunteering, first aid training, work that might be useful…"
					/>
				</Field>
			</FieldSet>
		</div>
	);
}

/**
 * Who to call, and — where the society counts this applicant as a child — who
 * says they may volunteer at all.
 *
 * **One screen for two records, and they stay two records.** A guardian
 * consents; an emergency contact is called. Those are different acts with
 * different legal weight, and a society that withdrew one must not thereby have
 * withdrawn the other, so the server stores `VMMS Guardian Consent` and
 * `VMMS Emergency Contact` separately and this form posts them separately. What
 * it does offer is the copy button, because the same person fills both roles
 * more often than not and typing a mother's name twice is not a principle worth
 * defending — it copies values into the second record rather than merging them.
 *
 * **The guardian block appears from the date of birth**, using the age of
 * majority the server served. A society that has configured none never sees any
 * of it. Neither half blocks the step: both are conditions of *approval* rather
 * than of submission, so somebody whose parent has not signed the form yet can
 * still send the application in and let the branch chase it.
 */
function EmergencyStep({
	contacts,
	onContacts,
	isMinor,
	minorAge,
	guardian,
	onGuardian,
}: {
	contacts: EmergencyContact[];
	onContacts: (next: EmergencyContact[]) => void;
	isMinor: boolean;
	minorAge: number | null;
	guardian: GuardianConsent;
	onGuardian: (next: GuardianConsent) => void;
}) {
	const first = contacts[0] ?? blankContact();

	const set = <K extends keyof EmergencyContact>(index: number, key: K, value: EmergencyContact[K]) =>
		onContacts(contacts.map((row, at) => (at === index ? { ...row, [key]: value } : row)));
	const setGuardian = <K extends keyof GuardianConsent>(key: K, value: GuardianConsent[K]) =>
		onGuardian({ ...guardian, [key]: value });

	return (
		<div className="space-y-9">
			<FieldSet
				title="Someone we can call"
				description="If something happens while you are volunteering, this is who we would contact. You can add more than one, and you can change them later."
			>
				<div className="space-y-6">
					{contacts.map((contact, index) => (
						<div
							key={index}
							className={cx(
								"grid gap-5 sm:grid-cols-2",
								index > 0 && "border-t border-card-line pt-6",
							)}
						>
							{/* The second and later contacts are numbered, because two
							    blocks of identically labelled fields on one screen are
							    ambiguous to read and unusable with a screen reader. The
							    first is not, because on the overwhelmingly common form
							    with one contact there is nothing to number. */}
							{index > 0 && (
								<p className="sm:col-span-2 text-[11px] font-bold uppercase tracking-wider text-slate-faint">
									Contact {index + 1}
								</p>
							)}

							<Field label="Their name" htmlFor={`ec-name-${index}`}>
								<TextInput
									id={`ec-name-${index}`}
									value={contact.contact_name}
									onChange={(value) => set(index, "contact_name", value)}
									placeholder="Full name"
								/>
							</Field>

							<Field label="How you know them" htmlFor={`ec-rel-${index}`}>
								<TextInput
									id={`ec-rel-${index}`}
									value={contact.relationship}
									onChange={(value) => set(index, "relationship", value)}
									placeholder="Mother, brother, friend"
								/>
							</Field>

							<Field label="Phone number" htmlFor={`ec-phone-${index}`}>
								<TextInput
									id={`ec-phone-${index}`}
									type="tel"
									value={contact.primary_phone}
									onChange={(value) => set(index, "primary_phone", value)}
									placeholder="Their main number"
								/>
							</Field>

							<Field
								label="Another number"
								htmlFor={`ec-alt-${index}`}
								hint="If there is somewhere else we could try."
							>
								<TextInput
									id={`ec-alt-${index}`}
									type="tel"
									value={contact.alternative_phone ?? ""}
									onChange={(value) => set(index, "alternative_phone", value)}
									placeholder="Optional"
								/>
							</Field>

							<div className="sm:col-span-2">
								{/* Not a formality. An unticked box means we hold a number we
								    have been told not to call, which is a different state
								    from holding no number — and the server counts only the
								    contacts somebody actually permitted. */}
								<label
									htmlFor={`ec-permission-${index}`}
									className="flex cursor-pointer items-start gap-3 rounded-xl border border-card-line bg-canvas-soft p-4"
								>
									<input
										id={`ec-permission-${index}`}
										type="checkbox"
										className="mt-0.5 h-4 w-4 shrink-0 accent-brand"
										checked={Boolean(contact.may_contact_in_emergency)}
										onChange={(event) =>
											set(index, "may_contact_in_emergency", event.target.checked)
										}
									/>
									<span>
										<span className="block text-[13px] font-semibold leading-snug text-ink">
											We may contact this person in an emergency
										</span>
										<span className="mt-1 block text-[11.5px] leading-relaxed text-slate-faint">
											Leave this unticked and we will keep the number on file without using
											it.
										</span>
									</span>
								</label>
							</div>

							{contacts.length > 1 && (
								<div className="sm:col-span-2">
									<button
										type="button"
										onClick={() => onContacts(contacts.filter((_row, at) => at !== index))}
										className="text-[11.5px] font-semibold text-slate-faint underline-offset-2 hover:text-danger hover:underline"
									>
										Remove this contact
									</button>
								</div>
							)}
						</div>
					))}

					<Button
						variant="navy"
						onClick={() => onContacts([...contacts, blankContact()])}
						disabled={!contacts.every(contactIsCoherent)}
					>
						Add another contact
					</Button>
				</div>
			</FieldSet>

			{isMinor && (
				<FieldSet
					title="A parent or guardian"
					description={`Because you are under ${minorAge ?? 18}, we need a parent or guardian to agree to you volunteering with us. Someone from your branch will check this with them before your application is decided.`}
				>
					<div className="mb-5">
						<Button
							variant="navy"
							onClick={() =>
								onGuardian({
									...guardian,
									guardian_name: first.contact_name,
									relationship: first.relationship,
									phone: first.primary_phone,
								})
							}
							disabled={!first.contact_name.trim()}
						>
							Same as the person above
						</Button>
					</div>

					{/* Labelled apart from the emergency contact above rather than
					    repeating "Their name" and "Phone number" on the same page.
					    Two identical labels on one screen is ambiguous to read and
					    unusable with a screen reader, and this block sits directly
					    under the block it would have collided with. */}
					<div className="grid gap-5 sm:grid-cols-2">
						<Field label="Parent or guardian's name" htmlFor="gc-name">
							<TextInput
								id="gc-name"
								value={guardian.guardian_name}
								onChange={(value) => setGuardian("guardian_name", value)}
								placeholder="Full name"
							/>
						</Field>

						<Field label="How they are related to you" htmlFor="gc-rel">
							<TextInput
								id="gc-rel"
								value={guardian.relationship}
								onChange={(value) => setGuardian("relationship", value)}
								placeholder="Mother, father, guardian"
							/>
						</Field>

						<Field label="A number for them" htmlFor="gc-phone">
							<TextInput
								id="gc-phone"
								type="tel"
								value={guardian.phone}
								onChange={(value) => setGuardian("phone", value)}
								placeholder="A number we can reach them on"
							/>
						</Field>

						<Field label="Email address" htmlFor="gc-email" hint="If they have one.">
							<TextInput
								id="gc-email"
								value={guardian.email ?? ""}
								onChange={(value) => setGuardian("email", value)}
								placeholder="Optional"
							/>
						</Field>

						<div className="sm:col-span-2">
							<label
								htmlFor="gc-given"
								className="flex cursor-pointer items-start gap-3 rounded-xl border border-card-line bg-canvas-soft p-4"
							>
								<input
									id="gc-given"
									type="checkbox"
									className="mt-0.5 h-4 w-4 shrink-0 accent-brand"
									checked={Boolean(guardian.consent_given)}
									onChange={(event) => setGuardian("consent_given", event.target.checked)}
								/>
								<span>
									<span className="block text-[13px] font-semibold leading-snug text-ink">
										They have agreed to me volunteering
									</span>
									<span className="mt-1 block text-[11.5px] leading-relaxed text-slate-faint">
										Someone from the branch will confirm this with them directly.
									</span>
								</span>
							</label>
						</div>

						{Boolean(guardian.consent_given) && (
							<Field label="When they agreed" htmlFor="gc-date">
								<TextInput
									id="gc-date"
									type="date"
									value={guardian.consent_date ?? ""}
									onChange={(value) => setGuardian("consent_date", value)}
								/>
							</Field>
						)}
					</div>
				</FieldSet>
			)}
		</div>
	);
}

/**
 * What the applicant agrees to, in the society's own current words.
 *
 * **Nothing on this screen is written in this file.** Every title and every
 * paragraph is a `VMMS Declaration` record, so a society's legal officer
 * rewrites all four without a deploy — and what gets stored on the application
 * is the exact wording shown here at the version shown here, which is the whole
 * reason the step exists at its own page rather than as a line of small print
 * beside the Submit button.
 *
 * **Four boxes, not one.** Bundling them is the thing this prevents: agreeing to
 * have your data processed so a society can consider your application is a
 * different act from agreeing to be contacted about other things, and somebody
 * who wants one and not the other has no way to say so if they share a tick.
 *
 * The text is rendered as the HTML a society wrote. It is authored on the desk
 * by an administrator — the same trust boundary `VMMS Content Block` sits on —
 * and never by an applicant.
 */
function ConsentsStep({
	declarations,
	accepted,
	onToggle,
}: {
	declarations: Declaration[];
	accepted: string[];
	onToggle: (name: string, yes: boolean) => void;
}) {
	return (
		<div className="space-y-4">
			{declarations.map((declaration) => {
				const id = `declaration-${declaration.name}`;
				const ticked = accepted.includes(declaration.name);

				return (
					<section
						key={declaration.name}
						className={cx(
							"overflow-hidden rounded-xl border transition",
							ticked ? "border-blue bg-rail/[0.03]" : "border-card-line bg-white",
						)}
					>
						<header className="flex items-baseline justify-between gap-4 border-b border-card-line px-5 py-3">
							<h3 className="text-[14.5px] font-bold text-ink">
								{declaration.title}
								{declaration.is_required && (
									<span className="ml-1 text-blue" aria-hidden="true">
										*
									</span>
								)}
							</h3>
							{/* Shown because it is stored. A person who asks later what
							    they agreed to gets an answer that names a version. */}
							<span className="flex-none text-[10.5px] font-semibold uppercase tracking-wider text-slate-faint">
								Version {declaration.version}
							</span>
						</header>

						{/* Two ways a society publishes a policy, and the second one
						    is not a degraded first. A society whose legal team owns
						    the privacy notice on its own website is asked to link to
						    it rather than to keep a second copy here, so the form
						    sends the applicant to the page it names instead of
						    reprinting words it does not have. */}
						{declaration.source === "Link" ? (
							<div className="px-5 py-4">
								<a
									href={declaration.external_url ?? undefined}
									target="_blank"
									rel="noreferrer noopener"
									className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-ink underline"
								>
									Read {declaration.title.toLowerCase()}
									<span aria-hidden="true">↗</span>
								</a>
								<p className="mt-2 text-[12px] leading-relaxed text-slate-faint">
									This opens in a new tab, so you will not lose what you have filled in.
								</p>
							</div>
						) : (
							<div
								className="space-y-2.5 px-5 py-4 text-[13px] leading-relaxed text-muted [&_a]:font-semibold [&_a]:text-ink [&_a]:underline"
								dangerouslySetInnerHTML={{ __html: declaration.body ?? "" }}
							/>
						)}

						<label
							htmlFor={id}
							className="flex cursor-pointer items-center gap-3 border-t border-card-line bg-surface/60 px-5 py-3.5"
						>
							<input
								id={id}
								type="checkbox"
								className="h-4 w-4 shrink-0 accent-brand"
								checked={ticked}
								onChange={(event) => onToggle(declaration.name, event.target.checked)}
							/>
							<span className="text-[13px] font-semibold text-ink">
								I have read this and I agree
							</span>
						</label>
					</section>
				);
			})}
		</div>
	);
}

function ConfirmStep({
	path,
	steps,
	onEdit,
	name,
	email,
	phone,
	gender,
	dateOfBirth,
	photo,
	node,
	chain,
	type,
	citizenship,
	disability,
	paymentLabel,
	identifications,
	declared,
	experience,
	societyAnswers,
	contacts,
	isMinor,
	guardian,
	consents,
}: {
	path: Path;
	steps: StepDef[];
	onEdit: (index: number) => void;
	name: string;
	email: string | null;
	phone: string;
	gender: string;
	dateOfBirth: string;
	photo: string;
	node: GeoNode | null;
	chain: GeoNode[];
	type: PricedType | null;
	citizenship: string;
	/** The disability answer, or an empty string on the member path. */
	disability: string;
	/**
	 * How they said they will pay, already resolved to the society's own word
	 * for it — never the gateway's record name, which is an identifier nobody
	 * outside the payments app has any reason to read.
	 */
	paymentLabel: string | null;
	/** Already resolved to the society's own words, and already filtered. */
	identifications: Array<{ label: string; number: string }>;
	declared: Record<"skills" | "languages" | "availability" | "motivations", string[]>;
	experience: string;
	societyAnswers: Array<{ label: string; shown: string }>;
	/** Only the ones that will actually be sent. */
	contacts: EmergencyContact[];
	isMinor: boolean;
	guardian: GuardianConsent;
	consents: Array<{ name: string; title: string; version: string; accepted: boolean }>;
}) {
	const indexOf = (id: StepId) => steps.findIndex((entry) => entry.id === id);

	// A step this registration never drew has nowhere to send anybody. Undefined
	// rather than -1, which `goTo` would clamp to the first screen.
	const editor = (id: StepId) => (indexOf(id) < 0 ? undefined : () => onEdit(indexOf(id)));

	return (
		<div className="space-y-5">
			<PersonCard
				name={name}
				email={email}
				phone={phone}
				gender={gender}
				dateOfBirth={dateOfBirth}
				photo={photo}
				// Read back where it was answered. Nationality has no step of its
				// own any more, so it belongs on the card for the step that asks it.
				citizenship={path === "volunteer" ? citizenship : null}
				disability={path === "volunteer" ? disability || null : null}
				onEdit={editor("identity")}
			/>

			{path === "member" && (
				<Review title="Your membership" onEdit={editor("plan")}>
					<Line label="Membership" value={type?.membership_type_name ?? null} />
					<Line
						label="Fee"
						value={type ? (type.free ? "Free" : formatMoney(type.amount, type.currency)) : null}
					/>
					<Line
						label="Runs for"
						value={type ? (type.is_lifetime ? "Lifetime" : `${type.duration_days} days`) : null}
					/>
					<Line
						label="Becomes active"
						value={
							type
								? type.requires_approver
									? "After the branch reviews it"
									: "As soon as the fee is settled"
								: null
						}
					/>
				</Review>
			)}

			{/* Its own card, so Edit goes to the step that asked. Drawn only where
			    there was a choice to make: a free membership and a society with
			    one way of paying both get no payment step, and a card under a
			    question nobody was asked is a form apologising for itself. */}
			{path === "member" && paymentLabel && (
				<Review title="How you'll pay" onEdit={editor("payment")}>
					<Line label="Paying by" value={paymentLabel} />
					<Line label="When" value="After you send this application" />
				</Review>
			)}

			<Review
				title={path === "member" ? "Your branch" : "Where you would serve"}
				onEdit={editor("placement")}
			>
				<Trail label="Placement" chain={chain} />
				<Line label="Recorded at" value={node?.level_name ?? null} />
			</Review>

			{path === "volunteer" && (
				<>
					<Review title="Identification" onEdit={editor("identification")}>
						{identifications.length === 0 ? (
							<Line label="ID type" value={null} />
						) : (
							// The document's own name as the label, so two rows do not
							// read as "ID type / ID type" with no way to tell which
							// number belongs to which.
							identifications.map((row) => (
								<Line key={row.label} label={row.label} value={row.number} mono />
							))
						)}
					</Review>

					<Review title="Your volunteering" onEdit={editor("declaration")}>
						<Chips label="Skills" values={declared.skills} />
						<Chips label="Languages" values={declared.languages} />
						<Chips label="Availability" values={declared.availability} />
						<Chips label="Motivation" values={declared.motivations} />
						<Block label="Anything done before" value={experience} />
					</Review>

					<Review title="If something happens" onEdit={editor("emergency")}>
						{contacts.length === 0 ? (
							<Line label="We would call" value={null} />
						) : (
							contacts.map((entry, index) => (
								<Fragment key={index}>
									<Line
										label={contacts.length > 1 ? `We would call (${index + 1})` : "We would call"}
										value={entry.contact_name || null}
									/>
									<Line label="Who they are" value={entry.relationship || null} />
									<Line label="On" value={entry.primary_phone || null} mono />
									<Line
										label="Another number"
										value={entry.alternative_phone || null}
										mono
									/>
									{!entry.may_contact_in_emergency && (
										<Block
											label="Permission"
											value={`You have asked us not to contact ${entry.contact_name || "this person"}. We will keep the number on file without using it.`}
										/>
									)}
								</Fragment>
							))
						)}
					</Review>

					{isMinor && (
						<Review
							title="Your parent or guardian"
							onEdit={editor("emergency")}
						>
							<Line label="Name" value={guardian.guardian_name || null} />
							<Line label="Who they are" value={guardian.relationship || null} />
							<Line label="Phone" value={guardian.phone || null} mono />
							<Line label="Email" value={guardian.email || null} />
							<Block
								label="Their agreement"
								value={
									guardian.consent_given
										? `Recorded${guardian.consent_date ? ` on ${guardian.consent_date}` : ""}. Someone from your branch will confirm it with them before your application is decided.`
										: "Not recorded yet. Your branch will follow this up before your application can be decided."
								}
							/>
						</Review>
					)}
				</>
			)}

			{/* The society's own questions, shown back the way everything else is.
			    Drawn from the answers rather than the question list, so a question
			    left blank because it was optional takes no room here. */}
			{societyAnswers.length > 0 && (
				<Review title="What your society asked" onEdit={editor("questions")}>
					{societyAnswers.map((answer) => (
						<Block key={answer.label} label={answer.label} value={answer.shown} />
					))}
				</Review>
			)}

			{/* Titles and versions, not the text again. Somebody has just read all
			    four in full on the step before this one, and reprinting them here
			    would bury the rest of the review. The version is shown because it
			    is what gets stored beside their acceptance. */}
			{consents.length > 0 && (
				<Review title="What you agreed to" onEdit={editor("consents")}>
					{consents.map((consent) => (
						<Line
							key={consent.name}
							label={consent.title}
							value={consent.accepted ? `Agreed — version ${consent.version}` : null}
						/>
					))}
				</Review>
			)}

			<p className="text-[12px] leading-relaxed text-slate-faint">
				Submitting sends this to your branch for review. You can follow it from your portal.
			</p>
		</div>
	);
}

/**
 * The review panels, and why they are not a list of one-line rows.
 *
 * The first version put every answer on its own line with the label left and
 * the value right, which reads as a receipt: five words of identity strung
 * across a page of white space, and a list of six chosen skills running off the
 * end of a phone as one comma-separated sentence. What somebody does on this
 * step is *check* — so an answer has to be findable, and a wrong one has to be
 * obvious. Hence a label above its value in a two-column grid, chosen
 * vocabularies drawn as the same tokens the question used, and free text given
 * a block of its own instead of being squeezed into a right-aligned column.
 */
function Review({
	title,
	onEdit,
	children,
}: {
	title: string;
	/**
	 * Where Edit goes, or nothing when there is no screen to go back to.
	 *
	 * A plan chosen before the wizard opened has no step in it — see
	 * `planPreselected` — and an Edit that quietly landed on step one would be
	 * worse than no Edit at all. Absent rather than disabled: a control that
	 * cannot act is not a control.
	 */
	onEdit?: () => void;
	children: React.ReactNode;
}) {
	return (
		<section className="overflow-hidden rounded-xl border border-card-line bg-white">
			<header className="flex items-center justify-between gap-4 border-b border-card-line bg-surface/60 px-4 py-2.5">
				<h3 className="text-[12px] font-semibold uppercase tracking-wider text-ink">
					{title}
				</h3>
				{onEdit && (
					<button
						type="button"
						onClick={onEdit}
						className="rounded-[4px] px-1.5 py-0.5 text-[11.5px] font-bold text-ink transition hover:bg-rail/10"
					>
						Edit
					</button>
				)}
			</header>
			<dl className="grid gap-x-6 gap-y-4 px-4 py-4 sm:grid-cols-2">{children}</dl>
		</section>
	);
}

const REVIEW_LABEL = "text-[10px] font-bold uppercase tracking-wider text-slate-faint";
const MISSING = "text-[13px] italic text-slate-faint";

function Line({ label, value, mono }: { label: string; value: string | null; mono?: boolean }) {
	return (
		<div className="min-w-0">
			<dt className={REVIEW_LABEL}>{label}</dt>
			<dd
				className={cx(
					"mt-1 break-words",
					value ? cx("text-[13.5px] font-semibold text-ink", mono && "font-mono") : MISSING,
				)}
			>
				{value || "Not given"}
			</dd>
		</div>
	);
}

/** Free text, which needs its lines kept and the width of the panel to sit in. */
function Block({ label, value }: { label: string; value: string }) {
	return (
		<div className="min-w-0 sm:col-span-2">
			<dt className={REVIEW_LABEL}>{label}</dt>
			<dd
				className={cx(
					"mt-1",
					value
						? "whitespace-pre-line rounded-xl bg-surface px-3.5 py-2.5 text-[13px] leading-relaxed text-slate-strong"
						: MISSING,
				)}
			>
				{value || "Not given"}
			</dd>
		</div>
	);
}

/** What was chosen, drawn the way it was chosen. A comma-run is not an answer. */
function Chips({ label, values }: { label: string; values: string[] }) {
	return (
		<div className="min-w-0 sm:col-span-2">
			<dt className={REVIEW_LABEL}>{label}</dt>
			<dd className="mt-1.5">
				{values.length === 0 ? (
					<span className={MISSING}>None chosen</span>
				) : (
					<span className="flex flex-wrap gap-1.5">
						{values.map((value) => (
							<span
								key={value}
								className="rounded-full border border-blue/20 bg-rail/[0.06] px-2.5 py-1 text-[12px] font-semibold text-ink"
							>
								{value}
							</span>
						))}
					</span>
				)}
			</dd>
		</div>
	);
}

/**
 * A placement as the ladder it was answered on, rung by rung.
 *
 * "Kenya Red Cross Society · Nairobi · Nairobi Central" is three answers
 * printed as one string. Separating them lets somebody see at a glance that the
 * county is right and the branch is not, which is the whole reason this step
 * exists. The rung labels come from the nodes themselves — this file knows no
 * society's hierarchy, the same rule `GeoSelects` follows.
 */
function Trail({ label, chain }: { label: string; chain: GeoNode[] }) {
	return (
		<div className="min-w-0 sm:col-span-2">
			<dt className={REVIEW_LABEL}>{label}</dt>
			<dd className="mt-1.5">
				{chain.length === 0 ? (
					<span className={MISSING}>Not given</span>
				) : (
					<ol className="flex flex-wrap items-center gap-x-2 gap-y-1">
						{chain.map((entry, index) => (
							<li key={entry.name} className="flex items-center gap-2">
								{index > 0 && (
									<span aria-hidden="true" className="text-slate-faint">
										<Icon.chevron size={12} className="-rotate-90" />
									</span>
								)}
								<span className="flex items-baseline gap-1.5">
									<span
										className={cx(
											"text-[13.5px]",
											index === chain.length - 1
												? "font-bold text-ink"
												: "font-semibold text-muted",
										)}
									>
										{entry.label}
									</span>
									{entry.level_name && (
										<span className="text-[10.5px] uppercase tracking-wide text-slate-faint">
											{entry.level_name}
										</span>
									)}
								</span>
							</li>
						))}
					</ol>
				)}
			</dd>
		</div>
	);
}

/**
 * Who is registering, at the top of the last step, as a person rather than five
 * rows of a table. The email carries its own lock, because it is the one thing
 * on this page the Edit button will not let anybody change.
 */
function PersonCard({
	name,
	email,
	phone,
	gender,
	dateOfBirth,
	photo,
	citizenship,
	disability,
	onEdit,
}: {
	name: string;
	email: string | null;
	phone: string;
	gender: string;
	dateOfBirth: string;
	photo: string;
	/** Null on the member path, which is never asked for one. */
	citizenship: string | null;
	/** The disability answer, or null on the member path. Never the free text:
	    what somebody wrote about themselves belongs on the record their branch
	    reads, not on a summary card. */
	disability: string | null;
	/** Absent when this registration never drew the step. See `Review`. */
	onEdit?: () => void;
}) {
	const monogram =
		name
			.split(/\s+/)
			.filter(Boolean)
			.slice(0, 2)
			.map((part) => part[0]?.toUpperCase() ?? "")
			.join("") || "?";

	return (
		<section className="overflow-hidden rounded-xl border border-card-line bg-white">
			<div className="flex items-start gap-4 border-b border-card-line bg-surface/60 px-4 py-4">
				{/* The portrait, where there is one. This step is a *check*, and the
				    picture is the one answer on it somebody can get wrong without
				    noticing — a monogram here said nothing about whether the file they
				    chose was the one they meant. The initials remain the fallback for
				    everybody who did not upload one, which is most people. */}
				{photo ? (
					<img
						src={photo}
						alt=""
						className="h-12 w-12 flex-none rounded-full border border-card-line object-cover"
					/>
				) : (
					<span
						aria-hidden="true"
						className="grid h-12 w-12 flex-none place-items-center rounded-full bg-rail text-[15px] font-semibold text-white"
					>
						{monogram}
					</span>
				)}

				<div className="min-w-0 flex-1">
					<p className="truncate text-[17px] font-semibold leading-tight text-ink">
						{name || "Your name"}
					</p>
					<p className="mt-1 flex items-center gap-1.5 text-[12.5px] text-muted">
						<span className="flex-none text-slate-faint">
							<Icon.lock size={12} />
						</span>
						<span className="truncate">{email ?? "Taken from your account"}</span>
					</p>
				</div>

				{onEdit && (
					<button
						type="button"
						onClick={onEdit}
						className="flex-none rounded-[4px] px-1.5 py-0.5 text-[11.5px] font-bold text-ink transition hover:bg-rail/10"
					>
						Edit
					</button>
				)}
			</div>

			<dl className="grid gap-x-6 gap-y-4 px-4 py-4 sm:grid-cols-3">
				<Line label="Phone" value={phone} />
				<Line label="Gender" value={gender} />
				<Line label="Date of birth" value={dateOfBirth ? formatDate(dateOfBirth) : null} />
				{citizenship && <Line label="Nationality" value={citizenship} />}
				{disability && <Line label="Disability" value={disability} />}
			</dl>
		</section>
	);
}

/**
 * What somebody sees when they open the wizard with an application already in.
 *
 * Not an error, and drawn to look like nothing has gone wrong, because nothing
 * has: they applied, it is being reviewed, and the only mistake was pressing the
 * button twice. So it says where the application got to and offers the two
 * things that are actually useful — go and look at it, or register for the
 * *other* thing, which is genuinely still open to them.
 *
 * **`otherOpen` is why that second offer is now conditional.** It used to be
 * made unconditionally and it did not work: switching path reloaded the page,
 * which re-asked an endpoint that answered "is anything of yours open" with the
 * volunteer application every time, and the same card came back. The offer is
 * only shown when the other road is genuinely empty, and it switches in place
 * rather than reloading, so what the button says is what happens.
 *
 * The state comes back from the server rather than being inferred from the
 * absence of a volunteer record, so "Submitted" and "In Review" read as the
 * different things they are.
 */
/**
 * The one thing worth saying at the top of a resumed registration.
 *
 * **Nothing, when nobody has asked for anything.** Coming back to your own
 * unfinished form is not an event. It used to be met with an amber panel
 * reading "Continuing your saved draft — nothing has been sent to an approver
 * yet. Review or complete the answers below, then submit when you are ready",
 * above the form it was describing, with a document name underneath it. Every
 * sentence of that is either visible from the form or of no use to the person
 * reading it. Somebody who clicks "register as a volunteer" and finds their
 * answers already in the fields has been told everything they need.
 *
 * **Something, when a reviewer has.** That is a real message from a real person
 * and it exists nowhere else on the screen, so it is drawn — and it is the only
 * case this component now has.
 */
function DraftNotice({ reason }: { reason: string }) {
	return (
		<div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-amber-950">
			<p className="text-[14px] font-bold">Your reviewer needs more information.</p>
			<p className="mt-1.5 text-[12.5px] leading-relaxed">{reason}</p>
		</div>
	);
}

function AlreadyApplied({
	path,
	state,
	otherOpen,
	onSwitch,
}: {
	path: Path;
	state: string;
	otherOpen: boolean;
	onSwitch: () => void;
}) {
	const other: Path = path === "volunteer" ? "member" : "volunteer";

	return (
		<Card className="p-7 sm:p-9">
			<div className="mb-5 grid h-14 w-14 place-items-center rounded-full bg-rail/[0.07] text-ink">
				<Icon.clock size={26} />
			</div>

			<h1 className="text-[26px] font-semibold leading-tight tracking-tight text-ink">
				You have already applied.
			</h1>

			<p className="mt-3 max-w-lg text-[13.5px] leading-relaxed text-muted">
				Your {path === "volunteer" ? "volunteer application" : "membership"} is with your branch
				and has not been decided yet, so there is nothing more to fill in.
				{otherOpen
					? ` Your ${other === "volunteer" ? "volunteer application" : "membership"} is with them as well.`
					: ""}
			</p>

			<div className="mt-5">
				<StateBadge state={state} />
			</div>

			<div className="mt-7 flex flex-wrap gap-2.5">
				<Link
					to="/dashboard"
					className="inline-flex items-center rounded-xl bg-rail px-5 py-2.5 text-[13px] font-bold text-white transition hover:bg-rail/90"
				>
					See where it got to
				</Link>
				{!otherOpen && (
					<button
						type="button"
						onClick={onSwitch}
						className="inline-flex items-center rounded-xl border border-card-line bg-white px-5 py-2.5 text-[13px] font-bold text-slate-strong transition hover:border-blue hover:text-ink"
					>
						Register as a {other} instead
					</button>
				)}
			</div>
		</Card>
	);
}

function Success({ path, payment }: { path: Path; payment: PaymentAsked | null }) {
	return (
		<Card className="p-7 sm:p-9">
			<div className="mb-5 grid h-14 w-14 place-items-center rounded-full bg-emerald-50">
				<svg viewBox="0 0 24 24" width="26" height="26" fill="none" aria-hidden="true">
					<path
						className="tick-draw"
						d="m5 13 4 4L19 7"
						stroke="#059669"
						strokeWidth="2.6"
						strokeLinecap="round"
						strokeLinejoin="round"
					/>
				</svg>
			</div>

			<h1 className="text-[26px] font-semibold leading-tight tracking-tight text-ink">
				That is with your branch now.
			</h1>

			<p className="mt-3 max-w-lg text-[13.5px] leading-relaxed text-muted">
				Your {path === "volunteer" ? "application" : "membership"} has gone to the branch you chose,
				and somebody there will review it.
			</p>

			{/* What the gateway itself said, unedited. Mobile money has already put
			    a prompt on the phone by the time this renders; a bank transfer
			    needs an account number and a reference. Neither sentence is
			    written in this app — see `membership._with_payment` — because only
			    the driver that was asked knows what it just did. */}
			{payment?.message && (
				<div className="mt-6 max-w-lg rounded-xl border border-card-line bg-surface px-4 py-3.5">
					<p className="text-[10.5px] font-bold uppercase tracking-wider text-slate-faint">
						Paying your fee
					</p>
					<p className="mt-1.5 whitespace-pre-line text-[13px] leading-relaxed text-ink">
						{payment.message}
					</p>
					{payment.transaction && (
						<p className="mt-2 font-mono text-[11.5px] text-slate-faint">
							Reference {payment.transaction}
						</p>
					)}
				</div>
			)}

			{/* To the dashboard, not to `/`. Under this app's basename `/` is the
			    public landing page: somebody who had just registered was sent to a
			    page whose header offers "Sign in" and "Become a volunteer", which
			    reads exactly like having been signed out. The portal is
			    `/dashboard`, and that is where "go to your portal" has to go. */}
			<div className="mt-7 flex flex-wrap gap-2.5">
				<Link
					to="/dashboard"
					className="inline-flex items-center rounded-xl bg-rail px-5 py-2.5 text-[13px] font-bold text-white transition hover:bg-rail/90"
				>
					Go to your portal
				</Link>
				<Link
					to={`/join?path=${path === "volunteer" ? "member" : "volunteer"}`}
					reloadDocument
					className="inline-flex items-center rounded-xl border border-card-line bg-white px-5 py-2.5 text-[13px] font-bold text-slate-strong transition hover:border-blue hover:text-ink"
				>
					Also register as a {path === "volunteer" ? "member" : "volunteer"}
				</Link>
			</div>
		</Card>
	);
}
