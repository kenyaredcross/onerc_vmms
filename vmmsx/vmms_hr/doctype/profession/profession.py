# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Profession — The society's own list of the trades and callings a volunteer can hold.

An open register, named by whoever creates the row, because what counts as a
profession is a fact about a country's labour market and not something this app
can enumerate. Referenced by the `profession` field on `Job Opening`.
"""

from frappe.model.document import Document


class Profession(Document):
	pass
