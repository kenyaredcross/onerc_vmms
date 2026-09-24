"""Token-based auth for the standalone offline mobile mini app.

The mini app runs from a ``file://`` origin inside a WebView and cannot use
Frappe's cookie session, so it authenticates with an API key/secret pair.
"""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60 * 5)
def mobile_login(usr: str, pwd: str) -> dict:
	"""Authenticate an email/password and return a Frappe API key/secret pair.

	Used by the standalone offline mini app, which runs from a ``file://``
	origin inside a WebView and therefore cannot use Frappe's cookie session.
	The returned pair is sent on every subsequent request as
	``Authorization: token <api_key>:<api_secret>`` (validated by
	``frappe/auth.py`` ``validate_auth_via_api_keys``).
	"""
	from frappe.core.doctype.user.user import User

	if not usr or not pwd:
		frappe.throw(_("Email and password are required"), frappe.AuthenticationError)

	user = User.find_by_credentials(usr, pwd)
	if not user or not user.get("is_authenticated"):
		frappe.throw(_("Invalid email or password"), frappe.AuthenticationError)
	if not user.get("enabled") and user.get("name") != "Administrator":
		frappe.throw(_("User is disabled"), frappe.AuthenticationError)

	user_name = user["name"]

	# Mint a fresh api_secret (and api_key on first use). We can't call the stock
	# generate_keys() — it requires "System Manager". Since the caller has already
	# proven the password, generate the pair directly with ignore_permissions.
	user_doc = frappe.get_doc("User", user_name)
	api_secret = frappe.generate_hash(length=15)
	if not user_doc.api_key:
		user_doc.api_key = frappe.generate_hash(length=15)
	user_doc.api_secret = api_secret
	user_doc.save(ignore_permissions=True)
	frappe.db.commit()

	return {
		"api_key": user_doc.api_key,
		"api_secret": api_secret,
		"user": user_name,
	}
