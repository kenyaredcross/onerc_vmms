import { useFrappeGetCall, useFrappePostCall } from "frappe-react-sdk";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { API, errorMessage } from "../lib/api";
import { useSession } from "../lib/session";
import { DeclarationCard } from "../ui/DeclarationCard";
import { Button } from "../ui/primitives";
import type { OutstandingDeclaration } from "./types";

/** A tick is for one declaration at one version, so a newer version starts unticked. */
const tickOf = (row: OutstandingDeclaration) => `${row.name}@${row.declaration_version ?? ""}`;

/**
 * The terms panel: over the whole portal until a volunteer or member has
 * accepted every required declaration they are held to.
 *
 * `consent.py::outstanding` decides who is asked what — somebody brought over
 * from the old system who never accepted, or a declaration republished with
 * "Ask everyone to accept again". When the answer is empty this draws nothing.
 *
 * There is no way round it but signing out: no close button, Escape does
 * nothing, and the page behind is inert. If the read itself fails the portal
 * stays open rather than locking somebody out over a network hiccup — the
 * question is asked again on the next visit.
 */
export function TermsGate() {
	const outstanding = useFrappeGetCall<{ message: OutstandingDeclaration[] }>(
		API.myOutstandingDeclarations,
		undefined,
		"portal:outstanding_declarations",
	);
	const accept = useFrappePostCall<{ message: OutstandingDeclaration[] }>(API.acceptMyDeclarations);
	const { logout } = useSession();

	const rows = outstanding.data?.message ?? [];
	const open = rows.length > 0;

	const [ticked, setTicked] = useState<string[]>([]);
	const [problem, setProblem] = useState<string | null>(null);
	const panel = useRef<HTMLDivElement>(null);

	useBlocking(open, panel);

	if (!open) return null;

	const unticked = rows.filter((row) => !ticked.includes(tickOf(row)));
	const anyUpdated = rows.some((row) => row.updated);

	const toggle = (row: OutstandingDeclaration, yes: boolean) => {
		setProblem(null);
		setTicked((now) => (yes ? [...now, tickOf(row)] : now.filter((tick) => tick !== tickOf(row))));
	};

	const submit = async () => {
		if (unticked.length) {
			setProblem("Tick each declaration to continue.");
			const box = document.getElementById(`declaration-${unticked[0].name}`);
			box?.scrollIntoView?.({ block: "center", behavior: "smooth" });
			box?.focus();
			return;
		}

		setProblem(null);
		try {
			const result = await accept.call({
				declarations: JSON.stringify(
					rows.map((row) => ({ declaration: row.name, declaration_version: row.declaration_version })),
				),
			});
			await outstanding.mutate(result, { revalidate: false });
		} catch (error) {
			setProblem(errorMessage(error, "Your acceptance was not saved. Try again."));
			// A newer version may have been published while they read; this brings
			// it in, and its tick starts empty because the version is part of it.
			void outstanding.mutate();
		}
	};

	const signOut = () => {
		void logout().then(() => {
			window.location.href = "/";
		});
	};

	return createPortal(
		<div className="fixed inset-0 z-[80] grid place-items-center p-4">
			<div aria-hidden="true" className="absolute inset-0 bg-ink/45 backdrop-blur-[3px]" />
			<div
				ref={panel}
				role="dialog"
				aria-modal="true"
				aria-labelledby="terms-gate-title"
				className="relative flex max-h-[calc(var(--screen,100vh)-2rem)] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-card-line bg-white shadow-[0_30px_70px_rgba(10,18,27,0.28)] motion-safe:animate-[rise_.18s_ease-out]"
			>
				<div className="border-b border-card-line px-6 py-4">
					<h2 id="terms-gate-title" className="text-[16px] font-semibold text-ink">
						Accept the terms to continue
					</h2>
					{anyUpdated && (
						<p className="mt-0.5 text-[12.5px] leading-snug text-muted">
							Some of these have changed since you last accepted them.
						</p>
					)}
				</div>

				<div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-5">
					{rows.map((row) => (
						<DeclarationCard
							key={tickOf(row)}
							declaration={row}
							ticked={ticked.includes(tickOf(row))}
							onToggle={(yes) => toggle(row, yes)}
							badge={row.updated ? "Updated" : undefined}
						/>
					))}
				</div>

				<div className="border-t border-card-line px-6 py-3.5">
					{problem && (
						<p role="alert" className="mb-2.5 text-[12.5px] font-medium text-danger">
							{problem}
						</p>
					)}
					<div className="flex flex-wrap items-center justify-between gap-2">
						<Button variant="quiet" onClick={signOut}>
							Sign out
						</Button>
						<Button onClick={() => void submit()} held={unticked.length > 0} busy={accept.loading}>
							Accept and continue
						</Button>
					</div>
				</div>
			</div>
		</div>,
		document.body,
	);
}

/**
 * Everything a dismissable dialog does, except dismissing: the page behind
 * stops scrolling and stops taking focus or clicks, and Escape is swallowed
 * before any overlay underneath can act on it.
 */
function useBlocking(open: boolean, panel: React.RefObject<HTMLDivElement | null>) {
	useEffect(() => {
		if (!open) return;

		const root = document.getElementById("root");
		const wasInert = root?.inert ?? false;
		if (root) root.inert = true;

		const overflow = document.body.style.overflow;
		document.body.style.overflow = "hidden";

		const swallow = (event: KeyboardEvent) => {
			if (event.key === "Escape") {
				event.preventDefault();
				event.stopImmediatePropagation();
			}
		};
		window.addEventListener("keydown", swallow, true);

		const focus = window.setTimeout(() => {
			panel.current?.querySelector<HTMLElement>("input, button")?.focus();
		}, 0);

		return () => {
			if (root) root.inert = wasInert;
			document.body.style.overflow = overflow;
			window.removeEventListener("keydown", swallow, true);
			window.clearTimeout(focus);
		};
	}, [open, panel]);
}
