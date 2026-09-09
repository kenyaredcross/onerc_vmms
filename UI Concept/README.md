# VMMS web portal UI concept

This directory is the standalone HTML/CSS/JavaScript prototype. It intentionally does not import or modify the production `portal/` application.

## Entry points

- `index.html` — public guest site
- `sign-in.html` — authentication journey
- `portal-home.html` — volunteer/member self-service home
- `volunteer-registration.html` — complete nine-section volunteer application with accessible transitions and record editors for every applicant-owned child table
- `membership-registration.html` — six-step membership application
- `manager.html#overview` — manager workspace; every manager process is available without Frappe Desk

Serve the directory locally and open the files through HTTP so hash navigation and shared assets behave consistently.

## End-to-end journeys represented

- Account creation, password setup/reset, email-link sign-in
- Shared Red Profile identity and contact data
- Volunteer application with conditional nationality, disability and guardian questions; repeatable identifications and emergency contacts; searchable multi-select skills, languages, availability and motivations; profession plus education, training, work, professional-licence, driving-licence and reference child records; dynamic Society questions; versioned declarations; review, submission, correction and approval status
- Membership selection, Society questions, payment/proof, declarations, submission, correction, approval, activation, renewal and certificate access; My Memberships renders every branch-specific membership independently and supports concurrent active memberships across branches
- Self-service profile, availability, training, full-page tasks, task clarification conversations, hours, events, opportunities, notifications and deployments
- Deployment invitation response, current mission file, TOR, evidence, tasks and historical service record
- Manager application queues and dossiers, configured-stage decisions, volunteer/member registries, deployments and TORs, matching/invitations/assignments/transfers, task batches, stipend reports/payments/exceptions, events, communications, content, application questions, analytics and audit/configuration

## Source-of-truth mapping

The concept labels and groupings follow the current VMMS DocTypes: Red Profile and Red Profile Identification; VMMS Volunteer Application and Volunteer; VMMS Membership; VMMS Task and child records; VMMS Deployment, Terms of Reference, Assignment, Request and Transfer; stipend report/payment records; announcements, content blocks and application questions. Task clarification uses `VMMS Task.open_question` and the `VMMS Task Update` child table: volunteer `question` entries remain visible to the assignment author, manager `answer` entries clear the flag, and both sides retain author, posted time, note and optional proof in the same task conversation.

Approval stage labels are display values only. The future production UI must use server-returned permissions and transition identifiers, geographic scope and ownership checks rather than hard-coded role or stage-name comparisons.

## Volunteer registration interaction model

The refreshed concept is a representative partial saved draft, so completed, unanswered and conditional states can be reviewed without retyping test data. It follows the applicant-editable contract in `vmmsx/api/registration.py` and the child DocTypes rather than reproducing a Frappe grid in a public journey.

- The nine logical sections retain a visible current/total step, persistent progress, browser-history navigation, focused page headings, autosave feedback and an error summary linked to invalid fields.
- Skills, languages, availability and motivations use compact multi-select choices. Disability types use the live form's scalable searchable multi-select pattern: a filtered, scrollable list with descriptions and removable selected tokens.
- Complex child tables—identification, emergency contacts, education, declared training, work experience, personnel licences, driving licences and professional references—use a summary-list/add-edit loop. Each saved row remains readable, editable and individually removable; removal offers Undo.
- Personnel Licence includes its complete applicant payload: licence type and name, institution, qualification, registration number, validity, non-expiry, description and attachment. Guardian reviewer fields (`is_verified`, `verified_by`, `verified_on`) remain excluded because applicants must not set them.
- Conditional fields appear only when their parent answer makes them relevant: non-citizen details, disability type/support, guardian consent, document-copy rules and expiry/end dates.
- Citizenship is deliberately unanswered by default and must be explicitly selected; choosing No reveals the country and local-status questions.

The interaction decisions were informed by the [W3C multi-page form guidance](https://www.w3.org/WAI/tutorials/forms/multi-page/), [GOV.UK form structure](https://www.gov.uk/service-manual/design/form-structure), [GOV.UK check-answers pattern](https://design-system.service.gov.uk/patterns/check-answers/), and [MOJ Add another component](https://design-patterns.service.justice.gov.uk/components/add-another/). Visual flow references were reviewed in Gummble across [Superhuman onboarding](https://gummble.com/apps/superhuman-web?tab=flows&flow=9f1a6b5e-3af2-42ee-abb0-273192bc6829), [Linear onboarding](https://gummble.com/apps/linear-web?tab=flows&flow=66be2ec3-c818-45f3-a058-9581e10a330b), [Deputy onboarding](https://gummble.com/screens/sc_4853157637014c43b2e038eb2514c935), and [Peerlist profile editing](https://gummble.com/screens/sc_b078a32badb349ab919aa27c65de21d8).

## Known implementation boundaries

This prototype uses representative data and local interactions. Upload, approval, messaging, payment, report export and persistence actions are visual demonstrations until the approved concept is implemented against the APIs. Current backend gaps that must remain visible during production planning include departmental stipend-approver routing and any event/opportunity integrations still owned by other Frappe applications.
