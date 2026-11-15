import { apiFetch } from './main.js';

// --- Endpoints ---
const REPORT_ENDPOINT = '/reports/media-publications/';

// --- DOM Elements ---
const mediaTotalCount   = document.getElementById('media-total-count');

// Filters
const filterSearch      = document.getElementById('filter-search');
const filterFinalStatus = document.getElementById('filter-final-status');
const filterSinceDate   = document.getElementById('filter-since-date');
const filterUntilDate   = document.getElementById('filter-until-date');

// Actions & Table
const btnExportExcel    = document.getElementById('btn-export-excel');
const tbody             = document.getElementById('media-tbody');

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
  tbody.innerHTML = '<tr><td colspan="5" class="cell-center" style="padding: 2rem; color: #666;">Loading...</td></tr>';

  try {
    const p = buildQueryParams();
    const publications = await apiFetch(`${REPORT_ENDPOINT}?${p.toString()}`);

    renderTable(publications);
  } catch (err) {
    showError(err);
  }
}

function renderTable(list) {
  mediaTotalCount.textContent = `(${list.length})`;
  tbody.innerHTML = '';

  if (list.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="cell-center" style="padding: 2rem; color: #666;">No archived media publications found matching criteria.</td></tr>';
    return;
  }

  list.forEach(item => {
    const tr = document.createElement('tr');
    tr.dataset.id = item.id;

    const titleStr = item.title.length > 65 ? item.title.substring(0, 65) + '...' : item.title;
    const pubDate = item.published_date ? item.published_date.split('T')[0] : '';

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
      <td><button class="btn expand-btn" title="Preview Article">+</button> ${clusterBadge}<strong>${titleStr}</strong></td>
      <td>${item.source_name || '-'}</td>
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

  // Header & Link
  const rawTitle = item.title || 'Untitled';
  const safeTitle = rawTitle.length > 250 ? rawTitle.substring(0, 250) + '...' : rawTitle;

  const linkHtml = item.content_url
    ? `<a href="${item.content_url}" target="_blank" class="preview-link">🔗 Open Original Article</a>`
    : `<span class="preview-link disabled" title="No URL provided for this item">🔗 No Original Link</span>`;

  // Left Column Metadata
  const citedMembers = item.cited_members_parsed || 'None listed.';
  const notesText = item.notes || 'No notes.';
  const aiJustification = item.ai_justification || 'No AI justification provided.';

  const aiPillClass = item.ai_recommendation === 'relevant' ? 'pill-relevant'
                    : item.ai_recommendation === 'irrelevant' ? 'pill-irrelevant'
                    : 'pill-uncertain';
  const aiText = item.ai_recommendation ? item.ai_recommendation.toUpperCase() : 'UNKNOWN';
  const aiBadge = `<span class="status-pill ${aiPillClass}">${aiText}</span>`;

  // Right Column Full Text
  const fullBody = item.article_body || 'No full text available.';

  panel.innerHTML = `
    <td colspan="5">
      <div class="expanded-content">
        <div class="preview-header">
          <h4 class="preview-title">${safeTitle}</h4>${linkHtml}
        </div>

        <div class="preview-grid">
          <div class="preview-col-left">
            <div class="preview-section">
              <h4>Cited Members</h4>
              <div class="content-box"><p>${citedMembers}</p></div>
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
            <h4>Original Text (Full)</h4>
            <div class="content-box"><p>${fullBody}</p></div>
          </div>
        </div>

        ${item.duplicates && item.duplicates.length > 0 ? `
        <div class="duplicates-section">
          <h4>Alternate Versions (${item.duplicates.length})</h4>
          <div class="duplicates-list">
            ${item.duplicates.map(dup => {
              const dupDate = dup.published_date ? dup.published_date.split('T')[0] : '';
              const dupLink = dup.content_url
                ? `<a href="${dup.content_url}" target="_blank" class="preview-link" style="margin-left:0.5rem; font-size:0.8rem;">🔗 Open</a>`
                : `<span class="preview-link disabled" style="margin-left:0.5rem; font-size:0.8rem;" title="No URL">🔗 No Link</span>`;

              return `
                <div class="duplicate-item">
                  <div class="dup-info">
                    <strong>${dup.source_name || '-'}</strong> | ${dupDate} ${dupLink}<br/>
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
