(function () {
  const toast = document.createElement('div');
  toast.className = 'portal-toast';
  toast.setAttribute('role', 'status');
  document.body.appendChild(toast);

  function say(message) {
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(window.__portalToast);
    window.__portalToast = setTimeout(() => toast.classList.remove('show'), 2400);
  }

  document.querySelector('.menu-toggle')?.addEventListener('click', () => {
    document.querySelector('.sidebar')?.classList.toggle('open');
  });

  document.querySelectorAll('.page-tabs a').forEach((tab) => {
    tab.addEventListener('click', (event) => {
      if (!tab.getAttribute('href')) event.preventDefault();
      tab.parentElement.querySelectorAll('a').forEach((item) => item.classList.toggle('on', item === tab));
      say(`${tab.textContent.trim()} view selected.`);
    });
  });

  document.querySelectorAll('.task-row input[type="checkbox"]').forEach((box) => {
    box.addEventListener('change', () => {
      box.closest('.task-row').classList.toggle('task-complete', box.checked);
      say(box.checked ? 'Task marked complete.' : 'Task returned to open.');
    });
  });

  document.querySelector('.notification-actions button')?.addEventListener('click', () => {
    document.querySelectorAll('.notification-row.unread').forEach((row) => row.classList.remove('unread'));
    say('All notifications marked as read.');
  });

  document.querySelectorAll('form').forEach((form) => form.addEventListener('submit', (event) => {
    event.preventDefault();
    say('Saved successfully in this concept preview.');
  }));
})();
