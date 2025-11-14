# Personnel

The **Personnel** DocType is a **renamed and transitioned** version of the original **Employee** DocType.
Rather than introducing a new structure, it extends and simplifies the existing one to support both **staff** and **volunteers** within the same framework.
This transition maintains all existing employee data while adding flexibility for volunteer management.

---

## Features

### 1. **Volunteer Identification**

A new flag enables each Personnel record to be marked as a volunteer.

- **Field Name:** `is_volunteer`
- **Label:** **Is Volunteer**
- **Type:** Checkbox

When enabled, the record represents a **volunteer** instead of a paid employee.
This allows both categories to coexist within the same doctype, reducing duplication and ensuring smooth reporting across the organization.

---

### 2. **Conditional Salary Visibility**

All salary-related sections and fields are **automatically hidden** for volunteers.

**Condition Example:**

```js
depends_on: eval: doc.is_volunteer != 1;
```

This ensures:

- Payroll information is visible **only for salaried personnel**.
- Volunteer records remain **focused on non-financial data** like deployments and roles.

---

## Navigation

<div style="display: flex; align-items: center;">

  <a href="./User.md" style="margin-right: 10px;">
    <img height="34" src="https://img.shields.io/badge/←%20Previous-1E3A8A?style=for-the-badge" />
  </a>

  <a href="../../../README.md" style="margin-right: 10px;">
    <img height="34" src="https://img.shields.io/badge/⌂%20Home-047857?style=for-the-badge" />
  </a>

  <a href="./Settings.md" style="margin-right: 10px;">
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
