(function () {
  const toggle = document.querySelector('.map-directions-toggle');
  const map = document.getElementById('meeting-point-map');
  if (!toggle || !map) return;

  toggle.addEventListener('click', () => {
    const opening = map.hidden;
    map.hidden = !opening;
    toggle.setAttribute('aria-expanded', String(opening));
    toggle.textContent = opening ? 'Hide meeting point map ↑' : 'Get directions to meeting point →';
    if (opening) {
      const frame = map.querySelector('iframe[data-src]');
      if (frame && !frame.hasAttribute('src')) frame.src = frame.dataset.src;
      if (matchMedia('(max-width: 900px)').matches) map.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });

  if (new URLSearchParams(location.search).get('meeting') === 'open') toggle.click();
}());
