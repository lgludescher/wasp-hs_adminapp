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

// Actions
const btnProcessPending = document.getElementById('btn-process-pending');
const btnPushAllWp = document.getElementById('btn-push-all-wp');

// ============================================================================
// State Management
// ============================================================================
let currentTab = 'tab-ingestion';
let expandedRow = null;
let currentListData = []; // Store current tab's data for easy reference
let pendingConfirmAction = null;

// ============================================================================
// Initialization
// ============================================================================
(async function init() {
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

    // Tab-specific local filtering if needed (e.g., separating Ingestion from Review based on AI)
    if (currentTab === 'tab-ingestion') {
      list = list.filter(item => !item.ai_recommendation); // Only items with no AI yet
    } else if (currentTab === 'tab-review') {
      list = list.filter(item => item.ai_recommendation); // Only items processed by AI
    } else if (currentTab === 'tab-archive') {
      // Terminal states: Published OR explicitly Rejected OR Kept Internal
      list = list.filter(item =>
        item.is_published_to_wp === true ||
        item.is_relevant === false ||
        item.wp_post_id === -1
      );
    }

    currentListData = list;

    // 3. Render Data
    tbody.innerHTML = '';
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

      let html = `<td class="cell-center"><input type="checkbox" class="row-checkbox" value="${item.id}" /></td>`;

      if (currentTab === 'tab-ingestion') {
        html += `
          <td><strong>${titleStr}</strong></td>
          <td>${item.source_name || '-'}</td>
          <td>${platform}</td>
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
          <td><button class="btn expand-btn" title="Preview Summary">+</button> <strong>${titleStr}</strong></td>
          <td>${item.source_name || '-'}</td>
          <td>${pubDate}</td>
          <td class="cell-actions">
            <button class="btn btn-approve" style="background: #2e7d32; color: #fff;">Approve</button>
            <button class="btn btn-reject" style="background: #c62828; color: #fff;">Reject</button>
          </td>`;
      }
      else if (currentTab === 'tab-publish') {
        html += `
          <td><strong>${titleStr}</strong></td>
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

  // Clean up body text for preview
  const rawBody = item.article_body || 'No full text available.';
  const previewBody = rawBody.length > 1000 ? rawBody.substring(0, 1000) + '... (truncated)' : rawBody;

  // Note: Assuming ai_summary or notes might exist, falling back if not.
  const aiSummary = item.notes || 'No AI reasoning notes provided.';

  panel.innerHTML = `
    <td colspan="6">
      <div class="expanded-content">
        <div class="preview-grid">
          <div class="preview-section">
            <h4>AI Reasoning</h4>
            <p style="background: #fff; padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px;">${aiSummary}</p>
          </div>
          <div class="preview-section">
            <h4>Original Text (Excerpt)</h4>
            <p>${previewBody}</p>
          </div>
        </div>
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
    bulkButtons.innerHTML = `<button id="bulk-delete" class="btn" style="background: #c62828;">Delete Selected</button>`;
    document.getElementById('bulk-delete').onclick = () => bulkUpdate(checked, { action: 'delete' });
  }
  else if (currentTab === 'tab-review') {
    bulkButtons.innerHTML = `
      <button id="bulk-approve" class="btn" style="background: #2e7d32;">Approve Selected</button>
      <button id="bulk-reject" class="btn" style="background: #c62828;">Reject Selected</button>
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
  btnProcessPending.onclick = async () => {
    try {
      await apiFetch('/media-publications/actions/process-pending', { method: 'POST' });
      showSystemStatus('AI Processing Started...');
      loadActivityLogs(); // Instantly fetch the new IN_PROGRESS log
      setTimeout(loadCurrentTab, 3000); // Wait a bit then refresh table
    } catch (err) { showError(err); }
  };

  btnPushAllWp.onclick = async () => {
    try {
      await apiFetch('/media-publications/actions/push-to-wp', { method: 'POST' });
      showSystemStatus('Pushing to WP...');
      loadActivityLogs(); // Instantly fetch the new IN_PROGRESS log
      setTimeout(loadCurrentTab, 3000); // Wait a bit then refresh table
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
