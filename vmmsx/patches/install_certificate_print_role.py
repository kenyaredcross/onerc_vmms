# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Who, besides the member, may print a membership certificate — and the logo.

Two things, both of which a site that already installed vmmsx needs and cannot
get from the patch that first set the Member module up: a patch runs **once per
site, by name**, and `setup_member_module` is long since in every Patch Log.

**1. The print role.** `vmms_certificate_print_role`, a Custom Field vmmsx owns
on core's National Society Settings. Core's doctype is not edited: a product
pushing its fields into the shared foundation's source is how the foundation
stops being shared.

It ships **empty**, and empty means *nobody but the member*. That is the one
place in this app where blank configuration is a closed door rather than an
unconstrained one, and it is deliberate — see `certificate.may_print()`. A blank
access rule that read as "everybody" would hand every member's certificate to
every logged-in user and look exactly like a working system while doing it.

**2. The certificate template, refreshed for the logo** — but only if the
society has not touched it. The shipped template gained a logo block, and a site
installed before that has the old body sitting in a `VMMS Template` row. That
row is *configuration*: its description says "edit freely", and rewriting an
administrator's certificate on migrate would be this app taking back something
it gave away.

So the body is replaced only when it is still byte-for-byte what vmmsx shipped,
recognised by the hash below. Anything else — one character changed — is left
exactly as it is, and the society adds `{{ society_logo }}` themselves if they
want it. The hash rather than the old text because the old text is markup, and
markup does not go in a Python file; a test asserts as much.
"""

import hashlib
from pathlib import Path

import frappe

SETTINGS_DOCTYPE = "National Society Settings"
TEMPLATE_DOCTYPE = "VMMS Template"

PRINT_ROLE_FIELD = "vmms_certificate_print_role"
CERTIFICATE_TEMPLATE_KEY = "membership_certificate"

SEED = Path(frappe.get_app_path("vmmsx")) / "templating" / "seeds" / "membership_certificate.html"

# sha256 of the body vmmsx shipped before the logo was added. A row still
# carrying exactly this is one nobody has edited, and the only one this patch
# will overwrite.
UNEDITED_V1_BODY_SHA256 = "c4766714b1d8220e35c0f750e703cf16bdf81a942e1427265a6c928627c343bf"

CONTEXT_KEYS = (
	"member_name, membership_id, membership_type, geo_path, valid_from, valid_to, benefits,"
	" society_name, society_logo, issued_on, payment_receipt, payment_transaction"
)


def execute():
	install_print_role_field()
	refresh_unedited_certificate_template()


def install_print_role_field() -> None:
	"""Install the print-role setting, once."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if frappe.db.exists("Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": PRINT_ROLE_FIELD}):
		return

	create_custom_field(
		SETTINGS_DOCTYPE,
		{
			"fieldname": PRINT_ROLE_FIELD,
			"label": "Certificate Print Role",
			# A Link to Role, so the desk offers only roles that exist. vmmsx
			# still re-checks on every print: a Link can be left holding a role
			# that was deleted afterwards, and that must refuse rather than grant.
			"fieldtype": "Link",
			"options": "Role",
			"insert_after": "vmms_membership_scope_role",
			"description": (
				"Which role may print a membership certificate that is not their own. A member can"
				" always print theirs, recognised by the login on their Red Profile. Left empty,"
				" nobody else can print one at all. Owned by vmmsx."
			),
		},
		ignore_validate=True,
	)


def refresh_unedited_certificate_template() -> None:
	"""Give the shipped template its logo back, unless a society has edited it."""
	if not frappe.db.exists(TEMPLATE_DOCTYPE, CERTIFICATE_TEMPLATE_KEY):
		# No template on this site: `setup_member_module` seeds it from the same
		# file on first install, and it will already carry the logo.
		return

	template = frappe.get_doc(TEMPLATE_DOCTYPE, CERTIFICATE_TEMPLATE_KEY)
	current = template.body or ""

	if hashlib.sha256(current.encode()).hexdigest() != UNEDITED_V1_BODY_SHA256:
		# Either already refreshed, or edited by the society. Both are left alone:
		# this patch updates what vmmsx wrote, never what a society did.
		return

	template.body = SEED.read_text()
	template.description = (
		f"The default membership certificate. Context keys: {CONTEXT_KEYS}. Edit freely — nothing"
		" in the code depends on this wording."
	)
	template.save(ignore_permissions=True)
