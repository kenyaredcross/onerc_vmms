import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { Pager } from "./primitives";

/** Page numbers come ten at a time, never one button per page of a long register. */
describe("the pager", () => {
	it("shows the first ten pages and a way to the next ten", () => {
		const onPage = vi.fn();
		render(<Pager page={0} pageCount={39} total={951} onPage={onPage} />);

		expect(screen.getByRole("button", { name: "1" })).toBeTruthy();
		expect(screen.getByRole("button", { name: "10" })).toBeTruthy();
		expect(screen.queryByRole("button", { name: "11" })).toBeNull();

		fireEvent.click(screen.getByRole("button", { name: "Pages 11 to 20" }));
		expect(onPage).toHaveBeenCalledWith(10);
	});

	it("moves on to the next ten once the reader passes the tenth page", () => {
		render(<Pager page={12} pageCount={39} total={951} onPage={() => {}} />);

		expect(screen.queryByRole("button", { name: "10" })).toBeNull();
		expect(screen.getByRole("button", { name: "11" })).toBeTruthy();
		expect(screen.getByRole("button", { name: "20" })).toBeTruthy();
		expect(screen.getByRole("button", { name: "Pages 1 to 10" })).toBeTruthy();
		expect(screen.getByRole("button", { name: "13" }).getAttribute("aria-current")).toBe("page");
	});

	it("shows only the pages that exist in the last group", () => {
		render(<Pager page={35} pageCount={39} total={951} onPage={() => {}} />);

		expect(screen.getByRole("button", { name: "39" })).toBeTruthy();
		expect(screen.queryByRole("button", { name: "40" })).toBeNull();
		expect(screen.queryByRole("button", { name: /^Pages 41/ })).toBeNull();
	});
});
