import { apiFetch } from './main.js';

(async () => {
  try {
    const me = await apiFetch('/users/me');
    document.getElementById('welcome-user').textContent = me.username;
  } catch (err) {
    console.error('Failed to load current user in index.js:', err);
    document.getElementById('welcome-user').textContent = 'Guest';
  }
})();
