import { apiFetch } from './main.js';

const ROLE_DISPLAY = { 1: 'Researcher', 2: 'PhD Student', 3: 'Postdoc' };
const ROLE_PATHS = { 1: 'researchers', 2: 'phd-students', 3: 'postdocs' };

// --- DOM Elements ---
const detailsSection = document.getElementById('project-details-section');
const modal = document.getElementById('modal-confirm');
const modalText = document.getElementById('modal-text');
const modalConfirmBtn = document.getElementById('modal-confirm-btn');
const modalCancelBtn = document.getElementById('modal-cancel-btn');

// --- State ---
let projectId = null;
let projectData = {};
let pendingRemove = null;

// --- Initialization ---
(async function init() {
  const pathParts = window.location.pathname.split('/').filter(p => p);
  projectId = parseInt(pathParts[pathParts.length - 1], 10);

  if (!projectId) {
    return showError("Could not determine a valid Project ID from the URL.");
  }

  try {
    await loadAndRenderMainDetails();
    setupPanelToggles();
  } catch (err) {
    showError(err);
    detailsSection.innerHTML = `<p>Error loading details. Please try again.</p>`;
  }

  modalCancelBtn.onclick = () => { pendingRemove = null; modal.classList.add('hidden'); };
  modalConfirmBtn.onclick = confirmRemove;
})();


// --- Main Details Logic ---
async function loadAndRenderMainDetails() {
  try {
    projectData = await apiFetch(`/projects/${projectId}/`);
    renderMainDetails();
  } catch (err) {
    showError(err);
  }
}

function renderMainDetails(isEdit = false) {
  if (isEdit) {
    detailsSection.innerHTML = `
      <div class="details-box-content">
        <label class="detail-item" style="grid-column: 1 / 3;"><strong>Project Number</strong><input name="project_number" type="text" value="${projectData.project_number || ''}"></label>
        <label class="detail-item" style="grid-column: 3 / 5;"><strong>Call Type</strong><select name="call_type_id"></select></label>
        
        <label class="detail-item" style="grid-column: 1 / 3;"><strong>Start Date</strong><input name="start_date" type="date" value="${projectData.start_date?.split('T')[0] || ''}"></label>
        <label class="detail-item" style="grid-column: 3 / 5;"><strong>End Date</strong><input name="end_date" type="date" value="${projectData.end_date?.split('T')[0] || ''}"></label>

        <label class="detail-item" style="grid-column: 1 / 5;"><strong>Project Title</strong><input name="title" type="text" value="${projectData.title || ''}"></label>

        <div class="detail-item"><label class="checkbox-label"><input name="final_report_submitted" type="checkbox" ${projectData.final_report_submitted ? 'checked' : ''}> Final Report Submitted?</label></div>
        <div class="detail-item"><label class="checkbox-label"><input name="is_extended" type="checkbox" ${projectData.is_extended ? 'checked' : ''}> Extended?</label></div>
        <label class="detail-item" style="grid-column: 3 / 5;"><strong>Notes</strong><textarea name="notes">${projectData.notes || ''}</textarea></label>
      </div>
      <div class="details-box-actions">
        <button class="btn save-btn">Save</button>
        <button class="btn cancel-btn">Cancel</button>
      </div>
    `;
    populateDropdown(detailsSection.querySelector('[name="call_type_id"]'), '/project-call-types/', 'type', projectData.call_type_id);
    detailsSection.querySelector('.save-btn').onclick = saveMainDetails;
    detailsSection.querySelector('.cancel-btn').onclick = () => renderMainDetails(false);
  } else {
    detailsSection.innerHTML = `
      <button class="btn btn-edit-main">Edit</button>
      <div class="details-box-content">
        <div class="detail-item" style="grid-column: 1 / 3;"><strong>Project Number:</strong> <span>${projectData.project_number || ''}</span></div>
        <div class="detail-item" style="grid-column: 3 / 5;"><strong>Call Type:</strong> <span>${projectData.call_type?.type || ''}</span></div>
        
        <div class="detail-item" style="grid-column: 1 / 3;"><strong>Start Date:</strong> <span>${projectData.start_date?.split('T')[0] || ''}</span></div>
        <div class="detail-item" style="grid-column: 3 / 5;"><strong>End Date:</strong> <span>${projectData.end_date?.split('T')[0] || ''}</span></div>

        <div class="detail-item" style="grid-column: 1 / 5;"><strong>Project Title:</strong> <span>${projectData.title || ''}</span></div>

        <div class="detail-item"><strong>Final Report Submitted?</strong> <input type="checkbox" disabled ${projectData.final_report_submitted ? 'checked' : ''}></div>
        <div class="detail-item"><strong>Extended?</strong> <input type="checkbox" disabled ${projectData.is_extended ? 'checked' : ''}></div>
        <div class="detail-item" style="grid-column: 3 / 5;"><strong>Notes:</strong> <span>${projectData.notes || ''}</span></div>
      </div>
    `;
    detailsSection.querySelector('.btn-edit-main').onclick = () => renderMainDetails(true);
  }
}

async function saveMainDetails() {
    const form = detailsSection;
    const projectUpdate = {
        project_number: form.querySelector('[name="project_number"]').value.trim() || null,
        call_type_id: parseInt(form.querySelector('[name="call_type_id"]').value, 10) || null,
        start_date: form.querySelector('[name="start_date"]').value || null,
        end_date: form.querySelector('[name="end_date"]').value || null,
        title: form.querySelector('[name="title"]').value.trim() || null,
        final_report_submitted: form.querySelector('[name="final_report_submitted"]').checked,
        is_extended: form.querySelector('[name="is_extended"]').checked,
        notes: form.querySelector('[name="notes"]').value.trim() || null,
    };
    try {
        await apiFetch(`/projects/${projectId}/`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(projectUpdate) });
        await loadAndRenderMainDetails();
    } catch (err) {
        showError(err);
    }
}

// --- Panel Management ---
const panelLoaders = {
  members: loadMembers,
  fields: loadFields,
  outputs: loadResearchOutputReports,
  letters: loadDecisionLetters,
};

function setupPanelToggles() {
  document.querySelectorAll('.panel-header').forEach(header => {
    header.onclick = () => togglePanel(header.querySelector('.expand-btn').dataset.panel);
  });
}
function togglePanel(panelName) {
    const contentDiv = document.getElementById(`panel-content-${panelName}`);
    const btn = document.querySelector(`.expand-btn[data-panel="${panelName}"]`);
    if (!contentDiv || !btn) return;
    const isHidden = contentDiv.classList.toggle('hidden');
    btn.textContent = isHidden ? '+' : '–';

    if (isHidden) {
      // If panel is being collapsed, remove its 'loaded' status to force a fresh
      // reload on next open. This discards any inline-edit states.
      delete contentDiv.dataset.loaded;
      const tableContent = contentDiv.querySelector('.data-table');
      if (tableContent) tableContent.innerHTML = '<thead></thead><tbody></tbody>';
    } else if (!contentDiv.dataset.loaded) {
      // If panel is being expanded and hasn't been loaded yet, load it.
      panelLoaders[panelName](contentDiv);
      contentDiv.dataset.loaded = 'true';
    }
}

function setupPanelAddForm(panel, config) {
  const { addCallback, loadFn } = config;
  const showFormBtn = panel.querySelector('.btn-show-add-form');
  const addForm = panel.querySelector('.item-add-form');
  const cancelBtn = addForm.querySelector('.cancel-btn');

  showFormBtn.onclick = () => { addForm.classList.toggle('hidden'); };

  cancelBtn.onclick = () => {
    addForm.reset();
    addForm.classList.add('hidden');
    showFormBtn.classList.remove('hidden');

    // THE FIX: Find the first select element (the filter) and trigger its change event.
    const firstSelect = addForm.querySelector('select');
    if (firstSelect) {
      firstSelect.dispatchEvent(new Event('change'));
    }
  };

  addForm.onsubmit = async (e) => {
    e.preventDefault();
    try {
      await addCallback(new FormData(addForm));
      addForm.reset();
      addForm.classList.add('hidden');
      showFormBtn.classList.remove('hidden');

      // Also trigger the event after a successful save for good measure.
      const firstSelect = addForm.querySelector('select');
      if (firstSelect) {
        firstSelect.dispatchEvent(new Event('change'));
      }

      await loadFn(panel);
    } catch (err) { showError(err); }
  };
}


// --- MEMBERS PANEL ---
async function loadMembers(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = `
    <tr>
      <th></th>
      <th class="cell-center">PI?</th>
      <th class="cell-center">Leader?</th>
      <th>Role</th>
      <th>Name</th>
      <th></th>
    </tr>`;
  try {
    const members = await apiFetch(`/projects/${projectId}/people-roles/`);

    // Enrich each member with their full details
    const enrichedData = await Promise.all(members.map(async (member) => {
      const personRole = await apiFetch(`/person-roles/${member.person_role_id}`);
      const subRolePath = ROLE_PATHS[personRole.role.id];

      let subRoleId = null;
      if (subRolePath) {
        const subRoleData = await apiFetch(`/${subRolePath}/?person_role_id=${personRole.id}`);
        if (subRoleData.length > 0) {
          subRoleId = subRoleData[0].id;
        }
      }
      return { ...member, personRole, subRolePath, subRoleId };
    }));

    tbody.innerHTML = '';
    if (!enrichedData.length) {
      tbody.innerHTML = `<tr><td colspan="6">No members associated with this project.</td></tr>`;
    } else {
      enrichedData.forEach(item => {
        const tr = document.createElement('tr');
        tr.dataset.personRoleId = item.person_role_id;
        renderMemberRow(tr, item);
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6">Could not load members: ${err.message}</td></tr>`;
  }
  setupMembersAddForm(panel);
}

function renderMemberRow(tr, item) {
    const person = item.personRole.person;
    const roleName = ROLE_DISPLAY[item.personRole.role.id] || item.personRole.role.role;
    const profileLink = item.subRoleId ? `<a href="/manage-${item.subRolePath}/${item.subRoleId}/" class="go-to-btn">Go to Profile</a>` : '';

    tr.innerHTML = `
      <td>${profileLink}</td>
      <td class="cell-center">${item.is_principal_investigator ? '✔' : '✘'}</td>
      <td class="cell-center">${item.is_leader ? '✔' : '✘'}</td>
      <td>${roleName}</td>
      <td>${person.first_name} ${person.last_name}</td>
      <td class="cell-actions">
        <button class="btn edit-btn">Edit</button>
        <button class="btn remove-btn">Remove</button>
      </td>`;
    tr.querySelector('.edit-btn').onclick = () => startEditMemberRow(tr, item);
    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = {
            type: 'project_member',
            item,
            name: `association for ${person.first_name} ${person.last_name}`
        };
        showModal(`Remove ${pendingRemove.name}?`);
    };
}

function startEditMemberRow(tr, item) {
    const person = item.personRole.person;
    const roleName = ROLE_DISPLAY[item.personRole.role.id] || item.personRole.role.role;
    const profileLink = item.subRoleId ? `<a href="/manage-${item.subRolePath}/${item.subRoleId}/" class="go-to-btn">Go to Profile</a>` : '';

    tr.innerHTML = `
      <td>${profileLink}</td>
      <td class="cell-center"><input type="checkbox" name="is_pi" ${item.is_principal_investigator ? 'checked' : ''}></td>
      <td class="cell-center"><input type="checkbox" name="is_leader" ${item.is_leader ? 'checked' : ''}></td>
      <td>${roleName}</td>
      <td>${person.first_name} ${person.last_name}</td>
      <td class="cell-actions">
        <button class="btn save-btn">Save</button>
        <button class="btn cancel-btn">Cancel</button>
      </td>`;
    tr.querySelector('.cancel-btn').onclick = () => renderMemberRow(tr, item);
    tr.querySelector('.save-btn').onclick = async () => {
        const data = {
            person_role_id: item.person_role_id,
            is_principal_investigator: tr.querySelector('[name=is_pi]').checked,
            is_leader: tr.querySelector('[name=is_leader]').checked
        };
        try {
            const updatedItem = await apiFetch(`/projects/${projectId}/people-roles/${item.person_role_id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            renderMemberRow(tr, { ...item, ...updatedItem });
        } catch (err) {
            showError(err);
            renderMemberRow(tr, item);
        }
    };
}

async function setupMembersAddForm(panel) {
    const addForm = panel.querySelector('.item-add-form');
    const roleFilterSelect = addForm.querySelector('[name=member_role_filter]');
    const personSelect = addForm.querySelector('[name=person_role_id]');

    const populatePeople = async () => {
        const rolePath = roleFilterSelect.value; // 'researchers', 'phd-students', or 'postdocs'
        const url = `/${rolePath}/?is_active=true`;
        const activePeople = await apiFetch(url);

        personSelect.innerHTML = '<option value="">Select a person...</option>';
        activePeople.forEach(person => {
           const p = person.person_role.person;
           const option = new Option(`${p.first_name} ${p.last_name}`, person.person_role.id);
           personSelect.add(option);
        });
    };

    roleFilterSelect.onchange = populatePeople;
    await populatePeople(); // Initial population

    setupPanelAddForm(panel, {
        loadFn: loadMembers,
        addCallback: (formData) => apiFetch(`/projects/${projectId}/people-roles/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                person_role_id: parseInt(formData.get('person_role_id')),
                is_principal_investigator: formData.get('is_pi') === 'on',
                is_leader: formData.get('is_leader') === 'on'
            })
        }),
    });
}


// --- ACADEMIC FIELDS PANEL ---
async function loadFields(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = `<tr><th>Field (Branch)</th><th></th></tr>`;
  try {
    const fields = await apiFetch(`/projects/${projectId}/fields/`);
    // Enrich each field with its branch name
    const enrichedData = await Promise.all(fields.map(async (field) => {
      const branch = await apiFetch(`/branches/${field.branch_id}`);
      return { ...field, branch };
    }));

    tbody.innerHTML = '';
    if (!enrichedData.length) {
      tbody.innerHTML = `<tr><td colspan="2">No academic fields associated.</td></tr>`;
    } else {
      enrichedData.forEach(item => {
        const tr = document.createElement('tr');
        tr.dataset.fieldId = item.id;
        renderFieldRow(tr, item);
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="2">Could not load academic fields: ${err.message}</td></tr>`;
  }
  setupFieldsAddForm(panel);
}

function renderFieldRow(tr, item) {
    tr.innerHTML = `
      <td>${item.field} (${item.branch.branch})</td>
      <td class="cell-actions">
        <button class="btn remove-btn">Remove</button>
      </td>`;
    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = {
            type: 'field',
            item,
            name: `association for field "${item.field}"`
        };
        showModal(`Remove ${pendingRemove.name}?`);
    };
}

async function setupFieldsAddForm(panel) {
    const addForm = panel.querySelector('.item-add-form');
    const branchSelect = addForm.querySelector('[name=field_branch_filter]');
    const fieldSelect = addForm.querySelector('[name=field_id]');

    await populateDropdown(branchSelect, '/branches/', 'branch', null, 'All Branches');

    branchSelect.onchange = () => {
      const branchId = branchSelect.value;
      const endpoint = branchId ? `/fields/?branch_id=${branchId}` : '/fields/';
      populateDropdown(fieldSelect, endpoint, 'field');
    };
    branchSelect.dispatchEvent(new Event('change'));

    setupPanelAddForm(panel, {
        loadFn: loadFields,
        addCallback: (formData) => apiFetch(`/projects/${projectId}/fields/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                field_id: parseInt(formData.get('field_id'))
            })
        }),
    });
}


// --- RESEARCH OUTPUT REPORTS PANEL ---
async function loadResearchOutputReports(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = `<tr><th>Link</th><th></th></tr>`;
  try {
    const reports = await apiFetch(`/projects/${projectId}/research-output-reports/`);
    tbody.innerHTML = '';
    if (!reports.length) {
      tbody.innerHTML = `<tr><td colspan="2">No research output reports associated.</td></tr>`;
    } else {
      reports.forEach(item => {
        const tr = document.createElement('tr');
        tr.dataset.reportId = item.id;
        renderResearchOutputReportRow(tr, item);
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="2">Could not load reports: ${err.message}</td></tr>`;
  }
  setupResearchOutputReportsAddForm(panel);
}

function renderResearchOutputReportRow(tr, item) {
    tr.innerHTML = `
      <td>${renderAsConditionalLink(item.link)}</td>
      <td class="cell-actions">
        <button class="btn edit-btn">Edit</button>
        <button class="btn remove-btn">Remove</button>
      </td>`;
    tr.querySelector('.edit-btn').onclick = () => startEditResearchOutputReportRow(tr, item);
    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = {
            type: 'research_output_report',
            item,
            name: `research output report link "${(item.link || '').substring(0, 40)}..."`
        };
        showModal(`Remove ${pendingRemove.name}?`);
    };
}

function startEditResearchOutputReportRow(tr, item) {
    tr.innerHTML = `
      <td><input name="link" type="text" value="${item.link || ''}"></td>
      <td class="cell-actions">
        <button class="btn save-btn">Save</button>
        <button class="btn cancel-btn">Cancel</button>
      </td>`;
    tr.querySelector('.cancel-btn').onclick = () => renderResearchOutputReportRow(tr, item);
    tr.querySelector('.save-btn').onclick = async () => {
        const data = { link: tr.querySelector('[name=link]').value.trim() };
        try {
            const updatedItem = await apiFetch(`/projects/${projectId}/research-output-reports/${item.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            renderResearchOutputReportRow(tr, updatedItem);
        } catch (err) { showError(err); renderResearchOutputReportRow(tr, item); }
    };
}

function setupResearchOutputReportsAddForm(panel) {
    setupPanelAddForm(panel, {
        loadFn: loadResearchOutputReports,
        addCallback: (formData) => apiFetch(`/projects/${projectId}/research-output-reports/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ link: formData.get('link').trim() })
        }),
    });
}


// --- DECISION LETTERS PANEL ---
async function loadDecisionLetters(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = `<tr><th>Link</th><th></th></tr>`;
  try {
    const letters = await apiFetch(`/projects/${projectId}/decision-letters/`);
    tbody.innerHTML = '';
    if (!letters.length) {
      tbody.innerHTML = `<tr><td colspan="2">No decision letters associated.</td></tr>`;
    } else {
      letters.forEach(item => {
        const tr = document.createElement('tr');
        tr.dataset.letterId = item.id;
        renderDecisionLetterRow(tr, item);
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="2">Could not load decision letters: ${err.message}</td></tr>`;
  }
  setupDecisionLettersAddForm(panel);
}

function renderDecisionLetterRow(tr, item) {
    tr.innerHTML = `
      <td>${renderAsConditionalLink(item.link)}</td>
      <td class="cell-actions">
        <button class="btn edit-btn">Edit</button>
        <button class="btn remove-btn">Remove</button>
      </td>`;
    tr.querySelector('.edit-btn').onclick = () => startEditDecisionLetterRow(tr, item);
    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = {
            type: 'decision_letter',
            item,
            name: `decision letter link "${(item.link || '').substring(0, 40)}..."`
        };
        showModal(`Remove ${pendingRemove.name}?`);
    };
}

function startEditDecisionLetterRow(tr, item) {
    tr.innerHTML = `
      <td><input name="link" type="text" value="${item.link || ''}"></td>
      <td class="cell-actions">
        <button class="btn save-btn">Save</button>
        <button class="btn cancel-btn">Cancel</button>
      </td>`;
    tr.querySelector('.cancel-btn').onclick = () => renderDecisionLetterRow(tr, item);
    tr.querySelector('.save-btn').onclick = async () => {
        const data = { link: tr.querySelector('[name=link]').value.trim() };
        try {
            const updatedItem = await apiFetch(`/projects/${projectId}/decision-letters/${item.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            renderDecisionLetterRow(tr, updatedItem);
        } catch (err) { showError(err); renderDecisionLetterRow(tr, item); }
    };
}

function setupDecisionLettersAddForm(panel) {
    setupPanelAddForm(panel, {
        loadFn: loadDecisionLetters,
        addCallback: (formData) => apiFetch(`/projects/${projectId}/decision-letters/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ link: formData.get('link').trim() })
        }),
    });
}


// --- Utility Functions ---
function showModal(message) {
  modalText.textContent = message;
  modalConfirmBtn.style.display = '';
  modalCancelBtn.textContent = 'Cancel';
  modal.classList.remove('hidden');
}

function showError(err) {
  modalText.textContent = err.message || String(err);
  modalConfirmBtn.style.display = 'none';
  modalCancelBtn.textContent = 'OK';
  modal.classList.remove('hidden');
}

async function confirmRemove() {
  if (!pendingRemove) return;
  const { type, item } = pendingRemove;
  try {
    if (type === 'project_member') {
      await apiFetch(`/projects/${projectId}/people-roles/${item.person_role_id}`, { method: 'DELETE' });
      await loadMembers(document.getElementById('panel-content-members'));
    } else if (type === 'field') {
      await apiFetch(`/projects/${projectId}/fields/${item.id}`, { method: 'DELETE' });
      await loadFields(document.getElementById('panel-content-fields'));
    } else if (type === 'research_output_report') {
      await apiFetch(`/projects/${projectId}/research-output-reports/${item.id}`, { method: 'DELETE' });
      await loadResearchOutputReports(document.getElementById('panel-content-outputs'));
    } else if (type === 'decision_letter') {
      await apiFetch(`/projects/${projectId}/decision-letters/${item.id}`, { method: 'DELETE' });
      await loadDecisionLetters(document.getElementById('panel-content-letters'));
    }
    pendingRemove = null;
    modal.classList.add('hidden');
  } catch (err) {
    showError(err);
  }
}

function renderAsConditionalLink(link) {
  if (!link) return '';
  if (link.startsWith('http://') || link.startsWith('https://')) {
    return `<a href="${link}" target="_blank" rel="noopener noreferrer">${link}</a>`;
  }
  return `<span>${link}</span>`;
}

async function populateDropdown(select, endpoint, textField, selectedId = null, defaultOption = 'Select...') {
  try {
    const items = await apiFetch(endpoint);
    select.innerHTML = `<option value="">${defaultOption}</option>`;
    items.forEach(item => {
      const text = typeof textField === 'function' ? textField(item) : item[textField];
      const option = new Option(text, item.id);
      if (item.id === selectedId) option.selected = true;
      select.add(option);
    });
  } catch (err) { showError(err); }
}
