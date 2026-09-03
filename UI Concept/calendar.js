(function () {
  const events = [...document.querySelectorAll('.calendar-event')];
  const fields = {
    type: document.getElementById('calendar-detail-type'),
    title: document.getElementById('calendar-detail-title'),
    date: document.getElementById('calendar-detail-date'),
    time: document.getElementById('calendar-detail-time'),
    location: document.getElementById('calendar-detail-location'),
    description: document.getElementById('calendar-detail-description'),
    action: document.getElementById('calendar-detail-action')
  };

  function selectEvent(eventButton, moveFocus) {
    if (!eventButton) return;
    document.querySelectorAll('.month-day.selected').forEach((day) => day.classList.remove('selected'));
    eventButton.closest('.month-day')?.classList.add('selected');
    fields.type.textContent = eventButton.dataset.type;
    fields.title.textContent = eventButton.dataset.title;
    fields.date.textContent = eventButton.dataset.date;
    fields.time.textContent = eventButton.dataset.time;
    fields.location.textContent = eventButton.dataset.location;
    fields.description.textContent = eventButton.dataset.description;
    fields.action.textContent = `${eventButton.dataset.action} →`;
    fields.action.href = eventButton.dataset.href;
    if (moveFocus && matchMedia('(max-width: 760px)').matches) {
      document.querySelector('.calendar-detail')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  events.forEach((eventButton) => eventButton.addEventListener('click', () => selectEvent(eventButton, true)));
  document.querySelectorAll('[data-calendar-select]').forEach((shortcut) => shortcut.addEventListener('click', () => {
    const eventButton = events.find((item) => item.dataset.title === shortcut.dataset.calendarSelect);
    selectEvent(eventButton, false);
    eventButton?.focus({ preventScroll: true });
  }));
})();
