# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The declarations an applicant is asked to agree to, per registration.

**Shipped as a starting point, owned by the society from the moment they land.**
Every national society operates under its own data-protection law and its own
statutes, and the wording below is deliberately the plainest honest version of
each undertaking rather than anybody's model clause. A society's legal officer
is expected to rewrite all four; `declarations.install` never edits a record
that already exists, so a rewrite survives every deploy afterwards.

What the app *does* insist on is the shape: four separate declarations, agreed
to separately, each stored with its own version and its own text.

**Why four and not one tick.** Bundling them is the thing this is built to
prevent. Consenting to have your data processed so a society can consider your
application is a different act from agreeing to be contacted about other things,
which is a different act again from letting the society use your photograph in
its newsletter — and a person who wants the first two and not the third has no
way to say so if all three are one box. The accuracy declaration is different in
kind from all of them: it is a statement the applicant makes, not a permission
they give.

**Written in the second person, plainly, and short enough to be read.** A
declaration nobody reads is not consent, whatever the checkbox says. Each is a
few sentences, says what will happen rather than what is permitted to happen,
and names what the applicant can do about it later.

**Society-neutral.** No country, no law, no society name and no retention period
appears below, for the same reason none appears in the shipped email templates
or content blocks — the app does not know which society installed it. Where a
society must fill something in, the text says so in the plainest terms rather
than guessing.

**Each entry names the doctype it applies to.** `VMMS Declaration.applies_to` has
always been a Link to DocType and `declarations.py` has always been generic; this
list was the one place that assumed a volunteer application, and the
existing-membership proof is the second caller. A declaration is a fact about one
registration, and the two registrations ask for materially different things: a
volunteer is giving permissions, and somebody proving an existing membership is
making a statement about evidence they have uploaded.
"""

APPLICATION_DOCTYPE = "VMMS Volunteer Application"
MEMBERSHIP_DOCTYPE = "VMMS Membership"

# Opaque, stable keys. A society may rewrite every word of every title and body
# below; nothing looks a declaration up by what it says.
PRIVACY = "vmms-volunteer-privacy"
CONTACT = "vmms-volunteer-contact"
PERSONAL_DATA = "vmms-volunteer-personal-data"
ACCURACY = "vmms-volunteer-accuracy"
MEMBERSHIP_PROOF = "vmms-membership-proof-accuracy"

# The version every shipped declaration starts at. A society that edits a body
# must move this — `VMMS Declaration` refuses the save otherwise — so the number
# on an acceptance always identifies the wording that was accepted.
INITIAL_VERSION = "1"

DECLARATIONS = (
	{
		"declaration_key": PRIVACY,
		"applies_to": APPLICATION_DOCTYPE,
		"title": "How we will use your information",
		"sequence": 10,
		"body": (
			"<p>To consider your application we need to record what you have told us about"
			" yourself: your name, your contact details, your date of birth, the identification"
			" you have given us, and your answers to the questions on this form.</p>"
			"<p>Your application is read by the people at this Society responsible for deciding"
			" it. If you are accepted, this information becomes your volunteer record and is"
			" used to place you, contact you and keep you safe while you are volunteering. If"
			" you are not accepted, we keep the application so we have a record of the decision"
			" and why it was made.</p>"
			"<p>You can ask us at any time to show you what we hold about you, to correct"
			" anything that is wrong, and to explain why we still hold it.</p>"
		),
	},
	{
		"declaration_key": CONTACT,
		"applies_to": APPLICATION_DOCTYPE,
		"title": "Permission to contact you",
		"sequence": 20,
		"body": (
			"<p>You agree that we may contact you about this application, and about volunteering"
			" with us, using the phone number and email address you have given.</p>"
			"<p>This covers what you need to hear from us: whether your application has been"
			" accepted, what we need from you next, and — once you are volunteering —"
			" invitations, tasks, changes to arrangements and anything urgent.</p>"
			"<p>You can tell us to stop contacting you about anything else at any time, and we"
			" will still send you the messages you need in order to volunteer safely.</p>"
		),
	},
	{
		"declaration_key": PERSONAL_DATA,
		"applies_to": APPLICATION_DOCTYPE,
		"title": "Use of your personal and biographical details",
		"sequence": 30,
		"body": (
			"<p>You agree that we may use your personal and biographical details — including your"
			" photograph, the skills and languages you have declared, and your record of"
			" volunteering with us — for the ordinary running of our volunteering programme.</p>"
			"<p>That means, for example, printing your volunteer identity card, matching you to"
			" work that suits what you can do, introducing you to the team you are deployed with,"
			" and reporting on our volunteering to those we are accountable to.</p>"
			"<p>This is not permission to use your details in public campaigns, fundraising or"
			" publicity. If we want to do that, we will ask you separately.</p>"
		),
	},
	{
		"declaration_key": ACCURACY,
		"applies_to": APPLICATION_DOCTYPE,
		"title": "Your declaration",
		"sequence": 40,
		"body": (
			"<p>You declare that everything you have entered on this form is true and complete to"
			" the best of your knowledge, and that the identification and any documents you have"
			" uploaded are your own.</p>"
			"<p>If something you have told us changes, you will let us know.</p>"
			"<p>You understand that if we find out this declaration was not true, your"
			" application may be refused, or your volunteering with us may be ended.</p>"
		),
	},
	{
		# Somebody proving a membership they already hold is not asking for
		# permissions and is not joining anything — they are asserting that a
		# document is theirs and that the dates on it are right. That is one
		# statement, so it is one declaration rather than a copy of the volunteer
		# set, and it names the evidence explicitly because the evidence is the
		# whole of what an approver is being asked to accept.
		"declaration_key": MEMBERSHIP_PROOF,
		"applies_to": MEMBERSHIP_DOCTYPE,
		"title": "Your declaration about this membership",
		"sequence": 10,
		"body": (
			"<p>You declare that the membership details you have given here are true and complete"
			" to the best of your knowledge, and that the document you have uploaded is genuine"
			" and belongs to you.</p>"
			"<p>The dates you have given are what you are telling us. Somebody at this Society"
			" will check them against the document you uploaded, and it is the dates they confirm"
			" that decide when your membership runs from and to.</p>"
			"<p>You understand that if we find out this declaration was not true, your membership"
			" may be refused or ended.</p>"
		),
	},
)
