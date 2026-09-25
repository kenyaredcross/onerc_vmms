"""Branch stock, issues and returns. Every staff action uses the asset role's Geo Assignments."""

import frappe
from frappe import _
from frappe.utils import now_datetime
from onerc_core.access.services import enforcement, scope
from onerc_core.geo.services import adapter
from onerc_core.society.services import config

from vmmsx.notifications.services import direct
from vmmsx.setup.core_roles import ROLE_ASSET_MANAGER

ASSET = "VMMS Branch Asset"
TRANSACTION = "VMMS Asset Transaction"
PICKER_LIMIT = 20
LIST_LIMIT = 50
ASSET_PORTAL = "/portal/assets"


def _role() -> str:
	return config.settings().get("vmms_asset_scope_role") or ROLE_ASSET_MANAGER


def _manager(node: str) -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Sign in to manage assets."), frappe.PermissionError)
	if not scope.has_unrestricted_scope() and _role() not in frappe.get_roles():
		frappe.throw(_("The asset manager role is required."), frappe.PermissionError)
	if not enforcement.is_in_scope(ASSET, node):
		frappe.throw(_("This branch is outside your asset scope."), frappe.PermissionError)


def _positive(value) -> int:
	try:
		quantity = int(value)
	except TypeError, ValueError:
		quantity = 0
	if quantity <= 0 or str(value).strip() != str(quantity):
		frappe.throw(_("Quantity must be a positive whole number."))
	return quantity


def _asset(name: str):
	doc = frappe.get_doc(ASSET, name)
	_manager(doc.geo_node)
	return doc


def _branch_nodes(geo_node: str) -> set[str]:
	"""Include the asset's node and the smaller areas it serves."""
	return {geo_node, *adapter.get_descendants(geo_node)}


def _row(doc) -> dict:
	return {
		key: doc.get(key)
		for key in (
			"name",
			"asset_name",
			"category",
			"unit",
			"geo_node",
			"description",
			"total_quantity",
			"available_quantity",
			"is_active",
		)
	}


@frappe.whitelist()
def branches() -> list[dict]:
	"""Only nodes covered by this person's asset assignment."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Sign in to manage assets."), frappe.PermissionError)
	if not scope.has_unrestricted_scope() and _role() not in frappe.get_roles():
		return []
	nodes = scope.get_user_geo_scope(frappe.session.user, _role())
	return (
		frappe.get_all(
			"Geo Node", filters={"name": ("in", list(nodes))}, fields=["name"], order_by="name asc"
		)
		if nodes
		else []
	)


@frappe.whitelist()
def stock(geo_node: str | None = None, search: str | None = None) -> dict:
	if geo_node:
		_manager(geo_node)
	elif not scope.has_unrestricted_scope() and _role() not in frappe.get_roles():
		frappe.throw(_("The asset manager role is required."), frappe.PermissionError)
	filters = {"geo_node": geo_node} if geo_node else {}
	if search and search.strip():
		filters["asset_name"] = ("like", f"%{search.strip()[:100]}%")
	rows = frappe.get_list(
		ASSET,
		filters=filters,
		fields=[
			"name",
			"asset_name",
			"category",
			"unit",
			"geo_node",
			"description",
			"total_quantity",
			"available_quantity",
			"is_active",
		],
		order_by="asset_name asc",
		limit=LIST_LIMIT + 1,
	)
	return {"assets": rows[:LIST_LIMIT], "has_more": len(rows) > LIST_LIMIT}


@frappe.whitelist()
def search_assets(geo_node: str, search: str | None = None) -> list[dict]:
	"""Small, scoped result set for the issue and receipt picker."""
	_manager(geo_node)
	term = (search or "").strip()[:100]
	if len(term) < 2:
		return []
	return frappe.db.sql(
		"""
		SELECT name, asset_name, category, unit, geo_node, total_quantity,
			available_quantity, is_active
		FROM `tabVMMS Branch Asset`
		WHERE geo_node = %s AND (asset_name LIKE %s OR category LIKE %s OR name LIKE %s)
		ORDER BY asset_name ASC, name ASC
		LIMIT %s
		""",
		(geo_node, f"%{term}%", f"%{term}%", f"%{term}%", PICKER_LIMIT),
		as_dict=True,
	)


@frappe.whitelist()
def create_asset(
	asset_name: str,
	geo_node: str,
	category: str | None = None,
	unit: str = "each",
	description: str | None = None,
) -> dict:
	_manager(geo_node)
	if not asset_name or not asset_name.strip():
		frappe.throw(_("Enter an asset name."))
	doc = frappe.get_doc(
		{
			"doctype": ASSET,
			"asset_name": asset_name.strip(),
			"geo_node": geo_node,
			"category": category,
			"unit": unit or "each",
			"description": description,
			"total_quantity": 0,
			"available_quantity": 0,
		}
	)
	doc.insert(ignore_permissions=True)
	return _row(doc)


def _locked(name: str):
	# A row lock serializes receipts, issues and returns for this stock line.
	frappe.db.sql("SELECT name FROM `tabVMMS Branch Asset` WHERE name = %s FOR UPDATE", name)
	return _asset(name)


def _record(
	asset,
	kind: str,
	quantity: int,
	volunteer: str | None = None,
	issue: str | None = None,
	notes: str | None = None,
) -> dict:
	doc = frappe.get_doc(
		{
			"doctype": TRANSACTION,
			"asset": asset.name,
			"geo_node": asset.geo_node,
			"transaction_type": kind,
			"quantity": quantity,
			"volunteer": volunteer,
			"issue": issue,
			"notes": notes,
			"occurred_at": now_datetime(),
			"recorded_by": frappe.session.user,
		}
	)
	doc.flags.asset_service = True
	doc.insert(ignore_permissions=True)
	return {
		"name": doc.name,
		"asset": asset.name,
		"transaction_type": kind,
		"quantity": quantity,
		"volunteer": volunteer,
		"issue": issue,
		"occurred_at": doc.occurred_at,
	}


@frappe.whitelist()
def receive(asset: str, quantity: int, notes: str | None = None) -> dict:
	item = _locked(asset)
	q = _positive(quantity)
	entry = _record(item, "Receipt", q, notes=notes)
	frappe.db.set_value(
		ASSET,
		item.name,
		{"total_quantity": item.total_quantity + q, "available_quantity": item.available_quantity + q},
	)
	return entry


@frappe.whitelist()
def issue(asset: str, volunteer: str, quantity: int, notes: str | None = None) -> dict:
	item = _locked(asset)
	q = _positive(quantity)
	if not item.is_active or q > item.available_quantity:
		frappe.throw(_("There is not enough available stock."))
	person = frappe.db.get_value(
		"VMMS Volunteer", volunteer, ["name", "status", "home_geo_node"], as_dict=True
	)
	if not person or person.status != "Active":
		frappe.throw(_("Choose an active volunteer."))
	if person.home_geo_node not in _branch_nodes(item.geo_node):
		frappe.throw(_("The volunteer is outside this asset's branch."), frappe.PermissionError)
	entry = _record(item, "Issue", q, volunteer=volunteer, notes=notes)
	frappe.db.set_value(ASSET, item.name, "available_quantity", item.available_quantity - q)
	entry["notification_queued"] = _tell_holder(
		volunteer,
		entry["name"],
		_("Your branch issued you {0} {1}. View it in My equipment.").format(q, item.asset_name),
	)
	return entry


def _tell_holder(volunteer: str, issue_name: str, subject: str) -> bool:
	login = direct.login_of(volunteer)
	return bool(
		direct.tell(
			[login] if login else [], subject, TRANSACTION, issue_name, about=volunteer, link=ASSET_PORTAL
		)
	)


def _return(issue_name: str, quantity: int, notes: str | None = None, own: bool = False) -> dict:
	issued = frappe.get_doc(TRANSACTION, issue_name)
	if issued.transaction_type != "Issue":
		frappe.throw(_("Choose an issue to return."))
	if own:
		profile = frappe.db.get_value("Red Profile", {"user": frappe.session.user}, "name")
		if not profile or frappe.db.get_value("VMMS Volunteer", issued.volunteer, "red_profile") != profile:
			frappe.throw(_("This issue is not yours."), frappe.PermissionError)
	else:
		_manager(issued.geo_node)
	item = _locked(issued.asset) if not own else _lock_for_owner(issued.asset)
	q = _positive(quantity)
	returned = frappe.db.sql(
		"SELECT COALESCE(SUM(quantity), 0) FROM `tabVMMS Asset Transaction` WHERE issue = %s AND transaction_type = 'Return'",
		issue_name,
	)[0][0]
	if q > issued.quantity - returned:
		frappe.throw(_("Return quantity exceeds the outstanding issue."))
	entry = _record(item, "Return", q, volunteer=issued.volunteer, issue=issued.name, notes=notes)
	frappe.db.set_value(ASSET, item.name, "available_quantity", item.available_quantity + q)
	return entry


def _lock_for_owner(name: str):
	frappe.db.sql("SELECT name FROM `tabVMMS Branch Asset` WHERE name = %s FOR UPDATE", name)
	return frappe.get_doc(ASSET, name)


@frappe.whitelist()
def return_asset(issue: str, quantity: int, notes: str | None = None) -> dict:
	return _return(issue, quantity, notes)


@frappe.whitelist()
def remind(issue: str) -> dict:
	"""Send an in-app reminder for an outstanding issue within the manager's scope."""
	issued = frappe.get_doc(TRANSACTION, issue)
	if issued.transaction_type != "Issue":
		frappe.throw(_("Choose an issue to remind."))
	_manager(issued.geo_node)
	_locked(issued.asset)
	issued.reload()
	returned = frappe.db.sql(
		"SELECT COALESCE(SUM(quantity), 0) FROM `tabVMMS Asset Transaction` WHERE issue = %s AND transaction_type = 'Return'",
		issue,
	)[0][0]
	remaining = issued.quantity - returned
	if remaining <= 0:
		frappe.throw(_("This equipment has already been returned."))
	asset_name = frappe.db.get_value(ASSET, issued.asset, "asset_name")
	queued = _tell_holder(
		issued.volunteer,
		issued.name,
		_("Reminder: you still have {0} {1} from your branch. View it in My equipment.").format(
			remaining, asset_name
		),
	)
	if queued:
		frappe.db.set_value(
			TRANSACTION,
			issued.name,
			{
				"last_reminded_at": now_datetime(),
				"reminder_count": (issued.reminder_count or 0) + 1,
			},
			update_modified=False,
		)
	return {"notification_queued": queued, "outstanding": remaining}


@frappe.whitelist()
def my_assets() -> list[dict]:
	profile = frappe.db.get_value("Red Profile", {"user": frappe.session.user}, "name")
	volunteer = frappe.db.get_value("VMMS Volunteer", {"red_profile": profile}, "name") if profile else None
	if not volunteer:
		return []
	return _issues({"volunteer": volunteer})


@frappe.whitelist()
def return_my_asset(issue: str, quantity: int, notes: str | None = None) -> dict:
	if frappe.session.user == "Guest":
		frappe.throw(_("Sign in to return an asset."), frappe.PermissionError)
	return _return(issue, quantity, notes, own=True)


def _issues(filters: dict) -> list[dict]:
	rows = frappe.get_all(
		TRANSACTION,
		filters={**filters, "transaction_type": "Issue"},
		fields=[
			"name",
			"asset",
			"geo_node",
			"volunteer",
			"quantity",
			"occurred_at",
			"last_reminded_at",
			"reminder_count",
		],
		order_by="occurred_at desc",
		limit=500,
	)
	for row in rows:
		row["returned"] = frappe.db.sql(
			"SELECT COALESCE(SUM(quantity), 0) FROM `tabVMMS Asset Transaction` WHERE issue = %s AND transaction_type = 'Return'",
			row.name,
		)[0][0]
		row["outstanding"] = row.quantity - row.returned
		row["asset_name"] = frappe.db.get_value(ASSET, row.asset, "asset_name")
	for row in rows:
		profile = frappe.db.get_value("VMMS Volunteer", row.volunteer, "red_profile")
		row["volunteer_name"] = (
			frappe.db.get_value("Red Profile", profile, "full_name") if profile else row.volunteer
		)
	return [row for row in rows if row["outstanding"] > 0]


@frappe.whitelist()
def outstanding(geo_node: str | None = None, search: str | None = None) -> list[dict]:
	if geo_node:
		_manager(geo_node)
	elif not scope.has_unrestricted_scope() and _role() not in frappe.get_roles():
		frappe.throw(_("The asset manager role is required."), frappe.PermissionError)
	term = (search or "").strip()[:100]
	if term and len(term) < 2:
		return []
	nodes = (
		[geo_node]
		if geo_node
		else (
			[]
			if scope.has_unrestricted_scope()
			else sorted(scope.get_user_geo_scope(frappe.session.user, _role()))
		)
	)
	if not nodes and not scope.has_unrestricted_scope():
		return []
	where = []
	values: list = []
	if nodes:
		where.append(f"issued.geo_node IN ({', '.join(['%s'] * len(nodes))})")
		values.extend(nodes)
	if term:
		where.append("(asset.asset_name LIKE %s OR profile.full_name LIKE %s OR issued.volunteer LIKE %s)")
		values.extend([f"%{term}%"] * 3)
	values.append(LIST_LIMIT)
	return frappe.db.sql(
		f"""
		SELECT issued.name, issued.asset, issued.geo_node, issued.volunteer,
			issued.quantity, issued.occurred_at, issued.last_reminded_at,
			issued.reminder_count, asset.asset_name,
			COALESCE(profile.full_name, issued.volunteer) AS volunteer_name,
			COALESCE(returned.quantity, 0) AS returned,
			issued.quantity - COALESCE(returned.quantity, 0) AS outstanding
		FROM `tabVMMS Asset Transaction` issued
		INNER JOIN `tabVMMS Branch Asset` asset ON asset.name = issued.asset
		LEFT JOIN `tabVMMS Volunteer` volunteer ON volunteer.name = issued.volunteer
		LEFT JOIN `tabRed Profile` profile ON profile.name = volunteer.red_profile
		LEFT JOIN (
			SELECT issue, SUM(quantity) AS quantity
			FROM `tabVMMS Asset Transaction`
			WHERE transaction_type = 'Return'
			GROUP BY issue
		) returned ON returned.issue = issued.name
		WHERE issued.transaction_type = 'Issue'
			AND issued.quantity > COALESCE(returned.quantity, 0)
			{("AND " + " AND ".join(where)) if where else ""}
		ORDER BY issued.occurred_at DESC, issued.name DESC
		LIMIT %s
		""",
		values,
		as_dict=True,
	)


@frappe.whitelist()
def search_volunteers(geo_node: str, search: str | None = None) -> list[dict]:
	"""Search names, email or volunteer ID inside this asset branch only."""
	_manager(geo_node)
	term = (search or "").strip()[:100]
	if len(term) < 2:
		return []
	nodes = _branch_nodes(geo_node) & scope.get_user_geo_scope(frappe.session.user, _role())
	if not nodes:
		return []
	placeholders = ", ".join(["%s"] * len(nodes))
	pattern = f"%{term}%"
	return frappe.db.sql(
		f"""
		SELECT volunteer.name, profile.full_name, volunteer.home_geo_node
		FROM `tabVMMS Volunteer` volunteer
		INNER JOIN `tabRed Profile` profile ON profile.name = volunteer.red_profile
		WHERE volunteer.status = 'Active'
			AND volunteer.home_geo_node IN ({placeholders})
			AND (profile.full_name LIKE %s OR profile.email LIKE %s OR volunteer.name LIKE %s)
		ORDER BY profile.full_name ASC, volunteer.name ASC
		LIMIT %s
		""",
		[*sorted(nodes), pattern, pattern, pattern, PICKER_LIMIT],
		as_dict=True,
	)
