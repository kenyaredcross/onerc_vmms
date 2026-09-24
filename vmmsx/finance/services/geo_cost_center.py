"""Mirror child Geo Nodes into ERPNext's Cost Center tree.

The parentless National node uses ERPNext's existing Company root. Every child
gets a reporting group and a posting leaf. ERPNext forbids turning a posted
ledger Cost Center into a group later; keeping the two distinct means a node
may receive its first child after membership income has already been posted.
The opaque Geo Node key makes names stable when a society relabels a branch.
"""

import frappe
from frappe import _

from vmmsx.setup.geo_cost_center_fields import GROUP_FIELD, POSTING_FIELD


def _ready() -> bool:
	return "erpnext" in frappe.get_installed_apps() and frappe.get_meta("Geo Node").has_field(POSTING_FIELD)


def _company() -> str:
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		companies = frappe.get_all("Company", filters={"is_group": 0}, limit=2, pluck="name")
		company = companies[0] if len(companies) == 1 else None
	if not company or not frappe.db.exists("Company", company):
		frappe.throw(_("Set the society's ERPNext default Company before adding a Geo Node."))
	if frappe.db.get_value("Company", company, "is_group"):
		frappe.throw(_("The default Company is a group. Choose the Company that owns transactions."))
	return company


def _root(company: str) -> str:
	root = frappe.db.get_value(
		"Cost Center", {"company": company, "cost_center_name": company, "is_group": 1}, "name"
	)
	if not root or frappe.db.get_value("Cost Center", root, "parent_cost_center"):
		frappe.throw(_("The Company needs its root Cost Center before Geo Nodes can be added."))
	return root


def _cost_center(node, field: str, label: str, parent: str, is_group: bool, company: str) -> str:
	name = node.get(field)
	if name and not frappe.db.exists("Cost Center", name):
		frappe.throw(_("Geo Node {0} points to a missing Cost Center {1}.").format(node.name, name))
	if not name and frappe.db.exists("Cost Center", {"company": company, "cost_center_name": label}):
		frappe.throw(
			_("A Cost Center named {0} already exists without a link to Geo Node {1}.").format(
				label, node.name
			)
		)
	if name:
		row = frappe.db.get_value(
			"Cost Center",
			name,
			["company", "is_group", "parent_cost_center", "cost_center_name"],
			as_dict=True,
		)
		if row.company != company or bool(row.is_group) != is_group or row.cost_center_name != label:
			frappe.throw(_("Cost Center {0} does not match Geo Node {1}.").format(name, node.name))
		if row.parent_cost_center != parent:
			cc = frappe.get_doc("Cost Center", name)
			cc.parent_cost_center = parent
			cc.save(ignore_permissions=True)
	else:
		cc = frappe.get_doc(
			{
				"doctype": "Cost Center",
				"cost_center_name": label,
				"company": company,
				"parent_cost_center": parent,
				"is_group": int(is_group),
			}
		).insert(ignore_permissions=True)
		name = cc.name
	if node.get(field) != name:
		node.db_set(field, name, update_modified=False)
		node.set(field, name)
	return name


def sync_node(doc, method=None) -> None:
	"""Run after Geo Node insert/update, in the node's database transaction."""
	if not _ready() or not doc.parent_geo_node:
		return
	company = _company()
	parent = frappe.get_doc("Geo Node", doc.parent_geo_node)
	if parent.parent_geo_node:
		if not parent.get(GROUP_FIELD):
			sync_node(parent)
		parent_cc = parent.get(GROUP_FIELD)
	else:
		parent_cc = _root(company)
	group = _cost_center(doc, GROUP_FIELD, f"VMMS {doc.name} Group", parent_cc, True, company)
	_cost_center(doc, POSTING_FIELD, f"VMMS {doc.name} Own", group, False, company)


def before_delete(doc, method=None) -> None:
	"""Remove empty node Cost Centers; posted accounting blocks node deletion."""
	if not _ready():
		return
	for field in (POSTING_FIELD, GROUP_FIELD):
		name = doc.get(field)
		if not name:
			continue
		if frappe.db.exists("GL Entry", {"cost_center": name}):
			frappe.throw(_("Geo Node {0} has accounting entries and cannot be deleted.").format(doc.name))
		doc.db_set(field, None, update_modified=False)
		doc.set(field, None)
		frappe.delete_doc("Cost Center", name, ignore_permissions=True)


def backfill() -> None:
	"""Create missing mappings for existing child nodes after field installation."""
	if not _ready():
		return
	# A new site's first migration may precede ERPNext Company setup. Creation
	# is strict once a Company exists; later migrations reconcile older nodes.
	if (
		not frappe.db.get_single_value("Global Defaults", "default_company")
		and frappe.db.count("Company", {"is_group": 0}) != 1
	):
		return
	for name in frappe.get_all(
		"Geo Node", filters={"parent_geo_node": ("is", "set")}, order_by="lft asc", pluck="name"
	):
		sync_node(frappe.get_doc("Geo Node", name))
