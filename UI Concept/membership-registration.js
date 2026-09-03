(function () {
  const plans = [...document.querySelectorAll('input[name="plan"]')];
  const branch = document.getElementById('membership-branch');

  function selectedPlan() {
    return document.querySelector('input[name="plan"]:checked')?.value || 'ordinary';
  }

  function setText(id, value) {
    const node = document.getElementById(id);
    if (node) node.textContent = value;
  }

  function syncPlan() {
    const life = selectedPlan() === 'life';
    document.getElementById('ordinary-payment-flow').hidden = life;
    document.getElementById('life-approval-flow').hidden = !life;
    setText('membership-plan-note', life
      ? 'Life Member has no fee, is routed to an authorised branch approver and activates with no expiry date after approval.'
      : 'Ordinary membership waits for payment confirmation, then activates automatically. Each branch application creates a separate membership record.');
    setText('membership-payment-title', life ? 'Branch approval' : 'Payment');
    setText('membership-payment-intro', life
      ? 'No payment is collected. The selected branch reviews this membership before it can become active.'
      : 'Pay the configured fee and provide the transaction information needed for confirmation.');
    setText('membership-payment-save-note', life ? 'Approval begins after submission' : 'Payment is confirmed after submission');
    setText('membership-review-type', life ? 'Life Member' : 'Ordinary');
    setText('membership-review-plan', life ? 'No fee · Lifetime after approval' : 'KES 1,000 · 365 days');
    setText('membership-review-process-title', life ? 'Approval' : 'Payment');
    setText('membership-review-process', life
      ? 'The selected branch must approve this membership'
      : 'Payment will activate this membership after confirmation');
  }

  function syncBranch() {
    setText('membership-review-branch', `${branch.value} · Required answer complete`);
  }

  const requested = new URLSearchParams(location.search).get('type');
  const requestedRadio = plans.find((radio) => radio.value === requested);
  if (requestedRadio) requestedRadio.checked = true;

  plans.forEach((radio) => radio.addEventListener('change', syncPlan));
  branch.addEventListener('change', syncBranch);
  syncPlan();
  syncBranch();
})();
