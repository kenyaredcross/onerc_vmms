import time
from dataclasses import dataclass
from datetime import datetime

import frappe
from frappe import _

from .user import get_user_info


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method -- public events listing, read-only
def get_events(search=None, event_type="upcoming") -> list[dict[str, any]]:
	user_info = get_user_info()

	fields = [
		"name",
		"title",
		"short_description",
		"start_date",
		"start_time",
		"venue",
		"banner_image",
		"event_access",
		"route",
	]

	if search:
		search_filters = {
			"venue": ["like", f"%{search}%"],
			"title": ["like", f"%{search}%"],
		}

	base_filters = {
		"is_published": 1,
	}
	if event_type == "upcoming":
		base_filters["end_date"] = [">=", datetime.now().date()]

	if user_info == "Guest":
		base_filters["event_access"] = ["in", ["Public", "Private"]]

	elif user_info.get("is_member"):
		pass
	elif user_info.get("is_volunteer"):
		base_filters["event_access"] = ["in", ["Public", "Private"]]

	events = frappe.get_all(
		"Buzz Event",
		fields=fields,
		filters=base_filters,
		or_filters=search_filters if search else None,
		order_by="start_date asc, start_time asc",
	)

	for event in events:
		event.short_description = (
			frappe.utils.strip_html_tags(event.short_description) if event.short_description else ""
		)

	return events


@dataclass
class EventRegistrationPayload:
	attendee: dict[str, any]
	event_name: str | int
	registration_responses: list[dict[str, any]]


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method -- public event registration flow
def register_event(payload: dict) -> None:
	payload_object = EventRegistrationPayload(**payload)
	attendee = payload_object.attendee
	event_name = payload_object.event_name
	registration_responses = payload_object.registration_responses

	processed_responses = process_multiselect_reponse(registration_responses)

	if not event_name or not frappe.db.exists("Buzz Event", event_name):
		frappe.throw("This event does not exist.")
	if not frappe.db.exists("Event Ticket Type", {"event": event_name}):
		frappe.throw("No ticket types available for this event.")

	event = frappe.db.get_value("Buzz Event", event_name, ["is_ticketed"], as_dict=True)
	if event and not event.is_ticketed:
		ticket = frappe.db.get_value("Event Ticket Type", {"event": event_name}, as_dict=True)

	try:
		event_booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": event_name,
				"primary_contact": attendee.get("email"),
				"attendees": [
					{
						"full_name": attendee.get("full_name"),
						"email": attendee.get("email"),
						"ticket_type": ticket.name,
					}
				],
				"responses": processed_responses,
			}
		)

		event_booking.insert(ignore_permissions=True)
		event_booking.submit()
		frappe.db.commit()

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Event Registration Error")
		frappe.throw("Event Registration Error")


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method -- public event detail, read-only
def get_event_details(event_name: str | int) -> dict:
	if not event_name:
		frappe.throw(_("This event does not exist."))

	name = frappe.db.get_value("Buzz Event", {"route": event_name, "is_published": 1}) or frappe.db.get_value(
		"Buzz Event", {"name": event_name, "is_published": 1}
	)
	if not name:
		frappe.throw(_("This event does not exist."))

	event = frappe.get_doc("Buzz Event", name).as_dict()
	event.update(frappe.db.get_value("Buzz Event", name, ["event_access", "is_ticketed"], as_dict=True) or {})
	validate_event_access(event.get("event_access"))

	event["about"] = frappe.utils.strip_html_tags(event["about"]) if event.get("about") else ""
	event["short_description"] = (
		frappe.utils.strip_html_tags(event["short_description"]) if event.get("short_description") else ""
	)

	if event.get("host"):
		host = frappe.get_doc("Event Host", event.host).as_dict()
		host["about"] = frappe.utils.strip_html_tags(host.get("about") or "")
		event["host"] = host

	event["tickets"] = frappe.get_all(
		"Event Ticket Type",
		filters={"event": name, "is_published": 1},
		fields=[
			"name",
			"title",
			"price",
			"currency",
			"ticket_type",
			"ticket_capacity",
			"max_tickets_available",
		],
		order_by="price asc",
	)

	event["event_registration_questions"] = frappe.get_all(
		"Event Registration Question",
		filters={"parent": name, "parenttype": "Buzz Event"},
		fields=["name", "question", "question_type", "options", "is_required", "help_text"],
		order_by="idx asc",
	)

	event["speakers"] = get_event_speakers(event)

	event["sponsors"] = frappe.get_all(
		"Event Sponsor",
		filters={"event": name},
		fields=["company_name", "company_logo", "website"],
	)

	event["is_past_event"] = bool(event.get("end_date")) and event["end_date"] < datetime.now().date()

	return event


def validate_event_access(event_access: str | None) -> None:
	"""Mirror the visibility rules get_events applies to the listing.

	Public and Private events are listed to everyone; Members Only events are
	restricted to members.
	"""
	if event_access != "Members Only":
		return

	user_info = get_user_info()
	if user_info == "Guest" or not user_info.get("is_member"):
		frappe.throw(_("This event is only open to members."), frappe.PermissionError)


def get_event_speakers(event: dict) -> list[dict[str, any]]:
	speaker_names = [row.speaker for row in event.get("featured_speakers") or [] if row.speaker]

	for sched in event.get("schedule") or []:
		if not sched.talk:
			continue
		talk = frappe.get_doc("Event Talk", sched.talk)
		speaker_names.extend([row.speaker for row in talk.speakers if row.speaker])

	speakers = []
	seen = set()
	for speaker_name in speaker_names:
		if speaker_name in seen:
			continue
		seen.add(speaker_name)
		speakers.append(frappe.get_doc("Speaker Profile", speaker_name).as_dict())

	return speakers


@dataclass
class TicketPaymentPayload:
	event_name: str | int
	ticket_name: str | int
	booking_details: list[dict[str, any]]
	registration_responses: list[dict[str, any]]


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method -- public ticket payment flow
def handle_ticket_payment(payload: dict) -> dict:
	if not payload:
		frappe.throw(_("Error processing ticket payment."))
	payload_object = TicketPaymentPayload(**payload)
	attendee_booking_details = []
	for attendee in payload_object.booking_details:
		attendee_booking_details.append(
			{
				"full_name": attendee.get("full_name"),
				"email": attendee.get("email"),
				"phone": attendee.get("phone"),
				"ticket_type": payload_object.ticket_name,
			}
		)

	processed_responses = process_multiselect_reponse(payload_object.registration_responses)

	data = create_event_booking(payload_object, processed_responses, attendee_booking_details)

	return data


def create_event_booking(
	payload_object: TicketPaymentPayload,
	processed_responses: list[dict[str, any]],
	attendee_booking_details: list[dict[str, any]],
) -> dict[str, any]:
	error_message = "Error processing ticket payment."
	try:
		event_booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": payload_object.event_name,
				"primary_contact": payload_object.booking_details[0]["email"],
				"attendees": attendee_booking_details,
				"responses": processed_responses,
			}
		)
		event_booking.insert(ignore_permissions=True)
		pr, invoice = event_booking.initialize_payment(
			phone_number=payload_object.booking_details[0]["phone"], payment_token=True
		)
		data = frappe._dict(
			{
				"invoice": invoice.name,
				"event_booking": event_booking.name,
				"payment_token": pr.payment_token,
			}
		)
		return data
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(frappe.get_traceback(), "Ticket Payment Error")
		frappe.throw(_(error_message))


@frappe.whitelist(
	allow_guest=True
)  # nosemgrep: guest-whitelisted-method -- public ticket type lookup, read-only
def get_event_ticket_type(ticket_id: str | int) -> dict[str, any]:
	if not ticket_id or not frappe.db.exists("Event Ticket Type", ticket_id):
		frappe.throw("This ticket type does not exist.")

	ticket = frappe.get_doc(
		"Event Ticket Type",
		ticket_id,
	).as_dict()

	ticket["event_details"] = {}

	event_name, event_title, event_route = frappe.db.get_value(
		"Buzz Event", ticket.event, ["name", "title", "route"]
	)
	ticket["event_details"]["title"] = event_title
	ticket["event_details"]["route"] = event_route
	ticket["event_details"]["name"] = event_name

	return ticket


def process_multiselect_reponse(
	responses: list[dict[str, any]],
) -> str:
	processed_responses = []
	for response in responses:
		processed_response = response.copy()

		if isinstance(response.get("response"), list):
			processed_response["response"] = "\n".join(str(item) for item in response["response"])

		processed_responses.append(processed_response)

	return processed_responses
