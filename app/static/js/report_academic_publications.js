import { apiFetch } from './main.js';

// --- Endpoints ---
const REPORT_ENDPOINT = '/reports/academic-publications/';

// --- DOM Elements ---
const academicTotalCount = document.getElementById('academic-total-count');

// Filters
const filterSearch      = document.getElementById('filter-search');
const filterPubType     = document.getElementById('filter-publication-type');
const filterFinalStatus = document.getElementById('filter-final-status');
const filterSinceDate   = document.getElementById('filter-since-date');
const filterUntilDate   = document.getElementById('filter-until-date');

// Actions & Table
const btnExportExcel    = document.getElementById('btn-export-excel');
const tbody             = document.getElementById('academic-tbody');

// Modal Elements
const modal             = document.getElementById('modal-confirm');
const modalText         = document.getElementById('modal-text');
const modalCancelBtn    = document.getElementById('modal-cancel-btn');

// --- State ---
let expandedRow = null;

/**
 * Initialization
 */
;(async function init() {
  try {
    setupFilters();
    if (modalCancelBtn) modalCancelBtn.onclick = () => modal.classList.add('hidden');

    await loadReport();
  } catch (err) {
    showError(err);
  }
})();

function setupFilters() {
  filterSearch.oninput = debounce(loadReport, 300);
  filterPubType.oninput = debounce(loadReport, 300);

  [
    filterFinalStatus,
    filterSinceDate,
    filterUntilDate
  ].forEach(el => el.onchange = loadReport);
}

/**
 * Main Logic: Fetch data and Render
 */
async function loadReport() {
  collapseExpanded();
  tbody.innerHTML = '<tr><td colspan="7" class="cell-center" style="padding: 2rem; color: #666;">Loading...</td></tr>';

  try {
    const p = buildQueryParams();
    const publications = await apiFetch(`${REPORT_ENDPOINT}?${p.toString()}`);

    renderTable(publications);
  } catch (err) {
    showError(err);
  }
}

function renderTable(list) {
  academicTotalCount.textContent = `(${list.length})`;
  tbody.innerHTML = '';

  if (list.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="cell-center" style="padding: 2rem; color: #666;">No archived academic publications found matching criteria.</td></tr>';
    return;
  }

  list.forEach(item => {
    const tr = document.createElement('tr');
    tr.dataset.id = item.id;

    const titleStr = item.title.length > 55 ? item.title.substring(0, 55) + '...' : item.title;
    const authorsStr = item.authors_raw
      ? (item.authors_raw.length > 30 ? item.authors_raw.substring(0, 30) + '...' : item.authors_raw)
      : '-';
    const journalStr = item.journal_name
      ? (item.journal_name.length > 30 ? item.journal_name.substring(0, 30) + '...' : item.journal_name)
      : '-';
    const typeStr = item.publication_type
      ? (item.publication_type.length > 25 ? item.publication_type.substring(0, 25) + '...' : item.publication_type)
      : '-';
    const pubDate = formatPublished(item);

    // Cluster / Alternate Versions Badge
    const duplicatesCount = (item.duplicates && item.duplicates.length > 0) ? item.duplicates.length : 0;
    const clusterBadge = duplicatesCount > 0
      ? `<span class="status-pill cluster-badge" title="This cluster contains ${duplicatesCount} alternate version(s)">🔗 ${duplicatesCount} Alt Versions</span>`
      : '';

    // Final Status Pill
    let finalStatus = 'Unknown';
    let pillClass = 'pill-internal';

    if (item.is_pushed_to_wp === true) {
      finalStatus = 'PUBLISHED';
      pillClass = 'pill-published';
    } else if (item.is_pushed_to_wp === false) {
      finalStatus = 'KEPT INTERNAL';
      pillClass = 'pill-internal';
    } else if (item.is_relevant === false) {
      finalStatus = 'REJECTED';
      pillClass = 'pill-irrelevant';
    }

    // WordPress Post Link
    const wpLink = item.wp_post_id > 0
      ? `<a href="/wp-admin/post.php?post=${item.wp_post_id}&action=edit" target="_blank" style="color: var(--color-primary); text-decoration: underline;">View ID ${item.wp_post_id}</a>`
      : '-';

    tr.innerHTML = `
      <td><button class="btn expand-btn" title="Preview Publication">+</button> ${clusterBadge}<strong>${titleStr}</strong></td>
      <td>${authorsStr}</td>
      <td>${journalStr}</td>
      <td>${typeStr}</td>
      <td>${pubDate}</td>
      <td class="cell-center"><span class="status-pill ${pillClass}">${finalStatus}</span></td>
      <td class="cell-center">${wpLink}</td>
    `;

    const expandBtn = tr.querySelector('.expand-btn');
    if (expandBtn) {
      expandBtn.onclick = () => togglePreviewRow(item, tr);
    }

    tbody.append(tr);
  });
}

// --- Expanded Preview Row ---

function togglePreviewRow(item, tr) {
  if (expandedRow && expandedRow !== tr) collapseExpanded();

  const btn = tr.querySelector('.expand-btn');
  if (tr.nextElementSibling?.classList.contains('expanded-row')) {
    collapseExpanded();
    return;
  }

  btn.textContent = '–';
  expandedRow = tr;

  const panel = document.createElement('tr');
  panel.classList.add('expanded-row');

  // Header & DOI Link
  const rawTitle = item.title || 'Untitled';
  const safeTitle = rawTitle.length > 250 ? rawTitle.substring(0, 250) + '...' : rawTitle;

  const doiUrl = formatDoiUrl(item.doi);
  const linkHtml = doiUrl
    ? `<a href="${doiUrl}" target="_blank" class="preview-link">🔗 Open DOI (${item.doi})</a>`
    : `<span class="preview-link disabled" title="No DOI provided for this item">🔗 No DOI Link</span>`;

  // Top Metadata Bar
  const metaParts = [
    `<span><strong>Journal / Venue:</strong> ${item.journal_name || '-'}</span>`,
    `<span><strong>Type:</strong> ${item.publication_type || '-'}</span>`,
    `<span><strong>Published:</strong> ${formatPublished(item)}</span>`
  ];
  if (item.swepub_id) metaParts.push(`<span><strong>SwePub ID:</strong> ${item.swepub_id}</span>`);
  if (item.funding_info) metaParts.push(`<span><strong>Funding:</strong> ${item.funding_info}</span>`);

  // Left Column Details
  const authorsText = item.authors_raw || 'No authors listed.';
  const notesText = item.notes || 'No notes.';
  const aiJustification = item.ai_justification || 'No AI justification provided.';

  const aiPillClass = item.ai_recommendation === 'relevant' ? 'pill-relevant'
                    : item.ai_recommendation === 'irrelevant' ? 'pill-irrelevant'
                    : 'pill-uncertain';
  const aiText = item.ai_recommendation ? item.ai_recommendation.toUpperCase() : 'UNKNOWN';
  const aiBadge = `<span class="status-pill ${aiPillClass}">${aiText}</span>`;

  // Right Column Abstract
  const abstractText = item.abstract || 'No abstract available.';

  panel.innerHTML = `
    <td colspan="7">
      <div class="expanded-content">
        <div class="preview-header">
          <h4 class="preview-title">${safeTitle}</h4>${linkHtml}
        </div>

        <div class="preview-meta">
          ${metaParts.join('')}
        </div>

        <div class="preview-grid">
          <div class="preview-col-left">
            <div class="preview-section">
              <h4>Authors</h4>
              <div class="content-box"><p>${authorsText}</p></div>
            </div>

            <div class="preview-section">
              <h4>AI Original Assessment ${aiBadge}</h4>
              <div class="content-box"><p>${aiJustification}</p></div>
            </div>

            <div class="preview-section">
              <h4>Notes</h4>
              <div class="content-box"><p>${notesText}</p></div>
            </div>
          </div>

          <div class="preview-section">
            <h4>Abstract</h4>
            <div class="content-box"><p>${abstractText}</p></div>
          </div>
        </div>

        ${item.duplicates && item.duplicates.length > 0 ? `
        <div class="duplicates-section">
          <h4>Alternate Versions (${item.duplicates.length})</h4>
          <div class="duplicates-list">
            ${item.duplicates.map(dup => {
              const dupDate = formatPublished(dup);
              const dupDoiUrl = formatDoiUrl(dup.doi);
              const dupLink = dupDoiUrl
                ? `<a href="${dupDoiUrl}" target="_blank" class="preview-link" style="margin-left:0.5rem; font-size:0.8rem;">🔗 Open DOI</a>`
                : `<span class="preview-link disabled" style="margin-left:0.5rem; font-size:0.8rem;" title="No DOI">🔗 No DOI</span>`;

              return `
                <div class="duplicate-item">
                  <div class="dup-info">
                    <strong>${dup.journal_name || dup.publication_type || '-'}</strong> | ${dupDate} ${dupLink}<br/>
                    <span style="font-size: 0.85rem; color: #555;">${dup.title}</span>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
        ` : ''}
      </div>
    </td>
  `;

  tr.after(panel);
}

function collapseExpanded() {
  if (!expandedRow) return;
  const btn = expandedRow.querySelector('.expand-btn');
  if (btn) btn.textContent = '+';
  const next = expandedRow.nextElementSibling;
  if (next?.classList.contains('expanded-row')) next.remove();
  expandedRow = null;
}

// --- Exports & Query Builder ---

btnExportExcel.onclick = () => {
  const p = buildQueryParams();
  const exportUrl = `${REPORT_ENDPOINT}export/excel?${p.toString()}`;
  window.location.href = exportUrl;
};

function buildQueryParams() {
  const p = new URLSearchParams();

  if (filterSearch.value.trim()) {
    p.set('search', filterSearch.value.trim());
  }
  if (filterPubType.value.trim()) {
    p.set('publication_type', filterPubType.value.trim());
  }
  if (filterFinalStatus.value) {
    p.set('final_status', filterFinalStatus.value);
  }
  if (filterSinceDate.value) {
    p.set('since_date', `${filterSinceDate.value}T00:00:00`);
  }
  if (filterUntilDate.value) {
    p.set('until_date', `${filterUntilDate.value}T23:59:59`);
  }

  return p;
}

// --- Utilities ---

function formatPublished(item) {
  if (item.published_date) return item.published_date.split('T')[0];
  if (item.published_year) return String(item.published_year);
  return '-';
}

function formatDoiUrl(doi) {
  if (!doi) return null;
  const trimmed = doi.trim();
  if (!trimmed) return null;
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  return `https://doi.org/${trimmed.replace(/^doi:\s*/i, '')}`;
}

function showError(err) {
  if (modalText) {
    modalText.textContent = err.message || String(err);
    const confirmBtn = document.getElementById('modal-confirm-btn');
    if (confirmBtn) confirmBtn.style.display = 'none';
    if (modalCancelBtn) modalCancelBtn.textContent = 'OK';
    modal.classList.remove('hidden');
  } else {
    alert(err.message || String(err));
  }
}

function debounce(fn, delay) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), delay);
  };
}
