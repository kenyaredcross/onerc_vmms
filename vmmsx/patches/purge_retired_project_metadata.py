# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Sweep the metadata `VMMS Project` left behind on sites that migrated first.

`adopt_standard_project` deletes the doctype, and deleting a doctype does not
delete the things that named it — a `Property Setter` for its naming series, a
`Custom Field` targeting it. Neither errors and neither is visible unless
somebody goes looking, which is what makes it exactly the sort of leftover a
cleanup phase exists to find.

The sweep now runs at the end of that patch. This is the same sweep under a name
this site's Patch Log has not seen, because **a Frappe patch runs once per site
by name** and the first one has already run everywhere the doctype was retired.
The eleventh-ish instance of a pattern this app has a name for; see
`register_member_modules.py`, which states it first.

Idempotent and quiet: on a site with nothing left over it deletes nothing and
reports nothing.
"""

from vmmsx.patches.adopt_standard_project import purge_metadata


def execute():
	purge_metadata()
