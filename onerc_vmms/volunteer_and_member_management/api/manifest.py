import json

import frappe
from requests import Response


@frappe.whitelist(
	allow_guest=True
)  # nosemgrep: guest-whitelisted-method -- public PWA manifest, static content
def get_pwa_manifest():
	title = frappe.db.get_single_value("Website Settings", "app_name") or "VMMS"

	icon_url = frappe.db.get_single_value("Website Settings", "banner_image")

	manifest = {
		"name": title,
		"short_name": title,
		"description": "Easy to use, 100% open source volunteer and member management system.",
		"start_url": "/vmms",
		"scope": "/vmms",
		"display": "standalone",
		"background_color": "#ffffff",
		"theme_color": "#0F0F0F",
		"icons": [
			{
				"src": icon_url,
				"sizes": "192x192",
				"type": "image/png",
				"purpose": "maskable any",
			},
		],
	}

	frappe.response["type"] = "json"
	frappe.response["data"] = manifest
