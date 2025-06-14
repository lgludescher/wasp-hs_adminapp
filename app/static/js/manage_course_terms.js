import { apiFetch } from './main.js';

const btnAddNext          = document.getElementById('btn-add-next');
const btnRemoveMostRecent = document.getElementById('btn-remove-most-recent');
const tbody               = document.getElementById('terms-tbody');

const modal         = document.getElementById('modal-confirm');
const modalText     = document.getElementById('modal-text');
const modalConfirm  = document.getElementById('modal-confirm-btn');
const modalCancel   = document.getElementById('modal-cancel-btn');

let termsList = [];
let pendingAction = null;

/** Load and render all terms */
async function loadTerms() {
  try {
    termsList = await apiFetch('/course-terms/?');
    renderTable(termsList);
  } catch (err) {
    showError(err);
  }
}

function renderTable(list) {
  tbody.innerHTML = '';
  list.forEach(item => {
    const label = `${item.season} ${item.year}`;
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${label}</td>
      <td>${item.is_active ? 'Yes' : 'No'}</td>
      <td class="cell-actions">
        <button class="btn edit-btn">Edit</button>
      </td>
    `;
    attachRowHandlers(tr, item);
    tbody.appendChild(tr);
  });
}

function attachRowHandlers(tr, item) {
  tr.querySelector('.edit-btn').onclick = () => startEdit(tr, item);
}

function startEdit(tr, item) {
  const label = `${item.season} ${item.year}`;
  tr.innerHTML = `
    <td>${label}</td>
    <td><input type="checkbox" name="is_active" ${item.is_active ? 'checked' : ''}></td>
    <td class="cell-actions">
      <button class="btn save-btn">Save</button>
      <button class="btn cancel-btn">Cancel</button>
    </td>
  `;
  const checkbox = tr.querySelector('input[name="is_active"]');
  tr.querySelector('.cancel-btn').onclick = loadTerms;
  tr.querySelector('.save-btn').onclick = async () => {
    const updated = { is_active: checkbox.checked };
    try {
      await apiFetch(`/course-terms/${item.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated),
      });
      loadTerms();
    } catch (err) {
      showError(err);
    }
  };
}

/** Add Next Term */
btnAddNext.onclick = () => {
  pendingAction = { type: 'add' };
  showModal('Create next term?');
};

/** Remove Most Recent Term */
btnRemoveMostRecent.onclick = () => {
  if (!termsList.length) {
    showError('No terms to remove.');
    return;
  }
  // Find the term with the highest id
  const mostRecent = termsList.reduce((prev, curr) =>
    curr.id > prev.id ? curr : prev
  );
  const label = `${mostRecent.season} ${mostRecent.year}`;
  pendingAction = { type: 'remove', id: mostRecent.id, label };
  showModal(`Remove most recent term “${label}”?`);
};

/** Modal handlers */
function showModal(message) {
  modalText.textContent = message;
  modalConfirm.style.display = '';
  modalCancel.textContent = 'Cancel';
  modal.classList.add('active');
}
modalCancel.onclick = () => {
  pendingAction = null;
  modal.classList.remove('active');
};
modalConfirm.onclick = async () => {
  if (!pendingAction) return;
  try {
    if (pendingAction.type === 'add') {
      await apiFetch('/course-terms/next', { method: 'POST' });
    } else {
      await apiFetch(`/course-terms/${pendingAction.id}`, { method: 'DELETE' });
    }
    pendingAction = null;
    modal.classList.remove('active');
    loadTerms();
  } catch (err) {
    showError(err);
  }
};

/** Show backend error in modal */
function showError(err) {
  const msg = err instanceof Error ? err.message : String(err);
  modalText.textContent = msg;
  modalConfirm.style.display = 'none';
  modalCancel.textContent = 'OK';
  modal.classList.add('active');
}

// Initial load
loadTerms();
