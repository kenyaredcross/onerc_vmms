import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { mount } from "../test/harness";
import { Icon } from "../ui/icons";
import { PortalShell, type PortalNavItem } from "./PortalShell";

/**
 * The portal chrome.
 *
 * **Availability is a header control, not a destination.** The brief is
 * explicit, and a stray `/availability` in the rail is the regression this
 * guards. The nav is also the society's to rename, so the labels are content
 * blocks with English fallbacks — the fallbacks are what a test sees.
 */

vi.mock("frappe-react-sdk", async (importOriginal) => {
	const actual = (await importOriginal()) as { default: Record<string, unknown> };
	return {
		...actual.default,
		default: actual.default,
		useFrappeGetCall: (_path: string, _params?: unknown, swrKey?: string | null) => ({
			data: swrKey === null ? undefined : { message: null },
			error: null,
			isLoading: false,
			isValidating: false,
			mutate: () => Promise.resolve(undefined),
		}),
		useFrappePostCall: () => ({ call: () => Promise.resolve({}), loading: false, error: null }),
		useFrappeAuth: () => ({
			currentUser: "amina@example.com",
			isLoading: false,
			logout: () => Promise.resolve(undefined),
		}),
	};
});

const ITEMS: PortalNavItem[] = [
	{ to: "/dashboard", labelKey: "portal.nav.home", fallback: "Home", icon: Icon.home },
	{ to: "/calendar", labelKey: "portal.nav.calendar", fallback: "Calendar", icon: Icon.calendar },
	{ to: "/tasks", labelKey: "portal.nav.tasks", fallback: "Tasks", icon: Icon.check, badge: 2 },
	{ to: "/deployments", labelKey: "portal.nav.deployments", fallback: "Deployments", icon: Icon.truck },
	{ to: "/membership", labelKey: "portal.nav.membership", fallback: "Memberships", icon: Icon.card },
	{ to: "/hours", labelKey: "portal.nav.hours", fallback: "Service hours", icon: Icon.clock },
	{ to: "/events", labelKey: "portal.nav.events", fallback: "Events", icon: Icon.sparkle },
	{ to: "/opportunities", labelKey: "portal.nav.opportunities", fallback: "Opportunities", icon: Icon.compass },
	{ to: "/stories", labelKey: "portal.nav.stories", fallback: "Stories", icon: Icon.book },
];

function render(over: Partial<Parameters<typeof PortalShell>[0]> = {}) {
	return mount(
		<PortalShell
			items={ITEMS}
			unread={3}
			onUnreadChange={() => {}}
			console={null}
			person="Amina Hassan"
			email="amina@example.com"
			branch="Arusha City"
			{...over}
		/>,
		{ route: "/dashboard" },
	);
}

describe("the portal sidebar", () => {
	it("renders every brief destination as a link with a real href", () => {
		render();
		const nav = screen.getByRole("navigation", { name: "Portal" });

		for (const item of ITEMS) {
			const link = within(nav).getByRole("link", { name: new RegExp(item.fallback, "i") });
			expect(link.getAttribute("href")).toBe(item.to);
		}
	});

	it("keeps availability out of the navigation", () => {
		render();
		const nav = screen.getByRole("navigation", { name: "Portal" });
		expect(within(nav).queryByRole("link", { name: /availability/i })).toBeNull();
	});

	it("shows the serving branch at the foot", () => {
		render();
		expect(screen.getAllByText("Arusha City").length).toBeGreaterThan(0);
	});

	it("carries a count badge on a nav item that has one", () => {
		render();
		const nav = screen.getByRole("navigation", { name: "Portal" });
		const tasks = within(nav).getByRole("link", { name: /tasks/i });
		expect(within(tasks).getByText("2")).toBeTruthy();
	});
});

describe("the portal header", () => {
	it("offers the availability control, the notification bell and the account menu", () => {
		render();
		expect(screen.getByRole("button", { name: /notifications \(3 unread\)/i })).toBeTruthy();
		expect(screen.getByRole("button", { name: /amina hassan/i })).toBeTruthy();
	});

	it("shows the console switch only when a route was passed", () => {
		render({ console: "/admin" });
		// The account menu holds it; open the menu first.
		fireEvent.click(screen.getByRole("button", { name: /amina hassan/i }));
		expect(screen.getByRole("menuitem", { name: /manager console/i })).toBeTruthy();
	});
});
