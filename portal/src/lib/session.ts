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
 * Where to send somebody who has no account yet, coming back here afterwards.
 *
 * **The `#signup` hash and the `redirect-to` argument are both load-bearing, and
 * only one of them was here before.** Frappe's login page opens its sign-up form
 * when the hash says so, and `frappe.core.doctype.user.user.sign_up` stashes
 * `redirect-to` against the new account under `redirect_after_login` — so the
 * link the verification email carries lands the person back where they started.
 * A bare `/login#signup` creates the account with nowhere recorded to return to,
 * and Frappe falls back to the site's home page: somebody who pressed "Become a
 * volunteer", created an account and verified it arrived at the landing page
 * having lost the wizard, with no indication that they were ever meant to end up
 * somewhere else. That is the whole of that bug.
 *
 * **They do still have to sign in once**, and no argument here changes it.
 * Frappe's sign-up creates the account with a random password and mails a link
 * to set one; nobody is signed in by the act of registering. What this fixes is
 * where they land afterwards, which is the part that was actually broken.
 */
export function signupUrl(returnTo: string = window.location.pathname): string {
	return `${loginUrl(returnTo)}#signup`;
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
