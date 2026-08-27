"""Generate the detailed VMMS end-to-end volunteer journey work plan."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from generate_two_week_plan import (
    CONTENT_TYPES,
    DOC_RELS,
    NUMBERING,
    ROOT_RELS,
    W,
    bullet,
    page_break,
    para,
    run,
    styles,
    table,
)


OUTPUT = Path(__file__).resolve().parents[2] / "VMMS_End_to_End_Volunteer_Journey_Work_Plan.docx"


def journey_table(rows: list[list[str]]) -> str:
    return table(
        ["Step", "User journey", "Management and system requirements", "Completion evidence"],
        rows,
        [1050, 2500, 3900, 1600],
    )


def document() -> str:
    body: list[str] = [
        para("VMMS", bold=True, color="2E75B6", size=44, align="center", before=1400, after=120),
        para("End-to-End Volunteer Journey Work Plan", bold=True, color="17365D", size=34, align="center", after=180),
        para("From Registration to Record Management, Engagement and Deployment", size=24, color="5B6573", align="center", after=650),
        para("A configurable product for National Red Cross and Red Crescent Societies", size=20, color="68737D", align="center", after=750),
        para("Prepared for supervisor and product review", bold=True, size=22, align="center", after=100),
        para("Prepared by: ______________________________", size=20, align="center", after=120),
        para("Supervisor: _______________________________", size=20, align="center", after=120),
        para("Date: 26 August 2026", size=20, align="center", after=120),
        page_break(),
        para("1. Purpose and product vision", style="Heading1"),
        para(
            "This work plan follows the volunteer and member journey in the order a real person experiences it. It begins before registration, continues through application and review, creates a trustworthy long-term record, and then uses that record for opportunities, events, communication and deployment. The purpose is to make sure we do not build isolated modules that look complete but leave the user or manager with a dead end."
        ),
        para(
            "The target is not a system that works only for one country. VMMS should be a configurable product that another National Society can adopt without changing source code for its questions, geography, terminology, approval ladder, membership types, languages, communications or optional integrations. Every stage below therefore covers both the visible user experience and the configuration, permissions, audit and testing needed underneath it."
        ),
        para("Guiding product rules", style="Heading2"),
        bullet("One person, one Red Profile, with separate volunteer and member affiliations when the person has both."),
        bullet("Core data needed for identity, matching, access and reporting remains structured; society-specific questions are configurable."),
        bullet("Every page tells the user where they are, what happened, what happens next and who can help."),
        bullet("Every manager action is geographically scoped, permission checked and recorded in an audit history."),
        bullet("A workflow is not complete until both the user-facing action and the manager-facing response are usable."),
        bullet("No country name, currency, phone prefix, language, branch level, branding or approval role is hard-coded."),
        bullet("Mobile, slow-network, accessibility, privacy and notification behaviour are acceptance requirements, not later decoration."),
        para("2. Whole journey at a glance", style="Heading1"),
        table(
            ["Journey stage", "Volunteer/member experience", "Society outcome"],
            [
                ["1. Discover and sign in", "Understands the Society, available paths and how personal data will be used; creates or accesses an account.", "A secure account is linked to one person without duplicates."],
                ["2. Register", "Completes the relevant core fields and the Society’s own configured questions; saves and resumes if interrupted.", "A complete, validated application is routed to the correct geography and workflow."],
                ["3. Review and correct", "Tracks status, receives a clear request for more information, edits and resubmits.", "Authorized reviewers make consistent, auditable decisions within their scope."],
                ["4. Onboard", "Receives approval, orientation and a clear home dashboard.", "An active volunteer or member record is created once and linked to its source application."],
                ["5. Manage the relationship", "Maintains permitted profile, skills and availability information.", "Managers have a current, searchable and historically accurate record."],
                ["6. Participate", "Finds volunteer opportunities and events, expresses interest or registers, and sees outcomes.", "Managers can select people, manage capacity and see participation."],
                ["7. Deploy", "Receives an assignment, confirms availability, gets instructions, completes work and records service.", "The Society plans, staffs, monitors and closes a deployment safely."],
                ["8. Communicate and retain", "Receives relevant, preferred and timely messages; can give feedback or leave.", "The Society maintains engagement, service history and lifecycle records."],
            ],
            [1900, 4000, 3050],
        ),
        page_break(),
        para("3. What already exists and how the plan treats it", style="Heading1"),
        para(
            "The current VMMS codebase already contains several strong foundations. The implementation work should validate and extend them rather than creating competing versions."
        ),
        table(
            ["Capability", "Current foundation", "Work-plan treatment"],
            [
                ["Identity", "A shared Red Profile supports separate volunteer and member records.", "Keep it as the canonical person record; strengthen duplicate, merge and correction journeys."],
                ["Geographic access", "Geo Nodes, assignments and fail-closed scope rules exist.", "Use the same scope service for lists, dossiers, decisions, communications and exports; test every role."],
                ["Dynamic questions", "VMMS Application Question and the Form Questions screen already support groups, order, required status, help text, activation and multiple answer types.", "Harden and extend the existing builder with versioning, conditions, translation, preview and data-governance controls."],
                ["Approvals", "A routed approval engine supports approve, reject and request-more-information decisions.", "Complete the applicant edit/resubmit loop and make reviewer queues operationally complete."],
                ["Google sign-in", "The installed Frappe framework supports Google through Social Login Key and its OAuth login flow.", "Configure and test the native feature; do not build a second OAuth implementation."],
                ["Events and communication", "Buzz integration, event intentions, announcements, email and SMS seams exist.", "Choose clear sources of truth and finish the manager status/participant/delivery loops."],
                ["Deployments", "Requests, Terms of Reference, assignments, invitations, tasks and status services exist.", "Connect them into one guided planning-to-closeout journey."],
            ],
            [2000, 3950, 3000],
        ),
        para("4. Stage 0 — National Society setup before registration opens", style="Heading1"),
        para(
            "Registration cannot be truly dynamic if each new Society requires a developer to change labels, branches or rules. The first administrative journey is therefore the Society setup wizard. It should be completed before public registration is enabled."
        ),
        journey_table([
            ["0.1", "An implementation administrator creates the Society profile.", "Configure name, emblem, public contacts, help desk, website domain, privacy links, default locale, time zone, date format and feature flags.", "Branding and help details appear consistently on public, portal, email and document surfaces."],
            ["0.2", "The administrator imports or builds the geographic structure.", "Configure country, regions, districts, branches and any permitted application anchor level; validate parent/child integrity.", "Registration branch picker and manager scope tests return the expected branches."],
            ["0.3", "The administrator defines local vocabularies.", "Configure skills, languages, availability slots, motivations, identification types, membership types, event categories and deployment terms.", "No local vocabulary is embedded in frontend code."],
            ["0.4", "The administrator defines roles and assignments.", "Set volunteer reviewer, membership reviewer, coordinator, deployment manager and communication permissions; assign each to geography and validity dates.", "A role-and-scope matrix proves allowed and refused actions."],
            ["0.5", "The administrator builds approval ladders.", "Choose workflow stages, roles, geography, SLA, escalation and delegation separately for volunteer and membership applications.", "A test application routes to exactly the expected reviewer sequence."],
            ["0.6", "The administrator configures integrations.", "Enable only installed providers: Google sign-in, email, SMS, Buzz, payments, LMS or HRMS. Store credentials securely per deployment.", "Configuration health page shows ready, unavailable or action required for each integration."],
        ]),
        para("Stage 0 deliverable", style="Heading2"),
        para("A repeatable Society setup package, configuration checklist and health report that can prepare a new National Society without source-code changes."),
        page_break(),
        para("5. Stage 1 — Discovery, account creation and sign-in", style="Heading1"),
        journey_table([
            ["1.1", "A visitor opens the public landing page and understands what volunteering and membership mean.", "Publish Society-owned content, eligibility, benefits/responsibilities, expected time, fees where relevant, safeguarding statement, privacy notice and support contact.", "Usability test users can choose the correct path without staff explanation."],
            ["1.2", "The visitor chooses Volunteer, Member or Both over time.", "Keep the paths independent but use one account and one profile. Explain that a user may complete the second affiliation later.", "A volunteer application never blocks a valid membership application, and vice versa."],
            ["1.3", "The visitor creates an account with email/password or Google.", "Use Frappe’s native signup and Social Login Key. Preserve the intended return URL so successful login returns to the chosen registration path.", "Both login methods return the user to the correct step without losing their selection."],
            ["1.4", "The user verifies the account and accepts essential terms.", "Apply email verification according to policy, rate limiting, CAPTCHA where justified, consent version capture and secure session handling.", "Unverified or abusive signup attempts cannot submit an application; legitimate recovery succeeds."],
            ["1.5", "A returning user signs in or recovers access.", "Provide password reset/email link fallback even when Google is enabled. Handle disabled accounts and changed email through governed account support.", "Recovery, expired link and provider-error scenarios give a clear next action."],
        ]),
        para("Google sign-in configuration checklist", style="Heading2"),
        bullet("Create a Google OAuth client for the Society’s actual domain and configure the approved consent screen."),
        bullet("Create and enable the Frappe Social Login Key for Google; store the client secret outside source control."),
        bullet("Register the exact callback/redirect URL shown by Frappe and test production HTTPS behaviour."),
        bullet("Decide whether new social-login users may sign up or only existing accounts may link."),
        bullet("Match on verified email and prevent a second User or Red Profile when the same person changes login method."),
        bullet("Preserve /join?path=volunteer or /join?path=member across the OAuth round trip."),
        bullet("Test consent denial, missing email, existing email, disabled account, provider outage, revoked access and fallback login."),
        para("Stage 1 deliverable", style="Heading2"),
        para("A tested account-entry journey with native Google sign-in, a conventional fallback, correct redirect handling and no duplicate person creation."),
        page_break(),
        para("6. Stage 2 — Registration form design", style="Heading1"),
        para("6.1 Separate system-critical fields from configurable questions", style="Heading2"),
        para(
            "Fields used by identity matching, geographic routing, opportunity matching, permissions or reporting should remain structured core fields. A National Society may change their labels and whether optional policy fields are shown, but should not replace them with free-text custom answers. Questions that are locally important but do not drive system logic belong in the form builder."
        ),
        table(
            ["Core form section", "Volunteer registration", "Membership registration", "Important rules"],
            [
                ["Identity", "First and last name, preferred name if adopted, date of birth/age eligibility, profile photo where required.", "Same shared identity; do not ask again when already known.", "Email comes from the account. Collect gender, nationality or ID only when policy and purpose justify it."],
                ["Contact", "Primary phone, preferred language and safe communication channel.", "Same shared contact record.", "Normalize numbers using Society country settings; allow governed self-correction."],
                ["Geography", "Residence and requested serving branch, including local/abroad path.", "Membership branch or chapter.", "Use the configured Geo Node tree; do not hard-code administrative levels."],
                ["Volunteer profile", "Skills, languages, availability, interests/motivation, prior experience and relevant certifications.", "Not normally required unless the membership type needs them.", "Use controlled vocabularies plus carefully governed ‘not listed’ requests."],
                ["Membership choice", "Optional link inviting the user to join as a member later.", "Membership type, fee information, period and branch.", "Prices, currency and eligibility come from configuration."],
                ["Safety and consent", "Code of conduct, safeguarding/privacy acknowledgements, emergency contact where deployment policy requires it.", "Privacy, membership rules and communications consent.", "Record policy version, date, method and withdrawal rules; avoid blanket consent."],
                ["Documents", "Identification or locally required evidence.", "Proof or documents only where the configured process requires them.", "Private upload, size/type checks, ownership, malware scanning if available, retention and authorized access."],
            ],
            [1700, 2700, 2300, 2250],
        ),
        para("6.2 Step-by-step registration screen", style="Heading2"),
        journey_table([
            ["2.1", "The user sees eligibility, expected documents, time needed and privacy information before starting.", "Render content from Society settings and registration type; do not surprise the user near submission.", "Start page is understandable on a phone and has an accessible help route."],
            ["2.2", "The user confirms or completes identity details.", "Prefill the Red Profile, prevent email reassignment, identify possible duplicates and separate self-correction from application claims.", "Existing users do not re-enter known data and cannot attach themselves to another profile."],
            ["2.3", "The user selects residence and serving branch.", "Use a searchable cascading Geo Node picker; explain why the branch receives the application; support local and abroad rules.", "Only permitted registration anchor levels can be submitted."],
            ["2.4", "The volunteer records skills, languages, interests, experience and availability.", "Load controlled vocabularies dynamically and save stable identifiers, not display labels.", "The resulting data is usable by opportunity/deployment matching."],
            ["2.5", "The member selects a membership type and sees the corresponding obligations, period and fee.", "Filter available types by Society policy and location; state whether payment is before or after approval.", "The selected type and expected next step are unambiguous."],
            ["2.6", "The user answers the Society’s custom questions.", "Fetch the published form version for this registration, evaluate conditions server-side and render accessible controls grouped into sections.", "The submitted application preserves exactly what was asked and answered."],
            ["2.7", "The user uploads required documents.", "Use private files, verify owner/MIME/size, attach atomically to the application and remove abandoned uploads after retention period.", "A reviewer with application access can open the file; nobody else can."],
            ["2.8", "The user reviews all answers and declarations before submission.", "Show a sectioned summary with Edit links, consent text/version and any missing requirement.", "No required field is missing and the user can correct any section without losing later answers."],
            ["2.9", "The user submits once and receives a reference.", "Perform server validation, duplicate/open-application checks, assign geography/workflow, freeze a revision and make the operation idempotent.", "Double-click or retry does not create duplicate applications."],
            ["2.10", "The user sees confirmation and status.", "Display reference, submission time, responsible branch, expected response time, next step and help contact; send preferred-channel confirmation.", "The applicant can return later and see the same truthful status."],
        ]),
        para("6.3 Draft, autosave and resilience", style="Heading2"),
        bullet("Create an authenticated server-side draft early, then autosave changed sections with a visible saved timestamp."),
        bullet("Resume the draft on another device and preserve the chosen volunteer/member path."),
        bullet("Handle offline or slow-network failure without clearing entered data or creating duplicate writes."),
        bullet("Warn before leaving with unsaved changes and provide an intentional Save and continue later action."),
        bullet("Version the form so a draft can be migrated deliberately if questions change before submission."),
        bullet("Expire abandoned drafts and unattached files according to a configurable retention policy."),
        page_break(),
        para("7. Stage 3 — Dynamic form builder", style="Heading1"),
        para(
            "The project already has a dynamic question builder. It should be treated as a product capability and completed to the standard needed for reuse across National Societies. An administrator should be able to adapt registration safely without asking a developer or changing old applications."
        ),
        table(
            ["Builder capability", "Required behaviour", "Status/direction"],
            [
                ["Target and grouping", "Choose Volunteer Application or Membership; organize questions into named sections and reorder them.", "Existing foundation—validate and polish."],
                ["Question controls", "Short text, long text, number, date, checkbox, single select, multi-select, attachment and informational text.", "Several types exist; add missing multi-select/information types only when renderer and server validation are ready."],
                ["Question definition", "Label, stable key, help text, placeholder, required status, choices, validation/range and answer sensitivity.", "Extend existing definition without breaking historical answers."],
                ["Conditional rules", "Show or require a question based on registration path, membership type, age band, geography or a previous answer.", "Add a small governed rule builder; evaluate the same rule on client and server."],
                ["Lifecycle", "Draft changes, preview, publish a version, schedule activation, retire rather than delete, and restore a prior version.", "Add explicit versions; published forms are immutable."],
                ["Historical accuracy", "Store question wording, type, group, choices and form version with each answer.", "Snapshot pattern exists—retain and expand it."],
                ["Translation", "Provide a source label/help text and translations for enabled Society languages, with fallback.", "Add to builder and frontend locale infrastructure."],
                ["Privacy", "Mark purpose, sensitivity, reviewer visibility and retention rule; warn before collecting high-risk data.", "Add governance metadata and enforce it in dossiers/exports."],
                ["Reuse", "Clone a form, export/import a reviewed template, compare versions and provide recommended baseline questions.", "Needed for rolling VMMS out to additional Societies."],
                ["Permissions and audit", "Only a dedicated configuration role can publish; every change records who, when and why.", "Keep server-side DocType permissions; add publish permission and audit presentation."],
            ],
            [2100, 4800, 2050],
        ),
        para("Form-builder safeguards", style="Heading2"),
        bullet("Do not allow a custom question to replace a structured field used for routing, access, identity or matching."),
        bullet("Validate all answers again on the server; the browser is never the source of truth."),
        bullet("Do not apply a newly published required question retrospectively to already-submitted applications."),
        bullet("Block deletion when answers exist; deactivate or retire instead."),
        bullet("Preview the exact mobile and desktop form before publishing."),
        bullet("Run a form health check for duplicate keys, unreachable conditions, missing translations and invalid choices."),
        para("Stage 2–3 deliverable", style="Heading2"),
        para("A resumable, versioned volunteer and membership registration journey whose core fields support system logic and whose local questions can be safely managed without code changes."),
        page_break(),
        para("8. Stage 4 — Submission, review and applicant correction", style="Heading1"),
        para("8.1 Application state model", style="Heading2"),
        table(
            ["State", "Who owns the next action", "Allowed actions"],
            [
                ["Draft", "Applicant", "Edit, save, submit or discard."],
                ["Submitted", "System/queue", "Route to the first valid reviewer; applicant may view or withdraw under policy."],
                ["In Review", "Assigned reviewer", "Approve stage, request more information, reject, add internal note or reassign/delegate if allowed."],
                ["More Information Required", "Applicant", "Read the reason, edit permitted sections/files, save and resubmit or withdraw."],
                ["Approved", "System/onboarding staff", "Create/activate the appropriate affiliation and start onboarding."],
                ["Rejected", "Applicant/support", "View reason and appeal/reapply according to policy."],
                ["Withdrawn/Expired", "Applicant/system", "View history and start again only when policy permits."],
            ],
            [1900, 2600, 4450],
        ),
        para("8.2 Reviewer journey", style="Heading2"),
        journey_table([
            ["4.1", "The authorized reviewer opens My Review Queue.", "Show only routed and in-scope applications; include count, SLA/age, branch, type and safe search/filter/sort.", "Cross-branch and unrouted access tests fail; legitimate queue results are complete."],
            ["4.2", "The reviewer opens a clear application dossier.", "Show identity, placement, structured volunteer/member data, grouped custom answers, readable attachments, duplicate warnings, prior decisions and current stage.", "The reviewer need not open Desk or several records to understand the application."],
            ["4.3", "The reviewer records a decision.", "Require an explicit confirmation naming the applicant and consequence. Require a useful reason for rejection and more-information requests.", "One decision is recorded with actor, role, stage, time and reason."],
            ["4.4", "The reviewer requests more information.", "Select or describe the exact fields/documents needing correction; return the application to the applicant and invalidate prior approval endorsements for the changed revision.", "The applicant receives an actionable request, not a generic status."],
            ["4.5", "The applicant follows the notification back to the application.", "Authorize by session ownership; display reviewer reason; highlight requested sections and prefill the submitted revision.", "The applicant can edit the correct record and cannot edit another person’s application."],
            ["4.6", "The applicant edits, saves and resubmits.", "Allow only policy-approved fields; retain previous revision and attachments; validate the current form contract; create a new revision and restart review safely.", "Before/after history is readable and the new submission appears once in the correct queue."],
            ["4.7", "All parties are notified.", "Send applicant notifications for received, more info, resubmitted, approved and rejected; notify the next reviewer when their action starts.", "Notification log matches state history and contains working deep links."],
            ["4.8", "Supervisors monitor workload.", "Provide overdue counts, escalation, temporary delegation and an audit trail without widening geography.", "No application becomes invisible because a reviewer is absent."],
        ]),
        para("8.3 Exact correction loop to implement", style="Heading2"),
        para(
            "Submitted → In Review → Reviewer chooses Request More Information and gives a reason → application becomes More Information Required → applicant receives email/SMS/in-app notification with a secure link → applicant opens the submitted answers in edit mode → requested fields are highlighted → applicant saves a revised draft → applicant reviews and resubmits → revision number increases and previous revision remains read-only → review restarts at the configured stage → reviewer receives a resubmission notification → final decision continues normally."
        ),
        para("Stage 4 deliverable", style="Heading2"),
        para("A geographically scoped, auditable review process with a complete and tested request-more-information/edit/resubmit loop for both volunteer and membership applications."),
        page_break(),
        para("9. Stage 5 — Approval, onboarding and activation", style="Heading1"),
        journey_table([
            ["5.1", "The applicant receives a clear approval message.", "State what was approved, effective date, branch, membership validity where relevant, next onboarding task and contact.", "Approval message and portal status agree."],
            ["5.2", "The system creates or activates the affiliation.", "Idempotently create one VMMS Volunteer and/or VMMS Member linked to the same Red Profile and source application; apply correct portal roles.", "Retrying approval cannot create duplicate affiliations or roles."],
            ["5.3", "The new volunteer completes onboarding.", "Configure induction checklist: orientation, code of conduct, safeguarding, required training, emergency details, ID/card and availability confirmation.", "Dashboard shows completed and outstanding onboarding steps."],
            ["5.4", "The member completes membership activation.", "Handle the configured approval/payment order, validity dates, receipt, card/certificate and renewal date.", "Membership is Active only when the configured conditions are satisfied."],
            ["5.5", "The user arrives at a relevant home dashboard.", "Adapt navigation to actual affiliations; show next actions, current status, opportunities, events, deployments and messages.", "A member-only user does not see irrelevant volunteer pages and a dual-status user sees both clearly."],
        ]),
        para("Stage 5 deliverable", style="Heading2"),
        para("An approved application reliably becomes one active, usable affiliation with a guided onboarding checklist and an appropriate portal experience."),
        para("10. Stage 6 — Volunteer and member record management", style="Heading1"),
        para(
            "The record is the continuing relationship with the person, not just a copy of the application. The original application and each revision remain historical evidence; the current profile, capabilities and status are maintained separately with clear ownership."
        ),
        journey_table([
            ["6.1", "A manager searches the people register.", "Search by name, reference, phone/email where permitted, branch, affiliation, status, skill, language, availability and standing; paginate and sort server-side.", "A branch user finds legitimate records quickly and cannot infer out-of-scope records."],
            ["6.2", "A manager opens one person dossier.", "Show overview, contact, affiliations, applications, skills, availability, certifications, events, opportunities, deployments, tasks, hours, communications, documents and audit tabs according to permission.", "One dossier provides the operational picture without overexposing sensitive data."],
            ["6.3", "The person maintains permitted information.", "Allow self-service updates to contact, preferred language, skills and availability; route sensitive identity or branch changes for approval.", "Every editable field has a named owner and change history."],
            ["6.4", "The manager changes status when justified.", "Support Active, Suspended and Exited with reason, dates, effect on assignments/roles and reactivation policy.", "Status changes are auditable and consistently enforced across the portal."],
            ["6.5", "A person changes branch.", "Provide a transfer request, source/destination review, effective date, open-deployment warning and history.", "Transfer changes future scope without rewriting historical service records."],
            ["6.6", "Data quality staff handle duplicates and corrections.", "Detect probable duplicates; provide governed merge/relink tools; never silently combine people.", "Duplicate resolution produces an audit report and preserves references."],
            ["6.7", "Authorized users export or report.", "Apply the same scope and field-level privacy rules to reports/exports; log sensitive exports and limit bulk size.", "Export cannot become a shortcut around dossier permissions."],
        ]),
        para("Stage 6 deliverable", style="Heading2"),
        para("A current, searchable and privacy-aware person dossier that supports both self-service and manager operations while preserving application and lifecycle history."),
        page_break(),
        para("11. Stage 7 — Volunteer opportunities and expressions of interest", style="Heading1"),
        para(
            "Volunteer opportunities must be distinct from paid employment vacancies. HRMS Job Opening can continue to represent jobs, while VMMS should own a volunteer opportunity and interest workflow that can lead to an event role, task or deployment."
        ),
        journey_table([
            ["7.1", "A manager creates a volunteer opportunity.", "Capture title, programme, branch/scope, description, responsibilities, dates, place/remote mode, capacity, application window, contact, required skills/certifications, age/safeguarding constraints and status.", "A complete draft can be previewed before publication."],
            ["7.2", "The opportunity is approved and published.", "Apply optional content approval, publish/unpublish dates and geographic/audience visibility.", "Only approved, open opportunities appear to eligible users."],
            ["7.3", "A volunteer browses and filters opportunities.", "Filter by location, date, programme, skill, remote/in-person and eligibility; explain why a user is or is not eligible.", "Cards show enough information to make an informed choice."],
            ["7.4", "The volunteer expresses interest.", "Prefill profile/capabilities, ask only opportunity-specific questions, capture consent/availability and prevent duplicate interest.", "Volunteer receives a reference and meaningful status."],
            ["7.5", "A manager reviews interested volunteers.", "Show fit indicators without making an opaque automated decision; shortlist, waitlist, accept or decline with reason.", "Manager can fill capacity and every applicant receives an outcome."],
            ["7.6", "Accepted interest becomes operational work.", "Convert to an event role, task or deployment assignment without retyping the person and requirements.", "Traceability links opportunity → interest → assignment → service outcome."],
        ]),
        para("Stage 7 deliverable", style="Heading2"),
        para("A configurable volunteer-opportunity catalogue and interest pipeline that is separate from employment recruitment and connects directly to operational assignment."),
        para("12. Stage 8 — Events and participation", style="Heading1"),
        para(
            "Choose one source of truth. Where Buzz is installed, Buzz should own event publication, ticket/booking rules, payment, verification and check-in. VMMS should present the event to the right users and bring the participation status back into the volunteer dossier. A separate VMMS intention should only remain if managers genuinely use it for planning and its meaning is clearly different from a booking."
        ),
        journey_table([
            ["8.1", "An event manager creates and publishes an event.", "Capture schedule, venue/online link, host, category, capacity, accessibility, audience, registration window, cost and check-in rules in the chosen source system.", "Published event has one canonical identifier and owner."],
            ["8.2", "A volunteer/member discovers the event.", "Show only published events; provide search, date/location/category filters and accessible event details.", "User understands whether the action is RSVP, interest or confirmed booking."],
            ["8.3", "The user registers or books.", "Delegate ticket/payment rules to Buzz when used; prevent duplicate booking and return a clear confirmation/cancellation path.", "User and manager see the same participation status."],
            ["8.4", "The manager views participants and capacity.", "Provide scoped participant register, waitlist, cancellations, special requirements and safe export.", "Manager can plan from the register without using another hidden list."],
            ["8.5", "Attendance is recorded.", "Use QR/manual check-in with correction controls; sync attendance to the volunteer’s service history where policy permits.", "Participation history distinguishes registered, attended, absent and cancelled."],
        ]),
        para("Stage 8 deliverable", style="Heading2"),
        para("One coherent event discovery, registration, participant-management and attendance journey with an explicit VMMS/Buzz ownership contract."),
        page_break(),
        para("13. Stage 9 — Deployment from need to closeout", style="Heading1"),
        journey_table([
            ["9.1", "A programme or branch raises a need for volunteers.", "Create a deployment request with purpose, Terms of Reference, geography, dates, numbers, roles, skills, risk, safeguarding, budget/logistics and justification.", "Request is complete enough to approve and staff."],
            ["9.2", "The request is reviewed and approved.", "Route using configured scope/workflow; record changes and approval; create the deployment only once.", "Approved request and created deployment are linked."],
            ["9.3", "The manager plans the deployment.", "Confirm lead, dates, locations, capacity, role slots, itinerary, transport, accommodation, contacts, safety briefing and required documents/training.", "Readiness checklist identifies blockers before invitations."],
            ["9.4", "The manager finds suitable volunteers.", "Filter by active status, geography, skill, language, certification, availability, recent workload and conflicts. Show why each candidate matches; let the manager decide.", "Candidate list is explainable, scoped and does not overbook people."],
            ["9.5", "Selected volunteers receive invitations.", "Send role, dates, place, expectations, deadline and accept/decline links; support reminders and accessible fallback.", "Every invitation has Sent, Delivered where available, Accepted, Declined, Expired or Cancelled status."],
            ["9.6", "The volunteer responds.", "Derive identity from the session; capture decline reason optionally; prevent response after cancellation/expiry; update available capacity.", "Both volunteer and manager immediately see the same answer."],
            ["9.7", "The manager finalizes the roster.", "Fill role slots, manage reserve list, confirm readiness documents, prevent conflicts and issue final instructions.", "A versioned roster and contact sheet are available to authorized staff."],
            ["9.8", "The team deploys and receives updates.", "Activate deployment; support check-in, announcements, itinerary changes, task assignment, welfare/safety contacts and incident escalation.", "Operational dashboard shows people, tasks, issues and latest update."],
            ["9.9", "Volunteers complete tasks and time.", "Separate volunteer submission from manager sign-off; attach proof securely; approve/dispute hours and record attendance.", "Only validated service appears in recognized totals."],
            ["9.10", "The manager closes the deployment.", "Confirm all people are accounted for, close tasks, approve hours/expenses as applicable, record outcomes and lessons, and notify participants.", "Deployment cannot be Completed while defined closure checks are open."],
            ["9.11", "The volunteer sees the completed service.", "Add deployment role, dates, approved hours, feedback and any certificate/service letter to the personal history.", "Service record is traceable to an approved assignment and completion."],
        ]),
        para("Recommended deployment state model", style="Heading2"),
        para("Requested → Under Approval → Planned → Recruiting → Ready → Active → Closing → Completed, with Cancelled available from governed stages. Assignments move through Proposed → Invited → Accepted/Declined/Expired → Active → Completed/Withdrawn."),
        para("Stage 9 deliverable", style="Heading2"),
        para("An explainable, conflict-aware deployment workflow connecting the approved need, suitable people, invitations, readiness, live coordination, validated service and closeout history."),
        page_break(),
        para("14. Stage 10 — Communication throughout the journey", style="Heading1"),
        para(
            "Communication is not one screen at the end. Transactional notifications should be designed with each state change, while campaign communication gives managers a safe way to address groups."
        ),
        journey_table([
            ["10.1", "The system sends transactional updates.", "Create configurable templates and deep links for signup, submission, more information, resubmission, decisions, onboarding, opportunity outcomes, event changes and deployment invitations/status.", "Each important state transition has an appropriate, tested notification."],
            ["10.2", "The user sets communication preferences.", "Store preferred language/channel and non-essential opt-outs separately from messages required to deliver a requested service.", "Campaigns respect consent while essential operational notices remain governed and explicit."],
            ["10.3", "A manager selects an audience.", "Resolve audience from current scoped records, opportunity/event/deployment participation or configured segment; never accept an unscoped hidden recipient list.", "Preview shows actual people and reachable count by channel."],
            ["10.4", "The manager composes and previews.", "Support approved templates, variables, language variants, links, schedule, expiry, test send and confirmation naming audience/count/channel.", "Manager can verify the message and recipients before the irreversible action."],
            ["10.5", "The system sends or hands off.", "Use in-app/email directly and create a governed SMS campaign in onerc_sms; make idempotency and provider failures visible.", "A retry does not duplicate successful deliveries."],
            ["10.6", "The manager reviews delivery.", "Show queued, sent, delivered, failed, bounced and opted-out counts where providers support them; allow safe retry of failures.", "Communication history is visible from campaign and person/deployment context."],
        ]),
        para("Stage 10 deliverable", style="Heading2"),
        para("Consistent, Society-branded and preference-aware communication with recipient preview, approval where needed, delivery history and working links back to the relevant action."),
        para("15. Stage 11 — Ongoing service, retention and exit", style="Heading1"),
        journey_table([
            ["11.1", "The volunteer maintains capability and availability.", "Self-service skills, languages, certifications and availability; verification/expiry for capabilities that affect safety.", "Matching uses current, trusted data."],
            ["11.2", "The volunteer sees a service history.", "Summarize approved tasks, events, deployments, hours, training and recognition with source links.", "Totals can be reproduced from approved underlying records."],
            ["11.3", "The Society checks engagement and wellbeing.", "Use transparent reminders and manager follow-up, not hidden automated judgments; record feedback and safeguarding referrals appropriately.", "Managers can identify follow-up needs within scope."],
            ["11.4", "Membership renews or changes.", "Provide expiry reminders, safe renewal, permitted type change, payment/approval status and preserved history.", "A renewal creates a new period without rewriting the previous one."],
            ["11.5", "A person pauses, transfers or exits.", "Capture reason, effective date, open obligations, asset/card return, communication changes and re-entry policy.", "Exit disables future assignment without deleting history."],
            ["11.6", "The person exercises privacy rights.", "Document correction, export, consent withdrawal, retention and lawful redaction/anonymization processes per Society policy.", "A tested data-subject request can be completed and audited."],
        ]),
        para("Stage 11 deliverable", style="Heading2"),
        para("A responsible full lifecycle that maintains capability and service history, supports renewal/transfer/exit and applies the National Society’s privacy and retention rules."),
        page_break(),
        para("16. Cross-cutting requirements for a reusable National Society product", style="Heading1"),
        table(
            ["Requirement", "Product standard"],
            [
                ["Configurability", "Society settings drive branding, terminology, geography levels, vocabularies, roles, workflows, currencies, phone rules, languages, forms, notification templates and feature availability."],
                ["Isolation and access", "Every list, API, dossier, file, export and aggregate uses current role plus geographic assignment and fails closed when configuration is missing."],
                ["Integration boundaries", "Each external capability has one adapter and one source of truth. Missing optional apps produce a supported unavailable state, not a broken page."],
                ["Auditability", "Applications, revisions, decisions, role assignments, status changes, exports, communications, deployments and configuration publications record actor, time and reason."],
                ["Data governance", "Each field has purpose, owner, sensitivity, visibility, correction route and retention rule. Collect the minimum necessary data."],
                ["Accessibility", "WCAG 2.2 AA target; keyboard operation, named controls, managed focus, status announcements, contrast, zoom and screen-reader tests."],
                ["Mobile and resilience", "Phone-first layouts, progressive save, bounded requests, loading/error/empty states, idempotent submissions and safe retries on unstable networks."],
                ["Localization", "Translated interface and content, right date/number formats, local names for geography and roles, and no country-specific strings in source."],
                ["Performance", "Server-side pagination/filtering, indexed operational queries, bounded exports, cached safe vocabularies and measured page/API targets."],
                ["Operations", "Installation must fail visibly or report unhealthy state; migrations are repeatable; demo data is explicitly separate; backups, monitoring and rollback are documented."],
                ["Testing", "Unit, contract, role/scope, integration, browser journey, accessibility, mobile/slow-network and upgrade tests run in CI with representative configurations."],
                ["Distribution", "Versioned releases, supported Frappe/app compatibility, configuration templates, import/export tools, deployment guide, administrator guide and upgrade notes."],
            ],
            [2100, 6850],
        ),
        para("17. Implementation work packages and deliverables", style="Heading1"),
        table(
            ["Work package", "Scope", "Required deliverable / exit gate"],
            [
                ["WP0 Product contract", "Personas, core data, Society settings, roles, source-of-truth decisions and journey states.", "Approved product/data/workflow specification and traceability matrix."],
                ["WP1 Account and identity", "Signup, native Google login, fallback, Red Profile matching, duplicate prevention and recovery.", "Tested entry journey with no duplicate identity paths."],
                ["WP2 Registration platform", "Volunteer/member core forms, draft/resume, dynamic questions, private uploads, consent, submission and status.", "Both applications complete successfully on phone and desktop."],
                ["WP3 Review and onboarding", "Scoped queues, dossiers, decisions, correction/resubmit, notifications, activation and checklists.", "Applicant and reviewer complete the full loop with audit history."],
                ["WP4 Record management", "Registers, dossiers, self-service fields, capabilities, transfers, status, duplicates and scoped exports.", "Managers can safely operate the live volunteer/member register."],
                ["WP5 Opportunities and events", "Volunteer Opportunity/Interest plus the explicit Buzz event participation contract.", "Users participate and managers see outcomes/participants."],
                ["WP6 Deployment", "Request, approval, planning, matching, invitations, readiness, live operations, tasks/hours and closeout.", "One deployment completes end to end and updates service history."],
                ["WP7 Communication", "Transactional templates, audience preview, campaigns, preferences and delivery history.", "Every core transition and operational audience can be reached safely."],
                ["WP8 Productization", "Localization, setup wizard, health checks, configuration packages, docs, CI, upgrades and pilot feedback.", "A second Society can install, configure and complete acceptance without code changes."],
            ],
            [1950, 4300, 2700],
        ),
        page_break(),
        para("18. First two-week execution plan — begin with the foundation", style="Heading1"),
        para(
            "The complete master journey is larger than a responsible ten-day build. The first two weeks should perfect the foundation—account entry, volunteer/member registration, review, correction and record creation—because every opportunity, event and deployment depends on those records being correct. Later work packages then follow the same master plan without redesigning the foundation."
        ),
        table(
            ["Day", "Focus", "Step-by-step work", "Daily deliverable"],
            [
                ["Day 1", "Journey and data contract", "Walk the existing volunteer/member paths; confirm core versus configurable data, personas, states, permissions, Society settings and acceptance tests.", "Approved journey map, core field catalogue, state model and task board."],
                ["Day 2", "Account and identity", "Configure/test standard signup, Google Social Login Key, redirect return, recovery, existing-email matching and one Red Profile rule.", "Both sign-in paths enter the correct registration without duplicates."],
                ["Day 3", "Volunteer core form", "Complete identity, geography, skills, languages, availability, motivation, documents and mobile step validation.", "Core volunteer registration works through Review before submission."],
                ["Day 4", "Member core form", "Complete shared-profile prefill, membership type, branch, terms/fee explanation and independent dual-affiliation path.", "Member registration works without repeating or overwriting identity."],
                ["Day 5", "Dynamic forms", "Audit the existing builder; complete safe question creation/order/group/activation, preview and server validation; specify versioning/conditions if not achievable in sprint.", "Administrator changes the live form without code and history remains accurate."],
                ["Day 6", "Draft, files and submission", "Implement or harden server draft/resume, upload ownership/privacy, review page, idempotent submit, reference and confirmation.", "Interrupted application resumes and submits once with readable private files."],
                ["Day 7", "Reviewer queue and dossier", "Complete routed/scoped list, filters, applicant summary, grouped answers, attachments, SLA and decision confirmation.", "Correct reviewer can fully assess the application; others cannot access it."],
                ["Day 8", "More-information loop", "Implement returned state, reason/field requests, deep-link notification, applicant edit, revised draft, resubmit and revision audit.", "Reviewer and applicant complete one request/correction/resubmission cycle."],
                ["Day 9", "Approval and records", "Make final approval idempotently create volunteer/member affiliation, correct role, onboarding state and searchable manager dossier.", "Approved applicant appears once in the appropriate register and portal."],
                ["Day 10", "End-to-end acceptance", "Test first-time, returning, dual-status, cross-branch denial, phone, keyboard, slow network and failure/retry journeys; fix blockers and demonstrate.", "Foundation release candidate, test report, user guide, known issues and next work-package plan."],
            ],
            [1050, 1800, 4300, 1800],
        ),
        para("Two-week foundation exit criteria", style="Heading2"),
        bullet("Volunteer and member users can sign up, save, resume, submit, track, correct and resubmit without staff workarounds."),
        bullet("A National Society administrator can configure local questions without a code deployment."),
        bullet("A reviewer can find, understand and decide only applications routed to their current scope."),
        bullet("Approval creates exactly one usable affiliation and one searchable management dossier."),
        bullet("Google and standard login work with recovery and duplicate prevention."),
        bullet("Mobile, accessibility, file privacy, notification and error/retry acceptance tests pass for the core journey."),
        para("19. Journey roadmap after the first two weeks", style="Heading1"),
        table(
            ["Next sequence", "Why it comes next", "Demonstrable outcome"],
            [
                ["1. Record management and onboarding", "The new records must stay current and operational.", "Managers and users maintain capabilities, availability, status and onboarding."],
                ["2. Volunteer opportunities", "Current, trusted profiles can now be matched to real needs.", "Opportunity → interest → decision works."],
                ["3. Events", "Participation should become a managed engagement record.", "Event → registration/booking → attendance works with one source of truth."],
                ["4. Deployment", "Approved and capable volunteers can be assigned safely.", "Request → plan → match → invite → operate → close works."],
                ["5. Communication and service history", "Every stage needs traceable engagement and long-term value.", "Targeted messages, delivery status and validated service history work."],
                ["6. Productization for another Society", "The workflow is proven and can now be packaged.", "A second-Society configuration and acceptance pilot succeeds without a fork."],
            ],
            [2300, 3450, 3200],
        ),
        page_break(),
        para("20. Final acceptance scenarios", style="Heading1"),
        table(
            ["Scenario", "Evidence of success"],
            [
                ["First-time volunteer", "Creates an account, resumes a draft, answers local questions, uploads a file, submits, corrects requested information, is approved and sees onboarding."],
                ["Prospective member", "Uses the same identity, selects a valid membership type, understands fees/status, is approved/activated and sees validity details."],
                ["Dual-status person", "Has one profile, separate affiliations, no duplicated data and navigation relevant to both."],
                ["Branch reviewer", "Sees only routed in-scope applications, opens all authorized evidence, requests a correction and decides the resubmission."],
                ["Volunteer manager", "Finds a volunteer by skill/availability, reviews standing and assigns a suitable opportunity or deployment."],
                ["Volunteer participant", "Expresses interest, receives an outcome, accepts a deployment, completes work and sees validated service history."],
                ["Event manager", "Publishes through the chosen source, sees capacity and participants, records attendance and avoids duplicate participation states."],
                ["Communication manager", "Previews actual scoped recipients, sends approved content and reviews channel delivery/failure status."],
                ["National administrator", "Configures forms, vocabulary, geography, workflows, roles, branding, locale and integrations without editing code."],
                ["Second National Society", "Installs a supported version, imports or configures its own setup, passes the same journey suite and receives upgrade documentation."],
            ],
            [2650, 6300],
        ),
        para("21. Handover deliverables", style="Heading1"),
        bullet("Approved journey, data, permission, state and integration specifications."),
        bullet("Versioned code and migrations with connected-app compatibility recorded."),
        bullet("Administrator setup guide, form-builder guide and National Society configuration template."),
        bullet("Applicant, volunteer/member, reviewer, coordinator and deployment-manager user guides."),
        bullet("Automated test suite plus role/scope, browser, mobile, accessibility, slow-network and upgrade evidence."),
        bullet("Deployment, configuration-health, backup and rollback runbooks."),
        bullet("Known limitations and prioritized later enhancements, separated from MVP blockers."),
        para("22. Supervisor approval", style="Heading1"),
        para(
            "I am requesting approval to use this end-to-end journey as the product work plan, beginning with the two-week registration, review and record foundation. Each later module will be accepted only when the user action, management response, system state, notification, permission and audit trail work together."
        ),
        para("Plan approved:  Yes / No / Approved with changes", bold=True, after=240),
        para("Supervisor comments: _______________________________________________________________", after=240),
        para("________________________________________________________________________________", after=240),
        para("Supervisor signature: __________________________    Date: __________________________", after=180),
        para("Prepared-by signature: _________________________    Date: __________________________", after=180),
        para("Source: VMMS Product, UX, Security and Integration Review, 25 August 2026, supplemented by inspection of the current VMMS and Frappe implementation.", size=17, color="6B747C", before=500),
    ]

    section = (
        '<w:sectPr><w:headerReference w:type="default" r:id="rId2"/>'
        '<w:footerReference w:type="default" r:id="rId3"/><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1134" w:right="900" w:bottom="1134" w:left="900" w:header="550" w:footer="550"/>'
        '</w:sectPr>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<w:body>{''.join(body)}{section}</w:body></w:document>"
    )


def main() -> None:
    created = "2026-08-26T00:00:00Z"
    core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>VMMS End-to-End Volunteer Journey Work Plan</dc:title><dc:subject>Registration, management, engagement and deployment product plan</dc:subject><dc:creator>VMMS Project Team</dc:creator><cp:lastModifiedBy>VMMS Project Team</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified></cp:coreProperties>'''
    app = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Microsoft Office Word</Application><Company>VMMS Project Team</Company></Properties>'''
    header = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr xmlns:w="{W}">{para("VMMS  |  END-TO-END VOLUNTEER JOURNEY WORK PLAN", bold=True, color="68737D", size=16, align="right", after=0)}</w:hdr>'''
    footer = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr xmlns:w="{W}"><w:p><w:pPr><w:jc w:val="center"/></w:pPr>{run("Supervisor Review  •  26 August 2026  •  Page ", color="68737D", size=16)}<w:r><w:rPr><w:color w:val="68737D"/><w:sz w:val="16"/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText> PAGE </w:instrText></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>'''
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", ROOT_RELS)
        archive.writestr("word/document.xml", document())
        archive.writestr("word/styles.xml", styles())
        archive.writestr("word/numbering.xml", NUMBERING)
        archive.writestr("word/header1.xml", header)
        archive.writestr("word/footer1.xml", footer)
        archive.writestr("word/_rels/document.xml.rels", DOC_RELS)
        archive.writestr("docProps/core.xml", core)
        archive.writestr("docProps/app.xml", app)
    print(OUTPUT)


if __name__ == "__main__":
    main()
