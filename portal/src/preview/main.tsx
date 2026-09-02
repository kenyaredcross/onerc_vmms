import { useEffect } from "react";
import ReactDOM from "react-dom/client";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { FrappeProvider } from "frappe-react-sdk";

import "../index.css";
import PortalLayout from "../portal/PortalLayout";
import Dashboard from "../portal/Dashboard";
import Calendar from "../portal/Calendar";
import Tasks, { TaskRecord } from "../portal/Tasks";
import Deployments, { DeploymentRecord, DeploymentRequest } from "../portal/Deployments";
import Membership from "../portal/Membership";
import AdminLayout from "../admin/AdminLayout";
import Finance from "../admin/Finance";
import WhatsAppChannel from "../admin/WhatsApp";
import Communication from "../admin/Communication";
import {
	JobApplicant,
	JobApplications,
	OpeningDetailPage,
	OpeningForm,
	Openings,
} from "../admin/Recruitment";
import { Overview } from "../admin/Screens";

/**
 * A backend-free preview of the portal, for design iteration and screenshots.
 *
 * It mounts the real components against `scripts/mock-api.mjs`, which serves
 * synthetic data — a Tanzania-flavoured volunteer from the supplied prototype.
 * Nothing here ships: `preview.html` is not referenced by `vmmsx/www/portal.py`
 * and the route is dev-server only.
 *
 * `?route=/calendar` picks the screen. Console routes are mounted too — the
 * harness is the only place the manager console can be looked at without a
 * bench, and the console is where most of the design work now is.
 */
const params = new URLSearchParams(window.location.search);
const MOCK = (import.meta.env.VITE_MOCK_API as string) || "http://localhost:9977";
const route = params.get("route") || "/dashboard";

/**
 * `?open=notifications|account|availability` clicks the matching header control
 * after mount, so a capture can show that state without a `--prepare` hook.
 */
function AutoOpen() {
	const open = params.get("open");
	useEffect(() => {
		if (!open) return;
		const pick: Record<string, string> = {
			notifications: "Notifications",
			account: "Nigel Nathan",
			availability: "Availability not set",
			drawer: "Open navigation",
		};
		// Anything not in the table is taken as the control's own label, so a
		// capture can open a named tab ("?open=Messages") without this map
		// growing a line per screen.
		const label = pick[open] ?? open;
		const timer = window.setTimeout(() => {
			const button = [...document.querySelectorAll("button")].find((b) =>
				(b.getAttribute("aria-label") || b.textContent || "").includes(label),
			);
			button?.click();
		}, 700);
		return () => window.clearTimeout(timer);
	}, [open]);
	return null;
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
	<FrappeProvider url={MOCK}>
		<MemoryRouter initialEntries={[route]}>
			<AutoOpen />
			<Routes>
				<Route element={<PortalLayout />}>
					<Route path="/dashboard" element={<Dashboard />} />
					<Route path="/calendar" element={<Calendar />} />
					<Route path="/tasks" element={<Tasks />} />
					<Route path="/tasks/:name" element={<TaskRecord />} />
					<Route path="/deployments" element={<Deployments />} />
					<Route path="/deployments/requests/:assignment" element={<DeploymentRequest />} />
					<Route path="/deployments/:name" element={<DeploymentRecord />} />
					<Route path="/membership" element={<Membership />} />
				</Route>
				<Route path="/admin" element={<AdminLayout />}>
					<Route index element={<Overview />} />
					<Route path="finance" element={<Finance />} />
					<Route path="recruitment/openings" element={<Openings />} />
					<Route path="recruitment/openings/new" element={<OpeningForm />} />
					<Route path="recruitment/openings/:name" element={<OpeningDetailPage />} />
					<Route path="recruitment/applications" element={<JobApplications />} />
					<Route path="recruitment/applications/:name" element={<JobApplicant />} />
					<Route path="communication/whatsapp/channel" element={<WhatsAppChannel />} />
					<Route path="communication/:channel/:view" element={<Communication />} />
				</Route>
				<Route path="*" element={<Dashboard />} />
			</Routes>
		</MemoryRouter>
	</FrappeProvider>,
);
