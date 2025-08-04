import { apiFetch } from './main.js';

const POSTDOCS_ENDPOINT     = '/postdocs/';
const INSTITUTIONS_ENDPOINT = '/institutions/';
const BRANCHES_ENDPOINT     = '/branches/';
const FIELDS_ENDPOINT       = '/fields/';
const TITLE_ENDPOINT        = '/researcher-titles/';

// Controls
const filterSearch      = document.getElementById('filter-search');
const filterActive      = document.getElementById('filter-active');
const filterCohort      = document.getElementById('filter-cohort');
const filterMobility    = document.getElementById('filter-mobility-status');
const filterInstitution = document.getElementById('filter-institution');
const filterBranch      = document.getElementById('filter-branch');
const filterField       = document.getElementById('filter-field');
const btnDefault        = document.getElementById('btn-default');
const btnActivity       = document.getElementById('btn-activity');
const theadRow          = document.getElementById('postdocs-thead');
const tbody             = document.getElementById('postdocs-tbody');

const modal             = document.getElementById('modal-confirm');
const modalText         = document.getElementById('modal-text');
const modalConfirmBtn   = document.getElementById('modal-confirm-btn');
const modalCancelBtn    = document.getElementById('modal-cancel-btn');

let viewMode = 'default';
let titlesList = [];
let institutionsList = [];

;(async function init() {
  filterActive.value = 'true';

  // preload title & institution lists
  [titlesList, institutionsList] = await Promise.all([
    apiFetch(TITLE_ENDPOINT),
    apiFetch(INSTITUTIONS_ENDPOINT)
  ]);

  await loadCohorts();
  await loadBranches();
  await loadFields();

  setupViewToggle();
  setupFilters();

  modalCancelBtn.onclick = () => modal.classList.add('hidden');

  renderHeader();
  loadPostdocs();
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
  loadPostdocs();
}

async function loadCohorts() {
  const list = await apiFetch(POSTDOCS_ENDPOINT);
  const distinct = Array.from(new Set(list.map(p => p.cohort_number).filter(n => n != null))).sort((a, b) => a - b);
  filterCohort.innerHTML = '<option value="">All cohorts</option>';
  distinct.forEach(n => filterCohort.append(new Option(n, n)));
}

async function loadBranches() {
  const list = await apiFetch(BRANCHES_ENDPOINT);
  filterBranch.innerHTML = '<option value="">All branches</option>';
  list.forEach(b => filterBranch.append(new Option(b.branch, b.id)));
}

async function loadFields(branchId = '') {
  const url = branchId ? `${FIELDS_ENDPOINT}?branch_id=${branchId}` : FIELDS_ENDPOINT;
  const list = await apiFetch(url);
  filterField.innerHTML = '<option value="">All fields</option>';
  list.forEach(f => filterField.append(new Option(f.field, f.id)));
}

function setupFilters() {
  filterSearch.oninput = debounce(loadPostdocs, 300);
  filterActive.onchange = loadPostdocs;
  filterCohort.onchange = loadPostdocs;
  filterMobility.onchange = loadPostdocs;
  filterInstitution.onchange = loadPostdocs;
  filterBranch.onchange = async () => { await loadFields(filterBranch.value); loadPostdocs(); };
  filterField.onchange = loadPostdocs;
}

async function loadPostdocs() {
  const p = new URLSearchParams();
  if (filterSearch.value.trim()) p.set('search', filterSearch.value.trim());
  if (filterActive.value) p.set('is_active', filterActive.value);
  if (filterCohort.value) p.set('cohort_number', filterCohort.value);
  if (filterMobility.value) p.set('is_outgoing', filterMobility.value);
  if (filterInstitution.value) p.set('institution_id', filterInstitution.value);
  if (filterBranch.value) p.set('branch_id', filterBranch.value);
  if (filterField.value) p.set('field_id', filterField.value);

  const list = await apiFetch(`${POSTDOCS_ENDPOINT}?${p}`);
  renderTable(list);
}

function renderHeader() {
  if (viewMode === 'default') {
    theadRow.innerHTML = `
      <th></th><th>Name</th><th>Email</th><th>Cohort</th>
      <th>Mobility Status</th><th>Start Date</th><th>End Date</th>
      <th class="cell-actions"></th>`;
  } else {
    theadRow.innerHTML = `
      <th></th><th>Name</th><th>Cohort</th>
      <th>Current Title</th><th>Current Institution</th>
      <th class="cell-actions"></th>`;
  }
}

function renderTable(list) {
  tbody.innerHTML = '';
  list.forEach(item => {
    const pr = item.person_role;
    const name = `${pr.person.first_name} ${pr.person.last_name}`;
    const cohort = item.cohort_number ?? '';
    const mobility = item.is_outgoing ? 'Outgoing' : 'Incoming';
    const start = pr.start_date?.split('T')[0] || '';
    const end = pr.end_date?.split('T')[0] || '';
    let cols;
    if (viewMode === 'default') {
      cols = `
        <td>${name}</td><td>${pr.person.email}</td><td>${cohort}</td>
        <td>${mobility}</td><td>${start}</td><td>${end}</td>`;
    } else {
      const titleText = item.current_title_id
        ? item.current_title?.title
        : (item.current_title_other || '');
      const instText = item.current_institution_id
        ? item.current_institution?.institution
        : (item.current_institution_other || '');
      cols = `
        <td>${name}</td><td>${cohort}</td>
        <td>${titleText}</td><td>${instText}</td>`;
    }
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><a class="go-btn" href="/manage-postdocs/${item.id}/">Go to postdoc</a></td>
      ${cols}
      <td class="cell-actions"><button class="btn edit-btn">Edit</button></td>`;
    attachHandlers(tr, item);
    tbody.append(tr);
  });
}

function attachHandlers(tr, item) {
  tr.querySelector('.edit-btn').onclick = () => startEdit(tr, item);
}

function startEdit(tr, item) {
  const pr = item.person_role;
  const name = `${pr.person.first_name} ${pr.person.last_name}`;
  const start = pr.start_date?.split('T')[0] || '';
  const end = pr.end_date?.split('T')[0] || '';

  const existingTitleId = item.current_title_id;
  const existingTitleOther = item.current_title_other || '';
  const existingInstId = item.current_institution_id;
  const existingInstOther = item.current_institution_other || '';

  let editCols = '';
  if (viewMode === 'default') {
    editCols = `
      <td>${name}</td>
      <td>${pr.person.email}</td>
      <td><input name="cohort_number" type="number" min="0" max="99" value="${item.cohort_number ?? ''}" /></td>
      <td>
        <select name="is_outgoing">
          <option value="false">Incoming</option>
          <option value="true">Outgoing</option>
        </select>
      </td>
      <td><input name="start_date" type="date" value="${start}" /></td>
      <td><input name="end_date" type="date" value="${end}" /></td>
    `;
  } else {
    editCols = `
      <td>${name}</td>
      <td><input name="cohort_number" type="number" min="0" max="99" value="${item.cohort_number ?? ''}" /></td>
      <td>
        <select name="current_title_id" id="sel-title">
          <option value="">--</option>
          ${titlesList.map(t => `<option value="${t.id}">${t.title}</option>`).join('')}
          <option value="other">Other</option>
        </select>
        <input name="current_title_other" id="inp-title-other" type="text" placeholder="Specify title" style="display:none;" value="${existingTitleOther}" />
      </td>
      <td>
        <select name="current_institution_id" id="sel-inst">
          <option value="">--</option>
          ${institutionsList.map(i => `<option value="${i.id}">${i.institution}</option>`).join('')}
          <option value="other">Other</option>
        </select>
        <input name="current_institution_other" id="inp-inst-other" type="text" placeholder="Specify institution" style="display:none;" value="${existingInstOther}" />
      </td>
    `;
  }

  tr.innerHTML = `
    <td><a class="go-btn" href="/manage-postdocs/${item.id}/">Go to postdoc</a></td>
    ${editCols}
    <td class="cell-actions">
      <button class="btn save-btn">Save</button>
      <button class="btn cancel-btn">Cancel</button>
    </td>
  `;

  if (viewMode === 'default') {
    tr.querySelector('select[name="is_outgoing"]').value = String(item.is_outgoing);
  } else {
    const selT = tr.querySelector('#sel-title');
    const inpT = tr.querySelector('#inp-title-other');
    if (existingTitleId) {
      selT.value = String(existingTitleId);
    } else if (existingTitleOther) {
      selT.value = 'other';
      inpT.style.display = 'inline-block';
    }
    selT.onchange = () => { inpT.style.display = selT.value === 'other' ? 'inline-block' : 'none'; };

    const selI = tr.querySelector('#sel-inst');
    const inpI = tr.querySelector('#inp-inst-other');
    if (existingInstId) {
      selI.value = String(existingInstId);
    } else if (existingInstOther) {
      selI.value = 'other';
      inpI.style.display = 'inline-block';
    }
    selI.onchange = () => { inpI.style.display = selI.value === 'other' ? 'inline-block' : 'none'; };
  }

  const cohortInput = tr.querySelector('[name="cohort_number"]');
  cohortInput.oninput = () => { if (cohortInput.value.length > 2) cohortInput.value = cohortInput.value.slice(0,2); };

  tr.querySelector('.cancel-btn').onclick = loadPostdocs;
  tr.querySelector('.save-btn').onclick = async () => {
    const newCoh = parseInt(cohortInput.value) || null;
    const payload = { cohort_number: newCoh };
    if (viewMode === 'default') {
      payload.is_outgoing = tr.querySelector('[name="is_outgoing"]').value === 'true';
    } else {
      const selT = tr.querySelector('#sel-title');
      const inpT = tr.querySelector('#inp-title-other');
      if (selT.value === 'other') { payload.current_title_id = null; payload.current_title_other = inpT.value || null; }
      else { payload.current_title_id = selT.value || null; payload.current_title_other = null; }
      const selI = tr.querySelector('#sel-inst');
      const inpI = tr.querySelector('#inp-inst-other');
      if (selI.value === 'other') { payload.current_institution_id = null; payload.current_institution_other = inpI.value || null; }
      else { payload.current_institution_id = selI.value || null; payload.current_institution_other = null; }
    }
    try {
      await apiFetch(`/postdocs/${item.id}/`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      await apiFetch(`/person-roles/${item.person_role_id}/`,{ method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ start_date: start, end_date: end }) });
      await loadCohorts(); loadPostdocs();
    } catch (err) { showError(err); }
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
