# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Fixtures for the self-service journey. Nothing here is mocked.

Geo comes from **core's** geo fixtures. Identity is a real `Red Profile` written
by the real `before_insert` hook. Approval is a real `VMMS Approval Workflow`
driving the real engine, decided through the real `api/approvals.py` gate.
Payment is the real `onerc_payments` Manual driver. And the registration itself
goes through **Frappe's own `web_form.accept()`**, the function the browser calls
— not a helper that inserts a document and pretends.

That last one is the point of this suite. Every other way of creating an
application already had tests; what had none was the path where a person who
holds no permission on anything fills in a form and ends up with an identity, a
record and, eventually, a role. If a test here passes, that path works.

**A society named in data, never in code.** Roles, levels, membership types and
workflow stages are all built here with names that appear nowhere in
`vmmsx/registration/`. The suite would pass unchanged with every one of them
renamed, which is the property the whole app is arranged around.
"""

import json
from contextlib import contextmanager

import frappe
from onerc_core.geo.tests import fixtures as geo_fixtures

TEST_PREFIX = "REGTEST"
USER_DOMAIN = "@registration.test"

# Kept distinct from the other suites' level prefixes so no two suites can
# delete each other's geo.
LEVEL_PREFIX = "RG"

# Society-named roles. Nothing under `vmmsx/registration/` names any of them:
# they arrive as configuration on a settings field or on an approval stage.
APPROVER_ROLE = f"{TEST_PREFIX} Branch Approver"
SELF_SERVICE_ROLE = f"{TEST_PREFIX} Applicant"
VOLUNTEER_ROLE = f"{TEST_PREFIX} Volunteer"
MEMBER_ROLE = f"{TEST_PREFIX} Member"

TEST_ROLES = (APPROVER_ROLE, SELF_SERVICE_ROLE, VOLUNTEER_ROLE, MEMBER_ROLE)

# Membership type keys. In data, precisely so that no source file knows them.
TYPE_AUTO = f"{TEST_PREFIX}-auto"
TYPE_ROUTED = f"{TEST_PREFIX}-routed"

TEMPLATE_KEY = f"{TEST_PREFIX}-certificate"

SETTINGS_DOCTYPE = "National Society Settings"
IDENTIFICATION_TYPE_DOCTYPE = "Identification Type"
ID_TYPE = f"{TEST_PREFIX}-national-id"
APPLICATION_DOCTYPE = "VMMS Volunteer Application"
VOLUNTEER_DOCTYPE = "VMMS Volunteer"
MEMBERSHIP_DOCTYPE = "VMMS Membership"
MEMBER_DOCTYPE = "VMMS Member"
TYPE_DOCTYPE = "VMMS Membership Type"
TEMPLATE_DOCTYPE = "VMMS Template"
WORKFLOW_DOCTYPE = "VMMS Approval Workflow"
PROFILE_DOCTYPE = "Red Profile"

MEMBERSHIP_FORM = "register-as-a-member"


# --- geo, through core ----------------------------------------------------


def build_society() -> dict:
	"""Region → County → Branch, with two branches under the county.

	The approver is placed at the county and applications are made at a branch,
	so `nearest_ancestor` has an actual walk to do rather than finding somebody
	at the node it started from.
	"""
	region, county, branch = (
		geo_fixtures.make_level(f"{LEVEL_PREFIX}-{order}", label, order)
		for order, label in enumerate(["Region", "County", "Branch"], start=1)
	)

	tree = {"levels": {"region": region, "county": county, "branch": branch}}
	tree["region"] = geo_fixtures.make_node("Rift", region, None, is_group=True)
	tree["county"] = geo_fixtures.make_node("Nakuru", county, tree["region"], is_group=True)
	tree["branch"] = geo_fixtures.make_node("Naivasha", branch, tree["county"])
	tree["other_branch"] = geo_fixtures.make_node("Molo", branch, tree["county"])

	return tree


# --- people ---------------------------------------------------------------


def make_role(name: str, desk_access: bool = True) -> str:
	if not frappe.db.exists("Role", name):
		frappe.get_doc({"doctype": "Role", "role_name": name, "desk_access": int(desk_access)}).insert()

	return name


def website_account(handle: str) -> str:
	"""An account somebody made for themselves, holding the self-service role.

	This is what Frappe's signup produces once Portal Settings names a default
	role: a `User` whose whole name went into `first_name`, holding one role and
	nothing else. The `user_type` is left to Frappe to derive — it promotes the
	account to a System User because the role has desk access, and that
	derivation is a thing the journey depends on, so the fixture must not
	pre-empt it by setting the field itself.
	"""
	email = f"{handle}{USER_DOMAIN}"

	if frappe.db.exists("User", email):
		frappe.delete_doc("User", email, force=True)

	make_role(SELF_SERVICE_ROLE)

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": handle.replace(".", " ").replace("_", " ").title(),
			"send_welcome_email": 0,
		}
	).insert()
	user.add_roles(SELF_SERVICE_ROLE)
	frappe.clear_cache(user=email)

	return email


def make_user(handle: str, roles: list[str] | None = None) -> str:
	"""A user with the given roles and nothing else. Never a System Manager."""
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


def make_identification_type(key: str = ID_TYPE) -> str:
	"""A test-owned Identification Type — required to submit a volunteer application."""
	if frappe.db.exists(IDENTIFICATION_TYPE_DOCTYPE, key):
		return key

	frappe.get_doc(
		{
			"doctype": IDENTIFICATION_TYPE_DOCTYPE,
			"identification_type_key": key,
			"identification_type_name": key.replace(f"{TEST_PREFIX}-", "").replace("-", " ").title(),
			"is_active": 1,
		}
	).insert()

	return key


def test_country() -> str:
	"""Any Country the site already has, so citizenship is a real Link value.

	Not a literal like "Kenya": Country is Frappe's own shipped list, and
	defaulting `country_of_citizenship` from the society's own settings is the
	behaviour under test elsewhere — this is only what a fixture supplies so a
	form submission does not depend on that setting being configured on
	whichever site the suite happens to run against.
	"""
	return frappe.db.get_value("Country", {}, "name", order_by="name") or "Kenya"


#: A date of birth for anybody these fixtures make. Fixed rather than derived
#: from `today()`, so an age-dependent assertion cannot change its answer on
#: somebody's birthday.
DEFAULT_DATE_OF_BIRTH = "1990-01-01"


def make_profile(first_name: str, last_name: str, **kwargs) -> str:
	"""A Red Profile written directly, for the paper-registration cases.

	**It carries a date of birth**, because `assert_ready` requires one before a
	volunteer application may be submitted — and a clerk filling in a paper form
	at the branch desk writes one down, so a fixture without it was modelling a
	form nobody submits rather than the paper case it stands for.

	Pass `date_of_birth=None` for the applicant that requirement is meant to
	refuse.
	"""
	slug = f"{first_name}.{last_name}".lower()
	values = {
		"doctype": PROFILE_DOCTYPE,
		"first_name": first_name,
		"last_name": last_name,
		"email": kwargs.pop("email", f"{slug}.{frappe.generate_hash(length=6)}{USER_DOMAIN}"),
		"date_of_birth": DEFAULT_DATE_OF_BIRTH,
	}
	values.update(kwargs)

	return frappe.get_doc(values).insert().name


# --- configuration --------------------------------------------------------


def make_template() -> None:
	if frappe.db.exists(TEMPLATE_DOCTYPE, TEMPLATE_KEY):
		return

	frappe.get_doc(
		{
			"doctype": TEMPLATE_DOCTYPE,
			"template_key": TEMPLATE_KEY,
			"template_name": "Registration Test Certificate",
			"template_category": "certificate",
			"subject": "Certificate of Membership",
			"body": "Member: {{ member_name }} | Type: {{ membership_type }} | At: {{ geo_path }}",
			"output_format": "html",
			"is_active": 1,
		}
	).insert()


def make_types() -> None:
	"""One fee-bearing auto-on-payment type, one free routed type.

	The free routed one is what makes the routed journey testable end to end
	without a gateway in the way: approval alone settles it, which is precisely
	what `membership.try_activate()`'s predicate is supposed to allow.
	"""
	make_template()

	for key, mode, fee in ((TYPE_AUTO, "auto_on_payment", 500), (TYPE_ROUTED, "routed", 0)):
		if frappe.db.exists(TYPE_DOCTYPE, key):
			continue

		frappe.get_doc(
			{
				"doctype": TYPE_DOCTYPE,
				"membership_type_key": key,
				"membership_type_name": key.replace("-", " ").title(),
				"approval_mode": mode,
				"fee_amount": fee,
				"duration_days": 365,
				"is_active": 1,
				"template_key": TEMPLATE_KEY,
				"benefits": [{"benefit_key": "clinic", "benefit_name": "Clinic access", "is_active": 1}],
			}
		).insert()


def make_workflows(anchor_levels: list[str]) -> None:
	"""One workflow per governed doctype, each with one rejecting stage."""
	for doctype, applicant_field in ((APPLICATION_DOCTYPE, "red_profile"), (MEMBERSHIP_DOCTYPE, "member")):
		existing = frappe.db.get_value(WORKFLOW_DOCTYPE, {"workflow_for": doctype}, "name")

		if existing:
			frappe.delete_doc(WORKFLOW_DOCTYPE, existing, force=True)

		frappe.get_doc(
			{
				"doctype": WORKFLOW_DOCTYPE,
				"workflow_for": doctype,
				"geo_node_field": "geo_node",
				"applicant_field": applicant_field,
				"allow_withdrawal": 1,
				"allowed_anchor_levels": [{"geo_level": level} for level in anchor_levels],
				"stages": [
					{
						"sequence": 1,
						"stage_label": "Branch Review",
						"required_role": APPROVER_ROLE,
						"resolution_rule": "nearest_ancestor",
						"completion_rule": "single",
						"can_reject": 1,
						"is_optional": 0,
						"sla_days": 5,
						"on_sla_breach": "escalate_up",
					}
				],
			}
		).insert()


def grant_doctype_access(doctype: str, role: str, permissions=("read", "write", "create", "share")) -> None:
	"""Let a society role act on a doctype, the way an administrator would.

	An approver *saves* the document they decide on, so the role a stage names
	needs write on the governed doctype. The shipped JSONs grant only System
	Manager, because which society role gets this is configuration.
	"""
	from frappe.permissions import add_permission, update_permission_property

	make_role(role)
	add_permission(doctype, role, 0)

	for permission in permissions:
		update_permission_property(doctype, role, 0, permission, 1)

	frappe.clear_cache(doctype=doctype)


def set_settings(**values) -> None:
	"""Write society settings straight onto the single and drop the cache.

	What an administrator saving the form amounts to, as far as every reader in
	this app is concerned.
	"""
	for field, value in values.items():
		frappe.db.set_single_value(SETTINGS_DOCTYPE, field, value)

	frappe.clear_document_cache(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE)


def role_settings() -> tuple[str, ...]:
	"""Every settings field the self-service journey reads a role from."""
	from vmmsx.member.services.society import MEMBER_ROLE_FIELD as MEMBERSHIP_MEMBER_ROLE
	from vmmsx.member.services.society import PRINT_ROLE_FIELD
	from vmmsx.registration.services.society import SELF_SERVICE_ROLE_FIELD
	from vmmsx.volunteer.services.society import MEMBER_ROLE_FIELD as VOLUNTEER_MEMBER_ROLE

	return (
		"vmms_volunteer_scope_role",
		"vmms_membership_scope_role",
		PRINT_ROLE_FIELD,
		VOLUNTEER_MEMBER_ROLE,
		MEMBERSHIP_MEMBER_ROLE,
		SELF_SERVICE_ROLE_FIELD,
	)


def snapshot_settings() -> dict:
	"""What the site had configured before this suite started.

	Read so it can be put back. `teardown` runs *after* the runner's rollback, so
	anything it writes survives the test run: a suite that cleared these would
	quietly un-configure whatever society was already set up on the bench it ran
	against, and the seeded demo would stop working with nothing saying why.
	"""
	settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)

	return {field: settings.get(field) for field in role_settings()}


def restore_settings(snapshot: dict) -> None:
	"""Put the site's own configuration back, and rebuild its surfaces from it."""
	from vmmsx.registration.services import workspaces

	set_settings(**snapshot)
	workspaces.install()


def configure_society(tree: dict) -> None:
	"""Every setting the journey reads, pointed at this suite's roles."""
	from vmmsx.member.services.society import MEMBER_ROLE_FIELD as MEMBERSHIP_MEMBER_ROLE
	from vmmsx.member.services.society import PRINT_ROLE_FIELD
	from vmmsx.registration.services.society import SELF_SERVICE_ROLE_FIELD
	from vmmsx.volunteer.services.society import MEMBER_ROLE_FIELD as VOLUNTEER_MEMBER_ROLE

	for role in TEST_ROLES:
		make_role(role)

	set_settings(
		**{
			"vmms_volunteer_scope_role": APPROVER_ROLE,
			"vmms_membership_scope_role": APPROVER_ROLE,
			PRINT_ROLE_FIELD: APPROVER_ROLE,
			VOLUNTEER_MEMBER_ROLE: VOLUNTEER_ROLE,
			MEMBERSHIP_MEMBER_ROLE: MEMBER_ROLE,
			SELF_SERVICE_ROLE_FIELD: SELF_SERVICE_ROLE,
		}
	)


def clear_society_roles() -> None:
	"""Put every role setting back to the shipped, fail-closed empty state."""
	set_settings(**dict.fromkeys(role_settings()))


# --- the web forms, driven the way a browser drives them ------------------


def submit_volunteer_form(geo_node: str, **values):
	"""Post the portal volunteer registration as whoever is logged in.

	The React portal is the supported registration surface. It sends person facts
	to `register_as_volunteer`, which writes Red Profile before creating the thin
	application and submits both in one transaction.

	**`applicant_date_of_birth` is an intake-buffer field, not a stored one.**
	`intake.claim_profile` reads it in `before_insert`, writes it onto the Red
	Profile and blanks it, which is why `assert_ready` looks for the date on the
	profile rather than on the application. Passing it here is what a browser
	does; passing `applicant_date_of_birth=None` builds the applicant the
	requirement is meant to refuse.
	"""
	payload = {
		"first_name": values.pop("applicant_first_name", "Amina"),
		"last_name": values.pop("applicant_last_name", "Otieno"),
		"date_of_birth": values.pop("applicant_date_of_birth", "1990-01-01"),
		"phone": values.pop("applicant_phone", None),
		"gender": values.pop("applicant_gender", None),
		"geo_node": geo_node,
		"country_of_citizenship": test_country(),
		"residency_type": "Local",
		"home_geo_node": geo_node,
		"id_type": make_identification_type(),
		"id_number": f"{TEST_PREFIX}-{frappe.generate_hash(length=8)}",
		"prior_experience": "School first aid club",
	}
	payload.update(values)

	from vmmsx.api.registration import register_as_volunteer

	result = register_as_volunteer(**payload)

	return frappe.get_doc(APPLICATION_DOCTYPE, result["name"])


def submit_membership_form(geo_node: str, membership_type: str, **values):
	"""POST the membership registration form as whoever is logged in."""
	payload = {
		"applicant_first_name": "Amina",
		"applicant_last_name": "Otieno",
		"geo_node": geo_node,
		"membership_type": membership_type,
	}
	payload.update(values)

	return _accept(MEMBERSHIP_FORM, payload)


def _accept(web_form: str, payload: dict):
	"""Frappe's own web form endpoint, called exactly as the browser calls it.

	`in_web_form` is set by `accept()` itself and reset here, because the flag is
	request-scoped in production and a test process has one long request.
	"""
	from frappe.website.doctype.web_form.web_form import accept

	try:
		return accept(web_form=web_form, data=json.dumps(payload))
	finally:
		frappe.flags.in_web_form = False


# --- payment --------------------------------------------------------------


def use_manual_gateway() -> None:
	"""Point the payments app at its Manual driver for the duration of a test."""
	settings = frappe.get_single("OneRC Payment Settings")
	settings.active_gateway = _manual_gateway_name()
	settings.save(ignore_permissions=True)
	frappe.clear_document_cache("OneRC Payment Settings", "OneRC Payment Settings")


def _manual_gateway_name() -> str:
	name = frappe.db.get_value("OneRC Payment Gateway", {"driver_class": ("like", "%manual%")}, "name")

	if name:
		return name

	return (
		frappe.get_doc(
			{
				"doctype": "OneRC Payment Gateway",
				"gateway_name": "Manual",
				"driver_class": "onerc_payments.gateways.manual.ManualGateway",
				"is_active": 1,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def confirm_payment_through_manual_driver(membership) -> dict:
	"""Settle this membership's fee through the real Manual gateway.

	The payments app's own admin path: it marks the transaction Completed and
	calls `on_payment_confirmed` on this membership by name. Nothing here fakes
	a hook.
	"""
	from onerc_payments.gateways.manual import confirm_payment

	membership.reload()

	return confirm_payment(membership.payment_transaction, f"MANUAL-{frappe.generate_hash(length=6)}")


# --- session --------------------------------------------------------------


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
	for doctype in (APPLICATION_DOCTYPE, VOLUNTEER_DOCTYPE, MEMBERSHIP_DOCTYPE, MEMBER_DOCTYPE):
		for name in frappe.get_all(doctype, pluck="name"):
			frappe.delete_doc(doctype, name, force=True)

	for doctype in (APPLICATION_DOCTYPE, MEMBERSHIP_DOCTYPE):
		workflow = frappe.db.get_value(WORKFLOW_DOCTYPE, {"workflow_for": doctype}, "name")

		if workflow:
			frappe.delete_doc(WORKFLOW_DOCTYPE, workflow, force=True)

	for key in (TYPE_AUTO, TYPE_ROUTED):
		if frappe.db.exists(TYPE_DOCTYPE, key):
			frappe.delete_doc(TYPE_DOCTYPE, key, force=True)

	if frappe.db.exists(TEMPLATE_DOCTYPE, TEMPLATE_KEY):
		frappe.delete_doc(TEMPLATE_DOCTYPE, TEMPLATE_KEY, force=True)

	if frappe.db.exists(IDENTIFICATION_TYPE_DOCTYPE, ID_TYPE):
		frappe.delete_doc(IDENTIFICATION_TYPE_DOCTYPE, ID_TYPE, force=True)

	for user in frappe.get_all("User", filters={"email": ("like", f"%{USER_DOMAIN}")}, pluck="name"):
		for permission in frappe.get_all("User Permission", filters={"user": user}, pluck="name"):
			frappe.delete_doc("User Permission", permission, force=True)

	for profile in frappe.get_all(
		PROFILE_DOCTYPE, filters={"email": ("like", f"%{USER_DOMAIN}")}, pluck="name"
	):
		frappe.delete_doc(PROFILE_DOCTYPE, profile, force=True)

	for user in frappe.get_all("User", filters={"email": ("like", f"%{USER_DOMAIN}")}, pluck="name"):
		frappe.delete_doc("User", user, force=True)

	_reset_geo()


def _reset_geo() -> None:
	"""Geo goes deepest-first: NestedSet refuses to delete a node with children."""
	levels = [
		level for level in frappe.get_all("Geo Level", pluck="name") if level.startswith(f"{LEVEL_PREFIX}-")
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


def teardown(settings_snapshot: dict | None = None) -> None:
	"""Undo everything this suite did, including to the site's own configuration.

	`settings_snapshot` is what the site had before the suite ran. It is restored
	rather than cleared, because this function runs after the runner's rollback
	and so anything it writes is permanent: clearing the settings would leave the
	bench it ran on with an un-configured society and no surfaces.
	"""
	reset()

	if settings_snapshot is None:
		clear_society_roles()
	else:
		restore_settings(settings_snapshot)

	for role in TEST_ROLES:
		if frappe.db.exists("Role", role):
			frappe.delete_doc("Role", role, force=True)
