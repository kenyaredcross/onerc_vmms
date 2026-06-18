# Copyright (c) 2024, Kenya Red Cross Society and Contributors
# GNU GPLv3 License. See license.txt

import frappe
from frappe import _

# Allow guests to access this page
no_cache = True
guest_allow = True


def get_context(context):
    context.no_header = True
    context.no_breadcrumbs = True
    context.title = "Gambia Red Cross Society — Volunteer & Member Portal"
    context.hide_login = False
    return context
