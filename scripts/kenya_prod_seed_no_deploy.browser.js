/* Kenya Red Cross Society — run the UAT seed from the Desk browser console,
 * against code that is ALREADY DEPLOYED. No app update needed.
 *
 * Paste this whole file into the browser console on the Desk of the site you
 * want to seed, signed in as Administrator.
 *
 * WHY THIS EXISTS, AND WHEN TO USE THE OTHER ONE.
 * `kenya_prod_seed.browser.js` calls `vmmsx.seed.kenya_install.start/status/check`
 * — three whitelisted endpoints that are cleaner, guarded, and report progress
 * step by step. Use that one once the app has been redeployed.
 *
 * This script is for before that. The deployed build has `kenya_install.main()`
 * and `readiness()` but nothing whitelisted, so there is no `/api/method/` route
 * to either. What it does have is Frappe's own `Scheduled Job Type`, whose
 * `method` field is a dotted path that `execute()` runs through
 * `frappe.get_attr(...)()` — real Python, not the `safe_exec` sandbox — and whose
 * `execute_event` is whitelisted to System Manager. So: create a stopped job
 * pointing at the seed, force it onto the queue once, watch its log, delete it.
 *
 * WHY NOT THE SYSTEM CONSOLE. It looks like the obvious answer and it is not.
 * `System Console` runs `safe_exec`, which cannot import, and whose `enqueue`
 * only reaches `call_whitelisted_function` — that is, whitelisted functions
 * only. The seed is not whitelisted in the deployed build, so the console cannot
 * reach it. Checked, rather than assumed.
 *
 * WHY THE JOB RUNS IN THE BACKGROUND. The seed writes 338 Geo Nodes and each
 * insert into a nested set rewrites bounds across the tree; a run takes minutes.
 * `Daily Long` is chosen for `frequency` purely because `get_queue_name()` reads
 * the word "Long" and puts the job on the long queue, which has the timeout for
 * it. `stopped = 1` means it never runs on a schedule — it runs once, because
 * `enqueue(force=True)` ignores whether it was due.
 *
 * WHAT IT WRITES. Roles, a three-rung geo ladder, 338 Geo Nodes, membership
 * types, two approval workflows, `approver@krcs.demo` (no password), and openly
 * demo content: 10 stories, 15 events, 11 opportunities, 3 announcements. NO
 * volunteers, members or coordinators. Every step is idempotent — run it twice
 * and the second run reports `exists` throughout.
 *
 * IT CANNOT PURGE. `main()` is called with no arguments, so `purge` stays false.
 *
 * BEFORE A LIVE SITE. The stories, events and openings are invented. Good prose,
 * still fiction. On a site with real volunteers that is the society publishing
 * fiction under its own name — worth a decision, not a paste.
 */
(async () => {
  const METHOD = "vmmsx.seed.kenya_install.main";
  const POLL_MS = 5000;
  const GIVE_UP_AFTER_MS = 20 * 60 * 1000;

  const call = async (method, args = {}) => (await frappe.call({ method, args })).message;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  const site = frappe.boot?.sitename || window.location.hostname;
  const user = frappe.session?.user;

  console.log("%cKenya Red Cross Society — UAT seed (no-deploy route)", "font-size:15px;font-weight:600");
  console.log(`site: ${site}\nsigned in as: ${user}\nwill run: ${METHOD}`);

  if (user !== "Administrator") {
    console.error(`Signed in as ${user}. Run this as Administrator.`);
    return;
  }

  const typed = window.prompt(
    `Type the site name to seed it.\n\nThis writes 338 geo nodes, two approval workflows and demo content to:\n\n${site}\n\nNo volunteers, members or coordinators are created. It cannot purge.`,
  );

  if (typed !== site) {
    console.warn(
      typed === null ? "Cancelled. Nothing was written." : `Typed "${typed}", expected "${site}". Nothing was written.`,
    );
    return;
  }

  /* 1. The job. `stopped` so the scheduler never picks it up on its own;
   *    `create_log` so there is something to watch. */
  let job;

  try {
    const existing = await call("frappe.client.get_list", {
      doctype: "Scheduled Job Type",
      filters: [["method", "=", METHOD]],
      fields: ["name"],
      limit_page_length: 1,
    });

    job = existing?.[0]?.name;

    if (job) {
      console.log(`Reusing the job row left by an earlier run: ${job}`);
    } else {
      const inserted = await call("frappe.client.insert", {
        doc: {
          doctype: "Scheduled Job Type",
          method: METHOD,
          frequency: "Daily Long",
          stopped: 1,
          create_log: 1,
        },
      });
      job = inserted.name;
      console.log(`Created ${job}`);
    }
  } catch (error) {
    console.error(
      "Could not create the Scheduled Job Type. This needs System Manager, and it needs vmmsx" +
        " to be installed on this site.",
      error,
    );
    return;
  }

  /* 2. Note where the log currently ends, so the poll below reads THIS run's row
   *    and not a previous one's. */
  const priorLogs = await call("frappe.client.get_list", {
    doctype: "Scheduled Job Log",
    filters: [["scheduled_job_type", "=", job]],
    fields: ["name"],
    limit_page_length: 1,
    order_by: "creation desc",
  });
  const priorLatest = priorLogs?.[0]?.name || null;

  /* 3. Force it onto the long queue, once. */
  await call("frappe.core.doctype.scheduled_job_type.scheduled_job_type.execute_event", {
    doc: { name: job },
  });

  console.log("Queued on the long queue. The job runs on the server — you can close this tab.");
  console.log("Watching its log. Expect several minutes; most of it is the 338-node tree.");

  /* 4. Watch the Scheduled Job Log. `execute()` writes Start, then Complete or
   *    Failed, and puts the traceback on `details` when it fails — so a failure
   *    here is visible rather than silent. */
  const startedAt = Date.now();
  let last = "";

  for (;;) {
    await sleep(POLL_MS);

    const logs = await call("frappe.client.get_list", {
      doctype: "Scheduled Job Log",
      filters: [["scheduled_job_type", "=", job]],
      fields: ["name", "status", "details", "creation"],
      limit_page_length: 1,
      order_by: "creation desc",
    }).catch(() => null);

    const row = logs?.[0];

    if (!row || row.name === priorLatest) {
      if (Date.now() - startedAt > 90000) {
        console.warn(
          "No log row yet after 90s. That usually means no background worker is running" +
            " on this site, so the job is queued and nothing is consuming it.",
        );
      }
      continue;
    }

    if (row.status !== last) {
      console.log(`[${row.status}] ${row.creation}`);
      last = row.status;
    }

    if (row.status === "Failed") {
      console.error("The seed failed. Frappe rolled the failing step back; earlier steps stand.");
      console.error(row.details || "(no traceback recorded)");
      console.log("Every step is idempotent — fix the cause and run this again; done steps report `exists`.");
      break;
    }

    if (row.status === "Complete") {
      console.log("%cDone.", "font-size:14px;font-weight:600");

      const counts = {};
      const surfaces = [
        ["Counties", "Geo Node", { geo_level: "krcs-county" }],
        ["Sub-counties", "Geo Node", { geo_level: "krcs-sub-county" }],
        ["Stories", "Article", { status: "Published", docstatus: 1 }],
        ["Events", "Buzz Event", { is_published: 1 }],
        ["Opportunities", "Job Opening", { publish: 1, status: "Open" }],
        ["Announcements", "VMMS Announcement", { status: "Published" }],
        ["Volunteers (should be 0)", "VMMS Volunteer", {}],
      ];

      for (const [label, doctype, filters] of surfaces) {
        counts[label] = await call("frappe.client.get_count", { doctype, filters }).catch(() => "n/a");
      }

      console.table(counts);
      console.log(
        "Expect 47 counties and 290 sub-counties. If counties is 0, read the log row's" +
          " details — the job ran but the seed refused, most likely because the site is" +
          " not migrated for vmmsx.",
      );
      break;
    }

    if (Date.now() - startedAt > GIVE_UP_AFTER_MS) {
      console.warn(`Still running after 20 minutes. Check the worker logs, or read ${job}'s job log in the Desk.`);
      break;
    }
  }

  /* 5. Tidy up. The row was only ever a way to call a function; leaving it
   *    behind puts a fake scheduled job in somebody's list forever. */
  try {
    await call("frappe.client.delete", { doctype: "Scheduled Job Type", name: job });
    console.log(`Removed ${job}.`);
  } catch (error) {
    console.warn(`Could not remove ${job} — delete it by hand from Scheduled Job Type.`, error);
  }
})();
