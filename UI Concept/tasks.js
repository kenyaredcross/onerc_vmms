(function () {
  const cards = [...document.querySelectorAll('.volunteer-task-card')];
  const search = document.getElementById('task-search');
  const filters = [...document.querySelectorAll('[data-task-filter]')];
  const empty = document.querySelector('.task-empty');
  const count = document.getElementById('task-result-count');
  let activeFilter = 'active';

  function matchesStatus(card) {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'active') return ['assigned', 'accepted', 'submitted'].includes(card.dataset.status);
    if (activeFilter === 'questions') return card.dataset.openQuestion === 'true';
    return card.dataset.status === activeFilter;
  }

  function applyFilters() {
    const query = search.value.trim().toLowerCase(); let visible = 0;
    cards.forEach((card) => {
      const text = `${card.dataset.title} ${card.dataset.context} ${card.dataset.type}`.toLowerCase();
      card.hidden = !(matchesStatus(card) && (!query || text.includes(query)));
      if (!card.hidden) visible += 1;
    });
    empty.hidden = visible !== 0;
    count.textContent = `${visible} ${activeFilter === 'active' ? 'active' : 'shown'}`;
  }

  filters.forEach((button) => button.addEventListener('click', () => {
    activeFilter = button.dataset.taskFilter;
    filters.forEach((item) => item.classList.toggle('active', item === button));
    applyFilters();
  }));
  search.addEventListener('input', applyFilters);
  applyFilters();
})();
