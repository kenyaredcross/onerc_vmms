# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

import frappe

from vmmsx.spa import resolve_assets

no_cache = 1


def get_context(context):
	context.no_cache = 1
	assets = resolve_assets()
	context.bundle_js = assets["js"]
	context.bundle_css = assets["css"]
	# Read by the SDK from window.csrf_token for POSTs. Not exercised in Phase 0
	# (the probe is a GET), but the page has to carry it before the first write.
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.sitename = frappe.local.site
	return context
