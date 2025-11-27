import { apiFetch } from './main.js';

const researcherTitleTotalCount = document.getElementById('researcher-title-total-count');
const searchInput    = document.getElementById('title-search');
const btnShowCreate  = document.getElementById('btn-show-create');
const formCreate     = document.getElementById('form-create');
const btnCancel      = document.getElementById('btn-cancel');
const tbody          = document.getElementById('titles-tbody');

const modal          = document.getElementById('modal-confirm');
const modalText      = document.getElementById('modal-text');
const modalConfirm   = document.getElementById('modal-confirm-btn');
const modalCancelBtn = document.getElementById('modal-cancel-btn');

let pendingRemove = null;
let currentFilter = '';

/** Load & render titles */
async function loadTitles() {
  try {
    const params = new URLSearchParams();
    if (currentFilter) params.set('search', currentFilter);
    const list = await apiFetch(`/researcher-titles/?${params}`);
    renderTable(list);
  } catch (err) {
    showError(err);
  }
}

function renderTable(list) {
  researcherTitleTotalCount.textContent = `(${list.length})`;

  tbody.innerHTML = '';
  list.forEach(item => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${item.title}</td>
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
    showModal(`Remove title “${item.title}”?`);
  };
}

function startEdit(tr, item) {
  tr.innerHTML = `
    <td><input name="title" value="${item.title}" /></td>
    <td class="cell-actions">
      <button class="btn save-btn">Save</button>
      <button class="btn cancel-btn">Cancel</button>
    </td>
  `;
  const input = tr.querySelector('input[name="title"]');
  tr.querySelector('.cancel-btn').onclick = loadTitles;
  tr.querySelector('.save-btn').onclick = async () => {
    const updated = { title: input.value.trim() };
    try {
      await apiFetch(`/researcher-titles/${item.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated),
      });
      loadTitles();
    } catch (err) {
      showError(err);
    }
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
  const data = { title: formCreate.title.value.trim() };
  try {
    await apiFetch('/researcher-titles/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    formCreate.reset();
    formCreate.classList.add('hidden');
    btnShowCreate.disabled = false;
    loadTitles();
  } catch (err) {
    showError(err);
  }
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
    await apiFetch(`/researcher-titles/${pendingRemove}`, { method: 'DELETE' });
    pendingRemove = null;
    modal.classList.remove('active');
    loadTitles();
  } catch (err) {
    showError(err);
  }
};

function showError(err) {
  const msg = err instanceof Error ? err.message : String(err);
  modalText.textContent = msg;
  modalConfirm.style.display = 'none';
  modalCancelBtn.textContent = 'OK';
  modal.classList.add('active');
}

searchInput.oninput = () => {
  currentFilter = searchInput.value.trim();
  loadTitles();
};

loadTitles();
