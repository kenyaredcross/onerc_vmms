# VM Settings

The **VM Settings** Doctype is a central configuration record for the **Volunteer and Member Management System (VMMS)**.
It controls automation and system-wide defaults related to **Membership Management**, **Recruitment**, and **Branding**.

---

## 1. Membership Settings

These fields define how membership billing, invoicing, and communication are handled.

### Billing & Invoicing

| Field                                | Description                                                                            |
| ------------------------------------ | -------------------------------------------------------------------------------------- |
| **Billing Cycle**                    | Defines the billing period for memberships — _Monthly_ or _Yearly_.                    |
| **Billing Frequency**                | Specifies how many cycles the billing should run (e.g., 12 for 1 year billed monthly). |
| **Allow Invoicing for Memberships**  | Enables invoicing for all new memberships.                                             |
| **Automate Invoicing for Web Forms** | Automatically creates invoices when a membership payment is made through the portal.   |
| **Automate Payment Entry Creation**  | Auto-generates a Payment Entry after invoice creation.                                 |

### Financial Accounts

| Field                          | Description                                                                  |
| ------------------------------ | ---------------------------------------------------------------------------- |
| **Company**                    | Default company used for memberships created through the portal or webhooks. |
| **Debit Account**              | Account used when posting membership invoices.                               |
| **Membership Payment To**      | Target account for membership payments.                                      |
| **Membership Mode of Payment** | Default payment mode for membership transactions.                            |

### Communication & Acknowledgement

| Field                               | Description                                                      |
| ----------------------------------- | ---------------------------------------------------------------- |
| **Send Membership Acknowledgement** | Sends an email confirmation upon successful membership creation. |
| **Send Invoice with Email**         | Includes the invoice when sending acknowledgement emails.        |
| **Membership Print Format**         | Print format for membership documents.                           |
| **Invoice Print Format**            | Print format for invoices.                                       |
| **Email Template**                  | Template used for membership confirmation emails.                |

---

## 2. Recruitment & Hiring Settings

These settings extend the standard ERPNext HR recruitment process to integrate **Opportunities**, **Screening**, and **Rejection Notifications** within VMMS.

### Interview Roles & Scoring

| Field                  | Description                                                                     |
| ---------------------- | ------------------------------------------------------------------------------- |
| **Interview Roles**    | Defines system roles eligible to participate in interviews.                     |
| **Minimum Pass Score** | The minimum percentage required for passing screening or interview assessments. |

### Rejection Notifications

| Field                                            | Description                                                                                |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| **Enable Automatic Rejection Notifications**     | When enabled, applicants marked as _Rejected_ are automatically notified.                  |
| **Send Rejection Email Immediately**             | Sends notifications as soon as an applicant is rejected.                                   |
| **Notify Unshortlisted Applicants After (Days)** | Delays notification for unshortlisted applicants until a set number of days after closing. |
| **Rejection Email Template**                     | Email template used for rejection notifications.                                           |

---

## 3. Automation User

| Field                                                                | Description                                                                           |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| **Creation User**                                                    | The system user used to create Donations, Memberships, Invoices, and Payment Entries. |
| This user must have sufficient permissions to all relevant doctypes. |                                                                                       |

---

## 4. Branding

These options control visual appearance for the organization’s VMMS portal and internal desk.

| Field          | Description                                           |
| -------------- | ----------------------------------------------------- |
| **Brand Name** | Display name shown in the portal and documents.       |
| **Logo**       | Image displayed in the top-left corner of the system. |

---

## Related Documents

- [Membership-Management.md](./Membership-Management.md)
- [Opportunities.md](./Opportunities.md)
- [Personnel-Deployment-Request.md](./Personnel-Deployment-Request.md)
- [Volunteer-Deployment-Criteria.md](./Volunteer-Deployment-Criteria.md)

## Documentation & Support

Need help? Browse detailed guides, FAQs, or open an issue in our GitHub repository.

[![Full Documentation](https://img.shields.io/badge/Full_Documentation-6366F1?style=for-the-badge&logo=readthedocs&logoColor=fff)](https://github.com/kenyaredcross/onerc_vmms.git)
[![ERPNext Docs](https://img.shields.io/badge/ERPNext_Docs-FF6B6B?style=for-the-badge&logo=erpnext&logoColor=fff)](https://docs.erpnext.com)
[![Frappe Framework](https://img.shields.io/badge/Frappe_Framework-00C49A?style=for-the-badge&logo=frappe&logoColor=fff)](https://frappeframework.com/docs)
[![Community Forum](https://img.shields.io/badge/Community_Forum-F59E0B?style=for-the-badge&logo=discourse&logoColor=fff)](https://discuss.frappe.io)
[![Report Issue](https://img.shields.io/badge/Report_Issue-E63946?style=for-the-badge&logo=githubissues&logoColor=fff)](https://github.com/kenyaredcross/onerc_vmms.git/issues)
[![Website](https://img.shields.io/badge/Website-1E293B?style=for-the-badge&logo=googlechrome&logoColor=fff)](https://navari.co.ke)
