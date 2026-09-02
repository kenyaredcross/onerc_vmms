# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One text message, when something happened that a person needs to know about.

**Why this is not `onerc_sms`'s campaign builder.** That is a broadcast tool: a
coordinator picks an audience with a query, writes one message and sends it to
everybody in it. What this module sends is the other kind entirely — a single
message to a single person, about their own application, raised by the system
at the moment the thing happened. A campaign of one is not that, and building it
out of one would put a person's decision letter in a marketing register.

**vmmsx does not own sending, and this does not become a second gateway.** Every
message leaves through `onerc_sms.utils.providers.send_via_provider`, which owns
the adapters, the credentials and the sandbox switch. There is no Africa's
Talking here, no Twilio, no API key and no branch on which one is configured —
the same discipline `member/services/payment.py` keeps for money.

**Absent is ordinary.** `onerc_sms` is not in `required_apps` and it never will
be: a society that has not bought SMS credit runs this product perfectly well.
So `is_available()` asks `frappe.get_installed_apps()` rather than trying an
import, and every function here answers "not sent" rather than raising.

**Nothing here may raise, and that is the whole delivery contract.** These
functions are called from inside the save that approved somebody's application.
A gateway that is down, a provider nobody configured, a phone number that is not
a phone number — none of them is a reason for an approval to roll back. The
person being approved is the event; the text message about it is how they hear.

**Email is still the record.** Everything sent from here has already been sent
by email, or will be, by `lifecycle.py`. A text is a nudge to go and read it, not
the letter: it carries what happened and the reference, and it never carries a
reason for a refusal or anything a person would not want read over a shoulder.
"""

import frappe

# The app that owns sending. Named once.
SMS_APP = "onerc_sms"

# What one message may be. Not a technical limit — the gateway will take more
# and charge for the extra parts — but a shape: a notification that does not fit
# in a couple of segments is a letter, and there is one of those in the inbox
# already.
MAX_LENGTH = 300


def is_available() -> bool:
	"""Is the SMS app installed on this site?

	Asked of `frappe.get_installed_apps()`, deliberately, rather than by trying
	the import and catching `ImportError`: an app can sit in the bench and not be
	installed on *this* site, which is the case that actually bites.
	"""
	return SMS_APP in frappe.get_installed_apps()


def tell(phone: str | None, message: str) -> bool:
	"""Send one message. Returns whether it went. Never raises.

	`False` covers every ordinary reason not to send — no SMS app, no provider
	configured, no number on file, nothing to say — and they are deliberately
	indistinguishable to the caller. None of them is an error, and a caller that
	branched on which one would be a caller making a delivery decision that
	belongs here.
	"""
	number = (phone or "").strip()
	body = (message or "").strip()[:MAX_LENGTH]

	if not (number and body and is_available()):
		return False

	try:
		# Imported here, not at module scope: a society without SMS need not
		# install the app, and this is the only line that would break if it were
		# absent.
		from onerc_sms.utils.providers import get_active_provider, send_via_provider

		provider = get_active_provider()
		result = send_via_provider(provider, number, body)

		# The gateway's own word for what happened. `send_via_provider` never
		# raises — it returns a failed result — so this is where a delivery
		# failure is noticed, and it is noticed quietly.
		return str(result.get("status") or "").lower() not in ("failed", "")
	except Exception:
		# Deliberately broad and deliberately swallowed. See the module
		# docstring: the alternative is an approval that rolls back because a
		# gateway blinked.
		frappe.log_error(
			title="vmmsx: could not send a notification by SMS",
			message=frappe.get_traceback(),
		)

		return False
