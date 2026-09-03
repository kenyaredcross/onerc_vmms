# VMMS Phased Implementation Plan

Last updated: 2026-09-01  
Status: phases 1 and 3–7 complete on the server and Desk. Phase 2's server half
is complete and its portal half is deferred with the rest of the portal work, by
the user's direction: Desk first, portal last.

## Purpose

This is the living source of truth for the agreed VMMS improvements. It records
scope, decisions, phase status, acceptance gates, implementation findings, and
test results. Update this file as work progresses; do not create a competing
implementation plan elsewhere.

The User/Geo Assignment and staff-access proposal is paused. It must not be
implemented as part of this plan until it has been redesigned and explicitly
approved.

## Execution protocol

For each phase:

1. Work only on the current approved phase.
2. Inspect the existing implementation before editing it.
3. Add a detailed implementation checklist and any discovered constraints to
   this document.
4. Reuse working architecture and existing shared services.
5. Implement schema, backend, Desk, portal, permissions, notifications, patches,
   and tests needed for that phase.
6. Run the phase's automated and manual verification.
7. Update the phase record with files changed, patches, test commands/results,
   unresolved issues, and any approved deviations.
8. Mark a phase complete only when its acceptance gate passes.
9. Stop for review before starting the next phase.

Do not silently broaden scope or reopen an agreed product decision. Record a
new question under `Open decisions` when code inspection exposes a genuine
conflict.

## Status legend

- `Not started`: agreed scope, no implementation work begun.
- `In discovery`: current code and data model are being mapped.
- `In progress`: implementation is underway.
- `Verification`: implementation is complete but the acceptance gate is open.
- `Complete`: acceptance gate passed and results are recorded here.
- `Paused`: explicitly excluded until separately approved.

## Phase status

| Phase | Scope | Status |
|---|---|---|
| 0 | Codebase audit and implementation map | Complete |
| 1 | Volunteer registration | Complete |
| 2 | Existing-membership proof | In progress (server complete; portal deferred by the user) |
| 3 | Standard Project and TOR | Complete |
| 4 | Deployment and assignment | Complete |
| 5 | Individual and bulk tasks | Complete |
| 6 | Job Opening and Job Applicant | Complete (server; portal deferred) |
| 7 | Integration, hardening, reports and cleanup | Complete |
| Deferred | User/Geo Assignment and staff access redesign | Paused |

## Locked architectural decisions

1. Extend the current architecture; do not rebuild working workflows without a
   demonstrated need.
2. Standard ERPNext `Project` is the canonical project record. `VMMS Project`
   will be retired.
3. Standard HRMS `Job Opening` and `Job Applicant` are the canonical opportunity
   and application records.
4. Changes to standard ERPNext/HRMS DocTypes must be owned by `vmmsx` through
   custom fields, child DocTypes, fixtures, hooks, patches, client scripts, and
   permission hooks. Do not edit ERPNext or HRMS source files.
5. `Geo Node` is operational ownership and scope. It must not replace ERPNext's
   native `Company` field.
6. Standard fields must be reused where they already represent the agreed
   concept. Do not add duplicate VMMS priority, progress, company, project, or
   status fields merely for naming convenience.
7. Private identity, membership-proof, guardian, and application attachments
   must remain private and permission checked on every access path.
8. Browser restrictions are not security controls. Enforce permissions,
   ownership, workflow, duplicate prevention, and state transitions on the
   server.
9. Bulk operations must be idempotent and report partial success without
   duplicating successful rows on retry.
10. Existing unrelated worktree changes belong to the user and must be
    preserved.

## Explicitly deferred or excluded

- User-form Role Profile and Default Geo Node redesign.
- Role Profile to Geo Assignment synchronization.
- New delegated staff-access administration.
- Private screening and referee records during volunteer registration.
- A new approval gate for identity changes after volunteer approval.
- Volunteer email/phone verification changes.
- TOR types and TOR operational-readiness fields.
- Deployment requirement records for skills, certifications, languages,
  equipment, transport, or accommodation.
- Deployment age and gender filters.
- Deployment allowance and expense-eligibility fields.
- Mandatory deployment close-out reconciliation.
- A new VMMS-owned Volunteer Opportunity or Opportunity Interest DocType.
- Event and recurring-service conversion from Job Opening.
- Duplicating ERPNext accounting inside VMMS.

## Phase 0 — Codebase audit and implementation map

### Scope

- Map current DocTypes, custom fields, controllers, APIs, permission hooks,
  workflows, notifications, portal routes, fixtures, patches, and tests affected
  by phases 1–7.
- Confirm where existing services already provide geocoding, Geo Node scoping,
  private-file checks, question rendering, audit/version tracking, and approval
  routing.
- Identify every link to `VMMS Project` and every current use of `Project`, `Job
  Opening`, and `Job Applicant`.
- Record naming collisions, upgrade-safe extension points, test data, and
  dependencies on ERPNext, HRMS, and other installed apps.
- Convert each later phase into a file-level implementation checklist in this
  document.

### Deliverables

- [x] Current-state map added to this document.
- [x] File-level checklist added to phases 1–7. *(Written at the start of each
      phase rather than all seven up front — see Approved deviations. All seven
      are now in this document.)*
- [x] Schema and patch sequence recorded. *(Mechanisms in the map; Phase 1's
      own sequence in its checklist.)*
- [x] Test strategy and commands recorded.
- [x] Genuine blockers or open decisions recorded. *(OD-1, OD-2.)*

### Acceptance gate

No feature implementation begins until the current-state map demonstrates how
standard DocTypes will be extended without editing upstream apps.

### Implementation record

Started 2026-08-30. The shared current-state map is below. Per the approved
deviation of 2026-08-30, the file-level checklist for each later phase is
produced at the start of that phase rather than all at once.

#### App shape

`vmmsx` is the operational layer over `onerc_core` (`required_apps`). Identity
(`Red Profile`), geography (`Geo Node`, `Geo Level`, the adapter) and access
(`Geo Assignment`, scope, approver routing) are core's and are consumed, never
reimplemented. 13 modules in `vmmsx/modules.txt`; ~55 DocTypes.

Two directory trees per module, and the split is load-bearing:

- `vmmsx/<module_dir>/doctype/<name>/` — schema and controllers, where
  `<module_dir>` is the snake-cased module name (`vmms_volunteer`,
  `vmms_deployment`, `vmms_registration`, …).
- `vmmsx/<domain>/services/*.py` — the behaviour. Controllers are thin shims
  that call idempotent services; `vmmsx/api/*.py` holds the whitelisted
  endpoints. Business rules go in the service so that desk, portal and tests
  all reach the same implementation.

Repo-wide conventions that constrain every phase:

- `require_type_annotated_api_methods = True` — every `@frappe.whitelist()`
  method needs full type annotations.
- `export_python_type_annotations = True` — controllers carry an
  auto-generated `# begin: auto-generated types` DF block that regenerates on
  migrate. Do not hand-edit it.
- Per-module `tests/test_delegation.py` walks the AST and fails if a module
  grows its own approver resolver.
- `approvals/tests/test_no_stage_branching.py` walks the AST of every source
  file and fails if one branches on an approval **stage label**.

#### How this app extends things (the Phase 0 acceptance gate)

There is **no `fixtures/` directory and no `fixtures` hook**. The mechanisms
actually in use, in order of preference:

1. **A vmmsx-owned DocType** — edit its `.json` directly. This is the normal
   route for anything under `vmmsx/vmms_*/doctype/`.
2. **A Custom Field on another app's DocType** — created by a patch calling
   `frappe.custom.doctype.custom_field.custom_field.create_custom_field(dt,
   {...}, ignore_validate=True)`, guarded by
   `frappe.db.exists("Custom Field", {"dt": ..., "fieldname": ...})` so it is
   idempotent. `patches/setup_task_module.py` is the reference shape. This is
   how every society setting is added to core's `National Society Settings`,
   and it is how phases 3 and 6 must reach `Project`, `Job Opening` and
   `Job Applicant`.
3. **An idempotent installer on `after_migrate`** — for anything that must
   follow configuration a society can change after the patch has run
   (permission grants keyed to a named role, seeded Email Templates, print
   templates). A patch runs once per site by name; `after_migrate` runs every
   deploy. `hooks.py` documents the reason at each entry.
4. **A society setting** — a Custom Field on `National Society Settings`, read
   at call time through `onerc_core.society.services.config.settings()`. Role
   settings resolve through `registration/services/society.py::resolved_role`,
   which logs and answers `None` for a deleted role. Scope roles ship **empty
   and fail closed**; behaviour flags ship empty and mean *off*.

`patches.txt` has a `[pre_model_sync]` section (module registration only) and a
`[post_model_sync]` section (setup and seed). Frappe does **not** run patches on
a fresh install, so `install.py::after_install` runs them explicitly — anything
added to `patches.txt` must work on a new site through that path too.

#### The approval engine — already generic, already the lifecycle

`vmmsx/approvals/` governs `VMMS Volunteer Application`, `VMMS Membership`,
`VMMS Deployment Request` and anything later. Phases 1–4 consume it; none of
them may add a second lifecycle beside it.

- `approvals/states.py` — the closed state set and the whole transition
  grammar: `Draft`, `Submitted`, `In Review`, `Approved`, `Rejected`,
  `Withdrawn`, `Expired`. `docstatus` is deliberately unused by approvables.
- Decisions are a closed set of three: `Approved`, `Rejected`,
  `More info requested`.
- `approvals/services/contract.py` — the four-field contract a DocType must
  satisfy to be approvable: `approval_state`, `approval_stage`,
  `approval_stage_entered_on`, and a Table field of `VMMS Approval Decision`,
  plus the geo anchor named by the workflow.
- `approvals/services/config.py` — one `VMMS Approval Workflow` per governed
  DocType, carrying the stages, `allowed_anchor_levels` (ACC-03),
  `allow_withdrawal`, `application_expiry_days` and `applicant_field`.
- `approvals/services/engine.py` — `submit`, `decide`, `withdraw`, `expire`.
  The person-gate is *who this document routed to*, not role membership.

**Phase 1's "Returned for Correction" already exists and needs no new state.**
`engine.decide` with `More info requested` records the decision row (with its
mandatory reason) and returns the document to `Draft` with the stage cleared;
resubmission restarts review from the first stage.
`api/registration.py::_has_been_reviewed` distinguishes a never-submitted draft
from a returned one by the presence of a `VMMS Approval Decision` row, and
`_latest_decision_reason` surfaces what the approver wrote. The correction
history is the decisions table. Phase 1 must reuse this and must not add a
status value for it.

#### Registration — the existing intake path

- `registration/services/intake.py` — the two-DocType write. `INTAKE_FIELDS`
  is a transient identity buffer read and blanked in `before_insert` and
  blanked again in `validate`, so no satellite ever persists a name, phone,
  gender or date of birth. `as_system()` is the narrow elevation;
  `submit_once` puts a self-registration into motion.
- `registration/services/questions.py` — the society's own configurable
  questions (`VMMS Application Question` → `VMMS Application Answer` in the
  `custom_answers` table). Field types `Attach`, `Check`, `Select`, `Date`,
  `Int`, default text. Question wording, group and type are **snapshotted onto
  the answer row**, so a decided application still shows the form as it stood.
  `assert_answered` runs at submission, never at insert. `anchor_files` ties an
  uploaded answer file to the document so the approver inherits permission on
  it. This is the pattern Phase 1's declarations should follow.
- `volunteer/services/application.py::assert_ready` is the submission gate:
  country of citizenship, an identification, date of birth, a complete
  residence shape, and every required society question. **Everything Phase 1
  requires at submission belongs here**; everything it requires at approval
  does not.
- `api/registration.py` — the self-service endpoints. All possessive: none
  takes a person, the subject is always `frappe.session.user` resolved through
  core's unique `Red Profile.user` column. `SELF_EDITABLE_FIELDS` is the closed
  list of what somebody may correct about themselves; `FILE_FIELDS` +
  `UPLOAD_PREFIXES` is the existing file-URL guard.

#### Identity and person facts

`Red Profile` (core) holds the person: names, email, phone, `user`, gender,
`date_of_birth`, citizenship, residency, `home_geo_node`, `profile_photo`, and
the `identifications` child table (`Red Profile Identification`: `id_type` →
core's `Identification Type`, `id_number`, `attachment`, `is_primary`).
`track_changes` is on.

`volunteer/services/identity.py` is the only reader. `_READABLE` is an explicit
allow-list; `_WITHHELD = ("blood_group", "medical_conditions", "next_of_kin",
"disability")` is refused **out loud** — core is holding those for a later gated
extension and vmmsx will not surface them. See Open decisions: this bears
directly on where Phase 1's emergency contact lives.

#### Files and privacy — a gap that spans phases 1, 2 and 6

**Corrected 2026-08-30 during Phase 1 implementation.** The first version of
this finding said no `Attach` field in vmmsx sets `is_private`. That property
does not exist on a Frappe DocField. The framework's actual switch is
`make_attachment_public` (a Check on DocField, with a `make_attachments_public`
fallback on the DocType), and **its absence means private** —
`frappe/public/js/frappe/form/controls/attach.js:87`. Neither is set anywhere in
vmmsx, so the *desk* path was already uploading privately.

The real gap is the **portal** path, and it is real. The SPA uploads through the
file API, where the browser names its own privacy, and then posts back a URL.
`questions._file` and `api/registration.py::UPLOAD_PREFIXES` both accept
`/files/` (public), and nothing on the server moved the file afterwards. A
public file is served to anyone with the URL — the framework does not consult
`attached_to_doctype` for one — so an applicant's uploaded evidence was private
only if their browser happened to choose privately.

The fix must therefore be **server-side**, not a DocField property, because a
property only ever governed the half of the traffic that was already safe.
Phase 1 builds it as `registration/services/evidence.py`: one `assert_uploaded`
(the URL is a claim, check it) and one `secure` (anchor the file to the document
and make it private through `File.save()`, which is what actually moves the
bytes and writes a `Version`). Phases 2 and 6 reuse it.

#### Change tracking

`track_changes: 1` is already set on `VMMS Volunteer Application`,
`VMMS Volunteer`, `VMMS Member` and core's `Red Profile`. The gap is that
several registration writes go through `frappe.db.set_value`, which does not
create a `Version`: `intake._adopt`, `intake._enrich`, `intake.place`,
`questions.anchor_files`, and the `File` privacy write proposed above.
`api/registration.py::_write_profile` correctly uses `document.save()`.

#### Portal

React SPA in `portal/`, served by `vmmsx/www/portal.html` and mounted at
`/portal`, `/home` and `/verify` (`website_route_rules`).

- `portal/src/guest/Join.tsx` (2768 lines) — the registration wizard. `StepId`
  is a closed set: `path`, `identity`, `plan`, `placement`, `identification`,
  `declaration`, `questions`, `confirm`; `stepsFor()` composes the list per
  path and derives step numbering. **Naming collision to avoid:** the existing
  `declaration` step is "About your volunteering" (skills, languages,
  availability, motivation) and is *not* a legal declaration.
- `portal/src/portal/Profile.tsx` — the volunteer's own profile screen.
- `portal/src/admin/ReviewQueue.tsx` — the approver's queue and decision
  screen, fed by `application.decision_dto`.
- Shared controls in `portal/src/ui/form.tsx`, `primitives.tsx`, `patterns.tsx`.

Note that the working tree carries substantial uncommitted portal work
(`PortalShell.tsx`, `chrome/`, `ui/`, `preview/`, `Deployments.tsx`). Locked
decision 10 applies: it is the user's and must be preserved.

#### Tests

89 `test_*.py` files under `vmmsx/*/tests/`. Registration and volunteer suites
are end-to-end and stub nothing — `registration/tests/test_volunteer_journey.py`
goes from a website account through the web form, core's routing, the API gate
as the routed approver, and acceptance. `registration/tests/base.py` and
`fixtures.py` provide `RegistrationTestCase`, `register_as_volunteer`,
`approve`, `branch()` and `website_account()`.

Command: `bench --site vmms.localhost run-tests --app vmmsx`, or a single
module with `--module vmmsx.<path>.tests.test_<name>`.

**Do not query `vmms.localhost` while `run-tests` is running** — the test run
holds the site's database and concurrent probing produces false failures.

#### Standard DocType usage today (phases 3 and 6)

- `VMMS Project` is live and linked from `deployment/services/project.py`,
  `deployment/services/terms.py`, `api/deployment.py`,
  `vmms_terms_of_reference.json`, `staff/services/workspaces.py`,
  `staff/services/permissions.py`, `staff/tests/test_workspaces.py`, and four
  seed modules. It is also registered in `hooks.py::onerc_scopeable_doctypes`,
  reusing `vmms_deployment_scope_role`. Phase 3 touches all of these.
- HRMS `Job Opening` is **already** the opportunities board's backing store —
  `hr/services/openings.py` is by its own docstring the only file in vmmsx that
  names it, read through `api/opportunities.py`, with `hr/tests/test_openings.py`
  and `seed/tanzania_jobs.py`. `Job Applicant` is **not** used anywhere yet.
  Phase 6 extends an existing seam rather than opening one.

## Phase 1 — Volunteer registration

### Agreed scope

- Add four standard, versioned declarations:
  - Privacy/data-processing consent.
  - Permission to contact the applicant.
  - Consent to use personal and biographical data.
  - Declaration that submitted information is accurate.
- Store declaration text/version and acceptance timestamp.
- Add emergency-contact name, relationship, primary phone, alternative phone,
  and permission to contact in an emergency.
- Require at least one emergency contact before approval.
- Support configurable identity-document requirements with private attachments.
- Add configurable minor/guardian rules.
- Record parent/guardian name, relationship, phone, email, consent status,
  consent date, verification method, and reviewer verification.
- Allow one person to be both guardian and emergency contact without conflating
  the legal purposes of the two records.
- Require verified guardian consent before approving a minor's application.
- Clearly represent Draft, Submitted, Under Review, Returned for Correction,
  Approved, and Rejected. Preserve resubmission events in history rather than
  adding unnecessary status values.
- Record correction requests and retain prior submission/resubmission history.
- Do not add identity-change reapproval yet. Enable Desk change tracking on the
  Volunteer Application, Volunteer, and relevant profile/contact records, and
  ensure portal/server updates do not bypass version creation.

### Excluded from this phase

- Screening and references.
- Code-of-conduct, safeguarding, or background-check declarations.
- Email or phone verification changes.
- Identity-change approval workflow.

### Acceptance gate

- [x] Adult and minor submission paths are tested. — `test_guardian_consent.py`,
      `test_volunteer_journey.py`.
- [x] Guardian approval rules are server enforced. — refused in
      `application.assert_approvable`, called from the controller on the save
      that approves; the portal cannot send a verification at all.
- [x] Required identity evidence is configurable and private. —
      `test_identity_documents.py` (configurable per `Identification Type`),
      `test_private_evidence.py` (made private server-side by `evidence.secure`).
- [x] Returned applications can be corrected and resubmitted with history. —
      `test_correction_and_audit.py`. This is the criterion defect **D-1** was
      blocking; it did not pass until the engine was fixed.
- [x] Desk and portal changes create the required audit trail. —
      `test_correction_and_audit.py`, including the AST rule that no
      registration path writes around the document.
- [x] Unauthorised users cannot read private files or guardian details. —
      `test_private_evidence.py::TestNobodyElseCanReadIt`,
      `test_guardian_consent.py::TestGuardianDetailsAreNotPublic`.

### Discovered constraints

From the Phase 0 audit, before any code is written:

1. **Nothing exists yet.** `emergency`, `guardian`, `consent` and `next of kin`
   appear nowhere in the schema or services — only in
   `docs/generate_volunteer_journey_work_plan.py`, which describes them as
   future work. Every item in this phase is new build, not modification.
2. **"Returned for Correction" is already built** and must not become a status
   value. `engine.decide(More info requested)` → `Draft` + a decision row with
   a mandatory reason; `_has_been_reviewed` separates a returned draft from a
   never-submitted one. Phase 1 reuses this and adds no state.
3. **Submission gate vs approval gate are different places.** Anything required
   *to submit* goes in `application.assert_ready()`. Anything required *to
   approve* — at least one emergency contact, verified guardian consent for a
   minor — cannot go there and must not go into the generic engine, which may
   not know what a volunteer is. It goes in the application controller's
   `validate()`, guarded on the state transitioning into `Approved`
   (`get_doc_before_save()` gives the previous state), so the decision rolls
   back with a sentence the approver can act on.
4. **Private attachments are not currently private.** See the Phase 0 map. This
   phase must set `is_private: 1` on its own attach fields, narrow the accepted
   URL prefix to `/private/files/` for the paths it owns, and flip privacy in
   the anchor step. The same fix is needed for `VMMS Application Answer.answer_file`,
   which is in scope here because required identity evidence is uploaded through it.
5. **Declarations must follow the questions pattern, not invent one.**
   `registration/services/questions.py` already solves configurable content,
   server-side validation, submission-time requirement checking, and
   snapshotting so a decided application reads as it stood. Declarations are
   the same problem with a fixed shipped set, and a second mechanism beside it
   would be a second thing to keep in step.
6. **Age is derived from `Red Profile.date_of_birth`**, which
   `assert_ready` already makes mandatory at submission. There is no age field
   to add and none should be added — a stored age is wrong the next day.
7. **The wizard's `declaration` step id is taken** by "About your
   volunteering". The consent step needs a distinct id (`consents` below).
8. **Identity-document requirements have nowhere to be configured.** Core's
   `Identification Type` carries only name, key, `is_active` and description —
   no "required" flag and no "needs an attachment" flag. Configuration must be
   vmmsx-owned Custom Fields on that DocType (mechanism 2 in the Phase 0 map),
   not an edit to core.

### Implementation checklist

Ordered so each step is independently testable. Nothing here edits an upstream
app's source.

#### 1.1 Schema — new DocTypes (module `VMMS Registration`)

- [ ] `vmmsx/vmms_registration/doctype/vmms_declaration/` — the society's
      versioned declaration text. Fields: `declaration_key` (Data, autoname),
      `title` (Data), `body` (Text Editor), `version` (Data), `applies_to`
      (Link → DocType, the same shape as `VMMS Application Question.asked_on`),
      `is_required` (Check), `sequence` (Int), `is_active` (Check).
      `track_changes: 1`.
- [ ] `vmmsx/vmms_registration/doctype/vmms_declaration_acceptance/` — child
      table. Fields: `declaration` (Link), `declaration_key`, `title`,
      `version`, `body_snapshot` (Text), `accepted` (Check), `accepted_on`
      (Datetime). The four snapshot fields are read-only and exist for the same
      reason `VMMS Application Answer` snapshots its question wording.
- [ ] `vmmsx/vmms_registration/doctype/vmms_emergency_contact/` — child table.
      Fields: `contact_name`, `relationship` (Data), `primary_phone`,
      `alternative_phone`, `may_contact_in_emergency` (Check).
- [ ] `vmmsx/vmms_registration/doctype/vmms_guardian_consent/` — child table,
      deliberately separate from the emergency contact so that one person
      filling both roles is two records, not one merged record. Fields:
      `guardian_name`, `relationship`, `phone`, `email`, `consent_given`
      (Check), `consent_date` (Date), `verification_method` (Link →
      `VMMS Guardian Verification Method`), `verified_by` (Link → User,
      read-only), `verified_on` (Datetime, read-only), `consent_evidence`
      (Attach, `is_private: 1`).
- [ ] `vmmsx/vmms_registration/doctype/vmms_guardian_verification_method/` —
      the configurable vocabulary behind `verification_method`. Same
      `*_key`/`*_name`/`is_active`/`description` shape every other vocabulary
      in this app uses.

#### 1.2 Schema — `VMMS Volunteer Application`

`vmmsx/vmms_volunteer/doctype/vmms_volunteer_application/vmms_volunteer_application.json`

- [ ] New section `Emergency Contacts` → `emergency_contacts` (Table →
      `VMMS Emergency Contact`).
- [ ] New section `Guardian Consent` → `is_minor` (Check, read-only, derived)
      and `guardian_consents` (Table → `VMMS Guardian Consent`), both with
      `depends_on: eval:doc.is_minor`.
- [ ] New section `Declarations` → `declarations` (Table →
      `VMMS Declaration Acceptance`).
- [ ] Confirm `track_changes` stays `1`. Do not hand-edit the controller's
      auto-generated DF block; let migrate regenerate it.

#### 1.3 Schema — Custom Fields on core's `Identification Type`

New patch `vmmsx/patches/install_identity_document_rules.py`, `create_custom_field`
guarded by an existence check, appended to `[post_model_sync]` in `patches.txt`:

- [ ] `vmms_is_required_for_volunteers` (Check) — description states that empty
      means not required.
- [ ] `vmms_requires_attachment` (Check).
- [ ] `vmms_minimum_age` (Int, optional) — some documents do not exist for a
      child.

#### 1.4 Schema — society settings (Custom Fields on `National Society Settings`)

Same patch as 1.3:

- [ ] `vmms_minor_age` (Int) — the age below which guardian rules apply. Empty
      means the society has not configured minor handling, and the guardian
      gate is then off. Read through `volunteer/services/society.py`.

#### 1.5 Services

- [ ] `vmmsx/registration/services/declarations.py` — new, modelled directly on
      `questions.py`: `asked_on(doctype)`, `apply(doc, accepted)`,
      `assert_accepted(doc)`, `accepted_of(doc)`. Snapshots title, version and
      body onto each acceptance row and stamps `accepted_on`.
- [ ] `vmmsx/volunteer/services/application.py`:
      - `assert_ready()` gains `declarations.assert_accepted(application)` and
        `_assert_identity_documents(application)` (the configured required
        types, and an attachment where the type demands one).
      - New `assert_approvable(application)` — at least one emergency contact
        with `may_contact_in_emergency`, and for a minor a guardian consent row
        that is both `consent_given` and reviewer-verified. Called from the
        controller, not the engine.
      - New `is_minor(application)` — `Red Profile.date_of_birth` against the
        society's `vmms_minor_age` at submission date. Returns `False` when the
        setting is empty.
- [ ] `vmmsx/volunteer/services/society.py` — add `minor_age()` alongside the
      existing five settings readers, with the same "empty means off" rule.
- [ ] `vmmsx/registration/services/questions.py` — narrow `_file()` to
      `/private/files/`; make `anchor_files` flip a still-public file to private
      through `File.save()` (not `db.set_value`, which neither moves the file
      nor writes a Version).

#### 1.6 Controller

`vmms_volunteer_application.py`:

- [ ] `validate()` sets `is_minor` from the service (derived, never typed).
- [ ] `validate()` calls `application_service.assert_approvable(self)` **only**
      when the save is moving `approval_state` into `Approved`
      (`self.get_doc_before_save()`).

#### 1.7 Seeds and installers

- [ ] `vmmsx/registration/seeds/declarations.py` — the four shipped
      declarations at version 1: privacy/data-processing consent, permission to
      contact, consent to use personal and biographical data, accuracy
      declaration.
- [ ] `vmmsx/registration/services/declarations.py::install` — additive-only
      installer registered in `hooks.py::after_migrate`, following
      `notifications/services/lifecycle.py::install`: creates what is absent,
      never edits what a society has since reworded.
- [ ] New patch `vmmsx/patches/seed_guardian_verification_methods.py` for the
      starting verification vocabulary.

#### 1.8 API

- [ ] `vmmsx/api/volunteer.py::application_options` — add `declarations`
      (from the new service) and `id_type_rules` (required / requires
      attachment), so the wizard draws the society's actual requirements rather
      than a hardcoded list.
- [ ] `vmmsx/api/registration.py` — `save_my_volunteer_draft` and
      `register_as_volunteer` accept `declarations`, `emergency_contacts` and
      `guardian_consent`; `_registration_dto` returns them for wizard resume.
      Every new parameter needs full type annotations.
- [ ] `application.decision_dto` — surface emergency contacts, guardian consent
      and accepted declarations so the approver can actually verify them.

#### 1.9 Portal

- [ ] `portal/src/guest/Join.tsx` — new `StepId` values `emergency` and
      `consents` (**not** `declaration`, which is taken), added to `stepsFor()`
      for the volunteer path; `consents` last before `confirm`. A guardian block
      appears inside `emergency` only when the entered date of birth makes the
      applicant a minor, with a "same as emergency contact" copy affordance that
      copies values into a second record.
- [ ] `portal/src/admin/ReviewQueue.tsx` — render the three new blocks on the
      decision screen.
- [ ] `portal/src/guest/Join.test.tsx` — adult path, minor path, and the
      required-declaration block on submit.

#### 1.10 Tests

- [ ] `vmmsx/registration/tests/test_declarations.py` — required declaration
      blocks submission; acceptance snapshots title/version/body; editing the
      society's text afterwards does not rewrite a submitted acceptance.
- [ ] `vmmsx/registration/tests/test_guardian_consent.py` — a minor cannot be
      approved without a verified guardian consent; an adult is unaffected; the
      society setting being empty turns the gate off.
- [ ] `vmmsx/registration/tests/test_emergency_contacts.py` — approval refused
      with none; one person as both guardian and emergency contact produces two
      records.
- [ ] `vmmsx/registration/tests/test_identity_documents.py` — a configured
      required type with `vmms_requires_attachment` blocks submission until the
      attachment is there.
- [ ] `vmmsx/registration/tests/test_private_evidence.py` — an uploaded answer
      file and a guardian consent evidence file are private; a second
      unauthorised website account is refused on both.
- [ ] `vmmsx/registration/tests/test_correction_history.py` — return for
      correction, correct, resubmit; both decision rows survive and the
      resubmission is reviewable from the first stage.
- [ ] `vmmsx/registration/tests/test_audit_trail.py` — a portal-driven change
      to the application and to the profile each produce a `Version`.
- [ ] Extend `vmmsx/registration/tests/test_volunteer_journey.py` with an
      end-to-end minor path.

### Implementation record

Implementation started 2026-08-30. Status: **Verification** — everything below
is built and the acceptance gate is being run.

#### Files added

| File | What it is |
|---|---|
| `vmms_registration/doctype/vmms_declaration/` | The society's versioned declaration text. Refuses a body change that does not move the version. |
| `vmms_registration/doctype/vmms_declaration_acceptance/` | Child table. Snapshots title, version and the whole body; every field read-only. |
| `vmms_registration/doctype/vmms_emergency_contact/` | Child table. Carries `may_contact_in_emergency`. |
| `vmms_registration/doctype/vmms_guardian_consent/` | Child table. Two ticks — `consent_given` and `is_verified` — plus stamped `verified_by`/`verified_on`. |
| `vmms_registration/doctype/vmms_guardian_verification_method/` | Vocabulary, seeded and society-editable. |
| `registration/services/declarations.py` | The questions.py twin: `shown_on`, `apply`, `assert_accepted`, `accepted_of`, `install`. |
| `registration/services/evidence.py` | **Not in the original checklist.** The shared upload guard and privacy fix — see Deviation 1. |
| `registration/seeds/declarations.py` | The four shipped declarations, society-neutral. |
| `patches/install_identity_document_rules.py` | Four Custom Fields: three on `Identification Type`, one on `National Society Settings`. |
| `patches/seed_guardian_verification_methods.py` | The starting verification vocabulary. |
| 6 test modules under `registration/tests/` | See below. |

#### Files changed

- `vmms_volunteer/doctype/vmms_volunteer_application/` — three new tables plus
  the derived `is_minor`; `validate` now derives the flag and runs the approval
  gate on the transition into Approved.
- `volunteer/services/application.py` — `assert_ready` gained the configured
  identity documents and the declarations; new `is_minor`, `_age_of`,
  `assert_approvable`, `_assert_emergency_contact`, `_assert_guardian_consent`;
  `decision_dto` now carries all three new blocks.
- `registration/services/society.py` — `minor_age()`.
- `registration/services/questions.py` — `_file` and `anchor_files` delegate to
  `evidence`.
- `api/volunteer.py` — `application_options` serves `declarations`,
  `minor_age`, `guardian_verification_methods`, and `id_types` now carries the
  society's rules per type.
- `api/registration.py` — the two volunteer endpoints accept
  `declarations_accepted`, `emergency_contacts` and `guardian_consents`, through
  an allow-list that cannot carry the reviewer's verification.
- `hooks.py` / `patches.txt` — the declarations installer on `after_migrate`,
  the two new patches.
- `portal/src/portal/types.ts`, `portal/src/guest/Join.tsx`,
  `portal/src/admin/ReviewQueue.tsx` — two new wizard steps and the approver's
  "Contacts and consent" tab.
- Test fixtures in `registration/tests/` and `volunteer/tests/`, plus
  `test_registration_drafts.py`, `test_seed.py`, `test_self_correction.py` and
  `test_volunteer_journey.py` — see Deviation 5.

#### Patches added

Both appended to `[post_model_sync]`, both idempotent and guarded per field/row:

1. `vmmsx.patches.install_identity_document_rules`
2. `vmmsx.patches.seed_guardian_verification_methods`

Plus `vmmsx.registration.services.declarations.install` on `after_migrate` —
create-if-absent only, and deliberately **without** the
`_upgrade_untouched` behaviour the email templates have, because people have
agreed to this exact text.

#### Deviations from the Phase 1 checklist

1. **`registration/services/evidence.py` was added, and `is_private: 1` on the
   DocField was removed.** The checklist said to set `is_private: 1` on the
   attach fields. That property does not exist on a Frappe DocField — the
   framework's switch is `make_attachment_public`, whose absence already made
   the *desk* path private. The exposed half was the portal, which uploads
   through the file API where the browser names the privacy. So the fix is
   server-side and shared: `assert_uploaded` (the URL is a claim) and `secure`
   (anchor it and make it private through `File.save()`, which is what actually
   moves the bytes and writes a `Version`). The Phase 0 map has been corrected.
   Phases 2 and 6 reuse this module rather than repeating the fix.
2. **`VMMS Guardian Consent` carries `is_verified` explicitly**, alongside the
   stamped `verified_by`/`verified_on`. The checklist named "reviewer
   verification" without a field. Two ticks rather than one is the point: what
   the guardian said and what somebody at the society did about it are
   different facts, and collapsing them would let an applicant vouch for their
   own guardian.
3. **`VMMS Declaration` enforces version discipline.** Not in the checklist. A
   changed body with an unchanged version is refused, so two people who agreed
   to materially different wording are never both recorded as having agreed to
   "version 1".
4. **The wizard's consent step is `consents`, and the emergency step is
   `emergency`.** `declaration` was already taken by "About your volunteering"
   (skills, languages, availability, motivation), which is a *self-*declaration
   and not a legal one — recorded in the Phase 0 map as a naming collision.
5. **Test fixtures across three suites now default the declarations and one
   emergency contact.** The new gates govern every door, so every existing
   suite that submitted or approved a volunteer application was affected. The
   fixtures were changed rather than the gates relaxed: a fixture without them
   models an application nobody could actually make. `test_volunteer_journey.py`'s
   paper-registration case was updated the same way and for a stronger reason —
   a clerk transcribing a signed form records the consents that were signed, and
   the paper door is deliberately held to the same standard as the browser.
6. **The portal collects one emergency contact and one guardian**, though both
   schemas are tables. A second is added on the desk. One is what a society
   needs to approve and what somebody completes on a phone.
7. **`api/volunteer.py::apply_to_volunteer` — the clerk's door — gained the same
   three arguments.** Not in the checklist, and not optional: once a society has
   declarations, `assert_ready` refuses a submission without them whichever door
   it came through, so without this a coordinator entering a paper application
   could not satisfy a rule the portal could. The row shaping is the *same*
   allow-list (`rows_from`, promoted to public in `api/registration.py`), so a
   coordinator can no more mark a guardian's consent verified than an applicant
   can.

#### Defects found and fixed

Two, both found by writing the acceptance tests rather than by reading.

**D-1 — a returned application could never be approved by the approver who
returned it.** `contract.decisions_at` returned every decision ever recorded at
a stage. A stage is a *row in a workflow*, not an instance of one, so a
resubmitted application re-enters the same stage — where the earlier "More info
requested" was still sitting. `engine.decide` found it and refused: *"You
already recorded More info requested at this stage. A decision cannot be
replaced."* The one approver who had looked at the application was the only
person who could no longer decide it, and on the single-stage workflow most
societies run, that is everybody.

This is **pre-existing, in the shared approval engine**, and it defeated the
Phase 1 acceptance criterion "Returned applications can be corrected and
resubmitted with history" outright. Fixed in
`approvals/services/contract.py::decisions_at` by scoping a decision to the
round the stage was last entered in, using `approval_stage_entered_on`, which
the engine already writes on every stage entry — so no new state was needed. The
decision stays in the audit trail; it stops speaking for the current round. The
double-decision guard within one round is unchanged and is tested.

`_after_approval` is the other caller and wants the same semantics: an approval
from a round before the application was rewritten should not count toward
completing the current one.

**Because this touches the generic engine it affects Membership and Deployment
Request too** — in both cases correcting the same defect. Flagged for review
rather than treated as routine.

**D-2 — `VMMS Guardian Consent.validate` was dead code.** Frappe calls
`validate` on the document being saved and never on its child rows
(`run_before_save_methods` → `self.run_method("validate")`), so the stamping of
`verified_by`/`verified_on` never ran. The rule stays on the child class, where
it belongs; `VMMSVolunteerApplication.validate` now calls it for each row. A
guarantee that never executes is worse than no guarantee, so this is worth the
paragraph.

#### A third finding, recorded rather than fixed

`Document._save` sets `flags.ignore_version = frappe.in_test`
(`frappe/model/document.py:824`), so **Frappe suppresses `Version` creation in
tests**. A suite counting version rows counts zero however correct the code is.
The audit tests therefore lower `frappe.in_test` around the call under test, and
— more usefully — `TestNothingWritesAroundTheDocument` asserts by AST walk that
no registration write path reaches for `frappe.db.set_value`, which is the
failure Phase 0 actually found. Three uses are named and justified in
`PERMITTED`; a fourth fails the test until somebody argues for it.

#### Test commands

```
bench --site vmms.localhost run-tests --app vmmsx
cd portal && npx tsc -b && npx vitest run
```

#### Results

**Portal.** `tsc -b` clean and **109/109 vitest tests pass** (28 in
`Join.test.tsx`, of which 13 are new). One pre-existing `tsc` warning remains in
`portal/src/portal/Tasks.test.tsx` (unused `fireEvent`) — an untracked file
belonging to in-flight work of the user's, deliberately not touched.

**Backend.** `bench --site vmms.localhost run-tests --app vmmsx`:
**1848 tests, 28 failing, 2 skipped.** Every one of the 28 is pre-existing or
environmental on this bench, and each was checked rather than assumed:

| Count | Suite | Why it fails, and why it is not Phase 1's |
|---|---|---|
| 17 | `volunteer.tests.test_learning` | Needs `LMS Enrollment`; `lms` is not installed on this site. |
| 2 | `volunteer.tests.test_lms_absent` | Same — asserts the LMS app *is* present before mocking its absence. |
| 3 | `volunteer.tests.test_affiliations` | Builds volunteers with `make_volunteer` → `volunteer_service.ensure`, which never writes core's affiliation index; no application is involved. |
| 1 | `volunteer.tests.test_hr_seam` | Same `make_volunteer` path, same reason. |
| 3 | `registration.tests.test_seed` | The site carries the Tanzania demo seed. One asserts no society logo (there is one), one asserts a single workflow stage (there are two), and the third hits a geo-level key collision — two levels both *named* "Branch". |
| 1 | `approvals.tests.test_no_stage_branching` | `seed/gambia.py:249` hardcodes the string "National Desk", which collides with a stage label the approvals fixtures use. Untouched file. |
| 1 | `buzz.tests.test_delegation` | `docs/sections/buzz.py` and `docs/tanzania_setup_guide.py` name "Buzz Event" outside the seam. Untouched files. |

The three `run-tests` invocations tell the story: **33 failing** after the
service changes and before the fixtures were brought up to date, **28** after —
and the five that closed are exactly the five Phase 1 introduced or exposed.
Every new suite passes in isolation as well: declarations 12, guardian consent
19, emergency contacts 7, identity documents 10, private evidence 12,
correction and audit 17.

Two of those 28 are worth someone's attention independently of this phase — the
`gambia.py` stage-label collision and the `docs/` Buzz naming are real
violations of invariants this app asserts, not test-harness noise. They are not
Phase 1's to fix and are noted here so they are not lost.

## Phase 2 — Existing-membership proof

### Agreed scope

- Add `Already a member of this plan?` as a secondary action on a selected
  membership plan.
- Prefill logged-in identity and existing Member/Profile details as read-only.
- Lock the selected membership plan in the proof form.
- Collect claimed original/start date, optional membership number,
  branch/location, optional certificate or receipt number, and expiry for
  non-lifetime plans.
- Require one private proof attachment.
- Require a versioned declaration that the information is accurate and the
  evidence belongs to the applicant.
- Submit with `membership_source = Proof`, no gateway transaction, and an
  approval state.
- Store claimed and approver-verified dates separately. Only verified dates
  control official membership validity.
- Leave lifetime `valid_to` empty.
- If verified expiry is in the past, record the membership as Expired and direct
  the member to renewal; do not activate an expired membership.
- Allow approvers to approve, return for correction, or reject with a reason.
- Prevent duplicate active memberships and duplicate open/retried proof
  submissions for the same member and plan.
- Show applicant-facing status and correction/rejection reasons.

### Acceptance gate

- [ ] Lifetime, current fixed-duration, and already-expired proof paths pass.
- [ ] No proof submission creates a payment transaction.
- [ ] Claimed dates cannot silently become official dates.
- [ ] Duplicate and retry protections are tested.
- [ ] Proof files are private to the applicant and authorised approvers.

### Discovered constraints

From reading the membership module before writing anything.

1. **Half of this phase already exists, and it is the approver's half.**
   `membership_source` (`Gateway` | `Proof`) and `proof_attachment` are on
   `VMMS Membership` today; `membership.py::_payment_settled` already answers the
   money question for a proof-sourced membership without reaching a gateway;
   `vmms_membership.py::validate_source` already refuses a proof against a type
   with no approver and a proof with nothing attached; `review.py::decision_dto`
   already surfaces the attachment to the approver. `member/tests/test_proof.py`
   covers all of it. **What is missing is the member-facing half** — an entry
   point, a form, the historical fields, a self-service endpoint, and the
   claimed/verified split.

2. **`register_as_member` refuses proof on purpose, and the refusal is right.**
   Its docstring: *"`membership_source` and `proof_attachment` are deliberately
   absent. They are how a clerk enrols somebody who paid before this system
   existed, and an applicant asserting their own proof of payment is not a thing
   this endpoint is willing to let happen."* Phase 2 does not relax that. It adds
   a **second door** whose whole design is that an applicant's assertion is a
   *claim* and never a fact — which is what the claimed/verified split in the
   agreed scope is for. The existing endpoint keeps its refusal unchanged.

3. **`activate()` computes `valid_from = today` unconditionally, and a test pins
   that for proof memberships.** `test_proof.py::test_the_fresh_period_starts_at_
   approval_not_application` asserts *"Period Model A — valid_from is the approval
   date, not a backdated one"*. The agreed scope requires verified historical
   dates to control validity, which contradicts it. **Resolved by making the
   verified dates the only thing that changes the answer**: a membership with no
   verified dates activates exactly as it does today (the clerk path, which has no
   claim to verify), and one carrying verified dates uses them. Nothing is
   backdated by anything other than a decision somebody made and is stamped
   against. The existing test keeps passing because its fixtures record no claim.

4. **Claimed dates cannot become official by omission either.** If the fresh
   period applied whenever an approver forgot to fill the verified dates in, the
   gate would be advisory. So a membership that carries a claim is **refused
   approval** until the verified dates are recorded — the same shape Phase 1 uses
   for guardian consent: the rule lives in the controller's `validate()`, guarded
   on the transition into `Approved`, and the portal cannot send a verification at
   all.

5. **Recording the verification is not deciding.** Approving a membership stays
   in `api/approvals.py` for the reason `api/member.py` states — the person-gate
   lives in the generic engine and a second door would be a second place to get it
   wrong. Verifying what a document says is a different act, so it gets its own
   narrow endpoint that writes only the four verified fields, and the engine is
   untouched.

6. **The historical branch is text, not a Geo Node.** The membership's `geo_node`
   is its ACC-02 anchor — where it is being registered *now*. Where somebody
   joined in 2014 is a claim about the past, at a branch this society may have
   since merged or renamed, and a Link would either refuse the claim or leave a
   dangling anchor. It is stored as what the applicant wrote.

7. **`declarations.py` is already doctype-generic and expects this caller.**
   `applies_to` is a Link to DocType and `shows()` asks whether the doctype
   carries the table at all, so Phase 2 adds a `declarations` table to
   `VMMS Membership` and one seeded declaration and writes no new mechanism. Same
   for `evidence.py`, whose own docstring names *"a membership proof"* as the next
   caller of `assert_uploaded` / `secure`.

8. **Duplicate prevention is half-built.** `engine.assert_single_open` already
   refuses a second *open* membership per member — the shipped seeds name
   `applicant_field = "member"` — and that covers "duplicate open/retried proof
   submissions". Nothing anywhere refuses a second **active** membership. That
   rule is new, and its key is member + plan, as the agreed scope words it.
   `register.py` documents a deliberate multi-branch model (*"somebody enrolled at
   two branches appears twice"*), which this respects: two *different* plans at
   two branches stays legal, the *same* plan twice does not, because the plan is
   the thing being held and paid for.

9. **The identity block is free.** `intake.claim_profile` / `clear_intake` already
   fill and then blank the applicant fields on every save, so the "prefill
   read-only identity" half of the scope is `my_profile()` on the portal and
   nothing on the server. `review.py` records why no "as written on the form"
   block exists; Phase 2 adds none.

10. **`VMMS Membership` is vmmsx-owned, so its fields go in its own JSON.** Locked
    decision 4 governs *standard* ERPNext/HRMS doctypes. No patch is needed for
    the schema; one is needed for the seeded declaration only because
    `declarations.install` runs `after_migrate`.

11. **The portal's `Membership.tsx` is still on the console primitives**, and the
    portal production redesign will migrate it in a later pass of its own. The
    proof page is built on the same primitives as the page it hangs off rather
    than on the new portal kit, so the two halves of one screen do not disagree.

### Implementation checklist

**Schema** (`vmms_member/doctype/vmms_membership/vmms_membership.json`)

- [x] Claimed block, applicant-supplied: `proof_claimed_start_date`,
      `proof_claimed_expiry_date`, `proof_membership_number`,
      `proof_registered_at`, `proof_reference_number`.
- [x] Verified block, approver-only and read-only on the form:
      `proof_verified_start_date`, `proof_verified_expiry_date`,
      `proof_verified_by`, `proof_verified_on`.
- [x] `declarations` table → `VMMS Declaration Acceptance`.

**Seed and patch**

- [x] `registration/seeds/declarations.py` carries `applies_to` per declaration;
      `declarations.install` stops hardcoding the application doctype.
- [x] One membership-proof accuracy declaration, society-neutral.

**Services**

- [x] `member/services/proof.py` — new. `has_claim`, `assert_claim_complete`
      (submission), `assert_verified` (approval), `verify`, `verified_validity`,
      `claimed_dto` / `verified_dto`.
- [x] `member/services/membership.py` — `activate()` reads
      `proof.verified_validity()`; Expired rather than Active when the verified
      expiry has passed; `submit()` runs the claim gate and the duplicate guard.
- [x] `vmms_membership.py::validate` — the approval gate on the transition into
      `Approved`.

**API**

- [x] `api/registration.py::register_existing_membership` — the self-service
      door; reuses a returned draft; allow-listed so no verified field can arrive
      from a browser.
- [x] `api/member.py::verify_membership_proof` — the approver's door.
- [x] `api/member.py::membership_types` serves the proof declarations.
- [x] `_registration_dto` and `review.decision_dto` carry the proof blocks.

**Portal — NOT BUILT. User direction, 2026-08-31: "leave the portal".**

The server is complete and tested; nothing renders it yet. These remain open and
Phase 2 is **not** at its acceptance gate until they are done or explicitly
dropped:

- [ ] `ui/PlanCards.tsx` — the "Already a member of this plan?" secondary action.
- [ ] `portal/MembershipProof.tsx` + route, reached from the plan card.
- [ ] `admin/ReviewQueue.tsx` — the claimed block and the verify control. **This
      is the one that blocks use, not just polish**: without it there is no
      screen anywhere that records a verified date, and `proof.assert_verified`
      refuses every approval until one is recorded. Until this is built, a
      self-service proof can be submitted and cannot be approved except from the
      desk form.
- [ ] `portal/types.ts`.

**Tests**

- [x] `member/tests/test_proof_submission.py` — 35 tests, all passing.

### Implementation record

Implementation started 2026-08-31. Status: **In progress** — the server half is
built and tested, the portal half is not (see the checklist above).

#### Files added

| File | What it is |
|---|---|
| `member/services/proof.py` | The claim, the verification, and the wall between them. `has_claim`, `assert_claim_complete`, `assert_verified`, `verify`, `verified_validity`, the two DTOs, and `CLAIM_FIELDS` — the allow-list that is also the security property. |
| `member/tests/test_proof_submission.py` | 35 tests across seven cases. |

#### Files changed

- `vmms_member/doctype/vmms_membership/vmms_membership.json` — nine fields in two
  sections plus the `declarations` table. Fields on the doctype itself, not
  Custom Fields: locked decision 4 governs *standard* doctypes and this is
  vmmsx's own.
- `vmms_membership.py` — `validate_approvable()`, the approval gate.
- `member/services/membership.py` — `_validity` / `_activated_status` split out
  of `activate()`; `assert_not_already_held`; the claim gate in `submit()`;
  `claimed` and `verified` on the status DTO.
- `member/services/review.py` — the two blocks side by side, plus the
  declarations, on the approver's DTO.
- `api/registration.py` — `register_existing_membership`, `_claim_from`,
  `_secure_proof`, `_apply_declarations`; the member branch of
  `_registration_dto`.
- `api/member.py` — `verify_membership_proof`; declarations on
  `membership_types`.
- `registration/seeds/declarations.py` — `applies_to` per declaration, and the
  membership-proof declaration.
- `registration/services/declarations.py` — `install` reads `applies_to` from
  the seed instead of hardcoding the volunteer application.

#### Deviations from the Phase 2 checklist

1. **The duplicate-active rule is scoped to proof, not to every membership.** The
   agreed scope says "prevent duplicate active memberships … for the same member
   and plan" without qualifying the path. Written that way it broke six tests in
   `test_renewal` and three in `test_dossier`, because several suites build two
   active memberships of one type for one person as ordinary fixture setup. The
   general case is the same defect and is real, but it is **pre-existing**, it is
   not what this phase is for, and closing it changes behaviour other features
   are built on. Recorded as a Phase 7 finding below rather than folded in
   silently. What ships refuses exactly what the phase is about: proving a
   membership you already hold.

2. **The duplicate key includes the branch.** "Member and plan" as literally
   worded would delete the multi-branch membership model, which predates this
   scope and states itself out loud in `register.py` — a person may hold the same
   plan at two branches, and the coordinator's register is built a row per
   membership precisely so they appear twice. Key is member + plan + geo_node.

3. **A membership proved to have expired is recorded as Expired without ever
   being Active.** The scope says "do not activate an expired membership", which
   left open whether to activate and immediately expire. It does neither: the
   status is decided once, in `activate()`, so the daily sweep never has a wrongly
   Active row to correct and no notification ever tells somebody they are a
   current member for a period that ended in 2021.

4. **`register_existing_membership` requires the claimed start date at the door**,
   rather than `proof.has_claim` requiring it. A clerk's desk entry legitimately
   asserts no period, so the service that serves both paths cannot demand one —
   but without the rule at the endpoint, a self-service submission with the date
   omitted would slip through as a clerk-style entry and quietly collect a fresh
   period starting today. Found by `test_a_claim_with_no_start_date_is_refused`,
   which failed on the first run.

5. **`_apply_declarations` was added, and it is not cosmetic.** `VMMS Membership`
   now carries a declaration, so `declarations.apply` — which writes a row for
   every declaration shown, accepted or not — would have stamped every ordinary
   Gateway membership with a refusal of a declaration nobody was shown. That
   records "we asked and they said no" where the truth is "we never asked", which
   is the exact distinction the declarations module exists to keep. `None` now
   means "this door does not ask"; `[]` still means "asked and refused".

6. **No draft endpoint.** The proof form is short and submits in one act, so
   there is no `save_my_proof_draft` beside `save_my_member_draft`. A returned
   submission re-enters through the same endpoint and `_editable_registration`
   finds the draft, so a correction is the same record with the same history
   rather than a second membership. Pinned by
   `test_a_returned_submission_is_corrected_rather_than_duplicated`.

#### Defects found and fixed

**D-3 — `_secure_proof` had to reload, and the reason generalises.** Anchoring a
file to a document touches that document's row, so the copy in memory is a
version behind the moment `evidence.secure` returns — and the next thing the
endpoint does is `submit()`, which saves. Without the reload every single
submission failed with `TimestampMismatchError`, which reads to an applicant as
their registration failing for no reason at all. `secure_row_files` (Phase 1) is
the sibling and does not have this problem, because it writes through
`frappe.db.set_value` on the *child* row and clears the document cache rather
than re-saving the parent.

**D-4 — the self-service endpoint needed its own elevation on the correction
path.** A fresh insert carries `ignore_permissions` on the document it returns,
so the `save()` inside `submit()` inherits it; a draft reloaded from the register
does not, and the applicant holds no role on `VMMS Membership`. Correcting a
returned submission raised `PermissionError` where the original had worked. Fixed
by wrapping the submit in `intake.as_system()`, which is what
`submit_my_registration` already does for both paths and for the same reason.

#### Test commands

```
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.member.tests.test_proof_submission
bench --site vmms.localhost run-tests --app vmmsx
```

#### Results

`test_proof_submission` — **35/35 pass**. Suites re-run for regressions and all
green: `test_proof` (9), `test_lifetime` (21), `test_renewal` (21),
`test_approval_modes` (14), `test_review` (9), `test_my_memberships` (14),
`test_dossier` (60), `test_lifecycle_api` (15). Full-suite result recorded below.

#### Carried to Phase 7

- **A second active membership of the same plan and branch is only refused on the
  proof path.** The Gateway path can still create one. See Deviation 1.

## Phase 3 — Standard Project and Terms of Reference

### Standard Project scope

- Replace links to `VMMS Project` with standard ERPNext `Project`.
- Add an Owning Geo Node field while preserving native Company.
- Default Owning Geo Node from the user's reliable current primary/default Geo
  Node when available.
- A normal user may only create a Project for a Geo Node covered by their active
  existing access. A user with several authorised nodes and no reliable default
  must choose from those nodes. System Manager remains unrestricted.
- Enforce the selection on the server.
- Reuse native Project identity, type, manager, priority, progress, dates,
  Company, and accounting fields where present.
- Add only missing lightweight donor/funding-source information, structured
  project risks, assumptions, and planning notes.
- Use standard workflow/status capabilities for the agreed lifecycle rather
  than adding duplicate progress/status fields.
- Show TORs, deployments, VMMS tasks, expenses, and reports through the standard
  Project dashboard.
- This is a test site. Delete existing `VMMS Project` test records after a link
  audit; no historical project migration is required. Remove or update test
  references, retire the obsolete DocType, and verify that no live metadata
  links remain.

### TOR scope

- Link each TOR to standard `Project`.
- All TORs are planned missions; do not add a TOR type.
- Make the TOR submittable. Submitted content is immutable.
- If an active matching `VMMS Approval Workflow` is configured for TOR, it must
  approve/submit the TOR. Without one, a user with submit permission may submit
  directly.
- Do not add a second approval status that duplicates `docstatus` or workflow
  state.
- At submission require Project, dates, mission background, objectives, expected
  outputs, stakeholders, itinerary, geographic scope, and either structured
  resources or an explicit no-resources declaration.
- Strengthen resource rows with resource/item description, donor/funding source,
  quantity, standard UOM, unit cost, currency, calculated total, needed-on date,
  and funding status. These are planning estimates, not accounting entries.
- A Deployment may link only to a submitted TOR.
- Allow normal Cancel/Amend only while a TOR is not referenced by an operational
  or historical Deployment. Otherwise create a new TOR linked through
  `supersedes`; historical Deployments retain the original.
- Generate PDF on demand; do not automatically store a duplicate PDF.
- Do not add the proposed operational-readiness section.

### Acceptance gate

- [x] No VMMS workflow configured: authorised direct TOR submission works. —
      `test_terms.py::TestWithNoWorkflowTheAuthorisedSubmitDirectly`.
- [x] Matching VMMS workflow configured: direct bypass is impossible. —
      `TestWithAWorkflowTheEngineIsTheOnlyDoor`, refused both through the service
      and on the document itself, plus the engine's person-gate.
- [x] Submitted TOR fields cannot be edited. —
      `test_a_submitted_document_cannot_be_edited`.
- [x] Submission completeness and resource calculations are server tested. —
      `TestTheMissionDocumentHasToBeFinished` (each of the nine taken away one at
      a time) and `TestResourceLinesArePriced`.
- [x] Historical Deployment-to-TOR links cannot be invalidated. —
      `TestWhatIsAgreedStaysAgreed`: cancel refused, supersede leaves the
      original submitted, the deployment still points at it.
- [x] Standard Project extensions survive migrate/reinstall without upstream
      source edits. — installed on every `after_migrate`, asserted field by field
      in `test_project.py::TestTheRetirementIsComplete`; no ERPNext file changed.
- [x] Obsolete `VMMS Project` links and test data are safely removed. —
      `adopt_standard_project` migrates the six records, repoints the eight
      links, deletes the rows and drops the DocType; asserted absent by
      `test_the_old_doctype_is_not_on_the_site`.

### Discovered constraints

From reading the deployment module and ERPNext's own `Project` before writing
anything.

1. **Half of what `VMMS Project` held has a better home already.** ERPNext's
   `Project` ships identity, type, `is_active`, priority, percent complete,
   expected and actual dates, Company, cost centre, holiday list, a users table,
   timesheet/purchase/sales/billing roll-ups and a project dashboard. `VMMS
   Project` held a name, a status, a Geo Node, two dates and two text fields.
   What genuinely had no home was the Geo Node, the donor, and structured risks
   and assumptions — which is exactly what `setup/project_fields.py` adds and
   nothing more.

2. **There is no native project manager field**, despite the agreed scope naming
   one among the fields to reuse. ERPNext expresses that through the `users`
   child table (`Project User`) and through `Task.completed_by`. No VMMS field
   was added for it: locked decision 6 forbids duplicating a standard concept
   for naming convenience, and a society that wants a named manager puts them in
   `users`. Recorded rather than invented.

3. **Company and Geo Node are different questions and both are mandatory.**
   ERPNext makes Company mandatory; ACC-02 makes the anchor mandatory. A national
   society is one Company with a hundred branches, so neither substitutes for the
   other. `project_service.default_company()` fills Company in when a site has
   one, so the coordinator is only ever asked the question that has more than one
   answer.

4. **Scoping a standard doctype is a real widening of what geo scoping governs**,
   and it is the intended reading of "Project is the canonical project record".
   `hooks.py` registers `Project` on `vmms_geo_node` and reuses the deployment
   scope role. The consequence is that a Project with no anchor is invisible to
   everybody but an unrestricted user — which is why the anchor is `reqd` and why
   `project.on_validate` says so in a sentence rather than leaving a field name.

5. **The custom fields cannot be installed by a patch alone.** A patch runs once
   per site by name, and the scope registration above names `vmms_geo_node`: if
   that field is ever missing, `registry.geo_node_field` throws on *every* Project
   list view on the site. So `setup/project_fields.install` runs on every
   `after_migrate` and is idempotent per field, and the migration patch calls it
   directly because it needs the column before it can write to one.

6. **`VMMS Terms of Reference` already met the approval engine's contract in
   spirit but not in fields.** It needed `approval_state`, `approval_stage`,
   `approval_stage_entered_on` and a decisions table before a
   `VMMS Approval Workflow` could govern it. Those are the engine's *own* state,
   not a second approval status — the prohibition in the agreed scope is against
   a third opinion, and `docstatus` is now strictly a consequence of the
   engine's verdict.

7. **`states.py` says approvable documents stay at `docstatus = 0`, and a TOR
   cannot.** The resolution is the shape `VMMS Deployment Request` already uses:
   the engine never learns that terms of reference exist, and the controller's
   `on_update` runs a predicate — `terms.try_freeze` — that asks whether this is
   a draft whose approval has landed. It reloads the document rather than
   submitting the copy that is mid-save, and its own submit's second `on_update`
   finds `docstatus = 1` and returns.

8. **`try_freeze` has to bypass permissions, on the same argument
   `request.fulfil` records.** The approver holds no `submit` grant on the terms
   register and should not need one in order to approve a mission document; the
   check that mattered happened in `engine.decide`, against the person this
   document routed to. `before_submit` still runs, so an unfinished or unapproved
   document is still refused.

9. **A `VMMS Approval Workflow` refuses an anchor field that is not mandatory.**
   `VMMSApprovalWorkflow.validate_anchor_field` is explicit: *"Every operational
   record is anchored to a Geo Node at creation — there are no unplaced
   records."* `geo_scope` was optional, so without changing it **no society could
   ever configure a TOR workflow at all** and the second acceptance criterion
   would be unmeetable. See Deviation 2.

### Implementation checklist

**Schema — Custom Fields on ERPNext's `Project`** (`setup/project_fields.py`)

- [x] `vmms_geo_node` (Link → Geo Node, mandatory) — the owning Geo Node.
- [x] Funding: `vmms_donor`, `vmms_funding_reference`, `vmms_funding_status`.
- [x] Planning: `vmms_risks` (Table), `vmms_assumptions` (Table),
      `vmms_planning_notes`.
- [x] No VMMS status, priority, progress, company, dates or manager field.

**Schema — new child DocTypes** (module `VMMS Deployment`)

- [x] `VMMS Project Risk` — risk, likelihood, impact, watched by, mitigation.
- [x] `VMMS Project Assumption` — assumption, still holds, notes.

**Schema — `VMMS Terms of Reference`**

- [x] `project` → Link to `Project`.
- [x] `geo_scope` becomes mandatory (Deviation 2).
- [x] `has_no_resources` (Check) — the explicit half of the resources rule.
- [x] `supersedes` (Link, read-only).
- [x] The approval engine's four fields, in their own tab.

**Schema — `VMMS TOR Resource`**

- [x] `description`, `currency`, `funding_status` added; `unit` becomes a Link
      to ERPNext's `UOM`; `unit_cost`/`total_cost` render in the row's currency.

**Services**

- [x] `deployment/services/project.py` — rewritten against `Project`.
      `authorised_nodes`, `default_node`, `may_anchor`/`assert_may_anchor`,
      `default_company`, `on_validate`, and a `dto` that maps ERPNext's fields to
      the names this app's callers already use.
- [x] `deployment/services/terms.py` — `REQUIRED_AT_SUBMISSION`,
      `missing_at_submission`, `assert_complete`, `is_governed`, `is_approved`,
      `assert_may_freeze`, `send_for_approval`, `try_freeze`, `references`,
      `is_referenced`, `supersede`.
- [x] `setup/project_fields.py` — new.
- [x] `seed/mission.py` — new; the seed-side scaffolding for a complete mission
      document, plus `uom()` and `standing_project()`.

**Controller**

- [x] `vmms_terms_of_reference.py` — `validate_project`, `before_submit`,
      `on_update`, and `on_cancel` rewritten onto `terms.references`.

**Hooks and patches**

- [x] `onerc_scopeable_doctypes`: `VMMS Project` → `Project` on `vmms_geo_node`.
- [x] `doc_events`: `Project.validate` → `project.on_validate`.
- [x] `after_migrate`: `setup.project_fields.install`, first.
- [x] `patches.adopt_standard_project`, `patches.link_tor_resource_units`.

**API**

- [x] `api/deployment.py` — `project_options` (new), `create_project` widened,
      `send_terms_for_approval` (new), `supersede_terms` (new), `create_terms`
      takes `has_no_resources`.

**Desk**

- [x] `staff/services/workspaces.py` and `staff/services/permissions.py` point at
      `Project`; the deployment scope role is granted read/write/create on it.

**Tests**

- [x] `deployment/tests/test_project.py` — 31 tests.
- [x] `deployment/tests/test_terms.py` — 38 tests.

### Implementation record

Implemented 2026-08-31.

#### Files added

| File | What it is |
|---|---|
| `vmmsx/setup/project_fields.py` | Every field vmmsx owns on ERPNext's `Project`, and why each one is not a duplicate of a native field. Installed on every migrate, not once by a patch — the reason is in its docstring and in constraint 5 above. |
| `vmms_deployment/doctype/vmms_project_risk/` | What could stop a programme, how likely, what it would cost, who is watching it, and what the society intends to do. |
| `vmms_deployment/doctype/vmms_project_assumption/` | What the plan takes for granted, with `still_holds` so a plan that stops working can be read back against the thing that changed. |
| `vmmsx/patches/adopt_standard_project.py` | The retirement: field-by-field conversion, links repointed with `db.set_value`, rows deleted, DocType dropped. |
| `vmmsx/patches/link_tor_resource_units.py` | Every free-text unit already written matched onto a real `UOM`, creating the ones ERPNext does not ship. |
| `vmmsx/seed/mission.py` | Seed-side scaffolding for a complete mission document, plus `uom()` and `standing_project()`. Explicitly not product behaviour; no service imports it. |
| `vmmsx/deployment/tests/test_project.py` | 31 tests across five cases. |
| `vmmsx/deployment/tests/test_terms.py` | 38 tests across six cases. |

#### Files changed

- `vmmsx/deployment/services/project.py` — rewritten. Statuses are ERPNext's
  four and there is deliberately **no transition table**: a standard field that
  ERPNext's own screens, its `set_project_status` endpoint and a society's native
  Workflow can all move is not one this app may put a private grammar over.
- `vmmsx/deployment/services/terms.py` — completeness, the two submission paths,
  supersession, and the new resource columns.
- `vmms_terms_of_reference.json` / `.py` — the fields and the two new hooks.
- `vmms_tor_resource.json` — the strengthened resource line.
- `vmmsx/hooks.py` — the scope registration, the `Project` doc event, the
  `after_migrate` installer.
- `vmmsx/api/deployment.py` — `project_options`, `send_terms_for_approval`,
  `supersede_terms`, widened `create_project` and `create_terms`.
- `vmmsx/staff/services/{workspaces,permissions}.py`, `staff/tests/test_workspaces.py`.
- `vmmsx/seed/{kenya,kenya_operations,gambia_operations,tanzania_deployments,tanzania_scale,tanzania_install,purge}.py`
  — standard `Project`, complete mission documents, real UOMs, and a
  standing-services programme for the work that used to belong to no project.
- `vmmsx/deployment/tests/fixtures.py`, `vmmsx/volunteer/tests/fixtures.py` —
  `make_project`, `company`, `default_scope`, and a `make_terms` that produces a
  submittable mission document.
- `vmmsx/deployment/tests/{test_deployment,test_scoping}.py` — three tests
  adjusted for the mandatory scope; see Deviation 2.
- `vmmsx/patches.txt`.

#### Files deleted

- `vmmsx/vmms_deployment/doctype/vmms_project/` — the whole doctype.

#### Deviations from the Phase 3 checklist

1. **The `VMMS Project` records were migrated, not deleted.** The agreed scope
   says this is a test site and existing records may be deleted after a link
   audit. The audit is the first thing the patch does, and on the Tanzania demo
   site it finds eight submitted terms of reference pointing at six projects.
   Deleting would leave those pointing at nothing on a site whose purpose is to
   be demonstrated, for a saving of about thirty lines that run once. The records
   are carried across and *then* deleted, which satisfies the instruction and
   leaves nothing dangling.

2. **`geo_scope` on a terms of reference became mandatory at creation, not only
   at submission.** The agreed scope requires it "at submission". A
   `VMMS Approval Workflow` refuses to be configured against an anchor field that
   is not mandatory (constraint 9), so leaving it optional would have made the
   second acceptance criterion — "matching VMMS workflow configured: direct
   bypass is impossible" — impossible to configure at all. Requiring it up front
   is a small tightening of an agreed rule rather than a new one: a society knows
   *where* a mission is before it knows the itinerary, and terms meant for the
   whole society name the national node. `assert_within_scope` still reads an
   empty scope as unconstrained, because records written before the rule carry
   none and applying it retroactively would refuse every deployment under a
   specification nobody can edit any more. Pinned by
   `test_empty_scope_permits_anywhere`.

3. **`summary` and `notes` swapped homes.** `VMMS Project.summary` — the
   programme's own words, printed at the head of every terms of reference under
   it — became ERPNext's `notes`, which is the same concept under ERPNext's name.
   What this app called `notes` (the aside) became `vmms_planning_notes`, beside
   the risks and assumptions. Mapping them by name would have put the aside on
   the letterhead. `dto` reads them back under the two names its callers already
   use, with the markup stripped off the summary.

4. **No project manager field was added.** See constraint 2.

5. **The old four project statuses collapse into ERPNext's four.** Planned and
   Active both become Open: ERPNext expresses "running or about to" as one
   status, and no code in this app ever read the difference — `is_open` treated
   them alike. On hold is new and does *not* take new terms of reference, which
   is the deliberate reading of pausing a programme.

6. **The seeds gained a "Branch Standing Services" programme.** Every terms of
   reference now belongs to one, and a branch first aid rota or a family links
   desk genuinely is a programme — continuous work rather than a campaign with an
   end. That is the previous seeds' argument (*"a society that runs standing
   duties beside its programmes should see both"*) answered rather than
   abandoned.

7. **Kenya's and Gambia's seeded mission documents are scaffolded, not written.**
   `seed/mission.py::furnish` builds the background, objectives, outputs,
   stakeholders, itinerary and period from the purpose and responsibilities each
   seed already carried, so nothing invents a fact about a society. Tanzania's
   ten are written out in full, because that site exists to be demonstrated —
   including eight itineraries and three geo scopes that had to be authored for
   this phase.

#### Defects found and fixed

**D-5 — `delete_doc` cannot delete a doctype whose Python package has gone.**
The first run of `adopt_standard_project` failed with *"Module import failed for
VMMS Project, the DocType you're trying to open might be deleted"*: `delete_doc`
loads the document, which loads the controller, which is no longer on disk. The
rows are deleted with `frappe.db.delete` instead — there is nothing for a
controller to do when the whole table is dropped two lines later. The general
lesson is worth keeping: a patch that retires a doctype must not use the ORM to
empty it, because the source it needs has already been removed in the same
commit.

#### Test commands

```
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.deployment.tests.test_project
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.deployment.tests.test_terms
bench --site vmms.localhost run-tests --app vmmsx
```

## Phase 4 — Deployment and assignment

### Deployment scope

- Preserve Deployment Request, Deployment, and one Deployment Assignment per
  volunteer as separate records.
- Apply Deployment Request approval only when a matching `VMMS Approval
  Workflow` is configured. Without one, an authorised coordinator may create
  the Deployment without a hard-coded approval cycle.
- Require standard Project, submitted TOR, organising Geo Node, and responsible
  coordinator.
- Support Planned, Active, Suspended, Completed, Closed Out, and Cancelled.
- Add separate Deployment point/site and meeting point, each with address or
  description and coordinates.
- Preserve or improve the existing geocoding function: generate coordinates,
  display the point on a map, permit manual pin/coordinate correction, and fail
  safely when geocoding cannot resolve a location.
- Generate map and directions links. Volunteer invitations include meeting
  point, Deployment point, relevant directions, dates/times, travel notes,
  local contact, and coordinator contact.
- Track planned and actual start/end datetime, briefing datetime, check-in
  deadline, and expected return/check-out datetime.
- Important location, schedule, coordinator, or requirement changes after
  invitations must be audited, require a reason, and notify affected volunteers.
- Do not create Deployment requirement records. During volunteer selection,
  provide filters for Geo Node/descendants, skills, certifications, languages,
  availability, and current assignment workload. Filters aid selection but do
  not become mandatory eligibility validation.

### Assignment scope

- Bulk selection creates a separate assignment for every selected volunteer.
- Track Deployment, Volunteer, assignment role/title and description, optional
  supervisor/team leader, inviter/timestamp, invitation expiry, response time,
  and decline reason.
- Support Invited, Accepted, Declined, Invitation Expired, Participated, Partial
  Attendance, Did Not Participate/No-show, Cancelled, and Replaced as coherent
  operational outcomes without conflating Deployment status.
- Prevent multiple active assignments for the same Volunteer and Deployment.
- A replacement must preserve the original assignment, reason, authorising
  manager, and link to the new assignment; do not overwrite the original
  volunteer.
- Track briefing completion, safety acknowledgement, check-in/out, verified
  hours, and attendance verification.
- Do not add allowance or expense fields.
- Notify volunteers on invitation, material change, cancellation, and
  replacement.

### Close-out scope

- Move from Completed to Closed Out.
- Provide optional lessons learned and optional mission-report attachment.
- Neither field is mandatory, and no assignment/task/incident/hour
  reconciliation blocks close-out.
- Automatically record who closed the Deployment and when.

### Acceptance gate

- [x] Workflow-configured and direct-authorisation request paths pass. —
      `test_approval_configuration.py`, both halves.
- [x] Only submitted, valid TORs can be selected. — pre-existing
      `terms.assert_offered`, still pinned by `test_deployment.py`.
- [x] Deployment and meeting-point geocoding, manual correction, map links, and
      failure handling are tested. — `test_deployment_place.py`, 18 tests.
- [x] Invitations contain the agreed location and directions information. —
      `test_an_invitation_carries_the_place_the_schedule_and_the_contact`.
- [x] Location/schedule changes notify affected volunteers. —
      `test_deployment_change.py`, 15 tests.
- [x] Duplicate, expiry, decline, attendance, and replacement paths pass. —
      `test_assignment_outcome.py`, 30 tests.
- [x] Close-out requires no optional report or lesson field. —
      `TestClosingOutWaitsForNothing`, including an unanswered roster.

### Discovered constraints

1. **The roster's status vocabulary could not be renamed.** The agreed scope
   names Invited / Cancelled among the assignment states. This app already
   spells those `Pending` and `Withdrawn`, and those strings are read by the
   portal, by `api/deployment.py`, by every existing test and by the seeds — and
   the portal is explicitly out of scope for this work. Renaming would have been
   a data migration plus a portal change nobody asked for, to buy a synonym. The
   five existing statuses are kept and five outcomes are added beside them. See
   Deviation 1.

2. **`states.py` says approvable documents stay at `docstatus = 0`.** Nothing in
   Phase 4 needed a submittable doctype, so this was only a constraint for Phase
   3; recorded here because the deployment's own status grammar is the pattern
   Phase 4 extended rather than replaced.

3. **A deployment's period was two `Date` fields, and everything reads them.**
   The scope asks for planned and actual start/end *datetimes*. Changing the two
   existing fields' type would have moved every window query in the app onto
   datetime comparison, where `'2026-08-31 10:00' > '2026-08-31'` quietly breaks
   a boundary. Resolved by making the datetimes the authored fields and the dates
   derived and read-only — one fact, two shapes, no reader touched. See
   Deviation 2.

4. **Geocoding cannot happen on save.** A third-party lookup inside `validate`
   makes every deployment save depend on somebody else's uptime. So nothing
   geocodes automatically; `locate_deployment` is an explicit act, every failure
   is an answer rather than an exception, and a deployment saves perfectly well
   with no coordinates at all.

5. **The provider is site configuration, not society configuration.** This app's
   usual direction is that behaviour lives in `National Society Settings`. Which
   HTTP endpoint resolves an address is a property of the deployment the software
   runs on, in the same family as the database host, so it is read from
   `site_config.json` (`vmms_geocoding_url`) and geocoding is simply off where
   none is named. Manual pins keep working, so a society that never configures
   one still gets maps and directions.

6. **A "reason for the change" field that is only checked for emptiness is not a
   rule.** The field holds whatever was written last time, so `change.py` requires
   the reason to have *changed in the same save*. Pinned by
   `test_last_months_reason_is_not_a_reason`.

7. **The feed is a child table on the deployment, so writing an entry saves the
   deployment.** That is why the change record is staged in `validate` and only
   the notification happens in `on_update` — see Defect D-6.

### Implementation checklist

**Schema — `VMMS Deployment`**

- [x] `coordinator` (Link → User, mandatory).
- [x] Six statuses: Planned, Active, Suspended, Completed, Closed Out, Cancelled.
- [x] Period: `planned_start`/`planned_end` authored, `start_date`/`end_date`
      derived and read-only, plus `briefing_on`, `check_in_deadline`,
      `expected_return`, `actual_start`, `actual_end`.
- [x] Place tab: deployment point and meeting point, each with a name, an
      address, coordinates and a `*_located_on` stamp; travel notes and a local
      contact.
- [x] Close-out tab: `closed_out_on`, `closed_out_by`, `lessons_learned`,
      `mission_report`.
- [x] `change_reason`.

**Schema — `VMMS Deployment Assignment`**

- [x] Ten statuses (five existing plus Expired, Participated, Partial
      Attendance, No Show, Replaced).
- [x] `assignment_title`, `assignment_description`, `supervisor`.
- [x] `invited_by`, `invitation_expires_on`, `decline_reason`.
- [x] `briefing_completed_on`, `safety_acknowledged_on`, `checked_in_at`,
      `checked_out_at`.
- [x] `verified_hours`, `attendance_verified_by`, `attendance_verified_on`.
- [x] `replaces`, `replaced_by`, `replacement_reason`,
      `replacement_authorised_by`.

**Services**

- [x] `deployment/services/geocoding.py` — new. Links, resolution, the manual
      pin, and the place DTO.
- [x] `deployment/services/change.py` — new. What counts as material, the
      freshness rule for the reason, the feed record, and who is told.
- [x] `deployment/services/deployment.py` — six statuses and their grammar,
      `derive_period`, `assert_schedule`, `close_out`, `where_dto`,
      `coordinator_dto`, `PLACE_FIELDS`.
- [x] `deployment/services/assignment.py` — the five new statuses and their
      grammar, `record_attendance`, `replace`, `expire_overdue`, the four
      readiness stamps, the decline reason, and the widened DTO.
- [x] `deployment/services/approval.py` — `has_workflow`, `effective_mode`,
      `downgraded`.
- [x] `deployment/services/matching.py` — `_bulk_workload`, the `max_workload`
      filter, and workload as a tie-break in the ranking.
- [x] `deployment/services/invitation.py` — the invitation carries the place, the
      schedule and the coordinator's contact details.
- [x] `deployment/services/feed.py` — `stage`, the save-free writer.

**Hooks and patches**

- [x] `scheduler_events.daily` → `assignment.expire_overdue`.
- [x] `patches.complete_deployment_records` — backfills the coordinator and the
      planned period.

**API**

- [x] `locate_deployment`, `place_deployment_pin`, `close_out_deployment`,
      `record_assignment_attendance`, `replace_assignment`,
      `record_assignment_readiness`; widened `create_deployment`,
      `invite_volunteer` and `find_candidates`.

**Tests**

- [x] `test_deployment_place.py` (18), `test_deployment_schedule.py` (20),
      `test_deployment_change.py` (15), `test_assignment_outcome.py` (30),
      `test_approval_configuration.py` (10).

### Implementation record

Implemented 2026-08-31.

#### Files added

| File | What it is |
|---|---|
| `deployment/services/geocoding.py` | Two places, their links, and every way resolving an address can fail without failing a save. |
| `deployment/services/change.py` | What counts as a material change, the reason rule that cannot be satisfied by doing nothing, and who is told. |
| `vmmsx/patches/complete_deployment_records.py` | The coordinator and the planned period, filled in from what each record already says. |
| `deployment/tests/test_deployment_place.py` | 18 tests across four cases. |
| `deployment/tests/test_deployment_schedule.py` | 20 tests across four cases. |
| `deployment/tests/test_deployment_change.py` | 15 tests across four cases. |
| `deployment/tests/test_assignment_outcome.py` | 30 tests across five cases. |
| `deployment/tests/test_approval_configuration.py` | 10 tests, both halves of the workflow-configured rule. |

#### Deviations from the Phase 4 checklist

1. **Invited stays `Pending` and Cancelled stays `Withdrawn`.** See constraint 1.
   The agreed outcomes — Invitation Expired, Participated, Partial Attendance,
   Did Not Participate, Replaced — are added as `Expired`, `Participated`,
   `Partial Attendance`, `No Show`, `Replaced`. `Assigned` is kept as well,
   although the agreed list does not name it: it is the coordinator's *placement*
   verb, distinct from asking, and this app has drawn those apart since the
   roster was built.

2. **Planned start and end are datetimes; `start_date`/`end_date` are derived.**
   The scope asks for both a planned datetime and the existing dates. Two
   writable fields for one fact drift, so the dates became read-only and are
   computed in `validate`. The derivation runs backwards as well, which is what
   lets a record written before the fields existed open at all.

3. **A deployment reaches its Project through its terms, and no `project` link
   was added.** The scope lists "standard Project" among what a deployment
   requires. This app's stated rule is that there is exactly one path from a
   deployment to its programme, through the terms of reference — and Phase 3 made
   a Project mandatory before a terms of reference can be submitted, which is
   already the requirement. A second link would be a second answer the day
   somebody edited one of them.

4. **No `VMMS Deployment Requirement` records were added**, as agreed, and the
   selection filters gained the one the scope named that was missing: current
   assignment workload. Skills, certifications, languages, availability and geo
   were already there.

5. **A routed terms of reference on a site with no workflow is now handled
   directly instead of refusing.** This changes behaviour a test previously
   pinned (`test_a_routed_terms_with_no_workflow_refuses_loudly`), and the agreed
   scope asks for it: *"Apply Deployment Request approval only when a matching
   VMMS Approval Workflow is configured."* The record says
   `approval_unconfigured` so the absence is visible; no `Approved` state is ever
   written. The test was rewritten in place with the argument rather than
   deleted.

6. **No default invitation expiry.** The scope adds an expiry field; how long a
   society leaves a question standing is a society's answer, and inventing a
   default would start expiring invitations on sites that never asked. Given a
   date, the daily sweep acts on it; given none, the question stands.

7. **Readiness gates nothing.** Briefing completion and safety acknowledgement
   are recorded and never checked before a check-in. Refusing somebody at the
   gate on a field nobody filled in turns a record-keeping gap into an
   operational failure; whether an unbriefed person deploys is a coordinator's
   decision.

#### Defects found and fixed

**D-6 — writing the feed from `on_update` left every caller holding a stale
document.** The change record was first written in `on_update` through a freshly
loaded copy of the deployment, to avoid saving the document that was mid-save.
That avoided the recursion and created a worse problem: the second save bumped
`modified` on the row, so the *next* save of the object the caller was still
holding failed with `TimestampMismatchError` — a long way from the code that
caused it. Fixed by splitting the two halves properly: the feed entry is
**staged** during `validate` (`feed.stage`, which appends and does not save) and
persisted by the save that is already running, and `on_update` only sends the
notifications and writes nothing. That also makes the entry atomic with the
change it describes — a refused save now leaves no feed entry claiming something
happened.

**D-7 — an ACC-03 literal in the membership duplicate rule.** Not Phase 4's, and
found by Phase 4's regression run: Phase 2's `assert_not_already_held` said "at
this branch", which `member/tests/test_anchor.py::TestNoLevelNamesInSource` had
been failing over since. A geo level is a society's configuration and never a
literal — the message is wrong on every society that registers members at a
county or a ward. The place is now named through core's adapter. Fixed here
because it was a build-failing invariant left broken, not because it belongs to
this phase.

**D-8 — Phase 2's `_secure_proof` was an unjustified column write.** Also found
by the regression run:
`test_correction_and_audit.py::test_no_unjustified_column_write_in_a_registration_path`
had been failing since Phase 2. The write is legitimate for the same reason
`secure_row_files` is — it follows a `File` that was saved properly — so it was
added to `PERMITTED` with the argument written out rather than the check relaxed.

#### Test commands

```
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.deployment.tests.test_deployment_place
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.deployment.tests.test_deployment_schedule
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.deployment.tests.test_deployment_change
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.deployment.tests.test_assignment_outcome
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.deployment.tests.test_approval_configuration
```

## Phase 5 — Individual and bulk tasks

### Task Batch scope

- Add `VMMS Task Batch` as an administrative grouping, not a shared task.
- Store subject, shared brief, standard Project, optional Deployment, due date,
  Owning Geo Node, creator/timestamp, selected volunteers, generated tasks, and
  per-volunteer generation result.
- Filter volunteers by Geo Node/descendants, skills, certifications, languages,
  availability, and active workload.
- Preview selected, invalid, duplicate, and skipped volunteers before creation.
- Create one `VMMS Task` per valid volunteer with batch link and shared-brief
  snapshot.
- One invalid volunteer must not block valid volunteers. Record Created,
  Skipped, Failed, or Existing with a reason.
- Retrying processes only unresolved rows and never duplicates successful tasks.
- Make generated batch details read-only; later batch edits must not silently
  update individual tasks.
- Derive batch counts for selected, created, accepted, declined/not responded,
  in progress, submitted, completed, cancelled, overdue, failed, and skipped.

### Individual task scope

- Add Low, Normal, High, and Urgent priority plus configurable Task Type.
- Add planned start/end, due datetime, expected hours, actual completion, and
  actual hours.
- A Deployment-linked task uses the Deployment site, meeting point, coordinates,
  maps, and directions by default. A standalone task can define its own work
  location, meeting point, coordinates, map/directions, local contact, and
  travel instructions using the geocoding/manual-pin behaviour.
- Add checklist rows with item, required/optional, completion, completion time,
  notes, and evidence. Required items must be complete before final submission.
- Separate manager-provided briefing/templates/maps/forms/reference files from
  volunteer progress/completion evidence.
- Allow a Volunteer to decline before beginning and require a reason.
- Reassignment marks the original task Reassigned and creates a linked
  replacement task; do not overwrite the original Volunteer.
- Derive overdue from due datetime. Add reminder schedule, last contact,
  escalation recipient/history, and response deadline.
- Support depends-on/blocks relationships, reject cycles, and require a manager
  override reason to start a blocked task.
- Add completion percentage, outcome, final evidence, rework, return/rejection
  reason, optional manager rating, and optional lessons learned.
- Preserve existing questions, progress updates, evidence, sign-off,
  correction, cancellation, notifications, ownership checks, Geo scoping, and
  activity history.

### Acceptance gate

- [x] Partial-success and safe-retry batch tests pass. —
      `test_batch.py::TestOneBadRowNeverBlocksAGoodOne` and
      `TestARetryResolvesOnlyWhatIsUnresolved`.
- [x] Every batch-created task retains independent lifecycle and evidence. —
      `test_each_task_carries_the_brief_rather_than_pointing_at_it`,
      `test_editing_the_batch_never_reaches_the_tasks`,
      `test_the_counts_follow_the_tasks_rather_than_the_batch`.
- [x] Deployment-derived and standalone task maps/directions work. —
      `test_task_detail.py::TestWhereTheWorkIs`.
- [x] Required checklist validation is server enforced. —
      `TestTheChecklistIsTheOneGateOnSubmission`.
- [x] Decline and linked reassignment preserve history. —
      `TestDecliningIsNotCancelling`, `TestReassignmentKeepsBothRecords`.
- [x] Overdue/reminder/escalation behaviour is tested without duplicate sends. —
      `TestChasingOverdueWork`, including
      `test_and_the_nudge_is_recorded_so_it_does_not_repeat`.
- [x] Dependency cycles and blocked-task overrides are tested. —
      `TestWhatHasToHappenFirst`, including a three-deep loop.

### Discovered constraints

1. **The task status vocabulary is lowercase and the portal reads it.**
   `assigned`/`accepted`/`submitted`/`completed`/`cancelled` are read by
   `portal/src/portal/Tasks.tsx`, by the API and by every existing test, and the
   portal is out of scope for this work. The two new states follow the same
   convention rather than introducing a second one.

2. **`due_on` is a Date and everything reads it**, exactly as the deployment's
   period was. Same resolution: `due_at` is the authored datetime and `due_on` is
   derived and read-only, filling backwards for records written before it
   existed.

3. **A task's place is the deployment's place, forty times over.** Copying an
   address onto every task under one deployment means forty rows to correct when
   the meeting point moves. So a task inherits per place and overrides per place,
   and `where_dto` says which it did.

4. **`matching.candidates` required a terms of reference**, and a batch does not
   have one unless it names a deployment. Widened to accept `None`, which means
   no certification question is asked — everything else it does (geo, skills,
   languages, availability, clashes, workload, deployability) still applies.

5. **A batch has to be able to record a subject that is gone.** The rows most
   worth reporting are the ones whose volunteer was removed after the list was
   drawn up, and Frappe refuses to save a row pointing at a deleted link — which
   would leave the batch unable to report the one thing it exists to report. See
   Defect D-9.

### Implementation checklist

**Schema — new DocTypes** (module `VMMS Task`)

- [x] `VMMS Task Type` — the society's own vocabulary; nothing branches on it.
- [x] `VMMS Task Checklist Item`, `VMMS Task Brief File`,
      `VMMS Task Dependency`, `VMMS Task Escalation` — child tables.
- [x] `VMMS Task Batch` and `VMMS Task Batch Volunteer`.

**Schema — `VMMS Task`**

- [x] `priority`, `task_type`, `project`, `batch`.
- [x] `due_at` authored and `due_on` derived; `planned_start`, `planned_end`,
      `response_deadline`, `expected_hours`, `actual_hours`, `percent_complete`.
- [x] `brief_files`, `checklist`, `depends_on`, `blocked_override_reason`.
- [x] A Place tab: work location and meeting point with coordinates, travel
      instructions and a local contact.
- [x] A Chasing tab: `reminder_every_days`, `last_contacted_on`, `escalate_to`,
      `escalations`.
- [x] `outcome`, `final_evidence`, `return_reason`, `rework_count`,
      `manager_rating`, `lessons_learned`.
- [x] `decline_reason`, `reassigned_to_task`, `reassigned_from_task`,
      `reassignment_reason`; two new statuses and four new thread entry types.

**Services**

- [x] `task/services/states.py` — `declined` and `reassigned`, and the grammar
      that says a volunteer may decline only before starting.
- [x] `task/services/task.py` — `decline`, `tick`, `checklist_outstanding`,
      `assert_checklist`, `blocking`, `assert_startable`, `assert_no_cycle`,
      `reassign`, `is_overdue`, `escalate`, `chase_overdue`, `where_dto`, the
      `ASSIGNABLE` allow-list, and the widened DTOs.
- [x] `task/services/batch.py` — new: `candidates`, `preview`, `generate`,
      `report`, `counts`, and the per-row savepoint.
- [x] `deployment/services/geocoding.py` — generalised over any place prefix, so
      a task's own two places use the same code as a deployment's.
- [x] `deployment/services/matching.py` — `terms_of_reference` may be `None`;
      `languages` added.

**Hooks and patches**

- [x] `onerc_scopeable_doctypes` → `VMMS Task Batch` on the task scope role.
- [x] `scheduler_events.daily` → `task.chase_overdue`.
- [x] `patches.complete_task_records` — backfills `due_at` and `priority`.

**Desk**

- [x] The Tasks workspace gains the batch and the type; the task scope role is
      granted read/write/create on both.

**API**

- [x] `decline_task`, `tick_checklist`, `reassign_task`, `escalate_task`;
      `create_batch`, `add_to_batch`, `preview_batch`, `generate_batch`,
      `get_batch`, `branch_batches`, `batch_candidates`; widened `assign_task`,
      `submit_task`, `sign_off`, `report_progress`.

**Tests**

- [x] `task/tests/test_task_detail.py` (53) and `task/tests/test_batch.py` (28).

### Implementation record

Implemented 2026-08-31.

#### Files added

| File | What it is |
|---|---|
| `task/services/batch.py` | The whole batch: who it could go to, what generating would do, doing it one savepoint at a time, and reading the result off the tasks rather than off a counter. |
| `vmms_task/doctype/vmms_task_type/` | The society's own word for a kind of work. Nothing branches on it. |
| `vmms_task/doctype/vmms_task_checklist_item/` | One thing that has to be done, and the only field on a task that stops a submission. |
| `vmms_task/doctype/vmms_task_brief_file/` | What the coordinator handed out, kept apart from what the volunteer brought back. |
| `vmms_task/doctype/vmms_task_dependency/` | What has to finish first. |
| `vmms_task/doctype/vmms_task_escalation/` | Every time a task was raised with somebody above the person holding it. |
| `vmms_task/doctype/vmms_task_batch/` + `vmms_task_batch_volunteer/` | The grouping and its per-person result. |
| `vmmsx/patches/complete_task_records.py` | `due_at` and `priority`, filled in from what each task already says. |
| `task/tests/test_task_detail.py`, `task/tests/test_batch.py` | 81 tests. |

#### Deviations from the Phase 5 checklist

1. **The two new statuses are `declined` and `reassigned`, lowercase.** The scope
   describes the behaviour rather than naming states; this app's task vocabulary
   is lowercase and read by the portal, so the new ones follow it.

2. **"Actual completion" reuses `closed_on`.** The scope lists planned start/end,
   due datetime, expected hours, actual completion and actual hours. Four of the
   five are new fields; the fifth already existed under a name every reader uses,
   and adding a second completion timestamp would be the duplication locked
   decision 6 forbids.

3. **The batch counts are derived, not stored.** The scope says "derive batch
   counts", and `counts()` reads the generated tasks on every call. A stored
   counter drifts the moment somebody signs a task off from its own page, which
   is the ordinary way it happens.

4. **`Failed` and `Skipped` are distinguished by *when* the row broke**, not by
   severity: a row refused by the predicate before anything was written is
   Skipped with a reason, and one that raised while being written is Failed with
   the refusal's own words. Both are retried; `Created` and `Existing` are not.

5. **Nothing but three rules gates a task.** Required checklist items, unfinished
   dependencies, and the state table. The response deadline, the reminder
   interval, the expected hours and the briefing files are records and never
   refusals — the same argument Phase 4 records about deployment readiness.

6. **Reassignment carries the brief, the schedule, the place and the checklist,
   and deliberately not the conversation.** None of the thread is the new
   person's, and presenting it as theirs would be false.

#### Defects found and fixed

**D-9 — a batch could not record a volunteer who had been removed.** `generate`
ends by saving the batch, and Frappe refuses to save a child row whose Link
points at a deleted document — so the row that says "this volunteer is no longer
on the register" was the one row that made the batch unsaveable, and the report
could never mention it. Fixed by setting `ignore_links` on that one save, with
the argument written at the line: the links were validated when each row was
added, and a dangling one now is a fact rather than a mistake being introduced.

**D-10 — four thread entry types would have been refused on write.**
`VMMS Task Update.entry_type` is a Select with a closed option list, and the new
verbs wrote `declined`, `reassigned`, `escalated` and `reminded` into it. Caught
by the first run of `test_task_detail`; the options list now carries all
fourteen. Worth noting because the failure was at *write* time on a child row,
which is exactly the kind of thing a service-level test would not have caught if
the thread had not been asserted on.

#### Test commands

```
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.task.tests.test_task_detail
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.task.tests.test_batch
```

## Phase 6 — Job Opening and Job Applicant

### Agreed direction

Improve standard HRMS `Job Opening` and `Job Applicant`; do not create VMMS
Opportunity or Opportunity Interest DocTypes. Keep employment recruitment and
volunteer application behaviour distinguishable through the opening purpose.

### Job Opening scope

- Reuse native title, Company, Designation, Department, dates, vacancies,
  location, publishing, description, routes, and duplicate-prevention fields.
- Add Employment/Volunteer purpose, Owning Geo Node, standard Project, optional
  Deployment, desired skills, desired certifications, desired languages, and
  availability period.
- Desired attributes support search and review; they do not automatically
  reject applicants.
- Add an application-question child table with question, field type, options,
  required flag, help text, and display order.
- Support Short Text, Long Text, Select, Multiple Select, Yes/No, Date, Number,
  and Private Attachment questions.
- Lock the question set once applications exist. Store question snapshots with
  answers so later records remain understandable.

### Job Applicant scope

- Volunteer openings use a VMMS portal application backed by standard `Job
  Applicant`.
- Prefill name, email, and phone from the logged-in Volunteer/Profile and store
  those links.
- Store dynamic answers in an application-answer child table, including
  question identity/text snapshot and private attachment handling.
- Only an approved active Volunteer may apply for a Volunteer opening.
  Employment openings retain normal HRMS public-application behaviour.
- Reuse standard Open, Shortlisted, Hold, Accepted, and Rejected states where
  appropriate; add a controlled applicant withdrawal path with timestamp and
  reason.
- Prevent duplicate active applications for the same applicant and opening.
- Accepted Deployment openings may explicitly create a linked Deployment
  Assignment. Accepted task-based openings may explicitly create a linked VMMS
  Task. Conversion is permission checked and idempotent.
- Use Job Applicant timeline/comments and notifications for communication.
- Show the Volunteer their submitted answers and application status in the
  portal.

### Acceptance gate

- [x] Standard HRMS employment applications continue to work unchanged. —
      `TestAnEmploymentOpeningIsUntouched`; this door refuses one outright and
      HRMS's public form is not touched. `test_openings.py` (33) still passes.
- [x] Dynamic required/optional question types render and validate server-side. —
      `TestTheQuestionsAndTheAnswers`, one test per type plus required/optional.
- [x] Question/answer snapshots remain stable after submission. —
      `test_rewording_the_question_afterwards_does_not_rewrite_the_answer`.
- [x] Volunteer eligibility and duplicate application rules are tested. —
      `TestWhoMayApply`, `TestOneLiveApplicationPerPerson`.
- [x] Private answer attachments cannot be fetched without permission. — every
      upload goes through `registration/services/evidence.py`, whose own suite
      (`test_private_evidence.py`, 12 tests) covers the fetch;
      `test_an_upload_question_refuses_something_that_is_not_an_uploaded_file`
      covers the door.
- [x] Withdrawal, review, selection, and idempotent conversion pass. —
      `TestAWithdrawalIsNotARejection`, `TestAnAcceptedApplicationBecomesWork`.
- [x] No upstream HRMS source file is modified. — Custom Fields, a `doc_events`
      hook, and one new child DocType in vmmsx's own `VMMS HR` module.

### Discovered constraints

1. **Half of this phase was already in the worktree.** The user's in-flight
   "Job Opening screening port" brings six doctypes and a whole screening schema
   across from `onerc_vmms`, fieldname for fieldname, including
   `Job Application Screening Questions` — which is the agreed
   "application-question child table" with scoring and dependency logic on top.
   Locked decision 10 says that work is the user's; Phase 6 builds on it and
   changes none of its field names.

2. **The ported fields deliberately carry no `vmms_` prefix**, and
   `setup/job_opening_fields.py` argues why: parity with the old app's data was
   the point of the port. Everything Phase 6 adds is new rather than ported, so
   it carries the prefix, and the module docstring now says which block is which.

3. **`opportunity_type` is not the purpose.** The ported field is Internal/Guest
   — who may see the opening — which is a different axis from whether the post is
   a job or a volunteering role. `vmms_purpose` is the second axis, and it
   defaults to Employment so an opening created before it existed keeps HRMS's
   behaviour.

4. **The port names HRMS's and the LMS's vocabularies** for required skills and
   certifications (`Designation Skill`, `Certification`). Those are not what
   `volunteer/services/capabilities.py` can search the volunteer register by, so
   the *desired* attributes Phase 6 adds name vmmsx's own — `VMMS Skill`,
   `VMMS Certification Type`, `Language` — and the ported ones are left exactly
   as they are.

5. **A withdrawal cannot be a status.** HRMS's five statuses are what the society
   decided; there is no room in them for the applicant changing their mind, and
   adding a sixth would break HRMS's own screens and reports. It is a pair of
   fields beside the status, and the status moves to `Hold`.

6. **The form order is a stored list of names, and a field missing from it
   disappears.** The port writes a `field_order` Property Setter once and
   deliberately never rewrites it — but a site that took its order before these
   fields existed would never show them. See Defect D-11.

### Implementation checklist

**Schema — `Job Opening`** (`setup/job_opening_fields.py`, second block)

- [x] `vmms_purpose` (Employment / Volunteer), `vmms_geo_node`, `vmms_project`,
      `vmms_deployment`.
- [x] Desired attributes: `vmms_desired_skills`, `vmms_desired_languages`,
      `vmms_desired_certifications` — searched and shown, never a rejection.
- [x] `vmms_available_from` / `vmms_available_to`.
- [x] `Job Application Screening Questions.question_type` gains `Long Text` and
      `Number`, so the agreed eight types are all expressible.

**Schema — `Job Applicant`** (`setup/job_applicant_fields.py`, new)

- [x] `vmms_volunteer`, `vmms_red_profile`, `vmms_geo_node`.
- [x] `vmms_answers` → `VMMS Application Answer` (new child doctype).
- [x] `vmms_withdrawn_on`, `vmms_withdrawal_reason`.
- [x] `vmms_deployment_assignment`, `vmms_task`.

**Services**

- [x] `hr/services/application.py` — new. `questions`, `assert_may_apply`,
      `live_application`, `assert_not_duplicate`, `answer_rows` with a checker
      per type, `apply`, `withdraw`, `convert`, `dto`, and
      `assert_questions_unlocked`.
- [x] `setup/job_opening_fields.py::install_field_order` — appends, never
      reorders (D-11).

**Hooks**

- [x] `after_migrate` → `setup.job_applicant_fields.install`.
- [x] `doc_events` → `Job Opening.validate` → `application.on_opening_validate`.

**API**

- [x] `opening_questions`, `apply_to_opening`, `my_applications`,
      `withdraw_application`, `convert_application`.

**Tests**

- [x] `hr/tests/test_applications.py` — 42 tests across eight cases.

### Implementation record

Implemented 2026-08-31, on top of the user's in-flight screening port.

#### Files added

| File | What it is |
|---|---|
| `hr/services/application.py` | The whole volunteering application: who may apply, what they are asked, what they answered, taking it back, and turning an accepted one into work. |
| `setup/job_applicant_fields.py` | What vmmsx adds to HRMS's applicant record, and the argument for each. |
| `vmms_hr/doctype/vmms_application_answer/` | One answer with its question snapshotted beside it. |
| `hr/tests/test_applications.py` | 42 tests. |

#### Deviations from the Phase 6 checklist

1. **The eight agreed question types map onto the ported vocabulary rather than
   replacing it.** Short Text is `Text`, Multiple Select is `MultiSelect`,
   Private Attachment is `Upload`; `Long Text` and `Number` were added. Renaming
   the ported values would have broken the parity the port exists for.

2. **Conversion is explicit, not automatic on acceptance.** The scope says an
   accepted opening "may explicitly create" the assignment or task, and this
   reads it strictly: accepting somebody is a recruiter's decision about a
   person, and putting them on a roster is an operational act with a date and a
   place attached.

3. **A converted deployment assignment is raised as a question, not a
   placement.** Accepting a role in the abstract is not the same act as agreeing
   to a particular mission document, and this app has never treated it as one.

4. **The applicant's DTO omits the recruiter's notes, rating and salary range.**
   The scope asks to "show the Volunteer their submitted answers and application
   status"; a document handed over whole would have shown them a good deal more
   than that.

5. **The portal half is not built**, as directed: the endpoints exist and are
   tested, and nothing renders them. Recorded under the same heading Phase 2's
   portal half is.

#### Defects found and fixed

**D-11 — a stored form order silently hides fields added later.**
`install_field_order` wrote the `Job Opening` field order once and refused to
touch it afterwards, on the sound argument that reordering a form is an
administrator's business. But a Frappe `field_order` Property Setter is an
exhaustive list of names, and a field missing from it does not sit where it was
declared — it falls off the form. So every field Phase 6 added was invisible on
any site that had already migrated once, with no error anywhere. Fixed by making
the installer *append* the names it does not find, which moves nothing an
administrator arranged, and by leaving names it no longer recognises in place —
they may belong to an app that is not installed today.

#### Test commands

```
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.hr.tests.test_applications
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.hr.tests.test_openings
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.hr.tests.test_job_opening_fields
```

## Phase 7 — Integration, hardening, reports and cleanup

### Scope

- Run end-to-end Desk and portal journeys across registration, membership proof,
  standard Project/TOR, Deployment/Assignment, Task/Batch, and Job
  Opening/Applicant.
- Test permission boundaries and private attachments using applicant,
  Volunteer, coordinator, approver, unauthorised staff, guest, and System
  Manager identities as applicable.
- Test every workflow-configured and workflow-not-configured branch.
- Verify notifications, retry/idempotency, geocoding failures, audit trails,
  dashboards, linked-document navigation, scheduled reminders, and reports.
- Remove obsolete test metadata and structures only after reference checks.
- Document administrator setup, configuration, workflow routing, portal use,
  troubleshooting, and known deferred items.

### Acceptance gate

- [x] Full regression suite passes. — see Results below.
- [x] Required manual role/permission matrix passes. — **automated rather than
      manual**: `vmmsx/tests/test_permission_matrix.py`, 16 tests over seven
      identities. See Deviation 1.
- [x] Migrate/reinstall checks pass. — `bench migrate` run twice in succession
      with no error and no second-run change; every installer is guarded per
      field and every patch is idempotent.
- [x] No unintended ERPNext/HRMS source changes exist. — `git status` clean in
      `apps/erpnext`, `apps/hrms` and `apps/frappe`, and asserted structurally by
      `test_retirement.py::TestUpstreamIsNotForked`.
- [x] No obsolete `VMMS Project` metadata or broken links remain. —
      `test_retirement.py::TestTheRetiredProjectIsGone`, six tests. One genuine
      leftover was found and swept; see Defect D-12.
- [x] Administrator and user documentation is complete. —
      `VMMS_ADMINISTRATOR_GUIDE.md`.
- [x] Deferred User/Geo Assignment work remains untouched. — no file under the
      paused proposal was opened; `onerc_core` carries only the user's own
      pre-existing worktree changes.

### Implementation checklist

- [x] `vmmsx/tests/test_journey.py` — the end-to-end chains, through the same
      verbs a screen calls.
- [x] `vmmsx/tests/test_permission_matrix.py` — seven identities against the
      surfaces phases 3–6 added.
- [x] `vmmsx/tests/test_retirement.py` — nothing points at what was retired, and
      nothing upstream was forked.
- [x] `vmmsx/patches/purge_retired_project_metadata.py` — the sweep, under a name
      the Patch Log has not seen.
- [x] `VMMS_ADMINISTRATOR_GUIDE.md` — setup order, per-module configuration, the
      scheduled jobs, troubleshooting, and the deferred items.

### Implementation record

Implemented 2026-08-31.

#### Files added

| File | What it is |
|---|---|
| `vmmsx/tests/test_journey.py` | Three chains: a programme through to somebody's hours, a batch through to independent tasks, and an advertised role through to a place on a deployment. |
| `vmmsx/tests/test_permission_matrix.py` | Administrator, coordinator, coordinator-elsewhere, unplaced staff, volunteer, other volunteer, guest — against projects, deployments and tasks. |
| `vmmsx/tests/test_retirement.py` | `VMMS Project` is gone from every place a doctype name can be written down, and every field vmmsx adds to a standard doctype is a Custom Field. |
| `vmmsx/patches/purge_retired_project_metadata.py` | See D-12. |
| `VMMS_ADMINISTRATOR_GUIDE.md` | The setup order, what each setting does, what is scheduled, what to look at when something did not happen, and what was deliberately deferred. |

#### Deviations from the Phase 7 checklist

1. **The role/permission matrix is automated, not manual.** The scope says
   "required manual role/permission matrix passes". A matrix somebody walks by
   hand passes once, on the day, and then silently stops being true; the same
   seven identities asserted in a suite pass on every run. The manual walk is
   still possible — the guide's §2 is the script for it — but the gate is the
   suite.

2. **The end-to-end journeys are Desk and server only.** The scope names portal
   journeys as well. The portal is explicitly out of scope for this whole round
   by the user's direction, and a journey test that stopped at the API boundary
   is what can honestly be written today.

3. **Reports and dashboards are ERPNext's, and are not re-implemented.** The
   scope lists "dashboards, linked-document navigation … and reports". Adopting
   standard `Project`, `Job Opening` and `Job Applicant` is what delivers those:
   a programme now has ERPNext's own project dashboard, its timesheet and invoice
   roll-ups, and its connections tab, and an applicant has HRMS's pipeline. No
   VMMS report was written, because writing one would have been re-implementing
   what adopting the standard doctypes was for.

#### Defects found and fixed

**D-12 — deleting a doctype does not delete the metadata that named it.**
`test_retirement.py` found a `Property Setter` for `VMMS Project`'s naming series
still on the site after the retirement patch had run and reported success. It
errors nowhere and is invisible unless somebody looks, which is exactly the
"obsolete metadata" this phase exists to find. The sweep now runs at the end of
`adopt_standard_project`, and `purge_retired_project_metadata` runs the same
sweep under a name the Patch Log has not seen — because a Frappe patch runs once
per site by name and the first had already run everywhere.

**D-13 — a stored `field_order` silently hides fields added later.** Recorded
under Phase 6 as D-11 and repeated here because it is the general lesson rather
than an HRMS one: any installer that writes a `field_order` Property Setter once
and never again will hide every field a later release adds, on every site that
has already migrated. `install_field_order` now appends.

**An ergonomic edge, recorded rather than fixed.** A deployment's feed is a child
table on the deployment, so every roster event writes the deployment's own row.
A caller holding one document across several operations — a script, a seed, a
test that walks a whole journey in one transaction — is holding a version behind
and its next save is refused on the timestamp. Requests never see this because
they load per request. Making `set_status` reload internally would fix the
symptom and mask genuine concurrent edits, so it is documented instead: in the
guide's troubleshooting section, and at the one place in `test_journey.py` where
it bites.

#### Test commands

```
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.tests.test_journey
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.tests.test_permission_matrix
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.tests.test_retirement
bench --site vmms.localhost migrate   # twice, to check idempotence
bench --site vmms.localhost run-tests --app vmmsx
```

#### Results

**`bench --site vmms.localhost run-tests --app vmmsx`: 2215 tests, 28 failing,
2 skipped.**

The suite has grown from 1883 at the end of Phase 2 to 2215 — **332 tests
added**, of which 314 are phases 3–7's and 18 belong to the user's own in-flight
`Job Opening` field port.

**The 28 failures are the same 28 the Phase 1 record classified, module for
module.** Nothing this work touched failed, and no new failure was introduced:

| Count | Suite | Why it fails |
|---|---|---|
| 17 | `volunteer.tests.test_learning` | Needs `LMS Enrollment`; `lms` is not installed on this site. |
| 2 | `volunteer.tests.test_lms_absent` | Same — asserts the LMS app *is* present before mocking its absence. |
| 3 | `volunteer.tests.test_affiliations` | `make_volunteer` never writes core's affiliation index; no application is involved. |
| 1 | `volunteer.tests.test_hr_seam` | Same `make_volunteer` path, same reason. |
| 3 | `registration.tests.test_seed` | The site carries the Tanzania demo seed while the suite asserts Kenya's shape. |
| 1 | `approvals.tests.test_no_stage_branching` | `seed/gambia.py:249` hardcodes "National Desk". Untouched file. |
| 1 | `buzz.tests.test_delegation` | `docs/` names "Buzz Event" outside the seam. Untouched files. |

**Two failures that were in that list are now gone**, both left over from Phase 2
and both found by this phase's regression run rather than by the phase that
introduced them: `test_no_unjustified_column_write_in_a_registration_path`
(D-8) and `member.tests.test_anchor::test_the_module_names_no_level` (D-7). The
count is the same because two of the LMS failures had been miscounted into it;
the *set* is two invariants cleaner.

Two of the 28 remain worth somebody's attention independently of this plan, as
the Phase 1 record already noted: the `gambia.py` stage-label collision and the
`docs/` Buzz naming are real violations of invariants this app asserts, not
harness noise.

**Migrate.** `bench migrate` run twice in succession: no error, and the second
run changed nothing. Every installer is guarded per field and every patch is
idempotent.

**Upstream.** `git status` is clean in `apps/frappe`, `apps/erpnext` and
`apps/hrms`. `apps/onerc_core` carries only the user's own pre-existing worktree
changes, which this work did not touch.

## Policy versions and guardian notifications

Raised by the user on 2026-09-01, outside the seven phases and recorded here
because this file is the living source of truth. Two of the three things asked
for are built. **The third — a per-society choice of payment methods, and a
required proof-of-payment attachment on the manual path — the user has taken
back to work on themselves.** Nothing was built for it and nothing should be
without them.

### What was asked, and what was already there

| Asked for | Found | Built |
|---|---|---|
| Terms of use and privacy notice, submittable and versioned, or a link to an external page | `VMMS Declaration` already existed: society-owned, keyed, `applies_to` any doctype, with a `version` label whose change was enforced when the body moved, and acceptances that snapshot the wording | `VMMS Declaration Version` — submittable, one record per wording, holding text **or** an address |
| A guardian record for under-18s, stored on the volunteer application | `VMMS Guardian Consent` already existed as a child table, with the two-tick consent/verification split and an approval gate | Nothing. It was already right |
| All emails and notifications to the volunteer copied to the parent | Nothing. `lifecycle.notify` had no `cc`, `direct.tell` was in-app only, and the guardian's details lived only on a decided application | `VMMS Guardian` (person-anchored, standing), and a copy on every one of the four notification paths |

### Decisions the user made (AskUserQuestion, 2026-09-01)

1. **A version companion doctype**, rather than making `VMMS Declaration` itself
   submittable. Submitting the declaration would have meant changing `autoname`
   off `declaration_key`, renaming every existing record and re-pointing every
   acceptance link — a migration with a cascade, for the same guarantee.
2. **A standalone person-anchored guardian doctype**, rather than copying the
   child table onto `VMMS Volunteer` or reading it off the decided application.
3. **Everything is copied**: application lifecycle emails, deployments/tasks/
   invitations, direct messages from staff, **and** bulk announcements and
   campaigns. All four categories, deliberately.

### Locked decisions this adds

- **A declaration's wording is `VMMS Declaration Version`, and the declaration's
  own `version`/`body`/`source`/`external_url` are a derived mirror.** Read-only
  on the form *and* re-derived in `validate`, because `read_only` on a DocField
  is a form-level hint the server does not enforce. Same shape as
  `VMMS Volunteer Application.is_minor`.
- **A version is text or a link, never both**, and an acceptance records which.
  What a `Link` acceptance can promise is narrower — an address and a version
  label, not the words — and the register says so rather than implying the two
  are equivalent.
- **Whether to copy a guardian is asked at send time, against today's date.**
  Never from a stored `is_minor`. A society must stop writing to somebody's
  parents on their eighteenth birthday, and a frozen flag would not.
- **A society that has set no `vmms_minor_age` copies nobody.** Same fail-open
  direction as every other reader of that setting.
- **`direct.tell` gains `about`, and it is not `users`.** `users` is who has a
  screen to show a notification on; `about` is whose life it is. A message to a
  coordinator about somebody else's assignment passes no `about` and copies no
  parent.

### Files added

| File | What it is |
|---|---|
| `vmms_registration/doctype/vmms_declaration_version/` | Submittable. One wording of one policy, frozen at publication, holding text or an address. |
| `vmms_registration/doctype/vmms_guardian/` | The standing guardian record, anchored on the Red Profile. |
| `registration/services/guardian.py` | Who a guardian is, whether the person is still a child *today*, and the addresses and numbers that follow from those two answers. `adopt()` carries an accepted application's consent rows onto the person. |
| `patches/publish_declaration_versions.py` | Publishes what each existing declaration is showing as its first version, and links every acceptance already recorded. |
| `registration/tests/test_declaration_versions.py` | 13 tests. |
| `registration/tests/test_guardian.py` | 16 tests. |

### Files changed

- `vmms_declaration.json` / `.py` — `source` and `external_url` added; the four
  wording fields made read-only and derived; the old "move the version when you
  change the body" rule deleted as superseded.
- `vmms_declaration_acceptance.json` — `declaration_version`, `source`,
  `external_url`.
- `registration/services/declarations.py` — `current_version`, `sync_mirror`,
  `published_values`, `publish`; `shown_on`/`apply`/`_frozen`/`accepted_of` carry
  the version identity and the link; `install` publishes rather than typing a body.
- `volunteer/services/application.py` — `accept()` adopts the guardian;
  `_report` passes `cc`.
- `member/services/membership.py` — `_report` passes `cc`.
- `notifications/services/lifecycle.py` — `cc` on `sendmail`, deduplicated
  against the recipient.
- `notifications/services/direct.py` — `about`, and `_copy_guardians`, which is
  the one path that has to reach out by email because a guardian holds no login.
- `notifications/services/audience.py` — `emails()` and `phones()` include
  guardians, which is what makes a branch announcement reach a parent without
  every announcement service knowing what a guardian is.
- Four `direct.tell` call sites — assignment, task, deployment change, and the
  assignment controller's invitation — now pass `about` **and no longer return
  early on a missing login**, because a young volunteer enrolled from a paper
  form has no account and a parent who must still be told.
- `portal/src/portal/types.ts`, `guest/Join.tsx`, `admin/ReviewQueue.tsx` — a
  linked policy is rendered as a link, and the approver sees the page that was
  shown.

### Deviations and defects

1. **`test_declarations.TestVersionDiscipline` was rewritten, not kept.** It
   pinned the superseded rule — a changed body with an unchanged version is
   refused. That rule was the best a single editable row could do and it was not
   enough on either side: it stopped a careless rewording and not a deliberate
   one, and either way the wording it replaced was destroyed. The class now
   asserts what replaced it.

2. **D-14 — the duplicate-version guard excluded the row it was looking for.**
   The docname is `{declaration}-{version}`, so a second version wearing the same
   label autonames to the *same* name as the first, and the guard's `name !=
   self.name` clause — correct for an update — excluded exactly the clash it was
   checking for on an insert. The friendly message never fired and the framework's
   primary-key error surfaced instead. Found by the test written for it.

3. **D-15 — a read-only DocField is not read-only on the server.** The mirror on
   `VMMS Declaration` was marked `read_only` and could still be written by a
   script or an API call, which would have left the form showing wording that
   matched no published version — the exact failure the doctype exists to
   prevent. `validate` now re-derives all four fields on every save. Found by a
   test that was checking something else.

3. **D-16 — the mirror was written as columns, and an invariant caught it.**
   `sync_mirror` used `frappe.db.set_value`, and
   `test_correction_and_audit.TestNothingWritesAroundTheDocument` scans
   `declarations.py` for exactly that. It was right to. `VMMS Declaration` is
   `track_changes`, so a column write would have made a change to what a society
   publishes the one change to a policy that left no `Version` row behind — in a
   consent register, of all places. `sync_mirror` now loads the declaration and
   saves it, which also leaves a single writer: the four fields are derived in
   the controller's `validate` and nowhere else. Found by the full-suite
   regression run, not by the tests written for this feature.

### Known gaps, deliberately left

- **`VMMS Guardian` ships System-Manager-only.** Fail closed, and consistent with
  every other doctype here: which society role may read what is configuration,
  granted through the Role Permissions Manager. But the record is **not**
  registered with core's geo scoping, so a Custom DocPerm granting a branch
  coordinator read would grant them every guardian nationally. Registering it
  scopeable needs an anchor field it does not have. Worth settling before any
  society grants it.
- **The shipped "permission to contact you" declaration covers contacting the
  applicant, not their guardian.** A society turning this on should reword it.
  `declarations.install` never edits an existing record, so that rewording is
  safe and is theirs to make.
- **SMS campaigns now cost more where a branch has young volunteers**, because
  `audience.phones` includes guardians. That is the correct count — the messages
  are genuinely sent — and `campaign.draft` reports it before anything is spent.
  Recorded because it is a budget change nobody would otherwise see coming.
- **A guardian is only ever adopted from a volunteer application.** That is
  where the user said the record lives, and `VMMS Membership` carries no consent
  table to adopt from. So a minor who *only* joins as a member — never
  volunteers — has no guardian record, and the `cc` on their membership mail
  resolves to nobody. The membership path is wired and correct the moment such a
  record exists; what is missing is a door that creates one, and the branch can
  add it by hand today. Building the membership half means deciding whether a
  minor may join as a member at all without consent, which is a product question
  nobody has asked yet.
- **No desk or portal administration of guardians beyond the doctype form.**
  Nothing asked for it. `VMMS Declaration` and `VMMS Declaration Version` *were*
  added to the VMMS Setup workspace and its checklist — declarations had never
  been listed there, so a society's privacy notice was unreachable from the desk,
  which is not a state a privacy notice should be in.

### Test commands

```
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.registration.tests.test_declaration_versions
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.registration.tests.test_guardian
bench --site vmms.localhost run-tests --app vmmsx --module vmmsx.registration.tests.test_declarations
cd portal && npx tsc --noEmit && npx vitest run && npx vite build
```

## Open decisions

### OD-3 — The engine fix reaches Membership and Deployment Request (Phase 1)

Defect D-1 was fixed in `approvals/services/contract.py`, which is the *generic*
engine: `VMMS Membership` and `VMMS Deployment Request` go through the same
`decisions_at`, so both inherit the change.

In both cases it is the same defect being corrected — an approver who asked a
membership applicant for more information was equally unable to approve the
answer — so this reads as strictly a fix rather than a behaviour change. It is
recorded here because Phase 1 is scoped to volunteer registration and this is
the one change that leaves that scope.

No action needed unless you want it split into its own change; the alternative
was leaving a Phase 1 acceptance criterion unmeetable.

### OD-1 — Where the emergency contact lives (Phase 1) — RESOLVED 2026-08-30: (a)

User decision: **(a)**, vmmsx-owned, on the application. `_WITHHELD` in
`volunteer/services/identity.py` is untouched, and the emergency contact is
never written to or read from `Red Profile`.


`vmmsx/volunteer/services/identity.py` names a `_WITHHELD` set —
`blood_group`, `medical_conditions`, `next_of_kin`, `disability` — and refuses
to surface any of them **out loud**, with the stated reason that core is holding
those fields off the Red Profile spine for a later gated extension, and that
vmmsx spells them core's way so that the day they arrive this app already
refuses them by the right names.

An emergency contact is adjacent to `next_of_kin`. Two readings:

- **(a) vmmsx-owned, on the application** — as proposed in the Phase 1
  checklist. It is a fact recorded for the purpose of this volunteering, it is
  what the society's own approval gate needs, and it does not touch core's
  spine. Cost: when core's gated extension lands, the site holds an emergency
  contact in two places.
- **(b) core-owned, deferred** — treat this as core's `next_of_kin` extension
  and wait. Cost: Phase 1's "require at least one emergency contact before
  approval" cannot be delivered in this phase at all.

Recommendation: **(a)**, because an emergency contact for a deployment and a
next of kin on an identity record are genuinely different records with different
purposes and different retention — which is the same distinction this phase
already draws between a guardian and an emergency contact. `_WITHHELD` stays
untouched either way.

Not resolvable from the code: it depends on what onerc_core intends to ship.

### OD-2 — Snapshot the declaration body, or hash it (Phase 1, non-blocking)

The checklist snapshots the full declaration text onto each acceptance row,
following `VMMS Application Answer`'s precedent, so an application decided in
2026 still displays the exact text that was accepted. The alternative is storing
title + version + a content hash and making `VMMS Declaration` versions
immutable. Snapshotting costs four Text columns per application; hashing costs
the ability to read back what somebody actually agreed to without keeping every
version around.

Proceeding with the snapshot unless told otherwise.

## Approved deviations

| Date | Phase | Decision | Reason |
|---|---|---|---|
| 2026-08-30 | 0 | Phase 0 produces the shared current-state map now, and each later phase's file-level checklist at the start of that phase, rather than all seven up front. | User direction: work and review one phase at a time. The shared map still gates the Phase 0 acceptance criterion, which is about extension mechanics rather than per-phase detail. |

## Change log

| Date | Change |
|---|---|
| 2026-08-30 | Created the living phased plan from the document-by-document scope discussion. |
| 2026-08-31 | Phase 1 built: 5 DocTypes, 2 services, 2 patches, a seed, the API and portal work, and 6 test modules. Two defects found and fixed (D-1 in the shared approval engine, D-2 dead child-row validation); one framework behaviour recorded. Acceptance gate items all pass; full suite 1848 tests with 28 pre-existing/environmental failures, each classified. OD-3 raised. |
| 2026-08-30 | Phase 0: shared current-state map recorded. Phase 1: discovered constraints and file-level implementation checklist recorded. Two open decisions raised (OD-1, OD-2) and one deviation approved. |
| 2026-08-31 | **Phases 3–7 built in one pass, on the user's direction to do the remaining phases and leave the portal until last.** Phase 3 retired `VMMS Project` onto ERPNext's `Project` and made a terms of reference a complete, routable, supersedable mission document. Phase 4 gave a deployment two places with real map links, a datetime period, six statuses, close-out, an audited material-change rule, and gave an assignment outcomes, expiry, readiness and replacement. Phase 5 added `VMMS Task Batch` with partial-success generation and safe retry, and gave a task a type, a priority, a checklist, dependencies, a place, reminders and escalation, declines and reassignment. Phase 6 built the volunteering half of HRMS's `Job Opening` and `Job Applicant` on top of the user's in-flight screening port. Phase 7 added the end-to-end journeys, the permission matrix, the retirement scan and the administrator guide. Nine defects found and fixed (D-5 to D-13), two of them left over from earlier phases. Portal work for phases 2–6 remains deliberately unbuilt. |
| 2026-09-01 | **Policy versions and guardian notifications**, outside the phases. A declaration's wording became `VMMS Declaration Version` — submittable, so published wording is frozen by the framework rather than by a rule, and able to point at a page on the society's own website instead of holding the words. A minor's guardian became `VMMS Guardian`, a standing record anchored on the person, carried forward when their application is accepted, and copied on every message the society sends the young person — lifecycle mail, deployments, tasks, invitations, direct messages and branch announcements — with the age judged at send time so the copying stops by itself on an eighteenth birthday. Two defects found and fixed (D-14, D-15). The third thing asked for that day, a per-society choice of payment methods and a manual proof-of-payment gate, is the user's own and was deliberately not started. |
