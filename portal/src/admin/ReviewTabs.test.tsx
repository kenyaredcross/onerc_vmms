import { Route, Routes } from "react-router-dom";
import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import { mount } from "../test/harness";
import type { ApprovalStatus } from "../portal/types";

/**
 * What a reviewer can read on one application: the tabs in the order the form
 * asks, every file the applicant attached shown as itself, the wording of each
 * declaration version they agreed to, and the record's activity below it all.
 */
const reads = new Map<string, unknown>();
const asked: string[] = [];

vi.mock("frappe-react-sdk", async (importOriginal) => {
	const actual = (await importOriginal()) as { default: Record<string, unknown> };

	return {
		...actual.default,
		default: actual.default,
		useFrappeGetCall: (path: string, _params?: unknown, swrKey?: string | null) => {
			if (swrKey !== null) asked.push(path);
			return {
				data: swrKey === null ? undefined : { message: reads.get(path) },
				error: null,
				isLoading: false,
				isValidating: false,
				mutate: () => Promise.resolve(undefined),
			};
		},
	};
});

const ApplicationReview = (await import("./ReviewQueue")).default;

const STATUS = {
	doctype: "VMMS Volunteer Application",
	name: "APP-0001",
	state: "In Review",
	is_open: true,
	is_terminal: false,
	geo_node: "GEO-1",
	geo_path: "Kenya Red Cross Society › Nairobi",
	applicant: {
		doctype: "Red Profile",
		name: "RP-1",
		red_profile: "RP-1",
		full_name: "Asha Mwangi",
		email: "asha@example.com",
		phone: null,
		photo: null,
	},
	stage: null,
	can_act: false,
	approver_count: 0,
	approvers: [],
	escalated_to: [],
	allow_withdrawal: true,
	can_withdraw: false,
	decisions: [],
} as unknown as ApprovalStatus;

const FILE = (table: string, index: number, group: string, label: string, name: string) => ({
	key: `${table}:${index}`,
	table,
	index,
	group,
	label,
	attachment: `/private/files/${name}`,
	file_name: name,
	url: `/api/method/vmmsx.api.registration.download_evidence?doctype=VMMS+Volunteer+Application&name=APP-0001&attachment=%2Fprivate%2Ffiles%2F${name}`,
});

function open(tab: string) {
	reads.clear();
	asked.length = 0;
	reads.set(API.approvalStatus, STATUS);
	reads.set(API.applicationDecision, {
		name: "APP-0001",
		full_name: "Asha Mwangi",
		applied_on: "2026-08-19",
		answers: [],
		skills: [],
		languages: [],
		availability: [],
		motivation: [],
		identifications: [{ id_type: "national_id", id_type_name: "National ID", id_number: "12345678", attachment: null, is_primary: true }],
		emergency_contacts: [],
		guardian_consents: [],
		is_minor: false,
		disability_status: "Yes",
		disabilities: ["Visual impairment"],
		disability_needs: "Large print forms",
		citizenship_status: "Citizen",
		personal_details: { linkedin: "https://www.linkedin.com/in/asha", github: "https://github.com/asha" },
		background: {
			education: [{ institution: "KCA", level: "Degree", qualification: "BSc IT", started_in: 2015, finished_in: 2019, is_ongoing: false }],
			training: [],
			work_experience: [],
			licences: [],
			driving_licences: [],
			references: [],
		},
		declarations: [
			{
				declaration: "code",
				title: "Code of Conduct",
				version: "3",
				declaration_version: "code-3",
				source: "Text",
				body: "<p>I will respect the seven principles.</p>",
				external_url: null,
				accepted: true,
				accepted_on: "2026-08-18",
			},
		],
		attachments: [
			FILE("identifications", 0, "Identification", "National ID 12345678", "id-front.png"),
			FILE("supporting_documents", 0, "Supporting documents", "Good Conduct", "good-conduct.pdf"),
			FILE("education", 0, "Education", "BSc IT · KCA", "degree.pdf"),
		],
	});
	reads.set(API.auditTrail, [
		{
			on: "2026-08-19 10:15:00",
			by: "Asha Mwangi",
			record: "Personal details",
			kind: "changed",
			changes: [{ field: "Place of Work", from: null, to: "Kenya Red Cross" }],
		},
		{ on: "2026-08-18 09:00:00", by: "Asha Mwangi", record: "Application", kind: "created", changes: [] },
	]);

	return mount(
		<Routes>
			<Route path="/admin/queue/:kind/:name" element={<ApplicationReview />} />
		</Routes>,
		{ route: `/admin/queue/volunteers/APP-0001${tab ? `?tab=${tab}` : ""}` },
	);
}

beforeEach(() => {
	reads.clear();
	window.localStorage.clear();
});

describe("the application tabs", () => {
	it("puts education and experience between the applicant and additional info", () => {
		open("");

		const labels = screen.getAllByRole("tab").map((tab) => tab.textContent?.replace(/\d+$/, "").trim());
		expect(labels.slice(0, 3)).toEqual(["Applicant", "Education and experience", "Additional Info"]);
		expect(labels).toContain("Documents");
		// The change log is not a tab: it sits at the foot of every tab.
		expect(labels).not.toContain("History");
		// The decision is not a tab either: it sits beside every tab.
		expect(labels).not.toContain("Decision");
		expect(screen.getByRole("complementary", { name: "Decision" })).toBeTruthy();
	});

	it("shows everything the applicant entered, with profile links that can be clicked", () => {
		open("applicant");

		expect(screen.getByText("Citizen")).toBeTruthy();
		expect(screen.getByText("Visual impairment")).toBeTruthy();
		expect(screen.getByText("Large print forms")).toBeTruthy();
		// The profile links are under Professional profiles, not here.
		expect(screen.queryByRole("link", { name: "https://github.com/asha" })).toBeNull();
		// The identification's own file, by name, beside the number.
		expect(screen.getByRole("link", { name: /id-front\.png/ })).toBeTruthy();
	});

	it("groups LinkedIn, GitHub and profession under Professional profiles", () => {
		open("background");

		expect(screen.getByText("Professional profiles")).toBeTruthy();
		expect(screen.getByRole("link", { name: "https://www.linkedin.com/in/asha" }).getAttribute("target")).toBe("_blank");
		expect(screen.getByRole("link", { name: "https://github.com/asha" })).toBeTruthy();
	});

	it("shows the file on the row it belongs to", () => {
		open("background");

		expect(screen.getByRole("columnheader", { name: "File" })).toBeTruthy();
		expect(screen.getByRole("link", { name: /degree\.pdf/ }).getAttribute("href")).toContain("inline=1");
	});

	it("lists every attached document, shown rather than named", () => {
		open("documents");

		expect(screen.getByText("Supporting documents")).toBeTruthy();
		expect(screen.getByText("Good Conduct")).toBeTruthy();
		const picture = screen.getByRole("img", { name: "National ID 12345678" });
		expect(picture.getAttribute("src")).toContain("inline=1");
	});

	it("shows the wording of the declaration version that was agreed to", () => {
		open("safeguarding");

		expect(screen.getByText(/Agreed · version 3/)).toBeTruthy();
		fireEvent.click(screen.getByText("Read version 3"));
		expect(screen.getByText("I will respect the seven principles.")).toBeTruthy();
	});

	it("keeps the activity off, and unread, until it is switched on", () => {
		open("applicant");

		const toggle = screen.getByRole("switch", { name: "Show activity" });
		expect(toggle.getAttribute("aria-checked")).toBe("false");
		expect(asked).not.toContain(API.auditTrail);
		expect(screen.queryByText(/created this application/)).toBeNull();
	});

	it("stays on for the next application once switched on", () => {
		const first = open("applicant");
		fireEvent.click(screen.getByRole("switch", { name: "Show activity" }));
		first.unmount();

		open("applicant");
		expect(screen.getByRole("switch", { name: "Show activity" }).getAttribute("aria-checked")).toBe("true");
		expect(screen.getByText(/created this application/)).toBeTruthy();
	});

	it.each(["applicant", "documents"])("shows the activity at the foot of the %s tab once switched on", (tab) => {
		open(tab);
		fireEvent.click(screen.getByRole("switch", { name: "Show activity" }));

		const activity = screen.getByRole("region", { name: "Activity" });
		expect(activity.textContent).toMatch(/Asha Mwangi changed Place of Work on personal details from empty to Kenya Red Cross/);
		expect(activity.textContent).toMatch(/Asha Mwangi created this application/);
		expect(asked).toContain(API.auditTrail);
	});
});
