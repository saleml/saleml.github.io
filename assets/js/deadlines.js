let CONFERENCES = [];

/* ----- helpers ----- */
function parseDeadlineEnd(dateStr, timezone) {
  if (!dateStr) return null;
  const [y, m, d] = dateStr.split('-').map(Number);
  const tz = (timezone || 'AoE').toUpperCase();
  if (tz === 'AOE' || tz === 'UTC-12') {
    return new Date(Date.UTC(y, m - 1, d + 1, 12, 0, 0));
  }
  return new Date(Date.UTC(y, m - 1, d, 23, 59, 59));
}

function daysBetween(a, b) {
  return Math.ceil((b - a) / (1000 * 60 * 60 * 24));
}

function formatDate(dateStr) {
  const [y, m, d] = dateStr.split('-').map(Number);
  const dt = new Date(y, m - 1, d);
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function getNextDeadline(conf) {
  const now = new Date();
  for (const dl of (conf.deadlines || [])) {
    if (!dl.date) continue;
    const end = parseDeadlineEnd(dl.date, dl.timezone);
    if (end && end > now) return dl;
  }
  return null;
}

function getLatestDeadline(conf) {
  const d = (conf.deadlines || []).filter((x) => x.date);
  return d.length ? d[d.length - 1] : null;
}

/* ----- sorting ----- */

function hasUpcomingOrTba(conf) {
  if (getNextDeadline(conf)) return true;
  return (conf.deadlines || []).some((d) => !d.date);
}

function sortConferences(confs) {
  const now = new Date();
  return confs.slice().sort((a, b) => {
    const nextA = getNextDeadline(a);
    const nextB = getNextDeadline(b);
    // upcoming first, then by earliest upcoming deadline
    if (nextA && !nextB) return -1;
    if (!nextA && nextB) return 1;
    if (nextA && nextB) {
      return parseDeadlineEnd(nextA.date, nextA.timezone) - parseDeadlineEnd(nextB.date, nextB.timezone);
    }
    // both passed: sort by latest deadline descending
    const latA = getLatestDeadline(a);
    const latB = getLatestDeadline(b);
    return parseDeadlineEnd(latB.date, latB.timezone) - parseDeadlineEnd(latA.date, latA.timezone);
  });
}

/* ----- rendering ----- */
function renderConferences(filter) {
  const list = document.getElementById('conf-list');
  const noResults = document.getElementById('no-results');
  list.innerHTML = '';

  const now = new Date();
  const sorted = sortConferences(CONFERENCES);

  let hasUpcoming = false;
  let hasPassed = false;
  let shownUpcomingDivider = false;
  let shownPassedDivider = false;
  let visibleCount = 0;

  // separate into upcoming and passed
  const upcoming = sorted.filter(c => hasUpcomingOrTba(c));
  const passed = sorted.filter(c => !hasUpcomingOrTba(c));

  function matchesFilter(conf) {
    if (filter === 'all') return true;
    return conf.tags.includes(filter);
  }

  // Upcoming section
  if (upcoming.some(matchesFilter)) {
    const divider = document.createElement('div');
    divider.className = 'section-divider';
    divider.textContent = 'Upcoming Deadlines';
    list.appendChild(divider);
  }

  upcoming.forEach(conf => {
    const card = renderCard(conf, now, matchesFilter(conf));
    list.appendChild(card);
    if (matchesFilter(conf)) visibleCount++;
  });

  // Passed section
  if (passed.some(matchesFilter)) {
    const divider = document.createElement('div');
    divider.className = 'section-divider';
    divider.textContent = 'Past Deadlines';
    list.appendChild(divider);
  }

  passed.forEach(conf => {
    const card = renderCard(conf, now, matchesFilter(conf));
    list.appendChild(card);
    if (matchesFilter(conf)) visibleCount++;
  });

  noResults.style.display = visibleCount === 0 ? 'block' : 'none';
}

function renderCard(conf, now, visible) {
  const card = document.createElement('div');
  card.className = 'conf-card' + (visible ? '' : ' hidden');

  const tagsHtml = (conf.tags || []).map(t =>
    `<span class="conf-tag ${t}">${t}</span>`
  ).join('');

  let deadlinesHtml = '';
  const dls = (conf.deadlines && conf.deadlines.length) ? conf.deadlines : [{ label: 'Submission', date: null, note: 'TBA' }];
  dls.forEach(dl => {
    if (!dl.date) {
      deadlinesHtml += '<div class="tba-note">' + dl.label + ': ' + (dl.note || 'TBA') + '</div>';
      return;
    }
    const end = parseDeadlineEnd(dl.date, dl.timezone);
    const isPassed = end <= now;
    const days = daysBetween(now, end);

    let countdownHtml = '';
    let rowClass = '';
    let icon = '';

    if (isPassed) {
      const ago = Math.abs(days);
      const label = ago === 0 ? 'Today' : ago === 1 ? '1 day ago' : `${ago} days ago`;
      countdownHtml = `<span class="countdown imminent">${label}</span>`;
      rowClass = 'passed';
      icon = '';
    } else {
      const isImminent = days <= 14;
      const label = days === 0 ? 'Today!' : days === 1 ? '1 day left' : `${days} days left`;
      countdownHtml = `<span class="countdown ${isImminent ? 'imminent' : 'upcoming'}">${label}</span>`;
      rowClass = 'upcoming';
      icon = `<i class="fa fa-clock-o deadline-clock${isImminent ? ' imminent' : ''}" aria-hidden="true"></i>`;
    }

    const noteHtml = dl.note ? ` <span style="font-size:.75rem;color:#999;">(${dl.note})</span>` : '';

    deadlinesHtml += `
      <div class="deadline-row ${rowClass}">
        <span>${icon}<span class="deadline-label">${dl.label}:</span>
        <span class="deadline-date">${dl.note && dl.note.includes('Expected') ? '~' : ''}${formatDate(dl.date)}${noteHtml}</span></span>
        ${countdownHtml}
      </div>`;
  });

  card.innerHTML = `
    <div class="conf-card-header">
      <div>
        <div class="conf-name">${conf.link ? `<a href="${conf.link}" target="_blank" rel="noopener">${conf.name} <i class="fa fa-external-link" style="font-size:.7em;"></i></a>` : conf.name}</div>
        <div class="conf-full-name">${conf.fullName}</div>
      </div>
      <div class="conf-tags">${tagsHtml}</div>
    </div>
    <div class="conf-meta">
      <span><i class="fa fa-map-marker" aria-hidden="true"></i> ${conf.location}</span>
      <span><i class="fa fa-calendar" aria-hidden="true"></i> ${conf.dates}</span>
    </div>
    <div class="deadline-list">${deadlinesHtml}</div>`;

  return card;
}

/* ----- filter logic ----- */
function initDeadlinesPage() {
  CONFERENCES = window.CONFERENCES || [];
  renderConferences('all');

  document.querySelectorAll('.filter-tag').forEach(tag => {
    tag.addEventListener('click', () => {
      document.querySelectorAll('.filter-tag').forEach(t => t.classList.remove('active'));
      tag.classList.add('active');
      renderConferences(tag.dataset.tag);
    });
  });
}
