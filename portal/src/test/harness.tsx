import type { ReactNode } from "react";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { FrappeProvider } from "frappe-react-sdk";

import { ContentProvider } from "../content/ContentProvider";

/**
 * Mount a component the way the app mounts it.
 *
 * Three providers, because almost everything in `ui/` reaches for at least one
 * of them: a router (every navigation is a real route), the Frappe SDK (which
 * `ContentProvider` reads through), and the content layer (every visible string
 * in this product is an editable block with a fallback).
 *
 * **No request is stubbed.** The SDK's fetch fails in jsdom and that is the
 * case worth testing against: `EditableText` must render its English fallback
 * when the content surface has not arrived, because that is exactly what a real
 * visitor sees on a slow connection. A test that mocked the content away would
 * pass while the fallback path was broken.
 */
export function mount(ui: ReactNode, { route = "/" }: { route?: string } = {}) {
	return render(
		<MemoryRouter initialEntries={[route]}>
			<FrappeProvider url="http://localhost">
				<ContentProvider surface="test">{ui}</ContentProvider>
			</FrappeProvider>
		</MemoryRouter>,
	);
}
