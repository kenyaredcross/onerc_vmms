"""Generate the supervisor-ready VMMS two-week implementation plan."""

from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


OUTPUT = Path(__file__).resolve().parents[2] / "VMMS_Two_Week_Implementation_Plan.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def run(text: str, *, bold: bool = False, color: str | None = None, size: int | None = None) -> str:
    props = []
    if bold:
        props.append("<w:b/>")
    if color:
        props.append(f'<w:color w:val="{color}"/>')
    if size:
        props.append(f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>')
    rpr = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def para(
    text: str = "",
    *,
    style: str | None = None,
    bold: bool = False,
    color: str | None = None,
    size: int | None = None,
    align: str | None = None,
    before: int = 0,
    after: int = 120,
    keep: bool = False,
) -> str:
    ppr = []
    if style:
        ppr.append(f'<w:pStyle w:val="{style}"/>')
    if align:
        ppr.append(f'<w:jc w:val="{align}"/>')
    ppr.append(f'<w:spacing w:before="{before}" w:after="{after}" w:line="276" w:lineRule="auto"/>')
    if keep:
        ppr.append("<w:keepNext/>")
    return f"<w:p><w:pPr>{''.join(ppr)}</w:pPr>{run(text, bold=bold, color=color, size=size)}</w:p>"


def bullet(text: str) -> str:
    return (
        '<w:p><w:pPr><w:pStyle w:val="ListParagraph"/><w:numPr><w:ilvl w:val="0"/>'
        '<w:numId w:val="1"/></w:numPr><w:spacing w:after="80" w:line="276" w:lineRule="auto"/>'
        f"</w:pPr>{run(text)}</w:p>"
    )


def cell(text: str, *, header: bool = False, width: int = 2000) -> str:
    shade = '<w:shd w:fill="1F4E78"/>' if header else '<w:shd w:fill="F7F9FB"/>'
    color = "FFFFFF" if header else None
    content = para(text, bold=header, color=color, size=19, after=40)
    return (
        f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{shade}'
        '<w:tcMar><w:top w:w="80" w:type="dxa"/><w:left w:w="100" w:type="dxa"/>'
        '<w:bottom w:w="80" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tcMar></w:tcPr>'
        f"{content}</w:tc>"
    )


def table(headers: list[str], rows: list[list[str]], widths: list[int]) -> str:
    borders = (
        '<w:tblBorders><w:top w:val="single" w:sz="4" w:color="B8C4CE"/>'
        '<w:left w:val="single" w:sz="4" w:color="B8C4CE"/>'
        '<w:bottom w:val="single" w:sz="4" w:color="B8C4CE"/>'
        '<w:right w:val="single" w:sz="4" w:color="B8C4CE"/>'
        '<w:insideH w:val="single" w:sz="4" w:color="D7DEE4"/>'
        '<w:insideV w:val="single" w:sz="4" w:color="D7DEE4"/></w:tblBorders>'
    )
    out = [f'<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/>{borders}<w:tblLayout w:type="fixed"/></w:tblPr>']
    out.append("<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in widths) + "</w:tblGrid>")
    out.append("<w:tr><w:trPr><w:tblHeader/></w:trPr>" + "".join(cell(h, header=True, width=w) for h, w in zip(headers, widths)) + "</w:tr>")
    for row in rows:
        out.append("<w:tr>" + "".join(cell(v, width=w) for v, w in zip(row, widths)) + "</w:tr>")
    out.append("</w:tbl>")
    return "".join(out)


def page_break() -> str:
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def build_document() -> str:
    body: list[str] = []

    # Cover page
    body += [
        para("VMMS", bold=True, color="2E75B6", size=44, align="center", before=1500, after=120),
        para("Two-Week Implementation Plan", bold=True, color="17365D", size=36, align="center", after=180),
        para("Security Stabilization and Critical Journey Recovery", size=24, color="5B6573", align="center", after=700),
        para("Prepared for supervisor review", bold=True, size=22, align="center", after=100),
        para("Proposed delivery window: 31 August–11 September 2026", size=21, align="center", after=80),
        para("Based on the VMMS Product, UX, Security and Integration Review dated 25 August 2026", size=19, color="68737D", align="center", after=900),
        para("Prepared by: ______________________________", size=20, align="center", after=120),
        para("Supervisor: _______________________________", size=20, align="center", after=120),
        para("Approval date: _____________________________", size=20, align="center", after=120),
        page_break(),
    ]

    body += [
        para("1. Purpose of this plan", style="Heading1"),
        para(
            "My aim over these two weeks is to move VMMS from a strong but partly exposed foundation to a safer, testable pilot candidate. "
            "The product review found several valuable capabilities already in place, but it also identified security and user-journey issues that must be resolved before unrestricted production acceptance. I will therefore focus first on the work that protects people’s data, payment integrity and access control, then repair the two most important broken user journeys and finish with evidence-based testing and handover."
        ),
        para(
            "This is deliberately a focused stabilization sprint. I do not intend to claim that every gap in the review can be completed in ten working days. Larger capabilities—such as a full stipend payout workflow, advanced bulk operations, complete localization and long-term analytics—will be documented and sequenced for a later phase."
        ),
        para("2. Outcome at the end of the two weeks", style="Heading1"),
        para("By the end of Day 10, I expect to present a release candidate with the following outcomes:"),
        bullet("Critical payment operations are authorized against the caller, source document, gateway and expected amount."),
        bullet("Production configuration cannot silently create privileged demo users or known credentials."),
        bullet("Volunteer applications and member dossiers no longer expose personal information outside an authorized geographic or routed scope."),
        bullet("Uploaded identity, answer and task-proof files are checked for ownership, privacy and attachment before use."),
        bullet("Applicants asked for more information can securely edit and resubmit their application with history preserved."),
        bullet("Public QR/card verification retains the token and works through a tested deep link."),
        bullet("Unsafe incomplete workflows, especially stipend submission, are gated until their approval path exists."),
        bullet("Automated and role-based test evidence, a deployment checklist and a concise handover report are available for review."),
        para("3. Scope and priorities", style="Heading1"),
        table(
            ["Priority", "Included in this sprint", "Review references"],
            [
                ["P0 – Must complete", "Payment authorization; demo-seed safety; application and dossier privacy scope", "VMMS-01 to VMMS-04"],
                ["P1 – Must complete", "Secure file boundary; correction/resubmission; QR deep link; installation health", "VMMS-05 to VMMS-07, VMMS-24"],
                ["P1 – Control or complete", "Hours ownership/visibility; task proof; stipend safety gate", "VMMS-08 to VMMS-10"],
                ["P2 – If core work is stable", "Payment recovery copy and retry; focused accessibility corrections", "VMMS-12, VMMS-22"],
            ],
            [1500, 5450, 2000],
        ),
        para("Work specifically deferred", style="Heading2"),
        para(
            "The following items remain important but are too large or policy-dependent for this sprint: a complete stipend approval/payout/reconciliation module; membership benefits, termination and upgrade policy; a new volunteer-opportunity product; full event/Buzz reconciliation; advanced register bulk actions and duplicate merging; complete localization; and retention/erasure policy implementation. These will be added to the post-sprint backlog with owners, dependencies and estimates."
        ),
        page_break(),
    ]

    days = [
        ["Day 1\nMon 31 Aug", "Confirm scope and baseline", "Reproduce priority findings; map affected repositories; agree acceptance criteria; create a protected working branch and test matrix.", "Approved sprint scope, issue-to-test traceability matrix, baseline test results and risk log."],
        ["Day 2\nTue 1 Sep", "Secure payment boundary", "Add caller/source ownership checks, bind expected amount, restrict manual confirmation to the correct gateway, and add negative authorization tests.", "Payment security patch with passing legitimate and cross-user/cross-source rejection tests."],
        ["Day 3\nWed 2 Sep", "Remove unsafe setup paths", "Separate demo seeding from production society configuration; remove known-password behavior; make setup failure visible and actionable.", "Safe seed/bootstrap behavior, migration/install health check, tests and remediation note for existing environments."],
        ["Day 4\nThu 3 Sep", "Close personal-data scope gaps", "Enforce routed/geographic access for volunteer applications and require an in-scope membership before staff dossier access.", "Permission patch plus multi-role, cross-branch and no-record-oracle tests."],
        ["Day 5\nFri 4 Sep", "Create a secure file boundary", "Centralize File resolution and verify owner, privacy, MIME/type and target attachment for application answers, profile photos and task proof.", "Reusable secure-file service, updated call sites and ownership/ACL tests. Week 1 review demo."],
        ["Day 6\nMon 7 Sep", "Repair applicant correction", "Build the ownership-checked edit/save/resubmit path for applications returned for more information; preserve decision and resubmission history.", "Working applicant correction journey with backend and frontend tests."],
        ["Day 7\nTue 8 Sep", "Fix verification and workflow safety", "Correct the /verify deep link and token handling; gate stipend submission; derive the volunteer for time logging from the authenticated session and align form visibility.", "Verified QR route, stipend safety control and secure hours ownership tests."],
        ["Day 8\nWed 9 Sep", "Recovery and usability hardening", "Expose manual payment instructions and safe retry/status behavior where feasible; fix the highest-impact label/focus issues; improve error versus empty-state messaging in touched areas.", "Tested payment recovery flow and focused accessibility/usability corrections, or a documented carry-over if payment dependency blocks it."],
        ["Day 9\nThu 10 Sep", "Integrated acceptance testing", "Run automated suites and targeted browser tests across applicant, volunteer, member, coordinator and unauthorized roles; test phone viewport, slow network and keyboard use.", "Acceptance test report, defect list with severity, and release-candidate build if exit criteria are met."],
        ["Day 10\nFri 11 Sep", "Remediate, document and hand over", "Fix release-blocking defects, rerun tests, prepare deployment/rollback steps, update backlog and demonstrate the completed journeys to the supervisor.", "Final code/release candidate, test evidence, deployment checklist, rollback plan, deferred backlog and supervisor demo."],
    ]
    body += [
        para("4. Ten-working-day implementation schedule", style="Heading1"),
        para(
            "The dates below assume the sprint starts on Monday, 31 August 2026. If approval comes later, the same Day 1–Day 10 sequence can move without changing its dependencies. I will give a short progress update at the end of each day and raise a blocker as soon as it threatens a committed deliverable."
        ),
        table(["Day", "Focus", "Main activities", "End-of-day deliverable"], days, [1250, 1750, 3400, 2550]),
        page_break(),
        para("5. Week-by-week milestones", style="Heading1"),
        para("Week 1 milestone — the critical security foundation is closed", style="Heading2"),
        para(
            "By Friday of Week 1, I will demonstrate that the highest-risk payment, setup, privacy and file-access findings are either fixed and tested or clearly escalated with evidence. No user-facing feature work will be treated as complete if its server-side authorization tests are missing."
        ),
        bullet("Milestone deliverable: reviewed patches for VMMS-01 through VMMS-04 and VMMS-06."),
        bullet("Evidence: automated negative tests, role/scope matrix, baseline-versus-current test summary and remediation note."),
        bullet("Decision gate: proceed to pilot-journey hardening only if there is no open Critical security defect."),
        para("Week 2 milestone — the pilot journeys are recoverable and release evidence is ready", style="Heading2"),
        para(
            "By Friday of Week 2, I will demonstrate the correction/resubmission and QR verification journeys, the controls placed around incomplete workflows, and the acceptance evidence. The supervisor will receive a concise statement of what is safe to pilot, what is still restricted and what comes next."
        ),
        bullet("Milestone deliverable: applicant correction, QR verification, workflow safety controls and targeted recovery/accessibility improvements."),
        bullet("Evidence: end-to-end results, screenshots where useful, regression report, deployment checklist and rollback steps."),
        bullet("Decision gate: recommend pilot only when every exit criterion below is met; otherwise provide a no-go recommendation with remaining blockers."),
        para("6. Definition of done and acceptance criteria", style="Heading1"),
        table(
            ["Area", "Acceptance criterion"],
            [
                ["Security", "Unauthorized cross-user, cross-branch and cross-source requests fail without disclosing whether a protected record exists."],
                ["Payments", "The confirmed amount, source, owner and gateway are bound and verified; manual confirmation cannot be used for other gateway types."],
                ["Privacy", "Staff can only open applications and member dossiers allowed by routed authority and current geographic assignment."],
                ["Files", "A private file cannot be adopted by URL alone; owner, privacy, MIME/type and attachment are validated atomically."],
                ["Applicant journey", "A returned application can be edited and resubmitted once per valid state transition, while the audit history remains intact."],
                ["Verification", "Opening a generated QR URL directly displays the intended minimal public verification result and keeps the token."],
                ["Quality", "New tests pass, existing relevant suites do not regress, and no open Critical or High defect affects the planned pilot paths."],
                ["Operations", "Deployment, rollback, configuration health and deferred restrictions are documented and reviewed."],
            ],
            [2200, 6750],
        ),
        page_break(),
    ]

    body += [
        para("7. Working approach and reporting", style="Heading1"),
        para(
            "I will work in small, reviewable changes rather than one large final merge. Each change will begin with a failing or negative test that represents the risk, followed by the implementation and a regression check. Where a fix spans VMMS and another connected application, I will keep the contract change explicit and record the required version or deployment order."
        ),
        bullet("Daily: brief update covering completed work, test evidence, blockers and the next day’s target."),
        bullet("End of Week 1: security checkpoint and demonstration, with a go/no-go decision for Week 2’s pilot hardening."),
        bullet("End of Week 2: supervisor demonstration, release recommendation and handover pack."),
        bullet("Change control: any newly discovered Critical defect takes priority; a lower-priority Day 8 item may move to the backlog to protect the security and acceptance commitments."),
        para("8. Dependencies and support needed", style="Heading1"),
        table(
            ["Dependency", "Why it is needed", "Required action"],
            [
                ["Access to connected repositories", "Payment and shared geographic controls sit partly in onerc_payments and onerc_core.", "Confirm compatible branches and reviewers by Day 1."],
                ["Safe test site and role accounts", "Authorization must be tested as applicant, volunteer, member, coordinator and out-of-scope staff.", "Provide non-production accounts/data; no real PII."],
                ["National Society policy decisions", "Payment confirmation, hours approval, stipend gating and geographic authority need an agreed policy.", "Nominate a decision owner and answer blocking questions within one working day."],
                ["Reviewer availability", "Cross-app security changes need timely review to avoid a late integration queue.", "Book checkpoints for Day 5 and Day 10."],
                ["Provider/test configuration", "Payment status and QR flows need representative configuration without live financial impact.", "Provide sandbox gateway/configuration where available."],
            ],
            [2200, 3950, 2800],
        ),
        para("9. Risks and mitigations", style="Heading1"),
        table(
            ["Risk", "Impact", "Mitigation"],
            [
                ["Cross-repository changes take longer than expected", "Payment work could delay later tasks.", "Agree contracts on Day 1, keep patches small and prioritize authorization tests before UI polish."],
                ["Live behavior differs from the static review", "A finding may be broader or narrower than expected.", "Reproduce first, record evidence and update acceptance criteria before implementation."],
                ["Policy is unclear", "Hours, stipends or geographic roles could be implemented incorrectly.", "Use a safe deny/gate default and escalate the policy decision instead of guessing."],
                ["Regression in existing journeys", "A security fix may block legitimate users.", "Test both denial and allowed paths for every affected role and run relevant existing suites."],
                ["Two-week scope pressure", "Quality may be traded for too many features.", "Protect P0/P1 deliverables; move Day 8 enhancements first and document them transparently."],
            ],
            [2650, 2800, 3500],
        ),
        page_break(),
        para("10. Final handover deliverables", style="Heading1"),
        para("At the close of the sprint, I will hand over one package containing:"),
        bullet("The reviewed implementation changes and the exact connected-app versions or branches required."),
        bullet("A traceability matrix linking each included review finding to its change, test and result."),
        bullet("Automated test output and a targeted manual acceptance report across the agreed personas and devices."),
        bullet("A deployment checklist, configuration checks, data-remediation notes and tested rollback steps."),
        bullet("A release recommendation: pilot-ready, conditionally ready, or not ready, supported by open-defect evidence."),
        bullet("A prioritized post-sprint backlog for deferred product, governance, integration and accessibility work."),
        para("11. Supervisor approval", style="Heading1"),
        para(
            "I am asking for approval to proceed with this order of work and for timely access to the connected repositories, test roles and policy owners listed above. I will treat security and privacy acceptance as non-negotiable and will report honestly if the system does not meet the pilot exit criteria within the two-week window."
        ),
        para("Plan approved:  Yes / No / Approved with changes", bold=True, after=240),
        para("Supervisor comments: _______________________________________________________________", after=240),
        para("________________________________________________________________________________", after=240),
        para("Supervisor signature: __________________________    Date: __________________________", after=180),
        para("Prepared-by signature: _________________________    Date: __________________________", after=180),
        para("Source: VMMS Product, UX, Security and Integration Review, 25 August 2026.", size=17, color="6B747C", before=500),
    ]

    sect = (
        '<w:sectPr><w:headerReference w:type="default" r:id="rId2"/>'
        '<w:footerReference w:type="default" r:id="rId3"/><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1134" w:right="1000" w:bottom="1134" w:left="1000" w:header="550" w:footer="550"/>'
        '</w:sectPr>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<w:body>{''.join(body)}{sect}</w:body></w:document>"
    )


def styles() -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{W}">
 <w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:sz w:val="21"/><w:szCs w:val="21"/><w:color w:val="263238"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
 <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
 <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="260" w:after="120"/></w:pPr><w:rPr><w:rFonts w:ascii="Aptos Display" w:hAnsi="Aptos Display"/><w:b/><w:color w:val="1F4E78"/><w:sz w:val="30"/></w:rPr></w:style>
 <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="220" w:after="90"/></w:pPr><w:rPr><w:b/><w:color w:val="2E75B6"/><w:sz w:val="24"/></w:rPr></w:style>
 <w:style w:type="paragraph" w:styleId="ListParagraph"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="420" w:hanging="220"/></w:pPr></w:style>
</w:styles>'''


CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="xml" ContentType="application/xml"/>
 <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
 <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
 <Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
 <Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>
 <Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
 <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
 <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''

ROOT_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
 <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
 <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''

DOC_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
 <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>
 <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
 <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
</Relationships>'''

NUMBERING = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="{W}"><w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="singleLevel"/><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/><w:pPr><w:tabs><w:tab w:val="num" w:pos="420"/></w:tabs><w:ind w:left="420" w:hanging="220"/></w:pPr><w:rPr><w:rFonts w:ascii="Symbol" w:hAnsi="Symbol"/></w:rPr></w:lvl></w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>'''


def main() -> None:
    created = date(2026, 8, 26).isoformat() + "T00:00:00Z"
    core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>VMMS Two-Week Implementation Plan</dc:title><dc:subject>Security stabilization and critical journey recovery</dc:subject><dc:creator>VMMS Project Team</dc:creator><cp:lastModifiedBy>VMMS Project Team</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified></cp:coreProperties>'''
    app = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Microsoft Office Word</Application><Company>VMMS Project Team</Company></Properties>'''
    header = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr xmlns:w="{W}">{para("VMMS  |  TWO-WEEK IMPLEMENTATION PLAN", bold=True, color="68737D", size=16, align="right", after=0)}</w:hdr>'''
    footer = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr xmlns:w="{W}"><w:p><w:pPr><w:jc w:val="center"/></w:pPr>{run("Supervisor Review  •  26 August 2026  •  Page ", color="68737D", size=16)}<w:r><w:rPr><w:color w:val="68737D"/><w:sz w:val="16"/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText> PAGE </w:instrText></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>'''
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", ROOT_RELS)
        z.writestr("word/document.xml", build_document())
        z.writestr("word/styles.xml", styles())
        z.writestr("word/numbering.xml", NUMBERING)
        z.writestr("word/header1.xml", header)
        z.writestr("word/footer1.xml", footer)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS)
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)
    print(OUTPUT)


if __name__ == "__main__":
    main()
