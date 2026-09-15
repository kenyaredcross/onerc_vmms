"""
Patch: seed_icha_questions
Inserts all 52 ICHA assessment questions from 4 courses.
Idempotent — skips questions that already exist.
"""

import frappe

QUESTIONS = [
	# ── DiDRR (8 questions) ───────────────────────────────────────────────────
	{
		"course": "DiDRR",
		"question": (
			"During a severe flood response, emergency team observed that deaf community members "
			"failed to evacuate early. A medical officer claims this was due to the residents' "
			"sensory impairment. How should a DiDRR advisor reframe this situation under the "
			"Human Rights Model of Disability?"
		),
		"option_a": (
			"The primary source of risk was the biological severity of the hearing impairment "
			"combined with sudden flood waters."
		),
		"option_b": (
			"The primary source of disability was an environmental and institutional barrier: "
			"broadcasting early warnings exclusively via audio sirens without visual alerts."
		),
		"option_c": (
			"The primary source of handicap was the failure of the local community to assign "
			"dedicated personal caregivers to deaf households."
		),
		"option_d": (
			"The primary source of risk was the lack of specialized medical diagnostic facilities "
			"at the local emergency reception center."
		),
	},
	{
		"course": "DiDRR",
		"question": (
			"A humanitarian organization is establishing an emergency cash-transfer program following "
			"an earthquake. How should the team structure the program to correctly reflect both tracks "
			"of the Twin-Track Approach?"
		),
		"option_a": (
			"Track 1: Provide cash exclusively to medical clinics; Track 2: Provide physical food "
			"packages directly to all households with disabled family members."
		),
		"option_b": (
			"Track 1: Ensure standard distribution sites have ramps and priority lines; Track 2: "
			"Provide additional top-up funds or home delivery for individuals needing replacement "
			"mobility aids."
		),
		"option_c": (
			"Track 1: Partner with national government banks; Track 2: Delegate all disaster "
			"management execution to local non-governmental organizations."
		),
		"option_d": (
			"Track 1: Conduct census surveys using general demographics; Track 2: Limit financial "
			"aid distribution strictly to elderly individuals with chronic illnesses."
		),
	},
	{
		"course": "DiDRR",
		"question": (
			"A regional risk reduction committee collects Sex, Age, and Disability Disaggregated "
			"Data (SADDD) during a drought crisis. How should program managers use this data to "
			"ensure an equitable response?"
		),
		"option_a": (
			"Use the data to justify reducing the overall humanitarian relief budget by targeting "
			"only one demographic group."
		),
		"option_b": (
			"Analyze the intersectional gaps to design accessible water delivery points and targeted "
			"protection mechanisms for high-risk sub-groups."
		),
		"option_c": (
			"Store the disaggregated data exclusively as an administrative archive required for "
			"international academic publishing."
		),
		"option_d": (
			"Restrict emergency cash distributions solely to registered heads of households "
			"regardless of individual functional requirements."
		),
	},
	{
		"course": "DiDRR",
		"question": (
			"A coastal municipality is updating its tsunami early warning protocol. To comply with "
			"the Sendai Framework for Disaster Risk Reduction priorities, which EWS strategy should "
			"the team adopt?"
		),
		"option_a": (
			"Install high-decibel audio sirens across the entire coastline as the sole high-speed "
			"broadcast channel."
		),
		"option_b": (
			"Deploy a multi-modal alert system combining audio sirens, SMS text alerts, flashing "
			"beacons, and trained local community wardens using door-to-door visual signals."
		),
		"option_c": (
			"Send text messages written in complex technical meteorological terminology exclusively "
			"to municipal council leaders."
		),
		"option_d": (
			"Delay broadcasting public warning alerts until all primary evacuation highways are "
			"completely cleared of civilian traffic."
		),
	},
	{
		"course": "DiDRR",
		"question": (
			"Following a cyclone, a shelter cluster is rebuilding a primary community reception "
			"center. Applying the principles of Universal Design and UN CRPD Article 11, how should "
			"the infrastructure be designed?"
		),
		"option_a": (
			"Construct a standard high-step building for the general public and erect a separate, "
			"isolated structure nearby exclusively for people with mobility impairments."
		),
		"option_b": (
			"Build wide entrances, gentle slope ramps, multi-sensory signage, and accessible "
			"sanitation facilities that are usable by all community members from the outset."
		),
		"option_c": (
			"Rebuild the structure using its original pre-disaster blueprints to minimize immediate "
			"construction material costs."
		),
		"option_d": (
			"Install heavy manual security doors and high-threshold steps to protect emergency "
			"supplies against potential theft."
		),
	},
	{
		"course": "DiDRR",
		"question": (
			"An international agency is drafting a municipal disaster preparedness plan. Some local "
			"officials suggest saving time by drafting the plan internally and asking a local OPD to "
			"sign off on it afterward. Why is this approach ethically and operationally flawed?"
		),
		"option_a": (
			"OPDs are legally required to fund 50% of municipal shelter construction costs and must "
			"be present for budget votes."
		),
		"option_b": (
			"It violates 'Nothing About Us Without Us' by treating OPDs as passive rubber-stamps "
			"rather than active experts in identifying barriers and co-designing solutions."
		),
		"option_c": (
			"International law requires that OPDs take complete operational leadership of all "
			"search-and-rescue military units during emergencies."
		),
		"option_d": (
			"OPDs only possess technical knowledge regarding clinical medical care and cannot "
			"contribute to general community risk mapping."
		),
	},
	{
		"course": "DiDRR",
		"question": (
			"During a sudden displacement crisis, an assessment reveals that women and girls with "
			"disabilities face heightened risks of Gender-Based Violence (GBV) in collective "
			"shelters. Which immediate structural modification should shelter managers implement?"
		),
		"option_a": (
			"Require women with disabilities to remain inside personal tents at all times during "
			"night hours."
		),
		"option_b": (
			"Install accessible, well-lit, lockable sanitation facilities located close to main "
			"living areas with clear protection monitoring mechanisms."
		),
		"option_c": (
			"Separate all family members with disabilities from their relatives and house them in "
			"a central medical facility."
		),
		"option_d": (
			"Replace community-based protection committees with armed security personnel inside "
			"all private sleeping spaces."
		),
	},
	{
		"course": "DiDRR",
		"question": (
			"A district emergency office is organizing a flood evacuation simulation drill. How "
			"should persons with diverse impairments be integrated into the exercise?"
		),
		"option_a": (
			"Excuse persons with disabilities from the exercise entirely to eliminate any risk of "
			"physical injury or operational delay."
		),
		"option_b": (
			"Include persons with disabilities as active planners, participants, and evaluators to "
			"test real-world accessibility, warning systems, and evacuation routes."
		),
		"option_c": (
			"Position persons with disabilities strictly as passive observers in designated safe "
			"zones to watch the simulation from a distance."
		),
		"option_d": (
			"Involve persons with disabilities only after the drill concludes to review photographs "
			"and media press releases."
		),
	},

	# ── HCD (10 questions) ────────────────────────────────────────────────────
	{
		"course": "HCD",
		"question": (
			"An assessment team is entering a displacement camp to understand water collection "
			"challenges. To maintain a human-centered approach while respecting Accountability to "
			"Affected Populations (AAP) principles, how should the team structure interviews?"
		),
		"option_a": (
			"Conduct unannounced video interviews with individuals queueing at water points to "
			"capture unscripted, real-time complaints."
		),
		"option_b": (
			"Establish clear informed consent, use open-ended, non-extractively structured "
			"questions, and ensure interviews are held in safe, confidential spaces."
		),
		"option_c": (
			"Offer immediate cash rewards to participants prior to asking technical questions "
			"about municipal engineering infrastructure."
		),
		"option_d": (
			"Rely exclusively on camp committee leaders to answer questions on behalf of all "
			"displaced women and children to save time."
		),
	},
	{
		"course": "HCD",
		"question": (
			"During a protracted drought crisis, a design team seeks out 'extreme users' to "
			"understand severe coping strategies regarding food distribution. They identify "
			"child-headed households. How should the team balance HCD research goals with "
			"humanitarian protection?"
		),
		"option_a": (
			"Interview child-headed households intensely, pushing for detailed emotional stories "
			"to build maximum empathy for investor pitches."
		),
		"option_b": (
			"Engage specialized child protection officers to guide inclusive, safe interactions "
			"without placing the children at further social or safety risk."
		),
		"option_c": (
			"Exclude child-headed households completely from all humanitarian data collection "
			"and rely solely on secondary literature."
		),
		"option_d": (
			"Require child head-of-households to participate in public focus groups alongside "
			"community elders to validate claims."
		),
	},
	{
		"course": "HCD",
		"question": (
			"After synthesizing qualitative findings from a flood-prone informal settlement, the "
			"team discovers residents refuse to use elevated emergency latrines because they lack "
			"lighting and lockable doors at night. Which 'How Might We' (HMW) statement best "
			"drives a dignified, actionable solution?"
		),
		"option_a": "How might we force residents to use elevated latrines during night hours?",
		"option_b": (
			"How might we redesign camp sanitation facilities so that women and girls feel safe, "
			"private, and dignified when accessing them at any hour?"
		),
		"option_c": (
			"How might we lower the financial cost of municipal concrete latrine construction "
			"by 80 percent?"
		),
		"option_d": (
			"How might we convince residents that physical safety concerns are secondary to "
			"public sanitation risks?"
		),
	},
	{
		"course": "HCD",
		"question": (
			"A team lead is facilitating a co-creation workshop combining international technical "
			"experts, local aid workers, and affected community members. How should the lead "
			"ensure equitable ideation without local voices being silenced?"
		),
		"option_a": (
			"Allow international technical experts to speak first and set the parameters for "
			"what technologies are feasible."
		),
		"option_b": (
			"Defer judgment, utilize visual and multi-lingual silent ideation tools (e.g., "
			"drawing, sorting), and explicitly encourage community-led ideas."
		),
		"option_c": (
			"Critique non-technical ideas immediately during the session to avoid wasting "
			"humanitarian budget on unviable concepts."
		),
		"option_d": (
			"Separate community members into an advisory room while international engineers "
			"select the final solution."
		),
	},
	{
		"course": "HCD",
		"question": (
			"A design team wants to test a low-fidelity, rapid prototype of an alternative "
			"cash-for-work registration app in an active conflict zone. What ethical constraint "
			"must override standard 'fail fast' HCD principles during field testing?"
		),
		"option_a": (
			"Prototyping must never occur until a commercial patent is secured by the agency."
		),
		"option_b": (
			"Low-fidelity testing must be sandboxed or ethically pre-screened to ensure system "
			"failures do not cause real-world loss of aid, security breaches, or harm."
		),
		"option_c": (
			"Testing must be restricted entirely to agency headquarters staff without ever "
			"engaging displaced people."
		),
		"option_d": (
			"Prototypes must be fully functional, high-fidelity production software before any "
			"field user is allowed to touch them."
		),
	},
	{
		"course": "HCD",
		"question": (
			"When testing a complex non-violent communication protocol in a low-literacy "
			"humanitarian setting, which prototype method best allows community members to "
			"evaluate the flow?"
		),
		"option_a": (
			"A 50-page operational manual written in the official administrative language."
		),
		"option_b": (
			"A visual, sequence-based Storyboard using localized illustrations depicting "
			"relatable daily scenarios to invite candid feedback."
		),
		"option_c": (
			"A technical UML architecture diagram showing backend server communication."
		),
		"option_d": "A formal legal contract outlining community compliance obligations.",
	},
	{
		"course": "HCD",
		"question": (
			"An emergency water solution is highly desired by refugees (Desirable) and chemically "
			"effective (Feasible), but requires imported filter cartridges that local markets "
			"cannot source after the NGO leaves. Under humanitarian HCD, why does this fail?"
		),
		"option_a": (
			"It lacks operational viability and long-term sustainability, creating dependency "
			"rather than localized resilience."
		),
		"option_b": (
			"It fails to satisfy international public relations and marketing objectives."
		),
		"option_c": (
			"It violates the principle of rapid, low-fidelity prototyping during initial research."
		),
		"option_d": (
			"It places too much financial responsibility on international donor agencies."
		),
	},
	{
		"course": "HCD",
		"question": (
			"A pilot program for localized solar lighting in displacement camps is moving to "
			"implementation. What key element distinguishes a humanitarian Action Plan from "
			"early ideation outputs?"
		),
		"option_a": "A collection of raw sticky notes collected during preliminary brainstorms.",
		"option_b": (
			"Clear operational milestones, assigned local roles, safety protocols, supply chain "
			"strategies, and monitoring frameworks."
		),
		"option_c": (
			"A theoretical essay describing the history of design thinking methodology."
		),
		"option_d": (
			"A non-binding pledge from community leaders promising zero equipment maintenance."
		),
	},
	{
		"course": "HCD",
		"question": (
			"Three weeks into a pilot distribution of fuel-efficient stoves, monitoring reveals "
			"that households are modifying the stoves with wire to cook traditional large-batch "
			"meals. How should a human-centered design team respond?"
		),
		"option_a": (
			"Confiscate the modified stoves and issue penalties for violating project guidelines."
		),
		"option_b": (
			"View the user modifications as critical insight, iterate the stove design to fit "
			"actual cooking habits, and re-test."
		),
		"option_c": (
			"Close the project immediately and declare fuel-efficient stoves unviable in the region."
		),
		"option_d": (
			"Ignore the modifications as long as the initial donor metrics are reported on time."
		),
	},
	{
		"course": "HCD",
		"question": (
			"Which indicator best demonstrates that a humanitarian organization has successfully "
			"embedded Human-Centered Design into its disaster response operations?"
		),
		"option_a": (
			"The organization holds all strategy meetings behind closed doors in capital cities."
		),
		"option_b": (
			"Programs feature continuous, safe feedback loops where community inputs directly "
			"drive iterative adaptations in service delivery."
		),
		"option_c": (
			"The agency completes all project deliverables strictly according to original 5-year "
			"proposals without changing a single activity."
		),
		"option_d": (
			"Field teams conduct user research as a one-time compliance box to check before "
			"deploying pre-selected equipment."
		),
	},

	# ── TRREE (20 questions) ──────────────────────────────────────────────────
	{
		"course": "TREE",
		"question": (
			"During an acute cholera outbreak in a displaced persons camp, an international NGO "
			"distributes clean water kits while concurrently gathering longitudinal data to test "
			"an unproven water purification tablet. How should the country director categorize "
			"this activity according to TRREE ethics principles?"
		),
		"option_a": (
			"As standard humanitarian emergency assistance that requires no ethics committee "
			"review or formal consent protocols."
		),
		"option_b": (
			"As research involving human participants that must undergo independent ethical "
			"review despite the ongoing humanitarian emergency."
		),
		"option_c": (
			"As clinical audit, exempting the researchers from community engagement or "
			"post-study benefit obligations."
		),
		"option_d": (
			"As public health surveillance that permits bypassing individual participant "
			"safety monitoring mechanisms."
		),
	},
	{
		"course": "TREE",
		"question": (
			"A research institute proposes evaluating a new trauma therapy protocol in an active "
			"conflict zone. However, due to security risks, the sample size will be too small to "
			"yield statistically significant conclusions. Under TRREE research ethics guidelines, "
			"what is the primary ethical status of this study?"
		),
		"option_a": (
			"Ethically acceptable, because collecting any data in a conflict zone is valuable "
			"regardless of sample size."
		),
		"option_b": (
			"Ethically unacceptable, as scientifically invalid research exposes participants to "
			"risk without generating reliable scientific benefit."
		),
		"option_c": (
			"Ethically mandatory, as research in active war zones is exempt from traditional "
			"statistical power calculations."
		),
		"option_d": (
			"Ethically neutral, provided the researchers sign individual safety waivers before "
			"entering the field."
		),
	},
	{
		"course": "TREE",
		"question": (
			"A doctor working for an international aid agency is both treating severely acute "
			"malnourished children and serving as Principal Investigator for a novel therapeutic "
			"food trial. What ethical risk is most prominent in this dual role?"
		),
		"option_a": (
			"Therapeutic misconception, where guardians believe participation is necessary to "
			"receive routine life-saving medical care."
		),
		"option_b": (
			"Operational burnout, which automatically invalidates the scientific methodology "
			"of the clinical protocol."
		),
		"option_c": (
			"Moral injury, caused by prioritizing research data entry over administrative "
			"logistics management."
		),
		"option_d": (
			"Presenteeism, which prevents the clinician from filing routine donor compliance "
			"financial reports."
		),
	},
	{
		"course": "TREE",
		"question": (
			"Researchers want to test a candidate vaccine during an Ebola outbreak in a region "
			"where an existing, moderately effective vaccine is available. The draft protocol "
			"proposes a pure placebo control group. According to Helsinki/CIOMS guidelines "
			"adapted by TRREE, is this ethical?"
		),
		"option_a": (
			"Yes, because using a placebo accelerates the research timeline during a public "
			"health crisis."
		),
		"option_b": (
			"No, because trial participants must receive the established effective intervention "
			"unless compelling methodological reasons justify a placebo without adding harm."
		),
		"option_c": (
			"Yes, provided the local government health authority signs an operational release form."
		),
		"option_d": (
			"No, because international regulations prohibit vaccine trials during emergency "
			"outbreak conditions."
		),
	},
	{
		"course": "TREE",
		"question": (
			"An international university conducts a biomarker study on refugees in a border camp, "
			"using local populations solely for biological sample collection. The diagnostic tool "
			"under development will be patented and priced for high-income hospitals. How does "
			"TRREE evaluate this scenario?"
		),
		"option_a": (
			"As equitable research that provides immediate diagnostic exposure to refugees."
		),
		"option_b": (
			"As exploitation, violating justice principles because burdens are placed on a "
			"vulnerable population without ensuring post-research access or local benefit."
		),
		"option_c": (
			"As an acceptable application of global clinical trial standards in low-resource "
			"environments."
		),
		"option_d": (
			"As a standard public health research intervention exempt from fair benefit rules."
		),
	},
	{
		"course": "TREE",
		"question": (
			"Following a devastating earthquake, an academic team requests emergency ethical "
			"clearance for a mental health survey. The national Research Ethics Committee (REC) "
			"implements a fast-track review process. What minimum standard must be maintained?"
		),
		"option_a": (
			"The committee may waive all risk-benefit assessments to approve the project "
			"within 24 hours."
		),
		"option_b": (
			"The committee must maintain rigorous multi-disciplinary review of participant "
			"safety, rights, and protocol validity without compromising ethical standards."
		),
		"option_c": (
			"The committee must delegate the entire review authority to international NGO "
			"field managers."
		),
		"option_d": (
			"The committee can eliminate the requirement for local community consultation and "
			"data security plans."
		),
	},
	{
		"course": "TREE",
		"question": (
			"A university in the Global North receives REC approval from its home board to "
			"conduct a gender-based violence (GBV) study in a refugee camp in Africa. The "
			"researchers claim local REC approval in the host country is unnecessary due to "
			"collapsed infrastructure. How should TRREE guidelines treat this protocol?"
		),
		"option_a": (
			"Research must receive local REC or host-country ethical approval (or authorized "
			"national waiver) to respect local governance and context."
		),
		"option_b": (
			"Foreign institutional approval is legally and ethically sufficient in all "
			"humanitarian displacement settings."
		),
		"option_c": (
			"The protocol requires approval only from the United Nations High Commissioner "
			"for Refugees (UNHCR)."
		),
		"option_d": (
			"Ethics review is waived entirely when researching sensitive protection topics "
			"like gender-based violence."
		),
	},
	{
		"course": "TREE",
		"question": (
			"When reviewing a study protocol on epidemic response, a Research Ethics Committee "
			"evaluates the project's Community Advisory Board (CAB) plan. Why is local CAB "
			"engagement critical under TRREE guidelines?"
		),
		"option_a": (
			"It ensures the community funds 50% of the operational research expenses."
		),
		"option_b": (
			"It provides contextual insights to adapt informed consent, minimize cultural harms, "
			"and ensure research relevance."
		),
		"option_c": (
			"It replaces the requirement for individual written informed consent forms."
		),
		"option_d": (
			"It allows researchers to bypass local institutional review boards."
		),
	},
	{
		"course": "TREE",
		"question": (
			"A member of a national REC reviewing a high-budget crisis research protocol is also "
			"a paid consultant for the pharmaceutical company donating the trial drug. What is "
			"the mandatory action under TRREE REC operating procedures?"
		),
		"option_a": (
			"The member must disclose the conflict of interest and recuse themselves from "
			"deliberations and decision-making on that protocol."
		),
		"option_b": (
			"The member may vote on the protocol provided they sign a confidentiality agreement."
		),
		"option_c": (
			"The REC must dissolve immediately and transfer the file to an international tribunal."
		),
		"option_d": (
			"The member should lead the ethical review panel to ensure technical accuracy."
		),
	},
	{
		"course": "TREE",
		"question": (
			"Six months into an observational study on displacement dynamics, security "
			"deteriorates significantly, increasing participant exposure to military retaliation. "
			"What is the ethical obligation of the research team and REC?"
		),
		"option_a": (
			"Continue data collection without change until the pre-scheduled project end date."
		),
		"option_b": (
			"Suspend or modify the research protocol immediately to mitigate heightened risks "
			"to human subjects."
		),
		"option_c": (
			"Destroy all collected data to prevent administrative audits by donor agencies."
		),
		"option_d": (
			"Shift the study focus from human observation to non-consensual biological sampling."
		),
	},
	{
		"course": "TREE",
		"question": (
			"During a famine response, researchers offer cash grants equivalent to three months' "
			"income to starving villagers who agree to participate in a clinical trial. How should "
			"an ethics reviewer categorize this offer under TRREE consent standards?"
		),
		"option_a": (
			"As a fair operational compensation for participant time and effort."
		),
		"option_b": (
			"As undue inducement, which compromises voluntary consent by distorting the "
			"participant's ability to assess research risks."
		),
		"option_c": (
			"As an adaptive humanitarian relief mechanism that bypasses standard consent."
		),
		"option_d": (
			"As a standard practice supported by international clinical trial frameworks."
		),
	},
	{
		"course": "TREE",
		"question": (
			"In an acute displacement setting where most participants cannot read or write, a "
			"research team seeks to obtain consent for a social survey. Which procedure aligns "
			"with TRREE Module 3 on Informed Consent?"
		),
		"option_a": (
			"Require illiterate participants to sign formal legal English documentation."
		),
		"option_b": (
			"Administer an oral consent process in the local language, witnessed and documented "
			"by an independent impartial witness."
		),
		"option_c": (
			"Waive consent entirely because written documentation is physically impossible."
		),
		"option_d": (
			"Obtain blanket consent from camp community leaders on behalf of all individuals."
		),
	},
	{
		"course": "TREE",
		"question": (
			"A health study aims to include unaccompanied refugee children (under age 16) who "
			"lack legal parents or guardians present in the camp. According to TRREE standards, "
			"how can consent/assent be ethically structured?"
		),
		"option_a": (
			"Children may be enrolled without any assent process if researchers deem it beneficial."
		),
		"option_b": (
			"Seek child assent paired with authorization from an appointed legal guardian, "
			"independently designated advocate, or ethics committee-approved proxy."
		),
		"option_c": (
			"Unaccompanied minors are strictly prohibited from participating in all forms of "
			"humanitarian research under all circumstances."
		),
		"option_d": (
			"Require the military camp commander to sign parental release forms for all minors."
		),
	},
	{
		"course": "TREE",
		"question": (
			"A participant enrolled in a post-traumatic stress trial in a civilian protection camp "
			"decides to withdraw from the study midway. The local clinic coordinator threatens to "
			"stop providing them standard food rations. What ethical principle is violated?"
		),
		"option_a": (
			"The requirement that consent must be freely withdrawn at any time without penalty "
			"or loss of entitled standard benefits."
		),
		"option_b": (
			"The principle of double-blind operational randomization."
		),
		"option_c": (
			"The obligation to maintain strict epidemiological data disaggregation."
		),
		"option_d": (
			"The requirement for continuous pre-registration of clinical trials."
		),
	},
	{
		"course": "TREE",
		"question": (
			"A 12-page dense technical consent form detailing molecular genetics is translated "
			"word-for-word into a local dialect and read aloud to displaced participants during a "
			"flood response. Tests show participants understand none of the risks. Under TRREE, "
			"what is the status of this consent?"
		),
		"option_a": (
			"Valid, because all technical facts were fully disclosed in the local language."
		),
		"option_b": (
			"Invalid, because informed consent requires actual participant comprehension, not "
			"merely the technical disclosure of information."
		),
		"option_c": (
			"Valid, provided the participant signs or leaves a thumbprint at the end."
		),
		"option_d": (
			"Invalid, because genetics research cannot be conducted in emergency settings."
		),
	},
	{
		"course": "TREE",
		"question": (
			"Researchers collect GPS location coordinates and survey data on survivors of sexual "
			"violence in an active war zone. The data is stored on an unencrypted cloud drive. "
			"What is the major ethical violation according to TRREE data security standards?"
		),
		"option_a": (
			"Failure to publish the dataset open-access within 48 hours of collection."
		),
		"option_b": (
			"Severe breach of confidentiality that exposes vulnerable survivors to lethal "
			"retaliation, re-traumatization, and social stigma."
		),
		"option_c": (
			"Violation of local copyright laws regarding geographical mapping data."
		),
		"option_d": (
			"Failure to charge commercial usage fees for international donor access."
		),
	},
	{
		"course": "TREE",
		"question": (
			"When assessing research involving displaced populations, how does TRREE define "
			"'vulnerability' in an ethical context?"
		),
		"option_a": (
			"As an inherent biological flaw present in specific ethnic minority groups."
		),
		"option_b": (
			"As a context-dependent state where individuals have a reduced capacity to protect "
			"their own interests due to structural, social, or situational factors."
		),
		"option_c": (
			"As an administrative status applied only to individuals under 18 years of age."
		),
		"option_d": (
			"As a complete inability to make autonomous decisions under any circumstances."
		),
	},
	{
		"course": "TREE",
		"question": (
			"An international team collects viral pathogens and blood samples from crisis-affected "
			"patients during an outbreak. The team transfers samples to foreign laboratories without "
			"a Material Transfer Agreement (MTA) or benefit-sharing plan. What TRREE rule is breached?"
		),
		"option_a": (
			"The ethical requirement for transparent data governance, local capacity building, "
			"and equitable benefit-sharing regarding biological resources."
		),
		"option_b": (
			"The prohibition of international transport of biological samples during wartime."
		),
		"option_c": (
			"The mandate that all biological samples must be destroyed immediately after collection."
		),
		"option_d": (
			"The requirement that foreign universities assume ownership of host-country health data."
		),
	},
	{
		"course": "TREE",
		"question": (
			"During a refugee meningitis outbreak, the Ministry of Health conducts mandatory "
			"anonymous biological screening to establish population-level infection thresholds. "
			"How does public health ethics differ from individual clinical research ethics here?"
		),
		"option_a": (
			"Public health surveillance prioritizes collective population risk reduction and may "
			"operate under statutory public authority without individual consent, subject to "
			"strict safeguards."
		),
		"option_b": (
			"Public health surveillance requires higher monetary compensation for participants "
			"than clinical trials."
		),
		"option_c": (
			"Clinical research ethics permits non-consensual invasive testing, whereas public "
			"health surveillance forbids it."
		),
		"option_d": (
			"There is no difference; both operate under identical clinical trial regulations."
		),
	},
	{
		"course": "TREE",
		"question": (
			"An NGO completes a 2-year mental health study in a post-conflict zone. The researchers "
			"publish their findings in a high-impact European journal but do not return to share "
			"results or actionable recommendations with the community. How is this evaluated?"
		),
		"option_a": (
			"As standard academic practice that completely fulfills all research ethics obligations."
		),
		"option_b": (
			"As an ethical failure to provide feedback to researched communities, violating "
			"principles of respect, transparency, and accountability."
		),
		"option_c": (
			"As an exemplary demonstration of data privacy and participant protection."
		),
		"option_d": (
			"As a legal breach of international intellectual property conventions."
		),
	},

	# ── Wellness & Resilience (12 questions) ──────────────────────────────────
	{
		"course": "Wellness & Resilience",
		"question": (
			"During a sudden flood response, a logistician's heart rate spikes, breathing becomes "
			"shallow, and they experience a surge of focus to clear a blocked supply route. Six "
			"hours later, after the immediate danger passes, the same worker remains hyper-vigilant, "
			"irritable, and unable to process basic delivery manifests. How should a team lead "
			"evaluate these two states?"
		),
		"option_a": (
			"Both states represent maladaptive distress requiring immediate operational suspension "
			"and psychological debriefing."
		),
		"option_b": (
			"The initial response was a functional acute stress reaction (eustress), whereas the "
			"prolonged state indicates overwhelming distress requiring rest and stabilization."
		),
		"option_c": (
			"The initial reaction was a sign of vicarious trauma, while the secondary state "
			"represents chronic operational burnout."
		),
		"option_d": (
			"The worker is experiencing moral injury brought on by the rapid operational tempo "
			"of the emergency response."
		),
	},
	{
		"course": "Wellness & Resilience",
		"question": (
			"A caseworker with four years of continuous deployment in conflict zones has gradually "
			"become emotionally detached, routinely refers to displaced families using cynical "
			"language, and expresses a sense that their efforts no longer matter. They continue to "
			"complete tasks on time. What condition is primarily indicated here?"
		),
		"option_a": "Acute stress reaction triggered by recent field events.",
		"option_b": "Vicarious trauma resulting from a single traumatic disclosure.",
		"option_c": "Occupational burnout characterized by emotional exhaustion and depersonalization.",
		"option_d": "Moral injury caused by a direct violation of personal ethical principles.",
	},
	{
		"course": "Wellness & Resilience",
		"question": (
			"A human rights interviewer transcribing daily accounts of severe violence begins "
			"experiencing intrusive imagery, nightmares, and an altered worldview where they feel "
			"nowhere is safe. They have not been exposed to direct physical danger themselves. "
			"What is the most accurate assessment of their condition?"
		),
		"option_a": (
			"The worker is demonstrating normal workplace fatigue that can be resolved with "
			"standard annual leave."
		),
		"option_b": (
			"The worker is experiencing vicarious trauma from indirect, repeated exposure to "
			"severe traumatic content."
		),
		"option_c": (
			"The worker is showing signs of presenteeism caused by excessive administrative workloads."
		),
		"option_d": (
			"The worker is experiencing a temporary acute stress reaction that will clear "
			"automatically during their shift."
		),
	},
	{
		"course": "Wellness & Resilience",
		"question": (
			"During an epidemic outbreak, a medical triage officer must turn away ill individuals "
			"because the clinic has run out of basic life-saving supplies. Weeks later, the officer "
			"is paralyzed by guilt and self-loathing, feeling they violated their core human duty. "
			"How should a manager interpret this psychological response?"
		),
		"option_a": (
			"As a standard manifestation of physical exhaustion requiring rest and relaxation cycles."
		),
		"option_b": (
			"As moral injury stemming from witnessing and executing actions that transgressed "
			"deeply held moral values."
		),
		"option_c": (
			"As a failure of personal adaptive coping mechanisms that requires mandatory "
			"technical retraining."
		),
		"option_d": (
			"As a typical eustress response that will eventually drive improved clinical performance."
		),
	},
	{
		"course": "Wellness & Resilience",
		"question": (
			"Upon arriving at an emergency site following a structural collapse, a field worker "
			"trained in PFA immediately prepares to offer support. Following the 'LOOK' action "
			"principle, what should be their immediate priority before approaching distressed "
			"individuals?"
		),
		"option_a": (
			"Ask survivors detailed questions about who is missing to establish immediate line lists."
		),
		"option_b": (
			"Check for physical safety hazards, observe who has urgent basic needs, and identify "
			"severe distress."
		),
		"option_c": (
			"Gather all affected individuals into a structured circle to deliver group "
			"psychoeducation."
		),
		"option_d": (
			"Distribute emergency contact numbers and link survivors to secondary health facilities."
		),
	},
	{
		"course": "Wellness & Resilience",
		"question": (
			"A survivor of a severe disaster approaches an aid worker, weeping uncontrollably and "
			"speaking incoherently. Which action by the aid worker strictly aligns with PFA "
			"'LISTEN' guidelines?"
		),
		"option_a": (
			"Press the survivor to explain the exact timeline of events so an incident report "
			"can be filed."
		),
		"option_b": (
			"Interrupt gently to offer immediate solutions and assure them that everything will "
			"turn out fine."
		),
		"option_c": (
			"Stay close, listen quietly without forcing speech, validate their feelings, and "
			"inquire about immediate needs."
		),
		"option_d": (
			"Escort the survivor immediately to a clinical psychologist for specialized trauma "
			"counseling."
		),
	},
	{
		"course": "Wellness & Resilience",
		"question": (
			"An aid worker is supporting a displaced person who is anxious about finding their "
			"lost adolescent child. The survivor refuses food and water. According to PFA "
			"priorities, how should the worker execute the 'LINK' principle?"
		),
		"option_a": (
			"Require the person to eat and sleep before initiating any search efforts or "
			"contacting support agencies."
		),
		"option_b": (
			"Connect the survivor with family tracing services, basic emergency supplies, and "
			"available community networks."
		),
		"option_c": (
			"Advise the survivor to accept that the child is gone and refer them to long-term "
			"grief therapy."
		),
		"option_d": (
			"Take personal responsibility for locating the missing child while leaving the "
			"survivor unattended."
		),
	},
	{
		"course": "Wellness & Resilience",
		"question": (
			"Following high-intensity field shifts, two team members cope differently: Worker A "
			"spends an hour exercising and calling family, while Worker B drinks heavily every "
			"evening to block out memories of the shift. How should an organizational reviewer "
			"categorize these strategies?"
		),
		"option_a": (
			"Both are acceptable coping strategies if they allow the workers to report for duty "
			"the next morning."
		),
		"option_b": (
			"Worker A uses adaptive coping that builds long-term resilience; Worker B uses "
			"maladaptive coping that creates secondary risks."
		),
		"option_c": (
			"Worker A is engaging in presenteeism, whereas Worker B is demonstrating personal "
			"reframing."
		),
		"option_d": (
			"Worker A requires organizational intervention, while Worker B is demonstrating "
			"standard field self-care."
		),
	},
	{
		"course": "Wellness & Resilience",
		"question": (
			"A logistics officer's convoy is turned back due to a sudden border closure, delaying "
			"critical aid delivery. Instead of viewing the event as an absolute failure, the "
			"officer notes: 'This route is blocked today, but our team is safe, and this gives us "
			"time to establish an alternative river passage.' What cognitive technique is being "
			"demonstrated?"
		),
		"option_a": (
			"Cognitive reframing to convert a feeling of helplessness into a manageable "
			"operational challenge."
		),
		"option_b": (
			"Maladaptive denial of operational realities to preserve team morale."
		),
		"option_c": (
			"Vicarious processing to deflect responsibility onto border control authorities."
		),
		"option_d": (
			"Psychological detachment to avoid addressing project management deficiencies."
		),
	},
	{
		"course": "Wellness & Resilience",
		"question": (
			"A project manager notices that a senior field coordinator has worked 16-hour days for "
			"three consecutive weeks without taking days off. The coordinator insists they are "
			"'fine,' but they are making frequent analytical errors, missing critical safety "
			"alerts, and acting snappy with staff. What phenomenon is occurring, and how should "
			"the manager respond?"
		),
		"option_a": (
			"Eustress; the manager should award the coordinator an exemplary performance review."
		),
		"option_b": (
			"Presenteeism; the manager must enforce mandatory rest periods and redistribute the "
			"workload to safeguard the staff member and operations."
		),
		"option_c": (
			"Vicarious resilience; the manager should ask the coordinator to mentor junior staff "
			"on endurance."
		),
		"option_d": (
			"Moral injury; the manager should immediately refer the coordinator for specialized "
			"psychiatric evaluation."
		),
	},
	{
		"course": "Wellness & Resilience",
		"question": (
			"A country office operating in a chronic emergency setting experiences high staff "
			"turnover and widespread operational fatigue. Which policy intervention represents an "
			"effective organizational duty-of-care response to prevent burnout?"
		),
		"option_a": (
			"Replacing structured debriefings with mandatory individual self-care assignments "
			"after hours."
		),
		"option_b": (
			"Establishing mandatory Rest & Recuperation (R&R) cycles, enforceable shift limits, "
			"and fair workload distribution."
		),
		"option_c": (
			"Offering financial bonuses to workers who voluntarily forfeit their annual leave "
			"during crisis peaks."
		),
		"option_d": (
			"Requiring staff to sign liability waivers acknowledging personal responsibility for "
			"field-induced stress."
		),
	},
	{
		"course": "Wellness & Resilience",
		"question": (
			"A field team is completing a six-month deployment in an active conflict zone. What is "
			"the primary welfare objective of conducting an end-of-deployment operational "
			"debriefing?"
		),
		"option_a": (
			"To collect detailed evidence for internal financial audits and inventory reconciliations."
		),
		"option_b": (
			"To acknowledge contributions, process operational challenges, and facilitate a safe "
			"psychological transition out of the emergency setting."
		),
		"option_c": (
			"To identify individual team members responsible for project delays and assign "
			"administrative accountability."
		),
		"option_d": (
			"To require staff to pledge availability for immediate redeployment to new emergency "
			"zones."
		),
	},
]


# Correct answers per course, in question order (from official answer keys)
CORRECT_ANSWERS = {
	"DiDRR": ["B", "B", "B", "B", "B", "B", "B", "B"],
	"HCD":   ["B", "B", "B", "B", "B", "B", "A", "B", "B", "B"],
	"TREE":  ["B", "B", "A", "B", "B", "B", "A", "B", "A", "B", "B", "B", "B", "A", "B", "B", "B", "A", "A", "B"],
	"Wellness & Resilience": ["B", "C", "B", "B", "B", "C", "B", "B", "A", "B", "B", "B"],
}


def execute():
	"""Seed ICHA Questions. Idempotent — skips any already inserted.
	Also corrects any existing records that still have wrong correct_answer values."""
	inserted = 0
	course_counters = {}

	for q_data in QUESTIONS:
		course = q_data["course"]
		course_counters[course] = course_counters.get(course, 0)
		idx = course_counters[course]
		correct_answer = CORRECT_ANSWERS[course][idx]
		course_counters[course] += 1

		existing = frappe.db.get_value(
			"ICHA Question",
			{"course": course, "question": q_data["question"]},
			["name", "correct_answer"],
			as_dict=True,
		)

		if existing:
			# Fix correct_answer if it was previously wrong
			if existing.correct_answer != correct_answer:
				frappe.db.set_value("ICHA Question", existing.name, "correct_answer", correct_answer)
			continue

		doc = frappe.get_doc(
			{
				"doctype": "ICHA Question",
				"course": course,
				"question": q_data["question"],
				"option_a": q_data["option_a"],
				"option_b": q_data["option_b"],
				"option_c": q_data["option_c"],
				"option_d": q_data["option_d"],
				"correct_answer": correct_answer,
			}
		)
		doc.insert(ignore_permissions=True)
		inserted += 1

	frappe.db.commit()
