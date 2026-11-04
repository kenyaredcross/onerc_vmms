import { useState } from "react";
import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mount } from "../test/harness";
import { RegistrationDetails, RegistrationDetailsSummary, registrationDetailGaps } from "./RegistrationDetails";
import type { PersonalDetails } from "../portal/types";

function Editor() {
	const [value, setValue] = useState<PersonalDetails>({
		number_of_dependants: 0,
		allergies: [{ allergy: "Penicillin" }],
	});
	return (
		<>
			<RegistrationDetails value={value} onChange={setValue} />
			<output data-testid="held">{JSON.stringify(value)}</output>
		</>
	);
}

describe("restored registration details", () => {
	it("edits structured personal facts without dropping other fields or zero dependants", () => {
		mount(<Editor />);
		fireEvent.change(screen.getByLabelText("Other names"), { target: { value: "Wanjiru" } });
		fireEvent.change(screen.getByLabelText("Marital status"), { target: { value: "Married" } });
		expect(JSON.parse(screen.getByTestId("held").textContent!)).toMatchObject({
			middle_name: "Wanjiru",
			marital_status: "Married",
			number_of_dependants: 0,
			allergies: [{ allergy: "Penicillin" }],
		});
	});
	it("distinguishes required evidence from a document name without an upload", () => {
		const required = [{ key: "CV", label: "CV", is_required: true }];
		expect(
			registrationDetailGaps(
				{ supporting_documents: [{ type: "CV", document_name: "My CV", attachment: "" }] },
				required,
			),
		).toContain("Upload CV");
		expect(
			registrationDetailGaps(
				{
					supporting_documents: [
						{ type: "CV", document_name: "My CV", attachment: "/private/files/cv.pdf" },
					],
				},
				required,
			),
		).toEqual([]);
	});
	it("requires the configured name for Other evidence without discarding free-text skills", () => {
		expect(registrationDetailGaps({supporting_documents:[{type:"Other",document_name:"",attachment:"/private/files/letter.pdf"}]},[{key:"Other",label:"Other",is_required:false,requires_name:true}])).toEqual(["Name the Other document"]);
		mount(<Editor/>);
		fireEvent.click(screen.getByRole("button", {name:"Add another skill"}));
		fireEvent.change(screen.getByLabelText("Additional skill 1"),{target:{value:"Community radio"}});
		expect(JSON.parse(screen.getByTestId("held").textContent!)).toMatchObject({additional_skills:[{additional_skill:"Community radio"}],number_of_dependants:0});
	});

});

it("offers configured blood groups and preserves an existing value outside the register", () => {
	mount(<RegistrationDetails value={{blood_group: "Legacy result"}} onChange={() => {}} bloodGroups={["A+", "O-", "Don't Know"]} />);
	const field = screen.getByRole("combobox", {name: "Blood group"}) as HTMLSelectElement;
	expect(Array.from(field.options).map((option) => option.value)).toEqual(["", "A+", "O-", "Don't Know", "Legacy result"]);
	expect(field.value).toBe("Legacy result");
});

it("retains other names and blood group in review summaries after rearranging the form", () => {
	mount(<RegistrationDetailsSummary value={{middle_name: "Wanjiru", blood_group: "AB-"}} />);
	expect(screen.getByText("Other names")).toBeTruthy();
	expect(screen.getByText("Wanjiru")).toBeTruthy();
	expect(screen.getByText("Blood group")).toBeTruthy();
	expect(screen.getByText("AB-")).toBeTruthy();
});

it("gives a required document its own field, apart from the supporting documents", () => {
	const types = [
		{ key: "Good Conduct", label: "Good Conduct", is_required: true },
		{ key: "CV", label: "CV", is_required: false },
	];
	mount(
		<RegistrationDetails
			value={{ supporting_documents: [{ type: "Good Conduct", document_name: "", attachment: "/private/files/conduct.pdf" }] }}
			onChange={() => {}}
			documentTypes={types}
			documentsOnly
		/>,
	);

	expect(screen.getByText("Required documents")).toBeTruthy();
	expect(screen.getByLabelText(/Good Conduct/)).toBeTruthy();
	// The uploaded certificate shows in its own field, not as a row in the list.
	expect(screen.getByRole("link", { name: /conduct\.pdf/ })).toBeTruthy();
	expect(screen.queryByLabelText("Document type")).toBeNull();

	// The list offers only the optional types.
	fireEvent.click(screen.getByRole("button", { name: "Add supporting document" }));
});

it("lists only optional types when adding a supporting document", () => {
	function WithTypes() {
		const [value, setValue] = useState<PersonalDetails>({});
		return (
			<RegistrationDetails
				value={value}
				onChange={setValue}
				documentTypes={[
					{ key: "Good Conduct", label: "Good Conduct", is_required: true },
					{ key: "CV", label: "CV", is_required: false },
				]}
				documentsOnly
			/>
		);
	}
	mount(<WithTypes />);
	fireEvent.click(screen.getByRole("button", { name: "Add supporting document" }));
	const select = screen.getByLabelText("Document type") as HTMLSelectElement;
	expect(Array.from(select.options).map((option) => option.value)).toEqual(["", "CV"]);
});

