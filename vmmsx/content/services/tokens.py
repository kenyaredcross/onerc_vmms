# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The handful of facts a page's wording may quote, and how it quotes them.

A content block is a sentence somebody in the society owns. Most of them say
the same thing whoever is reading, but a few want to name the society or the
country it works in — and those are exactly the two facts this app is forbidden
to write into a sentence, because they live on core's `National Society
Settings` and a second copy of them goes stale the day somebody edits the
first. The shipped hero headline is the case in point: "Show up for your
community." is true everywhere and lands nowhere, and "Show up for Kenya." is
one society's copy sitting in every society's source.

So a block may carry a token instead, and the token is resolved *at render*:

    Show up for {country|your community}.

`{country}` is the value; the part after the pipe is what to say when there
isn't one, which is the ordinary state of a site whose settings form nobody has
opened yet. A default is not decoration — without it, a fresh site's front page
reads "Show up for ." — so every token this app seeds carries one.

**Only the two words in `KEYS` are tokens.** Everything else between braces is
somebody's prose and is left where they typed it.

**Resolved on the way out, never on the way in.** What is stored is the token,
what is drawn is the value, and the pencil edits the token. Substituting into
the stored text would mean the first person to open the editor silently freezing
today's country into the sentence, which is the staleness this exists to avoid.
That rule is why this module has no writer: `blocks.write_block` never calls it.

The frontend has its own copy of the substitution, in
`portal/src/content/tokens.ts`, for the same reason the auth stylesheet carries
the palette as literals: React cannot call this, and the alternative — resolving
inside `api/content.py::surface` — would hand the editor the resolved sentence
and lose the token on the next save.
"""

import re

import frappe

#: `{key}` or `{key|what to say when there is no value}`. Deliberately narrow:
#: a key is a bare word, so a stray brace in somebody's prose — "{see note}" —
#: is left alone rather than eaten.
TOKEN = re.compile(r"\{(\w+)(?:\|([^{}]*))?\}")

#: The whole vocabulary, and the reason it is a constant rather than whatever
#: `values()` happened to return: **anything not named here is left exactly as
#: it was written.** An administrator's own prose is full of brace-words this
#: app has never heard of, and the failure this avoids is the silent one —
#: substituting an unknown key would delete their words with nothing on the page
#: to show it had happened, where a brace left where they typed it is visible
#: and fixable. It also means a settings read that fails resolves to the seeded
#: fallbacks rather than to braces, because the vocabulary is known even when
#: the values are not.
KEYS = ("country", "society")


def values() -> dict[str, str]:
	"""What the tokens stand for on this site. Empty is an ordinary answer.

	Read through core's service, like every other reader of society identity in
	this app — see `api/society.py` for why there is no fourth home for it.

	Never raises. This is called while rendering pages, including the sign-in
	page, and the rule there is absolute: a settings single that will not load
	has to produce a page whose wording falls back, not a traceback.
	"""
	try:
		from onerc_core.society.services.config import get_ui_config

		society = get_ui_config()["society"]
	except Exception:
		frappe.log_error(title="vmmsx: could not read society values for content tokens")
		society = {}

	return {
		"country": (society.get("country") or "").strip(),
		# The full name, not the short one. A sentence that names the society is
		# a sentence naming it properly; the abbreviation belongs in a corner,
		# which is where `BrandLockup` draws it.
		"society": (society.get("name") or society.get("short_name") or "").strip(),
	}


def resolve(text: str, known: dict[str, str] | None = None) -> str:
	"""One block's text with its tokens filled in. See `KEYS` for what is one."""
	if not text or "{" not in text:
		return text

	known = values() if known is None else known

	def substitute(match: re.Match) -> str:
		key, fallback = match.group(1), match.group(2)

		if key not in KEYS:
			return match.group(0)

		return (known.get(key) or "").strip() or (fallback or "")

	return TOKEN.sub(substitute, text)


def resolve_words(words: dict[str, str]) -> dict[str, str]:
	"""A whole surface's text, resolved once against one read of the values."""
	known = values()

	return {key: resolve(text, known) for key, text in words.items()}
