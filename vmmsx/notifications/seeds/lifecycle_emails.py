# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The four things a society says to somebody about their own application.

**These are `Email Template` records, and the reason is the one the welcome
email states**: message wording belongs on the desk, in a record a society can
edit without a deploy, rather than in a template file only a developer can
reach. A branch that wants to add its office hours to the acknowledgement, or
to say something warmer on approval, edits a record.

Each is created once and never edited again — see
`notifications/services/lifecycle.py::install` — so a society's rewrite
survives every deploy afterwards.

**Society-neutral, like the shipped content blocks.** No country, no currency,
no society name and no count appears below. The society's own name arrives at
render time through `lockup()`, which is why the masthead is not written here
either: `templates/emails/standard.html` puts it above every message the site
sends.

**Plain text with the lightest possible markup**, because these are read on a
phone in a mail client nobody chose. The context each one renders against is
built by `lifecycle.py` and documented on each template's own record.
"""

# The names are the site's keys for these records, so they are opaque-ish and
# stable: a society may rewrite the subject and the body, and nothing looks a
# template up by what it says.
RECEIVED = "VMMS Application Received"
APPROVED = "VMMS Application Approved"
REJECTED = "VMMS Application Not Accepted"
MORE_INFO = "VMMS Application Needs More Information"

# The greeting and sign-off every one of these messages shares.
#
# **Composed by concatenation, not by `str.format`.** These bodies are Jinja and
# Jinja's variables are `{{ name }}`; `str.format` reads `{{` as an escaped
# literal brace and collapses it to `{`. So wrapping the body through `.format`
# turned `{{ holder_name }}` into `{ holder_name }` before the template was ever
# saved, Jinja found no variable to substitute, and every applicant was greeted
# by name as **"Dear { holder_name },"**. The body kept its own variables
# because only the frame passed through the formatter, which is exactly why it
# survived review: the mail looked right apart from the first line.
_HEAD = "<p>Dear {{ holder_name }},</p>\n"
_FOOT = '\n<p style="margin-top:20px">{{ society_name }}</p>\n'


def _wrap(body: str) -> str:
	"""Frame one message. No formatter touches Jinja braces on the way through."""
	return f"{_HEAD}{body}{_FOOT}"


TEMPLATES = (
	{
		"name": RECEIVED,
		"subject": "We have your {{ kind }} application",
		"body": _wrap(
			"""<p>
	Thank you. Your {{ kind }} application has been received and is with
	{{ geo_path or "your branch" }} for review.
</p>
<p>
	Your reference is <strong>{{ record_id }}</strong>. Nobody needs to be chased:
	it is already in the queue of the people responsible for that place.
</p>
{% if portal_url %}
<p><a href="{{ portal_url }}">Follow where it has got to</a>.</p>
{% endif %}"""
		),
		"description": (
			"Sent once, when an application is submitted for review. Context: holder_name, kind,"
			" record_id, geo_path, portal_url, society_name."
		),
	},
	{
		"name": APPROVED,
		"subject": "Welcome, {{ holder_name }}",
		"body": _wrap(
			"""<p>
	Your {{ kind }} application has been approved. Welcome.
</p>
<p>
	Your {{ kind }} card is attached to this message and is also on your profile,
	where it stays up to date if anything about your record changes.
</p>
<p>
	The code on the card can be scanned by anybody who needs to check it. They see
	your name, your branch and whether it is current, and nothing else.
</p>
{% if portal_url %}
<p><a href="{{ portal_url }}">Open your profile</a>.</p>
{% endif %}"""
		),
		"description": (
			"Sent once, when an application is approved and the record it creates exists. The card"
			" PDF is attached by the sender, not by this template. Context: holder_name, kind,"
			" record_id, geo_path, portal_url, society_name."
		),
	},
	{
		"name": REJECTED,
		"subject": "About your {{ kind }} application",
		"body": _wrap(
			"""<p>
	Your {{ kind }} application ({{ record_id }}) has not been accepted on this
	occasion.
</p>
{% if reason %}
<p><strong>Why:</strong> {{ reason }}</p>
{% endif %}
<p>
	If anything about that is unclear, your branch is the right place to ask.
</p>"""
		),
		"description": (
			"Sent once, when an application is declined. `reason` is the decision's own reason and"
			" is always present, because the engine refuses a rejection without one. Context:"
			" holder_name, kind, record_id, reason, geo_path, portal_url, society_name."
		),
	},
	{
		"name": MORE_INFO,
		"subject": "Your {{ kind }} application needs something more",
		"body": _wrap(
			"""<p>
	Your {{ kind }} application ({{ record_id }}) has been sent back to you, because
	the people reviewing it need something more before they can decide.
</p>
{% if reason %}
<p><strong>What is needed:</strong> {{ reason }}</p>
{% endif %}
<p>
	Nothing has been lost. Add what is asked for and submit it again, and it goes
	back to the same people.
</p>
{% if portal_url %}
<p><a href="{{ portal_url }}">Open your application</a>.</p>
{% endif %}"""
		),
		"description": (
			"Sent when an approver asks for more information, which returns the application to the"
			" applicant. Context: holder_name, kind, record_id, reason, geo_path, portal_url,"
			" society_name."
		),
	},
)
