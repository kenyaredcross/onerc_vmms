import {
	createContext,
	useCallback,
	useContext,
	useMemo,
	useState,
	type ReactNode,
} from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage } from "../lib/api";

/** One editable slot, exactly as `blocks.block_dto` builds it. */
export interface Block {
	key: string;
	label: string;
	text: string;
	href: string;
	image: string | null;
	image_alt: string;
	image_credit: string;
}

export type BlockPatch = Partial<Pick<Block, "text" | "href" | "image" | "image_alt" | "image_credit">>;

interface SurfaceResponse {
	surface: string;
	blocks: Record<string, Block>;
	can_edit: boolean;
}

interface ContentValue {
	/** The block for a key, or undefined when the site has never seeded one. */
	get: (key: string) => Block | undefined;
	/** Whether this user may reword the page at all. Answered by the server. */
	canEdit: boolean;
	/** Whether the pencils are currently showing. */
	editing: boolean;
	setEditing: (on: boolean) => void;
	/** Write one slot. Resolves when the server has accepted it. */
	save: (key: string, patch: BlockPatch) => Promise<void>;
	isLoading: boolean;
	error: string | null;
}

const ContentContext = createContext<ContentValue | null>(null);

/**
 * Loads one surface's wording and makes it editable in place.
 *
 * **One request per surface, not per slot.** A page has seventy-odd editable
 * strings on it; seventy requests would be seventy round trips before the hero
 * paints. The provider fetches the surface once and every `Editable` below it
 * reads out of that dictionary.
 *
 * **Saving is optimistic against the local cache, then confirmed.** The pencil
 * closes immediately and the new words are on the page; if the server refuses,
 * the mutate below pulls the truth back and the editor sees the old text return
 * along with the message. Anything else means an editor watching a spinner
 * after every full stop.
 *
 * **`canEdit` is a hint, never the check.** It decides whether a pencil is
 * drawn. The endpoint re-asks the permission layer on every write, so a browser
 * that flips this flag gains an inert pencil and a refusal.
 */
export function ContentProvider({ surface, children }: { surface: string; children: ReactNode }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [editing, setEditing] = useState(false);

	const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: SurfaceResponse }>(
		API.contentSurface,
		{ surface },
		`content:${surface}`,
		{
			// Wording changes when somebody edits it, which this provider already
			// knows about. Re-fetching on every window focus would be a request
			// per tab switch for data that cannot have changed underneath.
			revalidateOnFocus: false,
		},
	);

	const blocks = data?.message?.blocks;
	const canEdit = Boolean(data?.message?.can_edit);

	const get = useCallback((key: string) => blocks?.[key], [blocks]);

	const save = useCallback(
		async (key: string, patch: BlockPatch) => {
			// The API names its fields as the doctype does; the DTO shortens them
			// for the components. Translated here, in the one place that knows
			// about both.
			const payload: Record<string, string> = { content_key: key };
			if (patch.text !== undefined) payload.text_value = patch.text;
			if (patch.href !== undefined) payload.link_href = patch.href;
			if (patch.image !== undefined) payload.image = patch.image ?? "";
			if (patch.image_alt !== undefined) payload.image_alt = patch.image_alt;
			if (patch.image_credit !== undefined) payload.image_credit = patch.image_credit;

			const optimistic = blocks?.[key]
				? { ...data!.message, blocks: { ...blocks, [key]: { ...blocks[key], ...patch } } }
				: undefined;

			if (optimistic) {
				await mutate({ message: optimistic }, { revalidate: false });
			}

			try {
				await call.post(API.contentUpdate, payload);
			} finally {
				// Whether it succeeded or threw, the server is now the authority
				// on what this slot says. On success this confirms the optimistic
				// write; on failure it undoes it.
				await mutate();
			}
		},
		[blocks, call, data, mutate],
	);

	const value = useMemo<ContentValue>(
		() => ({
			get,
			canEdit,
			// Edit mode cannot be on for somebody who may not edit, whatever the
			// toggle's local state says. One expression rather than two places
			// that have to agree.
			editing: canEdit && editing,
			setEditing,
			save,
			isLoading,
			error: error ? errorMessage(error, "The page content could not be loaded.") : null,
		}),
		[get, canEdit, editing, save, isLoading, error],
	);

	return <ContentContext.Provider value={value}>{children}</ContentContext.Provider>;
}

/**
 * The content of the nearest surface.
 *
 * Throws when used outside a provider, deliberately: a silent fallback here
 * would mean a page that renders empty headings in production and nobody
 * noticing until a visitor mentioned it.
 */
export function useContent(): ContentValue {
	const value = useContext(ContentContext);

	if (!value) {
		throw new Error("useContent must be used inside a <ContentProvider>.");
	}

	return value;
}

/**
 * The text of one slot, without subscribing to the editing machinery.
 *
 * For the places that need a string rather than a rendered element: a `title`
 * attribute, an `alt`, a document title.
 */
export function useText(key: string, fallback = ""): string {
	const { get } = useContent();
	return get(key)?.text || fallback;
}
