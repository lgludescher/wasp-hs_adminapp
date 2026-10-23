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
const modalUpload = document.getElementById('modal-upload');
const formUpload = document.getElementById('form-upload');
const btnShowUpload = document.getElementById('btn-show-upload');
const btnCancelUpload = document.getElementById('btn-cancel-upload');

const modalPub = document.getElementById('modal-publication-form');
const formPub = document.getElementById('form-publication');
const btnAddRecord = document.getElementById('btn-add-record');
const btnCancelPub = document.getElementById('btn-cancel-publication');
const pubFormTitle = document.getElementById('publication-form-title');

const modalConfirm = document.getElementById('modal-confirm');
const modalText = document.getElementById('modal-text');
const modalConfirmBtn = document.getElementById('modal-confirm-btn');
const modalCancelBtn = document.getElementById('modal-cancel-btn');

// Search Generator
const btnGenerateSearch = document.getElementById('btn-generate-search');
const searchOutput = document.getElementById('search-string-output');
const btnCopySearch = document.getElementById('btn-copy-search');

// Banner
const updateBanner = document.getElementById('update-banner');
const updateBannerText = document.getElementById('update-banner-text');
const btnRefreshData = document.getElementById('btn-refresh-data');

// Actions
const btnProcessAll = document.getElementById('btn-process-all');
const btnPushAllWp = document.getElementById('btn-push-all-wp');

// ============================================================================
// State Management
// ============================================================================
let currentTab = 'tab-ingestion';
let expandedRow = null;
let currentListData = []; // Store current tab's data for easy reference
let pendingConfirmAction = null;
let lastProcessingStatus = null; // Tracks background AI job
let lastPublishStatus = null;    // Tracks background WP job

// ============================================================================
// Initialization
// ============================================================================
(async function init() {
  // Bind the new refresh banner button
  btnRefreshData.onclick = () => {
    updateBanner.classList.add('hidden');
    loadCurrentTab();
  };

  setupTabs();
  setupModals();
  setupGlobalActions();
  setupBulkActions();
  setupSearchGenerator();

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
  tbody.innerHTML = '<tr><td colspan="6" class="cell-center">Loading...</td></tr>';

  try {
    const params = new URLSearchParams();

    // 1. Build Query Parameters based on Tab rules
    if (currentTab === 'tab-ingestion') {
      // In backend: ai_recommendation might be handled via a custom string or omit if null.
      // Assuming backend handles explicit false/null filters.
      params.set('has_processing_error', 'false');
      // For ingestion, we want unprocessed items
      params.set('is_reviewed', 'false');
    }
    else if (currentTab === 'tab-review') {
      params.set('is_reviewed', 'false');
      params.set('has_processing_error', 'false');
    }
    else if (currentTab === 'tab-publish') {
      params.set('is_reviewed', 'true');
      params.set('is_relevant', 'true');
      params.set('is_published_to_wp', 'false');
      params.set('has_processing_error', 'false');
    }
    else if (currentTab === 'tab-quarantine') {
      params.set('has_processing_error', 'true');
    }
    else if (currentTab === 'tab-archive') {
      // Archive is a mix of terminal states. We fetch reviewed items and filter locally
      // if the backend doesn't support complex OR queries via URL params.
      params.set('is_reviewed', 'true');
    }

    // 2. Fetch Data
    let list = await apiFetch(`/media-publications/?${params.toString()}`);

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
      if (currentTab === 'tab-publish') return item.is_reviewed && item.is_relevant && !item.wp_post_id;
      if (currentTab === 'tab-archive') return item.is_reviewed && (!item.is_relevant || item.wp_post_id);

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
      tbody.innerHTML = '<tr><td colspan="6" class="cell-center" style="padding: 2rem; color: #666;">No publications found for this stage.</td></tr>';
      return;
    }

    list.forEach(item => {
      const tr = document.createElement('tr');
      tr.dataset.id = item.id;

      const titleStr = item.title.length > 60 ? item.title.substring(0, 60) + '...' : item.title;
      const pubDate = item.published_date ? item.published_date.split('T')[0] : '';
      const platform = item.platform.charAt(0).toUpperCase() + item.platform.slice(1);

      // Detection & Badges Logic
      const isProtected = item.content_url && item.content_url.includes('ret.nu') && (!item.article_body || item.article_body.trim() === '');
      const protectedBadge = isProtected ? `<span class="status-pill pill-warning" style="margin-right: 0.5rem;" title="Protected link. Requires manual URL resolution.">⚠️ Protected</span>` : '';

      const duplicatesCount = (item.duplicates && item.duplicates.length > 0) ? item.duplicates.length : 0;
      const clusterBadge = duplicatesCount > 0
        ? `<span class="status-pill cluster-badge" title="This cluster contains ${duplicatesCount} alternate version(s)">🔗 ${duplicatesCount} Alt Versions</span>`
        : '';

      let html = `<td class="cell-center"><input type="checkbox" class="row-checkbox" value="${item.id}" data-protected="${isProtected}" /></td>`;

      if (currentTab === 'tab-ingestion') {
        const actionBtns = isProtected
          ? `<button class="btn btn-resolve" style="background: var(--color-accent); color: #fff;">⚠️ Resolve Link</button>
             <button class="btn btn-delete">Delete</button>`
          : `<button class="btn btn-edit">Edit</button>
             <button class="btn btn-delete">Delete</button>`;

        html += `
          <td>${protectedBadge}${clusterBadge}<strong>${titleStr}</strong></td>
          <td>${item.source_name || '-'}</td>
          <td>${platform}</td>
          <td>${pubDate}</td>
          <td class="cell-actions">
            ${actionBtns}
          </td>`;
      }
      else if (currentTab === 'tab-review') {
        const pillClass = item.ai_recommendation === 'relevant' ? 'pill-relevant'
                        : item.ai_recommendation === 'irrelevant' ? 'pill-irrelevant' : 'pill-uncertain';
        const aiText = item.ai_recommendation ? item.ai_recommendation.toUpperCase() : 'UNKNOWN';
        html += `
          <td class="cell-center"><span class="status-pill ${pillClass}">${aiText}</span></td>
          <td><button class="btn expand-btn" title="Preview Summary">+</button> ${protectedBadge}${clusterBadge}<strong>${titleStr}</strong></td>
          <td>${item.source_name || '-'}</td>
          <td>${pubDate}</td>
          <td class="cell-actions">
            <button class="btn btn-approve" style="background: #2e7d32; color: #fff;">Mark Relevant</button>
            <button class="btn btn-reject" style="background: #c62828; color: #fff;">Mark Irrelevant</button>
          </td>`;
      }
      else if (currentTab === 'tab-publish') {
        html += `
          <td><button class="btn expand-btn" title="Preview Article">+</button> <strong>${titleStr}</strong></td>
          <td>${item.source_name || '-'}</td>
          <td>${pubDate}</td>
          <td class="cell-actions">
            <button class="btn btn-push-now">Push Now</button>
            <button class="btn btn-secondary btn-keep-internal">Keep Internal</button>
          </td>`;
      }
      else if (currentTab === 'tab-quarantine') {
        html += `
          <td><strong>${titleStr}</strong></td>
          <td class="error-text">${item.processing_error_msg || 'Unknown error'}</td>
          <td class="cell-actions">
            <button class="btn btn-edit">Edit & Retry</button>
            <button class="btn btn-secondary btn-dismiss">Dismiss</button>
          </td>`;
      }
      else if (currentTab === 'tab-archive') {
        let finalStatus = 'Unknown';
        let pillClass = 'pill-internal';

        if (item.is_published_to_wp) { finalStatus = 'PUBLISHED'; pillClass = 'pill-published'; }
        else if (item.is_relevant === false) { finalStatus = 'REJECTED'; pillClass = 'pill-irrelevant'; }
        else if (item.wp_post_id === -1) { finalStatus = 'KEPT INTERNAL'; pillClass = 'pill-internal'; }

        const wpLink = item.wp_post_id > 0 ? `<a href="/wp-admin/post.php?post=${item.wp_post_id}&action=edit" target="_blank" style="color: var(--color-primary); text-decoration: underline;">View ID ${item.wp_post_id}</a>` : '-';

        html = `
          <td><strong>${titleStr}</strong></td>
          <td>${item.source_name || '-'}</td>
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
  bind('.btn-resolve', (i) => {
    window.open(i.content_url, '_blank'); // Opens link for the user to resolve
    openEditModal(i);                     // Opens our standard edit form
    setTimeout(() => formPub.content_url.focus(), 200); // Highlight where they need to paste it
  });
  bind('.btn-delete', (i) => confirmAction(`Delete "${i.title}" permanently?`, () => deleteRecord(i.id)));

  bind('.expand-btn', togglePreviewRow);

  bind('.btn-approve', (i) => updateRecord(i.id, { is_reviewed: true, is_relevant: true }));
  bind('.btn-reject', (i) => updateRecord(i.id, { is_reviewed: true, is_relevant: false }));

  bind('.btn-push-now', (i) => updateRecord(i.id, { is_published_to_wp: true, wp_post_id: 9999 })); // Mock WP ID for now, real implementation would trigger background task
  bind('.btn-keep-internal', (i) => confirmAction(`Keep "${i.title}" internal (will not publish)?`, () => updateRecord(i.id, { wp_post_id: -1 })));

  bind('.btn-dismiss', (i) => confirmAction(`Dismiss error for "${i.title}"?`, () => updateRecord(i.id, { has_processing_error: false, processing_error_msg: null })));
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

  // Full Body (No truncation, handled by CSS scroll)
  const fullBody = item.article_body || 'No full text available.';

  // AI Justification
  const aiJustification = item.ai_justification || 'No AI justification provided.';

  // External Link with disabled fallback
  const linkHtml = item.content_url
    ? `<a href="${item.content_url}" target="_blank" class="preview-link">🔗 Open Original Article</a>`
    : `<span class="preview-link disabled" title="No URL provided for this item">🔗 No Original Link</span>`;

  panel.innerHTML = `
    <td colspan="6">
      <div class="expanded-content">
        <div class="preview-header">
          <h4 class="preview-title">${safeTitle}</h4>${linkHtml}
        </div>
        <div class="preview-grid" ${currentTab === 'tab-publish' ? 'style="grid-template-columns: 1fr;"' : ''}>
          ${currentTab === 'tab-review' ? `
          <div class="preview-section">
            <h4>AI Justification</h4>
            <div class="content-box"><p>${aiJustification}</p></div>
          </div>
          ` : ''}
          <div class="preview-section">
            <h4>Original Text (Full)</h4>
            <div class="content-box"><p>${fullBody}</p></div>
          </div>
        </div>
        
        ${item.duplicates && item.duplicates.length > 0 && currentTab !== 'tab-publish' ? `
        <div class="duplicates-section">
          <h4 style="margin-bottom: 0.75rem; color: #333;">Alternate Versions</h4>
          <div class="duplicates-list">
            ${item.duplicates.map(dup => {
              const dupDate = dup.published_date ? dup.published_date.split('T')[0] : '';
              const dupLink = dup.content_url 
                ? `<a href="${dup.content_url}" target="_blank" class="preview-link" style="margin-left:0.5rem; font-size:0.8rem;">🔗 Open</a>`
                : `<span class="preview-link disabled" style="margin-left:0.5rem; font-size:0.8rem;" title="No URL">🔗 No Link</span>`;
              
              const promoteAction = dup.has_processing_error 
                ? `<span class="status-pill pill-warning" style="font-size:0.75rem;">⚠️ Fix in Quarantine</span>`
                : `<button class="btn btn-promote" data-id="${dup.id}">⭐ Promote to Main</button>`;
                
              return `
                <div class="duplicate-item">
                  <div class="dup-info">
                    <strong>${dup.source_name || '-'}</strong> | ${dupDate} ${dupLink}<br/>
                    <span style="font-size: 0.85rem; color: #555;">${dup.title}</span>
                  </div>
                  <div class="dup-action">${promoteAction}</div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
        ` : ''}
        
        <div class="preview-actions">
          ${currentTab === 'tab-publish' ? `<button class="btn btn-secondary btn-panel-demote" style="margin-right: 0.5rem; background: #c62828;">↩️ Send Back to Review</button>` : ''}
          <button class="btn btn-secondary btn-panel-edit">✏️ Edit Record</button>
        </div>
      </div>
    </td>
  `;

  // Bind the inline Edit button
  panel.querySelector('.btn-panel-edit').onclick = () => openEditModal(item);

  // Bind the Demote button (if it exists)
  const btnDemote = panel.querySelector('.btn-panel-demote');
  if (btnDemote) {
    btnDemote.onclick = () => confirmAction(`Send this article back to the Needs Review tab?`, () => updateRecord(item.id, { is_reviewed: false }));
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

  const checked = Array.from(tbody.querySelectorAll('.row-checkbox:checked')).map(cb => parseInt(cb.value));

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
      const allChecked = Array.from(tbody.querySelectorAll('.row-checkbox:checked'));
      const validBoxes = allChecked.filter(cb => cb.dataset.protected !== "true");
      const skippedCount = allChecked.length - validBoxes.length;

      if (validBoxes.length === 0) {
        showModal('Cannot process. All selected items are protected links that require manual resolution first.');
        return;
      }

      const skipMsg = skippedCount > 0 ? `\n\n(${skippedCount} item(s) will be skipped due to protected links).` : '';
      confirmAction(`Send ${validBoxes.length} selected item(s) to AI Processing?${skipMsg}`, () => {
        triggerProcessing(validBoxes.map(cb => parseInt(cb.value)));
      });
    };

    document.getElementById('bulk-delete').onclick = () => {
      confirmAction(`Permanently delete ${checked.length} selected item(s)?`, () => bulkUpdate(checked, { action: 'delete' }));
    };
  }
  else if (currentTab === 'tab-review') {
    bulkButtons.innerHTML = `
      <button id="bulk-approve" class="btn" style="background: #2e7d32;">Mark Relevant</button>
      <button id="bulk-reject" class="btn" style="background: #c62828;">Mark Irrelevant</button>
    `;
    document.getElementById('bulk-approve').onclick = () => bulkUpdate(checked, { is_reviewed: true, is_relevant: true });
    document.getElementById('bulk-reject').onclick = () => bulkUpdate(checked, { is_reviewed: true, is_relevant: false });
  }
}

function resetBulkSelection() {
  document.querySelectorAll('.select-all').forEach(cb => cb.checked = false);
  document.querySelectorAll('.row-checkbox').forEach(cb => cb.checked = false);
  bulkActionBar.classList.add('hidden');
}

async function bulkUpdate(ids, payload) {
  try {
    for (const id of ids) {
      if (payload.action === 'delete') {
        await apiFetch(`/media-publications/${id}`, { method: 'DELETE' });
      } else {
        await apiFetch(`/media-publications/${id}`, {
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
// Modals & Forms (Upload & CRUD)
// ============================================================================
function setupModals() {
  // Global Add Record
  btnAddRecord.onclick = () => {
    formPub.reset();
    delete formPub.dataset.editId;
    pubFormTitle.textContent = 'Add Media Publication';
    modalPub.classList.remove('hidden');
  };
  btnCancelPub.onclick = () => modalPub.classList.add('hidden');

  // Publication Form Submit (Add/Edit)
  formPub.onsubmit = async (e) => {
    e.preventDefault();
    const editId = formPub.dataset.editId;

    // Convert datetime-local string to standard ISO format if needed
    let pubDate = formPub.published_date.value;
    if (pubDate && !pubDate.includes('Z') && !pubDate.includes('+')) {
       pubDate = new Date(pubDate).toISOString();
    }

    const payload = {
      title: formPub.title.value.trim(),
      source_name: formPub.source_name.value.trim(),
      platform: formPub.platform.value,
      published_date: pubDate,
      content_url: formPub.content_url.value.trim() || null,
      external_id: formPub.external_id.value.trim() || null,
      article_body: formPub.article_body.value.trim() || null,
      notes: formPub.notes.value.trim() || null
    };

    try {
      const url = editId ? `/media-publications/${editId}` : '/media-publications/';
      const method = editId ? 'PUT' : 'POST';

      // If editing a quarantined item, clear the error flag automatically
      if (editId && currentTab === 'tab-quarantine') {
        payload.has_processing_error = false;
        payload.processing_error_msg = null;
      }

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

  // Upload Form
  btnShowUpload.onclick = () => { formUpload.reset(); modalUpload.classList.remove('hidden'); };
  btnCancelUpload.onclick = () => modalUpload.classList.add('hidden');

  formUpload.onsubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData(formUpload);

    try {
      const btn = formUpload.querySelector('.save-btn');
      btn.disabled = true;
      btn.textContent = 'Uploading...';

      // Note: We don't set Content-Type header so fetch sets the boundary for multipart/form-data
      const summary = await apiFetch('/media-publications/actions/upload', {
        method: 'POST',
        body: formData
      });

      modalUpload.classList.add('hidden');
      btn.disabled = false;
      btn.textContent = 'Upload';

      // Show success modal with summary
      const msg = `Upload Complete!\nPlatform: ${summary.platform}\nParsed: ${summary.total_parsed}\nSaved: ${summary.new_saved}\nSkipped (Duplicates): ${summary.duplicates_skipped}\nErrors: ${summary.errors}`;
      showModal(msg, true);

      loadCurrentTab();
      loadActivityLogs(); // Refresh activity bar
    } catch (err) {
      formUpload.querySelector('.save-btn').disabled = false;
      formUpload.querySelector('.save-btn').textContent = 'Upload';
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

  formPub.title.value = item.title;
  formPub.source_name.value = item.source_name;
  formPub.platform.value = item.platform;

  if (item.published_date) {
    // Format to YYYY-MM-DDThh:mm for datetime-local input
    formPub.published_date.value = item.published_date.substring(0, 16);
  }

  formPub.content_url.value = item.content_url || '';
  formPub.external_id.value = item.external_id || '';
  formPub.article_body.value = item.article_body || '';
  formPub.notes.value = item.notes || '';

  modalPub.classList.remove('hidden');
}

// ============================================================================
// Global Actions (Triggers)
// ============================================================================
function setupGlobalActions() {
  btnProcessAll.onclick = () => {
    const tbody = document.getElementById('tbody-ingestion');
    if (!tbody) return;

    // 1. Process ALL items, strictly ignoring user selections
    const allCheckboxes = Array.from(tbody.querySelectorAll('.row-checkbox'));

    if (allCheckboxes.length === 0) {
      showModal('There are no pending items to process.');
      return;
    }

    // 2. Filter out protected links
    const validBoxes = allCheckboxes.filter(cb => cb.dataset.protected !== "true");
    const skippedCount = allCheckboxes.length - validBoxes.length;

    if (validBoxes.length === 0) {
      showModal('Cannot process. All pending items are protected links that require manual resolution first.');
      return;
    }

    // 3. Demand confirmation for sending ALL items
    const skipMsg = skippedCount > 0 ? `\n\nNote: ${skippedCount} protected item(s) will be skipped until their links are resolved.` : '';
    confirmAction(`Are you sure you want to send ALL ${validBoxes.length} item(s) to AI Processing?${skipMsg}`, () => {
      triggerProcessing(validBoxes.map(cb => parseInt(cb.value)));
    });
  };

  btnPushAllWp.onclick = async () => {
    try {
      await apiFetch('/media-publications/actions/push-to-wp', { method: 'POST' });
      showSystemStatus('Pushing to WP...');
      loadActivityLogs();
      // Removed the forced 3-second reload!
    } catch (err) { showError(err); }
  };
}

async function updateRecord(id, payload) {
  try {
    await apiFetch(`/media-publications/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    loadCurrentTab();
  } catch (err) { showError(err); }
}

async function deleteRecord(id) {
  try {
    await apiFetch(`/media-publications/${id}`, { method: 'DELETE' });
    loadCurrentTab();
  } catch (err) { showError(err); }
}

// ============================================================================
// Search String Generator
// ============================================================================
function setupSearchGenerator() {
  btnGenerateSearch.onclick = async () => {
    btnGenerateSearch.textContent = 'Generating...';
    try {
      // Fetch active researchers
      const researchers = await apiFetch('/researchers/?is_active=true');

      // Extract names and format
      const names = researchers
        .filter(r => r.person)
        .map(r => `"${r.person.first_name} ${r.person.last_name}"`);

      const boolString = `(${names.join(' OR ')})`;
      searchOutput.value = boolString;

    } catch (err) {
      showError('Failed to generate search string: ' + err.message);
    } finally {
      btnGenerateSearch.textContent = 'Generate String';
    }
  };

  btnCopySearch.onclick = async () => {
    if (!searchOutput.value) return;
    try {
      await navigator.clipboard.writeText(searchOutput.value);
      const orig = btnCopySearch.innerHTML;
      btnCopySearch.innerHTML = `<span style="font-size:0.8rem; font-weight:bold;">Copied!</span>`;
      setTimeout(() => btnCopySearch.innerHTML = orig, 2000);
    } catch (err) {
      alert('Could not copy text automatically.');
    }
  };
}

// ============================================================================
// Utilities & UI Helpers
// ============================================================================
async function triggerProcessing(ids) {
  try {
    await apiFetch('/media-publications/actions/process-pending', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ publication_ids: ids })
    });
    showSystemStatus('AI Processing Started...');
    loadActivityLogs(); // Grabs the new IN_PROGRESS state instantly
    resetBulkSelection(); // Instantly unchecks boxes for local UI feedback
    // Removed the forced 3-second reload!
  } catch (err) {
    showError(err);
  }
}

async function promoteDuplicate(duplicateId) {
  confirmAction('Promote this alternate version to become the Primary article for this cluster?', async () => {
    try {
      await apiFetch(`/media-publications/${duplicateId}/actions/promote`, { method: 'POST' });
      showSystemStatus('Item successfully promoted to Primary.');
      loadActivityLogs(); // Update the log bar
      loadCurrentTab();   // Refresh the table UI
    } catch (err) {
      showError(err);
    }
  });
}

async function loadActivityLogs() {
  const elRetriever = document.getElementById('activity-ingest-retriever');
  const elFactiva = document.getElementById('activity-ingest-factiva');
  const elProcessing = document.getElementById('activity-processing');
  const elPublish = document.getElementById('activity-publish');

  try {
    // Fetch recent logs (fetching enough to ensure we find recent actions of each type)
    const logs = await apiFetch('/automation-logs/?limit=100');

    // Helper to find the most recent log for a specific action type
    const getLatest = (type) => logs.find(log => log.action_type === type);

    const procLog = getLatest('media_processing');
    const pubLog = getLatest('media_publish');

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
      // Check if it lacks a 'Z' AND lacks an offset like '+02:00' or '-05:00' at the end of the string
      if (!/(Z|[+-]\d{2}:?\d{2})$/.test(ts)) {
        ts += 'Z';
      }

      const dateOpts = { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
      // toLocaleString automatically converts the UTC time to the user's local browser timezone
      const dateStr = new Date(ts).toLocaleString(undefined, dateOpts);

      const userStr = log.user ? log.user.username : (log.trigger_source === 'system' ? 'System' : 'Unknown');

      const statusIcon = log.status === 'success' ? '✅' :
                         log.status === 'failed' ? '❌' :
                         log.status === 'in_progress' ? '⏳' : '⚠️';

      return `<em>${dateStr} by ${userStr} ${statusIcon}</em>`;
    };

    // Update the UI
    elRetriever.innerHTML = `Retriever Upload: ${formatLog(getLatest('media_ingestion_retriever'))}`;
    elFactiva.innerHTML = `Factiva Upload: ${formatLog(getLatest('media_ingestion_factiva'))}`;
    elProcessing.innerHTML = `Processing: ${formatLog(getLatest('media_processing'))}`;
    elPublish.innerHTML = `WP Push: ${formatLog(getLatest('media_publish'))}`;

  } catch (err) {
    console.warn("Could not load activity logs", err);
    const errHtml = '<em>Unavailable</em>';
    elRetriever.innerHTML = `Retriever Upload: ${errHtml}`;
    elFactiva.innerHTML = `Factiva Upload: ${errHtml}`;
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
