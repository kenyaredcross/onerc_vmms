# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The SMS channel: a draft campaign, filed for onerc_sms to approve and send.

The console's Communication screen sends on three channels and vmmsx owns two of
them. The in-app notification and the email are `VMMS Announcement`'s fan-out,
which this app wrote. SMS is `onerc_sms`'s, an optional companion app, and this
module is the whole of the seam to it — the same shape as the learning seam in
`volunteer/services/learning.py`: one file, named as a seam, and no other file in
this app mentions an SMS doctype.

**Nothing here sends anything.** It creates a Draft `SMS Campaign` and stops.
onerc_sms ships an approval workflow — Draft, Pending, Approved — and
`SMSCampaign.validate_approval()` refuses to submit a campaign that has not
reached Approved. Reaching around that to dispatch from here would be this app
deciding that its own console outranks another app's approval policy, which is
exactly the argument vmmsx makes in the other direction about its own engine.
So the console composes, files, and hands back a link to the campaign on the
desk, where whoever holds the approver role finishes it.

**The recipients are resolved here and written down, rather than left as a
query.** onerc_sms's "Doctype Query" source would be the obvious choice and is
the wrong one twice over:

1. *It cannot express the audience.* `SMS Campaign Filter` offers `equals`,
   `contains` and their negations — there is no `in` — so a geo filter could
   name one node and never the subtree beneath it. A branch coordinator
   addressing their branch would silently miss every ward under it, which is
   the failure that looks like it worked.
2. *An approver should approve a list, not a query.* A query approved on Monday
   and dispatched on Friday reaches whoever matches it on Friday. The number of
   people a broadcast reaches is the thing being approved.

So the audience is resolved through `audience.py` — the same resolver the
in-app notification and the email use, so all three channels reach the same set
of people — and the numbers are written onto the campaign as its manual
recipient list.

**Scope is the caller's, twice.** `audience.py` reads with
`ignore_permissions` on purpose (its own docstring argues why a fan-out must
not be narrowed by the reader), so the floor here is the check made *before*
this is reached: `api/communication.py` asserts the caller may create an
announcement anchored at this node, which is core's geo scoping on a scopeable
doctype. The campaign is then inserted as the caller, so onerc_sms's own
permissions have their say as well.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

from vmmsx.notifications.services import audience

CAMPAIGN_DOCTYPE = "SMS Campaign"

#: onerc_sms's own manual-recipient mode: a list of numbers on the campaign
#: rather than a query it re-runs at send time. See the module docstring.
SOURCE_MANUAL = "Manual"

STATUS_DRAFT = "Draft"

#: What `SMSCampaign.resolve_from_manual` will accept. A number without a
#: country code is logged and skipped there, silently as far as the composer is
#: concerned — so it is counted here instead, and reported, because "we could
#: not text 40 of these people" is something to know before filing rather than
#: after sending.
INTERNATIONAL_PREFIX = "+"


def installed() -> bool:
	"""Is onerc_sms on this site at all?

	Asked by doctype rather than by app name, the same graceful-absence contract
	`staff/services/permissions.py::_grant` keeps: a site without the companion
	app is an ordinary site, and the Communication screen simply does not offer
	the channel.
	"""
	return bool(frappe.db.exists("DocType", CAMPAIGN_DOCTYPE))


def available() -> bool:
	"""May this caller file a campaign — is the app here, and are they allowed?"""
	return installed() and bool(frappe.has_permission(CAMPAIGN_DOCTYPE, ptype="create"))


def reachable(geo_node: str, who: str) -> dict:
	"""How many of this audience carry a number, and how many do not.

	Both halves, because only one of them is actionable: a coordinator who can
	see that a third of their volunteers have no phone number on file knows to
	go and collect them, and a screen reporting only the reachable count hides
	exactly that.
	"""
	addressed = audience.profiles(geo_node, who)
	numbers = _sendable(audience.phones(addressed))

	return {
		"addressed": len(addressed),
		"reachable": len(numbers["ok"]),
		"unreachable": len(addressed) - len(numbers["ok"]),
		"malformed": len(numbers["bad"]),
	}


def draft(name: str, message: str, geo_node: str, who: str, scheduled_at=None) -> dict:
	"""File a Draft campaign to this audience. Returns what was filed.

	`scheduled_at` defaults to now, which does **not** mean "send now": nothing
	is dispatched until the campaign is approved and submitted in onerc_sms, and
	the field is what that submission compares against to decide between sending
	immediately and queueing. A composer who wants it held until Thursday says
	so; a composer who says nothing means "as soon as it is approved".
	"""
	if not available():
		frappe.throw(
			_("SMS is not available on this site."),
			frappe.PermissionError,
			title=_("No SMS Channel"),
		)

	if not (message or "").strip():
		frappe.throw(_("An SMS needs something to say."), frappe.ValidationError)

	addressed = audience.profiles(geo_node, who)
	numbers = _sendable(audience.phones(addressed))

	if not numbers["ok"]:
		frappe.throw(
			_(
				"Nobody in that audience has a phone number on file, so there is no campaign to file."
			),
			frappe.ValidationError,
			title=_("No Recipients"),
		)

	campaign = frappe.new_doc(CAMPAIGN_DOCTYPE)
	campaign.campaign_name = name
	campaign.message = message
	campaign.source_type = SOURCE_MANUAL
	campaign.phone_numbers = "\n".join(numbers["ok"])
	campaign.status = STATUS_DRAFT
	campaign.scheduled_at = scheduled_at or now_datetime()
	# Inserted as the caller, not elevated: whether somebody may file a campaign
	# is onerc_sms's question and it should be asked of them, not answered here.
	campaign.insert()

	return {
		"campaign": campaign.name,
		"recipients": len(numbers["ok"]),
		"malformed": len(numbers["bad"]),
		"addressed": len(addressed),
		# Where to finish it. The desk, because approving a campaign is
		# onerc_sms's own workflow on its own form, and building a second face
		# for it here would be this app owning a policy it deliberately does not.
		"url": f"/app/sms-campaign/{campaign.name}",
	}


def _sendable(numbers: list[str]) -> dict[str, list[str]]:
	"""Split resolved numbers into the ones onerc_sms will take and the rest.

	The rule is onerc_sms's, not this app's — `resolve_from_manual` skips
	anything without a country code — and it is applied here so the count a
	composer is shown is the count that will actually be texted. Applying it in
	two places would be two answers; applying it in neither is how a campaign
	reports 900 recipients and sends 600.
	"""
	ok, bad = [], []

	for number in numbers:
		(ok if number.startswith(INTERNATIONAL_PREFIX) else bad).append(number)

	return {"ok": ok, "bad": bad}
