import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { mount } from "../test/harness";
import { CommunicationSubNav, inCommunication } from "./CommunicationNav";
import { PeopleSubNav, inPeople } from "./PeopleNav";

describe("focused coordinator workspaces", () => {
	it("exposes direct channel routes and marks the current communication route", () => {
		mount(<CommunicationSubNav />, { route: "/admin/communication/sms/compose" });
		expect(screen.getByRole("link", { name: "Compose SMS" }).getAttribute("href")).toBe("/admin/communication/sms/compose");
		expect(screen.getByRole("link", { name: "Compose SMS" }).getAttribute("aria-current")).toBe("page");
		expect(screen.getByRole("link", { name: "Sent notifications" }).getAttribute("href")).toBe("/admin/communication/system/sent");
	});

	it("keeps queues and registers as distinct People routes", () => {
		mount(<PeopleSubNav />, { route: "/admin/queue/members" });
		expect(screen.getByRole("link", { name: "Volunteer applications" }).getAttribute("href")).toBe("/admin/queue/volunteers");
		expect(screen.getByRole("link", { name: "Membership applications" }).getAttribute("aria-current")).toBe("page");
		expect(screen.getByRole("link", { name: "Members" }).getAttribute("href")).toBe("/admin/registry/members");
	});

	it("recognises detail routes as part of their focused workspace", () => {
		expect(inCommunication("/admin/communication/email/sent")).toBe(true);
		expect(inPeople("/admin/queue/volunteers/APP-1")).toBe(true);
		expect(inPeople("/admin/deployments")).toBe(false);
	});
});
