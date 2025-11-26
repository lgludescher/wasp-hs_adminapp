import { apiFetch, openEmailListModal } from './main.js';

const PHDS_ENDPOINT         = '/phd-students/';
const INSTITUTIONS_ENDPOINT = '/institutions/';
const BRANCHES_ENDPOINT     = '/branches/';
const FIELDS_ENDPOINT       = '/fields/';

const filterSearch      = document.getElementById('filter-search');
const filterActive      = document.getElementById('filter-active');
const filterCohort      = document.getElementById('filter-cohort');
const filterAffiliated  = document.getElementById('filter-affiliated');
const filterGraduated   = document.getElementById('filter-graduated');
const filterInstitution = document.getElementById('filter-institution');
const filterBranch      = document.getElementById('filter-branch');
const filterField       = document.getElementById('filter-field');
const btnDefault        = document.getElementById('btn-default');
const btnActivity       = document.getElementById('btn-activity');
const btnExportExcel    = document.getElementById('btn-export-excel');
const btnExportEmails   = document.getElementById('btn-export-emails');
const theadRow          = document.getElementById('students-thead');
const tbody             = document.getElementById('students-tbody');

const modal             = document.getElementById('modal-confirm');
const modalText         = document.getElementById('modal-text');
const modalConfirmBtn   = document.getElementById('modal-confirm-btn');
const modalCancelBtn    = document.getElementById('modal-cancel-btn');

let viewMode = 'default';

;(async function init() {
  filterActive.value = 'true';

  await loadCohorts();
  await loadInstitutions();
  await loadBranches();
  await loadFields();
  setupViewToggle();
  setupFilters();

  btnExportExcel.onclick = () => {
    const p = new URLSearchParams();
    // Add all the same filters as the loadStudents function
    if (filterSearch.value.trim()) p.set('search', filterSearch.value.trim());
    if (filterActive.value)        p.set('is_active', filterActive.value);
    if (filterCohort.value)        p.set('cohort_number', filterCohort.value);
    if (filterAffiliated.value)    p.set('is_affiliated', filterAffiliated.value);
    if (filterGraduated.value)     p.set('is_graduated', filterGraduated.value);
    if (filterInstitution.value)   p.set('institution_id', filterInstitution.value);
    if (filterBranch.value)        p.set('branch_id', filterBranch.value);
    if (filterField.value)         p.set('field_id', filterField.value);

    // Crucially, add the current view mode
    p.set('view_mode', viewMode);

    const exportUrl = `/phd-students/export/phd-students.xlsx?${p.toString()}`;
    window.location.href = exportUrl;
  };

  btnExportEmails.onclick = async () => {
    try {
      const p = new URLSearchParams();
      // Apply the same filters as the list view
      if (filterSearch.value.trim()) p.set('search', filterSearch.value.trim());
      if (filterActive.value)        p.set('is_active', filterActive.value);
      if (filterCohort.value)        p.set('cohort_number', filterCohort.value);
      if (filterAffiliated.value)    p.set('is_affiliated', filterAffiliated.value);
      if (filterGraduated.value)     p.set('is_graduated', filterGraduated.value);
      if (filterInstitution.value)   p.set('institution_id', filterInstitution.value);
      if (filterBranch.value)        p.set('branch_id', filterBranch.value);
      if (filterField.value)         p.set('field_id', filterField.value);

      // Fetch the data (returns { count, filter_summary, emails })
      const data = await apiFetch(`/phd-students/export/emails?${p.toString()}`);

      // Open the shared modal
      openEmailListModal(data);
    } catch (err) {
      showError(err);
    }
  };

  modalCancelBtn.onclick = () => modal.classList.add('hidden');
  renderHeader();
  loadStudents();
})();

function setupViewToggle() {
  btnDefault.onclick = () => switchView('default');
  btnActivity.onclick = () => switchView('activity');
}

function switchView(mode) {
  if (viewMode === mode) return;
  viewMode = mode;
  btnDefault.classList.toggle('active', mode === 'default');
  btnActivity.classList.toggle('active', mode === 'activity');
  filterActive.value = mode === 'default' ? 'true' : 'false';
  renderHeader();
  loadStudents();
}

async function loadCohorts() {
  try {
    const list = await apiFetch(PHDS_ENDPOINT);
    const years = Array.from(new Set(list.map(s => s.cohort_number).filter(n => n!=null))).sort((a,b)=>a-b);
    filterCohort.innerHTML = '<option value="">All cohorts</option>';
    years.forEach(n => filterCohort.append(new Option(n, n)));
  } catch (err) { showError(err) }
}

async function loadInstitutions() {
  try {
    const list = await apiFetch(INSTITUTIONS_ENDPOINT);
    filterInstitution.innerHTML = '<option value="">All institutions</option>';
    list.forEach(i => filterInstitution.append(new Option(i.institution, i.id)));
  } catch (err) { showError(err) }
}

async function loadBranches() {
  try {
    const list = await apiFetch(BRANCHES_ENDPOINT);
    filterBranch.innerHTML = '<option value="">All branches</option>';
    list.forEach(b => filterBranch.append(new Option(b.branch, b.id)));
  } catch (err) { showError(err) }
}

async function loadFields(branchId='') {
  try {
    const url = branchId ? `${FIELDS_ENDPOINT}?branch_id=${branchId}` : FIELDS_ENDPOINT;
    const list = await apiFetch(url);
    filterField.innerHTML = '<option value="">All fields</option>';
    list.forEach(f => filterField.append(new Option(f.field, f.id)));
  } catch (err) { showError(err) }
}

function setupFilters() {
  filterSearch.oninput      = debounce(loadStudents, 300);
  filterActive.onchange      = loadStudents;
  filterCohort.onchange      = loadStudents;
  filterAffiliated.onchange  = loadStudents;
  filterGraduated.onchange   = loadStudents;
  filterInstitution.onchange = loadStudents;
  filterBranch.onchange      = async () => { await loadFields(filterBranch.value); loadStudents(); };
  filterField.onchange       = loadStudents;
}

async function loadStudents() {
  try {
    const p = new URLSearchParams();
    if (filterSearch.value.trim()) p.set('search', filterSearch.value.trim());
    if (filterActive.value)        p.set('is_active', filterActive.value);
    if (filterCohort.value)        p.set('cohort_number', filterCohort.value);
    if (filterAffiliated.value)    p.set('is_affiliated', filterAffiliated.value);
    if (filterGraduated.value)     p.set('is_graduated', filterGraduated.value);
    if (filterInstitution.value)   p.set('institution_id', filterInstitution.value);
    if (filterBranch.value)        p.set('branch_id', filterBranch.value);
    if (filterField.value)         p.set('field_id', filterField.value);

    const list = await apiFetch(PHDS_ENDPOINT + '?' + p);
    renderTable(list);
  } catch (err) { showError(err) }
}

function renderHeader() {
  if (viewMode === 'default') {
    theadRow.innerHTML = `
      <th></th>
      <th>Name</th>
      <th>Email</th>
      <th class="col-center">Cohort</th>
      <th class="col-center">Affiliated</th>
      <th class="col-center">Graduated</th>
      <th>&nbsp;Start&nbsp;Date&nbsp;</th>
      <th>&nbsp;&nbsp;End&nbsp;Date&nbsp;&nbsp;</th>
      <th class="cell-actions"></th>
    `;
  } else {
    theadRow.innerHTML = `
      <th></th>
      <th>Name</th>
      <th class="col-center">Cohort</th>
      <th class="col-center">Affiliated</th>
      <th class="col-center">Graduated</th>
      <th>Current Title</th>
      <th>Current Organization</th>
      <th class="cell-actions"></th>
    `;
  }
}

function renderTable(list) {
  tbody.innerHTML = '';
  list.forEach(item => {
    const pr   = item.person_role;
    const name = pr.person.first_name + ' ' + pr.person.last_name;
    const cohort = item.cohort_number ?? '';
    const affChk = item.is_affiliated ? 'checked' : '';
    const grdChk = item.is_graduated   ? 'checked' : '';
    const start  = pr.start_date?.split('T')[0] || '';
    const end    = pr.end_date?.split('T')[0]   || '';
    let cols;
    if (viewMode === 'default') {
      cols = `
        <td>${name}</td>
        <td>${pr.person.email}</td>
        <td class="col-center">${cohort}</td>
        <td class="col-center"><input type="checkbox" disabled ${affChk} /></td>
        <td class="col-center"><input type="checkbox" disabled ${grdChk} /></td>
        <td>${start}</td>
        <td>${end}</td>
      `;
    } else {
      cols = `
        <td>${name}</td>
        <td class="col-center">${cohort}</td>
        <td class="col-center"><input type="checkbox" disabled ${affChk} /></td>
        <td class="col-center"><input type="checkbox" disabled ${grdChk} /></td>
        <td>${item.current_title ?? ''}</td>
        <td>${item.current_organization ?? ''}</td>
      `;
    }
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <a class="go-btn" href="/manage-phd-students/${item.id}/">Go to student</a>
      </td>
      ${cols}
      <td class="cell-actions">
        <button class="btn edit-btn">Edit</button>
      </td>
    `;
    attachHandlers(tr, item);
    tbody.append(tr);
  });
}

function attachHandlers(tr, item) {
  tr.querySelector('.edit-btn').onclick = () => startEdit(tr, item);
}

function startEdit(tr, item) {
  const pr    = item.person_role;
  const name  = pr.person.first_name + ' ' + pr.person.last_name;
  const start = pr.start_date?.split('T')[0] || '';
  const end   = pr.end_date?.split('T')[0]   || '';
  let editCols;
  if (viewMode === 'default') {
    editCols = `
      <td>${name}</td>
      <td>${pr.person.email}</td>
      <td class="col-center"><input name="cohort_number" type="number" min="0" max="99" value="${item.cohort_number ?? ''}" /></td>
      <td class="col-center"><input name="is_affiliated" type="checkbox" ${item.is_affiliated?'checked':''} /></td>
      <td class="col-center"><input name="is_graduated"  type="checkbox" ${item.is_graduated  ?'checked':''} /></td>
      <td><input name="start_date"    type="date"       value="${start}" /></td>
      <td><input name="end_date"      type="date"       value="${end}"   /></td>
    `;
  } else {
    editCols = `
      <td>${name}</td>
      <td class="col-center"><input name="cohort_number" type="number" min="0" max="99" value="${item.cohort_number ?? ''}" /></td>
      <td class="col-center"><input name="is_affiliated" type="checkbox" ${item.is_affiliated?'checked':''} /></td>
      <td class="col-center"><input name="is_graduated"  type="checkbox" ${item.is_graduated  ?'checked':''} /></td>
      <td><input name="current_title" type="text" value="${item.current_title ?? ''}" /></td>
      <td><input name="current_organization" type="text" value="${item.current_organization ?? ''}" /></td>
    `;
  }
  tr.innerHTML = `
    <td><a class="go-btn" href="/manage-phd-students/${item.id}/">Go to student</a></td>
    ${editCols}
    <td class="cell-actions">
      <button class="btn save-btn">Save</button>
      <button class="btn cancel-btn">Cancel</button>
    </td>
  `;
  const cohortInput = tr.querySelector('[name="cohort_number"]');
  cohortInput.oninput = () => { if (cohortInput.value.length>2) cohortInput.value = cohortInput.value.slice(0,2); };
  tr.querySelector('.cancel-btn').onclick = loadStudents;
  tr.querySelector('.save-btn').onclick = async () => {
    const newCoh  = parseInt(cohortInput.value) || null;
    const newAff  = tr.querySelector('[name="is_affiliated"]').checked;
    const newGrd  = tr.querySelector('[name="is_graduated"]').checked;
    let newStart, newEnd;
    if (viewMode === 'default') {
      newStart = tr.querySelector('[name="start_date"]').value || null;
      newEnd   = tr.querySelector('[name="end_date"]').value   || null;
    } else {
      // <<< FIX START
      // In activity view, keep original dates, ensuring empty strings become null
      newStart = start || null;
      newEnd   = end || null;
      // <<< FIX END
    }
    let newTitle = null, newOrg = null;
    if (viewMode === 'activity') {
      newTitle = tr.querySelector('[name="current_title"]').value || null;
      newOrg   = tr.querySelector('[name="current_organization"]').value || null;
    }
    try {
      const payload = { cohort_number: newCoh, is_affiliated: newAff, is_graduated: newGrd };
      if (viewMode === 'activity') {
        payload.current_title = newTitle;
        payload.current_organization = newOrg;
      }
      await apiFetch(`/phd-students/${item.id}/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      await apiFetch(`/person-roles/${item.person_role_id}/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start_date: newStart, end_date: newEnd })
      });
      await loadCohorts();
      loadStudents();
    } catch (err) { showError(err) }
  };
}

function showError(err) {
  modalText.textContent = err.message || String(err);
  modalConfirmBtn.style.display = 'none';
  modalCancelBtn.textContent = 'OK';
  modal.classList.remove('hidden');
}

function debounce(fn, delay) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), delay);
  };
}
