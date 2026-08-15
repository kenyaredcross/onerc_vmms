# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The public edge of a card, which is the only part a stranger can reach.

`api/cards.py::verify` is this app's fourth `allow_guest` endpoint, and the
whole of what bounds it is the token. So the things worth testing are the ones
that would quietly widen it:

* **The token is the only key.** A docname must not resolve, or a public lookup
  would let anybody walk the register by counting.
* **A miss says one thing.** "No such card" and "a card that was withdrawn"
  must not be distinguishable, or this becomes somewhere to test guesses.
* **The DTO is small, and stays small.** A field added to a volunteer record
  must not appear here by accident: the contract is that everything returned is
  already printed on the card in the reader's hand.
* **A token, once minted, does not move.** A card in somebody's pocket has it
  printed on it.
"""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.api import cards as cards_api
from vmmsx.cards.services import token
from vmmsx.volunteer.services import card as volunteer_card

EXTRA_TEST_RECORD_DEPENDENCIES = []

VOLUNTEER = "VMMS Volunteer"

# Everything `verify` is allowed to say about somebody. Written out rather than
# derived, so adding a field to the DTO has to be a deliberate edit here too.
PUBLIC_FIELDS = {
	"found",
	"kind",
	"holder_name",
	"record_id",
	"status",
	"is_current",
	"geo_path",
	"since",
	"valid_to",
}


class CardTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		node = frappe.get_all("Geo Node", limit=1, pluck="name")
		cls.node = node[0] if node else None
		cls.volunteer = cls._volunteer("Active")

	@classmethod
	def _volunteer(cls, status):
		profile = frappe.get_doc(
			{
				"doctype": "Red Profile",
				"first_name": "Card",
				"last_name": frappe.generate_hash(length=6),
				"email": f"{frappe.generate_hash(length=8)}@example.org",
			}
		).insert(ignore_permissions=True)

		return frappe.get_doc(
			{
				"doctype": VOLUNTEER,
				"red_profile": profile.name,
				"home_geo_node": cls.node,
				"status": status,
			}
		).insert(ignore_permissions=True)


class TestTheToken(CardTestCase):
	def test_a_token_is_minted_once_and_never_changes(self):
		first = token.ensure(self.volunteer)
		again = token.ensure(frappe.get_doc(VOLUNTEER, self.volunteer.name))

		self.assertTrue(first)
		self.assertEqual(first, again, "a card already printed carries this value")

	def test_two_records_do_not_share_a_token(self):
		other = self._volunteer("Active")

		self.assertNotEqual(token.ensure(self.volunteer), token.ensure(other))

	def test_a_blank_token_resolves_to_nothing(self):
		"""Otherwise "no card" would find the first row with an empty column."""
		self.assertIsNone(token.holder("", (VOLUNTEER,)))
		self.assertIsNone(token.holder(None, (VOLUNTEER,)))

	def test_a_token_only_resolves_within_the_doctypes_it_was_offered(self):
		minted = token.ensure(self.volunteer)

		self.assertIsNone(token.holder(minted, ("VMMS Membership",)))


class TestWhatAStrangerIsTold(CardTestCase):
	def test_a_real_token_is_found_and_reports_the_card_as_current(self):
		answer = cards_api.verify(token.ensure(self.volunteer))

		self.assertTrue(answer["found"])
		self.assertTrue(answer["is_current"])
		self.assertEqual(answer["record_id"], self.volunteer.name)

	def test_the_docname_is_not_a_key(self):
		"""A sequence is guessable; that is the whole reason for the token."""
		self.assertEqual(cards_api.verify(self.volunteer.name), {"found": False})

	def test_an_unknown_token_says_only_that_it_is_unknown(self):
		self.assertEqual(cards_api.verify("not-a-real-token"), {"found": False})

	def test_nothing_beyond_the_agreed_fields_is_returned(self):
		answer = cards_api.verify(token.ensure(self.volunteer))

		self.assertEqual(
			set(answer) - PUBLIC_FIELDS,
			set(),
			"verify grew a field: check it is one a person holding the card can already read",
		)

	def test_a_withdrawn_card_is_found_but_not_current(self):
		"""Found and not-current are different answers; unknown is a third."""
		lapsed = self._volunteer("Exited")
		answer = cards_api.verify(token.ensure(lapsed))

		self.assertTrue(answer["found"])
		self.assertFalse(answer["is_current"])


class TestWhoHasACard(CardTestCase):
	def test_an_active_volunteer_holds_one(self):
		self.assertTrue(volunteer_card.holds_card(self.volunteer))
		volunteer_card.assert_holds(self.volunteer)

	def test_a_volunteer_who_is_not_active_is_refused_one(self):
		"""A card is evidence of standing, so one without standing is evidence of nothing."""
		lapsed = self._volunteer("Exited")

		self.assertFalse(volunteer_card.holds_card(lapsed))

		with self.assertRaises(frappe.ValidationError):
			volunteer_card.assert_holds(lapsed)
