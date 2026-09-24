import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import { mount } from "../test/harness";

const reads = new Map<string, unknown>();

vi.mock("frappe-react-sdk", async (importOriginal) => {
	const actual = (await importOriginal()) as { default: Record<string, unknown> };
	return {
		...actual.default,
		default: actual.default,
		useFrappeGetCall: (path: string) => ({
			data: { message: reads.get(path) },
			error: null,
			isLoading: false,
			isValidating: false,
			mutate: () => Promise.resolve(undefined),
		}),
	};
});

vi.mock("../ui/GeoSelects", () => ({ GeoSelects: () => null, selectedNode: () => null }));

const AdminEvents = (await import("./Events")).default;

beforeEach(() => {
	reads.clear();
	reads.set(API.eventsUpcoming, { available: true, events: [] });
	reads.set(API.eventFilters, { available: true, categories: [] });
	reads.set(API.managedEvents, { events: [] });
});

describe("event creation in the portal", () => {
	it("shows Desk's required event fields to a Buzz event creator", () => {
		reads.set(API.eventManagementOptions, {
			available: true,
			can_create: true,
			categories: ["Training"],
			hosts: ["Society"],
			venues: ["Branch Hall"],
		});
		mount(<AdminEvents />);
		fireEvent.click(screen.getByRole("button", { name: "New event" }));

		for (const label of [/title/i, /category/i, /host/i, /start date/i, /start time/i, /end time/i]) {
			expect(screen.getByLabelText(label)).toBeTruthy();
		}
		expect(screen.getByRole("button", { name: "Create event" })).toBeTruthy();
		expect((screen.getByLabelText("Free event") as HTMLInputElement).checked).toBe(true);
		fireEvent.click(screen.getByLabelText("Free event"));
		expect((screen.getByLabelText("Publish now") as HTMLInputElement).disabled).toBe(true);
	});

	it("does not offer creation to someone without Buzz create permission", () => {
		reads.set(API.eventManagementOptions, {
			available: true,
			can_create: false,
			categories: [], hosts: [], venues: [],
		});
		mount(<AdminEvents />);
		expect(screen.queryByRole("button", { name: "New event" })).toBeNull();
	});

	it("opens the Desk record for management even when registration uses another site", () => {
		reads.set(API.eventManagementOptions, { available: true, can_create: false, categories: [], hosts: [], venues: [] });
		reads.set(API.eventsUpcoming, {
			available: true,
			events: [{ event: "42", title: "First aid training", start_date: "2026-10-01", end_date: "2026-10-01", href: "https://registration.example.org/event/42", going: 0 }],
		});
		mount(<AdminEvents />);
		expect(screen.getByRole("link", { name: "Manage in Buzz Desk" }).getAttribute("href")).toBe("/app/buzz-event/42");
		expect(screen.getByRole("link", { name: /view registration page/i }).getAttribute("href")).toBe("https://registration.example.org/event/42");
	});

	it("shows confirmed Buzz registrations separately from attendance intentions", () => {
		reads.set(API.eventManagementOptions, { available: true, can_create: true, categories: [], hosts: [], venues: [] });
		reads.set(API.eventsUpcoming, {
			available: true,
			events: [{ event: "935", title: "First aid training", start_date: "2026-10-01", end_date: "2026-10-01", href: "/b/register/first-aid-training", going: 2 }],
		});
		reads.set(API.eventRegistrations, {
			total: 1,
			registrations: [{ ticket: "TICKET-1", name: "Amina Otieno", email: "amina@example.org" }],
		});
		mount(<AdminEvents />);
		fireEvent.click(screen.getByRole("button", { name: /confirmed registrations/i }));
		expect(screen.getByText("1 confirmed registration")).toBeTruthy();
		expect(screen.getByText("Amina Otieno")).toBeTruthy();
		expect(screen.getByText(/2 said they are coming/i)).toBeTruthy();
	});
});
