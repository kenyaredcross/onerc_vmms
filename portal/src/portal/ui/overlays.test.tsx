import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { mount } from "../../test/harness";
import { Drawer, Modal } from "./overlays";

/**
 * The portal's floating surfaces.
 *
 * **An overlay must escape the chrome that opened it.** Both shells blur their
 * sticky header, and a `backdrop-filter` makes that header the containing block
 * for every `position: fixed` descendant — so the availability dialog, opened
 * from a control in the header, was centred on a 56px strip and hung half of
 * itself above the top of the window. Layout is invisible to jsdom; where the
 * dialog is mounted is not, and that is the thing that went wrong.
 */

function Chrome({ children }: { children: React.ReactNode }) {
	return (
		<div data-testid="shell">
			<header className="sticky top-0 z-40 backdrop-blur-sm">{children}</header>
		</div>
	);
}

describe("an overlay opened from the blurred header", () => {
	it("mounts the modal outside the header, not within it", () => {
		mount(
			<Chrome>
				<Modal open onClose={() => {}} title="Your usual availability">
					<p>Monday</p>
				</Modal>
			</Chrome>,
		);

		const dialog = screen.getByRole("dialog", { name: "Your usual availability" });
		expect(screen.getByTestId("shell").contains(dialog)).toBe(false);
		expect(dialog.closest("header")).toBeNull();
	});

	it("mounts the drawer outside the header too", () => {
		mount(
			<Chrome>
				<Drawer open onClose={() => {}} title="A task">
					<p>Details</p>
				</Drawer>
			</Chrome>,
		);

		const dialog = screen.getByRole("dialog", { name: "A task" });
		expect(screen.getByTestId("shell").contains(dialog)).toBe(false);
	});
});
