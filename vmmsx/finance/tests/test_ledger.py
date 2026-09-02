# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What the finance report counts, and — more importantly — what it refuses to.

The screen this feeds carries two caveats in as many sentences, and they are the
whole reason this suite exists: a report derived from records that were never
kept as accounts is only honest while the derivation is exactly what it says it
is. Four properties have to hold, and each of them is one small edit away from
silently breaking.

**A proved membership is not income.** `membership_source` tells apart somebody
who paid the society through this system from somebody who showed evidence of a
membership they already held elsewhere. Both are members; only the first brought
money in. Counting the second would turn a data-migration exercise into a
revenue spike, and nothing on the screen would say so.

**A membership with no fee is counted and contributes nothing.** An honorary
type, or one whose price has not been set, is a real membership and a zero
amount — so it must appear in the breakdown (with `unpriced` set, which is what
the screen prints "No fee set" from) and must not quietly inflate a total.

**`paid_on` is the date, not `creation`.** A society records a payment when it
is reconciled, routinely a different day from when the applicant filled the form
in, and a window that used the wrong one would put revenue in the wrong month.

**Currency is grouped, never converted.** A site with two currencies gets two
totals. A single number would be a made-up exchange rate wearing a report's
clothes.

Built on `member/tests/fixtures.py` rather than on hand-rolled inserts: a
membership is a geo-anchored document with a real `VMMS Member` behind it, and
arranging that by hand here would be a second, drifting answer to what one is.
"""

from frappe.utils import add_days, add_months, today

from vmmsx.finance.services import ledger
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase


class LedgerTestCase(MemberTestCase):
	"""Three membership types at three prices, in one branch."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.annual = fixtures.make_type("ledger-annual", "auto_on_payment", fee=25_000).name
		# `routed`, not `auto_on_payment`: the doctype refuses a zero-fee type
		# that activates on payment, because nothing would ever have to happen —
		# which is the right rule, and it is also how an honorary membership
		# really works. Somebody decides it.
		cls.honorary = fixtures.make_type("ledger-honorary", "routed", fee=0).name
		cls.foreign = fixtures.make_type(
			"ledger-foreign", "auto_on_payment", fee=1_200, fee_currency="USD"
		).name
		# A proof-based membership needs an approver to verify what was attached,
		# so its type has to be routed — the doctype refuses the pairing
		# otherwise, and it is right to. Priced like the annual one, so the test
		# below is about `membership_source` and nothing else.
		cls.proved = fixtures.make_type("ledger-proved", "routed", fee=25_000).name

		cls.profile = fixtures.make_profile("Ledger", "Subject")
		cls.node = cls.society_a["ward"]

	def _paid(self, membership_type: str, paid_on: str, source: str = "Gateway", **overrides):
		"""One membership with a payment date on it.

		Written after the insert rather than passed to it: `paid_on` is set by
		the payment seam in real life, and the doctype's own validation does not
		expect it on a document being created.
		"""
		doc = fixtures.make_membership(
			self.profile, membership_type, self.node, membership_source=source, **overrides
		)
		doc.db_set("paid_on", paid_on, update_modified=False)

		return doc


class TestWhatCountsAsIncome(LedgerTestCase):
	def test_a_gateway_payment_is_income(self):
		before = ledger.summary()["income"]["count"]

		self._paid(self.annual, today())

		answer = ledger.summary()

		self.assertEqual(answer["income"]["count"], before + 1)
		self.assertTrue(any(row["amount"] >= 25_000 for row in answer["income"]["totals"]))

	def test_a_proved_membership_is_not_income(self):
		"""The rule the module docstring leads with.

		Somebody who showed evidence of a membership held elsewhere is a member
		and is not a sale. If this ever passes by counting them, a society
		migrating its paper register would appear to have had a record year.
		"""
		before = ledger.summary()["income"]["count"]

		# A real proof file, because the doctype requires one: a proof-based
		# membership without the document is a claim with nothing behind it.
		self._paid(
			self.proved,
			today(),
			source="Proof",
			proof_attachment=fixtures.make_proof_file(),
		)

		self.assertEqual(ledger.summary()["income"]["count"], before)

	def test_a_payment_outside_the_window_is_not_counted(self):
		"""`paid_on` bounds the window, and a payment reconciled long ago stays
		out of it.

		A delta rather than an absolute zero: Frappe rolls the test transaction
		back once per *class*, so whatever an earlier method in this class
		created is still there. Asserting "nothing at all" would pass or fail on
		test ordering rather than on the thing being tested.
		"""
		window = {"from_date": add_days(today(), -20), "to_date": today()}
		before = ledger.summary(**window)["income"]["count"]

		self._paid(self.annual, add_months(today(), -18))

		self.assertEqual(ledger.summary(**window)["income"]["count"], before)

	def test_an_unpriced_type_is_counted_and_contributes_nothing(self):
		"""It is a real membership and a zero amount, and the payload says both."""
		self._paid(self.honorary, today())

		row = next(
			entry
			for entry in ledger.summary()["income"]["by_type"]
			if entry["membership_type"] == self.honorary
		)

		self.assertTrue(row["unpriced"])
		self.assertEqual(row["count"], 1)
		self.assertEqual(row["amount"], 0)

	def test_the_basis_travels_with_the_answer(self):
		"""The screen prints its caveat from this rather than hard-coding it."""
		self.assertEqual(ledger.summary()["basis"], ledger.BASIS_PUBLISHED_FEE)


class TestCurrencyIsGroupedNotConverted(LedgerTestCase):
	def test_two_currencies_come_back_as_two_totals(self):
		self._paid(self.annual, today())
		self._paid(self.foreign, today())

		currencies = {row["currency"] for row in ledger.summary()["income"]["totals"]}

		self.assertIn("USD", currencies)
		self.assertGreaterEqual(len(currencies), 2)

	def test_net_is_computed_per_currency(self):
		"""Never across them: income in one money minus expenditure in another
		is not a number, and a screen showing one would be inventing a rate."""
		self._paid(self.foreign, today())

		rows = ledger.summary()["net"]

		self.assertTrue(rows)
		for row in rows:
			self.assertEqual(row["net"], row["income"] - row["expenses"])


class TestTheShapeOfTheYear(LedgerTestCase):
	def test_every_month_in_the_window_is_present_even_when_empty(self):
		"""A quiet month is a fact about the year, not a month to leave out.

		A chart whose columns appear and disappear between refreshes cannot be
		read at all — the shape is the thing somebody is looking at.
		"""
		answer = ledger.summary(from_date=add_months(today(), -5), to_date=today())
		months = [row["month"] for row in answer["months"]]

		self.assertEqual(len(months), 6)
		self.assertEqual(months, sorted(months))

	def test_a_backwards_window_is_read_forwards(self):
		"""A caller who passes the dates the wrong way round gets the window they
		meant rather than an empty report."""
		answer = ledger.summary(from_date=today(), to_date=add_days(today(), -30))

		self.assertLessEqual(answer["from_date"], answer["to_date"])
