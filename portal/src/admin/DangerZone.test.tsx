import { act, fireEvent, screen } from "@testing-library/react";
import { FrappeContext } from "frappe-react-sdk";
import { describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import { mount } from "../test/harness";
import type { VolunteerDossier } from "../portal/types";
import { DangerZone } from "./Person";

/**
 * A volunteer's status changes sit in a closed danger zone at the foot of the
 * record. Nothing is offered until the zone is opened, and nothing changes until
 * a reason is given and the change confirmed.
 */

function zone(status: string) {
	const post = vi.fn(() => Promise.resolve({}));
	const onActed = vi.fn();
	const dossier = { volunteer: "VOL-1", identity: { status } } as unknown as VolunteerDossier;
	mount(
		<FrappeContext.Provider value={{ call: { post } } as never}>
			<DangerZone dossier={dossier} onActed={onActed} />
		</FrappeContext.Provider>,
	);
	return { post, onActed };
}

describe("the volunteer danger zone", () => {
	it("is closed until opened", () => {
		zone("Active");
		const toggle = screen.getByRole("button", { name: /Danger zone/ });
		expect(toggle.getAttribute("aria-expanded")).toBe("false");
		expect(screen.queryByRole("button", { name: "Suspend volunteer" })).toBeNull();

		fireEvent.click(toggle);
		expect(toggle.getAttribute("aria-expanded")).toBe("true");
		expect(screen.getByRole("button", { name: "Suspend volunteer" })).toBeTruthy();
		expect(screen.getByRole("button", { name: "Record exit" })).toBeTruthy();
		expect(screen.queryByRole("button", { name: "Reinstate" })).toBeNull();
	});

	it("changes nothing until a reason is given and the change confirmed", async () => {
		const { post, onActed } = zone("Active");
		fireEvent.click(screen.getByRole("button", { name: /Danger zone/ }));
		fireEvent.click(screen.getByRole("button", { name: "Suspend volunteer" }));
		expect(post).not.toHaveBeenCalled();

		const confirm = screen.getByRole("button", { name: "Suspend volunteer" }) as HTMLButtonElement;
		expect(confirm.disabled).toBe(true);

		fireEvent.change(screen.getByRole("textbox"), { target: { value: "Conduct review" } });
		expect(confirm.disabled).toBe(false);

		await act(async () => {
			fireEvent.click(confirm);
		});
		expect(post).toHaveBeenCalledWith(API.suspendVolunteer, { name: "VOL-1", reason: "Conduct review" });
		expect(onActed).toHaveBeenCalled();
	});

	it("offers reinstatement to a suspended volunteer", () => {
		zone("Suspended");
		fireEvent.click(screen.getByRole("button", { name: /Danger zone/ }));
		expect(screen.getByRole("button", { name: "Reinstate" })).toBeTruthy();
		expect(screen.queryByRole("button", { name: "Suspend volunteer" })).toBeNull();
	});
});
