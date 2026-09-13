# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What a page's wording may quote, and what happens when there is nothing there.

The substitution itself is four lines of regex; what is worth a test is the
*promise around it*, because a break in any of these is a broken sentence on the
front door of a national society's website and nobody would see it until a
visitor did:

- **A token with no value falls back rather than disappearing.** A site whose
  settings form nobody has opened is the ordinary first state of this product,
  and the hero on it has to read "Show up for your community." rather than
  "Show up for .".
- **Nothing is ever written back.** The stored text keeps the token; only what
  is drawn is resolved. A resolver that quietly wrote through would freeze one
  day's country into a society's database, which is the staleness the whole
  mechanism exists to avoid.
- **Prose is not eaten.** Braces appear in ordinary writing, and a block that
  says "{see the note}" — or "{name}", a key this app has never defined — must
  still say it. Only the two words in `tokens.KEYS` are ever substituted.

The frontend's copy of this lives in `portal/src/content/tokens.ts`, and its
defaults come from the same seed rows, so the two cannot disagree about what a
shipped block means.
"""

from frappe.tests import IntegrationTestCase

from vmmsx.content.services import tokens

EXTRA_TEST_RECORD_DEPENDENCIES = []

KNOWN = {"country": "Kenya", "society": "Kenya Red Cross Society"}
NOTHING = {"country": "", "society": ""}


class TestTokensResolve(IntegrationTestCase):
	def test_a_token_is_replaced_by_its_value(self):
		self.assertEqual(
			tokens.resolve("Show up for {country|your community}.", KNOWN),
			"Show up for Kenya.",
		)

	def test_a_token_with_no_value_falls_back_to_what_follows_the_pipe(self):
		self.assertEqual(
			tokens.resolve("Show up for {country|your community}.", NOTHING),
			"Show up for your community.",
		)

	def test_a_token_with_no_value_and_no_fallback_leaves_nothing_behind(self):
		self.assertEqual(tokens.resolve("Show up for {country}.", NOTHING), "Show up for .")

	def test_a_key_this_app_does_not_know_is_left_exactly_as_it_was_written(self):
		"""The silent failure this avoids: an administrator's own brace-word being
		deleted, with nothing on the page to show that it had been."""
		self.assertEqual(tokens.resolve("For {region|everyone}.", KNOWN), "For {region|everyone}.")
		self.assertEqual(tokens.resolve("Hello {name}", KNOWN), "Hello {name}")

	def test_more_than_one_token_in_a_sentence(self):
		self.assertEqual(
			tokens.resolve("{society|The Society} works across {country|the country}.", KNOWN),
			"Kenya Red Cross Society works across Kenya.",
		)

	def test_ordinary_prose_with_a_brace_in_it_is_left_alone(self):
		self.assertEqual(tokens.resolve("A {see the note} aside", KNOWN), "A {see the note} aside")

	def test_text_with_no_braces_is_returned_untouched(self):
		self.assertEqual(tokens.resolve("Nothing to do here", KNOWN), "Nothing to do here")

	def test_empty_text_is_not_a_failure(self):
		self.assertEqual(tokens.resolve("", KNOWN), "")

	def test_a_whole_surface_keeps_every_key_it_was_given(self):
		"""`resolve_words` reads this site's own society, whatever it says. What is
		promised is that every slot comes back — a surface that lost a key would
		be a page with a hole in it."""
		words = {"a": "In {country|the country}", "b": "plain", "c": "{society|us}"}
		resolved = tokens.resolve_words(words)

		self.assertEqual(set(resolved), set(words))
		self.assertEqual(resolved["b"], "plain")
		self.assertNotIn("{", resolved["a"])
		self.assertNotIn("{", resolved["c"])

	def test_the_values_are_the_two_this_app_documents(self):
		"""Never raises, whatever core says: this is read while drawing a page."""
		self.assertEqual(set(tokens.values()), {"country", "society"})


class TestTokensNeverWriteBack(IntegrationTestCase):
	def test_resolving_does_not_touch_the_stored_block(self):
		"""The pencil edits the token; the visitor reads the value. See the module
		docstring for why the two must not converge."""
		from vmmsx.content.tests.test_blocks import make_block, make_surface

		make_surface("CONTENT-TEST-tokens", public=True)
		block = make_block(
			"content-test.token.one",
			surface="CONTENT-TEST-tokens",
			text_value="Show up for {country|your community}.",
		)

		self.assertEqual(tokens.resolve(block.text_value, KNOWN), "Show up for Kenya.")
		self.assertEqual(
			block.reload().text_value,
			"Show up for {country|your community}.",
		)
