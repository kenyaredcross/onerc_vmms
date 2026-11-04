import type { ReactNode } from "react";
import { Link, useHref } from "react-router-dom";

import { signupUrl, useSession } from "../lib/session";

/**
 * A "join" control, and the one decision every one of them makes.
 *
 * **A guest is sent to the sign-up page, not to the wizard.** They used to land
 * on `/join`, which — having no session to work with — could only draw a
 * "Sign in to continue" card and offer the same two links again. That card was
 * a bridge between two pages that both said the same thing, and the second one
 * is the one that can actually do something. So the bridge is gone: the header's
 * "Join us", the hero's two paths, the membership band and the closing call to
 * action all open the same auth page the header's "Sign in" opens. Which panel
 * it shows is the only difference between them.
 *
 * **The intent survives the round trip.** `signupUrl` writes the destination
 * into `redirect-to`, which Frappe stashes against the new account and the
 * verification link honours — so somebody who pressed "Become a volunteer"
 * comes back to the volunteer path rather than to the front page, having
 * forgotten why they were sent away. `useHref` is what makes that
 * address correct: the router is mounted under a basename (`/home`), and a bare
 * `/join?path=volunteer` would be a site path this app does not answer.
 *
 * **Somebody already signed in keeps the direct route.** They have the session
 * the wizard wanted; sending them through a sign-in page to get it would be the
 * bridge again, pointing the other way.
 */
export function JoinLink({
	to,
	className,
	children,
}: {
	to: string;
	className?: string;
	children: ReactNode;
}) {
	const { isGuest, isLoading } = useSession();
	// Unconditional, as every hook must be: the basename-qualified address is
	// cheap and only one of the two branches below reads it.
	const href = useHref(to);

	// While the session is still unknown, the client route is the safe render:
	// `/join` resolves for both audiences, and only the guest's extra hop is
	// deferred until we know they are one.
	if (isLoading || !isGuest) {
		return (
			<Link to={to} className={className}>
				{children}
			</Link>
		);
	}

	// A real navigation, not a route: the auth page is Frappe's and is not part
	// of this bundle.
	return (
		<a href={signupUrl(href)} className={className}>
			{children}
		</a>
	);
}
