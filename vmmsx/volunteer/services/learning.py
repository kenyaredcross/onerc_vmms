# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The learning seam — the only file in vmmsx that knows an LMS exists.

**What crosses the boundary, and in which direction.** This module reads one
fact out of the learning system — *this person finished that course* — and
writes one record of our own: a `VMMS Certification`. Nothing goes the other
way, and no LMS model comes across with it. There is no enrollment, no lesson,
no quiz, no batch and no LMS certificate anywhere in the vmmsx domain, and no
other file in this app names an LMS doctype. If the society replaces its LMS
next year, this file is the diff.

**The mapping is configuration, not code.** Which course produces which
certification lives in `VMMS Course Mapping`, one row per course, written by an
administrator. No course name and no certification name appears here — pointing
a mapping at a different `VMMS Certification Type` changes what every future
completion of that course awards, with no code change anywhere in the app. That
is the whole point of the doctype: the alternative is a dictionary in a source
file that a society cannot edit.

**Identity crosses through Red Profile, never around it.** The learning system
knows a `User`. This app knows a volunteer. The path between them is
User → Red Profile → `VMMS Volunteer`, because Red Profile is core's identity
spine and resolving people any other way would be a second answer to who
somebody is. A learner with no Red Profile, or a profile with no volunteer
record, is not an error — it is somebody doing a course who is not a volunteer,
and the seam has nothing to say about them.

**The seam is safe when the LMS is absent.** vmmsx declares
`required_apps = ["onerc_core"]` and not the LMS: a society running volunteering
without one is ordinary. The hook simply never fires, `is_available()` answers
honestly, and `sync_volunteer()` reports that it read nothing rather than
raising.
"""

import frappe
from frappe.utils import flt, getdate, today

from vmmsx.volunteer.services import certification

# --- the boundary ---------------------------------------------------------
#
# Every name the learning system owns is gathered here, in one block, so that
# the surface this app depends on can be read at a glance and swapped in one
# place. Below this block, the module speaks only vmmsx's own vocabulary.

LEARNING_APP = "lms"

ENROLLMENT_DOCTYPE = "LMS Enrollment"
ENROLLMENT_LEARNER_FIELD = "member"
ENROLLMENT_COURSE_FIELD = "course"
ENROLLMENT_PROGRESS_FIELD = "progress"

# The learning system records progress as a percentage of the course's lessons.
# Finished is finished; a course 99% done has not been completed.
COMPLETE_AT_PERCENT = 100.0

# --- ours -----------------------------------------------------------------

MAPPING_DOCTYPE = "VMMS Course Mapping"
VOLUNTEER_DOCTYPE = "VMMS Volunteer"
PROFILE_DOCTYPE = "Red Profile"


def is_available() -> bool:
	"""Is a learning system installed on this site?

	Asked of `frappe.get_installed_apps()` rather than by attempting an import
	and catching the failure: an app can sit in the bench without being
	installed on *this* site, which is the case that actually bites, and a
	question answered by an exception cannot be asked at configuration time.
	"""
	return LEARNING_APP in frappe.get_installed_apps()


# --- configuration --------------------------------------------------------


def mapping_for(external_course: str):
	"""The active mapping for a course, or None if the society mapped none.

	None is the ordinary answer. Most courses a society runs are not
	certifications, and a completion the society did not map is a completion
	this app has nothing to say about.
	"""
	if not external_course:
		return None

	name = frappe.db.get_value(MAPPING_DOCTYPE, {"external_course": external_course, "is_active": 1}, "name")

	return frappe.get_cached_doc(MAPPING_DOCTYPE, name) if name else None


def mapped_courses() -> list[str]:
	"""Every course the society has mapped to a certification, active only."""
	return frappe.get_all(MAPPING_DOCTYPE, filters={"is_active": 1}, pluck="external_course")


# --- the hook -------------------------------------------------------------


def on_enrollment_update(enrollment, method=None) -> dict | None:
	"""A learner's progress changed. Award a certification if that completed it.

	Registered on the learning system's own doctype through `doc_events` in
	`hooks.py`, which is what that hook is for: reaching into another app's
	document without that app knowing we exist. The learning system is not
	modified and does not import vmmsx.

	Idempotent, and it has to be — this fires on every save of an enrollment,
	including the many saves after the course was already finished.
	"""
	if not _is_complete(enrollment):
		return None

	return record_completion(
		learner=enrollment.get(ENROLLMENT_LEARNER_FIELD),
		external_course=enrollment.get(ENROLLMENT_COURSE_FIELD),
		completed_on=_completed_on(enrollment),
	)


def _is_complete(enrollment) -> bool:
	"""Has this enrollment reached the end of its course?"""
	return flt(enrollment.get(ENROLLMENT_PROGRESS_FIELD)) >= COMPLETE_AT_PERCENT


def _completed_on(enrollment):
	"""The date the seam treats as the completion date.

	The learning system records progress but not the moment it reached the end,
	so the enrollment's own last-modified date is the best available answer and
	is the moment the hook is firing on the save that completed it. Stated
	plainly because it is an approximation, and a society reconciling a
	certificate against a training register should know which date it is
	looking at.
	"""
	return getdate(enrollment.get("modified") or today())


# --- the write ------------------------------------------------------------


def record_completion(learner: str, external_course: str, completed_on=None) -> dict | None:
	"""Turn one completed course into one held certification. Idempotent.

	Returns what it did, or None when there was nothing to do — no mapping, no
	volunteer behind the learner. Both are ordinary and neither is an error.

	This is the whole of the crossing. Everything above it is the learning
	system's vocabulary; everything it calls below is ours.
	"""
	mapping = mapping_for(external_course)

	if not mapping:
		return None

	volunteer = volunteer_for_user(learner)

	if not volunteer:
		return None

	held = certification.record(
		volunteer=volunteer,
		certification_type=mapping.certification_type,
		completion_date=getdate(completed_on or today()),
		source_mapping=mapping.name,
	)

	return {
		"volunteer": volunteer,
		"mapping": mapping.name,
		"certification": held.name,
		"certification_type": held.certification_type,
		"completion_date": held.completion_date,
		# Computed from the type's configured validity period, not from anything
		# the learning system said.
		"expiry_date": held.expiry_date,
	}


def volunteer_for_user(user: str) -> str | None:
	"""User → Red Profile → volunteer. The only identity path this seam uses.

	Two hops rather than one, deliberately. The learning system knows a login;
	core's Red Profile is the one place a login is tied to a person; the
	volunteer satellite hangs off that person. Short-circuiting to a lookup on
	the volunteer register would be this app inventing a second way to identify
	somebody.
	"""
	if not user:
		return None

	profile = frappe.db.get_value(PROFILE_DOCTYPE, {"user": user}, "name")

	if not profile:
		return None

	return frappe.db.get_value(VOLUNTEER_DOCTYPE, {"red_profile": profile}, "name")


# --- catching up ----------------------------------------------------------


def sync_volunteer(volunteer) -> dict:
	"""Award everything this volunteer has already completed. Idempotent.

	For the cases the hook cannot cover: courses finished before the society
	wrote the mapping, before this module existed, or before the person became a
	volunteer. Safe to run repeatedly — every award goes through the same
	idempotent `certification.record()`.
	"""
	from vmmsx.volunteer.services import identity

	summary = {"volunteer": volunteer.name, "read": 0, "awarded": []}

	if not is_available():
		return summary

	user = identity.user_of(volunteer)

	if not user:
		return summary

	courses = mapped_courses()

	if not courses:
		return summary

	completions = frappe.get_all(
		ENROLLMENT_DOCTYPE,
		filters={
			ENROLLMENT_LEARNER_FIELD: user,
			ENROLLMENT_COURSE_FIELD: ("in", courses),
			ENROLLMENT_PROGRESS_FIELD: (">=", COMPLETE_AT_PERCENT),
		},
		fields=[ENROLLMENT_COURSE_FIELD, "modified"],
	)

	summary["read"] = len(completions)

	for row in completions:
		awarded = record_completion(
			learner=user,
			external_course=row[ENROLLMENT_COURSE_FIELD],
			completed_on=getdate(row["modified"]),
		)

		if awarded:
			summary["awarded"].append(awarded["certification"])

	return summary
