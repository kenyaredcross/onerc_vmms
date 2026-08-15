# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The closed set of task states, and the moves between them.

Modelled on `approvals/services/states.py` and for the same reason: a state
machine written down in one place can be reasoned about, and one scattered
across controllers cannot. **States are code.** Unlike an approval stage, which
is a society's configuration, these five are the same in every society, because
they describe the shape of asking somebody to do something rather than the shape
of a particular society's paperwork.

    assigned   somebody has been asked, and has not answered
    accepted   they have taken it on
    submitted  they say it is done, and a coordinator has not agreed yet
    completed  a coordinator has agreed. Terminal
    cancelled  called off before it finished. Terminal

**Why `submitted` is its own state rather than a flag on `accepted`.** The whole
point of the brief is that finishing is not the volunteer's decision alone: they
offer the work, and a coordinator signs it off. Two states make "waiting on you"
answerable by a query, which is what a coordinator's list is.

**Why there is no `clarification` state.** A question is a flag on the task
(`open_question`), not a state, and the argument is in the doctype's own field
description: a question does not stop the work or move the task backwards, so a
state for it would need a remembered way back to wherever the task was when it
was asked. A flag needs nothing remembered.

**Why `submitted` can return to `accepted`.** A coordinator who does not agree
the work is done sends it back, and the volunteer picks it up where they were.
That is the only backwards move in the table, and it is deliberate: everything
else moves forwards or stops.
"""

ASSIGNED = "assigned"
ACCEPTED = "accepted"
SUBMITTED = "submitted"
COMPLETED = "completed"
CANCELLED = "cancelled"

ALL = (ASSIGNED, ACCEPTED, SUBMITTED, COMPLETED, CANCELLED)

# Terminal states. A task in one of these is finished with, and the service
# refuses every move out of it rather than checking the pair each time.
TERMINAL = (COMPLETED, CANCELLED)

# Which states a task may still be worked on from. Named rather than derived as
# "not terminal", because a reader of a query should see the intent.
OPEN = (ASSIGNED, ACCEPTED, SUBMITTED)

# The transition table. Read as: from this state, these are the states a task
# may reach. Anything not listed is refused, including a move to the state a
# task is already in, which the service answers as "already done" rather than as
# an error.
TRANSITIONS: dict[str, tuple[str, ...]] = {
	ASSIGNED: (ACCEPTED, CANCELLED),
	ACCEPTED: (SUBMITTED, CANCELLED),
	SUBMITTED: (COMPLETED, ACCEPTED, CANCELLED),
	COMPLETED: (),
	CANCELLED: (),
}


def can_move(current: str | None, target: str) -> bool:
	"""Is this move allowed by the table above?"""
	return target in TRANSITIONS.get(current or "", ())


def is_open(status: str | None) -> bool:
	"""Is there still work to do on a task in this state?"""
	return status in OPEN
