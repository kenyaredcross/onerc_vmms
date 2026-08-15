# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The HR seam — a link, pointing one way, carrying nothing back.

**Direction.** `VMMS Volunteer.employee` is a Link to Frappe HR's `Employee`.
vmmsx points at HR; HR does not point at vmmsx, does not import it, and is not
modified by this app. Everything about the seam lives on our side of it, which
is what makes it removable: uninstall HR and a nullable link goes unused.

**Identity never moves.** Red Profile is the spine and stays the spine. Nothing
in this app ever reads `employee_name`, `personal_email`, `company` or any other
field on an Employee as the answer to who somebody is — those questions are
answered by `volunteer/services/identity.py`, which reads Red Profile. Identity
is *given* to HR when a record is created and never taken back. A `fetch_from`
pointing at Employee would be the whole principle undone in one JSON attribute,
and there is none.

**One thing does come back, and it is not identity.** `_INBOUND` is an
allow-list of exactly one field: the Employee's department. A department is an
organisational placement that HR owns and vmmsx does not model, and it is read
for one purpose — stipend approval runs from a supervisor to the head of the
volunteer's *department*, so the paperwork has to be able to record which
department that would be. It is recorded as a routing target and never as an
answer to who somebody is, nothing branches on it, and nothing routes on it
today. The list is an allow-list rather than prose precisely so that the next
field somebody wants back has to be added deliberately, in this file, with a
reason. See `vmmsx/stipend/services/department.py`, its only caller.

**No employment model crosses either.** Payroll, salary structures, attendance,
leave and timesheets are HR's. A volunteer is not an employee; the link exists
because a society's HR office may need a record for a person who holds a badge
and appears in an emergency roster, not because volunteering is employment.
`VMMS Time Log` is this app's own record of volunteered hours and has nothing to
do with Timesheet.

**Provisioning is off unless a society switches it on.** Two settings govern it,
both Custom Fields vmmsx owns: `vmms_volunteer_provision_employee` and
`vmms_volunteer_employee_company`. With the switch off — the shipped state —
accepting a volunteer creates no Employee at all.

**And vmmsx will not invent identity to satisfy another app's schema.** HR
requires a gender and a date of birth on every Employee. Core's Red Profile
carries both — they were added to the identity spine as optional person-facts —
and this app now *displays* both on the volunteer page. It still does not pass
either to HR, and the difference between those two sentences is the whole of
`_OUTBOUND` below.

Showing somebody's date of birth to a coordinator who may already see their
record is one decision. Writing it into an employment register, where a payroll
run and a leave policy will read it, is a different one. They were the same
decision only for as long as the two lists were the same list. `_OUTBOUND` is
what this seam hands over, it is narrower than what `identity.read()` will
return, and it is asserted to stay that way.

Where HR refuses a record for want of data this app does not pass on, the refusal
is logged with the fields named and the volunteer is entirely unaffected: they
are a volunteer either way. Refusing to provision is the correct outcome, not a
bug to be worked around by filling in a placeholder date of birth.

Widening `_OUTBOUND` so that provisioning can succeed is a deliberate decision
about what a volunteer record may push into an employment register, and a
deliberate one about consent. It is a later enrichment, not an oversight here.
"""

import frappe
from frappe.utils import getdate, today

from vmmsx.volunteer.services import identity, society

# The one doctype this module names. Nothing else in vmmsx does.
EMPLOYEE_DOCTYPE = "Employee"
EMPLOYEE_LINK_FIELD = "employee"

VOLUNTEER_DOCTYPE = "VMMS Volunteer"

HR_APP = "hrms"

# What `provision()` did. Constants rather than prose, so a caller — or a test —
# asserts on a fact.
OUTCOME_ALREADY_LINKED = "already_linked"
OUTCOME_DISABLED = "disabled"
OUTCOME_NO_HR = "no_hr"
OUTCOME_ADOPTED = "adopted"
OUTCOME_CREATED = "created"
OUTCOME_NO_COMPANY = "no_company"
OUTCOME_HR_REFUSED = "hr_refused"

PROVISIONING_LOG_TITLE = "Volunteer HR provisioning did not complete"

# Everything vmmsx is willing to hand to an employment register, and the whole of
# it. Deliberately narrower than `identity._READABLE`, which is what the desk
# displays: this list is what leaves the app.
#
# Gender and date of birth are the two HR insists on, and the two that are not
# here. That is the seam holding, not core lacking the fields — core has both,
# and the volunteer page shows both. A society that wants complete HR records
# completes them in HR.
_OUTBOUND = ("first_name", "middle_name", "last_name", "email", "phone", "user")

# Everything vmmsx is willing to read back off an employment register, and the
# whole of it. One field, and not an identity field: see the note at the top.
# Anything added here is a decision about what an employment register is allowed
# to tell this app about a volunteer, and it is made here or not at all.
_INBOUND = ("department",)


def is_available() -> bool:
	"""Is Frappe HR installed on this site?

	Asked of `frappe.get_installed_apps()` rather than by attempting an import:
	an app can sit in the bench without being installed on *this* site.
	"""
	return HR_APP in frappe.get_installed_apps()


def linked_employee(volunteer) -> str | None:
	"""The Employee this volunteer is linked to, if any. The whole read surface.

	One field, and no employment data. A caller that wants to know about a
	person's employment asks HR about this docname; it does not ask vmmsx, which
	knows nothing beyond the fact of the link.
	"""
	return volunteer.get(EMPLOYEE_LINK_FIELD) or None


def read_back(volunteer, field: str) -> str | None:
	"""One allow-listed fact from this volunteer's Employee record, or None.

	The whole inbound half of the seam, and it degrades at every step rather than
	throwing: no HR on this site, no Employee linked, or a field this build of HR
	does not have all answer None, and None is ordinary. A volunteer without an
	employment record is a volunteer, which is the normal case.

	A field outside `_INBOUND` is refused rather than fetched. That is the point
	of having a list: a caller that wants something else has to come here and
	argue for it, in a file whose docstring says what the seam is for.
	"""
	if field not in _INBOUND:
		raise PermissionError(
			f"{field!r} is not something vmmsx reads back from {EMPLOYEE_DOCTYPE}."
			f" The seam reads {', '.join(_INBOUND)} and nothing else; see volunteer/services/hr.py."
		)

	employee = linked_employee(volunteer)

	if not (employee and is_available()):
		return None

	if not frappe.get_meta(EMPLOYEE_DOCTYPE).has_field(field):
		# A different build of HR. Nothing about a volunteer depends on this, so
		# the absence is simply reported as "no answer".
		return None

	return frappe.db.get_value(EMPLOYEE_DOCTYPE, employee, field) or None


def provision(volunteer) -> dict:
	"""Give this volunteer an HR record, if the society asked for one. Idempotent.

	Called from acceptance, and safe to call again: an already-linked volunteer
	is reported and left alone. Never raises into its caller — a volunteer who
	could not be provisioned is still a volunteer, and an HR misconfiguration
	must not be able to fail an approval.
	"""
	outcome = {"volunteer": volunteer.name, "employee": linked_employee(volunteer), "outcome": None}

	if outcome["employee"]:
		outcome["outcome"] = OUTCOME_ALREADY_LINKED

		return outcome

	if not is_available():
		outcome["outcome"] = OUTCOME_NO_HR

		return outcome

	if not society.provisions_employees():
		# The shipped state. Nothing is created, nothing is logged: this is a
		# society running volunteering without HR, which is ordinary.
		outcome["outcome"] = OUTCOME_DISABLED

		return outcome

	adopted = _existing_employee(volunteer)

	if adopted:
		# HR already has this person. Linking beats creating a second record —
		# a duplicate Employee is a worse outcome than no Employee.
		_link(volunteer, adopted)
		outcome.update(employee=adopted, outcome=OUTCOME_ADOPTED)

		return outcome

	company = society.employee_company()

	if not company:
		_log(volunteer, "no company is configured in vmms_volunteer_employee_company")
		outcome["outcome"] = OUTCOME_NO_COMPANY

		return outcome

	created = _create(volunteer, company)

	if not created:
		outcome["outcome"] = OUTCOME_HR_REFUSED

		return outcome

	_link(volunteer, created)
	outcome.update(employee=created, outcome=OUTCOME_CREATED)

	return outcome


def _existing_employee(volunteer) -> str | None:
	"""HR's record for this person, found through their login if they have one.

	The lookup goes through the Red Profile's `user`, because that is the one
	identifier core says ties a person to a login. It does not match on name or
	email: two people share a name, and matching identity by string is how a
	volunteer ends up linked to somebody else's HR record.
	"""
	user = identity.user_of(volunteer)

	if not user:
		return None

	return frappe.db.get_value(EMPLOYEE_DOCTYPE, {"user_id": user}, "name")


def _create(volunteer, company: str) -> str | None:
	"""Create HR's record from what vmmsx legitimately knows. May decline.

	Everything supplied comes from Red Profile or from society configuration, and
	only through `identity.read()` asked for `_OUTBOUND` — which is what decides
	that gender and date of birth are not vmmsx's to pass on, whatever else the
	reader is willing to show a coordinator on screen. Nothing is invented. Where
	HR wants one of those two, the insert fails, and that failure is the correct
	answer: it is logged with HR's own complaint and the volunteer is untouched.

	The read is narrowed rather than the dict filtered afterwards, so there is no
	moment at which this function is holding a person-fact it has no business
	sending.
	"""
	person = identity.read(volunteer, _OUTBOUND)

	employee = frappe.get_doc(
		{
			"doctype": EMPLOYEE_DOCTYPE,
			"company": company,
			"first_name": person.get("first_name"),
			"middle_name": person.get("middle_name"),
			"last_name": person.get("last_name"),
			"personal_email": person.get("email"),
			"cell_number": person.get("phone"),
			"user_id": person.get("user"),
			"date_of_joining": getdate(volunteer.joined_on or today()),
		}
	)

	try:
		# Provisioning runs on an approver's decision, and an approver holds no
		# permission on HR's register — nor should a society have to grant one in
		# order for approvals to work. The record's contents come from core's
		# identity spine and the society's own settings, not from the approver.
		employee.insert(ignore_permissions=True)
	except Exception as exception:
		# Deliberately broad, and deliberately swallowed. HR can refuse for any
		# number of reasons this app has no view of, and none of them is a reason
		# to fail the approval that triggered it. The complaint is logged in full
		# so an administrator can see exactly what HR wanted.
		_log(volunteer, f"{EMPLOYEE_DOCTYPE} was refused by HR: {exception}")

		return None

	return employee.name


def _link(volunteer, employee: str) -> None:
	"""Record the link on the volunteer, and nothing else.

	`db.set_value` rather than a full save: the field is read-only, engine-written
	state on a record whose lifecycle is being driven by somebody else's save, and
	a nested save here would re-enter the acceptance path for no gain. The
	in-memory document is updated too, so a caller holding it sees the truth.
	"""
	frappe.db.set_value(VOLUNTEER_DOCTYPE, volunteer.name, EMPLOYEE_LINK_FIELD, employee)
	volunteer.set(EMPLOYEE_LINK_FIELD, employee)


def _log(volunteer, why: str) -> None:
	"""Say what did not happen, where an administrator will find it.

	Logged rather than raised, and never silent. A society that switched
	provisioning on and is getting no Employee records needs to be able to find
	out why without reading the source.
	"""
	frappe.log_error(
		title=PROVISIONING_LOG_TITLE,
		message=(
			f"{VOLUNTEER_DOCTYPE} {volunteer.name} was accepted but no {EMPLOYEE_DOCTYPE} record"
			f" was provisioned: {why}. The volunteer is unaffected."
		),
		reference_doctype=VOLUNTEER_DOCTYPE,
		reference_name=volunteer.name,
	)
