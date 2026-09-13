import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { PersonCard, PersonSummaryBody } from "./PersonCard";

/**
 * Where the card lands, on a page measured the way the real one is.
 *
 * jsdom measures nothing — every rect is zeroes and every `offset*` is zero —
 * so these tests hand it the three numbers the placement is a function of: the
 * trigger's rect, the card's rect, and the scale between window pixels and the
 * card's own units. That third one is not a detail. The signed-in shells run at
 * `zoom: 0.8`, which is why the card spent three attempts sitting a hundred
 * pixels off the name it belonged to, and a test on an unzoomed page would have
 * passed through every one of them.
 */
const WINDOW = 738;
const ROW = 37;
/** What `html.workspace-density` does to every length this component writes. */
const ZOOM = 0.8;

let row = 0;
let card = 344;

/** The trigger's top edge, in window pixels — what a rect would report. */
function anchorAt(next: number) {
	row = next;
}

function rect(top: number, left: number, width: number, height: number) {
	return { top, left, width, height, bottom: top + height, right: left + width, x: left, y: top, toJSON: () => ({}) } as DOMRect;
}

/** The fixed wrapper the placement writes to: dialog → gap padding → wrapper. */
function placed() {
	return screen.getByRole("dialog", { name: "Person summary" }).parentElement!.parentElement!;
}

/** Let the frame loop run, the way a real browser would between paints. */
async function frames() {
	await act(async () => {
		await new Promise((done) => setTimeout(done, 48));
	});
}

function open(body: () => React.ReactNode = () => <p>The summary body</p>) {
	render(
		// Mounted under a basename, the way the app mounts it — which is the
		// whole of what the link test is about.
		<MemoryRouter basename="/home" initialEntries={["/home"]}>
			<PersonCard label="Nigel Nasser">{body}</PersonCard>
		</MemoryRouter>,
	);

	return act(async () => {
		fireEvent.focus(screen.getByRole("button"));
	});
}

describe("where the person card lands", () => {
	beforeEach(() => {
		window.innerHeight = WINDOW;
		window.innerWidth = 1877;
		card = 344;

		// The card's own width in its own units. Divided into the width its rect
		// reports, this is the scale the placement corrects by.
		Object.defineProperty(HTMLElement.prototype, "offsetWidth", {
			configurable: true,
			get: () => 300,
		});

		HTMLButtonElement.prototype.getBoundingClientRect = () => rect(row, 300, 300 * ZOOM, ROW);
		HTMLDivElement.prototype.getBoundingClientRect = () => rect(0, 0, 300 * ZOOM, card);
	});

	afterEach(() => {
		// @ts-expect-error — putting jsdom's own zeroes back.
		delete HTMLElement.prototype.offsetWidth;
	});

	it("hangs under the name when there is room under it", async () => {
		anchorAt(120);
		await open();

		// The window says 157; the card writes 157 / 0.8, which is the same place
		// in the units it is drawn in.
		expect(placed().style.top).toBe(`${(120 + ROW) / ZOOM}px`);
		expect(placed().style.transform).toBe("none");
	});

	it("flips flush above the name when there is not", async () => {
		anchorAt(508);
		await open();

		// Flush, and said without the card's height: it is pinned at the head of
		// the row and flipped onto its own foot by the browser. The visible gap
		// is padding inside the card, which is what keeps a mouse crossing into
		// it from passing over the row underneath and closing what it reached for.
		expect(placed().style.top).toBe(`${508 / ZOOM}px`);
		expect(placed().style.transform).toBe("translateY(-100%)");
	});

	it("keeps its foot on the name however tall it turns out to be", async () => {
		// The card is measured while its dossier is still in flight and grows
		// when the phone number and the Call and Email actions arrive. A
		// placement computed from the height it had at that moment leaves it
		// hanging in the air; one flipped onto its own foot does not.
		anchorAt(508);
		await open();
		expect(placed().style.top).toBe(`${508 / ZOOM}px`);

		card = 344 + 96;
		await frames();

		expect(placed().style.top).toBe(`${508 / ZOOM}px`);
		expect(placed().style.transform).toBe("translateY(-100%)");
	});

	it("follows the row when the page reflows underneath it", async () => {
		// The register renders before the summary tiles and the page's own
		// description arrive; when they do, every row moves down together. That
		// is not a scroll, not a resize, and not a change in the card's own size
		// — and a card that listened only for those three would be left hanging.
		anchorAt(400);
		await open();
		expect(placed().style.top).toBe(`${400 / ZOOM}px`);

		anchorAt(508);
		await frames();

		expect(placed().style.top).toBe(`${508 / ZOOM}px`);
	});

	it("stays on the screen when neither side has room", async () => {
		window.innerHeight = 360;
		anchorAt(150);
		await open();

		// Clamped onto the screen rather than flipped into a position just as cut
		// off: (360 - 16 - 344) is zero, so the top edge wins at 16.
		expect(placed().style.top).toBe(`${16 / ZOOM}px`);
		expect(placed().style.transform).toBe("none");
	});

	it("pulls back from the right edge instead of opening off it", async () => {
		window.innerWidth = 500;
		anchorAt(120);
		await open();

		// The trigger's right edge is 540 in window pixels and the card is 240
		// wide there, so it starts at 300 — and is written as 300 / 0.8.
		expect(placed().style.left).toBe(`${300 / ZOOM}px`);
	});
});

describe("the way out of the card", () => {
	it("goes through the router rather than leaving the app", async () => {
		await open(() => (
			<PersonSummaryBody
				name="Nigel Nasser"
				facts={[]}
				open={{ to: "/admin/registry/volunteer/VOL-00001", label: "Open full record" }}
			/>
		));

		// A bare anchor carries no basename, so the browser asked the site for
		// `/admin/registry/volunteer/VOL-00001`, which no route claims, and
		// Frappe answered with its own "Page not found". Through the router the
		// basename is on the address and it lands on the record.
		const link = screen.getByRole("link", { name: /Open full record/ });
		expect(link.getAttribute("href")).toBe("/home/admin/registry/volunteer/VOL-00001");
	});
});
