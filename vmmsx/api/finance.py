# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What the society took in and what it paid out.

One method, and it reads. There is deliberately no write here: this app holds no
record of money — see `finance/services/ledger.py` for what that costs and why
the screen says so — and an endpoint that let somebody file a figure would be
inventing an accounting system inside a volunteer register.

**No scope argument, like every listing in this app.** Both reads inside go
through `frappe.get_list`, so the caller's Geo Assignment bounds every figure
and there is no parameter here that could widen it. A coordinator over one
branch is shown that branch's position; nobody is shown a national total by
naming one.
"""

import frappe

from vmmsx.finance.services import ledger


@frappe.whitelist()
def summary(from_date: str | None = None, to_date: str | None = None) -> dict:
	"""Income, expenditure and the shape of the year, over one window.

	The window is the only argument, and it is a convenience: leave it out and
	the answer is the last twelve months, which is what the screen opens on.
	"""
	return ledger.summary(from_date=from_date, to_date=to_date)
