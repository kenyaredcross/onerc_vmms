# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A QR code, as bytes inside the document that shows it.

**A data URI and never a URL to an image**, for the same reason
`certificate.printable_asset` is one: a card is rendered to PDF as often as it
is rendered to a screen, and a PDF renderer has no page to resolve a relative
path against and no guarantee it can reach this site over HTTP at all. Bytes in
the document render identically on a laptop, in a container with no ingress,
and behind authentication.

**Never raises.** A card whose QR could not be drawn is a card with a gap in
it; a card that refuses to print because of one is a person who cannot prove
they are a volunteer. Every caller treats an empty string as "no QR" and the
shipped templates guard on it, exactly as they do for a society that has
uploaded no logo.

Domain-free: it takes a string and gives back a data URI.
"""

from base64 import b64encode
from io import BytesIO

import frappe

LOG_TITLE = "Card QR could not be drawn"

# Rendered small and scaled by CSS. A QR is square modules, so the bytes only
# need to carry enough resolution for print; the card decides its size.
BOX_SIZE = 8
BORDER = 2


def data_uri(text: str) -> str:
	"""`text` as a PNG QR code in a `data:` URI, or "" if it could not be drawn."""
	if not (text or "").strip():
		return ""

	try:
		import qrcode

		image = qrcode.make(text, box_size=BOX_SIZE, border=BORDER)
		buffer = BytesIO()
		image.save(buffer, format="PNG")

		return f"data:image/png;base64,{b64encode(buffer.getvalue()).decode()}"
	except Exception:
		# Cosmetic, so it is logged and swallowed. See the module docstring.
		frappe.log_error(title=LOG_TITLE, message=frappe.get_traceback())

		return ""
