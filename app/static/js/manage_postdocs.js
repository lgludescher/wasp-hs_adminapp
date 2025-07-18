import { apiFetch } from './main.js';

const POSTDOCS_ENDPOINT     = '/postdocs/';
const INSTITUTIONS_ENDPOINT = '/institutions/';
const BRANCHES_ENDPOINT     = '/branches/';
const FIELDS_ENDPOINT       = '/fields/';

const filterSearch       = document.getElementById('filter-search');
const filterActive       = document.getElementById('filter-active');
const filterCohort       = document.getElementById('filter-cohort');
const filterInstitution  = document.getElementById('filter-institution');
const filterBranch       = document.getElementById('filter-branch');
const filterField        = document.getElementById('filter-field');
const tbody              = document.getElementById('postdocs-tbody');

const modal              = document.getElementById('modal-confirm');
const modalText          = document.getElementById('modal-text');
const modalConfirmBtn    = document.getElementById('modal-confirm-btn');
const modalCancelBtn     = document.getElementById('modal-cancel-btn');

;(async function init() {
  await loadCohorts();
  await loadInstitutions();
  await loadBranches();
  await loadFields();
  setupFilters();
  modalCancelBtn.onclick = () => modal.classList.add('hidden');
  loadPostdocs();
})();

async function loadCohorts() {
  try {
    const list = await apiFetch(POSTDOCS_ENDPOINT);
    const distinct = Array.from(new Set(
      list.map(p => p.cohort_number).filter(n => n != null)
    )).sort((a, b) => a - b);
    filterCohort.innerHTML = '<option value="">All cohorts</option>';
    distinct.forEach(n => filterCohort.append(new Option(n, n)));
  } catch (err) {
    showError(err);
  }
}

async function loadInstitutions() {
  try {
    const list = await apiFetch(INSTITUTIONS_ENDPOINT);
    filterInstitution.innerHTML = '<option value="">All institutions</option>';
    list.forEach(i => filterInstitution.append(new Option(i.institution, i.id)));
  } catch (err) {
    showError(err);
  }
}

async function loadBranches() {
  try {
    const list = await apiFetch(BRANCHES_ENDPOINT);
    filterBranch.innerHTML = '<option value="">All branches</option>';
    list.forEach(b => filterBranch.append(new Option(b.branch, b.id)));
  } catch (err) {
    showError(err);
  }
}

async function loadFields(branchId = '') {
  try {
    const url = branchId
      ? `${FIELDS_ENDPOINT}?branch_id=${branchId}`
      : FIELDS_ENDPOINT;
    const list = await apiFetch(url);
    filterField.innerHTML = '<option value="">All fields</option>';
    list.forEach(f => filterField.append(new Option(f.field, f.id)));
  } catch (err) {
    showError(err);
  }
}

function setupFilters() {
  filterSearch.oninput       = debounce(loadPostdocs, 300);
  filterActive.onchange       = loadPostdocs;
  filterCohort.onchange       = loadPostdocs;
  filterInstitution.onchange  = loadPostdocs;
  filterBranch.onchange       = async () => {
    await loadFields(filterBranch.value);
    loadPostdocs();
  };
  filterField.onchange        = loadPostdocs;
}

async function loadPostdocs() {
  try {
    const p = new URLSearchParams();
    if (filterSearch.value.trim())    p.set('search', filterSearch.value.trim());
    if (filterActive.value)           p.set('is_active', filterActive.value);
    if (filterCohort.value)           p.set('cohort_number', filterCohort.value);
    if (filterInstitution.value)      p.set('institution_id', filterInstitution.value);
    if (filterBranch.value)           p.set('branch_id', filterBranch.value);
    if (filterField.value)            p.set('field_id', filterField.value);

    const list = await apiFetch(POSTDOCS_ENDPOINT + '?' + p);
    renderTable(list);
  } catch (err) {
    showError(err);
  }
}

function renderTable(list) {
  tbody.innerHTML = '';
  list.forEach(item => {
    const pr     = item.person_role;
    const name   = pr.person.first_name + ' ' + pr.person.last_name;
    const email  = pr.person.email;
    const cohort = item.cohort_number ?? '';
    const start  = pr.start_date?.split('T')[0] || '';
    const end    = pr.end_date?.split('T')[0]   || '';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <a class="go-btn" href="/manage-postdocs/${item.id}/">
          Go to postdoc
        </a>
      </td>
      <td>${name}</td>
      <td>${email}</td>
      <td>${cohort}</td>
      <td>${start}</td>
      <td>${end}</td>
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
  const pr     = item.person_role;
  const name   = pr.person.first_name + ' ' + pr.person.last_name;
  const email  = pr.person.email;
  const start  = pr.start_date?.split('T')[0] || '';
  const end    = pr.end_date?.split('T')[0]   || '';

  tr.innerHTML = `
    <td>
      <a class="go-btn" href="/manage-postdocs/${item.id}/">
        Go to postdoc
      </a>
    </td>
    <td>${name}</td>
    <td>${email}</td>
    <td>
      <input
        name="cohort_number"
        type="number" min="0" max="99"
        value="${item.cohort_number ?? ''}"
      />
    </td>
    <td><input name="start_date" type="date" value="${start}" /></td>
    <td><input name="end_date"   type="date" value="${end}"   /></td>
    <td class="cell-actions">
      <button class="btn save-btn">Save</button>
      <button class="btn cancel-btn">Cancel</button>
    </td>
  `;

  const cohortInput = tr.querySelector('[name="cohort_number"]');
  cohortInput.oninput = () => {
    if (cohortInput.value.length > 2) {
      cohortInput.value = cohortInput.value.slice(0,2);
    }
  };

  tr.querySelector('.cancel-btn').onclick = loadPostdocs;
  tr.querySelector('.save-btn').onclick   = async () => {
    const newCoh   = cohortInput.value ? parseInt(cohortInput.value) : null;
    const newStart = tr.querySelector('[name="start_date"]').value || null;
    const newEnd   = tr.querySelector('[name="end_date"]').value   || null;

    try {
      // 1) update postdoc’s cohort
      await apiFetch(`/postdocs/${item.id}/`, {
        method: 'PUT',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ cohort_number: newCoh })
      });
      // 2) update the person-role dates
      await apiFetch(`/person-roles/${item.person_role_id}/`, {
        method: 'PUT',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ start_date: newStart, end_date: newEnd })
      });
      // 3) refresh cohort filter & table
      await loadCohorts();
      loadPostdocs();
    } catch (err) {
      showError(err);
    }
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
