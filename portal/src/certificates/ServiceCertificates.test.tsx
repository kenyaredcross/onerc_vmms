import { fireEvent, screen, waitFor } from "@testing-library/react";
import { FrappeContext, type FrappeConfig } from "frappe-react-sdk";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { mount } from "../test/harness";
import { CERTIFICATE_API, ServiceCertificatePanel, ServiceCertificateReviews } from "./ServiceCertificates";

const reads = new Map<string, unknown>();
const post = vi.fn();
vi.mock("frappe-react-sdk", async (importOriginal) => {
	const actual = (await importOriginal()) as { default: Record<string, unknown> };
	return { ...actual.default, default: actual.default,
		useFrappeGetCall: (path: string, _params?: unknown, key?: string | null) => ({
			data: key === null ? undefined : { message: reads.get(path) }, error: null, isLoading: false,
			mutate: () => Promise.resolve(),
		}),
	};
});

const request = {
	name: "CSR-00001", applicant_name: "Alex Morgan", applicant_kind: "Volunteer", branch: "Central",
	request_date: "2026-10-02", service_from: "2020-01-01", service_to: "2026-10-02",
	position: "Support", service_summary: "Branch service", review_note: "", status: "Pending", generation_status: "Not issued",
	can_review: false, can_generate: false, can_download: false, decisions: [],
	service_history: [], service_hours: 0, additional_answers: [], certificate_html: "<p>Certificate preview</p>",
};

function show(ui: React.ReactNode) {
	return mount(<FrappeContext.Provider value={{ call: { post } } as unknown as FrappeConfig}>{ui}</FrappeContext.Provider>);
}

beforeEach(() => {
	reads.clear(); post.mockReset(); post.mockResolvedValue({ message: request });
	reads.set(CERTIFICATE_API.options, { applicant_name: "Alex Morgan", today: "2026-10-02", custom_fields: [],
		choices: [{ kind: "Volunteer", record: "VOL-00001", branch: "Central", joined_on: "2020-01-01" }] });
	reads.set(CERTIFICATE_API.mine, { requests: [], has_more: false });
	reads.set(CERTIFICATE_API.detail, request);
});

describe("Certificate of Service", () => {
	it("opens the occasional profile action and submits the person's selected registration", async () => {
		show(<ServiceCertificatePanel />);
		expect(screen.queryByRole("dialog")).toBeNull();
		fireEvent.click(screen.getByRole("button", { name: "Request certificate" }));
		expect(screen.getByLabelText("Name")).toHaveProperty("readOnly", true);
		fireEvent.change(screen.getByLabelText("Position"), { target: { value: "Community support" } });
		fireEvent.click(screen.getByRole("button", { name: "Submit request" }));
		await waitFor(() => expect(post).toHaveBeenCalledWith(CERTIFICATE_API.submit, expect.objectContaining({
			kind: "Volunteer", record: "VOL-00001", service_from: "2020-01-01", service_to: "2026-10-02", position: "Community support",
		})));
	});

	it("shows a pending request without offering a duplicate", () => {
		reads.set(CERTIFICATE_API.mine, { requests: [request], has_more: false });
		show(<ServiceCertificatePanel />);
		expect(screen.getByText("Pending review")).toBeTruthy();
		expect(screen.queryByRole("button", { name: "Request certificate" })).toBeNull();
		fireEvent.click(screen.getByRole("button", { name: "View request" }));
		expect(screen.queryByRole("button", { name: "Approve" })).toBeNull();
	});

	it("offers the issued PDF and exposes the rejection reason", () => {
		reads.set(CERTIFICATE_API.mine, { requests: [{ ...request, status: "Approved", can_download: true }], has_more: false });
		show(<ServiceCertificatePanel />);
		expect(screen.getByRole("link", { name: "Download certificate" }).getAttribute("href")).toContain("download?name=CSR-00001");
	});

	it("requires verification notes before approving and a separate reason before rejecting", async () => {
		reads.set(CERTIFICATE_API.reviews, { requests: [{ ...request, can_review: true }], has_more: false });
		reads.set(CERTIFICATE_API.detail, { ...request, can_review: true });
		show(<ServiceCertificateReviews />);
		fireEvent.click(screen.getByRole("button", { name: "View / Review" }));
		expect(screen.getByRole("button", { name: "Approve" })).toHaveProperty("disabled", true);
		expect(screen.getByRole("button", { name: "Reject" })).toHaveProperty("disabled", true);
		fireEvent.change(screen.getByLabelText("Service verification notes"), { target: { value: "Checked branch register" } });
		fireEvent.click(screen.getByRole("button", { name: "Approve" }));
		await waitFor(() => expect(post).toHaveBeenCalledWith(CERTIFICATE_API.decide, expect.objectContaining({ decision: "Approved", review_note: "Checked branch register" })));
	});

	it("allows an authorised reviewer to retry generation without deciding again", async () => {
		const failed = { ...request, status: "Approved", generation_status: "Failed", can_generate: true };
		reads.set(CERTIFICATE_API.reviews, { requests: [failed], has_more: false });
		reads.set(CERTIFICATE_API.detail, failed);
		show(<ServiceCertificateReviews />);
		fireEvent.click(screen.getByRole("button", { name: "Generate" }));
		expect(screen.queryByRole("button", { name: "Approve" })).toBeNull();
		fireEvent.click(screen.getByRole("button", { name: "Generate certificate" }));
		await waitFor(() => expect(post).toHaveBeenCalledWith(CERTIFICATE_API.generate, { name: request.name }));
	});
});
