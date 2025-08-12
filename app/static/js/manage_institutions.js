import { apiFetch } from './main.js';

const searchInput    = document.getElementById('institution-search');
const btnShowCreate  = document.getElementById('btn-show-create');
const btnExportExcel = document.getElementById('btn-export-excel');
const formCreate     = document.getElementById('form-create');
const btnCancel      = document.getElementById('btn-cancel');
const tbody          = document.getElementById('institutions-tbody');

const modal          = document.getElementById('modal-confirm');
const modalText      = document.getElementById('modal-text');
const modalConfirm   = document.getElementById('modal-confirm-btn');
const modalCancelBtn = document.getElementById('modal-cancel-btn');

let currentFilter = '', pendingRemove = null;

// Load & render institutions
async function loadInstitutions() {
  const params = new URLSearchParams();
  if (currentFilter) params.set('search', currentFilter);
  const list = await apiFetch(`/institutions/?${params}`);
  renderTable(list);
}

function renderTable(list) {
  tbody.innerHTML = '';
  list.forEach(item => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${item.institution}</td>
      <td class="cell-actions">
        <button class="btn edit-btn">Edit</button>
        <button class="btn remove-btn">Remove</button>
      </td>
    `;
    attachHandlers(tr, item);
    tbody.appendChild(tr);
  });
}

function attachHandlers(tr, item) {
  tr.querySelector('.edit-btn').onclick = () => startEdit(tr, item);
  tr.querySelector('.remove-btn').onclick = () => {
    pendingRemove = item.id;
    showModal(`Remove institution “${item.institution}”?`);
  };
}

function startEdit(tr, item) {
  tr.innerHTML = `
    <td><input name="institution" value="${item.institution}" /></td>
    <td class="cell-actions">
      <button class="btn save-btn">Save</button>
      <button class="btn cancel-btn">Cancel</button>
    </td>
  `;
  const input = tr.querySelector('input[name="institution"]');
  tr.querySelector('.cancel-btn').onclick = loadInstitutions;
  tr.querySelector('.save-btn').onclick = async () => {
    const updated = { institution: input.value.trim() };
    try {
      await apiFetch(`/institutions/${item.id}`, {
        method: 'PUT',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(updated)
      });
      loadInstitutions();
    } catch (err) {
      showError(err.message);
    }
  };
}

// Create‐new form
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
  const data = { institution: formCreate.institution.value.trim() };
  try {
    await apiFetch('/institutions/', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(data)
    });
    formCreate.reset();
    formCreate.classList.add('hidden');
    btnShowCreate.disabled = false;
    loadInstitutions();
  } catch (err) {
    showError(err.message);
  }
};

// Filters
searchInput.oninput = () => {
  currentFilter = searchInput.value.trim();
  loadInstitutions();
};

// Export button
btnExportExcel.onclick = () => {
  const params = new URLSearchParams();
  if (currentFilter) {
    params.set('search', currentFilter);
  }
  // Construct the URL with the current filter and trigger the download
  const exportUrl = `/institutions/export/institutions.xlsx?${params.toString()}`;
  window.location.href = exportUrl;
};

// Modal logic
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
    await apiFetch(`/institutions/${pendingRemove}`, { method: 'DELETE' });
    loadInstitutions();
    pendingRemove = null;
    modal.classList.remove('active');
  } catch (err) {
    showError(err.message);
  }
};
function showError(msg) {
  modalText.textContent = msg;
  modalConfirm.style.display = 'none';
  modalCancelBtn.textContent = 'OK';
  modal.classList.add('active');
}

// Initial load
loadInstitutions();
