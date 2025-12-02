# Copyright (c) 2025, Kenya Red Cross Society and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class VMNotificationCenter(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from hrms.hr.doctype.designation_skill.designation_skill import DesignationSkill
        from lms.lms.doctype.related_courses.related_courses import RelatedCourses
        from onerc_vmms.volunteer_and_member_management.doctype.administrative_location_table.administrative_location_table import AdministrativeLocationTable
        from onerc_vmms.volunteer_and_member_management.doctype.company_item.company_item import CompanyItem
        from onerc_vmms.volunteer_and_member_management.doctype.county_table.county_table import CountyTable
        from onerc_vmms.volunteer_and_member_management.doctype.department_item.department_item import DepartmentItem
        from onerc_vmms.volunteer_and_member_management.doctype.designation_item.designation_item import DesignationItem
        from onerc_vmms.volunteer_and_member_management.doctype.employment_type_item.employment_type_item import EmploymentTypeItem
        from onerc_vmms.volunteer_and_member_management.doctype.membership_type_item.membership_type_item import MembershipTypeItem
        from onerc_vmms.volunteer_and_member_management.doctype.personnel_licence_item.personnel_licence_item import PersonnelLicenceItem
        from onerc_vmms.volunteer_and_member_management.doctype.sub_county_table.sub_county_table import SubCountyTable
        from onerc_vmms.volunteer_and_member_management.doctype.ward_table.ward_table import WardTable

        administrative_location: DF.TableMultiSelect[AdministrativeLocationTable]
        amended_from: DF.Link | None
        branch: DF.TableMultiSelect[CompanyItem]
        company: DF.Literal["Volunteer", "Employee Staff"]
        county: DF.TableMultiSelect[CountyTable]
        courses: DF.TableMultiSelect[RelatedCourses]
        department: DF.TableMultiSelect[DepartmentItem]
        designation: DF.TableMultiSelect[DesignationItem]
        licences: DF.TableMultiSelect[PersonnelLicenceItem]
        membership_branch: DF.TableMultiSelect[CompanyItem]
        membership_region: DF.TableMultiSelect[CompanyItem]
        membership_status: DF.Literal["", "Draft", "Pending", "Active", "Rejected", "Expired"]
        membership_type: DF.TableMultiSelect[MembershipTypeItem]
        party_type: DF.Link
        personnel_type: DF.TableMultiSelect[EmploymentTypeItem]
        region: DF.TableMultiSelect[CompanyItem]
        short_description: DF.SmallText | None
        skills: DF.TableMultiSelect[DesignationSkill]
        sub_county: DF.TableMultiSelect[SubCountyTable]
        title: DF.Data
        ward: DF.TableMultiSelect[WardTable]
    # end: auto-generated types
    
    @frappe.whitelist()
    def get_party_list(self) -> list[dict[str, any]]:
        party_list = frappe.get_all(
            self.party_type,
        )

        return party_list
