# Opportunity Opening

The Opportunity Opening is a translated version of standard Job Opening DocType — extended to support both employment and volunteer opportunities.
This transition ensures compatibility with the Volunteer and Member Management System (VMMS).

---

![Details Overview](../images/opening/details.png)

## Extended Fields

| Field                    | Type       | Description                                                                                                                          |
| ------------------------ | ---------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Opening Type**         | **Select** | Classifies the opportunity as either _Internal (Employment)_ or _Guest (Volunteer/External)_. Controls access rules and eligibility. |
| **Profession**           | **Link**   | Associates the opening with a defined professional category for improved skill and qualification matching.                           |
| **Job Opening Template** | **Link**   | Enables creation of opportunities from reusable templates for consistent configuration.                                              |

## Screening & Qualification Requirements

### Education Requirements

![Requirements Overview](../images/opening/requirements.png)
| Field | Type | Description |
| ------------------------------------- | ------ | -------------------------------------------------------------------------- |
| **Enable Auto-Grading** | Check | Activate automated application scoring system |
| **Disqualify if Requirement Not Met** | Check | Automatically reject applications not meeting minimum criteria |
| **Minimum Pass Score** | Float | Required scoring threshold for application consideration |
| **Minimum Qualification Level** | Select | Education level: Primary, Secondary, Undergraduate, Graduate, Postgraduate |
| **Allow Equivalent Experience** | Check | Accept relevant work experience as qualification substitute |
| **Required GPA / Grade** | Data | Minimum academic performance requirement |
| **Preferred Field of Study** | Data | Desired educational background or major |

### Experience Requirements

| Field                           | Type  | Description                                                    |
| ------------------------------- | ----- | -------------------------------------------------------------- |
| **Minimum Years of Experience** | Float | Required number of years in relevant field                     |
| **Experience Area**             | Data  | Specific industry or functional experience required            |
| **Disqualify if Below Minimum** | Check | Automatically reject applications with insufficient experience |

---

## Skills & Certifications

### Licences & Skills Section

| Field                      | Type  | Description                                    |
| -------------------------- | ----- | ---------------------------------------------- |
| **Required Skills**        | Table | Mandatory skills with proficiency levels       |
| **Required Certification** | Table | Professional certifications and credentials    |
| **Required Licences**      | Table | Regulatory or professional licenses required   |
| **Required Attachments**   | Table | Mandatory document submissions for application |

---

## Screening Questions

![Questions Overview](../images/opening/questions.png)

| Field                   | Type   | Description                                    |
| ----------------------- | ------ | ---------------------------------------------- |
| **Screening Questions** | Table  | Custom qualification assessment questions      |
| **Question Type**       | Select | Type of question (Multiple Choice, Text, etc.) |
| **Weight**              | Float  | Scoring weight for automated evaluation        |
| **Required**            | Check  | Whether question must be answered              |

---

## Notification Settings

![Notification Overview](../images/opening/notification.png)

### Rejection Notification Settings

| Field                                        | Type  | Description                                                  |
| -------------------------------------------- | ----- | ------------------------------------------------------------ |
| **Enable Automatic Rejection Notifications** | Check | System-generated rejection email notifications               |
| **Send Rejection Email Immediately**         | Check | Instant notification when application is rejected            |
| **Rejection Email Template**                 | Link  | Custom email template for rejection communications           |
| **Notify Unshortlisted Applicants After**    | Int   | Days after closing date to notify non-shortlisted applicants |
| **Shortlisted Rejection Notification Date**  | Date  | Specific date to notify rejected shortlisted candidates      |

---

## Navigation

<div style="display: flex; align-items: center;">

  <a href="./Membership.md" style="margin-right: 10px;">
    <img height="34" src="https://img.shields.io/badge/←%20Previous-1E3A8A?style=for-the-badge" />
  </a>

  <a href="../../../README.md" style="margin-right: 10px;">
    <img height="34" src="https://img.shields.io/badge/⌂%20Home-047857?style=for-the-badge" />
  </a>

  <a href="./Opportunity-Applicant.md" style="margin-right: 10px;">
    <img height="34" src="https://img.shields.io/badge/Next%20→-6D28D9?style=for-the-badge" />
  </a>

</div>

## Documentation & Support

Need help? Browse detailed guides, FAQs, or open an issue in our GitHub repository.

[![Full Documentation](https://img.shields.io/badge/Full_Documentation-6366F1?style=for-the-badge&logo=readthedocs&logoColor=fff)](https://github.com/kenyaredcross/onerc_vmms.git)
[![ERPNext Docs](https://img.shields.io/badge/ERPNext_Docs-FF6B6B?style=for-the-badge&logo=erpnext&logoColor=fff)](https://docs.erpnext.com)
[![Frappe Framework](https://img.shields.io/badge/Frappe_Framework-00C49A?style=for-the-badge&logo=frappe&logoColor=fff)](https://frappeframework.com/docs)
[![Community Forum](https://img.shields.io/badge/Community_Forum-F59E0B?style=for-the-badge&logo=discourse&logoColor=fff)](https://discuss.frappe.io)
[![Report Issue](https://img.shields.io/badge/Report_Issue-E63946?style=for-the-badge&logo=githubissues&logoColor=fff)](https://github.com/kenyaredcross/onerc_vmms.git/issues)
[![Website](https://img.shields.io/badge/Website-1E293B?style=for-the-badge&logo=googlechrome&logoColor=fff)](https://navari.co.ke)
