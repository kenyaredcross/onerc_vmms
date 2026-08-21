# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Move every roster row onto its own VMMS Deployment Assignment.

The roster used to be `VMMS Deployment.participants`, a child table. It is now a
register of documents, because each person's deployment needed things a child
row cannot carry — a URL a volunteer can open, a reference a notification can
point at, a lifecycle with a grammar, and a record of which submitted terms of
reference they agreed to. `deployment/services/assignment.py` makes the case in
full.

**Without this patch every existing deployment appears to have nobody on it**,
and worse, `participation.is_participant` starts returning False for people who
demonstrably served — which would refuse their time logs. The child rows are
still in the database; nothing reads them any more.

How each row is translated
--------------------------

    response blank     ->  Assigned   a coordinator placed them, no question asked
    response invited   ->  Pending    asked, never answered
    response accepted  ->  Accepted
    response declined  ->  Declined

That mapping is exact: the old model's blank-versus-`invited` distinction is the
same distinction `Assigned` and `Pending` draw, which is why it survives the
move without anybody having to guess.

**Inserted with the rules turned off, deliberately.** `db_insert` rather than
`frappe.get_doc(...).insert()`, for three reasons that all point the same way:

* The headcount cap did not exist when these rosters were built. A deployment
  that recorded eight people against a six-person need is a fact about what
  happened, and a patch that refused to carry two of them across would be
  destroying history to satisfy a rule invented afterwards.
* `assert_terms_offered` refuses terms that have been retired. Deployments run
  under terms a society has since withdrawn are ordinary, and their rosters are
  not less real for it.
* `after_insert` sends a notification. Migrating a two-year-old roster must not
  post an invitation to everybody who was ever on a deployment.

**Idempotent.** A deployment that already has assignments is skipped whole, so
re-running the patch on a site where it half-ran cannot double the roster.
"""

import frappe
from frappe.utils import now

DEPLOYMENT_DOCTYPE = "VMMS Deployment"
PARTICIPANT_DOCTYPE = "VMMS Deployment Participant"
ASSIGNMENT_DOCTYPE = "VMMS Deployment Assignment"

# The old nullable `response` field, mapped onto the new status vocabulary.
# Blank is not "unknown": it meant a coordinator placed somebody without asking,
# which is exactly what Assigned means.
STATUS_OF_RESPONSE = {
	None: "Assigned",
	"": "Assigned",
	"invited": "Pending",
	"accepted": "Accepted",
	"declined": "Declined",
}


def execute():
	if not frappe.db.table_exists(PARTICIPANT_DOCTYPE):
		return

	rows = frappe.db.sql(
		"""
		select parent, volunteer, response, invited_on, responded_on, response_note,
		       joined_on, left_on, participation_notes, idx
		  from `tabVMMS Deployment Participant`
		 where parenttype = %s and parentfield = 'participants'
		 order by parent, idx
		""",
		(DEPLOYMENT_DOCTYPE,),
		as_dict=True,
	)

	if not rows:
		return

	deployments = _deployments(sorted({row.parent for row in rows}))
	already = set(
		frappe.get_all(ASSIGNMENT_DOCTYPE, distinct=True, pluck="deployment", ignore_permissions=True)
	)

	moved = 0

	for row in rows:
		deployment = deployments.get(row.parent)

		# The roster row outlived its deployment, or the deployment already has a
		# register of its own. Either way there is nothing to do and nothing to
		# report: a partially restored backup should not stop a patch.
		if not deployment or row.parent in already or not row.volunteer:
			continue

		# Terms are required on an assignment, because it records what the person
		# agreed to. A deployment with none is malformed and predates the link
		# being mandatory; skipping is better than inventing an answer.
		if not deployment.terms_of_reference:
			continue

		_insert(row, deployment)
		moved += 1

	if moved:
		frappe.db.commit()


def _deployments(names: list[str]) -> dict:
	"""The facts each assignment copies off its deployment, in one read."""
	return {
		row["name"]: frappe._dict(row)
		for row in frappe.get_all(
			DEPLOYMENT_DOCTYPE,
			filters={"name": ("in", names)},
			fields=["name", "terms_of_reference", "geo_node", "start_date", "end_date", "owner"],
			ignore_permissions=True,
		)
	}


def _insert(row, deployment) -> None:
	"""One assignment, written straight to the table.

	`get_doc(...).db_insert()` rather than `insert()`: the document is built so
	that its fields are named and defaulted the way the doctype says, but none of
	the controller's `validate` or `after_insert` runs. See the module docstring
	for why each of those has to stay out of a migration.
	"""
	doc = frappe.get_doc(
		{
			"doctype": ASSIGNMENT_DOCTYPE,
			"deployment": deployment.name,
			"volunteer": row.volunteer,
			"terms_of_reference": deployment.terms_of_reference,
			"geo_node": deployment.geo_node,
			"status": STATUS_OF_RESPONSE.get(row.response, "Assigned"),
			"role": "member",
			"start_date": deployment.start_date,
			"end_date": deployment.end_date,
			"invited_on": row.invited_on,
			"responded_on": row.responded_on,
			"response_note": row.response_note,
			"joined_on": row.joined_on,
			"left_on": row.left_on,
			"participation_notes": row.participation_notes,
		}
	)

	doc.name = frappe.model.naming.make_autoname("DPA-.YYYY.-.#####", doctype=ASSIGNMENT_DOCTYPE, doc=doc)
	# The deployment's own filer, not whoever runs the migration: this record is
	# a restatement of something they wrote, and stamping it with an administrator
	# would lose that.
	doc.owner = deployment.owner
	doc.creation = doc.modified = now()
	doc.modified_by = deployment.owner

	doc.db_insert()
