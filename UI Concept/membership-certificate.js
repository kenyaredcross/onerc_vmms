(function () {
  const params = new URLSearchParams(location.search);
  const values = {
    number: params.get('membership') || 'MSHIP-00142',
    type: params.get('type') || 'Ordinary membership',
    branch: params.get('branch') || 'Nairobi Branch',
    from: params.get('from') || '1 Jan 2026',
    to: params.get('to') || '31 Dec 2026'
  };
  const set = (id, value) => { const field = document.getElementById(id); if (field) field.textContent = value; };
  set('toolbar-record', values.number); set('certificate-number', values.number); set('certificate-type', values.type);
  set('certificate-branch', values.branch); set('signature-branch', values.branch); set('certificate-from', values.from);
  set('certificate-to', values.to); set('certificate-verify', values.number);
  document.querySelector('[data-print]').addEventListener('click', () => window.print());
}());
