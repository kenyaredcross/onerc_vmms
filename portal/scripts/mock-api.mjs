#!/usr/bin/env node
/**
 * A stand-in for the Frappe backend, for previewing and screenshotting portal
 * screens without a populated login.
 *
 * It answers `GET /api/method/<dotted.name>` with `{ message: <canned> }`. The
 * data is synthetic — a Tanzania-flavoured volunteer named in the supplied
 * prototype — and is clearly labelled as such wherever it could be mistaken for
 * real. Nothing here writes anything; POSTs echo `{ message: {} }`.
 *
 * Run:  node portal/scripts/mock-api.mjs [--port 9977]
 * Point Vite's preview entry at it (see portal/src/preview/main.tsx).
 */

import http from "node:http";

const port = Number(process.argv.find((a) => a.startsWith("--port="))?.slice(7) ?? 9977);

const TODAY = new Date();
const iso = (offsetDays) => {
	const d = new Date(TODAY);
	d.setDate(d.getDate() + offsetDays);
	return d.toISOString().slice(0, 10);
};

/* --------------------------------------------------- synthetic demo data */

const VOLUNTEER = {
	volunteer: "VOL-00011",
	red_profile: "RP-00011",
	full_name: "Nigel Nathan",
	email: "nigel@example.org",
	phone: "0712 444 444",
	gender: "Male",
	date_of_birth: "1994-05-02",
	preferred_language: "English",
	profile_photo: null,
	status: "Active",
	joined_on: iso(-3),
	exited_on: null,
	geo_node: "GEO-ARUSHA-CITY",
	// Core renders `get_full_path` deepest-first: leaf, then up to the society.
	geo_path: "Arusha City — Arusha — Tanzania Red Cross Society",
	home_geo_node: "GEO-ARUSHA",
	home_geo_path: "Arusha — Tanzania Red Cross Society",
};

const CANNED = {
	"frappe.auth.get_logged_user": "nigel@example.org",

	"vmmsx.api.volunteer.my_volunteer": VOLUNTEER,
	"vmmsx.api.registration.my_profile": {
		red_profile: "RP-00011",
		first_name: "Nigel",
		last_name: "Nathan",
		full_name: "Nigel Nathan",
		email: "nigel@example.org",
		phone: "0712 444 444",
		gender: "Male",
		date_of_birth: "1994-05-02",
		preferred_language: "English",
		profile_photo: null,
		country_of_citizenship: "Tanzania",
		citizenship_status: "Citizen",
		residency_type: "Local",
		home_geo_node: "GEO-ARUSHA",
		country_of_residence: "Tanzania",
		residence_address: "",
		identifications: [],
	},

	"vmmsx.api.registration.my_open_registrations": {},

	"vmmsx.api.member.my_memberships": [
		{
			name: "MSHP-00012",
			member: "MEM-00011",
			member_name: "Nigel Nathan",
			membership_type: "ordinary-member",
			membership_type_name: "Ordinary Member",
			membership_status: "Active",
			is_active: true,
			approval_state: "Approved",
			approval_settled: true,
			payment_settled: true,
			requires_approver: false,
			is_lifetime: false,
			fee: { amount: 10000, currency: "TZS" },
			geo_node: "GEO-ARUSHA-CITY",
			geo_path: "Arusha City — Arusha — Tanzania Red Cross Society",
			valid_from: iso(-120),
			valid_to: iso(245),
			paid_on: iso(-120),
			payment_receipt: null,
			payment_transaction: null,
			membership_source: "Self service",
			certificate_available: true,
			renewable: false,
		},
	],

	"vmmsx.api.member.membership_types": {
		types: [
			{
				known: true,
				membership_type: "youth-in-school",
				membership_type_name: "Youth In School",
				description: "Annual youth membership for students.",
				amount: 1000,
				currency: "TZS",
				free: false,
				is_lifetime: false,
				duration_days: 365,
				requires_approver: false,
				benefits: [
					{ key: "certificate", label: "Youth membership certificate", description: null },
					{ key: "events", label: "Invitations to special events", description: null },
					{ key: "activities", label: "Take part in branch activities", description: null },
				],
			},
			{
				known: true,
				membership_type: "youth-out-of-school",
				membership_type_name: "Youth Out Of School",
				description: "Annual youth membership for young adults.",
				amount: 5000,
				currency: "TZS",
				free: false,
				is_lifetime: false,
				duration_days: 365,
				requires_approver: false,
				benefits: [
					{ key: "certificate", label: "Youth membership certificate", description: null },
					{ key: "events", label: "Invitations to special events", description: null },
					{ key: "activities", label: "Take part in branch activities", description: null },
					{ key: "register", label: "Listed in the branch register", description: null },
				],
			},
			{
				known: true,
				membership_type: "ordinary-member",
				membership_type_name: "Ordinary Member",
				description: "The society's standing annual membership.",
				amount: 10000,
				currency: "TZS",
				free: false,
				is_lifetime: false,
				duration_days: 365,
				requires_approver: false,
				benefits: [
					{ key: "certificate", label: "Ordinary membership certificate", description: null },
					{ key: "events", label: "Invitations to special events", description: null },
					{ key: "activities", label: "Take part in branch activities", description: null },
					{ key: "register", label: "Listed in the branch register", description: null },
				],
			},
			{
				known: true,
				membership_type: "life-member",
				membership_type_name: "Life Member",
				description: "Lifetime membership, with no renewals.",
				amount: 50000,
				currency: "TZS",
				free: false,
				is_lifetime: true,
				duration_days: 0,
				requires_approver: true,
				benefits: [
					{ key: "certificate", label: "Life membership certificate", description: null },
					{ key: "life-day", label: "Invitation to Life Members Day", description: null },
					{ key: "activities", label: "Take part in branch activities", description: null },
					{ key: "register", label: "Listed in the branch register", description: null },
					{ key: "governance", label: "Vote or stand for governance positions", description: null },
				],
			},
		],
	},

	"vmmsx.api.volunteer.my_certifications": {
		volunteer: "VOL-00011",
		as_of: iso(0),
		status: "Active",
		deployable: true,
		blocking_reasons: [],
		certifications: [
			{
				name: "CERT-1",
				certification_type: "basic-first-aid",
				certification_type_name: "Basic First Aid",
				completion_date: iso(-360),
				expiry_date: iso(18),
				reference_number: "BFA-2211",
				lapsed: false,
				blocks_deployment: true,
			},
			{
				name: "CERT-2",
				certification_type: "community-mobilisation",
				certification_type_name: "Community mobilisation",
				completion_date: iso(-120),
				expiry_date: iso(400),
				reference_number: null,
				lapsed: false,
				blocks_deployment: false,
			},
		],
	},

	"vmmsx.api.volunteer.my_time_logs": {
		volunteer: "VOL-00011",
		total_hours: 96,
		log_count: 3,
		hours_by_type: { "Deployment service": 96 },
		recent: [
			{
				name: "TL-1",
				log_type: "Deployment service",
				log_category: "field",
				category_label: "Field work",
				deployment: "DEP-0031",
				geo_node: "Zanzibar Urban",
				geo_path: "Zanzibar Urban — Zanzibar — Tanzania Red Cross Society",
				activity_date: iso(-190),
				hours: 96,
				notes: null,
			},
		],
	},

	"vmmsx.api.tasks.my_tasks": {
		volunteer: "VOL-00011",
		tasks: [
			{
				name: "TASK-0007",
				subject: "Household assessment forms — Kyela ward 4",
				status: "accepted",
				volunteer: "VOL-00011",
				geo_node: "GEO-RUNGWE",
				due_on: iso(1),
				assigned_on: iso(-4),
				open_question: false,
				is_open: true,
				due_at: `${iso(1)} 17:00:00`,
				priority: "Normal",
				task_type: "Field evidence",
				percent_complete: 40,
				is_overdue: false,
			},
			{
				name: "TASK-0008",
				subject: "Submit branch first-aid kit inventory",
				status: "accepted",
				volunteer: "VOL-00011",
				geo_node: "GEO-ARUSHA-CITY",
				due_on: iso(-6),
				assigned_on: iso(-12),
				open_question: true,
				is_open: true,
				due_at: `${iso(-6)} 17:00:00`,
				priority: "High",
				task_type: "Record update",
				percent_complete: 10,
				is_overdue: true,
			},
			{
				name: "TASK-0009",
				subject: "Confirm transport for the Sep 12 induction",
				status: "assigned",
				volunteer: "VOL-00011",
				geo_node: "GEO-ARUSHA-CITY",
				due_on: iso(4),
				assigned_on: iso(-1),
				open_question: false,
				is_open: true,
				due_at: `${iso(4)} 17:00:00`,
				priority: "Normal",
				task_type: "Deployment response",
				percent_complete: 0,
				is_overdue: false,
			},
			{
				name: "TASK-0010",
				subject: "Prepare the demonstration kit for World First Aid Day",
				status: "submitted",
				volunteer: "VOL-00011",
				geo_node: "GEO-ARUSHA-CITY",
				due_on: iso(9),
				assigned_on: iso(-5),
				open_question: false,
				is_open: true,
				due_at: `${iso(9)} 17:00:00`,
				priority: "Normal",
				task_type: "Field evidence",
				percent_complete: 100,
				is_overdue: false,
			},
			{
				name: "TASK-0006",
				subject: "Read the updated volunteer code of conduct",
				status: "completed",
				volunteer: "VOL-00011",
				geo_node: "GEO-ARUSHA-CITY",
				due_on: null,
				assigned_on: iso(-30),
				open_question: false,
				is_open: false,
				due_at: null,
				priority: "Low",
				task_type: "Required training",
				percent_complete: 100,
				is_overdue: false,
			},
			{
				name: "TASK-0003",
				subject: "Distribute safe-water leaflets — Kyela ward 2",
				status: "completed",
				volunteer: "VOL-00011",
				geo_node: "Zanzibar Urban",
				due_on: "2026-04-30",
				assigned_on: "2026-04-20",
				open_question: false,
				is_open: false,
				due_at: `${"2026-04-30"} 17:00:00`,
				priority: "Normal",
				task_type: "Field evidence",
				percent_complete: 100,
				is_overdue: false,
			},
		],
	},

	"vmmsx.api.deployment.my_invitations": {
		volunteer: "VOL-00011",
		waiting: [
			{
				assignment: "ASG-0001",
				deployment: "DEP-0042",
				title: "Rungwe Flood Response — Wave 3",
				terms_of_reference: "TOR-0009",
				deployment_status: "Planned",
				start_date: iso(15),
				end_date: iso(26),
				geo_node: "Rungwe District",
				notes:
					"Support household health screening, safe-water messaging and referral of urgent cases across six wards.",
				response: "Pending",
				role: "Community Health Volunteer",
				invited_on: iso(-1),
				responded_on: null,
				response_note: null,
			},
		],
		answered: [
			{
				assignment: "ASG-0002",
				deployment: "DEP-0040",
				title: "World First Aid Day — public demonstration",
				terms_of_reference: "TOR-0008",
				deployment_status: "Planned",
				start_date: iso(11),
				// A multi-day run, so the preview exercises the continuous mission
				// strip the concept draws across a deployment's own days.
				end_date: iso(19),
				geo_node: "GEO-ARUSHA-CITY",
				notes: null,
				response: "Accepted",
				role: "Demonstrator",
				invited_on: iso(-6),
				responded_on: iso(-5),
				response_note: null,
			},
			{
				assignment: "ASG-0000",
				deployment: "DEP-0031",
				title: "Zanzibar Heatwave Awareness",
				terms_of_reference: "TOR-0004",
				deployment_status: "Completed",
				start_date: iso(-200),
				end_date: iso(-188),
				geo_node: "Zanzibar Urban",
				notes: null,
				response: "Accepted",
				role: "Community Mobiliser",
				invited_on: iso(-220),
				responded_on: iso(-210),
				response_note: null,
			},
		],
	},

	"vmmsx.api.events.upcoming": {
		available: true,
		events: [
			{
				event: "EVT-101",
				title: "Psychological First Aid refresher",
				summary: "A practical half-day refresher for people who already hold the certificate.",
				category: "Training",
				venue: "Online",
				medium: "Online",
				start_date: iso(2),
				end_date: iso(2),
				start_time: "14:00:00",
				end_time: "17:00:00",
				time_zone: "Africa/Dar_es_Salaam",
				image: "",
				geo_node: "",
				href: null,
				multi_day: false,
			},
			{
				event: "EVT-102",
				title: "Arusha branch open day",
				summary: "Meet the branch team and see response equipment.",
				category: "Community",
				venue: "Arusha Branch Office",
				medium: "In person",
				start_date: iso(8),
				end_date: iso(8),
				start_time: "10:00:00",
				end_time: "15:00:00",
				time_zone: "Africa/Dar_es_Salaam",
				image: "",
				geo_node: "",
				href: null,
				multi_day: false,
			},
			{
				event: "EVT-103",
				title: "Community cholera prevention forum",
				summary: "A public session on safe water and early warning signs.",
				category: "Public health",
				venue: "Kigoma Community Hall",
				medium: "In person",
				start_date: iso(13),
				end_date: iso(13),
				start_time: "09:30:00",
				end_time: "12:30:00",
				time_zone: "Africa/Dar_es_Salaam",
				image: "",
				geo_node: "",
				href: null,
				multi_day: false,
			},
		],
	},

	"vmmsx.api.events.calendar": {
		available: true,
		attending: ["EVT-101", "EVT-201"],
		events: [
			{
				event: "EVT-101",
				title: "Psychological First Aid refresher",
				summary: "",
				category: "Training",
				venue: "Online",
				medium: "Online",
				start_date: iso(2),
				end_date: iso(2),
				start_time: "14:00:00",
				end_time: "17:00:00",
				time_zone: "Africa/Dar_es_Salaam",
				image: "",
				geo_node: "",
				href: null,
				multi_day: false,
			},
			{
				event: "EVT-201",
				title: "Arusha branch first-aid demonstration",
				summary: "",
				category: "Community",
				venue: "Arusha Branch Office",
				medium: "In person",
				start_date: iso(-4),
				end_date: iso(-4),
				start_time: "09:00:00",
				end_time: "12:00:00",
				time_zone: "Africa/Dar_es_Salaam",
				image: "",
				geo_node: "",
				href: null,
				multi_day: false,
			},
		],
	},

	"vmmsx.api.notifications.unread_count": { unread: 3 },
	"vmmsx.api.notifications.my_notifications": {
		unread: 3,
		notifications: [
			{
				id: "N1",
				source: "announcement",
				title: "New deployment request",
				summary: "Rungwe Flood Response — review the terms of reference and respond.",
				body: "",
				urgency: "urgent",
				rank: 1,
				label: "Deployment",
				geo_node: "",
				sent_on: iso(-1),
				read: false,
				link_label: "Review",
				href: "/deployments",
			},
			{
				id: "N2",
				source: "log",
				title: "Changes requested on your task",
				summary: "Household assessment forms — Kyela ward 4",
				body: "",
				urgency: "important",
				rank: 2,
				label: "Task",
				geo_node: "",
				sent_on: iso(-2),
				read: false,
				link_label: "Open",
				href: "/tasks",
			},
			{
				id: "N3",
				source: "log",
				title: "Membership payment confirmed",
				summary: "Your Arusha City membership remains active through December.",
				body: "",
				urgency: "routine",
				rank: 3,
				label: "Membership",
				geo_node: "",
				sent_on: iso(-4),
				read: true,
				link_label: "",
				href: "",
			},
		],
	},

	// The console, open, with every section this build draws — including the two
	// new ones. The preview harness is the only place the console can be seen
	// without a bench, and a console answering `available: false` would mean the
	// admin routes could never be captured.
	"vmmsx.api.console.sections": {
		available: true,
		sections: [
			"overview",
			"queue",
			"recruitment",
			"registry",
			"tasks",
			"deployments",
			"finance",
			"stipends",
			"events",
			"analytics",
			"communication",
			"content",
			"questions",
		],
		desk: true,
		sms: true,
	},
	"vmmsx.api.approvals.my_queue": [
		{ doctype: "VMMS Volunteer Application", name: "VAPP-00214", subject: "Neema Mtei", stage: { label: "Branch review", is_breached: true, days_overdue: 4 }, state: "In Review", modified: "2026-08-27" },
		{ doctype: "VMMS Volunteer Application", name: "VAPP-00213", subject: "Baraka Msuya", stage: { label: "Branch review", is_breached: false }, state: "Submitted", modified: "2026-08-29" },
		{ doctype: "VMMS Membership", name: "MSHIP-00415", subject: "Zawadi Lyimo", stage: { label: "Proof review", is_breached: false }, state: "In Review", modified: "2026-08-30" },
	],
	"vmmsx.api.volunteer.find_volunteers": { count: 1284, total: 1284, volunteers: [] },
	"vmmsx.api.member.find_members": { count: 862, total: 862, member_count: 862, members: [] },
	"vmmsx.api.analytics.branch_summary": {
		trend: (() => {
			const out = [];
			const now = new Date();
			for (let back = 11; back >= 0; back -= 1) {
				const date = new Date(now.getFullYear(), now.getMonth() - back, 1);
				out.push({
					month: `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`,
					volunteers: 18 + Math.round(Math.sin(back / 1.7) * 11) + back,
					members: 26 + Math.round(Math.cos(back / 2.3) * 14),
				});
			}
			return out;
		})(),
		volunteers: { total: 1284, by_status: { Active: 1121, Suspended: 24, Exited: 139 } },
		members: { total: 862, by_status: { Active: 704, Expired: 121, Cancelled: 37 } },
		tasks: { open: 46, awaiting_sign_off: 9, overdue: 7 },
		coverage: [
			{ geo_node: "GEO-0021", label: "Ubungo", volunteers: 412, members: 288 },
			{ geo_node: "GEO-0022", label: "Kinondoni", volunteers: 366, members: 241 },
			{ geo_node: "GEO-0031", label: "Kilombero", volunteers: 258, members: 174 },
			{ geo_node: "GEO-0034", label: "Ifakara", volunteers: 149, members: 96 },
			{ geo_node: "GEO-0040", label: "Morogoro Urban", volunteers: 99, members: 63 },
		],
	},

	// ------------------------------------------------------------- finance
	// One currency, twelve months, and a shape with a story in it: membership
	// income rising into the renewal season while stipend expenditure tracks the
	// deployments. The caveats on the screen are about the *derivation*, and
	// they hold for synthetic data exactly as they do for real.
	"vmmsx.api.finance.summary": (() => {
		const months = [];
		const income = {};
		const expenses = {};
		const now = new Date();

		for (let back = 11; back >= 0; back -= 1) {
			const date = new Date(now.getFullYear(), now.getMonth() - back, 1);
			const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
			const inAmount = 1_450_000 + Math.round(Math.sin(back / 2) * 520_000) + back * 40_000;
			const outAmount = 890_000 + Math.round(Math.cos(back / 3) * 340_000);

			income[key] = inAmount;
			expenses[key] = outAmount;
			months.push({
				month: key,
				income: [{ currency: "TZS", amount: inAmount }],
				expenses: [{ currency: "TZS", amount: outAmount }],
			});
		}

		const totalIn = Object.values(income).reduce((a, b) => a + b, 0);
		const totalOut = Object.values(expenses).reduce((a, b) => a + b, 0);

		return {
			from_date: months[0].month + "-01",
			to_date: new Date().toISOString().slice(0, 10),
			basis: "published_fee",
			income: {
				totals: [{ currency: "TZS", amount: totalIn }],
				count: 428,
				by_month: {},
				by_type: [
					{ membership_type: "MT-ANNUAL", label: "Annual", count: 286, amount: Math.round(totalIn * 0.62), currency: "TZS", unpriced: false },
					{ membership_type: "MT-LIFE", label: "Life", count: 34, amount: Math.round(totalIn * 0.28), currency: "TZS", unpriced: false },
					{ membership_type: "MT-YOUTH", label: "Youth", count: 96, amount: Math.round(totalIn * 0.10), currency: "TZS", unpriced: false },
					{ membership_type: "MT-HONORARY", label: "Honorary", count: 12, amount: 0, currency: null, unpriced: true },
				],
				recent: [
					{ name: "MSHIP-00412", label: "Annual", paid_on: "2026-08-28", status: "Active", amount: 25000, currency: "TZS" },
					{ name: "MSHIP-00411", label: "Life", paid_on: "2026-08-27", status: "Active", amount: 400000, currency: "TZS" },
					{ name: "MSHIP-00409", label: "Youth", paid_on: "2026-08-26", status: "Active", amount: 10000, currency: "TZS" },
					{ name: "MSHIP-00407", label: "Honorary", paid_on: "2026-08-24", status: "Active", amount: null, currency: null },
					{ name: "MSHIP-00404", label: "Annual", paid_on: "2026-08-21", status: "Active", amount: 25000, currency: "TZS" },
				],
			},
			expenses: {
				totals: [{ currency: "TZS", amount: totalOut }],
				count: 37,
				by_month: {},
				by_state: [
					{ state: "Pending Departmental Approval", count: 24, amount: Math.round(totalOut * 0.71), currency: "TZS" },
					{ state: "Draft", count: 13, amount: Math.round(totalOut * 0.29), currency: "TZS" },
				],
				recent: [
					{ name: "SPF-00037", amount: 1_240_000, currency: "TZS", period_from: "2026-08-01", period_to: "2026-08-31", state: "Draft", progress_report: "SPR-00031" },
					{ name: "SPF-00036", amount: 980_000, currency: "TZS", period_from: "2026-07-01", period_to: "2026-07-31", state: "Pending Departmental Approval", progress_report: "SPR-00029" },
					{ name: "SPF-00035", amount: 1_105_000, currency: "TZS", period_from: "2026-06-01", period_to: "2026-06-30", state: "Pending Departmental Approval", progress_report: "SPR-00026" },
				],
			},
			net: [{ currency: "TZS", income: totalIn, expenses: totalOut, net: totalIn - totalOut }],
			months,
		};
	})(),

	// --------------------------------------------------------- recruitment
	"vmmsx.api.hr.openings": {
		available: true,
		statuses: ["Open", "Closed"],
		openings: [
			{ name: "JOB-2026-0011", job_title: "Community health outreach volunteer", status: "Open", designation: "Community Health Worker", department: "Health", company: "Tanzania Red Cross Society", location: "Kilombero District", vacancies: 12, closes_on: "2026-09-05", purpose: "Volunteer", is_published: true, is_closing: true, url: "/jobs/trcs/community-health", modified: "2026-08-30", pipeline: { total: 34, withdrawn: 2, Open: 11, Shortlisted: 8, Hold: 3, Accepted: 9, Rejected: 1 } },
			{ name: "JOB-2026-0010", job_title: "Logistics officer — flood response", status: "Open", designation: "Logistics Officer", department: "Operations", company: "Tanzania Red Cross Society", location: "Morogoro", vacancies: 2, closes_on: "2026-09-30", purpose: "Employment", is_published: true, is_closing: false, url: "/jobs/trcs/logistics-officer", modified: "2026-08-26", pipeline: { total: 18, withdrawn: 0, Open: 6, Shortlisted: 5, Hold: 2, Accepted: 2, Rejected: 3 } },
			{ name: "JOB-2026-0009", job_title: "First aid trainer", status: "Open", designation: "Trainer", department: "Training", company: "Tanzania Red Cross Society", location: "Dar es Salaam", vacancies: 4, closes_on: null, purpose: "Volunteer", is_published: false, is_closing: false, url: null, modified: "2026-08-14", pipeline: { total: 0, withdrawn: 0, Open: 0, Shortlisted: 0, Hold: 0, Accepted: 0, Rejected: 0 } },
			{ name: "JOB-2026-0006", job_title: "Blood donation drive coordinator", status: "Closed", designation: "Coordinator", department: "Health", company: "Tanzania Red Cross Society", location: "Ubungo", vacancies: 1, closes_on: "2026-07-15", purpose: "Volunteer", is_published: false, is_closing: false, url: null, modified: "2026-07-16", pipeline: { total: 22, withdrawn: 1, Open: 0, Shortlisted: 0, Hold: 0, Accepted: 1, Rejected: 20 } },
		],
		totals: { openings: 4, published: 2, open: 3, applicants: 74, waiting: 17 },
	},
	"vmmsx.api.hr.applicants": {
		available: true,
		statuses: ["Open", "Shortlisted", "Hold", "Accepted", "Rejected"],
		applicants: [
			{ name: "HR-APP-2026-0091", applicant_name: "Amina Hassan", email: "amina.hassan@example.tz", phone: "+255 712 000 001", status: "Open", opening: "JOB-2026-0011", opening_title: "Community health outreach volunteer", applied_on: "2026-08-29", volunteer: "VOL-00231", geo_node: "Kilombero — Morogoro — Tanzania Red Cross Society", is_withdrawn: false },
			{ name: "HR-APP-2026-0090", applicant_name: "Joseph Mwangi", email: "j.mwangi@example.tz", phone: "+255 712 000 002", status: "Shortlisted", opening: "JOB-2026-0010", opening_title: "Logistics officer — flood response", applied_on: "2026-08-28", volunteer: null, geo_node: null, is_withdrawn: false },
			{ name: "HR-APP-2026-0088", applicant_name: "Grace Kimaro", email: "grace.k@example.tz", phone: "+255 712 000 003", status: "Accepted", opening: "JOB-2026-0011", opening_title: "Community health outreach volunteer", applied_on: "2026-08-25", volunteer: "VOL-00198", geo_node: "Ifakara — Morogoro — Tanzania Red Cross Society", is_withdrawn: false },
			{ name: "HR-APP-2026-0085", applicant_name: "Peter Ndulu", email: "p.ndulu@example.tz", phone: "+255 712 000 004", status: "Hold", opening: "JOB-2026-0010", opening_title: "Logistics officer — flood response", applied_on: "2026-08-22", volunteer: null, geo_node: null, is_withdrawn: false },
			{ name: "HR-APP-2026-0081", applicant_name: "Fatuma Said", email: "f.said@example.tz", phone: "+255 712 000 005", status: "Shortlisted", opening: "JOB-2026-0011", opening_title: "Community health outreach volunteer", applied_on: "2026-08-19", volunteer: "VOL-00174", geo_node: "Kilombero — Morogoro — Tanzania Red Cross Society", is_withdrawn: true },
		],
		counts: { total: 5, withdrawn: 1, Open: 1, Shortlisted: 1, Hold: 1, Accepted: 1, Rejected: 0 },
	},
	"vmmsx.api.hr.options": {
		available: true,
		statuses: ["Open", "Closed"],
		purposes: ["Volunteer", "Employment"],
		pipeline: ["Open", "Shortlisted", "Hold", "Accepted", "Rejected"],
		designations: [{ value: "Community Health Worker", label: "Community Health Worker" }, { value: "Logistics Officer", label: "Logistics Officer" }, { value: "Trainer", label: "Trainer" }],
		departments: [{ value: "Health", label: "Health" }, { value: "Operations", label: "Operations" }, { value: "Training", label: "Training" }],
		companies: [{ value: "Tanzania Red Cross Society", label: "Tanzania Red Cross Society" }],
		employment_types: [{ value: "Full-time", label: "Full-time" }, { value: "Part-time", label: "Part-time" }],
		skills: [{ value: "First Aid", label: "First Aid" }, { value: "Community Health", label: "Community Health" }, { value: "Logistics", label: "Logistics" }, { value: "Driving", label: "Driving" }, { value: "Data Collection", label: "Data Collection" }],
		languages: [{ value: "English", label: "English" }, { value: "Kiswahili", label: "Kiswahili" }, { value: "Maasai", label: "Maasai" }],
		projects: [],
	},

	// -------------------------------------------------------- communication
	"vmmsx.api.communication.options": {
		can_send: true,
		audiences: ["everyone", "volunteers", "members"],
		urgencies: ["Normal", "Urgent"],
		channels: { notification: true, email: true, sms: true, whatsapp: true },
		sms_templates: [],
		sms_source_doctypes: [
			{ value: "VMMS Volunteer", label: "Volunteers" },
			{ value: "VMMS Membership", label: "Memberships" },
		],
	},
	"vmmsx.api.communication.preview": { addressed: 2104, notification: 1877, email: 1342, sms: 1988, whatsapp: 1961 },
	"vmmsx.api.geo.ladder": {
		levels: [
			{ level: "Region", label: "Region" },
			{ level: "District", label: "District" },
			{ level: "Ward", label: "Ward" },
		],
	},
	"vmmsx.api.geo.browse": {
		nodes: [
			{ name: "GEO-0002", node_name: "Morogoro", geo_level: "Region" },
			{ name: "GEO-0003", node_name: "Dar es Salaam", geo_level: "Region" },
		],
	},

	// ------------------------------------------------------------- whatsapp
	"vmmsx.api.whatsapp.channel": {
		installed: true,
		configured: true,
		can_send: true,
		enabled: true,
		gateway_url: "http://open-wa:8080",
		session_id: "trcs-broadcast",
		pacing_seconds: 8,
		daily_limit: 900,
		opt_out_notice: "Reply STOP to stop receiving these messages.",
		opt_out_count: 27,
	},
	"vmmsx.api.whatsapp.connection": { connected: true, status: "ready", reason: "" },
	"vmmsx.api.whatsapp.broadcasts": {
		broadcasts: [
			{ name: "WA-00019", title: "Flood advisory — Kilombero", status: "Sent", audience: "volunteers", geo_node: "Kilombero", scheduled_at: null, sent_on: "2026-08-30 08:15:00", creation: "2026-08-30", addressed: 812, total_recipients: 786, total_sent: 771, total_failed: 9, total_skipped: 6, awaiting_release: false },
			{ name: "WA-00018", title: "Branch meeting moved to Saturday", status: "Partly Sent", audience: "everyone", geo_node: "Morogoro", scheduled_at: null, sent_on: "2026-08-24 17:40:00", creation: "2026-08-24", addressed: 2104, total_recipients: 1988, total_sent: 1641, total_failed: 312, total_skipped: 35, awaiting_release: false },
			{ name: "WA-00017", title: "First aid refresher — sign up", status: "Draft", audience: "volunteers", geo_node: "Dar es Salaam", scheduled_at: "2026-09-02 09:00:00", sent_on: null, creation: "2026-08-31", addressed: 0, total_recipients: 0, total_sent: 0, total_failed: 0, total_skipped: 0, awaiting_release: true },
		],
	},
	"vmmsx.api.whatsapp.opt_outs": {
		count: 27,
		opt_outs: [
			{ name: "WA-OUT-00027", phone_number: "+255712000917", opted_out_on: "2026-08-30 08:22:00", source: "Reply", notes: null },
			{ name: "WA-OUT-00026", phone_number: "+255754001188", opted_out_on: "2026-08-24 18:03:00", source: "Reply", notes: null },
			{ name: "WA-OUT-00025", phone_number: "+255689224410", opted_out_on: "2026-08-19 11:47:00", source: "Staff", notes: "Asked at the branch desk" },
		],
	},

	"vmmsx.api.companions.available": { apps: [] },

	// --- Phase 2 ---------------------------------------------------------

	"vmmsx.api.tasks.get_task": {
		name: "TASK-0008",
		subject: "Submit branch first-aid kit inventory",
		description:
			"Count and record the contents of the two response kits in the Arusha City store. Use the checklist sheet on the door and photograph anything that is missing or expired.",
		status: "accepted",
		volunteer: "VOL-00011",
		geo_node: "GEO-ARUSHA-CITY",
		deployment: null,
		due_on: iso(-6),
		assigned_on: iso(-12),
		accepted_on: iso(-11),
		submitted_on: null,
		closed_on: null,
		open_question: true,
		completion_notes: null,
		is_open: true,
		// The rest of the server's own `task.dto` — the mock predates most of it,
		// and the task record draws every field below.
		project: null,
		batch: null,
		due_at: `${iso(-6)} 17:00:00`,
		planned_start: `${iso(-11)} 09:00:00`,
		planned_end: `${iso(-6)} 16:00:00`,
		response_deadline: null,
		expected_hours: 4,
		actual_hours: 2.5,
		percent_complete: 10,
		priority: "High",
		task_type: "Record update",
		is_overdue: true,
		checklist: [
			{ idx: 1, item: "Count the contents of response kit A", is_required: true, is_done: true, done_on: iso(-8), notes: null, evidence: null },
			{ idx: 2, item: "Count the contents of response kit B", is_required: true, is_done: false, done_on: null, notes: null, evidence: null },
			{ idx: 3, item: "Photograph anything expired", is_required: false, is_done: false, done_on: null, notes: null, evidence: null },
		],
		checklist_outstanding: ["Count the contents of response kit B"],
		brief_files: [
			{ label: "Response kit checklist sheet", file: "#", notes: "Two pages, print both sides" },
		],
		depends_on: [],
		blocking: [],
		blocked_override_reason: null,
		where: {
			work: {
				name: "Arusha City branch store",
				address: "Sokoine Road, Arusha",
				latitude: null,
				longitude: null,
				has_point: false,
				located_on: null,
				map: null,
				directions: null,
			},
			meeting_point: {
				name: null,
				address: null,
				latitude: null,
				longitude: null,
				has_point: false,
				located_on: null,
				map: null,
				directions: null,
			},
			travel_instructions: "The store is behind the training room; ask at the front desk.",
			local_contact: { name: "Asha Mbwana", phone: "0755 111 222" },
			inherited_from: null,
		},
		outcome: null,
		final_evidence: null,
		return_reason: null,
		rework_count: 0,
		manager_rating: null,
		lessons_learned: null,
		decline_reason: null,
		reassigned_to_task: null,
		reassigned_from_task: null,
		reassignment_reason: null,
		thread: [
			{ entry_type: "assigned", author: "Asha Mbwana", posted_on: iso(-12), note: "Please get to this before the end of the month.", proof: null },
			{ entry_type: "accepted", author: "Nigel Nathan", posted_on: iso(-11), note: null, proof: null },
			{ entry_type: "progress", author: "Nigel Nathan", posted_on: iso(-8), note: "Kit A is done. Kit B is locked and I do not have the key.", proof: null },
			{ entry_type: "progress requested", author: "Asha Mbwana", posted_on: iso(-7), note: "The key is with the duty officer — ask at the front desk.", proof: null },
			{ entry_type: "question", author: "Nigel Nathan", posted_on: iso(-2), note: "Do you want the expired items thrown out or kept for the return?", proof: null },
		],
	},

	"vmmsx.api.deployment.my_deployments": {
		volunteer: "VOL-00011",
		deployments: [
			{
				name: "DEP-0031",
				title: "Zanzibar Heatwave Awareness",
				terms_of_reference: "TOR-0004",
				geo_node: "Zanzibar Urban",
				geo_path: "Zanzibar Urban — Zanzibar — Tanzania Red Cross Society",
				status: "Completed",
				is_open: false,
				start_date: iso(-200),
				end_date: iso(-188),
				volunteers_required: 8,
				email_template: null,
				participant_count: 8,
				assignment_counts: { Assigned: 0, Pending: 0, Accepted: 8, Declined: 1, Withdrawn: 0, on_deployment: 8, open: 0, total: 9 },
				places_left: 0,
			},
			{
				name: "DEP-0018",
				title: "Mbarali Flood Relief",
				terms_of_reference: "TOR-0002",
				geo_node: "Mbarali District",
				geo_path: "Mbarali District — Mbeya — Tanzania Red Cross Society",
				status: "Completed",
				is_open: false,
				start_date: "2024-03-04",
				end_date: "2024-03-19",
				volunteers_required: 12,
				email_template: null,
				participant_count: 12,
				assignment_counts: { Assigned: 0, Pending: 0, Accepted: 12, Declined: 0, Withdrawn: 0, on_deployment: 12, open: 0, total: 12 },
				places_left: 0,
			},
			{
				name: "DEP-0009",
				title: "National Blood Donor Week",
				terms_of_reference: "TOR-0001",
				geo_node: "GEO-ARUSHA-CITY",
				geo_path: "Arusha City — Arusha — Tanzania Red Cross Society",
				status: "Completed",
				is_open: false,
				start_date: "2023-06-12",
				end_date: "2023-06-18",
				volunteers_required: 6,
				email_template: null,
				participant_count: 6,
				assignment_counts: { Assigned: 0, Pending: 0, Accepted: 6, Declined: 0, Withdrawn: 0, on_deployment: 6, open: 0, total: 6 },
				places_left: 0,
			},
		],
	},

	"vmmsx.api.deployment.get_my_assignment": {
		assignment: {
			name: "ASG-0001",
			deployment: "DEP-0042",
			volunteer: "VOL-00011",
			full_name: "Nigel Nathan",
			photo: null,
			terms_of_reference: "TOR-0009",
			geo_node: "Rungwe District",
			status: "Pending",
			is_on_deployment: false,
			is_open: true,
			is_settled: false,
			role: "Community Health Volunteer",
			is_leader: false,
			start_date: iso(15),
			end_date: iso(26),
			invited_on: iso(-1),
			responded_on: null,
			response_note: null,
			joined_on: null,
			left_on: null,
			participation_notes: null,
			notes: null,
		},
		terms: {
			name: "TOR-0009",
			tor_key: "rungwe-flood-community-health",
			tor_name: "Rungwe Flood Response — Community Health",
			is_active: true,
			docstatus: 1,
			is_draft: false,
			is_submitted: true,
			is_cancelled: false,
			is_offered: true,
			amended_from: null,
			expected_start_date: iso(15),
			expected_end_date: iso(26),
			section_counts: { stakeholders: 2, objectives: 3, expected_outputs: 3, approach_methods: 1, itinerary: 3, resources: 2 },
			purpose:
				"Support household health screening, safe-water messaging and referral of urgent cases across six wards affected by the March floods.",
			responsibilities:
				"Visit assigned households with a branch partner. Complete the section-4 screening form. Refer anyone with warning signs to the ward health post. Keep a daily tally.",
			geo_scope: "Rungwe District",
			geo_scope_path: "Rungwe District — Mbeya — Tanzania Red Cross Society",
			default_duration_days: 12,
			approval_mode: "single",
			requires_approver: true,
			required_certifications: ["Basic First Aid"],
			desirable_certifications: ["Psychological First Aid"],
			project: "PRJ-0003",
			project_name: "Southern Highlands Flood Response 2026",
			mission_background:
				"<p>Heavy rain in early March caused flooding and landslides across Rungwe District. An emergency appeal is funding a three-month relief operation.</p>",
			notes: null,
			certification_requirements: [
				{ certification_type: "Basic First Aid", is_mandatory: true, requirement_notes: null },
			],
			stakeholders: [
				{ designation: "Branch coordinator", full_name: "Asha Mbwana", phone_number: "0754 210 118", email: "asha@example.org" },
				{ designation: "Ward health officer", full_name: "Dr. J. Mwakasege", phone_number: null, email: null },
			],
			objectives: [
				{ objective: "Screen 1,200 households across six wards." },
				{ objective: "Refer all urgent cases to a health post within 24 hours." },
				{ objective: "Deliver safe-water guidance to every household visited." },
			],
			expected_outputs: [
				{ output: "Completed screening forms for every household visited." },
				{ output: "A daily referral tally per ward." },
				{ output: "A short end-of-wave report." },
			],
			approach_methods: [{ methodology: "Household visits", notes: "In pairs, with a branch partner." }],
			itinerary: [
				{ activity_date: iso(15), activity_time: "07:30:00", activity: "Report to Mbeya Branch Office for briefing", person_responsible: "Asha Mbwana" },
				{ activity_date: iso(16), activity_time: "08:00:00", activity: "Deploy to Kyela ward 4", person_responsible: null },
				{ activity_date: iso(25), activity_time: "16:00:00", activity: "Wave debrief and handover", person_responsible: "Asha Mbwana" },
			],
			resources: [
				{ resource: "Accommodation at the Mbeya branch guesthouse", needed_on: iso(15), quantity: 12, unit: "nights", unit_cost: null, donor: null },
				{ resource: "Screening form packs", needed_on: iso(15), quantity: 20, unit: "packs", unit_cost: null, donor: null },
			],
			resources_total: 0,
		},
		deployment: {
			name: "DEP-0042",
			status: "Planned",
			start_date: iso(15),
			end_date: iso(26),
			geo_node: "Rungwe District",
			notes: "Wave 3. Report to the Mbeya branch office on the morning of the 14th.",
		},
	},

	"vmmsx.api.locations.published": {
		count: 2,
		locations: [
			{
				name: "LOC-MBEYA",
				location_name: "Mbeya Branch Office",
				geo_node: "Rungwe District",
				address: "Jacaranda Road, Mbeya",
				latitude: -8.9094,
				longitude: 33.4608,
				has_point: true,
				phone: "0252 502 111",
				email: "mbeya@example.org",
				opening_hours: "Mon–Fri 08:00–17:00",
				photo: "",
			},
			{
				name: "LOC-ARUSHA",
				location_name: "Arusha City Branch Office",
				geo_node: "GEO-ARUSHA-CITY",
				address: "Old Moshi Road, Arusha",
				latitude: -3.3725,
				longitude: 36.6949,
				has_point: true,
				phone: "0272 544 000",
				email: "arusha@example.org",
				opening_hours: "Mon–Fri 08:00–17:00",
				photo: "",
			},
		],
	},

	"vmmsx.api.volunteer.my_availability": {
		volunteer: "VOL-00011",
		exists: false,
		available_on_holidays: false,
		valid_from: null,
		valid_to: null,
		notes: null,
		days: [],
		slots: [
			{ name: "S1", slot_name: "Morning", start_time: "08:00:00", end_time: "12:00:00", description: null },
			{ name: "S2", slot_name: "Afternoon", start_time: "12:00:00", end_time: "17:00:00", description: null },
			{ name: "S3", slot_name: "Evening", start_time: "17:00:00", end_time: "21:00:00", description: null },
		],
	},

	"vmmsx.api.society.branding": {
		name: "Tanzania Red Cross Society",
		short_name: "TRCS",
		logo: "",
		logo_dark: "",
	},

	"vmmsx.api.content.surface": { blocks: {} },
};

/* ---------------------------------------------------------------- server */

const server = http.createServer((req, res) => {
	// frappe-js-sdk sends every request with `withCredentials: true`; a browser
	// rejects a wildcard `Allow-Origin` on a credentialed request, so echo the
	// caller's origin and allow credentials explicitly.
	res.setHeader("Access-Control-Allow-Origin", req.headers.origin || "*");
	res.setHeader("Access-Control-Allow-Credentials", "true");
	res.setHeader("Access-Control-Allow-Headers", req.headers["access-control-request-headers"] || "*");
	res.setHeader("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS");
	res.setHeader("Vary", "Origin");
	res.setHeader("Content-Type", "application/json");

	if (req.method === "OPTIONS") {
		res.writeHead(204);
		res.end();
		return;
	}

	const url = new URL(req.url, "http://localhost");
	const method = decodeURIComponent(url.pathname.replace(/^\/api\/method\//, ""));

	if (req.method !== "GET") {
		res.writeHead(200);
		res.end(JSON.stringify({ message: {} }));
		return;
	}

	if (method in CANNED) {
		res.writeHead(200);
		res.end(JSON.stringify({ message: CANNED[method] }));
		return;
	}

	// An endpoint we have not canned: answer empty rather than 404, so a screen
	// that reads it renders its own "nothing here" state.
	res.writeHead(200);
	res.end(JSON.stringify({ message: null }));
});

server.listen(port, () => {
	// eslint-disable-next-line no-console
	console.log(`mock-api listening on http://localhost:${port} (synthetic data)`);
});
