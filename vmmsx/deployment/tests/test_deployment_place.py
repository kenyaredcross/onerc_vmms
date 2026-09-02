# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Where a deployment is, and how somebody standing at a bus stand gets there.

Two places — the deployment point and the meeting point — because they are
routinely not the same one, and a volunteer told only the first arrives at a
flooded ward with no idea where the team gathered.

The rules worth asserting rather than believing:

1. **Nothing geocodes on save.** A deployment saves with no coordinates, with a
   half-written address, and on a site with no geocoding service configured at
   all. A third party being slow must never be the reason a coordinator cannot
   file their work.
2. **Every failure is an answer, not an exception.** No provider, no address,
   nothing found: all come back as `located: false` and a sentence somebody can
   act on.
3. **A pin dropped by hand wins.** Coordinates already on the record are never
   overwritten by an automatic pass, because whoever moved it knew something the
   address does not.
4. **The links are pure.** `map` and `directions` need no network, and they are
   `None` — never a link to nowhere — where there is no point.
"""

import frappe

from vmmsx.deployment.services import deployment as deployment_service
from vmmsx.deployment.services import geocoding
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class PlaceTestCase(DeploymentTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.terms = fixtures.make_terms()

	def deployment(self, **overrides):
		return fixtures.make_deployment(self.terms.name, self.society_a["branch"], **overrides)


class TestTheLinksNeedNothing(PlaceTestCase):
	def test_a_point_produces_a_map_link(self):
		link = geocoding.map_link(-6.7924, 39.2083)

		self.assertIn("openstreetmap.org", link)
		self.assertIn("-6.7924", link)

	def test_and_a_directions_link(self):
		self.assertIn("directions", geocoding.directions_link(-6.7924, 39.2083))

	def test_directions_from_somewhere_carry_both_ends(self):
		link = geocoding.directions_link(-6.7924, 39.2083, -3.3869, 36.6830)

		self.assertIn("-3.3869,36.683", link)
		self.assertIn("-6.7924,39.2083", link)

	def test_no_point_is_no_link_rather_than_a_link_to_nowhere(self):
		"""Zero and zero is the middle of the Atlantic, which is where an empty
		Float pair sends anybody who follows it."""
		self.assertIsNone(geocoding.map_link(None, None))
		self.assertIsNone(geocoding.map_link(0, 0))
		self.assertIsNone(geocoding.directions_link(0, 0))


class TestADeploymentSavesWithoutAPoint(PlaceTestCase):
	def test_a_deployment_with_no_place_at_all_saves(self):
		self.assertTrue(self.deployment().name)

	def test_a_deployment_with_an_address_and_no_coordinates_saves(self):
		deployment = self.deployment(
			site_name="Kigamboni Ward Office", site_address="Kigamboni, Dar es Salaam"
		)

		self.assertFalse(geocoding.has_point(deployment, geocoding.SITE))

	def test_and_its_place_still_describes_itself(self):
		deployment = self.deployment(site_name="Kigamboni Ward Office", site_address="Kigamboni")
		place = geocoding.dto(deployment, geocoding.SITE)

		self.assertEqual(place["name"], "Kigamboni Ward Office")
		self.assertFalse(place["has_point"])
		self.assertIsNone(place["map"])


class TestAFailureIsAnAnswer(PlaceTestCase):
	def test_an_empty_address_is_refused_with_a_sentence(self):
		answer = geocoding.locate("")

		self.assertFalse(answer["located"])
		self.assertTrue(answer["reason"])

	def test_a_site_with_no_provider_says_so(self):
		"""The shipped state. Nothing is configured, and the answer says what to
		do about it rather than failing."""
		if geocoding.is_configured():
			self.skipTest("this bench has a geocoding provider configured")

		answer = geocoding.locate("Kigamboni, Dar es Salaam")

		self.assertFalse(answer["located"])
		self.assertIn("by hand", answer["reason"])

	def test_locating_a_deployment_with_no_provider_leaves_it_alone(self):
		if geocoding.is_configured():
			self.skipTest("this bench has a geocoding provider configured")

		deployment = self.deployment(site_address="Kigamboni, Dar es Salaam")
		answer = geocoding.locate_place(deployment, geocoding.SITE)

		self.assertFalse(answer["located"])
		self.assertFalse(geocoding.has_point(deployment.reload(), geocoding.SITE))

	def test_a_place_that_is_not_one_of_the_two_is_refused(self):
		"""The allowed list belongs to the caller: a deployment has a site and a
		meeting point, and must not be able to name a task's."""
		with self.assertRaises(frappe.ValidationError):
			geocoding.assert_known("somewhere_else", geocoding.PLACES)


class TestAPinDroppedByHandWins(PlaceTestCase):
	def test_placing_a_pin_puts_the_point_on_the_record(self):
		deployment = self.deployment()
		answer = geocoding.relocate(deployment, geocoding.SITE, -6.7924, 39.2083)

		self.assertTrue(answer["located"])
		self.assertEqual(deployment.site_latitude, -6.7924)

	def test_a_hand_placed_pin_carries_no_located_on_stamp(self):
		"""Which is the whole difference between a point that came from an address
		and one that came from somebody's finger."""
		deployment = self.deployment()
		geocoding.relocate(deployment, geocoding.SITE, -6.7924, 39.2083)

		self.assertIsNone(deployment.site_located_on)

	def test_an_automatic_pass_leaves_an_existing_pin_alone(self):
		deployment = self.deployment(site_address="Somewhere else entirely")
		geocoding.relocate(deployment, geocoding.SITE, -6.7924, 39.2083)

		answer = geocoding.locate_place(deployment, geocoding.SITE)

		self.assertTrue(answer["located"])
		self.assertEqual(deployment.site_latitude, -6.7924)

	def test_the_two_places_are_separate(self):
		deployment = self.deployment()
		geocoding.relocate(deployment, geocoding.SITE, -6.7924, 39.2083)

		self.assertTrue(geocoding.has_point(deployment, geocoding.SITE))
		self.assertFalse(geocoding.has_point(deployment, geocoding.MEETING))


class TestTheInvitationCarriesTheWholeThing(PlaceTestCase):
	def test_a_deployment_describes_both_of_its_places(self):
		deployment = self.deployment(
			site_name="Kigamboni Ward Office",
			meeting_point="Branch office car park",
			travel_notes="The last two kilometres are unpaved.",
			local_contact_name="Joseph Kimaro",
			local_contact_phone="+255712000101",
		)
		where = deployment_service.where_dto(deployment)

		self.assertEqual(where["site"]["name"], "Kigamboni Ward Office")
		self.assertEqual(where["meeting_point"]["name"], "Branch office car park")
		self.assertEqual(where["travel_notes"], "The last two kilometres are unpaved.")
		self.assertEqual(where["local_contact"]["phone"], "+255712000101")

	def test_the_coordinator_comes_back_as_a_person_rather_than_a_login(self):
		deployment = self.deployment()
		contact = deployment_service.coordinator_dto(deployment)

		self.assertEqual(contact["user"], deployment.coordinator)
		self.assertIsInstance(contact["phone"], str)

	def test_an_invitation_carries_the_place_the_schedule_and_the_contact(self):
		from vmmsx.deployment.services import invitation

		volunteer = fixtures.make_volunteer(
			fixtures.make_profile("Invited", "Volunteer"), self.society_a["branch"]
		)
		deployment = self.deployment(
			meeting_point="Branch office car park",
			briefing_on=f"{frappe.utils.today()} 07:00:00",
		)
		invitation.invite(deployment, volunteer.name)

		rows = invitation.pending_for(volunteer.name)

		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["where"]["meeting_point"]["name"], "Branch office car park")
		self.assertTrue(rows[0]["schedule"]["briefing_on"])
		self.assertEqual(rows[0]["coordinator_contact"]["user"], deployment.coordinator)
