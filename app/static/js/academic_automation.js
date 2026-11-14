import { apiFetch } from './main.js';

// ============================================================================
// DOM Elements
// ============================================================================
const systemStatus = document.getElementById('system-status');

// Tabs
const tabBtns = document.querySelectorAll('.tab-btn');
const tabPanes = document.querySelectorAll('.tab-pane');

// Bulk Action Bar
const bulkActionBar = document.getElementById('bulk-action-bar');
const bulkCount = document.getElementById('bulk-count');
const bulkButtons = document.getElementById('bulk-buttons');

// Modals
const modalPub = document.getElementById('modal-publication-form');
const formPub = document.getElementById('form-publication');
const btnAddRecord = document.getElementById('btn-add-record');
const btnCancelPub = document.getElementById('btn-cancel-publication');
const pubFormTitle = document.getElementById('publication-form-title');

const modalConfirm = document.getElementById('modal-confirm');
const modalText = document.getElementById('modal-text');
const modalConfirmBtn = document.getElementById('modal-confirm-btn');
const modalCancelBtn = document.getElementById('modal-cancel-btn');

// Banner
const updateBanner = document.getElementById('update-banner');
const updateBannerText = document.getElementById('update-banner-text');
const btnRefreshData = document.getElementById('btn-refresh-data');

// Actions
const btnSyncSwepub = document.getElementById('btn-sync-swepub');
const btnProcessAll = document.getElementById('btn-process-all');

// ============================================================================
// State Management
// ============================================================================
let currentTab = 'tab-ingestion';
let expandedRow = null;
let currentListData = []; // Store current tab's data for easy reference
let pendingConfirmAction = null;
let lastSyncStatus = null;       // Tracks background SwePub sync job
let lastProcessingStatus = null; // Tracks background AI job
let lastPublishStatus = null;    // Tracks background WP job

// ============================================================================
// Initialization
// ============================================================================
(async function init() {
  // Bind the refresh banner button
  btnRefreshData.onclick = () => {
    updateBanner.classList.add('hidden');
    loadCurrentTab();
  };

  setupTabs();
  setupModals();
  setupGlobalActions();
  setupBulkActions();

  // Load initial data
  await loadActivityLogs();
  loadCurrentTab();

  // Poll activity logs every 15 seconds to catch background task completions
  setInterval(loadActivityLogs, 15000);
})();

// ============================================================================
// Tab Navigation & Data Loading
// ============================================================================
function setupTabs() {
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      // Update active classes
      tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      // Hide all panes, show target
      currentTab = btn.dataset.tab;
      tabPanes.forEach(p => p.classList.add('hidden'));
      document.getElementById(currentTab).classList.remove('hidden');

      // Reset states and load data
      resetBulkSelection();
      collapseExpanded();
      loadCurrentTab();
    });
  });
}

async function loadCurrentTab() {
  const tbody = document.getElementById(`tbody-${currentTab.split('-')[1]}`);
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="7" class="cell-center">Loading...</td></tr>';

  try {
    const params = new URLSearchParams();

    // 1. Build Query Parameters based on Tab rules
    if (currentTab === 'tab-ingestion') {
      params.set('has_processing_error', 'false');
      params.set('is_reviewed', 'false');
    }
    else if (currentTab === 'tab-review') {
      params.set('is_reviewed', 'false');
      params.set('has_processing_error', 'false');
    }
    else if (currentTab === 'tab-publish') {
      params.set('is_reviewed', 'true');
      params.set('is_relevant', 'true');
      params.set('has_processing_error', 'false');
    }
    else if (currentTab === 'tab-quarantine') {
      params.set('has_processing_error', 'true');
    }
    else if (currentTab === 'tab-archive') {
      params.set('is_reviewed', 'true');

      // Calculate two years ago in ISO UTC format
      const twoYearsAgo = new Date();
      twoYearsAgo.setFullYear(twoYearsAgo.getFullYear() - 2);
      params.set('since_date', twoYearsAgo.toISOString());
    }

    // 2. Fetch Data
    let list = await apiFetch(`/academic-publications/?${params.toString()}`);

    // Unified Routing & Filtering Logic (The "Golden Rule")
    list = list.filter(item => {
      // 1. Quarantine Tab Logic
      if (currentTab === 'tab-quarantine') {
        if (!item.has_processing_error) return false;
        // If it's a duplicate, ghost it if the primary has already been reviewed
        if (item.is_duplicate) {
          const primary = list.find(p => p.id === item.duplicate_of_id);
          if (primary && primary.is_reviewed) return false;
        }
        return true;
      }

      // 2. Hide errors from all normal pipeline tabs
      if (item.has_processing_error) return false;

      // 3. GOLDEN RULE: Hide all duplicates from normal pipeline tabs
      if (item.is_duplicate === true) return false;

      // 4. Normal Pipeline Routing (for Primary Items and un-evaluated items)
      if (currentTab === 'tab-ingestion') return !item.is_reviewed && !item.ai_recommendation;
      if (currentTab === 'tab-review') return !item.is_reviewed && item.ai_recommendation;
      if (currentTab === 'tab-publish') return item.is_reviewed && item.is_relevant && item.is_pushed_to_wp === null;
      if (currentTab === 'tab-archive') return item.is_reviewed && (!item.is_relevant || item.is_pushed_to_wp !== null);

      return false;
    });

    currentListData = list;

    // 3. Render Data
    tbody.innerHTML = '';

    // Disable the "Process All" button if there's nothing to process
    if (currentTab === 'tab-ingestion' && btnProcessAll) {
      btnProcessAll.disabled = list.length === 0;
    }

    if (list.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="cell-center" style="padding: 2rem; color: #666;">No publications found for this stage.</td></tr>';
      return;
    }

    list.forEach(item => {
      const tr = document.createElement('tr');
      tr.dataset.id = item.id;

      const titleStr = item.title.length > 60 ? item.title.substring(0, 60) + '...' : item.title;
      const authorsStr = item.authors_raw
        ? (item.authors_raw.length > 35 ? item.authors_raw.substring(0, 35) + '...' : item.authors_raw)
        : '-';
      const journalStr = item.journal_name
        ? (item.journal_name.length > 35 ? item.journal_name.substring(0, 35) + '...' : item.journal_name)
        : '-';
      const pubType = item.publication_type || '-';
      const pubDate = formatPublished(item);

      // Cluster Badge Logic
      const duplicatesCount = (item.duplicates && item.duplicates.length > 0) ? item.duplicates.length : 0;
      const clusterBadge = duplicatesCount > 0
        ? `<span class="status-pill cluster-badge" title="This cluster contains ${duplicatesCount} alternate version(s)">🔗 ${duplicatesCount} Alt Versions</span>`
        : '';

      let html = `<td class="cell-center"><input type="checkbox" class="row-checkbox" value="${item.id}" /></td>`;

      if (currentTab === 'tab-ingestion') {
        html += `
          <td>${clusterBadge}<strong>${titleStr}</strong></td>
          <td>${authorsStr}</td>
          <td>${journalStr}</td>
          <td>${pubType}</td>
          <td>${pubDate}</td>
          <td class="cell-actions">
            <button class="btn btn-edit">Edit</button>
            <button class="btn btn-delete">Delete</button>
          </td>`;
      }
      else if (currentTab === 'tab-review') {
        const pillClass = item.ai_recommendation === 'relevant' ? 'pill-relevant'
                        : item.ai_recommendation === 'irrelevant' ? 'pill-irrelevant' : 'pill-uncertain';
        const aiText = item.ai_recommendation ? item.ai_recommendation.toUpperCase() : 'UNKNOWN';
        html += `
          <td class="cell-center"><span class="status-pill ${pillClass}">${aiText}</span></td>
          <td><button class="btn expand-btn" title="Preview Abstract & Details">+</button> ${clusterBadge}<strong>${titleStr}</strong></td>
          <td>${authorsStr}</td>
          <td>${journalStr}</td>
          <td>${pubDate}</td>
          <td class="cell-actions">
            <button class="btn btn-approve" style="background: #2e7d32; color: #fff;">Mark Relevant</button>
            <button class="btn btn-reject" style="background: #c62828; color: #fff;">Mark Irrelevant</button>
          </td>`;
      }
      else if (currentTab === 'tab-publish') {
        html += `
          <td><button class="btn expand-btn" title="Preview Publication">+</button> <strong>${titleStr}</strong></td>
          <td>${authorsStr}</td>
          <td>${journalStr}</td>
          <td>${pubDate}</td>
          <td class="cell-actions">
            <button class="btn btn-push-wp" style="background: #0073aa; color: #fff;">Push to WP</button>
            <button class="btn btn-secondary btn-keep-internal">Keep Internal</button>
          </td>`;
      }
      else if (currentTab === 'tab-quarantine') {
        const errorMsg = item.processing_error_msg || 'Unknown error';
        const safeError = errorMsg.length > 50 ? errorMsg.substring(0, 50) + '...' : errorMsg;

        html += `
          <td><button class="btn expand-btn" title="Preview Error">+</button> <strong>${titleStr}</strong></td>
          <td class="error-text" style="color: #c62828;">${safeError}</td>
          <td class="cell-actions">
            <button class="btn btn-requeue" style="background: var(--color-primary); color: #fff;">Requeue</button>
            <button class="btn btn-edit">Edit</button>
            <button class="btn btn-delete">Delete</button>
          </td>`;
      }
      else if (currentTab === 'tab-archive') {
        let finalStatus = 'Unknown';
        let pillClass = 'pill-internal';

        if (item.is_pushed_to_wp === true) { finalStatus = 'PUBLISHED'; pillClass = 'pill-published'; }
        else if (item.is_pushed_to_wp === false) { finalStatus = 'KEPT INTERNAL'; pillClass = 'pill-internal'; }
        else if (item.is_relevant === false) { finalStatus = 'REJECTED'; pillClass = 'pill-irrelevant'; }

        const wpLink = item.wp_post_id > 0
          ? `<a href="/wp-admin/post.php?post=${item.wp_post_id}&action=edit" target="_blank" style="color: var(--color-primary); text-decoration: underline;">View ID ${item.wp_post_id}</a>`
          : '-';

        html = `
          <td><button class="btn expand-btn" title="Preview Publication">+</button> <strong>${titleStr}</strong></td>
          <td>${journalStr}</td>
          <td>${pubDate}</td>
          <td class="cell-center"><span class="status-pill ${pillClass}">${finalStatus}</span></td>
          <td class="cell-center">${wpLink}</td>`;
      }

      tr.innerHTML = html;
      attachRowHandlers(tr, item);
      tbody.append(tr);
    });

  } catch (err) {
    showError(err);
  }
}

// ============================================================================
// Row-Level Handlers & Previews
// ============================================================================
function attachRowHandlers(tr, item) {
  // Checkboxes
  const cb = tr.querySelector('.row-checkbox');
  if (cb) cb.addEventListener('change', updateBulkActionBar);

  // Buttons mapped by class
  const bind = (selector, handler) => {
    const btn = tr.querySelector(selector);
    if (btn) btn.onclick = () => handler(item, tr);
  };

  bind('.btn-edit', openEditModal);
  bind('.btn-delete', (i) => confirmAction(`Delete "${i.title}" permanently?`, () => deleteRecord(i.id)));

  bind('.expand-btn', togglePreviewRow);

  bind('.btn-approve', (i) => updateRecord(i.id, { is_reviewed: true, is_relevant: true })); // Instant (Safe)
  bind('.btn-reject', (i) => confirmAction(`Reject "${i.title}" and archive it as irrelevant?`, () => updateRecord(i.id, { is_reviewed: true, is_relevant: false }))); // Confirmed (Terminal)

  bind('.btn-push-wp', (i) => confirmAction(`Publish "${i.title}" to WordPress now?`, () => triggerWpPush([i.id])));
  bind('.btn-keep-internal', (i) => confirmAction(`Archive "${i.title}" internally (will not publish)?`, () => updateRecord(i.id, { is_pushed_to_wp: false })));

  bind('.btn-requeue', (i) => confirmAction(`Clear the error for "${i.title}" and return it to the processing pipeline?`, () => updateRecord(i.id, { has_processing_error: false, processing_error_msg: null })));
}

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

  // Safe truncation for Title
  const rawTitle = item.title || 'Untitled';
  const safeTitle = rawTitle.length > 250 ? rawTitle.substring(0, 250) + '...' : rawTitle;

  // Abstract & AI Justification
  const abstractText = item.abstract || 'No abstract available.';
  const aiJustification = item.ai_justification || 'No AI justification provided.';

  // DOI Link with disabled fallback
  const doiUrl = formatDoiUrl(item.doi);
  const linkHtml = doiUrl
    ? `<a href="${doiUrl}" target="_blank" class="preview-link">🔗 Open DOI (${item.doi})</a>`
    : `<span class="preview-link disabled" title="No DOI provided for this item">🔗 No DOI Link</span>`;

  // Academic Metadata Bar
  const metaParts = [
    `<span><strong>Authors:</strong> ${item.authors_raw || '-'}</span>`,
    `<span><strong>Journal / Venue:</strong> ${item.journal_name || '-'}</span>`,
    `<span><strong>Type:</strong> ${item.publication_type || '-'}</span>`,
    `<span><strong>Published:</strong> ${formatPublished(item)}</span>`
  ];
  if (item.swepub_id) metaParts.push(`<span><strong>SwePub ID:</strong> ${item.swepub_id}</span>`);
  if (item.funding_info) metaParts.push(`<span><strong>Funding:</strong> ${item.funding_info}</span>`);

  panel.innerHTML = `
    <td colspan="7">
      <div class="expanded-content">
        <div class="preview-header">
          <h4 class="preview-title">${safeTitle}</h4>${linkHtml}
        </div>
        <div class="preview-meta">
          ${metaParts.join('')}
        </div>
        <div class="preview-grid" ${(currentTab === 'tab-publish' || currentTab === 'tab-archive') ? 'style="grid-template-columns: 1fr;"' : ''}>
          
          ${currentTab === 'tab-quarantine' ? `
          <div class="preview-section" style="grid-column: 1 / -1; margin-bottom: 1rem;">
            <h4 style="color: #c62828;">Processing Error</h4>
            <div class="content-box" style="border-left: 4px solid #c62828; background: #ffebee;">
              <p style="color: #b71c1c; font-family: monospace; white-space: pre-wrap; margin: 0;">${item.processing_error_msg || 'Unknown error'}</p>
            </div>
          </div>
          ` : ''}
          
          ${currentTab === 'tab-review' ? `
          <div class="preview-section">
            <h4>AI Justification</h4>
            <div class="content-box"><p>${aiJustification}</p></div>
          </div>
          ` : ''}
          <div class="preview-section">
            <h4>Abstract</h4>
            <div class="content-box"><p>${abstractText}</p></div>
          </div>
        </div>
        
        ${item.duplicates && item.duplicates.length > 0 && currentTab !== 'tab-publish' && currentTab !== 'tab-archive' ? `
        <div class="duplicates-section">
          <h4 style="margin-bottom: 0.75rem; color: #333;">Alternate Versions</h4>
          <div class="duplicates-list">
            ${item.duplicates.map(dup => {
              const dupDate = formatPublished(dup);
              const dupDoiUrl = formatDoiUrl(dup.doi);
              const dupLink = dupDoiUrl 
                ? `<a href="${dupDoiUrl}" target="_blank" class="preview-link" style="margin-left:0.5rem; font-size:0.8rem;">🔗 Open DOI</a>`
                : `<span class="preview-link disabled" style="margin-left:0.5rem; font-size:0.8rem;" title="No DOI">🔗 No DOI</span>`;
              
              const promoteAction = dup.has_processing_error 
                ? `<span class="status-pill pill-warning" style="font-size:0.75rem;">⚠️ Fix in Quarantine</span>`
                : `<button class="btn btn-promote" data-id="${dup.id}">⭐ Promote to Main</button>`;
                
              return `
                <div class="duplicate-item">
                  <div class="dup-info">
                    <strong>${dup.journal_name || dup.publication_type || '-'}</strong> | ${dupDate} ${dupLink}<br/>
                    <span style="font-size: 0.85rem; color: #555;">${dup.title}</span>
                  </div>
                  <div class="dup-action">${promoteAction}</div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
        ` : ''}
        
        ${currentTab !== 'tab-archive' ? `
        <div class="preview-actions">
          ${currentTab === 'tab-publish' ? `<button class="btn btn-secondary btn-panel-demote" style="margin-right: 0.5rem; background: #c62828;">↩️ Send Back to Review</button>` : ''}
          <button class="btn btn-secondary btn-panel-edit">✏️ Edit Record</button>
        </div>
        ` : ''}
      </div>
    </td>
  `;

  // Bind the inline Edit button (if it exists)
  const btnEdit = panel.querySelector('.btn-panel-edit');
  if (btnEdit) {
    btnEdit.onclick = () => openEditModal(item);
  }

  // Bind the Demote button (if it exists)
  const btnDemote = panel.querySelector('.btn-panel-demote');
  if (btnDemote) {
    btnDemote.onclick = () => confirmAction(`Send this publication back to the Needs Review tab?`, () => updateRecord(item.id, { is_reviewed: false }));
  }

  // Bind the promote buttons
  panel.querySelectorAll('.btn-promote').forEach(btn => {
    btn.onclick = () => promoteDuplicate(btn.getAttribute('data-id'));
  });

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

// ============================================================================
// Bulk Actions
// ============================================================================
function setupBulkActions() {
  // Select All Toggles
  document.querySelectorAll('.select-all').forEach(cb => {
    cb.addEventListener('change', (e) => {
      const targetId = e.target.dataset.target;
      const tbody = document.getElementById(targetId);
      const rowCbs = tbody.querySelectorAll('.row-checkbox');
      rowCbs.forEach(rowCb => rowCb.checked = e.target.checked);
      updateBulkActionBar();
    });
  });
}

function updateBulkActionBar() {
  const tbody = document.getElementById(`tbody-${currentTab.split('-')[1]}`);
  if (!tbody) return;

  const allBoxes = tbody.querySelectorAll('.row-checkbox');
  const checkedBoxes = Array.from(allBoxes).filter(cb => cb.checked);
  const checked = checkedBoxes.map(cb => parseInt(cb.value));

  // Update the Select All checkbox state (Indeterminate logic)
  const selectAllCb = document.querySelector(`.select-all[data-target="${tbody.id}"]`);
  if (selectAllCb) {
    if (checked.length === 0) {
      selectAllCb.checked = false;
      selectAllCb.indeterminate = false;
    } else if (checked.length === allBoxes.length) {
      selectAllCb.checked = true;
      selectAllCb.indeterminate = false;
    } else {
      selectAllCb.checked = false;
      selectAllCb.indeterminate = true;
    }
  }

  if (checked.length === 0) {
    bulkActionBar.classList.add('hidden');
    return;
  }

  bulkCount.textContent = `${checked.length} item(s) selected`;
  bulkActionBar.classList.remove('hidden');

  // Render context-aware buttons
  bulkButtons.innerHTML = '';

  if (currentTab === 'tab-ingestion') {
    bulkButtons.innerHTML = `
      <button id="bulk-process" class="btn" style="background: var(--color-primary); color: #fff;">Process Selected</button>
      <button id="bulk-delete" class="btn" style="background: #c62828; color: #fff;">Delete Selected</button>
    `;

    document.getElementById('bulk-process').onclick = () => {
      confirmAction(`Send ${checked.length} selected item(s) to AI Processing?`, () => {
        triggerProcessing(checked);
      });
    };

    document.getElementById('bulk-delete').onclick = () => {
      confirmAction(`Permanently delete ${checked.length} selected item(s)?`, () => bulkUpdate(checked, { action: 'delete' }));
    };
  }
  else if (currentTab === 'tab-review') {
    bulkButtons.innerHTML = `
      <button id="bulk-approve" class="btn" style="background: #2e7d32; color: #fff;">Mark Relevant</button>
      <button id="bulk-reject" class="btn" style="background: #c62828; color: #fff;">Mark Irrelevant</button>
    `;
    document.getElementById('bulk-approve').onclick = () => {
      confirmAction(`Mark ${checked.length} selected item(s) as Relevant and send to the publish queue?`, () => bulkUpdate(checked, { is_reviewed: true, is_relevant: true }));
    };
    document.getElementById('bulk-reject').onclick = () => {
      confirmAction(`Reject and archive ${checked.length} selected item(s) as Irrelevant?`, () => bulkUpdate(checked, { is_reviewed: true, is_relevant: false }));
    };
  }
  else if (currentTab === 'tab-publish') {
    bulkButtons.innerHTML = `
      <button id="bulk-push-wp" class="btn" style="background: #0073aa; color: #fff;">Push Selected to WP</button>
      <button id="bulk-keep-internal" class="btn btn-secondary">Keep Selected Internal</button>
    `;
    document.getElementById('bulk-push-wp').onclick = () => {
      confirmAction(`Publish ${checked.length} selected item(s) to WordPress?`, () => triggerWpPush(checked));
    };
    document.getElementById('bulk-keep-internal').onclick = () => {
      confirmAction(`Archive ${checked.length} selected item(s) internally?`, () => bulkUpdate(checked, { is_pushed_to_wp: false }));
    };
  }
  else if (currentTab === 'tab-quarantine') {
    bulkButtons.innerHTML = `
      <button id="bulk-requeue" class="btn" style="background: var(--color-primary); color: #fff;">Requeue Selected</button>
      <button id="bulk-delete" class="btn" style="background: #c62828; color: #fff;">Delete Selected</button>
    `;
    document.getElementById('bulk-requeue').onclick = () => {
      confirmAction(`Clear errors and return ${checked.length} selected item(s) to the pipeline?`, () => bulkUpdate(checked, { has_processing_error: false, processing_error_msg: null }));
    };
    document.getElementById('bulk-delete').onclick = () => {
      confirmAction(`Permanently delete ${checked.length} selected error item(s)?`, () => bulkUpdate(checked, { action: 'delete' }));
    };
  }
}

function resetBulkSelection() {
  document.querySelectorAll('.select-all').forEach(cb => {
    cb.checked = false;
    cb.indeterminate = false;
  });
  document.querySelectorAll('.row-checkbox').forEach(cb => cb.checked = false);
  bulkActionBar.classList.add('hidden');
}

async function bulkUpdate(ids, payload) {
  try {
    for (const id of ids) {
      if (payload.action === 'delete') {
        await apiFetch(`/academic-publications/${id}`, { method: 'DELETE' });
      } else {
        await apiFetch(`/academic-publications/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }
    }
    resetBulkSelection();
    loadCurrentTab();
  } catch (err) {
    showError(err);
  }
}

// ============================================================================
// Modals & Forms (CRUD)
// ============================================================================
function setupModals() {
  // Global Add Record
  btnAddRecord.onclick = () => {
    formPub.reset();
    delete formPub.dataset.editId;
    pubFormTitle.textContent = 'Add Academic Publication';
    modalPub.classList.remove('hidden');
  };
  btnCancelPub.onclick = () => modalPub.classList.add('hidden');

  // Publication Form Submit (Add/Edit)
  formPub.onsubmit = async (e) => {
    e.preventDefault();
    const editId = formPub.dataset.editId;

    // Convert datetime-local string to standard ISO format if provided
    let pubDate = formPub.published_date.value;
    if (pubDate && !pubDate.includes('Z') && !pubDate.includes('+')) {
      pubDate = new Date(pubDate).toISOString();
    } else if (!pubDate) {
      pubDate = null;
    }

    const pubYearRaw = formPub.published_year.value.trim();
    const pubYear = pubYearRaw ? parseInt(pubYearRaw, 10) : null;

    const payload = {
      title: formPub.title.value.trim(),
      journal_name: formPub.journal_name.value.trim() || null,
      authors_raw: formPub.authors_raw.value.trim() || null,
      publication_type: formPub.publication_type.value.trim() || null,
      published_year: pubYear,
      published_date: pubDate,
      doi: formPub.doi.value.trim() || null,
      swepub_id: formPub.swepub_id.value.trim() || null,
      funding_info: formPub.funding_info.value.trim() || null,
      abstract: formPub.abstract.value.trim() || null,
      notes: formPub.notes.value.trim() || null
    };

    try {
      const url = editId ? `/academic-publications/${editId}` : '/academic-publications/';
      const method = editId ? 'PUT' : 'POST';

      await apiFetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      modalPub.classList.add('hidden');
      loadCurrentTab();
    } catch (err) {
      showError(err);
    }
  };

  // Confirm Modal Cancel
  modalCancelBtn.onclick = () => {
    pendingConfirmAction = null;
    modalConfirm.classList.add('hidden');
  };
}

function openEditModal(item) {
  formPub.reset();
  formPub.dataset.editId = item.id;
  pubFormTitle.textContent = `Edit: ${item.title}`;

  formPub.title.value = item.title || '';
  formPub.journal_name.value = item.journal_name || '';
  formPub.authors_raw.value = item.authors_raw || '';
  formPub.publication_type.value = item.publication_type || '';
  formPub.published_year.value = item.published_year || '';

  if (item.published_date) {
    // Format to YYYY-MM-DDThh:mm for datetime-local input
    formPub.published_date.value = item.published_date.substring(0, 16);
  } else {
    formPub.published_date.value = '';
  }

  formPub.doi.value = item.doi || '';
  formPub.swepub_id.value = item.swepub_id || '';
  formPub.funding_info.value = item.funding_info || '';
  formPub.abstract.value = item.abstract || '';
  formPub.notes.value = item.notes || '';

  modalPub.classList.remove('hidden');
}

// ============================================================================
// Global Actions (Triggers)
// ============================================================================
function setupGlobalActions() {
  if (btnSyncSwepub) {
    btnSyncSwepub.onclick = () => {
      confirmAction('Trigger background synchronization with SwePub now?', () => {
        triggerSwepubSync();
      });
    };
  }

  if (btnProcessAll) {
    btnProcessAll.onclick = () => {
      const tbody = document.getElementById('tbody-ingestion');
      if (!tbody) return;

      const allCheckboxes = Array.from(tbody.querySelectorAll('.row-checkbox'));

      if (allCheckboxes.length === 0) {
        showModal('There are no pending items to process.');
        return;
      }

      confirmAction(`Are you sure you want to send ALL ${allCheckboxes.length} item(s) to AI Processing?`, () => {
        triggerProcessing(allCheckboxes.map(cb => parseInt(cb.value)));
      });
    };
  }
}

async function updateRecord(id, payload) {
  try {
    await apiFetch(`/academic-publications/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    loadCurrentTab();
  } catch (err) { showError(err); }
}

async function deleteRecord(id) {
  try {
    await apiFetch(`/academic-publications/${id}`, { method: 'DELETE' });
    loadCurrentTab();
  } catch (err) { showError(err); }
}

// ============================================================================
// Utilities & UI Helpers
// ============================================================================
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

async function triggerSwepubSync() {
  try {
    await apiFetch('/academic-publications/actions/sync-swepub', {
      method: 'POST'
    });
    showSystemStatus('SwePub Sync Started...');
    loadActivityLogs(); // Grabs the new IN_PROGRESS state immediately
  } catch (err) {
    showError(err);
  }
}

async function triggerProcessing(ids) {
  try {
    await apiFetch('/academic-publications/actions/process-pending', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ publication_ids: ids })
    });
    showSystemStatus('AI Processing Started...');
    loadActivityLogs();   // Grabs the new IN_PROGRESS state immediately
    resetBulkSelection(); // Instantly unchecks boxes for local UI feedback
  } catch (err) {
    showError(err);
  }
}

async function triggerWpPush(ids) {
  try {
    await apiFetch('/academic-publications/actions/push-to-wp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ publication_ids: ids })
    });
    showSystemStatus('WP Push Started...');
    loadActivityLogs();   // Grabs the new IN_PROGRESS state immediately
    resetBulkSelection(); // Instantly unchecks boxes for local UI feedback
  } catch (err) {
    showError(err);
  }
}

async function promoteDuplicate(duplicateId) {
  confirmAction('Promote this alternate version to become the Primary publication for this cluster?', async () => {
    try {
      await apiFetch(`/academic-publications/${duplicateId}/actions/promote`, { method: 'POST' });
      showSystemStatus('Item successfully promoted to Primary.');
      loadActivityLogs(); // Update the log bar
      loadCurrentTab();   // Refresh the table UI
    } catch (err) {
      showError(err);
    }
  });
}

async function loadActivityLogs() {
  const elSync = document.getElementById('activity-sync');
  const elProcessing = document.getElementById('activity-processing');
  const elPublish = document.getElementById('activity-publish');

  try {
    // Fetch recent logs
    const logs = await apiFetch('/automation-logs/?limit=100');

    // Helper to find the most recent log for a specific action type
    const getLatest = (type) => logs.find(log => log.action_type === type);

    const syncLog = getLatest('academic_sync');
    const procLog = getLatest('academic_processing');
    const pubLog = getLatest('academic_publish');

    // Detect if SwePub Sync just finished
    if (syncLog) {
      if (lastSyncStatus === 'in_progress' && syncLog.status !== 'in_progress') {
        const isWarning = syncLog.status !== 'success';
        showUpdateBanner(`✨ SwePub Sync concluded (${syncLog.status.toUpperCase()}).`, isWarning);
      }
      lastSyncStatus = syncLog.status;
    }

    // Detect if Processing just finished
    if (procLog) {
      if (lastProcessingStatus === 'in_progress' && procLog.status !== 'in_progress') {
        const isWarning = procLog.status !== 'success';
        showUpdateBanner(`✨ AI Processing concluded (${procLog.status.toUpperCase()}).`, isWarning);
      }
      lastProcessingStatus = procLog.status;
    }

    // Detect if WP Push just finished
    if (pubLog) {
      if (lastPublishStatus === 'in_progress' && pubLog.status !== 'in_progress') {
        const isWarning = pubLog.status !== 'success';
        showUpdateBanner(`✨ WordPress Push concluded (${pubLog.status.toUpperCase()}).`, isWarning);
      }
      lastPublishStatus = pubLog.status;
    }

    // Helper to format the log into readable HTML
    const formatLog = (log) => {
      if (!log) return '<em>None yet</em>';

      // Ensure the timestamp is treated as UTC if the backend sends a naive datetime string
      let ts = log.timestamp;
      if (!/(Z|[+-]\d{2}:?\d{2})$/.test(ts)) {
        ts += 'Z';
      }

      const dateOpts = { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
      const dateStr = new Date(ts).toLocaleString(undefined, dateOpts);

      const userStr = log.user ? log.user.username : (log.trigger_source === 'system' ? 'System' : 'Unknown');

      const statusIcon = log.status === 'success' ? '✅' :
                         log.status === 'failed' ? '❌' :
                         log.status === 'in_progress' ? '⏳' : '⚠️';

      return `<em>${dateStr} by ${userStr} ${statusIcon}</em>`;
    };

    // Update the UI
    elSync.innerHTML = `SwePub Sync: ${formatLog(syncLog)}`;
    elProcessing.innerHTML = `Processing: ${formatLog(procLog)}`;
    elPublish.innerHTML = `WP Push: ${formatLog(pubLog)}`;

  } catch (err) {
    console.warn("Could not load activity logs", err);
    const errHtml = '<em>Unavailable</em>';
    elSync.innerHTML = `SwePub Sync: ${errHtml}`;
    elProcessing.innerHTML = `Processing: ${errHtml}`;
    elPublish.innerHTML = `WP Push: ${errHtml}`;
  }
}

function showSystemStatus(msg) {
  systemStatus.textContent = msg;
  systemStatus.style.color = 'var(--color-accent)';
  setTimeout(() => { systemStatus.textContent = ''; }, 5000);
}

function confirmAction(message, callback) {
  modalText.textContent = message;
  modalConfirmBtn.style.display = 'inline-block';
  modalCancelBtn.textContent = 'Cancel';
  pendingConfirmAction = async () => {
    await callback();
    modalConfirm.classList.add('hidden');
    pendingConfirmAction = null;
  };
  modalConfirmBtn.onclick = pendingConfirmAction;
  modalConfirm.classList.remove('hidden');
}

function showModal(msg, isInfo = false) {
  modalText.innerText = msg; // innerText respects \n
  modalConfirmBtn.style.display = 'none';
  modalCancelBtn.textContent = 'OK';
  modalConfirm.classList.remove('hidden');
}

function showError(err) {
  const msg = err instanceof Error ? err.message : String(err);
  showModal(`Error:\n${msg}`);
}

function showUpdateBanner(msg, isWarning = false) {
  updateBannerText.textContent = msg;
  if (isWarning) {
    updateBanner.classList.add('warning');
  } else {
    updateBanner.classList.remove('warning');
  }
  updateBanner.classList.remove('hidden');
}
