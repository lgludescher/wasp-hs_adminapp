export let APP_CONFIG = {
  debug: false,
  currentUser: null,
};

(async () => {
  APP_CONFIG = await fetch('/config').then(r => r.json());
  try {
    const me = await apiFetch('/users/me');
    APP_CONFIG.currentUser = me;
    const badge = document.getElementById('user-badge');
    badge.textContent = me.username + (APP_CONFIG.debug ? ' (dev)' : '');
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
 * - Attaches X-Dev-User in debug mode
 * - Throws on 401/403
 * - Returns parsed JSON, or `undefined` on 204
 * - On other errors, extracts just the server’s exception message
 */
export async function apiFetch(path, opts = {}) {
  const headers = new Headers(opts.headers || {});
  if (APP_CONFIG.debug) {
    const u = localStorage.getItem('devUser') || prompt('X-Dev-User:', 'alice');
    if (u) {
      headers.set('X-Dev-User', u);
      localStorage.setItem('devUser', u);
    }
  }

  const response = await fetch(path, { ...opts, headers });

  if (response.status === 204) {
    return; // No Content
  }
  if (response.status === 401) throw new Error('401 Unauthorized');
  if (response.status === 403) throw new Error('403 Forbidden');

  if (!response.ok) {
    const ct = response.headers.get('Content-Type') || '';
    let msg = `Error ${response.status}`;

    if (ct.includes('application/json')) {
      // JSON error response, e.g. { "detail": "..." }
      try {
        const errJson = await response.json();
        msg = errJson.detail ?? JSON.stringify(errJson);
      } catch {
        // fallback to status text
        msg = response.statusText || msg;
      }
    } else {
      // HTML or plain‐text: strip tags, split lines
      const raw = await response.text();
      const noHtml = raw.replace(/<[^>]*>/g, '');
      const lines = noHtml
        .split(/\r?\n/)
        .map(l => l.trim())
        .filter(l => l);

      // 1) Look from bottom up for "Exception: actual message"
      const excLine = [...lines].reverse()
        .find(l => /Exception\s*:/.test(l));
      if (excLine) {
        // extract after the colon
        msg = excLine.split(/Exception\s*:\s*/).pop().trim();
      } else {
        // 2) Otherwise filter out any lines containing tracing noise
        const filtered = lines.filter(l =>
          !/Traceback/.test(l) &&
          !/Exception Group/.test(l) &&
          !/^File /.test(l)
        );
        if (filtered.length) {
          msg = filtered[0];
        }
      }
    }

    throw new Error(msg);
  }

  // Success: parse JSON
  return response.json();
}
