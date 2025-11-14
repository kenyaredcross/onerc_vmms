# VM Membership

The **VM Membership** DocType manages member subscriptions, payment tracking, and validity within the Volunteer and Member Management system.

Each record represents a specific membership plan linked to a member, branch (company), and payment status. It tracks the start and end dates of validity, whether the membership is paid, and includes workflow states for approval and renewal.

---

## Key Features

- **Membership Plans:** Each membership is linked to a defined _Membership Type_ (e.g., Annual, Lifetime).
- **Validity Tracking:** Start and end dates define the membership duration, with an optional “Member Since” date.
- **Payment Details:** Captures payment status, currency, and amount. Payment may be completed through the portal or reconciled by admins.
- **Status Workflow:** Supports statuses — _Draft_, _Pending_, _Active_, _Rejected_, and _Expired_.
- **QR Code:** Each membership includes a scannable QR code for verification and certificate use.
- **Company Link:** Supports multiple memberships per member, each tied to a specific branch or company.
- **Integration:** Links directly to related _Sales Invoices_ and _Payment Requests_.

---

## Navigation

<div style="display: flex; align-items: center;">

  <a href="./Member.md" style="margin-right: 10px;">
    <img height="34" src="https://img.shields.io/badge/←%20Previous-1E3A8A?style=for-the-badge" />
  </a>

  <a href="../../../README.md" style="margin-right: 10px;">
    <img height="34" src="https://img.shields.io/badge/⌂%20Home-047857?style=for-the-badge" />
  </a>

  <a href="./Opportunity-Opening.md" style="margin-right: 10px;">
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
