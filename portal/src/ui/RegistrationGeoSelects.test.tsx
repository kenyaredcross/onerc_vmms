import { useState } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { API } from "../lib/api";
import type { GeoNode, PersonalDetails } from "../portal/types";
import { ResidenceFields } from "./ResidenceFields";
import { RegistrationGeoSelects } from "./RegistrationGeoSelects";

const { reads } = vi.hoisted(() => ({ reads: new Map<string, unknown>() }));
vi.mock("frappe-react-sdk", () => ({
	useFrappeGetCall: (method: string, params?: unknown, key?: string | null) => ({
		data: key === null ? undefined : { message: reads.get(`${method}:${JSON.stringify(params ?? {})}`) },
		isLoading: false, error: null,
	}),
}));
const node = (name: string, level: string, label = name): GeoNode => ({ name, label, level, level_name: level });
const national = node("national", "national", "Kenya Red Cross Society");
const west = node("west", "region", "KRCS West Kenya");
const rift = node("rift", "region", "KRCS North Rift");
const kisumu = node("kisumu", "county", "Kisumu");
const turkana = node("turkana", "county", "Turkana");
const nyando = node("nyando", "sub_county", "Nyando");
const ahero = node("ahero", "ward", "Ahero");
function answer(method: string, params: unknown, message: unknown) {
	reads.set(`${method}:${JSON.stringify(params ?? {})}`, message);
}
function Picker({ initial = [] }: { initial?: GeoNode[] }) {
	const [chain, setChain] = useState(initial);
	return <><RegistrationGeoSelects chain={chain} onChain={setChain} allowedLevels={["county"]} /><output data-testid="chain">{JSON.stringify(chain.map((row) => row.name))}</output></>;
}
beforeEach(() => {
	reads.clear();
	answer(API.geoLadder, undefined, { levels: ["national", "region", "county", "sub_county", "ward"].map((key, i) => ({ key, name: key === "county" ? "County" : key, order: i + 1, is_lowest: key === "ward" })) });
	answer(API.geoBrowse, { level: "county" }, { nodes: [kisumu, turkana] });
	for (const [county, region] of [[kisumu, west], [turkana, rift]]) {
		answer(API.geoChain, { node: county.name }, { node: county.name, chain: [national, region, county] });
		answer(API.geoBrowse, { parent: county.name }, { nodes: county === kisumu ? [nyando, node("seme", "sub_county")] : [] });
	}
	answer(API.geoBrowse, { parent: "nyando" }, { nodes: [ahero, node("awasi", "ward")] });
	answer(API.geoBrowse, { parent: "ahero" }, { nodes: [] });
});
describe("county-first registration", () => {
	it("asks for county and resolves its region without asking the applicant", async () => {
		render(<Picker />);
		expect(screen.queryByRole("combobox", { name: /region/i })).toBeNull();
		fireEvent.change(screen.getByLabelText(/^County/), { target: { value: "kisumu" } });
		await waitFor(() => expect(screen.getByTestId("chain").textContent).toBe('["national","west","kisumu"]'));
		expect((screen.getByLabelText(/^County/) as HTMLSelectElement).value).toBe("kisumu");
		expect(screen.queryByText(/KRCS West Kenya/)).toBeNull();
	});
	it("clears a previous sub-county and ward when county changes", async () => {
		render(<Picker initial={[national, west, kisumu, nyando, ahero]} />);
		fireEvent.change(screen.getByLabelText(/^County/), { target: { value: "turkana" } });
		await waitFor(() => expect(screen.getByTestId("chain").textContent).toBe('["national","rift","turkana"]'));
		expect(screen.queryByRole("combobox", { name: /region/i })).toBeNull();
		expect(screen.getByRole("combobox", { name: "sub_county" }).hasAttribute("disabled")).toBe(true);
	});
	it("restores an existing county and ancestry without a region question", () => {
		render(<Picker initial={[national, west, kisumu]} />);
		expect((screen.getByLabelText(/^County/) as HTMLSelectElement).value).toBe("kisumu");
		expect(screen.getByTestId("chain").textContent).toBe('["national","west","kisumu"]');
	});
});

function Residence() {
	const [details, setDetails] = useState<PersonalDetails>({county: "Previous county", sub_county: "Previous sub county", ward: "Previous ward", administrative_location: "Saved location", blood_group: "O+"});
	return <><ResidenceFields residency="Local" onResidency={() => {}} sameHome={true} onSameHome={() => {}} chain={[]} onChain={() => {}} branchChain={[national, west, kisumu, nyando, ahero]} country="" onCountry={() => {}} address="" onAddress={() => {}} details={details} onDetails={setDetails} /><output data-testid="residence">{JSON.stringify(details)}</output></>;
}
it("uses the selected county hierarchy for residence without asking for duplicate county entries", async () => {
	render(<Residence />);
	await waitFor(() => expect(JSON.parse(screen.getByTestId("residence").textContent!)).toMatchObject({county: "Kisumu", sub_county: "Nyando", ward: "Ahero", administrative_location: "Saved location", blood_group: "O+"}));
	expect(document.getElementById("residence-county")).toBeNull();
	expect(screen.getByRole("heading", {name: "Contact & Location"})).toBeTruthy();
});

it("shows editable saved county and sub-county immediately for a separate residence", () => {
	render(<ResidenceFields residency="Local" onResidency={() => {}} sameHome={false} onSameHome={() => {}} recordedHome="ahero" chain={[national, west, kisumu, nyando, ahero]} onChain={() => {}} country="" onCountry={() => {}} address="" onAddress={() => {}} details={{county: "Kisumu", sub_county: "Nyando"}} onDetails={() => {}} />);
	expect((screen.getByLabelText(/^County/) as HTMLSelectElement).value).toBe("kisumu");
	expect(screen.getByRole("combobox", {name: "sub_county"})).toBeTruthy();
	expect(screen.queryByRole("button", {name: "Change location"})).toBeNull();
});

it("shows County and disabled Sub County before a separate residence has been selected", () => {
	render(<ResidenceFields residency="Local" onResidency={() => {}} sameHome={false} onSameHome={() => {}} chain={[]} onChain={() => {}} country="" onCountry={() => {}} address="" onAddress={() => {}} details={{}} onDetails={() => {}} />);
	expect(screen.getByLabelText(/^County/)).toBeTruthy();
	expect(screen.getByRole("combobox", {name: "sub_county"}).hasAttribute("disabled")).toBe(true);
	expect(screen.getByLabelText("Location")).toBeTruthy();
	expect(screen.getByLabelText("Sub Location")).toBeTruthy();
});

it("asks nothing below the county when it stops at the deepest allowed level", async () => {
	function Stopping() {
		const [chain, setChain] = useState<GeoNode[]>([national, west, kisumu]);
		return <RegistrationGeoSelects chain={chain} onChain={setChain} allowedLevels={["county"]} stopAtAllowed />;
	}
	render(<Stopping />);
	expect((screen.getByLabelText(/^County/) as HTMLSelectElement).value).toBe("kisumu");
	expect(screen.queryByRole("combobox", { name: "sub_county" })).toBeNull();
});
