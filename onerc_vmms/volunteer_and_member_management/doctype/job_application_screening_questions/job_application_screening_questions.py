# Copyright (c) 2025, Kenya Red Cross Society and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class JobApplicationScreeningQuestions(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		depends_on_question: DF.Data | None
		enable_scoring: DF.Check
		expected_answer: DF.SmallText | None
		help_text: DF.SmallText | None
		is_knock_off: DF.Check
		is_required: DF.Check
		max_score: DF.Float
		options: DF.SmallText | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		question: DF.SmallText
		question_id: DF.Data
		question_type: DF.Literal[
			"Text", "Select", "MultiSelect", "Rating", "Upload", "Date", "Yes/No", "Email", "Phone"
		]
		show_if_answer_is: DF.SmallText | None
		weight: DF.Float
	# end: auto-generated types
	pass
