/* Paste this entire file into the Frappe Desk browser console as Administrator.
 * Rerunnable: records are matched by stable keys/titles/emails before insertion.
 * Demo people are fictional and use the reserved .invalid email domain.
 */
(async () => {
  const DRY_RUN = true; // Change to false only after reviewing CONFIG and DATA.
  const CONFIG = {
    company: "Tanzania Red Cross Society",
    national: "GEO-00001",
    coordinator: "Administrator",
    imageBase: "https://images.unsplash.com",
  };

  const results = { created: [], updated: [], skipped: [], errors: [] };
  const call = async (method, args = {}) => (await frappe.call({ method, args })).message;
  const list = async (doctype, fields = ["name"], filters = [], limit = 1000) =>
    (await call("frappe.client.get_list", { doctype, fields, filters, limit_page_length: limit })) || [];
  const clean = (value) => Object.fromEntries(Object.entries(value).filter(([, v]) => v !== undefined));
  const find = async (doctype, filters) => (await list(doctype, ["name"], filters, 1))[0]?.name;
  const upsert = async (doctype, match, values, label) => {
    try {
      const name = await find(doctype, Object.entries(match).map(([k, v]) => [k, "=", v]));
      if (DRY_RUN) {
        results.skipped.push(`DRY RUN ${name ? "update" : "create"}: ${label}`);
        return name || `DRY-RUN:${label}`;
      }
      if (name) {
        const doc = await call("frappe.client.get", { doctype, name });
        const saved = await call("frappe.client.save", { doc: clean({ ...doc, ...values, doctype, name }) });
        results.updated.push(`${doctype}: ${saved.name}`);
        return saved.name;
      }
      const inserted = await call("frappe.client.insert", { doc: clean({ doctype, ...values }) });
      results.created.push(`${doctype}: ${inserted.name}`);
      return inserted.name;
    } catch (error) {
      results.errors.push({ label, doctype, error: error?.message || String(error) });
      console.error(`Failed: ${label}`, error);
      return null;
    }
  };
  const setValue = async (doctype, name, fieldname, value) => {
    if (DRY_RUN || !name || name.startsWith("DRY-RUN:")) return;
    try {
      await call("frappe.client.set_value", { doctype, name, fieldname, value });
    } catch (error) {
      results.errors.push({ label: `${doctype} ${name}.${fieldname}`, error: error?.message || String(error) });
    }
  };
  const addDays = (days) => {
    const date = new Date(); date.setDate(date.getDate() + days);
    return date.toISOString().slice(0, 10);
  };

  const branches = [
    ["Arusha", "Arusha Branch", "Sokoine Road, Arusha", -3.3869, 36.6830],
    ["GEO-00112", "Dar es Salaam Branch", "Upanga, Dar es Salaam", -6.7924, 39.2083],
    ["GEO-00147", "Dodoma Branch", "Area C, Dodoma", -6.1630, 35.7516],
    ["GEO-00333", "Kigoma Branch", "Ujiji Road, Kigoma", -4.8833, 29.6333],
    ["GEO-00477", "Mbeya Branch", "Sisimba, Mbeya", -8.9094, 33.4608],
    ["GEO-00487", "Mjini Magharibi Branch", "Zanzibar City, Unguja", -6.1659, 39.2026],
    ["GEO-00509", "Morogoro Branch", "Boma Road, Morogoro", -6.8278, 37.6591],
    ["GEO-00599", "Mwanza Branch", "Pamba Road, Mwanza", -2.5164, 32.9175],
    ["GEO-00682", "Pwani Branch", "Kibaha Town, Pwani", -6.7667, 38.9167],
    ["GEO-00711", "Ruvuma Branch", "Songea Town, Ruvuma", -10.6833, 35.6500],
    ["GEO-00761", "Tabora Branch", "Market Street, Tabora", -5.0162, 32.8266],
    ["GEO-00784", "Tanga Branch", "Independence Avenue, Tanga", -5.0689, 39.0988],
  ];
  for (const [geo_node, location_name, address, latitude, longitude] of branches) {
    await upsert("VMMS Branch Location", { geo_node }, {
      naming_series: "BRLOC-.#####", location_name, geo_node, is_published: 1,
      address, latitude, longitude, phone: "+255 22 215 0330",
      email: "info@trcs.or.tz", opening_hours: "Mon–Fri, 08:00–16:30",
      notes: "Volunteer enquiries, first-aid information and community-service coordination.",
    }, location_name);
    // The public branch locator reads VMMS Branch Location, while the
    // deployment-area map reads the canonical Geo Node point.
    await upsert("Geo Node", { name: geo_node }, { latitude, longitude }, `${location_name} map point`);
  }

  const membershipTypes = [
    ["youth", "Youth Member", 5000, 365, "For young people aged 18–25 building humanitarian leadership and service experience.", ["Branch activities", "Youth leadership forums", "First-aid learning opportunities"]],
    ["annual", "Annual Member", 20000, 365, "Annual membership for people supporting humanitarian action through their local branch.", ["Member assemblies", "Branch programme updates", "Priority training notices"]],
    ["professional", "Professional Member", 50000, 365, "For professionals contributing technical knowledge, mentoring and specialist response capacity.", ["Technical working groups", "Professional networking", "Specialist deployment alerts"]],
    ["lifetime", "Lifetime Member", 500000, 0, "A lifelong commitment to the Fundamental Principles and work of Tanzania Red Cross Society.", ["Lifetime recognition", "National member briefings", "Invitations to major society events"]],
  ];
  for (const [key, name, fee, days, description, benefits] of membershipTypes) {
    await upsert("VMMS Membership Type", { membership_type_key: key }, {
      membership_type_key: key, membership_type_name: name, is_active: 1, description,
      fee_amount: fee, fee_currency: "TZS", is_lifetime: days === 0 ? 1 : 0,
      duration_days: days, approval_mode: "routed",
      approval_note: "Applications are reviewed by the applicant’s serving branch.",
      benefits: benefits.map((benefit_name, i) => ({ benefit_key: `${key}_${i + 1}`, benefit_name, is_active: 1 })),
    }, name);
  }

  const announcementTypes = [
    ["Community Update", "News from humanitarian programmes and local branches."],
    ["Training", "Learning, preparedness and certification notices."],
    ["Emergency Notice", "Time-sensitive preparedness and response information."],
    ["Member Notice", "Updates for members of Tanzania Red Cross Society."],
  ];
  for (const [name, description] of announcementTypes)
    await upsert("VMMS Announcement Type", { name }, { name, enabled: 1, description }, name);

  const skills = [
    ["public_health", "Public Health", "Community health promotion, surveillance and referral."],
    ["psychosocial_support", "Psychosocial Support", "Safe, supportive listening and basic psychosocial assistance."],
    ["community_engagement", "Community Engagement", "Participatory communication and accountable engagement."],
    ["data_collection", "Data Collection", "Responsible field data collection and reporting."],
    ["water_sanitation", "Water, Sanitation and Hygiene", "Community WASH promotion and monitoring."],
    ["search_rescue", "Search and Rescue", "Trained support to coordinated search-and-rescue operations."],
  ];
  for (const [skill_key, skill_name, description] of skills)
    await upsert("VMMS Skill", { skill_key }, { skill_key, skill_name, description, is_active: 1 }, skill_name);

  const people = [
    ["Asha", "Mwakalinga", "Female", "GEO-00113", "1995-04-12"],
    ["Baraka", "Msuya", "Male", "GEO-00005", "1992-11-03"],
    ["Neema", "Kessy", "Female", "GEO-00150", "1998-07-22"],
    ["Juma", "Mhando", "Male", "GEO-00601", "1990-02-16"],
    ["Rehema", "Mwinuka", "Female", "GEO-00479", "1996-09-08"],
    ["Hassan", "Said", "Male", "GEO-00488", "1993-05-19"],
    ["Zawadi", "Kimaro", "Female", "GEO-00511", "1999-12-01"],
    ["Emmanuel", "Magesa", "Male", "GEO-00785", "1989-08-27"],
    ["Upendo", "Mrema", "Female", "GEO-00685", "1997-03-14"],
    ["Kelvin", "Lusajo", "Male", "GEO-00334", "1994-06-30"],
    ["Janeth", "Mushi", "Female", "GEO-00762", "1991-10-11"],
    ["Daudi", "Mbise", "Male", "GEO-00714", "1988-01-25"],
  ];
  const personRecords = [];
  for (let i = 0; i < people.length; i++) {
    const [first, last, gender, geo, dob] = people[i];
    const email = `demo.${first}.${last}@example.invalid`.toLowerCase();
    const profile = await upsert("Red Profile", { email }, {
      first_name: first, last_name: last, email, phone: `+255 700 10${String(i + 1).padStart(2, "0")}`,
      gender, date_of_birth: dob, country_of_citizenship: "Tanzania",
      country_of_residence: "Tanzania", citizenship_status: "Citizen",
      residency_type: "Local", home_geo_node: geo,
    }, `${first} ${last}`);
    const volunteer = await upsert("VMMS Volunteer", { red_profile: profile }, {
      naming_series: "VOL-.#####", red_profile: profile, home_geo_node: geo,
      notes: "Fictional demonstration profile created for the TRCS portal presentation.",
    }, `Volunteer ${first} ${last}`);
    const member = i < 10 ? await upsert("VMMS Member", { red_profile: profile }, {
      naming_series: "MEM-.#####", red_profile: profile,
      notes: "Fictional demonstration member created for the TRCS portal presentation.",
    }, `Member ${first} ${last}`) : null;
    if (member) await upsert("VMMS Membership", { member, geo_node: geo }, {
      naming_series: "MSHIP-.#####", member,
      membership_type: ["annual", "youth", "professional"][i % 3], geo_node: geo,
      membership_source: "Gateway",
      applicant_first_name: first, applicant_last_name: last, applicant_gender: gender, applicant_date_of_birth: dob,
    }, `Membership ${first} ${last}`);
    await setValue("VMMS Volunteer", volunteer, "status", "Active");
    await setValue("VMMS Member", member, "status", "Active");
    personRecords.push({ first, last, geo, profile, volunteer, member });
  }

  const stories = [
    ["Community first-aid teams strengthen market-day safety", "Community Update", "GEO-00112", "volunteers", "important", "In Kariakoo and neighbouring wards, trained volunteers have worked with traders, transport groups and local leaders to improve first-aid readiness on busy market days. The teams mapped access routes, refreshed referral contacts and demonstrated practical responses to bleeding, burns and fainting. The activity is part of a wider effort to place simple lifesaving skills closer to where people live and work."],
    ["Youth volunteers lead climate preparedness conversations", "Community Update", "GEO-00599", "everyone", "routine", "Young volunteers around Mwanza have been holding small community conversations on extreme heat, strong winds and safe action near the lakeshore. Sessions combine local knowledge with early-warning messages and encourage families to agree on meeting points, protect important documents and check on neighbours who may need additional help."],
    ["New volunteer induction dates announced", "Training", "GEO-00147", "volunteers", "routine", "The Dodoma Branch will hold a two-day induction covering the Fundamental Principles, safeguarding, volunteer conduct, community engagement and safe referral. New and returning volunteers should confirm their availability through the portal and arrive with identification and a notebook."],
    ["Preparedness teams monitor seasonal rainfall", "Emergency Notice", "GEO-00509", "everyone", "important", "Branch preparedness teams are monitoring forecasts and community reports during the seasonal rains. Residents are encouraged to keep drainage paths clear, avoid crossing moving floodwater and follow official local guidance. Volunteers should not self-deploy; coordinators will communicate verified assignments through the portal."],
    ["Member dialogue focuses on accountable local service", "Member Notice", "Arusha", "members", "routine", "Members from local units met to discuss how branch plans can better reflect community priorities. The dialogue highlighted transparent feedback, responsible use of resources, youth participation and regular reporting back to the communities served."],
    ["Mobile health outreach connects families to referral services", "Community Update", "GEO-00477", "everyone", "routine", "Volunteers supporting a mobile outreach in Mbeya helped organise safe queues, share health information and guide families to appropriate referral services. Community leaders supported mobilisation, while the team recorded recurring questions to improve future sessions."],
  ];
  for (let i = 0; i < stories.length; i++) {
    const [title, announcement_type, geo_node, audience, urgency, body] = stories[i];
    await upsert("VMMS Announcement", { title }, {
      naming_series: "ANN-.#####", title, announcement_type, geo_node, audience, urgency,
      summary: body.slice(0, 155) + "…", body, status: "Published",
      link_label: i % 2 ? "View opportunities" : "Read the full update",
      link_href: i % 2 ? "/portal/opportunities" : "/portal/stories",
      expires_on: addDays(120), also_email: 0,
    }, title);
  }

  await upsert("Event Host", { name: "Tanzania Red Cross Society" }, {
    name: "Tanzania Red Cross Society", country: "Tanzania", by_line: "Humanity in Action",
    address: "Dar es Salaam, Tanzania", about: "<p>Tanzania Red Cross Society brings volunteers, members and communities together for principled humanitarian action.</p>",
  }, "TRCS event host");
  const venues = [
    ["TRCS Dar es Salaam Training Centre", "Upanga, Dar es Salaam"],
    ["TRCS Dodoma Branch Hall", "Area C, Dodoma"],
    ["TRCS Mwanza Branch Grounds", "Pamba Road, Mwanza"],
    ["TRCS Arusha Branch Hall", "Sokoine Road, Arusha"],
  ];
  for (const [name, address] of venues) await upsert("Event Venue", { name }, { name, address, type: "Open Street Map" }, name);

  const events = [
    ["Community First Aid Open Day", "Local", "TRCS Dar es Salaam Training Centre", "GEO-00112", 12, "09:00:00", "15:30:00", "Practical demonstrations, preparedness advice and conversations with local first-aid volunteers."],
    ["Youth Humanitarian Leadership Forum", "Conferences", "TRCS Dodoma Branch Hall", "GEO-00147", 20, "08:30:00", "16:00:00", "A participatory forum for young people exploring humanitarian principles, leadership and community service."],
    ["Lake Zone Climate Preparedness Dialogue", "Meetups", "TRCS Mwanza Branch Grounds", "GEO-00599", 28, "10:00:00", "14:00:00", "Community leaders and volunteers discuss practical preparedness for weather-related risks around the Lake Zone."],
    ["Volunteer Safeguarding Refresher", "Local", "TRCS Arusha Branch Hall", "Arusha", 36, "09:00:00", "13:00:00", "A refresher on safe conduct, reporting concerns, confidentiality and respectful community engagement."],
    ["Membership Orientation Webinar", "Webinars", null, CONFIG.national, 44, "18:00:00", "19:30:00", "An online introduction to membership, branch participation and the Fundamental Principles."],
    ["World First Aid Day Community Session", "Local", "TRCS Dar es Salaam Training Centre", "GEO-00112", 58, "09:00:00", "16:00:00", "A public learning day focused on simple actions that can preserve life until professional help arrives."],
  ];
  for (let i = 0; i < events.length; i++) {
    const [title, category, venue, geo_node, days, start_time, end_time, short_description] = events[i];
    await upsert("Buzz Event", { title }, {
      title, category, host: "Tanzania Red Cross Society", venue,
      medium: venue ? "In Person" : "Online", free_event: 1,
      start_date: addDays(days), end_date: addDays(days), start_time, end_time,
      time_zone: "Africa/Dar_es_Salaam", short_description,
      about: `<h2>${title}</h2><p>${short_description}</p><p>Participants will meet TRCS volunteers, learn practical approaches and receive clear information about the next steps for becoming involved. The programme is inclusive, free to attend and designed around respectful participation.</p><h3>What to bring</h3><p>Bring a notebook, drinking water and any accessibility information the organisers should know.</p>`,
      is_published: 1, route: `trcs-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`,
      geo_node, allow_guest_booking: 1, guest_verification_method: "Email OTP",
      card_image: `${CONFIG.imageBase}/photo-1593113598332-cd288d649433?auto=format&fit=crop&w=1200&q=80`,
      banner_image: `${CONFIG.imageBase}/photo-1559027615-cd4628902d4a?auto=format&fit=crop&w=1600&q=80`,
    }, title);
  }

  const openings = [
    ["Community First Aid Volunteer", "Associate", "Operations - TRCS", "GEO-00112", 18, "Support public demonstrations, preparedness sessions and referral information under a trained team lead."],
    ["Youth Engagement Volunteer", "Associate", "Human Resources - TRCS", "GEO-00147", 10, "Help organise youth forums, maintain participant communication and gather structured feedback."],
    ["Emergency Logistics Volunteer", "Administrative Assistant", "Dispatch - TRCS", "GEO-00599", 8, "Support stock counts, loading plans, waybills and accountable movement of relief items."],
    ["Community Health Promotion Volunteer", "Associate", "Operations - TRCS", "GEO-00477", 20, "Share approved health messages, support mobilisation and guide community members toward appropriate services."],
    ["Information Management Volunteer", "Analyst", "Research & Development - TRCS", "GEO-00509", 6, "Clean field data, maintain simple dashboards and support timely situation reporting."],
    ["Psychosocial Support Volunteer", "Consultant", "Operations - TRCS", "GEO-00784", 12, "Provide safe supportive listening and referrals under supervision during community activities."],
  ];
  for (const [job_title, designation, department, vmms_geo_node, vacancies, purpose] of openings) {
    await upsert("Job Opening", { job_title, company: CONFIG.company }, {
      job_title, designation, company: CONFIG.company, department,
      employment_type: "Part-time", status: "Open", publish: 1,
      posted_on: new Date().toISOString().slice(0, 19).replace("T", " "), closes_on: addDays(45),
      route: `volunteer-${job_title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`,
      description: `<h2>${job_title}</h2><p>${purpose}</p><h3>What you will do</h3><ul><li>Work through the assigned branch and designated team lead.</li><li>Follow safeguarding, security and data-protection requirements.</li><li>Record activities accurately and raise concerns promptly.</li></ul><h3>Who should apply</h3><p>Reliable volunteers who respect humanitarian principles, communicate well and can commit to the advertised dates.</p>`,
      vmms_purpose: "Volunteer", vmms_geo_node, vmms_available_from: addDays(50), vmms_available_to: addDays(140),
      vacancies, currency: "TZS", prevent_duplicate_applicant: 1,
    }, job_title);
  }

  const tors = [
    ["trcs_demo_flood_preparedness", "Seasonal Flood Preparedness and Community Readiness", "GEO-00509", "Strengthen practical readiness in flood-prone communities before peak seasonal rainfall.", 55, 60, "Morogoro Flood Preparedness Field Mission", "Kihonda and surrounding wards, Morogoro", -6.8278, 37.6591],
    ["trcs_demo_first_aid_outreach", "Community First Aid Outreach Mission", "GEO-00112", "Bring practical first-aid learning and referral information closer to high-footfall communities.", 70, 73, "Dar es Salaam Community First Aid Outreach", "Kariakoo and Ilala, Dar es Salaam", -6.8161, 39.2804],
    ["trcs_demo_lake_safety", "Lake Zone Community Safety Assessment", "GEO-00599", "Understand priority risks and strengthen locally owned safety actions in lakeshore communities.", 85, 90, "Mwanza Lakeshore Safety Mission", "Ilemela lakeshore communities, Mwanza", -2.4908, 32.8994],
  ];
  for (const [tor_key, tor_name, geo_scope, purpose, start, end, deploymentName, site, latitude, longitude] of tors) {
    const tor = await upsert("VMMS Terms of Reference", { tor_key }, {
      tor_key, tor_name, geo_scope, is_active: 1, approval_mode: "direct", purpose,
      expected_start_date: `${addDays(start)} 08:00:00`, expected_end_date: `${addDays(end)} 17:00:00`,
      default_duration_days: end - start + 1,
      mission_background: `<p>Tanzania Red Cross Society is undertaking this mission as part of its branch-led preparedness and community resilience work. The activity will be coordinated with local authorities and community leaders, use verified information and follow safeguarding and security requirements.</p><p>The team will listen to affected communities, document practical priorities and leave clear referral and feedback pathways.</p>`,
      stakeholders: [
        { designation: "TRCS Branch Coordinator", full_name: "Branch Coordination Team", email: "info@trcs.or.tz" },
        { designation: "Local Government Focal Person", full_name: "Local authority representative" },
        { designation: "Community Representative", full_name: "Community leadership representative" },
      ],
      objectives: [
        { objective: purpose },
        { objective: "Engage communities safely and document priority needs, capacities and feedback." },
        { objective: "Agree on practical follow-up actions, owners and reporting dates with local stakeholders." },
      ],
      expected_outputs: [
        { output: "A concise field situation and activity report with disaggregated participation figures." },
        { output: "A verified action tracker showing responsibilities, deadlines and referral pathways." },
        { output: "Community feedback themes and recommendations for the responsible branch." },
      ],
      approach_methods: [
        { methodology: "community_mobilisation", notes: "Mobilisation through branch volunteers and recognised local leaders." },
        { methodology: "key_informant_interview", notes: "Short structured interviews with service and community focal persons." },
        { methodology: "direct_service", notes: "Safe delivery of approved information and practical assistance." },
      ],
      itinerary: [
        { activity_date: addDays(start), activity_time: "08:30:00", activity: "Team briefing, safeguarding check and stakeholder introductions", person_responsible: "Mission Coordinator" },
        { activity_date: addDays(start + 1), activity_time: "09:00:00", activity: "Community engagement and field activities", person_responsible: "Field Team Leads" },
        { activity_date: addDays(end), activity_time: "15:00:00", activity: "Debrief, feedback validation and action planning", person_responsible: "Mission Coordinator" },
      ],
      resources: [
        { resource: "First-aid and visibility materials", description: "Branch-issued materials for safe field work", needed_on: addDays(start), quantity: 12, unit: "Nos", currency: "TZS", unit_cost: 35000, funding_status: "Committed" },
        { resource: "Local transport", description: "Team movement between agreed field sites", needed_on: addDays(start), quantity: end - start + 1, unit: "Day", currency: "TZS", unit_cost: 180000, funding_status: "Planned" },
        { resource: "Drinking water and field refreshments", description: "Safe hydration for the field team", needed_on: addDays(start), quantity: 24, unit: "Nos", currency: "TZS", unit_cost: 5000, funding_status: "Planned" },
      ],
      responsibilities: "The coordinator confirms authorisation, security and daily briefings. Team leads supervise safe delivery and reporting. Every participant follows the Fundamental Principles, code of conduct, safeguarding requirements and agreed information-management procedures.",
      notes: "Presentation-quality demonstration TOR; operational authorisation is still required before any real deployment.",
    }, tor_name);
    await upsert("VMMS Deployment", { terms_of_reference: tor, geo_node: geo_scope }, {
      naming_series: "DEP-.#####", terms_of_reference: tor, geo_node: geo_scope,
      coordinator: CONFIG.coordinator, status: "Planned", volunteers_required: 12,
      planned_start: `${addDays(start)} 08:00:00`, planned_end: `${addDays(end)} 17:00:00`,
      briefing_on: `${addDays(start - 2)} 14:00:00`, check_in_deadline: `${addDays(start)} 07:30:00`,
      expected_return: `${addDays(end)} 18:30:00`, site_name: deploymentName, site_address: site,
      site_latitude: latitude, site_longitude: longitude,
      meeting_point: "TRCS Branch Office", meeting_address: site,
      meeting_latitude: latitude, meeting_longitude: longitude,
      travel_notes: "Travel only after coordinator confirmation. Carry identification, charged phone, water and issued visibility items.",
      local_contact_name: "TRCS Branch Coordination Desk", local_contact_phone: "+255 22 215 0330",
      notes: "Fictional demonstration deployment linked to a detailed TOR.",
    }, deploymentName);
  }

  window.TRCS_DEMO_SEED_RESULTS = results;
  console.table(results.errors);
  console.log(DRY_RUN ? "DRY RUN COMPLETE — no records were changed." : "TRCS DEMO SEED COMPLETE", results);
  frappe.show_alert({ message: DRY_RUN ? "TRCS demo dry run complete" : "TRCS demo content seeded", indicator: DRY_RUN ? "blue" : "green" }, 10);
  return results;
})();
