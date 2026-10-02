# VMMSX MVP production readiness audit — 24 September 2026

## Decision

**No launch sign-off yet.** The current checkout and `vmms4.localhost` development site do not establish that the product is secure, fully working, or capable of serving 5,000 active volunteers. The app has useful automated coverage, and this review fixed two membership defects plus one vulnerable production dependency. The gates below require evidence on a launch-equivalent deployment before public use.

The intended load must be defined as both **at least 5,000 registered volunteers** and an agreed peak concurrency and request mix. No peak-load run, latency distribution, error-rate result, or queue-drain measurement exists in this review.

## Launch blockers

| Priority | Finding and evidence | Required closure |
| --- | --- | --- |
| P0 | **Membership fee accounting is absent.** `vmmsx/member/services/payment.py` confirms a `OneRC Payment Transaction`, while `vmmsx/finance/services/ledger.py` explicitly describes its output as a report, not a book of account, and computes historical income using today's published fee. There is no Sales Invoice or Payment Entry creation in vmmsx. | Finance-approved invoice, allocation, Payment Entry, immutable paid amount, Company and node Cost Center, reconciliation, refund/rejection rules; test both manual and gateway paths against the ledger. |
| P0 | **Manual fees can be confirmed without a receipt/reference or proof.** `vmmsx/member/services/payment.py:205` accepts an optional receipt; `vmmsx/member/tests/test_record_payment.py` explicitly tests successful confirmation without one. This does not meet the stated MVP payment controls in `LAUNCH_MVP_TEST_PLAN.md`. | Require a private proof and traceable reference before confirmation, with role and geographic scope, audit trail, duplicate prevention, and a separate approval action. |
| P0 | **No 5,000-volunteer capacity evidence.** No launch-equivalent load test, production telemetry, or peak workload target was supplied. The finance report also silently caps each source at 5,000 rows (`vmmsx/finance/services/ledger.py:68,119,253`), and analytics uses unbounded reads (`vmmsx/analytics/services/summary.py:167`). | Seed at least 5,000 realistic volunteers with related applications, assignments, hours and events; test agreed concurrent journeys; measure p50/p95/p99 latency, errors, DB queries, CPU, memory and worker queue drain. Remove or surface report truncation and bound expensive reads. |
| P1 | **Version and deployment mismatch.** `pyproject.toml` requires Frappe `>=16,<17`; the configured `vmms4` rehearsal site is on Frappe 17 development. `bench --site vmms4.localhost doctor` reports its scheduler disabled, and no local server was listening on port 8000 during this audit. | Pin and test the exact production versions of Frappe and every companion app; deploy with HTTPS, running web/Redis/workers/scheduler, monitoring, backup and restore rehearsal. |
| P1 | **Normal gateway applications can duplicate an already current membership for the same member, type and branch.** `vmmsx/member/services/membership.py:255` documents that `assert_not_already_held` is proof-only and that the ordinary Gateway case remains open. | Enforce one current membership per member/type/branch at submission, preserve valid multi-branch membership, and test concurrent requests. |
| P1 | **End-to-end journeys and attack checks lack sign-off.** `LAUNCH_MVP_TEST_PLAN.md` has no completed journey gate. Browser, phone, provider callback, delivery, cross-node authorization, private-file access, backup restore and outage recovery were not verified here. | Execute the tracker on a launch-equivalent site with synthetic identities and retain dated, redacted evidence for each role and branch. |

## Fixes made in this audit

- A membership that is stored `Active` after `valid_to` now reads as expired in the membership DTO, member profile and public card verification, and certificate/card generation refuses it. Self-service active membership selection also filters by the effective date. Added an integration regression test. The stored status and core affiliation still require the scheduled expiry sweep.
- Expired and cancelled memberships no longer make the portal show “Application in” and suppress Join. Only Draft, Awaiting Payment and Awaiting Approval do.
- Added a portal dependency override for `ws >=8.21.0`. Before the change, the live npm advisory check found a high severity `ws` denial-of-service advisory in the production dependency tree. After install, `npm audit --omit=dev --json` reported zero known production advisories. This is a dependency advisory check, not a penetration test.

## Checks run and their limits

| Check | Result |
| --- | --- |
| `bench --site vmms4.localhost run-tests --module vmmsx.member.tests.test_certificate` | 11/11 passed after the member-profile extension, including the new expiry regression. |
| `bench --site vmms4.localhost run-tests --module vmmsx.member.tests.test_my_memberships` | 14/14 passed. |
| `npm run typecheck` | Passed after the code and dependency changes. |
| `npm run build` | Passed after the dependency update; Vite warned that the main JS chunk is about 895 kB minified (287 kB gzip). This needs a real mobile network timing check. |
| `npx vitest run --maxWorkers=1 --testTimeout=20000 --reporter=dot` | 279 tests passed in 26 suites; the Operations suite failed to start because a Vitest worker timed out fetching a module. It also timed out alone with the default pool, but passed 31/31 using `--pool=forks --maxWorkers=1 --minWorkers=1`. A reproducible green full-suite command is still needed. |
| `ruff check vmmsx` | 39 existing findings across tests, document generators and two application files. Changed Python files passed focused Ruff. |
| `npm run translations:check` | Failed with 664 missing Swahili strings. Define English-only MVP scope or complete supported localization before advertising it. |
| `bench doctor` on vmms4 | Scheduler disabled/inactive; one worker online. This describes a development site, not production. |
| Live browser and load tests | Not run: local HTTP server was not serving, and no launch-equivalent environment or workload was available. |

## Required release evidence

1. Close the payment/accounting and duplicate-membership blockers with automated integration tests and finance sign-off.
2. Rehearse registration, save/resume, approval, payment, renewal, card verification, opportunity, event, deployment, hours and notifications on desktop and narrow phones with separate applicant, volunteer, member and wrong-branch staff accounts.
3. Exercise guest and authenticated authorization, cross-user and cross-branch IDs, private attachments, file upload limits, callback signature/replay/wrong amount, CSRF, login abuse, throttling and secrets/log redaction. Record negative results, not only successful paths.
4. Run a load test on pinned production versions with at least 5,000 populated volunteer records and agreed peak concurrency. Capture p95/p99 response times, error rate, slow queries, queue depth/drain, CPU, memory, and DB resource use; repeat after fixes.
5. Verify HTTPS, worker and scheduler operation, backup/restore, monitoring/alerts, incident owners and rollback on the actual launch topology.

No security review can prove immunity from all attacks. This audit establishes specific controls and missing evidence; production approval requires the above gates to pass.
