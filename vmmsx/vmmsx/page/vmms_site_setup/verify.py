# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Is the site ready? Read-only, always. Moved from `site-setup/99_verify.py`.

Sorts what it finds into:

- `blocking`: the site is not ready; the step named fixes it;
- `before_go_live`: fine for loading data, needed before real people use it
  (keys, real coordinators, posting switched on);
- `ok`: what was checked and passed.

Frappe Cloud serves the site at its own address, so `host_name` is not
checked; and the onerc_core oversight code is read off the installed code, not
a patch script.
"""

EXPECTED = {"national": 1, "region": 8, "county": 47}
KENYA_TYPES = ("Youth In School", "Youth Out Of School", "Ordinary Member", "Life Member")
COUNTY_COORDINATOR = "County Coordinator"
APPS = ("erpnext", "onerc_core", "onerc_payments", "vmmsx")


def run(frappe, settings: dict, apply: bool) -> dict:
	report = {"blocking": [], "before_go_live": [], "ok": []}

	def block(step, message):
		report["blocking"].append(f"{step}: {message}")

	def later(step, message):
		report["before_go_live"].append(f"{step}: {message}")

	def ok(message):
		report["ok"].append(message)

	# Apps and site
	installed = set(frappe.get_installed_apps())
	missing = [app for app in APPS if app not in installed]
	block("Apps", f"Not installed: {', '.join(missing)}") if missing else ok(
		f"Apps installed: {', '.join(APPS)}"
	)
	from frappe.utils.scheduler import is_scheduler_disabled

	if is_scheduler_disabled():
		block(
			"Scheduler",
			"Off: daily jobs (expiry, SLA, posting, receipt lookups, licence notices) will not run.",
		)
	else:
		ok("Scheduler is on")

	# onerc_core oversight code (a branch on Frappe Cloud, not a patch)
	from onerc_core.access.services import registry

	from vmmsx.setup import national_oversight, regional_oversight

	if hasattr(registry, "resolve_read_role") and national_oversight.core_reads_nationally():
		ok("onerc_core reads for Head of Region and NSD Coordinator")
	else:
		later(
			"onerc_core",
			"The deployed onerc_core has no reading roles: Head of Region and NSD Coordinator will see nothing."
			" Deploy the vmmsx-edition-oversight branch.",
		)

	# First run
	from vmmsx.setup import wizard

	if not frappe.is_setup_complete():
		block("Setup wizard", "Not completed.")
	elif not wizard._already_configured():
		block(
			"Society",
			"The society's name, logo, levels or application level are missing: run the Society step.",
		)
	else:
		ok("Setup wizard complete; society identity set")
	settings_doc = frappe.get_single("National Society Settings")
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if company:
		ok(f"ERPNext company {company} ({frappe.db.get_value('Company', company, 'default_currency')})")
	else:
		block("Setup wizard", "ERPNext has no default company.")

	# Geography
	counts = {
		level: frappe.db.count("Geo Node", {"geo_level": level})
		for level in ("national", "region", "county", "sub_county", "ward")
	}
	wrong = {
		level: (counts.get(level), want) for level, want in EXPECTED.items() if counts.get(level) != want
	}
	if wrong:
		block("Geography", f"Counts (have, want): {wrong}")
	else:
		ok(f"Geography: {counts}")
	if not counts.get("sub_county"):
		later("Geography", "No sub-counties yet.")

	# Picker lists
	prefixed = frappe.db.count("Geo Node", {"geo_level": "region", "geo_node_name": ("like", "KRCS %")})
	block("Picker lists", f"{prefixed} regions still named 'KRCS …'.") if prefixed else ok(
		"Region names without 'KRCS '"
	)
	ids = frappe.db.count("Identification Type")
	block("Picker lists", "No identification types.") if not ids else ok(f"{ids} identification types")

	# Roles
	for field in ("vmms_volunteer_scope_role", "vmms_membership_scope_role"):
		value = settings_doc.get(field)
		if value != COUNTY_COORDINATOR:
			block("Roles", f"{field} is {value or '(empty)'}, not {COUNTY_COORDINATOR}.")
	if not (regional_oversight.role() and national_oversight.role()):
		block("Roles", "Head of Region or NSD Coordinator is not set.")
	else:
		ok("County Coordinator, Head of Region and NSD Coordinator configured")
	counties = frappe.get_all("Geo Node", filters={"geo_level": "county"}, pluck="name")
	covered = frappe.db.count(
		"Geo Assignment", {"role": COUNTY_COORDINATOR, "is_active": 1, "geo_node": ("in", counties or [""])}
	)
	if covered < len(counties):
		later(
			"Roles",
			f"County Coordinators assigned in {covered} of {len(counties)} counties; applications elsewhere route to nobody.",
		)
	if not frappe.db.count("Has Role", {"role": national_oversight.role() or "", "parenttype": "User"}):
		later("Roles", "Nobody holds NSD Coordinator (name them on the form and run Roles again).")

	# Registration
	types = frappe.get_all(
		"VMMS Membership Type",
		filters={"is_active": 1},
		fields=[
			"membership_type_name",
			"fee_amount",
			"fee_currency",
			"requires_age_requirement",
			"lower_age_limit",
			"upper_age_limit",
			"template_key",
		],
	)
	names = {row.membership_type_name for row in types}
	absent = [t for t in KENYA_TYPES if t not in names]
	if absent:
		block("Registration", f"Membership types missing: {absent}")
	else:
		ok(
			"Membership types: "
			+ ", ".join(
				f"{r.membership_type_name} {r.fee_currency} {r.fee_amount:g}"
				+ (f" ages {r.lower_age_limit}-{r.upper_age_limit}" if r.requires_age_requirement else "")
				for r in types
			)
		)
	no_certificate = [r.membership_type_name for r in types if not r.template_key]
	if no_certificate:
		block("Registration", f"No certificate template on: {', '.join(no_certificate)}")
	for doctype in ("VMMS Volunteer Application", "VMMS Membership"):
		if not frappe.db.exists("VMMS Approval Workflow", {"workflow_for": doctype}):
			block("Registration", f"No approval workflow for {doctype}.")
	if not any("approval workflow" in b for b in report["blocking"]):
		ok("Approval workflows for volunteers and memberships")
	for side in ("left", "right"):
		if not settings_doc.get(f"vmms_certificate_signature_{side}"):
			later(
				"Registration",
				f"No {side} signature picture on the membership certificate (National Society Settings).",
			)

	# Transfers
	from vmmsx.setup import branch_transfer

	transfer = branch_transfer.plan()
	if transfer.get("mode") != "routed" or not transfer.get("workflow"):
		block("Branch transfers", f"Not approved by both branches (mode {transfer.get('mode')}).")
	else:
		ok("Branch transfers routed through both branches")

	# County map
	block("County map", "No county map attached.") if not settings_doc.get("vmms_boundary_file") else ok(
		"County map attached"
	)

	# Payments
	from frappe.utils.password import get_decrypted_password

	pay = frappe.get_single("OneRC Payment Settings")
	if pay.active_gateway != "Mpesa Daraja":
		block(
			"Payments", f"The active payment gateway is {pay.active_gateway or '(none)'}, not Mpesa Daraja."
		)
	offered = [r.label for r in settings_doc.get("vmms_payment_methods") or [] if r.is_enabled]
	if offered != ["M-Pesa"]:
		block("Payments", f"The registration form offers {offered}, not M-Pesa only.")
	else:
		ok(f"Payments: M-Pesa only, {pay.environment}, shortcode {pay.mpesa_shortcode}")
	for field in ("mpesa_consumer_key", "mpesa_consumer_secret", "mpesa_passkey"):
		if not get_decrypted_password(
			"OneRC Payment Settings", "OneRC Payment Settings", field, raise_exception=False
		):
			later("Payments", f"{field} is not set in OneRC Payment Settings: no M-Pesa prompts can be sent.")
	if pay.environment != "Production":
		later("Payments", "M-Pesa is in Sandbox: no real money moves.")

	# Accounting
	from vmmsx.setup import membership_accounting

	for problem in membership_accounting.problems():
		# Off is a finance decision, not a fault: fees paid meanwhile are posted
		# by the daily job once it is switched on.
		(later if "switched off" in problem else block)("Accounting", problem)
	if not any(b.startswith("Accounting") for b in report["blocking"]):
		ok("Accounting set up")

	# Numbering
	rule = frappe.db.exists("Document Naming Rule", {"document_type": "VMMS Volunteer"})
	if not rule:
		block("Numbering", "The volunteer numbering rule is missing (migrate).")
	else:
		ok(f"Volunteer numbering rule counter {frappe.db.get_value('Document Naming Rule', rule, 'counter')}")

	return {"ready": not report["blocking"], **report}
