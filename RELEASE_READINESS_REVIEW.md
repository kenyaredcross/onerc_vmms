# VMMSX release readiness review — 22 September 2026

## Verdict

**Do not treat this working tree as ready for a public launch yet.** This is a read-only code review plus local static and portal tests, not a successful end-to-end rehearsal on a deployed site. Application code was not changed. The findings below are ordered by user impact; each needs a fix and a repeatable regression check before release.

The repository already contained uncommitted application changes when this review began. Findings describe that current working tree.

## Confirmed issues

### P0 — An expired membership can still verify as current and yield a certificate/card before the daily expiry job runs

**Journey:** member, public card verifier, gate staff. **Evidence:** `vmmsx/member/services/membership.py:540-558` explicitly recognises the interval after `valid_to` but before `expire_lapsed()` updates the stored status. Yet `vmmsx/member/services/membership.py:814`, `vmmsx/member/services/card.py:130-131`, and `vmmsx/member/services/certificate.py:328-343` use the stored `membership_status == Active` without the date check. `vmmsx/api/cards.py:256-279` selects the stored Active record for the member card. `vmmsx/api/member.py:830-845` exposes a certificate button under the same condition.

**Reproduce:** create a term membership that is stored Active, let its `valid_to` pass, and call the membership list, public card verification, and certificate/card download before the daily scheduler runs. These paths still report it active/current and allow a new certificate or card. The existing `effective_status()`/`is_current()` functions show the intended date-aware answer.

**Impact:** a lapsed member can present a card that verifies as current. This is a correctness and trust problem at the gate, especially if the scheduler is delayed or disabled.

### P1 — Any old non-active membership blocks joining through the membership page

**Journey:** returning member. **Evidence:** `portal/src/portal/Membership.tsx:74-75` defines `pending` as every row where `!row.is_active`; lines 150-161 replace every Join action with “Application in” whenever `pending.length > 0`, and lines 267-280 describe all those records as awaiting payment or approval. The backend has distinct Draft, Awaiting Payment, Awaiting Approval, Expired and Cancelled states (`vmmsx/member/services/membership.py:57-62`).

**Reproduce:** sign in as a person whose only membership is Expired or Cancelled, open `/portal/membership` (the SPA route is `/membership`), and inspect any offered plan. Join is unavailable, and the page wrongly says an application is in progress. A person may be able to reach `/join?path=member` by another link, but this page's primary path is blocked.

**Impact:** returning members cannot apply for a different membership type or branch from their account. The same wrong message appears for expired/cancelled history.

### P1 — “Save & exit” can discard the current step

**Journey:** volunteer and member registration. **Evidence:** the top control in `portal/src/guest/Join.tsx:1848-1859` is a plain `Link` to `/dashboard`; it does not call `saveDraft` or `autosave`. Draft autosave runs only on a step change (`goTo`, lines 1531-1533), and explicit Save draft is a different button (around line 2287).

**Reproduce:** fill or change fields on the current wizard step, then press “Save & exit” without changing steps or pressing Save draft. The route changes immediately and those changes have not been posted. On the first step, the user may have no draft at all. The label promises the opposite.

**Impact:** applicants lose work, especially on a phone or unreliable connection. This also undermines the promised resumable application journey.

### P1 — Renewal hides the payment instruction and announces success before payment/approval

**Journey:** member renewal. **Evidence:** `portal/src/portal/Membership.tsx:426-436` ignores the response from `API.renewMembership` and always displays “Membership renewed.” The server creates a new membership and calls `membership.submit()` (`vmmsx/member/services/renewal.py:151-179`); `vmmsx/member/services/membership.py:154-212` can return a gateway `payment.message` while the new record awaits payment and/or approval. The first-time join wizard does display that message (`portal/src/guest/Join.tsx:1749-1758`).

**Reproduce:** renew a lapsed membership type with a fee using a payment method that returns instructions, such as bank transfer or a phone prompt. The portal drops the instructions and says the membership has been renewed, though the new membership may still be awaiting payment/approval.

**Impact:** members can miss the payment step and believe they are covered when they are not.

### P1 — The hours page promises every entry but silently stops after 30

**Journey:** experienced volunteer checking their service history. **Evidence:** `portal/src/portal/Hours.tsx:82-91` labels the list “Every entry” and sends `API.myTimeLogs` with no limit or pagination (lines 39-44). The endpoint defaults to `limit=30` (`vmmsx/api/volunteer.py:935-948`) and returns only `summary.recent`; `vmmsx/volunteer/services/timelog.py:397-447` limits that list while correctly counting all logs in the total. The page has no next-page action.

**Reproduce:** give one volunteer 31 verified time logs, open `/hours`, and compare the Entries total with the rows visible. The total is 31; only 30 entries can be inspected. Nothing tells the volunteer that an older entry is hidden.

**Impact:** a long-serving volunteer cannot audit their complete hours record from the portal despite the page promising it.

### P1 — Manager review history and returned cases vanish after a fixed window

**Journey:** coordinator reviewing applications at volume. **Evidence:** `vmmsx/api/approvals.py:233-278` caps the Closed and Changes bands at 200 records. The Changes query first takes the latest 200 *Draft* registrations, then filters those to returned applications; 200 newer first-time drafts can therefore hide a still-returned older case. `portal/src/admin/ReviewQueue.tsx:129-199` calls this endpoint once and offers no paging or search into older cases.

**Reproduce:** create over 200 closed applications in one scope and open the Closed band; older cases cannot be reached there. For Changes, return one application for more information, then create 200 newer drafts in the same scope; the returned case drops out of the band even though its state did not change.

**Impact:** managers lose access to review history from the console, and the Changes band can silently omit work needing follow-up. This limit will be reached quickly at the expected daily volume.

## Release gate and performance findings

### P1 — Local installed framework differs from the declared production target

`pyproject.toml` declares `frappe >=16.0.0,<17.0.0`, and `PRODUCT.md` describes Frappe v16. The available `vmms.localhost` development site reports **Frappe 17.x.x-develop** (with vmmsx and the optional companion apps installed). Passing checks on this site would not establish compatibility with the declared v16 target; conversely, a failure might reflect the v17 development build. Install and rehearse on the exact Frappe major/minor release intended for launch.

### P2 — Default parallel portal test command is unreliable

`npm run typecheck` passed. `npm test -- --reporter=dot` finished with **273 passed, 29 failed, 4 worker errors** across 26 files. Most failures were five-second timeouts across manager and join suites; some assertions also failed under that load. The join suite passed **61/61** in isolation, and the complete suite passed **302/302** when rerun with one worker and a 20-second timeout. That points to runner contention rather than 29 confirmed product defects. The default test command still fails as configured, so CI or release instructions need a repeatable green command.

### P2 — Volunteer hours endpoint does a growing number of database reads

`vmmsx/api/volunteer.py:935-948` returns up to 100 log rows; `_my_log_row()` at lines 980-1018 fetches the category and deployment title for each row, and `_deployment_title()` fetches deployment and TOR separately. This can add roughly two to three database reads per log on every `/hours` visit. This is a code-path performance risk, not a measured production slowdown. Measure with a volunteer who has 100 logs and consolidate reads if the query count is high.

### P2 — Geocoding suggestions can consume external quota for any signed-in user

`vmmsx/api/deployment.py:1799-1820` lets every authenticated account call `suggest_places`, though it is presented as a coordinator editing aid. There is no deployment permission or apparent request rate limit here. A normal volunteer account could trigger repeated provider lookups. Verify the provider's quota and rate controls; restrict use to the intended desk audience if this endpoint is billable or quota limited.

## Checks and limits

- `npm run typecheck` in `portal/`: passed.
- `npm test -- --reporter=dot` in `portal/`: 273 passed, 29 failed, 4 worker errors. Failures are not assumed to be product defects without isolation.
- `npx vitest run src/guest/Join.test.tsx --maxWorkers=1 --testTimeout=20000`: 61 passed, 0 failed.
- `npx vitest run --maxWorkers=1 --testTimeout=20000`: 302 passed, 0 failed.
- Cross-checked the 175 `vmmsx.api.*` method strings in `portal/src/lib/api.ts` against Python definitions and `@frappe.whitelist` decorators: none were missing. This checks names and exposure, not request/response compatibility.
- `ruff check vmmsx --output-format concise`: 39 lint findings, mainly tests and document generators; also `vmmsx/task/services/batch.py` and a deployment doctype controller. These did not identify a syntax failure in the reviewed journeys but leave the repository lint gate red.
- No live browser journey, payment gateway callback, email/SMS delivery, load test, migration rehearsal, or Frappe integration suite was completed in this review. Therefore it would be false to claim that every volunteer, member, and manager process has been verified for thousands of daily users.
- The existing VMMS site is on Frappe 17 development while this package requires Frappe 16; it was not used as a disposable integration-test site.

## Required end-to-end rehearsal before launch

Use a **separate disposable site with the intended companion apps and society configuration**. Walk these with real browser sessions and capture server errors: guest signup/login and 2FA; volunteer and member draft, exit, resume, submit, return for information and resubmit; manager approval/rejection and geo scope; payment request, callback, manual confirmation, renewal and expiry; volunteer invitation accept/decline, assignment, task and verified hours; manager deployment creation, TOR submission, staffing, attendance, closeout, stipend report and communication; public card verification before and after expiry. Then run realistic concurrent traffic and inspect slow queries and worker queues. This is still outstanding, not implied by passing unit tests.
