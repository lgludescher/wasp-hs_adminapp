import { apiFetch } from './main.js';

const projectTotalCount = document.getElementById('project-total-count');
const filterSearch      = document.getElementById('filter-search');
const filterCallType    = document.getElementById('filter-call-type');
const filterStatus      = document.getElementById('filter-status');
const filterBranch      = document.getElementById('filter-branch');
const filterField       = document.getElementById('filter-field');
const btnExportExcel    = document.getElementById('btn-export-excel');

const btnShowCreate     = document.getElementById('btn-show-create');
const formCreate        = document.getElementById('form-create');
const btnCancelCreate   = document.getElementById('btn-cancel-create');
const createCallTypeSel = formCreate.querySelector('select[name="call_type_id"]');

const tbody             = document.getElementById('projects-tbody');

const modal             = document.getElementById('modal-confirm');
const modalText         = document.getElementById('modal-text');
const modalConfirmBtn   = document.getElementById('modal-confirm-btn');
const modalCancelBtn    = document.getElementById('modal-cancel-btn');

let pendingRemove = null;

/** Initial load */
;(async function init() {
  await loadCallTypes();
  await loadBranches();
  await loadFields();
  loadProjects();
})();

/** Load call types */
async function loadCallTypes() {
  try {
    const list = await apiFetch('/project-call-types/');
    list.forEach(item => {
      filterCallType.append(new Option(item.type, item.id));
      createCallTypeSel.append(new Option(item.type, item.id));
    });
  } catch (err) { showError(err) }
}

/** Load branches */
async function loadBranches() {
  try {
    const list = await apiFetch('/branches/');
    list.forEach(b => filterBranch.append(new Option(b.branch, b.id)));
  } catch (err) { showError(err) }
}

/** Load fields, optionally by branch */
async function loadFields(branchId = '') {
  try {
    const url = branchId ? `/fields/?branch_id=${branchId}` : '/fields/';
    const list = await apiFetch(url);
    filterField.innerHTML = '<option value="">All fields</option>';
    list.forEach(f => filterField.append(new Option(f.field, f.id)));
  } catch (err) { showError(err) }
}

/** Branch → fields → projects */
filterBranch.onchange = async () => {
  await loadFields(filterBranch.value);
  loadProjects();
};

/** Other filters → projects */
filterSearch.oninput    = debounce(loadProjects, 300);
filterCallType.onchange  = loadProjects;
filterStatus.onchange    = loadProjects;
filterField.onchange     = loadProjects;

function debounce(fn, delay) {
  let t;
  return (...a) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...a), delay);
  };
}

/** Fetch & render */
async function loadProjects() {
  try {
    const p = new URLSearchParams();
    if (filterSearch.value.trim())   p.set('search', filterSearch.value.trim());
    if (filterCallType.value)        p.set('call_type_id', filterCallType.value);
    if (filterStatus.value)          p.set('project_status', filterStatus.value);
    if (filterBranch.value)          p.set('branch_id', filterBranch.value);
    if (filterField.value)           p.set('field_id', filterField.value);

    const list = await apiFetch('/projects/?' + p);
    renderTable(list);
  } catch (err) { showError(err) }
}

/** Build rows, using an <a> for the “Go to project” link */
function renderTable(list) {
  projectTotalCount.textContent = `(${list.length})`;

  tbody.innerHTML = '';
  list.forEach(item => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><a class="go-btn" href="/manage-projects/${item.id}">Go to project</a></td>
      <td>${item.project_number}</td>
      <td>${item.call_type.type}</td>
      <td>${item.title}</td>
      
      <td class="cell-center">${item.field_count ?? 0}</td>
      
      <td>${item.start_date?.split('T')[0]||''}</td>
      <td>${item.end_date?.split('T')[0]||''}</td>
      <td class="cell-actions">
        <button class="btn edit-btn">Edit</button>
        <button class="btn remove-btn">Remove</button>
      </td>
    `;
    attachHandlers(tr, item);
    tbody.append(tr);
  });
}

/** Wire up Edit / Remove */
function attachHandlers(tr, item) {
  tr.querySelector('.edit-btn').onclick   = () => startEdit(tr, item);
  tr.querySelector('.remove-btn').onclick = () => {
    pendingRemove = item.id;
    showModal(`Remove project “${item.title}”?`);
  };
}

/** Inline edit (now preserves the Go link) */
function startEdit(tr, item) {
  tr.innerHTML = `
    <td><a class="go-btn" href="/manage-projects/${item.id}">Go to project</a></td>
    <td><input name="project_number" value="${item.project_number}" required /></td>
    <td><select name="call_type_id" required></select></td>
    <td><input name="title" value="${item.title}" required /></td>
    
    <td class="cell-center" style="color: #888;">${item.field_count ?? 0}</td>
    
    <td><input name="start_date" type="date" value="${item.start_date?.split('T')[0]||''}" /></td>
    <td><input name="end_date"   type="date" value="${item.end_date?.split('T')[0]||''}" /></td>
    <td class="cell-actions">
      <button class="btn save-btn">Save</button>
      <button class="btn cancel-btn">Cancel</button>
    </td>
  `;
  const sel = tr.querySelector('select[name="call_type_id"]');
  document.querySelectorAll('#filter-call-type option')
          .forEach(o => sel.append(o.cloneNode(true)));
  sel.value = item.call_type_id;

  tr.querySelector('.cancel-btn').onclick = loadProjects;
  tr.querySelector('.save-btn').onclick = async () => {
    const updated = {
      project_number: tr.querySelector('[name="project_number"]').value.trim() || null,
      call_type_id:   parseInt(sel.value) || null,
      title:          tr.querySelector('[name="title"]').value.trim() || null,
      start_date:     tr.querySelector('[name="start_date"]').value || null,
      end_date:       tr.querySelector('[name="end_date"]').value   || null,
    };
    try {
      await apiFetch(`/projects/${item.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated),
      });
      loadProjects();
    } catch (err) { showError(err) }
  };
}

/** Create‐form toggle */
btnShowCreate.onclick = () => {
  formCreate.classList.remove('hidden');
  btnShowCreate.disabled = true;
};
btnCancelCreate.onclick = () => {
  formCreate.reset();
  formCreate.classList.add('hidden');
  btnShowCreate.disabled = false;
};

/** Submit creation */
formCreate.onsubmit = async e => {
  e.preventDefault();
  const data = {
    project_number: formCreate.project_number.value.trim(),
    call_type_id:   parseInt(formCreate.call_type_id.value),
    title:          formCreate.title.value.trim(),
    final_report_submitted:  formCreate.final_report_submitted.checked,
    is_extended:    formCreate.is_extended.checked,
    start_date:     formCreate.start_date.value || null,
    end_date:       formCreate.end_date.value   || null,
    notes:          formCreate.notes.value.trim() || null,
  };
  try {
    await apiFetch('/projects/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    formCreate.reset();
    formCreate.classList.add('hidden');
    btnShowCreate.disabled = false;
    loadProjects();
  } catch (err) { showError(err) }
};

btnExportExcel.onclick = () => {
  const p = new URLSearchParams();
  if (filterSearch.value.trim())   p.set('search', filterSearch.value.trim());
  if (filterCallType.value)        p.set('call_type_id', filterCallType.value);
  if (filterStatus.value)          p.set('project_status', filterStatus.value);
  if (filterBranch.value)          p.set('branch_id', filterBranch.value);
  if (filterField.value)           p.set('field_id', filterField.value);

  const exportUrl = `/projects/export/projects.xlsx?${p.toString()}`;
  window.location.href = exportUrl;
};

/** Confirmation modal */
function showModal(message) {
  modalText.textContent = message;
  modalConfirmBtn.style.display = '';
  modalCancelBtn.textContent = 'Cancel';
  modal.classList.remove('hidden');
}
modalCancelBtn.onclick = () => {
  pendingRemove = null;
  modal.classList.add('hidden');
};
modalConfirmBtn.onclick = async () => {
  if (!pendingRemove) return;
  try {
    await apiFetch(`/projects/${pendingRemove}`, { method: 'DELETE' });
    loadProjects();
    pendingRemove = null;
    modal.classList.add('hidden');
  } catch (err) { showError(err) }
}

/** Error only */
function showError(err) {
  const msg = err instanceof Error ? err.message : String(err);
  modalText.textContent = msg;
  modalConfirmBtn.style.display = 'none';
  modalCancelBtn.textContent = 'OK';
  modal.classList.remove('hidden');
}
