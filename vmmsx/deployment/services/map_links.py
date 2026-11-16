# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A point from what a coordinator pastes: coordinates, or a Google Maps link.

The society has no paid map account, so when the free place search cannot find
somewhere the coordinator finds it on Google Maps in their browser and pastes
what it gives them. That is one of three things:

* the coordinates, copied by right-clicking the spot — `-1.29207, 36.82195`
* the page's own address — `…/@-1.29207,36.82195,17z/…`, `…!3d-1.29!4d36.82…`,
  `…?q=-1.29,36.82`
* a share link from a phone — `https://maps.app.goo.gl/…`, which says nothing
  until it is followed, so `follow` does that.

`portal/src/admin/deployments/mapLinks.ts` reads the first two in the browser;
this module reads all three and is the only one that may follow a link.
"""

import re
from urllib.parse import unquote, urljoin, urlparse

import requests

# Only Google's own short-link hosts are ever fetched.
SHORT_HOSTS = {"maps.app.goo.gl", "goo.gl"}
MAX_HOPS = 5
TIMEOUT = 5

_NUMBER = r"(-?\d{1,3}(?:\.\d+)?)"
_PATTERNS = (
	re.compile(r"!3d" + _NUMBER + r"!4d" + _NUMBER),
	re.compile(r"@" + _NUMBER + r"," + _NUMBER),
	re.compile(r"[?&](?:q|query|ll|destination|center)=" + _NUMBER + r"\s*,\s*" + _NUMBER),
	re.compile(r"/place/" + _NUMBER + r"\s*,\s*" + _NUMBER),
	re.compile(r"^\s*" + _NUMBER + r"\s*[, ]\s*" + _NUMBER + r"\s*$"),
)


def point_in(text: str | None) -> dict | None:
	"""The latitude and longitude written in this text, or None."""
	text = unquote(text or "")

	for pattern in _PATTERNS:
		found = pattern.search(text)

		if found:
			latitude, longitude = float(found.group(1)), float(found.group(2))

			if -90 <= latitude <= 90 and -180 <= longitude <= 180 and (latitude or longitude):
				return {"latitude": latitude, "longitude": longitude}

	return None


def follow(url: str | None) -> dict | None:
	"""Follow a Google Maps short link to the page it opens, and read its point.

	Never raises: a link that will not resolve is simply a link with no point,
	and the screen says to copy the coordinates instead.
	"""
	found = point_in(url)

	if found:
		return found

	current = (url or "").strip()

	for _hop in range(MAX_HOPS):
		if urlparse(current).hostname not in SHORT_HOSTS:
			return point_in(current)

		try:
			answer = requests.get(current, allow_redirects=False, timeout=TIMEOUT)
		except requests.RequestException:
			return None

		location = answer.headers.get("Location")

		if not location:
			return point_in(answer.text[:20000])

		current = urljoin(current, location)
		found = point_in(current)

		if found:
			return found

	return None
