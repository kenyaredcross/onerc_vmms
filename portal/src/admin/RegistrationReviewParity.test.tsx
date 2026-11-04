import { fireEvent, screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import { mount } from "../test/harness";
import { blankEducation, blankExperience, blankLicence } from "../ui/Background";

const reads = new Map<string, unknown>();
vi.mock("frappe-react-sdk", async (importOriginal) => {
	const actual = (await importOriginal()) as { default: Record<string, unknown> };
	return {
		...actual.default,
		default: actual.default,
		useFrappeGetCall: (path: string, _params?: unknown, key?: string | null) => ({
			data: key === null ? undefined : { message: reads.get(path) },
			error: null,
			isLoading: false,
			isValidating: false,
			mutate: () => Promise.resolve(undefined),
		}),
	};
});
const Review = (await import("./ReviewQueue")).default;
const Person = (await import("./Person")).default;
const details = {
	marital_status: "Married",
	blood_group: "O+",
	number_of_dependants: 0,
	allergies: [{ allergy: "Penicillin" }],
	supporting_documents: [
		{ type: "CV", document_name: "Curriculum vitae", attachment: "/private/files/cv.pdf" },
	],
};
const background = {
	education: [
		{
			...blankEducation(),
			institution: "County College",
			class_per: "A-",
			maj_opt_subj: "Nursing",
		},
	],
	training: [],
	certifications: [
		{
			certification_name: "First aid",
			organization: "Training centre",
			description: "Practical assessment",
			expire: true,
			issue_date: "2025-01-01",
			expiration_date: "2027-01-01",
		},
	],
	work_experience: [{ ...blankExperience(), organization: "County hospital", location: "Nakuru" }],
	licences: [
		{ ...blankLicence(), qualification: "Registered nurse", description: "Practice licence" },
	],
	driving_licences: [],
	references: [],
};
function approval(kind: "volunteer" | "member") {
	reads.set(API.approvalStatus, {
		name: "APP-1",
		doctype: kind === "volunteer" ? "VMMS Volunteer Application" : "VMMS Membership",
		state: "In Review",
		geo_path: "County",
		stage: null,
		decisions: [],
		applicant: { full_name: "Amina Otieno", red_profile: "RP-1" },
	});
}
function openReview(kind: "volunteer" | "member") {
	approval(kind);
	return mount(
		<Routes>
			<Route path="/admin/queue/:kind/:name" element={<Review />} />
		</Routes>,
		{
			route: `/admin/queue/${kind === "volunteer" ? "volunteers" : "members"}/APP-1?tab=applicant`,
		},
	);
}
describe("restored facts available to reviewers", () => {
	beforeEach(() => reads.clear());
	it("shows personal details and preserved background before a volunteer decision", () => {
		reads.set(API.applicationDecision, {
			name: "APP-1",
			full_name: "Amina Otieno",
			identifications: [],
			answers: [],
			skills: [],
			languages: [],
			availability: [],
			motivation: [],
			personal_details: details,
			background,
		});
		openReview("volunteer");
		expect(screen.getByText("Married")).toBeTruthy();
		expect(screen.getByText(/Penicillin/)).toBeTruthy();
		const href = screen.getByRole("link", { name: /cv\.pdf/ }).getAttribute("href")!;
		const evidence = new URL(href, "http://localhost");
		expect(evidence.pathname).toBe("/api/method/vmmsx.api.registration.download_evidence");
		expect(evidence.searchParams.get("attachment")).toBe("/private/files/cv.pdf");

		// Education and experience is its own tab, after the applicant.
		fireEvent.click(screen.getByRole("tab", { name: "Education and experience" }));
		expect(screen.getByText("A-")).toBeTruthy();
		expect(screen.getByText("Nursing")).toBeTruthy();
		expect(screen.getByText("Nakuru")).toBeTruthy();
		expect(screen.getByText("First aid")).toBeTruthy();
	});
	it("shows restored person facts on a membership review", () => {
		reads.set(API.membershipReview, {
			applicant: { full_name: "Amina Otieno", personal_details: details },
			answers: [],
		});
		openReview("member");
		expect(screen.getByText("O+")).toBeTruthy();
		expect(screen.getByText("Married")).toBeTruthy();
		expect(screen.getByText(/Penicillin/)).toBeTruthy();
	});
	it("shows restored member facts on the dossier overview", () => {
		reads.set(API.memberDossier, {
			member: "MEM-1",
			as_of: "2026-11-02",
			identity: { full_name: "Amina Otieno", personal_details: details },
			standing: {
				status: "Active",
				current_geo_paths: [],
				current_count: 1,
				lapsed_count: 0,
				visible_count: 1,
			},
			memberships: [],
			history: [],
			notes: null,
		});
		mount(
			<Routes>
				<Route path="/admin/people/:kind/:name" element={<Person />} />
			</Routes>,
			{ route: "/admin/people/member/MEM-1" },
		);
		expect(screen.getByText("Married")).toBeTruthy();
		expect(screen.getByText(/Penicillin/)).toBeTruthy();
	});
});
