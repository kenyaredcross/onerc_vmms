# Deployment Request Tool

The **Deployment Request Tool** is a Doctype used to plan, filter, and initiate personnel or volunteer deployments.
It connects project tasks, terms of reference, locations, and personnel selection filters — allowing administrators to identify, assign, and manage deployments efficiently.

---

## Core Workflow

1. **Create a Deployment Request**

   - Select the project, task, and location.
   - Define expected start and end dates.
   - Specify the number of volunteers required.

2. **Attach the Terms of Reference (TOR)**

   - Provides mission objectives, itinerary, and any resource needs.

3. **Filter and Select Personnel**

   - Use quick and advanced filters to shortlist suitable candidates.

4. **Send Requests**

   - Use the **“Send Requests”** button to issue deployment invitations to selected volunteers.
     This action automatically creates **Personnel Deployment Requests** for each selected individual.

5. **Review and Approve**

   - Once responses are received, admins can finalize and approve deployments.

---

## Key Fields

| Field                                  | Type                                | Description                                     |
| -------------------------------------- | ----------------------------------- | ----------------------------------------------- |
| **Project**                            | Link (Project)                      | The project linked to this deployment.          |
| **Task**                               | Link (Task)                         | Specific task under the project.                |
| **Specific Deployment Location**       | Link (Location)                     | Exact site or facility for deployment.          |
| **Expected Start / End Date**          | Datetime                            | Duration for which personnel are required.      |
| **Company / Branch**                   | Link (Company)                      | Branch or company managing the deployment.      |
| **Number of Volunteers Required**      | Int                                 | Expected personnel count.                       |
| **Require Contract Before Deployment** | Check                               | Enforces contract generation before deployment. |
| **Terms of Reference**                 | Link (Personnel Terms of Reference) | Defines objectives and scope.                   |
| **Notes**                              | Text Editor                         | Additional remarks or instructions.             |

---

## Filtering & Selection

The Deployment Request Tool includes **Quick Filters** and **Advanced Filters** to target suitable personnel.

### Quick Filters

Used for broad matching:

- Region
- Branch (County of Membership)
- Personnel Type
- Designation
- County / Subcounty / Ward
- Courses, Skills, Licenses

### Advanced Filters

Provides fine-grained search using saved **Volunteer Deployment Criteria**, configured through a custom HTML interface.

### Personnel Selection

Filtered personnel are listed under **Employee List**, allowing admins to:

- View candidate details
- Select volunteers for deployment
- Send requests or notifications

---

## Navigation

<div style="display: flex; align-items: center;">

  <a href="./Settings.md" style="margin-right: 10px;">
    <img height="34" src="https://img.shields.io/badge/←%20Previous-1E3A8A?style=for-the-badge" />
  </a>

  <a href="../../../README.md" style="margin-right: 10px;">
    <img height="34" src="https://img.shields.io/badge/⌂%20Home-047857?style=for-the-badge" />
  </a>

  <a href="./TOR.md" style="margin-right: 10px;">
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
