# Copyright (c) 2024, Kenya Red Cross Society and Contributors
# GNU GPLv3 License. See license.txt

import frappe
from frappe import _

# Allow guests to access this page
no_cache = True
guest_allow = True


def get_context(context):
    """
    Context for OneRC Portal Landing Page

    This landing page is shown to all users before they access VMMS.
    - Guests: See the three-panel landing page (Join, Volunteers/Members, Staff)
    - Logged-in users: See the same page with their username in header
    """

    # Set page metadata
    context.no_header = True
    context.no_breadcrumbs = True
    context.title = "OneRC — Gambia Red Cross Society"

    # Allow guest access
    context.hide_login = False

    return context
