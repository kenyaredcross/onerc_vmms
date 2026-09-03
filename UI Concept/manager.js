(function(){
  document.getElementById('view-deployments')?.insertAdjacentHTML('beforebegin',`<section class="manager-view" id="view-operations" data-view="operations" data-title="Operations">
    <div data-operation-panel="overview"><header class="view-head"><div><p class="eyebrow">Operations</p><h2>Field operations</h2><p>Plan approved work, mobilise volunteers, and keep every running deployment under control.</p></div><div class="action-row"><a class="secondary-btn" href="#operations?section=terms">Review TORs</a><a class="primary-btn" href="#operations?section=new">Create deployment</a></div></header><div class="operations-pulse"><article><small>Ongoing deployments</small><strong>3</strong><span>82 people currently assigned</span></article><article><small>Starting in 14 days</small><strong>2</strong><span>21 roles still unfilled</span></article><article class="attention"><small>Requests awaiting response</small><strong>9</strong><span>3 expire today</span></article><article><small>Tasks needing attention</small><strong>13</strong><span>7 questions · 6 overdue</span></article></div><div class="operations-grid"><section class="panel"><div class="panel-head"><div><h3>Live operations</h3><p>What is running and what needs intervention</p></div><a href="#operations?section=ongoing">View all →</a></div><a class="operation-row" href="#deployment-record"><span class="operation-state live">Live</span><span><strong>Garissa Nutrition Outreach</strong><small>Day 8 of 14 · Garissa County</small></span><span><small>People</small><b>34</b></span><span><small>Tasks</small><b class="warn">6 overdue</b></span><em>Ends 7 Sep</em><b class="chev">›</b></a><a class="operation-row" href="#deployment-record"><span class="operation-state mobilising">Mobilising</span><span><strong>Tana River Flood Response — Wave 3</strong><small>Starts 14 Sep · Tana River County</small></span><span><small>Filled</small><b>21 / 30</b></span><span><small>Responses</small><b class="warn">9 pending</b></span><em>12 days</em><b class="chev">›</b></a><a class="operation-row" href="#deployment-record"><span class="operation-state closeout">Close-out</span><span><strong>Kibera Fire Response</strong><small>Ended 27 Aug · Nairobi County</small></span><span><small>People</small><b>19</b></span><span><small>Close-out</small><b class="warn">Hours due</b></span><em>6 days ago</em><b class="chev">›</b></a></section><aside class="panel operations-attention"><div class="panel-head"><div><h3>Operations attention</h3><p>Across terms, requests and tasks</p></div></div><a href="#operations?section=terms"><span>TOR</span><div><strong>2 terms await approval</strong><small>Oldest waiting 3 days</small></div><b>›</b></a><a href="#operations?section=requests"><span>REQ</span><div><strong>3 invitations expire today</strong><small>Tana River Wave 3</small></div><b>›</b></a><a href="#tasks"><span>TSK</span><div><strong>7 volunteer questions</strong><small>Coordinator answer required</small></div><b>›</b></a><a href="#operations?section=documents"><span>DOC</span><div><strong>4 close-out files missing</strong><small>Kibera Fire Response</small></div><b>›</b></a></aside></div><section class="panel readiness-strip"><div><span class="readiness-icon">✓</span><div><strong>Next operation readiness</strong><small>Tana River Flood Response — Wave 3 · starts 14 September</small></div></div><div><small>Roles filled</small><strong>21 / 30</strong><i><b style="width:70%"></b></i></div><div><small>TOR</small><strong class="good">Approved</strong></div><div><small>Invitations</small><strong class="warn">9 pending</strong></div><a href="#deployment-record">Open operation →</a></section></div>
    <div data-operation-panel="terms" hidden><header class="view-head"><div><p class="eyebrow">Operations / Plan</p><h2>Terms of Reference</h2><p>Approved scope, resources, schedule and accountability before deployment begins.</p></div><button class="primary-btn" data-toast="Terms of Reference editor opened.">Write terms</button></header><div class="toolbar"><input placeholder="Search terms, project or area"><select><option>All approval states</option><option>Draft</option><option>In Review</option><option>Approved</option></select><button class="secondary-btn" data-toast="Terms of Reference documents filtered.">Filter</button></div><section class="tor-paper-grid"><a class="tor-paper approved" href="#" data-toast="Tana River TOR document preview opened."><span class="paper-fold"></span><header><span class="paper-mark">✚</span><div><strong>Kenya Red Cross Society</strong><small>Operations Directorate</small></div></header><div class="paper-rule"></div><p class="paper-type">Terms of Reference</p><small class="paper-reference">TOR-2026-041 · APPROVED VERSION</small><h3>Tana River Flood Response — Wave 3</h3><p class="paper-project">Flood Preparedness and Response</p><dl><dt>Purpose</dt><dd>Support flood-affected households with health, relief and protection services across Hola and surrounding settlements.</dd><dt>Area</dt><dd>Tana River County</dd><dt>Expected period</dt><dd>14–25 September 2026</dd></dl><footer><span>Approved 30 Aug 2026</span><b>Open document →</b></footer><em class="paper-stamp">Approved</em></a><a class="tor-paper review" href="#" data-toast="Coast Cholera TOR review opened."><span class="paper-fold"></span><header><span class="paper-mark">✚</span><div><strong>Kenya Red Cross Society</strong><small>Operations Directorate</small></div></header><div class="paper-rule"></div><p class="paper-type">Terms of Reference</p><small class="paper-reference">TOR-2026-044 · REVIEW COPY</small><h3>Coast Cholera Preparedness</h3><p class="paper-project">Health Emergency Readiness</p><dl><dt>Purpose</dt><dd>Prepare branch teams and health partners for rapid detection, referral and community risk communication.</dd><dt>Area</dt><dd>Mombasa County</dd><dt>Expected period</dt><dd>28 Sep–4 Oct 2026</dd></dl><footer><span>County approval · stage 2</span><b>Review document →</b></footer><em class="paper-stamp">In review</em></a><a class="tor-paper approved" href="#" data-toast="Garissa Nutrition TOR document preview opened."><span class="paper-fold"></span><header><span class="paper-mark">✚</span><div><strong>Kenya Red Cross Society</strong><small>Operations Directorate</small></div></header><div class="paper-rule"></div><p class="paper-type">Terms of Reference</p><small class="paper-reference">TOR-2026-036 · APPROVED VERSION</small><h3>Garissa Nutrition Outreach</h3><p class="paper-project">Community Health & Nutrition</p><dl><dt>Purpose</dt><dd>Deliver nutrition screening, health education and referral support through three coordinated field teams.</dd><dt>Area</dt><dd>Garissa County</dd><dt>Expected period</dt><dd>25 Aug–7 Sep 2026</dd></dl><footer><span>Approved 18 Aug 2026</span><b>Open document →</b></footer><em class="paper-stamp">Approved</em></a><a class="tor-paper draft" href="#" data-toast="Nairobi Marathon TOR draft opened."><span class="paper-fold"></span><header><span class="paper-mark">✚</span><div><strong>Kenya Red Cross Society</strong><small>Operations Directorate</small></div></header><div class="paper-rule"></div><p class="paper-type">Terms of Reference</p><small class="paper-reference">TOR-2026-043 · WORKING DRAFT</small><h3>Nairobi Marathon First Aid</h3><p class="paper-project">Event Medical Services</p><dl><dt>Purpose</dt><dd>Provide coordinated first-aid coverage, ambulance referral and incident reporting along the marathon route.</dd><dt>Area</dt><dd>Nairobi County</dd><dt>Expected period</dt><dd>20–21 September 2026</dd></dl><footer><span>Edited 1 Sep 2026</span><b>Continue writing →</b></footer><em class="paper-stamp">Draft</em></a><a class="tor-paper review" href="#" data-toast="Lake Victoria Flood Relief TOR review opened."><span class="paper-fold"></span><header><span class="paper-mark">✚</span><div><strong>Kenya Red Cross Society</strong><small>Operations Directorate</small></div></header><div class="paper-rule"></div><p class="paper-type">Terms of Reference</p><small class="paper-reference">TOR-2026-047 · REVIEW COPY</small><h3>Lake Victoria Flood Relief</h3><p class="paper-project">Flood Preparedness and Response</p><dl><dt>Purpose</dt><dd>Assess displaced households and coordinate relief, health and protection support with county partners.</dd><dt>Area</dt><dd>Kisumu County</dd><dt>Expected period</dt><dd>3–10 October 2026</dd></dl><footer><span>National review · stage 3</span><b>Review document →</b></footer><em class="paper-stamp">In review</em></a></section></div>
    <div data-operation-panel="new" hidden><header class="view-head"><div><p class="eyebrow">Operations / Plan</p><h2>Create deployment</h2><p>Raise a deployment from approved terms and a defined operational place.</p></div><a class="secondary-btn" href="#operations">Cancel</a></header><section class="panel form-card"><div class="field-grid"><div class="field full"><label>Deployment title *</label><input placeholder="e.g. Tana River Flood Response — Wave 4"></div><div class="field"><label>Approved Terms of Reference *</label><select><option>Select approved terms</option><option>Tana River Flood Response — Wave 3</option></select></div><div class="field"><label>Project</label><input value="2026 Flood Preparedness and Response" readonly></div><div class="field"><label>Operational area *</label><select><option>Tana River County</option><option>Nairobi County</option></select></div><div class="field"><label>Reporting point</label><input placeholder="Branch office or field location"></div><div class="field"><label>Starts *</label><input type="date"></div><div class="field"><label>Ends *</label><input type="date"></div><div class="field full"><label>Coordinator note</label><textarea></textarea></div></div><div class="action-row" style="margin-top:16px"><button class="secondary-btn" data-toast="Deployment draft saved.">Save draft</button><button class="primary-btn" data-toast="Deployment created from the approved terms.">Create deployment</button></div></section></div>
    <div data-operation-panel="ongoing" hidden><header class="view-head"><div><p class="eyebrow">Operations / Manage</p><h2>Ongoing deployments</h2><p>Mobilising, active and closing operations within your scope.</p></div><a class="primary-btn" href="#operations?section=new">Create deployment</a></header><div class="kanban"><section class="kanban-col"><div class="kanban-head"><span>Mobilising</span><b>2</b></div><a class="kanban-card" href="#deployment-record"><strong>Tana River Flood Response</strong><p>21 filled · 9 pending responses</p><small>Starts 14 Sep</small></a><a class="kanban-card" href="#deployment-record"><strong>Nairobi Marathon First Aid</strong><p>42 of 60 roles filled</p><small>Starts 21 Sep</small></a></section><section class="kanban-col"><div class="kanban-head"><span>Running</span><b>1</b></div><a class="kanban-card" href="#deployment-record"><strong>Garissa Nutrition Outreach</strong><p>34 people · 6 tasks overdue</p><small>Day 8 of 14</small></a></section><section class="kanban-col"><div class="kanban-head"><span>Close-out</span><b>1</b></div><a class="kanban-card" href="#deployment-record"><strong>Kibera Fire Response</strong><p>Hours and evidence outstanding</p><small>Ended 27 Aug</small></a></section></div></div>
    <div data-operation-panel="past" hidden><header class="view-head"><div><p class="eyebrow">Operations / Manage</p><h2>Past deployments</h2><p>Each closed mission is kept as a complete deployment file.</p></div></header><div class="toolbar"><input placeholder="Search mission file, reference or area"><select><option>All years</option><option>2026</option><option>2025</option><option>2024</option></select><button class="secondary-btn" data-toast="Past deployment folders filtered.">Filter</button></div><section class="past-folder-grid"><a class="past-folder-card" href="#deployment-record"><i></i><span>2026 mission file · DEP-2026-019</span><strong>Kibera Fire Response</strong><p>Emergency Response 2026 · Nairobi County</p><small>19 assignments · TOR · 12 documents</small><em>Closed 27 Aug 2026</em></a><a class="past-folder-card" href="#deployment-record"><i></i><span>2026 mission file · DEP-2026-014</span><strong>Garissa Drought Response</strong><p>Drought Recovery Programme · Garissa County</p><small>34 assignments · TOR · 9 documents</small><em>Closed 18 Jun 2026</em></a><a class="past-folder-card" href="#deployment-record"><i></i><span>2026 mission file · DEP-2026-008</span><strong>Lake Victoria Flood Relief</strong><p>Flood Preparedness · Kisumu County</p><small>26 assignments · TOR · 8 documents</small><em>Closed 22 Apr 2026</em></a><a class="past-folder-card" href="#deployment-record"><i></i><span>2025 mission file · DEP-2025-041</span><strong>Taveta Cholera Preparedness</strong><p>Health Emergency Readiness · Taita Taveta</p><small>18 assignments · TOR · 7 documents</small><em>Closed 11 Nov 2025</em></a><a class="past-folder-card" href="#deployment-record"><i></i><span>2025 mission file · DEP-2025-029</span><strong>Nairobi Marathon First Aid</strong><p>Event Medical Services · Nairobi County</p><small>60 assignments · TOR · 14 documents</small><em>Closed 29 Sep 2025</em></a><a class="past-folder-card" href="#deployment-record"><i></i><span>2024 mission file · DEP-2024-018</span><strong>National Blood Donor Week</strong><p>Blood Services Programme · National</p><small>45 assignments · TOR · 6 documents</small><em>Closed 21 Jun 2024</em></a></section></div>
    <div data-operation-panel="requests" hidden><header class="view-head"><div><p class="eyebrow">Operations / Manage</p><h2>Deployment requests</h2><p>Invitation responses and deadlines before assignments are confirmed.</p></div></header><div class="toolbar"><input placeholder="Search volunteer or deployment"><select><option>Awaiting response</option><option>Accepted</option><option>Declined</option><option>Expired</option></select><button class="secondary-btn">Filter</button></div><section class="panel data-panel"><table class="data-table"><thead><tr><th>Volunteer</th><th>Deployment</th><th>Role</th><th>Respond by</th><th>Status</th><th></th></tr></thead><tbody><tr><td><strong>Alex Mwangi</strong><small>KRC-V-2026-018</small></td><td>Tana River Flood Response</td><td>Community Health Volunteer</td><td>Today · 17:00</td><td><span class="status amber">Awaiting response</span></td><td><a href="#deployment-record">Open →</a></td></tr><tr><td><strong>Peter Kariuki</strong><small>KRC-V-2025-402</small></td><td>Nairobi Marathon First Aid</td><td>First aider</td><td>4 Sep · 17:00</td><td><span class="status amber">Awaiting response</span></td><td><a href="#deployment-record">Open →</a></td></tr></tbody></table></section></div>
    <div data-operation-panel="documents" hidden><header class="view-head"><div><p class="eyebrow">Operations / Manage</p><h2>Operations documents</h2><p>Private files attached to the project, terms or deployment they support.</p></div><button class="primary-btn" data-toast="Private document upload opened.">Upload document</button></header><div class="toolbar"><input placeholder="Search files or operational records"><select><option>All record types</option><option>Project</option><option>Terms of Reference</option><option>Deployment</option></select><button class="secondary-btn">Filter</button></div><section class="panel data-panel"><table class="data-table"><thead><tr><th>Document</th><th>Attached to</th><th>Record type</th><th>Owner</th><th>Updated</th><th></th></tr></thead><tbody><tr><td><strong>Tana River TOR v1.4.pdf</strong><small>1.8 MB · Private</small></td><td>Tana River Flood Response</td><td>Terms of Reference</td><td>Jane Njeri</td><td>30 Aug</td><td><a href="#" data-toast="Private document opened.">Open →</a></td></tr><tr><td><strong>Wave 3 resource plan.xlsx</strong><small>680 KB · Private</small></td><td>Tana River Flood Response</td><td>Deployment</td><td>Jane Njeri</td><td>31 Aug</td><td><a href="#" data-toast="Private document opened.">Open →</a></td></tr></tbody></table></section></div>
  </section>`);
  document.querySelector('[data-operation-panel="overview"] .operations-pulse')?.insertAdjacentHTML('afterend',`<section class="panel operations-map-card"><header class="operations-map-head"><div><span class="map-live-dot"></span><div><h3>Deployment map</h3><p>Operational sites from deployment coordinates; select a marker for the mission picture.</p></div></div><div class="map-controls"><button class="active" data-map-filter="all">All</button><button data-map-filter="Active">Active</button><button data-map-filter="Planned">Planned</button><button data-map-filter="Completed">Close-out</button></div></header><div class="operations-map-layout"><div class="map-stage"><div id="operations-map" aria-label="Map of deployments in scope"></div><div class="map-legend"><span><i class="active"></i>Active</span><span><i class="planned"></i>Planned</span><span><i class="completed"></i>Close-out</span><span><i class="meeting"></i>Meeting point</span></div><button class="map-fit" data-map-fit title="Show all deployments">⌖ Fit all</button></div><aside class="map-detail" data-map-detail><div class="map-detail-empty"><span>⌖</span><strong>Select a deployment</strong><p>Choose a marker to inspect its site, schedule, coordinator, roster and readiness.</p></div></aside></div></section>`);
  const views=[...document.querySelectorAll('.manager-view')];
  const links=[...document.querySelectorAll('.manager-nav a[data-view]')];
  const title=document.querySelector('[data-page-title]');
  const shell=document.querySelector('.manager-shell');
  const peopleViews=new Set(['people','applications','application','volunteers','volunteer-record','members','member-record','active-member-record','recruitment']);
  const operationsViews=new Set(['operations','deployment-record']);
  const communicationViews=new Set(['communication']);
  const memberSummary=document.querySelector('#view-members .registry-summary');
  if(memberSummary){
    memberSummary.className='registry-summary-grid';
    memberSummary.innerHTML='<article><span class="people-stat-icon">M</span><p><small>Active memberships</small><strong>3,842</strong><em>In your assigned scope</em></p></article><article><span class="summary-glyph">A</span><p><small>Annual memberships</small><strong>3,214</strong><em>83.7% of active records</em></p></article><article><span class="summary-glyph">L</span><p><small>Life memberships</small><strong>428</strong><em>No renewal date</em></p></article><article><span class="summary-glyph">↻</span><p><small>Renewals approaching</small><strong>219</strong><em>Valid for 30 days or less</em></p></article>';
  }
  const membershipQueue=document.querySelector('[data-tab-panel="applications"][data-panel="membership"]');
  if(membershipQueue){
    membershipQueue.insertAdjacentHTML('afterbegin','<div class="toolbar"><input placeholder="Search member applicant or membership reference"><select><option>All stages</option><option>Proof review</option><option>County approval</option><option>National verification</option></select><select><option>All branches</option><option>Nairobi</option><option>Eastleigh</option><option>Lang\'ata</option></select><button class="secondary-btn" data-toast="Membership application filters applied.">Filter</button></div>');
  }
  const deploymentMapData=[
    {name:'Garissa Nutrition Outreach',ref:'DEP-2026-024',status:'Active',terms:'TOR-2026-036',geo:'Kenya / North Eastern / Garissa County',coordinator:'Jane Njeri',required:40,assigned:34,accepted:34,pending:0,leaders:4,briefed:31,safety:34,checkedIn:29,tasks:6,plannedStart:'25 Aug · 08:00',plannedEnd:'7 Sep · 18:00',briefing:'24 Aug · 16:00',checkIn:'25 Aug · 07:30',expectedReturn:'7 Sep · 20:00',siteName:'Garissa County Referral Hospital',siteAddress:'Hospital Road, Garissa',site:[-0.4569,39.6461],meetingName:'Garissa Branch Office',meetingAddress:'Kismayu Road, Garissa',meeting:[-0.4632,39.6407],contact:'Ahmed Noor',phone:'+254 722 410 118',travel:'Team transport departs the branch office after the safety briefing.'},
    {name:'Tana River Flood Response — Wave 3',ref:'DEP-2026-031',status:'Planned',terms:'TOR-2026-041 · v1.4',geo:'Kenya / Coast / Tana River County',coordinator:'Jane Njeri',required:30,assigned:30,accepted:21,pending:9,leaders:3,briefed:0,safety:12,checkedIn:0,tasks:0,plannedStart:'14 Sep · 06:00',plannedEnd:'25 Sep · 18:00',briefing:'13 Sep · 15:00',checkIn:'14 Sep · 05:30',expectedReturn:'25 Sep · 21:00',siteName:'Hola Sub-County Hospital',siteAddress:'Hola Town, Tana River County',site:[-1.4997,40.0301],meetingName:'Tana River Branch Office',meetingAddress:'Hola, near County offices',meeting:[-1.4971,40.0264],contact:'Fatuma Abdi',phone:'+254 711 330 207',travel:'Four-wheel-drive transport required beyond Hola after heavy rain.'},
    {name:'Nairobi Marathon First Aid',ref:'DEP-2026-034',status:'Planned',terms:'TOR-2026-043',geo:'Kenya / Nairobi County',coordinator:'Peter Kariuki',required:60,assigned:51,accepted:42,pending:9,leaders:6,briefed:0,safety:18,checkedIn:0,tasks:0,plannedStart:'21 Sep · 04:30',plannedEnd:'21 Sep · 15:00',briefing:'20 Sep · 14:00',checkIn:'21 Sep · 04:00',expectedReturn:'21 Sep · 16:00',siteName:'Nyayo National Stadium',siteAddress:'Uhuru Highway, Nairobi',site:[-1.3042,36.8249],meetingName:'Nairobi Branch Office',meetingAddress:'South C, Nairobi',meeting:[-1.3188,36.8342],contact:'Mary Wanjiru',phone:'+254 700 117 404',travel:'Teams move from the meeting point to assigned first-aid stations by shuttle.'},
    {name:'Kibera Fire Response',ref:'DEP-2026-019',status:'Completed',terms:'TOR-2026-029',geo:'Kenya / Nairobi County / Lang\'ata',coordinator:'Jane Njeri',required:20,assigned:19,accepted:19,pending:0,leaders:2,briefed:19,safety:19,checkedIn:19,tasks:3,plannedStart:'23 Aug · 18:00',plannedEnd:'27 Aug · 17:00',briefing:'23 Aug · 17:30',checkIn:'23 Aug · 18:00',expectedReturn:'27 Aug · 19:00',siteName:'Kibera DC Grounds',siteAddress:'Kibera Drive, Nairobi',site:[-1.3133,36.7892],meetingName:'Lang\'ata Branch Muster Point',meetingAddress:'Mbagathi Road, Nairobi',meeting:[-1.3067,36.8006],contact:'John Omondi',phone:'+254 733 208 119',travel:'Close-out complete on site; mission report and verified hours remain outstanding.'}
  ];
  const deploymentRecord=document.getElementById('view-deployment-record');
  if(deploymentRecord){
    deploymentRecord.innerHTML=`<header class="deployment-command-head"><div><a class="record-back" href="#operations">← Operations</a><div class="record-title-line"><span class="operation-state mobilising">Planned</span><small>DEP-2026-031</small></div><h2>Tana River Flood Response — Wave 3</h2><p>Kenya / Coast / Tana River County · 14–25 September 2026</p></div><div class="action-row"><button class="secondary-btn" data-toast="Deployment change request opened with the current values preserved.">Request change</button><button class="secondary-btn" data-toast="Invitation batch preview opened for 9 pending volunteers.">Send reminders</button><button class="primary-btn" data-toast="Operational briefing pack generated from the approved TOR and deployment record.">Briefing pack</button></div></header>
      <div class="deployment-alert"><span>!</span><div><strong>Readiness gate needs attention</strong><p>9 invitation responses and 18 safety acknowledgements remain before the 14 September check-in deadline.</p></div><button data-toast="Readiness exceptions opened.">Review exceptions →</button></div>
      <nav class="record-tabs" data-tab-group="deployment-record"><button class="active" data-tab="record-overview">Command view</button><button data-tab="record-assignments">Assignments <b>30</b></button><button data-tab="record-terms">TOR & resources</button><button data-tab="record-closeout">Close-out</button></nav>
      <div data-tab-panel="deployment-record" data-panel="record-overview">
        <div class="deployment-command-grid"><section class="panel deployment-record-map-card"><div class="panel-head"><div><h3>Places & movement</h3><p>Deployment point, meeting point and planned field movement</p></div><a href="https://www.openstreetmap.org/directions?route=-1.4971,40.0264;-1.4997,40.0301" target="_blank" rel="noreferrer">Open directions ↗</a></div><div class="deployment-record-map-wrap"><div id="deployment-record-map" aria-label="Deployment and meeting point map"></div><div class="map-route-key"><span><i class="site"></i>Deployment point</span><span><i class="meeting"></i>Meeting point</span><span><i class="route"></i>Planned movement</span></div></div><div class="place-cards"><article><span class="place-icon site">⌖</span><div><small>Deployment point</small><strong>Hola Sub-County Hospital</strong><p>Hola Town, Tana River County</p><em>-1.4997, 40.0301</em></div><a href="https://www.openstreetmap.org/?mlat=-1.4997&mlon=40.0301#map=16/-1.4997/40.0301" target="_blank" rel="noreferrer">↗</a></article><article><span class="place-icon meeting">M</span><div><small>Meeting point</small><strong>Tana River Branch Office</strong><p>Hola, near County offices</p><em>-1.4971, 40.0264</em></div><a href="https://www.openstreetmap.org/?mlat=-1.4971&mlon=40.0264#map=16/-1.4971/40.0264" target="_blank" rel="noreferrer">↗</a></article></div></section>
          <aside class="deployment-side-stack"><section class="panel readiness-command"><div class="panel-head"><div><h3>Mission readiness</h3><p>Assignment control fields</p></div><strong>70%</strong></div><div class="readiness-ring-row"><div class="readiness-ring" style="--progress:70"><span><b>21</b><small>of 30 ready</small></span></div><div class="readiness-gates"><div><span><i class="done"></i>TOR approved</span><b>Ready</b></div><div><span><i class="warn"></i>Responses</span><b>9 pending</b></div><div><span><i class="warn"></i>Safety</span><b>12 / 30</b></div><div><span><i></i>Briefing</span><b>0 / 30</b></div></div></div><button class="readiness-review" data-toast="Assignment readiness exceptions opened.">Review readiness gates →</button></section>
            <section class="panel contact-card"><div class="panel-head"><div><h3>Operational contacts</h3><p>Coordinator and local contact</p></div></div><article><span>JN</span><div><small>Coordinator</small><strong>Jane Njeri</strong><p>Deployment lead</p></div><button data-toast="Message composer opened for Jane Njeri.">✉</button></article><article><span>FA</span><div><small>Local contact</small><strong>Fatuma Abdi</strong><p>+254 711 330 207</p></div><a href="tel:+254711330207">☎</a></article><p class="travel-callout"><b>Travel note</b>Four-wheel-drive transport required beyond Hola after heavy rain.</p></section></aside></div>
        <div class="deployment-facts"><article><small>Volunteers required</small><strong>30</strong><span>3 team leaders</span></article><article><small>Accepted assignments</small><strong>21</strong><span class="negative">9 awaiting response</span></article><article><small>Safety acknowledged</small><strong>12</strong><span class="negative">18 outstanding</span></article><article><small>Briefing completed</small><strong>0</strong><span>Briefing on 13 Sep</span></article><article><small>Open tasks</small><strong>7</strong><span class="negative">2 high priority</span></article></div>
        <div class="deployment-lower-grid"><section class="panel"><div class="panel-head"><div><h3>Control schedule</h3><p>Dates and deadlines from the deployment record</p></div><button data-toast="Deployment schedule editor opened.">Edit schedule</button></div><div class="schedule-track"><article class="complete"><i>✓</i><div><small>Terms approved</small><strong>30 Aug · 14:42</strong><p>Approved TOR-2026-041 · v1.4</p></div></article><article><i>1</i><div><small>Briefing</small><strong>13 Sep · 15:00</strong><p>Tana River Branch Office</p></div></article><article><i>2</i><div><small>Check-in deadline</small><strong>14 Sep · 05:30</strong><p>30 assignments expected</p></div></article><article><i>3</i><div><small>Planned start</small><strong>14 Sep · 06:00</strong><p>Hola Sub-County Hospital</p></div></article><article><i>4</i><div><small>Expected return</small><strong>25 Sep · 21:00</strong><p>Return and check-out</p></div></article></div></section>
          <section class="panel mission-brief"><div class="panel-head"><div><h3>Approved mission brief</h3><p>Linked Terms of Reference</p></div><a href="#operations?section=terms">TOR-2026-041 ↗</a></div><div class="tor-state"><span>Approved</span><small>Version 1.4 · approved 30 Aug</small></div><dl><dt>Purpose</dt><dd>Support flood-affected households with health, relief and protection services across Hola and surrounding settlements.</dd><dt>Expected outputs</dt><dd>Household needs verified, referrals completed, relief distribution supported and daily situation reports submitted.</dd><dt>Approach</dt><dd>Three mobile teams led by designated assignment leaders, reporting to the deployment coordinator.</dd></dl><a class="record-section-link" href="#operations?section=terms">Read full scope, responsibilities and resources →</a></section></div>
        <section class="panel assignment-preview"><div class="panel-head"><div><h3>Assignment readiness</h3><p>Invitation, role, briefing, safety and check-in state</p></div><button data-toast="Full assignment register opened.">View all 30 →</button></div><div class="assignment-head"><span>Volunteer</span><span>Role</span><span>Invitation</span><span>Briefing</span><span>Safety</span><span>Check-in</span><span></span></div><article><span class="assignment-person"><i>AM</i><b>Alex Mwangi<small>KRC-V-2026-018</small></b></span><span>Community Health Volunteer</span><span class="status amber">Awaiting response</span><span class="readiness-na">Not started</span><span class="readiness-na">Pending</span><span class="readiness-na">—</span><button data-toast="Reminder sent to Alex Mwangi.">Remind</button></article><article><span class="assignment-person"><i>AH</i><b>Amina Hassan<small>KRC-V-2024-203</small></b></span><span>WASH Mobiliser · Leader</span><span class="status green">Accepted</span><span class="readiness-ok">Complete</span><span class="readiness-ok">Acknowledged</span><span class="readiness-na">—</span><button data-toast="Amina Hassan's assignment opened.">Open</button></article><article><span class="assignment-person"><i>PO</i><b>Peter Otieno<small>KRC-V-2025-318</small></b></span><span>Relief Assistant</span><span class="status green">Accepted</span><span class="readiness-na">Not started</span><span class="readiness-ok">Acknowledged</span><span class="readiness-na">—</span><button data-toast="Peter Otieno's assignment opened.">Open</button></article></section>
      </div>
      <div data-tab-panel="deployment-record" data-panel="record-assignments" hidden><div class="record-tab-head"><div><p class="eyebrow">DEP-2026-031 / Assignments</p><h3>Assignment control</h3><span>Invitation, leadership, readiness and attendance for every assigned volunteer.</span></div><div class="action-row"><button class="secondary-btn" data-toast="Bulk reminder preview opened for 9 pending invitations.">Remind pending</button><button class="primary-btn" data-toast="Volunteer matching opened for the remaining roles.">Add volunteers</button></div></div><div class="record-tab-metrics"><article><small>Assigned</small><strong>30</strong><span>30 required</span></article><article><small>Accepted</small><strong>21</strong><span>70% response rate</span></article><article class="attention"><small>Awaiting response</small><strong>9</strong><span>3 expire today</span></article><article><small>Team leaders</small><strong>3</strong><span>All confirmed</span></article></div><div class="toolbar"><input placeholder="Search volunteer, reference or role"><select><option>All invitation states</option><option>Awaiting response</option><option>Accepted</option><option>Declined</option><option>Expired</option></select><select><option>All readiness states</option><option>Briefing outstanding</option><option>Safety outstanding</option><option>Ready</option></select><button class="secondary-btn" data-toast="Assignment filters applied.">Filter</button></div><section class="panel data-panel"><table class="data-table record-assignment-table"><thead><tr><th>Volunteer</th><th>Assignment</th><th>Role</th><th>Invitation</th><th>Briefing</th><th>Safety</th><th>Attendance</th><th></th></tr></thead><tbody><tr><td><strong>Alex Mwangi</strong><small>KRC-V-2026-018</small></td><td>Field team 2<small>Member · Jane Njeri</small></td><td>Community Health Volunteer</td><td><span class="status amber">Awaiting response</span><small>Expires today · 17:00</small></td><td>Not started</td><td><span class="negative-text">Pending</span></td><td>Not checked in</td><td><button data-toast="Reminder sent to Alex Mwangi.">Remind</button></td></tr><tr><td><strong>Amina Hassan</strong><small>KRC-V-2024-203</small></td><td>Field team 1<small>Leader · Jane Njeri</small></td><td>WASH Mobiliser</td><td><span class="status green">Accepted</span><small>1 Sep · 10:18</small></td><td><span class="positive-text">Complete</span></td><td><span class="positive-text">Acknowledged</span></td><td>Not checked in</td><td><button data-toast="Amina Hassan's assignment opened.">Open</button></td></tr><tr><td><strong>Peter Otieno</strong><small>KRC-V-2025-318</small></td><td>Field team 3<small>Member · Jane Njeri</small></td><td>Relief Assistant</td><td><span class="status green">Accepted</span><small>31 Aug · 18:44</small></td><td>Not started</td><td><span class="positive-text">Acknowledged</span></td><td>Not checked in</td><td><button data-toast="Peter Otieno's assignment opened.">Open</button></td></tr></tbody></table></section></div>
      <div data-tab-panel="deployment-record" data-panel="record-terms" hidden><div class="record-tab-head"><div><p class="eyebrow">TOR-2026-041 / Version 1.4</p><h3>Approved scope & resources</h3><span>The frozen operational mandate linked to this deployment.</span></div><div class="action-row"><button class="secondary-btn" data-toast="Approved TOR document preview opened.">Preview document</button><button class="primary-btn" data-toast="TOR revision request opened from version 1.4.">Request revision</button></div></div><div class="tor-approval-banner"><span>✓</span><div><strong>Approved for deployment</strong><p>Approved 30 Aug 2026 at 14:42 · version 1.4 · approval record retained</p></div><b>Approved</b></div><div class="tor-detail-grid"><section class="panel tor-narrative"><div class="panel-head"><div><h3>Operational mandate</h3><p>Terms of Reference fields</p></div></div><article><small>Purpose</small><p>Support flood-affected households with health, relief and protection services across Hola and surrounding settlements.</p></article><article><small>Objectives</small><p>Verify priority needs, complete health and protection referrals, support accountable relief distribution and maintain daily situation reporting.</p></article><article><small>Expected outputs</small><p>600 households assessed · referral desk operating · three distributions supported · 12 daily situation reports submitted.</p></article><article><small>Approach & responsibilities</small><p>Three mobile teams led by assignment leaders. The coordinator owns daily briefings, safety control, partner liaison and consolidated reporting.</p></article><article><small>Required certifications</small><div class="cert-chips"><span>First aid</span><span>Protection basics</span><span>Safeguarding</span></div></article></section><section class="panel tor-resource-card"><div class="panel-head"><div><h3>Resource plan</h3><p>Linked TOR resource lines</p></div><button data-toast="Resource line editor opened.">Manage</button></div><div class="resource-row"><span>V</span><div><strong>Volunteers</strong><small>Field teams and leaders</small></div><b>30 people</b></div><div class="resource-row"><span>4×4</span><div><strong>Field transport</strong><small>Four-wheel-drive vehicles</small></div><b>4 units</b></div><div class="resource-row"><span>PPE</span><div><strong>Protective equipment</strong><small>Boots, vests and rain gear</small></div><b>30 kits</b></div><div class="resource-row"><span>COM</span><div><strong>Communications</strong><small>Handheld radios</small></div><b>8 units</b></div><div class="resource-row"><span>MED</span><div><strong>Medical supplies</strong><small>Mobile first-aid kits</small></div><b>3 kits</b></div></section></div></div>
      <div data-tab-panel="deployment-record" data-panel="record-closeout" hidden><div class="record-tab-head"><div><p class="eyebrow">DEP-2026-031 / Close-out</p><h3>Mission close-out</h3><span>Completion gates become actionable as deployment activity is recorded.</span></div><button class="secondary-btn" data-toast="Close-out requirements exported.">Export checklist</button></div><div class="closeout-lock"><span>⌛</span><div><strong>Close-out is not yet available</strong><p>This deployment is planned to end on 25 Sep 2026 at 18:00. The checklist shows what the record will require.</p></div><b>Planned</b></div><div class="closeout-grid"><section class="panel closeout-checklist"><div class="panel-head"><div><h3>Completion gates</h3><p>Required before status can become Closed Out</p></div><strong>0 / 6</strong></div><label><input type="checkbox" disabled><span><b>Record actual start and end</b><small>actual_start · actual_end</small></span><em>Waiting</em></label><label><input type="checkbox" disabled><span><b>All assignments checked out</b><small>checked_out_at · left_on</small></span><em>0 / 30</em></label><label><input type="checkbox" disabled><span><b>Verify volunteer hours</b><small>verified_hours on each assignment</small></span><em>0 / 30</em></label><label><input type="checkbox" disabled><span><b>Capture assignment outcomes</b><small>Participated, Partial Attendance, No Show, Withdrawn or Replaced</small></span><em>0 / 30</em></label><label><input type="checkbox" disabled><span><b>Upload mission report</b><small>mission_report · private file</small></span><em>Missing</em></label><label><input type="checkbox" disabled><span><b>Record lessons learned</b><small>lessons_learned</small></span><em>Missing</em></label></section><section class="panel closeout-preview"><div class="panel-head"><div><h3>Closure record</h3><p>Fields written at final close-out</p></div></div><dl><dt>Actual start</dt><dd>—</dd><dt>Actual end</dt><dd>—</dd><dt>Closed out on</dt><dd>—</dd><dt>Closed out by</dt><dd>—</dd><dt>Mission report</dt><dd class="negative-text">Not uploaded</dd></dl><div class="closeout-footer"><button disabled>Close deployment</button><p>The action unlocks only when all required gates are complete.</p></div></section></div></div>`;
  }
  let operationsMapInstance=null;
  let deploymentRecordMapInstance=null;
  let operationsMarkers=[];
  let selectedMeetingLayer=null;
  const markerTone={Active:'#18794e',Planned:'#155eef',Completed:'#946200'};
  function renderDeploymentDetail(item){
    const panel=document.querySelector('[data-map-detail]');
    if(!panel)return;
    const fill=Math.min(100,Math.round((item.accepted/item.required)*100));
    const brief=Math.min(100,Math.round((item.briefed/item.assigned)*100));
    panel.innerHTML=`<div class="map-detail-head"><div><span class="operation-state ${item.status==='Active'?'live':item.status==='Planned'?'mobilising':'closeout'}">${item.status}</span><small>${item.ref}</small></div><h3>${item.name}</h3><p>${item.geo}</p></div><div class="map-detail-actions"><a href="https://www.openstreetmap.org/?mlat=${item.site[0]}&mlon=${item.site[1]}#map=15/${item.site[0]}/${item.site[1]}" target="_blank" rel="noreferrer">Open map ↗</a><a href="https://www.openstreetmap.org/directions?route=;${item.site[0]},${item.site[1]}" target="_blank" rel="noreferrer">Directions ↗</a></div><div class="map-detail-scroll"><section><h4>Deployment</h4><dl><dt>Terms of Reference</dt><dd>${item.terms}</dd><dt>Coordinator</dt><dd>${item.coordinator}</dd><dt>Planned start</dt><dd>${item.plannedStart}</dd><dt>Planned end</dt><dd>${item.plannedEnd}</dd></dl></section><section><h4>Places</h4><dl><dt>Deployment point</dt><dd>${item.siteName}<small>${item.siteAddress}</small></dd><dt>Meeting point</dt><dd>${item.meetingName}<small>${item.meetingAddress}</small></dd><dt>Local contact</dt><dd>${item.contact}<small>${item.phone}</small></dd></dl></section><section><h4>Readiness</h4><div class="readiness-meter"><span><b>Accepted assignments</b><em>${item.accepted} / ${item.required}</em></span><i><b style="width:${fill}%"></b></i></div><div class="readiness-meter"><span><b>Briefing completed</b><em>${item.briefed} / ${item.assigned}</em></span><i><b style="width:${brief}%"></b></i></div><div class="readiness-mini"><span><small>Pending</small><b>${item.pending}</b></span><span><small>Leaders</small><b>${item.leaders}</b></span><span><small>Safety</small><b>${item.safety}</b></span><span><small>Checked in</small><b>${item.checkedIn}</b></span></div></section><section><h4>Control times</h4><div class="control-timeline"><div><i></i><span><small>Briefing</small><b>${item.briefing}</b></span></div><div><i></i><span><small>Check-in deadline</small><b>${item.checkIn}</b></span></div><div><i></i><span><small>Expected return</small><b>${item.expectedReturn}</b></span></div></div></section><section class="travel-note"><h4>Travel notes</h4><p>${item.travel}</p></section></div><a class="map-detail-open" href="#deployment-record">Open full deployment record →</a>`;
  }
  function selectDeployment(item,marker){
    renderDeploymentDetail(item);
    operationsMarkers.forEach(entry=>entry.marker.getElement()?.classList.toggle('selected',entry.item===item));
    if(selectedMeetingLayer){operationsMapInstance.removeLayer(selectedMeetingLayer);selectedMeetingLayer=null;}
    if(window.L&&operationsMapInstance){
      const meetingIcon=L.divIcon({className:'meeting-map-icon',html:'<span></span>',iconSize:[18,18],iconAnchor:[9,9]});
      const meetingMarker=L.marker(item.meeting,{icon:meetingIcon}).bindTooltip(`<b>Meeting point</b><br>${item.meetingName}`);
      const route=L.polyline([item.meeting,item.site],{color:'#155eef',weight:2,dashArray:'5 6',opacity:.8});
      selectedMeetingLayer=L.layerGroup([meetingMarker,route]).addTo(operationsMapInstance);
      operationsMapInstance.flyToBounds(L.latLngBounds([item.site,item.meeting]).pad(.8),{duration:.7,maxZoom:11});
    }
  }
  function initOperationsMap(){
    const target=document.getElementById('operations-map');
    if(!target)return;
    if(!window.L){target.innerHTML='<div class="map-unavailable"><strong>Map tiles unavailable</strong><span>The deployment list and coordinates remain available.</span></div>';return;}
    if(operationsMapInstance){operationsMapInstance.invalidateSize();return;}
    operationsMapInstance=L.map(target,{zoomControl:false,attributionControl:true,minZoom:5}).setView([-0.4,37.7],6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© OpenStreetMap'}).addTo(operationsMapInstance);
    L.control.zoom({position:'bottomright'}).addTo(operationsMapInstance);
    operationsMarkers=deploymentMapData.map(item=>{
      const icon=L.divIcon({className:'deployment-map-icon',html:`<span style="--pin:${markerTone[item.status]}"><i></i><b>${item.assigned}</b></span>`,iconSize:[42,42],iconAnchor:[21,21]});
      const marker=L.marker(item.site,{icon,title:item.name}).addTo(operationsMapInstance).bindTooltip(`<b>${item.name}</b><br>${item.status} · ${item.assigned} assigned`,{direction:'top',offset:[0,-18]});
      marker.on('click',()=>selectDeployment(item,marker));
      return{item,marker};
    });
    const fit=()=>operationsMapInstance.fitBounds(L.featureGroup(operationsMarkers.map(entry=>entry.marker)).getBounds().pad(.22),{maxZoom:7});
    fit();
    document.querySelector('[data-map-fit]')?.addEventListener('click',fit);
    document.querySelectorAll('[data-map-filter]').forEach(button=>button.addEventListener('click',()=>{
      const status=button.dataset.mapFilter;
      document.querySelectorAll('[data-map-filter]').forEach(item=>item.classList.toggle('active',item===button));
      operationsMarkers.forEach(entry=>{const show=status==='all'||entry.item.status===status;if(show&&!operationsMapInstance.hasLayer(entry.marker))entry.marker.addTo(operationsMapInstance);if(!show&&operationsMapInstance.hasLayer(entry.marker))operationsMapInstance.removeLayer(entry.marker);});
      const visible=operationsMarkers.filter(entry=>operationsMapInstance.hasLayer(entry.marker)).map(entry=>entry.marker);
      if(visible.length)operationsMapInstance.fitBounds(L.featureGroup(visible).getBounds().pad(.25),{maxZoom:8});
    }));
    selectDeployment(deploymentMapData[1],operationsMarkers[1].marker);
  }
  function initDeploymentRecordMap(){
    const target=document.getElementById('deployment-record-map');
    if(!target||!window.L)return;
    if(deploymentRecordMapInstance){deploymentRecordMapInstance.invalidateSize();return;}
    const item=deploymentMapData[1];
    deploymentRecordMapInstance=L.map(target,{zoomControl:false,attributionControl:true,scrollWheelZoom:false}).fitBounds(L.latLngBounds([item.site,item.meeting]).pad(.9));
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© OpenStreetMap'}).addTo(deploymentRecordMapInstance);
    L.control.zoom({position:'bottomright'}).addTo(deploymentRecordMapInstance);
    const siteIcon=L.divIcon({className:'record-site-marker',html:'<span>30</span>',iconSize:[46,46],iconAnchor:[23,23]});
    const meetingIcon=L.divIcon({className:'record-meeting-marker',html:'<span>M</span>',iconSize:[30,30],iconAnchor:[15,15]});
    L.marker(item.site,{icon:siteIcon}).addTo(deploymentRecordMapInstance).bindTooltip(`<b>Deployment point</b><br>${item.siteName}`);
    L.marker(item.meeting,{icon:meetingIcon}).addTo(deploymentRecordMapInstance).bindTooltip(`<b>Meeting point</b><br>${item.meetingName}`);
    L.polyline([item.meeting,item.site],{color:'#155eef',weight:3,dashArray:'7 7',opacity:.85}).addTo(deploymentRecordMapInstance);
  }
  function route(){
    const raw=(location.hash||'#overview').slice(1);
    const [id,query='']=raw.split('?');
    const params=new URLSearchParams(query);
    const view=document.getElementById('view-'+id)||document.getElementById('view-overview');
    views.forEach(v=>v.classList.toggle('active',v===view));
    const peopleFocused=peopleViews.has(view.dataset.view);
    const operationsFocused=operationsViews.has(view.dataset.view);
    const communicationFocused=communicationViews.has(view.dataset.view);
    const focused=peopleFocused||operationsFocused||communicationFocused;
    shell?.classList.toggle('people-focused',focused);
    const sectionNav=communicationFocused?'communication':operationsFocused?'operations':'people';
    document.querySelectorAll('[data-section-nav]').forEach(nav=>nav.hidden=nav.dataset.sectionNav!==sectionNav);
    links.forEach(a=>a.classList.toggle('active',peopleFocused?a.dataset.view==='people':operationsFocused?a.dataset.view==='operations':a.dataset.view===view.dataset.view));
    const tab=params.get('tab');
    if(tab){
      document.querySelectorAll('[data-tab-group="'+id+'"] [data-tab]').forEach(button=>button.classList.toggle('active',button.dataset.tab===tab));
      document.querySelectorAll('[data-tab-panel="'+id+'"]').forEach(panel=>panel.hidden=panel.dataset.panel!==tab);
    }
    if(id==='applications'){
      const membership=tab==='membership';
      view.querySelectorAll('[data-queue-tabs]').forEach(bar=>bar.hidden=bar.dataset.queueTabs!==(membership?'membership':'volunteer'));
      const basePanel=membership?'membership':'volunteer';
      view.querySelectorAll('[data-tab-panel="applications"]').forEach(panel=>panel.hidden=panel.dataset.panel!==basePanel);
      view.querySelectorAll('[data-queue-tabs] [data-tab]').forEach(button=>button.classList.toggle('active',button.dataset.tab===basePanel));
      const heading=view.querySelector('[data-application-heading]');
      const lead=view.querySelector('[data-application-lead]');
      if(heading) heading.textContent=membership?'Membership applications':'Volunteer applications';
      if(lead) lead.textContent=membership?'Review membership applications through their configured approval stages.':'Review volunteer applications through their configured approval stages.';
    }
    if(id==='recruitment'){
      const openings=tab==='openings';
      const basePanel=openings?'openings':'candidates';
      view.querySelectorAll('[data-recruitment-tabs]').forEach(bar=>bar.hidden=bar.dataset.recruitmentTabs!==basePanel);
      view.querySelectorAll('[data-tab-panel="recruitment"]').forEach(panel=>panel.hidden=panel.dataset.panel!==basePanel);
      view.querySelectorAll('[data-recruitment-tabs] [data-tab]').forEach(button=>button.classList.toggle('active',button.dataset.tab===basePanel));
      const heading=view.querySelector('[data-recruitment-heading]');
      const lead=view.querySelector('[data-recruitment-lead]');
      if(heading) heading.textContent=openings?'Job openings':'Job applicants';
      if(lead) lead.textContent=openings?'Manage positions currently open for applications in your scope.':'Review people who have applied to staff openings in your scope.';
    }
    if(id==='communication'){
      const communicationPanel=params.get('view')||'compose';
      const panelName=communicationPanel==='sent'?'history':communicationPanel;
      document.querySelectorAll('[data-communication-panel]').forEach(panel=>panel.hidden=panel.dataset.communicationPanel!==panelName);
      document.querySelectorAll('[data-communication-action]').forEach(action=>action.classList.toggle('active',action.dataset.communicationAction===communicationPanel));
    }
    if(id==='operations'){
      const section=params.get('section')||'overview';
      const operationTitles={overview:'Operations',terms:'Terms of Reference',new:'Create deployment',ongoing:'Ongoing deployments',past:'Past deployments',requests:'Deployment requests',documents:'Operations documents'};
      view.dataset.title=operationTitles[section]||'Operations';
      view.querySelectorAll('[data-operation-panel]').forEach(panel=>panel.hidden=panel.dataset.operationPanel!==section);
      document.querySelectorAll('[data-operation-view]').forEach(a=>a.classList.toggle('active',(a.dataset.operationView||'').split(' ').includes(section)));
      if(section==='overview')window.setTimeout(initOperationsMap,50);
    }else if(id==='deployment-record'){
      document.querySelectorAll('[data-operation-view]').forEach(a=>a.classList.toggle('active',(a.dataset.operationView||'').split(' ').includes('deployment-record')));
      window.setTimeout(initDeploymentRecordMap,50);
    }
    let peopleKey=id+(tab?'-'+tab:'');
    if(id==='application') peopleKey='application';
    if(id==='volunteer-record') peopleKey='volunteer-record';
    if(id==='member-record') peopleKey='member-record';
    if(id==='active-member-record') peopleKey='active-member-record';
    document.querySelectorAll('[data-people-view]').forEach(a=>{
      a.classList.toggle('active',(a.dataset.peopleView||'').split(' ').includes(peopleKey));
    });
    if(params.get('preview')==='person') window.setTimeout(()=>view.querySelector('.person-hover-trigger')?.focus(),0);
    if(title) title.textContent=view.dataset.title||'Manager workspace';
    window.scrollTo(0,0);
  }
  addEventListener('hashchange',route);route();
  document.querySelectorAll('[data-tab-group]').forEach(group=>{
    const buttons=[...group.querySelectorAll('[data-tab]')];
    buttons.forEach(btn=>btn.addEventListener('click',()=>{
      buttons.forEach(b=>b.classList.toggle('active',b===btn));
      const owner=group.dataset.tabGroup;
      document.querySelectorAll('[data-tab-panel="'+owner+'"]').forEach(p=>p.hidden=p.dataset.panel!==btn.dataset.tab);
    }));
  });
  const toast=document.querySelector('.toast');
  function say(message){if(!toast)return;toast.textContent=message;toast.classList.add('show');clearTimeout(window.__toast);window.__toast=setTimeout(()=>toast.classList.remove('show'),2800)}
  document.querySelectorAll('[data-toast]').forEach(el=>el.addEventListener('click',e=>{if(el.tagName==='A'&&el.getAttribute('href')==='#')e.preventDefault();say(el.dataset.toast)}));
  document.querySelectorAll('[data-modal]').forEach(el=>el.addEventListener('click',e=>{e.preventDefault();document.getElementById(el.dataset.modal)?.classList.add('open')}));
  document.querySelectorAll('[data-close-modal]').forEach(el=>el.addEventListener('click',()=>el.closest('.modal')?.classList.remove('open')));
  document.querySelectorAll('.modal').forEach(m=>m.addEventListener('click',e=>{if(e.target===m)m.classList.remove('open')}));
  document.querySelectorAll('[data-decision]').forEach(btn=>btn.addEventListener('click',()=>{
    const decision=btn.dataset.decision;
    const state=document.querySelector('[data-application-state]');
    if(state){state.textContent=decision==='approve'?'Approved':'Changes requested';state.className='status '+(decision==='approve'?'green':'amber')}
    say(decision==='approve'?'Application approved and applicant notified.':'Correction request sent to the applicant.');
  }));
  document.querySelector('.mobile-manager-menu')?.addEventListener('click',()=>document.querySelector('.manager-sidebar')?.classList.toggle('open'));
  document.querySelectorAll('.manager-nav a').forEach(a=>a.addEventListener('click',()=>document.querySelector('.manager-sidebar')?.classList.remove('open')));
  document.getElementById('manager-answer-button')?.addEventListener('click',()=>{
    const input=document.getElementById('manager-answer-input');
    const reply=input.value.trim();
    if(!reply){input.focus();say('Write an answer before sending it.');return}
    const entry=document.createElement('article');
    entry.className='manager-chat-entry from-manager';
    const avatar=document.createElement('span');avatar.textContent='JN';
    const bubble=document.createElement('div');
    const meta=document.createElement('small');meta.textContent='Jane Njeri · Answer · Now';
    const note=document.createElement('p');note.textContent=reply;
    bubble.append(meta,note);entry.append(avatar,bubble);
    document.getElementById('manager-task-thread').appendChild(entry);
    const state=document.querySelector('[data-open-question-state]');
    state.textContent='Clarification answered';state.className='status green';
    input.closest('.manager-answer-box').classList.add('answered');
    say('Answer added to the task, open question cleared and Alex notified.');
  });
})();

(function initCommunicationConcept(){
  const view=document.getElementById('view-communication');
  if(!view)return;

  const tabs=[...view.querySelectorAll('[data-communication-tab]')];
  const panels=[...view.querySelectorAll('[data-communication-panel]')];
  tabs.forEach(tab=>tab.addEventListener('click',()=>{
    tabs.forEach(item=>item.classList.toggle('active',item===tab));
    panels.forEach(panel=>panel.hidden=panel.dataset.communicationPanel!==tab.dataset.communicationTab);
  }));

  const recipientChecks=[...view.querySelectorAll('[data-recipient-check]')];
  const selectAll=view.querySelector('[data-select-all-recipients]');
  const updateSelection=()=>{
    const selected=recipientChecks.filter(input=>input.checked).length;
    view.querySelectorAll('[data-selected-count],[data-send-selected-count]').forEach(node=>node.textContent=selected);
    const previewSelected=view.querySelector('[data-preview-selected]');
    if(previewSelected)previewSelected.textContent=selected;
    if(selectAll){selectAll.checked=selected===recipientChecks.length;selectAll.indeterminate=selected>0&&selected<recipientChecks.length}
  };
  selectAll?.addEventListener('change',()=>{recipientChecks.forEach(input=>input.checked=selectAll.checked);updateSelection()});
  recipientChecks.forEach(input=>input.addEventListener('change',updateSelection));

  const search=view.querySelector('[data-recipient-search]');
  const audienceType=view.querySelector('[data-audience-type]');
  const filterRecipients=()=>{
    const query=search.value.trim().toLowerCase();
    const type=audienceType?.value||'everyone';
    view.querySelectorAll('[data-recipient-row]').forEach(row=>{
      const matchesSearch=row.textContent.toLowerCase().includes(query);
      const matchesType=type==='everyone'||(row.dataset.recipientType||'').split(' ').includes(type);
      row.hidden=!(matchesSearch&&matchesType);
    });
  };
  search?.addEventListener('input',filterRecipients);
  audienceType?.addEventListener('change',()=>{
    view.querySelectorAll('[data-audience-kind]').forEach(group=>group.hidden=group.dataset.audienceKind!==audienceType.value);
    filterRecipients();
  });
  view.querySelector('[data-clear-communication-filters]')?.addEventListener('click',()=>{
    view.querySelectorAll('[data-audience-filter]').forEach(select=>select.selectedIndex=0);
    if(search){search.value='';search.dispatchEvent(new Event('input'))}
  });

  const channelChecks=[...document.querySelectorAll('[data-section-nav="communication"] [data-channel-check]')];
  const channelCopy={
    notification:{name:'In-app notification',short:'In app',heading:'Compose notification',preview:'Notification preview',reach:'1,248',help:'Write the title and message people will receive in the portal.',note:'Appears in the portal for people with a login.',delivery:'In-app notifications publish immediately after review.',review:'Review notification',icon:'◈',className:'portal'},
    email:{name:'Email',short:'Email',heading:'Compose email',preview:'Email preview',reach:'1,183',help:'Write the subject and email body people with an address will receive.',note:'Shows the branded email delivered to each valid address.',delivery:'Email is sent immediately to selected people with an address on file.',review:'Review email',icon:'✉',className:'email'},
    sms:{name:'SMS campaign',short:'SMS',heading:'Compose SMS',preview:'SMS preview',reach:'1,071',help:'Name the campaign and write the text message. It will be filed for approval.',note:'Shows the message as a recipient reads it in their SMS thread.',delivery:'SMS is filed as a draft campaign; the provider releases it after approval.',review:'Review SMS draft',icon:'SMS',className:'sms'},
    whatsapp:{name:'WhatsApp broadcast',short:'WhatsApp',heading:'Compose WhatsApp',preview:'WhatsApp preview',reach:'1,042',help:'Name the broadcast and write the message. It will be filed for approval.',note:'Includes the opt-out line appended by the server.',delivery:'WhatsApp is filed as a draft broadcast and paced after approval.',review:'Review broadcast',icon:'WA',className:'whatsapp'}
  };
  const updateChannels=()=>{
    const current=channelChecks.find(input=>input.checked)||channelChecks[0];
    const copy=channelCopy[current.value];
    channelChecks.forEach(input=>{
      input.closest('label')?.classList.toggle('selected',input.checked);
      const detail=view.querySelector('[data-channel-detail="'+input.value+'"]');
      if(detail)detail.hidden=!input.checked;
    });
    view.querySelector('[data-channel-count]').textContent=copy.short;
    const currentChannel=view.querySelector('[data-current-channel]');
    const currentChannelNote=view.querySelector('[data-current-channel-note]');
    if(currentChannel)currentChannel.textContent=copy.name;
    if(currentChannelNote)currentChannelNote.textContent=copy.note;
    view.querySelector('[data-compose-heading]').textContent=copy.heading;
    view.querySelector('[data-compose-help]').textContent=copy.help;
    view.querySelector('[data-compose-medium]').textContent=copy.short;
    view.querySelector('[data-delivery-explanation]').textContent=copy.delivery;
    view.querySelector('[data-review-label]').textContent=copy.review;
    view.querySelector('[data-preview-heading]').textContent=copy.preview;
    view.querySelector('[data-preview-reach]').textContent=copy.reach;
    view.querySelector('[data-preview-medium]').textContent=copy.name;
    view.querySelector('[data-preview-note]').textContent=copy.note;
    view.querySelectorAll('[data-message-preview]').forEach(preview=>preview.hidden=preview.dataset.messagePreview!==current.value);
    const icon=view.querySelector('[data-compose-icon]');
    icon.textContent=copy.icon;icon.className='comm-icon '+copy.className;
    const composeLabel=document.querySelector('[data-subnav-compose]');
    const sentLabel=document.querySelector('[data-subnav-sent]');
    if(composeLabel)composeLabel.textContent=copy.heading;
    if(sentLabel)sentLabel.textContent=current.value==='notification'?'Sent notifications':'Sent '+copy.short;
    const whatsappChannel=document.querySelector('[data-whatsapp-channel]');
    if(whatsappChannel)whatsappChannel.hidden=current.value!=='whatsapp';
  };
  channelChecks.forEach(input=>input.addEventListener('change',updateChannels));
  updateChannels();

  view.querySelectorAll('[data-schedule-mode]').forEach(select=>select.addEventListener('change',()=>{
    const fields=view.querySelector('[data-schedule-fields="'+select.dataset.scheduleMode+'"]');
    if(fields)fields.hidden=select.value!=='later';
  }));
  const smsMessage=view.querySelector('[data-sms-message]');
  const titleInput=view.querySelector('[data-message-title]');
  const bodyInput=view.querySelector('[data-message-body]');
  const waMessage=view.querySelector('[data-wa-message]');
  const updatePreviewText=()=>{
    const title=titleInput?.value.trim()||'Your subject';
    const body=bodyInput?.value.trim()||'Your message preview appears here.';
    view.querySelectorAll('[data-preview-title]').forEach(node=>node.textContent=title);
    view.querySelectorAll('[data-preview-body]').forEach(node=>node.textContent=body);
    const smsPreview=view.querySelector('[data-preview-sms]');
    const waPreview=view.querySelector('[data-preview-wa]');
    if(smsPreview)smsPreview.textContent=smsMessage?.value.trim()||body;
    if(waPreview)waPreview.textContent=waMessage?.value.trim()||body;
  };
  [titleInput,bodyInput,smsMessage,waMessage].forEach(input=>input?.addEventListener('input',updatePreviewText));
  smsMessage?.addEventListener('input',()=>{view.querySelector('[data-sms-count]').textContent=smsMessage.value.length});
  updatePreviewText();

  const historySearch=view.querySelector('[data-history-search]');
  const historyFilter=view.querySelector('[data-history-filter]');
  const filterHistory=()=>{
    const query=(historySearch?.value||'').trim().toLowerCase();
    const channel=historyFilter?.value||'all';
    view.querySelectorAll('[data-history-row]').forEach(row=>{
      const matchesText=row.textContent.toLowerCase().includes(query);
      const matchesChannel=channel==='all'||(row.dataset.historyChannel||'').split(' ').includes(channel);
      row.hidden=!(matchesText&&matchesChannel);
    });
  };
  historySearch?.addEventListener('input',filterHistory);
  historyFilter?.addEventListener('change',filterHistory);
  view.querySelector('[data-select-all-history]')?.addEventListener('change',event=>{
    view.querySelectorAll('[data-history-row]:not([hidden]) input[type="checkbox"]').forEach(input=>input.checked=event.target.checked);
  });
})();
