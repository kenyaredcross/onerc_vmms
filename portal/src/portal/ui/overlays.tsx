import {
	createContext,
	useCallback,
	useContext,
	useEffect,
	useRef,
	useState,
	type ReactNode,
} from "react";

import { Icon } from "../../ui/icons";
import { Button, cx, type ButtonTone } from "./kit";

/**
 * The portal's floating surfaces: a modal, a right-side detail drawer, and
 * toast feedback.
 *
 * All three trap the essentials — Escape closes, the backdrop closes, focus
 * moves in and the page behind stops scrolling — and all three collapse to
 * their end state under `prefers-reduced-motion`.
 */

/* ------------------------------------------------------------------- shared */

function useDismissable(
	open: boolean,
	onClose: () => void,
	panel: React.RefObject<HTMLElement | null>,
) {
	useEffect(() => {
		if (!open) return;

		const previous = document.body.style.overflow;
		document.body.style.overflow = "hidden";

		const onKey = (event: KeyboardEvent) => {
			if (event.key === "Escape") onClose();
		};
		document.addEventListener("keydown", onKey);

		// After paint, so the panel exists to receive focus.
		const focus = window.setTimeout(() => {
			panel.current?.querySelector<HTMLElement>(
				"[data-autofocus], a, button, input, select, textarea",
			)?.focus();
		}, 0);

		return () => {
			document.body.style.overflow = previous;
			document.removeEventListener("keydown", onKey);
			window.clearTimeout(focus);
		};
	}, [open, onClose, panel]);
}

/* -------------------------------------------------------------------- modal */

/**
 * A centred dialog. `size` widens it for a form that needs the room — the
 * availability grid is the one that does.
 */
export function Modal({
	open,
	onClose,
	title,
	description,
	footer,
	size = "md",
	children,
}: {
	open: boolean;
	onClose: () => void;
	title: ReactNode;
	description?: ReactNode;
	footer?: ReactNode;
	size?: "md" | "lg";
	children: ReactNode;
}) {
	const panel = useRef<HTMLDivElement>(null);
	useDismissable(open, onClose, panel);

	if (!open) return null;

	return (
		<div className="fixed inset-0 z-[60] grid place-items-center p-4">
			<button
				type="button"
				aria-label="Close"
				onClick={onClose}
				className="absolute inset-0 bg-ink/35 motion-safe:animate-[fade_.16s_ease-out]"
			/>
			<div
				ref={panel}
				role="dialog"
				aria-modal="true"
				aria-label={typeof title === "string" ? title : undefined}
				className={cx(
					"relative flex max-h-[calc(100vh-2rem)] w-full flex-col overflow-hidden rounded-2xl border border-card-line bg-white shadow-[0_30px_70px_rgba(10,18,27,0.28)] motion-safe:animate-[rise_.18s_ease-out]",
					size === "lg" ? "max-w-2xl" : "max-w-lg",
				)}
			>
				<div className="flex items-start justify-between gap-4 border-b border-card-line px-5 py-4">
					<div className="min-w-0">
						<h2 className="text-[15px] font-semibold text-ink">{title}</h2>
						{description && (
							<p className="mt-0.5 text-[12px] leading-snug text-muted">{description}</p>
						)}
					</div>
					<button
						type="button"
						onClick={onClose}
						aria-label="Close"
						className="grid h-8 w-8 flex-none place-items-center rounded-lg bg-surface text-slate-faint transition hover:text-ink"
					>
						<Icon.cross size={16} />
					</button>
				</div>

				<div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">{children}</div>

				{footer && (
					<div className="flex flex-wrap justify-end gap-2 border-t border-card-line px-5 py-3.5">
						{footer}
					</div>
				)}
			</div>
		</div>
	);
}

/**
 * The second press, for an act that cannot be taken back. Names what will
 * happen rather than asking "are you sure"; the confirm label is the verb.
 */
export function ConfirmModal({
	open,
	title,
	confirmLabel,
	tone = "primary",
	busy,
	onConfirm,
	onCancel,
	children,
}: {
	open: boolean;
	title: ReactNode;
	confirmLabel: string;
	tone?: ButtonTone;
	busy?: boolean;
	onConfirm: () => void;
	onCancel: () => void;
	children: ReactNode;
}) {
	return (
		<Modal
			open={open}
			onClose={onCancel}
			title={title}
			footer={
				<>
					<Button tone="quiet" onClick={onCancel} disabled={busy}>
						Go back
					</Button>
					<Button tone={tone} onClick={onConfirm} busy={busy}>
						{confirmLabel}
					</Button>
				</>
			}
		>
			<div className="text-[13px] leading-relaxed text-slate-strong">{children}</div>
		</Modal>
	);
}

/* ------------------------------------------------------------------- drawer */

/**
 * A right-side panel for one record read in place — a task, an event, an
 * opportunity — without leaving the list behind it. Stories deliberately do
 * not use this: an article is a page.
 */
export function Drawer({
	open,
	onClose,
	title,
	eyebrow,
	children,
	footer,
}: {
	open: boolean;
	onClose: () => void;
	title: ReactNode;
	eyebrow?: ReactNode;
	children: ReactNode;
	footer?: ReactNode;
}) {
	const panel = useRef<HTMLDivElement>(null);
	useDismissable(open, onClose, panel);

	if (!open) return null;

	return (
		<div className="fixed inset-0 z-[60] flex justify-end">
			<button
				type="button"
				aria-label="Close"
				onClick={onClose}
				className="absolute inset-0 bg-ink/30 motion-safe:animate-[fade_.16s_ease-out]"
			/>
			<div
				ref={panel}
				role="dialog"
				aria-modal="true"
				aria-label={typeof title === "string" ? title : undefined}
				className="relative flex h-full w-[min(600px,92vw)] flex-col bg-white shadow-[-22px_0_55px_rgba(17,31,48,0.18)] motion-safe:animate-[slidein_.22s_cubic-bezier(.2,.8,.2,1)]"
			>
				<div className="flex items-start justify-between gap-4 border-b border-card-line px-6 py-4">
					<div className="min-w-0">
						{eyebrow && (
							<div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-rail-label">
								{eyebrow}
							</div>
						)}
						<h2 className="text-[18px] font-semibold leading-snug tracking-[-0.01em] text-ink">
							{title}
						</h2>
					</div>
					<button
						type="button"
						onClick={onClose}
						aria-label="Close"
						className="grid h-8 w-8 flex-none place-items-center rounded-lg bg-surface text-slate-faint transition hover:text-ink"
					>
						<Icon.cross size={16} />
					</button>
				</div>

				<div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">{children}</div>

				{footer && (
					<div className="flex flex-wrap justify-end gap-2 border-t border-card-line px-6 py-4">
						{footer}
					</div>
				)}
			</div>
		</div>
	);
}

/* -------------------------------------------------------------------- toast */

interface ToastMessage {
	id: number;
	text: string;
	tone: "default" | "danger";
}

const ToastContext = createContext<(text: string, tone?: "default" | "danger") => void>(() => {});

/** `toast("Availability saved")` from anywhere under `PortalShell`. */
export function useToast() {
	return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
	const [messages, setMessages] = useState<ToastMessage[]>([]);
	const seq = useRef(0);

	const toast = useCallback((text: string, tone: "default" | "danger" = "default") => {
		const id = ++seq.current;
		setMessages((current) => [...current, { id, text, tone }]);
		window.setTimeout(() => {
			setMessages((current) => current.filter((message) => message.id !== id));
		}, 3200);
	}, []);

	return (
		<ToastContext.Provider value={toast}>
			{children}
			<div
				className="pointer-events-none fixed bottom-6 right-6 z-[80] flex flex-col items-end gap-2"
				role="status"
				aria-live="polite"
			>
				{messages.map((message) => (
					<div
						key={message.id}
						className={cx(
							"pointer-events-auto flex items-center gap-2.5 rounded-xl px-4 py-3 text-[13px] font-medium text-white shadow-[0_12px_36px_rgba(20,31,45,0.18)] motion-safe:animate-[rise_.2s_ease-out]",
							message.tone === "danger" ? "bg-danger" : "bg-[#172638]",
						)}
					>
						<Icon.check size={15} className="flex-none opacity-80" />
						{message.text}
					</div>
				))}
			</div>
		</ToastContext.Provider>
	);
}
