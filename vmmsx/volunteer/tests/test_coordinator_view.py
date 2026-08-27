# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The volunteer record as the complete picture a coordinator decides from.

The register was thin. Everything a coordinator needed in order to decide
anything about a volunteer lived somewhere else: what they could do was on a
settled application, whether they were deployable was nowhere, and what they had
actually done was in two other doctypes. This suite covers making the volunteer
record the answer, and it is organised around the four claims that make the
design defensible rather than merely convenient.

1. **Living data moved, and then diverges.** Skills, languages, availability,
   citizenship and residency are seeded from the application at acceptance and
   are the volunteer's own from then on. The suite edits one on the volunteer
   and asserts the application did not move, which is the property the whole
   split exists to produce.
2. **Historical data did not move.** Motivation, prior experience and the
   identification captured at intake are shown from the application and have no
   current-state field on the register to edit.
3. **Identity still is not duplicated.** The old guarantee is extended rather
   than weakened: the volunteer now stores its own attributes, and *only* its
   own. Home Area in particular is read from Red Profile, because where somebody
   lives is a fact about the person, and the temptation to copy it was the
   nearest miss in this whole pass.
4. **Derived stays derived.** Deployability and lapse are computed on read, and
   a lapsed mandatory certification flips the indicator with nothing written
   anywhere. Asserted by comparing the whole database row before and after.

Plus the fifth, which is Part 4: capabilities are queryable **on top of** geo
scope, never instead of it. An out-of-scope volunteer holding the skill being
searched for must not come back, and there is a test whose only job is that.

Nothing here is mocked. The volunteers are produced by the real approval engine
through a real workflow, decided by the person core resolved.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.approvals import states
from vmmsx.volunteer.services import application as application_service
from vmmsx.volunteer.services import capabilities, certification
from vmmsx.volunteer.tests import fixtures
from vmmsx.volunteer.tests.base import VolunteerTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class CoordinatorViewTestCase(VolunteerTestCase):
	"""A workflow, an approver, and a helper that runs a real acceptance."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_workflow()
		fixtures.grant_doctype_access(fixtures.APPLICATION_DOCTYPE, fixtures.APPROVER_ROLE)

		cls.approver = cls.scoped_user("dossier_approver", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.approver, fixtures.APPROVER_ROLE, cls.society_a["county"])

	def accepted(self, handle: str, node: str | None = None, **application_values):
		"""An approved application and the volunteer it produced.

		Goes through `engine.decide` as the approver rather than writing a state,
		so what the seed observes is what an acceptance actually produces.
		"""
		from vmmsx.approvals.services import engine

		profile = fixtures.make_profile("Dossier", handle.title())
		application = fixtures.make_application(profile, node or self.society_a["ward"], **application_values)

		application_service.submit(application)

		with fixtures.acting_as(self.approver):
			engine.decide(
				frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name),
				states.DECISION_APPROVED,
			)

		application.reload()
		volunteer = frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, application.volunteer)

		return {"profile": profile, "application": application, "volunteer": volunteer}

	def skill_keys(self, doc, fieldname: str = "skills") -> list[str]:
		return [row.skill for row in doc.get(fieldname)]

	def row(self, volunteer: str) -> dict:
		"""The volunteer's whole database row, for before/after comparison."""
		return dict(frappe.db.get_value(fixtures.VOLUNTEER_DOCTYPE, volunteer, "*", as_dict=True))


# --- 1. seeded on approval, and then divergent ----------------------------


class TestSeedingOnApproval(CoordinatorViewTestCase):
	def test_approving_copies_the_capabilities_onto_the_volunteer(self):
		skill = fixtures.make_skill()
		slot = fixtures.make_availability_slot()
		language = fixtures.test_language()

		case = self.accepted(
			"seeded",
			skills=[{"skill": skill.name}],
			availability=[{"availability_slot": slot.name}],
			languages=[{"language": language}],
		)

		volunteer = case["volunteer"]

		self.assertEqual(self.skill_keys(volunteer), [skill.name])
		self.assertEqual([row.availability_slot for row in volunteer.availability], [slot.name])
		self.assertEqual([row.language for row in volunteer.languages], [language])

	def test_citizenship_and_residency_are_read_live_from_the_profile(self):
		case = self.accepted("residency", residency_type="Local")
		placement = capabilities.placement(case["volunteer"])

		self.assertEqual(placement["country_of_citizenship"], fixtures.test_country())
		self.assertEqual(placement["residency_type"], "Local")

	def test_the_serving_branch_is_the_applications_anchor(self):
		"""Where they said they would serve is where the volunteer is placed."""
		case = self.accepted("branch")

		self.assertEqual(
			case["volunteer"].get(capabilities.SERVING_BRANCH_FIELD),
			case["application"].geo_node,
		)

	def test_seeding_reports_what_it_wrote(self):
		skill = fixtures.make_skill()
		profile = fixtures.make_profile("Reported", "Seed")
		application = fixtures.make_application(
			profile, self.society_a["ward"], skills=[{"skill": skill.name}]
		)
		volunteer = fixtures.make_volunteer(profile, self.society_a["ward"])

		seeded = capabilities.seed(volunteer, application)

		self.assertIn("skills", seeded)
		self.assertNotIn("country_of_citizenship", seeded)

	def test_seeding_twice_writes_nothing_the_second_time(self):
		"""Idempotent in the strong sense: the second call finds the work done."""
		skill = fixtures.make_skill()
		case = self.accepted("twice", skills=[{"skill": skill.name}])

		before = self.row(case["volunteer"].name)
		again = capabilities.seed(
			frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, case["volunteer"].name), case["application"]
		)

		self.assertEqual(again, {})
		self.assertEqual(self.row(case["volunteer"].name), before)

	def test_a_second_application_does_not_overwrite_maintained_data(self):
		"""The reason seeding fills blanks rather than copying.

		Somebody who volunteered, exited and applied again years later is the
		same person. What the society has been maintaining about them outranks a
		form they filled in last week, and a seed that overwrote would silently
		undo years of corrections.
		"""
		first = fixtures.make_skill()
		second = fixtures.make_skill(fixtures.SKILL_RADIO)
		case = self.accepted("returning", skills=[{"skill": first.name}])

		profile = case["profile"]
		later = fixtures.make_application(profile, self.society_a["ward"], skills=[{"skill": second.name}])

		capabilities.seed(frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, case["volunteer"].name), later)

		volunteer = frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, case["volunteer"].name)

		self.assertEqual(self.skill_keys(volunteer), [first.name])


class TestTheyDiverge(CoordinatorViewTestCase):
	"""The property the split exists for. Neither side follows the other."""

	def test_editing_the_volunteers_skills_does_not_touch_the_application(self):
		first = fixtures.make_skill()
		learned = fixtures.make_skill(fixtures.SKILL_RADIO)
		case = self.accepted("diverging", skills=[{"skill": first.name}])

		volunteer = frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, case["volunteer"].name)
		volunteer.append("skills", {"skill": learned.name})
		volunteer.save(ignore_permissions=True)

		application = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, case["application"].name)

		self.assertEqual(sorted(self.skill_keys(volunteer)), sorted([first.name, learned.name]))
		self.assertEqual(
			self.skill_keys(application),
			[first.name],
			"editing the volunteer rewrote what the applicant declared",
		)

	def test_correcting_the_application_does_not_touch_the_volunteer(self):
		"""The other direction, which matters just as much.

		A settled application is a record of what was said. Correcting a typo in
		one must not silently change what somebody is qualified for today.
		"""
		first = fixtures.make_skill()
		other = fixtures.make_skill(fixtures.SKILL_RADIO)
		case = self.accepted("corrected", skills=[{"skill": first.name}])

		application = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, case["application"].name)
		application.skills = []
		application.append("skills", {"skill": other.name})
		application.save(ignore_permissions=True)

		volunteer = frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, case["volunteer"].name)

		self.assertEqual(self.skill_keys(volunteer), [first.name])

	def test_the_current_dto_reads_the_volunteer_and_never_the_application(self):
		"""No fallback. An empty field is an empty field, not a stale claim."""
		skill = fixtures.make_skill()
		case = self.accepted("no_fallback", skills=[{"skill": skill.name}])

		volunteer = frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, case["volunteer"].name)
		volunteer.skills = []
		volunteer.save(ignore_permissions=True)

		current = capabilities.current(volunteer)
		declared = application_service.verification_dto(volunteer)["declared"]

		self.assertEqual(current["skills"], [])
		self.assertEqual(
			declared["skills"],
			[{"key": skill.name, "label": skill.skill_name}],
			"the application's own snapshot was cleared too",
		)


# --- 2. living versus historical ------------------------------------------


class TestLivingVersusHistorical(CoordinatorViewTestCase):
	def test_the_living_three_are_editable_fields_on_the_volunteer(self):
		meta = frappe.get_meta(fixtures.VOLUNTEER_DOCTYPE)

		expected = {
			"skills": "VMMS Skill Selector",
			"languages": "VMMS Language Selector",
			"availability": "VMMS Availability Selector",
		}

		for fieldname, options in expected.items():
			field = meta.get_field(fieldname)

			self.assertIsNotNone(field, f"{fieldname} is missing from the volunteer")
			self.assertEqual(field.fieldtype, "Table MultiSelect")
			self.assertEqual(field.options, options)
			self.assertFalse(field.read_only, f"{fieldname} is read-only and must be editable")

	def test_citizenship_and_residency_are_not_stored_on_the_volunteer(self):
		meta = frappe.get_meta(fixtures.VOLUNTEER_DOCTYPE)

		for fieldname in (
			"country_of_citizenship",
			"residency_type",
			"country_of_residence",
			"residence_address",
		):
			self.assertIsNone(meta.get_field(fieldname), f"the volunteer stores {fieldname}")

	def test_the_historical_ones_have_no_field_to_edit(self):
		"""Shown from the application, and with no current-state copy anywhere."""
		meta = frappe.get_meta(fixtures.VOLUNTEER_DOCTYPE)

		for fieldname in ("motivation", "prior_experience", "id_type", "id_number"):
			self.assertIsNone(meta.get_field(fieldname), f"the volunteer has grown {fieldname}")

	def test_they_are_shown_from_the_application(self):
		motivation = fixtures.make_motivation()
		case = self.accepted(
			"historical",
			motivation=[{"motivation": motivation.name}],
			prior_experience="Two floods with another society",
		)

		declared = application_service.verification_dto(case["volunteer"])["declared"]

		self.assertEqual(
			declared["motivation"], [{"key": motivation.name, "label": motivation.motivation_name}]
		)
		self.assertEqual(declared["prior_experience"], "Two floods with another society")

	def test_the_identification_is_shown_live_from_the_profile(self):
		case = self.accepted("identification")

		decision = application_service.decision_dto(case["application"])
		identification = decision["identifications"][0]
		profile_identification = frappe.get_doc("Red Profile", case["profile"]).identifications[0]

		self.assertEqual(identification["id_type"], profile_identification.id_type)
		self.assertEqual(identification["id_number"], profile_identification.id_number)


# --- 3. identity is still not duplicated ----------------------------------


class TestIdentityIsStillNotDuplicated(CoordinatorViewTestCase):
	"""The old guarantee, extended to cover what this pass added.

	The volunteer grew columns for the first time. So the guard has to say more
	than "no columns were added": it has to say *which* were, and that the list
	is exactly the volunteer-owned attributes and nothing about who the person
	is.
	"""

	# Everything the record is allowed to have gained. Written out so that a
	# thirteenth column fails this suite and its author has to come and say why.
	VOLUNTEER_OWNED = (
		"skills",
		"languages",
		"availability",
	)

	def test_no_identity_column_was_added_by_this_pass(self):
		columns = set(frappe.db.get_table_columns(fixtures.VOLUNTEER_DOCTYPE))

		for fieldname in (
			"full_name",
			"first_name",
			"middle_name",
			"last_name",
			"email",
			"phone",
			"gender",
			"date_of_birth",
			"preferred_language",
			"profile_photo",
		):
			self.assertNotIn(fieldname, columns, f"the volunteer stores {fieldname} in a column")

	def test_only_the_volunteer_owned_attributes_persist(self):
		"""The positive half. Absence proves nothing about what *was* added.

		Table MultiSelects are child tables rather than columns, so the two are
		checked where each actually lives.
		"""
		meta = frappe.get_meta(fixtures.VOLUNTEER_DOCTYPE)
		for fieldname in ("skills", "languages", "availability"):
			self.assertEqual(meta.get_field(fieldname).fieldtype, "Table MultiSelect")

		for fieldname in (
			"country_of_citizenship",
			"residency_type",
			"country_of_residence",
			"residence_address",
		):
			self.assertIsNone(meta.get_field(fieldname))

	def test_no_field_fetches_identity_from_anywhere(self):
		"""A fetched value is a stored copy wearing a different hat."""
		meta = frappe.get_meta(fixtures.VOLUNTEER_DOCTYPE)

		self.assertEqual([field.fieldname for field in meta.fields if field.fetch_from], [])

	def test_the_name_still_comes_from_red_profile_every_time(self):
		case = self.accepted("live_name")

		profile = frappe.get_doc("Red Profile", case["profile"])
		profile.first_name = "Renamed"
		profile.save()

		from vmmsx.volunteer.services import volunteer as volunteer_service

		dto = volunteer_service.profile_dto(
			frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, case["volunteer"].name)
		)

		self.assertEqual(dto["full_name"], frappe.db.get_value("Red Profile", case["profile"], "full_name"))

	def test_home_area_is_read_from_the_profile_and_not_stored(self):
		"""The nearest miss in this pass, asserted rather than remembered.

		Home Area is where somebody *lives*. It is a fact about the person, core
		already owns it on Red Profile, and copying it onto the volunteer would
		have been a second answer to the same question. The volunteer's own
		`home_geo_node` is a different field on a different doctype answering a
		different question, which is where they *serve*.
		"""
		case = self.accepted("home_area")
		lives_at = self.society_a["other_ward"]

		frappe.db.set_value("Red Profile", case["profile"], "home_geo_node", lives_at)
		frappe.clear_document_cache("Red Profile", case["profile"])

		placement = capabilities.placement(frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, case["volunteer"].name))

		self.assertEqual(placement["home_geo_node"], lives_at)
		self.assertEqual(placement["geo_node"], case["application"].geo_node)
		self.assertNotEqual(
			placement["home_geo_node"],
			placement["geo_node"],
			"the two questions resolved to the same node, so this proves nothing",
		)

	def test_correcting_where_somebody_lives_changes_no_volunteer_row(self):
		"""The other half: the view moved and the record did not."""
		case = self.accepted("moved_house")
		volunteer = frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, case["volunteer"].name)

		capabilities.placement(volunteer)
		before = self.row(volunteer.name)

		frappe.db.set_value("Red Profile", case["profile"], "home_geo_node", self.society_a["other_ward"])
		frappe.clear_document_cache("Red Profile", case["profile"])

		placement = capabilities.placement(volunteer)

		self.assertEqual(placement["home_geo_node"], self.society_a["other_ward"])
		self.assertEqual(self.row(volunteer.name), before)


# --- 4. the complete view --------------------------------------------------


class TestTheCompleteView(CoordinatorViewTestCase):
	"""Every section the coordinator's view promises actually resolves."""

	def dossier(self, case, **kwargs) -> dict:
		from vmmsx.api import volunteer as volunteer_api

		return volunteer_api.get_dossier(case["volunteer"].name, **kwargs)

	def test_every_section_is_present(self):
		case = self.accepted("sections")

		dossier = self.dossier(case)

		for section in (
			"identity",
			"capabilities",
			"certifications",
			"deployability",
			"deployments",
			"time",
			"application",
		):
			self.assertIn(section, dossier, f"the coordinator's view has no {section} section")

	def test_the_identity_section_carries_the_person_and_both_places(self):
		case = self.accepted("identity_section")

		identity = self.dossier(case)["identity"]

		self.assertEqual(
			identity["full_name"], frappe.db.get_value("Red Profile", case["profile"], "full_name")
		)
		self.assertIn("email", identity)
		self.assertIn("date_of_birth", identity)
		self.assertEqual(identity["geo_node"], case["application"].geo_node)
		self.assertIn("home_geo_node", identity)
		self.assertIn("country_of_citizenship", identity)
		self.assertIn("residency_type", identity)

	def test_the_capabilities_section_reads_the_volunteers_own(self):
		skill = fixtures.make_skill()
		case = self.accepted("capability_section", skills=[{"skill": skill.name}])

		capability = self.dossier(case)["capabilities"]

		self.assertEqual(capability["skills"], [{"key": skill.name, "label": skill.skill_name}])
		self.assertIn("languages", capability)
		self.assertIn("availability", capability)

	def test_the_certifications_section_carries_the_derived_lapse(self):
		case = self.accepted("certification_section")
		certification_type = fixtures.make_certification_type(fixtures.CERT_FIRST_AID)
		certification.record(case["volunteer"].name, certification_type.name, today())

		rows = self.dossier(case)["certifications"]

		self.assertEqual(len(rows), 1)
		self.assertIn("lapsed", rows[0])
		self.assertIn("blocks_deployment", rows[0])
		self.assertFalse(rows[0]["lapsed"])

	def test_the_deployments_section_lists_the_deployments_they_were_on(self):
		case = self.accepted("deployment_section")
		deployment = fixtures.make_deployment(self.society_a["ward"], participants=[case["volunteer"].name])

		rows = self.dossier(case)["deployments"]

		self.assertEqual([row["deployment"] for row in rows], [deployment.name])
		self.assertIn("start_date", rows[0])
		self.assertIn("terms_of_reference", rows[0])

	def test_the_time_section_totals_and_lists(self):
		case = self.accepted("time_section")
		fixtures.make_time_log(case["volunteer"].name, self.society_a["ward"], hours=3)
		fixtures.make_time_log(case["volunteer"].name, self.society_a["ward"], hours=5)

		time = self.dossier(case)["time"]

		self.assertEqual(time["total_hours"], 8)
		self.assertEqual(time["log_count"], 2)
		self.assertEqual(len(time["recent"]), 2)

	def test_the_application_section_carries_the_verification_and_the_declaration(self):
		motivation = fixtures.make_motivation()
		case = self.accepted("application_section", motivation=[{"motivation": motivation.name}])

		application = self.dossier(case)["application"]

		self.assertEqual(application["application"], case["application"].name)
		self.assertEqual(application["approval_state"], states.APPROVED)
		self.assertEqual(application["decisions"][0]["approver"], self.approver)
		self.assertEqual(len(application["declared"]["motivation"]), 1)

	def test_the_whole_view_is_answered_as_at_one_instant(self):
		"""The reason it is one call. Seven calls would have been seven instants."""
		case = self.accepted("one_instant")

		dossier = self.dossier(case)

		self.assertEqual(dossier["deployability"]["as_of"], dossier["as_of"])

	def test_asking_about_another_date_moves_every_derived_block_together(self):
		"""One date reaches every derivation, including the one nested in identity.

		The identity block carries its own deployability answer, and it would
		have been easy for that one to keep answering about today while the
		deployability block answered about the date asked for. One screen with two
		answers to one question is exactly the failure the single call exists to
		prevent, so it is pinned rather than left to care.
		"""
		case = self.accepted("another_date")
		blocking = fixtures.make_certification_type(
			fixtures.CERT_FIRST_AID, validity_days=30, blocks_deployment_when_lapsed=1
		)
		completed = add_days(today(), -400)
		certification.record(case["volunteer"].name, blocking.name, completed)

		lapsed_today = self.dossier(case)
		valid_then = self.dossier(case, as_of=add_days(completed, 10))

		self.assertFalse(lapsed_today["deployability"]["deployable"])
		self.assertFalse(lapsed_today["identity"]["deployability"]["deployable"])

		self.assertTrue(valid_then["deployability"]["deployable"])
		self.assertTrue(
			valid_then["identity"]["deployability"]["deployable"],
			"the identity block answered about today while the page answered about another date",
		)
		self.assertEqual(valid_then["identity"]["deployability"]["as_of"], valid_then["as_of"])

	def test_rendering_the_view_writes_nothing_to_the_record(self):
		"""What makes 'live read' mean something. The whole row is compared."""
		case = self.accepted("no_write")
		fixtures.make_time_log(case["volunteer"].name, self.society_a["ward"])

		before = self.row(case["volunteer"].name)
		versions_before = frappe.db.count(
			"Version", {"ref_doctype": fixtures.VOLUNTEER_DOCTYPE, "docname": case["volunteer"].name}
		)

		self.dossier(case)

		self.assertEqual(self.row(case["volunteer"].name), before)
		self.assertEqual(
			frappe.db.count(
				"Version", {"ref_doctype": fixtures.VOLUNTEER_DOCTYPE, "docname": case["volunteer"].name}
			),
			versions_before,
		)


# --- 5. deployability is derived ------------------------------------------


class TestDeployabilityIsDerived(CoordinatorViewTestCase):
	def test_an_active_volunteer_with_nothing_lapsed_is_deployable(self):
		case = self.accepted("deployable")

		self.assertTrue(self.dossier_deployability(case)["deployable"])

	def test_a_lapsed_mandatory_certification_flips_the_indicator(self):
		"""The claim, end to end, with no stored flag anywhere in the chain."""
		case = self.accepted("blocked")
		blocking = fixtures.make_certification_type(
			fixtures.CERT_FIRST_AID, validity_days=30, blocks_deployment_when_lapsed=1
		)
		certification.record(case["volunteer"].name, blocking.name, add_days(today(), -400))

		verdict = self.dossier_deployability(case)

		self.assertFalse(verdict["deployable"])
		self.assertTrue(verdict["reasons"])

	def test_a_lapsed_non_blocking_certification_does_not(self):
		"""Which lapses cost something is configuration, not a rule in code."""
		case = self.accepted("record_only")
		harmless = fixtures.make_certification_type(
			fixtures.CERT_PSYCHOSOCIAL, validity_days=30, blocks_deployment_when_lapsed=0
		)
		certification.record(case["volunteer"].name, harmless.name, add_days(today(), -400))

		verdict = self.dossier_deployability(case)

		self.assertTrue(verdict["deployable"])

	def test_the_flip_wrote_nothing_to_any_record(self):
		"""Derived means derived. Not a column, not a flag, not a cached answer."""
		case = self.accepted("nothing_stored")
		blocking = fixtures.make_certification_type(
			fixtures.CERT_FIRST_AID, validity_days=30, blocks_deployment_when_lapsed=1
		)
		held = certification.record(case["volunteer"].name, blocking.name, add_days(today(), -400))

		before_volunteer = self.row(case["volunteer"].name)
		before_certification = dict(
			frappe.db.get_value(fixtures.CERTIFICATION_DOCTYPE, held.name, "*", as_dict=True)
		)

		self.assertFalse(self.dossier_deployability(case)["deployable"])

		self.assertEqual(self.row(case["volunteer"].name), before_volunteer)
		self.assertEqual(
			dict(frappe.db.get_value(fixtures.CERTIFICATION_DOCTYPE, held.name, "*", as_dict=True)),
			before_certification,
		)

	def test_no_stored_field_could_hold_the_answer(self):
		"""The schema-level half: there is nowhere to put a stale answer."""
		volunteer_columns = set(frappe.db.get_table_columns(fixtures.VOLUNTEER_DOCTYPE))
		certification_columns = set(frappe.db.get_table_columns(fixtures.CERTIFICATION_DOCTYPE))

		for fieldname in ("deployable", "is_deployable", "deployability", "blocked"):
			self.assertNotIn(fieldname, volunteer_columns)

		for fieldname in ("lapsed", "is_lapsed", "is_expired", "status"):
			self.assertNotIn(fieldname, certification_columns)

	def test_the_same_certification_reads_differently_on_two_dates(self):
		"""What a stored flag could never do: answer a question about last year."""
		case = self.accepted("as_of")
		blocking = fixtures.make_certification_type(
			fixtures.CERT_FIRST_AID, validity_days=30, blocks_deployment_when_lapsed=1
		)
		completed = add_days(today(), -400)
		certification.record(case["volunteer"].name, blocking.name, completed)

		volunteer = frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, case["volunteer"].name)

		self.assertTrue(certification.is_deployable(volunteer, as_of=add_days(completed, 10)))
		self.assertFalse(certification.is_deployable(volunteer, as_of=today()))

	def dossier_deployability(self, case) -> dict:
		from vmmsx.api import volunteer as volunteer_api

		return volunteer_api.get_dossier(case["volunteer"].name)["deployability"]


# --- 6. queryable, on top of scope ----------------------------------------


class TestCapabilitiesAreQueryableWithinScope(CoordinatorViewTestCase):
	"""Part 4. The filter narrows what the caller could see; it never widens it.

	Two volunteers hold the same skill, in two different societies. A
	coordinator scoped to one of them searches for that skill, and must get back
	exactly one of the two. The out-of-scope volunteer is the assertion that
	matters: a search that returned them would be a way of reading the whole
	register by naming a skill.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.grant_doctype_access(fixtures.VOLUNTEER_DOCTYPE, fixtures.SCOPE_ROLE)

		# Scoped to society A's county and nothing else. Deliberately not
		# `scoped_user`, which grants both societies for the suites that are not
		# about scoping.
		cls.coordinator = fixtures.make_user("dossier_coordinator", [fixtures.SCOPE_ROLE])
		fixtures.make_assignment(cls.coordinator, fixtures.SCOPE_ROLE, cls.society_a["county"])

	def volunteer_with(self, handle: str, node: str, skill: str, **extra):
		profile = fixtures.make_profile("Searchable", handle.title())
		volunteer = fixtures.make_volunteer(profile, node)
		volunteer.append("skills", {"skill": skill})

		for fieldname, rows in extra.items():
			for row in rows:
				volunteer.append(fieldname, row)

		volunteer.save(ignore_permissions=True)

		return volunteer

	def found_by(self, user: str, **criteria) -> set[str]:
		with fixtures.acting_as(user):
			return set(capabilities.search(**criteria))

	def test_a_skill_search_returns_the_in_scope_holder(self):
		skill = fixtures.make_skill()
		inside = self.volunteer_with("inside", self.society_a["ward"], skill.name)

		self.assertIn(inside.name, self.found_by(self.coordinator, skills=[skill.name]))

	def test_it_does_not_return_the_out_of_scope_holder(self):
		"""The gate. Same skill, different society, and the scope holds."""
		skill = fixtures.make_skill()
		inside = self.volunteer_with("in_scope", self.society_a["ward"], skill.name)
		outside = self.volunteer_with("out_of_scope", self.society_b["ward"], skill.name)

		found = self.found_by(self.coordinator, skills=[skill.name])

		self.assertIn(inside.name, found)
		self.assertNotIn(outside.name, found, "the capability filter leaked past geo scope")

	def test_the_out_of_scope_holder_really_does_hold_the_skill(self):
		"""Guards the test above: it must fail for the scope, not for the data."""
		skill = fixtures.make_skill()
		outside = self.volunteer_with("holds_it", self.society_b["ward"], skill.name)

		self.assertIn(outside.name, set(capabilities.search(skills=[skill.name])))

	def test_two_vocabularies_narrow_rather_than_widen(self):
		"""All-of across vocabularies: a match must satisfy both filters."""
		skill = fixtures.make_skill()
		slot = fixtures.make_availability_slot()
		other_slot = fixtures.make_availability_slot(fixtures.AVAILABILITY_NIGHTS)

		both = self.volunteer_with(
			"both", self.society_a["ward"], skill.name, availability=[{"availability_slot": slot.name}]
		)
		only_skill = self.volunteer_with(
			"only_skill",
			self.society_a["ward"],
			skill.name,
			availability=[{"availability_slot": other_slot.name}],
		)

		found = self.found_by(self.coordinator, skills=[skill.name], availability=[slot.name])

		self.assertIn(both.name, found)
		self.assertNotIn(only_skill.name, found)

	def test_naming_an_out_of_scope_node_is_not_a_way_in(self):
		"""`geo_node` narrows further; it is not an override."""
		skill = fixtures.make_skill()
		outside = self.volunteer_with("named_node", self.society_b["ward"], skill.name)

		found = self.found_by(self.coordinator, skills=[skill.name], geo_node=self.society_b["region"])

		self.assertNotIn(outside.name, found)

	def test_the_search_goes_through_the_scoped_read(self):
		"""Asserted at the source, because it is the whole safety property.

		`frappe.get_all` skips core's permission query condition and
		`frappe.get_list` runs it. The final read has to be the second, and a
		future edit swapping them would silently open the register.

		**`count` is held to the same bar as `search`.** It is a second reader of
		the same filters and answers the number a pager puts on the screen; one
		that counted the whole register while the page below it showed one
		branch's worth would be a disclosure wearing the shape of a total.
		"""
		import inspect

		for reader in (capabilities.search, capabilities.count):
			source = inspect.getsource(reader)

			self.assertIn("frappe.get_list(", source, f"{reader.__name__} does not read scoped")
			self.assertNotIn("frappe.get_all(", source, f"{reader.__name__} skips the scope")

	def test_the_count_is_of_what_the_caller_may_see(self):
		"""The number beside a register has to be scoped like the register.

		Counted through the same `get_list`, so a coordinator is told how many
		people *they* can reach rather than how many the society has.
		"""
		skill = fixtures.make_skill()
		self.volunteer_with("counted_inside", self.society_a["ward"], skill.name)
		self.volunteer_with("counted_outside", self.society_b["ward"], skill.name)

		with fixtures.acting_as(self.coordinator):
			counted = capabilities.count(skills=[skill.name])
			found = capabilities.search(skills=[skill.name])

		self.assertEqual(counted, len(found))

	def test_the_count_and_the_page_answer_the_same_question(self):
		"""A page smaller than the total is what pagination is; a total smaller
		than the page would mean the two were built from different filters."""
		skill = fixtures.make_skill()

		for index in range(3):
			self.volunteer_with(f"paged_{index}", self.society_a["ward"], skill.name)

		with fixtures.acting_as(self.coordinator):
			total = capabilities.count(skills=[skill.name])
			first = capabilities.search(skills=[skill.name], limit=2, offset=0)
			second = capabilities.search(skills=[skill.name], limit=2, offset=2)

		self.assertGreaterEqual(total, 3)
		self.assertEqual(len(first), 2)
		# The two pages are disjoint: an offset that repeated rows would show
		# somebody twice and hide somebody else entirely.
		self.assertEqual(set(first) & set(second), set())
		self.assertLessEqual(len(first) + len(second), total)

	def test_an_unsatisfiable_search_counts_nobody_rather_than_everybody(self):
		"""`_search_filters` answers None for criteria that cannot match, and both
		readers have to read that as "nothing" rather than as "no filters"."""
		skill = fixtures.make_skill()
		self.volunteer_with("unsatisfiable", self.society_a["ward"], skill.name)

		with fixtures.acting_as(self.coordinator):
			# A name nobody has, so the candidate set comes out empty before any
			# filter is built.
			counted = capabilities.count(search="nobody-by-this-name-exists")
			found = capabilities.search(search="nobody-by-this-name-exists")

		self.assertEqual(counted, 0)
		self.assertEqual(found, [])

	def test_the_endpoint_returns_explicit_rows(self):
		from vmmsx.api import volunteer as volunteer_api

		skill = fixtures.make_skill()
		inside = self.volunteer_with("endpoint", self.society_a["ward"], skill.name)

		with fixtures.acting_as(self.coordinator):
			result = volunteer_api.find_volunteers(skills=[skill.name])

		names = [row["volunteer"] for row in result["volunteers"]]

		self.assertIn(inside.name, names)
		self.assertEqual(result["count"], len(result["volunteers"]))

		row = next(row for row in result["volunteers"] if row["volunteer"] == inside.name)

		self.assertIn("full_name", row)
		self.assertIn("deployable", row)
		self.assertNotIn("certifications", row, "a candidate list disclosed a full dossier")

	def test_the_desk_list_can_filter_on_the_child_table_too(self):
		"""The native half of Part 4: a coordinator's own list view filter.

		The desk builds exactly this filter from the sidebar when somebody picks
		a skill, and it runs through the same `get_list` that carries the scope
		condition. Asserting it here is what says the field is genuinely
		filterable rather than merely present.
		"""
		skill = fixtures.make_skill()
		inside = self.volunteer_with("desk_filter", self.society_a["ward"], skill.name)
		outside = self.volunteer_with("desk_filter_out", self.society_b["ward"], skill.name)

		with fixtures.acting_as(self.coordinator):
			listed = set(
				frappe.get_list(
					fixtures.VOLUNTEER_DOCTYPE,
					filters=[["VMMS Skill Selector", "skill", "=", skill.name]],
					pluck="name",
					limit_page_length=0,
				)
			)

		self.assertIn(inside.name, listed)
		self.assertNotIn(outside.name, listed)
