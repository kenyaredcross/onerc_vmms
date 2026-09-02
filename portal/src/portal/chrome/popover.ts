import { useEffect, useRef, useState } from "react";

/**
 * An anchored popover the header controls share — the notification dropdown and
 * the account menu.
 *
 * Closes on an outside click and on Escape, and returns focus to the trigger
 * when Escape closed it. The listeners are attached only while it is open, so a
 * header with three of these is not three document handlers running on every
 * click in the app.
 */
export function usePopover<T extends HTMLElement = HTMLDivElement>() {
	const [open, setOpen] = useState(false);
	const holder = useRef<T>(null);
	const trigger = useRef<HTMLButtonElement>(null);

	useEffect(() => {
		if (!open) return;

		const onPointer = (event: MouseEvent) => {
			if (!holder.current?.contains(event.target as Node)) setOpen(false);
		};
		const onKey = (event: KeyboardEvent) => {
			if (event.key === "Escape") {
				setOpen(false);
				trigger.current?.focus();
			}
		};

		document.addEventListener("mousedown", onPointer);
		document.addEventListener("keydown", onKey);
		return () => {
			document.removeEventListener("mousedown", onPointer);
			document.removeEventListener("keydown", onKey);
		};
	}, [open]);

	return { open, setOpen, holder, trigger };
}
