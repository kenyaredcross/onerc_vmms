# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The first message anybody gets from this site, as a record they can edit.

**Data, not behaviour**, exactly like `content/seeds/default_content.py`: this
declares what the welcome email says before a society has rewritten it, and
`notifications/services/welcome.py` puts it on the site as an `Email Template`
that is never overwritten afterwards.

**Why a record rather than a template file.** The obvious implementation is to
override `frappe/templates/emails/new_user.html`, the way this app already
overrides `standard.html`, and it was the first one written. It fails on the
subject line, which is the most visible part of the message. Frappe takes that
from the `welcome_email` hook and calls `frappe.get_hooks(...)[-1]` — the *last*
app to declare it — and hook order is installation order, which no app controls.
On a bench with ERPNext installed after vmmsx, the society's welcome email
arrives titled "Welcome to ERPNext". There is no ordering vmmsx can ask for and
no second hook to win with.

`System Settings.welcome_email_template` has no such contest: it names one
record, and when it is set Frappe uses that record's subject *and* body and asks
no hook at all. So the message lives here.

It is also the better home on this app's own terms. `notifications/services/
branding.py` says a society writes its own message text on the desk, in Frappe's
`Notification` and `Email Template` doctypes, and that vmmsx holds no second
copy — which is precisely what this is: the society's own record, seeded with
something sensible, editable without a deploy.

**What stays in code is the frame.** `templates/emails/standard.html` still puts
the society's lockup above every message the site sends, this one included, so
nothing below draws a logo or repeats a name in a masthead.

Two things the body relies on:

* `lockup()` — registered by the `jinja` hook in `hooks.py`, so it resolves
  inside an Email Template's Jinja like any other global. Guarded with
  `is defined` for the reason `standard.html` guards it: Frappe returns no jinja
  hooks when there is no site on `frappe.local`, and every sentence here has a
  version that reads correctly for a society that has not been named yet.
* the arguments Frappe passes to a welcome email, and only these:
  `first_name`, `user`, `link`, `site_url`, `created_by`.
"""

#: The docname of the seeded template. Opaque and prefixed, so a society's own
#: templates cannot collide with it and it is obvious where it came from.
TEMPLATE_NAME = "VMMS Welcome"

SUBJECT = "{% if lockup is defined and lockup().brand_name %}Welcome to {{ lockup().brand_name }}{% else %}Welcome — set your password{% endif %}"

BODY = """{%- set society = lockup().brand_name if lockup is defined else "" -%}
<h1 class="email-header-title">
{%- if society %}Welcome to {{ society }}{% else %}Welcome{% endif -%}
</h1>

<p>Hello {{ first_name }},</p>

<p>
{%- if society %}
	An account has been created for you with {{ society }}.
{%- else %}
	An account has been created for you.
{%- endif %}
	You will sign in with <b>{{ user }}</b>.
</p>

<p>There is one thing left to do: choose a password.</p>

<p>
	<a href="{{ link }}" rel="nofollow" class="btn btn-primary"
		style="display:inline-block;margin:8px 0;padding:11px 22px;border-radius:6px;background-color:#F5333F;color:#ffffff;font-size:14px;font-weight:700;line-height:20px;text-decoration:none;">
		Set your password
	</a>
</p>

<p class="text-muted text-small">
	Or copy and paste this link: <a href="{{ link }}">{{ link }}</a>
</p>

<p class="text-muted text-small">
	If you were not expecting this, you can ignore this email. The account cannot be used
	until this link is opened.
</p>
{%- if created_by != "Administrator" %}
<p>Thanks,<br>{{ created_by }}</p>
{%- endif %}
"""
