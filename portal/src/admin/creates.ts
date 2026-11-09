import { useFrappeGetCall } from "frappe-react-sdk";

import { API } from "../lib/api";

/** A kind of record the console has a create button for. Keys from `api/console.py::CREATABLE`. */
export type Creatable = "project" | "terms" | "deployment" | "asset";

/**
 * May this person start a record of this kind?
 *
 * Read from the same console answer the layout draws its sections from, under
 * the same key, so it costs no request of its own. Until that answer arrives,
 * or where a server predates `creates`, every button is offered as before: the
 * create endpoints refuse for themselves, so this only spares a read-only role
 * buttons that would be refused.
 */
export function useCanCreate(): (kind: Creatable) => boolean {
	const access = useFrappeGetCall<{ message: { creates?: string[] } }>(
		API.consoleSections,
		undefined,
		"admin:sections",
	);

	const creates = access.data?.message?.creates;

	return (kind) => !creates || creates.includes(kind);
}
