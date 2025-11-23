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

/**
 * Opens a modal to display a list of emails for copying.
 *
 * @param {Object} data
 * @param {string[]} data.emails - List of email strings
 * @param {string[]} data.filter_summary - List of human-readable filters applied
 * @param {number} data.count - Total number of results
 */
export function openEmailListModal(data) {
  // 1. Prepare content
  const emailsStr = data.emails.join('; ');

  // 2. Create DOM elements dynamically
  // We reuse the 'modal' and 'modal-content' classes from your CSS
  const modalOverlay = document.createElement('div');
  modalOverlay.className = 'modal'; // Starts visible (no 'hidden' class)

  // Inner HTML structure
  // We use inline styles for specific layout tweaks inside the modal to ensure it looks good
  // without requiring global CSS changes right away.
  modalOverlay.innerHTML = `
    <div class="modal-content" style="max-width: 500px; display: flex; flex-direction: column; gap: 1rem;">
      <h3 style="margin: 0; font-size: 1.2rem;">Export Email List</h3>
      
      <div>
        <p>Found <strong>${data.count}</strong> entities matching criteria:</p>
        <ul style="margin: 0.5rem 0; padding-left: 1.5rem; color: #555; font-size: 0.9rem;">
          ${data.filter_summary.map(f => `<li>${f}</li>`).join('')}
        </ul>
      </div>

      <details style="border: 1px solid #eee; border-radius: 4px; padding: 0.5rem;">
        <summary style="cursor: pointer; font-size: 0.9rem; color: #666;">Show raw email list</summary>
        <textarea readonly style="width: 100%; height: 100px; margin-top: 0.5rem; font-family: monospace; font-size: 0.85rem; border: 1px solid #ccc;">${emailsStr}</textarea>
      </details>

      <div class="modal-actions">
        <button id="btn-modal-copy" class="btn" style="background-color: var(--color-accent, #007bff); color: #fff;">Copy to Clipboard</button>
        <button id="btn-modal-close" class="btn cancel-btn">Close</button>
      </div>
    </div>
  `;

  // 3. Attach to DOM
  document.body.appendChild(modalOverlay);

  // 4. Event Handlers
  const btnCopy = modalOverlay.querySelector('#btn-modal-copy');
  const btnClose = modalOverlay.querySelector('#btn-modal-close');

  btnCopy.onclick = async () => {
    try {
      await navigator.clipboard.writeText(emailsStr);
      const originalText = btnCopy.textContent;
      btnCopy.textContent = 'Copied!';
      btnCopy.disabled = true;
      setTimeout(() => {
        btnCopy.textContent = originalText;
        btnCopy.disabled = false;
      }, 2000);
    } catch (err) {
      console.error('Failed to copy', err);
      alert('Could not copy automatically. Please open "Show raw email list" and copy manually.');
    }
  };

  const closeModal = () => {
    modalOverlay.remove(); // Completely remove from DOM
  };

  btnClose.onclick = closeModal;

  // Close on click outside
  modalOverlay.onclick = (e) => {
    if (e.target === modalOverlay) closeModal();
  };
}
