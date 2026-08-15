# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Shared templating — rendering society-authored documents from configuration.

This package is **domain-agnostic on purpose**. It knows nothing about members,
volunteers, deployments or notifications: a caller looks up a template by its
stable key, hands over a context dict, and gets rendered output back. Membership
certificates are the first consumer; volunteer agreements and notifications are
the next, and neither will need a line changed here.

It sits outside `member/` for exactly that reason. A `render_certificate()`
living under the member module would have to be copied or imported sideways the
first time volunteering wanted one, and the second copy is where the two start
to drift.

Two rules hold:

1. **Template content is configuration, never code.** The body lives on a
   `VMMS Template` record a society can edit. No source file in vmmsx contains
   the text of a certificate — the shipped default is seeded from
   `seeds/`, into a record, where an administrator can change it.
2. **A template is untrusted input.** It is written by society administrators,
   not developers, so it renders through Frappe's sandboxed Jinja and a template
   that reaches for Python internals is refused rather than executed.
"""
