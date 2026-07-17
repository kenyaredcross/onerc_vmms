app_name = "onerc_vmms"
app_title = "Volunteer and Member Management"
app_publisher = "Kenya Red Cross Society"
app_description = "Volunteer and Member Management"
app_email = "digital@redcross.or.ke"
app_license = "gpl-3.0"

# Apps
# ------------------

required_apps = ["erpnext", "lms", "hrms"]


add_to_apps_screen = [
	{
		"name": "vmms",
		"logo": "/assets/onerc_vmms/frontend/vmms.png",
		"title": "VMMS",
		"route": "/vmms",
		"has_permission": "onerc_vmms.volunteer_and_member_management.api.permission.check_app_permission",
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/onerc_vmms/css/onerc_vmms.css"
# app_include_js = "/assets/onerc_vmms/js/onerc_vmms.js"

# include js, css files in header of web template
# web_include_css = "/assets/onerc_vmms/css/onerc_vmms.css"
# web_include_js = "/assets/onerc_vmms/js/onerc_vmms.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "onerc_vmms/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	# "Project": "volunteer_and_member_management/overrides/client/project.js",
	"Attendance": "volunteer_and_member_management/overrides/client/attendance.js",
	"Employee Advance": "volunteer_and_member_management/overrides/client/employee_advance.js",
	"Expense Claim": "volunteer_and_member_management/overrides/client/expense_claim.js",
	"Timesheet": "volunteer_and_member_management/overrides/client/timesheet.js",
	"Job Opening": "volunteer_and_member_management/overrides/client/job_opening.js",
	"Employee Onboarding": "volunteer_and_member_management/overrides/client/employee_onboarding.js",
	"Employee": "volunteer_and_member_management/overrides/client/employee.js",
	"Job Applicant": "volunteer_and_member_management/overrides/client/job_applicant.js",
	"Contract": "volunteer_and_member_management/overrides/client/contract.js",
	"Interview": "volunteer_and_member_management/overrides/client/interview.js",
	"Interview Round": "volunteer_and_member_management/overrides/client/interview_round.js",
}

doctype_list_js = {"Job Applicant": "volunteer_and_member_management/overrides/client/job_applicant_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "onerc_vmms/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# ALL users (guests and logged-in) start at the OneRC portal
home_page = "index"

# website user home page (by Role)
# Everyone starts at the portal page
role_home_page = {
	"Guest": "index",
	"System User": "index",
}

# All users see the OneRC portal landing page first
# They can then navigate to VMMS or other services from there

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "onerc_vmms.utils.jinja_methods",
# 	"filters": "onerc_vmms.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "onerc_vmms.install.before_install"
# after_install = "onerc_vmms.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "onerc_vmms.uninstall.before_uninstall"
# after_uninstall = "onerc_vmms.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "onerc_vmms.utils.before_app_install"
# after_app_install = "onerc_vmms.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "onerc_vmms.utils.before_app_uninstall"
# after_app_uninstall = "onerc_vmms.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "onerc_vmms.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"LMS Enrollment": {
		"on_update": "onerc_vmms.volunteer_and_member_management.overrides.server.lms_enrollment.on_update"
	},
	"Employee": {
		"after_insert": "onerc_vmms.volunteer_and_member_management.overrides.server.employee.after_insert"
	},
	"Employee Onboarding": {
		"on_update": "onerc_vmms.volunteer_and_member_management.overrides.server.employee_onboarding.on_update",
		"on_update_after_submit": "onerc_vmms.volunteer_and_member_management.overrides.server.employee_onboarding.on_update_after_submit",
	},
	"Job Opening": {
		"validate": "onerc_vmms.volunteer_and_member_management.overrides.server.job_opening.validate"
	},
	"GL Entry": {
		"after_insert": "onerc_vmms.volunteer_and_member_management.overrides.server.gl_entry.on_update",
	},
	"Job Applicant": {
		"before_submit": "onerc_vmms.volunteer_and_member_management.overrides.server.job_applicant.before_submit",
		"on_submit": "onerc_vmms.volunteer_and_member_management.overrides.server.job_applicant.on_submit",
		"validate": "onerc_vmms.volunteer_and_member_management.overrides.server.job_applicant.validate",
	},
	"Language": {
		"before_naming": "onerc_vmms.volunteer_and_member_management.overrides.server.language.before_validate"
	},
	"User": {"on_update": "onerc_vmms.volunteer_and_member_management.overrides.server.user.on_update"},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"onerc_vmms.volunteer_and_member_management.doctype.vm_membership.vm_membership.set_expired_status",
		"onerc_vmms.volunteer_and_member_management.overrides.server.job_opening.send_opportunity_applicant_rejections",
		"onerc_vmms.volunteer_and_member_management.doctype.deployment_request_tool.deployment_request_tool.deploy_future_requests",
	],
	"cron": {
		"*/1 * * * *": ["onerc_vmms.volunteer_and_member_management.overrides.server.email.email_flush"],
	},
}

# Testing
# -------

# before_tests = "onerc_vmms.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "onerc_vmms.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "onerc_vmms.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["onerc_vmms.utils.before_request"]
# after_request = ["onerc_vmms.utils.after_request"]

# Job Events
# ----------
# before_job = ["onerc_vmms.utils.before_job"]
# after_job = ["onerc_vmms.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"onerc_vmms.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

website_route_rules = [
	{"from_route": "/vmms/<path:app_path>", "to_route": "vmms"},
]


fixtures = [
	{
		"doctype": "Role",
		"filters": [
			["name", "=", "Vmms Guest"],
		],
	},
]
