import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LanguageProvider, useLanguage } from "./LanguageProvider";
import { LanguageSwitcher } from "./LanguageSwitcher";

function Greeting() {
	const { t } = useLanguage();
	return <span>{t("Home")}</span>;
}

beforeEach(() => {
	window.localStorage.removeItem("vmms.ui.language");
	document.documentElement.lang = "en";
	document.documentElement.dir = "ltr";
});

afterEach(() => {
	window.localStorage.removeItem("vmms.ui.language");
	vi.restoreAllMocks();
});

describe("portal language", () => {
	it("uses Frappe's full catalogue for page content and field labels", async () => {
		window.localStorage.setItem("vmms.ui.language", "fr");
		vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
			message: { translations: { "A phrase only Frappe knows 9127": "Une phrase connue uniquement de Frappe" } },
		}), { status: 200, headers: { "Content-Type": "application/json" } }));
		render(<LanguageProvider><main><h1>A phrase only Frappe knows 9127</h1></main></LanguageProvider>);

		expect(await screen.findByText("Une phrase connue uniquement de Frappe")).toBeTruthy();
	});

	it("switches UI text, direction, and persists the Frappe preference", async () => {
		const request = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}"));
		render(<LanguageProvider><LanguageSwitcher /><Greeting /></LanguageProvider>);
		fireEvent.click(screen.getByRole("button", { name: "Language: English" }));
		expect(screen.queryByRole("combobox")).toBeNull();
		fireEvent.click(screen.getByRole("menuitemradio", { name: /العربية/ }));
		expect(screen.getByText("الرئيسية")).toBeTruthy();
		expect(document.documentElement.dir).toBe("rtl");
		await waitFor(() => expect(request).toHaveBeenCalledWith(
			"/api/method/vmmsx.api.locale.set_language",
			expect.objectContaining({ method: "POST", body: JSON.stringify({ language: "ar" }) }),
		));
	});
});
