# User

The **User** doctype has been extended to support comprehensive volunteer and personnel management capabilities. These enhancements provide detailed profile information, qualifications tracking, and location data essential for managing both staff and volunteers within the Volunteer and Member Management System (VMMS).

## Key Features

The **User** doctype has been extended to capture richer personal, professional, and health information. This includes detailed bio data, qualifications, skills, work experience, and location details.

These enhancements allow users to maintain up-to-date profiles that reflect their current competencies, certifications, and availability. The system can automatically fetch this information to **build resumes or profiles** for applications, volunteer engagement, and internal opportunity tracking, ensuring consistency and reducing repetitive data entry.

Additionally, the extended profile supports dynamic updates, enabling users to continually refine their personal and professional information over time.

![Useer Overview](../images/user/user.png)

## Extended Profile Information

### Personal Details

| Field                          | Type   | Description                               |
| ------------------------------ | ------ | ----------------------------------------- |
| **Marital Status**             | Select | Single, Married, Divorced, Widowed, Other |
| **Number of Dependants**       | Int    | Number of dependant family members        |
| **Consent to Use of Bio Data** | Check  | Permission for biometric data processing  |

![Profile Overview](../images/user/profile.png)

## Address & Location Details

| Field                       | Type   | Description                               |
| --------------------------- | ------ | ----------------------------------------- |
| **LGA**                     | Link   | Administrative LGA                        |
| **District**                | Link   | District administrative division          |
| **Access to Internet**      | Select | Internet availability: Yes, No, Sometimes |
| **Administrative Location** | Link   | Specific administrative location          |
| **Ward**                    | Link   | Local ward information                    |

![Location Overview](../images/user/location.png)

## Citizenship & Identification

| Field                      | Type   | Description                                   |
| -------------------------- | ------ | --------------------------------------------- |
| **Citizenship**            | Select | Citizen, Non-citizen, Refugee, Migrant, Other |
| **Identification Type**    | Link   | Type of identification document               |
| **ID Number**              | Data   | National identification number                |
| **Country of Citizenship** | Link   | Country of citizenship                        |

![Citizenship Overview](../images/user/citizenship.png)

---

## Language & Health Information

### Language Details

| Field         | Type              | Description              |
| ------------- | ----------------- | ------------------------ |
| **Languages** | Table MultiSelect | Languages spoken by user |

![Language Overview](../images/user/language.png)

### Health Information

| Field            | Type  | Description                               |
| ---------------- | ----- | ----------------------------------------- |
| **Blood Group**  | Data  | Blood type information                    |
| **Allergies**    | Table | Medical allergies and reactions           |
| **Disabilities** | Table | Disability information and accommodations |

![Health Overview](../images/user/health.png)

---

## Qualifications & Skills

### Education Details

| Field          | Type  | Description                         |
| -------------- | ----- | ----------------------------------- |
| **Profession** | Link  | Professional field or occupation    |
| **Education**  | Table | Academic qualifications and degrees |

![Education Overview](../images/user/education.png)

### Skills & Certifications

| Field                 | Type              | Description                                 |
| --------------------- | ----------------- | ------------------------------------------- |
| **Skill**             | Table             | User skills and competencies                |
| **Additional Skills** | Table             | Supplementary skills and qualifications     |
| **Driving Licence**   | Table MultiSelect | Valid driving licence categories            |
| **Certification**     | Table             | Professional certifications and credentials |
| **Courses**           | Table             | Professional courses and training           |

![Skils Overview](../images/user/courses.png)

---

## Work Experience & References

| Field               | Type  | Description                          |
| ------------------- | ----- | ------------------------------------ |
| **Work Experience** | Table | Employment history and positions     |
| **Work References** | Table | Professional references and contacts |

![Work Overview](../images/user/work.png)

---

## Supporting Documents

| Field                    | Type  | Description                   |
| ------------------------ | ----- | ----------------------------- |
| **Supporting Documents** | Table | Additional required documents |

![Documents Overview](../images/user/documents.png)

## Navigation

<div style="display: flex; align-items: center;">

  <a href="../../../README.md" style="margin-right: 10px;">
    <img height="34" src="https://img.shields.io/badge/⌂%20Home-047857?style=for-the-badge" />
  </a>

  <a href="./Personnel.md" style="margin-right: 10px;">
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
