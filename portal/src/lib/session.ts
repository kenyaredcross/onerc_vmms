import { useFrappeAuth } from "frappe-react-sdk";

/**
 * Who is signed in, in the terms this app cares about.
 *
 * `useFrappeAuth` answers "which login", and that is all this wraps: the
 * question of *what someone may do* is deliberately not answered here. Roles
 * come back from the endpoints themselves, as flags computed server-side
 * against the same check the write would make. `can_edit` on a content surface
 * and `can_act` on an approval are both that shape.
 *
 * The temptation is a `hasRole("Branch Coordinator")` helper. It would put a
 * society's role name in a source file, which the access model forbids, and it
 * would be a second answer to a question the server already answers.
 */
export function useSession() {
	const { currentUser, isLoading, logout } = useFrappeAuth();
	const isGuest = !currentUser || currentUser === "Guest";

	return { user: currentUser ?? null, isGuest, isLoading, logout };
}

/** Where to send somebody who needs to sign in first, coming back here after. */
export function loginUrl(returnTo: string = window.location.pathname): string {
	return `/login?redirect-to=${encodeURIComponent(returnTo)}`;
}

/**
 * A first name for the top bar's greeting, out of whatever `session.user` is
 * — an email in most societies, `Administrator` in this one. Good enough for
 * "Good morning, X": the part before an `@` if there is one, then the part
 * before the first separator in that.
 */
export function firstName(name: string | null | undefined): string {
	if (!name) return "";

	const local = name.includes("@") ? name.split("@")[0] : name;
	const first = local.split(/[\s._-]+/).filter(Boolean)[0];

	return first ? first[0].toUpperCase() + first.slice(1) : "";
}

/** Initials for an avatar tile. Empty string when there is nothing to shorten. */
export function initials(name: string | null | undefined): string {
	if (!name) return "";

	return name
		.split(/[\s@._-]+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((part) => part[0]?.toUpperCase() ?? "")
		.join("");
}
