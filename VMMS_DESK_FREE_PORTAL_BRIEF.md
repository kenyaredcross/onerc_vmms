# Design brief — a vmmsx web portal that replaces the Frappe desk

You are designing the complete interface for **vmmsx**, a volunteer and member
management system that a Red Cross or Red Crescent National Society runs itself
on. It is a Frappe (v16) application with a React single-page app in front of it.

Today roughly two thirds of the product has a purpose-built web interface, and
the remaining third — nearly all of it configuration and setup — can only be
reached through **Frappe's desk**, the framework's generic auto-generated admin
UI (list view / form view / workspace tiles). The desk is capable but it is
developer furniture: it exposes doctype names, link fields, child-table grids,
naming series and permission errors to people whose job is running a volunteer
branch in Dar es Salaam.

**Your job: design the screens that make the desk unnecessary.** Every person
who works for the society — from the national administrator setting the system
up on day one to a sub-branch coordinator approving an application on a laptop
with two bars of signal — should be able to do their entire job inside the web
portal, and should never be handed a `/app` link.

Read the whole brief before you start. Sections 1–4 are context. Section 5 is
the gap you are designing into. Sections 6–9 are the constraints and the
deliverables.

---

## 1. The product

A National Society uses vmmsx to take somebody from a stranger on its website to
a volunteer it has trained, placed and sent into the field — and to keep the
record of it. Recruitment, application, geographically-routed approval,
deployment to operations, hours, stipends, membership payments, and branch
communication, all in one system, themed and scoped to that society.

It is two-sided, and both sides are primary:

- **Coordinators** (society staff, frequently volunteers themselves) work a
  manager console. Each is bound by a *Geo Assignment* to one node of the
  society's geographic tree — national → branch → sub-branch — and sees only the
  records and sections that scope allows. Desk or laptop in a branch office,
  often on an intermittent connection.
- **Prospective volunteers and members** arrive at the public landing page or a
  shared deep link, on a phone as often as a computer. They complete a
  multi-step application that saves as a draft and can be resumed, then follow
  it through review.
- **Active volunteers and members** are signed into a portal. They accept or
  decline deployment invitations, complete tasks, log hours, manage a membership
  and its payment, record when they are available, browse opportunities and
  events, and show a membership card at a gate.

### The mechanisms that make it what it is

- **Geographic scope is the access model.** A person's Geo Assignment on a
  shared geo tree bounds what they can approve, read, see, and reach with an
  announcement. The frontend names no roles: a console section appears because
  the server says the person may *read* the records behind it. A society
  configures its own approval ladder — how many rungs, at which geographic
  levels — with no code.
- **The society owns its words and its intake.** Every string on the public site
  is a content block an administrator rewrites in place. The application form's
  questions and tabs are records the society builds in a form builder. Neither
  needs a developer or a deployment.
- **Multi-tenant by National Society.** Identity — name, marks, colours — is read
  from a settings record on every render.
- **The Terms of Reference is the contract.** A submittable TOR freezes its
  wording at the moment a volunteer accepts an assignment; there is no separate
  agreement document.
- **Registers first, maps second.** Coordination is a table of who does what
  where, consistent with IFRC GO and OCHA cluster practice. A map is a secondary
  rendering of that table, never the primary surface.

### Operating context

- **A federated organisation.** A national headquarters, branches beneath it,
  sub-branches beneath some of those. Many branches have no sub-branch, so an
  approval ladder's lower rungs are frequently unstaffed and escalate upward.
- **Field conditions are the normal case.** Card verification is opened on a
  phone camera's browser at a gate. The join wizard is completed on phones on
  poor connections. Low bandwidth and small screens are expected, not edge cases.
- **The application journey.** Draft → submit → stage-by-stage review (approve /
  reject / request more information) → active. "More information" returns the
  draft to the applicant to edit and resubmit.
- **The operations chain.** Project → Terms of Reference (the work, its
  methodology, its resources) → Deployment → one Assignment per person, each
  carrying its own assigned / pending / accepted / declined / withdrawn status.
- **Optional companion apps.** `onerc_core` is required and supplies the geo
  tree, geo assignments and society settings. `buzz` (events), `hrms`
  (opportunities board), `lms` (learning), `onerc_payments` (membership payment)
  and `onerc_sms` (SMS) light up when present and stay silent otherwise. Their
  own management screens are theirs; vmmsx links out rather than wrapping them.

### Vocabulary

| Term | Meaning |
| --- | --- |
| National Society | One national Red Cross / Red Crescent organisation. One deployment serves one. |
| Branch / sub-branch | Geographic subdivisions; the units coordinators are scoped to. |
| Geo Node / Geo Level | A place in the society's tree, and the tier it sits at. |
| Geo Assignment | The record binding a person to a node, carrying their scope. |
| Terms of Reference (TOR) | The definition of a piece of work and, once accepted, the volunteer's agreement to it. |
| Deployment | Putting volunteers to work against a TOR. |
| Assignment | One person on one deployment. |
| Stipend | A payment to a deployed volunteer, reported against attendance. |
| Coordinator | Society staff who admit and coordinate people within their geographic scope. |

---

## 2. The stack, and what is fixed

- **Backend:** Frappe v16. Data lives in doctypes; every action goes through a
  service layer and a whitelisted endpoint, never raw document insertion.
- **Frontend:** React + Vite SPA, TypeScript, Tailwind, React Router, served
  from the Frappe site. Three route families: public, `/…` portal, `/admin/…`
  console.
- **Authentication stays Frappe's** — password, magic link, OAuth, 2FA. It is
  not reimplemented in React. A custom split-panel sign-in / sign-up page and
  the password-reset pages are server-rendered HTML outside the SPA.
- **The server decides what a person may see.** No role name appears anywhere in
  the frontend. One endpoint returns the list of console sections the viewer may
  open; the layout draws exactly those. Every action is authorised again by the
  endpoint that performs it — drawing a button is a convenience, never a grant.
- **Design your screens against this model.** A screen that needs "only admins
  see this" gets it from the server's section list, not from a role check you
  invent in the UI.

---

## 3. The design system in place

Do not start a new visual language. Extend this one.

**Palette — the "grey shell".** A neutral chrome with one action colour.

```
shell            #ECECEC   the outermost ground
surface          #F5F5F5   cards and panels
authority        #24272C   the console's dark chrome  (deep #1B1E22, soft #32373E)
ink              #17191D   primary text
muted            #737982   secondary text
slate-strong     #3F444B   slate-faint #9AA0A8
blue             #155EEF   the single action colour  (hover #1150D0, press #0E42A8)
blue-soft        #EDF3FF   blue-line #B9CDF8
danger           #B4232C   soft #FFF1F2   line #EFAFB4
warning          #8C5A00   soft #FFF8E8   line #E2C37F
success          #1F6B45   soft #EAF6EF   line #A8D5BC
hairline         #E1E3E6   soft #EDEEF0   strong #D5D8DC
```

**Type.** *Schibsted Grotesk* for display, *Public Sans* for body, both from
Google Fonts with a `system-ui` fallback stack. The scale in use:

```
hero      70px / 800 / 0.98 / -0.045em      display   29px / 500 / 1.15
headline  17px / 800 / 1.2                  title     13.5px / 700
metric    30px / 500 / 1                     body      13.5px / 400 / 1.55
body-read 15px / 400 / 1.75                  label     10px / 600 / 0.14em caps
```

**Radii.** control 12px · card 18px · panel 24px.

**Brand commitments — these are not negotiable.**

- **The Red Cross / Red Crescent emblem is never drawn, recoloured or shipped.**
  It is protected under the Geneva Conventions and national law. The product
  ships a neutral geometric mark; a society uploads its own emblem to its
  settings. Never put a red cross or crescent in a mockup.
- **Blue is the action colour; red is destructive only.** No decorative red
  anywhere. Blue means "act on this" or "you are here" and nothing else carries
  that hue — decorative tints deliberately exclude blue so it never dilutes.
- **The society's identity has one home.** Name and marks come from the settings
  record on every render. A site whose settings have never been saved shows a
  neutral mark and no name rather than borrowing another society's.
- **Voice on public and portal screens: say the short true thing, or say
  nothing.** No framework or API errors, exception classes, endpoint names or
  internal document identifiers on any screen a member of the public sees. No
  copy that narrates the screen back to the person on it.
- **Accessibility: WCAG 2.1 AA.** A visible focus ring is global, not
  per-component. Colour is never the only carrier of state — every status badge
  carries text and a dot as well as a hue.

---

## 4. What already exists — do not redesign these unless asked

### Public, no account required

| Screen | Route | What it is |
| --- | --- | --- |
| Landing | `/` | The society's public page. Every string is an editable content block. |
| Join wizard | `/join` | Multi-step, resumable application. Volunteer, member, and "I already hold a membership" paths. Society-built questions and tabs. |
| Branch finder | `/locations` | Published branch locations, list plus a map. |
| Card verification | `/verify`, `/verify/:token` | Where a scanned membership card lands. Guest by design — the person at the gate has no account. The lightest screen in the app. |
| Sign in / sign up | server-rendered | Split-panel page outside the SPA, plus forgot / reset / set password and email-link pages. |

### Volunteer and member portal (signed in)

`/dashboard` · `/tasks` · `/deployments` (invitations and assignments) ·
`/availability` · `/hours` · `/membership` · `/profile` · `/notifications` ·
`/events` and `/events/:name` · `/calendar` · `/opportunities` and
`/opportunities/:name` · `/stories` and `/stories/:slug` · `/training` (a
link-out to the LMS).

Chrome: an account menu, a notification menu, and an availability control with
an inline editor and a nudge, all in the portal header.

### Manager console (`/admin`)

| Section | Routes |
| --- | --- |
| Overview | `/admin` — waiting-on-you, SLA breaches, registers in scope, 12-month registration trend, geographic coverage, needs-attention |
| Review queues | `/admin/queue/volunteers`, `/admin/queue/members`, `/admin/queue/:kind/:name` (the decision screen) |
| People | `/admin/people`, `/admin/registry/members`, `/admin/registry/volunteers`, `/admin/registry/:kind/:name` (the per-person dossier) |
| Operations | `/admin/projects(/:name)`, `/admin/deployments` hub, `/deployments/terms(/:name)`, `/deployments/ongoing`, `/deployments/past`, `/deployments/new`, `/deployments/:name`, `/deployments/requests`, `/deployments/documents` |
| Tasks | `/admin/tasks` — assignment, batches, sign-off, escalation |
| Stipends | `/admin/stipends` — progress reports and payment forms |
| Events | `/admin/events` — browses what Buzz has published; every call to action navigates out to Buzz |
| Analytics | `/admin/analytics` |
| Communication | `/admin/communication/:channel/:view` — announcements and SMS drafts, audience preview, composer |
| Page content | `/admin/content` — edit the public site's words in place |
| Form questions | `/admin/questions` — the application form builder |

---

## 5. The gap — everything that still needs the desk

**This is the brief.** Each item below is a real doctype or framework surface a
society's staff must use, with no purpose-built screen today. Group them, give
them an information architecture, and design them.

### 5.1 Society identity and configuration

- **National Society Settings** (a single record): society name, marks and
  emblem upload, colours, the bindings that name which role holds each scope
  (membership, volunteer, deployment, deployment request, branch transfer,
  stipend report, stipend payment, announcement, task, branch location), and
  feature toggles. This one record decides who can do anything in the product,
  and it is edited today in a generic form with thirty-odd link fields.
- **Society terminology** — the society's own words for the product's concepts.
- **Feature toggles** — which optional surfaces are on.
- **Affiliation types** and **identification types**.

### 5.2 Geography and access — the most important gap

- **Geo Level** — the tiers of the society's tree (national, region, branch,
  sub-branch, …), their order and their names.
- **Geo Node** — the tree itself. Creating, renaming, moving, retiring nodes.
  Note: force-deleting a node leaves dangling references that surface as
  errors during registration, so deletion needs a designed safe path.
- **Geo Assignment** — binding a person to a node. This is *the* access control
  act in the whole product, and it is performed today by creating a link record
  in the desk.
- **Staff onboarding** — inviting a colleague, giving them a scope, seeing who
  holds what where, and revoking it. There is no screen for this at all.

### 5.3 The approval ladder

- **Approval Workflow**, with its stages and anchor levels as child rows. A
  society defines, per record type, how many rungs an application climbs and at
  which geographic level each rung sits, with SLA windows. It is a
  builder-shaped problem presented today as a nested grid.
- **Approval Decision** history — who decided what, when, and why.

### 5.4 Registration configuration

- **Declarations, Declaration Versions (submittable) and Acceptances** — the
  codes of conduct and consents an applicant signs, versioned so an acceptance
  points at exact wording. Publishing a new version is a consequential act with
  no screen.
- **Guardians, guardian consent and verification methods** — the flow for a
  minor applicant.
- **Required documents** and **supporting document types** — what an applicant
  must attach.
- The **form builder** exists at `/admin/questions`; check it covers tabs,
  ordering, conditional questions and per-audience variants, and extend it.

### 5.5 Catalogues — the reference data every form picks from

All of these are desk-only list views today. They want one coherent, learnable
place, not sixteen separate screens:

- Membership types, their benefits and their pricing
- Skills · motivations · languages
- Certification types · certifications issued · course mappings (LMS course → certification)
- Professions · personnel licence types · personnel licences
- Task types
- Time-log categories
- Announcement types
- TOR methodologies
- Template categories and **templates** (email, SMS and document bodies, with
  variables and a preview)

### 5.6 Operational screens that were never built

- **Branch transfers** — endpoints exist to request, read and cancel a transfer;
  there is no console screen anywhere in the product.
- **Hours review** — a volunteer logs time in the portal; no coordinator screen
  reviews or approves it.
- **Certification issuing** — visible on a person's dossier, issued only in the desk.
- **Volunteer suspension, reinstatement and exit** — endpoints exist; the
  console has no considered flow for them.
- **Membership renewals, cancellations and expiry** oversight, and the payment
  record that `onerc_payments` owns.
- **Branch locations (Places)** — the addresses the public branch finder shows.
- **Content surfaces** — blocks are editable in place, but creating and
  publishing a *surface* is desk-only.
- **Notification records and lifecycle** — what the system sent and to whom.

### 5.7 Framework surfaces a society administrator still needs

Design human equivalents for these; do not simply link to the desk.

- **Users** — create, deactivate, reset a password, see who has signed in.
- **Email** — outgoing account setup and health, the send queue, failures and
  retries. A society whose email silently stops is a society whose applicants
  never hear back.
- **SMS provider** status and credit, where `onerc_sms` is installed.
- **Print formats and letter heads** for certificates, cards and TOR documents.
- **Import and export** — bringing an existing volunteer register in from a
  spreadsheet is the first thing every society does, and today it is Frappe's
  generic Data Import.
- **Audit and activity** — who changed what, in human sentences.
- **Scheduled work** — whether the nightly jobs (expiry, reminders, digests) ran.

**Boundary, stated honestly:** true infrastructure — server backups, error logs,
bench commands, the site's own configuration — stays with whoever administers
the server, and is out of scope. The target is that **no National Society
employee, in any role, needs the desk to do their job.** If you find something
in the list above that you believe genuinely belongs to a systems administrator
rather than a society administrator, say so and argue it rather than silently
dropping it.

---

## 6. What to design

Produce a complete target information architecture and the screens under it. At
minimum:

1. **A settings and administration area** the console does not have today —
   its top-level shape, its navigation, and how a coordinator with narrow scope
   sees a subset of it without the interface ever mentioning a role.
2. **Every screen in section 5**, at a fidelity that could be built from:
   layout, hierarchy, real-looking (invented, plausible) content, all
   interactive states.
3. **The additions to the existing console navigation** that make the new
   sections findable without burying the daily work of a coordinator, who opens
   the queue and the registers many times a day and settings twice a year.
4. **A first-run experience.** A freshly installed site has no geo tree, no
   roles bound, no membership types, no questions and no content. Today that is
   a desk onboarding checklist. Design the sequence that takes a new
   administrator from an empty site to one that can accept its first applicant.
5. **The patterns the new screens need** and the existing system lacks — a tree
   editor, a rule/ladder builder, a template editor with variable insertion, an
   import mapper, a person-picker with scope awareness, a versioned-document
   publisher. Specify each as a reusable component, not as a one-off.

### Every screen must specify

- **Empty, loading, error, partial-permission, and offline/slow states.** The
  partial-permission state matters more here than in most products: a
  sub-branch coordinator opening the geography screen sees their own subtree and
  nothing above it, and that must read as normal rather than as a failure.
- **Mobile behaviour.** Coordinators use laptops, but a branch officer will open
  the console on a phone. Registers must degrade to something usable.
- **Destructive-action handling.** Retiring a geo node, superseding a
  declaration version and revoking a geo assignment all have consequences the
  interface must make legible before the click, not after.
- **The record behind it.** Name the doctype and the action. Where the endpoint
  to support your design does not exist yet, say so explicitly — a flagged gap
  is useful, an invented endpoint is not.

---

## 7. Rules

- **No emblem.** Never a red cross or red crescent, in any mockup, at any size.
- **No society's name hardcoded.** Kenya, Tanzania and Gambia exist as demo
  seed data; they demonstrate, they do not define. Use a placeholder society.
- **No invented evidence.** No society has gone live on this software. There are
  no testimonials, no real volunteer counts, no benchmarks, no pricing, no case
  studies. Do not put any in a mockup.
- **No role names in the interface.** Not in labels, not in empty states. The
  server says what a person may open; the screen never explains why in terms of
  a role.
- **Do not propose embedding the desk.** An iframe of a desk form is not a
  design. If a surface genuinely cannot be replaced, say so and argue it.
- **Do not redesign section 4's screens** unless the new architecture forces a
  change — and if it does, say which and why before you change them.
- **Extend the design system in section 3.** New tokens are allowed where the
  system genuinely lacks one; state each addition and its reason.

---

## 8. Deliverables

1. **An IA map** of the whole product after the change — public, portal,
   console, settings — showing what moved and what is new.
2. **A screen inventory**: every screen, its route, its audience, the record
   behind it, and whether it exists today, is being extended, or is new.
3. **Designs for the new screens**, states included, at build-ready fidelity.
4. **Component specs** for the new patterns in section 6.5.
5. **A flagged list of backend gaps** — every place your design needs an
   endpoint or a field that does not exist.
6. **A sequenced plan**: what to build first so the desk becomes unnecessary in
   the order that removes the most pain per week of work. Assume the geography
   and access screens are the highest-value, and argue if you disagree.

## 9. How to work

Start by telling me your reading of the problem and the IA you propose, before
you draw anything. I would rather argue about the shape of the settings area for
an hour than receive forty polished screens hung off the wrong tree.

Where the brief is ambiguous, ask. Where you think it is wrong, say so — but
finish the work under a stated assumption rather than stopping.
