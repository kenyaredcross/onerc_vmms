import { type KeyboardEvent, type MouseEvent, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";

const INTERACTIVE =
	"a, button, input, select, textarea, label, summary, [role='button'], [role='link'], [contenteditable='true']";

/** Opens the destination from any non-interactive part of its table row. */
export function NavigableRow({
	children,
	to,
	openNewTab,
	label,
	className,
}: {
	children: ReactNode;
	to?: string;
	openNewTab?: string;
	label: string;
	className: string;
}) {
	const navigate = useNavigate();
	const navigateToTarget = () => {
		if (openNewTab) window.open(openNewTab, "_blank", "noopener,noreferrer");
		else if (to) void navigate(to);
	};

	const open = (event: MouseEvent<HTMLTableRowElement>) => {
		if (
			event.defaultPrevented ||
			event.button !== 0 ||
			event.metaKey ||
			event.ctrlKey ||
			event.shiftKey ||
			event.altKey
		) return;
		if (event.target instanceof Element && event.target.closest(INTERACTIVE)) return;
		navigateToTarget();
	};

	const openWithKeyboard = (event: KeyboardEvent<HTMLTableRowElement>) => {
		if (event.target !== event.currentTarget || (event.key !== "Enter" && event.key !== " ")) return;
		event.preventDefault();
		navigateToTarget();
	};

	return (
		<tr className={className} tabIndex={0} aria-label={label} onClick={open} onKeyDown={openWithKeyboard}>
			{children}
		</tr>
	);
}
