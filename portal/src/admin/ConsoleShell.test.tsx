import { screen } from "@testing-library/react";
import { act } from "react";
import { Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import { mount } from "../test/harness";
import { Icon } from "../ui/icons";
import { ConsoleShell, type NavItem } from "./ConsoleShell";

/**
 * The console shell's two structural promises.
 *
 * Moved here from `ui/Shell.test.tsx` when the console stopped sharing a shell
 * with the portal. The assertions are unchanged: the two shells are separate
 * components now, but these promises are about *layout mechanics* rather than
 * about either one's visual language, and they are the promises that break
 * silently when somebody refactors a rail.
 *
 * **Collapsing is a layout change, never a navigation.** The route must survive
 * it untouched — a rail that remounted the page would throw away whatever the
 * person was reading and re-fetch it.
 *
 * **The preference persists per device**, and a browser that refuses storage is
 * an ordinary browser rather than a crash.
 */

const ITEMS: NavItem[] = [
	{ to: "/admin", labelKey: "a", fallback: "Overview", icon: Icon.home, end: true },
	{ to: "/tasks", labelKey: "b", fallback: "My tasks", icon: Icon.check },
	{ to: "/admin/deployments", labelKey: "c", fallback: "Deployments", icon: Icon.truck, hasSubNav: true },
];

function show(route: string, subNav?: (horizontal: boolean) => React.ReactNode) {
	return mount(
		<Routes>
			<Route element={<ConsoleShell items={ITEMS} subNav={subNav} />}>
				<Route path="/admin" element={<p>overview body</p>} />
				<Route path="/tasks" element={<p>tasks body</p>} />
				<Route path="/admin/deployments" element={<p>deployments body</p>} />
				<Route path="/admin/deployments/ongoing" element={<p>ongoing body</p>} />
				<Route path="/admin/deployments/terms/:name" element={<p>one terms body</p>} />
			</Route>
		</Routes>,
		{ route },
	);
}

afterEach(() => {
	window.localStorage.clear();
});

describe("the collapse control", () => {
	it("keeps the current route when the rail is collapsed", async () => {
		show("/tasks");

		expect(screen.getByText("tasks body")).toBeTruthy();

		const collapse = screen.getByRole("button", { name: "Collapse menu" });
		await act(async () => collapse.click());

		// Still on the same page, and the rail now offers the opposite action.
		expect(screen.getByText("tasks body")).toBeTruthy();
		expect(screen.getByRole("button", { name: "Expand menu" })).toBeTruthy();
	});

	it("writes the preference so the next visit opens the same way", async () => {
		show("/admin");

		await act(async () => screen.getByRole("button", { name: "Collapse menu" }).click());

		expect(window.localStorage.getItem("vmms.nav.collapsed")).toBe("1");
	});

	it("reads the stored preference on mount", () => {
		window.localStorage.setItem("vmms.nav.collapsed", "1");
		show("/admin");

		expect(screen.getByRole("button", { name: "Expand menu" })).toBeTruthy();
	});

	it("keeps every destination reachable while collapsed, by accessible name", () => {
		window.localStorage.setItem("vmms.nav.collapsed", "1");
		show("/admin");

		// The label is hidden, so `aria-label` and `title` are the only things
		// naming these. An icon rail with no names would fail here.
		expect(screen.getByRole("link", { name: "My tasks" })).toBeTruthy();
		expect(screen.getByRole("link", { name: "Deployments" })).toBeTruthy();
	});
});

describe("a section with its own navigation", () => {
	it("forces the rail narrow and disables the collapse control", () => {
		show("/admin/deployments", () => <p>section nav</p>);

		const control = screen.getByRole("button", { name: "Expand menu" });

		// Forced narrow, so the manual control has nothing to do — and it says so
		// rather than silently ignoring a click.
		expect((control as HTMLButtonElement).disabled).toBe(true);
		expect(control.getAttribute("title")).toBe("This section uses its own menu");
	});

	it("renders the section panel in both arrangements", () => {
		show("/admin/deployments", (horizontal) => <p>{horizontal ? "row nav" : "column nav"}</p>);

		// One in the desktop column, one in the mobile scroller — both in the
		// markup, with CSS deciding which is visible.
		expect(screen.getByText("column nav")).toBeTruthy();
		expect(screen.getByText("row nav")).toBeTruthy();
	});

	it("leaves the rail alone on a section that has none", () => {
		show("/admin");

		expect((screen.getByRole("button", { name: "Collapse menu" }) as HTMLButtonElement).disabled).toBe(
			false,
		);
	});

	it("collapses the rail on a nested route, not only on the section's own page", () => {
		// The case a bookmark lands on. `hasSubNav` is declared on the rail item
		// and `currentTab` matches by prefix, so arriving three segments deep
		// still takes the rail down — otherwise two expanded navigation columns
		// sit side by side and the content column is a corridor.
		show("/admin/deployments/ongoing", () => <p>section nav</p>);

		expect(screen.getByText("ongoing body")).toBeTruthy();
		expect((screen.getByRole("button", { name: "Expand menu" }) as HTMLButtonElement).disabled).toBe(
			true,
		);
	});

	it("collapses on a bookmarked detail route under the section", () => {
		show("/admin/deployments/terms/TOR-1", () => <p>section nav</p>);

		expect(screen.getByText("one terms body")).toBeTruthy();
		expect(screen.getByRole("button", { name: "Expand menu" })).toBeTruthy();
	});

	it("lights the section's rail row from a nested route", () => {
		show("/admin/deployments/ongoing", () => <p>section nav</p>);

		// The rail is icon-only here, so the row is named by `aria-label`. Without
		// the prefix match nothing would be lit and the rail could not say where
		// the reader is.
		expect(
			screen.getByRole("link", { name: "Deployments" }).className.includes("bg-white/[0.12]"),
		).toBe(true);
	});
});

describe("the page title", () => {
	it("names the current section in the top row", () => {
		show("/tasks");

		expect(screen.getByRole("heading", { level: 1, name: "My tasks" })).toBeTruthy();
	});

	it("keeps exactly one h1 on the page", () => {
		show("/tasks");

		expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
	});
});
