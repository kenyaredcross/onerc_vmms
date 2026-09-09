# Copyright (c) 2026, Kenya Red Cross Society and contributors
# For license information, please see license.txt

import frappe

CATEGORY_ORDER = [
	"General",
	"Membership",
	"Volunteering",
	"Opportunities",
	"Events",
	"Deployments",
	"Account and Profile",
]


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method -- published help content only
def get_help_content():
	"""About blurb plus published FAQs, grouped by category for the portal Help page."""
	return {
		"about": get_about(),
		"categories": get_faqs_by_category(),
	}


def get_about():
	about = frappe.get_cached_doc("VMMS About")
	return {
		"heading": about.heading,
		"subheading": about.subheading,
		"body": about.body,
	}


def get_faqs_by_category():
	# get_all skips permission checks by design; the is_published filter is the only gate,
	# and every argument here is hardcoded so no caller input reaches the query.
	faqs = frappe.get_all(
		"FAQ",
		filters={"is_published": 1},
		fields=["name", "question", "answer", "category", "display_order"],
		order_by="display_order asc, creation asc",
	)

	grouped = {}
	for faq in faqs:
		grouped.setdefault(faq.category, []).append(faq)

	known = [
		{"category": category, "faqs": grouped.pop(category)}
		for category in CATEGORY_ORDER
		if category in grouped
	]
	# Anything left over came from a category that was removed from the Select options.
	extra = [{"category": category, "faqs": grouped[category]} for category in sorted(grouped)]

	return known + extra
