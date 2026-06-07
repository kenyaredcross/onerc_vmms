import frappe
from frappe.utils import today, add_years


@frappe.whitelist(allow_guest=True)
def get_membership_plans():
	plans = frappe.get_all(
		"OneRC Membership Plan",
		filters={"is_active": 1},
		fields=["name", "plan_name", "description", "annual_fee", "currency",
				"requires_age_requirement", "min_age", "max_age"]
	)
	for plan in plans:
		plan["benefits"] = frappe.get_all(
			"Membership Plan Benefit",
			filters={"parent": plan["name"]},
			fields=["benefit", "description"]
		)
	return plans


@frappe.whitelist()
def get_my_membership():
	user = frappe.session.user
	member = frappe.db.get_value(
		"OneRC Member", {"user_account": user}, "name"
	)
	if not member:
		return None

	member_doc = frappe.get_doc("OneRC Member", member)
	subscription = frappe.db.get_value(
		"OneRC Member Subscription",
		{"member": member, "status": ["in", ["Active", "Pending Payment", "Expired"]]},
		["name", "status", "plan", "from_date", "to_date",
		 "payment_confirmed", "qr_code"],
		as_dict=True,
		order_by="to_date desc"
	)

	return {
		"member": member,
		"full_name": member_doc.full_name,
		"photo": member_doc.photo,
		"membership_status": member_doc.membership_status,
		"subscription": subscription,
	}


@frappe.whitelist()
def apply_for_membership(plan, payment_method, payment_reference):
	user = frappe.session.user

	member = frappe.db.get_value(
		"OneRC Member", {"user_account": user}, "name"
	)
	if not member:
		frappe.throw("No member profile found. Please contact support.")

	existing = frappe.db.exists(
		"OneRC Member Subscription",
		{"member": member, "status": ["in", ["Active", "Pending Payment"]]}
	)
	if existing:
		frappe.throw("You already have an active or pending membership subscription.")

	plan_doc = frappe.get_doc("OneRC Membership Plan", plan)

	sub = frappe.get_doc({
		"doctype": "OneRC Member Subscription",
		"member": member,
		"plan": plan,
		"status": "Pending Payment",
		"amount": plan_doc.annual_fee,
		"currency": plan_doc.currency,
		"payment_method": payment_method,
		"payment_reference": payment_reference,
		"from_date": today(),
		"to_date": add_years(today(), 1),
	})
	sub.insert(ignore_permissions=True)
	frappe.db.commit()

	return {"name": sub.name, "status": sub.status}


@frappe.whitelist(allow_guest=True)
def verify_member(vol_id):
	volunteer = frappe.db.get_value(
		"Volunteer", vol_id,
		["full_name", "photo", "volunteer_status"],
		as_dict=True
	)
	if not volunteer:
		return {"status": "not_found"}

	member = frappe.db.get_value(
		"OneRC Member", {"volunteer": vol_id},
		["name", "full_name", "photo"],
		as_dict=True
	)
	if not member:
		return {"status": "not_a_member", "name": volunteer.full_name}

	subscription = frappe.db.get_value(
		"OneRC Member Subscription",
		{"member": member.name, "status": ["in", ["Active", "Expired"]]},
		["name", "plan", "status", "from_date", "to_date"],
		as_dict=True,
		order_by="to_date desc"
	)
	if not subscription:
		return {"status": "no_subscription", "name": volunteer.full_name}

	return {
		"status": subscription.status,
		"name": member.full_name,
		"photo": member.photo or volunteer.photo,
		"plan": subscription.plan,
		"from_date": str(subscription.from_date),
		"to_date": str(subscription.to_date),
		"vol_id": vol_id,
	}
