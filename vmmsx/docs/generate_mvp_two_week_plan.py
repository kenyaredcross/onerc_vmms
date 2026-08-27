"""Generate the product-focused VMMS MVP two-week plan."""

from zipfile import ZIP_DEFLATED, ZipFile

from generate_two_week_plan import (
    CONTENT_TYPES,
    DOC_RELS,
    NUMBERING,
    OUTPUT,
    ROOT_RELS,
    W,
    bullet,
    page_break,
    para,
    run,
    styles,
    table,
)


def document() -> str:
    body: list[str] = [
        para("VMMS", bold=True, color="2E75B6", size=44, align="center", before=1500, after=120),
        para("Two-Week MVP Implementation Plan", bold=True, color="17365D", size=36, align="center", after=180),
        para("Building a Complete Volunteer and Membership Management Experience", size=24, color="5B6573", align="center", after=700),
        para("Prepared for supervisor review", bold=True, size=22, align="center", after=100),
        para("Proposed delivery window: 31 August–11 September 2026", size=21, align="center", after=80),
        para("Informed by the VMMS Product, UX, Security and Integration Review", size=19, color="68737D", align="center", after=900),
        para("Prepared by: ______________________________", size=20, align="center", after=120),
        para("Supervisor: _______________________________", size=20, align="center", after=120),
        para("Approval date: _____________________________", size=20, align="center", after=120),
        page_break(),
        para("1. Purpose of the two-week plan", style="Heading1"),
        para(
            "Over these two weeks, I will focus on making the VMMS minimum viable product feel complete and dependable for its main users. The priority is a clear journey from registering a volunteer or member, reviewing and managing their record, matching them to opportunities, organizing events and deployments, and communicating with the people involved."
        ),
        para(
            "The system already has a good technical foundation. My task in this sprint is to connect and polish the core pieces so that they work as one practical product rather than as separate features. I will keep the scope realistic: the essential daily work must be smooth first, while advanced reporting, automation and other nice-to-have features will follow in later phases."
        ),
        para("2. MVP goal", style="Heading1"),
        para("At the end of the two weeks, the MVP should allow the team to complete this full working cycle:"),
        table(
            ["Stage", "What the MVP must support"],
            [
                ["1. Register", "A volunteer or prospective member creates an account, completes the correct application and receives a clear confirmation."],
                ["2. Review", "An authorized manager finds the application, reviews the information, requests corrections where needed, and approves or rejects it."],
                ["3. Manage records", "Staff can search and open volunteer and member records, see current status, update permitted details and follow the person’s history."],
                ["4. Engage", "Approved volunteers can view opportunities and events, register interest, and receive a clear response or assignment."],
                ["5. Deploy", "Managers create a deployment, assign suitable volunteers, communicate instructions and track acceptance or completion."],
                ["6. Communicate", "Managers send relevant announcements or updates to the correct audience and can confirm what was prepared or sent."],
            ],
            [1900, 7050],
        ),
        para("3. What is included in the MVP", style="Heading1"),
        bullet("Volunteer registration, application review, correction and approval."),
        bullet("Membership registration, application review, membership status and basic record management."),
        bullet("A usable volunteer and member register with search, filters and clear profile summaries."),
        bullet("Event listing and registration or expression of interest, with a manager view of participants."),
        bullet("Volunteer opportunity listing and registration of interest."),
        bullet("Deployment creation, volunteer assignment, invitation response and status tracking."),
        bullet("Targeted in-app, email or SMS communication using the project’s existing communication connections."),
        bullet("Clear navigation, status messages, empty states and next steps across the core journeys."),
        bullet("Essential access control, privacy checks and tests for every feature completed in the sprint."),
        para("Not part of this two-week MVP", style="Heading2"),
        para(
            "The first release will not attempt to complete stipend payments, advanced analytics, bulk imports and merges, recognition awards, full learning-management integration, sophisticated membership benefits, complete localization or every possible automated reminder. These are valuable, but they should not delay a reliable registration-to-engagement workflow."
        ),
        page_break(),
        para("4. Two-week implementation schedule", style="Heading1"),
        para(
            "The schedule below assumes a ten-working-day sprint. I will share a short update at the end of each day and demonstrate the completed Week 1 foundation before moving into the engagement features in Week 2."
        ),
        table(
            ["Day", "Main focus", "Planned work", "Clear deliverable"],
            [
                ["Day 1\nMon 31 Aug", "Confirm the MVP journey", "Walk through the current system as an applicant, member, volunteer and manager. Confirm required fields, statuses, roles and success measures. Organize the work into small testable tasks.", "Agreed MVP checklist, simple user-flow map, prioritized task board and baseline issues list."],
                ["Day 2\nTue 1 Sep", "Volunteer registration", "Polish account entry and the volunteer application form. Check validation, required documents, progress messages, mobile layout and submission confirmation.", "A volunteer can complete and submit a clear, validated application from start to finish."],
                ["Day 3\nWed 2 Sep", "Volunteer review and correction", "Improve the manager review queue and application summary. Complete the request-for-information, applicant correction and resubmission loop. Confirm approve/reject actions.", "A manager can review an application, request a change and receive a corrected resubmission with history preserved."],
                ["Day 4\nThu 3 Sep", "Member registration and approval", "Polish the membership application, membership-type selection, review and approval. Make status, fees or next steps understandable without building advanced payment features.", "A prospective member can apply and an authorized officer can review and update the application to an approved membership record."],
                ["Day 5\nFri 4 Sep", "Volunteer and member records", "Improve registers, basic search and filters, profile summaries, status labels and record history. Make no-data, no-match and no-access states distinct.", "Managers can quickly find and understand volunteer and member records. Week 1 demo and feedback note."],
                ["Day 6\nMon 7 Sep", "Events", "Connect the event list to a simple user registration or interest action. Give managers a usable participant view and make event dates, places, capacity and status clear.", "A user can discover and register for an event, and a manager can view the resulting participant list."],
                ["Day 7\nTue 8 Sep", "Volunteer opportunities", "Present volunteer opportunities separately from employment vacancies. Allow eligible volunteers to express interest and managers to view and act on those expressions.", "A volunteer can register interest in an opportunity and a manager can see and process it."],
                ["Day 8\nWed 9 Sep", "Deployments and assignments", "Polish deployment creation, volunteer selection, invitations, responses and status tracking. Link the deployment back to the relevant volunteer record.", "A manager can create a deployment, assign volunteers and track acceptance through a clear workflow."],
                ["Day 9\nThu 10 Sep", "Communication and overall polish", "Test audience selection and prepare targeted in-app, email or SMS updates. Improve navigation, feedback messages, mobile presentation and accessibility in the core screens.", "A manager can prepare and confirm a scoped communication, and the main MVP journeys feel consistent and understandable."],
                ["Day 10\nFri 11 Sep", "End-to-end testing and handover", "Run the complete registration-to-engagement scenarios with each user role. Fix release-blocking issues, document setup and demonstrate the MVP to the supervisor.", "Tested MVP release candidate, demonstration, user guide, known-issues list and next-phase backlog."],
            ],
            [1200, 1800, 3450, 2500],
        ),
        page_break(),
        para("5. Weekly milestones", style="Heading1"),
        para("Week 1 — registration and records are dependable", style="Heading2"),
        para(
            "The first week is successful when a volunteer and a member can register, managers can review their applications, corrections can be made without starting again, and approved records can be found and understood easily. This provides the people and data foundation required by every other VMMS module."
        ),
        bullet("Deliverable 1: complete volunteer registration and review journey."),
        bullet("Deliverable 2: complete member registration and approval journey."),
        bullet("Deliverable 3: searchable, understandable volunteer and member management views."),
        bullet("Milestone review: live demonstration on Day 5 and agreement on any small adjustments for Week 2."),
        para("Week 2 — people can participate and managers can coordinate", style="Heading2"),
        para(
            "The second week is successful when approved users can discover events and volunteer opportunities, register their interest, receive deployment assignments and get relevant communication. Managers should be able to see the resulting participation from the appropriate management screens."
        ),
        bullet("Deliverable 4: usable event discovery, registration and participant management."),
        bullet("Deliverable 5: volunteer opportunity discovery and interest management."),
        bullet("Deliverable 6: deployment creation, assignment and response tracking."),
        bullet("Deliverable 7: targeted communication and a tested end-to-end MVP handover."),
        para("6. Definition of done", style="Heading1"),
        table(
            ["MVP area", "The feature is done when…"],
            [
                ["Volunteer registration", "A new user can complete, submit, correct and track an application without needing technical help."],
                ["Member registration", "A prospective member can apply for the right membership type and understand the current status and next step."],
                ["Record management", "An authorized manager can search, filter and open a useful profile while an unauthorized person cannot access it."],
                ["Events", "A user can register interest or attendance and the responsible manager can see the participant information."],
                ["Opportunities", "A volunteer can identify a suitable opportunity, express interest and see a meaningful status."],
                ["Deployments", "A manager can assign a volunteer, the volunteer can respond, and both sides can see the latest status."],
                ["Communication", "The intended audience and channel are clear before sending, and the system provides a useful confirmation or status."],
                ["Overall quality", "Core screens work on phone and desktop, messages explain the next action, relevant tests pass and no critical issue blocks the main journey."],
            ],
            [2200, 6750],
        ),
        page_break(),
        para("7. How I will approach the work", style="Heading1"),
        para(
            "I will complete one usable journey at a time and test it through the eyes of the person using it. For example, registration is only complete when the applicant receives a useful next step and the manager can see the submitted record. This will help me avoid polishing isolated screens that do not yet connect into a working service."
        ),
        bullet("I will keep changes small enough to review and demonstrate regularly."),
        bullet("I will test allowed and unauthorized roles while building each feature, so privacy and security are part of the MVP rather than a separate final activity."),
        bullet("I will use realistic test data but no real personal or payment information."),
        bullet("If a dependency blocks a feature, I will provide a safe simplified MVP behavior and record the fuller integration for the next phase."),
        para("8. Dependencies and support required", style="Heading1"),
        table(
            ["Dependency", "Support needed"],
            [
                ["MVP decisions", "Supervisor or product owner confirms the essential fields, statuses and approval roles on Day 1."],
                ["Test users and data", "Provide safe accounts representing applicant, volunteer, member, coordinator and membership officer."],
                ["Connected applications", "Confirm access and compatible versions for shared profiles, events/Buzz, SMS and any payment status used by the MVP."],
                ["Communication setup", "Provide test email/SMS configuration or approve a non-sending preview mode for acceptance testing."],
                ["Timely feedback", "Attend the short Day 5 review and final Day 10 demonstration so decisions do not remain open."],
            ],
            [2800, 6150],
        ),
        para("9. Main risks and how I will manage them", style="Heading1"),
        table(
            ["Risk", "Response"],
            [
                ["Trying to include too many features", "Protect the registration, records and engagement cycle first; move enhancements to the next-phase list."],
                ["Unclear ownership between VMMS and connected apps", "Choose and document one simple MVP source of truth for events, opportunities and communication."],
                ["Late discovery of broken links between modules", "Test each journey end to end as soon as it is connected, rather than waiting until Day 10."],
                ["Feedback changes the scope midway", "Accept small corrections that support the agreed MVP; record larger additions for the next phase."],
                ["A privacy or access issue is found", "Pause the affected journey, correct the access rule and retest before it is demonstrated as complete."],
            ],
            [3400, 5550],
        ),
        page_break(),
        para("10. Final handover deliverables", style="Heading1"),
        para("At the end of the two weeks, I will provide:"),
        bullet("A working MVP release candidate covering registration, records, events, opportunities, deployments and communication."),
        bullet("A live demonstration of the complete volunteer and member journeys."),
        bullet("A short user guide for applicants, volunteers, members and managers."),
        bullet("Test results for the main journeys, user roles and mobile/desktop views."),
        bullet("A configuration and deployment checklist for the test or pilot environment."),
        bullet("A known-issues list that clearly states any temporary limitations."),
        bullet("A prioritized next-phase backlog for nice-to-have features."),
        para("11. What comes after the MVP", style="Heading1"),
        para(
            "Once the core workflow is stable and users have tried it, I will use their feedback to prioritize the next release. Likely next steps include payment recovery and reconciliation, stipend approval and payout, advanced reports and exports, bulk record operations, duplicate handling, training and certification journeys, recognition, communication delivery history, localization, preferences and automated reminders."
        ),
        para(
            "This order keeps the first release useful and achievable: we first make it easy to bring people into VMMS, manage them responsibly and involve them in real activities. We can then add automation and richer management features on top of a proven workflow."
        ),
        para("12. Supervisor approval", style="Heading1"),
        para("I am requesting approval to proceed with this MVP scope and delivery sequence.", after=220),
        para("Plan approved:  Yes / No / Approved with changes", bold=True, after=240),
        para("Supervisor comments: _______________________________________________________________", after=240),
        para("________________________________________________________________________________", after=240),
        para("Supervisor signature: __________________________    Date: __________________________", after=180),
        para("Prepared-by signature: _________________________    Date: __________________________", after=180),
        para("Source: VMMS Product, UX, Security and Integration Review, 25 August 2026.", size=17, color="6B747C", before=500),
    ]

    section = (
        '<w:sectPr><w:headerReference w:type="default" r:id="rId2"/>'
        '<w:footerReference w:type="default" r:id="rId3"/><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1134" w:right="1000" w:bottom="1134" w:left="1000" w:header="550" w:footer="550"/>'
        '</w:sectPr>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<w:body>{''.join(body)}{section}</w:body></w:document>"
    )


def main() -> None:
    created = "2026-08-26T00:00:00Z"
    core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>VMMS Two-Week MVP Implementation Plan</dc:title><dc:subject>Volunteer and membership management MVP</dc:subject><dc:creator>VMMS Project Team</dc:creator><cp:lastModifiedBy>VMMS Project Team</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified></cp:coreProperties>'''
    app = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Microsoft Office Word</Application><Company>VMMS Project Team</Company></Properties>'''
    header = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr xmlns:w="{W}">{para("VMMS  |  TWO-WEEK MVP IMPLEMENTATION PLAN", bold=True, color="68737D", size=16, align="right", after=0)}</w:hdr>'''
    footer = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr xmlns:w="{W}"><w:p><w:pPr><w:jc w:val="center"/></w:pPr>{run("Supervisor Review  •  26 August 2026  •  Page ", color="68737D", size=16)}<w:r><w:rPr><w:color w:val="68737D"/><w:sz w:val="16"/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText> PAGE </w:instrText></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>'''
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", ROOT_RELS)
        archive.writestr("word/document.xml", document())
        archive.writestr("word/styles.xml", styles())
        archive.writestr("word/numbering.xml", NUMBERING)
        archive.writestr("word/header1.xml", header)
        archive.writestr("word/footer1.xml", footer)
        archive.writestr("word/_rels/document.xml.rels", DOC_RELS)
        archive.writestr("docProps/core.xml", core)
        archive.writestr("docProps/app.xml", app)
    print(OUTPUT)


if __name__ == "__main__":
    main()
