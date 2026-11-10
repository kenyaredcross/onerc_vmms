# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The shorter setup steps, each moved from its script in `VMMS-Kenya scripts`.

Every function here has the same shape, `step(frappe, settings, apply)`, and
returns what it found or did. None of them commits: `steps.execute()` commits
after a Run and rolls back after a Check, as the scripts did.
"""

import hashlib
import json
from pathlib import Path

import vmmsx

HERE = Path(__file__).resolve().parent
COUNTY_MAP = HERE / "data" / "kenya-counties.geojson"
SETTINGS = "National Society Settings"


# --- the society (site-setup/02_first_run.py) --------------------------------

# The wizard's vmmsx questions, answered for Kenya. Needed when the setup wizard
# was completed before vmmsx was installed: its questions never appeared, so the
# society has no name, logo, levels or application level. Frappe Cloud cannot
# rerun the wizard without redoing ERPNext's company.
LEVELS = ["National", "Region", "County", "Sub-county", "Ward"]
APPLICATION_LEVEL = "County"
LOGO = HERE / "data" / "krcs-logo.png"


def society(frappe, settings: dict, apply: bool) -> dict:
	"""The society's name, logo, five geographic levels and the level applications are taken at."""
	from vmmsx.setup import wizard

	nss = frappe.get_single(SETTINGS)
	if wizard._already_configured():
		return {
			"already_set_up": True,
			"name": nss.organization_name,
			"short_name": nss.organization_short_name,
			"country": nss.country,
			"logo": nss.logo,
			"levels": frappe.get_all("Geo Level", pluck="geo_level_name", order_by="geo_level_order"),
		}

	values = {
		"language": (settings.get("society_language") or "English").strip(),
		"country": (settings.get("society_country") or "Kenya").strip(),
		"vmms_organization_name": (settings.get("society_name") or "").strip(),
		"vmms_organization_short_name": (settings.get("society_short_name") or "").strip(),
		"vmms_geo_levels_json": json.dumps([{"label": label} for label in LEVELS]),
		"vmms_application_anchor_order": LEVELS.index(APPLICATION_LEVEL) + 1,
	}
	if not values["vmms_organization_name"] or not values["vmms_organization_short_name"]:
		raise ValueError("Fill in the society's name and short name on the setup form first.")
	if not frappe.db.exists("Country", values["country"]):
		raise ValueError(f"There is no country called {values['country']!r}.")

	preview = {
		"already_set_up": False,
		"name": values["vmms_organization_name"],
		"short_name": values["vmms_organization_short_name"],
		"country": values["country"],
		"language": values["language"],
		"levels": LEVELS,
		"applications_taken_at": APPLICATION_LEVEL,
		"logo": settings.get("society_logo") or f"{LOGO.name} (shipped with the app)",
	}
	if not apply:
		# Not done and rolled back like the other steps: the logo would be
		# written to the site's files, and a rollback does not take a file back.
		return preview

	values["vmms_logo"] = settings.get("society_logo") or _upload_logo(frappe)
	wizard.setup_national_society(values)
	nss = frappe.get_single(SETTINGS)
	return {
		**preview,
		"logo": nss.logo,
		"national_node": frappe.db.get_value(
			"Geo Node", {"parent_geo_node": ("is", "not set")}, "geo_node_name"
		),
		"set_up": wizard._already_configured(),
	}


def _upload_logo(frappe) -> str:
	"""The bundled logo as a public File, reused if the same file is already there."""
	from frappe.utils.file_manager import get_content_hash

	content = LOGO.read_bytes()
	existing = frappe.db.get_value(
		"File", {"content_hash": get_content_hash(content), "is_private": 0}, "file_url"
	)
	if existing:
		return existing
	return (
		frappe.get_doc({"doctype": "File", "file_name": LOGO.name, "content": content, "is_private": 0})
		.insert(ignore_permissions=True)
		.file_url
	)


# --- picker lists (configure_vocabularies.py) ---------------------------------


def vocabularies(frappe, settings: dict, apply: bool) -> dict:
	"""The old VMMS's picker values where missing, and "KRCS " off the region names."""
	from vmmsx.setup import registration_parity

	return {
		"added": registration_parity.install_kenya_vocabularies(),
		"regions": registration_parity.drop_region_prefix(),
	}


# --- registration (site-setup/06_registration.py) -----------------------------

# (lower, upper) inclusive, or None for no age rule. Chosen by Kenya on 2026-11-04.
KENYA_AGES = {
	"Youth In School": (7, 17),
	"Youth Out Of School": (18, 29),
	"Ordinary Member": (30, 150),
	"Life Member": None,
}
DESCRIPTIONS = {
	"Youth In School": "Annual membership for young people in school, supporting school-based service, first aid and humanitarian learning.",
	"Youth Out Of School": "Annual membership supporting young adults in community service, skills development and branch participation.",
	"Ordinary Member": "Annual membership for adults participating in the humanitarian work and governance of the Society.",
	"Life Member": "One-off lifetime membership supporting a sustained commitment to the Society and its humanitarian mission.",
}
ANCHORS = ("vmms_deployment_anchor_level", "vmms_stipend_anchor_level")
ANCHOR_LEVEL = "county"
CERTIFICATE = "membership_certificate_principles"
PLAIN_CERTIFICATE = "membership_certificate"
SIGNATORIES = {
	"vmms_certificate_signatory_left": "The Governor",
	"vmms_certificate_signatory_right": "Secretary General",
}


def registration(frappe, settings: dict, apply: bool) -> dict:
	"""Kenya's registration rules, membership types and approval workflows.

	`registration_parity.configure_kenya`, then on top: Kenya's age limits on a
	type still carrying the old site's, a description on each type that has
	none, deployments and stipends anchored at County, no volunteer cards, and
	the certificate with the Fundamental Principles and its two signatories.
	"""
	from vmmsx.setup import registration_parity

	result = {"kenya": registration_parity.configure_kenya()}

	seeds = {
		row["membership_type"]: row
		for row in json.loads(
			(Path(vmmsx.__file__).parent / "registration/seeds/kenya_registration_plans.json").read_text()
		)
	}
	types = []
	for label, ages in KENYA_AGES.items():
		name = frappe.db.get_value("VMMS Membership Type", {"membership_type_name": label}, "name")
		if not name:
			types.append({"type": label, "missing": True})
			continue
		doc = frappe.get_doc("VMMS Membership Type", name)
		changed = []
		seed = seeds.get(label) or {}
		untouched = (
			int(doc.requires_age_requirement or 0) == int(seed.get("requires_age_requirement") or 0)
			and int(doc.lower_age_limit or 0) == int(seed.get("lower_age_limit") or 0)
			and int(doc.upper_age_limit or 0) == int(seed.get("upper_age_limit") or 0)
		)
		wanted = (1, *ages) if ages else (0, 0, 0)
		current = (
			int(doc.requires_age_requirement or 0),
			int(doc.lower_age_limit or 0),
			int(doc.upper_age_limit or 0),
		)
		if untouched and current != wanted:
			doc.requires_age_requirement, doc.lower_age_limit, doc.upper_age_limit = wanted
			changed.append(
				f"ages {current[1]}-{current[2]} -> {wanted[1]}-{wanted[2]}" if ages else "no age rule"
			)
		if not doc.description:
			doc.description = DESCRIPTIONS[label]
			changed.append("description")
		if (
			frappe.db.exists("VMMS Template", CERTIFICATE)
			and (doc.template_key or PLAIN_CERTIFICATE) == PLAIN_CERTIFICATE
		):
			doc.template_key = CERTIFICATE
			changed.append("certificate")
		if changed:
			doc.save(ignore_permissions=True)
		types.append(
			{
				"type": label,
				"fee": doc.fee_amount,
				"ages": f"{doc.lower_age_limit}-{doc.upper_age_limit}"
				if doc.requires_age_requirement
				else "any",
				"changed": changed,
			}
		)
	result["membership_types"] = types

	nss = frappe.get_single(SETTINGS)
	changed = {}
	for field in ANCHORS:
		if nss.meta.has_field(field) and not nss.get(field):
			nss.set(field, ANCHOR_LEVEL)
			changed[field] = ANCHOR_LEVEL
	if nss.meta.has_field("vmms_issues_volunteer_cards") and nss.get("vmms_issues_volunteer_cards") != 0:
		nss.vmms_issues_volunteer_cards = 0
		changed["vmms_issues_volunteer_cards"] = 0
	for field, title in SIGNATORIES.items():
		if nss.meta.has_field(field) and not nss.get(field):
			nss.set(field, title)
			changed[field] = title
	if changed:
		nss.save(ignore_permissions=True)
	result["settings_set"] = changed
	result["workflows"] = frappe.get_all(
		"VMMS Approval Workflow", fields=["name", "workflow_for"], order_by="workflow_for"
	)
	return result


# --- branch transfers (configure_branch_transfers.py) -------------------------


def branch_transfers(frappe, settings: dict, apply: bool) -> dict:
	"""Two-branch approval for transfers: the branch left releases, the branch joined accepts."""
	from vmmsx.setup import branch_transfer

	if not frappe.get_meta("VMMS Approval Stage").has_field("anchor_field"):
		raise ValueError("The approval stage's Route From Field is missing: the site needs migrating.")
	before = branch_transfer.plan()
	if not before["role"]:
		raise ValueError(
			"Set Branch Transfer Scope Role in National Society Settings first (the Roles step does)."
		)
	result = {"before": before}
	if apply:
		result["after"] = branch_transfer.configure()
	return result


# --- county map (attach_county_map.py) ----------------------------------------

BOUNDARY_FILE_FIELD = "vmms_boundary_file"
BOUNDARY_CREDIT_FIELD = "vmms_boundary_credit"


def county_map(frappe, settings: dict, apply: bool) -> dict:
	"""Attach the 47 county boundaries to National Society Settings, for the Region and National maps."""
	from vmmsx.analytics.services import boundaries, oversight

	if not frappe.get_meta(SETTINGS).has_field(BOUNDARY_FILE_FIELD):
		raise ValueError("The County Boundaries field is missing: the site needs migrating.")
	area = oversight.national_area()
	if not area:
		raise ValueError("The site has no national node: run the Geography step first.")

	content = COUNTY_MAP.read_bytes()
	counties = oversight.counties(area)
	matched = boundaries._match(boundaries._layers(content), counties)
	missing = sorted(unit["label"] for unit in counties if unit["name"] not in matched)
	# The fingerprint Frappe itself keeps on a File.
	digest = hashlib.md5(content).hexdigest()
	current_url = frappe.db.get_single_value(SETTINGS, BOUNDARY_FILE_FIELD)
	current_hash = (
		frappe.db.get_value("File", {"file_url": current_url}, "content_hash") if current_url else None
	)
	result = {
		"counties": len(counties),
		"matched": len(matched),
		"unmatched": missing,
		"currently_attached": current_url,
		"already_this_file": bool(current_hash and current_hash == digest),
	}
	if not apply:
		return result
	if missing:
		raise ValueError(f"{len(missing)} counties have no shape in the map: {', '.join(missing)}.")
	if not result["already_this_file"]:
		doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": COUNTY_MAP.name,
				"is_private": 0,
				"content": content,
				"attached_to_doctype": SETTINGS,
				"attached_to_name": SETTINGS,
				"attached_to_field": BOUNDARY_FILE_FIELD,
			}
		).insert(ignore_permissions=True)
		frappe.db.set_single_value(SETTINGS, BOUNDARY_FILE_FIELD, doc.file_url)
		result["attached"] = doc.file_url
	credit = (settings.get("boundary_credit") or "").strip()
	if credit:
		frappe.db.set_single_value(SETTINGS, BOUNDARY_CREDIT_FIELD, credit)
	frappe.clear_document_cache(SETTINGS, SETTINGS)
	return result


# --- payments (site-setup/09_payments.py) -------------------------------------

GATEWAY = "Mpesa Daraja"
MANUAL = "Manual"
PAYMENT_SETTINGS = "OneRC Payment Settings"
# The keys are typed into OneRC Payment Settings in Desk, never on this page:
# a setup form that held them would be one more place a secret is stored.
SECRETS = ("mpesa_consumer_key", "mpesa_consumer_secret", "mpesa_passkey", "mpesa_security_credential")


def payments(frappe, settings: dict, apply: bool) -> dict:
	"""M-Pesa as the only way to pay a membership fee."""
	from frappe.utils.password import get_decrypted_password

	from vmmsx.member.services import methods

	shortcode = (settings.get("mpesa_shortcode") or "").strip()
	callback = (settings.get("mpesa_callback_base_url") or "").strip().rstrip("/")
	if not shortcode or not callback:
		raise ValueError("Fill in the M-Pesa shortcode and callback address on the setup form first.")
	if not frappe.db.exists("OneRC Payment Gateway", GATEWAY):
		raise ValueError("The Mpesa Daraja gateway is missing: install onerc_payments and migrate first.")

	frappe.db.set_value("OneRC Payment Gateway", GATEWAY, "is_active", 1)
	pay = frappe.get_single(PAYMENT_SETTINGS)
	pay.active_gateway = GATEWAY
	pay.environment = settings.get("mpesa_environment") or "Sandbox"
	pay.default_currency = pay.default_currency or settings.get("currency") or "KES"
	pay.mpesa_shortcode = shortcode
	pay.mpesa_callback_base_url = callback
	if (settings.get("mpesa_initiator_name") or "").strip():
		pay.mpesa_initiator_name = settings["mpesa_initiator_name"].strip()
	pay.save(ignore_permissions=True)

	# The registration form's payment methods: one row per live gateway.
	methods.sync()
	nss = frappe.get_single(methods.SETTINGS_DOCTYPE)
	for row in nss.get(methods.METHODS_FIELD) or []:
		if row.gateway == GATEWAY:
			row.is_enabled = 1
			row.label = "M-Pesa"
		elif row.gateway == MANUAL:
			row.is_enabled = 0
	nss.flags.ignore_permissions = True
	nss.save()

	keys = {
		field: bool(get_decrypted_password(PAYMENT_SETTINGS, PAYMENT_SETTINGS, field, raise_exception=False))
		for field in SECRETS
	}
	problems = [
		f"{field} is empty: type it into OneRC Payment Settings."
		for field, present in keys.items()
		if not present and field != "mpesa_security_credential"
	]
	if not callback.startswith("https://") or "localhost" in callback:
		problems.append(
			f"The callback address {callback} is not a public https address; Safaricom cannot reach it."
		)
	if not (pay.mpesa_initiator_name and keys["mpesa_security_credential"]):
		problems.append(
			"Receipt lookups are off (no initiator name or security credential). Staff can still type a missing M-Pesa code in."
		)
	return {
		"gateway": GATEWAY,
		"environment": pay.environment,
		"shortcode": pay.mpesa_shortcode,
		"callback_base_url": callback,
		"keys_set": keys,
		"offered_on_the_form": [row.label for row in nss.get(methods.METHODS_FIELD) or [] if row.is_enabled],
		"problems": problems,
	}


# --- accounting (configure_membership_accounting.py) --------------------------


def accounting(frappe, settings: dict, apply: bool) -> dict:
	"""ERPNext ready to receive membership fees: accounts, item, payment modes, settings."""
	from vmmsx.setup import membership_accounting

	if "erpnext" not in frappe.get_installed_apps():
		raise ValueError("ERPNext is not installed on this site, so there is nothing to post to.")
	before = membership_accounting.plan()
	after = membership_accounting.configure(
		company=(settings.get("accounting_company") or "").strip() or None,
		mpesa_account=(settings.get("mpesa_account") or "").strip() or None,
		income_account=(settings.get("income_account") or "").strip() or None,
		starts_on=settings.get("posting_starts_on") or None,
		enable=bool(int(settings.get("posting_enabled") or 0)),
	)
	return {"before": before, "after": after, "ready": not after["problems"]}


# --- numbering (configure_numbering.py) ---------------------------------------

# Read from the old site on 2026-11-03. The form's values raise these, never lower them.
OLD_VOLUNTEER_COUNTER = 31709
OLD_SERIES = {
	"VM-MEM-2025-": 31,
	"VM-MEM-2026-": 1474,
	"VM-MSH-2025-": 71,
	"VM-MSH-2026-": 2593,
}


def numbering(frappe, settings: dict, apply: bool) -> dict:
	"""Continue the old VMMS's volunteer, member and membership numbers."""
	from vmmsx.setup import numbering as counters

	options = frappe.get_meta("VMMS Member").get_field("naming_series").options or ""
	if "VM-MEM-" not in options:
		raise ValueError(
			"This site's vmmsx is not the vmms_kenya numbering: deploy the vmms_kenya branch first."
		)
	volunteer = max(OLD_VOLUNTEER_COUNTER, int(settings.get("old_volunteer_counter") or 0))
	series = parse_series(settings.get("old_series"))
	result = {"before": counters.plan(volunteer, series)}
	if apply:
		result["after"] = counters.raise_counters(volunteer, series)
	return result


def parse_series(value) -> dict[str, int]:
	"""Lines such as `VM-MEM-2026-=1500`, on top of the floors read from the old site."""
	floors = dict(OLD_SERIES)
	for line in (value or "").replace(",", "\n").splitlines():
		line = line.strip()
		if not line:
			continue
		key, _, number = line.partition("=")
		key, number = key.strip(), number.strip()
		if not key.startswith(("VM-MEM-", "VM-MSH-")) or not number.isdigit():
			raise ValueError(f"Expected a line such as VM-MEM-2026-=1500, not {line!r}.")
		floors[key] = max(floors.get(key, 0), int(number))
	return floors
