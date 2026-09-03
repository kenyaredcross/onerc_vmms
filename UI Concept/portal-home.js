(function () {
  const root = document.getElementById('home-state-content');
  const select = document.getElementById('home-state-select');
  if (!root || !select) return;

  const events = `<section class="card upcoming-card"><div class="card-head"><h3>Coming up near you</h3><a class="text-link" href="calendar.html">View calendar →</a></div><a class="event-row" href="event-detail.html"><span class="event-date">05<small>SEP</small></span><span class="event-info"><strong>Community first-aid demonstration</strong><span>09:00 · Nairobi County</span></span><span>›</span></a><a class="event-row" href="event-detail.html"><span class="event-date">12<small>SEP</small></span><span class="event-info"><strong>Volunteer information session</strong><span>14:00 · Online</span></span><span>›</span></a></section>`;
  const discover = `<section class="card discover-card"><div class="card-head"><h3>Discover</h3></div><a class="discover-link" href="opportunities.html">Browse opportunities <span>→</span></a><a class="discover-link" href="events.html">Upcoming events <span>→</span></a><a class="discover-link" href="stories.html">Volunteer stories <span>→</span></a></section>`;
  const action = (href, label, secondary = false) => `<a class="home-${secondary ? 'secondary' : 'primary'}-action" href="${href}">${label}</a>`;
  const shell = (main, side) => `<div class="dashboard-grid"><div>${main}</div><aside class="side-stack">${side}</aside></div>`;
  const steps = (label, percent, title, copy, done, remaining) => `<section class="card progress-card"><div class="progress-ring" style="--home-progress:${percent * 3.6}deg"><strong>${label}</strong></div><h3>${title}</h3><p>${copy}</p><div class="checklist">${done.map(item => `<div class="check-item done"><i>✓</i><span>${item}</span></div>`).join('')}${remaining.map((item, i) => `<div class="check-item"><i>${done.length + i + 1}</i><span>${item}</span></div>`).join('')}</div></section>`;
  const note = (kicker, title, copy, href, label) => `<section class="card home-note-card"><span>${kicker}</span><h3>${title}</h3><p>${copy}</p><a href="${href}">${label} →</a></section>`;

  const views = {
    new: {
      role: 'New account', chip: 'Registration not started', tone: '', eyebrow: 'Welcome to your portal', title: 'Start where your heart<br>wants to <em>serve.</em>', intro: 'Join Kenya Red Cross as a volunteer, become a member, or do both. Choose a path and we will guide you step by step.',
      body: () => shell(`<section class="card choice-card"><div class="choice-intro"><p class="choice-kicker">Your next step</p><h2>How would you like<br>to get involved?</h2><p>Give your time as a volunteer or become a member of the Society. You can add the other path later.</p></div><div class="horizontal-choices"><a class="horizontal-path primary" href="volunteer-registration.html"><span class="horizontal-path-icon">♡</span><span><strong>Register as a volunteer</strong><small>Serve communities with your time and skills</small></span><i>→</i></a><a class="horizontal-path" href="membership.html"><span class="horizontal-path-icon">♧</span><span><strong>Become a member</strong><small>Join and support our humanitarian mission</small></span><i>→</i></a></div></section>${events}`, steps('1/4', 12, 'Set up your record', 'Complete these steps to unlock opportunities matched to you.', ['Account created'], ['Choose your path', 'Complete registration', 'Submit for review']) + discover)
    },
    draft: {
      role: 'Volunteer applicant', chip: 'Application in progress', tone: '', eyebrow: 'Welcome back', title: 'Your application is<br><em>saved</em> and waiting.', intro: 'Pick up exactly where you stopped. Your profile, documents and completed answers are still here.',
      body: () => shell(`<section class="card resume-card"><div class="resume-heading"><div><p class="choice-kicker">Volunteer application · Draft</p><h2>Continue your application</h2><p>Last saved today at 10:42 · Nairobi Branch</p></div><strong>5 of 8 sections</strong></div><div class="resume-meter"><i style="width:62.5%"></i></div><div class="resume-next"><span><b>Next: Skills &amp; availability</b><small>Add the details that help us match you to the right work.</small></span>${action('volunteer-registration.html#step-5', 'Continue application →')}</div></section>${events}`, steps('5/8', 62.5, 'Application progress', 'Save and return at any time before submission.', ['Personal details', 'Identification', 'Emergency contacts', 'Location', 'Background'], ['Skills & availability', 'Questions', 'Declarations & review']) + discover)
    },
    review: {
      role: 'Volunteer applicant', chip: 'Application under review', tone: 'info', eyebrow: 'Application VAPP-00152', title: 'Your application is<br>with your <em>branch.</em>', intro: 'There is nothing you need to do right now. We will notify you when the review moves forward or if information is needed.',
      body: () => shell(`<section class="card application-home-card"><div class="application-home-head"><span class="state-symbol">✓</span><div><p class="choice-kicker">Submitted 1 September 2026</p><h2>Branch review in progress</h2><p>Nairobi Branch · Estimated review 3–5 working days</p></div></div><div class="review-timeline"><span class="done"><i>✓</i><b>Submitted</b></span><span class="current"><i>2</i><b>Branch review</b></span><span><i>3</i><b>Next approval</b></span><span><i>4</i><b>Activation</b></span></div>${action('volunteer-status.html', 'Track application details →', true)}</section>${events}`, note('Nothing needed from you', 'We will keep you updated', 'Decisions and requests appear in Notifications and are also sent by email.', 'notifications.html', 'Open notifications') + discover)
    },
    action: {
      role: 'Volunteer applicant', chip: 'Action required', tone: 'danger', eyebrow: 'A reviewer has replied', title: 'One update will keep<br>your application <em>moving.</em>', intro: 'Your application has returned to draft so you can correct the requested information without starting again.',
      body: () => shell(`<section class="card correction-card"><div class="correction-head"><span>!</span><div><p class="choice-kicker">Information requested · 1 September</p><h2>Replace your identification proof</h2></div></div><blockquote>“The uploaded ID image is cropped. Please upload a clear copy showing all four corners and the expiry date.”</blockquote><div class="correction-meta"><span><small>Requested by</small><strong>Jane Wanjiku · Nairobi Branch</strong></span><span><small>Return by</small><strong>5 September 2026</strong></span></div>${action('volunteer-registration.html#step-2', 'Update requested section →')}</section>${events}`, steps('1', 30, 'One item to update', 'Only the affected section needs attention. Your other answers remain saved.', [], ['Replace ID proof', 'Review change', 'Resubmit application']) + discover)
    },
    active: {
      role: 'Active volunteer', chip: 'Active volunteer', tone: 'success', eyebrow: 'Nairobi Branch · KRC-V-2026-018', title: 'Ready to make an<br><em>impact,</em> Alex?', intro: 'Your volunteer workspace brings today’s assignments, deployment requests, learning and service record together.',
      body: () => shell(`<section class="volunteer-summary-grid"><article class="home-stat"><span>Open tasks</span><strong>3</strong><a href="tasks.html">View tasks →</a></article><article class="home-stat urgent"><span>Response needed</span><strong>1</strong><a href="deployment-request.html">Deployment request →</a></article><article class="home-stat"><span>Service this year</span><strong>136h</strong><a href="hours.html">View hours →</a></article></section><section class="card volunteer-focus"><div class="card-head"><div><p class="choice-kicker">Your priority</p><h3>Tana River Flood Response — Wave 3</h3></div><span class="home-deadline">Reply by 2 Sep</span></div><p>You have been invited as a Community Health Volunteer from 14–25 September.</p><div>${action('deployment-request.html', 'Review invitation →')}${action('tasks.html', 'See today’s tasks', true)}</div></section>${events}`, `<section class="card readiness-card"><div class="readiness-score"><strong>92%</strong><span>Ready</span></div><h3>Your readiness record</h3><p>One safeguarding refresher is due soon. Everything else needed for deployment is current.</p><a href="training.html">Continue training →</a></section>${discover}`)
    },
    closed: {
      role: 'Portal account', chip: 'Application closed', tone: 'neutral', eyebrow: 'Application VAPP-00152', title: 'This application<br>has <em>closed.</em>', intro: 'Rejected, withdrawn and expired applications remain in your record. The exact outcome and next available action are always visible.',
      body: () => shell(`<section class="card closed-state-card"><div class="closed-state-tabs"><button class="active" data-closed="rejected">Rejected</button><button data-closed="withdrawn">Withdrawn</button><button data-closed="expired">Expired</button></div><div data-closed-panel></div></section>${events}`, note('Your record is preserved', 'No information has been lost', 'Your profile, membership and previous application remain available.', 'profile.html', 'Review my profile') + discover)
    }
  };

  const closedCopy = {
    rejected: ['×', 'Decision recorded 1 September 2026', 'Application not approved', 'The required identification could not be verified. This decision does not affect your portal profile or membership.', 'You may apply again from 1 December 2026', 'Use your existing profile and updated documents when a new application becomes available.'],
    withdrawn: ['↩', 'Withdrawn by you · 1 September 2026', 'Application withdrawn', 'You chose to stop this application before a final decision. It is no longer being reviewed.', 'Start a new application when you are ready', 'Your profile can be reused, but the new application will have its own review.'],
    expired: ['○', 'Expired 1 September 2026', 'Application expired', 'The configured response period passed without the requested update.', 'Contact your branch before applying again', 'The branch can explain the next intake window and documents needed.']
  };
  function renderClosed(key) {
    const value = closedCopy[key];
    document.querySelector('[data-closed-panel]').innerHTML = `<span class="state-symbol closed">${value[0]}</span><p class="choice-kicker">${value[1]}</p><h2>${value[2]}</h2><p>${value[3]}</p><div class="closed-guidance"><strong>${value[4]}</strong><span>${value[5]}</span></div>${action('volunteer-status.html', 'View application record →', true)}`;
  }
  function render(key) {
    const view = views[key] || views.new;
    document.querySelector('.profile-button small').textContent = view.role;
    root.innerHTML = `<header class="page-intro"><div><p class="date-label">Tuesday, 1 September</p><h1>Good morning, <span>Alex.</span></h1></div><span class="status-chip ${view.tone}">${view.chip}</span></header><section class="welcome-card"><div class="welcome-copy"><p class="eyebrow">${view.eyebrow}</p><h2>${view.title}</h2><p>${view.intro}</p></div><div class="welcome-image"><img src="../vmmsx/public/images/seed_kenya/outreach-lamu.jpg" alt="Kenya Red Cross community outreach"></div></section>${view.body()}`;
    const url = new URL(location.href); url.searchParams.set('state', key); history.replaceState({}, '', url);
    if (key === 'closed') {
      renderClosed('rejected');
      document.querySelectorAll('[data-closed]').forEach(button => button.addEventListener('click', () => {
        document.querySelectorAll('[data-closed]').forEach(item => item.classList.toggle('active', item === button));
        renderClosed(button.dataset.closed);
      }));
    }
  }
  const requested = new URLSearchParams(location.search).get('state');
  select.value = views[requested] ? requested : 'new';
  select.addEventListener('change', () => render(select.value));
  render(select.value);
}());
