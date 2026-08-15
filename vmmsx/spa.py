# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Resolve the hashed Vite entry assets for the www SPA pages.

The frontend is built into public/portal with a manifest; we read it server-side
so the page always points at the current hashed bundle (no fixed-name cache
issues, and no copied index.html to fall out of step with the build).
"""

import json

import frappe

_BASE = "/assets/vmmsx/portal/"


def _unbuilt() -> dict:
	"""No bundle to point at. The page says so rather than throwing a 500."""
	return {"js": "", "css": []}


def resolve_assets(entry: str = "index.html") -> dict:
	"""Return {'js': url, 'css': [urls]} for a Vite manifest entry.

	An unbuilt bundle is not an error here: it returns empty strings and the
	page says so, rather than throwing a 500 on a fresh bench.
	"""
	manifest_path = frappe.get_app_path("vmmsx", "public", "portal", ".vite", "manifest.json")
	# Two handlers rather than `except (A, B)`: the bench environment's ruff
	# formatter rewrites the parenthesised form into invalid Python 3 (see the
	# environment note in CLAUDE.md).
	try:
		with open(manifest_path) as fh:
			manifest = json.load(fh)
	except FileNotFoundError:
		return _unbuilt()
	except ValueError:
		return _unbuilt()

	item = manifest.get(entry) or next((v for v in manifest.values() if v.get("isEntry")), {})
	if not item.get("file"):
		return _unbuilt()

	# Collect CSS from the entry and its static imports (Vite splits shared CSS
	# into chunks). Route-level CSS is loaded on demand by Vite.
	css: list[str] = []
	seen: set[str] = set()

	def collect(node: dict, key: str | None = None) -> None:
		if key is not None:
			if key in seen:
				return
			seen.add(key)
		for href in node.get("css", []):
			url = _BASE + href
			if url not in css:
				css.append(url)
		for imp in node.get("imports", []):
			collect(manifest.get(imp, {}), imp)

	collect(item)
	return {"js": _BASE + item["file"], "css": css}
