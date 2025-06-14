import { apiFetch, APP_CONFIG } from './main.js';

const searchInput   = document.getElementById('user-search');
const filterSelect  = document.getElementById('filter-admin');
const btnShowCreate = document.getElementById('btn-show-create');
const formCreate    = document.getElementById('form-create-user');
const btnCancel     = document.getElementById('btn-cancel-create');
const usersTbody    = document.getElementById('users-tbody');

const modal         = document.getElementById('modal-confirm');
const modalText     = document.getElementById('modal-text');
const modalConfirm  = document.getElementById('modal-confirm-btn');
const modalCancel   = document.getElementById('modal-cancel-btn');

let currentFilters = { search: '', is_admin: '' };
let pendingRemove  = null;

// Fetch and display users
async function loadUsers() {
  const params = new URLSearchParams();
  if (currentFilters.search)          params.set('search',  currentFilters.search);
  if (currentFilters.is_admin !== '') params.set('is_admin', currentFilters.is_admin);

  const users = await apiFetch(`/users/?${params.toString()}`);
  renderTable(users);
}

// Build the table rows
function renderTable(users) {
  usersTbody.innerHTML = '';
  users.forEach(user => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${user.username}</td>
      <td>${user.name}</td>
      <td>${user.email}</td>
      <td>${user.is_admin ? '✔︎' : ''}</td>
      <td class="cell-actions">
        <button class="btn edit-btn">Edit</button>
        <button class="btn remove-btn">Remove</button>
      </td>
    `;
    attachRowHandlers(tr, user);
    usersTbody.appendChild(tr);
  });
}

// Wire up Edit and Remove buttons
function attachRowHandlers(tr, user) {
  tr.querySelector('.edit-btn')
    .addEventListener('click', () => startEditing(tr, user));

  tr.querySelector('.remove-btn')
    .addEventListener('click', () => {
      if (APP_CONFIG.currentUser?.username === user.username) {
        showInfoModal("You cannot remove your own account.");
      } else {
        showRemoveModal(user.username);
      }
    });
}

// Inline-edit a row
function startEditing(tr, user) {
  const isSelf = APP_CONFIG.currentUser?.username === user.username;
  const disabledAttr = isSelf ? 'disabled' : '';
  tr.innerHTML = `
    <td><input name="username" value="${user.username}" disabled /></td>
    <td><input name="name"     value="${user.name}"     /></td>
    <td><input name="email"    type="email" value="${user.email}" /></td>
    <td><input name="is_admin" type="checkbox" ${user.is_admin ? 'checked' : ''} ${disabledAttr} /></td>
    <td class="cell-actions">
      <button class="btn save-btn">Save</button>
      <button class="btn cancel-btn">Cancel</button>
    </td>
  `;
  tr.querySelector('.cancel-btn').addEventListener('click', () => loadUsers());
  tr.querySelector('.save-btn').addEventListener('click', async () => {
    const updated = {
      name:     tr.querySelector('input[name="name"]').value,
      email:    tr.querySelector('input[name="email"]').value,
      is_admin: tr.querySelector('input[name="is_admin"]').checked
    };
    await apiFetch(`/users/${user.username}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updated)
    });
    loadUsers();
  });
}

// Show the dangerous-remove modal
function showRemoveModal(username) {
  pendingRemove = username;
  modalConfirm.style.display = '';
  modalCancel.textContent = 'Cancel';
  modalText.textContent = `Remove user “${username}”? This action cannot be undone.`;
  modal.classList.add('active');
}

// Show an informational modal (e.g. self-delete guard)
function showInfoModal(message) {
  pendingRemove = null;
  modalConfirm.style.display = 'none';
  modalCancel.textContent = 'OK';
  modalText.textContent = message;
  modal.classList.add('active');
}

// Hide & reset modal
function hideModal() {
  pendingRemove = null;
  modal.classList.remove('active');
  modalConfirm.style.display = '';
  modalCancel.textContent = 'Cancel';
}

// Modal button handlers
modalCancel.addEventListener('click', hideModal);
modalConfirm.addEventListener('click', async () => {
  if (!pendingRemove) return;
  try {
    await apiFetch(`/users/${pendingRemove}`, { method: 'DELETE' });
  } catch (err) {
    console.error('Failed to remove user:', err);
  }
  hideModal();
  await loadUsers();
});

// Create-new form toggling & submission
btnShowCreate.addEventListener('click', () => {
  formCreate.classList.remove('hidden');
  btnShowCreate.disabled = true;
});
btnCancel.addEventListener('click', () => {
  formCreate.reset();
  formCreate.classList.add('hidden');
  btnShowCreate.disabled = false;
});
formCreate.addEventListener('submit', async e => {
  e.preventDefault();
  const data = {
    username: formCreate.username.value.trim(),
    name:     formCreate.name.value.trim(),
    email:    formCreate.email.value.trim(),
    is_admin: formCreate.is_admin.checked
  };
  await apiFetch('/users/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  formCreate.reset();
  formCreate.classList.add('hidden');
  btnShowCreate.disabled = false;
  loadUsers();
});

// Filters
searchInput.addEventListener('input', () => {
  currentFilters.search = searchInput.value.trim();
  loadUsers();
});
filterSelect.addEventListener('change', () => {
  currentFilters.is_admin = filterSelect.value;
  loadUsers();
});

// Initial fetch
loadUsers();
