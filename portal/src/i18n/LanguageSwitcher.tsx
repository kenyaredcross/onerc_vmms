import { useEffect, useRef, useState } from "react";

import { Icon } from "../ui/icons";
import { useLanguage } from "./LanguageProvider";
import { SUPPORTED_LANGUAGES, type LanguageCode } from "./translations";

export function LanguageSwitcher({ tone = "light" }: { tone?: "light" | "dark" }) {
	const { language, setLanguage, t } = useLanguage();
	const [open, setOpen] = useState(false);
	const root = useRef<HTMLDivElement>(null);
	const active = SUPPORTED_LANGUAGES.find((option) => option.code === language) ?? SUPPORTED_LANGUAGES[0];

	useEffect(() => {
		if (!open) return;
		const dismiss = (event: MouseEvent) => {
			if (!root.current?.contains(event.target as Node)) setOpen(false);
		};
		const escape = (event: KeyboardEvent) => {
			if (event.key === "Escape") setOpen(false);
		};
		document.addEventListener("mousedown", dismiss);
		document.addEventListener("keydown", escape);
		return () => {
			document.removeEventListener("mousedown", dismiss);
			document.removeEventListener("keydown", escape);
		};
	}, [open]);

	return (
		<div ref={root} className="relative flex-none" dir="ltr">
			<button
				type="button"
				onClick={() => setOpen((value) => !value)}
				aria-label={`${t("Language")}: ${active.label}`}
				aria-haspopup="menu"
				aria-expanded={open}
				className={tone === "dark"
					? "inline-flex h-9 items-center gap-2 rounded-lg border border-white/20 px-2.5 text-[12px] font-semibold text-white/85 transition hover:border-white/35 hover:bg-white/10 hover:text-white"
					: "inline-flex h-9 items-center gap-2 rounded-lg border border-card-line bg-white px-2.5 text-[12px] font-semibold text-slate-strong shadow-[0_1px_2px_rgba(30,50,73,0.04)] transition hover:border-hairline-strong hover:bg-canvas hover:text-ink"
				}
			>
				<Icon.globe size={16} />
				<span className="uppercase tracking-[0.04em]">{active.code}</span>
				<Icon.chevron size={12} className={open ? "rotate-180 transition" : "transition"} />
			</button>
			{open && (
				<div role="menu" aria-label={t("Choose language")} className="absolute end-0 top-full z-[90] mt-2 w-[210px] overflow-hidden rounded-xl border border-card-line bg-white p-1.5 text-ink shadow-[0_16px_40px_rgba(20,32,46,0.16)]">
					<div className="px-2.5 pb-1.5 pt-1 text-[10px] font-bold uppercase tracking-[0.1em] text-slate-faint">{t("Choose language")}</div>
					{SUPPORTED_LANGUAGES.map((option) => {
						const selected = option.code === language;
						return (
							<button key={option.code} type="button" role="menuitemradio" aria-checked={selected}
								onClick={() => { setLanguage(option.code as LanguageCode); setOpen(false); }}
								className={`flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-start transition ${selected ? "bg-blue-soft text-blue-press" : "text-slate-strong hover:bg-canvas hover:text-ink"}`}>
								<span className="w-7 flex-none text-[10px] font-bold uppercase tracking-wider text-slate-faint">{option.code}</span>
								<span className="min-w-0 flex-1 text-[13px] font-semibold" dir={option.code === "ar" ? "rtl" : "ltr"}>{option.nativeLabel}</span>
								{selected && <Icon.check size={14} className="flex-none" />}
							</button>
						);
					})}
				</div>
			)}
		</div>
	);
}
