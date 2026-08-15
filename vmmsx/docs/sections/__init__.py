# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The guide's sections, in the order they appear.

One module per top-level section, and the order of this tuple is the order of
the document and of its contents page. A later stage appends its module here
and leaves the earlier ones untouched — the guide grows, it is not rewritten.

Each module exposes:

    TITLE     str                  the section heading
    SUMMARY   str                  one line, for the cover
    render    (writer) -> None     the body, starting with writer.h1(TITLE)
"""

from vmmsx.docs.sections import (
	approval_engine,
	buzz,
	content,
	deployment,
	member,
	notifications,
	self_service,
	stipend,
	volunteer,
)

# Deployment sits after Volunteer because it reads as a continuation of it: the
# deployment time log finishes a rule the volunteer spine specified, and matching
# is built on the certifications the volunteer register holds. Stipend follows
# Deployment for the same reason: it is the paperwork for volunteers who have
# been sent to do something, and its picker is the volunteer register's scope
# question asked again. Buzz sits after Stipend as unrelated, lateral
# infrastructure — a seam onto another app entirely, owing nothing to the
# volunteer/member spine before it. Self-service stays last, as the surfaces
# layer over everything before it — and Content sits with it, immediately after,
# because it is the same subject read the other way round: Self-service is the
# desk surfaces built from records Frappe already has, Content is the portal
# surface and the records that make its every sentence configuration. Notifications
# closes the guide because it is the last thing added and reads as a consequence
# of everything before it: it addresses the volunteers and members the earlier
# sections describe, at the geo nodes the approval engine already routes by, and
# it is read on the portal surface Content documents.
SECTIONS = (
	approval_engine,
	member,
	volunteer,
	deployment,
	stipend,
	buzz,
	self_service,
	content,
	notifications,
)
