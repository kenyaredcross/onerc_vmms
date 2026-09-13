import { useFrappeGetCall } from "frappe-react-sdk";
import { Navigate } from "react-router-dom";

import { API } from "./lib/api";
import { Spinner } from "./portal/ui/kit";

/**
 * The role-aware front door used when authentication did not name a page.
 *
 * Social sign-in has to choose its return address before it knows which user
 * is coming back. This tiny authenticated route asks the same permission-based
 * endpoint as the manager shell after the account exists, then forwards once.
 */
export default function WorkspaceHome() {
	const access = useFrappeGetCall<{ message: { available: boolean } }>(
		API.consoleSections,
		undefined,
		"workspace:home",
	);

	if (access.isLoading) return <Spinner page label="Opening your workspace…" />;

	return <Navigate to={access.data?.message?.available ? "/admin" : "/dashboard"} replace />;
}
