import { Route, Routes } from "react-router-dom";
import { act, fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import { mount } from "../test/harness";
import type { DeploymentSite, DeploymentSummary, TermsOfReference } from "../portal/types";

/**
 * The Operations workspace.
 *
 * **The rules these hold.** Every headline figure is a scoped server aggregate,
 * never a page's length. The status bands name the doctype's own six — Suspended
 * and Closed Out included, which they were not before, and a filter that
 * silently returned nothing for a real value is worse than no filter. The map
 * plots individual deployments from their own coordinates and says how many it
 * could not. And a deployment request is `VMMS Deployment Request`, decided in
 * the review queue and nowhere else.
 */

const calls: Array<{ path: string; params: Record<string, unknown> | undefined }> = [];
const reads = new Map<string, unknown>();

vi.mock("frappe-react-sdk", async (importOriginal) => {
	const actual = (await importOriginal()) as { default: Record<string, unknown> };

	return {
		...actual.default,
		default: actual.default,
		useFrappeGetCall: (
			path: string,
			params?: Record<string, unknown>,
			swrKey?: string | null,
		) => {
			if (swrKey === null) {
				return {
					data: undefined,
					error: null,
					isLoading: false,
					isValidating: false,
					mutate: () => Promise.resolve(undefined),
				};
			}

			calls.push({ path, params });

			return {
				data: { message: reads.get(path) },
				error: null,
				isLoading: false,
				isValidating: false,
				mutate: () => Promise.resolve(undefined),
			};
		},
	};
});

// Leaflet touches layout APIs jsdom does not implement, and what these tests are
// about is the data and the accessible list rather than the canvas. The real
// component is exercised in the browser captures.
vi.mock("./OperationsMap", () => ({
	OperationsMap: ({ deployments }: { deployments: DeploymentSite[] }) => (
		<div data-testid="map">{deployments.length} plotted</div>
	),
	MapLegend: ({ statuses }: { statuses: string[] }) => <ul>{statuses.map((s) => <li key={s}>{s}</li>)}</ul>,
}));

const {
	DeploymentsHub,
	DeploymentsOngoing,
	OperationsDocuments,
	PastDeployments,
	RequestList,
} = await import("./Deployments");
const { TermsList } = await import("./Projects");

function deployment(over: Partial<DeploymentSummary> = {}): DeploymentSummary {
	return {
		name: "DEP-0001",
		terms_of_reference: "Tana River Flood Response",
		geo_node: "GEO-1",
		geo_path: "Geita — Tanzania Red Cross Society",
		status: "Active",
		is_open: true,
		is_settled: false,
		is_closed_out: false,
		coordinator: "coordinator@example.com",
		start_date: "2026-09-14",
		end_date: "2026-09-25",
		planned_start: "2026-09-14 08:00:00",
		planned_end: "2026-09-25 17:00:00",
		briefing_on: "2026-09-13 16:00:00",
		check_in_deadline: "2026-09-14 07:00:00",
		expected_return: "2026-09-25 20:00:00",
		actual_start: null,
		actual_end: null,
		volunteers_required: 30,
		email_template: null,
		participant_count: 21,
		assignment_counts: {
			Assigned: 10,
			Pending: 9,
			Accepted: 11,
			Declined: 0,
			Withdrawn: 0,
			on_deployment: 21,
			open: 30,
			total: 30,
		},
		places_left: 9,
		...over,
	} as DeploymentSummary;
}

function site(over: Partial<DeploymentSite> = {}): DeploymentSite {
	return {
		...deployment(),
		where: {
			site: {
				name: "Hola Sub-County Hospital",
				address: "Hola Town",
				latitude: -1.4997,
				longitude: 40.0301,
				has_point: true,
				located_on: null,
				map: "https://www.openstreetmap.org/?mlat=-1.4997&mlon=40.0301",
				directions: "https://www.openstreetmap.org/directions?route=;-1.4997,40.0301",
			},
			meeting_point: {
				name: "Tana River Branch Office",
				address: "Hola",
				latitude: -1.4971,
				longitude: 40.0264,
				has_point: true,
				located_on: null,
				map: null,
				directions: null,
			},
			travel_notes: "Ferry crossing closes at dusk.",
			local_contact: { name: "Jane Njeri", phone: "+255 700 000 001" },
		},
		coordinator_contact: {
			user: "coordinator@example.com",
			full_name: "Peter Kariuki",
			email: "coordinator@example.com",
			phone: "",
		},
		readiness: { briefed: 12, safety: 18, checked_in: 0, leaders: 3 },
		...over,
	} as DeploymentSite;
}

const SUMMARY = {
	as_of: "2026-09-02",
	ongoing: 7,
	by_status: { Planned: 2, Active: 3, Suspended: 1, Completed: 1 },
	people: 82,
	starting_soon: 2,
	starting_soon_days: 14,
	unfilled_soon: 21,
	pending: 9,
	closing_out: 1,
	requests: 12,
	requests_open: 3,
	terms: 18,
	terms_awaiting: 2,
	capped: false,
};

function show(element: React.ReactNode, route: string) {
	return mount(
		<Routes>
			<Route path="*" element={element} />
		</Routes>,
		{ route },
	);
}

function argsFor(path: string) {
	return calls.filter((call) => call.path === path).at(-1)?.params;
}

beforeEach(() => {
	calls.length = 0;
	reads.clear();
});

/* ------------------------------------------------------ operations overview */

describe("the operations overview", () => {
	beforeEach(() => {
		reads.set(API.operationsSummary, SUMMARY);
		reads.set(API.deploymentSites, {
			deployments: [site(), site({ name: "DEP-0002", status: "Planned" })],
			count: 3,
			plotted: 2,
			unplotted: 1,
			capped: false,
		});
		reads.set(API.branchDeployments, {
			count: 1,
			total: 7,
			deployments: [deployment()],
			open_count: 1,
		});
	});

	it("takes every metric from the scoped aggregate, not from a page of rows", () => {
		show(<DeploymentsHub />, "/admin/deployments");

		expect(calls.some((call) => call.path === API.operationsSummary)).toBe(true);
		// 7 ongoing across the whole scope, from a page holding one row.
		expect(screen.getByText("7")).toBeTruthy();
		expect(screen.getByText("82 people currently assigned")).toBeTruthy();
		expect(screen.getByText("21 roles still unfilled")).toBeTruthy();
	});

	it("asks the live list for the ongoing band as a set of statuses", () => {
		show(<DeploymentsHub />, "/admin/deployments");

		// A band is not one status. Asking for the set is the difference between
		// a register and whichever members of it landed on the first page.
		expect(argsFor(API.branchDeployments)).toEqual({
			statuses: ["Planned", "Active", "Suspended", "Completed"],
			mine: 0,
		});
	});

	it("says how many deployments it could not plot rather than drawing fewer pins", () => {
		show(<DeploymentsHub />, "/admin/deployments");

		// Once in the mocked canvas's own text, once in the line beside the
		// legend. What matters is that the count of the ones it could not draw is
		// said out loud rather than silently dropped.
		expect(screen.getAllByText(/2 plotted/).length).toBeGreaterThan(0);
		expect(screen.getByText(/1 without coordinates/)).toBeTruthy();
	});

	it("says why the map is empty rather than leaving a gap where one should be", () => {
		reads.set(API.deploymentSites, {
			deployments: [
				site({
					where: {
						...site().where,
						site: { ...site().where.site, has_point: false, latitude: null, longitude: null },
					},
				}),
			],
			count: 1,
			plotted: 0,
			unplotted: 1,
			capped: false,
		});

		show(<DeploymentsHub />, "/admin/deployments");

		// An empty box where a map should be reads as a map that failed to load.
		expect(screen.getByText("Nothing here can be put on a map yet")).toBeTruthy();
		expect(screen.queryByTestId("map")).toBeNull();
		// And everything is still listed underneath.
		expect(screen.getAllByText(/Tana River Flood Response/).length).toBeGreaterThan(0);
	});

	it("keeps an unlocated deployment in the accessible list, marked as such", () => {
		reads.set(API.deploymentSites, {
			deployments: [
				site(),
				site({
					name: "DEP-0003",
					terms_of_reference: "Coast Cholera Preparedness",
					where: {
						...site().where,
						site: { ...site().where.site, has_point: false, latitude: null, longitude: null },
					},
				}),
			],
			count: 2,
			plotted: 1,
			unplotted: 1,
			capped: false,
		});

		show(<DeploymentsHub />, "/admin/deployments");

		// A map that dropped it would hide the gap in the data it exists to show.
		expect(screen.getByText(/no coordinates yet/)).toBeTruthy();
	});

	it("offers every one of the doctype's six statuses as a map filter", () => {
		show(<DeploymentsHub />, "/admin/deployments");

		for (const status of ["Planned", "Active", "Suspended", "Completed", "Closed Out", "Cancelled"]) {
			expect(screen.getByRole("button", { name: status })).toBeTruthy();
		}
	});

	it("narrows the map read when a status is chosen, and never widens it", async () => {
		show(<DeploymentsHub />, "/admin/deployments");

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Suspended" }));
		});

		expect(argsFor(API.deploymentSites)).toEqual({ status: "Suspended" });
	});

	it("shows the selected deployment's mission picture from the server's own DTO", () => {
		show(<DeploymentsHub />, "/admin/deployments");

		// Terms, coordinator, both places, the local contact, readiness and the
		// control times — every one off the DTO, none derived here.
		expect(screen.getAllByText("Tana River Flood Response").length).toBeGreaterThan(0);
		expect(screen.getByText("Peter Kariuki")).toBeTruthy();
		expect(screen.getByText("Hola Sub-County Hospital")).toBeTruthy();
		expect(screen.getByText("Tana River Branch Office")).toBeTruthy();
		expect(screen.getByText("Jane Njeri")).toBeTruthy();
		expect(screen.getByText("Ferry crossing closes at dusk.")).toBeTruthy();
		expect(screen.getByRole("link", { name: "Directions ↗" })).toBeTruthy();
	});

	it("selects a deployment from the keyboard-operable list, not only from the canvas", async () => {
		show(<DeploymentsHub />, "/admin/deployments");

		const rows = screen.getAllByRole("button", { name: /Tana River Flood Response/ });
		await act(async () => {
			fireEvent.click(rows[rows.length - 1]);
		});

		expect(rows[rows.length - 1].getAttribute("aria-current")).toBe("true");
	});
});

/* ----------------------------------------------------- ongoing deployments */

describe("ongoing deployments", () => {
	it("asks for the four ongoing statuses and excludes the two that are over", () => {
		reads.set(API.branchDeployments, { count: 0, total: 0, deployments: [], open_count: 0 });

		show(<DeploymentsOngoing />, "/admin/deployments/ongoing");

		const args = argsFor(API.branchDeployments) as { statuses: string[] };

		expect(args.statuses).toEqual(["Planned", "Active", "Suspended", "Completed"]);
		expect(args.statuses).not.toContain("Closed Out");
		expect(args.statuses).not.toContain("Cancelled");
	});

	it("groups rows into the four operational columns by their real status", () => {
		reads.set(API.branchDeployments, {
			count: 4,
			total: 4,
			deployments: [
				deployment({ name: "DEP-1", status: "Planned" }),
				deployment({ name: "DEP-2", status: "Active" }),
				deployment({ name: "DEP-3", status: "Suspended", is_open: true }),
				deployment({
					name: "DEP-4",
					status: "Completed",
					is_open: false,
					is_settled: true,
					is_closed_out: false,
				}),
			],
			open_count: 3,
		});

		show(<DeploymentsOngoing />, "/admin/deployments/ongoing");

		// Suspended is a column of its own, drawn as a warning rather than folded
		// into "running" or dropped.
		for (const column of ["Mobilising", "Running", "Suspended", "Close-out"]) {
			expect(screen.getByRole("heading", { name: column })).toBeTruthy();
		}
	});

	it("keeps a closed-out deployment out of the close-out column", () => {
		reads.set(API.branchDeployments, {
			count: 1,
			total: 1,
			deployments: [
				deployment({
					name: "DEP-9",
					terms_of_reference: "Kibera Fire Response",
					status: "Completed",
					is_open: false,
					is_settled: true,
					// The paperwork is filed. Its place is Past deployments.
					is_closed_out: true,
				}),
			],
			open_count: 0,
		});

		show(<DeploymentsOngoing />, "/admin/deployments/ongoing");

		expect(screen.queryByText("Kibera Fire Response")).toBeNull();
		expect(screen.getAllByText("Nothing here").length).toBe(4);
	});

	it("reports how much of the band is on screen rather than calling a page a total", () => {
		reads.set(API.branchDeployments, {
			count: 1,
			total: 42,
			deployments: [deployment()],
			open_count: 1,
		});

		show(<DeploymentsOngoing />, "/admin/deployments/ongoing");

		expect(screen.getByText("1 of 42 ongoing")).toBeTruthy();
	});
});

/* -------------------------------------------------------- past deployments */

describe("past deployments", () => {
	it("asks for the three settled statuses, Closed Out among them", () => {
		reads.set(API.branchDeployments, { count: 0, total: 0, deployments: [], open_count: 0 });

		show(<PastDeployments />, "/admin/deployments/past");

		const args = argsFor(API.branchDeployments) as { statuses: string[] };

		// Closed Out was in neither band before, so a closed-out deployment
		// appeared in no register at all — the worst way for a filter to fail,
		// because the list still looks complete.
		expect(args.statuses).toEqual(["Completed", "Closed Out", "Cancelled"]);
	});

	it("files each mission as a folder under the year it was closed", () => {
		reads.set(API.branchDeployments, {
			count: 1,
			total: 1,
			deployments: [
				deployment({
					name: "DEP-0019",
					terms_of_reference: "Kibera Fire Response",
					status: "Closed Out",
					is_open: false,
					is_settled: true,
					is_closed_out: true,
					// The date the file was filed, which is not the date the work
					// ended: a mission closed in December stays a December file.
					end_date: "2026-08-27",
					closed_out_on: "2026-12-04",
				}),
			],
			open_count: 0,
		});

		show(<PastDeployments />, "/admin/deployments/past");

		expect(screen.getByText("2026 mission file")).toBeTruthy();
		expect(screen.getByText("DEP-0019")).toBeTruthy();
		expect(screen.getByText("Kibera Fire Response")).toBeTruthy();
		// Once on the folder's own foot, once in the status filter above it.
		expect(screen.getAllByText("Closed Out").length).toBe(2);
		// The whole folder is the link, not a corner of it.
		expect(
			screen.getByRole("link", { name: /Kibera Fire Response/ }).getAttribute("href"),
		).toBe("/admin/deployments/DEP-0019");
	});

	it("falls back to the end date for a mission whose file is not yet closed", () => {
		reads.set(API.branchDeployments, {
			count: 1,
			total: 1,
			deployments: [
				deployment({
					name: "DEP-0020",
					status: "Completed",
					is_settled: true,
					is_closed_out: false,
					end_date: "2025-11-11",
					closed_out_on: null,
				}),
			],
			open_count: 0,
		});

		show(<PastDeployments />, "/admin/deployments/past");

		expect(screen.getByText("2025 mission file")).toBeTruthy();
	});

	it("says nothing was deleted when the shelf is empty", () => {
		reads.set(API.branchDeployments, { count: 0, total: 0, deployments: [], open_count: 0 });

		show(<PastDeployments />, "/admin/deployments/past");

		expect(screen.getByText("No mission files here")).toBeTruthy();
		expect(screen.getByText(/Nothing is ever deleted/)).toBeTruthy();
	});
});

/* ------------------------------------------------------ deployment requests */

describe("deployment requests", () => {
	const request = (over: Record<string, unknown> = {}) => ({
		name: "DREQ-00001",
		terms_of_reference: "Tana River Flood Response",
		geo_node: "GEO-1",
		geo_path: "Geita — Tanzania Red Cross Society",
		volunteers_requested: 30,
		needed_from: "2026-09-14",
		needed_until: "2026-09-25",
		justification: "Three wards flooded; households need health and relief support.",
		is_published: false,
		approval_mode: "routed",
		requires_approver: true,
		approval_settled: false,
		is_refused: false,
		deployment: null,
		is_fulfilled: false,
		approval: null,
		...over,
	});

	it("shows the request's own fields, including why it was raised", () => {
		reads.set(API.branchRequests, { count: 1, requests: [request()] });

		show(<RequestList />, "/admin/deployments/requests");

		expect(screen.getByText("Volunteers requested")).toBeTruthy();
		expect(screen.getByText("30")).toBeTruthy();
		expect(
			screen.getByText("Three wards flooded; households need health and relief support."),
		).toBeTruthy();
		// Whether volunteers can see the ask at all — otherwise an approved,
		// unpublished request looks identical to one nobody wants.
		expect(screen.getByText("Not published")).toBeTruthy();
	});

	it("says a request needs no approver where its terms ask for none", () => {
		reads.set(API.branchRequests, { count: 1, requests: [request({ approval: null })] });

		show(<RequestList />, "/admin/deployments/requests");

		expect(screen.getByText("No approver required")).toBeTruthy();
		expect(screen.getByText(/Needs no approver/)).toBeTruthy();
	});

	it("sends an approver to the review queue rather than offering a second decision", () => {
		reads.set(API.branchRequests, {
			count: 1,
			requests: [
				request({
					approval: {
						state: "In Review",
						is_open: true,
						can_act: true,
						stage: { label: "County approval", entered_on: "2026-08-30" },
						decisions: [],
					},
				}),
			],
		});

		show(<RequestList />, "/admin/deployments/requests");

		// The person-gate lives in `api/approvals.py`. A decision control here
		// would be a second door into the same decision.
		expect(screen.queryByRole("button", { name: /Approve/ })).toBeNull();
		expect(
			screen.getByRole("link", { name: "Decide this in your review queue →" }).getAttribute("href"),
		).toBe("/admin/queue/volunteers");
		// The stage label is displayed. It is never compared.
		expect(screen.getByText("County approval")).toBeTruthy();
	});

	it("reports a refused request and a fulfilled one differently", () => {
		reads.set(API.branchRequests, {
			count: 2,
			requests: [
				request({ name: "DREQ-1", is_refused: true, approval_settled: true }),
				request({ name: "DREQ-2", is_fulfilled: true, deployment: "DEP-0001" }),
			],
		});

		show(<RequestList />, "/admin/deployments/requests");

		expect(screen.getByText(/Refused/)).toBeTruthy();
		expect(screen.getByText("Fulfilled by a deployment")).toBeTruthy();
		expect(
			screen.getByRole("link", { name: /Open deployment DEP-0001/ }).getAttribute("href"),
		).toBe("/admin/deployments/DEP-0001");
	});
});

/* ---------------------------------------------------- operations documents */

describe("operations documents", () => {
	const answer = (over: Record<string, unknown> = {}) => ({
		count: 1,
		files: [
			{
				name: "FILE-1",
				file_name: "Tana River TOR v1.4.pdf",
				file_url: "/private/files/tor.pdf",
				file_size: 1_887_436,
				is_private: 1,
				attached_to_doctype: "VMMS Terms of Reference",
				attached_to_name: "TOR-2026-041",
				owner: "jane@example.com",
				creation: "2026-08-30",
				modified: "2026-08-30",
			},
		],
		targets: [{ doctype: "VMMS Deployment", name: "DEP-0001" }],
		record_types: ["Project", "VMMS Terms of Reference", "VMMS Deployment"],
		...over,
	});

	it("lists a file with its record, type, owner and privacy", () => {
		reads.set(API.operationsDocuments, answer());

		show(<OperationsDocuments />, "/admin/deployments/documents");

		expect(screen.getByText("Tana River TOR v1.4.pdf")).toBeTruthy();
		expect(screen.getByText("TOR-2026-041")).toBeTruthy();
		expect(screen.getAllByText("Terms of Reference").length).toBeGreaterThan(0);
		expect(screen.getAllByText(/Private/).length).toBeGreaterThan(0);
		expect(screen.getByRole("link", { name: "Open" }).getAttribute("href")).toBe(
			"/private/files/tor.pdf",
		);
	});

	it("narrows by record type through the server, not in the browser", async () => {
		reads.set(API.operationsDocuments, answer());

		show(<OperationsDocuments />, "/admin/deployments/documents");

		await act(async () => {
			fireEvent.change(screen.getByLabelText("Record type"), {
				target: { value: "VMMS Deployment" },
			});
		});

		expect(argsFor(API.operationsDocuments)).toEqual({
			search: "",
			doctype: "VMMS Deployment",
		});
	});

	it("offers only the write targets the server handed back", () => {
		reads.set(API.operationsDocuments, answer());

		show(<OperationsDocuments />, "/admin/deployments/documents");

		const options = Array.from(
			(screen.getByLabelText(/Store against/) as HTMLSelectElement).options,
		).map((option) => option.value);

		// One writable target and the empty prompt. A record the caller may read
		// but not write is not offered, because the server would refuse it.
		expect(options).toEqual(["", "VMMS Deployment\nDEP-0001"]);
	});

	it("refuses an upload with no target chosen, and keeps the context", async () => {
		reads.set(API.operationsDocuments, answer());
		const sent = vi.fn();
		vi.stubGlobal("fetch", sent);

		show(<OperationsDocuments />, "/admin/deployments/documents");

		const picker = document.querySelector('input[type="file"]') as HTMLInputElement;
		await act(async () => {
			fireEvent.change(picker, {
				target: { files: [new File(["x"], "plan.pdf", { type: "application/pdf" })] },
			});
		});

		expect(sent).not.toHaveBeenCalled();
		expect(screen.getByText("Choose the operational record this file belongs to.")).toBeTruthy();
		// The register is still on screen; an error must not cost the reader
		// their place.
		expect(screen.getByText("Tana River TOR v1.4.pdf")).toBeTruthy();

		vi.unstubAllGlobals();
	});

	it("uploads privately, with the CSRF token, against a server-supplied target", async () => {
		reads.set(API.operationsDocuments, answer());
		const sent = vi.fn().mockResolvedValue({ ok: true });
		vi.stubGlobal("fetch", sent);
		(window as unknown as { csrf_token: string }).csrf_token = "tok-1";

		show(<OperationsDocuments />, "/admin/deployments/documents");

		await act(async () => {
			fireEvent.change(screen.getByLabelText(/Store against/), {
				target: { value: "VMMS Deployment\nDEP-0001" },
			});
		});

		const picker = document.querySelector('input[type="file"]') as HTMLInputElement;
		await act(async () => {
			fireEvent.change(picker, {
				target: { files: [new File(["x"], "plan.pdf", { type: "application/pdf" })] },
			});
		});

		expect(sent).toHaveBeenCalledTimes(1);
		const [url, init] = sent.mock.calls[0] as [string, RequestInit];

		expect(url).toBe("/api/method/upload_file");
		expect((init.headers as Record<string, string>)["X-Frappe-CSRF-Token"]).toBe("tok-1");

		const body = init.body as FormData;
		// Private, always: an operational document is a plan, an assessment or
		// evidence, and none of those is public because somebody missed a box.
		expect(body.get("is_private")).toBe("1");
		expect(body.get("doctype")).toBe("VMMS Deployment");
		expect(body.get("docname")).toBe("DEP-0001");

		vi.unstubAllGlobals();
	});
});

/* ------------------------------------------------------- terms of reference */

describe("the terms of reference gallery", () => {
	const terms = (over: Partial<TermsOfReference> = {}): TermsOfReference =>
		({
			name: "TOR-2026-041",
			tor_key: "TOR-2026-041",
			tor_name: "Tana River Flood Response — Wave 3",
			is_active: true,
			docstatus: 1,
			is_draft: false,
			is_submitted: true,
			is_cancelled: false,
			is_offered: true,
			is_governed: true,
			approval_state: "Approved",
			amended_from: null,
			supersedes: null,
			missing: [],
			has_no_resources: false,
			expected_start_date: "2026-09-14",
			expected_end_date: "2026-09-25",
			section_counts: {
				stakeholders: 0,
				objectives: 4,
				expected_outputs: 0,
				approach_methods: 0,
				itinerary: 6,
				resources: 2,
			},
			purpose: "Support flood-affected households with health, relief and protection services.",
			responsibilities: null,
			geo_scope: "GEO-1",
			geo_scope_path: "Tana River — Tanzania Red Cross Society",
			default_duration_days: 12,
			approval_mode: "routed",
			requires_approver: true,
			required_certifications: [],
			desirable_certifications: [],
			project: "PROJ-1",
			project_name: "Flood Preparedness and Response",
			...over,
		}) as TermsOfReference;

	it("splits a new terms document into visible sections and reports completion", async () => {
		reads.set(API.branchTerms, { count: 0, terms: [], states: [] });
		reads.set(API.branchProjects, { projects: [] });
		reads.set(API.torMethodologies, {
			methodologies: [],
			certification_types: [],
			currencies: [],
			units: [],
			funding_statuses: [],
		});

		show(<TermsList />, "/admin/deployments/terms?new=1");

		const progress = screen.getByRole("progressbar", { name: "Form completion" });
		expect(progress.getAttribute("aria-valuenow")).toBe("0");
		expect(screen.getAllByRole("tab")).toHaveLength(5);
		expect(screen.getByRole("tab", { name: /Overview & scope/ }).getAttribute("aria-selected")).toBe("true");
		expect(screen.getByRole("tab", { name: /Review & create/ })).toBeTruthy();

		fireEvent.change(screen.getByLabelText(/What your society calls this piece of work/), {
			target: { value: "Flood response" },
		});
		fireEvent.change(screen.getByLabelText(/What a deployment under these terms is for/), {
			target: { value: "Reach isolated households" },
		});
		fireEvent.change(screen.getByLabelText(/What happened, what is needed/), {
			target: { value: "Seasonal flooding has isolated three communities." },
		});

		expect(progress.getAttribute("aria-valuenow")).toBe("1");
		await act(async () => {
			fireEvent.click(screen.getByRole("tab", { name: /Roles & outcomes/ }));
		});
		expect(screen.getByRole("tab", { name: /Roles & outcomes/ }).getAttribute("aria-selected")).toBe("true");
		expect(screen.getByText("Responsibilities")).toBeTruthy();
	});

	it("draws each terms of reference as a document, with the approved facts on it", () => {
		reads.set(API.branchTerms, { count: 1, terms: [terms()], states: [] });

		show(<TermsList />, "/admin/deployments/terms");

		expect(screen.getByText("TOR-2026-041")).toBeTruthy();
		expect(screen.getByText("Tana River Flood Response — Wave 3")).toBeTruthy();
		expect(screen.getByText("Flood Preparedness and Response")).toBeTruthy();
		expect(screen.getByText(/Support flood-affected households/)).toBeTruthy();
		// The geo scope, rendered through `format.geoPath`: core writes a full
		// path deepest-first with em dashes, and this is what a reader sees.
		expect(screen.getByText("Tana River · Tanzania Red Cross Society")).toBeTruthy();
		// And it opens the document rather than an editor.
		expect(
			screen.getByRole("link", { name: /Tana River Flood Response/ }).getAttribute("href"),
		).toBe("/admin/deployments/terms/TOR-2026-041");
	});

	it("stamps each state from the exact approval state, never from a stage label", () => {
		reads.set(API.branchTerms, {
			count: 4,
			terms: [
				terms({ name: "T1", tor_name: "Approved one", approval_state: "Approved" }),
				terms({ name: "T2", tor_name: "Reviewing one", approval_state: "In Review" }),
				terms({
					name: "T3",
					tor_name: "Draft one",
					docstatus: 0,
					is_draft: true,
					is_submitted: false,
					approval_state: null,
				}),
				terms({ name: "T4", tor_name: "Rejected one", approval_state: "Rejected" }),
			],
			states: ["Draft", "Submitted", "In Review", "Approved", "Rejected", "Withdrawn", "Expired"],
		});

		show(<TermsList />, "/admin/deployments/terms");

		// One stamp per card, plus the same word in the filter's option list.
		expect(screen.getAllByText("Approved").length).toBeGreaterThan(0);
		expect(screen.getByText("In review")).toBeTruthy();
		expect(screen.getAllByText("Draft").length).toBeGreaterThan(0);
		expect(screen.getAllByText("Rejected").length).toBeGreaterThan(0);
		// A draft is the one you continue writing; the rest you open or review.
		expect(screen.getByText("Continue writing →")).toBeTruthy();
		expect(screen.getByText("Review document →")).toBeTruthy();
	});

	it("offers only the seven exact states as a filter, from the server's own list", async () => {
		const states = ["Draft", "Submitted", "In Review", "Approved", "Rejected", "Withdrawn", "Expired"];
		reads.set(API.branchTerms, { count: 0, terms: [], states });

		show(<TermsList />, "/admin/deployments/terms");

		const options = Array.from(
			(screen.getByLabelText("Approval state") as HTMLSelectElement).options,
		).map((option) => option.value);

		expect(options).toEqual(["", ...states]);

		await act(async () => {
			fireEvent.change(screen.getByLabelText("Approval state"), {
				target: { value: "In Review" },
			});
		});

		expect(argsFor(API.branchTerms)).toMatchObject({ state: "In Review" });
	});

	it("says a society that routes nothing has submitted terms rather than draft ones", () => {
		reads.set(API.branchTerms, {
			count: 1,
			// Frozen wording, and no approval workflow governs terms here.
			terms: [terms({ is_governed: false, approval_state: null })],
			states: [],
		});

		show(<TermsList />, "/admin/deployments/terms");

		expect(screen.getByText("Submitted")).toBeTruthy();
	});
});
