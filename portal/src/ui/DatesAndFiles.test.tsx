import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("frappe-react-sdk", async (importOriginal) => {
	const actual = (await importOriginal()) as { default: Record<string, unknown> };
	return {
		...actual.default,
		default: actual.default,
		useFrappeFileUpload: () => ({ upload: vi.fn(), loading: false }),
	};
});

const { backgroundDateGaps, emptyBackground, endsBefore } = await import("./Background");
const { PrivateUpload } = await import("./form");

/** An end date is never earlier than its start, anywhere on the background form. */
describe("date order", () => {
	it("compares only when both dates are given", () => {
		expect(endsBefore("2026-05-01", "2026-04-30")).toBe(true);
		expect(endsBefore("2026-05-01", "2026-05-01")).toBe(false);
		expect(endsBefore("", "2026-04-30")).toBe(false);
	});

	it("reports each row that ends before it starts, and ignores open-ended rows", () => {
		const value = {
			...emptyBackground(),
			licences: [
				{ license_type: "", license_name: "Nursing", institution: "", registration_no: "", valid_from: "2026-05-01", valid_to: "2026-01-01", does_not_expire: false, attachment: null },
				{ license_type: "", license_name: "Pharmacy", institution: "", registration_no: "", valid_from: "2026-05-01", valid_to: "2026-01-01", does_not_expire: true, attachment: null },
			],
			certifications: [
				{ certification_name: "First aid", organization: "", description: "", expire: true, issue_date: "2026-03-01", expiration_date: "2025-03-01" },
			],
			education: [
				{ institution: "KCA", level: "", qualification: "", started_in: 2019, finished_in: 2015, is_ongoing: false, attachment: null },
			],
		};

		expect(backgroundDateGaps(value).map((gap) => gap.anchor)).toEqual(["ed-to-0", "cert-until-0", "lc-to-0"]);
	});
});

describe("an attached file", () => {
	it("is shown by its name and, for a picture, as itself", () => {
		render(<PrivateUpload id="doc" value="/private/files/good%20conduct.png" onChange={() => {}} />);

		expect(screen.queryByText("Attached")).toBeNull();
		expect(screen.getByRole("link", { name: /good conduct\.png/ }).getAttribute("href")).toBe(
			"/private/files/good%20conduct.png",
		);
		expect(screen.getByRole("img", { name: "The attached file" })).toBeTruthy();
	});
});

describe("professional profiles", () => {
	it("asks LinkedIn, GitHub and profession together, and flags an address that is not a link", async () => {
		const { BackgroundFields, profileLinkGaps } = await import("./Background");
		render(
			<BackgroundFields
				value={emptyBackground()}
				onChange={() => {}}
				profiles={{ linkedin: "linkedin.com/in/asha", github: "" }}
				onProfiles={() => {}}
			/>,
		);

		expect(screen.getByText("Professional profiles")).toBeTruthy();
		expect(screen.getByLabelText("LinkedIn profile")).toBeTruthy();
		expect(screen.getByPlaceholderText("https://github.com/username")).toBeTruthy();
		expect(screen.getByLabelText("Profession")).toBeTruthy();
		expect(screen.getByText("Enter the full address, starting with https://")).toBeTruthy();
		expect(profileLinkGaps({ linkedin: "linkedin.com/in/asha", github: "" }).map((gap) => gap.anchor)).toEqual(["bg-linkedin"]);
	});
});
