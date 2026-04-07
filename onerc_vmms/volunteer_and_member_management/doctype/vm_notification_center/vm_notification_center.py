# Copyright (c) 2025, Kenya Red Cross Society and contributors
# For license information, please see license.txt

import frappe
from frappe import msgprint
from frappe.model.document import Document
from typing import Callable
from frappe.core.doctype.sms_settings.sms_settings import send_sms as core_send_sms
from frappe.utils import cstr
from frappe.query_builder import DocType
from pypika import Criterion
from frappe.query_builder.functions import Coalesce


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

        active: DF.Check
        amended_from: DF.Link | None
        branch: DF.TableMultiSelect[CompanyItem]
        communication_channel: DF.Literal["", "SMS", "Email"]
        courses: DF.TableMultiSelect[RelatedCourses]
        department: DF.TableMultiSelect[DepartmentItem]
        designation: DF.TableMultiSelect[DesignationItem]
        expired: DF.Check
        licences: DF.TableMultiSelect[PersonnelLicenceItem]
        membership_branch: DF.TableMultiSelect[CompanyItem]
        membership_type: DF.TableMultiSelect[MembershipTypeItem]
        message: DF.Code | None
        pending: DF.Check
        personnel_specific_type: DF.Literal["", "Volunteer", "Employee Staff"]
        personnel_type: DF.TableMultiSelect[EmploymentTypeItem]
        recipient_type: DF.Link
        rejected: DF.Check
        short_description: DF.SmallText | None
        skills: DF.TableMultiSelect[DesignationSkill]
        title: DF.Data
        total_recipients: DF.Int
    # end: auto-generated types

    def on_submit(self):
        self.queue_action("send_notification")
        msgprint(
            msg=f"Notification has been queued to be sent to {self.total_recipients} recipient(s).",
            title="Notification Queued",
            indicator="blue",
        )

    def before_submit(self):
        if not self.message:
            frappe.throw("Please enter the message to be sent before submitting.")

    def send_notification(self):
        comm_channel = self.get_communication_channel(self.communication_channel)
        comm_channel()

    def get_communication_channel(self, selected_channel: str) -> Callable[..., None]:
        comm_map = {
            "SMS": self._send_sms,
            "Email": self._send_email,
        }
        comm_channel = comm_map.get(selected_channel)
        if not comm_channel:
            frappe.throw("Invalid communication channel selected")
        return comm_channel

    def _send_sms(self):
        self.get_sms_settings()
        recipient_nos = self.get_recipients_nos()
        if not recipient_nos:
            frappe.throw("No valid recipient phone numbers found.")
        core_send_sms(receiver_list=recipient_nos, msg=cstr(self.message))

    def _send_email(self):
        self.get_email_settings()
        recipient_list = self.get_recipient_list()
        if not recipient_list:
            frappe.throw("No valid recipient email addresses found.")
        email_recipients = [r["user"] for r in recipient_list if r.get("user")]
        frappe.sendmail(
            recipients=email_recipients,
            subject=self.title,
            message=self.message,
        )

    @frappe.whitelist()
    def get_recipient_list(
        self,
    ) -> list[dict[str, str]]:

        recipient_map = {
            "Employee": self._fetch_personnel_recipients,
            "VM Member": self._fetch_member_recipients,
        }
        if not recipient_map.get(self.recipient_type):
            frappe.throw("Invalid recipient type selected")

        return recipient_map[self.recipient_type]()

    def _fetch_personnel_recipients(self) -> list[dict[str, str]]:
        recipient = DocType("Employee")
        user = DocType("User")

        conditions = self._build_conditions(
            recipient, self.map_personel_filters_to_registry()
        )

        query = (
            frappe.qb.from_(recipient)
            .inner_join(user)
            .on(recipient.user_id == user.name)
            .select(
                recipient.name.as_("recipient_id"),
                user.full_name.as_("recipient_name"),
                user.name.as_("user"),
                Coalesce(user.mobile_no, user.phone).as_("phone"),
            )
        )

        if conditions:
            query = query.where(Criterion.all(conditions))

        return query.run(as_dict=True)

    def _fetch_member_recipients(self) -> list[dict[str, str]]:
        recipient = DocType("VM Member")
        user = DocType("User")
        membership = DocType("VM Membership")

        member_conditions = self._build_conditions(
            recipient, self.map_personel_filters_to_registry()
        )
        membership_conditions = self._build_conditions(
            membership, self.map_membership_filters_to_registry()
        )
        membership_statuses = self.map_membership_status()

        query = (
            frappe.qb.from_(recipient)
            .inner_join(user)
            .on(recipient.email_id == user.name)
            .inner_join(membership)
            .on(recipient.name == membership.member)
            .select(
                recipient.name.as_("recipient_id"),
                user.full_name.as_("recipient_name"),
                user.name.as_("user"),
                Coalesce(user.mobile_no, user.phone).as_("phone"),
            )
            .distinct()
        )

        conditions = list(member_conditions) + list(membership_conditions)

        if membership_statuses:
            conditions.append(membership.status.isin(membership_statuses))

        if conditions:
            query = query.where(Criterion.all(conditions))

        return query.run(as_dict=True)

    @staticmethod
    def _build_conditions(table: DocType, filters: dict[str, list]) -> list:
        return [
            table[field].isin(values) for field, values in filters.items() if values
        ]

    def personel_registry_filters(self) -> list[dict[str, str]]:
        return [
            {"branch": "company"},
            {"department": "department"},
            {"designation": "designation"},
            {"personnel_type": "employment_type"},
        ]

    def membership_registry_filters(self) -> list[dict[str, str]]:
        return [
            {"membership_branch": "company"},
            {"membership_type": "membership_type"},
        ]

    def _map_filters_to_registry(
        self, filter_definitions: list[dict[str, str]]
    ) -> dict[str, list]:
        """Generic mapper: reads child-table fields from self and returns {doctype_field: [values]}."""
        result = {}
        for filter_def in filter_definitions:
            for self_field, doctype_field in filter_def.items():
                rows = getattr(self, self_field, None)
                if rows:
                    result[doctype_field] = [
                        getattr(row, doctype_field) for row in rows
                    ]
        return result

    def map_personel_filters_to_registry(self) -> dict[str, list]:
        return self._map_filters_to_registry(self.personel_registry_filters())

    def map_membership_filters_to_registry(self) -> dict[str, list]:
        return self._map_filters_to_registry(self.membership_registry_filters())

    def map_membership_status(self) -> list[str]:
        status_map = {
            "Active": self.active,
            "Pending": self.pending,
            "Expired": self.expired,
            "Rejected": self.rejected,
        }
        return [status for status, is_selected in status_map.items() if is_selected]

    def get_recipients_nos(self) -> list[str]:
        recipient_list = self.get_recipient_list()
        recipient_nos = [r["phone"] for r in recipient_list if r.get("phone")]
        frappe.log_error(
            message=f"No phone numbers found for recipients: {recipient_list}",
            title=f"No Recipient Phone Numbers {len(recipient_nos)}",
        )
        self.db_set("total_recipients", len(recipient_nos), update_modified=False)
        self.reload()
        return recipient_nos

    @staticmethod
    def get_sms_settings():
        if not frappe.db.get_single_value(
            "SMS Settings", "sms_gateway_url", cache=True
        ):
            frappe.throw(
                "Please set up <a href='/app/sms-settings' target='_blank'>SMS Settings</a> before sending notifications via SMS."
            )

    @staticmethod
    def get_email_settings():
        if not frappe.db.exists("Email Account", {"enable_outgoing": 1}, cache=True):
            frappe.throw(
                "Please set up an outgoing <a href='/app/email-account' target='_blank'>Email Account</a> before sending notifications via Email."
            )

    @staticmethod
    def get_user_phone(user_id: str) -> str | None:
        mobile_no, phone = frappe.db.get_value("User", user_id, ["mobile_no", "phone"])
        return mobile_no or phone
