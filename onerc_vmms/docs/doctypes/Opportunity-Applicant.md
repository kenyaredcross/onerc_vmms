# Opportunity Applicant

The **Opportunity Applicant** is a translated and extended version of ERPNext's standard Job Applicant DocType, designed to support both employment candidates and volunteer applicants within a unified framework. This comprehensive system captures detailed applicant information while maintaining compatibility with the Volunteer and Member Management System (VMMS).

## Core Purpose

The doctype manages multiple types of engagements in one place:

- **Volunteer Opportunities**: Simplified application process focusing on volunteers, skipping some traditional HR steps like job offers, and automatically creating a **Personnel record of type Volunteer** for successful applicants.
- **Employment Opportunities**: Full HR recruitment workflow including qualification tracking, automated scoring, and offer generation.
- **Internal Opportunities**: Tracks _Required Skills_ and, upon verification, updates the corresponding **Personnel record**, keeping skill profiles up-to-date.

---

## Key Features

### Dual Applicant Support

The system handles both volunteers and employees in a single workflow. Volunteers experience a streamlined process, while employment applicants follow a comprehensive screening and qualification process.

### Automated Screening & Tracking

Applications are evaluated automatically based on defined criteria. Screening questions are scored, eligibility is tracked, and responses are used to determine qualification for the opportunity. Personnel records are updated where relevant, such as assigning skills from internal openings.

### Skills & Competency Updates

Internal Opportunity Openings can define _Required Skills_ which, once verified during recruitment, are mapped to the Personnel record. This ensures employee or volunteer competency profiles remain accurate over time.

---

## Extended Main Fields

| Field            | Type  | Description                                         |
| ---------------- | ----- | --------------------------------------------------- |
| **Is Volunteer** | Check | Identifies applicant as volunteer vs. paid employee |

---

## Application Review & Rejection

| Field                                        | Type       | Description                                    |
| -------------------------------------------- | ---------- | ---------------------------------------------- |
| **Rejection Reason**                         | Small Text | Detailed explanation for rejected applications |
| **Applicant Notified of Application Status** | Check      | Tracks notification status to applicant        |

---

## Personal Information

### Basic Details

| Field                          | Type   | Description                                                            |
| ------------------------------ | ------ | ---------------------------------------------------------------------- |
| **First Name**                 | Data   | Legal first name                                                       |
| **Surname**                    | Data   | Family name/last name                                                  |
| **Other Names**                | Data   | Middle names or additional given names                                 |
| **MPESA Mobile Phone**         | Data   | Mobile number for MPESA transactions                                   |
| **Profile Photo**              | Attach | Applicant's photograph                                                 |
| **Marital Status**             | Select | Single, Married, Divorced, Widowed, Other                              |
| **Number of Dependants**       | Int    | Number of dependant family members                                     |
| **Place of Work**              | Data   | Current or previous workplace                                          |
| **Has Insurance (KRCS)**       | Select | Insurance coverage status                                              |
| **Gender**                     | Link   | Gender identification                                                  |
| **Date of Birth**              | Date   | Applicant's birth date                                                 |
| **Reason to Join**             | Select | Motivation: Humanitarian, Skill Development, Social Cohesion, Personal |
| **Consent to Use of Bio Data** | Check  | Permission for data processing                                         |

---

## Citizenship & Identification

| Field                      | Type   | Description                                   |
| -------------------------- | ------ | --------------------------------------------- |
| **Identification Type**    | Link   | Type of identification document               |
| **ID Number**              | Data   | Identification number                         |
| **Citizenship**            | Select | Citizen, Non-citizen, Refugee, Migrant, Other |
| **Country of Citizenship** | Link   | Country of citizenship                        |

---

## Address & Location

| Field                       | Type   | Description                               |
| --------------------------- | ------ | ----------------------------------------- |
| **County**                  | Link   | Administrative county                     |
| **Sub County**              | Link   | Sub-county administrative division        |
| **Administrative Location** | Link   | Specific administrative location          |
| **Ward**                    | Link   | Local ward information                    |
| **Access to Internet**      | Select | Internet availability: Yes, No, Sometimes |

---

## Language & Professional Profile

| Field           | Type              | Description                      |
| --------------- | ----------------- | -------------------------------- |
| **Languages**   | Table MultiSelect | Languages spoken by applicant    |
| **Profession**  | Link              | Professional field or occupation |
| **Github ID**   | Data              | GitHub profile URL               |
| **LinkedIn ID** | Data              | LinkedIn profile URL             |

---

## Health & Wellness

| Field            | Type  | Description                               |
| ---------------- | ----- | ----------------------------------------- |
| **Blood Group**  | Data  | Blood type information                    |
| **Disabilities** | Table | Disability information and accommodations |
| **Allergies**    | Table | Medical allergies and reactions           |

---

## Qualifications & Experience

### Education

| Field                 | Type  | Description                             |
| --------------------- | ----- | --------------------------------------- |
| **Education**         | Table | Academic qualifications and degrees     |
| **Courses**           | Table | Professional courses and certifications |
| **Additional Skills** | Table | Supplementary skills and competencies   |

### Work Experience

| Field               | Type  | Description                          |
| ------------------- | ----- | ------------------------------------ |
| **Work Experience** | Table | Employment history and positions     |
| **Work References** | Table | Professional references and contacts |

---

## Licences & Certifications

| Field                         | Type              | Description                                        |
| ----------------------------- | ----------------- | -------------------------------------------------- |
| **Driving Licence Classes**   | Table MultiSelect | Valid driving licence categories                   |
| **Licences & Certifications** | Table             | Professional licences, certifications, and permits |

---

## Screening & Assessment

| Field                            | Type    | Description                            |
| -------------------------------- | ------- | -------------------------------------- |
| **Total Score**                  | Float   | Overall screening score                |
| **Screening Score (%)**          | Percent | Percentage score from screening        |
| **Eligibility Status**           | Select  | Eligible, Not Eligible, Pending Review |
| **Screening Question Responses** | Table   | Responses to screening questions       |

---

## Supporting Documents

| Field                    | Type  | Description                   |
| ------------------------ | ----- | ----------------------------- |
| **Supporting Documents** | Table | Additional required documents |

---

## Documentation & Support

Need help? Browse detailed guides, FAQs, or open an issue in our GitHub repository.

[![Full Documentation](https://img.shields.io/badge/Full_Documentation-6366F1?style=for-the-badge&logo=readthedocs&logoColor=fff)](https://github.com/kenyaredcross/onerc_vmms.git)
[![ERPNext Docs](https://img.shields.io/badge/ERPNext_Docs-FF6B6B?style=for-the-badge&logo=erpnext&logoColor=fff)](https://docs.erpnext.com)
[![Frappe Framework](https://img.shields.io/badge/Frappe_Framework-00C49A?style=for-the-badge&logo=frappe&logoColor=fff)](https://frappeframework.com/docs)
[![Community Forum](https://img.shields.io/badge/Community_Forum-F59E0B?style=for-the-badge&logo=discourse&logoColor=fff)](https://discuss.frappe.io)
[![Report Issue](https://img.shields.io/badge/Report_Issue-E63946?style=for-the-badge&logo=githubissues&logoColor=fff)](https://github.com/kenyaredcross/onerc_vmms.git/issues)
[![Website](https://img.shields.io/badge/Website-1E293B?style=for-the-badge&logo=googlechrome&logoColor=fff)](https://navari.co.ke)
