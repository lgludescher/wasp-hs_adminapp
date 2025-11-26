import { apiFetch } from './main.js';

const ROLE_DISPLAY = {
  1: 'Researcher',
  2: 'PhD Student',
  3: 'Postdoc'
};

const filterSearch    = document.getElementById('filter-search');
const btnShowCreate   = document.getElementById('btn-show-create');
const formCreate      = document.getElementById('form-create');
const btnCancelCreate = document.getElementById('btn-cancel-create');
const tbody           = document.getElementById('people-tbody');

const modal           = document.getElementById('modal-confirm');
const modalText       = document.getElementById('modal-text');
const modalConfirmBtn = document.getElementById('modal-confirm-btn');
const modalCancelBtn  = document.getElementById('modal-cancel-btn');

let pendingRemove = null;
let expandedRow   = null;

/** Initial load */
(async function init() {
  filterSearch.oninput = debounce(loadPeople, 300);
  btnShowCreate.onclick = () => {
    formCreate.classList.remove('hidden');
    btnShowCreate.disabled = true;
  };
  btnCancelCreate.onclick = () => {
    formCreate.reset();
    formCreate.classList.add('hidden');
    btnShowCreate.disabled = false;
  };
  formCreate.onsubmit = createPerson;
  modalCancelBtn.onclick = () => { pendingRemove = null; modal.classList.add('hidden'); };
  modalConfirmBtn.onclick = confirmRemove;

  loadPeople();
})();

/** Load & render people */
async function loadPeople() {
  const params = new URLSearchParams();
  if (filterSearch.value.trim()) params.set('search', filterSearch.value.trim());
  try {
    const list = await apiFetch('/people/?' + params);
    renderTable(list);
  } catch (err) {
    showError(err);
  }
}

/** Render main table */
function renderTable(list) {
  tbody.innerHTML = '';
  list.forEach(person => {
    const tr = document.createElement('tr');
    tr.dataset.personId = person.id;
    tr.innerHTML = `
      <td><button class="expand-btn btn">+</button></td>
      <td>${person.first_name}</td>
      <td>${person.last_name}</td>
      <td>${person.email}</td>
      <td class="cell-actions">
        <button class="btn edit-btn">Edit</button>
        <button class="btn remove-btn">Remove</button>
      </td>
    `;
    attachPersonHandlers(tr, person);
    tbody.append(tr);
  });
}

/** Wire up each row’s handlers */
function attachPersonHandlers(tr, person) {
  tr.querySelector('.expand-btn').onclick = () => toggleExpand(tr, person);
  tr.querySelector('.edit-btn').onclick   = () => startEditPerson(tr, person);
  tr.querySelector('.remove-btn').onclick = () => {
    pendingRemove = {
      type: 'person',
      id: person.id,
      name: person.first_name + ' ' + person.last_name
    };
    showModal(`Remove person “${pendingRemove.name}”?`);
  };
}

/** Toggle expand/collapse */
async function toggleExpand(tr, person) {
  if (expandedRow && expandedRow !== tr) collapseExpanded();

  const btn = tr.querySelector('.expand-btn');
  if (tr.nextElementSibling?.classList.contains('expanded-row')) {
    collapseExpanded();
    return;
  }

  btn.textContent = '–';
  expandedRow = tr;

  // 1) fetch person-roles
  let rawRoles;
  try {
    rawRoles = await apiFetch(`/person-roles/?person_id=${person.id}`);
  } catch (err) {
    showError(err);
    return;
  }

  // 2) lookup each sub-record ID
  const roles = await Promise.all(rawRoles.map(async r => {
    let subType = '', subId = '';
    const rid = r.id;
    if (r.role.id === 1) { // Researcher
      subType = 'researchers';
      const arr = await apiFetch(`/researchers/?person_role_id=${rid}`);
      subId = arr[0]?.id || '';
    } else if (r.role.id === 2) { // PhD Student
      subType = 'phd-students';
      const arr = await apiFetch(`/phd-students/?person_role_id=${rid}`);
      subId = arr[0]?.id || '';
    } else if (r.role.id === 3) { // Postdoc
      subType = 'postdocs';
      const arr = await apiFetch(`/postdocs/?person_role_id=${rid}`);
      subId = arr[0]?.id || '';
    }
    return { ...r, subType, subId };
  }));

  // 3) render expanded panel
  const panel = document.createElement('tr');
  panel.classList.add('expanded-row');
  panel.innerHTML = `
    <td colspan="5">
      <div class="expanded-content">
        <button class="btn btn-secondary add-role-btn">Add Role</button>
        <form class="role-form hidden">
          <label>Role:
            <select name="role_id">
              <option value="">Select…</option>
              <option value="1">Researcher</option>
              <option value="2">PhD Student</option>
              <option value="3">Postdoc</option>
            </select>
          </label>
          <label>Start Date:
            <input name="start_date" type="date" min="2019-01-01" required />
          </label>
          <label>End Date:
            <input name="end_date" type="date" min="2019-01-01" />
          </label>
          <label>Notes:
            <input name="notes" type="text" />
          </label>
          <div class="form-actions-inline">
            <button type="submit" class="btn btn-secondary save-btn">Save</button>
            <button type="button" class="btn btn-secondary cancel-btn">Cancel</button>
          </div>
        </form>
        <table class="role-table">
          <thead>
            <tr>
              <th></th>
              <th>Role</th>
              <th>&nbsp;Start&nbsp;Date&nbsp;</th>
              <th>&nbsp;&nbsp;End&nbsp;Date&nbsp;&nbsp;</th>
              <th>Notes</th>
              <th class="cell-actions"></th>
            </tr>
          </thead>
          <tbody>
            ${roles.map(r => renderRoleRow(r)).join('')}
          </tbody>
        </table>
      </div>
    </td>
  `;
  tr.after(panel);
  attachPanelHandlers(panel, person.id);
}

/** Collapse panel */
function collapseExpanded() {
  if (!expandedRow) return;
  expandedRow.querySelector('.expand-btn').textContent = '+';
  const next = expandedRow.nextElementSibling;
  if (next?.classList.contains('expanded-row')) next.remove();
  expandedRow = null;
}

/** Render one role‐row */
function renderRoleRow(r) {
  const { id, subType, subId } = r;
  return `
    <tr data-role-id="${id}" data-sub-type="${subType}" data-sub-id="${subId}">
      <td>
        <a href="/manage-${subType}/${subId}/" class="go-role-btn">Go to Profile</a>
      </td>
      <td>${ROLE_DISPLAY[r.role.id] || r.role.role}</td>
      <td>${r.start_date?.split('T')[0] || ''}</td>
      <td>${r.end_date?.split('T')[0]   || ''}</td>
      <td>${r.notes || ''}</td>
      <td class="cell-actions">
        <button class="btn btn-secondary edit-role-btn">Edit</button>
        <button class="btn btn-secondary remove-role-btn">Remove</button>
      </td>
    </tr>
  `;
}

/** Setup add/edit/remove in panel */
function attachPanelHandlers(panel, personId) {
  const addBtn     = panel.querySelector('.add-role-btn');
  const form       = panel.querySelector('.role-form');
  const cancelForm = form.querySelector('.cancel-btn');

  // Check backend for active roles before showing the form
  addBtn.onclick = async () => {
    try {
      // Call the endpoint with the active=true filter
      const activeRoles = await apiFetch(`/person-roles/?person_id=${personId}&active=true`);

      // If the list is not empty, an active role exists
      if (activeRoles.length > 0) {
        showError('Only one active role is allowed at a time.');
        return;
      }

      // Safe to add new role
      form.classList.remove('hidden');
    } catch (err) {
      showError(err);
    }
  };

  cancelForm.onclick   = () => form.reset() || form.classList.add('hidden');

  form.onsubmit = async e => {
    e.preventDefault();
    // pre-validate role selection
    if (!form.role_id.value) {
      showError('Please select a role.');
      return;
    }

    const data = {
      person_id:  personId,
      role_id:    +form.role_id.value,
      start_date: form.start_date.value,
      end_date:   form.end_date.value || null,
      notes:      form.notes.value.trim() || null,
    };
    try {
      const pr = await apiFetch('/person-roles/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      const map = { 1:'researchers',2:'phd-students',3:'postdocs' };
      const subPath = map[pr.role.id];
      try {
        await apiFetch(`/${subPath}/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ person_role_id: pr.id }),
        });
      } catch (subErr) {
        await apiFetch(`/person-roles/${pr.id}`,{ method:'DELETE' });
        throw subErr;
      }
      form.reset();
      form.classList.add('hidden');
      await refreshRoles(personId);
    } catch (err) {
      showError(err);
    }
  };

  panel.querySelectorAll('tr[data-role-id]').forEach(row => {
    const rid = row.dataset.roleId;
    row.querySelector('.remove-role-btn').onclick = () => {
      pendingRemove = { type: 'role', id: rid, personId };
      showModal(`Remove this role?`);
    };
    row.querySelector('.edit-role-btn').onclick = () =>
      startEditRole(row, personId);
  });
}

/** Refresh only roles (no collapse) */
async function refreshRoles(personId) {
  try {
    const panel = expandedRow.nextElementSibling;
    const tbodyR = panel.querySelector('.role-table tbody');
    const rawRoles = await apiFetch(`/person-roles/?person_id=${personId}`);
    const roles = await Promise.all(rawRoles.map(async r => {
      let subType='', subId='';
      const rid = r.id;
      if (r.role.id===1) {
        subType='researchers';
        const arr=await apiFetch(`/researchers/?person_role_id=${rid}`);
        subId=arr[0]?.id||'';
      } else if(r.role.id===2) {
        subType='phd-students';
        const arr=await apiFetch(`/phd-students/?person_role_id=${rid}`);
        subId=arr[0]?.id||'';
      } else if(r.role.id===3) {
        subType='postdocs';
        const arr=await apiFetch(`/postdocs/?person_role_id=${rid}`);
        subId=arr[0]?.id||'';
      }
      return {...r,subType,subId};
    }));
    tbodyR.innerHTML = roles.map(r=>renderRoleRow(r)).join('');
    attachPanelHandlers(panel, personId);
  } catch (err) {
    showError(err);
  }
}

/** Inline edit person */
function startEditPerson(tr, person) {
  tr.innerHTML = `
    <td><button class="expand-btn btn">+</button></td>
    <td><input name="first_name" value="${person.first_name}" /></td>
    <td><input name="last_name"  value="${person.last_name}"  /></td>
    <td><input name="email"      value="${person.email}"      /></td>
    <td class="cell-actions">
      <button class="btn save-btn">Save</button>
      <button class="btn cancel-btn">Cancel</button>
    </td>
  `;
  tr.querySelector('.expand-btn').onclick = () => toggleExpand(tr, person);
  tr.querySelector('.cancel-btn').onclick = loadPeople;
  tr.querySelector('.save-btn').onclick   = async () => {
    const updated = {
      first_name: tr.querySelector('[name="first_name"]').value.trim(),
      last_name:  tr.querySelector('[name="last_name"]').value.trim(),
      email:      tr.querySelector('[name="email"]').value.trim()
    };
    try {
      await apiFetch(`/people/${person.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated),
      });
      loadPeople();
    } catch (err) {
      showError(err);
    }
  };
}

/** Inline edit role */
function startEditRole(row, personId) {
  const rid      = row.dataset.roleId;
  const roleName = ROLE_DISPLAY[row.dataset.subType === 'researchers' ? 1
                     : row.dataset.subType === 'phd-students' ? 2
                     : 3];
  const subType  = row.dataset.subType;
  const subId    = row.dataset.subId;

  row.innerHTML = `
    <td>
      <a href="/manage-${subType}/${subId}/" class="go-role-btn">Go to Profile</a>
    </td>
    <td>${roleName}</td>
    <td><input name="start_date" type="date" value="${row.cells[2].textContent}" /></td>
    <td><input name="end_date"   type="date" value="${row.cells[3].textContent}" /></td>
    <td><input name="notes"      value="${row.cells[4].textContent}"              /></td>
    <td class="cell-actions">
      <button class="btn btn-secondary save-btn">Save</button>
      <button class="btn btn-secondary cancel-btn">Cancel</button>
    </td>
  `;

  row.querySelector('.cancel-btn').onclick = () => refreshRoles(personId);
  row.querySelector('.save-btn').onclick   = async () => {
    const updated = {
      start_date: row.querySelector('[name="start_date"]').value,
      end_date:   row.querySelector('[name="end_date"]').value || null,
      notes:      row.querySelector('[name="notes"]').value.trim() || null
    };
    try {
      await apiFetch(`/person-roles/${rid}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated),
      });
      await refreshRoles(personId);
    } catch (err) {
      showError(err);
    }
  };
}

/** Create person */
async function createPerson(e) {
  e.preventDefault();
  const data = {
    first_name: formCreate.first_name.value.trim(),
    last_name:  formCreate.last_name.value.trim(),
    email:      formCreate.email.value.trim()
  };
  try {
    await apiFetch('/people/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    formCreate.reset();
    formCreate.classList.add('hidden');
    btnShowCreate.disabled = false;
    loadPeople();
  } catch (err) {
    showError(err);
  }
}

/** Confirmation modal */
function showModal(message) {
  modalText.textContent = message;
  modalConfirmBtn.style.display = '';
  modalCancelBtn.textContent = 'Cancel';
  modal.classList.remove('hidden');
}

async function confirmRemove() {
  if (!pendingRemove) return;
  try {
    if (pendingRemove.type === 'role') {
      const { id: rId, personId } = pendingRemove;
      const row = document.querySelector(`tr[data-role-id="${rId}"]`);
      const subType = row.dataset.subType;
      const subId   = row.dataset.subId;
      if (subType && subId) {
        await apiFetch(`/${subType}/${subId}/`, { method: 'DELETE' });
      }
      await apiFetch(`/person-roles/${rId}/`, { method: 'DELETE' });
      await refreshRoles(personId);
    } else {
      await apiFetch(`/people/${pendingRemove.id}/`, { method: 'DELETE' });
      await loadPeople();
    }
    pendingRemove = null;
    modal.classList.add('hidden');
  } catch (err) {
    showError(err);
  }
}

/** Error modal */
function showError(err) {
  modalText.textContent = err.message || String(err);
  modalConfirmBtn.style.display = 'none';
  modalCancelBtn.textContent = 'OK';
  modal.classList.remove('hidden');
}

/** Debounce */
function debounce(fn, delay) {
  let t;
  return (...a) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...a), delay);
  };
}
