# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The work itself: programmes, the terms written under them, and who went.

    bench --site <site> execute vmmsx.seed.tanzania_deployments.main

`tanzania_people.py` fills the register with volunteers. This is what the
society then *did with them*: six programmes of work, ten terms of reference
written under them, ten deployments run against those, and a roster on each —
some accepted, some still waiting for an answer, one declined, one led.

**Every record here is made the way a coordinator makes it**, which is the same
rule `tanzania_people.py` states at length and for the same reason. Nothing
below writes a `VMMS Project`, a `VMMS Deployment` or an assignment status
directly:

* a **deployment coordinator** login is created, given
  `Deployment Manager` — the role this society's settings already name as
  `vmms_deployment_scope_role` — and placed at the national node;
* `frappe.set_user` becomes them, and every creation goes through
  `vmmsx.api.deployment`'s own whitelisted endpoints, which check permission,
  then core's geo scope, then the coherence rules (a project must be open
  before terms may be written under it, terms must be submitted before anybody
  can be asked to agree to them, a deployment must sit inside its terms' scope);
* `frappe.set_user` becomes each **volunteer**, who answers their own
  invitation through `respond_to_assignment` — so an acceptance is an
  acceptance of the exact submitted terms of reference, which is the whole
  reason that doctype is submittable and why there is no separate contract.

**The coordinator is a third login, not one of the two approvers.**
`tanzania.place_approver` says out loud that neither approver holds
`ROLE_DEPLOYMENT_MANAGER`, deliberately: the split between reviewing people and
sending them out is only visible on a demo account that is missing one of them.
Adding the role to `branch@mail.com` to save a login would erase exactly the
thing that note protects.

**Placed at the national node, and only there.** This seed's work spans six
branches, and a coordinator per branch would be six logins nobody signs into.
Geo scope is a node *and its descendants*, so one assignment at the root is a
national operations desk — which is what a portfolio spanning six regions is
run from anyway.

**Certifications come first, and they are the point of the candidate search.**
Three of the terms below require one, mandatorily. Without a register of who
holds what, the matching panel would answer "nobody" everywhere and teach a
reader that the feature is broken rather than that it is selective. So a
handful of the approved volunteers hold what their branch actually trains for,
and the people the search leaves out are left out for a reason somebody can
read.

**Dates are moved backwards afterwards**, the same admission
`tanzania_people._backdate` makes: a coordinator cannot open a programme last
March, so `creation` is rewritten once the trail exists. The dates that are
*fields* — start, end, joined on — are written forward from the day this runs,
so a demo looked at in six months still has work in it rather than a register
of things that all ended.

Idempotent. A second run finds every project by name and does nothing.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.seed import tanzania

PROJECT_DOCTYPE = "VMMS Project"
TERMS_DOCTYPE = "VMMS Terms of Reference"
DEPLOYMENT_DOCTYPE = "VMMS Deployment"
ASSIGNMENT_DOCTYPE = "VMMS Deployment Assignment"

# --- the coordinator ----------------------------------------------------------

# The third demo login, beside the two approvers. See the module docstring for
# why they are a separate person and why they sit at the national node.
COORDINATOR = "deployments@mail.com"
COORDINATOR_FIRST_NAME = "Upendo"
COORDINATOR_LAST_NAME = "Kessy"

COORDINATOR_ROLE = tanzania.ROLE_DEPLOYMENT_MANAGER

# What that role has to be able to write for a coordinator to do any of this.
#
# The shipped doctype JSONs grant only System Manager, deliberately — which
# society role runs deployments is configuration, not product. A role holding a
# Geo Assignment and nothing else fails `frappe.get_list`'s own permission check
# before the geo scope condition is ever consulted, so without this the console
# is empty and says nothing about why. `kenya.py::APPROVER_WRITABLE` carries the
# same note against the same four doctypes.
COORDINATOR_WRITABLE = (
	PROJECT_DOCTYPE,
	TERMS_DOCTYPE,
	DEPLOYMENT_DOCTYPE,
	ASSIGNMENT_DOCTYPE,
	"VMMS Deployment Request",
)

# --- what people hold ---------------------------------------------------------

# Certifications, by the volunteer who holds one. The types are
# `tanzania_operations.CERTIFICATION_TYPES`' own keys and the volunteers are
# `tanzania_people.VOLUNTEERS`' own logins — only the ten whose applications
# were approved appear, because nobody else has a volunteer record to hold one.
#
# `days_ago` is when the course was completed. Two of them are deliberately old
# enough to have lapsed against their type's validity period, because a register
# in which everything is current is a register that never shows what a lapse
# does to the candidate search.
#
# (volunteer login, certification type, days ago)
CERTIFICATIONS = (
	("grace.mushi@mail.com", "first-aid", 300),
	("grace.mushi@mail.com", "cbha", 240),
	("daniel.mbwana@mail.com", "water-safety", 210),
	("daniel.mbwana@mail.com", "disaster-response", 400),
	("neema.kileo@mail.com", "psychological-first-aid", 260),
	("emmanuel.laizer@mail.com", "first-aid", 190),
	("emmanuel.laizer@mail.com", "rfl", 520),
	("happiness.sanare@mail.com", "cbha", 150),
	("furaha.magesa@mail.com", "water-safety", 120),
	("furaha.magesa@mail.com", "first-aid", 95),
	("peter.masanja@mail.com", "disaster-response", 330),
	("elia.chusi@mail.com", "cbha", 200),
	("sophia.massawe@mail.com", "first-aid", 60),
	("sophia.massawe@mail.com", "psychological-first-aid", 175),
	("godfrey.mwakyusa@mail.com", "disaster-response", 280),
	# Lapsed: First Aid runs for 730 days and this one was completed before that.
	# The candidate search for terms requiring it will not offer them, and the
	# volunteer's own record says why.
	("godfrey.mwakyusa@mail.com", "first-aid", 900),
	("peter.masanja@mail.com", "water-safety", 810),
)

# --- the programmes -----------------------------------------------------------

# `where` is resolved by `_node()`: ("national",), ("branch", label) or
# ("sub_branch", label, parent). `start_in` / `end_in` are days from the day
# this runs, so a re-run next year produces a live portfolio rather than a page
# of things that finished.
#
# `status` is where the seed *stops driving* the project, not a field it writes:
# every one is opened Planned by `create_project` and moved from there through
# `set_project_status`, which is the same grammar a coordinator is held to.
#
# The work is TRCS's own shape — seasonal flooding on the coast, community
# health and WASH around the lake, road safety, the Kilimanjaro Marathon's first
# aid cover, blood drives with the national blood service, landslide
# preparedness in the southern highlands. The programmes are invented; the kinds
# of work are not.
PROJECTS = (
	{
		"key": "dsm-floods",
		"name": "Dar es Salaam Flood Response 2026",
		"where": ("branch", "Dar es Salaam"),
		"status": "Active",
		"start_in": -38,
		"end_in": 52,
		"summary": (
			"The branch's coordinated response to this season's long rains: household evacuation"
			" support, relief distribution and a reception centre for displaced families across"
			" the flood-affected sub-branches."
		),
	},
	{
		"key": "mwanza-health",
		"name": "Lake Zone Community Health and WASH Programme",
		"where": ("branch", "Mwanza"),
		"status": "Active",
		"start_in": -170,
		"end_in": 120,
		"summary": (
			"Household health promotion and safe water and sanitation work in the lakeside wards,"
			" run with the regional health office over three quarters."
		),
	},
	{
		"key": "road-safety",
		"name": "National Road Safety Campaign 2026",
		"where": ("national",),
		"status": "Planned",
		"start_in": 24,
		"end_in": 160,
		"summary": (
			"A national campaign ahead of the December travel season: awareness at bus stands and"
			" schools, and first aid cover on the trunk roads, branch by branch."
		),
	},
	{
		"key": "kilimanjaro-marathon",
		"name": "Kilimanjaro Marathon First Aid Cover",
		"where": ("branch", "Kilimanjaro"),
		"status": "Completed",
		"start_in": -128,
		"end_in": -112,
		"summary": (
			"First aid posts and a mobile team along the route of the Kilimanjaro Marathon in"
			" Moshi, provided under the branch's standing agreement with the organisers."
		),
	},
	{
		"key": "northern-blood",
		"name": "Northern Zone Blood Donation Drives",
		"where": ("branch", "Arusha"),
		"status": "Active",
		"start_in": -60,
		"end_in": 90,
		"summary": (
			"Six mobile blood donation drives with the national blood transfusion service, staffed"
			" from the branch's own volunteer register."
		),
	},
	{
		"key": "mbeya-landslides",
		"name": "Southern Highlands Landslide Preparedness",
		"where": ("branch", "Mbeya"),
		"status": "Planned",
		"start_in": 14,
		"end_in": 180,
		"summary": (
			"Community risk assessment and early warning work on the slopes above Rungwe, before"
			" the next heavy season rather than during it."
		),
	},
)

PROJECTS_BY_KEY = {project["key"]: project for project in PROJECTS}

# --- the terms the work is done under -----------------------------------------
#
# `project` is one of `PROJECTS`' keys, or absent. **Two of these have no
# project on purpose**: a branch's standing first aid duty and the family links
# desk are not programmes with a start and an end, and a demo in which
# everything has been filed under something teaches that the link is mandatory
# when the field is deliberately optional.
#
# `requires` is (certification type, mandatory). A mandatory requirement is what
# `matching.candidates()` filters on, so the three terms carrying one are the
# three where the candidate panel has something to demonstrate.
#
# `scope` narrows where terms may be used; absent means anywhere. The mission
# tables — objectives, outputs, approach, itinerary, stakeholders, resources —
# are what the printed terms of reference is *made of*, and the two flagship
# operations carry a full set so that the document is worth opening.
#
# **`approach` names a `VMMS TOR Methodology` by its key, not a phrase.** How a
# society goes about its work is its own vocabulary, keyed and relabelled
# independently of the terms citing it, so the first half of each pair is one of
# the seven keys that doctype ships with and the second is this piece of work's
# own note against it. A key this site does not have is dropped rather than
# guessed at, the same guard the certification requirements carry.
TERMS = (
	{
		"key": "flood-response-team",
		"name": "Flood Response Team",
		"project": "dsm-floods",
		"scope": ("branch", "Dar es Salaam"),
		"duration_days": 14,
		"requires": (("water-safety", True), ("first-aid", False)),
		"purpose": (
			"Search, evacuation support and relief distribution in wards cut off by the seasonal"
			" floods, working to the branch operations desk."
		),
		"background": (
			"The long rains flood the low-lying wards of Kinondoni, Ilala and Temeke every season."
			" The branch keeps a standing response team so that the first days of an event are run"
			" by people who have trained together, rather than by whoever is available."
		),
		"responsibilities": (
			"Support household evacuation and keep the headcount for the ward.\n"
			"Distribute relief items against the branch register and account for what was given.\n"
			"Report needs, hazards and protection concerns to the operations desk daily."
		),
		"objectives": (
			"Reach every household in the affected wards within 48 hours of an alert.",
			"Move displaced families to the reception centre safely and with their belongings.",
			"Keep a distribution record the branch can reconcile afterwards.",
		),
		"outputs": (
			"A daily situation report from each ward team.",
			"A signed distribution register for every relief item issued.",
			"A list of households needing follow-up after the water recedes.",
		),
		"approach": (
			("direct_service", "Ward teams of four: a leader, two responders and a recorder."),
			("community_mobilisation", "Evacuation messages carried through the ward executive officers."),
			("observation", "Access and hazard reporting to the operations desk twice a day."),
		),
		"itinerary": (
			(-38, "08:00", "Branch briefing and team assignment", "Branch operations desk"),
			(-37, "07:00", "First ward sweep and household headcount", "Ward team leaders"),
			(-30, "09:00", "Relief distribution, Kinondoni and Ilala", "Logistics lead"),
			(14, "09:00", "Post-flood follow-up visits", "Ward team leaders"),
		),
		"stakeholders": (
			("Branch Operations Manager", "Joseph Kimaro", "+255712000101", "branch@mail.com"),
			("Ward Executive Officer", "", "", ""),
			("Regional Disaster Management Office", "", "", ""),
		),
		"resources": (
			("Inflatable rescue boat", -38, 2, "unit", 0, "Branch stock"),
			("Family relief kit", -30, 400, "kit", 85000, "IFRC appeal"),
			("Life jacket", -38, 24, "unit", 45000, "Branch stock"),
			("Tarpaulin", -30, 200, "unit", 32000, "IFRC appeal"),
		),
	},
	{
		"key": "reception-centre",
		"name": "Reception Centre Support",
		"project": "dsm-floods",
		"scope": ("branch", "Dar es Salaam"),
		"duration_days": 10,
		"requires": (("psychological-first-aid", False),),
		"purpose": "Setting up and running a temporary reception centre for displaced households.",
		"background": (
			"When a ward is evacuated the branch opens a reception centre in a school or community"
			" hall. Running one is a distinct piece of work from the response itself, and the"
			" people who do it are on site for days rather than hours."
		),
		"responsibilities": (
			"Set up sleeping, washing and feeding areas to the branch standard.\n"
			"Register arriving households and keep the occupancy list current.\n"
			"Refer protection, health and psychosocial concerns to the branch lead the same day."
		),
		"objectives": (
			"Open the centre within six hours of the branch calling for it.",
			"Register every household on arrival, with the ward they came from.",
		),
		"outputs": (
			"A daily occupancy return to the branch operations desk.",
			"A referral log for health and protection cases.",
		),
		"approach": (
			("direct_service", "Two shifts a day, 07:00 to 19:00 and 19:00 to 07:00, four people each."),
			("observation", "Occupancy counted at every shift change. Nobody sleeps here unregistered."),
		),
		"itinerary": (),
		"stakeholders": (
			("Centre Manager", "", "", ""),
			("School Head Teacher", "", "", ""),
		),
		"resources": (
			("Sleeping mat", -34, 300, "unit", 12000, "Branch stock"),
			("Mosquito net", -34, 300, "unit", 9000, "IFRC appeal"),
			("Jerry can, 20L", -34, 150, "unit", 7500, "Branch stock"),
		),
	},
	{
		"key": "household-health-promotion",
		"name": "Household Health Promotion",
		"project": "mwanza-health",
		"scope": ("branch", "Mwanza"),
		"duration_days": 20,
		"requires": (("cbha", True),),
		"purpose": (
			"Household visits on the branch health campaign — hygiene, immunisation awareness and"
			" referral to the nearest facility."
		),
		"background": (
			"The lakeside wards carry a steady burden of waterborne illness, and the regional"
			" health office asks the branch for household-level promotion each dry season."
		),
		"responsibilities": (
			"Visit the households on the round the branch has planned, with a partner.\n"
			"Deliver the campaign's key messages as they are written, without improvising them.\n"
			"Refer anybody who needs care, and record the referral."
		),
		"objectives": (
			"Visit 600 households across the two sub-branches.",
			"Refer every suspected case to the ward facility the same day.",
		),
		"outputs": ("A visit register per ward.", "A weekly referral summary for the health office."),
		"approach": (
			("household_survey", "A short questionnaire at each visit, one per household on the round."),
			("community_mobilisation", "Pairs, never alone, and one of each pair CBHA-certified."),
			("key_informant_interview", "The ward health officer, at the start and end of each round."),
		),
		"itinerary": (),
		"stakeholders": (
			("Regional Medical Officer", "", "", ""),
			("Ward Health Officer", "", "", ""),
		),
		"resources": (
			("Household hygiene kit", -160, 600, "kit", 18000, "Regional health office"),
			("Campaign leaflet", -165, 2000, "unit", 500, "Branch stock"),
		),
	},
	{
		"key": "safe-water-support",
		"name": "Safe Water and Sanitation Support",
		"project": "mwanza-health",
		"scope": ("branch", "Mwanza"),
		"duration_days": 12,
		"requires": (),
		"purpose": "Water point cleaning, chlorination support and latrine promotion in the lakeside wards.",
		"background": (
			"The WASH half of the same programme. It runs alongside the household visits and draws"
			" on the same volunteers, which is why it is separate terms rather than a line in"
			" theirs: the work, the training and the reporting are all different."
		),
		"responsibilities": (
			"Support the ward technician at each water point.\n"
			"Demonstrate household water treatment and record who was shown.\n"
			"Report any water point the technician condemns to the branch the same day."
		),
		"objectives": ("Cover the twelve water points on the ward list.",),
		"outputs": ("A condition report per water point.",),
		"approach": (
			("observation", "Water point condition assessed alongside the ward technician."),
			("training", "Household treatment demonstrated at each point, with attendance recorded."),
		),
		"itinerary": (),
		"stakeholders": (("Ward Water Technician", "", "", ""),),
		"resources": (("Water treatment sachets", -120, 5000, "unit", 200, "Regional health office"),),
	},
	{
		"key": "road-safety-awareness",
		"name": "Road Safety Awareness Team",
		"project": "road-safety",
		"scope": None,
		"duration_days": 7,
		"requires": (),
		"purpose": "Public awareness at bus stands and schools ahead of the December travel season.",
		"background": (
			"Road traffic injury is among the commonest reasons a branch first aid post is used at"
			" all. The campaign is national, and each branch runs it in its own bus stands."
		),
		"responsibilities": (
			"Run stand-side awareness sessions with the branch team.\n"
			"Distribute campaign materials and record the reach.\n"
			"Support the schools programme where one is scheduled."
		),
		"objectives": ("Reach 5,000 travellers across the participating branches.",),
		"outputs": ("A reach return per branch, weekly.",),
		"approach": (
			(
				"community_mobilisation",
				"Bus stand sessions twice a day, at the morning and evening departures.",
			),
			("training", "School sessions where the branch and the head teacher have scheduled one."),
		),
		"itinerary": (),
		"stakeholders": (("National Road Safety Council", "", "", ""),),
		"resources": (("Campaign banner", 24, 40, "unit", 65000, "National headquarters"),),
	},
	{
		"key": "marathon-first-aid",
		"name": "Marathon First Aid Cover",
		"project": "kilimanjaro-marathon",
		"scope": ("branch", "Kilimanjaro"),
		"duration_days": 2,
		"requires": (("first-aid", True),),
		"purpose": "Staffing the first aid posts and the mobile team along the marathon route.",
		"background": (
			"The branch has provided the race's first aid cover for years. The posts are fixed, the"
			" mobile team follows the last runner, and everything is handed back to the organisers"
			" the same evening."
		),
		"responsibilities": (
			"Staff an assigned post for the whole of the race.\n"
			"Treat within scope and refer anything beyond it to the ambulance point.\n"
			"Keep the treatment log and hand it to the branch afterwards."
		),
		"objectives": ("Cover all six posts and the mobile team for the duration of the race.",),
		"outputs": ("A treatment log per post, handed to the branch the same day.",),
		"approach": (
			("direct_service", "Six fixed posts at 5km intervals, four responders each."),
			("observation", "One mobile team behind the final runner, reporting to the medical director."),
		),
		"itinerary": (
			(-128, "05:30", "Post set-up and equipment check", "Branch first aider"),
			(-128, "06:30", "Race start, posts staffed", "Post leaders"),
			(-128, "14:00", "Stand down and hand over treatment logs", "Branch first aider"),
		),
		"stakeholders": (
			("Race Medical Director", "", "", ""),
			("Branch First Aid Lead", "", "", ""),
		),
		"resources": (
			("First aid kit, post", -129, 6, "unit", 120000, "Branch stock"),
			("Stretcher", -129, 4, "unit", 180000, "Branch stock"),
		),
	},
	{
		"key": "blood-drive-support",
		"name": "Blood Drive Support",
		"project": "northern-blood",
		"scope": ("branch", "Arusha"),
		"duration_days": 2,
		"requires": (),
		"purpose": "Running the reception, refreshment and recovery areas at a mobile blood drive.",
		"background": (
			"The national blood transfusion service brings the clinical team; the branch brings the"
			" people who receive donors, keep the queue moving and watch the recovery area."
		),
		"responsibilities": (
			"Register donors and direct them through the drive.\n"
			"Staff the refreshment and recovery area for the whole session.\n"
			"Watch for and escalate any donor who becomes unwell."
		),
		"objectives": ("Receive 200 donors per drive without a queue leaving unregistered.",),
		"outputs": ("A donor reception count per drive.",),
		"approach": (
			("direct_service", "Reception, refreshment and recovery: three stations, two volunteers each."),
			("community_mobilisation", "Donor recruitment at the campus and the market the week before."),
		),
		"itinerary": (),
		"stakeholders": (("National Blood Transfusion Service", "", "", ""),),
		"resources": (("Refreshment pack", -60, 400, "unit", 3000, "NBTS"),),
	},
	{
		"key": "landslide-assessment",
		"name": "Landslide Risk Assessment",
		"project": "mbeya-landslides",
		"scope": ("branch", "Mbeya"),
		"duration_days": 8,
		"requires": (("disaster-response", True),),
		"purpose": "Community risk mapping and early warning arrangements on the Rungwe slopes.",
		"background": (
			"Rungwe's slopes move in the heavy season and the branch has responded to three"
			" landslides in as many years. This is the preparedness half: mapping which"
			" settlements sit below which slope, and agreeing what the warning is."
		),
		"responsibilities": (
			"Map settlements and access routes with the village committee.\n"
			"Record the households that would have to move first.\n"
			"Agree the local warning signal and who gives it."
		),
		"objectives": (
			"Produce a risk map for each of the six villages on the list.",
			"Agree a warning arrangement with every village committee.",
		),
		"outputs": ("A risk map and a household list per village.",),
		"approach": (
			(
				"focus_group_discussion",
				"The village committee first. Nothing is mapped without them in the room.",
			),
			("household_survey", "A household listing for the settlements below each slope."),
			(
				"key_informant_interview",
				"The district disaster management officer, once per village cluster.",
			),
		),
		"itinerary": (),
		"stakeholders": (
			("District Disaster Management Officer", "", "", ""),
			("Village Chairperson", "", "", ""),
		),
		"resources": (("GPS handset", 14, 4, "unit", 350000, "Branch stock"),),
	},
	{
		"key": "branch-first-aid-duty",
		"name": "Branch First Aid Duty",
		"project": None,
		"scope": None,
		"duration_days": 1,
		"requires": (("first-aid", True),),
		"purpose": "The standing first aid post a branch staffs at a public event on request.",
		"background": (
			"Not a programme and not an emergency: the ordinary duty a branch is asked for a dozen"
			" times a year — a football match, a school sports day, a public rally. It has no start"
			" and no end, which is why it is written under no project."
		),
		"responsibilities": (
			"Staff the post for the duration of the event, under a branch first aider.\n"
			"Treat minor injuries and refer anything beyond scope.\n"
			"Hand the treatment log to the branch the same day."
		),
		"objectives": ("Cover the event from gates open to gates closed.",),
		"outputs": ("A treatment log per duty.",),
		"approach": (("direct_service", "Never fewer than two on a post: a first aider and an assistant."),),
		"itinerary": (),
		"stakeholders": (("Event Organiser", "", "", ""),),
		"resources": (("First aid kit, post", 0, 2, "unit", 120000, "Branch stock"),),
	},
	{
		"key": "family-links-desk",
		"name": "Restoring Family Links Desk",
		"project": None,
		"scope": None,
		"duration_days": 30,
		"requires": (("rfl", True),),
		"purpose": "Taking tracing requests and following them through the Family Links Network.",
		"background": (
			"A standing service rather than an operation. Requests arrive at a branch at any time"
			" and the desk is staffed by whoever holds the training, which is why these terms are"
			" written once and used wherever somebody is needed."
		),
		"responsibilities": (
			"Take tracing requests and record them as the Network requires.\n"
			"Keep the requesting family informed of progress, including when there is none.\n"
			"Escalate anything involving an unaccompanied child immediately."
		),
		"objectives": ("Acknowledge every request within three working days.",),
		"outputs": ("A monthly case return to the national RFL focal point.",),
		"approach": (
			(
				"key_informant_interview",
				"The request taken face to face, on the Network's own form, unmodified.",
			),
		),
		"itinerary": (),
		"stakeholders": (("National RFL Focal Point", "", "", ""),),
		"resources": (),
	},
)

# --- what was actually run ----------------------------------------------------
#
# `terms` is a `TERMS` key. `where` is where the work happens — a sub-branch for
# most of these, because that is the rung the work is done at, and the terms'
# own `scope` (the branch) contains it, which is the containment rule
# `terms.assert_within_scope` enforces.
#
# `roster` is one entry per person, and each entry says how they came to be on
# it, in the app's own two verbs:
#
#   asked     invited, and left waiting for an answer          -> Pending
#   accepted  invited, and they answered yes themselves        -> Accepted
#   declined  invited, and they answered no, with a reason     -> Declined
#   placed    the coordinator placed them; nobody was asked    -> Assigned
#
# `lead` names the one person on the deployment whose role is leader; the
# controller refuses a second.
#
# `status` is where the seed stops driving the deployment, moved through
# `set_deployment_status` rather than written. `updates` are feed entries the
# coordinator posted, which is the only way a feed entry can exist at all — the
# author and the time come from the session.
DEPLOYMENTS = (
	{
		"key": "flood-kinondoni",
		"terms": "flood-response-team",
		"where": ("sub_branch", "Kinondoni", "Dar es Salaam"),
		"start_in": -12,
		"end_in": 10,
		"required": 6,
		"status": "Active",
		"lead": "grace.mushi@mail.com",
		"roster": (
			("grace.mushi@mail.com", "accepted", None),
			("daniel.mbwana@mail.com", "accepted", None),
			("neema.kileo@mail.com", "asked", None),
		),
		"updates": (
			("milestone", "Ward sweep completed in Mikocheni and Msasani. 214 households reached."),
			("update", "Relief distribution runs tomorrow from the branch store, 09:00."),
			("concern", "The Msasani access road is still under water. Boat access only."),
		),
	},
	{
		"key": "reception-ilala",
		"terms": "reception-centre",
		"where": ("sub_branch", "Ilala", "Dar es Salaam"),
		"start_in": 4,
		"end_in": 18,
		"required": 4,
		"status": "Planned",
		"lead": None,
		"roster": (
			("neema.kileo@mail.com", "asked", None),
			("grace.mushi@mail.com", "asked", None),
		),
		"updates": (),
	},
	{
		"key": "health-nyamagana",
		"terms": "household-health-promotion",
		"where": ("sub_branch", "Nyamagana", "Mwanza"),
		"start_in": -25,
		"end_in": 20,
		"required": 4,
		"status": "Active",
		"lead": "furaha.magesa@mail.com",
		"roster": (
			("furaha.magesa@mail.com", "accepted", None),
			("peter.masanja@mail.com", "accepted", None),
		),
		"updates": (
			("update", "412 households visited so far. Two wards left on the round."),
			("milestone", "Referral slips reconciled with the ward facility for October."),
		),
	},
	{
		"key": "water-ilemela",
		"terms": "safe-water-support",
		"where": ("sub_branch", "Ilemela", "Mwanza"),
		"start_in": -6,
		"end_in": 6,
		"required": 3,
		"status": "Active",
		"lead": None,
		"roster": (("peter.masanja@mail.com", "placed", None),),
		"updates": (("update", "Nine of the twelve water points cleaned and reported."),),
	},
	{
		"key": "road-safety-dodoma",
		"terms": "road-safety-awareness",
		"where": ("sub_branch", "Dodoma City", "Dodoma"),
		"start_in": 26,
		"end_in": 33,
		"required": 5,
		"status": "Planned",
		"lead": None,
		"roster": (("elia.chusi@mail.com", "accepted", None),),
		"updates": (),
	},
	{
		"key": "marathon-moshi",
		"terms": "marathon-first-aid",
		"where": ("sub_branch", "Moshi", "Kilimanjaro"),
		"start_in": -128,
		"end_in": -127,
		"required": 8,
		"status": "Completed",
		"lead": "sophia.massawe@mail.com",
		"roster": (("sophia.massawe@mail.com", "accepted", None),),
		"updates": (
			("milestone", "All six posts staffed from 05:30. 34 runners treated, none referred on."),
			("update", "Treatment logs handed to the race medical director at 14:00."),
		),
	},
	{
		"key": "blood-arusha",
		"terms": "blood-drive-support",
		"where": ("sub_branch", "Arusha City", "Arusha"),
		"start_in": -3,
		"end_in": 1,
		"required": 6,
		"status": "Active",
		"lead": "emmanuel.laizer@mail.com",
		"roster": (
			("emmanuel.laizer@mail.com", "accepted", None),
			("happiness.sanare@mail.com", "declined", "Away at a family funeral in Karatu that week."),
		),
		"updates": (("update", "163 donors received on the first day. NBTS asking for a third station."),),
	},
	{
		"key": "blood-meru",
		"terms": "blood-drive-support",
		"where": ("sub_branch", "Meru", "Arusha"),
		"start_in": 20,
		"end_in": 21,
		"required": 6,
		"status": "Planned",
		"lead": None,
		"roster": (("happiness.sanare@mail.com", "asked", None),),
		"updates": (),
	},
	{
		"key": "landslide-rungwe",
		"terms": "landslide-assessment",
		"where": ("sub_branch", "Rungwe", "Mbeya"),
		"start_in": 16,
		"end_in": 24,
		"required": 4,
		"status": "Planned",
		"lead": None,
		"roster": (("godfrey.mwakyusa@mail.com", "asked", None),),
		"updates": (),
	},
	{
		"key": "duty-temeke",
		"terms": "branch-first-aid-duty",
		"where": ("sub_branch", "Temeke", "Dar es Salaam"),
		"start_in": -45,
		"end_in": -45,
		"required": 2,
		"status": "Completed",
		"lead": None,
		"roster": (("grace.mushi@mail.com", "placed", None),),
		"updates": (("update", "Post staffed for the district school sports day. Four minor treatments."),),
	},
)


def main(commit: bool = True) -> dict:
	"""Build the portfolio and report what changed. Safe to re-run."""
	if not tanzania.national():
		print("The Tanzania configuration is not on this site. Run vmmsx.seed.tanzania.main first.")
		return {}

	report = {
		"coordinator": _coordinator(),
		"certifications": _certifications(),
		"projects": _projects(),
		"terms": _terms(),
		"deployments": _deployments(),
		"closed": _close_projects(),
	}
	report["backdating"] = _backdate()

	if commit:
		frappe.db.commit()

	_print(report)

	return report


# --- the coordinator ----------------------------------------------------------


def _coordinator() -> list[dict]:
	"""The login that files all of this, with the role and the scope to do it.

	Public in effect for the same reason `tanzania.place_approver` is: a site
	seeded before this module existed needs the account, the permissions and the
	Geo Assignment, and they are three separate things that can each be missing.
	"""
	rows = [{"key": COORDINATOR, "status": _login()}]

	for doctype in COORDINATOR_WRITABLE:
		rows.append({"key": f"{COORDINATOR_ROLE} on {doctype}", "status": _permit(doctype, COORDINATOR_ROLE)})

	rows.append(
		{"key": f"{COORDINATOR} holds {COORDINATOR_ROLE}", "status": _grant(COORDINATOR, COORDINATOR_ROLE)}
	)

	root = tanzania.national()

	if root:
		rows.append(
			{
				"key": f"{COORDINATOR}: {COORDINATOR_ROLE} at the national node",
				"status": _assign(COORDINATOR, COORDINATOR_ROLE, root),
			}
		)

	frappe.clear_cache(user=COORDINATOR)

	return rows


def _login() -> str:
	"""The account, with `tanzania.DEMO_PASSWORD` on it. See that constant's note."""
	from frappe.utils.password import update_password

	if frappe.db.exists("User", COORDINATOR):
		status = "exists"
	else:
		frappe.get_doc(
			{
				"doctype": "User",
				"email": COORDINATOR,
				"first_name": COORDINATOR_FIRST_NAME,
				"last_name": COORDINATOR_LAST_NAME,
				"send_welcome_email": 0,
				"user_type": "System User",
			}
		).insert(ignore_permissions=True)
		status = "created"

	update_password(COORDINATOR, tanzania.DEMO_PASSWORD)

	return status


def _permit(doctype: str, role: str) -> str:
	"""Read, write, create and share on one doctype for one role."""
	from frappe.permissions import add_permission, update_permission_property

	added = bool(add_permission(doctype, role, 0))

	for permission in ("read", "write", "create", "share"):
		update_permission_property(doctype, role, 0, permission, 1)

	# Terms of reference are submittable and the coordinator is the one who
	# freezes the wording, so the submit right is part of the role rather than
	# something a System Manager has to do on their behalf.
	if frappe.get_meta(doctype).is_submittable:
		update_permission_property(doctype, role, 0, "submit", 1)

	frappe.clear_cache(doctype=doctype)

	return "created" if added else "exists"


def _grant(login: str, role: str) -> str:
	if role in frappe.get_roles(login):
		return "exists"

	frappe.get_doc("User", login).add_roles(role)

	return "created"


def _assign(login: str, role: str, node: str) -> str:
	"""One Geo Assignment: this person holds this role at this node."""
	if frappe.db.exists("Geo Assignment", {"user": login, "role": role, "geo_node": node}):
		return "exists"

	frappe.get_doc(
		{"doctype": "Geo Assignment", "user": login, "role": role, "geo_node": node, "is_active": 1}
	).insert(ignore_permissions=True)

	return "created"


# --- what people hold ---------------------------------------------------------


def _certifications() -> list[dict]:
	"""The register of who holds what, through the app's own idempotent constructor.

	`certification.record` and not an insert written here: one row per volunteer
	per type is a rule that module owns, and the expiry is computed from the
	type's configured validity period rather than from arithmetic in a seed. The
	human path to the same record is the desk form, which a coordinator fills in
	when somebody hands them a certificate.
	"""
	from vmmsx.volunteer.services import certification

	rows = []

	for login, certification_type, days_ago in CERTIFICATIONS:
		volunteer = _volunteer(login)

		if not volunteer:
			rows.append({"key": f"{login}: {certification_type}", "status": "skipped: not a volunteer"})
			continue

		if not frappe.db.exists("VMMS Certification Type", certification_type):
			rows.append({"key": f"{login}: {certification_type}", "status": "skipped: type not seeded"})
			continue

		existing = frappe.db.exists(
			"VMMS Certification", {"volunteer": volunteer, "certification_type": certification_type}
		)

		certification.record(
			volunteer,
			certification_type,
			add_days(today(), -int(days_ago)),
			reference_number=f"TRCS/{certification_type.upper()}/{abs(hash(login)) % 10000:04d}",
		)

		rows.append({"key": f"{login}: {certification_type}", "status": "exists" if existing else "created"})

	return rows


# --- the programmes -----------------------------------------------------------


def _projects() -> list[dict]:
	"""Each programme, opened — and started, if it ever ran.

	**A programme that finished is left Active here and closed at the end**, by
	`_close_projects`, because `project.assert_open` refuses terms of reference
	under a closed one. That refusal is right and the order it forces is the real
	one: a society writes the terms while the programme is running and marks it
	Completed once the work under it is done, not before.
	"""
	from vmmsx.api.deployment import create_project, set_project_status

	rows = []

	for project in PROJECTS:
		existing = _project(project["key"])

		if existing:
			rows.append({"key": project["key"], "name": existing, "status": "exists"})
			continue

		node = _node(project["where"])

		if not node:
			rows.append({"key": project["key"], "status": "skipped: no geo node"})
			continue

		frappe.set_user(COORDINATOR)

		try:
			created = create_project(
				project_name=project["name"],
				geo_node=node,
				start_date=add_days(today(), project["start_in"]),
				end_date=add_days(today(), project["end_in"]),
				summary=project["summary"],
			)

			# Opened Planned by the endpoint, like any other. Anything else is a
			# move through the grammar, recorded as one — and the furthest this
			# step goes is Active, whatever the entry's final status is.
			if project["status"] in ("Active", "Completed"):
				set_project_status(created["name"], "Active")
		finally:
			frappe.set_user("Administrator")

		rows.append({"key": project["key"], "name": created["name"], "status": "created"})

	return rows


def _close_projects() -> list[dict]:
	"""Close the programmes whose work is done. Last, and that is the point.

	The other half of `_projects`. A closed project takes no new terms of
	reference, so closing one before its terms were written would need the seed
	to bypass the rule it is meant to be demonstrating. Run after the
	deployments, which is also the order it happens in a society: the marathon is
	run, the posts are stood down, and then somebody marks the programme done.
	"""
	from vmmsx.api.deployment import set_project_status

	rows = []

	for project in PROJECTS:
		if project["status"] not in ("Completed", "Cancelled"):
			continue

		name = _project(project["key"])

		if not name:
			continue

		if frappe.db.get_value(PROJECT_DOCTYPE, name, "status") == project["status"]:
			rows.append({"key": project["key"], "status": f"already {project['status'].lower()}"})
			continue

		frappe.set_user(COORDINATOR)

		try:
			set_project_status(name, project["status"])
		finally:
			frappe.set_user("Administrator")

		rows.append({"key": project["key"], "status": project["status"].lower()})

	return rows


def _project(key: str | None) -> str | None:
	"""The docname of a seeded project, found by the society's own name for it.

	By `project_name` rather than by docname, the same reason `tanzania.branch()`
	resolves geo by label: the doctype autonames itself opaquely and a second
	bench numbers its projects differently.
	"""
	if not key:
		return None

	spec = next((project for project in PROJECTS if project["key"] == key), None)

	if not spec:
		return None

	return frappe.db.get_value(PROJECT_DOCTYPE, {"project_name": spec["name"]}, "name")


# --- the terms -----------------------------------------------------------------


def _terms() -> list[dict]:
	"""Each terms of reference, written and then submitted — two deliberate acts.

	Submitted, not left as a draft, because a draft takes no deployment: what
	somebody accepts when they accept an assignment is exactly this document, so
	the wording is frozen before anybody can be asked. That is the same pair of
	buttons the editor draws.
	"""
	from vmmsx.api.deployment import create_terms, submit_terms

	rows = []

	for spec in TERMS:
		existing = _terms_name(spec["key"])

		if existing:
			rows.append({"key": spec["key"], "name": existing, "status": "exists"})
			continue

		project = _project(spec["project"])

		if spec["project"] and not project:
			rows.append({"key": spec["key"], "status": "skipped: project missing"})
			continue

		frappe.set_user(COORDINATOR)

		try:
			created = create_terms(
				tor_name=spec["name"],
				project=project,
				purpose=spec["purpose"],
				mission_background=spec["background"],
				responsibilities=spec["responsibilities"],
				geo_scope=_node(spec["scope"]),
				default_duration_days=spec["duration_days"],
				required_certifications=[
					{"certification_type": key, "is_mandatory": 1 if mandatory else 0}
					for key, mandatory in spec["requires"]
					if frappe.db.exists("VMMS Certification Type", key)
				],
				objectives=[{"objective": line} for line in spec["objectives"]],
				expected_outputs=[{"output": line} for line in spec["outputs"]],
				approach_methods=[
					{"methodology": method, "notes": note}
					for method, note in spec["approach"]
					if frappe.db.exists("VMMS TOR Methodology", method)
				],
				itinerary=[
					{
						"activity_date": add_days(today(), day),
						"activity_time": time,
						"activity": activity,
						"person_responsible": who,
					}
					for day, time, activity, who in spec["itinerary"]
				],
				stakeholders=[
					{"designation": role, "full_name": name, "phone_number": phone, "email": email}
					for role, name, phone, email in spec["stakeholders"]
				],
				resources=[
					{
						"resource": resource,
						"needed_on": add_days(today(), day),
						"quantity": quantity,
						"unit": unit,
						"unit_cost": cost,
						"donor": donor,
					}
					for resource, day, quantity, unit, cost, donor in spec["resources"]
				],
			)
			submit_terms(created["name"])
		finally:
			frappe.set_user("Administrator")

		rows.append({"key": spec["key"], "name": created["name"], "status": "created"})

	return rows


def _terms_name(key: str | None) -> str | None:
	"""The docname of a seeded terms of reference, found by its display name.

	`tor_key` is derived by the service from the name and disambiguated against
	whatever the site already holds, so a seed cannot assume what it came out as
	— which is exactly why it is looked up by the words instead.
	"""
	if not key:
		return None

	spec = next((terms for terms in TERMS if terms["key"] == key), None)

	if not spec:
		return None

	return frappe.db.get_value(TERMS_DOCTYPE, {"tor_name": spec["name"]}, "name")


# --- the deployments -----------------------------------------------------------


def _deployments() -> list[dict]:
	"""Each deployment, its roster, its feed, and the status it ended up at."""
	rows = []

	for spec in DEPLOYMENTS:
		try:
			rows.append(_one_deployment(spec))
		except Exception as error:
			# One deployment that cannot be set up must not cost the other nine.
			# Reported with the real message, because a seed that silently skipped
			# one would leave a demo missing a branch and nothing to say why.
			frappe.db.rollback()
			rows.append({"key": spec["key"], "status": f"failed: {error}"})
		finally:
			frappe.set_user("Administrator")

	return rows


def _one_deployment(spec: dict) -> dict:
	"""One deployment, from nothing to wherever its entry stops."""
	from vmmsx.api.deployment import (
		assign_volunteers,
		create_deployment,
		post_deployment_update,
		set_assignment_role,
		set_deployment_status,
	)

	terms_of_reference = _terms_name(spec["terms"])
	node = _node(spec["where"])

	if not terms_of_reference:
		return {"key": spec["key"], "status": "skipped: terms missing"}

	if not node:
		return {"key": spec["key"], "status": "skipped: no geo node"}

	if _deployment(spec):
		return {"key": spec["key"], "status": "exists"}

	frappe.set_user(COORDINATOR)

	deployment = create_deployment(
		terms_of_reference=terms_of_reference,
		geo_node=node,
		start_date=add_days(today(), spec["start_in"]),
		end_date=add_days(today(), spec["end_in"]),
		volunteers_required=spec["required"],
	)

	# The roster, in the app's two verbs. Asking and placing are separate calls
	# because they are separate acts: `ask=True` raises a question the volunteer
	# answers, `ask=False` records that a coordinator has already arranged it.
	asked = [login for login, how, _note in spec["roster"] if how != "placed"]
	placed = [login for login, how, _note in spec["roster"] if how == "placed"]

	for logins, ask in ((asked, True), (placed, False)):
		volunteers = [_volunteer(login) for login in logins]
		volunteers = [volunteer for volunteer in volunteers if volunteer]

		if volunteers:
			assign_volunteers(name=deployment["name"], volunteers=volunteers, ask=ask)

	frappe.set_user("Administrator")

	# --- as each volunteer, answering their own -------------------------------
	answers = []

	for login, how, note in spec["roster"]:
		if how in ("placed", "asked"):
			continue

		answers.append(f"{login.split('@')[0]}: {_answer(deployment['name'], login, how, note)}")

	# --- back as the coordinator ----------------------------------------------
	frappe.set_user(COORDINATOR)

	if spec["lead"]:
		assignment = _assignment(deployment["name"], _volunteer(spec["lead"]))

		if assignment:
			set_assignment_role(name=assignment, role="leader")

	for entry_type, note in spec["updates"]:
		post_deployment_update(name=deployment["name"], note=note, entry_type=entry_type)

	# Last, because a status is where this stops rather than how it started:
	# every deployment is opened Planned and moved from there, and the roster and
	# the feed belong to a deployment that was open when they happened.
	if spec["status"] != "Planned":
		set_deployment_status(name=deployment["name"], status="Active")

		if spec["status"] == "Completed":
			set_deployment_status(name=deployment["name"], status="Completed")

	frappe.set_user("Administrator")

	return {
		"key": spec["key"],
		"name": deployment["name"],
		"status": "created",
		"where": _label(spec["where"]),
		"trail": f"{spec['status'].lower()}, {len(spec['roster'])} on the roster"
		+ (f" ({', '.join(answers)})" if answers else ""),
	}


def _answer(deployment: str, login: str, how: str, note: str | None) -> str:
	"""The volunteer's own answer to their own invitation, as the volunteer.

	`api.deployment.respond_to_assignment` and not the service, so the ownership
	check runs: the assignment being answered has to belong to the caller's own
	volunteer record. If the seed ever asked the wrong person, this is what would
	say so.
	"""
	from vmmsx.api.deployment import respond_to_assignment

	volunteer = _volunteer(login)
	assignment = _assignment(deployment, volunteer) if volunteer else None

	if not assignment:
		return "no assignment"

	frappe.set_user(login)

	try:
		respond_to_assignment(assignment=assignment, accept=how == "accepted", note=note)
	finally:
		frappe.set_user("Administrator")

	return how


def _deployment(spec: dict) -> str | None:
	"""This entry's deployment, if a previous run made it.

	Identified by its terms, its place and its start date together, because a
	deployment has no business key of its own — two blood drives under the same
	terms in the same branch are two deployments, and the date is what separates
	them.
	"""
	terms_of_reference = _terms_name(spec["terms"])
	node = _node(spec["where"])

	if not (terms_of_reference and node):
		return None

	return frappe.db.get_value(
		DEPLOYMENT_DOCTYPE,
		{
			"terms_of_reference": terms_of_reference,
			"geo_node": node,
			"start_date": add_days(today(), spec["start_in"]),
		},
		"name",
	)


def _assignment(deployment: str, volunteer: str | None) -> str | None:
	"""This volunteer's assignment on this deployment, whatever state it is in."""
	if not volunteer:
		return None

	return frappe.db.get_value(ASSIGNMENT_DOCTYPE, {"deployment": deployment, "volunteer": volunteer}, "name")


def _volunteer(login: str) -> str | None:
	"""The volunteer record behind a seeded login, or None if they have none.

	Through the Red Profile, which is the person, because the volunteer record is
	one of the things a person may be. Somebody whose application was rejected or
	is still in review has a profile and no volunteer, and this returns None for
	them rather than pretending otherwise.
	"""
	profile = frappe.db.get_value("Red Profile", {"user": login}, "name")

	if not profile:
		return None

	return frappe.db.get_value("VMMS Volunteer", {"red_profile": profile}, "name")


# --- where --------------------------------------------------------------------


def _node(where) -> str | None:
	"""A `where` tuple resolved to a Geo Node, through `tanzania.py`'s own lookups.

	`None` in — a terms of reference with no scope means anywhere — and `None`
	out for a node this site does not have, which every caller reports rather
	than guessing past.
	"""
	if not where:
		return None

	kind, *rest = where

	if kind == "national":
		return tanzania.national()

	if kind == "branch":
		return tanzania.branch(rest[0])

	return tanzania.sub_branch(rest[0], rest[1])


def _label(where) -> str:
	"""The same tuple as words, for the report."""
	if not where:
		return "anywhere"

	kind, *rest = where

	if kind == "national":
		return tanzania.ORGANIZATION_NAME

	if kind == "branch":
		return rest[0]

	return f"{rest[1]} / {rest[0]}"


# --- the one thing a user could not do ----------------------------------------


def _backdate() -> list[dict]:
	"""Move each record's `creation` back to when the work says it began.

	The same admission `tanzania_people._backdate` makes: everything else here is
	the product's own behaviour, and this is the seed owning up to having run
	today. A project that started in March but was filed this morning reads as a
	demo built this morning, which is the one thing this seed exists to avoid.

	Only `creation` moves. The dates that are *fields* — start, end, joined on —
	were written forward from today at creation and are already right, and
	rewriting them here would make the two disagree. `update_modified=False` so
	the rewrite does not stamp today onto `modified` and undo half the effect.

	**Nothing is ever dated forward.** Work that has not started yet was filed
	today, which is both the truth and what a coordinator's own register would
	show, so `_no_later_than_today` floors every date below at today rather than
	inventing a record that was created next month.
	"""
	rows = []

	for spec in PROJECTS:
		name = _project(spec["key"])

		if not name:
			continue

		# A programme is opened a little before it starts, not on the morning of.
		when = _no_later_than_today(int(spec["start_in"]) - 10)
		frappe.db.set_value(PROJECT_DOCTYPE, name, "creation", when, update_modified=False)

		# The terms written under it, and everything run against those, cannot
		# predate it. Each is dated from its own work rather than from the
		# project, and floored at the project's own date below.
		rows.append({"key": spec["key"], "status": f"project dated {when}"})

	for spec in TERMS:
		name = _terms_name(spec["key"])

		if not name:
			continue

		project = PROJECTS_BY_KEY.get(spec["project"])
		# Terms are written after the programme is opened and before the work
		# starts. With no project — the two standing duties — they are simply old.
		when = _no_later_than_today(int(project["start_in"]) - 5 if project else -240)
		frappe.db.set_value(TERMS_DOCTYPE, name, "creation", when, update_modified=False)
		rows.append({"key": spec["key"], "status": f"terms dated {when}"})

	for spec in DEPLOYMENTS:
		name = _deployment(spec)

		if not name:
			continue

		when = _no_later_than_today(int(spec["start_in"]) - 4)
		frappe.db.set_value(DEPLOYMENT_DOCTYPE, name, "creation", when, update_modified=False)

		# The roster and the feed happened while the deployment was being set up,
		# so they move with it rather than staying on today.
		for assignment in frappe.get_all(ASSIGNMENT_DOCTYPE, filters={"deployment": name}, pluck="name"):
			frappe.db.set_value(ASSIGNMENT_DOCTYPE, assignment, "creation", when, update_modified=False)

		rows.append({"key": spec["key"], "status": f"deployment dated {when}"})

	return rows


def _no_later_than_today(days: int):
	"""`days` from today, floored at today. Never a record created in the future."""
	return add_days(today(), min(int(days), 0))


def _print(report: dict) -> None:
	print("\n" + "=" * 66)
	print("Tanzania Red Cross Society — projects, terms of reference and deployments")
	print("=" * 66)

	for section, entries in report.items():
		print(f"\n{section}")

		for row in entries:
			detail = row.get("trail") or row.get("where") or ""
			print(f"  {row['status']:<28} {row['key']}{'  ' + detail if detail else ''}")

	print(f"\nThe coordinator signs in as {COORDINATOR} with {tanzania.DEMO_PASSWORD}")
	print(f"  {len(PROJECTS)} projects, {len(TERMS)} terms of reference, {len(DEPLOYMENTS)} deployments")
	print()
