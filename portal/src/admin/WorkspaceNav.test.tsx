import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { mount } from "../test/harness";
import { CommunicationSubNav, inCommunication } from "./CommunicationNav";
import { DeploymentSubNav, inDeployments } from "./DeploymentNav";
import { PeopleSubNav, inPeople } from "./PeopleNav";

describe("focused coordinator workspaces", () => {
	it("exposes direct channel routes and marks the current communication route", () => {
		mount(<CommunicationSubNav />, { route: "/admin/communication/sms/compose" });

		expect(screen.getByRole("link", { name: "Compose SMS" }).getAttribute("href")).toBe("/admin/communication/sms/compose");
		expect(screen.getByRole("link", { name: "Sent SMS" }).getAttribute("href")).toBe("/admin/communication/sms/sent");
		// The channel switcher is a segmented control of four, and the selected
		// one carries `aria-current` — the channel is a route, so somebody
		// arriving by link is told which one they are on.
		expect(screen.getByRole("link", { name: "SMS" }).getAttribute("aria-current")).toBe("page");
		// "In app", not "System". The reader is a coordinator, not a sysadmin,
		// and the channel is a notification inside the portal.
		expect(screen.getByRole("link", { name: "In app" }).getAttribute("href")).toBe("/admin/communication/system/compose");
	});

	it("offers the channel's own screen only where there is a channel to look at", () => {
		mount(<CommunicationSubNav />, { route: "/admin/communication/sms/compose" });
		expect(screen.queryByRole("link", { name: "The channel" })).toBeNull();

		// WhatsApp is the one channel with a thing behind it: a linked phone that
		// can drop, a pacing limit, and a list of people who replied STOP.
		mount(<CommunicationSubNav />, { route: "/admin/communication/whatsapp/compose" });
		expect(screen.getByRole("link", { name: "The channel" }).getAttribute("href")).toBe("/admin/communication/whatsapp/channel");
	});

	it("keeps queues, recruitment and registers as distinct People routes", () => {
		mount(<PeopleSubNav />, { route: "/admin/queue/members" });

		expect(screen.getByRole("link", { name: "Volunteer applications" }).getAttribute("href")).toBe("/admin/queue/volunteers");
		expect(screen.getByRole("link", { name: "Membership applications" }).getAttribute("aria-current")).toBe("page");
		// "Active members", not "Members": the register is of current memberships,
		// and a row labelled with the wider word would promise a list that
		// includes draft, awaiting-payment, expired and cancelled records.
		expect(screen.getByRole("link", { name: "Active members" }).getAttribute("href")).toBe("/admin/registry/members");
		expect(screen.getByRole("link", { name: "Active volunteers" }).getAttribute("href")).toBe("/admin/registry/volunteers");
		// The third door into the society, beside the other two.
		expect(screen.getByRole("link", { name: "Job applications" }).getAttribute("href")).toBe("/admin/recruitment/applications");
		expect(screen.getByRole("link", { name: "Job openings" }).getAttribute("href")).toBe("/admin/recruitment/openings");
	});

	it("offers each People row only to somebody the server said holds its section", () => {
		// Its six destinations come from three different sections, and the rail no
		// longer lists them — so this filter is the only one left between a
		// coordinator and a column of links back to /admin.
		mount(<PeopleSubNav sections={new Set(["people", "registry"])} />, {
			route: "/admin/registry/members",
		});

		expect(screen.getByRole("link", { name: "Active members" })).toBeTruthy();
		expect(screen.getByRole("link", { name: "Active volunteers" })).toBeTruthy();
		expect(screen.queryByRole("link", { name: "Volunteer applications" })).toBeNull();
		expect(screen.queryByRole("link", { name: "Job openings" })).toBeNull();
		// The overview is gated on `people`, which this panel already stands on.
		expect(screen.getByRole("link", { name: "Overview" })).toBeTruthy();
	});

	it("recognises detail routes as part of their focused workspace", () => {
		expect(inCommunication("/admin/communication/email/sent")).toBe(true);
		expect(inPeople("/admin/queue/volunteers/APP-1")).toBe(true);
		expect(inPeople("/admin/recruitment/openings/JOB-1")).toBe(true);
		expect(inPeople("/admin/deployments")).toBe(false);
	});

	it("keeps a queue's own band routes inside the People workspace", () => {
		// A bookmarked history band is still People. Without this the rail would
		// expand again on arrival, which is the bug `hasSubNav` exists to stop.
		expect(inPeople("/admin/queue/volunteers/changes")).toBe(true);
		expect(inPeople("/admin/queue/members/closed")).toBe(true);
	});

	it("marks the parent queue row while a band route is open", () => {
		mount(<PeopleSubNav />, { route: "/admin/queue/volunteers/changes" });

		// The panel names sections, not states: standing in a queue's Changes
		// band is standing in that queue, and the row has to say so or the reader
		// loses their place in the section.
		expect(
			screen.getByRole("link", { name: "Volunteer applications" }).getAttribute("aria-current"),
		).toBe("page");
		expect(
			screen.getByRole("link", { name: "Membership applications" }).getAttribute("aria-current"),
		).toBeNull();
	});

	it("gives Operations every approved destination as a real route", () => {
		mount(<DeploymentSubNav />, { route: "/admin/deployments/ongoing" });

		expect(screen.getByRole("link", { name: "Operations overview" }).getAttribute("href")).toBe("/admin/deployments");
		expect(screen.getByRole("link", { name: "Terms of Reference" }).getAttribute("href")).toBe("/admin/deployments/terms");
		expect(screen.getByRole("link", { name: "Ongoing deployments" }).getAttribute("aria-current")).toBe("page");
		expect(screen.getByRole("link", { name: "Deployment requests" }).getAttribute("href")).toBe("/admin/deployments/requests");
		expect(screen.getByRole("link", { name: "Documents" }).getAttribute("href")).toBe("/admin/deployments/documents");
		// Not approved for redesign, and still reachable: removing them would
		// break navigation the rest of the console depends on.
		expect(screen.getByRole("link", { name: "Create deployment" }).getAttribute("href")).toBe("/admin/deployments/new");
		expect(screen.getByRole("link", { name: "Past deployments" }).getAttribute("href")).toBe("/admin/deployments/past");
	});

	it("carries Projects and Tasks, which the rail cannot show beside a panel", () => {
		// The section declares `hasSubNav`, so standing here forces the rail to
		// icons — which hides the Operations group's children and disables the
		// control that would bring them back. Without these two rows there is no
		// route from the Operations overview to Projects at all.
		mount(<DeploymentSubNav sections={new Set(["deployments", "tasks"])} />, {
			route: "/admin/deployments",
		});

		expect(screen.getByRole("link", { name: "Projects" }).getAttribute("href")).toBe("/admin/projects");
		expect(screen.getByRole("link", { name: "Tasks" }).getAttribute("href")).toBe("/admin/tasks");
	});

	it("offers Tasks only to somebody the server said holds it", () => {
		// Projects shares the `deployments` key this whole panel stands behind,
		// so it is never the row in question. Tasks is its own section, and
		// offering it to somebody without it is a link straight back to /admin.
		mount(<DeploymentSubNav sections={new Set(["deployments"])} />, { route: "/admin/deployments" });

		expect(screen.getByRole("link", { name: "Projects" })).toBeTruthy();
		expect(screen.queryByRole("link", { name: "Tasks" })).toBeNull();
	});

	it("recognises a deployment detail route as part of Operations", () => {
		expect(inDeployments("/admin/deployments/DEP-1")).toBe(true);
		expect(inDeployments("/admin/deployments/terms/TOR-1")).toBe(true);
		expect(inDeployments("/admin/people")).toBe(false);
	});

	it("counts Projects and Tasks as Operations, because the panel is their navigation", () => {
		// They are no longer rows under the rail's Operations group, so a Projects
		// page outside this section would be a page with none of its section's
		// navigation on it and no way across to Tasks.
		expect(inDeployments("/admin/projects")).toBe(true);
		expect(inDeployments("/admin/projects/PROJ-1")).toBe(true);
		expect(inDeployments("/admin/tasks")).toBe(true);
		// Not a prefix match on the word: a different section starting with the
		// same letters is a different section.
		expect(inDeployments("/admin/projections")).toBe(false);
	});
});
