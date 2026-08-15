# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Time Log — volunteered hours, of one structural kind or another.

The controller holds no rules of its own. Everything a log must satisfy lives in
`vmmsx/volunteer/services/timelog.py`, behind one dispatch table keyed by
`log_type`, so that adding a kind is adding an entry there and never adding a
branch here.

Two things are worth knowing before reading further:

- **The geo anchor is required on every kind** (ACC-02), and it is checked
  before the dispatch, so a deployment log with no anchor is refused for the
  anchor rather than for anything about deployments.
- **A deployment log is checked against the deployment's roster.**
  `timelog._deployment()` asks `deployment/services/participation.py` whether
  this volunteer is a participant, and the log is refused if they are not. That
  is ownership, not geo scoping: see `participation.OWNERSHIP_RULE`. The check
  is here, on the server, so it holds for the desk form, the API and a script
  alike, and hiding a deployment from a picker is never the control.
"""

from frappe.model.document import Document

from vmmsx.volunteer.services import timelog


class VMMSTimeLog(Document):
	def validate(self):
		timelog.validate(self)
