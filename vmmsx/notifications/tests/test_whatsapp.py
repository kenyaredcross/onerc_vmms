# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The WhatsApp channel: who it can reach, what it files, and what it sends.

Four properties, and each of them is a failure this channel would otherwise have
by construction:

1. **A number is only a WhatsApp address if it was written with a country code.**
   The same rule the SMS channel applies, applied here for the same reason: the
   way to resolve `0712345678` is to ask the person, not to assume the society's
   own country and write to a stranger.

2. **Somebody who asked to be left alone is left alone — twice.** Once when the
   broadcast is composed, so the figure an approver reads is honest, and again
   when it is sent, so a person who replies STOP on Thursday is not written to
   on Friday by a broadcast approved on Wednesday.

3. **Nothing is sent by composing, and nothing is sent by approving.** The
   console files a draft, submitting queues a job, and only the job writes to
   anybody. A screen that said "sent" for either of the first two would be
   telling a branch something untrue about four thousand people.

4. **A half-finished broadcast finishes where it stopped.** Every recipient is a
   row with its own status and the job only picks up the ones still pending, so
   a worker that died at nine hundred does not start again at one.

The gateway itself is the one thing stubbed. Everything else is real: geo comes
from core's fixtures, the audience is the real resolver, and the broadcast is
the real document going through its real submit.
"""

from unittest.mock import patch

import frappe

from vmmsx.api import communication
from vmmsx.api import whatsapp as whatsapp_api
from vmmsx.notifications.services import whatsapp
from vmmsx.notifications.tests.test_communication import CommunicationFixture

EXTRA_TEST_RECORD_DEPENDENCIES = []


class WhatsAppFixture(CommunicationFixture):
	"""The communication suite's arrangement, plus a configured gateway."""

	def setUp(self):
		super().setUp()

		self.configure()

	def configure(self, **overrides) -> None:
		"""A gateway that exists on paper. No call is made to set this up."""
		config = frappe.get_doc(whatsapp.SETTINGS_DOCTYPE)
		config.enabled = 1
		config.gateway_url = "http://gateway.invalid:2785"
		config.session_id = "test-session"
		config.api_key = "test-key"
		# Zero, so a suite that walks a hundred recipients does not take five
		# minutes proving something about pacing that one test asserts directly.
		config.pacing_seconds = 0
		config.daily_limit = 0
		config.opt_out_notice = "Reply STOP to stop receiving messages from us."
		config.opt_out_keywords = "STOP\nUNSUBSCRIBE"

		for field, value in overrides.items():
			setattr(config, field, value)

		config.save(ignore_permissions=True)
		frappe.clear_document_cache(whatsapp.SETTINGS_DOCTYPE, whatsapp.SETTINGS_DOCTYPE)

	def with_number(self, handle: str, number: str) -> str:
		"""A volunteer at the branch carrying one phone number."""
		self.make_volunteer(handle, self.branch)
		profile = frappe.db.get_value("Red Profile", {"first_name": handle}, "name")
		frappe.db.set_value("Red Profile", profile, "phone", number)

		return profile

	def stop(self, number: str) -> None:
		whatsapp.record_opt_out(number, source=whatsapp.OPT_OUT_STAFF)


class TestANumberBecomesAnAddress(WhatsAppFixture):
	def test_a_number_with_a_country_code_becomes_a_chat_address(self):
		self.assertEqual(whatsapp.chat_id("+255712345678"), "255712345678@c.us")

	def test_the_way_a_person_writes_it_does_not_matter(self):
		"""Spaces, dashes and brackets are how humans write numbers down."""
		self.assertEqual(whatsapp.chat_id("+255 (712) 345-678"), "255712345678@c.us")

	def test_a_number_without_a_country_code_is_not_an_address(self):
		"""The rule that stops this app guessing a country on somebody's behalf."""
		self.assertIsNone(whatsapp.chat_id("0712345678"))

	def test_a_short_code_is_not_an_address(self):
		self.assertIsNone(whatsapp.chat_id("+1234"))

	def test_nothing_is_not_an_address(self):
		self.assertIsNone(whatsapp.chat_id(""))
		self.assertIsNone(whatsapp.chat_id(None))


class TestTheReachExcludesPeopleWhoAskedToBeLeftAlone(WhatsAppFixture):
	def test_the_channel_is_counted_separately_from_sms(self):
		"""Two people with numbers, one of whom has opted out.

		SMS reaches both, because opting out of WhatsApp is not opting out of
		everything, and a channel that leaked its own opt-out list into another
		one would be answering a question nobody asked it.
		"""
		self.with_number("reachable", "+255700000011")
		self.with_number("stopped", "+255700000012")
		self.stop("+255700000012")

		reach = communication.preview(self.branch, "volunteers")

		self.assertEqual(reach["addressed"], 2)
		self.assertEqual(reach["sms"], 2)
		self.assertEqual(reach["whatsapp"], 1)

	def test_the_gap_is_reported_as_a_choice_rather_than_as_missing_data(self):
		"""`unreachable` and `opted_out` are different facts about a branch.

		One is a data-collection problem a coordinator can act on. The other is
		people who answered, and nobody should go chasing them for a number they
		have already given.
		"""
		self.with_number("has-a-number", "+255700000013")
		self.with_number("stopped", "+255700000014")
		self.stop("+255700000014")
		self.make_volunteer("no-number", self.branch)

		counts = whatsapp.reachable(self.branch, "volunteers")

		self.assertEqual(counts["addressed"], 3)
		self.assertEqual(counts["reachable"], 1)
		self.assertEqual(counts["unreachable"], 1)
		self.assertEqual(counts["opted_out"], 1)

	def test_asking_twice_records_one_refusal(self):
		self.assertTrue(whatsapp.record_opt_out("+255700000015"))
		self.assertFalse(whatsapp.record_opt_out("+255700000015"))
		self.assertEqual(frappe.db.count(whatsapp.OPT_OUT_DOCTYPE, {"phone_number": "+255700000015"}), 1)

	def test_a_number_written_two_ways_is_one_refusal(self):
		"""The whole reason opt-outs are compared as chat addresses.

		A person recorded as `+255 700 000 016` and a broadcast resolving
		`+255700000016` are the same human being, and a channel that could not
		see that would keep writing to somebody who had asked it to stop.
		"""
		self.with_number("spaced", "+255700000016")
		self.stop("+255 700 000 016")

		self.assertEqual(whatsapp.reachable(self.branch, "volunteers")["reachable"], 0)


class TestComposingFilesAndSendsNothing(WhatsAppFixture):
	def test_the_console_files_a_draft_and_texts_nobody(self):
		self.with_number("recipient", "+255700000021")

		with patch.object(whatsapp, "_request") as gateway:
			report = communication.send(
				title="Flood advisory",
				body="The river is rising.",
				geo_node=self.branch,
				who="volunteers",
				channels=["whatsapp"],
				whatsapp_message="The river is rising. Stay off the bridge.",
			)

		gateway.assert_not_called()

		broadcast = frappe.get_doc(whatsapp.BROADCAST_DOCTYPE, report["whatsapp"]["broadcast"])
		self.assertEqual(broadcast.docstatus, 0, "a filed broadcast is not an approved one")
		self.assertEqual(broadcast.status, whatsapp.STATUS_DRAFT)
		self.assertEqual(len(broadcast.recipients), 1)
		self.assertEqual(broadcast.recipients[0].chat_id, "255700000021@c.us")
		self.assertEqual(broadcast.recipients[0].delivery_status, whatsapp.RECIPIENT_PENDING)

	def test_the_wording_is_its_own_and_not_the_announcements(self):
		"""A WhatsApp message reads differently from a notice, so it is written
		separately. The announcement's body is only a fallback."""
		self.with_number("recipient", "+255700000022")

		report = communication.send(
			title="Flood advisory",
			body="A formal notice, in the register of a circular.",
			geo_node=self.branch,
			who="volunteers",
			channels=["whatsapp"],
			whatsapp_message="River's up — stay off the bridge today.",
		)

		broadcast = frappe.get_doc(whatsapp.BROADCAST_DOCTYPE, report["whatsapp"]["broadcast"])
		self.assertEqual(broadcast.message, "River's up — stay off the bridge today.")

	def test_the_announcement_and_the_broadcast_are_two_separate_records(self):
		"""Choosing both channels is one act and two documents, and the WhatsApp
		one is still unsent when the announcement has already been published."""
		self.with_number("recipient", "+255700000023")

		report = communication.send(
			title="Flood advisory",
			body="The river is rising.",
			geo_node=self.branch,
			who="volunteers",
			channels=["notification", "whatsapp"],
		)

		self.assertIsNotNone(report["announcement"])
		self.assertIsNotNone(report["whatsapp"])
		self.assertEqual(
			frappe.db.get_value(whatsapp.BROADCAST_DOCTYPE, report["whatsapp"]["broadcast"], "docstatus"),
			0,
		)

	def test_an_audience_nobody_in_it_can_be_reached_is_refused_rather_than_filed(self):
		"""An empty broadcast is a mistake to catch now, not a document to
		explain later."""
		self.make_volunteer("no-number", self.branch)

		with self.assertRaises(frappe.ValidationError):
			communication.send(
				title="Nobody",
				body="Nobody is reachable here.",
				geo_node=self.branch,
				who="volunteers",
				channels=["whatsapp"],
			)

	def test_a_channel_this_society_does_not_have_is_still_refused(self):
		"""The closed set gained a member; it did not stop being closed."""
		with self.assertRaises(frappe.ValidationError):
			communication.send(
				title="Nowhere",
				body="…",
				geo_node=self.branch,
				who="volunteers",
				channels=["telegram"],
			)


class TestApprovingQueuesRatherThanSends(WhatsAppFixture):
	def file_one(self, number: str = "+255700000031") -> str:
		self.with_number("recipient", number)

		return communication.send(
			title="Advisory",
			body="Something happened.",
			geo_node=self.branch,
			who="volunteers",
			channels=["whatsapp"],
		)["whatsapp"]["broadcast"]

	def test_submitting_queues_the_work_and_does_not_do_it(self):
		"""The property that stops a branch of four thousand from being sent
		inside the request that approved it."""
		name = self.file_one()

		with patch.object(whatsapp.frappe, "enqueue") as queued:
			frappe.get_doc(whatsapp.BROADCAST_DOCTYPE, name).submit()

		queued.assert_called_once()
		self.assertEqual(queued.call_args.kwargs["broadcast"], name)
		self.assertEqual(queued.call_args.kwargs["queue"], "long")

	def test_one_broadcast_is_one_job_however_often_it_is_released(self):
		"""Two workers on one list of people would write to everybody twice."""
		name = self.file_one()

		with patch.object(whatsapp.frappe, "enqueue") as queued:
			whatsapp.release(name)
			whatsapp.release(name)

		self.assertTrue(queued.call_args.kwargs["deduplicate"])
		self.assertEqual(
			{call.kwargs["job_id"] for call in queued.call_args_list},
			{f"vmmsx-whatsapp-{name}"},
			"both releases name the same job",
		)

	def test_a_broadcast_held_until_later_is_not_queued_yet(self):
		name = self.file_one()
		frappe.db.set_value(whatsapp.BROADCAST_DOCTYPE, name, "scheduled_at", frappe.utils.add_days(None, 3))

		with patch.object(whatsapp.frappe, "enqueue") as queued:
			frappe.get_doc(whatsapp.BROADCAST_DOCTYPE, name).submit()

		queued.assert_not_called()
		self.assertEqual(
			frappe.db.get_value(whatsapp.BROADCAST_DOCTYPE, name, "status"),
			whatsapp.STATUS_SCHEDULED,
		)

	def test_the_sweep_releases_one_whose_time_has_come(self):
		name = self.file_one()
		frappe.db.set_value(whatsapp.BROADCAST_DOCTYPE, name, "scheduled_at", frappe.utils.add_days(None, 3))

		with patch.object(whatsapp.frappe, "enqueue"):
			frappe.get_doc(whatsapp.BROADCAST_DOCTYPE, name).submit()

		frappe.db.set_value(whatsapp.BROADCAST_DOCTYPE, name, "scheduled_at", frappe.utils.add_days(None, -1))

		with patch.object(whatsapp.frappe, "enqueue") as queued:
			released = whatsapp.release_scheduled()

		self.assertEqual(released, 1)
		queued.assert_called_once()


class TestTheSendingItself(WhatsAppFixture):
	"""The job that actually writes to people.

	`frappe.db.commit` is stubbed throughout this class. In production the
	per-recipient commit is the whole of the resumability guarantee — a worker
	killed mid-broadcast has still recorded who it reached — and in a test it
	would commit the suite's own fixtures past the rollback that separates one
	test from the next. The behaviour under test is what gets written, not when
	it is durable.
	"""

	def setUp(self):
		super().setUp()

		commit = patch.object(frappe.db, "commit")
		commit.start()
		self.addCleanup(commit.stop)

	def approve(self, numbers: list[str]) -> str:
		"""File a broadcast to these numbers and approve it, queueing nothing."""
		for index, number in enumerate(numbers):
			self.with_number(f"person-{index}", number)

		name = communication.send(
			title="Advisory",
			body="The river is rising.",
			geo_node=self.branch,
			who="volunteers",
			channels=["whatsapp"],
			whatsapp_message="The river is rising.",
		)["whatsapp"]["broadcast"]

		with patch.object(whatsapp.frappe, "enqueue"):
			frappe.get_doc(whatsapp.BROADCAST_DOCTYPE, name).submit()

		return name

	def run_job(self, name: str, answer=(True, {"messageId": "wamid.1"}, "")):
		"""Run the send with a stubbed gateway. Returns the patched call."""
		connected = {"connected": True, "status": "ready", "reason": ""}

		with (
			patch.object(whatsapp, "session_state", return_value=connected),
			patch.object(whatsapp, "_request", return_value=answer) as gateway,
		):
			whatsapp.send(name)

		return gateway

	def sent_today(self) -> int:
		"""What the daily cap has already seen, by the same count the code makes."""
		return frappe.db.count(
			whatsapp.RECIPIENT_DOCTYPE,
			{
				"parenttype": whatsapp.BROADCAST_DOCTYPE,
				"delivery_status": whatsapp.RECIPIENT_SENT,
				"sent_on": [">=", frappe.utils.today()],
			},
		)

	def rows(self, name: str) -> list[dict]:
		return frappe.get_all(
			whatsapp.RECIPIENT_DOCTYPE,
			filters={"parent": name},
			fields=["phone", "delivery_status", "error"],
			order_by="phone asc",
			ignore_permissions=True,
		)

	def test_every_recipient_is_written_to_once_and_the_outcome_recorded(self):
		name = self.approve(["+255700000041", "+255700000042"])

		gateway = self.run_job(name)

		self.assertEqual(gateway.call_count, 2)
		self.assertEqual(
			[row["delivery_status"] for row in self.rows(name)],
			[whatsapp.RECIPIENT_SENT, whatsapp.RECIPIENT_SENT],
		)
		broadcast = frappe.get_doc(whatsapp.BROADCAST_DOCTYPE, name)
		self.assertEqual(broadcast.status, whatsapp.STATUS_SENT)
		self.assertEqual(broadcast.total_sent, 2)

	def test_the_opt_out_line_is_part_of_what_is_actually_sent(self):
		"""Appended by the server, so it cannot be forgotten on the one message
		somebody sends in a hurry."""
		name = self.approve(["+255700000043"])

		gateway = self.run_job(name)

		text = gateway.call_args.args[2]["text"]
		self.assertIn("The river is rising.", text)
		self.assertIn("Reply STOP", text)

	def test_somebody_who_opted_out_after_approval_is_not_written_to(self):
		"""The second subtraction, and the reason there are two.

		The approver saw two recipients and approved two. One of them asked to
		be left alone before the job ran, and the approved figure stays a ceiling
		rather than a promise.
		"""
		name = self.approve(["+255700000044", "+255700000045"])
		self.stop("+255700000045")

		gateway = self.run_job(name)

		self.assertEqual(gateway.call_count, 1)
		statuses = {row["phone"]: row["delivery_status"] for row in self.rows(name)}
		self.assertEqual(statuses["+255700000044"], whatsapp.RECIPIENT_SENT)
		self.assertEqual(statuses["+255700000045"], whatsapp.RECIPIENT_SKIPPED)

	def test_a_broadcast_carries_on_from_where_it_stopped(self):
		"""A worker that died at nine hundred does not start again at one."""
		name = self.approve(["+255700000046", "+255700000047"])
		already = frappe.get_all(
			whatsapp.RECIPIENT_DOCTYPE,
			filters={"parent": name, "phone": "+255700000046"},
			pluck="name",
			ignore_permissions=True,
		)[0]
		frappe.db.set_value(whatsapp.RECIPIENT_DOCTYPE, already, "delivery_status", whatsapp.RECIPIENT_SENT)

		gateway = self.run_job(name)

		self.assertEqual(gateway.call_count, 1, "the recipient already written to is left alone")
		self.assertEqual(gateway.call_args.args[2]["chatId"], "255700000047@c.us")

	def test_a_refusal_is_recorded_against_the_person_it_happened_to(self):
		"""One failure is one row, not a broadcast nobody can account for."""
		name = self.approve(["+255700000048"])

		self.run_job(name, answer=(False, {}, "The gateway refused the message (403)."))

		row = self.rows(name)[0]
		self.assertEqual(row["delivery_status"], whatsapp.RECIPIENT_FAILED)
		self.assertIn("403", row["error"])
		self.assertEqual(
			frappe.db.get_value(whatsapp.BROADCAST_DOCTYPE, name, "status"), whatsapp.STATUS_FAILED
		)

	def test_a_gateway_that_is_not_connected_writes_to_nobody(self):
		"""Asked once, before the loop, rather than discovered four thousand
		identical failures later."""
		name = self.approve(["+255700000049"])
		down = {"connected": False, "status": "disconnected", "reason": "The link dropped."}

		with (
			patch.object(whatsapp, "session_state", return_value=down),
			patch.object(whatsapp, "_request") as gateway,
		):
			whatsapp.send(name)

		gateway.assert_not_called()
		self.assertEqual(self.rows(name)[0]["delivery_status"], whatsapp.RECIPIENT_PENDING)
		self.assertEqual(
			frappe.db.get_value(whatsapp.BROADCAST_DOCTYPE, name, "status"), whatsapp.STATUS_FAILED
		)

	def test_a_cancelled_broadcast_is_not_sent_by_a_worker_that_had_already_started(self):
		name = self.approve(["+255700000050"])
		frappe.get_doc(whatsapp.BROADCAST_DOCTYPE, name).cancel()

		with patch.object(whatsapp, "_request") as gateway:
			whatsapp.send(name)

		gateway.assert_not_called()

	def test_the_daily_limit_stops_rather_than_fails_the_rest(self):
		"""The people who were never tried stay pending, so the remainder goes
		out when the cap resets. Marking them failed would lose them.

		The limit is set relative to what today has already carried rather than
		to a literal 1. This class rolls back once at the end rather than between
		tests, so the rows earlier tests sent are still there and count against
		the same cap the code reads — which is correct behaviour and would make a
		fixed number mean something different depending on test order.
		"""
		self.configure(daily_limit=self.sent_today() + 1)
		name = self.approve(["+255700000051", "+255700000052"])

		gateway = self.run_job(name)

		self.assertEqual(gateway.call_count, 1)
		statuses = sorted(row["delivery_status"] for row in self.rows(name))
		self.assertEqual(statuses, [whatsapp.RECIPIENT_PENDING, whatsapp.RECIPIENT_SENT])
		self.assertEqual(
			frappe.db.get_value(whatsapp.BROADCAST_DOCTYPE, name, "status"),
			whatsapp.STATUS_PARTLY_SENT,
		)

	def test_a_broadcast_whose_whole_audience_had_left_is_finished_not_failed(self):
		"""Nothing went wrong: everybody had asked to be left alone. Marking it
		failed would send somebody looking for a fault that is not there."""
		name = self.approve(["+255700000053"])
		self.stop("+255700000053")

		gateway = self.run_job(name)

		gateway.assert_not_called()
		broadcast = frappe.get_doc(whatsapp.BROADCAST_DOCTYPE, name)
		self.assertEqual(broadcast.status, whatsapp.STATUS_SENT)
		self.assertEqual(broadcast.total_sent, 0)
		self.assertEqual(broadcast.total_skipped, 1)

	def test_the_sweep_comes_back_for_the_people_the_cap_stopped(self):
		"""The other half of the daily limit. Without this the cap would not
		delay those messages, it would quietly cancel them."""
		self.configure(daily_limit=self.sent_today() + 1)
		name = self.approve(["+255700000054", "+255700000055"])

		self.run_job(name)

		self.assertEqual(
			frappe.db.get_value(whatsapp.BROADCAST_DOCTYPE, name, "status"),
			whatsapp.STATUS_PARTLY_SENT,
		)

		with patch.object(whatsapp.frappe, "enqueue") as queued:
			whatsapp.release_scheduled()

		self.assertIn(name, [call.kwargs["broadcast"] for call in queued.call_args_list])

	def test_the_sweep_leaves_alone_a_broadcast_with_nobody_left_to_try(self):
		"""A remainder that failed is not a remainder that was never tried, and
		retrying it every quarter of an hour for ever is not a repair."""
		name = self.approve(["+255700000056", "+255700000057"])
		self.run_job(name, answer=(False, {}, "The gateway refused the message (403)."))
		frappe.db.set_value(whatsapp.BROADCAST_DOCTYPE, name, "status", whatsapp.STATUS_PARTLY_SENT)

		with patch.object(whatsapp.frappe, "enqueue") as queued:
			whatsapp.release_scheduled()

		self.assertNotIn(name, [call.kwargs["broadcast"] for call in queued.call_args_list])


class TestTheReplyThatTakesSomebodyOffTheList(WhatsAppFixture):
	"""The inbound webhook, which reads a reply for one word and drops the rest."""

	def inbound(self, sender: str, text: str, authentic: bool = True) -> dict:
		payload = {"event": whatsapp_api.EVENT_MESSAGE, "data": {"from": sender, "body": text}}

		with (
			patch.object(whatsapp_api, "_authentic", return_value=authentic),
			patch.object(whatsapp_api, "_body", return_value=payload),
		):
			return whatsapp_api.inbound()

	def test_a_reply_that_is_only_the_word_stop_takes_that_number_off(self):
		self.inbound("255700000061@c.us", "STOP")

		self.assertTrue(frappe.db.exists(whatsapp.OPT_OUT_DOCTYPE, {"phone_number": "+255700000061"}))

	def test_it_does_not_matter_how_they_capitalised_it(self):
		self.inbound("255700000062@c.us", "stop")

		self.assertTrue(frappe.db.exists(whatsapp.OPT_OUT_DOCTYPE, {"phone_number": "+255700000062"}))

	def test_a_sentence_containing_the_word_is_a_sentence(self):
		""" "Please stop the deployment on Tuesday" is somebody talking about
		work, and a substring match would remove them for saying so."""
		self.inbound("255700000063@c.us", "Please stop the deployment on Tuesday")

		self.assertFalse(frappe.db.exists(whatsapp.OPT_OUT_DOCTYPE, {"phone_number": "+255700000063"}))

	def test_a_society_can_add_the_word_its_own_volunteers_would_use(self):
		"""The keywords are configuration, not a constant in a source file."""
		self.configure(opt_out_keywords="STOP\nACHA")

		self.inbound("255700000064@c.us", "acha")

		self.assertTrue(frappe.db.exists(whatsapp.OPT_OUT_DOCTYPE, {"phone_number": "+255700000064"}))

	def test_a_group_has_no_one_person_to_take_off_a_list(self):
		self.inbound("255700000065-1234@g.us", "STOP")

		self.assertEqual(frappe.db.count(whatsapp.OPT_OUT_DOCTYPE, {"source": "Reply"}), 0)

	def test_a_call_without_the_token_changes_nothing(self):
		answer = self.inbound("255700000066@c.us", "STOP", authentic=False)

		self.assertFalse(answer["ok"])
		self.assertFalse(frappe.db.exists(whatsapp.OPT_OUT_DOCTYPE, {"phone_number": "+255700000066"}))

	def test_the_same_answer_whether_or_not_anything_happened(self):
		"""A webhook that reported which numbers are on the society's list would
		be a way to ask, one number at a time, who volunteers for the Red
		Cross."""
		removed = self.inbound("255700000067@c.us", "STOP")
		ignored = self.inbound("255700000068@c.us", "thanks!")

		self.assertEqual(removed, ignored)

	def test_a_site_with_no_token_set_refuses_every_call(self):
		"""A society that has not configured the webhook has not opened it."""
		self.configure(webhook_token="")

		with patch.object(frappe, "get_request_header", return_value="anything"):
			self.assertFalse(whatsapp_api._authentic())
