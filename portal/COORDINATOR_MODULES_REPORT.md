# Communication and People Management report

## Routes implemented

- `/admin/communication` redirects to `/admin/communication/system/compose`.
- `/admin/communication/{system,email,sms}/{compose,sent}` are direct routes. Compose uses the existing permission-scoped API; Sent shows an explicit unavailable state until a safe history API exists.
- `/admin/people` is the permission-scoped operational overview.
- Existing queue, application-review, member/volunteer register, and dossier routes are reused inside the People workspace: `/admin/queue/{volunteers,members}`, `/admin/queue/:kind/:name`, `/admin/registry/{members,volunteers}`, and `/admin/registry/:kind/:name`.

Both modules use Deployments' focused-workspace shell: icon global rail, routed secondary panel, and the Shell's small-screen route scroller.

## Existing contracts retained

- Communication options and `can_send` come from `vmmsx.api.communication.options`.
- Preview validates the geographic anchor, then server-resolves the configured closed audience. Send repeats that validation and resolution.
- Notification/email use VMMS Announcement. SMS creates a provider-owned Draft campaign; VMMS does not claim it was dispatched.
- Approval queues come from caller assignments and are revalidated against current routing. `can_act` is document-specific and every decision is checked again server-side.
- Registers use Frappe permission queries as their scope floor. Filters only narrow; pages and totals remain server-owned.
- Dossiers omit unreadable related records and identifiers.

## Backend/API gaps (not simulated)

- Individual/multi-recipient selection and durable secure audience references. Current communication supports configured audience groups below a geographic anchor only.
- Notification/email drafts, templates, cancellation, and scheduled delivery.
- Permission-scoped, server-paged campaign history/detail, recipient results, provider status, and audit-history DTOs.
- Provider/encoding-aware SMS segment and cost estimation.
- People aggregates for expiring certifications, approaching renewals, and unmatched payments.
- Paging/search/sort parameters for the personal approval queue; it currently returns the caller's validated ToDo set.
- Permission-preserving exports and reviewer assignment.

An individual-recipient API must use opaque server-owned selections, recalculate against current scope at preview and send time, prevent stale selection expansion, and avoid returning private contact details. Until that exists, no unrestricted ID list is accepted or persisted by the frontend.
