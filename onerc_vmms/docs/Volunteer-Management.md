## Volunteer Management

The **Volunteer Management** module streamlines the full lifecycle of a volunteer — from registration and onboarding to deployment and post-deployment activities — all integrated seamlessly within ERPNext’s personnel and HR framework.

---

### Overview

Volunteers are treated as **personnel** in the system (a redefined version of the ERPNext _Employee_ doctype) with a distinct `is_volunteer` flag.
This ensures consistency across HR, LMS, and operational modules while preserving the volunteer’s unique engagement flow.

The lifecycle consists of the following major stages:

1. **Registration & Application**
2. **Review & Personnel Conversion**
3. **Onboarding & Training**
4. **Deployment & Attendance**
5. **Post-Deployment Activities**

---

### 1. Volunteer Registration & Application

Volunteers begin their journey via the **Volunteer Portal**.

#### Process

1. The volunteer **visits the online portal** and creates an account.
2. After login, they access and **submit the Volunteer Application Form** — capturing:

   - Personal details (bio data, contact info)
   - Skills, interests, and experience
   - Location info
   - Branch selection (mapped to ERPNext _Company_)

3. Upon submission, the record is created in the **Personnel Applicant** doctype
   _(a renamed version of the ERPNext **Job Applicant** doctype)_.

#### Notes

- Automated notifications can be configured to alert HR or branch coordinators upon submission.

---

### 2. Application Review & Personnel Creation

After submission, administrators review the application.

- HR or authorized staff can verify applicant details and supporting documents.
- Once approved, the system allows conversion into a **Personnel** record
  _(formerly Employee, with the `is_volunteer` flag set to `1`)_.
- This conversion automatically links the applicant to their originating branch (Company).

---

### 3. Onboarding & Training

After creation, the volunteer enters the **Personnel Onboarding** phase — an enhanced version of ERPNext’s onboarding process, fully integrated with **Learning Management System (LMS)** features.

#### Features

- Each onboarding activity can be linked to a **Course** (via LMS Course Doctype).
- When a course-linked activity is assigned, the system **automatically enrolls the volunteer**.
- Onboarding activities may include:

  - Orientation or induction courses
  - Code of conduct acknowledgments
  - Safety and preparedness training
  - Documentation verification

---

### 4. Deployment Lifecycle

Once onboarding is complete, volunteers are ready for **deployment**.
Deployment management integrates multiple doctypes and tools to ensure structured mobilization and accountability.

#### a. Availability Setup

Volunteers use the portal to define their **availability**, specifying preferred timeframes.

This availability information becomes the foundation for matching during deployment requests.

#### b. Terms of Reference (TOR)

Each deployment begins with a **Personnel Terms of Reference (TOR)** document, defining:

- Assignment Approach, Objectives & Outputs
- Duration
- Stakeholders Involved
- Itinerary & Resources

The TOR serves as the authoritative framework for the volunteer’s engagement.

#### c. Project Initiation

A **Project** is created from the TOR, enabling:

- Resource planning
- Timeline management
- Integration with other project-related modules in ERPNext

#### d. Deployment Request Tool

Deployment requests are managed using the **Personnel Deployment Request Tool**.

- HR or project managers can **filter volunteers** based on various criteria

- Matching volunteers are automatically retrieved and notified.

Each request is stored under the **Personnel Deployment Request** doctype.

#### e. Volunteer Response & Approval

- Volunteers view incoming deployment requests via the portal.
- They can **Accept** or **Decline** directly online.
- Accepted deployments proceed to review and approval by HR or deployment managers.
- Once approved, the volunteer is **officially deployed**.

#### f. Post-Deployment Operations

During active deployment:

- Volunteers **mark attendance** daily or per assignment.
- **Expense Claims** and **Advances** can be submitted directly against the deployment.
- Supervisors can review attendance, approve claims, and record performance notes.

---

### 5. Extended Volunteer Access & HR Integration

Volunteers, once onboarded, gain access to multiple standard ERPNext modules — consistent with full-time personnel but scoped to their volunteer role.

#### Access Includes

- **Learning Management System (LMS)**
  Access to ongoing training and certifications.
- **Helpdesk / Ticketing System**
  Volunteers can raise support requests.
- **Community & Collaboration**
  Integration with **Raven** (Frappe’s chat/community platform) enables volunteers to join discussion groups, projects, and local chapters.
- **HR Features**
  Personal profile management, document uploads, leave applications (if enabled), and notifications.

## Related Documents

- [User](./doctypes/User.md)
- [Personnel](./doctypes/Personnel.md)
- [Settings](./doctypes/Settings.md)
- [Deployment Tool](./Deployment-Tool.md)
- [Deployment Terms of Reference](./doctypes/TOR.md)
- [Opportunity Applicant](./doctypes/Opportunity-Applicant.md)

## Navigation

<div style="display: flex; align-items: center;">

  <a href="../../README.md" style="margin-right: 10px;">
    <img height="34" src="https://img.shields.io/badge/⌂%20Home-047857?style=for-the-badge" />
  </a>

  <a href="Membership-Management.md" style="margin-right: 10px;">
    <img height="34" src="https://img.shields.io/badge/Next%20→-6D28D9?style=for-the-badge" />
  </a>

</div>

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

[![Full Documentation](https://img.shields.io/badge/Full_Documentation-6366F1?style=for-the-badge&logo=readthedocs&logoColor=fff)](https://github.com/kenyaredcross/onerc_vmms/wiki)
[![ERPNext Docs](https://img.shields.io/badge/ERPNext_Docs-FF6B6B?style=for-the-badge&logo=erpnext&logoColor=fff)](https://docs.erpnext.com)
[![Frappe Framework](https://img.shields.io/badge/Frappe_Framework-00C49A?style=for-the-badge&logo=frappe&logoColor=fff)](https://frappeframework.com/docs)
[![Community Forum](https://img.shields.io/badge/Community_Forum-F59E0B?style=for-the-badge&logo=discourse&logoColor=fff)](https://discuss.frappe.io)
[![Report Issue](https://img.shields.io/badge/Report_Issue-E63946?style=for-the-badge&logo=githubissues&logoColor=fff)](https://github.com/kenyaredcross/onerc_vmms.git/issues)
[![Website](https://img.shields.io/badge/Website-1E293B?style=for-the-badge&logo=googlechrome&logoColor=fff)](https://navari.co.ke)
