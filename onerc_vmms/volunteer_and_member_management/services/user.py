import frappe
from frappe import _

VMMS_GUEST_ROLE = "Vmms Guest"

_SELF_PERMISSION_EXEMPT = {"Guest", "Administrator"}


def ensure_user_self_permission(user: str) -> None:
	if not user or user in _SELF_PERMISSION_EXEMPT:
		return

	if frappe.db.exists(
		"User Permission",
		{"user": user, "allow": "User", "for_value": user},
	):
		return

	frappe.get_doc(
		{
			"doctype": "User Permission",
			"user": user,
			"allow": "User",
			"for_value": user,
			"is_default": 1,
			"apply_to_all_doctypes": 1,
		}
	).insert(ignore_permissions=True)


def _ensure_role(role_name: str) -> None:
	if not frappe.db.exists("Role", role_name):
		frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 0}).insert(
			ignore_permissions=True
		)  # nosemgrep


def create_vmms_user(
	email: str,
	first_name: str = "",
	last_name: str = "",
	phone: str = "",
	gender: str = "",
) -> str:
	email = (email or "").strip()
	if not email:
		frappe.throw(_("Email is required"))

	if frappe.db.exists("User", {"email": email}):
		frappe.throw(_("User already exists with this email"))

	first_name = first_name or ""
	last_name = last_name or ""
	_ensure_role(VMMS_GUEST_ROLE)

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first_name,
			"last_name": last_name,
			"full_name": f"{first_name} {last_name}".strip(),
			"phone": phone or "",
			"gender": gender or "",
			"enabled": 1,
			"default_app": "onerc_vmms",
			"roles": [{"role": VMMS_GUEST_ROLE}],
		}
	)
	user.insert(ignore_permissions=True)

	ensure_user_self_permission(user.name)
