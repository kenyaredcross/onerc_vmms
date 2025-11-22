from frappe import _
import frappe
import json
import time
from datetime import datetime


from .user import create_user, get_user_info
from dataclasses import dataclass


@frappe.whitelist(allow_guest=True)
def get_events(search=None):

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

    base_filters = {"end_date": [">=", datetime.now().date()], "is_published": 1}

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
            frappe.utils.strip_html_tags(event.short_description)
            if event.short_description
            else ""
        )

    return events


@frappe.whitelist(allow_guest=True)
def register_event(event_name: str | int, attendee: dict[str, any]) -> None:

    if not event_name or not frappe.db.exists("Buzz Event", event_name):
        frappe.throw("This event does not exist.")
    if not frappe.db.exists("Event Ticket Type", {"event": event_name}):
        frappe.throw("No ticket types available for this event.")

    event = frappe.db.get_value("Buzz Event", event_name, ["is_ticketed"], as_dict=True)
    if event and not event.is_ticketed:
        ticket = frappe.db.get_value(
            "Event Ticket Type", {"event": event_name}, as_dict=True
        )

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
            }
        )

        event_booking.insert(ignore_permissions=True)
        event_booking.submit()
        frappe.db.commit()

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Event Registration Error")
        frappe.throw("Event Registration Error")


@frappe.whitelist(allow_guest=True)
def get_event_details(event_name: str | int) -> dict:
    try:
        event = frappe.get_doc("Buzz Event", {"route": event_name}).as_dict()
        event_name = event.name

        event["description"] = (
            frappe.utils.strip_html_tags(event["description"])
            if event.get("description")
            else ""
        )

        event["about"] = (
            frappe.utils.strip_html_tags(event["about"]) if event.get("about") else ""
        )

        event["host"] = frappe.get_doc("Event Host", event.host).as_dict()
        event["host"]["about"] = frappe.utils.strip_html_tags(
            event["host"].get("about") if event["host"].get("about") else ""
        )

        event_tickets = frappe.get_all(
            "Event Ticket Type",
            filters={"event": event.name},
            fields=["name", "title", "price", "currency"],
            order_by="price asc",
        )
        event["tickets"] = event_tickets or []

        for sched in event.schedule:
            talk = frappe.get_doc("Event Talk", sched.talk)

            speakers = []

            for talk in talk.speakers:
                speaker = frappe.get_doc("Speaker Profile", talk.speaker)
                speakers.append(speaker.as_dict())

            event["speakers"] = speakers

        sponsors = []

        event_sponsors = frappe.get_all(
            "Event Sponsor",
            filters={"event": event.name},
            fields=["company_name", "company_logo", "website"],
        )

        for sponsor in event_sponsors:
            sponsors.append(sponsor)

        event["sponsors"] = sponsors

        return event

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error fetching event details")
        frappe.throw("Error fetching event details")


@dataclass
class TicketPaymentPayload:
    event_name: str | int
    ticket_name: str | int
    booking_details: list[dict[str, any]]


@frappe.whitelist(allow_guest=True)
def handle_ticket_payment(payload: dict) -> dict:
    error_message = "Error processing ticket payment."

    if not payload:
        frappe.throw(_(error_message))

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

    try:

        event_booking = frappe.get_doc(
            {
                "doctype": "Event Booking",
                "event": payload_object.event_name,
                "primary_contact": payload_object.booking_details[0]["email"],
                "attendees": attendee_booking_details,
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


@frappe.whitelist(allow_guest=True)
def confirm_payment(
    invoice_name: str, event_booking: str, confirm_payment_manual: bool
) -> str:
    def helper():
        frappe.set_user("Administrator")
        error_message = "Error confirming payment"

        if not invoice_name:
            frappe.throw(_(error_message))

        try:
            invoice = frappe.get_doc("Sales Invoice", invoice_name)

            if invoice.status == "Paid" and invoice.outstanding_amount == 0:
                ev_booking = frappe.get_doc("Event Booking", event_booking)
                ev_booking.submit()

                return "paid"

            return "unpaid"

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Confirm Payment Error")
            frappe.throw(_("Error confirming payment: {0}").format(str(e)))
        finally:
            frappe.set_user(frappe.session.user)

    if confirm_payment_manual:
        time.sleep(10)
        return helper()
    return helper()


@frappe.whitelist(allow_guest=True)
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
