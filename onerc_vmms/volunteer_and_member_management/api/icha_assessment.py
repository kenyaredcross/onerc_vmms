import json
import random

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import now_datetime


def _require_research_assistant():
	"""
	Raise PermissionError if the calling user is not a Research Assistant.
	Returns the user email on success.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)

	profession = frappe.db.get_value("User", user, "profession")
	if profession != "Research Assistant":
		frappe.throw(
			_("This assessment is only available to Research Assistants."),
			frappe.PermissionError,
		)

	return user


def _get_existing_attempt(user: str):
	"""Return a Completed ICHA Assessment Attempt for this user, or None."""
	return frappe.db.get_value(
		"ICHA Assessment Attempt",
		{"user": user, "status": "Completed"},
		["name", "score", "total_questions", "percentage", "passed", "submitted_on"],
		as_dict=True,
	)


def _build_attempt_result(attempt_name: str):
	"""Load a completed attempt and return a rich dict for the frontend."""
	attempt = frappe.get_doc("ICHA Assessment Attempt", attempt_name)

	# Parse stored shuffle metadata (order + shuffled options)
	try:
		stored = json.loads(attempt.shuffled_questions or "{}")
		if isinstance(stored, list):
			# Legacy: old format was just a list of names
			shuffled_order = stored
			stored_options = {}
		else:
			shuffled_order = stored.get("order", [])
			stored_options = stored.get("options", {})
	except (ValueError, TypeError):
		shuffled_order = []
		stored_options = {}

	# Build answer list using stored shuffled options where available
	answer_map = {}
	for row in attempt.answers:
		q = frappe.db.get_value(
			"ICHA Question",
			row.question,
			["question", "course", "option_a", "option_b", "option_c", "option_d"],
			as_dict=True,
		)
		# Use the shuffled options that were shown to the user
		opts = stored_options.get(row.question)
		if opts:
			options = {
				"A": opts.get("option_a", ""),
				"B": opts.get("option_b", ""),
				"C": opts.get("option_c", ""),
				"D": opts.get("option_d", ""),
			}
		elif q:
			options = {"A": q.option_a, "B": q.option_b, "C": q.option_c, "D": q.option_d}
		else:
			options = {"A": "", "B": "", "C": "", "D": ""}

		answer_map[row.question] = {
			"question": row.question,
			"question_text": q.question if q else "",
			"course": q.course if q else "",
			"options": options,
			"selected_answer": row.selected_answer,
			"correct_answer": row.correct_answer,
			"is_correct": bool(row.is_correct),
		}

	# Return in the shuffled order the user saw
	if shuffled_order:
		answers = [answer_map[n] for n in shuffled_order if n in answer_map]
	else:
		answers = list(answer_map.values())

	return {
		"already_attempted": True,
		"score": attempt.score,
		"total_questions": attempt.total_questions,
		"percentage": attempt.percentage,
		"passed": bool(attempt.passed),
		"submitted_on": str(attempt.submitted_on),
		"answers": answers,
	}


@frappe.whitelist()
def check_eligibility():
	"""
	Returns eligibility status for the current user.
	Does NOT throw — returns a dict so the Vue page can branch.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		return {"eligible": False, "reason": "not_logged_in"}

	profession = frappe.db.get_value("User", user, "profession")
	if profession != "Research Assistant":
		return {"eligible": False, "reason": "wrong_profession"}

	existing = _get_existing_attempt(user)
	if existing:
		return {"eligible": False, "reason": "already_attempted", "attempt": existing}

	return {"eligible": True}


def _shuffle_options(q):
	"""
	Shuffle the A/B/C/D options of a question randomly.
	Returns (shuffled_question_dict, new_correct_letter, option_map).
	option_map: {original_letter: new_letter} — stored so scoring can reverse-lookup.
	"""
	original_correct = frappe.db.get_value("ICHA Question", q["name"], "correct_answer")
	letters = ["A", "B", "C", "D"]
	original_options = {
		"A": q["option_a"],
		"B": q["option_b"],
		"C": q["option_c"],
		"D": q["option_d"],
	}

	shuffled_letters = letters[:]
	random.shuffle(shuffled_letters)

	# shuffled_letters[i] is now in position letters[i]
	# e.g. if shuffled_letters = ["C","A","D","B"], then new slot A gets original C, etc.
	new_options = {}
	option_map = {}  # original → new position
	for new_pos, orig_letter in zip(letters, shuffled_letters):
		new_options[new_pos] = original_options[orig_letter]
		option_map[orig_letter] = new_pos

	new_correct = option_map[original_correct]

	return {
		"name": q["name"],
		"course": q["course"],
		"question": q["question"],
		"option_a": new_options["A"],
		"option_b": new_options["B"],
		"option_c": new_options["C"],
		"option_d": new_options["D"],
	}, new_correct, option_map


@frappe.whitelist()
@rate_limit(limit=10, seconds=60)
def get_assessment():
	"""
	Returns assessment questions in a random order unique to this session,
	with options shuffled per question.
	OR returns the completed attempt result if this user has already taken it.
	"""
	user = _require_research_assistant()

	existing = _get_existing_attempt(user)
	if existing:
		return _build_attempt_result(existing.name)

	questions = frappe.get_all(
		"ICHA Question",
		fields=["name", "course", "question", "option_a", "option_b", "option_c", "option_d"],
		order_by="course asc",
	)

	if not questions:
		frappe.throw(_("No assessment questions are configured yet. Please contact an administrator."))

	random.shuffle(questions)

	# Shuffle options per question and store the mapping so scoring is accurate
	served = []
	shuffle_meta = {}  # {question_name: {new_correct, option_map}}
	for q in questions:
		q_dict = {k: q[k] for k in ["name", "course", "question", "option_a", "option_b", "option_c", "option_d"]}
		shuffled_q, new_correct, option_map = _shuffle_options(q_dict)
		served.append(shuffled_q)
		shuffle_meta[q["name"]] = {"new_correct": new_correct, "option_map": option_map}

	shuffle_meta_json = json.dumps(shuffle_meta)

	# Primary store: Redis cache (fast path for submit)
	frappe.cache().set_value(
		f"icha_shuffle_{user}",
		shuffle_meta_json,
		expires_in_sec=60 * 60 * 8,  # 8 hours
	)

	# Secondary store: DB (survives Redis restart / long sessions)
	# Upsert a "Pending" attempt row that submit_assessment will finalise
	existing_pending = frappe.db.get_value(
		"ICHA Assessment Attempt", {"user": user, "status": "Pending"}, "name"
	)
	if existing_pending:
		frappe.db.set_value("ICHA Assessment Attempt", existing_pending, "shuffled_questions", shuffle_meta_json)
	else:
		pending = frappe.get_doc({
			"doctype": "ICHA Assessment Attempt",
			"user": user,
			"submitted_on": now_datetime(),
			"status": "Pending",
			"total_questions": len(served),
			"score": 0,
			"percentage": 0,
			"passed": 0,
			"shuffled_questions": shuffle_meta_json,
		})
		pending.insert(ignore_permissions=True)
		frappe.db.commit()

	return {
		"already_attempted": False,
		"questions": served,
		"total": len(served),
		"pass_percentage": 70,
	}


@frappe.whitelist()
@rate_limit(limit=5, seconds=60 * 5)
def submit_assessment(answers):
	"""
	Score and persist the assessment attempt.

	`answers` is a JSON string or dict mapping ICHA Question name -> selected letter (A/B/C/D).
	Returns scored result dict.
	"""
	user = _require_research_assistant()

	# One-attempt guard
	existing = _get_existing_attempt(user)
	if existing:
		return _build_attempt_result(existing.name)

	# Parse answers
	if isinstance(answers, str):
		try:
			answers = json.loads(answers)
		except (ValueError, TypeError):
			frappe.throw(_("Invalid answers format."))

	if not isinstance(answers, dict) or not answers:
		frappe.throw(_("No answers submitted."))

	# Load all questions
	question_names = list(answers.keys())
	question_records = frappe.get_all(
		"ICHA Question",
		filters={"name": ["in", question_names]},
		fields=["name", "course", "question", "option_a", "option_b", "option_c", "option_d", "correct_answer"],
	)
	question_map = {q.name: q for q in question_records}

	# Load shuffle metadata — try Redis first, fall back to Pending attempt in DB
	shuffle_meta_raw = frappe.cache().get_value(f"icha_shuffle_{user}")
	if not shuffle_meta_raw:
		pending_name = frappe.db.get_value(
			"ICHA Assessment Attempt", {"user": user, "status": "Pending"}, "name"
		)
		if pending_name:
			shuffle_meta_raw = frappe.db.get_value(
				"ICHA Assessment Attempt", pending_name, "shuffled_questions"
			)
	shuffle_meta = json.loads(shuffle_meta_raw) if shuffle_meta_raw else {}

	# Build child rows and score
	answer_rows = []
	correct_count = 0
	for q_name, selected in answers.items():
		q = question_map.get(q_name)
		if not q:
			continue
		selected_upper = (selected or "").upper()

		meta = shuffle_meta.get(q_name, {})
		if meta.get("new_correct"):
			# Cache hit — use the remapped correct letter directly
			correct_in_shuffled_position = meta["new_correct"]
		else:
			# Cache miss (e.g. Redis expired) — derive correct answer by matching
			# the original correct option text against the submitted options.
			# The frontend echoes back the letter it showed, so we need the text of
			# the original correct answer and find which letter it ended up in.
			# Since we don't have the shuffled options here without cache, fall back
			# to scoring against the original DB letter. This may rarely mismatch if
			# cache expired, but is better than silently wronging every answer.
			correct_in_shuffled_position = q.correct_answer

		is_correct = selected_upper == correct_in_shuffled_position
		if is_correct:
			correct_count += 1
		answer_rows.append(
			{
				"doctype": "ICHA Attempt Answer",
				"question": q_name,
				"course": q.course,
				"selected_answer": selected_upper,
				"correct_answer": correct_in_shuffled_position,
				"is_correct": 1 if is_correct else 0,
			}
		)

	total = len(answer_rows)
	percentage = round((correct_count / total) * 100, 2) if total else 0.0
	passed = percentage >= 70.0

	# Store question order + per-question shuffled options for review reconstruction
	shuffled_order = list(answers.keys())
	shuffled_options_store = {}
	for q_name in shuffled_order:
		q = question_map.get(q_name)
		if q:
			shuffled_options_store[q_name] = {
				"option_a": q.option_a,
				"option_b": q.option_b,
				"option_c": q.option_c,
				"option_d": q.option_d,
			}
		# Override with the shuffled versions from cache if available
		meta = shuffle_meta.get(q_name, {})
		if meta.get("option_map") and q:
			inv = {v: k for k, v in meta["option_map"].items()}  # new_pos → orig_letter
			orig = {"A": q.option_a, "B": q.option_b, "C": q.option_c, "D": q.option_d}
			shuffled_options_store[q_name] = {
				f"option_{new.lower()}": orig[inv[new]] for new in ["A", "B", "C", "D"]
			}

	stored_json = json.dumps({"order": shuffled_order, "options": shuffled_options_store})
	pending_name = frappe.db.get_value(
		"ICHA Assessment Attempt", {"user": user, "status": "Pending"}, "name"
	)

	try:
		frappe.db.begin()
		if pending_name:
			# Finalise the existing Pending record
			attempt = frappe.get_doc("ICHA Assessment Attempt", pending_name)
			attempt.submitted_on = now_datetime()
			attempt.status = "Completed"
			attempt.total_questions = total
			attempt.score = correct_count
			attempt.percentage = percentage
			attempt.passed = 1 if passed else 0
			attempt.shuffled_questions = stored_json
			attempt.answers = []
			for r in answer_rows:
				attempt.append("answers", r)
			attempt.save(ignore_permissions=True)
		else:
			attempt = frappe.get_doc(
				{
					"doctype": "ICHA Assessment Attempt",
					"user": user,
					"submitted_on": now_datetime(),
					"status": "Completed",
					"total_questions": total,
					"score": correct_count,
					"percentage": percentage,
					"passed": 1 if passed else 0,
					"shuffled_questions": stored_json,
					"answers": answer_rows,
				}
			)
			attempt.insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error(frappe.get_traceback(), "ICHA Assessment Submission Error")
		frappe.throw(_("Could not save your assessment. Please try again."))

	return {
		"already_attempted": True,
		"score": correct_count,
		"total_questions": total,
		"percentage": percentage,
		"passed": passed,
		"submitted_on": str(now_datetime()),
		"answers": [
			{
				"question": r["question"],
				"question_text": question_map[r["question"]].question,
				"course": r["course"],
				"options": {
					"A": shuffled_options_store.get(r["question"], {}).get("option_a", question_map[r["question"]].option_a),
					"B": shuffled_options_store.get(r["question"], {}).get("option_b", question_map[r["question"]].option_b),
					"C": shuffled_options_store.get(r["question"], {}).get("option_c", question_map[r["question"]].option_c),
					"D": shuffled_options_store.get(r["question"], {}).get("option_d", question_map[r["question"]].option_d),
				},
				"selected_answer": r["selected_answer"],
				"correct_answer": r["correct_answer"],
				"is_correct": bool(r["is_correct"]),
			}
			for r in answer_rows
		],
	}
