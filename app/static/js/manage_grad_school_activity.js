import { apiFetch } from './main.js';

// --- DOM Elements ---
const detailsSection = document.getElementById('grad-school-activity-details-section');
const modal = document.getElementById('modal-confirm');
const modalText = document.getElementById('modal-text');
const modalConfirmBtn = document.getElementById('modal-confirm-btn');
const modalCancelBtn = document.getElementById('modal-cancel-btn');

// --- State ---
let gradSchoolActivityId = null;
let gradSchoolActivityData = {};
let pendingRemove = null;

// --- Initialization ---
(async function init() {
  const pathParts = window.location.pathname.split('/').filter(p => p);
  gradSchoolActivityId = parseInt(pathParts[pathParts.length - 1], 10);

  if (!gradSchoolActivityId) {
    return showError("Could not determine a valid Grad School Activity ID from the URL.");
  }

  try {
    await loadAndRenderMainDetails();
    setupPanelToggles();
  } catch (err) {
    showError(err);
    detailsSection.innerHTML = `<p>Error loading details. Please try again.</p>`;
  }

  modalCancelBtn.onclick = () => { pendingRemove = null; modal.classList.add('hidden'); };
  modalConfirmBtn.onclick = confirmRemove;
})();


// --- Main Details Logic ---
async function loadAndRenderMainDetails() {
  try {
    gradSchoolActivityData = await apiFetch(`/grad-school-activities/${gradSchoolActivityId}/`);
    renderMainDetails();
  } catch (err) {
    showError(err);
  }
}

function renderMainDetails(isEdit = false) {
  if (isEdit) {
    detailsSection.innerHTML = `
      <div class="details-box-content">
        <label class="detail-item"><strong>Activity Type</strong><select name="activity_type_id"></select></label>
        <label class="detail-item"><strong>Year</strong><input name="year" type="number" min="2000" value="${gradSchoolActivityData.year || ''}"></label>
        <label class="detail-item"><strong>Description</strong><textarea name="description">${gradSchoolActivityData.description || ''}</textarea></label>
      </div>
      <div class="details-box-actions">
        <button class="btn save-btn">Save</button>
        <button class="btn cancel-btn">Cancel</button>
      </div>
    `;

    populateDropdown(detailsSection.querySelector('[name="activity_type_id"]'), '/grad-school-activity-types/', 'type', gradSchoolActivityData.activity_type.id);
    detailsSection.querySelector('.save-btn').onclick = saveMainDetails;
    detailsSection.querySelector('.cancel-btn').onclick = () => renderMainDetails(false);
  } else {
    detailsSection.innerHTML = `
      <button class="btn btn-edit-main">Edit</button>
      <div class="details-box-content">
        <div class="detail-item"><strong>Activity Type:</strong> <span>${gradSchoolActivityData.activity_type.type}</span></div>
        <div class="detail-item"><strong>Year:</strong> <span>${gradSchoolActivityData.year || ''}</span></div>
        <div class="detail-item"><strong>Description:</strong> <span>${gradSchoolActivityData.description || ''}</span></div>
      </div>
    `;
    detailsSection.querySelector('.btn-edit-main').onclick = () => renderMainDetails(true);
  }
}

async function saveMainDetails() {
    const form = detailsSection;
    const activityUpdate = {
        activity_type_id: parseInt(form.querySelector('[name="activity_type_id"]').value, 10) || null,
        year: parseInt(form.querySelector('[name="year"]').value, 10) || null,
        description: form.querySelector('[name="description"]').value.trim() || null,
    };
    try {
        await apiFetch(`/grad-school-activities/${gradSchoolActivityId}/`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(activityUpdate) });
        await loadAndRenderMainDetails();
    } catch (err) {
        showError(err);
    }
}

// --- Panel Management ---
const panelLoaders = {
  courses: loadCourses,
  students: loadStudents,
};

function setupPanelToggles() {
  document.querySelectorAll('.panel-header').forEach(header => {
    header.onclick = () => togglePanel(header.querySelector('.expand-btn').dataset.panel);
  });
}
function togglePanel(panelName) {
    const contentDiv = document.getElementById(`panel-content-${panelName}`);
    const btn = document.querySelector(`.expand-btn[data-panel="${panelName}"]`);
    if (!contentDiv || !btn) return;
    const isHidden = contentDiv.classList.toggle('hidden');
    btn.textContent = isHidden ? '+' : '–';

    if (isHidden) {
      delete contentDiv.dataset.loaded;
      const tableContent = contentDiv.querySelector('.data-table');
      if (tableContent) tableContent.innerHTML = '<thead></thead><tbody></tbody>';
    } else if (!contentDiv.dataset.loaded) {
      panelLoaders[panelName](contentDiv);
      contentDiv.dataset.loaded = 'true';
    }
}

function setupPanelAddForm(panel, config) {
  const { addCallback, loadFn, filterSelect } = config;
  const showFormBtn = panel.querySelector('.btn-show-add-form');
  const addForm = panel.querySelector('.item-add-form');
  const cancelBtn = addForm.querySelector('.cancel-btn');
  showFormBtn.onclick = () => { addForm.classList.toggle('hidden'); };

  cancelBtn.onclick = () => {
    addForm.reset();
    addForm.classList.add('hidden');
    showFormBtn.classList.remove('hidden');
    if (filterSelect) {
      filterSelect.dispatchEvent(new Event('change'));
    }
  };

  addForm.onsubmit = async (e) => {
    e.preventDefault();
    try {
      await addCallback(new FormData(addForm));
      addForm.reset();
      addForm.classList.add('hidden');
      showFormBtn.classList.remove('hidden');
      if (filterSelect) {
        filterSelect.dispatchEvent(new Event('change'));
      }
      await loadFn(panel);
    } catch (err) { showError(err); }
  };
}


// --- COURSES PANEL ---
async function loadCourses(panel) {
    const tbody = panel.querySelector('tbody');
    panel.querySelector('thead').innerHTML = `
        <tr>
            <th></th>
            <th>Title</th>
            <th class="cell-center">Credits</th>
            <th>Notes</th>
            <th></th>
        </tr>`;
    try {
        const courses = await apiFetch(`/grad-school-activities/${gradSchoolActivityId}/courses/`);
        tbody.innerHTML = '';
        if (!courses.length) {
            tbody.innerHTML = `<tr><td colspan="5">No courses associated with this activity.</td></tr>`;
        } else {
            courses.forEach(item => {
                const tr = document.createElement('tr');
                tr.dataset.courseId = item.id;
                renderCourseRow(tr, item);
                tbody.appendChild(tr);
            });
        }
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5">Could not load courses: ${err.message}</td></tr>`;
    }
    setupCoursesAddForm(panel);
}

function renderCourseRow(tr, item) {
    tr.innerHTML = `
        <td><a href="/manage-courses/${item.id}/" class="go-to-btn">Go to Course</a></td>
        <td>${item.title}</td>
        <td class="cell-center">${item.credit_points || ''}</td>
        <td>${item.notes || ''}</td>
        <td class="cell-actions">
            <button class="btn edit-btn">Edit</button>
            <button class="btn remove-btn">Remove</button>
        </td>`;
    tr.querySelector('.edit-btn').onclick = () => startEditCourseRow(tr, item);
    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = { type: 'course', item, name: `course "${item.title}"` };
        showModal(`Remove ${pendingRemove.name}?`);
    };
}

function startEditCourseRow(tr, item) {
    tr.innerHTML = `
        <td><a href="/manage-courses/${item.id}/" class="go-to-btn">Go to Course</a></td>
        <td><input name="title" type="text" value="${item.title || ''}"></td>
        <td class="cell-center"><input name="credit_points" type="number" min="0" value="${item.credit_points || ''}" style="width: 80px;"></td>
        <td><textarea name="notes">${item.notes || ''}</textarea></td>
        <td class="cell-actions">
            <button class="btn save-btn">Save</button>
            <button class="btn cancel-btn">Cancel</button>
        </td>`;
    tr.querySelector('.cancel-btn').onclick = () => renderCourseRow(tr, item);
    tr.querySelector('.save-btn').onclick = async () => {
        const data = {
            title: tr.querySelector('[name=title]').value.trim(),
            credit_points: parseInt(tr.querySelector('[name=credit_points]').value, 10) || null,
            notes: tr.querySelector('[name=notes]').value.trim() || null,
            grad_school_activity_id: gradSchoolActivityId // Keep the link
        };
        try {
            const updated = await apiFetch(`/courses/${item.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            renderCourseRow(tr, updated);
        } catch (err) { showError(err); renderCourseRow(tr, item); }
    };
}

function setupCoursesAddForm(panel) {
    setupPanelAddForm(panel, {
        loadFn: () => loadCourses(panel),
        addCallback: (formData) => apiFetch(`/courses/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                grad_school_activity_id: gradSchoolActivityId,
                title: formData.get('title').trim(),
                credit_points: parseInt(formData.get('credit_points'), 10) || null,
                notes: formData.get('notes').trim() || null,
            })
        }),
    });
}


// --- STUDENTS PANEL ---
async function loadStudents(panel) {
    const tbody = panel.querySelector('tbody');
    const searchInput = panel.querySelector('#student-search-input'); // Assumes you added this input in the HTML
    panel.querySelector('thead').innerHTML = `
        <tr>
            <th></th>
            <th class="cell-center">Completed?</th>
            <th>Grade</th>
            <th>Name</th>
            <th></th>
        </tr>`;

    const fetchAndRender = async () => {
        try {
            const params = new URLSearchParams();
            const searchTerm = searchInput.value.trim();
            if (searchTerm) {
                params.set('search', searchTerm);
            }
            // The API endpoint now includes the search parameter
            const studentActivities = await apiFetch(`/grad-school-activities/${gradSchoolActivityId}/student-activities/?${params.toString()}`);

            const enrichedData = await Promise.all(studentActivities.map(async (activity) => {
                const student = await apiFetch(`/phd-students/${activity.phd_student_id}`);
                return { ...activity, student };
            }));

            tbody.innerHTML = '';
            if (!enrichedData.length) {
                tbody.innerHTML = `<tr><td colspan="5">No students found.</td></tr>`;
            } else {
                enrichedData.forEach(item => {
                    const tr = document.createElement('tr');
                    tr.dataset.activityId = item.id;
                    renderStudentRow(tr, item);
                    tbody.appendChild(tr);
                });
            }
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="5">Could not load students: ${err.message}</td></tr>`;
        }
    };

    // Set up the debounced event listener and trigger the initial load
    searchInput.oninput = debounce(fetchAndRender, 300);
    await fetchAndRender();
    setupStudentsAddForm(panel);
}

function renderStudentRow(tr, item) {
    const person = item.student.person_role.person;

    // Define the display text
    const gradeDisplay = item.grade ? item.grade.toUpperCase() : 'Not available';

    tr.innerHTML = `
        <td><a href="/manage-phd-students/${item.phd_student_id}/" class="go-to-btn">Go to Student</a></td>
        <td class="cell-center">${item.is_completed ? '✔' : '✘'}</td>
        <td>${gradeDisplay}</td>
        <td>${person.first_name} ${person.last_name}</td>
        <td class="cell-actions">
            <button class="btn edit-btn">Edit</button>
            <button class="btn remove-btn">Remove</button>
        </td>`;
    tr.querySelector('.edit-btn').onclick = () => startEditStudentRow(tr, item);
    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = { type: 'student_activity', item, name: `association for ${person.first_name} ${person.last_name}` };
        showModal(`Remove ${pendingRemove.name}?`);
    };
}

function startEditStudentRow(tr, item) {
    const person = item.student.person_role.person;
    tr.innerHTML = `
        <td><a href="/manage-phd-students/${item.phd_student_id}/" class="go-to-btn">Go to Student</a></td>
        <td class="cell-center"><input name="is_completed" type="checkbox" ${item.is_completed ? 'checked' : ''}></td>
        <td>
            <select name="grade">
                <option value="" ${!item.grade ? 'selected' : ''}>Not available</option>
                <option value="pass" ${item.grade === 'pass' ? 'selected' : ''}>PASS</option>
                <option value="fail" ${item.grade === 'fail' ? 'selected' : ''}>FAIL</option>
            </select>
        </td>
        <td>${person.first_name} ${person.last_name}</td>
        <td class="cell-actions">
            <button class="btn save-btn">Save</button>
            <button class="btn cancel-btn">Cancel</button>
        </td>`;
    tr.querySelector('.cancel-btn').onclick = () => renderStudentRow(tr, item);
    tr.querySelector('.save-btn').onclick = async () => {
        const data = {
            phd_student_id: item.phd_student_id,
            activity_id: gradSchoolActivityId,
            is_completed: tr.querySelector('[name=is_completed]').checked,
            grade: tr.querySelector('[name=grade]').value || null,
        };
        try {
            const updated = await apiFetch(`/phd-students/${item.phd_student_id}/activities/${item.id}/grad`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            renderStudentRow(tr, { ...item, ...updated });
        } catch (err) { showError(err); renderStudentRow(tr, item); }
    };
}

async function setupStudentsAddForm(panel) {
    const studentSelect = panel.querySelector('[name=phd_student_id]');
    await populateDropdown(studentSelect, '/phd-students/?is_active=true', s => `${s.person_role.person.first_name} ${s.person_role.person.last_name}`, null, 'Select a student...');

    setupPanelAddForm(panel, {
        loadFn: () => loadStudents(panel),
        addCallback: async (formData) => {
            const phdId = parseInt(formData.get('phd_student_id'));
            const data = {
                phd_student_id: phdId,
                activity_id: gradSchoolActivityId,
                is_completed: formData.get('is_completed') === 'on',
                grade: formData.get('grade') || null
            };
            await apiFetch(`/phd-students/${phdId}/activities/grad-school`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        },
    });
}


// --- Utility Functions ---
function showModal(message) {
  modalText.textContent = message;
  modalConfirmBtn.style.display = '';
  modalCancelBtn.textContent = 'Cancel';
  modal.classList.remove('hidden');
}

function showError(err) {
  modalText.textContent = err.message || String(err);
  modalConfirmBtn.style.display = 'none';
  modalCancelBtn.textContent = 'OK';
  modal.classList.remove('hidden');
}

async function confirmRemove() {
  if (!pendingRemove) return;
  const { type, item } = pendingRemove;
  try {
    if (type === 'course') {
        await apiFetch(`/courses/${item.id}`, { method: 'DELETE' });
        await loadCourses(document.getElementById('panel-content-courses'));
    } else if (type === 'student_activity') {
        await apiFetch(`/phd-students/${item.phd_student_id}/activities/${item.id}`, { method: 'DELETE' });
        await loadStudents(document.getElementById('panel-content-students'));
    }
    pendingRemove = null;
    modal.classList.add('hidden');
  } catch (err) {
    showError(err);
  }
}

async function populateDropdown(select, endpoint, textField, selectedId = null, defaultOption = 'Select...') {
  try {
    const items = await apiFetch(endpoint);
    select.innerHTML = `<option value="">${defaultOption}</option>`;
    items.forEach(item => {
      const text = typeof textField === 'function' ? textField(item) : item[textField];
      const option = new Option(text, item.id);
      if (item.id === selectedId) option.selected = true;
      select.add(option);
    });
  } catch (err) { showError(err); }
}

function debounce(fn, delay) {
  let t;
  return (...a) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...a), delay);
  };
}
