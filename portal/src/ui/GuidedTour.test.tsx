import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GuidedTour, startGuidedTour } from "./GuidedTour";

const steps = [{ title: "Your workspace", body: "Find your work here.", selector: "#tour-target" }];

beforeEach(() => {
	vi.useFakeTimers();
	window.localStorage.clear();
});

afterEach(() => {
	cleanup();
	vi.useRealTimers();
});

describe("workspace tours", () => {
	it("does not interrupt login or a later visit, even with cleared browser storage", () => {
		const first = render(<GuidedTour id="portal" steps={steps} />);
		act(() => vi.advanceTimersByTime(1000));
		expect(screen.queryByRole("dialog")).toBeNull();
		first.unmount();
		window.localStorage.clear();
		render(<GuidedTour id="portal" steps={steps} />);
		act(() => vi.advanceTimersByTime(1000));
		expect(screen.queryByRole("dialog")).toBeNull();
	});

	it("opens on request and can be skipped and replayed", () => {
		render(<GuidedTour id="portal" steps={steps} />);
		act(() => startGuidedTour("portal"));
		expect(screen.getByRole("dialog")).toBeTruthy();
		fireEvent.click(screen.getByRole("button", { name: "Skip tour" }));
		expect(screen.queryByRole("dialog")).toBeNull();
		act(() => startGuidedTour("portal"));
		expect(screen.getByRole("dialog")).toBeTruthy();
		fireEvent.click(screen.getByRole("button", { name: "Close tour" }));
		expect(screen.queryByRole("dialog")).toBeNull();
		act(() => startGuidedTour("portal"));
		fireEvent.keyDown(document, { key: "Escape" });
		expect(screen.queryByRole("dialog")).toBeNull();
	});

	it("opens only the requested workspace tour", () => {
		render(<GuidedTour id="console" steps={steps} />);
		act(() => startGuidedTour("portal"));
		expect(screen.queryByRole("dialog")).toBeNull();
		act(() => startGuidedTour("console"));
		fireEvent.click(screen.getByRole("button", { name: "Finish" }));
		expect(screen.queryByRole("dialog")).toBeNull();
	});
});
