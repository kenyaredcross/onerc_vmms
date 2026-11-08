import { fireEvent, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { mount } from "../test/harness";
import { RowList } from "./Background";
import { TextInput } from "./form";

type Row = { institution: string };

function Editor() {
	const [rows, setRows] = useState<Row[]>([
		{ institution: "Alliance High School" },
		{ institution: "University of Nairobi" },
		{ institution: "Kenyatta University" },
	]);
	return (
		<RowList
			title="Education"
			noun="Education"
			rows={rows}
			onRows={setRows}
			blank={() => ({ institution: "" })}
			add="Add another education record"
			renderRow={(row, index, set) => (
				<TextInput
					id={`place-${index}`}
					value={row.institution}
					onChange={(value) => set("institution", value)}
				/>
			)}
		/>
	);
}

describe("removing an entry from a repeating section", () => {
	it("heads every entry with its number and a remove button that names it", () => {
		mount(<Editor />);

		expect(screen.getByText("Education 1")).toBeTruthy();
		expect(screen.getByText("Education 3")).toBeTruthy();
		expect(screen.getByRole("button", { name: "Remove education 1" })).toBeTruthy();
		expect(screen.getByRole("button", { name: "Remove education 3" })).toBeTruthy();
	});

	it("removes exactly the entry the button names, and renumbers the rest", () => {
		mount(<Editor />);

		fireEvent.click(screen.getByRole("button", { name: "Remove education 2" }));

		expect(screen.queryByDisplayValue("University of Nairobi")).toBeNull();
		expect(screen.getByDisplayValue("Alliance High School")).toBeTruthy();
		expect(screen.getByDisplayValue("Kenyatta University")).toBeTruthy();
		expect(screen.queryByRole("button", { name: "Remove education 3" })).toBeNull();
		expect(screen.getByRole("button", { name: "Remove education 2" })).toBeTruthy();
	});
});
