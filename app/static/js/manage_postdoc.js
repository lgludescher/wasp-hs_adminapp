import { apiFetch } from './main.js';

const ROLE_DISPLAY = { 1: 'Researcher', 2: 'PhD Student', 3: 'Postdoc' };
const ROLE_PATHS = { 1: 'researchers', 2: 'phd-students', 3: 'postdocs' };

// --- DOM Elements ---
const detailsSection = document.getElementById('postdoc-details-section');
const modal = document.getElementById('modal-confirm');
const modalText = document.getElementById('modal-text');
const modalConfirmBtn = document.getElementById('modal-confirm-btn');
const modalCancelBtn = document.getElementById('modal-cancel-btn');

// --- State ---
let postdocId = null;
let postdocData = {};
let pendingRemove = null;

// --- Initialization ---
(async function init() {
  const pathParts = window.location.pathname.split('/').filter(p => p);
  postdocId = parseInt(pathParts[pathParts.length - 1], 10);

  if (!postdocId) {
    return showError("Could not determine a valid Postdoc ID from the URL.");
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
    postdocData = await apiFetch(`/postdocs/${postdocId}/`);
    if (!postdocData || !postdocData.person_role) {
      throw new Error("Failed to load Postdoc data.");
    }
    renderMainDetails();
  } catch (err) {
    showError(err);
  }
}

function renderMainDetails(isEdit = false) {
  const { person_role: role } = postdocData;
  const person = role.person;

  if (isEdit) {
    detailsSection.innerHTML = `
      <div class="details-box-content">
        <div class="detail-top-section">
            <div class="detail-column">
                <div class="detail-item"><strong>Name:</strong> <span>${person.first_name} ${person.last_name}</span></div>
                <label class="detail-item"><strong>Start Date</strong><input name="start_date" type="date" value="${role.start_date?.split('T')[0] || ''}"></label>
                <label class="detail-item"><strong>End Date</strong><input name="end_date" type="date" value="${role.end_date?.split('T')[0] || ''}"></label>
            </div>
            <div class="detail-column">
                <div class="detail-item"><strong>Email:</strong> <span>${person.email}</span></div>
                <label class="detail-item"><strong>Personal Link</strong><input name="link" type="url" value="${postdocData.link || ''}"></label>
                <label class="detail-item"><strong>Notes</strong><textarea name="notes">${postdocData.notes || ''}</textarea></label>
            </div>
        </div>
        <div class="detail-bottom-section">
            <label class="detail-item"><strong>Cohort Number</strong><input name="cohort_number" type="number" min="0" max="99" value="${postdocData.cohort_number || ''}"></label>
            <label class="detail-item"><span class="checkbox-label"><input name="is_incoming" type="checkbox" ${postdocData.is_incoming ? 'checked' : ''}> Incoming?</span></label>
            <label class="detail-item"><strong>Department</strong><input name="department" type="text" value="${postdocData.department || ''}"></label>
            <label class="detail-item"><strong>Discipline</strong><input name="discipline" type="text" value="${postdocData.discipline || ''}"></label>
            
            <label class="detail-item" style="grid-column: 1 / 5;"><strong>Postdoc Project Title</strong><input name="postdoc_project_title" type="text" value="${postdocData.postdoc_project_title || ''}"></label>
            
            <label class="detail-item" style="grid-column: 1 / 3;">
                <strong>Current Title</strong>
                <select name="current_title_id"></select>
                <div class="other-input-container hidden" id="current_title_other_container">
                    <input name="current_title_other" type="text" placeholder="Specify other title...">
                </div>
            </label>
            <label class="detail-item" style="grid-column: 3 / 5;">
                <strong>Current Institution</strong>
                <select name="current_institution_id"></select>
                <div class="other-input-container hidden" id="current_institution_other_container">
                    <input name="current_institution_other" type="text" placeholder="Specify other institution...">
                </div>
            </label>
        </div>
      </div>
      <div class="details-box-actions">
        <button class="btn save-btn">Save</button>
        <button class="btn cancel-btn">Cancel</button>
      </div>
    `;
    setupConditionalInputs();
    detailsSection.querySelector('.save-btn').onclick = saveMainDetails;
    detailsSection.querySelector('.cancel-btn').onclick = () => renderMainDetails(false);
  } else {
    let currentTitle = postdocData.current_title ? postdocData.current_title.title : (postdocData.current_title_other || '');
    let currentInst = postdocData.current_institution ? postdocData.current_institution.institution : (postdocData.current_institution_other || '');

    detailsSection.innerHTML = `
      <button class="btn btn-edit-main">Edit</button>
      <div class="details-box-content">
        <div class="detail-top-section">
            <div class="detail-column">
                <div class="detail-item"><strong>Name:</strong> <span>${person.first_name} ${person.last_name}</span></div>
                <div class="detail-item"><strong>Start Date:</strong> <span>${role.start_date?.split('T')[0] || ''}</span></div>
                <div class="detail-item"><strong>End Date:</strong> <span>${role.end_date?.split('T')[0] || ''}</span></div>
            </div>
            <div class="detail-column">
                <div class="detail-item"><strong>Email:</strong> <span>${person.email}</span></div>
                <div class="detail-item"><strong>Personal Link:</strong> ${renderAsConditionalLink(postdocData.link)}</div>
                <div class="detail-item"><strong>Notes:</strong> <span>${postdocData.notes || ''}</span></div>
            </div>
        </div>
        <div class="detail-bottom-section">
            <div class="detail-item"><strong>Cohort Number:</strong> <span>${postdocData.cohort_number ?? ''}</span></div>
            <div class="detail-item"><strong>Incoming?:</strong> <input type="checkbox" disabled ${postdocData.is_incoming ? 'checked' : ''}></div>
            <div class="detail-item"><strong>Department:</strong> <span>${postdocData.department || ''}</span></div>
            <div class="detail-item"><strong>Discipline:</strong> <span>${postdocData.discipline || ''}</span></div>

            <div class="detail-item" style="grid-column: 1 / 5;"><strong>Postdoc Project Title:</strong> <span>${postdocData.postdoc_project_title || ''}</span></div>
            
            <div class="detail-item" style="grid-column: 1 / 3;"><strong>Current Title:</strong> <span>${currentTitle}</span></div>
            <div class="detail-item" style="grid-column: 3 / 5;"><strong>Current Institution:</strong> <span>${currentInst}</span></div>
        </div>
      </div>
    `;
    detailsSection.querySelector('.btn-edit-main').onclick = () => renderMainDetails(true);
  }
}

async function saveMainDetails() {
    const form = detailsSection;
    const titleSelect = form.querySelector('[name="current_title_id"]');
    const instSelect = form.querySelector('[name="current_institution_id"]');

    const postdocUpdate = {
        link: form.querySelector('[name="link"]').value.trim() || null,
        notes: form.querySelector('[name="notes"]').value.trim() || null,
        cohort_number: parseInt(form.querySelector('[name="cohort_number"]').value, 10) || null,
        is_incoming: form.querySelector('[name="is_incoming"]').checked,
        department: form.querySelector('[name="department"]').value.trim() || null,
        discipline: form.querySelector('[name="discipline"]').value.trim() || null,
        postdoc_project_title: form.querySelector('[name="postdoc_project_title"]').value.trim() || null,
        current_title_id: titleSelect.value === 'other' ? null : (parseInt(titleSelect.value, 10) || null),
        current_title_other: titleSelect.value === 'other' ? form.querySelector('[name="current_title_other"]').value.trim() : null,
        current_institution_id: instSelect.value === 'other' ? null : (parseInt(instSelect.value, 10) || null),
        current_institution_other: instSelect.value === 'other' ? form.querySelector('[name="current_institution_other"]').value.trim() : null,
    };
    const roleData = {
        start_date: form.querySelector('[name="start_date"]').value || null,
        end_date: form.querySelector('[name="end_date"]').value || null,
    };
    try {
        await apiFetch(`/postdocs/${postdocId}/`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(postdocUpdate) });
        await apiFetch(`/person-roles/${postdocData.person_role_id}/`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(roleData) });
        await loadAndRenderMainDetails();
    } catch (err) {
        showError(err);
    }
}

async function setupConditionalInputs() {
    const titleSelect = detailsSection.querySelector('[name="current_title_id"]');
    const titleOtherContainer = detailsSection.querySelector('#current_title_other_container');
    const titleOtherInput = detailsSection.querySelector('[name="current_title_other"]');

    const instSelect = detailsSection.querySelector('[name="current_institution_id"]');
    const instOtherContainer = detailsSection.querySelector('#current_institution_other_container');
    const instOtherInput = detailsSection.querySelector('[name="current_institution_other"]');

    const setupSelect = async (select, otherContainer, otherInput, endpoint, textField, currentId, currentOther) => {
        select.onchange = () => {
            const show = select.value === 'other';
            otherContainer.classList.toggle('hidden', !show);
            if (!show) otherInput.value = '';
        };

        await populateDropdown(select, endpoint, textField, currentId, 'Select...', [{id: 'other', [textField]: 'Other'}]);

        if (currentOther && !currentId) {
            select.value = 'other';
        }

        select.dispatchEvent(new Event('change'));
        if (select.value === 'other') {
            otherInput.value = currentOther || '';
        }
    };

    await Promise.all([
        setupSelect(titleSelect, titleOtherContainer, titleOtherInput, '/researcher-titles/', 'title', postdocData.current_title_id, postdocData.current_title_other),
        setupSelect(instSelect, instOtherContainer, instOtherInput, '/institutions/', 'institution', postdocData.current_institution_id, postdocData.current_institution_other)
    ]);
}

// --- Panel Management ---
const panelLoaders = {
  projects: loadProjects,
  institutions: loadInstitutions,
  fields: loadFields,
  supervisors: loadSupervisors,
  supervisees: loadSupervisees,
  courses: loadCoursesTeaching,
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


// --- PROJECTS PANEL ---
async function loadProjects(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = `
    <tr>
      <th></th>
      <th class="cell-center">PI?</th>
      <th class="cell-center">Leader?</th>
      <th>Project #</th>
      <th>Call Type</th>
      <th>Title</th>
      <th>Start</th>
      <th>End</th>
      <th></th>
    </tr>`;
  try {
    const projectLinks = await apiFetch(`/person-roles/${postdocData.person_role_id}/projects/`);
    const enrichedData = await Promise.all(projectLinks.map(async (link) => {
      const projectDetails = await apiFetch(`/projects/${link.project_id}/`);
      return { ...link, project: projectDetails };
    }));
    tbody.innerHTML = '';
    if (!enrichedData.length) {
      tbody.innerHTML = `<tr><td colspan="9">No projects associated.</td></tr>`;
    } else {
      enrichedData.forEach(item => {
        const tr = document.createElement('tr');
        tr.dataset.projectId = item.project.id;
        renderProjectRow(tr, item);
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9">Could not load project data: ${err.message}</td></tr>`;
  }
  setupProjectsAddForm(panel);
}
function renderProjectRow(tr, item) {
  tr.innerHTML = `
    <td><a href="/manage-projects/${item.project.id}/" class="go-to-btn">Go to Project</a></td>
    <td class="cell-center">${item.is_principal_investigator ? '✔' : '✘'}</td>
    <td class="cell-center">${item.is_leader ? '✔' : '✘'}</td>
    <td>${item.project.project_number}</td>
    <td>${item.project.call_type.type}</td>
    <td>${item.project.title}</td>
    <td>${item.project.start_date?.split('T')[0] || ''}</td>
    <td>${item.project.end_date?.split('T')[0] || ''}</td>
    <td class="cell-actions">
      <button class="btn edit-btn">Edit</button>
      <button class="btn remove-btn">Remove</button>
    </td>`;
  tr.querySelector('.edit-btn').onclick = () => startEditProjectRow(tr, item);
  tr.querySelector('.remove-btn').onclick = () => {
    pendingRemove = { type: 'project', item };
    showModal(`Remove association for project "${item.project.title}"?`);
  };
}
function startEditProjectRow(tr, item) {
  tr.innerHTML = `
    <td><a href="/manage-projects/${item.project.id}/" class="go-to-btn">Go to Project</a></td>
    <td class="cell-center"><input type="checkbox" name="is_pi" ${item.is_principal_investigator ? 'checked' : ''}></td>
    <td class="cell-center"><input type="checkbox" name="is_leader" ${item.is_leader ? 'checked' : ''}></td>
    <td>${item.project.project_number}</td>
    <td>${item.project.call_type.type}</td>
    <td>${item.project.title}</td>
    <td>${item.project.start_date?.split('T')[0] || ''}</td>
    <td>${item.project.end_date?.split('T')[0] || ''}</td>
    <td class="cell-actions">
      <button class="btn save-btn">Save</button>
      <button class="btn cancel-btn">Cancel</button>
    </td>`;
  tr.querySelector('.cancel-btn').onclick = () => renderProjectRow(tr, item);
  tr.querySelector('.save-btn').onclick = async () => {
    const data = {
        person_role_id: postdocData.person_role_id,
        is_principal_investigator: tr.querySelector('[name=is_pi]').checked,
        is_leader: tr.querySelector('[name=is_leader]').checked
    };
    try {
      const updatedItem = await apiFetch(`/projects/${item.project.id}/people-roles/${postdocData.person_role_id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
      renderProjectRow(tr, { ...item, ...updatedItem });
    } catch (err) { showError(err); renderProjectRow(tr, item); }
  };
}
async function setupProjectsAddForm(panel) {
    const addForm = panel.querySelector('.item-add-form');
    const callTypeSelect = addForm.querySelector('[name=project_call_type_filter]');
    const statusSelect = addForm.querySelector('[name=project_status_filter]');
    const projectSelect = addForm.querySelector('[name=project_id]');

    const updateProjectDropdown = async () => {
        const params = new URLSearchParams();
        const callTypeId = callTypeSelect.value;
        const projectStatus = statusSelect.value;

        if (callTypeId) params.set('call_type_id', callTypeId);
        if (projectStatus) params.set('project_status', projectStatus);

        const projects = await apiFetch(`/projects/?${params}`);

        projects.sort((a, b) => (a.project_number || '').localeCompare(b.project_number || ''));

        projectSelect.innerHTML = '<option value="">Select a project...</option>';
        projects.forEach(p => {
            const opt = new Option(`[${p.project_number}] ${p.title}`, p.id);
            projectSelect.add(opt);
        });
    };

    await populateDropdown(callTypeSelect, '/project-call-types/', 'type', '', 'All call types');

    callTypeSelect.onchange = updateProjectDropdown;
    statusSelect.onchange = updateProjectDropdown;

    await updateProjectDropdown();

    setupPanelAddForm(panel, {
      loadFn: loadProjects,
      addCallback: (formData) => apiFetch(`/projects/${formData.get('project_id')}/people-roles/`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ person_role_id: postdocData.person_role_id, is_principal_investigator: formData.get('is_pi') === 'on', is_leader: formData.get('is_leader') === 'on' })
      }),
    });
}


// --- INSTITUTIONS PANEL ---
async function loadInstitutions(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = '<tr><th>Institution</th><th>Start Date</th><th>End Date</th><th></th></tr>';
  try {
    const institutionLinks = await apiFetch(`/person-roles/${postdocData.person_role_id}/institutions/`);
    const enrichedData = await Promise.all(institutionLinks.map(async (link) => {
        const details = await apiFetch(`/institutions/${link.institution_id}`);
        return { ...link, institution: details };
    }));

    tbody.innerHTML = '';
    if (!enrichedData.length) {
      tbody.innerHTML = `<tr><td colspan="4">No institutions associated.</td></tr>`;
    } else {
      enrichedData.forEach(item => {
        const tr = document.createElement('tr');
        tr.dataset.institutionId = item.institution.id;
        renderInstitutionRow(tr, item);
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4">Could not load institutions: ${err.message}</td></tr>`;
  }
  setupInstitutionsAddForm(panel);
}
function renderInstitutionRow(tr, item) {
    tr.innerHTML = `
      <td>${item.institution.institution}</td>
      <td>${item.start_date?.split('T')[0] || ''}</td>
      <td>${item.end_date?.split('T')[0] || ''}</td>
      <td class="cell-actions">
        <button class="btn edit-btn">Edit</button>
        <button class="btn remove-btn">Remove</button>
      </td>`;
    tr.querySelector('.edit-btn').onclick = () => startEditInstitutionRow(tr, item);
    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = { type: 'institution', item };
        showModal(`Remove association for "${item.institution.institution}"?`);
    };
}
function startEditInstitutionRow(tr, item) {
    tr.innerHTML = `
      <td>${item.institution.institution}</td>
      <td><input type="date" name="start_date" value="${item.start_date?.split('T')[0] || ''}"></td>
      <td><input type="date" name="end_date" value="${item.end_date?.split('T')[0] || ''}"></td>
      <td class="cell-actions">
        <button class="btn save-btn">Save</button>
        <button class="btn cancel-btn">Cancel</button>
      </td>`;
    tr.querySelector('.cancel-btn').onclick = () => renderInstitutionRow(tr, item);
    tr.querySelector('.save-btn').onclick = async () => {
        const data = {
            institution_id: item.institution.id,
            start_date: tr.querySelector('[name=start_date]').value || null,
            end_date: tr.querySelector('[name=end_date]').value || null
        };
        try {
            const updatedLink = await apiFetch(`/person-roles/${postdocData.person_role_id}/institutions/${item.institution.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            renderInstitutionRow(tr, { ...item, ...updatedLink });
        } catch(err) {
            showError(err);
            renderInstitutionRow(tr, item);
        }
    };
}
async function setupInstitutionsAddForm(panel) {
    await populateDropdown(panel.querySelector('[name=institution_id]'), '/institutions/', 'institution');
    setupPanelAddForm(panel, {
        loadFn: loadInstitutions,
        addCallback: (formData) => apiFetch(`/person-roles/${postdocData.person_role_id}/institutions/`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                institution_id: parseInt(formData.get('institution_id')),
                start_date: formData.get('start_date') || null,
                end_date: formData.get('end_date') || null
            })
        }),
    });
}


// --- ACADEMIC FIELDS PANEL ---
async function loadFields(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = `<tr><th>Field (Branch)</th><th></th></tr>`;
  try {
    const fields = await apiFetch(`/person-roles/${postdocData.person_role_id}/fields/`);
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
        addCallback: (formData) => apiFetch(`/person-roles/${postdocData.person_role_id}/fields/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                field_id: parseInt(formData.get('field_id'))
            })
        }),
    });
}


// --- SUPERVISORS PANEL ---
async function loadSupervisors(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = `
    <tr>
      <th></th>
      <th class="cell-center">Main Supervisor?</th>
      <th>Role</th>
      <th>Name</th>
      <th></th>
    </tr>`;
  try {
    const supervisions = await apiFetch(`/person-roles/${postdocData.person_role_id}/supervisors/`);

    // Enrich each supervision with supervisor details
    const enrichedData = await Promise.all(supervisions.map(async (supervision) => {
      const supervisorRole = await apiFetch(`/person-roles/${supervision.supervisor_role_id}`);
      const subRolePath = ROLE_PATHS[supervisorRole.role.id];

      let subRoleId = null;
      if (subRolePath) {
        const subRoleData = await apiFetch(`/${subRolePath}/?person_role_id=${supervisorRole.id}`);
        if (subRoleData.length > 0) {
          subRoleId = subRoleData[0].id;
        }
      }
      return { ...supervision, supervisorRole, subRolePath, subRoleId };
    }));

    tbody.innerHTML = '';
    if (!enrichedData.length) {
      tbody.innerHTML = `<tr><td colspan="5">No supervisors associated.</td></tr>`;
    } else {
      enrichedData.forEach(item => {
        const tr = document.createElement('tr');
        tr.dataset.supervisionId = item.id;
        renderSupervisorRow(tr, item);
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5">Could not load supervisors: ${err.message}</td></tr>`;
  }
  setupSupervisorsAddForm(panel);
}

function renderSupervisorRow(tr, item) {
    const supervisor = item.supervisorRole.person;
    const roleName = ROLE_DISPLAY[item.supervisorRole.role.id] || item.supervisorRole.role.role;
    const profileLink = item.subRoleId ? `<a href="/manage-${item.subRolePath}/${item.subRoleId}/" class="go-to-btn">Go to Profile</a>` : '';

    tr.innerHTML = `
      <td>${profileLink}</td>
      <td class="cell-center">${item.is_main ? '✔' : '✘'}</td>
      <td>${roleName}</td>
      <td>${supervisor.first_name} ${supervisor.last_name}</td>
      <td class="cell-actions">
        <button class="btn edit-btn">Edit</button>
        <button class="btn remove-btn">Remove</button>
      </td>`;
    tr.querySelector('.edit-btn').onclick = () => startEditSupervisorRow(tr, item);
    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = {
            type: 'supervision',
            item,
            name: `supervision by ${supervisor.first_name} ${supervisor.last_name}`
        };
        showModal(`Remove ${pendingRemove.name}?`);
    };
}

function startEditSupervisorRow(tr, item) {
    const supervisor = item.supervisorRole.person;
    const roleName = ROLE_DISPLAY[item.supervisorRole.role.id] || item.supervisorRole.role.role;
    const profileLink = item.subRoleId ? `<a href="/manage-${item.subRolePath}/${item.subRoleId}/" class="go-to-btn">Go to Profile</a>` : '';

    tr.innerHTML = `
      <td>${profileLink}</td>
      <td class="cell-center"><input type="checkbox" name="is_main" ${item.is_main ? 'checked' : ''}></td>
      <td>${roleName}</td>
      <td>${supervisor.first_name} ${supervisor.last_name}</td>
      <td class="cell-actions">
        <button class="btn save-btn">Save</button>
        <button class="btn cancel-btn">Cancel</button>
      </td>`;
    tr.querySelector('.cancel-btn').onclick = () => renderSupervisorRow(tr, item);
    tr.querySelector('.save-btn').onclick = async () => {
        const data = {
            supervisor_role_id: item.supervisor_role_id,
            student_role_id: item.student_role_id,
            is_main: tr.querySelector('[name=is_main]').checked
        };
        try {
            const updatedItem = await apiFetch(`/person-roles/${item.student_role_id}/supervisors/${item.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            renderSupervisorRow(tr, { ...item, ...updatedItem });
        } catch (err) {
            showError(err);
            renderSupervisorRow(tr, item);
        }
    };
}

async function setupSupervisorsAddForm(panel) {
    const addForm = panel.querySelector('.item-add-form');
    const roleFilterSelect = addForm.querySelector('[name=supervisor_role_filter]');
    const supervisorSelect = addForm.querySelector('[name=supervisor_role_id]');

    const populateSupervisors = async () => {
        const rolePath = roleFilterSelect.value; // 'researchers' or 'postdocs'
        const url = `/${rolePath}/?is_active=true`;
        const activeSupervisors = await apiFetch(url);

        supervisorSelect.innerHTML = '<option value="">Select a person...</option>';
        activeSupervisors.forEach(supervisor => {
           const person = supervisor.person_role.person;
           const option = new Option(`${person.first_name} ${person.last_name}`, supervisor.person_role.id);
           supervisorSelect.add(option);
        });
    };

    roleFilterSelect.onchange = populateSupervisors;
    await populateSupervisors(); // Initial population

    setupPanelAddForm(panel, {
        loadFn: loadSupervisors,
        addCallback: (formData) => apiFetch(`/person-roles/${postdocData.person_role_id}/supervisors/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_role_id: postdocData.person_role_id,
                supervisor_role_id: parseInt(formData.get('supervisor_role_id')),
                is_main: formData.get('is_main') === 'on'
            })
        }),
    });
}


// --- SUPERVISEES PANEL ---
async function loadSupervisees(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = `
    <tr>
      <th></th>
      <th class="cell-center">Main Supervisor?</th>
      <th>Role</th>
      <th>Name</th>
      <th></th>
    </tr>`;
  try {
    const supervisions = await apiFetch(`/person-roles/${postdocData.person_role_id}/students/`);

    // Enrich each supervision with student details
    const enrichedData = await Promise.all(supervisions.map(async (supervision) => {
      const studentRole = await apiFetch(`/person-roles/${supervision.student_role_id}`);
      const subRolePath = ROLE_PATHS[studentRole.role.id];

      let subRoleId = null;
      if (subRolePath) {
        const subRoleData = await apiFetch(`/${subRolePath}/?person_role_id=${studentRole.id}`);
        if (subRoleData.length > 0) {
          subRoleId = subRoleData[0].id;
        }
      }
      return { ...supervision, studentRole, subRolePath, subRoleId };
    }));

    tbody.innerHTML = '';
    if (!enrichedData.length) {
      tbody.innerHTML = `<tr><td colspan="5">No supervisees associated.</td></tr>`;
    } else {
      enrichedData.forEach(item => {
        const tr = document.createElement('tr');
        tr.dataset.supervisionId = item.id;
        renderSuperviseeRow(tr, item);
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5">Could not load supervisees: ${err.message}</td></tr>`;
  }
  setupSuperviseesAddForm(panel);
}

function renderSuperviseeRow(tr, item) {
    const student = item.studentRole.person;
    const roleName = ROLE_DISPLAY[item.studentRole.role.id] || item.studentRole.role.role;
    const profileLink = item.subRoleId ? `<a href="/manage-${item.subRolePath}/${item.subRoleId}/" class="go-to-btn">Go to Profile</a>` : '';

    tr.innerHTML = `
      <td>${profileLink}</td>
      <td class="cell-center">${item.is_main ? '✔' : '✘'}</td>
      <td>${roleName}</td>
      <td>${student.first_name} ${student.last_name}</td>
      <td class="cell-actions">
        <button class="btn edit-btn">Edit</button>
        <button class="btn remove-btn">Remove</button>
      </td>`;
    tr.querySelector('.edit-btn').onclick = () => startEditSuperviseeRow(tr, item);
    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = {
            type: 'supervisee_relation', // Use a distinct type
            item,
            name: `supervision for ${student.first_name} ${student.last_name}`
        };
        showModal(`Remove ${pendingRemove.name}?`);
    };
}

function startEditSuperviseeRow(tr, item) {
    const student = item.studentRole.person;
    const roleName = ROLE_DISPLAY[item.studentRole.role.id] || item.studentRole.role.role;
    const profileLink = item.subRoleId ? `<a href="/manage-${item.subRolePath}/${item.subRoleId}/" class="go-to-btn">Go to Profile</a>` : '';

    tr.innerHTML = `
      <td>${profileLink}</td>
      <td class="cell-center"><input type="checkbox" name="is_main" ${item.is_main ? 'checked' : ''}></td>
      <td>${roleName}</td>
      <td>${student.first_name} ${student.last_name}</td>
      <td class="cell-actions">
        <button class="btn save-btn">Save</button>
        <button class="btn cancel-btn">Cancel</button>
      </td>`;
    tr.querySelector('.cancel-btn').onclick = () => renderSuperviseeRow(tr, item);
    tr.querySelector('.save-btn').onclick = async () => {
        const data = {
            supervisor_role_id: item.supervisor_role_id,
            student_role_id: item.student_role_id,
            is_main: tr.querySelector('[name=is_main]').checked
        };
        try {
            const updatedItem = await apiFetch(`/person-roles/${item.supervisor_role_id}/students/${item.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            renderSuperviseeRow(tr, { ...item, ...updatedItem });
        } catch (err) {
            showError(err);
            renderSuperviseeRow(tr, item);
        }
    };
}

async function setupSuperviseesAddForm(panel) {
    const addForm = panel.querySelector('.item-add-form');
    const roleFilterSelect = addForm.querySelector('[name=supervisee_role_filter]');
    const studentSelect = addForm.querySelector('[name=student_role_id]');

    const populateStudents = async () => {
        const rolePath = roleFilterSelect.value; // 'phd-students' or 'postdocs'
        const url = `/${rolePath}/?is_active=true`;
        const activeStudents = await apiFetch(url);

        studentSelect.innerHTML = '<option value="">Select a person...</option>';
        activeStudents.forEach(student => {
           const person = student.person_role.person;
           const option = new Option(`${person.first_name} ${person.last_name}`, student.person_role.id);
           studentSelect.add(option);
        });
    };

    roleFilterSelect.onchange = populateStudents;
    await populateStudents(); // Initial population

    setupPanelAddForm(panel, {
        loadFn: loadSupervisees,
        addCallback: (formData) => apiFetch(`/person-roles/${postdocData.person_role_id}/students/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                supervisor_role_id: postdocData.person_role_id,
                student_role_id: parseInt(formData.get('student_role_id')),
                is_main: formData.get('is_main') === 'on'
            })
        }),
    });
}


// --- COURSES TEACHING PANEL ---
async function loadCoursesTeaching(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = `
    <tr>
      <th></th>
      <th>Title</th>
      <th>Term</th>
      <th class="cell-center">Credits</th>
      <th></th>
    </tr>`;
  try {
    const courses = await apiFetch(`/person-roles/${postdocData.person_role_id}/courses_teaching/`);

    tbody.innerHTML = '';
    if (!courses.length) {
      tbody.innerHTML = `<tr><td colspan="5">This postdoc is not associated with any courses.</td></tr>`;
    } else {
      courses.forEach(item => {
        const tr = document.createElement('tr');
        tr.dataset.courseId = item.id;
        renderCourseTeachingRow(tr, item);
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5">Could not load courses: ${err.message}</td></tr>`;
  }
  setupCoursesTeachingAddForm(panel);
}

function renderCourseTeachingRow(tr, item) {
    let termLabel = '';
    if (item.course_term) {
      termLabel = `${item.course_term.season} ${item.course_term.year}`;
    } else if (item.grad_school_activity) {
      termLabel = `${item.grad_school_activity.activity_type.type} ${item.grad_school_activity.year}`;
    }

    tr.innerHTML = `
      <td><a href="/manage-courses/${item.id}/" class="go-to-btn">Go to Course</a></td>
      <td>${item.title}</td>
      <td>${termLabel}</td>
      <td class="cell-center">${item.credit_points || ''}</td>
      <td class="cell-actions">
        <button class="btn remove-btn">Remove</button>
      </td>`;

    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = {
            type: 'course_teaching',
            item,
            name: `teaching assignment for "${item.title}"`
        };
        showModal(`Remove ${pendingRemove.name}?`);
    };
}

async function setupCoursesTeachingAddForm(panel) {
    const addForm = panel.querySelector('.item-add-form');
    const termFilter = addForm.querySelector('[name=course_term_filter]');
    const activityFilter = addForm.querySelector('[name=course_activity_filter]');
    const courseSelect = addForm.querySelector('[name=course_id]');

    const allTerms = await apiFetch('/course-terms/');
    const allActivities = await apiFetch('/grad-school-activities/');

    termFilter.innerHTML = '<option value="">All Regular Terms</option>';
    allTerms
        .filter(t => t.is_active)
        .forEach(t => {
            const opt = new Option(`${t.season} ${t.year}`, t.id);
            termFilter.add(opt);
        });

    activityFilter.innerHTML = '<option value="">All GS Activities</option>';
    allActivities.forEach(a => {
        const opt = new Option(`${a.activity_type.type} ${a.year}`, a.id);
        activityFilter.add(opt);
    });

    const updateCourseList = async () => {
        const params = new URLSearchParams();
        params.set('is_active_term', 'true');

        const termId = termFilter.value;
        const activityId = activityFilter.value;

        if (termId) params.set('term_id', termId);
        if (activityId) params.set('activity_id', activityId);

        const courses = await apiFetch(`/courses/?${params}`);
        courseSelect.innerHTML = '<option value="">Select a course...</option>';
        courses.forEach(course => {
            let termLabel = '';
            if (course.course_term) termLabel = `${course.course_term.season} ${course.course_term.year}`;
            else if (course.grad_school_activity) termLabel = `${course.grad_school_activity.activity_type.type} ${course.grad_school_activity.year}`;
            const opt = new Option(`${course.title} (${termLabel})`, course.id);
            courseSelect.add(opt);
        });
    };

    termFilter.onchange = () => {
        if (termFilter.value) activityFilter.value = '';
        updateCourseList();
    };
    activityFilter.onchange = () => {
        if (activityFilter.value) termFilter.value = '';
        updateCourseList();
    };

    await updateCourseList();

    setupPanelAddForm(panel, {
        loadFn: loadCoursesTeaching,
        addCallback: (formData) => apiFetch(`/courses/${formData.get('course_id')}/teachers/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                person_role_id: postdocData.person_role_id,
            })
        }),
    });
}


// --- DECISION LETTERS PANEL ---
async function loadDecisionLetters(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = `<tr><th>Link</th><th></th></tr>`;
  try {
    const letters = await apiFetch(`/person-roles/${postdocData.person_role_id}/decision-letters/`);
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
        const data = {
            link: tr.querySelector('[name=link]').value.trim()
        };
        try {
            const updatedItem = await apiFetch(`/person-roles/${postdocData.person_role_id}/decision-letters/${item.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            renderDecisionLetterRow(tr, updatedItem);
        } catch (err) {
            showError(err);
            renderDecisionLetterRow(tr, item);
        }
    };
}

function setupDecisionLettersAddForm(panel) {
    setupPanelAddForm(panel, {
        loadFn: loadDecisionLetters,
        addCallback: (formData) => apiFetch(`/person-roles/${postdocData.person_role_id}/decision-letters/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                link: formData.get('link').trim()
            })
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
    if (type === 'project') {
      await apiFetch(`/projects/${item.project.id}/people-roles/${postdocData.person_role_id}`, { method: 'DELETE' });
      await loadProjects(document.getElementById('panel-content-projects'));
    } else if (type === 'institution') {
      await apiFetch(`/person-roles/${postdocData.person_role_id}/institutions/${item.institution.id}`, { method: 'DELETE' });
      await loadInstitutions(document.getElementById('panel-content-institutions'));
    } else if (type === 'field') {
      await apiFetch(`/person-roles/${postdocData.person_role_id}/fields/${item.id}`, { method: 'DELETE' });
      await loadFields(document.getElementById('panel-content-fields'));
    } else if (type === 'supervision') {
      await apiFetch(`/person-roles/${item.student_role_id}/supervisors/${item.id}`, { method: 'DELETE' });
      await loadSupervisors(document.getElementById('panel-content-supervisors'));
    } else if (type === 'supervisee_relation') {
      await apiFetch(`/person-roles/${item.supervisor_role_id}/students/${item.id}`, { method: 'DELETE' });
      await loadSupervisees(document.getElementById('panel-content-supervisees'));
    } else if (type === 'course_teaching') {
      await apiFetch(`/courses/${item.id}/teachers/${postdocData.person_role_id}`, { method: 'DELETE' });
      await loadCoursesTeaching(document.getElementById('panel-content-courses'));
    } else if (type === 'decision_letter') {
      await apiFetch(`/person-roles/${postdocData.person_role_id}/decision-letters/${item.id}`, { method: 'DELETE' });
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

async function populateDropdown(select, endpoint, textField, selectedId = null, defaultOption = 'Select...', extraOptions = []) {
  try {
    const items = await apiFetch(endpoint);
    select.innerHTML = `<option value="">${defaultOption}</option>`;

    extraOptions.forEach(item => {
        const text = item[textField];
        const option = new Option(text, item.id);
        select.add(option);
    });

    items.forEach(item => {
      const text = typeof textField === 'function' ? textField(item) : item[textField];
      const option = new Option(text, item.id);
      if (item.id === selectedId) option.selected = true;
      select.add(option);
    });
  } catch (err) { showError(err); }
}
