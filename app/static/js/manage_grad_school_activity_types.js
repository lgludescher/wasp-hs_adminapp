import { apiFetch } from './main.js';

const gsatTotalCount = document.getElementById('gsat-total-count');
const btnShowCreate  = document.getElementById('btn-show-create');
const formCreate     = document.getElementById('form-create');
const btnCancel      = document.getElementById('btn-cancel');
const tbody          = document.getElementById('types-tbody');

const modal          = document.getElementById('modal-confirm');
const modalText      = document.getElementById('modal-text');
const modalConfirm   = document.getElementById('modal-confirm-btn');
const modalCancelBtn = document.getElementById('modal-cancel-btn');

let pendingRemove = null;

/** Fetch and render all types */
async function loadTypes() {
  try {
    const list = await apiFetch('/grad-school-activity-types/');
    renderTable(list);
  } catch (err) {
    showError(err);
  }
}

/** Build table rows */
function renderTable(list) {
  gsatTotalCount.textContent = `(${list.length})`;

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

/** Wire up edit & remove */
function attachHandlers(tr, item) {
  tr.querySelector('.edit-btn').onclick = () => startEdit(tr, item);
  tr.querySelector('.remove-btn').onclick = () => {
    pendingRemove = item.id;
    showModal(`Remove type “${item.type}”?`);
  };
}

/** Inline edit a row */
function startEdit(tr, item) {
  tr.innerHTML = `
    <td><input name="type" value="${item.type}" /></td>
    <td class="cell-actions">
      <button class="btn save-btn">Save</button>
      <button class="btn cancel-btn">Cancel</button>
    </td>
  `;
  const input = tr.querySelector('input[name="type"]');
  tr.querySelector('.cancel-btn').onclick = loadTypes;
  tr.querySelector('.save-btn').onclick = async () => {
    const updated = { type: input.value.trim() };
    try {
      await apiFetch(`/grad-school-activity-types/${item.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated),
      });
      loadTypes();
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
    await apiFetch('/grad-school-activity-types/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    formCreate.reset();
    formCreate.classList.add('hidden');
    btnShowCreate.disabled = false;
    loadTypes();
  } catch (err) {
    showError(err);
  }
};

/** Modal handling */
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
    await apiFetch(`/grad-school-activity-types/${pendingRemove}`, {
      method: 'DELETE',
    });
    loadTypes();
    pendingRemove = null;
    modal.classList.remove('active');
  } catch (err) {
    showError(err);
  }
};

/** Show only the error message */
function showError(err) {
  const msg = err instanceof Error ? err.message : String(err);
  modalText.textContent = msg;
  modalConfirm.style.display = 'none';
  modalCancelBtn.textContent = 'OK';
  modal.classList.add('active');
}

// Initial load
loadTypes();
