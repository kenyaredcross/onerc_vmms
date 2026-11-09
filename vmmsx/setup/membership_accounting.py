# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Prepare a society's ERPNext for membership posting. Explicit, never on migrate.

`plan()` says what `configure()` would do and changes nothing. `configure()`
creates only what is missing, so running it twice changes nothing twice:

- a **Membership Fees** income account under the company's income group;
- a **Membership Fee** service item, and a selling price list if the company
  has none (ERPNext names one on every invoice);
- an **M-Pesa** bank account and an **M-Pesa** mode of payment whose default
  account it is; the Cash mode of payment gets the company's cash account if it
  has none;
- the society's payment methods mapped to those modes of payment (an M-Pesa
  gateway to M-Pesa, paying at a branch to Cash), where not already mapped;
- `VMMS Accounting Settings` filled in.

A society that already keeps an M-Pesa or income account names it
(`mpesa_account`, `income_account`) and nothing is created in its place.

It switches posting on only when asked (`enable`). Otherwise that is an
accounting decision, made by ticking "Post membership payments to ERPNext" once
the accounts are right. The Kenya script `configure_membership_accounting.py`
is the usual way to run this.

    bench --site X execute vmmsx.setup.membership_accounting.plan
    bench --site X execute vmmsx.setup.membership_accounting.configure
"""

import frappe
from frappe.utils import today

SETTINGS = "VMMS Accounting Settings"
INCOME_ACCOUNT = "Membership Fees"
MPESA = "M-Pesa"
CASH = "Cash"
ITEM_CODE = "MEMBERSHIP-FEE"


def plan() -> dict:
	company = _company()
	abbr = frappe.get_cached_value("Company", company, "abbr")
	settings = frappe.get_single(SETTINGS)
	return {
		"company": company,
		"income_account": settings.income_account
		or _existing_account(company, INCOME_ACCOUNT)
		or f"(create) {INCOME_ACCOUNT} - {abbr}",
		"mpesa_account": _existing_account(company, MPESA) or f"(create) {MPESA} - {abbr}",
		"item": ITEM_CODE if frappe.db.exists("Item", ITEM_CODE) else f"(create) {ITEM_CODE}",
		"modes_of_payment": {
			MPESA: bool(frappe.db.exists("Mode of Payment", MPESA)),
			CASH: bool(frappe.db.exists("Mode of Payment", CASH)),
		},
		"mpesa_mode_account": frappe.db.get_value(
			"Mode of Payment Account", {"parent": MPESA, "company": company}, "default_account"
		),
		"method_mapping": _mapping(),
		"posting_starts_on": settings.posting_starts_on,
		"posting_enabled": bool(settings.enabled),
		"branches_without_cost_centre": _branches_without_cost_centre(),
		"paid_fees_not_in_the_books": _outstanding_count(),
		"problems": problems(company),
	}


def problems(company: str | None = None) -> list[str]:
	"""What would stop a paid fee from posting, in plain words. Empty when ready.

	The same checks `membership_posting.post` makes one membership at a time,
	asked of the whole site at once, so a setup run can say "ready" or say why not
	before the first member pays.
	"""
	from vmmsx.member.services import methods

	found = []
	company = company or _company()
	settings = frappe.get_single(SETTINGS)

	if settings.company != company:
		found.append(f"VMMS Accounting Settings has company {settings.company or '(none)'}, not {company}.")
	if not settings.income_account:
		found.append("VMMS Accounting Settings has no membership income account.")
	if not settings.fee_item:
		found.append("VMMS Accounting Settings has no membership fee item.")

	currency = frappe.get_cached_value("Company", company, "default_currency")
	if not frappe.db.exists("Price List", {"selling": 1, "enabled": 1, "currency": currency}):
		found.append(f"There is no enabled selling price list in {currency}.")

	rows = [row for row in frappe.get_single(methods.SETTINGS_DOCTYPE).get(methods.METHODS_FIELD) or [] if row.get("is_enabled")]
	if not rows:
		found.append("No payment method is switched on in National Society Settings.")
	for row in rows:
		mode = row.get("mode_of_payment")
		if not mode:
			found.append(f"The payment method {row.gateway} has no ERPNext mode of payment.")
		elif not frappe.db.get_value("Mode of Payment Account", {"parent": mode, "company": company}, "default_account"):
			found.append(f"The mode of payment {mode} has no default account for {company}.")

	missing = _branches_without_cost_centre()
	if missing:
		found.append(f"{missing} branches have no cost centre yet.")

	if not settings.enabled:
		found.append("Posting is switched off (VMMS Accounting Settings > Enabled).")
	return found


def _branches_without_cost_centre() -> int | None:
	from vmmsx.setup.geo_cost_center_fields import POSTING_FIELD

	if not frappe.get_meta("Geo Node").has_field(POSTING_FIELD):
		return None
	return frappe.db.count("Geo Node", {"parent_geo_node": ("is", "set"), POSTING_FIELD: ("is", "not set")})


def _outstanding_count() -> int:
	from vmmsx.finance.services import membership_posting

	return len(membership_posting.outstanding(limit=None))


def configure(
	company: str | None = None,
	mpesa_account: str | None = None,
	income_account: str | None = None,
	starts_on: str | None = None,
	enable: bool = False,
) -> dict:
	"""Create what is missing and fill the settings. Returns `plan()` afterwards.

	`mpesa_account` and `income_account` name accounts the society already has,
	used instead of creating "M-Pesa" and "Membership Fees". `enable` ticks
	"Post membership payments to ERPNext"; left off, posting stays as it was.
	"""
	frappe.only_for(("System Manager", "Accounts Manager"))

	company = company or _company()
	if not frappe.db.exists("Company", company):
		frappe.throw(f"There is no company called {company}.")

	income = (
		_checked(income_account, company, root_type="Income")
		if income_account
		else _existing_account(company, INCOME_ACCOUNT)
		or _make_account(company, INCOME_ACCOUNT, parent=_income_group(company), account_type="Income Account")
	)
	mpesa = (
		_checked(mpesa_account, company, root_type="Asset")
		if mpesa_account
		else _existing_account(company, MPESA)
		or _make_account(company, MPESA, parent=_bank_group(company), account_type="Bank")
	)
	from vmmsx.finance.services import geo_cost_center

	# Branch cost centres are made on migrate, but only once ERPNext has a
	# company; a site whose company came later has none until this runs.
	if not frappe.db.get_single_value("Global Defaults", "default_company"):
		frappe.db.set_single_value("Global Defaults", "default_company", company)
	geo_cost_center.backfill()

	_mode_of_payment(MPESA, "Bank", company, mpesa)
	_mode_of_payment(CASH, "Cash", company, frappe.get_cached_value("Company", company, "default_cash_account"))
	item = _item()
	_selling_price_list(company)
	_map_methods()

	settings = frappe.get_single(SETTINGS)
	settings.company = company
	settings.income_account = income
	if not settings.fee_item:
		settings.fee_item = item
	if starts_on:
		settings.posting_starts_on = starts_on
	elif not settings.posting_starts_on:
		settings.posting_starts_on = today()
	if enable:
		settings.enabled = 1
	settings.save(ignore_permissions=True)

	return plan()


def _checked(account: str, company: str, root_type: str) -> str:
	"""An account the society named, checked to be one this can post to."""
	row = frappe.db.get_value("Account", account, ["company", "root_type", "is_group"], as_dict=True)
	if not row:
		frappe.throw(f"There is no account called {account}.")
	if row.company != company:
		frappe.throw(f"{account} belongs to {row.company}, not {company}.")
	if row.is_group:
		frappe.throw(f"{account} is a group. Name an account that can be posted to.")
	if row.root_type != root_type:
		frappe.throw(f"{account} is an {row.root_type} account; an {root_type} account is needed here.")
	return account


# --- pieces -----------------------------------------------------------------


def _company() -> str:
	company = frappe.db.get_single_value(SETTINGS, "company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)
	if not company:
		frappe.throw("Set the default Company in ERPNext first.")
	return company


def _existing_account(company: str, account_name: str) -> str | None:
	return frappe.db.get_value("Account", {"company": company, "account_name": account_name, "is_group": 0}, "name")


def _income_group(company: str) -> str:
	return frappe.db.get_value(
		"Account", {"company": company, "account_name": "Direct Income", "is_group": 1}, "name"
	) or frappe.db.get_value(
		"Account", {"company": company, "root_type": "Income", "is_group": 1}, "name", order_by="lft asc"
	)


def _bank_group(company: str) -> str:
	return frappe.db.get_value(
		"Account", {"company": company, "account_type": "Bank", "is_group": 1}, "name"
	) or frappe.db.get_value(
		"Account", {"company": company, "account_name": "Bank Accounts", "is_group": 1}, "name"
	) or frappe.db.get_value(
		"Account", {"company": company, "account_name": "Current Assets", "is_group": 1}, "name"
	)


def _make_account(company: str, account_name: str, parent: str, account_type: str) -> str:
	account = frappe.get_doc(
		{
			"doctype": "Account",
			"company": company,
			"account_name": account_name,
			"parent_account": parent,
			"account_type": account_type,
			"is_group": 0,
		}
	)
	account.flags.ignore_permissions = True
	account.insert()
	return account.name


def _mode_of_payment(name: str, kind: str, company: str, account: str | None) -> None:
	if frappe.db.exists("Mode of Payment", name):
		mode = frappe.get_doc("Mode of Payment", name)
	else:
		mode = frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": name, "type": kind, "enabled": 1})

	if account and not any(row.company == company for row in mode.get("accounts") or []):
		mode.append("accounts", {"company": company, "default_account": account})

	mode.flags.ignore_permissions = True
	mode.save()


def _item() -> str:
	if frappe.db.exists("Item", ITEM_CODE):
		return ITEM_CODE
	group = "Services" if frappe.db.exists("Item Group", "Services") else frappe.db.get_value(
		"Item Group", {"is_group": 0}, "name"
	)
	uom = "Nos" if frappe.db.exists("UOM", "Nos") else frappe.db.get_value("UOM", {}, "name")
	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": ITEM_CODE,
			"item_name": "Membership Fee",
			"item_group": group,
			"stock_uom": uom,
			"is_stock_item": 0,
			"is_sales_item": 1,
			"is_purchase_item": 0,
			"include_item_in_manufacturing": 0,
			"description": "A Red Cross membership fee.",
		}
	)
	item.flags.ignore_permissions = True
	item.insert()
	return item.name


def _selling_price_list(company: str) -> str:
	"""ERPNext names a price list on every selling document; make sure one exists."""
	currency = frappe.get_cached_value("Company", company, "default_currency")
	existing = frappe.db.get_value("Price List", {"selling": 1, "enabled": 1, "currency": currency}, "name")
	if existing:
		return existing
	price_list = frappe.get_doc(
		{"doctype": "Price List", "price_list_name": "Standard Selling", "selling": 1, "enabled": 1, "currency": currency}
	)
	if frappe.db.exists("Price List", "Standard Selling"):
		price_list.price_list_name = f"Standard Selling {currency}"
	price_list.flags.ignore_permissions = True
	price_list.insert()
	return price_list.name


def _mapping() -> dict:
	from vmmsx.member.services import methods

	rows = frappe.get_single(methods.SETTINGS_DOCTYPE).get(methods.METHODS_FIELD) or []
	return {row.gateway: row.get("mode_of_payment") for row in rows}


def _map_methods() -> None:
	from vmmsx.member.services import methods

	settings = frappe.get_single(methods.SETTINGS_DOCTYPE)
	changed = False
	for row in settings.get(methods.METHODS_FIELD) or []:
		if row.get("mode_of_payment"):
			continue
		target = CASH if row.gateway == methods.MANUAL else MPESA if _is_mpesa(row.gateway) else None
		if target:
			row.mode_of_payment = target
			changed = True
	if changed:
		settings.flags.ignore_permissions = True
		settings.save()


def _is_mpesa(gateway: str | None) -> bool:
	if not gateway:
		return False
	driver = frappe.db.get_value("OneRC Payment Gateway", gateway, "driver_class") or ""
	return "mpesa" in f"{gateway} {driver}".lower().replace("-", "")
