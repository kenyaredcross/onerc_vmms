# Opportunities Management

The **Opportunities Management** extends the standard HR recruitment process to support both **internal** and **external (guest)** openings — enabling seamless recruitment within the VMMS ecosystem.

It integrates deeply with the ERPNext HR framework while introducing advanced screening, assessment, and applicant tracking features.

There are two main opportunity types:

- **Internal Opportunities** — open only to registered _Personnel_ (employees or volunteers with active records).
- **Guest Opportunities** — open to the public or external applicants.

---

## 1. Opportunity Creation

Recruiters or administrators create openings using the **Opportunity Opening** doctype.
Each opening defines position details, department, requirements, location, and whether it is internal or external.

### Key Enhancements

- Categorization by department, region, or program
- Branch linkage (mapped to ERPNext _Company_)
- Assignment of hiring team or approvers
- Optional visibility control (internal-only or public)

---

## 2. Advanced Requirements

Opportunity openings can specify structured **requirements and qualifications**, allowing for better filtering and candidate matching.

- Education, skills, and certifications
- Minimum experience levels
- Minimum screening score

These requirements are later referenced during screening and evaluation.

---

## 3. Screening Questions

Each opening can include **custom screening questions** to help shortlist candidates automatically.

- Applicants respond to these during the application process.
- Answers are stored against the **Opportunity Applicant** record for review.
- Validation logic enforce mandatory answers or scoring rules.

---

## 4. Application & Applicant Details

Applicants apply via the **VMMS Opportunity Portal**, filling in an enhanced application form linked to the **Opportunity Applicant** doctype (adapted from ERPNext’s `Job Applicant`).

### Customizations

- Additional **Bio Data fields** for more comprehensive applicant profiles.
- Automatic linkage to existing **Personnel** or **User** records for internal candidates.
- Portal-friendly step-based application workflow with validation and progress indicators.

---

## 5. VMMS Opportunity Portal

The **Opportunity Portal** serves as the unified interface for all applicants — internal and external.

### Portal Features

- View all **available openings**.
- Apply directly via guided forms with integrated screening questions.
- Track application status and updates.
- Volunteers and members can reuse their stored profile data to apply faster.

This ensures a consistent recruitment experience across all applicant types.

---

## Related Documents

- [Opportunity Opening](./doctypes/Opportunity-Opening.md)
- [Opportunity Applicant](./doctypes//Opportunity-Applicant.md)
- [Settings](./doctypes//Settings.md)

## Navigation

<div style="display: flex; align-items: center;">

  <a href="./Membership-Management.md" style="margin-right: 10px;">
    <img height="34" src="https://img.shields.io/badge/←%20Previous-1E3A8A?style=for-the-badge" />
  </a>

  <a href="../../README.md" style="margin-right: 10px;">
    <img height="34" src="https://img.shields.io/badge/⌂%20Home-047857?style=for-the-badge" />
  </a>

  <a href="./Events.md" style="margin-right: 10px;">
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
