import { apiFetch, openEmailListModal } from './main.js';

const ROLE_TITLE_ENDPOINT    = '/researcher-titles/';
const INSTITUTIONS_ENDPOINT  = '/institutions/';
const BRANCHES_ENDPOINT      = '/branches/';
const FIELDS_ENDPOINT        = '/fields/';

const filterSearch       = document.getElementById('filter-search');
const filterActive       = document.getElementById('filter-active');
const filterTitle        = document.getElementById('filter-title');
const filterInstitution  = document.getElementById('filter-institution');
const filterBranch       = document.getElementById('filter-branch');
const filterField        = document.getElementById('filter-field');
const btnExportExcel     = document.getElementById('btn-export-excel');
const btnExportEmails    = document.getElementById('btn-export-emails');
const tbody              = document.getElementById('researchers-tbody');

const modal              = document.getElementById('modal-confirm');
const modalText          = document.getElementById('modal-text');
const modalConfirmBtn    = document.getElementById('modal-confirm-btn');
const modalCancelBtn     = document.getElementById('modal-cancel-btn');

/** Initial load */
;(async function init() {
  await loadTitles();
  await loadInstitutions();
  await loadBranches();
  await loadFields();         // initial: all fields
  setupFilters();
  modalCancelBtn.onclick = () => modal.classList.add('hidden');
  loadResearchers();
})();

/** Populate title filter */
async function loadTitles() {
  try {
    const list = await apiFetch(ROLE_TITLE_ENDPOINT);
    list.forEach(t => filterTitle.append(new Option(t.title, t.id)));
  } catch (err) { showError(err) }
}

/** Populate institution filter */
async function loadInstitutions() {
  try {
    const list = await apiFetch(INSTITUTIONS_ENDPOINT);
    list.forEach(i => filterInstitution.append(new Option(i.institution, i.id)));
  } catch (err) { showError(err) }
}

/** Populate branches */
async function loadBranches() {
  try {
    const list = await apiFetch(BRANCHES_ENDPOINT);
    list.forEach(b => filterBranch.append(new Option(b.branch, b.id)));
  } catch (err) { showError(err) }
}

/** Populate fields, optionally by branch */
async function loadFields(branchId = '') {
  try {
    const url = branchId
      ? `${FIELDS_ENDPOINT}?branch_id=${branchId}`
      : FIELDS_ENDPOINT;
    const list = await apiFetch(url);
    filterField.innerHTML = '<option value="">All fields</option>';
    list.forEach(f => filterField.append(new Option(f.field, f.id)));
  } catch (err) { showError(err) }
}

/** Wire up filters to reload */
function setupFilters() {
  filterSearch.oninput      = debounce(loadResearchers, 300);
  filterActive.onchange     = loadResearchers;
  filterTitle.onchange      = loadResearchers;
  filterInstitution.onchange= loadResearchers;
  filterBranch.onchange     = async () => {
    await loadFields(filterBranch.value);
    loadResearchers();
  };
  filterField.onchange      = loadResearchers;
}

/** Fetch & render list */
async function loadResearchers() {
  try {
    const p = new URLSearchParams();
    if (filterSearch.value.trim())    p.set('search', filterSearch.value.trim());
    if (filterActive.value)           p.set('is_active', filterActive.value);
    if (filterTitle.value)            p.set('title_id', filterTitle.value);
    if (filterInstitution.value)      p.set('institution_id', filterInstitution.value);
    if (filterBranch.value)           p.set('branch_id', filterBranch.value);
    if (filterField.value)            p.set('field_id', filterField.value);

    const list = await apiFetch('/researchers/?' + p);
    renderTable(list);
  } catch (err) { showError(err) }
}

/** Build table rows */
function renderTable(list) {
  tbody.innerHTML = '';
  list.forEach(item => {
    const pr = item.person_role;
    const name = pr.person.first_name + ' ' + pr.person.last_name;
    const email = pr.person.email;
    const start = pr.start_date?.split('T')[0] || '';
    const end   = pr.end_date?.split('T')[0]   || '';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <a class="go-btn" href="/manage-researchers/${item.id}/">Go to researcher</a>
      </td>
      <td>${item.title?.title ?? ''}</td>
      <td>${name}</td>
      <td>${email}</td>
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

/** Attach inline-edit handler */
function attachHandlers(tr, item) {
  tr.querySelector('.edit-btn').onclick = () => startEdit(tr, item);
}

/** Inline‐edit a researcher */
function startEdit(tr, item) {
  const pr      = item.person_role;
  const name    = pr.person.first_name + ' ' + pr.person.last_name;
  const email   = pr.person.email;
  const start   = pr.start_date?.split('T')[0] || '';
  const end     = pr.end_date?.split('T')[0]   || '';

  tr.innerHTML = `
    <td>
      <a class="go-btn" href="/manage-researchers/${item.id}/">Go to researcher</a>
    </td>
    <td><select name="title_id"></select></td>
    <td>${name}</td>
    <td>${email}</td>
    <td><input name="start_date" type="date" value="${start}" /></td>
    <td><input name="end_date"   type="date" value="${end}"   /></td>
    <td class="cell-actions">
      <button class="btn save-btn">Save</button>
      <button class="btn cancel-btn">Cancel</button>
    </td>
  `;

  // populate title dropdown
  const sel = tr.querySelector('select[name="title_id"]');
  document.querySelectorAll('#filter-title option')
    .forEach(o => sel.append(o.cloneNode(true)));
  sel.value = item.title_id;

  tr.querySelector('.cancel-btn').onclick = loadResearchers;
  tr.querySelector('.save-btn').onclick = async () => {
    const newTitleId = parseInt(sel.value);
    const newStart   = tr.querySelector('[name="start_date"]').value || null;
    const newEnd     = tr.querySelector('[name="end_date"]').value   || null;

    try {
      // 1) update researcher record
      await apiFetch(`/researchers/${item.id}/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title_id: newTitleId })
      });
      // 2) update underlying person-role for dates
      await apiFetch(`/person-roles/${item.person_role_id}/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start_date: newStart, end_date: newEnd })
      });
      loadResearchers();
    } catch (err) {
      showError(err);
    }
  };
}

btnExportExcel.onclick = () => {
  const p = new URLSearchParams();
  if (filterSearch.value.trim())    p.set('search', filterSearch.value.trim());
  if (filterActive.value)           p.set('is_active', filterActive.value);
  if (filterTitle.value)            p.set('title_id', filterTitle.value);
  if (filterInstitution.value)      p.set('institution_id', filterInstitution.value);
  if (filterBranch.value)           p.set('branch_id', filterBranch.value);
  if (filterField.value)            p.set('field_id', filterField.value);

  const exportUrl = `/researchers/export/researchers.xlsx?${p.toString()}`;
  window.location.href = exportUrl;
};

btnExportEmails.onclick = async () => {
    try {
        const p = new URLSearchParams();
        // Mimic the filters used in loadResearchers/ExportExcel
        if (filterSearch.value.trim()) p.set('search', filterSearch.value.trim());
        if (filterActive.value)        p.set('is_active', filterActive.value);
        if (filterTitle.value)         p.set('title_id', filterTitle.value);
        if (filterInstitution.value)   p.set('institution_id', filterInstitution.value);
        if (filterBranch.value)        p.set('branch_id', filterBranch.value);
        if (filterField.value)         p.set('field_id', filterField.value);

        // Fetch data
        const data = await apiFetch(`/researchers/export/emails?${p.toString()}`);

        // Open Modal
        openEmailListModal(data);
    } catch (err) {
        showError(err);
    }
};

/** Display error modal */
function showError(err) {
  modalText.textContent = err.message || String(err);
  modalConfirmBtn.style.display = 'none';
  modalCancelBtn.textContent = 'OK';
  modal.classList.remove('hidden');
}

/** Simple debounce */
function debounce(fn, delay) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), delay);
  };
}
