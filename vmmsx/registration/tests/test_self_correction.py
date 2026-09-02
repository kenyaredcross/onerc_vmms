# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Correcting your own details, and the two walls around it.

`api/registration.py::update_my_profile` is the only endpoint in this app that
overwrites core's identity spine, and it exists because the additive rule always
implied it: `intake._enrich` refuses to let a *registration form* contradict what
the society holds, and intake's own docstring says the correction belongs on the
profile instead. This is that door.

Two things have to stay true of it, and both are asserted here rather than
argued in a comment:

* **It is possessive.** No parameter names a person, so the profile written is
  the one carrying the caller's own login and there is nothing to tamper with.
* **It cannot reach the email.** The email is the login. An endpoint that could
  change it could walk a profile onto somebody else's account.

The suite registers people through the real forms, so the person doing the
correcting holds exactly what a self-registered applicant holds: the self-service
role and no write permission on Red Profile at all.
"""

import inspect

import frappe

from vmmsx.api import registration as registration_api
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestCorrectingYourOwnProfile(RegistrationTestCase):
	def _registered(self, handle: str) -> tuple[str, str]:
		"""Somebody who has registered, and the profile the registration made."""
		user, _ = self.register_as_volunteer(handle)
		profile = self.profile_of(user)

		self.assertIsNotNone(profile, "the registration should have produced a profile")

		return user, profile

	def _held(self, profile: str) -> dict:
		frappe.clear_document_cache(fixtures.PROFILE_DOCTYPE, profile)

		return frappe.db.get_value(
			fixtures.PROFILE_DOCTYPE,
			profile,
			[
				"first_name",
				"last_name",
				"phone",
				"gender",
				"date_of_birth",
				"preferred_language",
				"email",
				"user",
			],
			as_dict=True,
		)

	# --- the correction itself -------------------------------------------

	def test_a_person_may_rewrite_their_own_name_and_phone(self):
		"""The case the whole endpoint exists for.

		The applicant holds no write permission on Red Profile — nobody
		self-registering does — so this passing is also what proves the
		elevation inside the endpoint is doing its one job.
		"""
		user, profile = self._registered("correct.name")

		with fixtures.acting_as(user):
			registration_api.update_my_profile(
				first_name="Aminah", last_name="Otieno-Wanjiru", phone="+254700111222"
			)

		held = self._held(profile)

		self.assertEqual(held.first_name, "Aminah")
		self.assertEqual(held.last_name, "Otieno-Wanjiru")
		self.assertEqual(held.phone, "+254700111222")

	def test_a_field_left_out_is_left_alone(self):
		"""None means "do not touch", which is what makes a partial call safe."""
		user, profile = self._registered("correct.partial")

		with fixtures.acting_as(user):
			registration_api.update_my_profile(phone="+254700333444")

		held = self._held(profile)

		self.assertEqual(held.phone, "+254700333444")
		self.assertEqual(held.first_name, "Amina")
		self.assertEqual(held.last_name, "Otieno")

	# --- the photograph ---------------------------------------------------
	#
	# The one self-editable field holding a file rather than a value, and the
	# only one whose value ends up printed on a card a steward compares with a
	# face. So the refusal below matters more than the acceptance beside it.

	def test_a_person_may_set_their_own_photograph(self):
		user, profile = self._registered("correct.photo")

		with fixtures.acting_as(user):
			registration_api.update_my_profile(profile_photo="/files/portrait.png")

		self.assertEqual(
			frappe.db.get_value(fixtures.PROFILE_DOCTYPE, profile, "profile_photo"),
			"/files/portrait.png",
		)

	def test_a_private_upload_is_accepted_too(self):
		"""Both of the framework's own upload paths, not just the public one."""
		user, profile = self._registered("correct.photo.private")

		with fixtures.acting_as(user):
			registration_api.update_my_profile(profile_photo="/private/files/portrait.png")

		self.assertEqual(
			frappe.db.get_value(fixtures.PROFILE_DOCTYPE, profile, "profile_photo"),
			"/private/files/portrait.png",
		)

	def test_a_photograph_somewhere_else_is_refused(self):
		"""The property this check exists for.

		The value is rendered on every screen showing this person and inside a
		printed card. An endpoint that accepted an arbitrary URL would put
		somebody else's server there, which is the rule `questions._file` applies
		to an uploaded answer and `links.py` applies to a content block's href.
		"""
		user, profile = self._registered("correct.photo.remote")

		for elsewhere in (
			"https://example.com/portrait.png",
			"http://example.com/portrait.png",
			"//example.com/portrait.png",
			"javascript:alert(1)",
			"/etc/passwd",
		):
			with fixtures.acting_as(user), self.assertRaises(frappe.ValidationError):
				registration_api.update_my_profile(profile_photo=elsewhere)

		self.assertFalse(frappe.db.get_value(fixtures.PROFILE_DOCTYPE, profile, "profile_photo"))

	def test_a_photograph_can_be_taken_off(self):
		"""It is an optional field, so an empty string clears it. Somebody who
		would rather not have their face on a card does not have to ask."""
		user, profile = self._registered("correct.photo.remove")

		with fixtures.acting_as(user):
			registration_api.update_my_profile(profile_photo="/files/portrait.png")
			registration_api.update_my_profile(profile_photo="")

		self.assertFalse(frappe.db.get_value(fixtures.PROFILE_DOCTYPE, profile, "profile_photo"))

	# --- the photograph a *registration* carries ---------------------------
	#
	# The first-timer's case, and the one that was quietly broken: somebody with
	# no profile yet cannot correct one, so their portrait used to go up in a
	# second call made after the registration had already succeeded, with its
	# failure swallowed on purpose. Anything between the two calls — a reload, a
	# closed tab — lost the picture, and the only symptom was an empty control
	# the next time they registered for anything. It rides with the registration
	# now, and these assert both halves of that: it lands, and it is still
	# additive.

	def test_a_registration_carries_the_portrait_that_came_with_it(self):
		user = fixtures.website_account("register.with.photo")

		with fixtures.acting_as(user):
			registration_api.register_as_volunteer(
				geo_node=self.branch(),
				home_geo_node=self.branch(),
				id_type=fixtures.make_identification_type(),
				id_number="A-1234567",
				date_of_birth=fixtures.DEFAULT_DATE_OF_BIRTH,
				profile_photo="/files/portrait.png",
				# Required to submit, and this test is about the portrait. See
				# `fixtures.submit_volunteer_form` for why every suite that is
				# about something else answers it.
				disability_status="Prefer not to say",
				declarations_accepted=fixtures.required_declarations(),
			)

		profile = self.profile_of(user)

		self.assertEqual(
			frappe.db.get_value(fixtures.PROFILE_DOCTYPE, profile, "profile_photo"),
			"/files/portrait.png",
			"the picture chosen on the form should be on the profile the form made",
		)

	def test_a_membership_carries_one_too(self):
		"""Both doors, because both wizards draw the same control."""
		user = fixtures.website_account("register.member.photo")

		with fixtures.acting_as(user):
			registration_api.register_as_member(
				membership_type=fixtures.TYPE_ROUTED,
				geo_node=self.branch(),
				profile_photo="/files/portrait.png",
			)

		self.assertEqual(
			frappe.db.get_value(fixtures.PROFILE_DOCTYPE, self.profile_of(user), "profile_photo"),
			"/files/portrait.png",
		)

	def test_a_registration_does_not_replace_a_portrait_already_on_file(self):
		"""Additive, like every other value a registration carries.

		Registering is not the act of correcting: somebody joining as a member in
		August must not silently overwrite the portrait their volunteer
		application put on file in March. `update_my_profile` is the door for
		that, and it is the only one.
		"""
		user, profile = self._registered("register.photo.additive")

		with fixtures.acting_as(user):
			registration_api.update_my_profile(profile_photo="/files/held.png")
			registration_api.register_as_member(
				membership_type=fixtures.TYPE_ROUTED,
				geo_node=self.branch(),
				profile_photo="/files/newer.png",
			)

		self.assertEqual(
			frappe.db.get_value(fixtures.PROFILE_DOCTYPE, profile, "profile_photo"),
			"/files/held.png",
		)

	def test_a_registration_refuses_a_portrait_from_somewhere_else(self):
		"""The same wall `update_my_profile` puts up, on the same value."""
		user = fixtures.website_account("register.photo.remote")

		with fixtures.acting_as(user), self.assertRaises(frappe.ValidationError):
			registration_api.register_as_member(
				membership_type=fixtures.TYPE_ROUTED,
				geo_node=self.branch(),
				profile_photo="https://example.com/portrait.png",
			)

	def test_the_profile_serves_the_persons_home_area_for_confirmation(self):
		"""A second registration can confirm the home area already on the profile.

		Home Area is residence, not the volunteer's Serving Branch, so it is a
		person-owned fact they may correct through the profile endpoint.
		"""
		user, _profile = self._registered("placed.already")

		with fixtures.acting_as(user):
			served = registration_api.my_profile()

		self.assertEqual(served["home_geo_node"], self.branch())
		self.assertIn(
			"home_geo_node",
			inspect.signature(registration_api.update_my_profile).parameters,
			"home area is a person detail the profile endpoint may correct",
		)

	def test_the_photograph_reaches_the_card(self):
		"""What the whole change is for: the card reads the profile live.

		Rendered rather than asserted on the context alone, so this also proves
		the shipped template draws it — a context key nothing renders would be a
		photograph nobody ever sees.
		"""
		from vmmsx.volunteer.services import card as volunteer_card

		user, profile = self._registered("correct.photo.card")

		with fixtures.acting_as(user):
			registration_api.update_my_profile(profile_photo="/files/portrait.png")

		# Built directly rather than through an approval: what is being tested is
		# that the card reads the photograph off Red Profile, and routing that
		# through the engine would make this a test of the engine that fails for
		# reasons having nothing to do with a photograph.
		from vmmsx.volunteer.services import volunteer as volunteer_service

		volunteer = volunteer_service.ensure(profile, home_geo_node=self.branch())
		context = volunteer_card.context_for(volunteer)

		self.assertEqual(context["holder_photo"], "/files/portrait.png")

	def test_the_card_carries_no_photograph_when_there_is_none(self):
		"""An empty slot, not a broken image. The template draws nothing for it."""
		from vmmsx.volunteer.services import card as volunteer_card
		from vmmsx.volunteer.services import volunteer as volunteer_service

		_user, profile = self._registered("correct.photo.none")

		volunteer = volunteer_service.ensure(profile, home_geo_node=self.branch())

		self.assertEqual(volunteer_card.context_for(volunteer)["holder_photo"], "")

	def test_an_optional_field_can_be_emptied(self):
		"""Withdrawing a phone number is a correction like any other."""
		user, profile = self._registered("correct.clear")

		with fixtures.acting_as(user):
			registration_api.update_my_profile(phone="+254700555666")
			registration_api.update_my_profile(phone="")

		self.assertFalse(self._held(profile).phone)

	def test_a_name_may_not_be_emptied(self):
		"""Core refuses a profile without one, so this refuses it with a sentence."""
		user, profile = self._registered("correct.nameless")

		with fixtures.acting_as(user), self.assertRaises(frappe.ValidationError):
			registration_api.update_my_profile(first_name="  ")

		self.assertEqual(self._held(profile).first_name, "Amina")

	def test_the_full_name_is_recomposed(self):
		"""Written through the document's own save, so core's validate() runs."""
		user, profile = self._registered("correct.fullname")

		with fixtures.acting_as(user):
			registration_api.update_my_profile(first_name="Aminah", last_name="Wanjiru")

		self.assertEqual(
			frappe.db.get_value(fixtures.PROFILE_DOCTYPE, profile, "full_name"), "Aminah Wanjiru"
		)

	def test_the_contact_language_is_theirs_to_choose(self):
		"""A Link, so it is checked: a language the site does not have is refused."""
		user, profile = self._registered("correct.language")
		language = frappe.get_all("Language", limit=1, pluck="name")[0]

		with fixtures.acting_as(user):
			registration_api.update_my_profile(preferred_language=language)

		self.assertEqual(self._held(profile).get("preferred_language"), language)

	def test_it_returns_the_profile_as_it_now_stands(self):
		user, _ = self._registered("correct.returns")

		with fixtures.acting_as(user):
			dto = registration_api.update_my_profile(first_name="Aminah")

		self.assertEqual(dto["first_name"], "Aminah")

	# --- the walls --------------------------------------------------------

	def test_the_email_is_not_a_parameter(self):
		"""The login is the identity. There is no argument that could change it."""
		parameters = inspect.signature(registration_api.update_my_profile).parameters

		self.assertNotIn("email", parameters)
		self.assertNotIn("user", parameters)
		self.assertNotIn("red_profile", parameters)

	def test_nothing_it_writes_can_move_the_email(self):
		user, profile = self._registered("correct.email")
		before = self._held(profile)

		with fixtures.acting_as(user):
			registration_api.update_my_profile(first_name="Aminah", phone="+254700777888")

		after = self._held(profile)

		self.assertEqual(after.email, before.email)
		self.assertEqual(after.user, user)

	def test_it_touches_nobody_else(self):
		"""Possessive: the profile written is the session's, and only ever that."""
		_, mine = self._registered("correct.mine")
		other, theirs = self._registered("correct.theirs")

		with fixtures.acting_as(other):
			registration_api.update_my_profile(first_name="Nobody", last_name="Else")

		self.assertEqual(self._held(mine).first_name, "Amina")
		self.assertEqual(self._held(theirs).first_name, "Nobody")

	def test_a_guest_is_refused(self):
		with fixtures.acting_as("Guest"), self.assertRaises(frappe.PermissionError):
			registration_api.update_my_profile(first_name="Anybody")

	def test_somebody_with_no_profile_is_told_to_register(self):
		"""It corrects a profile; it does not mint one. `claim_my_profile` does that."""
		stranger = fixtures.website_account("correct.stranger")

		with fixtures.acting_as(stranger), self.assertRaises(frappe.ValidationError):
			registration_api.update_my_profile(first_name="Stranger")

	# --- and registration is still additive ------------------------------

	def test_registering_again_does_not_undo_a_correction(self):
		"""The two doors keep their own rules.

		This is the ordering the wizard depends on. A correction goes through the
		endpoint that overwrites; the registration that follows carries the same
		values in its intake buffer, and `intake._enrich` leaves them alone
		because core now holds them. If registration ever started overwriting,
		this test would still pass — so the one below is the one that guards it.
		"""
		user, profile = self._registered("correct.then.register")

		with fixtures.acting_as(user):
			registration_api.update_my_profile(first_name="Aminah", last_name="Wanjiru")
			fixtures.submit_membership_form(self.branch(), fixtures.TYPE_AUTO)

		held = self._held(profile)

		self.assertEqual(held.first_name, "Aminah")
		self.assertEqual(held.last_name, "Wanjiru")

	def test_a_registration_still_cannot_contradict_the_profile(self):
		"""The rule `update_my_profile` was added *beside*, not instead of."""
		user, profile = self._registered("register.cannot.overwrite")

		with fixtures.acting_as(user):
			fixtures.submit_membership_form(
				self.branch(),
				fixtures.TYPE_AUTO,
				applicant_first_name="Somebody",
				applicant_last_name="Different",
			)

		held = self._held(profile)

		self.assertEqual(held.first_name, "Amina")
		self.assertEqual(held.last_name, "Otieno")
