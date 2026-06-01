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

const MONTHS = {
  january: 0, february: 1, march: 2, april: 3, may: 4, june: 5,
  july: 6, august: 7, september: 8, october: 9, november: 10, december: 11,
  jan: 0, feb: 1, mar: 2, apr: 3, jun: 5, jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11,
};

function getNextDeadline(conf) {
  const now = new Date();
  let best = null;
  let bestEnd = null;
  for (const dl of conf.deadlines || []) {
    if (!dl.date) continue;
    const end = parseDeadlineEnd(dl.date, dl.timezone);
    if (end && end > now && (!bestEnd || end < bestEnd)) {
      best = dl;
      bestEnd = end;
    }
  }
  return best;
}

function hasSubmissionTba(conf) {
  return (conf.deadlines || []).some((d) => !d.date);
}

function conferenceYear(conf) {
  const m = (conf.name || '').match(/(\d{4})\s*$/);
  if (m) return parseInt(m[1], 10);
  const years = (conf.dates || '').match(/\b(20\d{2})\b/g);
  if (years && years.length) return Math.max(...years.map((y) => parseInt(y, 10)));
  return null;
}

/** Best-effort end of the in-person conference (for grouping). */
function parseConferenceEnd(conf) {
  const d = conf.dates || '';
  if (!d || d === 'TBD' || d === '—') {
    const y = conferenceYear(conf);
    return y ? new Date(Date.UTC(y, 11, 31, 23, 59, 59)) : null;
  }
  const range = d.match(
    /([A-Za-z]+)\s+(\d{1,2})\s*[–-]\s*(\d{1,2}),?\s*(\d{4})/,
  );
  if (range) {
    const mon = MONTHS[range[1].toLowerCase()];
    if (mon !== undefined) {
      return new Date(Date.UTC(parseInt(range[4], 10), mon, parseInt(range[3], 10), 23, 59, 59));
    }
  }
  const single = d.match(/([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})/);
  if (single) {
    const mon = MONTHS[single[1].toLowerCase()];
    if (mon !== undefined) {
      return new Date(Date.UTC(parseInt(single[3], 10), mon, parseInt(single[2], 10), 23, 59, 59));
    }
  }
  const y = conferenceYear(conf);
  return y ? new Date(Date.UTC(y, 11, 31, 23, 59, 59)) : null;
}

function isConferenceOver(conf, now) {
  const end = parseConferenceEnd(conf);
  if (end) return end < now;
  const y = conferenceYear(conf);
  if (y) return y < now.getUTCFullYear();
  return false;
}

function classifyConference(conf, now) {
  if (getNextDeadline(conf)) return 'open';
  if (hasSubmissionTba(conf) && !isConferenceOver(conf, now)) return 'open';
  if (!isConferenceOver(conf, now)) return 'closed';
  return 'past';
}

function sortKeyOpen(conf) {
  const next = getNextDeadline(conf);
  if (next) return parseDeadlineEnd(next.date, next.timezone).getTime();
  return Number.MAX_SAFE_INTEGER;
}

function sortKeyClosed(conf) {
  const end = parseConferenceEnd(conf);
  return end ? end.getTime() : Number.MAX_SAFE_INTEGER;
}

function sortKeyPast(conf) {
  const end = parseConferenceEnd(conf);
  return end ? -end.getTime() : 0;
}

function partitionConferences(confs, now) {
  const buckets = { open: [], closed: [], past: [] };
  for (const c of confs) {
    buckets[classifyConference(c, now)].push(c);
  }
  buckets.open.sort((a, b) => sortKeyOpen(a) - sortKeyOpen(b));
  buckets.closed.sort((a, b) => sortKeyClosed(a) - sortKeyClosed(b));
  buckets.past.sort((a, b) => sortKeyPast(a) - sortKeyPast(b));
  return buckets;
}

/* ----- rendering ----- */
function renderConferences(filter) {
  const list = document.getElementById('conf-list');
  const noResults = document.getElementById('no-results');
  list.innerHTML = '';

  const now = new Date();
  const { open, closed, past } = partitionConferences(CONFERENCES, now);

  let visibleCount = 0;

  function matchesFilter(conf) {
    if (filter === 'all') return true;
    return (conf.tags || []).includes(filter);
  }

  function appendSection(title, conferences) {
    const visible = conferences.filter(matchesFilter);
    if (!visible.length) return;
    const divider = document.createElement('div');
    divider.className = 'section-divider';
    divider.textContent = title;
    list.appendChild(divider);
    conferences.forEach((conf) => {
      const card = renderCard(conf, now, matchesFilter(conf));
      list.appendChild(card);
      if (matchesFilter(conf)) visibleCount++;
    });
  }

  appendSection('Open submissions (soonest deadline first)', open);
  appendSection('Submission closed — conference upcoming', closed);
  appendSection('Past conferences', past);

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

// Exported for local tests (node script strips the let binding).
function sortConferences(confs) {
  const now = new Date();
  const { open, closed, past } = partitionConferences(confs, now);
  return open.concat(closed, past);
}
