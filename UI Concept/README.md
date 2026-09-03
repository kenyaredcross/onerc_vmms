# VMMS web portal UI concept

This directory is the standalone HTML/CSS/JavaScript prototype. It intentionally does not import or modify the production `portal/` application.

## Entry points

- `index.html` — public guest site
- `sign-in.html` — authentication journey
- `portal-home.html` — volunteer/member self-service home
- `volunteer-registration.html` — eight-step volunteer application
- `membership-registration.html` — six-step membership application
- `manager.html#overview` — manager workspace; every manager process is available without Frappe Desk

Serve the directory locally and open the files through HTTP so hash navigation and shared assets behave consistently.

## End-to-end journeys represented

- Account creation, password setup/reset, email-link sign-in
- Shared Red Profile identity and contact data
- Volunteer application with repeatable identifications and emergency contacts; searchable multi-select skills, languages, availability and motivations; dynamic Society questions; versioned declarations; review, submission, correction and approval status
- Membership selection, Society questions, payment/proof, declarations, submission, correction, approval, activation, renewal and certificate access; My Memberships renders every branch-specific membership independently and supports concurrent active memberships across branches
- Self-service profile, availability, training, full-page tasks, task clarification conversations, hours, events, opportunities, notifications and deployments
- Deployment invitation response, current mission file, TOR, evidence, tasks and historical service record
- Manager application queues and dossiers, configured-stage decisions, volunteer/member registries, deployments and TORs, matching/invitations/assignments/transfers, task batches, stipend reports/payments/exceptions, events, communications, content, application questions, analytics and audit/configuration

## Source-of-truth mapping

The concept labels and groupings follow the current VMMS DocTypes: Red Profile and Red Profile Identification; VMMS Volunteer Application and Volunteer; VMMS Membership; VMMS Task and child records; VMMS Deployment, Terms of Reference, Assignment, Request and Transfer; stipend report/payment records; announcements, content blocks and application questions. Task clarification uses `VMMS Task.open_question` and the `VMMS Task Update` child table: volunteer `question` entries remain visible to the assignment author, manager `answer` entries clear the flag, and both sides retain author, posted time, note and optional proof in the same task conversation.

Approval stage labels are display values only. The future production UI must use server-returned permissions and transition identifiers, geographic scope and ownership checks rather than hard-coded role or stage-name comparisons.

## Known implementation boundaries

This prototype uses representative data and local interactions. Upload, approval, messaging, payment, report export and persistence actions are visual demonstrations until the approved concept is implemented against the APIs. Current backend gaps that must remain visible during production planning include departmental stipend-approver routing and any event/opportunity integrations still owned by other Frappe applications.
