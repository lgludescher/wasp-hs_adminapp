export let APP_CONFIG = {
  debug: false,
  currentUser: null,
};

//
// Immediately fetch runtime config and current user
//
(async () => {
  // 1. Get debug flag
  APP_CONFIG = await fetch('/config').then(res => res.json());

  // 2. Load the current user record
  try {
    const me = await apiFetch('/users/me');
    APP_CONFIG.currentUser = me;

    // Update the user badge
    const badge = document.getElementById('user-badge');
    badge.textContent = me.username + (APP_CONFIG.debug ? ' (dev)' : '');

    // 3. Gate the admin-only menu item
    if (!me.is_admin) {
      document.querySelectorAll('.menu-item.admin-only')
              .forEach(el => el.style.display = 'none');
    }
  } catch (err) {
    console.error('Error loading current user:', err);
  }
})();

/**
 * Universal fetch wrapper.
 *
 * - Attaches X-Dev-User in debug mode
 * - Throws on 401/403 for upstream handlers
 * - Returns parsed JSON
 */
export async function apiFetch(path, opts = {}) {
  const headers = new Headers(opts.headers || {});

  if (APP_CONFIG.debug) {
    // prompt once per session for dev user
    const u = localStorage.getItem('devUser') || prompt('X-Dev-User:', 'alice');
    if (u) {
      headers.set('X-Dev-User', u);
      localStorage.setItem('devUser', u);
    }
  }

  const response = await fetch(path, { ...opts, headers });
  if (response.status === 401) throw new Error('401 Unauthorized');
  if (response.status === 403) throw new Error('403 Forbidden');
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}
