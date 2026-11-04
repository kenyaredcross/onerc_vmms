# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The county shapes the Region and National maps are drawn from.

A society attaches its own boundary file in National Society Settings; this app
ships no country's map. The file is read once, its shapes matched to the
society's counties, simplified to what a console map needs, projected into one
fixed frame and cached. The browser is handed SVG paths and draws them.

**What a society may attach.** A GeoJSON file, or a zip of them, which is how
the UN's common operational datasets (`cod-ab-*` on HDX) are published: one
file per administrative level. From a zip the layer that matches the most
counties is used, so the archive can be attached as downloaded.

**How a shape is matched to a county**, in order:

1. a property whose value is the county's `geo_code`;
2. a property whose trailing digits are the trailing digits of the `geo_code`
   (`KE001` and `KE-COUNTY-001`);
3. a name property equal to the county's name, ignoring case, spaces and
   punctuation (`Elgeyo-Marakwet` and `Elgeyo Marakwet`);
4. a name that is the start of the other, where only one shape fits
   (`Nairobi` and `Nairobi City`).

A county no shape matches is drawn as a circle at its saved coordinates, the
same as every county is when no file has been attached, so a map is never
missing a county because a spelling differs.

**The projection is plain**: longitude scaled by the cosine of the middle
latitude, latitude flipped. Accurate enough for one country, and nothing a
reader is asked to measure on.
"""

import io
import json
import math
import re
import zipfile

import frappe

SETTINGS_DOCTYPE = "National Society Settings"
FILE_FIELD = "vmms_boundary_file"
CREDIT_FIELD = "vmms_boundary_credit"

WIDTH = 1000
# Douglas–Peucker tolerance in degrees: about a kilometre, invisible at the
# size the map is drawn and a fraction of the original file.
TOLERANCE = 0.01
CACHE_KEY = "vmmsx:boundaries"

NAME_KEYS = ("name", "adm1_en", "adm1_name", "name_1", "county", "county_nam", "admin1name", "shapename")


def shapes(units: list[dict]) -> dict:
	"""Paths for `units` (every county), or circles where there is no shape."""
	source = _source()
	features = _cached_features(source) if source else []
	matched = _match(features, units)

	points = [_lonlat(unit) for unit in units]
	rings = [ring for unit in units for ring in matched.get(unit["name"], [])]
	frame = _frame([point for point in points if point] + [p for ring in rings for p in ring])

	out = []

	for unit, point in zip(units, points):
		polygons = matched.get(unit["name"])

		if polygons:
			out.append({"name": unit["name"], "path": _path(polygons, frame), "centre": _project(_centre(polygons), frame)})
		elif point:
			out.append({"name": unit["name"], "path": None, "centre": _project(point, frame)})

	return {
		"view_box": f"0 0 {WIDTH} {frame['height']:.0f}",
		"shapes": out,
		"has_file": bool(features),
		"matched": len(matched),
		"credit": _credit(),
	}


# --- reading the file ---------------------------------------------------------------


def _source() -> str | None:
	if not frappe.get_meta(SETTINGS_DOCTYPE).has_field(FILE_FIELD):
		return None

	return frappe.db.get_single_value(SETTINGS_DOCTYPE, FILE_FIELD) or None


def _credit() -> str | None:
	if not frappe.get_meta(SETTINGS_DOCTYPE).has_field(CREDIT_FIELD):
		return None

	return frappe.db.get_single_value(SETTINGS_DOCTYPE, CREDIT_FIELD) or None


def _cached_features(url: str) -> list[dict]:
	"""The file's layers, simplified, cached until the attachment changes."""
	key = f"{CACHE_KEY}:{url}"
	cached = frappe.cache.get_value(key)

	if cached is not None:
		return cached

	try:
		layers = _layers(_read(url))
	except Exception:
		frappe.log_error(title="The county boundary file could not be read")
		layers = []

	frappe.cache.set_value(key, layers, expires_in_sec=7 * 24 * 3600)

	return layers


def _read(url: str) -> bytes:
	name = frappe.db.get_value("File", {"file_url": url}, "name")

	if not name:
		return b""

	return frappe.get_doc("File", name).get_content() or b""


def _layers(content: bytes) -> list[list[dict]]:
	"""Each GeoJSON layer in the file as [{properties, polygons}]."""
	if not content:
		return []

	if content[:2] == b"PK":
		with zipfile.ZipFile(io.BytesIO(content)) as archive:
			return [
				_layer(json.loads(archive.read(member)))
				for member in archive.namelist()
				if member.lower().endswith((".geojson", ".json")) and not member.startswith("__MACOSX")
			]

	return [_layer(json.loads(content))]


def _layer(geojson: dict) -> list[dict]:
	out = []

	for feature in geojson.get("features") or []:
		geometry = feature.get("geometry") or {}
		kind, coordinates = geometry.get("type"), geometry.get("coordinates") or []

		if kind == "Polygon":
			polygons = [coordinates]
		elif kind == "MultiPolygon":
			polygons = coordinates
		else:
			continue

		# The outer ring of each part. Holes are lakes and enclaves, not lines a
		# reader of a county map needs.
		rings = [_simplify([tuple(point[:2]) for point in polygon[0]]) for polygon in polygons if polygon]
		rings = [ring for ring in rings if len(ring) >= 4]

		if rings:
			out.append({"properties": {k: v for k, v in (feature.get("properties") or {}).items() if isinstance(v, (str, int))}, "rings": rings})

	return out


# --- matching ------------------------------------------------------------------------


def _match(layers: list[list[dict]], units: list[dict]) -> dict[str, list]:
	"""{county: rings} from whichever layer matches the most counties."""
	best = {}

	for layer in layers:
		found = {}

		for unit in units:
			feature = _find(layer, unit)

			if feature:
				found[unit["name"]] = feature["rings"]

		if len(found) > len(best):
			best = found

	return best


def _find(layer: list[dict], unit: dict) -> dict | None:
	code = (unit.get("code") or "").strip()
	digits = _digits(code)
	name = _plain(unit.get("label"))

	for test in (
		lambda value, key: code and str(value) == code,
		lambda value, key: digits and _digits(str(value)) == digits and not str(value).isdigit() and len(_digits(str(value))) == len(digits),
		lambda value, key: key.lower() in NAME_KEYS and name and _plain(value) == name,
	):
		for feature in layer:
			if any(test(value, key) for key, value in feature["properties"].items()):
				return feature

	# Last, and only when it picks out one shape: one name the start of the
	# other ("Nairobi" and "Nairobi City").
	if name:
		loose = [
			feature
			for feature in layer
			if any(
				key.lower() in NAME_KEYS and _plain(value) and (_plain(value).startswith(name) or name.startswith(_plain(value)))
				for key, value in feature["properties"].items()
			)
		]

		if len(loose) == 1:
			return loose[0]

	return None


def _digits(value: str) -> str:
	match = re.search(r"(\d+)$", value or "")
	return match.group(1) if match else ""


def _plain(value) -> str:
	return re.sub(r"[^a-z]", "", str(value or "").lower())


# --- geometry --------------------------------------------------------------------------


def _simplify(points: list[tuple], tolerance: float = TOLERANCE) -> list[tuple]:
	"""Douglas–Peucker, iteratively, so a long coastline cannot recurse too deep."""
	if len(points) < 3:
		return points

	keep = [False] * len(points)
	keep[0] = keep[-1] = True
	stack = [(0, len(points) - 1)]

	while stack:
		start, end = stack.pop()
		furthest, index = 0.0, None

		for i in range(start + 1, end):
			distance = _distance(points[i], points[start], points[end])

			if distance > furthest:
				furthest, index = distance, i

		if index is not None and furthest > tolerance:
			keep[index] = True
			stack += [(start, index), (index, end)]

	return [(round(p[0], 4), round(p[1], 4)) for p, kept in zip(points, keep) if kept]


def _distance(point, start, end) -> float:
	(x, y), (x1, y1), (x2, y2) = point, start, end
	dx, dy = x2 - x1, y2 - y1

	if dx == dy == 0:
		return math.hypot(x - x1, y - y1)

	return abs(dy * x - dx * y + x2 * y1 - y2 * x1) / math.hypot(dx, dy)


def _lonlat(unit: dict) -> tuple | None:
	point = unit.get("point")
	return (float(point["longitude"]), float(point["latitude"])) if point else None


def _centre(rings: list) -> tuple:
	"""The middle of the largest part: where a county's label or dot goes."""
	ring = max(rings, key=len)
	xs, ys = [p[0] for p in ring], [p[1] for p in ring]
	return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)


def _frame(points: list[tuple]) -> dict:
	if not points:
		return {"west": 0, "north": 0, "scale": 1, "cos": 1, "height": WIDTH * 0.75}

	west, east = min(p[0] for p in points), max(p[0] for p in points)
	south, north = min(p[1] for p in points), max(p[1] for p in points)
	cos = math.cos(math.radians((north + south) / 2)) or 1
	span = max((east - west) * cos, 1e-6)
	# A margin, so a circle on the edge is not cut in half.
	pad = span * 0.04
	scale = WIDTH / (span + 2 * pad)

	return {
		"west": west - pad / cos,
		"north": north + pad,
		"scale": scale,
		"cos": cos,
		"height": max((north - south + 2 * pad) * scale, 1),
	}


def _project(point: tuple, frame: dict) -> list[float]:
	return [
		round((point[0] - frame["west"]) * frame["cos"] * frame["scale"], 1),
		round((frame["north"] - point[1]) * frame["scale"], 1),
	]


def _path(rings: list, frame: dict) -> str:
	parts = []

	for ring in rings:
		projected = [_project(point, frame) for point in ring]
		parts.append("M" + "L".join(f"{x:g},{y:g}" for x, y in projected) + "Z")

	return "".join(parts)
