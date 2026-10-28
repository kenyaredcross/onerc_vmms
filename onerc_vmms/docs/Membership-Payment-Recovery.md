# VMMS membership and event M-Pesa accounting and recovery

The fix lives entirely in `onerc_vmms`. The installed `frappe_mpsa_payments` app
continues to initiate STK requests and supply its existing Daraja connector.
No changes to that app, ERPNext, paybill credentials, or the configured callback
URL are required.

## Confirmed incident cause

Automatic M-Pesa processing fails at the accounting stage because the payment request uses a receiving ledger account belonging to a different company from its invoice. In the membership flow, VMMS first selects a company-specific Payment Gateway Account, then immediately overwrites that selection with the default account for the currency, without retaining the company filter; this selects the HQ M-Pesa account owned by Kenya Red Cross Society for invoices belonging to branches such as Bomet and Nairobi. When the successful-payment handler creates a Payment Entry, it passes that HQ account into the branch transaction, and ERPNext rejects the resulting General Ledger entry with the account/company mismatch validation shown in the error logs. This prevents automatic completion and can leave the invoice in Draft and the Payment Request as Requested even when the customer has paid. The callback also saves its receipt, result and completion status only after accounting succeeds, so the same exception prevents those confirmation details from being retained through that path, while the disabled STK retry enqueue leaves no automatic catch-up in the inspected implementation. The manual September payment succeeded using Nairobi's own receiving account, supporting the account-routing diagnosis. Older August documents show Submitted and Paid statuses, but their entries in the database snapshot lack the balancing M-Pesa debit, so those statuses do not demonstrate a previously complete accounting flow. The evidence establishes the current failure mechanism, but does not establish the exact date it began or identify a particular upgrade or deployment as its trigger.

## How it works

- The Payment Request controller override affects Sales Invoices with a
  `membership` or `event_booking` link. Other payment requests use ERPNext's
  standard implementation. Event invoice links are present in the existing
  deployed Buzz schema; no new fields are required.
- Collection can use the central paybill. The Payment Entry receiving account
  must belong to the invoice company, match its currency, and be an enabled
  ledger account. VMMS falls back to the company's account under Mode of Payment.
- The existing STK callback URL is routed through a VMMS whitelisted-method hook.
  Other invoices and unsuccessful callbacks are delegated to the provider app.
- A successful VMMS callback must match the initiated amount and contain a
  receipt. VMMS saves it in Mpesa Express Request and a dedicated Integration
  Request before attempting accounting. A later accounting rollback preserves
  that confirmation evidence.
- Posting requires a server-to-server STK status query returning `ResultCode=0`
  for the exact stored CheckoutRequestID. An HTTP success, a draft invoice, an
  exception log, or a browser-supplied payment status does not establish payment.
- A row lock and existing submitted Payment Entry references prevent repeated
  callbacks or recovery attempts from posting the same request twice.
- Existing submitted entries must have balanced, positive ledger totals in the
  invoice company. Incomplete historical entries require reconciliation rather
  than another posting.
- Paid event bookings are submitted through their own controller after full
  invoice settlement. Its normal submission hook issues the tickets and QR
  codes. VMMS checks one submitted ticket per attendee. A submitted booking is
  reused; callbacks never call its ticket generator again. Cancelled bookings,
  existing tickets on draft bookings, and incomplete ticket sets require review.
- The website completion event is published after the accounting transaction
  commits. A member retry cannot cancel a request with a recorded confirmation
  and start another collection while accounting is pending.

## Deploy

Deploy the VMMS changes through the site's usual release process. On a self-hosted
bench, after updating this app:

```bash
bench --site YOUR_SITE migrate
bench --site YOUR_SITE clear-cache
bench restart
```

Migration registers the scheduler job; restarted web and worker processes load
the controller and callback overrides. The site scheduler must be running.
Configure each company's receiving ledger account in Mode of Payment, including
the mode selected in VM Settings. A separate branch paybill is not required.

Every 15 minutes the VMMS job checks up to 20 pending membership and event requests, prioritizing the
least recently modified. It checks requests created in the last day plus older
requests with a recorded successful result. Network failures and unmatched or
unsuccessful status responses never create Payment Entries.

## Inspect and recover the backlog

Accounts Managers or System Managers can inspect a single Express Request from
Desk's browser console after deployment:

```javascript
await frappe.call({
  method: "onerc_vmms.volunteer_and_member_management.services.membership_payments.recover_payment",
  args: { name: "YOUR_MEXP_REQUEST", dry_run: true }
});
```

Use `dry_run: false` to verify and recover that request. Posting also requires
Payment Entry creation and submission permissions. This queries the existing
checkout; it never initiates another charge.

For a bounded older batch, inspect first from the server:

```bash
bench --site YOUR_SITE execute onerc_vmms.volunteer_and_member_management.services.membership_payments.recover_pending_payments --kwargs '{"since":"2026-07-27","limit":20,"dry_run":true}'
```

Set `dry_run` to `false` to recover the reviewed batch. Successfully recovered
requests leave the pending batch. Pending failures update their modification
time so another batch can advance to the next requests. The maximum batch is 50.
Add `"payment_kind":"event"` or `"payment_kind":"membership"` to restrict a
batch. The earlier `recover_membership_payment` and
`recover_pending_membership_payments` entry points remain membership-only.

Results are `Inspection`, `Completed`, `Unconfirmed`, `Accounting Pending`, or
`Review Required`. Inspection does not contact Safaricom or post entries.
Unconfirmed does not establish that the customer failed to pay; it means this
attempt did not obtain a matching successful status response.

## Cases requiring reconciliation

VMMS leaves these cases pending and logs the accounting error rather than
creating another settlement:

- The invoice has already been settled manually without a matching Payment Entry
  for this request.
- The receipt already has an active C2B register record. Reconcile that record
  before posting another accounting entry; VMMS does not cancel provider records.
- The amount or currency differs from the outstanding request.
- The company's receiving account is missing or invalid.
- An older draft invoice fails standard submission validation, such as due date
  validation. Invoice dates and accounting validation are not bypassed.

Look for Error Logs titled `VMMS Payment Accounting Pending` or
`VMMS Payment Recovery`. Integration Requests with service
`VMMS M-Pesa Confirmation` preserve the callback and verified query.
STK queries do not return a receipt number: a previously lost callback receipt
cannot be reconstructed from a successful query and must be matched to the
provider statement if the receipt code is needed.

The older submitted Payment Entries with incomplete ledger postings require a
separate ledger reconciliation. Recovery does not recreate submitted entries or
rewrite historical ledgers.

## Verification

```bash
env/bin/python -m unittest onerc_vmms.volunteer_and_member_management.services.test_event_payments onerc_vmms.volunteer_and_member_management.services.test_membership_payments onerc_vmms.volunteer_and_member_management.doctype.vm_membership.test_vm_membership.TestMembershipPaymentRouting -v
```

The implementation was also exercised against an old production snapshot with
the provider app restored: balanced branch ledger posting, callback evidence
surviving an accounting failure, successful retry, and duplicate prevention.
Those tests blocked commits and provider calls and rolled back all financial
changes. They are not a live payment verification or production deployment.

The local upstream Buzz source differs from the deployed event implementation
and lacks the `Event Booking.initialize_payment()` called by VMMS. The deployed
Buzz source is required to finish a full event checkout/submission test. The
event unit tests exercise ticket-count and submission behavior through controller
test doubles; they do not verify that deployed controller or ticket delivery.
