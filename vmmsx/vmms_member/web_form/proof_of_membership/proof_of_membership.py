# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Retain the legacy form definition while routing page visits to the complete portal journey."""


def get_context(context):
	"""Send legacy page links to the complete registration journey."""
	import frappe

	frappe.local.flags.redirect_location = '/portal/membership'
	raise frappe.Redirect
