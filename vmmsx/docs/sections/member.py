# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Member section of the guide.

Field tables are generated from the doctype JSON; every other claim names the
file or function it describes. The shared templating engine is documented here
because Member is its first consumer, with the boundary stated plainly — it will
move to its own top-level section when a second module uses it.
"""

from vmmsx.docs import doctypes

TITLE = "Member"
SUMMARY = "Membership identity, the operational record, and the shared templating engine."

MEMBER = "VMMS Member"
MEMBERSHIP = "VMMS Membership"
TYPE = "VMMS Membership Type"
BENEFIT = "VMMS Membership Benefit"
TEMPLATE = "VMMS Template"
TEMPLATE_CATEGORY = "VMMS Template Category"


def render(w) -> None:
	w.h1(TITLE)

	_what_it_is(w)
	_member(w)
	_membership(w)
	_membership_type(w)
	_benefit(w)
	_approval_modes(w)
	_payment_seam(w)
	_proof_of_membership(w)
	_lifetime(w)
	_renewal(w)
	_templating(w)
	_printing(w)
	_my_memberships(w)
	_anchor(w)
	_identity(w)
	_coordinator_view(w)
	_what_is_tested(w)


# --- 2.1 -------------------------------------------------------------------


def _what_it_is(w) -> None:
	w.h2("What the Member module is")

	w.lead(
		"Membership is the first thing a national society runs and the first real consumer of the"
		" approval engine. This module records who is a member, what kind of membership they hold,"
		" where they hold it, what they paid for it, and when it lapses."
	)
	w.p(
		"It owns very little on its own, which is the point. Identity belongs to onerc_core's Red"
		" Profile. Routing and the approval gate belong to the approval engine. Money belongs to"
		" onerc_payments. Rendering belongs to the shared templating package. What is left — and"
		' what this module is — is the answer to "is this person a member, and of what".'
	)
	w.p(
		"Four doctypes carry that, plus two that belong to templating. The lifecycle services are"
		" in vmmsx/member/services/, and every one of them is idempotent and takes documents"
		" rather than names."
	)

	w.h3("Activation is a predicate, not a sequence")

	w.p(
		"A membership becomes active when everything its type requires has been met — approval, if"
		" its type routes for one, and payment, if its type charges. Both are questions about"
		" configuration rather than about which code path happened to run, so"
		" membership.try_activate() is safe to call after any event and in any order. A payment"
		" that confirms before the approver looks and one that confirms after are the same code,"
		" and there is no ordering bug to have because there is no ordering."
	)


# --- 2.2 to 2.5: the doctypes ---------------------------------------------


def _doctype_block(w, doctype: str, represents: list[str]) -> None:
	for paragraph in represents:
		w.p(paragraph)

	w.table(
		doctypes.FIELD_TABLE_HEADERS,
		doctypes.fields(doctype),
		doctypes.FIELD_TABLE_WIDTHS,
	)
	w.caption(f"Naming — {doctypes.naming_of(doctype)}")


def _member(w) -> None:
	w.h2(MEMBER)

	_doctype_block(
		w,
		MEMBER,
		[
			"A person's membership identity: one record per person who has ever applied. It links"
			" to a Red Profile and holds its own derived state, and that is all it holds.",
			"It stores no name, no email and no phone — not even as a fetched copy, which is a"
			" stored copy wearing a different hat. A second copy of a person is a second answer to"
			" who they are, and the two diverge the first time somebody corrects one of them. Every"
			" name on a certificate or in a queue is read through"
			" vmmsx/member/services/identity.py, which reads Red Profile at the moment of asking.",
			"In core's Design 2 this record is the **satellite**, which means it is the truth. The"
			" row on the person's Red Profile affiliation index is a summary written from here"
			" through set_affiliation(); nothing anywhere reads that row back to decide anything.",
		],
	)


def _membership(w) -> None:
	w.h2(MEMBERSHIP)

	_doctype_block(
		w,
		MEMBERSHIP,
		[
			"The operational record — one per membership term. This is what is applied for, paid"
			" for, approved, activated and eventually expired.",
			"It satisfies the approval engine's document contract (approval_state, approval_stage,"
			" approval_stage_entered_on and a table of VMMS Approval Decision) so that a routed"
			" type can be governed by a VMMS Approval Workflow without the engine ever naming it."
			" Those four fields are declared here and written only by the engine.",
			"It also carries its own membership_status, which is a different question from"
			" approval_state: one is where the approval stands, the other is whether the person is"
			" currently a member. A membership on an auto-on-payment type has no approval at all"
			" and stays at approval_state Draft for its whole life.",
		],
	)


def _membership_type(w) -> None:
	w.h2(TYPE)

	_doctype_block(
		w,
		TYPE,
		[
			"The configuration record, and the centre of this module. Everything a national society"
			" decides differently about a kind of membership is a field on it: the fee and its"
			" currency, how long it lasts, which certificate template renders it, and — MEM-02 —"
			" whether it is routed to an approver or activates on payment.",
			"Its guardrails are on the record rather than in the services, so a type that cannot"
			" work is impossible to save. The one worth knowing: a type that activates on payment"
			" and charges nothing is refused, because every application on it would activate the"
			" instant it was submitted — which may be what a society wants, but not by accident.",
		],
	)


def _benefit(w) -> None:
	w.h2(BENEFIT)

	_doctype_block(
		w,
		BENEFIT,
		[
			"One entitlement under a membership type, as a child row. The benefit_key is what a"
			" report or an integration refers to, so relabelling the benefit breaks nothing.",
			"Active benefits are passed into the certificate context, so what a member is told they"
			" get comes from configuration rather than from the template's wording.",
		],
	)


# --- 2.6 -------------------------------------------------------------------


def _approval_modes(w) -> None:
	w.h2("MEM-02 — approval is configurable")

	w.p(
		"A membership type's approval_mode field decides how a membership of that type becomes"
		" active. There are two modes, and the field is the whole of the decision:"
	)
	w.table(
		("approval_mode", "What happens", "What activation then waits for"),
		[
			[
				"routed",
				"vmmsx/member/services/approval.py hands the document to the approval engine, which"
				" resolves approvers through core and assigns it to them.",
				"approval_state reaching Approved — and payment too, if the type charges.",
			],
			[
				"auto_on_payment",
				"Nothing. The membership never enters the engine: no state, no stage, nobody's queue.",
				"Confirmed payment, and nothing else. There is no approver.",
			],
		],
		(1.35, 2.65, 2.50),
	)
	w.p(
		"**No source file branches on a membership type's name to select the path, and none"
		" branches on a stage's label.** The dispatch in approval.py is two dictionaries keyed by"
		" the configuration value itself — _BEGIN and _SETTLED — so adding a mode is adding a row,"
		" and a society switching a type from routed to auto-on-payment is a settings change that"
		" no source file knows happened."
	)
	w.p(
		"This is the same shape the approval engine proved with Kenya and The Gambia: one code"
		" path, configuration alone deciding the outcome. The test that makes it undeniable"
		" applies the same type twice with one field edited in between, and gets two different"
		" behaviours out of the same call."
	)

	w.h3("Routing is delegated, completely")

	w.p(
		"This module never resolves an approver, never queries Geo Assignment and never walks the"
		" geo tree. approval.begin() calls engine.submit() and the engine does all of it. Two"
		" resolvers would eventually disagree, and the day they did, memberships would route to"
		" people who cannot open them. A test walks the AST of every file under member/ and fails"
		" if resolve_approvers or a Geo Assignment query ever appears."
	)
	w.p(
		"Approving a membership therefore goes through vmmsx/api/approvals.py, the engine's own"
		" endpoint, and not through anything in this module. The person-gate lives there, and a"
		" second door into the same decision would be a second place to get it wrong."
	)


# --- 2.7 -------------------------------------------------------------------


def _payment_seam(w) -> None:
	w.h2("MEM-01 — the payment seam")

	w.p(
		"All money goes through onerc_payments. vmmsx/member/services/payment.py is the only file"
		" in this module that knows a payment exists, and even it knows nothing about a gateway:"
		" no M-Pesa, no STK push, no shortcode, and no branch on which driver is active. Swapping"
		" M-Pesa for a bank transfer is a setting in the payments app and changes nothing here."
	)
	w.p(
		'The import is lazy on purpose. vmmsx declares required_apps = ["onerc_core"] and not'
		" payments, so a society running fee-free membership need not install a gateway app at"
		" all; a zero-fee type never reaches the import."
	)
	w.p(
		"Because that absence is a supported state, it is guarded rather than crashed on — and"
		" guarded at configuration time, on the same principle as the ACC-02 anchor. A membership"
		" type that charges a fee refuses to save when onerc_payments is not installed, naming what"
		" is missing; a zero-fee type saves perfectly happily, because it collects nothing. A"
		" second guard sits in front of the lazy import, for the case where the app was removed"
		" after the type was configured, so an applicant gets a clear refusal instead of a"
		" ModuleNotFoundError surfacing as a 500."
	)
	w.p(
		"Both guards ask frappe.get_installed_apps() rather than trying the import and catching the"
		" failure. An app can be present in the bench and not installed on this site, which is the"
		" case that actually bites — and a question answered by an exception cannot be asked at"
		" configuration time, which is where the useful error belongs."
	)

	w.h3("Outbound: asking for the fee")

	w.p(
		"payment.request() calls initiate_payment() with the membership as the source document,"
		" the fee from the type, and the currency from the type or — where it names none — from"
		" the society's configured currency. It is idempotent: a membership that already has a"
		" transaction does not get a second one, because two live payment requests for one"
		" membership is a support call rather than a feature."
	)

	w.h3("Inbound: the two hooks")

	w.p(
		"onerc_payments calls back into the source document by name, guarded by hasattr, so the"
		" signatures must match exactly. They are verified against the live consumer,"
		" onerc_prequalification's Vendor Application, and a test asserts the parameter lists"
		" rather than trusting them:"
	)
	w.code(
		"# vmmsx/vmms_member/doctype/vmms_membership/vmms_membership.py\n"
		"def on_payment_confirmed(self, amount=None, receipt=None, transaction_id=None)\n"
		"def on_payment_receipt(self, receipt=None, transaction_id=None)"
	)
	w.bullets(
		[
			"on_payment_confirmed is the universal contract and the activation trigger. It fires"
			" whichever driver resolved the payment and cannot tell them apart — the Manual driver"
			" reaches it through confirm_payment(), M-Pesa through a callback or a status poll. It"
			" records the payment and saves; activation is re-evaluated from that save.",
			"on_payment_receipt is optional enrichment and nothing more. Some gateways deliver a"
			" receipt number only on a callback that lands after the payment resolved; the Manual"
			" driver may never deliver one separately at all. A membership is fully functional if"
			" this method is never called — the certificate simply renders without a receipt line.",
		]
	)
	w.note(
		"Everything about payment in the tests runs on the Manual driver, through the payments"
		" app's own confirm_payment(). Nothing is stubbed and neither hook is ever invoked by"
		" hand, so what is proven is the real path a society using bank transfer would take."
	)


# --- 2.8 -------------------------------------------------------------------


def _proof_of_membership(w) -> None:
	w.h2("Proof-of-Membership")

	w.lead(
		"A pre-rollout member paid before this system existed, and has no gateway transaction to"
		" point at. Proof-of-Membership is not a third path alongside routed and"
		" auto_on_payment — it is the routed path, unchanged, with an approver verifying an"
		" attached document instead of a gateway confirming a payment. No routing code, no state"
		" machine and no gate were written for it; the existing engine, resolved approver and"
		" person-gate are exactly what a proof submission goes through."
	)

	w.h3("Two fields on VMMS Membership")

	w.p(
		"membership_source (Gateway | Proof, defaulting to Gateway) and proof_attachment, an"
		" Attach field the doctype did not have before. Neither changes what routing does or who"
		" it routes to — they record which channel settled the fee and what evidence backs a Proof"
		" one. Both are in the doctype's own field table above, in the Proof of Membership"
		" section."
	)

	w.h3("The money question, answered a second way")

	w.p(
		"Activation still asks the same two questions it always has: is approval settled, and is"
		" payment settled. member/services/membership.py::_payment_settled() is the only new"
		" logic, and it widens the second question rather than replacing it: settled if"
		" payment.is_settled() says so, or if the membership is proof-sourced. payment.py itself"
		" is untouched — it is never asked about proof, and MEM-01's boundary (\"the only file in"
		' this module that knows a payment exists") stays exactly as true as it was.'
	)
	w.p(
		"submit() reads the same flag to skip payment.request() for a proof-sourced membership,"
		" so no gateway transaction is ever created for one — deliberately true even when the type"
		" charges a fee. A pre-rollout member typically belongs to the society's ordinary,"
		" fee-charging type; if the bypass only worked on a zero-fee type it would not fit the"
		" case it exists for, so the tests prove it on a type that charges."
	)

	w.h3("Routed only — enforced where the anchor already is")

	w.p(
		"A proof marked against a type with no approver would have nobody to look at what was"
		" attached, so VMMSMembership.validate_source() refuses the combination before the record"
		" can exist — the same moment validate_anchor() enforces ACC-02. It calls"
		" membership_service.assert_proof_consistent(), which asks the type's own approval_mode"
		" rather than assuming one, and refuses a Proof submission with nothing attached in the"
		" same pass. Neither check is approval logic: they gate what the existing engine is handed,"
		" and never touch routing, the state machine or the gate."
	)

	w.h3("A fresh period, not a backdated one")

	w.p(
		"activate() was not changed at all. valid_from is set to the day approval settles and"
		" valid_to follows the type's duration from there, exactly as it already did for every"
		" membership — a proof-verified member becomes current for a full period from when an"
		" approver looks at their evidence, not from whenever they actually first paid. Backdating"
		" a period to the original payment date was considered and set aside: it would need a"
		" second activation rule for one source, where reusing the existing one needs none."
	)

	w.h3("Two ways in, one doctype contract")

	w.p(
		"A pre-rollout member registers themselves through the native Web Form at"
		" /proof-of-membership — the same two-doctype write register-as-a-member uses, with a"
		" Proof section added: Source, shown and fixed to Proof, and the required attachment. A"
		" clerk enrolling somebody instead calls api/member.py::apply_for_membership(), which now"
		" takes membership_source and proof_attachment as optional arguments; left unset, a"
		" membership is the ordinary Gateway kind exactly as before. Both land on the same"
		" VMMS Membership record and the same validate_source() guardrail — there is no separate"
		" proof-submission code path to keep in sync with the ordinary one."
	)

	w.h3("The certificate needed nothing")

	w.p(
		"certificate.py was not touched. A proof-verified membership is Active exactly the way any"
		" other one is, and render_certificate() cannot tell the two apart — which is the point:"
		" a certificate is evidence of membership, and a member verified by proof is not a"
		" second kind of member."
	)


# --- 2.9 -------------------------------------------------------------------


def _lifetime(w) -> None:
	w.h2("Lifetime membership")

	w.lead(
		"A membership type may confer a membership that never ends. is_lifetime on"
		" VMMS Membership Type says so, and everything downstream follows from one fact: the"
		" membership activates with a start date and no end date."
	)

	w.p(
		"The reason this is a field rather than a large number is that a large number is still a"
		" number. Before it existed, a society wanting a life membership configured one with a"
		" duration of 3650 days, and that membership expires — silently, ten years after the"
		" demonstration that sold it, with nobody watching for the day. The seeded Kenya"
		" configuration carried exactly that stand-in and now carries is_lifetime instead."
	)

	w.h3("The duration guardrail, relaxed for one case and no other")

	w.p(
		"VMMSMembershipType.validate_duration() refuses a duration below one day, because a type"
		" that expires and has no duration produces a membership that lapses on the day it"
		" activates. A lifetime type is the one exception, and the exception is tied to the flag"
		" rather than to the rule being softened: clear is_lifetime again and the same save is"
		" refused again."
	)
	w.p(
		"A lifetime type's duration is not merely ignored, it is **cleared to zero on save**. A"
		" lifetime flag sitting beside a stored 365 is two answers to how long the membership"
		" lasts, and whichever a reader found first would be the one they believed. On the form the"
		" field is hidden and not required for a lifetime type, so an administrator is never asked"
		" for a number that will be discarded."
	)

	w.h3("No end date, not a distant one")

	w.p(
		"membership.activate() computes valid_to through _valid_to(), which returns None for a"
		" lifetime type. A placeholder date far in the future was the alternative and is worse: the"
		" expiry sweep would eventually act on it, and every screen would have to know which"
		" far-future date meant forever. An empty valid_to already means the right thing everywhere"
		" this module reads it."
	)
	w.table(
		("Asked of a lifetime membership", "Answer", "Why"),
		[
			[
				"membership.is_lapsed()",
				"False, at any date",
				"There is no window to close. Unchanged code: it already answered False for an"
				" empty valid_to.",
			],
			[
				"membership.expire_lapsed()",
				"Never selects it",
				"The daily sweep filters on valid_to being set, stated as its own filter rather"
				" than left to SQL's NULL comparison.",
			],
			[
				"renewal.is_renewable()",
				"False, in every state",
				"Checked against the type, first. A membership with no period has no period to buy.",
			],
			[
				"certificate context valid_to",
				'"Lifetime"',
				"A blank beside the words Valid to reads as a value that failed to load.",
			],
		],
		(2.10, 1.55, 2.85),
	)

	w.h3("There is no Lifetime status")

	w.p(
		"membership_status stays Active. A Lifetime value was considered and rejected: it would"
		" fork every comparison against Active in this app — the certificate gate, the activation"
		" predicate, renewal, the dossier's standing — into a pair that each caller would have to"
		" remember to keep in step, and the first one that forgot would quietly stop treating life"
		" members as members. Whether somebody is currently a member and whether their membership"
		" ends are two questions, and the second is answered by valid_to."
	)
	w.p(
		"So the status DTO carries is_lifetime alongside an empty valid_to, which is what the desk"
		" reads: vmms_member.js renders the validity cell as Lifetime rather than as a row that"
		" looks like it failed to load, and the membership form says Lifetime where it would"
		" otherwise say a number of days."
	)

	w.note(
		"The expiry sweep's skip is asserted against a real run, alongside a real lapsed membership"
		' that expires in the same call — so "the lifetime one did not expire" cannot pass'
		" because nothing happened. member/tests/test_lifetime.py."
	)


# --- 2.10 ------------------------------------------------------------------


def _renewal(w) -> None:
	w.h2("Renewal")

	w.lead(
		"Renewing is applying again. vmmsx/member/services/renewal.py creates a brand-new"
		" VMMS Membership for the same member and the same branch, and puts it through"
		" membership.submit() — the exact function a first application goes through. There is no"
		" second payment path and no second activation rule; a renewal is an ordinary membership"
		" that happens to name what it replaces."
	)

	w.h3("A new record, never an edit of the old one")

	w.p(
		"The prior membership is left exactly as it was. renewal.renew() reads member, geo_node"
		" and — unless the caller chooses a different one — membership_type off the prior record,"
		" and writes them onto a fresh document; it never opens the prior one for writing. The new"
		" record carries a renews Link back to it, so the chain a member's history forms — this"
		" year renews last year, which renews the year before — is a query rather than something"
		" reconstructed from dates."
	)
	w.p(
		"That also means a renewal's own certificate, its own payment transaction and its own"
		" approval state belong to it alone. Nothing about the prior membership's evidence changes"
		" when it is renewed, because nothing about the prior membership changes at all."
	)

	w.h3("Renewable only once a membership has lapsed")

	w.p(
		"Setting aside a lifetime type, which is never renewable at all,"
		" renewal.is_renewable() is true in exactly two states: membership_status is Expired"
		" outright, or it is still Active in the database but its own valid_to has already"
		" passed — the ordinary window between a membership actually lapsing and the daily"
		" expire_lapsed() job noticing. A membership that is genuinely current refuses, through"
		" renewal.assert_renewable(), with a message naming it."
	)
	w.p(
		"The restriction is deliberate rather than incidental. Renewing a membership that has not"
		" lapsed yet would create two live validity windows with two fees attached to one branch,"
		" and reopen the early-payment-and-refund problem that MEM-01's activation predicate was"
		" built to avoid — a membership is one period with one fee, and there is no clean way to"
		" unwind a second one stacked on top of a live first if that first is later cancelled. So"
		" the refusal is the answer, not a rule renewal.py works around."
	)
	w.table(
		("membership_status", "valid_to", "Renewable?"),
		[
			["Active", "in the future", "No — still current"],
			["Active", "already passed", "Yes — the pre-expire-job window"],
			["Expired", "any", "Yes"],
			["Draft / Awaiting Payment / Awaiting Approval", "unset", "No — nothing to renew from yet"],
			["Any, on a lifetime type", "never set", "No — there is no period to renew"],
		],
		(2.35, 2.05, 3.00),
	)
	w.p(
		"The last row is checked first and against the type, not the dates — see Lifetime"
		" membership above. A lifetime membership somebody moved to Expired by hand would"
		" otherwise match the second row and read as renewable."
	)

	w.h3("Multi-branch is unaffected by construction")

	w.p(
		"A renewal names the branch it is scoped to by reading geo_node off the one prior"
		" membership it was asked to renew — there is no argument through which a caller could"
		" widen that, and no step that looks at a member's other memberships at all. Renewing a"
		" member's Nairobi membership creates a new Nairobi membership; whatever they hold at"
		" Mombasa is never opened, read or written. Because assert_renewable() already refuses a"
		" still-current membership, a member cannot end up with two active memberships on one"
		" chain at one branch either — the old one is Expired by the time a renewal is allowed,"
		" and the new one is the only one that can become Active."
	)

	w.h3("The renewable flag")

	w.p(
		"api/member.py::my_memberships() adds one field beyond the status DTO it already returns:"
		" renewable, asked of renewal.is_renewable() for that row. It is what lets a screen show a"
		" renew action exactly when the server would accept one, computed the same way"
		" certificate_available already is — server-side, on every row, rather than a client"
		" guessing from a date."
	)

	w.h3("Who may renew")

	w.p(
		"api/member.py::renew_membership(membership, membership_type=None) takes the prior"
		" membership's name and nothing that could name a person. It loads the prior record"
		" through _readable(), the same owner-bypass gate every other endpoint here uses — the"
		" caller is either the membership's own holder or reaches it through the ordinary"
		" permission layer as an authorised coordinator within their geo scope — so entitlement is"
		" derived from the session on every call, exactly as my_memberships() is."
	)
	w.p(
		"Writing the new row asks the same question a second time, because reading somebody's"
		" membership and being allowed to create one on their behalf are different permissions."
		" A member renewing their own holds no create permission on VMMS Membership — there is no"
		" web form here for a bypass to lean on, the way first registration has — so"
		" renewal.renew() elevates narrowly, exactly one new row for exactly the member and branch"
		" already named, the same shape member.py's own _as_system() and"
		" registration/services/intake.py's as_system() already use. A coordinator instead goes"
		" through an ordinary, checked create permission — the same one apply_for_membership asks"
		" a clerk for — with no elevation at all."
	)
	w.note(
		"Reusing membership.submit() means a renewal's approval routes exactly the way a first"
		" application's does: an auto_on_payment type activates on the renewal's own confirmed"
		" payment, and a routed type is handed to the approval engine again. Neither path is"
		" special-cased for a renewal; both are proven by the same tests that prove a first"
		" application, run against a document that happens to carry a renews link."
	)


# --- 2.11 ------------------------------------------------------------------


def _templating(w) -> None:
	w.h2("The shared templating engine")

	w.p(
		"vmmsx/templating/ is deliberately **not** part of the Member module. It is shared"
		" infrastructure that volunteer agreements and notifications will reuse unchanged, and it"
		" knows nothing about members: a caller looks up a template by its stable key, hands over a"
		" context dict, and gets rendered output back."
	)
	w.p(
		"It is documented in this section because Member is its first consumer. It moves to its own"
		" top-level section when a second module uses it."
	)
	w.code(
		"# vmmsx/templating/services/render.py\n"
		"render_template(template_key: str, context: dict | None = None) -> dict\n"
		"    -> {template_key, template_name, category, format, subject, body}"
	)
	w.p(
		"A test in the templating suite asserts the separation structurally: it strips docstrings"
		" from every file under templating/ and fails if the words member, membership or"
		" certificate appear in the remaining code. Prose may explain what the first consumer is;"
		" code may not name it, because code that names it has coupled to it."
	)

	w.h3("Template content is configuration, never code")

	w.p(
		"No source file in vmmsx contains the text of a certificate. The shipped default is seeded"
		" from vmmsx/templating/seeds/membership_certificate.html into an ordinary editable record"
		" by the setup patch, and it is a society's from the moment it lands. Which template"
		" renders a certificate is the membership type's template_key — pointing it somewhere else"
		" changes every certificate that type issues, with no code change and no deployment."
	)

	w.h3("The sandbox")

	w.p(
		"A template body is written by society administrators through the desk, which makes it"
		" untrusted input running on the server. Rendering goes through frappe.render_template,"
		" whose environment is a FrappeSandboxedEnvironment, and this module screens the body for"
		" dunder access before it ever gets there."
	)
	w.p(
		"The screen sits in front of the sandbox so that this app gives one consistent answer."
		' Frappe itself refuses a template containing ".__" with a generic "Illegal template"'
		" error, and the sandbox refuses what gets past that with a SecurityError; without the"
		" screen, the same attack written two ways would surface as two different exceptions and a"
		" caller would have to know which layer caught it. Every refusal is logged and raised as a"
		" PermissionError with one message."
	)
	w.note(
		"What is guaranteed is that a template cannot execute code. Templates still run with"
		" Frappe's standard safe globals, which is a framework-wide design decision rather than"
		" something this module narrows."
	)

	w.h2(TEMPLATE)

	_doctype_block(
		w,
		TEMPLATE,
		[
			"One society-authored document: a certificate, an agreement, a notification body. Keyed"
			" by a stable business key so that configuration elsewhere can point at it without"
			" caring what it is called.",
			"The controller renders the body against an empty context on save, so a template that"
			" cannot render — or that tries to break out — is refused while its author is still"
			" looking at the form rather than weeks later when somebody's certificate fails.",
		],
	)

	w.h2(TEMPLATE_CATEGORY)

	_doctype_block(
		w,
		TEMPLATE_CATEGORY,
		[
			"The configurable set of kinds of template. Certificate, agreement and notification are"
			" seeded; a society may add to them.",
			"It is a doctype rather than a Select precisely so the set is a society's to extend."
			" **No source file branches on a category value** — the render service returns it as"
			" data and treats every template identically, which is what makes adding one free.",
		],
	)


# --- 2.12 ------------------------------------------------------------------


def _printing(w) -> None:
	w.h2("Printing a certificate")

	w.lead(
		"A certificate is evidence of membership, so it is issued only for an active one and only to"
		" somebody entitled to it. Both halves are enforced in"
		" member/services/certificate.py, and the order they run in is deliberate: the gate first,"
		" then the state, then anything renders at all. A caller who may not have the certificate"
		" cannot make the server build one."
	)

	w.h3("Whose certificate it is")

	w.p(
		"The member it names, and nobody else by default. The member is recognised through core's"
		" Red Profile.user — the link between a person and a login — and never through the"
		" document's owner. That distinction is the whole of this rule and it is easy to get wrong:"
		" a membership registered at a branch desk is *created by* a clerk, so its owner is the"
		" clerk's login and the member may never have touched a keyboard. Gating on owner would hand"
		" every member's certificate to whoever typed them in, and withhold it from the member. On a"
		" site where members register themselves the two coincide and the bug is invisible, which is"
		" why a test builds the case where they differ."
	)
	w.p(
		"A member with no login at all is ordinary — a paper registration has no account — and means"
		" simply that nobody matches as the holder. It is never read as 'anybody'."
	)

	w.h3("And who else a society lets print one")

	w.p(
		"vmms_certificate_print_role, a Custom Field vmmsx owns on National Society Settings and"
		" installs through its own patch. A membership officer printing a card at a counter holds"
		" it; nothing wider is implied. Which role that is, is the society's decision, and no role"
		" name appears in any executable line of this module."
	)
	w.p(
		"The field ships empty, and empty means nobody but the member. This is the one place in the"
		" Member module where blank configuration is a closed door rather than an unconstrained one,"
		" and it is deliberate: a blank access rule that read as 'everyone' would hand every"
		" member's certificate to every logged-in user while looking exactly like a working system."
		" A setting naming a role that was later deleted is treated the same way and logged, so a"
		" membership office whose printing has stopped can find out why. That is core's own"
		" registry.resolve_role discipline restated where this app makes the same kind of decision."
	)
	w.note(
		"Administrator and System Manager pass, through core's has_unrestricted_scope — the same"
		" framework exemption the scoping layers use, and not a society role this app invented."
	)

	w.h3("The PDF, and the logo trap")

	w.p(
		"api/member.py::download_certificate streams a PDF and stores nothing: no File row, no bytes"
		" on disk, and no change to the membership. A certificate is derived from the membership"
		" every time it is asked for, so a stored copy would only ever be a second answer waiting to"
		" go stale. The filename names the membership rather than the person, because a filename"
		" travels into a downloads folder and an email attachment without its contents being opened."
	)
	w.p(
		"The society's logo is where a PDF differs from a screen, and the difference is a trap worth"
		" stating plainly. An Attach Image stores a site-relative path such as /files/logo.png. A"
		" browser resolves that against the page it came from; a PDF renderer has no page, so the"
		" logo silently does not appear — no error, no warning, just a gap where the society's mark"
		" should be. certificate.context_for(absolute_assets=True) is the PDF path asking for asset"
		" references that carry their own location, and it is the only difference between what the"
		" PDF renders and what the HTML endpoint returns."
	)
	w.p(
		"What it produces is a data URI rather than an absolute URL, and that choice is not"
		" incidental. Frappe's get_pdf already runs scrub_urls, which would expand the path into"
		" http://<site>/files/logo.png, so an absolute URL is what you get for free by doing"
		" nothing. It is also the fragile answer: it makes rendering a certificate depend on the"
		" renderer reaching this site over HTTP — the right host, the right port, the file public"
		" rather than private, and a web server actually up — and get_pdf additionally passes"
		" disable-local-file-access. A data URI needs none of that, because the bytes are in the"
		" document. An absolute URL remains the fallback for a logo whose bytes cannot be read, on"
		" the grounds that a link which might resolve beats a path which certainly will not."
	)
	w.p(
		"A society with no logo uploaded gets a certificate without one: the shipped template guards"
		" the image on {% if society_logo %}, and empty is an ordinary state rather than a"
		" misconfiguration."
	)


def _my_memberships(w) -> None:
	w.h2("A member's own memberships")

	w.lead(
		"api/member.py::my_memberships() returns every membership held by whoever is logged in,"
		" across every branch. It takes no arguments, and that is the design rather than a"
		" convenience."
	)
	w.p(
		"An endpoint that accepted a member name would be a general-purpose reader of anybody's"
		" memberships wearing a possessive name, and the only thing standing between it and that"
		" would be a check somebody had to remember to write. There is nothing to remember here: the"
		" caller cannot name somebody else, because the caller cannot name anybody. This is the"
		" shape api/approvals.py::my_queue uses, and for the same reason."
	)
	w.p(
		"Each call walks User to Red Profile.user to VMMS Member.red_profile to"
		" VMMS Membership.member, and every hop is a lookup on a column core or this app makes"
		" unique — so there is no ordering or tie-breaking to specify. Any break in the chain"
		" returns an empty list rather than an error: somebody logged in who is not a member of the"
		" society is an ordinary visitor, not a failure."
	)
	w.p(
		"Every row is the membership status DTO the rest of the module already uses, so the view"
		" assembles no second opinion about what a membership is, plus one field of its own —"
		" whether this caller could actually print its certificate, asked of the same gate the"
		" download uses. A screen offering a button the server would refuse is worse than a screen"
		" with no button."
	)
	w.note(
		"One person may hold memberships at several branches at once. That is a supported state"
		" rather than an anomaly, so nothing here filters by node, takes a first row or assumes a"
		" single answer, and the tests build two concurrently active memberships at two branches to"
		" prove it."
	)


def _anchor(w) -> None:
	w.h2("ACC-02 and ACC-03 — where a membership sits")

	w.p(
		"Every membership carries a Geo Node. It is a Link, never free text, and it is mandatory at"
		" creation — refused by the field and refused again, in the app's own words, by"
		" VMMSMembership.validate_anchor(). There is no path that creates a membership and fills"
		" the anchor in later, because an unplaced record is invisible to core's geo scoping (the"
		" query filter is an IN, which excludes NULL) and unroutable by approvals."
	)
	w.p(
		"Which *level* it may sit at is the opposite kind of question: entirely a society's, and"
		" never a constant. The answer lives on National Society Settings as"
		" vmms_membership_anchor_level, a Custom Field vmmsx owns and installs through its own"
		" patch — core's settings doctype is not edited, because a product pushing its fields into"
		" the shared foundation's source is how the foundation stops being shared."
	)
	w.p(
		"Left empty it means unconstrained, not forbidden: a society that has not narrowed where"
		" memberships may be anchored has not thereby said they may exist nowhere. The tests prove"
		" the configurability by pointing the setting at two different levels and getting opposite"
		" answers from unchanged code, and a further test walks the module's AST and fails if the"
		" word county, ward, district or province ever appears in a string outside a docstring."
	)

	w.h3("Who may see a membership")

	w.p(
		"The same anchor is what geo scoping reads. VMMS Membership is registered with onerc_core"
		" through the onerc_scopeable_doctypes hook, on its geo_node field — so a membership is"
		" visible only to people whose authority covers the place it sits in, enforced across the"
		" list query, the document read and the API guard alike."
	)
	w.p(
		"Which role carries that authority is configuration, not a literal. The registration names"
		" role_from_setting rather than role, pointing at vmms_membership_scope_role — a second"
		" Custom Field vmmsx owns on National Society Settings, installed by its own patch and"
		" typed as a Link to Role so the desk offers only roles that exist."
	)
	w.p(
		"It ships empty, and that is deliberate. Empty means no role resolves, which means core"
		" fails closed: until a society chooses the role, no non-administrator can read a"
		" membership at all. Memberships carry personal data, so the safe direction is closed, and"
		" defaulting to some role would be this app inventing a society's access policy."
		" Administrators are unaffected by the framework exemption, so there is always somebody who"
		" can set it — and core logs every unresolved read, so the state is visible rather than"
		" looking like an empty database."
	)


def _identity(w) -> None:
	w.h2("Identity and the affiliation index")

	w.p(
		"vmmsx/member/services/member.py writes one row on the person's Red Profile affiliation"
		" index through core's set_affiliation(), under the affiliation key this app owns. That row"
		" is a derived summary. Nothing in vmmsx reads it back to decide anything, and the test"
		" that proves it deletes every row and asserts that the module's answers do not change."
	)
	w.p(
		"vmmsx registers itself with core through the onerc_affiliation_providers hook — core never"
		" imports vmmsx. The provider declares VMMS Member as the doctype it owns, and that"
		" declaration is what makes removal safe: core deletes an index row only when a registered"
		" provider owns its reference_doctype and did not claim it."
	)
	w.p(
		"One deliberate exception to the no-bypass rule lives here, and it is justified inline in"
		" member.py. Core's set_affiliation() saves the Red Profile without ignoring permissions,"
		" and asks satellites that must write on an unprivileged user's behalf to arrange elevation"
		" explicitly. Activation is triggered by an approver approving or a gateway callback"
		" confirming a payment, and neither has any business holding write permission on somebody's"
		" identity record — requiring it would mean granting Red Profile write access to every"
		" membership approver in the country. So exactly that one call runs as the system."
	)

	w.h3("What the module may read off the identity spine")

	w.p(
		"member/services/identity.py holds an explicit allow-list of the Red Profile fields this"
		" module will surface, so a field appearing on core's spine never starts flowing through a"
		" vmmsx DTO because nobody noticed it had arrived. It names full_name, first_name,"
		" last_name, email, phone, home_geo_node, user, gender, date_of_birth, profile_photo,"
		" preferred_language, nationality and citizenship_status, and the tests assert that tuple"
		" whole — adding a fourteenth fails the suite rather than passing quietly."
	)
	w.p(
		"The last six were added for the coordinator's view described below, and the guard working"
		" is the reason they can be trusted: widening the reader broke a test that somebody then"
		" had to justify. Widening what is read is not widening what is stored, and the two are"
		" independent — the member record gained no column, no fetch_from and no copy, and"
		" test_dossier.py asserts that none of these ever becomes one."
	)
	w.p(
		"user was added for one reason: to answer whether the person asking for a certificate is the"
		" person it belongs to. It is a login identifier rather than a person-fact — nothing about"
		" who somebody is, only which account is theirs — and it is read by the print gate rather"
		" than rendered onto anything. The sensitive set core holds back for a gated extension"
		" (blood group, medical conditions, next of kin, disability) stays out, and a test asserts"
		" it stays out."
	)


# --- 2.13 ------------------------------------------------------------------


def _coordinator_view(w) -> None:
	w.h2("The coordinator's complete view of a member")

	w.lead(
		"A VMMS Member record is thin by design, and that is correct as a schema and useless as a"
		" screen. Opening one showed a docname where a person should be, and answering an ordinary"
		" question about somebody meant visiting their Red Profile for the name, each membership"
		" for the branch and the dates, the payments app for the receipt and the approval trail for"
		" who verified it."
	)
	w.p(
		"vmmsx/api/member.py::get_dossier answers all of it in one call. It stores nothing and adds"
		" no new truth: every block is read from the record that already owns it, through the"
		" service that owns it, at the moment somebody looks. The assembly is in"
		" vmmsx/member/services/dossier.py."
	)
	w.table(
		("Block", "What it answers", "Where it is read from"),
		[
			[
				"identity",
				"Who this person is: name, photo, contact, gender, date of birth, nationality and"
				" the area they live in.",
				"onerc_core's Red Profile, through member/services/identity.py.",
			],
			[
				"standing",
				"What they are to the society right now, and which branches are carrying that status.",
				"member/services/member.py::derive_status, over the memberships.",
			],
			[
				"memberships",
				"What they hold, at every branch the reader may see: type, validity, whether it has"
				" lapsed, how it was paid for and whether a certificate can be had.",
				"The VMMS Membership records, through membership.py, payment.py and certificate.py.",
			],
			[
				"history",
				"Who approved or verified each membership, and when.",
				"The approval engine's own decision rows, through approvals/services/contract.py.",
			],
		],
		(1.15, 2.55, 2.80),
	)

	w.h3("One call, because one screen must answer as at one instant")

	w.p(
		"The round trips are not the reason. Whether a membership has lapsed, what its effective"
		" status is, whether it can be renewed and what the member's own standing is are all"
		" comparisons against a date — and four blocks compared against four different instants can"
		" contradict each other. A page showing a membership as lapsed beside a renew button"
		" saying not yet, because the two asked either side of midnight, would be wrong in the way"
		" that is hardest to notice and hardest to reproduce."
	)
	w.p(
		"So dossier.build() resolves as_of once and hands the same date to every derivation beneath"
		" it, including the ones nested inside another DTO. That last part is where the rule is"
		" easiest to lose: the renewable flag on each membership row comes from"
		" renewal.is_renewable(), which defaults to today unless it is told otherwise, and it is"
		" told otherwise here. A test asks the dossier about a date on which a membership was still"
		" current and asserts the inner derivation moved with the outer one."
	)

	w.h3("A member is their memberships, so nothing is copied onto the member")

	w.p(
		"The living-and-historical split the Volunteer module draws is more one-sided here. Almost"
		" nothing is the member's own: identity belongs to Red Profile, and branch, type, validity,"
		" payment and the approval trail all belong to the individual memberships. What VMMS Member"
		" holds is the derived status and the date the person first joined."
	)
	w.p(
		"That is a finding rather than an omission, and it is enforced rather than hoped for."
		" Correcting a name on a Red Profile, moving somebody's home area, or renaming a payment"
		" gateway each changes what the screen says while leaving this app's own stored row"
		" byte-identical — asserted in all three directions."
	)

	w.h3("Every branch, and a status derived from the set of them")

	w.p(
		"One person may hold memberships at several branches at once. That is a supported state"
		" rather than an anomaly, so the dossier lists them all, each distinct, and never takes a"
		" first row. Somebody active at one branch and expired at another is an active member —"
		" holding a current membership anywhere makes a person a current member — and the counts"
		" beside the status say which memberships are carrying it, so a reader is not left working"
		" out why an Active member has an obviously expired record beneath them."
	)
	w.p(
		"The status itself is produced by member.py::derive_status, the same function refresh()"
		" writes the stored field with. It is recomputed on read rather than read off the row, so"
		" it cannot be stale, and it is deliberately not a second derivation: one function, one"
		" answer."
	)

	w.h3("The payment picture is read live, never duplicated")

	w.p(
		"MEM-01 puts money on the other side of the payments seam, and reading it back honours the"
		" same boundary. member/services/payment.py::settlement() assembles what was owed from the"
		" membership type, what channel was used from the membership, and what the gateway actually"
		" did from onerc_payments — the last of those read on every call and copied nowhere."
	)
	w.p(
		"Which driver collected a fee is the payments app's fact and can change after the event: a"
		" transaction reconciled by hand, a receipt that arrived late, a gateway renamed. A copy on"
		" the membership would be a second answer going stale silently. The test that proves it is"
		" a mutation: renaming the gateway changes what the screen says and leaves the membership"
		" row untouched."
	)
	w.p(
		"A proof-of-membership record answers the same question from a different place. Its fee was"
		" paid before this system existed, so there is no transaction and never will be; what"
		" stands in for a gateway is the approver who examined the attached evidence, read from the"
		" approval decisions and named on the row."
	)
	w.p(
		"The payments app being absent is ordinary rather than an error — vmmsx does not require"
		" it — so the picture reports whether the live half could be read at all, and a fee-free"
		" membership on a site with no gateway installed still returns a complete answer saying"
		" nothing was owed."
	)

	w.h3("The register: scope is the floor, not a filter")

	w.p(
		"vmmsx/api/member.py::find_members is the list a membership office works from: who are the"
		" members here, at which branch, current or lapsed, and until when — with names rather than"
		" docnames. A row is a membership rather than a member, because branch and validity are"
		" facts about a membership and collapsing two branches into one row would mean choosing"
		" which to hide."
	)
	w.p(
		"member/services/register.py::search() ends in frappe.get_list, which runs core's permission"
		" query condition for VMMS Membership; frappe.get_all would skip it and is not used. Every"
		" argument narrows that result and none widens it, so naming a branch the caller has no"
		" authority over returns nothing rather than reaching past the scope. The dossier's own"
		" memberships block is held to the same bar, so opening somebody's record does not disclose"
		" a membership at a branch the reader cannot see."
	)
	w.p(
		"VMMS Member itself is deliberately not scopeable and could not be: it holds no Geo Node,"
		" because a person is not at a place — their membership is. Building the register by"
		" listing members first and looking up their branches afterwards would have had no floor at"
		" all."
	)

	w.h3("Three papercuts on the desk")

	w.bullets(
		[
			"**The heading names the person.** VMMS Member's title_field is red_profile and VMMS"
			" Membership has none, so both pages were headed by a code. The name is set from the"
			" DTO by the doctype's own client script, and the docname stays beneath it because that"
			" is what an audit trail and a support conversation refer to. A computed title field"
			" was rejected: it would put an identity value on the doctype's meta, which is exactly"
			" what this module refuses.",
			"**The price is visible while choosing.** Selecting a membership type meant choosing"
			" between names with nothing to say which one charges a fee."
			" api/member.py::membership_type_pricing reads the type's own fee live and the form"
			" shows it under the field, with free said as a word rather than as a zero beside a"
			" currency symbol.",
			"**The anchor picker offers only what Submit will accept.** Two configuration surfaces"
			" answer which level a membership may anchor at, and both are enforced independently —"
			" National Society Settings on every save, and the governing workflow's"
			" allowed_anchor_levels at Submit. api/member.py::geo_node_levels intersects them, so a"
			" level the picker offers can never be one the other check goes on to reject. Somebody"
			" could previously pick a region, save a perfectly good draft, and have Submit refuse it"
			" minutes later.",
		]
	)


# --- 2.14 ------------------------------------------------------------------


def _what_is_tested(w) -> None:
	w.h2("What is tested")

	w.p(
		"295 integration tests for this module and the templating package, on top of the approval"
		" engine's 185. Nothing is mocked: geo comes from core's geo fixtures, identity from real"
		" Red Profiles, authority from real Geo Assignment rows, approval from a real workflow"
		" driving the real engine, and payment from the real onerc_payments Manual driver."
	)
	w.table(
		("Test file", "Tests", "What it proves"),
		[
			[
				"test_dossier.py",
				"60",
				"One call answers every block; a member at two branches shows both, and active at"
				" one with expired at another derives Active; as_of resolves once and reaches the"
				" nested renewable derivation, proved by asking about a past date; no identity"
				" field is a column on VMMS Member and correcting a name, or moving a home area,"
				" leaves its row byte-identical; the gateway is read live and renaming it changes"
				" the screen without touching the membership; proof-of-membership is"
				" distinguishable from gateway and names its verifier; the register and the"
				" dossier's membership block both refuse to return an out-of-scope record, and an"
				" unconfigured scope role returns nothing rather than everything; the anchor picker"
				" offers exactly the levels that save and withholds one that would be refused.",
			],
			[
				"test_approval_modes.py",
				"14",
				"Two types differing in one field behave differently; the routed one reaches the"
				" resolved approver's real queue and the auto one never enters the engine; editing"
				" the field mid-test switches the behaviour; the gate refuses another county's"
				" approver, the applicant and a System Manager, and a refusal changes nothing;"
				" ending an approver's Geo Assignment revokes them without the membership being"
				" touched.",
			],
			[
				"test_payment_seam.py",
				"17",
				"A real transaction is created through the payments app; the Manual driver's own"
				" confirm_payment() activates the membership; both hook signatures match what"
				" payments passes, parameter for parameter; confirming twice activates once;"
				" activation works with no receipt ever, and a late receipt neither re-activates"
				" nor overwrites one already held; a routed type is not activated by payment alone;"
				" both orderings of approval and payment reach the same place.",
			],
			[
				"test_proof.py",
				"9",
				"A proof-sourced membership on a fee-charging routed type activates on the"
				" approver's decision alone, with no gateway transaction ever created and a fresh"
				" period from the approval date; membership_source distinguishes a proof"
				" submission from an ordinary one, and an unmarked membership still defaults to"
				" Gateway; a rejection leaves it unactivated exactly as any routed rejection does;"
				" a Proof marked against an auto_on_payment type is refused, and so is a Proof with"
				" nothing attached; the attachment is stored on the record and readable by the"
				" resolved approver; the certificate renders unchanged.",
			],
			[
				"test_anchor.py",
				"11",
				"ACC-02: a membership with no Geo Node is refused at creation, leaves nothing"
				" behind, and cannot have its anchor cleared later. ACC-03: unset means any level,"
				" and pointing the setting at two different levels produces opposite answers from"
				" the same code — in two differently shaped societies. No level name appears in the"
				" module's source.",
			],
			[
				"test_identity.py",
				"18",
				"The member doctype has no identity fields and no fetch_from; a name corrected on"
				" Red Profile is corrected everywhere immediately; the affiliation row is written"
				" through set_affiliation, points back at the satellite, and deleting it changes no"
				" decision the module makes; the index rebuilds from the satellite losing nothing;"
				" the provider declares its ownership and is registered with core.",
			],
			[
				"test_certificate.py",
				"10",
				"The context reads the name from Red Profile and the path from core's adapter;"
				" pointing the type at another template, or editing the template body, changes the"
				" certificate with no code change; a receipt appears only when a gateway produced"
				" one; a certificate is refused for a membership that is not active.",
			],
			[
				"test_certificate_print.py",
				"39",
				"The trap first: a membership created by a clerk for somebody else is printable by"
				" the member and refused to the clerk, proving the gate follows Red Profile.user and"
				" not the document's owner — and the clerk can still open the record, so the refusal"
				" is the gate rather than a permission. A holder of the configured role prints"
				" anyone's; pointing the setting elsewhere changes who; an empty setting, or one"
				" naming a deleted role, grants nobody while still letting the member print, and is"
				" logged. A non-active membership has none, and the gate is proved to run before the"
				" state check by the exception type. The PDF really is a PDF, is streamed with a"
				" filename naming the membership rather than the person, and stores nothing. The"
				" logo is embedded as a data URI from real file bytes, falls back to an absolute URL"
				" when unreadable, and is never left as a bare path.",
			],
			[
				"test_my_memberships.py",
				"14",
				"Two concurrently active memberships at two branches both come back, each with its"
				" own branch; a third awaiting payment comes back too and offers no certificate. A"
				" different session sees only its own, switching session switches the answer, and"
				" the endpoint is asserted to take no arguments at all. A user with no Red Profile,"
				" a profile with no member, and a member with no memberships each get an empty list"
				" rather than an error.",
			],
			[
				"test_payments_absent.py",
				"12",
				"With onerc_payments mocked absent: a fee-bearing type refuses to save and the message"
				" names the missing app; a zero-fee type still saves, so the guard does not"
				" over-block; an application raises a frappe error rather than a raw"
				" ModuleNotFoundError and leaves no half-initiated transaction; and with the app"
				" present everything works unchanged. A test asserts the mock really hides the app,"
				" and another that detection does not depend on the import failing.",
			],
			[
				"test_scoping.py",
				"23",
				"VMMS Membership is really registered with core on its geo_node anchor, naming no"
				" literal role; a configured role scopes by geo across all three layers and a holder"
				" cannot reach another society's records; pointing the setting at a different role"
				" changes who sees what; and with the setting empty every non-administrator is denied"
				" while an administrator still gets in — with the denial logged rather than silent.",
			],
			[
				"test_delegation.py",
				"6",
				"No file under member/ calls resolve_approvers or queries Geo Assignment; no"
				" gateway vocabulary appears in its code; nothing under templating/ names a member"
				" or a certificate in code. The scanner is itself tested against a planted leak — a"
				" scan that finds nothing because it is broken proves nothing.",
			],
			[
				"test_renewal.py",
				"21",
				"Renewing writes a new record carrying a renews link to the prior, which is left"
				" byte-for-byte unchanged and stays Expired; the new record activates through the"
				" ordinary submit() / on_payment_confirmed() path, with its own transaction. A"
				" current membership is refused with a named message; an Expired one and an"
				" Active-but-past-valid_to one are both allowed. The renewed period starts at"
				" today's activation rather than stacking on the prior's own valid_to. Renewing one"
				" branch never touches another, and each branch holds exactly one active membership"
				" afterwards. my_memberships() reports renewable server-side, true only once a"
				" membership has lapsed. The holder renews their own without create permission; an"
				" authorised coordinator renews it through an ordinary checked permission instead; a"
				" stranger with no scope is refused before reaching either. The renewed record"
				" prints its own certificate showing its own period.",
			],
			[
				"test_lifetime.py",
				"21",
				"A lifetime type saves with no duration and has any duration it was given cleared to"
				" zero, while a type with a zero or negative duration is still refused — and"
				" clearing the flag brings that refusal straight back, so the relaxation is tied to"
				" the flag rather than to the guardrail being softened. A lifetime membership"
				" activates with a start date and an end date that is empty in the database rather"
				" than a far-future placeholder, and reads as current at a date two centuries out."
				" The daily sweep, run for real, expires a genuinely lapsed membership in the same"
				' call while never selecting the lifetime one — asserted on the count, so "it did'
				' not expire" cannot pass because nothing ran. It is not renewable in any state,'
				" including one forced to Expired by hand, which is what proves the refusal is read"
				" off the type and not off the empty date; an ordinary lapsed membership stays"
				" renewable. The certificate context and the rendered certificate both say Lifetime"
				" where a date would go, an ordinary one still prints its date, and the status,"
				" dossier and pricing DTOs carry the flag the desk renders from.",
			],
			[
				"templating/tests/test_render.py",
				"20",
				"The renderer works from a config template and a context it has never seen; editing"
				" the template changes the output with no code change; the category is returned as"
				" data and never acted on; every escape attempt is refused and none half-executes;"
				" a template containing one is refused at save time; ordinary Jinja still works and"
				" broken syntax is an error rather than a refusal.",
			],
		],
		(1.55, 0.55, 4.40),
	)
