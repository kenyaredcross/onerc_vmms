# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The analytics endpoint. One method, and it takes no scope.

Every guarantee worth stating is in `analytics/services/summary.py`, which this
is a two-line whitelist over: the scope is the session's and cannot be supplied,
each doctype is counted through its own registered role, and a caller holding
nothing gets zeroes rather than a refusal.

**One endpoint rather than six.** The screen draws the tiles, the breakdowns,
the trend and the coverage table together, and six requests would paint it in six
stages, each with its own spinner and its own chance of a partial answer that
reads as a complete one.

**`geo_node` narrows and cannot widen.** It is intersected with what the caller
already holds, so a branch coordinator naming the country still gets their
branch. A node that does not exist counts nothing, which is what a query string
somebody typed deserves.
"""

import frappe

from vmmsx.analytics.services import summary


@frappe.whitelist()
def branch_summary(geo_node: str | None = None, months: int | None = None) -> dict:
	"""Every figure the console's analytics screen draws, for the caller's area."""
	return summary.branch_summary(geo_node=geo_node, months=int(months or summary.MONTHS))
