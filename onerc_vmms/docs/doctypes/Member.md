# VM Member

The **VM Member** Doctype represents an individual who holds one or more memberships within the Volunteer and Member Management System (VMMS).
It serves as a unified record for members, linking them with related **Customer**, **Supplier**, and optionally, **Volunteer (Personnel)** profiles.

---

## Core Fields

| Field             | Type         | Description                                                                  |
| ----------------- | ------------ | ---------------------------------------------------------------------------- |
| **Member Name**   | Data         | Full name of the member. Used as the display and title field.                |
| **Email Address** | Link (User)  | Portal or system user linked to the member. Enables login and notifications. |
| **Image**         | Attach Image | Member’s profile image, hidden by default in list view.                      |

---

## Customer & Supplier Linkage

VM Members can be optionally associated with Customer and Supplier records for accounting or partnership purposes.

| Field             | Type            | Description                                                                               |
| ----------------- | --------------- | ----------------------------------------------------------------------------------------- |
| **Customer**      | Link (Customer) | Links the member to a customer record, enabling billing and receivables tracking.         |
| **Customer Name** | Data            | Automatically fetched from the linked Customer.                                           |
| **Supplier**      | Link (Supplier) | Links the member to a supplier record, useful when the member provides goods or services. |

---

## Volunteer Association

| Field         | Type                        | Description                                                                                                                                          |
| ------------- | --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Volunteer** | Link (Employee / Personnel) | Connects the member to a Volunteer (Personnel) record if they also serve as an active volunteer. This supports unified HR and membership management. |

---

## Address and Contact

Dynamic HTML fields render the member’s related **Address** and **Contact** records when the document is saved.

| Field            | Type | Description                                          |
| ---------------- | ---- | ---------------------------------------------------- |
| **Address HTML** | HTML | Displays linked addresses for the member.            |
| **Contact HTML** | HTML | Displays linked contact details for quick reference. |

---

## Related Documents

- [Membership-Management.md](./Membership-Management.md)
- [VM-Settings.md](./VM-Settings.md)
- [Volunteer-Management.md](./Volunteer-Management.md)

## Documentation & Support

Need help? Browse detailed guides, FAQs, or open an issue in our GitHub repository.

[![Full Documentation](https://img.shields.io/badge/Full_Documentation-6366F1?style=for-the-badge&logo=readthedocs&logoColor=fff)](https://github.com/kenyaredcross/onerc_vmms.git)
[![ERPNext Docs](https://img.shields.io/badge/ERPNext_Docs-FF6B6B?style=for-the-badge&logo=erpnext&logoColor=fff)](https://docs.erpnext.com)
[![Frappe Framework](https://img.shields.io/badge/Frappe_Framework-00C49A?style=for-the-badge&logo=frappe&logoColor=fff)](https://frappeframework.com/docs)
[![Community Forum](https://img.shields.io/badge/Community_Forum-F59E0B?style=for-the-badge&logo=discourse&logoColor=fff)](https://discuss.frappe.io)
[![Report Issue](https://img.shields.io/badge/Report_Issue-E63946?style=for-the-badge&logo=githubissues&logoColor=fff)](https://github.com/kenyaredcross/onerc_vmms.git/issues)
[![Website](https://img.shields.io/badge/Website-1E293B?style=for-the-badge&logo=googlechrome&logoColor=fff)](https://navari.co.ke)