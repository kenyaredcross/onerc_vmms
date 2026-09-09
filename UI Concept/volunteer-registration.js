(function () {
  "use strict";

  const form = document.getElementById("volunteer-application");
  const steps = [...document.querySelectorAll(".form-step")];
  const dialog = document.getElementById("record-dialog");
  const recordForm = document.getElementById("record-form");
  const dialogFields = dialog.querySelector("[data-dialog-fields]");
  const dialogError = dialog.querySelector(".dialog-error");
  const saveStatus = document.querySelector("[data-save-status]");
  const saveStatusWrap = saveStatus.closest(".save-status");
  const toast = document.querySelector("[data-toast]");
  const continueButton = document.querySelector("[data-continue]");
  const backButton = document.querySelector("[data-back]");
  const backgroundTypes = ["education", "training", "work_experience", "licences", "driving_licences", "references"];
  const disabilityCombo = document.querySelector("[data-disability-combo]");
  const disabilitySearch = document.getElementById("disability-search");
  const disabilityList = document.querySelector("[data-disability-options]");
  const disabilityTokens = document.querySelector("[data-disability-tokens]");
  const disabilityValues = document.querySelector("[data-disability-values]");
  const disabilityOptions = [
    { key: "Blindness", label: "Blindness", description: "Vision" },
    { key: "Low vision", label: "Low vision", description: "Vision" },
    { key: "Deafness", label: "Deafness", description: "Hearing" },
    { key: "Hard of hearing", label: "Hard of hearing", description: "Hearing" },
    { key: "Wheelchair user", label: "Wheelchair user", description: "Mobility" },
    { key: "Difficulty walking or climbing steps", label: "Difficulty walking or climbing steps", description: "Mobility" },
    { key: "Limb difference", label: "Limb difference", description: "Mobility" },
    { key: "Learning disability", label: "Learning disability", description: "Cognition" },
    { key: "Difficulty remembering or concentrating", label: "Difficulty remembering or concentrating", description: "Cognition" },
    { key: "Difficulty with washing or dressing", label: "Difficulty with washing or dressing", description: "Self-care" },
    { key: "Speech impairment", label: "Speech impairment", description: "Communication" },
    { key: "Difficulty being understood", label: "Difficulty being understood", description: "Communication" }
  ];

  const select = (options) => options.map((option) => ({ value: option, label: option }));
  const fields = {
    identification: {
      title: "identification document",
      intro: "Add the document details exactly as they appear. The first saved document is your primary identification.",
      icon: "ID",
      fields: [
        { name: "id_type", label: "ID type", type: "select", required: true, options: select(["Birth Certificate", "National ID", "Passport", "Alien ID", "Driving Licence"]) },
        { name: "id_number", label: "ID number", type: "text", required: true, hint: "Enter letters, spaces and punctuation exactly as printed." },
        { name: "attachment", label: "Identification copy", type: "file", wide: true, hint: "Required for Birth Certificate and National ID in this example. Private to authorised reviewers." }
      ],
      summary: (row) => ({ title: row.id_type || "Identification document", detail: row.id_number || "No number entered", note: row.attachment ? `Copy attached · ${row.attachment}` : "No copy attached" })
    },
    emergency: {
      title: "emergency contact",
      intro: "Add one person per record. Permission applies to this person only, so a second contact can have a different answer.",
      icon: "EC",
      fields: [
        { name: "contact_name", label: "Full name", type: "text", required: true, autocomplete: "name" },
        { name: "relationship", label: "Relationship", type: "text", required: true, placeholder: "Mother, brother, friend" },
        { name: "primary_phone", label: "Primary phone number", type: "tel", required: true, autocomplete: "tel" },
        { name: "alternative_phone", label: "Alternative phone number", type: "tel", hint: "Optional" },
        { name: "may_contact_in_emergency", label: "Permission to contact in an emergency", type: "checkbox", wide: true, hint: "Clear this checkbox if Kenya Red Cross may not call this person." }
      ],
      summary: (row) => ({ title: row.contact_name || "Emergency contact", detail: [row.relationship, row.primary_phone].filter(Boolean).join(" · ") || "No contact details", note: row.may_contact_in_emergency ? "Permission given" : "Do not contact" })
    },
    education: {
      title: "education record",
      intro: "Add one school, college or university at a time. Years are enough; exact dates are not needed.",
      icon: "ED",
      fields: [
        { name: "institution", label: "School or institution", type: "text", required: true, wide: true },
        { name: "level", label: "Level", type: "select", options: select(["Primary", "Secondary", "Certificate", "Diploma", "Undergraduate degree", "Postgraduate degree"]) },
        { name: "qualification", label: "Qualification or certification", type: "text", hint: "As written on the certificate." },
        { name: "started_in", label: "Start year", type: "number", placeholder: "YYYY", min: "1950", max: "2026" },
        { name: "finished_in", label: "End year", type: "number", placeholder: "YYYY", min: "1950", max: "2035" },
        { name: "is_ongoing", label: "I am still studying here", type: "checkbox", wide: true, hint: "The end year will be cleared." },
        { name: "attachment", label: "Certificate copy", type: "file", wide: true, hint: "Optional · uploaded privately." }
      ],
      summary: (row) => ({ title: row.institution || "Education", detail: [row.qualification, row.level].filter(Boolean).join(" · ") || "No qualification entered", note: row.is_ongoing ? `Since ${row.started_in || "start date not entered"}` : [row.started_in, row.finished_in].filter(Boolean).join("–") })
    },
    training: {
      title: "training or course",
      intro: "Add relevant training, short courses or workshops. Attach the certificate only if you have it available.",
      icon: "TR",
      fields: [
        { name: "course_name", label: "Course", type: "text", required: true },
        { name: "institution", label: "Training provider", type: "text" },
        { name: "started_on", label: "Started", type: "date" },
        { name: "completed_on", label: "Completed", type: "date" },
        { name: "remarks", label: "Notes", type: "textarea", wide: true },
        { name: "attachment", label: "Certificate copy", type: "file", wide: true, hint: "Optional · uploaded privately." }
      ],
      summary: (row) => ({ title: row.course_name || "Training", detail: row.institution || "No training provider entered", note: row.completed_on ? `Completed ${displayDate(row.completed_on)}` : "Completion date not entered" })
    },
    work_experience: {
      title: "work experience",
      intro: "Include paid, unpaid or volunteer roles that help the branch understand your experience.",
      icon: "WE",
      fields: [
        { name: "organization", label: "Organization", type: "text", required: true },
        { name: "role", label: "Role or job title", type: "text" },
        { name: "started_on", label: "From", type: "date" },
        { name: "ended_on", label: "To", type: "date" },
        { name: "is_current", label: "I currently work here", type: "checkbox", wide: true, hint: "The end date will be cleared." },
        { name: "summary", label: "Responsibilities", type: "textarea", wide: true }
      ],
      summary: (row) => ({ title: row.role || "Work experience", detail: row.organization || "No organization entered", note: row.is_current ? "Current role" : [displayDate(row.started_on), displayDate(row.ended_on)].filter(Boolean).join(" – ") })
    },
    licences: {
      title: "licence or registration",
      intro: "Add every field carried by the Personnel Licence record. Only choose “Other” when the licence type is not listed.",
      icon: "PR",
      fields: [
        { name: "license_type", label: "Licence type", type: "select", required: true, options: select(["Medical", "Nursing", "Clinical officer", "Engineering", "Other"]) },
        { name: "license_name", label: "Licence name", type: "text", hint: "Required when the type is Other." },
        { name: "institution", label: "Issuing institution", type: "text", required: true },
        { name: "qualification", label: "Qualification", type: "text", required: true },
        { name: "registration_no", label: "Registration number", type: "text" },
        { name: "valid_from", label: "Valid from", type: "date", required: true },
        { name: "valid_to", label: "Valid until", type: "date" },
        { name: "does_not_expire", label: "This licence does not expire", type: "checkbox", wide: true, hint: "The valid-until date will be cleared." },
        { name: "description", label: "Description", type: "textarea", wide: true },
        { name: "attachment", label: "Licence copy", type: "file", wide: true, hint: "Optional · uploaded privately." }
      ],
      summary: (row) => ({ title: row.license_name || row.license_type || "Licence", detail: [row.institution, row.qualification, row.registration_no].filter(Boolean).join(" · "), note: row.does_not_expire ? "Does not expire" : row.valid_to ? `Valid to ${displayDate(row.valid_to)}` : "Expiry not entered" })
    },
    driving_licences: {
      title: "driving licence class",
      intro: "Add each driving class as a separate record so matching can use the exact class required for an assignment.",
      icon: "DL",
      fields: [
        { name: "licence_class", label: "Class", type: "select", required: true, options: select(["A — Motorcycle", "B — Light vehicle", "C — Heavy commercial", "D — Public service", "E — Special vehicle"]) },
        { name: "licence_number", label: "Licence number", type: "text" },
        { name: "valid_to", label: "Valid until", type: "date" },
        { name: "attachment", label: "Licence copy", type: "file", wide: true, hint: "Optional · uploaded privately." }
      ],
      summary: (row) => ({ title: row.licence_class || "Driving licence", detail: row.licence_number || "No licence number entered", note: row.valid_to ? `Valid to ${displayDate(row.valid_to)}` : "Expiry not entered" })
    },
    references: {
      title: "professional reference",
      intro: "Add someone who can speak about your work, education or volunteering. Do not list an emergency contact here unless they also act as a referee.",
      icon: "RF",
      fields: [
        { name: "reference_name", label: "Name", type: "text", required: true },
        { name: "relationship", label: "How they know you", type: "text", placeholder: "Former manager, teacher, colleague" },
        { name: "position", label: "Their position", type: "text" },
        { name: "organization", label: "Organization", type: "text" },
        { name: "email", label: "Email", type: "email" },
        { name: "phone", label: "Phone", type: "tel" },
        { name: "notes", label: "Notes", type: "textarea", wide: true }
      ],
      summary: (row) => ({ title: row.reference_name || "Reference", detail: [row.relationship || row.position, row.organization].filter(Boolean).join(" · "), note: row.email || row.phone || "No contact method entered" })
    }
  };

  const records = {
    identification: [{ id_type: "Birth Certificate", id_number: "B-2009-184276", attachment: "birth-certificate.pdf" }],
    emergency: [{ contact_name: "Mary Wanjiku", relationship: "Mother", primary_phone: "+254 722 108 455", alternative_phone: "", may_contact_in_emergency: true }],
    education: [{ institution: "Nairobi Day Secondary School", level: "Secondary", qualification: "Kenya Certificate of Secondary Education", started_in: "2023", finished_in: "", is_ongoing: true, attachment: "" }],
    training: [],
    work_experience: [{ organization: "Nairobi Youth Health Club", role: "Youth outreach volunteer", started_on: "2025-04-12", ended_on: "", is_current: true, summary: "Supported health awareness sessions and event registration." }],
    licences: [],
    driving_licences: [],
    references: []
  };

  let current = Math.max(0, steps.findIndex((step) => `#${step.id}` === location.hash));
  steps.forEach((step, index) => step.classList.toggle("is-active", index === current));
  let editing = { type: null, index: -1 };
  let saveTimer;
  let toastTimer;
  let removedRecord = null;
  let selectedDisabilities = ["Wheelchair user"];
  let activeDisabilityIndex = 0;

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);
  }

  function displayDate(value) {
    if (!value) return "";
    const date = new Date(`${value}T00:00:00`);
    return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(date);
  }

  function matchingDisabilities() {
    const query = disabilitySearch.value.trim().toLowerCase();
    if (!query) return disabilityOptions;
    return disabilityOptions.filter((option) => `${option.label} ${option.description}`.toLowerCase().includes(query));
  }

  function renderDisabilityPicker() {
    const matches = matchingDisabilities();
    activeDisabilityIndex = Math.max(0, Math.min(activeDisabilityIndex, matches.length - 1));
    disabilityList.innerHTML = matches.length ? matches.map((option, index) => {
      const selected = selectedDisabilities.includes(option.key);
      return `<li role="none"><button id="disability-option-${index}" type="button" role="option" aria-selected="${selected}" class="${index === activeDisabilityIndex ? "active" : ""}" data-disability-option="${escapeHtml(option.key)}"><span class="option-check" aria-hidden="true">✓</span><span><strong>${escapeHtml(option.label)}</strong><small>${escapeHtml(option.description)}</small></span></button></li>`;
    }).join("") : `<li class="multi-combo-empty">Nothing matches “${escapeHtml(disabilitySearch.value.trim())}”. The Society can add it to the configured list.</li>`;
    disabilityTokens.innerHTML = selectedDisabilities.map((key) => {
      const option = disabilityOptions.find((entry) => entry.key === key);
      return `<li><button type="button" data-remove-disability="${escapeHtml(key)}">${escapeHtml(option?.label || key)}<span aria-hidden="true">×</span><span class="sr-only">Remove</span></button></li>`;
    }).join("");
    disabilityValues.innerHTML = selectedDisabilities.map((key) => `<input type="hidden" name="disabilities" value="${escapeHtml(key)}">`).join("");
    const open = disabilityCombo.classList.contains("open");
    disabilityList.hidden = !open;
    disabilitySearch.setAttribute("aria-expanded", String(open));
    if (open && matches.length) disabilitySearch.setAttribute("aria-activedescendant", `disability-option-${activeDisabilityIndex}`);
    else disabilitySearch.removeAttribute("aria-activedescendant");
  }

  function setDisabilityPickerOpen(open) {
    disabilityCombo.classList.toggle("open", open);
    renderDisabilityPicker();
  }

  function toggleDisability(key) {
    selectedDisabilities = selectedDisabilities.includes(key)
      ? selectedDisabilities.filter((entry) => entry !== key)
      : [...selectedDisabilities, key];
    renderDisabilityPicker();
    renderReview();
    syncNav();
    markDirty();
  }

  function fieldMarkup(field, value) {
    const id = `record-${field.name}`;
    const required = field.required ? " required" : "";
    const requiredLabel = field.required ? '<b class="required">Required</b>' : "";
    const hint = field.hint ? `<i>${escapeHtml(field.hint)}</i>` : "";
    const wide = field.wide ? " wide" : "";
    if (field.type === "checkbox") {
      return `<label class="check-field${wide}" for="${id}"><input id="${id}" name="${field.name}" type="checkbox" ${value ? "checked" : ""}><span>${escapeHtml(field.label)}${field.hint ? `<small>${escapeHtml(field.hint)}</small>` : ""}</span></label>`;
    }
    let control = "";
    if (field.type === "select") {
      control = `<select id="${id}" name="${field.name}"${required}><option value="">Choose an option</option>${field.options.map((option) => `<option value="${escapeHtml(option.value)}" ${option.value === value ? "selected" : ""}>${escapeHtml(option.label)}</option>`).join("")}</select>`;
    } else if (field.type === "textarea") {
      control = `<textarea id="${id}" name="${field.name}" rows="3"${required}>${escapeHtml(value)}</textarea>`;
    } else if (field.type === "file") {
      const held = value ? `<i>Currently attached: ${escapeHtml(value)}</i>` : hint;
      control = `<input id="${id}" name="${field.name}" type="file" data-held-file="${escapeHtml(value || "")}"${required}>${held}`;
      return `<label class="${wide}">${escapeHtml(field.label)} ${requiredLabel}${control}</label>`;
    } else {
      const min = field.min ? ` min="${field.min}"` : "";
      const max = field.max ? ` max="${field.max}"` : "";
      const placeholder = field.placeholder ? ` placeholder="${escapeHtml(field.placeholder)}"` : "";
      const autocomplete = field.autocomplete ? ` autocomplete="${field.autocomplete}"` : "";
      control = `<input id="${id}" name="${field.name}" type="${field.type}" value="${escapeHtml(value)}"${min}${max}${placeholder}${autocomplete}${required}>`;
    }
    return `<label class="${wide}">${escapeHtml(field.label)} ${requiredLabel}${control}${hint}</label>`;
  }

  function syncDialogDependencies() {
    const ongoing = recordForm.elements.is_ongoing;
    const finished = recordForm.elements.finished_in;
    if (ongoing && finished) { finished.disabled = ongoing.checked; if (ongoing.checked) finished.value = ""; }
    const currentWork = recordForm.elements.is_current;
    const ended = recordForm.elements.ended_on;
    if (currentWork && ended) { ended.disabled = currentWork.checked; if (currentWork.checked) ended.value = ""; }
    const noExpiry = recordForm.elements.does_not_expire;
    const validTo = recordForm.elements.valid_to;
    if (noExpiry && validTo) { validTo.disabled = noExpiry.checked; validTo.required = !noExpiry.checked; if (noExpiry.checked) validTo.value = ""; }
    const licenceType = recordForm.elements.license_type;
    const licenceName = recordForm.elements.license_name;
    if (licenceType && licenceName) licenceName.required = licenceType.value === "Other";
  }

  function openRecord(type, index = -1) {
    const config = fields[type];
    if (!config) return;
    editing = { type, index };
    const row = index >= 0 ? records[type][index] : {};
    dialog.querySelector("[data-dialog-kicker]").textContent = index >= 0 ? "Edit saved record" : "Add record";
    dialog.querySelector("#record-dialog-title").textContent = `${index >= 0 ? "Edit" : "Add"} ${config.title}`;
    dialog.querySelector("[data-dialog-intro]").textContent = config.intro;
    dialogFields.innerHTML = config.fields.map((field) => fieldMarkup(field, row[field.name] ?? "")).join("");
    dialogError.hidden = true;
    recordForm.addEventListener("change", syncDialogDependencies);
    syncDialogDependencies();
    dialog.showModal();
    setTimeout(() => dialogFields.querySelector("input,select,textarea")?.focus(), 50);
  }

  function closeDialog() {
    dialog.close();
    editing = { type: null, index: -1 };
  }

  function dialogRow() {
    const config = fields[editing.type];
    const existing = editing.index >= 0 ? records[editing.type][editing.index] : {};
    const row = {};
    config.fields.forEach((field) => {
      const control = recordForm.elements[field.name];
      if (field.type === "checkbox") row[field.name] = Boolean(control.checked);
      else if (field.type === "file") row[field.name] = control.files?.[0]?.name || existing[field.name] || "";
      else row[field.name] = control.value.trim();
    });
    if (row.is_ongoing) row.finished_in = "";
    if (row.is_current) row.ended_on = "";
    if (row.does_not_expire) row.valid_to = "";
    return row;
  }

  function validateDialog(row) {
    syncDialogDependencies();
    const controlsValid = [...dialogFields.querySelectorAll("input,select,textarea")].every((control) => control.disabled || control.checkValidity());
    let customValid = true;
    if (editing.type === "identification") {
      const needsCopy = ["Birth Certificate", "National ID"].includes(row.id_type);
      customValid = (!needsCopy || Boolean(row.attachment)) && !records.identification.some((entry, index) => index !== editing.index && entry.id_type === row.id_type);
      dialogError.textContent = !row.attachment && needsCopy ? `Attach a copy of the ${row.id_type}.` : "Each identification type can be added only once.";
    } else if (editing.type === "licences" && !row.does_not_expire && !row.valid_to) {
      customValid = false;
      dialogError.textContent = "Enter the expiry date or select “This licence does not expire”.";
    } else {
      dialogError.textContent = "Complete the required fields before saving this record.";
    }
    dialogError.hidden = controlsValid && customValid;
    if (!controlsValid || !customValid) dialogFields.querySelector(":invalid")?.focus();
    return controlsValid && customValid;
  }

  function renderRecord(type, row, index, compact) {
    const config = fields[type];
    const summary = config.summary(row);
    const primary = type === "identification" && index === 0;
    return `<div class="record-item${primary ? " primary" : ""}">
      <span class="record-item-icon" aria-hidden="true">${config.icon}</span>
      <span class="record-item-copy">${primary ? "<small>Primary document</small>" : ""}<strong>${escapeHtml(summary.title)}</strong><span>${escapeHtml(summary.detail)}</span>${summary.note ? `<small>${escapeHtml(summary.note)}</small>` : ""}</span>
      <span class="record-actions"><button type="button" data-edit-record="${type}" data-record-index="${index}">Edit</button><button class="danger" type="button" data-remove-record="${type}" data-record-index="${index}">Remove</button></span>
    </div>`;
  }

  function renderRecords(type) {
    document.querySelectorAll(`[data-record-list="${type}"]`).forEach((container) => {
      container.innerHTML = records[type].map((row, index) => renderRecord(type, row, index, container.classList.contains("compact-list"))).join("");
    });
    document.querySelectorAll(`[data-count-for="${type}"]`).forEach((node) => {
      const count = records[type].length;
      node.textContent = node.classList.contains("record-count") ? `${count} ${count === 1 ? "added" : "added"}` : String(count);
    });
    renderReview();
  }

  function renderReview() {
    const citizenAnswer = form.elements.is_citizen.value;
    const citizenshipReview = document.querySelector("[data-review-citizenship]");
    citizenshipReview.textContent = citizenAnswer === "yes"
      ? "Kenyan citizen"
      : citizenAnswer === "no"
        ? [form.elements.country_of_citizenship.value, form.elements.citizenship_status.value].filter(Boolean).join(" · ") || "Not completed"
        : "Not answered";
    const disabilityReview = document.querySelector("[data-review-disability]");
    const disabilityStatus = form.elements.disability_status.value;
    const needs = form.elements.disability_needs.value.trim();
    disabilityReview.textContent = disabilityStatus === "Yes"
      ? [...selectedDisabilities, needs].filter(Boolean).join(" · ") || "Disability disclosed"
      : disabilityStatus === "No" ? "No disability disclosed" : disabilityStatus || "Not answered";
    document.querySelectorAll("[data-review-records]").forEach((container) => {
      const type = container.dataset.reviewRecords;
      const rows = records[type];
      container.innerHTML = rows.length ? rows.map((row, index) => {
        const summary = fields[type].summary(row);
        return `<div><dt>${escapeHtml(type === "identification" ? `Document ${index + 1}` : `Contact ${index + 1}`)}</dt><dd>${escapeHtml([summary.title, summary.detail, summary.note].filter(Boolean).join(" · "))}</dd></div>`;
      }).join("") : "<div><dt>Records</dt><dd>Not provided</dd></div>";
    });
    const background = document.querySelector("[data-review-background]");
    if (background) {
      const lines = backgroundTypes.flatMap((type) => records[type].map((row) => ({ type, summary: fields[type].summary(row) })));
      background.innerHTML = `<div><dt>Profession</dt><dd>${escapeHtml(form.elements.profession.value || "Not provided")}</dd></div>` + (lines.length ? lines.map((line) => `<div><dt>${escapeHtml(fields[line.type].title)}</dt><dd>${escapeHtml([line.summary.title, line.summary.detail].filter(Boolean).join(" · "))}</dd></div>`).join("") : "<div><dt>Optional records</dt><dd>Not provided</dd></div>");
    }
  }

  function showToast(message, undo) {
    clearTimeout(toastTimer);
    toast.innerHTML = `<span>✓</span><strong>${escapeHtml(message)}</strong>${undo ? '<button type="button" data-undo>Undo</button>' : ""}`;
    toast.hidden = false;
    toastTimer = setTimeout(() => { toast.hidden = true; removedRecord = null; }, undo ? 6500 : 2600);
  }

  function removeRecord(type, index) {
    const [row] = records[type].splice(index, 1);
    if (!row) return;
    removedRecord = { type, index, row };
    renderRecords(type);
    markDirty();
    showToast(`${fields[type].title} removed`, true);
  }

  function undoRemove() {
    if (!removedRecord) return;
    const { type, index, row } = removedRecord;
    records[type].splice(index, 0, row);
    renderRecords(type);
    removedRecord = null;
    showToast("Record restored");
  }

  function conditionalFields() {
    const citizenAnswer = form.elements.is_citizen.value;
    const citizenDetails = document.querySelector("[data-citizen-details]");
    citizenDetails.hidden = citizenAnswer !== "no";
    citizenDetails.querySelectorAll("[data-required-when-visible]").forEach((control) => { control.required = citizenAnswer === "no"; });
    document.querySelector("[data-citizen-confirmation]").hidden = citizenAnswer !== "yes";

    const disabilityDetails = document.querySelector("[data-disability-details]");
    disabilityDetails.hidden = form.elements.disability_status.value !== "Yes";

    const birth = new Date(`${form.elements.date_of_birth.value}T00:00:00`);
    const cutoff = new Date("2008-09-08T00:00:00");
    const minor = !Number.isNaN(birth.getTime()) && birth > cutoff;
    const guardian = document.querySelector("[data-guardian-panel]");
    const adultNote = document.querySelector("[data-adult-note]");
    guardian.hidden = !minor;
    adultNote.hidden = minor;
    guardian.querySelectorAll("input,select,textarea").forEach((control) => { control.disabled = !minor; });

    const consentDetails = document.querySelector("[data-consent-details]");
    const consent = form.elements.consent_given;
    consentDetails.hidden = !minor || !consent.checked;
    consentDetails.querySelectorAll("[data-required-when-visible]").forEach((control) => { control.required = minor && consent.checked; });
  }

  function consentProgress() {
    const boxes = [...document.querySelectorAll(".declaration-record input[type=checkbox]")];
    const accepted = boxes.filter((box) => box.checked).length;
    document.querySelector("[data-consent-count]").textContent = `${accepted} of ${boxes.length}`;
    document.querySelectorAll(".consent-progress i").forEach((bar, index) => bar.classList.toggle("off", index >= accepted));
  }

  function dynamicErrors(index) {
    const errors = [];
    if (index === 2 && records.identification.length === 0) errors.push({ label: "Add at least one identification document", target: document.querySelector('[data-add-record="identification"]') });
    if (index === 5 && !records.emergency.some((row) => row.contact_name && row.primary_phone && row.may_contact_in_emergency)) errors.push({ label: "Add an emergency contact who may be contacted", target: document.querySelector('[data-add-record="emergency"]') });
    if (index === steps.length - 1) {
      steps.slice(0, -1).forEach((step, stepIndex) => {
        if (!validateStep(stepIndex)) errors.push({ label: `Complete ${step.dataset.stepTitle}`, target: document.querySelector(`[data-step-target="${step.id}"]`), stepIndex });
      });
    }
    return errors;
  }

  function fieldLabel(control) {
    const text = control.closest("label")?.querySelector(":scope > span:first-child")?.textContent || control.name.replaceAll("_", " ");
    return text.replace(/Required|Optional/g, "").trim();
  }

  function validateStep(index, reveal = false) {
    conditionalFields();
    const step = steps[index];
    const invalid = [...step.querySelectorAll("input,select,textarea")].filter((control) => !control.disabled && !control.checkValidity());
    const errors = [...invalid.map((control) => ({ label: `Enter ${fieldLabel(control)}`, target: control })), ...dynamicErrors(index)];
    if (reveal) {
      const summary = step.querySelector(".error-summary");
      invalid.forEach((control) => control.setAttribute("aria-invalid", "true"));
      if (errors.length) {
        summary.querySelector("ul").innerHTML = errors.map((error, at) => `<li><a href="#" data-error-index="${at}">${escapeHtml(error.label)}</a></li>`).join("");
        summary.hidden = false;
        summary._errors = errors;
        summary.focus();
      } else {
        summary.hidden = true;
      }
    }
    return errors.length === 0;
  }

  function syncNav() {
    const completion = steps.map((step, index) => validateStep(index));
    document.querySelectorAll(".step-link").forEach((button, index) => {
      button.classList.toggle("active", index === current);
      button.classList.toggle("complete", index !== current && completion[index]);
      button.removeAttribute("aria-current");
      if (index === current) button.setAttribute("aria-current", "step");
    });
    const missing = completion.slice(0, -1).filter((complete) => !complete).length;
    const reviewBanner = document.querySelector("[data-review-banner]");
    reviewBanner.classList.toggle("incomplete", missing > 0);
    reviewBanner.querySelector("[data-review-state-icon]").textContent = missing ? "!" : "✓";
    reviewBanner.querySelector("[data-review-state-title]").textContent = missing ? `${missing} required ${missing === 1 ? "section needs" : "sections need"} attention` : "All required sections are complete";
    reviewBanner.querySelector("[data-review-state-copy]").textContent = missing ? "Return to the marked section before submitting your application." : "Your draft was saved. Submitting starts the branch review and locks these answers until a reviewer returns the application for changes.";
    document.querySelector("[data-overall-progress]").textContent = `${current + 1} of ${steps.length}`;
    document.querySelector("[data-rail-meter]").style.width = `${((current + 1) / steps.length) * 100}%`;
    backButton.disabled = current === 0;
    const submit = current === steps.length - 1;
    continueButton.classList.toggle("submit", submit);
    continueButton.innerHTML = submit ? 'Submit application <span aria-hidden="true">→</span>' : 'Continue <span aria-hidden="true">→</span>';
    document.title = `Step ${current + 1} of ${steps.length}: ${steps[current].dataset.stepTitle} — Kenya Red Cross volunteer registration`;
  }

  function goTo(index, push = true) {
    if (index < 0 || index >= steps.length || index === current) return;
    form.dataset.direction = index < current ? "back" : "forward";
    steps[current].classList.remove("is-active");
    current = index;
    steps[current].classList.add("is-active");
    steps[current].querySelector(".error-summary").hidden = true;
    if (push) history.pushState({ step: current }, "", `#${steps[current].id}`);
    syncNav();
    window.scrollTo({ top: Math.max(0, document.querySelector(".registration-wrap").offsetTop - 86), behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    const heading = steps[current].querySelector("h1");
    heading.tabIndex = -1;
    setTimeout(() => heading.focus({ preventScroll: true }), 220);
  }

  function goToHash() {
    const index = steps.findIndex((step) => `#${step.id}` === location.hash);
    if (index >= 0 && index !== current) goTo(index, false);
  }

  function markDirty() {
    clearTimeout(saveTimer);
    saveStatusWrap.classList.add("saving");
    saveStatus.textContent = "Saving changes…";
    saveTimer = setTimeout(saveDraft, 800);
  }

  function saveDraft(notify = false) {
    clearTimeout(saveTimer);
    saveStatusWrap.classList.remove("saving");
    const time = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit" }).format(new Date());
    saveStatus.textContent = `Draft saved at ${time}`;
    if (notify) showToast("Draft saved");
  }

  recordForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!editing.type) return;
    const row = dialogRow();
    if (!validateDialog(row)) return;
    const wasEditing = editing.index >= 0;
    if (editing.index >= 0) records[editing.type][editing.index] = row;
    else records[editing.type].push(row);
    const type = editing.type;
    renderRecords(type);
    closeDialog();
    markDirty();
    showToast(wasEditing ? "Record updated" : "Record added");
  });

  document.addEventListener("click", (event) => {
    const target = event.target.closest("button,a");
    if (!target) return;
    if (target.matches("[data-add-record]")) openRecord(target.dataset.addRecord);
    if (target.matches("[data-edit-record]")) openRecord(target.dataset.editRecord, Number(target.dataset.recordIndex));
    if (target.matches("[data-remove-record]")) removeRecord(target.dataset.removeRecord, Number(target.dataset.recordIndex));
    if (target.matches("[data-disability-option]")) toggleDisability(target.dataset.disabilityOption);
    if (target.matches("[data-remove-disability]")) toggleDisability(target.dataset.removeDisability);
    if (target.matches("[data-close-dialog]")) closeDialog();
    if (target.matches("[data-undo]")) undoRemove();
    if (target.matches("[data-step-target]")) goTo(steps.findIndex((step) => step.id === target.dataset.stepTarget));
    if (target.closest(".error-summary") && target.matches("[data-error-index]")) {
      event.preventDefault();
      const summary = target.closest(".error-summary");
      const error = summary._errors?.[Number(target.dataset.errorIndex)];
      if (Number.isInteger(error?.stepIndex)) goTo(error.stepIndex);
      else error?.target?.focus();
    }
  });

  disabilitySearch.addEventListener("focus", () => setDisabilityPickerOpen(true));
  disabilitySearch.addEventListener("input", () => { activeDisabilityIndex = 0; setDisabilityPickerOpen(true); });
  disabilitySearch.addEventListener("keydown", (event) => {
    const matches = matchingDisabilities();
    if (event.key === "ArrowDown") {
      event.preventDefault();
      activeDisabilityIndex = Math.min(activeDisabilityIndex + 1, Math.max(0, matches.length - 1));
      setDisabilityPickerOpen(true);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      activeDisabilityIndex = Math.max(activeDisabilityIndex - 1, 0);
      setDisabilityPickerOpen(true);
    } else if (event.key === "Enter" && disabilityCombo.classList.contains("open") && matches[activeDisabilityIndex]) {
      event.preventDefault();
      toggleDisability(matches[activeDisabilityIndex].key);
    } else if (event.key === "Escape") {
      disabilitySearch.value = "";
      setDisabilityPickerOpen(false);
    }
  });
  document.addEventListener("mousedown", (event) => {
    if (!disabilityCombo.contains(event.target)) setDisabilityPickerOpen(false);
  });

  document.querySelector("[data-back]").addEventListener("click", () => goTo(current - 1));
  continueButton.addEventListener("click", () => {
    if (!validateStep(current, true)) return;
    saveDraft();
    if (current === steps.length - 1) {
      showToast("Application submitted to Nairobi Branch");
      setTimeout(() => { location.href = "volunteer-status.html"; }, 900);
    } else goTo(current + 1);
  });
  document.querySelector("[data-save]").addEventListener("click", () => saveDraft(true));
  document.querySelector("[data-save-exit]").addEventListener("click", () => {
    saveDraft(true);
    setTimeout(() => { location.href = "portal-home.html"; }, 600);
  });
  document.querySelector("[data-copy-contact]").addEventListener("click", () => {
    const first = records.emergency[0];
    if (!first) return;
    form.elements.guardian_name.value = first.contact_name;
    form.elements.guardian_relationship.value = first.relationship;
    form.elements.guardian_phone.value = first.primary_phone;
    markDirty();
    showToast("Emergency contact copied");
  });

  form.addEventListener("input", (event) => {
    if (event.target === disabilitySearch) return;
    event.target.removeAttribute?.("aria-invalid");
    conditionalFields();
    consentProgress();
    renderReview();
    markDirty();
  });
  form.addEventListener("change", () => { conditionalFields(); consentProgress(); syncNav(); });
  window.addEventListener("popstate", goToHash);
  window.addEventListener("hashchange", goToHash);
  dialog.addEventListener("cancel", (event) => { event.preventDefault(); closeDialog(); });

  renderDisabilityPicker();
  Object.keys(records).forEach(renderRecords);
  conditionalFields();
  consentProgress();
  syncNav();
  if (!location.hash) history.replaceState({ step: current }, "", `#${steps[current].id}`);
  window.addEventListener("load", () => {
    goToHash();
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }, { once: true });
})();
