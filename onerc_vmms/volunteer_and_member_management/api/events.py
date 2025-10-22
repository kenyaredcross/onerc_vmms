import json
import time
from datetime import datetime

import frappe

from .user import create_user, get_user_info


@frappe.whitelist(allow_guest=True)
def get_events():
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

    base_filters = {"start_date": [">=", datetime.now().date()], "is_published": 1}

    if user_info == "Guest":
        base_filters["event_access"] = ["in", ["Public", "Private"]]

    elif user_info.get("is_member"):
        pass
    elif user_info.get("is_volunteer"):
        base_filters["event_access"] = ["in", ["Public", "Private"]]

    events = frappe.get_all("FE Event", fields=fields, filters=base_filters)

    for event in events:
        event.short_description = (
            frappe.utils.strip_html_tags(event.short_description)
            if event.short_description
            else ""
        )

    return events


@frappe.whitelist(allow_guest=True)
def register_event(event_name, user):
    try:
        user_info = get_user_info()

        if not frappe.db.exists("FE Event", event_name):
            frappe.throw("Event does not exist")

        attendee_registration = frappe.db.get_value(
            "Attendee Registration", {"event": event_name}, "name"
        )
        if not attendee_registration:
            frappe.throw("Attendee Registration not set up for this event")

        if frappe.db.exists(
            "Event Attendee Registration",
            {"parent": event_name, "email": user.get("email")},
        ):
            frappe.throw("This email has already been registered for the event")

        EAR = frappe.new_doc("Event Attendee Registration")
        EAR.parent = event_name
        EAR.parenttype = "Attendee Registration"
        EAR.parentfield = "event_attendees"
        EAR.email = user.get("email")
        EAR.full_name = user.get("full_name")
        EAR.phone_number = user.get("phone")
        EAR.personnel_type = (
            "Guest"
            if user_info == "Guest"
            else (
                "Volunteer"
                if user_info.get("is_volunteer")
                else (
                    "Member"
                    if user_info.get("is_member")
                    else "Employee" if user_info.get("employee") else "Other"
                )
            )
        )

        EAR.insert(ignore_permissions=True)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Event Registration Error")
        frappe.throw("Event Registration Error")


@frappe.whitelist(allow_guest=True)
def get_event_details(event_name):
    try:
        event = frappe.get_doc("FE Event", {"route": event_name}).as_dict()
        event_name = event.name

        event["description"] = (
            frappe.utils.strip_html_tags(event["description"])
            if event.get("description")
            else ""
        )

        event["about"] = (
            frappe.utils.strip_html_tags(event["about"]) if event.get("about") else ""
        )

        event_tickets = frappe.get_all(
            "Event Ticket Type",
            filters={"event": event.name},
            fields=["name", "title", "price", "currency"],
            order_by="price asc",
        )
        event["tickets"] = event_tickets or []

        event["booked_tickets"] = []

        if frappe.session.user and frappe.session.user != "Guest":
            booking = frappe.get_all(
                "Event Booking",
                filters={
                    "user": frappe.session.user,
                    "event": event_name,
                },
                fields=["name"],
                limit=1,
            )

            if booking:
                booking_name = booking[0].name
                booked_tickets = []
                tickets = frappe.get_all(
                    "Event Ticket",
                    filters={"booking": booking_name},
                    fields=[
                        "name",
                        "ticket_type",
                        "attendee_name",
                        "attendee_email",
                        "qr_code",
                    ],
                )

                for ticket in tickets:
                    ticket_title = frappe.db.get_value(
                        "Event Ticket Type", ticket.ticket_type, "title"
                    )
                    ticket_dict = ticket.copy()
                    ticket_dict["ticket_type_title"] = ticket_title
                    booked_tickets.append(ticket_dict)

                event["booked_tickets"] = booked_tickets or []

        return event

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error fetching event details")
        frappe.throw("Error fetching event details")


@frappe.whitelist(allow_guest=True)
def get_speaker_profiles(event_speakers):
    try:
        speakers_list = json.loads(event_speakers)

        speaker_profiles = []
        for speaker in speakers_list:

            speaker_profile = frappe.get_doc(
                "Speaker Profile", speaker.get("speaker")
            ).as_dict()
            speaker_profiles.append(speaker_profile)

        return speaker_profiles
    except Exception as e:
        frappe.log_error(title="Speaker Profile Fetch Error", message=str(e))
        frappe.throw("Error fetching speaker profiles")


@frappe.whitelist(allow_guest=True)
def handle_ticket_payment(phone, event_name, ticket_name, email, first_name, last_name):
    original_user = frappe.session.user
    try:
        if frappe.session.user == "Guest":
            if frappe.db.exists("User", email):
                user = frappe.get_doc("User", email)
            else:
                create_user(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                )
                user = frappe.get_doc("User", email)

            frappe.local.login_manager.login_as(email)
        else:
            user = frappe.get_doc("User", frappe.session.user)

        event_ticket_price = frappe.db.get_value(
            "Event Ticket Type", ticket_name, "price"
        )
        company = frappe.db.get_value("FE Event", event_name, "company")
        mode_of_payment = frappe.db.get_value("FE Event", event_name, "mode_of_payment")
        currency = frappe.db.get_value("Company", company, "default_currency")

        existing_booking = frappe.db.exists(
            "Event Booking", {"user": user.name, "event": event_name}
        )

        if existing_booking:
            event_booking = frappe.get_doc("Event Booking", existing_booking)
        else:
            event_booking = frappe.get_doc(
                {
                    "doctype": "Event Booking",
                    "event": event_name,
                    "user": user.name,
                    "mode_of_payment": mode_of_payment,
                    "attendees": [
                        {
                            "full_name": user.full_name,
                            "email": user.email,
                            "ticket_type": ticket_name,
                            "amount": event_ticket_price,
                            "currency": currency,
                        }
                    ],
                }
            )
            event_booking.insert(ignore_permissions=True)

        event_booking.initialize_payment(phone_number=phone)
        frappe.db.commit()

        max_wait_time = 30
        interval = 5
        elapsed_time = 0
        time.sleep(max_wait_time)

        # while elapsed_time < max_wait_time:
        #     time.sleep(interval)
        #     elapsed_time += interval

        #     tickets = frappe.get_all(
        #         "Event Ticket",
        #         filters={"booking": event_booking.name},
        #         fields=[
        #             "name",
        #             "ticket_type",
        #             "attendee_name",
        #             "attendee_email",
        #             "qr_code",
        #         ],
        #     )

        #     if len(tickets) > 0:
        #         if original_user == "Guest":
        #             frappe.local.login_manager.logout()

        #         return {
        #             "success": True,
        #             "message": "Payment successful",
        #             "booking": event_booking.name,
        #             "tickets": tickets,
        #         }

        if original_user == "Guest":
            frappe.local.login_manager.logout()

        tickets = frappe.get_all(
            "Event Ticket",
            filters={"booking": event_booking.name},
            fields=[
                "name",
                "ticket_type",
                "attendee_name",
                "attendee_email",
                "qr_code",
            ],
        )

        return {
            "success": False if not tickets else True,
            "message": (
                "Payment processing timed out. Please check your payment status later."
                if not tickets
                else "Payment successful"
            ),
            "booking": event_booking.name,
            "tickets": tickets,
        }

    except Exception as e:
        if original_user == "Guest" and frappe.session.user != "Guest":
            frappe.local.login_manager.logout()

        frappe.log_error(frappe.get_traceback(), "Ticket Payment Error")
        return {
            "success": False,
            "message": "Error occurred while processing ticket. Please try again.",
        }
