import { apiFetch } from './main.js';

const gsaTotalCount = document.getElementById('gsa-total-count');
const filterTypeSelect  = document.getElementById('filter-activity-type');
const filterYearInput   = document.getElementById('filter-year');
const btnShowCreate     = document.getElementById('btn-show-create');
const btnExportExcel    = document.getElementById('btn-export-excel');
const formCreate        = document.getElementById('form-create');
const btnCancel         = document.getElementById('btn-cancel');
const tbody             = document.getElementById('activities-tbody');

const modal             = document.getElementById('modal-confirm');
const modalText         = document.getElementById('modal-text');
const modalConfirm      = document.getElementById('modal-confirm-btn');
const modalCancelBtn    = document.getElementById('modal-cancel-btn');

let ACTIVITY_TYPES = [];
let pendingRemove  = null;
let typeFilter     = '';
let yearFilter     = '';

;(async function init() {
  try {
    ACTIVITY_TYPES = await apiFetch('/grad-school-activity-types/');
    populateTypeSelects();
    loadActivities();
  } catch (err) {
    showError(err);
  }
})();

function populateTypeSelects() {
  const formTypeSelect = formCreate.querySelector('select[name="activity_type_id"]');
  filterTypeSelect.innerHTML = '<option value="">All Types</option>';
  formTypeSelect.innerHTML    = '<option value="">Select type</option>';

  ACTIVITY_TYPES.forEach(t => {
    const opt1 = document.createElement('option');
    opt1.value = t.id; opt1.textContent = t.type;
    filterTypeSelect.appendChild(opt1);
    const opt2 = opt1.cloneNode(true);
    formTypeSelect.appendChild(opt2);
  });
}

async function loadActivities() {
  try {
    const params = new URLSearchParams();
    if (typeFilter) params.set('activity_type_id', typeFilter);
    if (yearFilter)  params.set('year', yearFilter);
    const list = await apiFetch(`/grad-school-activities/?${params}`);
    renderTable(list);
  } catch (err) { showError(err); }
}

function renderTable(list) {
  gsaTotalCount.textContent = `(${list.length})`;

  tbody.innerHTML = '';
  list.forEach(item => {
    const goLink = `<a class="btn go-btn" href="/manage-grad-school-activities/${item.id}/">Go to activity</a>`;
    const year   = item.year ?? '';
    const desc   = item.description ?? '';
    const tr     = document.createElement('tr');
    tr.innerHTML = `
      <td class="cell-go">${goLink}</td>
      <td>${item.activity_type.type}</td>
      <td>${year}</td>
      <td>${desc}</td>
      <td class="cell-actions">
        <button class="btn edit-btn">Edit</button>
        <button class="btn remove-btn">Remove</button>
      </td>
    `;
    attachRowHandlers(tr, item);
    tbody.appendChild(tr);
  });
}

function attachRowHandlers(tr, item) {
  tr.querySelector('.edit-btn').onclick = () => startEdit(tr, item);
  tr.querySelector('.remove-btn').onclick = () => {
    pendingRemove = item.id;
    showModal(`Remove activity “${item.activity_type.type} ${item.year}”?`);
  };
}

function startEdit(tr, item) {
  const goLink = `<a class="btn go-btn" href="/manage-grad-school-activities/${item.id}/">Go to activity</a>`;
  const year   = item.year ?? '';
  const desc   = item.description ?? '';

  const selectHtml = `
    <select name="activity_type_id" required>
      <option value="">Select type</option>
      ${ACTIVITY_TYPES.map(t =>
        `<option value="${t.id}"${t.id===item.activity_type.id?' selected':''}>${t.type}</option>`
      ).join('')}
    </select>`;

  tr.innerHTML = `
    <td class="cell-go">${goLink}</td>
    <td>${selectHtml}</td>
    <td><input name="year" type="number" value="${year}" required min="2020" max="2100"></td>
    <td><input name="description" value="${desc}"></td>
    <td class="cell-actions">
      <button class="btn save-btn">Save</button>
      <button class="btn cancel-btn">Cancel</button>
    </td>
  `;
  const typeSelect = tr.querySelector('select[name="activity_type_id"]');
  const yearInput  = tr.querySelector('input[name="year"]');
  const descInput  = tr.querySelector('input[name="description"]');

  tr.querySelector('.cancel-btn').onclick = loadActivities;
  tr.querySelector('.save-btn').onclick = async () => {
    const payload = {
      activity_type_id: parseInt(typeSelect.value,10)||null,
      year:              parseInt(yearInput.value,10)||null,
      description:       descInput.value.trim()||null,
    };
    try {
      await apiFetch(`/grad-school-activities/${item.id}`, {
        method: 'PUT',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payload),
      });
      loadActivities();
    } catch (err) { showError(err); }
  };
}

btnShowCreate.onclick = () => {
  formCreate.classList.remove('hidden');
  btnShowCreate.disabled = true;
};
btnCancel.onclick = () => {
  formCreate.reset();
  formCreate.classList.add('hidden');
  btnShowCreate.disabled = false;
};

formCreate.onsubmit = async e => {
  e.preventDefault();
  const formType = formCreate.querySelector('select[name="activity_type_id"]').value;
  const payload  = {
    activity_type_id: parseInt(formType,10)||null,
    year:              parseInt(formCreate.year.value,10)||null,
    description:       formCreate.description.value.trim()||null,
  };
  try {
    await apiFetch('/grad-school-activities/', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload),
    });
    formCreate.reset();
    formCreate.classList.add('hidden');
    btnShowCreate.disabled = false;
    loadActivities();
  } catch (err) { showError(err); }
};

btnExportExcel.onclick = () => {
  const params = new URLSearchParams();
  if (typeFilter) params.set('activity_type_id', typeFilter);
  if (yearFilter) params.set('year', yearFilter);

  const exportUrl = `/grad-school-activities/export/grad-school-activities.xlsx?${params.toString()}`;
  window.location.href = exportUrl;
};

filterTypeSelect.onchange = () => {
  typeFilter = filterTypeSelect.value;
  loadActivities();
};
filterYearInput.oninput = () => {
  yearFilter = filterYearInput.value.trim();
  loadActivities();
};

function showModal(message) {
  modalText.textContent = message;
  modalConfirm.style.display = '';
  modalCancelBtn.textContent = 'Cancel';
  modal.classList.add('active');
}
modalCancelBtn.onclick = () => {
  pendingRemove = null;
  modal.classList.remove('active');
};
modalConfirm.onclick = async () => {
  if (!pendingRemove) return;
  try {
    await apiFetch(`/grad-school-activities/${pendingRemove}`,{method:'DELETE'});
    pendingRemove = null;
    modal.classList.remove('active');
    loadActivities();
  } catch (err) { showError(err); }
};

function showError(err) {
  const msg = err instanceof Error ? err.message : String(err);
  modalText.textContent = msg;
  modalConfirm.style.display = 'none';
  modalCancelBtn.textContent = 'OK';
  modal.classList.add('active');
}
