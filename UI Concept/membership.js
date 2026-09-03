(function () {
  const toast = document.querySelector('.portal-toast');
  const modal = document.getElementById('membershipJoinModal');
  const form = document.getElementById('membershipJoinForm');
  const existingToggle = document.getElementById('existingMemberToggle');
  const paymentFlow = document.getElementById('membershipPaymentFlow');
  const proofFlow = document.getElementById('membershipProofFlow');
  const submitButton = document.getElementById('membershipSubmit');
  const errorMessage = document.getElementById('membershipFormError');
  const proofFile = document.getElementById('membershipProofFile');
  const claimedStart = document.getElementById('membershipClaimedStart');
  const proofDeclaration = document.getElementById('membershipProofDeclaration');

  const plans = {
    'youth-school': {
      name: 'Youth In School',
      price: 'KES 100',
      period: '/ year',
      eligibility: 'Ages below 18 years',
      description: 'Annual youth membership for students who want to participate in Red Cross activities through their local branch.',
      benefits: ['Youth membership certificate', 'Invites to special events', 'Briefings and participation in branch activities'],
    },
    'youth-out-school': {
      name: 'Youth Out Of School',
      price: 'KES 500',
      period: '/ year',
      eligibility: 'Ages 18–30 years',
      description: 'Annual youth membership for young adults participating through a Red Cross branch.',
      benefits: ['Youth membership certificate', 'Invites to special events', 'Briefings and participation in branch activities', 'Listed in the branch register of members'],
    },
    ordinary: {
      name: 'Ordinary Member',
      price: 'KES 1,000',
      period: '/ year',
      eligibility: 'Ages 30 years and above',
      description: 'Annual ordinary membership recorded at the branch selected during registration.',
      benefits: ['Ordinary membership certificate', 'Invites to special events', 'Briefings and participation in branch activities', 'Listed in the branch register of members'],
    },
    life: {
      name: 'Life Member',
      price: 'KES 5,000',
      period: 'one-off',
      eligibility: 'Lifetime membership',
      description: 'A one-off membership that does not expire or require annual renewal.',
      benefits: ['Life membership certificate', 'Invites to special events such as Life Members Day', 'Briefings and participation in branch activities', 'Listed in the branch register of members', 'Vote or vie for governance positions'],
    },
  };

  let selectedPlanKey = '';
  let returnFocus = null;

  function notify(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(window.__membershipToast);
    window.__membershipToast = window.setTimeout(() => toast.classList.remove('show'), 2500);
  }

  function showView(name) {
    modal.querySelectorAll('[data-membership-view]').forEach((view) => {
      view.hidden = view.dataset.membershipView !== name;
    });
  }

  function fillPlan(plan) {
    document.getElementById('selectedMembershipPlan').value = selectedPlanKey;
    modal.querySelector('[data-selected-plan]').textContent = plan.name;
    modal.querySelector('[data-selected-price]').textContent = plan.price;
    modal.querySelector('[data-selected-period]').textContent = plan.period;
    modal.querySelector('[data-payment-total]').textContent = plan.price;
    modal.querySelector('[data-modal-price]').textContent = plan.price;
    modal.querySelector('[data-modal-period]').textContent = plan.period;
    modal.querySelector('[data-modal-description]').textContent = plan.description;
    modal.querySelector('[data-modal-eligibility]').textContent = plan.eligibility;

    const benefits = modal.querySelector('[data-modal-benefits]');
    benefits.replaceChildren();
    plan.benefits.forEach((benefit) => {
      const item = document.createElement('li');
      item.textContent = benefit;
      benefits.appendChild(item);
    });
  }

  function openModal(planKey, view, trigger) {
    const plan = plans[planKey];
    if (!plan) return;

    selectedPlanKey = planKey;
    returnFocus = trigger || document.activeElement;
    fillPlan(plan);
    form.reset();
    document.getElementById('membershipPaymentPhone').value = '+254 712 345 678';
    errorMessage.hidden = true;
    updateExistingMode();

    document.getElementById('membershipModalKicker').textContent = view === 'details' ? 'Membership details' : 'Membership application';
    document.getElementById('membershipModalTitle').textContent = view === 'details' ? plan.name : `Join ${plan.name}`;
    showView(view);
    modal.hidden = false;
    document.body.classList.add('membership-modal-open');

    window.setTimeout(() => {
      const focusTarget = view === 'details' ? modal.querySelector('[data-detail-join]') : document.getElementById('membershipBranch');
      focusTarget.focus();
    }, 0);
  }

  function closeModal() {
    modal.hidden = true;
    document.body.classList.remove('membership-modal-open');
    if (returnFocus) returnFocus.focus();
  }

  function updateExistingMode() {
    const provingExisting = existingToggle.checked;
    paymentFlow.hidden = provingExisting;
    proofFlow.hidden = !provingExisting;
    document.getElementById('membershipPaymentPhone').required = !provingExisting;
    proofFile.required = provingExisting;
    claimedStart.required = provingExisting;
    proofDeclaration.required = provingExisting;
    submitButton.textContent = provingExisting ? 'Submit proof for verification' : 'Continue to payment';
    errorMessage.hidden = true;
  }

  function showError(message) {
    errorMessage.textContent = message;
    errorMessage.hidden = false;
    errorMessage.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  document.querySelectorAll('[data-membership-plan]').forEach((card) => {
    const planKey = card.dataset.membershipPlan;
    card.querySelector('[data-plan-details]').addEventListener('click', (event) => openModal(planKey, 'details', event.currentTarget));
    card.querySelector('[data-plan-join]').addEventListener('click', (event) => openModal(planKey, 'join', event.currentTarget));
  });

  modal.querySelector('[data-detail-join]').addEventListener('click', () => {
    const plan = plans[selectedPlanKey];
    document.getElementById('membershipModalKicker').textContent = 'Membership application';
    document.getElementById('membershipModalTitle').textContent = `Join ${plan.name}`;
    showView('join');
    document.getElementById('membershipBranch').focus();
  });

  modal.querySelector('[data-change-plan]').addEventListener('click', () => {
    closeModal();
    document.getElementById('membership-options').scrollIntoView({ behavior: 'smooth' });
  });

  modal.querySelectorAll('[data-membership-close]').forEach((button) => button.addEventListener('click', closeModal));
  existingToggle.addEventListener('change', updateExistingMode);

  proofFile.addEventListener('change', () => {
    modal.querySelector('[data-proof-file-name]').textContent = proofFile.files.length ? proofFile.files[0].name : 'JPG, JPEG, PNG or PDF';
  });

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const branch = document.getElementById('membershipBranch').value;
    const provingExisting = existingToggle.checked;

    if (!branch) {
      showError('Choose the branch where this membership should be recorded.');
      return;
    }
    if (provingExisting && !proofFile.files.length) {
      showError('Upload the document that proves your existing membership.');
      return;
    }
    if (provingExisting && !claimedStart.value) {
      showError('Enter the date you originally joined, as shown on your proof.');
      return;
    }
    if (provingExisting && !proofDeclaration.checked) {
      showError('Confirm that the existing-membership information is accurate.');
      return;
    }
    if (!provingExisting && !document.getElementById('membershipPaymentPhone').value.trim()) {
      showError('Enter the phone number that should receive the payment request.');
      return;
    }

    const plan = plans[selectedPlanKey];
    document.getElementById('membershipSuccessTitle').textContent = provingExisting ? 'Proof submitted for verification' : 'Payment request prepared';
    document.getElementById('membershipSuccessMessage').textContent = provingExisting
      ? `Your ${plan.name} claim for ${branch} has been sent to the branch for verification. No payment was requested.`
      : `A ${plan.price} payment request for ${plan.name} will be sent to ${document.getElementById('membershipPaymentPhone').value.trim()}.`;
    showView('success');
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !modal.hidden) closeModal();
  });

  document.querySelectorAll('[data-membership-action="certificate"]').forEach((link) => {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      const card = link.closest('[data-membership-record]');
      const facts = [...card.querySelectorAll('.live-membership-facts div')].reduce((values, fact) => {
        values[fact.querySelector('dt').textContent.trim()] = fact.querySelector('dd').textContent.trim();
        return values;
      }, {});
      const params = new URLSearchParams({
        membership: card.dataset.membershipRecord,
        type: card.querySelector('.live-membership-title strong').textContent.trim(),
        branch: card.querySelector('.live-membership-head p').textContent.trim(),
        from: facts['Valid from'],
        to: facts['Valid to']
      });
      location.href = `membership-certificate.html?${params}`;
    });
  });

  const pageParams = new URLSearchParams(location.search);
  const linkedPlan = pageParams.get('plan');
  if (linkedPlan && plans[linkedPlan]) {
    openModal(linkedPlan, pageParams.get('view') === 'details' ? 'details' : 'join');
    if (pageParams.get('mode') === 'proof') {
      existingToggle.checked = true;
      updateExistingMode();
    }
  }

  if (pageParams.get('state') === 'empty') {
    document.getElementById('paid-membership-grid').hidden = true;
    document.getElementById('membership-empty').hidden = false;
    document.getElementById('paid-membership-count').textContent = '0 active';
    document.getElementById('paid-membership-count').nextElementSibling.textContent = '0 records';
    document.getElementById('membership-summary').textContent = 'No membership records on your account';
    document.getElementById('membership-options-heading').textContent = 'Choose a membership and branch';
    document.querySelector('.side-nav .badge').textContent = '0';
    document.querySelector('.membership-account-menu nav a:nth-child(2) b').textContent = '0';
    document.querySelector('.plan-ribbon').hidden = true;
  }
})();
