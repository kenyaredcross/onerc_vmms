/**
 * The handful of facts a page's wording may quote.
 *
 * A block may carry `{country}` or `{society}` instead of naming either, and
 * the value is filled in when the block is drawn:
 *
 *     Show up for {country|your community}.
 *
 * The part after the pipe is what to say when there is no value, which is the
 * ordinary state of a site whose settings form nobody has opened yet. Without
 * one a fresh site's hero reads "Show up for .", so every token this app seeds
 * carries a default.
 *
 * **Only the two words in `KEYS` are tokens.** Everything else between braces is
 * somebody's prose and is left where they typed it.
 *
 * **Resolved on the way to the screen, never into the stored text.** The pencil
 * edits `{country|your community}` and the visitor reads "Tanzania", which is
 * what keeps one society's copy out of another society's database — the whole
 * argument is in `vmmsx/content/services/tokens.py`, which does the same
 * substitution for the two Jinja auth pages. Two implementations because React
 * cannot call Python, and resolving server-side would hand the editor the
 * resolved sentence and lose the token on the next save.
 */

/**
 * `{key}` or `{key|what to say when there is no value}`.
 *
 * Deliberately narrow: a key is a bare word, so a stray brace in somebody's
 * prose — "{see note}" — is left alone rather than eaten.
 */
const TOKEN = /\{(\w+)(?:\|([^{}]*))?\}/g;

/** What the tokens stand for. Every value may be empty, and empty is ordinary. */
export interface TokenValues {
	country?: string;
	society?: string;
}

/**
 * The whole vocabulary, and the reason it is a constant rather than the keys of
 * whatever was passed in: **anything not named here is left exactly as it was
 * written.** An administrator's own prose is full of brace-words this app has
 * never heard of, and the failure this avoids is the silent one — substituting
 * an unknown key would delete their words with nothing on the page to show it
 * had happened, where a brace left where they typed it is visible and fixable.
 * It also means a page rendering before `society:branding` has landed shows the
 * seeded fallbacks rather than braces.
 */
const KEYS: ReadonlySet<string> = new Set(["country", "society"]);

/** One block's text with its tokens filled in. See `KEYS` for what is one. */
export function resolveTokens(text: string, values: TokenValues): string {
	if (!text || !text.includes("{")) return text;

	return text.replace(TOKEN, (match, key: string, fallback?: string) => {
		if (!KEYS.has(key)) return match;

		return (values[key as keyof TokenValues] ?? "").trim() || fallback || "";
	});
}
