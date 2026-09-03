# VMMS — administrator guide

What somebody has to set up before this app does anything, in the order it has
to be done, and what to look at when a thing that should have happened did not.

It covers the surfaces built in phases 1–7 of
`VMMS_PHASED_IMPLEMENTATION_PLAN.md`. Everything here is Desk and server:
**the volunteer portal is deliberately out of scope for this round** and is
listed under "Known deferred items" at the end.

---

## 1. The shape of the thing

Five apps, and the boundaries between them are load-bearing:

| App | Owns |
|---|---|
| `frappe` | users, files, notifications, scheduler |
| `onerc_core` | identity (`Red Profile`), geography (`Geo Node`), access (`Geo Assignment`), society configuration (`National Society Settings`) |
| `erpnext` | `Company`, `Project`, `UOM`, `Currency` |
| `hrms` | `Job Opening`, `Job Applicant`, `Designation`, `Department` |
| `vmmsx` | volunteering, membership, deployment, tasks — and the extensions it adds to the four above |

**vmmsx never edits another app's source.** Everything it adds to `Project`,
`Job Opening`, `Job Applicant`, `Identification Type` and
`National Society Settings` is a Custom Field installed on every `bench migrate`
by an idempotent installer in `vmmsx/setup/`. `vmmsx/tests/test_retirement.py`
fails the build if one of them ever becomes a standard field.

---

## 2. Setting a site up, in order

Each step depends on the one before it. Doing them out of order is the commonest
cause of "the screen is empty and says nothing".

### 2.1 Geography

Create the `Geo Level` ladder and then the `Geo Node` tree, in core. A society's
ladder is its own — region/branch/post, province/district/ward, whatever it
uses. **No level name appears anywhere in vmmsx's source**, and a test walks the
AST to keep it that way.

### 2.2 Roles

`vmmsx.setup.core_roles.install` runs on every migrate and creates the six every
society needs: Volunteer Approver, Membership Approver, Deployment Manager,
Volunteer, Member, and the role a brand-new account holds. Rename them freely —
nothing in the app names one; every reader reads a **setting**.

### 2.3 The scope roles — the step most often missed

`National Society Settings` carries one field per scoped register:

| Setting | Governs |
|---|---|
| `vmms_volunteer_scope_role` | `VMMS Volunteer` |
| `vmms_membership_scope_role` | `VMMS Membership` |
| `vmms_deployment_scope_role` | `VMMS Deployment`, `VMMS Deployment Assignment`, and **ERPNext `Project`** |
| `vmms_deployment_request_scope_role` | `VMMS Deployment Request` |
| `vmms_branch_transfer_scope_role` | `VMMS Branch Transfer` |
| `vmms_task_scope_role` | `VMMS Task` and **`VMMS Task Batch`** |
| `vmms_branch_location_scope_role` | `VMMS Branch Location` |
| `vmms_announcement_scope_role` | `VMMS Announcement` |

**Every one of them ships empty, and empty means closed.** Core fails closed
deliberately: until a society names the role, nobody but an unrestricted user can
read those registers. That is the correct default for records holding personal
data, and it is the single most common reason a newly installed site shows a
coordinator an empty list.

> If a register is empty for a coordinator who should see it, check this table
> first, then their `Geo Assignment`, then whether they hold the role at all.
> `frappe.get_list` refuses before geo scoping is ever consulted if the role has
> no Role Permission on the doctype — which is what
> `vmmsx.staff.services.permissions` installs on migrate.

### 2.4 Geo Assignment

One row per person per role per node, with `is_active` and an optional validity
window. Authority is **the role and the assignment together**: stripping the role
empties the scope however many live rows remain.

Appointing somebody re-syncs every open approval queue immediately — see
`approvals/services/repair.py`. Nobody has to wait for a migrate.

### 2.5 Company

ERPNext requires one on every `Project`. Create the national society as a
`Company`. It is **not** the same axis as the Geo Node: one Company, many
branches. Both are mandatory on a project and neither substitutes for the other.

### 2.6 Approval workflows — optional, and optional per doctype

A `VMMS Approval Workflow` record governs one doctype. Create one only where the
society wants a decision recorded:

* `VMMS Volunteer Application`
* `VMMS Membership`
* `VMMS Deployment Request`
* `VMMS Terms of Reference` *(new in phase 3)*

**With no workflow, the work still happens.** A terms of reference is submitted
directly by anybody with submit permission; a deployment request whose terms say
`routed` is fulfilled directly and the record says `approval_unconfigured` so the
absence is visible rather than inferred. Configuration that has not been done
never blocks work — it only means nobody's decision is recorded.

The workflow's `geo_node_field` must be a mandatory Link to `Geo Node` on the
governed doctype. This is why `VMMS Terms of Reference.geo_scope` is mandatory.

### 2.7 Optional: geocoding

Add to `site_config.json`:

```json
"vmms_geocoding_url": "https://nominatim.openstreetmap.org/search"
```

With nothing configured, geocoding is simply off: coordinates are placed by hand
and maps and directions still work. **Nothing geocodes on save**, ever — it is an
explicit act, and every failure comes back as a sentence rather than an error.

---

## 3. Configuration by module

### Volunteer registration (phase 1)

* `Identification Type` — tick `vmms_is_required_for_volunteers` on the documents
  an applicant must produce, `vmms_requires_attachment` where a number is not
  enough, and `vmms_minimum_age` for documents that do not exist for a child.
  All empty = nothing required.
* `National Society Settings.vmms_minor_age` — the age of majority. **Empty means
  nobody is a minor** and the guardian rules never fire.
* `VMMS Declaration` — the statements an applicant agrees to, versioned. The
  wording is snapshotted onto each acceptance, so a 2026 application still shows
  the 2026 text.

### Membership proof (phase 2)

Nothing to configure. An applicant's claimed dates are never official: an
approver records the **verified** dates and the membership refuses approval
until they do. A membership proved to have expired is recorded Expired and never
made Active.

### Programmes and mission documents (phase 3)

* Programmes are ERPNext `Project` records. `vmms_geo_node` is mandatory and a
  coordinator may only file one where their own access reaches.
* A `VMMS Terms of Reference` cannot be submitted until it says: a project, a
  period, a place, a background, at least one objective, output, stakeholder and
  itinerary entry, and either resource lines or the tick that says it needs none.
* Submitted terms are frozen. To respecify work people are already deployed on,
  **supersede** rather than amend: a new document with a link back, leaving what
  everybody agreed to alone.

### Deployments (phase 4)

* Six statuses: Planned, Active, Suspended, Completed, Closed Out, Cancelled.
  Suspended is a pause; Closed Out is Completed plus optional paperwork and waits
  for nothing.
* Once anybody has been invited, changing the date, the place, the coordinator or
  the terms **requires a reason written for that change** and notifies everybody
  still on it.
* Invitations carry the meeting point, the deployment point, the schedule, travel
  notes and both contacts. Set an "Answer by" date to have unanswered invitations
  expire on the daily sweep; leave it empty and the question stands.

### Tasks (phase 5)

* `VMMS Task Type` is the society's own vocabulary — nothing branches on it.
* A required checklist item blocks a submission. An unfinished dependency blocks
  a start unless a manager writes an override reason. Nothing else gates a task.
* `Remind every (days)` is zero by default and sends nothing. Set it, and the
  daily sweep nudges the holder of overdue work and then escalates to
  `Escalate to` if there is one.
* A `VMMS Task Batch` is an administrative grouping. Preview it, generate it, and
  read the per-person result. Generating again resolves only what is unresolved
  and never duplicates. Once generated, the brief and schedule are frozen —
  adding people and generating again is how a batch grows.

### Openings and applications (phase 6)

* Set `vmms_purpose` on each `Job Opening`. **Employment** keeps HRMS's own
  public form untouched; **Volunteer** is applied for through the portal by an
  approved active volunteer.
* Screening questions lock once anybody has answered: wording and order stay
  editable, the set does not.
* An accepted application is turned into work by an explicit act —
  `convert_application` — which produces a deployment assignment where the
  opening names a deployment and a task where it does not, once.

---

## 4. Scheduled jobs

All daily, all idempotent, all safe to run twice:

| Job | What it does |
|---|---|
| `approvals.services.sla.sweep` | escalates approvals past their stage's SLA |
| `approvals.services.engine.expire_stale` | expires applications nobody decided |
| `member.services.membership.expire_lapsed` | moves Active memberships past their expiry to Expired |
| `deployment.services.transfer.apply_due` | applies branch transfers on their effective date |
| `approvals.services.repair.resync_pending` | backstop for authority that changed without a doc event |
| `deployment.services.assignment.expire_overdue` | expires unanswered invitations past their answer-by date |
| `task.services.task.chase_overdue` | nudges overdue tasks, then escalates |

If none of them is running, check the scheduler is enabled for the site
(`bench --site <site> enable-scheduler`).

---

## 5. Troubleshooting

**A register is empty for somebody who should see it.**
In order: the scope-role setting (§2.3), their `Geo Assignment`, whether they
hold the role, and whether the role has a Role Permission on the doctype.
Core logs every unresolvable scope role to the Error Log under
"Scopeable doctype role could not be resolved".

**"Geo Node GEO-xxxxx does not exist" on a register.**
A record is anchored to a node that was force-deleted. Registers show the
docname rather than failing; maps drop the row. Re-create the node or re-anchor
the record.

**A terms of reference will not submit.**
It is not finished, or the society routes them and it has not been approved. The
refusal lists everything missing at once.

**A deployment will not save: "Say why it changed".**
Somebody holds an open assignment on it, and a material field moved. Write a
reason — a fresh one, not the one already in the field.

**A task will not be handed in.**
A required checklist item is unticked. The refusal names them.

**An opening will not save: "Already answered".**
Somebody has applied. Reword or reorder questions freely; to ask something new,
post another opening.

**A `TimestampMismatchError` while scripting a whole journey.**
A deployment's feed is a child table on the deployment, so roster events write
the deployment's row. A script holding one document across several operations
must `reload()` between them. Requests never see this — they load per request.

**Applications, tasks or invitations produce no notification.**
The person has no login behind their `Red Profile`. Everything in this app
notifies quietly where there is nowhere to send.

---

## 6. Known deferred items

Recorded so they are not mistaken for oversights. All of these are decisions
somebody made, not gaps somebody missed.

* **The volunteer portal.** Everything in phases 2–6 is server-side and tested;
  the portal renders phases 3–6 not at all, and phase 2's membership-proof form
  is not built. This was the user's explicit direction: Desk first, portal last.
  The one that blocks *use* rather than polish is the membership-proof verify
  control — until it exists, a self-service proof is approved from the Desk form.
* **User/Geo Assignment and staff-access redesign.** Paused; must not be
  implemented until separately approved.
* **Auto-grading of screening questions.** The scoring fields on
  `Job Application Screening Questions` are editable and nothing reads them; the
  engine was not part of the port.
* **Budget roll-up.** A terms of reference costs its own resource lines and
  nothing reconciles that across a project or against stipend spend.
* **A duplicate *active* membership of the same plan and branch** is refused only
  on the proof path. The gateway path can still create one; see the phase 2
  record.
* **Private screening and referee records**, identity-change approval gates, TOR
  types, deployment requirement records, age and gender filters, allowances, and
  mandatory close-out reconciliation — all explicitly excluded.
