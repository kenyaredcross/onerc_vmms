# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What the Site Setup page calls. System Managers only. See `steps.py`."""

import frappe

from . import steps

ROLE = "System Manager"


@frappe.whitelist()
def state() -> dict:
	frappe.only_for(ROLE)
	return {
		"steps": [
			{
				"key": step.key,
				"title": step.title,
				"summary": step.summary,
				"uses": list(step.uses),
				"check_only": step.check_only,
			}
			for step in steps.STEPS
		],
		"settings": steps.settings(),
		"results": steps.results(),
		"running": steps.running(),
	}


@frappe.whitelist(methods=["POST"])
def save_settings(values: str | dict) -> dict:
	frappe.only_for(ROLE)
	return steps.save_settings(frappe.parse_json(values) or {})


@frappe.whitelist(methods=["POST"])
def start(step: str, apply: int | str = 0) -> dict:
	frappe.only_for(ROLE)
	steps.start(step, bool(int(apply or 0)))
	return state()
