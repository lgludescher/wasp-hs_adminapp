import { apiFetch } from './main.js';

const searchInput    = document.getElementById('calltype-search');
const btnShowCreate  = document.getElementById('btn-show-create');
const formCreate     = document.getElementById('form-create');
const btnCancel      = document.getElementById('btn-cancel');
const tbody          = document.getElementById('calltypes-tbody');

const modal          = document.getElementById('modal-confirm');
const modalText      = document.getElementById('modal-text');
const modalConfirm   = document.getElementById('modal-confirm-btn');
const modalCancelBtn = document.getElementById('modal-cancel-btn');

let pendingRemove = null;
let currentFilter = '';

/** Load and render all call types (with optional search) */
async function loadCallTypes() {
  try {
    const params = new URLSearchParams();
    if (currentFilter) params.set('search', currentFilter);
    const list = await apiFetch(`/project-call-types/?${params}`);
    renderTable(list);
  } catch (err) {
    showError(err);
  }
}

/** Render table rows */
function renderTable(list) {
  tbody.innerHTML = '';
  list.forEach(item => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${item.type}</td>
      <td class="cell-actions">
        <button class="btn edit-btn">Edit</button>
        <button class="btn remove-btn">Remove</button>
      </td>
    `;
    attachHandlers(tr, item);
    tbody.appendChild(tr);
  });
}

/** Attach edit & remove handlers */
function attachHandlers(tr, item) {
  tr.querySelector('.edit-btn').onclick = () => startEdit(tr, item);
  tr.querySelector('.remove-btn').onclick = () => {
    pendingRemove = item.id;
    showModal(`Remove call type “${item.type}”?`);
  };
}

/** Inline edit a call type */
function startEdit(tr, item) {
  tr.innerHTML = `
    <td><input name="type" value="${item.type}" /></td>
    <td class="cell-actions">
      <button class="btn save-btn">Save</button>
      <button class="btn cancel-btn">Cancel</button>
    </td>
  `;
  const input = tr.querySelector('input[name="type"]');
  tr.querySelector('.cancel-btn').onclick = loadCallTypes;
  tr.querySelector('.save-btn').onclick = async () => {
    const updated = { type: input.value.trim() };
    try {
      await apiFetch(`/project-call-types/${item.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated),
      });
      loadCallTypes();
    } catch (err) {
      showError(err);
    }
  };
}

/** Toggle create form */
btnShowCreate.onclick = () => {
  formCreate.classList.remove('hidden');
  btnShowCreate.disabled = true;
};
btnCancel.onclick = () => {
  formCreate.reset();
  formCreate.classList.add('hidden');
  btnShowCreate.disabled = false;
};

/** Submit create form */
formCreate.onsubmit = async e => {
  e.preventDefault();
  const data = { type: formCreate.type.value.trim() };
  try {
    await apiFetch('/project-call-types/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    formCreate.reset();
    formCreate.classList.add('hidden');
    btnShowCreate.disabled = false;
    loadCallTypes();
  } catch (err) {
    showError(err);
  }
};

/** Modal handling **/
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
    await apiFetch(`/project-call-types/${pendingRemove}`, { method: 'DELETE' });
    pendingRemove = null;
    modal.classList.remove('active');
    loadCallTypes();
  } catch (err) {
    showError(err);
  }
};

/** Display only the error message **/
function showError(err) {
  const msg = err instanceof Error ? err.message : String(err);
  modalText.textContent = msg;
  modalConfirm.style.display = 'none';
  modalCancelBtn.textContent = 'OK';
  modal.classList.add('active');
}

// Search filter binding
searchInput.oninput = () => {
  currentFilter = searchInput.value.trim();
  loadCallTypes();
};

// Initial load
loadCallTypes();
