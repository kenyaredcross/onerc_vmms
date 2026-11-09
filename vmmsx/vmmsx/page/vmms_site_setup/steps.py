# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The setup steps, the values they read, and the runner that does each one.

**Temporary.** This folder exists to set up a Frappe Cloud site, where the
setup scripts in `VMMS-Kenya scripts` cannot run because there is no shell. It
is removed once production is set up: delete the folder and add a patch that
deletes the `vmms-site-setup` Page and the two globals named below. Nothing
else in the app imports it.

**Check, then Run.** A Check does the step and rolls it back, reporting what it
would change — the scripts' default. A Run does it and commits — the scripts'
`--apply`. Every step is safe to run again: it creates only what is missing.

Each runs as a background job, as Administrator (the scripts ran as
Administrator too), and its last result is kept so the page can show it after a
reload. Only one step runs at a time.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field

import frappe
from frappe.utils import get_datetime, get_url, now_datetime, time_diff_in_seconds

from . import geography, kenya, roles, verify

SETTINGS_KEY = "vmmsx_site_setup"
RESULTS_KEY = "vmmsx_site_setup_results"
# A stored result longer than this is cut: the global it lives in is a Text column.
RESULT_LIMIT = 60000
JOB_TIMEOUT = 60 * 60


@dataclass(frozen=True)
class Step:
	key: str
	title: str
	summary: str
	work: Callable
	uses: tuple[str, ...] = field(default_factory=tuple)
	check_only: bool = False


STEPS = (
	Step(
		"geography",
		"Geography",
		"Eight regions, 47 counties and the KRCS sub-counties, under the national node the setup wizard made.",
		geography.run,
	),
	Step(
		"vocabularies",
		"Picker lists",
		"Professions, licence types, languages, disabilities, ID types and the old reasons to join; region names without “KRCS ”.",
		kenya.vocabularies,
	),
	Step(
		"roles",
		"Roles",
		"County Coordinator for everything done in a county; Head of Region and NSD Coordinator for oversight.",
		roles.run,
		uses=("nsd_emails",),
	),
	Step(
		"registration",
		"Registration",
		"Kenya's registration rules, the four membership types and their ages, approval workflows, no volunteer cards, and the certificate with its signatories.",
		kenya.registration,
	),
	Step(
		"branch_transfers",
		"Branch transfers",
		"A transfer is released by the branch being left, then accepted by the branch being joined.",
		kenya.branch_transfers,
	),
	Step(
		"county_map",
		"County map",
		"The 47 county boundaries for the Region and National maps.",
		kenya.county_map,
		uses=("boundary_credit",),
	),
	Step(
		"payments",
		"Payments",
		"M-Pesa as the only way to pay a membership fee. The keys are typed into OneRC Payment Settings, not here.",
		kenya.payments,
		uses=(
			"mpesa_environment",
			"mpesa_shortcode",
			"mpesa_callback_base_url",
			"mpesa_initiator_name",
			"currency",
		),
	),
	Step(
		"accounting",
		"Accounting",
		"ERPNext accounts, item and payment modes for membership fees, and the date posting starts.",
		kenya.accounting,
		uses=(
			"accounting_company",
			"mpesa_account",
			"income_account",
			"posting_starts_on",
			"posting_enabled",
		),
	),
	Step(
		"numbering",
		"Numbering",
		"Volunteer, member and membership numbers carry on from the old VMMS.",
		kenya.numbering,
		uses=("old_volunteer_counter", "old_series"),
	),
	Step(
		"verify",
		"Is the site ready?",
		"Checks everything above, and what is still needed before real people use the site.",
		verify.run,
		check_only=True,
	),
)

BY_KEY = {step.key: step for step in STEPS}


def defaults() -> dict:
	return {
		"nsd_emails": "",
		"boundary_credit": "Boundaries: IEBC, via OCHA (CC BY-IGO)",
		"mpesa_environment": "Sandbox",
		"mpesa_shortcode": "",
		"mpesa_callback_base_url": get_url(),
		"mpesa_initiator_name": "",
		"currency": "KES",
		"accounting_company": "",
		"mpesa_account": "",
		"income_account": "",
		"posting_starts_on": "",
		"posting_enabled": 0,
		"old_volunteer_counter": "",
		"old_series": "",
	}


def settings() -> dict:
	saved = _read(SETTINGS_KEY)
	return {**defaults(), **{key: value for key, value in saved.items() if key in defaults()}}


def save_settings(values: dict) -> dict:
	known = defaults()
	merged = {**settings(), **{key: value for key, value in (values or {}).items() if key in known}}
	frappe.db.set_global(SETTINGS_KEY, json.dumps(merged))
	return merged


def results() -> dict:
	"""Each step's last outcome. A "running" mark older than the job's time limit
	is a job that died without saying so, and is reported as failed."""
	stored = _read(RESULTS_KEY)
	for row in stored.values():
		if row.get("status") == "running" and _stale(row.get("at")):
			row.update(status="failed", error="The job stopped without finishing. Run the step again.")
	return stored


def running() -> str | None:
	"""The step a job is doing now, if any."""
	for key, row in results().items():
		if row.get("status") == "running":
			return key
	return None


def _stale(at) -> bool:
	try:
		started = get_datetime(at)
	except Exception:
		return True
	return time_diff_in_seconds(now_datetime(), started) > JOB_TIMEOUT + 300


def start(key: str, apply: bool) -> None:
	step = BY_KEY.get(key)
	if not step:
		frappe.throw(f"There is no setup step {key!r}.")
	busy = running()
	if busy:
		frappe.throw(f"{BY_KEY[busy].title} is still running. Wait for it to finish.")
	apply = bool(apply) and not step.check_only
	_record(
		key,
		{
			"status": "running",
			"mode": "run" if apply else "check",
			"by": frappe.session.user,
			"at": str(now_datetime()),
		},
	)
	frappe.db.commit()
	frappe.enqueue(
		"vmmsx.vmmsx.page.vmms_site_setup.steps.execute",
		queue="long",
		timeout=JOB_TIMEOUT,
		job_id=f"vmms_site_setup::{key}",
		deduplicate=True,
		key=key,
		apply=apply,
		by=frappe.session.user,
	)


def execute(key: str, apply: bool, by: str) -> None:
	"""The background job: do the step, commit or roll back, keep the outcome."""
	step = BY_KEY[key]
	mode = "run" if apply else "check"
	previous = frappe.session.user
	frappe.set_user("Administrator")
	try:
		result = step.work(frappe, settings(), apply)
		if apply:
			frappe.db.commit()
		else:
			frappe.db.rollback()
		outcome = {"status": "done", "mode": mode, "result": result}
	except Exception as error:
		frappe.db.rollback()
		frappe.log_error(title=f"Site setup: {step.title}")
		outcome = {"status": "failed", "mode": mode, "error": str(error) or error.__class__.__name__}
	finally:
		frappe.set_user(previous)
	_record(key, {**outcome, "by": by, "at": str(now_datetime())})
	frappe.db.commit()


def _record(key: str, row: dict) -> None:
	stored = results()
	text = json.dumps(row, default=str)
	if len(text) > RESULT_LIMIT:
		row = {
			**{k: v for k, v in row.items() if k != "result"},
			"result": {"note": "The result was too long to keep."},
		}
	stored[key] = row
	frappe.db.set_global(RESULTS_KEY, json.dumps(stored, default=str))


def _read(key: str) -> dict:
	try:
		return json.loads(frappe.db.get_global(key) or "{}")
	except ValueError:
		return {}
