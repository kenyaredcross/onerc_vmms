import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { CATALOGUES, SUPPORTED_LANGUAGES, type LanguageCode } from "./translations";

const STORAGE_KEY = "vmms.ui.language";
const CODES = new Set<string>(SUPPORTED_LANGUAGES.map(({ code }) => code));

function normalise(value?: string | null): LanguageCode {
	const code = (value || "").replace("_", "-").split("-")[0].toLowerCase();
	return CODES.has(code) ? (code as LanguageCode) : "en";
}

function initialLanguage(): LanguageCode {
	try {
		const saved = window.localStorage.getItem(STORAGE_KEY);
		if (saved) return normalise(saved);
	} catch { /* browser storage is optional */ }
	return normalise(window.frappe?.boot?.lang || document.documentElement.lang || navigator.language);
}

type LanguageContextValue = {
	language: LanguageCode;
	setLanguage: (language: LanguageCode) => void;
	t: (source: string) => string;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);
const sourceText = new WeakMap<Text, string>();
const renderedText = new WeakMap<Text, string>();
const sourceAttributes = new WeakMap<Element, Map<string, string>>();
const TRANSLATED_ATTRIBUTES = ["aria-label", "placeholder", "title"] as const;

function translateTree(root: Node, catalogue: Record<string, string>) {
	const visit = (node: Node) => {
		if (node instanceof HTMLElement && node.closest("[data-no-translate]")) return;
		if (node instanceof Element) {
			let sources = sourceAttributes.get(node);
			if (!sources) {
				sources = new Map();
				sourceAttributes.set(node, sources);
			}
			for (const attribute of TRANSLATED_ATTRIBUTES) {
				const current = node.getAttribute(attribute);
				if (!current) continue;
				if (!sources.has(attribute)) sources.set(attribute, current);
				const source = sources.get(attribute) as string;
				const translated = catalogue[source] ?? source;
				if (current !== translated) node.setAttribute(attribute, translated);
			}
		}
		if (node.nodeType === Node.TEXT_NODE) {
			const text = node as Text;
			const current = text.nodeValue || "";
			if (!sourceText.has(text) || (renderedText.has(text) && renderedText.get(text) !== current)) {
				sourceText.set(text, current);
			}
			const source = sourceText.get(text) || "";
			const trimmed = source.trim();
			const translated = catalogue[trimmed] ?? trimmed;
			const next = trimmed ? source.replace(trimmed, translated) : source;
			renderedText.set(text, next);
			if (current !== next) text.nodeValue = next;
			return;
		}
		node.childNodes.forEach(visit);
	};
	visit(root);
}

async function persist(language: LanguageCode) {
	document.cookie = `preferred_language=${language}; path=/; max-age=31536000; SameSite=Lax`;
	try {
		await fetch("/api/method/vmmsx.api.locale.set_language", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				...(window.csrf_token ? { "X-Frappe-CSRF-Token": window.csrf_token } : {}),
			},
			body: JSON.stringify({ language }),
		});
	} catch { /* local UI preference still works while offline */ }
}

export function LanguageProvider({ children }: { children: ReactNode }) {
	const [language, updateLanguage] = useState<LanguageCode>(initialLanguage);
	const [frappeCatalogue, setFrappeCatalogue] = useState<Record<string, string>>({});
	const catalogue = useMemo(
		() => ({ ...frappeCatalogue, ...CATALOGUES[language] }),
		[frappeCatalogue, language],
	);

	useEffect(() => {
		const controller = new AbortController();
		setFrappeCatalogue({});
		fetch(`/api/method/vmmsx.api.locale.get_translations?language=${encodeURIComponent(language)}`, {
			signal: controller.signal,
		})
			.then((response) => response.ok ? response.json() : Promise.reject(new Error("translation request failed")))
			.then((response: { message?: { translations?: Record<string, string> } }) => {
				setFrappeCatalogue(response.message?.translations ?? {});
			})
			.catch(() => { /* bundled VMMS translations remain available offline */ });
		return () => controller.abort();
	}, [language]);

	useEffect(() => {
		document.documentElement.lang = language;
		document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
		translateTree(document.body, catalogue);
		const observer = new MutationObserver((mutations) => {
			for (const mutation of mutations) {
				if (mutation.type === "characterData") translateTree(mutation.target, catalogue);
				mutation.addedNodes.forEach((node) => translateTree(node, catalogue));
			}
		});
		observer.observe(document.body, { subtree: true, childList: true, characterData: true });
		return () => observer.disconnect();
	}, [catalogue, language]);

	const value = useMemo<LanguageContextValue>(() => ({
		language,
		setLanguage(next) {
			updateLanguage(next);
			try { window.localStorage.setItem(STORAGE_KEY, next); } catch { /* optional */ }
			void persist(next);
		},
		t(source) { return catalogue[source] ?? source; },
	}), [catalogue, language]);

	return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
	const value = useContext(LanguageContext);
	if (!value) throw new Error("useLanguage must be used inside LanguageProvider");
	return value;
}

export function Translated({ children }: { children: string }) {
	const { t } = useLanguage();
	return <>{t(children)}</>;
}
