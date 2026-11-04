import { fireEvent, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { mount } from "../test/harness";
import {
	BackgroundFields,
	backgroundFrom,
	backgroundLines,
	backgroundPayload,
	blankEducation,
	blankExperience,
	blankLicence,
	emptyBackground,
} from "./Background";

function Editor() {
	const [value, setValue] = useState(() => ({
		...emptyBackground(),
		education: [blankEducation()],
		work_experience: [blankExperience()],
		licences: [blankLicence()],
	}));
	return (
		<BackgroundFields
			value={value}
			onChange={(patch) => setValue((held) => ({ ...held, ...patch }))}
		/>
	);
}

describe("registration background parity", () => {
	it("retains grades, subjects, work locations and certifications through reload and save", () => {
		const held = {
			education: [
				{ ...blankEducation(), institution: "School", class_per: "A-", maj_opt_subj: "Nursing" },
			],
			work_experience: [{ ...blankExperience(), organization: "Clinic", location: "Nakuru" }],
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
		};
		const reloaded = backgroundFrom(held);
		expect(backgroundPayload(reloaded)).toMatchObject(held);
		const lines = backgroundLines(undefined, reloaded)
			.map((line) => line.value)
			.join(" ");
		expect(lines).toContain("A-");
		expect(lines).toContain("Nursing");
		expect(lines).toContain("Nakuru");
		expect(lines).toContain("First aid");
	});

	it("sends an empty certification list when the last certification is removed", () => {
		expect(backgroundPayload(emptyBackground())).toHaveProperty("certifications", []);
	});

	it("provides labelled controls for the legacy fields and editable certification expiry", () => {
		mount(<Editor />);
		fireEvent.change(screen.getByLabelText("Grade or percentage"), { target: { value: "A-" } });
		fireEvent.change(screen.getByLabelText("Major or subjects"), { target: { value: "Nursing" } });
		fireEvent.change(screen.getByLabelText("Work location"), { target: { value: "Nakuru" } });
		fireEvent.change(screen.getByLabelText("Licence qualification"), {
			target: { value: "Registered nurse" },
		});
		fireEvent.change(screen.getByLabelText("Licence description"), {
			target: { value: "Practice licence" },
		});
		fireEvent.click(screen.getByRole("button", { name: "Add a certification" }));
		fireEvent.change(screen.getByLabelText(/Certification name/), {
			target: { value: "First aid" },
		});
		fireEvent.change(screen.getByLabelText("Certification issuer"), {
			target: { value: "Training centre" },
		});
		fireEvent.change(screen.getByLabelText("Certification issued on"), {
			target: { value: "2025-01-01" },
		});
		fireEvent.click(screen.getByLabelText("This certification expires"));
		fireEvent.change(screen.getByLabelText("Certification expires on"), {
			target: { value: "2027-01-01" },
		});
		expect((screen.getByLabelText("Grade or percentage") as HTMLInputElement).value).toBe("A-");
		expect((screen.getByLabelText("Work location") as HTMLInputElement).value).toBe("Nakuru");
		expect((screen.getByLabelText("Certification expires on") as HTMLInputElement).value).toBe(
			"2027-01-01",
		);
		fireEvent.click(screen.getByLabelText("This certification expires"));
		expect((screen.getByLabelText("Certification expires on") as HTMLInputElement).value).toBe("");
		expect((screen.getByLabelText("Certification expires on") as HTMLInputElement).disabled).toBe(
			true,
		);
	});
});

it("searches the full profession list and saves the selected match", () => {
	function Professions() {
		const [value, setValue] = useState(emptyBackground());
		return <><BackgroundFields value={value} onChange={(patch) => setValue((held) => ({...held, ...patch}))} options={{genders: [], disabilities: [], licence_types: [], education_levels: [], driving_licence_classes: [], professions: [...Array.from({length: 90}, (_, index) => `Profession ${index}`), "Psychological Counsellor"]}} /><output data-testid="profession">{value.profession}</output></>;
	}
	mount(<Professions />);
	const search = screen.getByLabelText(/^Profession/);
	fireEvent.change(search, {target: {value: "psychological"}});
	fireEvent.click(screen.getByRole("option", {name: "Psychological Counsellor"}));
	expect(screen.getByTestId("profession").textContent).toBe("Psychological Counsellor");
});
