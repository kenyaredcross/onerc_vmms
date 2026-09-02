# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Fixtures for the Volunteer module. Nothing here is mocked.

Geo comes from **core's** geo fixtures, identity from core's Red Profile,
authority from real `Geo Assignment` rows, approval from a real
`VMMS Approval Workflow` driving the real engine, and the learning seam from the
real `LMS Enrollment` doctype the site has installed. If a test passes here, the
thing it tested actually works end to end.

**Two hierarchies again**, deliberately shaped and named differently, because
the level a volunteer is placed at is a society's choice (ACC-03) and the code
must not hold an opinion:

    Uplands (region)                     Riverine (province)
    └── Nyeri (county)     ← approver    └── Lower Shire (district)  ← approver
        ├── Mweiga (ward)                    └── Chikwawa (ward)
        └── Kieni (ward)

Neither "county" nor "district" appears in any assertion about *behaviour* —
they are labels the fixtures chose, and the same code routes correctly in both.

**No certification or course name appears in a source file, so the fixtures
supply both.** `CERT_FIRST_AID` and friends are fixture data with deliberately
concrete names, precisely to demonstrate that the app never reads one.
"""

from contextlib import contextmanager

import frappe
from onerc_core.geo.tests import fixtures as geo_fixtures

TEST_PREFIX = "VOLTEST"
USER_DOMAIN = "@volunteer.test"

# Level key prefixes for the two societies these tests build. Kept distinct from
# the approval engine's fixtures (VK/VG) and the Member module's (MA/MB) so the
# three suites never delete each other's geo.
SOCIETY_A_PREFIX = "VLA"
SOCIETY_B_PREFIX = "VLB"
LEVEL_PREFIXES = (SOCIETY_A_PREFIX, SOCIETY_B_PREFIX)

# Society-named roles. Nothing in the Volunteer module names one; they arrive as
# configuration on an approval stage or in a settings field.
APPROVER_ROLE = f"{TEST_PREFIX} Volunteer Approver"
APPLICANT_ROLE = f"{TEST_PREFIX} Applicant"

# Who may *see* a volunteer, as distinct from who may decide an application.
# Deliberately a different role from APPROVER_ROLE: "where may I approve" and
# "where may I view" are different questions, and keeping them apart is what
# stops a person-gate test from passing because geo scoping denied the user
# first.
SCOPE_ROLE = f"{TEST_PREFIX} Volunteer Viewer"

TEST_ROLES = (APPROVER_ROLE, APPLICANT_ROLE, SCOPE_ROLE)

SETTINGS_DOCTYPE = "National Society Settings"

# The Custom Fields vmmsx installs and registers through onerc_scopeable_doctypes
# and reads through volunteer/services/society.py.
SCOPE_ROLE_SETTING = "vmms_volunteer_scope_role"
ANCHOR_LEVEL_SETTING = "vmms_volunteer_anchor_level"
PROVISION_SETTING = "vmms_volunteer_provision_employee"
COMPANY_SETTING = "vmms_volunteer_employee_company"

VOLUNTEER_DOCTYPE = "VMMS Volunteer"
APPLICATION_DOCTYPE = "VMMS Volunteer Application"
CERTIFICATION_DOCTYPE = "VMMS Certification"
CERTIFICATION_TYPE_DOCTYPE = "VMMS Certification Type"
MAPPING_DOCTYPE = "VMMS Course Mapping"
TIME_LOG_DOCTYPE = "VMMS Time Log"
CATEGORY_DOCTYPE = "VMMS Time Log Category"
WORKFLOW_DOCTYPE = "VMMS Approval Workflow"

# The deployment module's, used by the coordinator's view: a volunteer's
# deployment history is read from the roster, so this suite has to be able to
# put somebody on one.
DEPLOYMENT_DOCTYPE = "VMMS Deployment"
TERMS_DOCTYPE = "VMMS Terms of Reference"
# ERPNext's own, and the programme every terms of reference is written under.
PROJECT_DOCTYPE = "Project"

SKILL_DOCTYPE = "VMMS Skill"
MOTIVATION_DOCTYPE = "VMMS Motivation"
AVAILABILITY_DOCTYPE = "VMMS Availability Slot"
IDENTIFICATION_TYPE_DOCTYPE = "Identification Type"

MEMBER_DOCTYPE = "VMMS Member"

# Certification type keys the tests configure. Concrete, memorable names, chosen
# so that a grep of the app's source for any of them finds nothing — which is
# the point being made.
CERT_FIRST_AID = f"{TEST_PREFIX}-first-aid"
CERT_PSYCHOSOCIAL = f"{TEST_PREFIX}-psychosocial"
CERT_NEVER_EXPIRES = f"{TEST_PREFIX}-code-of-conduct"

# Course identifiers, as a learning system would name them.
COURSE_FIRST_AID = f"{TEST_PREFIX}-course-first-aid"
COURSE_UNMAPPED = f"{TEST_PREFIX}-course-unmapped"

# Application-vocabulary keys, fixture-owned for the same reason the
# certification keys above are: a grep of the app's source for any of them
# finds nothing.
SKILL_SWIMMING = f"{TEST_PREFIX}-swimming"
SKILL_RADIO = f"{TEST_PREFIX}-radio-operation"
MOTIVATION_SERVICE = f"{TEST_PREFIX}-service"
AVAILABILITY_WEEKENDS = f"{TEST_PREFIX}-weekends"
AVAILABILITY_NIGHTS = f"{TEST_PREFIX}-night-shifts"

# A test-owned Identification Type, rather than depending on core's seeded
# national_id/passport rows: those are fixture data belonging to a site's
# migration, not to this suite, and a test asserting against its own row is
# unaffected by a society renaming or deactivating the seeded ones.
ID_TYPE = f"{TEST_PREFIX}-national-id"

# Every vocabulary row this suite creates, so `reset()` removes exactly what it
# made. Listed once rather than spelled out at teardown: a key added above and
# forgotten below is a row that survives into the next run and quietly changes
# what a capability search finds.
VOCABULARY_KEYS = (
	(SKILL_DOCTYPE, SKILL_SWIMMING),
	(SKILL_DOCTYPE, SKILL_RADIO),
	(MOTIVATION_DOCTYPE, MOTIVATION_SERVICE),
	(AVAILABILITY_DOCTYPE, AVAILABILITY_WEEKENDS),
	(AVAILABILITY_DOCTYPE, AVAILABILITY_NIGHTS),
	(IDENTIFICATION_TYPE_DOCTYPE, ID_TYPE),
)


# --- geo, through core ----------------------------------------------------


def _ladder(prefix: str, labels: list[str]) -> list[str]:
	"""A level ladder that does not claim to be the society's lowest.

	`geo_fixtures.make_levels` flags its deepest level `is_lowest`, and core
	permits exactly one active lowest level per site — so building two societies
	that way makes the second one refuse to save. These tests need two ladders
	coexisting and never assert on `is_lowest`, so they are created without it.
	"""
	return [
		geo_fixtures.make_level(f"{prefix}-{order}", label, order)
		for order, label in enumerate(labels, start=1)
	]


def build_society_a() -> dict:
	"""Region → County → Ward."""
	region, county, ward = _ladder(SOCIETY_A_PREFIX, ["Region", "County", "Ward"])

	tree = {"levels": {"region": region, "county": county, "ward": ward}}
	tree["region"] = geo_fixtures.make_node("Uplands", region, None, is_group=True)
	tree["county"] = geo_fixtures.make_node("Nyeri", county, tree["region"], is_group=True)
	tree["ward"] = geo_fixtures.make_node("Mweiga", ward, tree["county"])
	tree["other_ward"] = geo_fixtures.make_node("Kieni", ward, tree["county"])

	return tree


def build_society_b() -> dict:
	"""Province → District → Ward. A different shape and different words."""
	province, district, ward = _ladder(SOCIETY_B_PREFIX, ["Province", "District", "Ward"])

	tree = {"levels": {"province": province, "district": district, "ward": ward}}
	tree["region"] = geo_fixtures.make_node("Riverine", province, None, is_group=True)
	tree["district"] = geo_fixtures.make_node("Lower Shire", district, tree["region"], is_group=True)
	tree["ward"] = geo_fixtures.make_node("Chikwawa", ward, tree["district"])

	return tree


# --- people ---------------------------------------------------------------


def make_role(name: str) -> str:
	if not frappe.db.exists("Role", name):
		frappe.get_doc({"doctype": "Role", "role_name": name, "desk_access": 1}).insert()

	return name


def make_user(handle: str, roles: list[str] | None = None) -> str:
	"""A System User with the given roles and nothing else.

	Never a System Manager unless a test is specifically about one: that role is
	core's documented scope bypass, so a user holding it would pass checks for
	the wrong reason.
	"""
	email = f"{handle}{USER_DOMAIN}"

	if frappe.db.exists("User", email):
		frappe.delete_doc("User", email, force=True)

	for role in roles or []:
		make_role(role)

	frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": handle.replace("_", " ").title(),
			"send_welcome_email": 0,
			"user_type": "System User",
			"roles": [{"role": role} for role in roles or []],
		}
	).insert()
	frappe.clear_cache(user=email)

	return email


#: A date of birth for anybody the fixtures make. Old enough to volunteer, and
#: fixed rather than derived from `today()` so an age-dependent assertion cannot
#: change its answer on somebody's birthday.
DEFAULT_DATE_OF_BIRTH = "1990-01-01"


def make_profile(first_name: str = "Wanjiru", last_name: str = "Kamau", **kwargs) -> str:
	"""A Red Profile — core's identity spine. The volunteer links to this.

	**It carries a date of birth by default**, because `assert_ready` requires
	one to submit a volunteer application: optional on the profile, mandatory
	there, the same asymmetry identification has. Without it every suite that
	submits an application would be arranging an applicant the product refuses,
	and would be testing the refusal rather than the thing it means to test.

	Pass `date_of_birth=None` to build somebody core knows nothing about — which
	is what a test *about* that requirement wants.
	"""
	slug = f"{first_name}.{last_name}".lower()
	values = {
		"doctype": "Red Profile",
		"first_name": first_name,
		"last_name": last_name,
		"email": kwargs.pop("email", f"{slug}.{frappe.generate_hash(length=6)}{USER_DOMAIN}"),
		"date_of_birth": DEFAULT_DATE_OF_BIRTH,
	}
	values.update(kwargs)

	return frappe.get_doc(values).insert().name


def make_assignment(user: str, role: str, geo_node: str) -> str:
	"""Authority: a role held at a place. Core's doctype, used as core intends."""
	make_role(role)

	return (
		frappe.get_doc(
			{
				"doctype": "Geo Assignment",
				"user": user,
				"role": role,
				"geo_node": geo_node,
				"is_active": 1,
			}
		)
		.insert()
		.name
	)


# --- configuration --------------------------------------------------------


def make_certification_type(key: str, validity_days: int = 365, **overrides):
	"""A certification the society recognises, and how long it lasts."""
	if frappe.db.exists(CERTIFICATION_TYPE_DOCTYPE, key):
		frappe.delete_doc(CERTIFICATION_TYPE_DOCTYPE, key, force=True)

	values = {
		"doctype": CERTIFICATION_TYPE_DOCTYPE,
		"certification_type_key": key,
		"certification_type_name": key.replace(f"{TEST_PREFIX}-", "").replace("-", " ").title(),
		"validity_days": validity_days,
		"blocks_deployment_when_lapsed": 1,
		"is_active": 1,
	}
	values.update(overrides)

	return frappe.get_doc(values).insert()


def make_mapping(external_course: str, certification_type: str, **overrides):
	"""One course, one certification. The whole of the learning seam's config."""
	existing = frappe.db.get_value(MAPPING_DOCTYPE, {"external_course": external_course}, "name")

	if existing:
		frappe.delete_doc(MAPPING_DOCTYPE, existing, force=True)

	values = {
		"doctype": MAPPING_DOCTYPE,
		"external_course": external_course,
		"course_label": external_course,
		"certification_type": certification_type,
		"is_active": 1,
	}
	values.update(overrides)

	return frappe.get_doc(values).insert()


def make_skill(key: str = SKILL_SWIMMING, **overrides):
	"""A society-configured skill, for the application's structured vocabulary."""
	return _make_vocab(SKILL_DOCTYPE, "skill_key", "skill_name", key, overrides)


def make_motivation(key: str = MOTIVATION_SERVICE, **overrides):
	"""A society-configured motivation, for the application's structured vocabulary."""
	return _make_vocab(MOTIVATION_DOCTYPE, "motivation_key", "motivation_name", key, overrides)


def make_availability_slot(key: str = AVAILABILITY_WEEKENDS, **overrides):
	"""A society-configured availability slot, for the application's structured vocabulary."""
	return _make_vocab(AVAILABILITY_DOCTYPE, "slot_key", "slot_name", key, overrides)


def _make_vocab(doctype: str, key_field: str, name_field: str, key: str, overrides: dict):
	if frappe.db.exists(doctype, key):
		return frappe.get_doc(doctype, key)

	values = {
		"doctype": doctype,
		key_field: key,
		name_field: key.replace(f"{TEST_PREFIX}-", "").replace("-", " ").title(),
		"is_active": 1,
	}
	values.update(overrides)

	return frappe.get_doc(values).insert()


def make_identification_type(key: str = ID_TYPE, **overrides) -> str:
	"""A test-owned Identification Type — the application's mandatory-at-submission kind."""
	if frappe.db.exists(IDENTIFICATION_TYPE_DOCTYPE, key):
		return key

	values = {
		"doctype": IDENTIFICATION_TYPE_DOCTYPE,
		"identification_type_key": key,
		"identification_type_name": key.replace(f"{TEST_PREFIX}-", "").replace("-", " ").title(),
		"is_active": 1,
	}
	values.update(overrides)

	frappe.get_doc(values).insert()

	return key


def test_country() -> str:
	"""Any Country the site already has, so citizenship is a real Link value.

	Not fixture-created and not a literal like "Kenya": Country is Frappe's own
	shipped list, and this suite has no business asserting which countries a
	site carries. Defaulting `country_of_citizenship` from the society's own
	settings is the feature under test elsewhere; this is only what a fixture
	overrides it with so a bare application does not depend on that setting
	being configured on whichever site the suite happens to run against.
	"""
	return frappe.db.get_value("Country", {}, "name", order_by="name") or "Kenya"


def test_language() -> str:
	"""Any language Frappe already ships, so a language selector row is real.

	Not a fixture-created row: Language is core's own doctype and this suite has
	no business inventing a second one, so this just borrows whichever the site
	already has.
	"""
	return frappe.db.get_value("Language", {}, "name", order_by="name") or "en"


def make_workflow(role: str = APPROVER_ROLE, **overrides):
	"""One approval workflow governing VMMS Volunteer Application.

	Deliberately built through the real config doctype: an application must go
	through the engine as configured, not through anything these tests wrote.
	"""
	existing = frappe.db.get_value(WORKFLOW_DOCTYPE, {"workflow_for": APPLICATION_DOCTYPE}, "name")

	if existing:
		frappe.delete_doc(WORKFLOW_DOCTYPE, existing, force=True)

	# The stage names a role, and a Link refuses one that does not exist yet. The
	# role is the society's, which is exactly why the workflow has to be handed
	# one rather than assume it.
	make_role(role)

	values = {
		"doctype": WORKFLOW_DOCTYPE,
		"workflow_for": APPLICATION_DOCTYPE,
		"geo_node_field": "geo_node",
		# The cooldown identifies the same person across two applications by
		# their profile rather than by who typed the form.
		"applicant_field": "red_profile",
		"stages": [
			{
				"sequence": 1,
				"stage_label": "Volunteer Review",
				"required_role": role,
				"resolution_rule": "nearest_ancestor",
				"completion_rule": "single",
				"can_reject": 1,
				"is_optional": 0,
				"sla_days": 5,
				"on_sla_breach": "escalate_up",
			}
		],
	}
	values.update(overrides)

	return frappe.get_doc(values).insert()


def grant_doctype_access(doctype: str, role: str) -> None:
	"""Let a society role read and write a doctype, the way an administrator would.

	An approver acting on an application *saves* it, so the role a society names
	on an approval stage needs write access to the governed doctype. The shipped
	doctypes grant only System Manager, because which society role gets this is
	configuration — so the tests grant it with a Custom DocPerm.
	"""
	from frappe.permissions import add_permission, update_permission_property

	make_role(role)
	add_permission(doctype, role, 0)

	for permission in ("read", "write", "create", "share", "delete"):
		update_permission_property(doctype, role, 0, permission, 1)

	frappe.clear_cache(doctype=doctype)


# --- society settings -----------------------------------------------------


def _set_setting(fieldname: str, value) -> None:
	"""Write one settings value the way an administrator saving the form would.

	Straight onto the single, with the document cache dropped so the next read
	sees it. That is what enforcement and the services observe.
	"""
	frappe.db.set_single_value(SETTINGS_DOCTYPE, fieldname, value)
	frappe.clear_document_cache(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE)


def set_scope_role(role: str | None) -> None:
	"""Point the society's volunteer scope role at a role — or clear it.

	Clearing it is the shipped default: no role, nobody but an administrator
	reads a volunteer record.
	"""
	_set_setting(SCOPE_ROLE_SETTING, role)


def set_anchor_level(geo_level: str | None) -> None:
	"""Point the society's ACC-03 setting at a level — or clear it."""
	_set_setting(ANCHOR_LEVEL_SETTING, geo_level)


def set_provisioning(enabled: bool, company: str | None = None) -> None:
	"""Switch HR provisioning on or off, and name the company it uses."""
	_set_setting(PROVISION_SETTING, 1 if enabled else 0)
	_set_setting(COMPANY_SETTING, company)


def grant_volunteer_scope(user: str, *nodes: str) -> None:
	"""Let this user see volunteers at these nodes and everything beneath them.

	Separate from `make_assignment(user, APPROVER_ROLE, ...)` on purpose. Being
	able to *see* a volunteer is what geo scoping governs; being the person an
	application routed to is what the approval engine's person-gate governs.
	Tests that assert a refusal need the first so they can prove it was the
	second.
	"""
	make_role(SCOPE_ROLE)
	frappe.get_doc("User", user).add_roles(SCOPE_ROLE)

	for node in nodes:
		make_assignment(user, SCOPE_ROLE, node)


# --- records --------------------------------------------------------------


def make_application(profile: str, geo_node: str, **overrides):
	"""An application, created the way the API creates one.

	Person facts are prepared on Red Profile first. The application itself gets
	only its Serving Branch and declarations, which is the production boundary.
	The legacy keyword names remain accepted here so focused tests can express a
	missing profile fact without every call site changing at once.
	"""
	country_of_citizenship = overrides.pop("country_of_citizenship", test_country())
	residency_type = overrides.pop("residency_type", "Local")
	home_geo_node = overrides.pop("home_geo_node", geo_node)
	country_of_residence = overrides.pop("country_of_residence", None)
	residence_address = overrides.pop("residence_address", None)
	id_type = overrides.pop("id_type", make_identification_type())
	id_number = overrides.pop("id_number", f"{TEST_PREFIX}-{frappe.generate_hash(length=8)}")

	person = frappe.get_doc("Red Profile", profile)
	person.country_of_citizenship = country_of_citizenship
	person.residency_type = residency_type
	person.home_geo_node = home_geo_node
	person.country_of_residence = country_of_residence
	person.residence_address = residence_address

	if id_type and id_number:
		person.set(
			"identifications",
			[{"id_type": id_type, "id_number": id_number, "is_primary": 1}],
		)
	else:
		person.set("identifications", [])

	person.save()

	values = {
		"doctype": APPLICATION_DOCTYPE,
		"red_profile": profile,
		"geo_node": geo_node,
		# What every real registration now carries. Defaulted here rather than in
		# each suite because these are conditions of submitting and of approving,
		# and a fixture without them models an application nobody could actually
		# make — see `accept_declarations` for the declarations' own half.
		"emergency_contacts": emergency_contact(),
	}
	values.update(overrides)

	application = frappe.get_doc(values)
	accept_declarations(application)

	return application.insert()


def emergency_contact(**values) -> list[dict]:
	"""One emergency contact, in the shape a registration stores.

	`application.assert_approvable` refuses an approval without one the applicant
	has permitted us to call, so a suite about routing or acceptance needs one
	without wanting to know why. A test about the requirement itself passes
	`emergency_contacts=[]`; those live in the registration suite, which owns the
	rule.
	"""
	row = {
		"contact_name": "Mercy Otieno",
		"relationship": "Sister",
		"primary_phone": "+254700000001",
		"may_contact_in_emergency": 1,
	}
	row.update(values)

	return [row]


def required_declarations() -> list[str]:
	"""The keys a caller would send with every required box ticked.

	Read from the live list rather than named here, so this suite does not have
	to know which four the app ships and a society's fifth is accepted without
	anybody editing this file.
	"""
	from vmmsx.registration.services import declarations

	return [row["name"] for row in declarations.shown_on(APPLICATION_DOCTYPE) if row["is_required"]]


def accept_declarations(application) -> list[str]:
	"""Record those acceptances on a document being built directly.

	`declarations.assert_accepted` refuses a submission with a required
	declaration unaccepted whichever door it came through, so a fixture that
	builds an application by hand has to do what every real door does.
	"""
	from vmmsx.registration.services import declarations

	return declarations.apply(application, required_declarations())


def make_volunteer(profile: str, home_geo_node: str):
	"""A volunteer directly, for tests that are not about the approval path."""
	from vmmsx.volunteer.services import volunteer as volunteer_service

	return volunteer_service.ensure(profile, home_geo_node=home_geo_node)


def make_member(profile: str):
	"""A member for the same person — for the two-provider tests.

	Created through the Member module's own service and then refreshed, which is
	what writes its affiliation row. Nothing about volunteering is involved; that
	is the point.
	"""
	from vmmsx.member.services import member as member_service

	member = member_service.ensure(profile)
	member_service.refresh(member.name)

	return member


def make_project(geo_node: str) -> str:
	"""The programme this suite's terms of reference are written under.

	One per node, found by name afterwards. Borrowed in shape from the Deployment
	module's own fixture and kept here for the reason `make_deployment` gives
	about its terms of reference: importing that module would drag a second geo
	hierarchy into every run of this suite for one record.

	Inserted as Administrator because `project.on_validate` refuses a programme
	anchored where the caller does not run, and a fixture is arranging scenery
	rather than exercising that rule.
	"""
	name = f"{TEST_PREFIX} Programme {geo_node}"
	existing = frappe.db.get_value(PROJECT_DOCTYPE, {"project_name": name}, "name")

	if existing:
		return existing

	caller = frappe.session.user
	frappe.set_user("Administrator")

	try:
		return frappe.get_doc(
			{
				"doctype": PROJECT_DOCTYPE,
				"project_name": name,
				"company": frappe.db.get_value("Company", {}, "name"),
				"status": "Open",
				"vmms_geo_node": geo_node,
			}
		).insert().name
	finally:
		frappe.set_user(caller)


def make_deployment(geo_node: str, participants: list[str] | None = None, **overrides):
	"""A deployment running in *this* suite's geo, with a roster.

	Built here rather than imported from `deployment/tests/fixtures.py`, which
	builds its own societies under its own level prefixes: a volunteer anchored
	in this suite's tree cannot be put on a deployment anchored in that one, and
	borrowing the fixture would drag a second geo hierarchy into every run of
	this suite for one record.

	Its terms of reference are generated per call, so a test that changes one
	does not change another's. Frappe rolls the test transaction back once per
	class rather than per method, and a shared ToR is exactly the kind of state
	that leaks between them.
	"""
	from frappe.utils import add_days, today

	key = f"{TEST_PREFIX}-tor-{frappe.generate_hash(length=8)}"
	# A complete mission document, because an incomplete one cannot be submitted
	# and an unsubmitted one takes no deployment. `terms.REQUIRED_AT_SUBMISSION`
	# is the list; nothing below the purpose is read by any assertion here. The
	# programme and the scope are this suite's own node, so the deployment about
	# to be anchored there is inside the terms that govern it.
	terms = frappe.get_doc(
		{
			"doctype": TERMS_DOCTYPE,
			"tor_key": key,
			"tor_name": key.replace(f"{TEST_PREFIX}-", "").replace("-", " ").title(),
			"purpose": "Whatever this society uses these terms for.",
			"approval_mode": "direct",
			"is_active": 1,
			"geo_scope": geo_node,
			"project": make_project(geo_node),
			"expected_start_date": today(),
			"expected_end_date": add_days(today(), 7),
			"mission_background": "<p>Why this society keeps a written specification for this work.</p>",
			"objectives": [{"objective": "Do the work these terms describe."}],
			"expected_outputs": [{"output": "A record of what was done."}],
			"stakeholders": [{"designation": "Branch Coordinator"}],
			"itinerary": [{"activity_date": today(), "activity": "Briefing"}],
			"has_no_resources": 1,
		}
	).insert()
	# Submitted, because `terms.assert_offered` refuses a draft: a deployment
	# cannot be run under wording that can still be edited.
	terms.submit()

	values = {
		"doctype": DEPLOYMENT_DOCTYPE,
		"terms_of_reference": terms.name,
		"geo_node": geo_node,
		"coordinator": frappe.session.user,
		"start_date": today(),
		"end_date": add_days(today(), 7),
		"status": "Planned",
	}
	values.update(overrides)

	deployment = frappe.get_doc(values).insert()

	# The roster is a register of `VMMS Deployment Assignment` documents rather
	# than a child table, so it is raised after the insert. `Assigned` — placed
	# by a coordinator, not asked — because a test naming a roster up front is
	# describing who went.
	from vmmsx.deployment.services import assignment

	for volunteer in participants or []:
		assignment.create(deployment, volunteer, status=assignment.STATUS_ASSIGNED)

	return deployment


def make_time_log(volunteer: str, geo_node: str, **overrides):
	"""A time log, with the general kind and plausible values by default."""
	from frappe.utils import today

	values = {
		"doctype": TIME_LOG_DOCTYPE,
		"volunteer": volunteer,
		"geo_node": geo_node,
		"log_type": "general",
		"activity_date": today(),
		"hours": 4,
	}
	values.update(overrides)

	return frappe.get_doc(values).insert()


@contextmanager
def acting_as(user: str):
	"""Run a block as somebody else, and always put the session back."""
	previous = frappe.session.user
	frappe.set_user(user)

	try:
		yield
	finally:
		frappe.set_user(previous)


# --- teardown -------------------------------------------------------------


def reset() -> None:
	"""Drop fixture rows left behind by a run that committed."""
	set_anchor_level(None)
	set_provisioning(False, None)

	# Order matters: a time log may name a deployment, and a deployment names a
	# terms of reference, so each goes before the thing it points at.
	for doctype in (
		TIME_LOG_DOCTYPE,
		CERTIFICATION_DOCTYPE,
		MAPPING_DOCTYPE,
		APPLICATION_DOCTYPE,
		DEPLOYMENT_DOCTYPE,
	):
		for name in frappe.get_all(doctype, pluck="name"):
			frappe.delete_doc(doctype, name, force=True)

	# Only this suite's own, matched by the prefix its keys carry: the deployment
	# suite's terms are none of this one's business.
	for name in frappe.get_all(
		TERMS_DOCTYPE, filters={"tor_key": ("like", f"{TEST_PREFIX}-%")}, pluck="name"
	):
		frappe.delete_doc(TERMS_DOCTYPE, name, force=True)

	# After the terms that point at them, and named rather than emptied
	# wholesale: `Project` is ERPNext's and this bench holds other people's.
	for name in frappe.get_all(
		PROJECT_DOCTYPE, filters={"project_name": ("like", f"{TEST_PREFIX}%")}, pluck="name"
	):
		frappe.delete_doc(PROJECT_DOCTYPE, name, force=True)

	for name in frappe.get_all(VOLUNTEER_DOCTYPE, pluck="name"):
		frappe.delete_doc(VOLUNTEER_DOCTYPE, name, force=True)

	# Members are created by the two-provider tests and are otherwise none of
	# this suite's business, so only this suite's are removed — matched by the
	# test domain on the profile they hang off.
	for name in frappe.get_all(MEMBER_DOCTYPE, pluck="name"):
		profile = frappe.db.get_value(MEMBER_DOCTYPE, name, "red_profile")
		email = frappe.db.get_value("Red Profile", profile, "email") if profile else None

		if email and email.endswith(USER_DOMAIN):
			frappe.delete_doc(MEMBER_DOCTYPE, name, force=True)

	for key in (CERT_FIRST_AID, CERT_PSYCHOSOCIAL, CERT_NEVER_EXPIRES):
		if frappe.db.exists(CERTIFICATION_TYPE_DOCTYPE, key):
			frappe.delete_doc(CERTIFICATION_TYPE_DOCTYPE, key, force=True)

	for doctype, key in VOCABULARY_KEYS:
		if frappe.db.exists(doctype, key):
			frappe.delete_doc(doctype, key, force=True)

	workflow = frappe.db.get_value(WORKFLOW_DOCTYPE, {"workflow_for": APPLICATION_DOCTYPE}, "name")

	if workflow:
		frappe.delete_doc(WORKFLOW_DOCTYPE, workflow, force=True)

	for profile in frappe.get_all(
		"Red Profile", filters={"email": ("like", f"%{USER_DOMAIN}")}, pluck="name"
	):
		frappe.delete_doc("Red Profile", profile, force=True)

	for user in frappe.get_all("User", filters={"email": ("like", f"%{USER_DOMAIN}")}, pluck="name"):
		frappe.delete_doc("User", user, force=True)

	_reset_geo()


def _reset_geo() -> None:
	"""Geo goes deepest-first: NestedSet refuses to delete a node with children."""
	levels = [
		level for level in frappe.get_all("Geo Level", pluck="name") if level.split("-")[0] in LEVEL_PREFIXES
	]

	if not levels:
		return

	for node in frappe.get_all(
		"Geo Node", filters={"geo_level": ("in", levels)}, order_by="lft desc", pluck="name"
	):
		for assignment in frappe.get_all("Geo Assignment", filters={"geo_node": node}, pluck="name"):
			frappe.delete_doc("Geo Assignment", assignment, force=True)

		frappe.delete_doc("Geo Node", node, force=True)

	for level in levels:
		frappe.delete_doc("Geo Level", level, force=True)


def teardown() -> None:
	reset()

	for role in TEST_ROLES:
		if frappe.db.exists("Role", role):
			frappe.delete_doc("Role", role, force=True)
