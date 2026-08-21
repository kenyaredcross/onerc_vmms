# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Where a record is, in words — and what to say when the place is gone.

One function, and it exists for one failure that has actually happened on a
site: a project or a deployment whose Geo Node was deleted underneath it.
`adapter.get_full_path` throws `DoesNotExistError` for a node that is not there,
and a dto that calls it unguarded turns one orphaned row into a register that
will not open at all — every project on the page replaced by
"Geo Node GEO-00004 does not exist".

**A cascade should prevent it and does not always.** Frappe refuses to delete a
document another one links to, but `frappe.delete_doc(force=True)` skips that
check, and both `seed/purge.py` and a partially restored backup can leave a row
pointing at a node the tree no longer has.

**So the answer is the docname, never an exception and never silence.** The
node's own name is the most honest thing left to show: it says the record is
anchored somewhere and that this site cannot resolve where, which is a sentence
a coordinator can act on. `api/deployment.py::deployment_map` makes the other
choice for the same fact — it drops the row, because a point it cannot place has
nothing to draw — and the two are not in conflict: a list can show a broken
anchor, a map cannot draw one.

**Asked by catching the refusal rather than by looking for the row**, which is
worth saying because the shorter version is `frappe.db.exists("Geo Node", …)`
and this module may not write that. Nothing in the Deployment module names a geo
doctype or reads a geo table; geo is core's, reached only through its adapter,
and `deployment/tests/test_delegation.py` fails the build over a single literal.
The adapter's own answer to "is this node there" is the exception it raises, so
that is what is caught.
"""

import frappe


def geo_path(node: str | None) -> str | None:
	"""The readable path for a node — its docname if the node is gone, None if unset.

	`None` in, `None` out: a record with no anchor is a different thing from one
	whose anchor was deleted, and only the second is a fault.
	"""
	if not node:
		return None

	from onerc_core.geo.services import adapter

	try:
		return adapter.get_full_path(node)
	except frappe.DoesNotExistError:
		# The throw that got us here queued a message, and a queued message is
		# rendered to whoever made the request. Dropped, because this is not a
		# failure being reported — it is a fact being described, and it goes into
		# the row itself where the reader can see which record carries it.
		frappe.clear_last_message()

		return node
