/* Kenya Red Cross Society — run the UAT seed from the Desk browser console.
 *
 * Paste this whole file into the browser console on the Desk of the site you
 * want to seed, signed in as **Administrator**, then follow what it prints.
 *
 * WHY THIS IS A THIN SCRIPT. The seed itself is Python — 47 counties, 290
 * sub-counties, the county-only approval workflows, the newsroom, the diary and
 * the opportunities board. It is not reimplemented here. This calls
 * `vmmsx.seed.kenya_install`'s three whitelisted endpoints and reports what they
 * say, so there is exactly one implementation of the seed and this cannot drift
 * from it. Contrast `tanzania_prod_demo_seed.browser.js`, which builds its
 * records in JavaScript because it predates there being a module to call.
 *
 * WHAT IT DOES TO THE SITE. Creates roles, a three-rung geo ladder, 338 Geo
 * Nodes, membership types, two approval workflows, the `approver@krcs.demo`
 * account (no password), and openly-demo content: 10 stories, 15 events, 11
 * opportunities, 3 announcements. It creates **no** volunteers, members or
 * coordinators — those are what a UAT is for. Every step is idempotent: run it
 * twice and the second run reports `exists` against everything.
 *
 * WHAT IT WILL NOT DO. It cannot purge. `main(purge=True)` empties a society off
 * a site and there is no confirmation string worth putting in front of that over
 * HTTP; that is a shell act, after a backup. This only ever adds.
 *
 * BEFORE YOU RUN IT ON ANYTHING LIVE. The stories, events and job openings below
 * are demo material — well-written, and still invented. On a site with real
 * volunteers on it they are the society publishing fiction. That is the one part
 * of this seed worth deciding about deliberately rather than by pasting.
 */
(async () => {
  const POLL_MS = 3000;
  const GIVE_UP_AFTER_MS = 15 * 60 * 1000;

  const call = async (method, args = {}) => (await frappe.call({ method, args })).message;
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const M = "vmmsx.seed.kenya_install";

  const site = frappe.boot?.sitename || window.location.hostname;
  const user = frappe.session?.user;

  console.log("%cKenya Red Cross Society — UAT seed", "font-size:15px;font-weight:600");
  console.log(`site: ${site}\nsigned in as: ${user}`);

  if (user !== "Administrator") {
    console.error(
      `Signed in as ${user}. This endpoint is Administrator-only — not because` +
        " System Manager is untrusted, but because writing a society's whole" +
        " configuration should not be something any of several System Managers" +
        " can trigger by opening a console. Sign in as Administrator and re-run.",
    );
    return;
  }

  /* Read-only, and worth doing first: it says what the site looks like now, so
   * "0 counties" tells you this is a fresh site and "47" tells you somebody has
   * already run this. */
  const before = await call(`${M}.check`).catch((error) => {
    console.error("Could not reach the seed endpoints. Is vmmsx installed and migrated on this site?", error);
    return null;
  });

  if (!before) return;

  console.log(`readiness before: ${before.total - before.failed.length}/${before.total} checks pass`);
  console.table(before.rows.map(({ key, status, detail }) => ({ check: key, status, detail })));

  /* The speed bump. Typing the site name is the difference between running this
   * and pasting something that runs it. */
  const typed = window.prompt(
    `Type the site name to seed it.\n\nThis writes 338 geo nodes, two approval workflows and demo content to:\n\n${site}\n\nIt creates no volunteers, members or coordinators. It cannot purge.`,
  );

  if (typed !== site) {
    console.warn(
      typed === null
        ? "Cancelled. Nothing was written."
        : `Typed "${typed}", expected "${site}". Nothing was written.`,
    );
    return;
  }

  const queued = await call(`${M}.start`, { confirm: typed });

  if (!queued.queued) {
    console.warn(`Not queued: ${queued.reason}`, queued.progress);
    return;
  }

  console.log(`Queued as ${queued.job_id}. It runs on the server's long queue, so you can close this tab.`);
  console.log("Polling for progress. A full run takes a few minutes — most of it is the 338-node tree.");

  /* Polled rather than awaited, because the run is a background job. That is the
   * point: a synchronous call would hold an HTTP worker open past nginx's proxy
   * timeout, and the request would carry on running after the browser gave up. */
  const startedAt = Date.now();
  let last = "";

  for (;;) {
    await sleep(POLL_MS);

    const progress = await call(`${M}.status`).catch(() => null);

    if (!progress) {
      console.warn("Status call failed; still polling.");
      continue;
    }

    const line = `[${progress.step ?? "?"}/${progress.of ?? "?"}] ${progress.message}`;

    if (line !== last) {
      console.log(line);
      last = line;
    }

    if (progress.failed) {
      console.error("The run failed and was rolled back to the last completed step.");
      console.error(progress.message);
      if (progress.traceback) console.error(progress.traceback);
      console.log("Every step is idempotent: fix the cause and run this again. Completed steps will report `exists`.");
      return;
    }

    if (progress.finished) {
      console.log("%cDone.", "font-size:14px;font-weight:600");

      if (progress.counts) console.table(progress.counts);

      const failed = (progress.readiness || []).filter((row) => row.status !== "ok");

      if (failed.length) {
        console.warn(`${failed.length} readiness check(s) failed — this site is not ready to be tested yet:`);
        console.table(failed.map(({ key, detail }) => ({ check: key, why: detail })));
      } else {
        console.log(`All ${(progress.readiness || []).length} readiness checks passed.`);
      }

      console.log(
        "%cRunning the UAT",
        "font-weight:600",
        "\n 1. Coordinators and volunteers each sign up for their own account at /login." +
          "\n 2. Give each coordinator their county — this part needs a shell:" +
          "\n      bench --site <site> execute vmmsx.seed.kenya.promote_coordinator \\" +
          '\n        --kwargs "{\'email\': \'their@email\', \'county_name\': \'Kisumu\'}"' +
          "\n 3. Until a county has its own coordinator, its applications route to" +
          "\n    approver@krcs.demo at the national root, so nothing lands in an empty queue." +
          "\n 4. Re-check this site any time:  await frappe.call('" + M + ".check')",
      );
      return;
    }

    if (Date.now() - startedAt > GIVE_UP_AFTER_MS) {
      console.warn(
        "Still running after 15 minutes, which is longer than this should take." +
          " The job is on the server and is not affected by this tab — check the" +
          " worker logs, or poll again with:  await frappe.call('" + M + ".status')",
      );
      return;
    }
  }
})();
