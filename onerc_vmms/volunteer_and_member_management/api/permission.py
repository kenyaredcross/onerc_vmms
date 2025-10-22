import frappe


def check_app_permission():
    """Check if the user has permission to access the app."""
    if frappe.session.user == "Administrator":
        return True

    roles = frappe.get_roles()
    vmms_roles = ["Volunteer", "Non Profit Member"]
    if any(role in roles for role in vmms_roles):
        return True

    return False
