import { Route, Routes } from "react-router-dom";
import { act, fireEvent, screen } from "@testing-library/react";
import { FrappeContext } from "frappe-react-sdk";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import { mount } from "../test/harness";
import type { SurgeEntry } from "../portal/types";

/**
 * The surge roster, the profession and disability filters on the register,
 * and the overview's disability figures.
 *
 * The roster is grouped by profession and each person's standing is the
 * server's answer. Adding or renewing records nothing until the licence
 * number and issuer are given. The overview shows counts and links to the
 * list; it never lists names itself.
 */

const calls: Array<{ path: string; params: Record<string, unknown> | undefined }> = [];
const reads = new Map<string, unknown>();

vi.mock("frappe-react-sdk", async (importOriginal) => {
	const actual = (await importOriginal()) as { default: Record<string, unknown> };

	return {
		...actual.default,
		default: actual.default,
		useFrappeGetCall: (path: string, params?: Record<string, unknown>, swrKey?: string | null) => {
			if (swrKey === null) {
				return { data: undefined, error: null, isLoading: false, mutate: () => Promise.resolve(undefined) };
			}

			calls.push({ path, params });

			return {
				data: reads.has(path) ? { message: reads.get(path) } : undefined,
				error: null,
				isLoading: false,
				mutate: () => Promise.resolve(undefined),
			};
		},
	};
});

const { SurgeRosterPeople, SurgeCard } = await import("./Surge");
const { VolunteersRegistry } = await import("./Registry");
const { DisabilityPanel } = await import("./overview/DisabilityPanel");

const ENTRY: SurgeEntry = {
	entry: "SURGE-00001",
	volunteer: "VOL-00042",
	profession: "Nurse",
	status: "Active",
	standing: "ready",
	ready: true,
	licence_number: "NCK-12345",
	issuing_body: "Nursing Council of Kenya",
	licence_expiry: "2027-06-30",
	licence_document: null,
	checked_by: "Grace Wanjiru",
	checked_on: "2026-11-01",
	notes: null,
	stood_down_on: null,
	stood_down_by: null,
	stood_down_reason: null,
};

function show(element: React.ReactNode, route = "/") {
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

describe("the surge roster", () => {
	beforeEach(() => {
		reads.set(API.surgeRoster, {
			as_of: "2026-11-03",
			figures: { on_roster: 2, people: 2, ready: 1, expiring: 0, needs_review: 1 },
			professions: [
				{ profession: "Nurse", count: 1, ready: 1 },
				{ profession: "Clinical Officer", count: 1, ready: 0 },
			],
			rows: [
				{ ...ENTRY, full_name: "Achieng Otieno", photo: null, phone: "0712000000", volunteer_status: "Active", branch: "Baringo" },
				{
					...ENTRY,
					entry: "SURGE-00002",
					volunteer: "VOL-00043",
					profession: "Clinical Officer",
					standing: "licence_expired",
					ready: false,
					full_name: "Baraka Kiprop",
					photo: null,
					phone: null,
					volunteer_status: "Active",
					branch: "Baringo",
				},
			],
		});
	});

	it("groups people by profession with their standing", () => {
		show(<SurgeRosterPeople />);

		expect(screen.getByRole("heading", { name: "Nurse" })).toBeTruthy();
		expect(screen.getByRole("heading", { name: "Clinical Officer" })).toBeTruthy();
		expect(screen.getByText("Achieng Otieno")).toBeTruthy();
		expect(screen.getAllByText("Licence expired").length).toBeGreaterThan(0);
		expect(screen.getByText("Needs review")).toBeTruthy();
	});

	it("narrows to one profession when its chip is chosen", () => {
		show(<SurgeRosterPeople />);

		fireEvent.click(screen.getByRole("button", { name: /Clinical Officer/ }));

		expect(argsFor(API.surgeRoster)).toMatchObject({ profession: "Clinical Officer" });
	});
});

describe("the surge card on a volunteer's record", () => {
	function card(canAct: boolean, entries: SurgeEntry[] = [ENTRY]) {
		const post = vi.fn(() => Promise.resolve({ message: { surge: entries } }));
		const onChanged = vi.fn();
		mount(
			<FrappeContext.Provider value={{ call: { post } } as never}>
				<SurgeCard
					volunteer="VOL-00042"
					entries={entries}
					canAct={canAct}
					volunteerActive
					suggestedProfession="Nurse"
					onChanged={onChanged}
				/>
			</FrappeContext.Provider>,
		);
		return { post, onChanged };
	}

	it("only reads for somebody who may not change the volunteer", () => {
		card(false);

		expect(screen.getByText("NCK-12345")).toBeTruthy();
		expect(screen.queryByRole("button", { name: "Add to the surge roster" })).toBeNull();
		expect(screen.queryByRole("button", { name: "Stand down" })).toBeNull();
	});

	it("records a renewed licence only once the number and issuer are given", async () => {
		const { post, onChanged } = card(true);

		fireEvent.click(screen.getByRole("button", { name: "Record a renewed licence" }));
		const issuer = screen.getByLabelText(/Issued by/) as HTMLInputElement;
		expect(issuer.value).toBe("Nursing Council of Kenya");

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Record the renewed licence" }));
		});
		expect(post).not.toHaveBeenCalled();
		expect(screen.getByText("Enter the licence number")).toBeTruthy();

		fireEvent.change(screen.getByLabelText(/Licence number/), { target: { value: "NCK-67890" } });
		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Record the renewed licence" }));
		});

		expect(post).toHaveBeenCalledWith(
			API.renewSurgeLicence,
			expect.objectContaining({ name: "SURGE-00001", licence_number: "NCK-67890" }),
		);
		expect(onChanged).toHaveBeenCalled();
	});

	it("asks for a reason before standing somebody down", async () => {
		const { post } = card(true);

		fireEvent.click(screen.getByRole("button", { name: "Stand down" }));
		await act(async () => {
			fireEvent.click(screen.getAllByRole("button", { name: "Stand down" }).at(-1) as HTMLElement);
		});
		expect(post).not.toHaveBeenCalled();

		fireEvent.change(screen.getByLabelText(/Why is this person being stood down/), {
			target: { value: "Moved abroad" },
		});
		await act(async () => {
			fireEvent.click(screen.getAllByRole("button", { name: "Stand down" }).at(-1) as HTMLElement);
		});
		expect(post).toHaveBeenCalledWith(API.standDownFromSurge, { name: "SURGE-00001", reason: "Moved abroad" });
	});
});

describe("the register's profession and disability filters", () => {
	beforeEach(() => {
		reads.set(API.findVolunteers, { count: 0, total: 0, volunteers: [] });
		reads.set(API.registerProfessions, { professions: [{ profession: "Nurse", count: 4 }], without: 12, active: 16 });
	});

	it("offers the professions held in scope and sends the one chosen", () => {
		show(<VolunteersRegistry />, "/admin/registry/volunteers");

		fireEvent.change(screen.getByRole("combobox", { name: "Profession" }), { target: { value: "Nurse" } });

		expect(argsFor(API.findVolunteers)).toMatchObject({ status: "Active", profession: "Nurse" });
		expect(screen.queryByText("12 with no profession recorded")).toBeNull();
	});

	it("takes the disability filter from the address and shows it as a chip", () => {
		show(<VolunteersRegistry />, "/admin/registry/volunteers?disability_category=Physical");

		expect(argsFor(API.findVolunteers)).toMatchObject({ disability_category: "Physical" });
		expect(screen.getByText("Disability: Physical")).toBeTruthy();
	});
});

describe("the overview's disability figures", () => {
	it("shows counts and kinds, and links to the list rather than naming anyone", () => {
		reads.set(API.disabilitySummary, {
			active: 200,
			yes: 14,
			no: 120,
			prefer_not: 6,
			not_asked: 60,
			categories: [{ category: "Physical", count: 9 }],
			unspecified: 3,
		});
		show(<DisabilityPanel />);

		expect(screen.getByText("Persons with disabilities")).toBeTruthy();
		expect(screen.getAllByText("14").length).toBeGreaterThan(0);
		expect(screen.getByText("7% of 200 active volunteers")).toBeTruthy();
		expect(screen.getByRole("link", { name: "Physical" }).getAttribute("href")).toBe(
			"/admin/registry/volunteers?disability_category=Physical",
		);
		expect(screen.getByRole("link", { name: /View the list/ }).getAttribute("href")).toBe(
			"/admin/registry/volunteers?disability=Yes",
		);
	});
});
