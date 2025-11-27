import { apiFetch } from './main.js';

const branchTotalCount = document.getElementById('branch-total-count');
const branchSearchInput     = document.getElementById('branch-search');
const btnShowCreateBranch   = document.getElementById('btn-show-create-branch');
const formCreateBranch      = document.getElementById('form-create-branch');
const btnCancelCreateBranch = document.getElementById('btn-cancel-create-branch');
const branchesTbody         = document.getElementById('branches-tbody');

const modal         = document.getElementById('modal-confirm');
const modalText     = document.getElementById('modal-text');
const modalConfirm  = document.getElementById('modal-confirm-btn');
const modalCancel   = document.getElementById('modal-cancel-btn');

let currentBranchFilter = '', pendingRemove = null;

function collapseAll() {
  document.querySelectorAll('tr.branch-details-row').forEach(dr => dr.classList.add('hidden'));
  document.querySelectorAll('.toggle-btn').forEach(btn => btn.textContent = '+');
}

async function loadBranches() {
  collapseAll();
  const params = new URLSearchParams();
  if (currentBranchFilter) params.set('search', currentBranchFilter);
  const branches = await apiFetch(`/branches/?${params}`);
  renderBranches(branches);
}

function renderBranches(branches) {
  branchTotalCount.textContent = `(${branches.length})`;

  branchesTbody.innerHTML = '';
  branches.forEach(branch => {
    const tr = document.createElement('tr');
    tr.dataset.branchId = branch.id;
    tr.innerHTML = `
      <td><button class="btn toggle-btn">+</button></td>
      <td class="cell-label">${branch.branch}</td>
      <td class="cell-actions">
        <button class="btn edit-branch-btn">Edit</button>
        <button class="btn remove-branch-btn">Remove</button>
      </td>
    `;
    branchesTbody.appendChild(tr);

    const dr = document.createElement('tr');
    dr.className = 'branch-details-row hidden';
    dr.dataset.branchId = branch.id;
    dr.innerHTML = `
      <td colspan="3">
        <div class="branch-details">
          <div class="subsection">
            <div class="section-subtitle">Fields</div>
            <div class="field-actions-bar">
              <input class="field-search" placeholder="Search fields…" />
              <button class="btn btn-show-create-field">Add New Field</button>
            </div>
          </div>
          <form class="field-form hidden">
            <h3>Create New Field</h3>
            <label>
              Field
              <input name="field" required />
            </label>
            <div class="form-actions">
              <button type="submit" class="btn">Create</button>
              <button type="button" class="btn btn-cancel-create-field">Cancel</button>
            </div>
          </form>
          <table class="fields-table">
            <tbody class="fields-tbody"></tbody>
          </table>
        </div>
      </td>
    `;
    branchesTbody.appendChild(dr);

    attachBranchHandlers(tr, dr, branch);
  });
}

function attachBranchHandlers(tr, dr, branch) {
  const toggleBtn = tr.querySelector('.toggle-btn');
  const editBtn   = tr.querySelector('.edit-branch-btn');
  const removeBtn = tr.querySelector('.remove-branch-btn');

  toggleBtn.addEventListener('click', () => {
    if (dr.classList.contains('hidden')) {
      collapseAll();
      dr.classList.remove('hidden');
      toggleBtn.textContent = '–';
      wireUpFields(dr, branch.id);
    } else {
      collapseAll();
    }
  });

  editBtn.addEventListener('click', () => startEditingBranch(tr, dr, branch));
  removeBtn.addEventListener('click', () => {
    pendingRemove = { type: 'branch', id: branch.id };
    showModal(`Remove branch “${branch.branch}”?`);
  });
}

async function startEditingBranch(tr, dr, branch) {
  const toggleCellHTML = tr.children[0].outerHTML;
  tr.innerHTML = `
    ${toggleCellHTML}
    <td><input name="branch" value="${branch.branch}" /></td>
    <td class="cell-actions">
      <button class="btn save-branch-btn">Save</button>
      <button class="btn cancel-branch-btn">Cancel</button>
    </td>
  `;
  tr.querySelector('.toggle-btn').addEventListener('click', () => {
    if (dr.classList.contains('hidden')) {
      collapseAll();
      dr.classList.remove('hidden');
      tr.querySelector('.toggle-btn').textContent = '–';
      wireUpFields(dr, branch.id);
    } else {
      collapseAll();
    }
  });
  tr.querySelector('.cancel-branch-btn').addEventListener('click', loadBranches);
  tr.querySelector('.save-branch-btn').addEventListener('click', async () => {
    const updated = { branch: tr.querySelector('input[name="branch"]').value.trim() };
    try {
      await apiFetch(`/branches/${branch.id}`, {
        method: 'PUT',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(updated),
      });
      loadBranches();
    } catch (err) {
      showError(err.message);
    }
  });
}

function wireUpFields(dr, branchId) {
  const searchInput     = dr.querySelector('.field-search');
  const btnShowField    = dr.querySelector('.btn-show-create-field');
  const formCreateField = dr.querySelector('.field-form');
  const btnCancelField  = dr.querySelector('.btn-cancel-create-field');
  const fieldsTbody     = dr.querySelector('.fields-tbody');

  let currentFieldFilter = '';

  async function refreshFields() {
    const params = new URLSearchParams({ branch_id: branchId });
    if (currentFieldFilter) params.set('search', currentFieldFilter);
    const fields = await apiFetch(`/fields/?${params}`);
    renderFields(fields, fieldsTbody, branchId);
  }

  searchInput.value = '';
  searchInput.oninput = () => {
    currentFieldFilter = searchInput.value.trim();
    refreshFields();
  };

  btnShowField.onclick = () => {
    formCreateField.classList.remove('hidden');
    btnShowField.disabled = true;
  };
  btnCancelField.onclick = () => {
    formCreateField.reset();
    formCreateField.classList.add('hidden');
    btnShowField.disabled = false;
  };
  formCreateField.onsubmit = async e => {
    e.preventDefault();
    const data = { field: formCreateField.field.value.trim(), branch_id: branchId };
    try {
      await apiFetch('/fields/', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(data),
      });
      formCreateField.reset();
      formCreateField.classList.add('hidden');
      btnShowField.disabled = false;
      refreshFields();
    } catch (err) {
      showError(err.message);
    }
  };

  refreshFields();
}

function renderFields(fields, tbody, branchId) {
  tbody.innerHTML = '';
  fields.forEach(field => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><span>${field.field}</span></td>
      <td class="cell-actions">
        <button class="btn edit-field-btn">Edit</button>
        <button class="btn remove-field-btn">Remove</button>
      </td>
    `;
    tbody.appendChild(tr);
    attachFieldHandlers(tr, field, branchId);
  });
}

function attachFieldHandlers(tr, field, branchId) {
  tr.querySelector('.edit-field-btn').onclick = () => {
    tr.innerHTML = `
      <td><input name="field" value="${field.field}" /></td>
      <td class="cell-actions">
        <button class="btn save-field-btn">Save</button>
        <button class="btn cancel-field-btn">Cancel</button>
      </td>
    `;
    tr.querySelector('.cancel-field-btn').onclick = () => {
      const dr = tr.closest('tr.branch-details-row');
      wireUpFields(dr, branchId);
    };
    tr.querySelector('.save-field-btn').onclick = async () => {
      const updated = { field: tr.querySelector('input[name="field"]').value.trim() };
      try {
        await apiFetch(`/fields/${field.id}`, {
          method: 'PUT',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify(updated),
        });
        const dr = tr.closest('tr.branch-details-row');
        wireUpFields(dr, branchId);
      } catch (err) {
        showError(err.message);
      }
    };
  };

  tr.querySelector('.remove-field-btn').onclick = () => {
    pendingRemove = { type: 'field', branchId, id: field.id };
    showModal(`Remove field “${field.field}”?`);
  };
}

function showModal(message) {
  modalText.textContent = message;
  modalConfirm.style.display = '';
  modalCancel.textContent = 'Cancel';
  modal.classList.add('active');
}

modalCancel.onclick = () => {
  pendingRemove = null;
  modal.classList.remove('active');
};

modalConfirm.onclick = async () => {
  if (!pendingRemove) return;
  try {
    if (pendingRemove.type === 'branch') {
      await apiFetch(`/branches/${pendingRemove.id}`, { method: 'DELETE' });
      loadBranches();
    } else {
      await apiFetch(`/fields/${pendingRemove.id}`, { method: 'DELETE' });
      const dr = document.querySelector(
        `tr.branch-details-row[data-branch-id="${pendingRemove.branchId}"]`
      );
      wireUpFields(dr, pendingRemove.branchId);
    }
    pendingRemove = null;
    modal.classList.remove('active');
  } catch (err) {
    showError(err.message);
  }
};

function showError(msg) {
  modalText.textContent = msg;
  modalConfirm.style.display = 'none';
  modalCancel.textContent = 'OK';
  modal.classList.add('active');
}

btnShowCreateBranch.onclick = () => {
  formCreateBranch.classList.remove('hidden');
  btnShowCreateBranch.disabled = true;
};
btnCancelCreateBranch.onclick = () => {
  formCreateBranch.reset();
  formCreateBranch.classList.add('hidden');
  btnShowCreateBranch.disabled = false;
};
formCreateBranch.onsubmit = async e => {
  e.preventDefault();
  const data = { branch: formCreateBranch.branch.value.trim() };
  try {
    await apiFetch('/branches/', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(data),
    });
    formCreateBranch.reset();
    formCreateBranch.classList.add('hidden');
    btnShowCreateBranch.disabled = false;
    loadBranches();
  } catch (err) {
    showError(err.message);
  }
};

branchSearchInput.oninput = () => {
  currentBranchFilter = branchSearchInput.value.trim();
  loadBranches();
};

loadBranches();
