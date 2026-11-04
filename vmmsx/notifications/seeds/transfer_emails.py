# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What a volunteer is told about their own branch transfer.

`Email Template` records for the same reason the application messages are
(see `lifecycle_emails.py`): a society rewords them on the desk without a
deploy, and `lifecycle.install` seeds them once and never overwrites them.

Three messages, one per thing that happens to a transfer: it was received, it
was approved, it was declined. Moving through the first branch's release to the
second branch's acceptance sends nothing — the volunteer is waiting either way,
and one letter saying so is enough.

Context: holder_name, record_id, from_place, to_place, raised_by_branch,
effective_date, is_effective, reason, portal_url, society_name.
"""

from vmmsx.notifications.seeds.lifecycle_emails import _wrap

REQUESTED = "VMMS Transfer Requested"
APPROVED = "VMMS Transfer Approved"
DECLINED = "VMMS Transfer Declined"

_REFERENCE = """<p style="margin:18px 0;padding:12px 16px;background-color:#F6F7F9;border-radius:6px">
	Your reference is <strong>{{ record_id }}</strong>. Please quote it if you contact
	your branch about this transfer.
</p>"""

TEMPLATES = (
	{
		"name": REQUESTED,
		"subject": "Your transfer request has been received",
		"body": _wrap(
			"""<p>
	{% if raised_by_branch %}{{ from_place }} has asked to move you to {{ to_place }}.{% else %}We have your request to move from {{ from_place }} to {{ to_place }}.{% endif %}
</p>"""
			+ _REFERENCE
			+ """<p>
	{% if raised_by_branch %}{{ to_place }} will review it next.{% else %}{{ from_place }} will review it first, then {{ to_place }}.{% endif %}
	We will write to you again when it has been decided. Until then you are still
	a volunteer with {{ from_place }}.
</p>
{% if portal_url %}
<p><a href="{{ portal_url }}">See your transfer</a></p>
{% endif %}"""
		),
	},
	{
		"name": APPROVED,
		"subject": "Your transfer to {{ to_place }} has been approved",
		"body": _wrap(
			"""<p>
	Your transfer from {{ from_place }} to {{ to_place }} has been approved.
	{% if is_effective %}You are now a volunteer with {{ to_place }}.{% else %}You will be a volunteer with {{ to_place }} from {{ effective_date }}.{% endif %}
</p>"""
			+ _REFERENCE
			+ """<p>
	Your hours, deployments and certificates stay on your record.
</p>
{% if portal_url %}
<p><a href="{{ portal_url }}">Open your profile</a></p>
{% endif %}"""
		),
	},
	{
		"name": DECLINED,
		"subject": "A decision on your transfer request",
		"body": _wrap(
			"""<p>
	Your transfer from {{ from_place }} to {{ to_place }} has not been approved.
	You are still a volunteer with {{ from_place }}.
</p>"""
			+ _REFERENCE
			+ """{% if reason %}
<p><strong>Reason given:</strong> {{ reason }}</p>
{% endif %}
<p>
	If you would like to talk about it, {{ from_place }} is the right place to ask.
</p>"""
		),
	},
)
