# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The people, and the months of decisions behind them.

    bench --site <site> execute vmmsx.seed.tanzania_people.main

**Every record here is made the way a person would make it.** That is the whole
brief and it is the one thing that separates this module from
`kenya_operations.py::_volunteers`, which creates a `VMMS Volunteer`, sets
`status = "Active"` by hand and says out loud that it is "standing in for an
acceptance that happened before the demo started". The result looks right on a
list view and falls apart the moment somebody opens it: no application, no
approval trail, no decision rows, nobody who decided, no email ever sent.

So instead:

* a login is created and given the applicant role, exactly as Frappe's own
  sign-up leaves somebody;
* `frappe.set_user` becomes that person, and
  `api.registration.register_as_volunteer` is called with what the wizard posts
  — which creates the Red Profile through `intake`, files the application,
  runs `assert_ready`, and routes it to its first stage;
* `frappe.set_user` becomes the sub-branch approver, who finds it in their
  queue and calls `api.approvals.decide`;
* then the branch approver, who does the same at the second stage, at which
  point the engine — not this file — creates the volunteer, sets the status,
  grants the self-service role and sends the acceptance email.

Nothing below writes a `VMMS Volunteer`, a `VMMS Member`, an approval state or
a decision row directly. If a rule would have refused a real applicant, it
refuses this seed, which is the point: a demo that can only be built by
bypassing the product is a demo of something else.

**The site therefore ends up with a real spread of unfinished work**, because a
society in use is never a list of approved people. Some applications are still
with the sub-branch, some have passed to the branch and are waiting, one was
turned down with a reason, one was sent back for more information. Those are not
decorations — each is the genuine output of the engine being driven to that
point and stopped.

**Dates are moved backwards afterwards.** `creation` and the approval
timestamps are rewritten once the trail exists, so the register reads as
eighteen months of joining rather than as a busy afternoon. That is the one
thing that cannot be done by acting like a user, because a user cannot file a
form last March.

**No stipends.** Deliberately: the user seeding this asked for the approval
chain and not the payment paperwork, and a stipend run with no real
reconciliation behind it would be the kind of decoration this module exists to
avoid.

Idempotent. A second run finds every login present and does nothing.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.seed import tanzania

# What each seeded person can sign in with. `tanzania.DEMO_PASSWORD` carries the
# note on why a demo password is written down in the open.
PASSWORD = tanzania.DEMO_PASSWORD

APPLICANT_ROLE = tanzania.ROLE_APPLICANT

# --- the roster ---------------------------------------------------------------

# One entry per person. `outcome` is where the seed stops driving them, and it
# is the only field here that is about the demo rather than about the person:
#
#   approved     both stages said yes; they are an active volunteer
#   at_branch    the sub-branch passed it up; the branch has not decided
#   at_subbranch just filed; nobody has looked at it yet
#   rejected     the branch turned it down, with a reason
#   more_info    an approver sent it back and it is with the applicant
#
# `days_ago` is when they applied, counted back from the day this runs.
#
# The names are ordinary Tanzanian names and the people are invented. Nobody
# below is a real volunteer, and none of these addresses is a real mailbox.
VOLUNTEERS = (
	# -- Dar es Salaam ---------------------------------------------------------
	{
		"email": "grace.mushi@mail.com",
		"first_name": "Grace",
		"last_name": "Mushi",
		"gender": "Female",
		"date_of_birth": "1996-04-12",
		"phone": "+255712004501",
		"branch": "Dar es Salaam",
		"sub_branch": "Kinondoni",
		"skills": ("first-aid", "community-health"),
		"days_ago": 520,
		"outcome": "approved",
	},
	{
		"email": "daniel.mbwana@mail.com",
		"first_name": "Daniel",
		"last_name": "Mbwana",
		"gender": "Male",
		"date_of_birth": "1993-11-03",
		"phone": "+255712004502",
		"branch": "Dar es Salaam",
		"sub_branch": "Kinondoni",
		"skills": ("logistics", "water-safety"),
		"days_ago": 470,
		"outcome": "approved",
	},
	{
		"email": "neema.kileo@mail.com",
		"first_name": "Neema",
		"last_name": "Kileo",
		"gender": "Female",
		"date_of_birth": "1999-07-22",
		"phone": "+255712004503",
		"branch": "Dar es Salaam",
		"sub_branch": "Ilala",
		"skills": ("psychosocial-support", "youth-leadership"),
		"days_ago": 388,
		"outcome": "approved",
	},
	{
		"email": "hassan.juma@mail.com",
		"first_name": "Hassan",
		"last_name": "Juma",
		"gender": "Male",
		"date_of_birth": "1991-02-18",
		"phone": "+255712004504",
		"branch": "Dar es Salaam",
		"sub_branch": "Temeke",
		"skills": ("first-aid", "logistics"),
		"days_ago": 41,
		"outcome": "at_branch",
	},
	{
		"email": "zainab.omary@mail.com",
		"first_name": "Zainab",
		"last_name": "Omary",
		"gender": "Female",
		"date_of_birth": "2001-09-30",
		"phone": "+255712004505",
		"branch": "Dar es Salaam",
		"sub_branch": "Ubungo",
		"skills": ("communications", "data-collection"),
		"days_ago": 9,
		"outcome": "at_subbranch",
	},
	# -- Arusha ----------------------------------------------------------------
	{
		"email": "emmanuel.laizer@mail.com",
		"first_name": "Emmanuel",
		"last_name": "Laizer",
		"gender": "Male",
		"date_of_birth": "1988-06-14",
		"phone": "+255712004506",
		"branch": "Arusha",
		"sub_branch": "Arusha City",
		"skills": ("first-aid", "restoring-family-links"),
		"days_ago": 610,
		"outcome": "approved",
	},
	{
		"email": "happiness.sanare@mail.com",
		"first_name": "Happiness",
		"last_name": "Sanare",
		"gender": "Female",
		"date_of_birth": "1997-12-05",
		"phone": "+255712004507",
		"branch": "Arusha",
		"sub_branch": "Meru",
		"skills": ("community-health",),
		"days_ago": 275,
		"outcome": "approved",
	},
	{
		"email": "baraka.mollel@mail.com",
		"first_name": "Baraka",
		"last_name": "Mollel",
		"gender": "Male",
		"date_of_birth": "2004-03-27",
		"phone": "+255712004508",
		"branch": "Arusha",
		"sub_branch": "Karatu",
		"skills": ("youth-leadership",),
		"days_ago": 63,
		"outcome": "rejected",
		"reason": (
			"The applicant is currently studying outside the branch area and could not commit to"
			" the induction weekends. Encouraged to reapply at their nearest sub-branch."
		),
	},
	# -- Mwanza ----------------------------------------------------------------
	{
		"email": "furaha.magesa@mail.com",
		"first_name": "Furaha",
		"last_name": "Magesa",
		"gender": "Female",
		"date_of_birth": "1994-08-09",
		"phone": "+255712004509",
		"branch": "Mwanza",
		"sub_branch": "Nyamagana",
		"skills": ("water-safety", "first-aid"),
		"days_ago": 432,
		"outcome": "approved",
	},
	{
		"email": "peter.masanja@mail.com",
		"first_name": "Peter",
		"last_name": "Masanja",
		"gender": "Male",
		"date_of_birth": "1990-01-16",
		"phone": "+255712004510",
		"branch": "Mwanza",
		"sub_branch": "Ilemela",
		"skills": ("logistics", "data-collection"),
		"days_ago": 198,
		"outcome": "approved",
	},
	{
		"email": "rehema.shija@mail.com",
		"first_name": "Rehema",
		"last_name": "Shija",
		"gender": "Female",
		"date_of_birth": "1998-05-21",
		"phone": "+255712004511",
		"branch": "Mwanza",
		"sub_branch": "Sengerema",
		"skills": ("psychosocial-support",),
		"days_ago": 22,
		"outcome": "more_info",
		"reason": (
			"Please upload a clearer copy of your identification — the number on the one attached"
			" is not legible."
		),
	},
	# -- Dodoma, Kilimanjaro, Mbeya --------------------------------------------
	{
		"email": "elia.chusi@mail.com",
		"first_name": "Elia",
		"last_name": "Chusi",
		"gender": "Male",
		"date_of_birth": "1992-10-11",
		"phone": "+255712004512",
		"branch": "Dodoma",
		"sub_branch": "Dodoma City",
		"skills": ("communications", "community-health"),
		"days_ago": 355,
		"outcome": "approved",
	},
	{
		"email": "sophia.massawe@mail.com",
		"first_name": "Sophia",
		"last_name": "Massawe",
		"gender": "Female",
		"date_of_birth": "1995-03-08",
		"phone": "+255712004513",
		"branch": "Kilimanjaro",
		"sub_branch": "Moshi",
		"skills": ("first-aid", "psychosocial-support"),
		"days_ago": 301,
		"outcome": "approved",
	},
	{
		"email": "godfrey.mwakyusa@mail.com",
		"first_name": "Godfrey",
		"last_name": "Mwakyusa",
		"gender": "Male",
		"date_of_birth": "1987-07-19",
		"phone": "+255712004514",
		"branch": "Mbeya",
		"sub_branch": "Mbeya City",
		"skills": ("logistics", "water-safety"),
		"days_ago": 244,
		"outcome": "approved",
	},
	{
		"email": "asha.mwaipopo@mail.com",
		"first_name": "Asha",
		"last_name": "Mwaipopo",
		"gender": "Female",
		"date_of_birth": "2000-11-25",
		"phone": "+255712004515",
		"branch": "Mbeya",
		"sub_branch": "Rungwe",
		"skills": ("community-health", "data-collection"),
		"days_ago": 16,
		"outcome": "at_branch",
	},
)

# --- the members --------------------------------------------------------------

# Membership is the society's other door and it is not the volunteer one with a
# different word on it: a member joins the Society formally, pays a fee, and
# carries a card. It goes through the same two rungs — `AWF-00006` is the
# membership workflow and has the identical Sub-Branch then Branch chain — but
# through `register_as_member`, and it has a second gate the volunteer path does
# not have: **the money**.
#
# `membership.is_activatable` needs approval settled *and* payment settled. TRCS
# is seeded with the Manual gateway, which means a person pays at the branch and
# a clerk records it — `payment.record_confirmation`. So a membership here can
# be sitting in three genuinely different places, and all three are seeded:
#
#   active             approved, and the fee confirmed by a clerk
#   awaiting_payment   both rungs said yes, nobody has confirmed the money
#   awaiting_approval  paid at the desk, still with the branch
#   rejected           turned down, with a reason
#
# **Three of these people are already volunteers above.** That is on purpose and
# it is the case a register most often gets wrong: one person, one Red Profile,
# two affiliations. `_assert_nothing_open` asks about one doctype, so an
# undecided volunteer application has nothing to say about a membership, and
# `intake.for_user` returns the profile that already exists rather than making a
# second one.
MEMBERS = (
	# -- people who are already volunteers -------------------------------------
	{
		"email": "grace.mushi@mail.com",
		"type": tanzania.TYPE_ORDINARY,
		"branch": "Dar es Salaam",
		"sub_branch": "Kinondoni",
		"days_ago": 300,
		"outcome": "active",
	},
	{
		"email": "emmanuel.laizer@mail.com",
		"type": tanzania.TYPE_LIFE,
		"branch": "Arusha",
		"sub_branch": "Arusha City",
		"days_ago": 420,
		"outcome": "active",
	},
	{
		"email": "sophia.massawe@mail.com",
		"type": tanzania.TYPE_ORDINARY,
		"branch": "Kilimanjaro",
		"sub_branch": "Moshi",
		"days_ago": 120,
		"outcome": "awaiting_payment",
	},
	# -- members only ----------------------------------------------------------
	{
		"email": "salma.rashid@mail.com",
		"first_name": "Salma",
		"last_name": "Rashid",
		"gender": "Female",
		"date_of_birth": "1979-02-14",
		"phone": "+255712004601",
		"type": tanzania.TYPE_LIFE,
		"branch": "Dar es Salaam",
		"sub_branch": "Ilala",
		"days_ago": 560,
		"outcome": "active",
	},
	{
		"email": "john.kessy@mail.com",
		"first_name": "John",
		"last_name": "Kessy",
		"gender": "Male",
		"date_of_birth": "1968-09-02",
		"phone": "+255712004602",
		"type": tanzania.TYPE_ORDINARY,
		"branch": "Dar es Salaam",
		"sub_branch": "Temeke",
		"days_ago": 410,
		"outcome": "active",
	},
	{
		"email": "mariam.selemani@mail.com",
		"first_name": "Mariam",
		"last_name": "Selemani",
		"gender": "Female",
		"date_of_birth": "1985-06-30",
		"phone": "+255712004603",
		"type": tanzania.TYPE_ORDINARY,
		"branch": "Mwanza",
		"sub_branch": "Nyamagana",
		"days_ago": 265,
		"outcome": "active",
	},
	{
		"email": "amani.katabazi@mail.com",
		"first_name": "Amani",
		"last_name": "Katabazi",
		"gender": "Male",
		"date_of_birth": "2009-04-18",
		"phone": "+255712004604",
		"type": tanzania.TYPE_YOUTH,
		"branch": "Mwanza",
		"sub_branch": "Ilemela",
		"days_ago": 180,
		"outcome": "active",
	},
	{
		"email": "upendo.mwakasege@mail.com",
		"first_name": "Upendo",
		"last_name": "Mwakasege",
		"gender": "Female",
		"date_of_birth": "2008-11-07",
		"phone": "+255712004605",
		"type": tanzania.TYPE_YOUTH,
		"branch": "Mbeya",
		"sub_branch": "Mbeya City",
		"days_ago": 95,
		"outcome": "active",
	},
	{
		"email": "frank.mwaijande@mail.com",
		"first_name": "Frank",
		"last_name": "Mwaijande",
		"gender": "Male",
		"date_of_birth": "1974-12-11",
		"phone": "+255712004606",
		"type": tanzania.TYPE_ORDINARY,
		"branch": "Dodoma",
		"sub_branch": "Dodoma City",
		"days_ago": 47,
		"outcome": "awaiting_approval",
	},
	{
		"email": "esther.mwansasu@mail.com",
		"first_name": "Esther",
		"last_name": "Mwansasu",
		"gender": "Female",
		"date_of_birth": "1990-08-23",
		"phone": "+255712004607",
		"type": tanzania.TYPE_ORDINARY,
		"branch": "Arusha",
		"sub_branch": "Meru",
		"days_ago": 33,
		"outcome": "awaiting_payment",
	},
	{
		"email": "hamisi.ally@mail.com",
		"first_name": "Hamisi",
		"last_name": "Ally",
		"gender": "Male",
		"date_of_birth": "1996-01-09",
		"phone": "+255712004608",
		"type": tanzania.TYPE_YOUTH,
		"branch": "Kilimanjaro",
		"sub_branch": "Hai",
		"days_ago": 58,
		"outcome": "rejected",
		"reason": (
			"Youth membership is for applicants aged 10 to 17. The applicant is above that age and"
			" has been invited to apply for ordinary membership instead."
		),
	},
)

# What a clerk writes on the receipt when they confirm a fee paid at the branch.
RECEIPT_PREFIX = "TRCS-RCT"

# The identification every applicant gives. `assert_ready` refuses a submission
# without one, so this is not optional padding — it is the reason these
# applications can be submitted at all.
#
# `Identification Type` is core's doctype and its docnames are keys, not labels:
# `national_id`, `passport`, `alien_id`, `driving_licence`. Naming the key here
# and falling back to whatever the site has is what keeps this working on a site
# whose list was configured differently.
ID_TYPE_DOCTYPE = "Identification Type"
ID_TYPE_PREFERRED = "national_id"


def main(commit: bool = True) -> dict:
	"""Register everybody, take each as far as their outcome says, and report."""
	if not tanzania.national():
		print("The Tanzania configuration is not on this site. Run vmmsx.seed.tanzania.main first.")
		return {}

	report = {"volunteers": _volunteers(), "members": _members()}
	report["backdating"] = _backdate()

	if commit:
		frappe.db.commit()

	_print(report)

	return report


def _volunteers() -> list[dict]:
	"""Each person: a login, a registration they filed, and a decision on it."""
	rows = []

	for person in VOLUNTEERS:
		try:
			rows.append(_one(person))
		except Exception as error:  # noqa: BLE001
			# One person who cannot be registered must not cost the other
			# fourteen. Reported rather than raised, and reported with the real
			# message, because a seed that silently skipped somebody would leave
			# a demo missing a branch and nothing to say why.
			frappe.db.rollback()
			rows.append({"key": person["email"], "status": f"failed: {error}"})
		finally:
			frappe.set_user("Administrator")

	return rows


def _one(person: dict) -> dict:
	"""One person, from no account at all to wherever their outcome stops."""
	node = tanzania.sub_branch(person["sub_branch"], person["branch"])

	if not node:
		return {"key": person["email"], "status": f"skipped: {person['sub_branch']} not seeded"}

	if _already_registered(person["email"]):
		return {"key": person["email"], "status": "exists"}

	_login(person)

	# --- as the applicant ---------------------------------------------------
	frappe.set_user(person["email"])
	application = _apply(person, node)
	frappe.set_user("Administrator")

	outcome = person["outcome"]
	trail = ["filed"]

	if outcome != "at_subbranch":
		trail.append(_decide_as(tanzania.SUB_BRANCH_APPROVER, application, person, stage="sub-branch"))

	if outcome in ("approved", "rejected"):
		trail.append(_decide_as(tanzania.BRANCH_APPROVER, application, person, stage="branch"))

	return {
		"key": person["email"],
		"name": application,
		"status": "created",
		"where": f"{person['branch']} / {person['sub_branch']}",
		"outcome": outcome,
		"trail": " → ".join(filter(None, trail)),
	}


def _already_registered(email: str) -> bool:
	"""Has a previous run done this person? Asked of the application, not the user.

	The login is the weaker test: a bench may carry an account somebody made by
	hand. The application is what this module creates and is what makes a second
	run a no-op.
	"""
	profile = frappe.db.get_value("Red Profile", {"user": email}, "name")

	if not profile:
		return False

	return bool(frappe.db.exists(tanzania.APPLICATION_DOCTYPE, {"red_profile": profile}))


def _login(person: dict) -> None:
	"""The account, exactly as Frappe's own sign-up leaves one.

	A Website User holding the applicant role and nothing else — no volunteer
	role, no desk access, no profile. Everything else about this person is
	created by the registration they are about to file, which is the point.
	"""
	from frappe.utils.password import update_password

	if not frappe.db.exists("User", person["email"]):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": person["email"],
				"first_name": person["first_name"],
				"last_name": person["last_name"],
				# Nobody is welcomed twice. The acceptance email the engine sends
				# later is the message that matters, and a welcome email per
				# seeded person would put fifteen messages in the queue that no
				# real event produced.
				"send_welcome_email": 0,
				"user_type": "Website User",
			}
		).insert(ignore_permissions=True)

		if frappe.db.exists("Role", APPLICANT_ROLE):
			user.add_roles(APPLICANT_ROLE)

	update_password(person["email"], PASSWORD)
	frappe.clear_cache(user=person["email"])


def _apply(person: dict, node: str) -> str:
	"""File the application through the endpoint the wizard posts to.

	Not `frappe.get_doc(...).insert()`. This is `register_as_volunteer`, which
	creates the Red Profile through `intake.for_user`, refuses a second open
	application, checks every answer against the question that asked for it,
	runs `assert_ready` — identification, date of birth, residency — and hands
	the application to the approval engine, which routes it to the sub-branch.

	`home_geo_node` is the same node as the serving one: these people volunteer
	where they live, which is what the wizard's own "same as serving branch"
	tick means and what the overwhelming majority of applications say.
	"""
	from vmmsx.api.registration import register_as_volunteer

	result = register_as_volunteer(
		geo_node=node,
		country_of_citizenship=_country(),
		residency_type="Local",
		home_geo_node=node,
		id_type=_id_type(),
		id_number=_id_number(person),
		# Answered, because `assert_ready` requires an answer of every applicant
		# and a seeded society whose applications could not be submitted would be
		# a demo of a broken product. "Prefer not to say" is the answer that
		# invents nothing about a person who does not exist.
		disability_status="Prefer not to say",
		skills=[key for key in person["skills"] if frappe.db.exists("VMMS Skill", key)],
		languages=[],
		availability=[],
		motivation=[],
		prior_experience=None,
		first_name=person["first_name"],
		last_name=person["last_name"],
		phone=person["phone"],
		gender=person["gender"] if frappe.db.exists("Gender", person["gender"]) else None,
		date_of_birth=person["date_of_birth"],
	)

	name = result.get("name") if isinstance(result, dict) else None

	if not name:
		# The DTO shape differs between the two doors; fall back to the record.
		profile = frappe.db.get_value("Red Profile", {"user": person["email"]}, "name")
		name = frappe.db.get_value(tanzania.APPLICATION_DOCTYPE, {"red_profile": profile}, "name")

	return name


def _country() -> str | None:
	"""The society's own default, if this site's Country list has it."""
	return tanzania.COUNTRY if frappe.db.exists("Country", tanzania.COUNTRY) else None


def _id_type() -> str | None:
	"""Whatever this site calls a national ID. Configuration, so it is looked up.

	`assert_ready` requires an ID type and number, and the type is a Link to a
	configured vocabulary. Taking the first configured row rather than naming
	one means this works on a site whose list was set up differently, and
	returning None on a site with none at all lets the failure be the honest
	one — the application is refused and the report says so.
	"""
	if frappe.db.exists(ID_TYPE_DOCTYPE, ID_TYPE_PREFERRED):
		return ID_TYPE_PREFERRED

	rows = frappe.get_all(ID_TYPE_DOCTYPE, limit=1, pluck="name")

	return rows[0] if rows else None


def _id_number(person: dict) -> str:
	"""A stable, obviously-fake identification number, derived from the person.

	Derived rather than random so a second run on a torn-down site produces the
	same number, and obviously patterned so nobody mistakes one for a real
	Tanzanian NIDA number.
	"""
	digits = f"{abs(hash(person['email'])) % 10**8:08d}"

	return f"{person['date_of_birth'].replace('-', '')}-{digits}"


def _decide_as(approver: str, application: str, person: dict, stage: str) -> str:
	"""One decision, recorded by the person who is actually entitled to make it.

	`api.approvals.decide` and not the engine directly, so the whole gate runs:
	the caller must be among the approvers this document routed to, holding the
	role is not enough, and a rejection without a reason is refused. If the
	routing is wrong, this raises — which is the seed telling the truth about
	the configuration rather than papering over it.
	"""
	from vmmsx.api.approvals import decide
	from vmmsx.approvals import states

	outcome = person["outcome"]

	# Which decision this rung records. Only the last rung a person reaches can
	# be anything other than an approval: a rejection at the sub-branch would
	# end the application there and the branch would never see it.
	if stage == "sub-branch" and outcome == "more_info":
		verdict, reason = states.DECISION_MORE_INFO, person["reason"]
	elif stage == "branch" and outcome == "rejected":
		verdict, reason = states.DECISION_REJECTED, person["reason"]
	else:
		verdict, reason = states.DECISION_APPROVED, None

	frappe.set_user(approver)

	try:
		decide(
			doctype=tanzania.APPLICATION_DOCTYPE,
			name=application,
			decision=verdict,
			reason=reason,
		)
	finally:
		frappe.set_user("Administrator")

	return f"{stage}: {verdict.lower()}"


# --- members ------------------------------------------------------------------


def _members() -> list[dict]:
	"""Each membership: registered, decided, and paid for — or stopped short."""
	rows = []

	for person in MEMBERS:
		try:
			rows.append(_one_member(person))
		except Exception as error:  # noqa: BLE001
			frappe.db.rollback()
			rows.append({"key": person["email"], "status": f"failed: {error}"})
		finally:
			frappe.set_user("Administrator")

	return rows


def _one_member(person: dict) -> dict:
	"""One membership, through `register_as_member` and the same two rungs.

	**Somebody who is already a volunteer keeps their profile.** `_login` is a
	no-op for them, and `register_as_member` resolves the Red Profile that their
	volunteer application created rather than making a second one — which is the
	rule this seed would rather demonstrate than assert.
	"""
	node = tanzania.sub_branch(person["sub_branch"], person["branch"])

	if not node:
		return {"key": person["email"], "status": f"skipped: {person['sub_branch']} not seeded"}

	if not frappe.db.exists("VMMS Membership Type", person["type"]):
		return {"key": person["email"], "status": f"skipped: {person['type']} not seeded"}

	if _already_a_member(person["email"]):
		return {"key": person["email"], "status": "exists"}

	# The member-only people need an account; the volunteers already have one.
	if "first_name" in person:
		_login(person)

	frappe.set_user(person["email"])
	membership = _join(person, node)
	frappe.set_user("Administrator")

	outcome = person["outcome"]
	trail = ["applied"]

	# **Paid at the desk, before the branch decided.** That is the ordinary
	# order at a Red Cross branch — somebody pays the subscription at the
	# counter and the paperwork follows — and it is the order that exercises
	# `_set_pending_status`, which parks a membership at Awaiting Approval only
	# once the money question is already answered.
	if outcome in ("active", "awaiting_approval"):
		trail.append(_confirm_fee(membership, person))

	if outcome != "awaiting_approval":
		trail.append(_decide_membership(tanzania.SUB_BRANCH_APPROVER, membership, person, "sub-branch"))
		trail.append(_decide_membership(tanzania.BRANCH_APPROVER, membership, person, "branch"))

	return {
		"key": person["email"],
		"name": membership,
		"status": "created",
		"where": f"{person['branch']} / {person['sub_branch']}  {person['type']}",
		"trail": " → ".join(filter(None, trail)),
	}


def _already_a_member(email: str) -> bool:
	profile = frappe.db.get_value("Red Profile", {"user": email}, "name")

	if not profile:
		return False

	member = frappe.db.get_value("VMMS Member", {"red_profile": profile}, "name")

	return bool(member and frappe.db.exists(tanzania.MEMBERSHIP_DOCTYPE, {"member": member}))


def _join(person: dict, node: str) -> str:
	"""File the membership through the endpoint the wizard posts to.

	`membership_source` and `proof_attachment` are deliberately not passed, and
	the endpoint would not accept them: those are how a *clerk* enrols somebody
	who paid before this system existed, and an applicant asserting their own
	proof of payment is not a thing that endpoint permits. These people are
	applying for themselves, so they pay like everybody else.
	"""
	from vmmsx.api.registration import register_as_member

	result = register_as_member(
		membership_type=person["type"],
		geo_node=node,
		first_name=person.get("first_name"),
		last_name=person.get("last_name"),
		phone=person.get("phone"),
		gender=person.get("gender") if frappe.db.exists("Gender", person.get("gender", "")) else None,
		date_of_birth=person.get("date_of_birth"),
	)

	name = result.get("name") if isinstance(result, dict) else None

	if not name:
		profile = frappe.db.get_value("Red Profile", {"user": person["email"]}, "name")
		member = frappe.db.get_value("VMMS Member", {"red_profile": profile}, "name")
		name = frappe.db.get_value(tanzania.MEMBERSHIP_DOCTYPE, {"member": member}, "name")

	return name


def _confirm_fee(membership: str, person: dict) -> str:
	"""The clerk's half: record that the subscription was paid at the branch.

	TRCS is seeded with the Manual gateway — see `tanzania._payment_gateway` —
	so there is no gateway callback and nothing settles itself. Somebody at the
	branch takes the money and records it, which is `payment.record_confirmation`
	and is the only honest way a membership becomes payable-satisfied here.

	Done as the branch approver, because they hold `Branch Coordinator`, which is
	the role a person at the counter would have.
	"""
	from vmmsx.member.services import membership as membership_service
	from vmmsx.member.services import payment

	frappe.set_user(tanzania.BRANCH_APPROVER)

	try:
		document = frappe.get_doc(tanzania.MEMBERSHIP_DOCTYPE, membership)
		changed = payment.record_confirmation(
			document,
			receipt=f"{RECEIPT_PREFIX}-{abs(hash(person['email'])) % 10**6:06d}",
		)

		if changed:
			document.save(ignore_permissions=True)

		# A fee confirmed after the approval has already settled is the moment
		# the membership becomes activatable, and nothing else will re-ask.
		membership_service.try_activate(document)
	finally:
		frappe.set_user("Administrator")

	return "fee confirmed"


def _decide_membership(approver: str, membership: str, person: dict, stage: str) -> str:
	"""One rung's decision on a membership. Same gate as a volunteer application."""
	from vmmsx.api.approvals import decide
	from vmmsx.approvals import states

	if stage == "branch" and person["outcome"] == "rejected":
		verdict, reason = states.DECISION_REJECTED, person["reason"]
	else:
		verdict, reason = states.DECISION_APPROVED, None

	frappe.set_user(approver)

	try:
		decide(
			doctype=tanzania.MEMBERSHIP_DOCTYPE,
			name=membership,
			decision=verdict,
			reason=reason,
		)
	finally:
		frappe.set_user("Administrator")

	return f"{stage}: {verdict.lower()}"


# --- making it look its age ---------------------------------------------------


def _backdate() -> list[dict]:
	"""Move each person's paper trail back to when they say they applied.

	**The one thing here that cannot be done by acting like a user**, because a
	user cannot file a form last March. Everything else in this module is the
	product's own behaviour; this is the seed admitting that it ran today.

	`creation` on the application and on everything the approval produced — the
	volunteer record, the decision rows, the Red Profile — plus `joined_on`,
	which is the date the register actually shows. Written with
	`update_modified=False` so the rewrite does not itself stamp today onto
	`modified` and undo half the effect.
	"""
	rows = []

	for person in VOLUNTEERS:
		profile = frappe.db.get_value("Red Profile", {"user": person["email"]}, "name")

		if not profile:
			continue

		when = add_days(today(), -int(person["days_ago"]))
		application = frappe.db.get_value(
			tanzania.APPLICATION_DOCTYPE, {"red_profile": profile}, "name"
		)

		touched = 0

		for doctype, name in (
			("Red Profile", profile),
			(tanzania.APPLICATION_DOCTYPE, application),
		):
			if name:
				frappe.db.set_value(doctype, name, "creation", when, update_modified=False)
				touched += 1

		volunteer = frappe.db.get_value("VMMS Volunteer", {"red_profile": profile}, "name")

		if volunteer:
			frappe.db.set_value("VMMS Volunteer", volunteer, "creation", when, update_modified=False)
			# The register's own "member since". Not derived from `creation`,
			# which is why setting one and not the other leaves a volunteer who
			# joined today according to every screen that shows this field.
			frappe.db.set_value("VMMS Volunteer", volunteer, "joined_on", when, update_modified=False)
			touched += 1

		rows.append({"key": person["email"], "status": f"{touched} records dated {when}"})

	for person in MEMBERS:
		profile = frappe.db.get_value("Red Profile", {"user": person["email"]}, "name")
		member = frappe.db.get_value("VMMS Member", {"red_profile": profile}, "name") if profile else None

		if not member:
			continue

		when = add_days(today(), -int(person["days_ago"]))
		membership = frappe.db.get_value(tanzania.MEMBERSHIP_DOCTYPE, {"member": member}, "name")
		touched = 0

		for doctype, name in (("VMMS Member", member), (tanzania.MEMBERSHIP_DOCTYPE, membership)):
			if name:
				frappe.db.set_value(doctype, name, "creation", when, update_modified=False)
				touched += 1

		# **`valid_from` moves and `valid_to` does not.** `activate()` computes
		# the expiry from the day it ran, and a life membership has no expiry at
		# all. Moving the start without recomputing the end would produce an
		# ordinary membership that ran for two years, so the pair is rewritten
		# together, through the same `_valid_to` the service itself uses.
		if membership and frappe.db.get_value(tanzania.MEMBERSHIP_DOCTYPE, membership, "valid_from"):
			_redate_validity(membership, when)
			touched += 1

		rows.append({"key": f"{person['email']} (member)", "status": f"{touched} records dated {when}"})

	return rows


def _redate_validity(membership: str, start) -> None:
	"""Move a membership's term to when it actually began.

	Uses `membership._valid_to`, not arithmetic written here: how long a term
	runs is the membership *type*'s answer — a duration in days, or nothing at
	all for a lifetime plan — and a second implementation of that would drift
	from the one the product uses the first time somebody edits a plan.
	"""
	from vmmsx.member.services import membership as membership_service

	document = frappe.get_doc(tanzania.MEMBERSHIP_DOCTYPE, membership)
	valid_to = membership_service._valid_to(membership_service.type_of(document), start)

	frappe.db.set_value(
		tanzania.MEMBERSHIP_DOCTYPE,
		membership,
		{"valid_from": start, "valid_to": valid_to},
		update_modified=False,
	)


def _print(report: dict) -> None:
	print("\n" + "=" * 66)
	print("Tanzania Red Cross Society — people")
	print("=" * 66)

	for section, entries in report.items():
		print(f"\n{section}")

		for row in entries:
			detail = row.get("trail") or row.get("where") or ""
			print(f"  {row['status']:<28} {row['key']}{'  ' + detail if detail else ''}")

	people = {p["email"] for p in VOLUNTEERS} | {p["email"] for p in MEMBERS}
	branches = {p["branch"] for p in VOLUNTEERS} | {p["branch"] for p in MEMBERS}
	both = {p["email"] for p in VOLUNTEERS} & {p["email"] for p in MEMBERS}

	print(f"\nEvery seeded login signs in with: {PASSWORD}")
	print(f"  approvers:  {tanzania.SUB_BRANCH_APPROVER}, {tanzania.BRANCH_APPROVER}")
	print(f"  volunteers: {len(VOLUNTEERS)} applications")
	print(f"  members:    {len(MEMBERS)} memberships, {len(both)} of them people who also volunteer")
	print(f"  in total:   {len(people)} people across {len(branches)} branches\n")
