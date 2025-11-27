import { apiFetch } from './main.js';

const courseTotalCount = document.getElementById('course-total-count');
const filterSearch      = document.getElementById('filter-search');
const filterTerm        = document.getElementById('filter-term');
const filterActivity    = document.getElementById('filter-activity');
const filterActiveTerm  = document.getElementById('filter-active-term');
const btnShowCreate     = document.getElementById('btn-show-create');
const btnExportExcel    = document.getElementById('btn-export-excel');
const formCreate        = document.getElementById('form-create');
const btnCancel         = document.getElementById('btn-cancel');
const tbody             = document.getElementById('courses-tbody');

const modal             = document.getElementById('modal-confirm');
const modalText         = document.getElementById('modal-text');
const modalConfirm      = document.getElementById('modal-confirm-btn');
const modalCancelBtn    = document.getElementById('modal-cancel-btn');

let COURSE_TERMS     = [];
let GSA_LIST         = [];
let pendingRemove    = null;
let searchFilter     = '';
let termFilter       = '';
let activityFilter   = '';
let activeTermFilter = 'true';  // default to Active Terms

;(async function init() {
  try {
    COURSE_TERMS = await apiFetch('/course-terms/');
    GSA_LIST     = await apiFetch('/grad-school-activities/');
    populateSelects();
    loadCourses();
  } catch (err) {
    showError(err);
  }
})();

function populateSelects() {
  const termSelect = formCreate.querySelector('select[name="course_term_id"]');
  const actSelect  = formCreate.querySelector('select[name="grad_school_activity_id"]');

  filterTerm.innerHTML     = '<option value="">All Terms</option>';
  termSelect.innerHTML     = '<option value="">None</option>';
  filterActivity.innerHTML = '<option value="">All Grad School</option>';
  actSelect.innerHTML      = '<option value="">None</option>';

  COURSE_TERMS.forEach(t => {
    const lab = `${t.season} ${t.year}`;
    [filterTerm, termSelect].forEach(sel => {
      const o = document.createElement('option');
      o.value = t.id;
      o.textContent = lab;
      if (!t.is_active) o.classList.add('inactive-option');
      sel.appendChild(o);
    });
  });

  GSA_LIST.forEach(g => {
    const lab = `${g.activity_type.type} ${g.year}`;
    [filterActivity, actSelect].forEach(sel => {
      const o = document.createElement('option');
      o.value = g.id;
      o.textContent = lab;
      sel.appendChild(o);
    });
  });

  // only two options now: All Terms + Active Terms
  filterActiveTerm.innerHTML = `
    <option value="true" selected>Active Terms</option>
    <option value="">All Terms</option>
  `;
}

async function loadCourses() {
  try {
    const params = new URLSearchParams();
    if (searchFilter)     params.set('search', searchFilter);
    if (termFilter)       params.set('term_id', termFilter);
    if (activityFilter)   params.set('activity_id', activityFilter);
    if (activeTermFilter) params.set('is_active_term', activeTermFilter);

    const list = await apiFetch(`/courses/?${params}`);
    renderTable(list);
  } catch (err) {
    showError(err);
  }
}

function renderTable(list) {
  courseTotalCount.textContent = `(${list.length})`;

  tbody.innerHTML = '';
  list.forEach(item => {
    let termLabel = '';
    if (item.course_term) {
      termLabel = `${item.course_term.season} ${item.course_term.year}`;
    } else if (item.grad_school_activity) {
      termLabel = `${item.grad_school_activity.activity_type.type} ${item.grad_school_activity.year}`;
    }
    const goLink = `<a class="btn go-btn" href="/manage-courses/${item.id}/">Go to course</a>`;
    const credits = item.credit_points ?? '';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="cell-go">${goLink}</td>
      <td>${item.title}</td>
      <td>${termLabel}</td>
      <td style="text-align: center;">${item.student_count ?? 0}</td>
      <td style="text-align: center;">${credits}</td>
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
    showModal(`Remove course “${item.title}”?`);
  };
}

function startEdit(tr, item) {
  const termOptions = COURSE_TERMS.map(t => {
    const lab = `${t.season} ${t.year}`;
    const sel = item.course_term?.id === t.id ? ' selected' : '';
    const cls = !t.is_active ? ' class="inactive-option"' : '';
    return `<option value="${t.id}"${sel}${cls}>${lab}</option>`;
  }).join('');
  const actOptions = GSA_LIST.map(g => {
    const lab = `${g.activity_type.type} ${g.year}`;
    const sel = item.grad_school_activity?.id === g.id ? ' selected' : '';
    return `<option value="${g.id}"${sel}>${lab}</option>`;
  }).join('');

  let termCellHtml = '';
  if (item.course_term) {
    termCellHtml = `<select name="course_term_id">
                      <option value="">None</option>${termOptions}
                    </select>`;
  } else {
    termCellHtml = `<select name="grad_school_activity_id">
                      <option value="">None</option>${actOptions}
                    </select>`;
  }

  tr.innerHTML = `
    <td class="cell-go">
      <a class="btn go-btn" href="/manage-courses/${item.id}/">Go to course</a>
    </td>
    <td><input name="title" value="${item.title}" /></td>
    <td>${termCellHtml}</td>
    <td style="text-align: center; color: #777;">
        ${item.student_count ?? 0}
    </td>
    <td><input name="credit_points" type="number" value="${item.credit_points||0}" min="0" /></td>
    <td class="cell-actions">
      <button class="btn save-btn">Save</button>
      <button class="btn cancel-btn">Cancel</button>
    </td>
  `;

  const titleI = tr.querySelector('input[name="title"]');
  const termS   = tr.querySelector('select[name="course_term_id"]');
  const actS    = tr.querySelector('select[name="grad_school_activity_id"]');
  const credI   = tr.querySelector('input[name="credit_points"]');

  tr.querySelector('.cancel-btn').onclick = loadCourses;
  tr.querySelector('.save-btn').onclick = async () => {
    const payload = {
      title: titleI.value.trim() || null,
      course_term_id: termS ? parseInt(termS.value,10) : null,
      grad_school_activity_id: actS ? parseInt(actS.value,10) : null,
      credit_points: parseInt(credI.value,10) || 0,
    };
    try {
      await apiFetch(`/courses/${item.id}`, {
        method: 'PUT',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payload),
      });
      loadCourses();
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
  const termVal = e.target.course_term_id.value;
  const actVal  = e.target.grad_school_activity_id.value;

  // Now require at least one selection
  if (!termVal && !actVal) {
    return showError(new Error(
      'Select a Course Term or a Grad School Activity before creating.'
    ));
  }
  // Still disallow both
  if (termVal && actVal) {
    return showError(new Error(
      'Select either a Course Term or a Grad School Activity, not both.'
    ));
  }

  const data = {
    title: e.target.title.value.trim(),
    course_term_id: parseInt(termVal,10) || null,
    grad_school_activity_id: parseInt(actVal,10) || null,
    credit_points: parseInt(e.target.credit_points.value,10) || 0,
    notes: e.target.notes.value.trim() || null,
  };
  try {
    await apiFetch('/courses/', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(data),
    });
    formCreate.reset();
    formCreate.classList.add('hidden');
    btnShowCreate.disabled = false;
    loadCourses();
  } catch (err) {
    showError(err);
  }
};

btnExportExcel.onclick = () => {
  const params = new URLSearchParams();
  if (searchFilter)     params.set('search', searchFilter);
  if (termFilter)       params.set('term_id', termFilter);
  if (activityFilter)   params.set('activity_id', activityFilter);
  if (activeTermFilter) params.set('is_active_term', activeTermFilter);

  const exportUrl = `/courses/export/courses.xlsx?${params.toString()}`;
  window.location.href = exportUrl;
};

filterSearch.oninput = () => {
  searchFilter = filterSearch.value.trim();
  loadCourses();
};
filterTerm.onchange = () => {
  termFilter = filterTerm.value;
  loadCourses();
};
filterActivity.onchange = () => {
  activityFilter = filterActivity.value;
  loadCourses();
};
filterActiveTerm.onchange = () => {
  activeTermFilter = filterActiveTerm.value;
  loadCourses();
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
    await apiFetch(`/courses/${pendingRemove}`, { method: 'DELETE' });
    modal.classList.remove('active');
    pendingRemove = null;
    loadCourses();
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
