import { fireEvent, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import { mount } from "../test/harness";
import type { DeploymentInvitation, OpenRegistration, VolunteerProfile } from "./types";

/**
 * The panel that tells somebody where their own registration stands.
 *
 * **"Draft" means two opposite things and this screen has to pick one.** A
 * registration nobody has submitted is a Draft; so is one an approver sent back
 * for more information. This panel read the state alone and chose the second
 * every time, so a person who had saved half a form and come back was told
 * "your application needs something from you — your branch has asked for
 * something", about an application no branch had ever seen. `reviewed` is the
 * server's answer to which one it is.
 *
 * **And in both cases there has to be a way back in.** The panel was the only
 * thing on the page that mentioned the application, and it named a document
 * reference and offered no link, so the form somebody was halfway through was
 * unreachable from the screen telling them about it. The link is now the panel's
 * whole answer to "what do I do next", and the reference is gone: a naming series
 * is how the desk finds the row, not how an applicant thinks about their own
 * application.
 */
const reads = new Map<string, unknown>();

vi.mock("frappe-react-sdk", async (importOriginal) => {
	// The SDK ships CommonJS: the real exports are the properties of `default`,
	// and spreading the namespace itself would hand back no named exports at all.
	const actual = (await importOriginal()) as { default: Record<string, unknown> };

	return {
		...actual.default,
		default: actual.default,
		useFrappeGetCall: (path: string, _params?: unknown, swrKey?: string | null) => ({
			data: swrKey === null ? undefined : { message: reads.get(path) },
			error: null,
			isLoading: false,
			isValidating: false,
			mutate: () => Promise.resolve(undefined),
		}),
		useFrappeAuth: () => ({
			currentUser: "amina@example.com",
			isLoading: false,
			logout: () => Promise.resolve(undefined),
		}),
	};
});

const Dashboard = (await import("./Dashboard")).default;

function registration(over: Partial<OpenRegistration> = {}): OpenRegistration {
	return {
		doctype: "VMMS Volunteer Application",
		name: "VAPP-00017",
		path: "volunteer",
		state: "Draft",
		...over,
	};
}

function volunteer(over: Partial<VolunteerProfile> = {}): VolunteerProfile {
	return {
		volunteer: "VOL-00010",
		red_profile: "RED-00010",
		full_name: "Godfrey Mwakyusa",
		email: "godfrey@example.com",
		phone: null,
		gender: null,
		date_of_birth: null,
		preferred_language: null,
		profile_photo: null,
		status: "Active",
		joined_on: "2025-12-19",
		exited_on: null,
		geo_node: "GEO-00066",
		geo_path: "Mbeya City — Mbeya — Tanzania Red Cross Society",
		home_geo_node: "GEO-00066",
		home_geo_path: "Mbeya City — Mbeya — Tanzania Red Cross Society",
		...over,
	};
}

/** A place the society has named but never located, which is the common case. */
function place() {
	return {
		name: null,
		address: null,
		latitude: null,
		longitude: null,
		has_point: false,
		located_on: null,
		map: null,
		directions: null,
	};
}

function invitation(over: Partial<DeploymentInvitation> = {}): DeploymentInvitation {
	return {
		assignment: "DASG-00004",
		deployment: "DEP-00002",
		title: "Landslide Risk Assessment",
		terms_of_reference: "TOR-00002",
		deployment_status: "Planned",
		start_date: "2026-09-06",
		end_date: "2026-09-14",
		geo_node: "GEO-00067",
		geo_path: "Rungwe — Mbeya — Tanzania Red Cross Society",
		notes: null,
		where: {
			site: place(),
			meeting_point: place(),
			travel_notes: null,
			local_contact: { name: null, phone: null },
		},
		response: "Pending",
		role: "Assessor",
		invited_on: "2026-09-01",
		responded_on: null,
		response_note: null,
		...over,
	};
}

beforeEach(() => {
	reads.clear();
});

describe("a draft nobody has sent yet", () => {
	beforeEach(() => {
		reads.set(API.myOpenRegistrations, { volunteer: registration({ reviewed: false }) });
	});

	it("says the application is unfinished, not that the branch is waiting", () => {
		mount(<Dashboard />);

		expect(screen.getByText("Your volunteer application is not finished")).toBeTruthy();
		expect(screen.queryByText("Your application needs something from you")).toBeNull();
	});

	it("offers the way back into the form, on the road it was started on", () => {
		mount(<Dashboard />);

		const link = screen.getByRole("link", { name: /continue application/i });
		expect(link.getAttribute("href")).toBe("/join?path=volunteer");
	});

	it("does not read the document name back to the applicant", () => {
		mount(<Dashboard />);

		expect(screen.queryByText(/VAPP-00017/)).toBeNull();
		expect(screen.queryByText(/your reference is/i)).toBeNull();
	});
});

describe("a draft an approver sent back", () => {
	beforeEach(() => {
		reads.set(API.myOpenRegistrations, {
			volunteer: registration({
				reviewed: true,
				reason: "Send us your first-aid certificate.",
			}),
		});
	});

	it("says the branch has asked for something, and shows what", () => {
		mount(<Dashboard />);

		expect(screen.getByText("Your volunteer application needs something from you")).toBeTruthy();
		expect(screen.getByText("Send us your first-aid certificate.")).toBeTruthy();
	});

	it("still offers the way back in", () => {
		mount(<Dashboard />);

		expect(
			screen.getByRole("link", { name: /continue application/i }).getAttribute("href"),
		).toBe("/join?path=volunteer");
	});
});

describe("a registration that is with the branch", () => {
	it("offers no way to edit it, because there is nothing to edit", () => {
		reads.set(API.myOpenRegistrations, {
			volunteer: registration({ state: "In Review", reviewed: true }),
		});

		mount(<Dashboard />);

		expect(screen.getByText("Your volunteer application is under review")).toBeTruthy();
		expect(screen.queryByRole("link", { name: /continue application/i })).toBeNull();
	});
});

describe("separate membership and volunteer paths", () => {
	it("identifies a membership review and still offers volunteer registration", () => {
		reads.set(API.myOpenRegistrations, {
			member: registration({
				doctype: "VMMS Membership",
				name: "MEM-00017",
				path: "member",
				state: "In Review",
			}),
			volunteer: null,
		});

		mount(<Dashboard />);

		expect(screen.getByText("Your membership application is under review")).toBeTruthy();
		expect(screen.getByRole("heading", { name: /your membership application is with your branch/i })).toBeTruthy();
		expect(screen.getByRole("link", { name: /register as a volunteer/i }).getAttribute("href")).toBe("/join?path=volunteer");
	});

	it("shows each open application by kind without offering either path again", () => {
		reads.set(API.myOpenRegistrations, {
			member: registration({ name: "MEM-00017", path: "member", state: "In Review" }),
			volunteer: registration({ state: "Submitted" }),
		});

		mount(<Dashboard />);

		expect(screen.getByText("Your membership application is under review")).toBeTruthy();
		expect(screen.getByText("Your volunteer application is in")).toBeTruthy();
		expect(screen.queryByRole("link", { name: /register as a volunteer/i })).toBeNull();
	});
});

/** The Home summary stays compact while issued documents open on demand. */
describe("an accepted volunteer's own front page", () => {
	beforeEach(() => {
		reads.set(API.myVolunteer, volunteer());
		reads.set(API.myOpenRegistrations, {});
	});

	it("does not label somebody's own name with their standing", () => {
		mount(<Dashboard />);

		expect(screen.queryByText(/active volunteer/i)).toBeNull();
	});

	it("keeps the issued ID compact and shows the real card on hover", () => {
		reads.set(API.myVolunteerCard, { html: '<div class="vmms-card">Issued volunteer ID</div>' });
		mount(<Dashboard />);
		expect(screen.queryByText("Your volunteer card")).toBeNull();
		const button = screen.getByRole("button", { name: /view volunteer id/i });
		expect(within(button).getByText("VOL-00010")).toBeTruthy();
		expect(screen.queryByTitle("Volunteer ID preview")).toBeNull();
		fireEvent.mouseEnter(button);
		const frame = screen.getByTitle("Volunteer ID preview");
		expect(frame.getAttribute("sandbox")).toBe("");
		expect(frame.getAttribute("srcdoc")).toContain("Issued volunteer ID");
		fireEvent.keyDown(document, { key: "Escape" });
		expect(screen.queryByTitle("Volunteer ID preview")).toBeNull();
	});

	it("still writes the record out for somebody the society has issued no card to", () => {
		mount(<Dashboard />);

		expect(screen.queryByText("Your volunteer card")).toBeNull();
		expect(screen.getByText("VOL-00010")).toBeTruthy();
	});

	it("names the branch a deployment is in, never its document reference", () => {
		reads.set(API.myInvitations, {
			volunteer: "VOL-00010",
			waiting: [invitation()],
			answered: [],
		});

		mount(<Dashboard />);

		expect(screen.getByText(/Rungwe · Mbeya/)).toBeTruthy();
		expect(screen.queryByText(/GEO-00067/)).toBeNull();
	});

	it("asks the question in words instead of calling it a priority", () => {
		reads.set(API.myInvitations, {
			volunteer: "VOL-00010",
			waiting: [invitation()],
			answered: [],
		});

		mount(<Dashboard />);

		expect(screen.getByText("You have been asked to join a deployment")).toBeTruthy();
		expect(screen.queryByText(/your priority/i)).toBeNull();
	});
});


describe("the approved Home page", () => {
	it("shows event images alongside the original date and details", () => {
		reads.set(API.eventsUpcoming, { events: [{ event: "EVENT-1", title: "First aid day", start_date: "2099-10-23", start_time: "09:00:00", venue: "Nairobi", image: "/files/event.jpg" }] });
		mount(<Dashboard />);
		expect(screen.getByText("Upcoming Events")).toBeTruthy();
		const event = screen.getByRole("link", { name: /first aid day/i });
		expect(event.querySelector("img")?.getAttribute("src")).toBe("/files/event.jpg");
		expect(event.querySelector("time")?.getAttribute("datetime")).toBe("2099-10-23");
	});

	it("does not add a broken thumbnail to an event without an image", () => {
		reads.set(API.eventsUpcoming, { events: [{ event: "EVENT-1", title: "First aid day", start_date: "2099-10-23", image: "" }] });
		mount(<Dashboard />);
		expect(screen.getByRole("link", { name: /first aid day/i }).querySelector("img")).toBeNull();
	});

	it("opens the holder's configured membership certificate on focus", () => {
		reads.set(API.myMemberships, [{ name: "MEMBERSHIP-1", member: "MEMBER-1", is_active: true, certificate_available: true, membership_type_name: "Annual membership" }]);
		reads.set("vmmsx.api.member.get_certificate", { body: "<h1>Issued membership certificate</h1>" });
		mount(<Dashboard />);
		const button = screen.getByRole("button", { name: /view membership certificate/i });
		expect(within(button).getByText("MEMBER-1")).toBeTruthy();
		fireEvent.focus(button);
		expect(screen.getByTitle("Membership certificate preview").getAttribute("srcdoc")).toContain("Issued membership certificate");
	});

	it("offers no certificate preview when the server says it is unavailable", () => {
		reads.set(API.myMemberships, [{ name: "MEMBERSHIP-1", member: "MEMBER-1", is_active: true, certificate_available: false, membership_type_name: "Annual membership" }]);
		mount(<Dashboard />);
		expect(screen.queryByRole("button", { name: /view membership certificate/i })).toBeNull();
	});
});
