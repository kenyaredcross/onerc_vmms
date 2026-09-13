"""The portal's language preference, shared with Frappe Desk."""

import frappe
from frappe import _

SUPPORTED_LANGUAGES = {"en", "sw", "ar", "pt", "fr"}


def _language_code(language: str) -> str:
	language = (language or "").strip().lower().replace("_", "-").split("-", 1)[0]
	if language not in SUPPORTED_LANGUAGES:
		frappe.throw(_("Unsupported language"), frappe.ValidationError)
	return language


@frappe.whitelist(allow_guest=True)
def get_translations(language: str) -> dict:
	"""Return Frappe's merged catalogue so every portal surface can translate."""
	language = _language_code(language)
	return {
		"language": language,
		"translations": frappe.translate.get_all_translations(language),
	}


@frappe.whitelist(allow_guest=True)
def set_language(language: str) -> dict:
	"""Set the caller's portal language and, when signed in, their Desk language."""
	language = _language_code(language)

	frappe.local.cookie_manager.set_cookie(
		"preferred_language", language, max_age=365 * 24 * 60 * 60, deduplicate=True
	)
	frappe.local.lang = language
	if frappe.session.user != "Guest":
		frappe.db.set_value("User", frappe.session.user, "language", language, update_modified=False)
		frappe.clear_cache(user=frappe.session.user)
		frappe.local.cookie_manager.set_cookie(
			"user_lang", language, max_age=365 * 24 * 60 * 60, deduplicate=True
		)

	return {"language": language, "desk_synced": frappe.session.user != "Guest"}
