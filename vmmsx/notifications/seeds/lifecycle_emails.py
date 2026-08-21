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
survives every deploy afterwards. The one exception is a body still holding
wording *this app* shipped and has since improved; `SHIPPED` below is what makes
that distinguishable from wording a society chose, and the mechanism is
documented on `lifecycle.install`.

**Society-neutral, like the shipped content blocks.** No country, no currency,
no society name and no count appears below. The society's own name arrives at
render time through `society_name`, which is why the masthead is not written
here either: `templates/emails/standard.html` puts it above every message the
site sends.

**Written to be read once, on a phone, by somebody who is anxious about the
answer.** That is the whole brief. Every message names what happened in its
first line, gives the reference in the second, and says what — if anything — the
reader has to do next. No message asks somebody to "kindly note", none of them
apologises for existing, and none opens with a paragraph about the society
before getting to the point. A person waiting on a decision should not have to
read to the third paragraph to find it.

**Plain text with the lightest possible markup**, because these are read in a
mail client nobody chose. The context each one renders against is built by
`lifecycle.py` and documented on each template's own record.
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

# Signed by the society, not by a system. "Kind regards" over the society's own
# name is what correspondence from a national society looks like, and it costs
# one line to stop these reading as machine output.
_FOOT = (
	'\n<p style="margin-top:24px">Kind regards,<br>'
	"<strong>{{ society_name }}</strong></p>\n"
)


def _wrap(body: str) -> str:
	"""Frame one message. No formatter touches Jinja braces on the way through."""
	return f"{_HEAD}{body}{_FOOT}"


# A reference line, identical in all four, because the reader quoting it back to
# a branch office is the point of having one.
_REFERENCE = """<p style="margin:18px 0;padding:12px 16px;background-color:#F6F7F9;border-radius:6px">
	Your reference is <strong>{{ record_id }}</strong>. Please quote it in any
	correspondence about this application.
</p>"""


TEMPLATES = (
	{
		"name": RECEIVED,
		"subject": "Your {{ kind }} application has been received",
		"body": _wrap(
			"""<p>
	Thank you for applying to volunteer your time with us. Your {{ kind }}
	application has been received and is now with
	{{ geo_path or "your branch" }} for review.
</p>"""
			+ _REFERENCE
			+ """<p>
	There is nothing further for you to do at this stage. Your application is
	already in the queue of the people responsible for that branch, and we will
	write to you again as soon as a decision has been made.
</p>
{% if portal_url %}
<p><a href="{{ portal_url }}">Track the progress of your application</a></p>
{% endif %}"""
		),
		"description": (
			"Sent once, when an application is submitted for review. Context: holder_name, kind,"
			" record_id, geo_path, portal_url, society_name."
		),
	},
	{
		"name": APPROVED,
		"subject": "Welcome to {{ society_name }}",
		"body": _wrap(
			"""<p>
	We are delighted to tell you that your {{ kind }} application has been
	approved. Welcome to {{ society_name }}.
</p>"""
			+ _REFERENCE
			+ """<p>
	Your {{ kind }} card is attached to this message and is also available on your
	profile, where it is kept up to date automatically if anything about your
	record changes.
</p>
<p>
	The code on the card can be scanned by anyone who needs to verify it. They
	will see your name, your branch and whether your record is current — and
	nothing else.
</p>
{% if portal_url %}
<p><a href="{{ portal_url }}">Open your profile</a></p>
{% endif %}
<p style="margin-top:18px">
	Thank you for choosing to give your time. We look forward to working with you.
</p>"""
		),
		"description": (
			"Sent once, when an application is approved and the record it creates exists. The card"
			" PDF is attached by the sender, not by this template. Context: holder_name, kind,"
			" record_id, geo_path, portal_url, society_name."
		),
	},
	{
		"name": REJECTED,
		"subject": "A decision on your {{ kind }} application",
		"body": _wrap(
			"""<p>
	Thank you for your interest in {{ society_name }}, and for the time you put
	into your application. After careful consideration, we are not able to take
	your {{ kind }} application forward on this occasion.
</p>"""
			+ _REFERENCE
			+ """{% if reason %}
<p><strong>Reason given:</strong> {{ reason }}</p>
{% endif %}
<p>
	This decision relates to this application only, and it does not prevent you
	from applying again in future. If anything about it is unclear, or you would
	like to discuss it, {{ geo_path or "your branch" }} is the right place to ask
	and will be glad to hear from you.
</p>
<p>
	We are grateful for your interest in the work of the Society, and we hope you
	will consider us again.
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
		"subject": "Action needed on your {{ kind }} application",
		"body": _wrap(
			"""<p>
	Your {{ kind }} application has been returned to you. The team reviewing it
	need a little more information before they can reach a decision.
</p>"""
			+ _REFERENCE
			+ """{% if reason %}
<p><strong>What is needed:</strong> {{ reason }}</p>
{% endif %}
<p>
	Nothing you have already submitted has been lost. Add what has been asked for
	and submit the application again, and it will return to the same reviewers at
	{{ geo_path or "your branch" }}.
</p>
{% if portal_url %}
<p><a href="{{ portal_url }}">Open your application</a></p>
{% endif %}"""
		),
		"description": (
			"Sent when an approver asks for more information, which returns the application to the"
			" applicant. Context: holder_name, kind, record_id, reason, geo_path, portal_url,"
			" society_name."
		),
	},
)


# --- what this app has shipped before ---------------------------------------

# **Every body these templates have ever been seeded with, keyed by template.**
#
# The rule is that a seeded message is never edited afterwards, so a society's
# rewrite survives every deploy. That rule is right, and it has one cost: an
# improvement to the shipped wording could never reach a site that had already
# migrated once, so the first site ever installed keeps the first draft forever.
#
# This is how both hold at once. `lifecycle.install` upgrades a record **only**
# when its current body is byte-identical to something in this tuple — that is,
# only when what is on the site is wording this app wrote and nobody has since
# touched. Anything else, including a single edited word, is a society's own
# message and is left exactly as it is.
#
# **Append, never rewrite.** Removing an entry does not tidy anything up; it
# strands every site still carrying that revision. When the wording above
# changes, the version being replaced moves down here.
SHIPPED: dict[str, tuple[str, ...]] = {
	RECEIVED: (
		"""<p>Dear {{ holder_name }},</p>
<p>
	Thank you. Your {{ kind }} application has been received and is with
	{{ geo_path or "your branch" }} for review.
</p>
<p>
	Your reference is <strong>{{ record_id }}</strong>. Nobody needs to be chased:
	it is already in the queue of the people responsible for that place.
</p>
{% if portal_url %}
<p><a href="{{ portal_url }}">Follow where it has got to</a>.</p>
{% endif %}
<p style="margin-top:20px">{{ society_name }}</p>
""",
	),
	APPROVED: (
		"""<p>Dear {{ holder_name }},</p>
<p>
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
{% endif %}
<p style="margin-top:20px">{{ society_name }}</p>
""",
	),
	REJECTED: (
		"""<p>Dear {{ holder_name }},</p>
<p>
	Your {{ kind }} application ({{ record_id }}) has not been accepted on this
	occasion.
</p>
{% if reason %}
<p><strong>Why:</strong> {{ reason }}</p>
{% endif %}
<p>
	If anything about that is unclear, your branch is the right place to ask.
</p>
<p style="margin-top:20px">{{ society_name }}</p>
""",
	),
	MORE_INFO: (
		"""<p>Dear {{ holder_name }},</p>
<p>
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
{% endif %}
<p style="margin-top:20px">{{ society_name }}</p>
""",
	),
}
