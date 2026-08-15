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
interface Branding {
	name: string;
	short_name: string;
	logo: string;
	logo_dark: string;
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
}: {
	tone?: "light" | "dark";
	compact?: boolean;
	/**
	 * The two lockup sizes the landing page uses, from option 7a: `md` in the
	 * 58px header, `sm` in the footer beside the emergency number. `compact`
	 * still wins, because it is the collapsed sidebar and is narrower than both.
	 */
	size?: "md" | "sm";
}) {
	const dark = tone === "dark";
	const small = size === "sm" && !compact;

	// Shared SWR key across every mount, so the sidebar, the landing header and
	// the wizard header cost one request between them rather than three.
	const { data } = useFrappeGetCall<{ message: Branding }>(
		API.societyBranding,
		undefined,
		"society:branding",
	);

	const society = data?.message;
	const mark = (dark ? society?.logo_dark : society?.logo) || "";
	// The full name is the society's, and the short name is what it calls itself
	// in a corner. Compact takes the short one where there is one, because a
	// collapsed sidebar is 56 pixels wide.
	const name = (compact && society?.short_name) || society?.name || society?.short_name || "";

	return (
		<div className="flex flex-none items-center gap-[9px]">
			{mark ? (
				<img
					src={mark}
					alt=""
					className={cx("w-auto object-contain", compact ? "h-6" : small ? "h-[22px]" : "h-8")}
					// The society's own upload, at whatever aspect it was made in.
					// Constraining the height and letting the width follow is the
					// only rule that does not distort somebody's emblem.
				/>
			) : (
				<CrossMark className="text-signal" size={compact ? 20 : small ? 17 : 21} />
			)}

			{name && (
				<span
					className={cx(
						"font-display font-extrabold leading-tight tracking-tight",
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
