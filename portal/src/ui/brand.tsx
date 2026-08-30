import { useFrappeGetCall } from "frappe-react-sdk";

import { API } from "../lib/api";
import { cx } from "./primitives";

/**
 * The fallback mark.
 *
 * A geometric cross drawn in the signal colour, not the Red Cross emblem. That
 * distinction is not cosmetic: the emblem is protected under the Geneva
 * Conventions and national legislation, and shipping one in an app's source
 * would put it on every society's screens whether or not that society is
 * entitled to display it there. A society uploads its own mark to National
 * Society Settings; this is what stands in until it does.
 */
export function CrossMark({ size = 22, className }: { size?: number; className?: string }) {
	return (
		<svg
			width={size}
			height={size}
			viewBox="0 0 24 24"
			className={className}
			aria-hidden="true"
			focusable="false"
		>
			<path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6z" fill="currentColor" />
		</svg>
	);
}

/** `api/society.py::branding`. */
export interface Branding {
	name: string;
	short_name: string;
	logo: string;
	logo_dark: string;
}

/**
 * The society's own name and marks, wherever a screen needs to say them.
 *
 * The lockup below is not the only place a society's identity is drawn: the
 * message composer renders a mock of the email it is about to send, and the
 * name on that mock is the name of the society sending it. Hardcoding one there
 * put "Tanzania Red Cross Society" on the screens of every society that is not
 * Tanzania's.
 *
 * **One request between every caller.** The SWR key is shared and constant, so
 * the sidebar, the landing header, the wizard header and the composer preview
 * cost one call between them however many of them are mounted.
 *
 * **It can answer nothing, and nothing is an ordinary answer.** A site whose
 * settings singleton has never been saved has no name, and a caller has to draw
 * something neutral rather than borrow another society's — see `BrandLockup`,
 * which renders no name at all rather than a stand-in.
 */
export function useSocietyBranding(): Branding | undefined {
	const { data } = useFrappeGetCall<{ message: Branding }>(
		API.societyBranding,
		undefined,
		"society:branding",
	);

	return data?.message;
}

/**
 * The society's own logo and name, read from National Society Settings.
 *
 * **Not content blocks, and that is the point of this component.** The lockup
 * used to be two `EditableText`s — the product's name beside a short name an
 * administrator typed into the page. A society that had already uploaded its
 * logo and named itself in settings still saw a placeholder mark and a product
 * name, because the page held a second copy of an identity core already owned.
 * So this reads the one home that identity has, the same rule `VMMS Volunteer`
 * follows about Red Profile: read on every call, copied nowhere.
 *
 * **The mark falls back and the name does not.** A society with no logo uploaded
 * gets `CrossMark`, because a broken image is worse than a placeholder. A
 * society whose settings carry no name at all gets nothing rather than somebody
 * else's name, which is the only honest answer.
 *
 * `tone` picks the palette rather than the caller passing class names: the
 * lockup appears on white, on navy and on near-black, and each needs different
 * contrast. It also picks *which* logo — `logo_dark` for a dark surface, which
 * core already falls back to `logo` for.
 */
export function BrandLockup({
	tone = "light",
	compact = false,
	size = "md",
	wrap = false,
}: {
	tone?: "light" | "dark";
	compact?: boolean;
	/**
	 * The two lockup sizes the landing page uses, from option 7a: `md` in the
	 * 58px header, `sm` in the footer beside the emergency number. `compact`
	 * still wins, because it is the collapsed sidebar and is narrower than both.
	 */
	size?: "md" | "sm";
	/**
	 * Let a long name break onto a second line instead of ending in an
	 * ellipsis — for the rail, which has the vertical room to spare and never
	 * wants a society's own name silently cut off. Everywhere else this sits
	 * in a fixed-height bar (the top bar, the landing header), where a second
	 * line would overflow it rather than fit inside it, so those keep the
	 * one-line, truncated default.
	 */
	wrap?: boolean;
}) {
	const dark = tone === "dark";
	const small = size === "sm" && !compact;

	const society = useSocietyBranding();
	const mark = (dark ? society?.logo_dark : society?.logo) || "";
	// The full name is the society's, and the short name is what it calls itself
	// in a corner. Compact takes the short one where there is one, because a
	// collapsed sidebar is 56 pixels wide.
	const name = (compact && society?.short_name) || society?.name || society?.short_name || "";

	return (
		<div className={cx("flex min-w-0 gap-[9px]", wrap ? "items-start" : "items-center")}>
			{mark ? (
				<img
					src={mark}
					alt=""
					className={cx("w-auto flex-none object-contain", compact ? "h-6" : small ? "h-[22px]" : "h-8")}
					// The society's own upload, at whatever aspect it was made in.
					// Constraining the height and letting the width follow is the
					// only rule that does not distort somebody's emblem.
				/>
			) : (
				<CrossMark className="flex-none text-signal" size={compact ? 20 : small ? 17 : 21} />
			)}

			{name && (
				<span
					className={cx(
						"font-display font-extrabold leading-tight tracking-tight",
						wrap ? "line-clamp-2 break-words" : "truncate",
						compact ? "text-[13px]" : small ? "text-[14px]" : "text-[16px]",
						dark ? "text-white" : "text-ink",
					)}
				>
					{name}
				</span>
			)}
		</div>
	);
}
