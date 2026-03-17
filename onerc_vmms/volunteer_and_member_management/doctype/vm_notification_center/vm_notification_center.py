# Copyright (c) 2025, Kenya Red Cross Society and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from typing import Callable
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from frappe.utils import cstr, get_link_to_form


class VMNotificationCenter(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from hrms.hr.doctype.designation_skill.designation_skill import DesignationSkill
        from lms.lms.doctype.related_courses.related_courses import RelatedCourses
        from onerc_vmms.volunteer_and_member_management.doctype.company_item.company_item import CompanyItem
        from onerc_vmms.volunteer_and_member_management.doctype.department_item.department_item import DepartmentItem
        from onerc_vmms.volunteer_and_member_management.doctype.designation_item.designation_item import DesignationItem
        from onerc_vmms.volunteer_and_member_management.doctype.employment_type_item.employment_type_item import EmploymentTypeItem
        from onerc_vmms.volunteer_and_member_management.doctype.membership_type_item.membership_type_item import MembershipTypeItem
        from onerc_vmms.volunteer_and_member_management.doctype.personnel_licence_item.personnel_licence_item import PersonnelLicenceItem

        amended_from: DF.Link | None
        branch: DF.TableMultiSelect[CompanyItem]
        communication_channel: DF.Literal["", "SMS", "Email"]
        courses: DF.TableMultiSelect[RelatedCourses]
        department: DF.TableMultiSelect[DepartmentItem]
        designation: DF.TableMultiSelect[DesignationItem]
        licences: DF.TableMultiSelect[PersonnelLicenceItem]
        membership_branch: DF.TableMultiSelect[CompanyItem]
        membership_status: DF.Literal["", "Draft", "Pending", "Active", "Rejected", "Expired"]
        membership_type: DF.TableMultiSelect[MembershipTypeItem]
        message: DF.Code | None
        personnel_specific_type: DF.Literal["Volunteer", "Employee Staff"]
        personnel_type: DF.TableMultiSelect[EmploymentTypeItem]
        recipient_type: DF.Link
        region: DF.TableMultiSelect[CompanyItem]
        short_description: DF.SmallText | None
        skills: DF.TableMultiSelect[DesignationSkill]
        title: DF.Data
        total_recipients: DF.Int
    # end: auto-generated types

    def validate(self): ...
    def on_submit(self):
        self.send_notification()

    def before_submit(self):
        (
            frappe.throw("Please enter the message to be sent before submitting.")
            if not self.message
            else ...
        )

    @frappe.whitelist()
    def get_recipient_list(self):
        party_type_map = {
            "Employee": self.get_personel_recipient_list,
            "VM Member": self.get_member_party_list,
        }

        recipient_type_list = party_type_map.get(self.recipient_type)
        if not recipient_type_list:
            frappe.throw("Invalid recipient type selected")

        return recipient_type_list()

    def get_member_party_list(self):
        print("Fetching member party list with filters:")

    def get_personel_recipient_list(self):
        registry_filters = self.map_personel_filters_to_registry()

        filters = []

        for field, values in registry_filters.items():
            filters.append([field, "in", values])

        filters.append(
            [
                "is_volunteer",
                "=",
                1 if self.personnel_specific_type == "Volunteer" else 0,
            ]
        )

        party_list = frappe.get_all(
            self.recipient_type,
            filters=filters,
            fields=["name", "user_id as user"],
        )

        return self.get_user_detail(party_list)

    def get_user_detail(self, party_list: list[dict[str, str]]):
        new_party_list = []

        for party in party_list:
            if party.get("user"):
                phone, full_name = frappe.db.get_value(
                    "User", party.get("user"), ["mobile_no", "full_name"]
                )

                party["phone"] = phone
                party["recipient_name"] = full_name
                new_party_list.append(party)

        return new_party_list

    def personel_registry_filters(self) -> list[dict[str, str]]:
        return [
            {"region": "company"},
            {"branch": "company"},
            {"department": "department"},
            {"designation": "designation"},
            {"personnel_type": "employment_type"},
            # {"county": "county"},
            # {"sub_county": "sub_county"},
            # {"ward": "ward"},
            # {"administrative_location": "administrative_location"},
            # {"skills": "skill"},
            # {"courses": "course"},
            # {"licences": "licence"},
        ]

    def map_personel_filters_to_registry(self):
        result = {}

        filters = self.personel_registry_filters()

        for filter in filters:

            for field, doctype in filter.items():
                value = getattr(self, field)

                if value:
                    result[doctype] = [getattr(v, doctype) for v in value]

        return result

    def map_member_filters_to_registry(self): ...

    def member_registry_filters(self) -> list[dict[str, str]]:
        return []

    def get_communication_channel(self, selected_channel: str) -> Callable[..., None]:
        comm_map = {
            "SMS": self._send_sms,
            "Email": self.send_email,
        }

        comm_channel = comm_map.get(selected_channel)
        if not comm_channel:
            frappe.throw("Invalid communication channel selected")

        return comm_channel

    def send_notification(self):
        comm_channel = self.get_communication_channel(self.communication_channel)
        comm_channel()

    def _send_sms(self):
        self.get_sms_settings()
        recipient_nos = self.get_recipients_nos()

        if not len(recipient_nos):
            frappe.throw("No valid recipient phone numbers found.")

        frappe.enqueue(
            send_sms,
            queue="long",
            receiver_list=recipient_nos,
            msg=cstr(self.message),
        )

        frappe.msgprint(
            msg=f"SMS notification has been queued and will be sent to {len(recipient_nos)} recipient(s).",
            title="Notification Queued",
            indicator="blue",
        )

    def send_email(self): ...

    def get_recipients_nos(self) -> list[str]:
        recipient_list = self.get_recipient_list()
        recipient_nos = [
            recipient.get("phone")
            for recipient in recipient_list
            if recipient.get("phone")
        ]

        self.total_recipients = len(recipient_nos)

        return recipient_nos

    @staticmethod
    def get_sms_settings():
        if not frappe.db.get_single_value("SMS Settings", "sms_gateway_url"):
            frappe.throw(
                f"Please set up <a href='/app/sms-settings' target='_blank'>SMS Settings</a> before sending notifications via SMS."
            )

    def auto_populate_title(self): ...
