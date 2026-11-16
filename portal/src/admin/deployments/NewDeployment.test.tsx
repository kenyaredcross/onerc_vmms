import { act, fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API } from "../../lib/api";
import { mount } from "../../test/harness";

/**
 * The one page a County Coordinator deploys from.
 *
 * Their own county is shown, not chosen; the branch office is the meeting point
 * unless unticked; the volunteer list is found with the filters first and is
 * the true count; and the press says what is missing instead of doing nothing.
 */

const posted: Array<{ method: string; body: Record<string, unknown> }> = [];
const asked: Array<{ method: string; params: Record<string, unknown> }> = [];
const reads = new Map<string, unknown>();

vi.mock("frappe-react-sdk", async (importOriginal) => {
	const actual = (await importOriginal()) as { default: Record<string, unknown> };
	const { createContext } = await import("react");

	return {
		...actual.default,
		default: actual.default,
		FrappeContext: createContext({
			call: {
				get: (method: string, params: Record<string, unknown>) => {
					asked.push({ method, params });
					return Promise.resolve({ message: reads.get(method) ?? null });
				},
				post: (method: string, body: Record<string, unknown>) => {
					posted.push({ method, body });

					if (method === API.sendToVolunteers) {
						return Promise.resolve({
							message: body.select_all
								? { state: "queued", count: 120 }
								: { state: "sent", success: body.volunteers, failure: [] },
						});
					}

					return Promise.resolve({
						message: {
							deployment: {
								name: "DEP-0009",
								title: body.title,
								sending: { send_on: body.send_on ?? null },
							},
							sending: null,
						},
					});
				},
			},
		}),
		FrappeProvider: ({ children }: { children: React.ReactNode }) => children,
		useFrappeGetCall: (method: string, params?: Record<string, unknown>, key?: string | null) => {
			if (key !== null) asked.push({ method, params: params ?? {} });
			return {
				data: key === null ? undefined : { message: reads.get(method) },
				error: null,
				isLoading: false,
				mutate: () => Promise.resolve(undefined),
			};
		},
	};
});

// Leaflet needs a real layout; the map is not what these tests are about.
vi.mock("./PinMap", () => ({ PinMap: () => <div data-testid="map" /> }));

const { DeploymentCreate } = await import("./NewDeployment");

function person(volunteer: string, full_name: string) {
	return {
		volunteer,
		red_profile: null,
		full_name,
		photo: null,
		status: "Active",
		home_geo_node: "GEO-NBI",
		geo_path: "Nairobi",
		deployable: true,
		blocking_reasons: [],
		missing_certifications: [],
		desirable_certifications_held: [],
		availability: { is_available: false, is_unavailable: false, missing_days: [], why: "" },
		clash: { is_clashing: false, deployments: [] },
		is_candidate: true,
	};
}

beforeEach(() => {
	posted.length = 0;
	asked.length = 0;
	reads.clear();
	reads.set(API.deploymentSetup, {
		level: "County",
		counties: [
			{
				name: "GEO-NBI",
				place_name: "Nairobi",
				point: { latitude: -1.28, longitude: 36.82 },
				branch_office: {
					name: "BL-1",
					location_name: "Nairobi Branch Office",
					address: "Upper Hill",
					latitude: -1.3,
					longitude: 36.81,
				},
			},
		],
		professions: ["Nurse"],
		time_zone: "Africa/Nairobi",
		projects: [
			{ name: "PROJ-1", project_name: "Nairobi Marathon" },
			{ name: "PROJ-2", project_name: "Long Rains" },
			{ name: "PROJ-3", project_name: "School Safety" },
		],
		can_attach_terms: true,
	});
	reads.set(API.deploymentOptions, { email_templates: [], professions: ["Nurse"] });
	reads.set(API.branchTerms, {
		terms: [
			{
				name: "TOR-1",
				tor_name: "Marathon First Aid",
				project: "PROJ-1",
				project_name: "Nairobi Marathon",
				is_offered: true,
				expected_start_date: "2026-11-20",
				expected_end_date: "2026-11-22",
			},
			{
				name: "TOR-2",
				tor_name: "Flood Response",
				project: "PROJ-2",
				project_name: "Long Rains",
				is_offered: true,
				expected_start_date: null,
				expected_end_date: null,
			},
		],
	});
	reads.set(API.findCandidates, {
		register_readable: true,
		candidate_count: 120,
		considered: 120,
		truncated: true,
		as_of: "2026-11-20",
		candidates: [person("VOL-1", "Amina Otieno"), person("VOL-2", "Brian Mwangi")],
	});
});

const terms = () => document.getElementById("new-deployment-terms") as HTMLSelectElement;

describe("setting up a deployment on one page", () => {
	it("shows the coordinator's own county, and offers only terms covering it", () => {
		mount(<DeploymentCreate />);

		expect(screen.getByText("Nairobi")).toBeTruthy();
		expect(document.getElementById("new-deployment-county")?.tagName).toBe("DIV");
		expect(asked.find((call) => call.method === API.branchTerms)?.params).toMatchObject({
			covering: "GEO-NBI",
			active_only: 1,
		});
	});

	it("meets at the branch office unless unticked", () => {
		mount(<DeploymentCreate />);

		const office = screen.getByRole("checkbox", { name: /Nairobi Branch Office/ });
		expect((office as HTMLInputElement).checked).toBe(true);
		expect(screen.queryByText(/Where the volunteers gather before setting off/)).toBeNull();

		fireEvent.click(office);
		expect(screen.getByText(/Where the volunteers gather before setting off/)).toBeTruthy();
	});

	it("keeps the button pressable and points at what is missing, top first", () => {
		mount(<DeploymentCreate />);

		const create = screen.getByRole("button", { name: "Save deployment" });
		expect(create.getAttribute("aria-disabled")).toBe("true");

		fireEvent.click(create);
		expect(screen.getByText("Choose the project.")).toBeTruthy();
		expect(document.activeElement).toBe(document.getElementById("new-deployment-project"));

		fireEvent.change(document.getElementById("new-deployment-project")!, { target: { value: "PROJ-1" } });
		fireEvent.click(create);
		expect(screen.getByText("Choose the terms of reference.")).toBeTruthy();
		expect(document.activeElement).toBe(terms());

		fireEvent.change(terms(), { target: { value: "TOR-1" } });
		fireEvent.click(create);

		expect(screen.getByText("Give the deployment a title.")).toBeTruthy();
		expect(document.activeElement).toBe(document.getElementById("new-deployment-title"));
		expect(posted).toHaveLength(0);
	});

	it("fills the project from the terms, and narrows the terms by project", () => {
		mount(<DeploymentCreate />);
		const project = document.getElementById("new-deployment-project") as HTMLSelectElement;

		fireEvent.change(terms(), { target: { value: "TOR-1" } });
		expect(project.value).toBe("PROJ-1");

		fireEvent.change(project, { target: { value: "PROJ-2" } });
		expect(terms().value).toBe("");
		expect([...terms().options].map((option) => option.value)).toEqual(["", "TOR-2"]);
	});

	it("offers every open project, not only those with terms already written", () => {
		mount(<DeploymentCreate />);
		const project = document.getElementById("new-deployment-project") as HTMLSelectElement;

		expect([...project.options].map((option) => option.value)).toEqual(["", "PROJ-2", "PROJ-1", "PROJ-3"]);
	});

	it("attaches a TOR from outside the system, uploads it, and records it under the project", async () => {
		const upload = vi.fn(() =>
			Promise.resolve(
				new Response(JSON.stringify({ message: { file_url: "/private/files/paper-tor.pdf" } }), { status: 200 }),
			),
		);
		vi.stubGlobal("fetch", upload);

		mount(<DeploymentCreate />);
		fireEvent.click(screen.getByRole("checkbox", { name: /The TOR is not in the system/ }));
		expect(document.getElementById("new-deployment-terms")).toBeNull();

		fireEvent.change(document.getElementById("new-deployment-project")!, { target: { value: "PROJ-3" } });
		fireEvent.change(document.getElementById("new-deployment-title")!, { target: { value: "School drill" } });
		fireEvent.change(document.getElementById("new-deployment-start")!, { target: { value: "2099-11-20" } });
		fireEvent.change(document.getElementById("new-deployment-end")!, { target: { value: "2099-11-21" } });

		const create = screen.getByRole("button", { name: "Save deployment" });
		fireEvent.click(create);
		expect(screen.getByText("Attach the TOR.")).toBeTruthy();
		expect(posted).toHaveLength(0);

		const paper = new File(["%PDF"], "paper-tor.pdf", { type: "application/pdf" });
		fireEvent.change(screen.getByLabelText("TOR attachment"), { target: { files: [paper] } });
		expect(screen.getByText("paper-tor.pdf")).toBeTruthy();

		await act(async () => {
			fireEvent.click(create);
		});

		expect(upload).toHaveBeenCalledWith("/api/method/upload_file", expect.objectContaining({ method: "POST" }));
		expect(posted[0].body).toMatchObject({
			terms_of_reference: "",
			tor_attachment: "/private/files/paper-tor.pdf",
			project: "PROJ-3",
		});
		vi.unstubAllGlobals();
	});

	it("asks for the TOR as a file where the county has no terms in the system", () => {
		reads.set(API.branchTerms, { terms: [] });
		mount(<DeploymentCreate />);

		expect(screen.getByLabelText("TOR attachment")).toBeTruthy();
		expect(screen.getByText(/no terms of reference in the system for this county/)).toBeTruthy();
	});

	it("never offers an attachment where the society approves its terms in the system", () => {
		reads.set(API.deploymentSetup, { ...(reads.get(API.deploymentSetup) as object), can_attach_terms: false });
		mount(<DeploymentCreate />);

		expect(screen.queryByRole("checkbox", { name: /The TOR is not in the system/ })).toBeNull();
	});

	it("pins a meeting point typed by hand, and sends its coordinates", async () => {
		mount(<DeploymentCreate />);

		// The branch office comes with its own pin; only another place needs one.
		expect(screen.queryByRole("button", { name: "Add a pin for the meeting point" })).toBeNull();
		fireEvent.click(screen.getByRole("checkbox", { name: /Nairobi Branch Office/ }));
		fireEvent.click(screen.getByRole("button", { name: "Add a pin for the meeting point" }));

		fireEvent.change(screen.getByPlaceholderText(/Google Maps link/), { target: { value: "-1.31, 36.79" } });
		fireEvent.click(screen.getByRole("button", { name: "Use" }));
		expect(screen.getByText("-1.31, 36.79")).toBeTruthy();

		fireEvent.change(terms(), { target: { value: "TOR-1" } });
		fireEvent.change(document.getElementById("new-deployment-title")!, { target: { value: "Marathon" } });
		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Save deployment" }));
		});

		expect(posted[0].body).toMatchObject({
			meeting_at_branch_office: 0,
			meeting_latitude: -1.31,
			meeting_longitude: 36.79,
		});
	});

	it("asks by email only while SMS is not ready, and says a system notification goes too", async () => {
		mount(<DeploymentCreate />);

		expect(screen.queryByRole("checkbox", { name: "SMS" })).toBeNull();
		expect(screen.getByText("A system notification will also be sent to the volunteer.")).toBeTruthy();

		fireEvent.change(terms(), { target: { value: "TOR-1" } });
		fireEvent.change(document.getElementById("new-deployment-title")!, { target: { value: "Marathon" } });
		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Save deployment" }));
		});

		expect(posted[0].body).toMatchObject({ notify_by_email: 1, notify_by_sms: 0 });
	});

	it("marks required fields with an asterisk and shows the time zone under the dates", () => {
		mount(<DeploymentCreate />);

		const details = screen.getByRole("heading", { name: "Details" }).parentElement!;

		expect(details.textContent).not.toContain("Required.");
		for (const label of ["Project", "Terms of reference", "Title", "Expected start date", "Expected end date"]) {
			const marked = [...details.querySelectorAll("span")].find((span) => span.firstChild?.textContent === label);
			expect(marked?.textContent).toBe(`${label}*`);
		}
		expect(details.textContent?.match(/Africa\/Nairobi/g)).toHaveLength(2);
	});

	it("keeps the terms with the dates they fill, in the old tool's words", () => {
		mount(<DeploymentCreate />);

		const details = screen.getByRole("heading", { name: "Details" }).parentElement!;

		expect(details.contains(terms())).toBe(true);
		expect(details.textContent).toContain("Expected start date");
		expect(details.textContent).toContain("Expected end date");
		expect(details.textContent).toContain("Number of volunteers required");
	});

	it("reads Details, the location, the notifications, then selecting volunteers", () => {
		mount(<DeploymentCreate />);

		const headings = screen
			.getAllByRole("heading")
			.map((heading) => heading.textContent)
			.filter((text) =>
				["Details", "Terms of reference", "Location", "Notifications", "Select volunteers"].includes(text ?? ""),
			);

		expect(headings).toEqual(["Details", "Location", "Notifications", "Select volunteers"]);
	});

	it("filters by the old tool's quick filters, availability included", async () => {
		reads.set(API.applicationOptions, {
			skills: [],
			languages: [],
			availability: [{ key: "weekend_mornings", label: "Weekend mornings", description: null }],
		});
		reads.set(API.volunteerFilters, {
			places: [
				{ county: "Nairobi", sub_county: "Westlands", ward: "Parklands" },
				{ county: "Nairobi", sub_county: "Kibra", ward: "Laini Saba" },
			],
			certification_types: [],
		});
		mount(<DeploymentCreate />);
		fireEvent.change(terms(), { target: { value: "TOR-1" } });

		fireEvent.focus(screen.getByRole("combobox", { name: "Availability" }));
		fireEvent.click(screen.getByRole("option", { name: /Weekend mornings/ }));
		fireEvent.focus(screen.getByRole("combobox", { name: "Sub-county" }));
		fireEvent.click(screen.getByRole("option", { name: /Westlands/ }));
		fireEvent.focus(screen.getByRole("combobox", { name: "Ward" }));

		// The wards narrow to the sub-counties chosen.
		expect(screen.queryByRole("option", { name: /Laini Saba/ })).toBeNull();
		fireEvent.click(screen.getByRole("option", { name: /Parklands/ }));
		fireEvent.click(screen.getByRole("checkbox", { name: "Only those free on the deployment dates" }));

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Find volunteers" }));
		});

		expect(asked.find((call) => call.method === API.findCandidates)?.params).toMatchObject({
			availability_slots: ["weekend_mornings"],
			residence_sub_counties: ["Westlands"],
			residence_wards: ["Parklands"],
			only_available: 1,
		});
	});

	it("keeps the place search near the county", async () => {
		reads.set(API.suggestPlaces, { places: [], reason: null });
		mount(<DeploymentCreate />);

		fireEvent.click(screen.getByRole("button", { name: "Add a pin for the site" }));
		vi.useFakeTimers();
		try {
			fireEvent.change(screen.getByPlaceholderText("Name or address"), { target: { value: "Upper Hill" } });
			await act(async () => {
				vi.advanceTimersByTime(450);
			});
		} finally {
			vi.useRealTimers();
		}

		expect(asked.find((call) => call.method === API.suggestPlaces)?.params).toEqual({
			query: "Upper Hill",
			latitude: -1.28,
			longitude: 36.82,
		});
	});

	it("fills the dates from the terms chosen", () => {
		mount(<DeploymentCreate />);

		fireEvent.change(terms(), { target: { value: "TOR-1" } });

		expect((document.getElementById("new-deployment-start") as HTMLInputElement).value).toBe("2026-11-20");
		expect((document.getElementById("new-deployment-end") as HTMLInputElement).value).toBe("2026-11-22");
	});

	it("finds nobody until asked, then the whole county's count, fifty at a time", async () => {
		mount(<DeploymentCreate />);
		fireEvent.change(terms(), { target: { value: "TOR-1" } });

		expect(asked.some((call) => call.method === API.findCandidates)).toBe(false);

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Find volunteers" }));
		});

		expect(asked.find((call) => call.method === API.findCandidates)?.params).toMatchObject({
			terms_of_reference: "TOR-1",
			geo_node: "GEO-NBI",
			as_of: "2026-11-20",
			limit: 50,
			offset: 0,
		});
		expect(screen.getByText("120 volunteers match")).toBeTruthy();
		expect(screen.getByText("Amina Otieno")).toBeTruthy();
	});

	it("saves first, then sends the request to everybody the search matched", async () => {
		mount(<DeploymentCreate />);
		fireEvent.change(terms(), { target: { value: "TOR-1" } });
		fireEvent.change(document.getElementById("new-deployment-title")!, {
			target: { value: "Nairobi Marathon" },
		});

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Find volunteers" }));
		});
		fireEvent.click(screen.getByRole("button", { name: "Select all 120" }));
		expect(screen.getByText("All 120 volunteers who match the filters.")).toBeTruthy();

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Save deployment" }));
		});

		// Saved, and nobody asked yet.
		expect(posted).toHaveLength(1);
		expect(posted[0].body).toMatchObject({
			terms_of_reference: "TOR-1",
			geo_node: "GEO-NBI",
			title: "Nairobi Marathon",
			meeting_at_branch_office: 1,
			notify_by_email: 1,
			// Off while SMS is hidden (SMS_READY).
			notify_by_sms: 0,
		});
		expect(posted[0].body.mode).toBeUndefined();
		expect(screen.getByText(/^Saved\./)).toBeTruthy();

		fireEvent.click(screen.getByRole("button", { name: "Submit and send request" }));
		const dialog = screen.getByRole("dialog");
		expect(dialog.textContent).toContain("Send the deployment request to all 120 volunteers who match the filters?");

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Submit" }));
		});

		const sent = posted.find((call) => call.method === API.sendToVolunteers)?.body;
		expect(sent).toMatchObject({ name: "DEP-0009", mode: "ask", select_all: 1 });
		expect(sent?.criteria).toMatchObject({ skills: [], professions: [], languages: [], surge_only: 0 });
		expect(screen.getByText(/Sending the deployment request to 120 volunteers/)).toBeTruthy();
	});

	it("lists who was selected, and names them in the popup before the request goes out", async () => {
		mount(<DeploymentCreate />);
		fireEvent.change(terms(), { target: { value: "TOR-1" } });
		fireEvent.change(document.getElementById("new-deployment-title")!, { target: { value: "Later" } });
		fireEvent.click(screen.getByRole("checkbox", { name: /Future deployment/ }));
		fireEvent.change(document.getElementById("new-deployment-send-on")!, {
			target: { value: "2099-11-16T08:00" },
		});

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Find volunteers" }));
		});
		fireEvent.click(screen.getByRole("checkbox", { name: "Select Amina Otieno" }));

		const selected = screen.getByRole("region", { name: "Selected volunteers" });
		expect(selected.textContent).toContain("Amina Otieno");

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Save deployment" }));
		});
		expect(posted[0].body).toMatchObject({ send_on: "2099-11-16 08:00:00" });

		fireEvent.click(screen.getByRole("button", { name: "Submit and send request" }));
		const dialog = screen.getByRole("dialog");
		expect(dialog.textContent).toContain("Amina Otieno");
		expect(dialog.textContent).toMatch(/It will be sent on /);

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Submit" }));
		});

		expect(posted.find((call) => call.method === API.sendToVolunteers)?.body).toMatchObject({
			mode: "ask",
			volunteers: ["VOL-1"],
		});
	});

	it("will not send before somebody is selected, and offers nobody a placement", async () => {
		mount(<DeploymentCreate />);
		fireEvent.change(terms(), { target: { value: "TOR-1" } });
		fireEvent.change(document.getElementById("new-deployment-title")!, { target: { value: "Empty" } });

		expect(screen.queryByRole("button", { name: /place/i })).toBeNull();

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Save deployment" }));
		});
		fireEvent.click(screen.getByRole("button", { name: "Submit and send request" }));

		expect(screen.queryByRole("dialog")).toBeNull();
		expect(screen.getByText("Select the volunteers to send the request to.")).toBeTruthy();
	});
});
