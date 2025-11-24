import { apiFetch, openEmailListModal } from './main.js';

const ROLE_DISPLAY = { 1: 'Researcher', 2: 'PhD Student', 3: 'Postdoc' };
const ROLE_PATHS = { 1: 'researchers', 2: 'phd-students', 3: 'postdocs' };

// --- DOM Elements ---
const detailsSection = document.getElementById('course-details-section');
const modal = document.getElementById('modal-confirm');
const modalText = document.getElementById('modal-text');
const modalConfirmBtn = document.getElementById('modal-confirm-btn');
const modalCancelBtn = document.getElementById('modal-cancel-btn');

// --- State ---
let courseId = null;
let courseData = {};
let pendingRemove = null;
let ALL_COURSE_TERMS = [];
let ALL_GSA_ACTIVITIES = [];

// --- Initialization ---
(async function init() {
  const pathParts = window.location.pathname.split('/').filter(p => p);
  courseId = parseInt(pathParts[pathParts.length - 1], 10);

  if (!courseId) {
    return showError("Could not determine a valid Course ID from the URL.");
  }

  try {
    [ALL_COURSE_TERMS, ALL_GSA_ACTIVITIES] = await Promise.all([
        apiFetch('/course-terms/'),
        apiFetch('/grad-school-activities/')
    ]);
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
    courseData = await apiFetch(`/courses/${courseId}/`);
    renderMainDetails();
  } catch (err) {
    showError(err);
  }
}

function renderMainDetails(isEdit = false) {
  if (isEdit) {
    let termEditHtml = '';
    if (courseData.course_term) {
        const termOptions = ALL_COURSE_TERMS
            .filter(t => t.is_active || t.id === courseData.course_term.id)
            .map(t => {
                const selected = t.id === courseData.course_term.id ? ' selected' : '';
                return `<option value="${t.id}"${selected}>${t.season} ${t.year}</option>`;
            }).join('');
        termEditHtml = `<label class="detail-item"><strong>Term</strong><select name="course_term_id"><option value="">Select...</option>${termOptions}</select></label>`;
    } else if (courseData.grad_school_activity) {
        const activityOptions = ALL_GSA_ACTIVITIES.map(a => {
            const selected = a.id === courseData.grad_school_activity.id ? ' selected' : '';
            return `<option value="${a.id}"${selected}>${a.activity_type.type} ${a.year}</option>`;
        }).join('');
        termEditHtml = `<label class="detail-item"><strong>Term</strong><select name="grad_school_activity_id"><option value="">Select...</option>${activityOptions}</select></label>`;
    }

    detailsSection.innerHTML = `
      <div class="details-box-content">
        <label class="detail-item"><strong>Title</strong><input name="title" type="text" value="${courseData.title || ''}"></label>
        ${termEditHtml}
        <label class="detail-item"><strong>Credits</strong><input name="credit_points" type="number" min="0" value="${courseData.credit_points || ''}"></label>
        <label class="detail-item"><strong>Notes</strong><textarea name="notes">${courseData.notes || ''}</textarea></label>
      </div>
      <div class="details-box-actions">
        <button class="btn save-btn">Save</button>
        <button class="btn cancel-btn">Cancel</button>
      </div>
    `;

    detailsSection.querySelector('.save-btn').onclick = saveMainDetails;
    detailsSection.querySelector('.cancel-btn').onclick = () => renderMainDetails(false);
  } else {
    let termLabel = '';
    if (courseData.course_term) {
      termLabel = `${courseData.course_term.season} ${courseData.course_term.year}`;
    } else if (courseData.grad_school_activity) {
      termLabel = `${courseData.grad_school_activity.activity_type.type} ${courseData.grad_school_activity.year}`;
    }

    detailsSection.innerHTML = `
      <button class="btn btn-edit-main">Edit</button>
      <div class="details-box-content">
        <div class="detail-item"><strong>Title:</strong> <span>${courseData.title || ''}</span></div>
        <div class="detail-item"><strong>Term:</strong> <span>${termLabel}</span></div>
        <div class="detail-item"><strong>Credits:</strong> <span>${courseData.credit_points || ''}</span></div>
        <div class="detail-item"><strong>Notes:</strong> <span>${courseData.notes || ''}</span></div>
      </div>
    `;
    detailsSection.querySelector('.btn-edit-main').onclick = () => renderMainDetails(true);
  }
}

async function saveMainDetails() {
    const form = detailsSection;
    const courseUpdate = {
        title: form.querySelector('[name="title"]').value.trim() || null,
        credit_points: parseInt(form.querySelector('[name="credit_points"]').value, 10) || null,
        notes: form.querySelector('[name="notes"]').value.trim() || null,
        course_term_id: form.querySelector('[name="course_term_id"]') ? parseInt(form.querySelector('[name="course_term_id"]').value, 10) : null,
        grad_school_activity_id: form.querySelector('[name="grad_school_activity_id"]') ? parseInt(form.querySelector('[name="grad_school_activity_id"]').value, 10) : null,
    };
    try {
        await apiFetch(`/courses/${courseId}/`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(courseUpdate) });
        await loadAndRenderMainDetails();
    } catch (err) {
        showError(err);
    }
}

// --- Panel Management ---
const panelLoaders = {
  teachers: loadTeachers,
  students: loadStudents,
  institutions: loadInstitutions,
  letters: loadDecisionLetters,
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


// --- TEACHERS PANEL ---
async function loadTeachers(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = `
    <tr>
      <th></th>
      <th>Role</th>
      <th>Name</th>
      <th></th>
    </tr>`;
  try {
    const teachers = await apiFetch(`/courses/${courseId}/teachers/`);
    const enrichedData = await Promise.all(teachers.map(async (teacher) => {
      const subRolePath = ROLE_PATHS[teacher.role.id];
      let subRoleId = null;
      if (subRolePath) {
        const subRoleData = await apiFetch(`/${subRolePath}/?person_role_id=${teacher.id}`);
        if (subRoleData.length > 0) {
          subRoleId = subRoleData[0].id;
        }
      }
      return { ...teacher, subRolePath, subRoleId };
    }));
    tbody.innerHTML = '';
    if (!enrichedData.length) {
      tbody.innerHTML = `<tr><td colspan="4">No teachers associated with this course.</td></tr>`;
    } else {
      enrichedData.forEach(item => {
        const tr = document.createElement('tr');
        tr.dataset.personRoleId = item.id;
        renderTeacherRow(tr, item);
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4">Could not load teachers: ${err.message}</td></tr>`;
  }
  setupTeachersAddForm(panel);

  // SETUP EXPORT BUTTON
  const btnExport = panel.querySelector('#btn-export-teacher-emails');
  if (btnExport) {
    btnExport.onclick = async () => {
      try {
        // Fetch Data (No filters needed for teachers)
        const data = await apiFetch(`/courses/${courseId}/teachers/export/emails`);

        // Open Modal
        openEmailListModal(data);
      } catch (err) {
        console.error(err);
        alert("Failed to generate email list: " + err.message);
      }
    };
  }
}

function renderTeacherRow(tr, item) {
    const person = item.person;
    const roleName = ROLE_DISPLAY[item.role.id] || item.role.role;
    const profileLink = item.subRoleId ? `<a href="/manage-${item.subRolePath}/${item.subRoleId}/" class="go-to-btn">Go to Profile</a>` : '';

    tr.innerHTML = `
      <td>${profileLink}</td>
      <td>${roleName}</td>
      <td>${person.first_name} ${person.last_name}</td>
      <td class="cell-actions">
        <button class="btn remove-btn">Remove</button>
      </td>`;
    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = { type: 'course_teacher', item, name: `teacher ${person.first_name} ${person.last_name}` };
        showModal(`Remove ${pendingRemove.name}?`);
    };
}

async function setupTeachersAddForm(panel) {
    const addForm = panel.querySelector('.item-add-form');
    const roleFilterSelect = addForm.querySelector('[name=teacher_role_filter]');
    const personSelect = addForm.querySelector('[name=person_role_id]');

    const populatePeople = async () => {
        const rolePath = roleFilterSelect.value;
        const url = `/${rolePath}/?is_active=true`;
        const activePeople = await apiFetch(url);

        personSelect.innerHTML = '<option value="">Select a person...</option>';
        activePeople.forEach(person => {
           const p = person.person_role.person;
           const option = new Option(`${p.first_name} ${p.last_name}`, person.person_role.id);
           personSelect.add(option);
        });
    };

    roleFilterSelect.onchange = populatePeople;
    await populatePeople();

    setupPanelAddForm(panel, {
        loadFn: loadTeachers,
        filterSelect: roleFilterSelect,
        addCallback: (formData) => apiFetch(`/courses/${courseId}/teachers/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ person_role_id: parseInt(formData.get('person_role_id')) })
        }),
    });
}

// --- STUDENTS PANEL ---
async function loadStudents(panel) {
  const tbody = panel.querySelector('tbody');
  const searchInput = panel.querySelector('#student-search-input');
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
        const studentLinks = await apiFetch(`/courses/${courseId}/students/?${params}`);
        const enrichedData = await Promise.all(studentLinks.map(async (link) => {
            const studentDetails = await apiFetch(`/phd-students/${link.phd_student_id}`);
            return { ...link, student: studentDetails };
        }));

        tbody.innerHTML = '';
        if (!enrichedData.length) {
            tbody.innerHTML = `<tr><td colspan="5">No students found.</td></tr>`;
        } else {
            enrichedData.forEach(item => {
                const tr = document.createElement('tr');
                tr.dataset.studentId = item.phd_student_id;
                renderStudentRow(tr, item);
                tbody.appendChild(tr);
            });
        }
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5">Could not load students: ${err.message}</td></tr>`;
    }
  };

  searchInput.oninput = debounce(fetchAndRender, 300);
  await fetchAndRender();
  setupStudentsAddForm(panel);

  // SETUP EXPORT BUTTON
  const btnExport = panel.querySelector('#btn-export-course-emails');
  if (btnExport) {
    btnExport.onclick = async () => {
      try {
        const params = new URLSearchParams();
        const searchTerm = searchInput.value.trim();
        if (searchTerm) {
            params.set('search', searchTerm);
        }

        // Fetch Data
        // Assumes 'courseId' is available in scope (global or captured)
        const data = await apiFetch(`/courses/${courseId}/students/export/emails?${params.toString()}`);

        // Open Modal
        openEmailListModal(data);
      } catch (err) {
        // Simple error handling
        console.error(err);
        alert("Failed to generate email list: " + err.message);
      }
    };
  }
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
        pendingRemove = { type: 'course_student', item, name: `student ${person.first_name} ${person.last_name}` };
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
            is_completed: tr.querySelector('[name=is_completed]').checked,
            grade: tr.querySelector('[name=grade]').value || null
        };
        try {
            const updatedItem = await apiFetch(`/courses/${courseId}/students/${item.phd_student_id}`, {
                method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data)
            });
            renderStudentRow(tr, { ...item, ...updatedItem });
        } catch(err) {
            showError(err);
            renderStudentRow(tr, item);
        }
    };
}

async function setupStudentsAddForm(panel) {
    const studentSelect = panel.querySelector('[name=phd_student_id]');

    studentSelect.innerHTML = '<option value="">Select a student...</option>'; // Add default option

    const activeStudents = await apiFetch('/phd-students/?is_active=true');
    activeStudents.forEach(student => {
        const person = student.person_role.person;
        const option = new Option(`${person.first_name} ${person.last_name}`, student.id);
        studentSelect.add(option);
    });

    setupPanelAddForm(panel, {
        loadFn: () => loadStudents(panel),
        addCallback: (formData) => apiFetch(`/courses/${courseId}/students/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                phd_student_id: parseInt(formData.get('phd_student_id')),
                is_completed: formData.get('is_completed') === 'on',
                grade: formData.get('grade') || null
            })
        }),
    });
}


// --- INSTITUTIONS PANEL ---
async function loadInstitutions(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = '<tr><th>Institution</th><th></th></tr>';
  try {
    const institutions = await apiFetch(`/courses/${courseId}/institutions/`);
    tbody.innerHTML = '';
    if (!institutions.length) {
      tbody.innerHTML = `<tr><td colspan="2">No institutions associated.</td></tr>`;
    } else {
      institutions.forEach(item => {
        const tr = document.createElement('tr');
        tr.dataset.institutionId = item.id;
        renderInstitutionRow(tr, item);
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="2">Could not load institutions: ${err.message}</td></tr>`;
  }
  setupInstitutionsAddForm(panel);
}

function renderInstitutionRow(tr, item) {
    tr.innerHTML = `
      <td>${item.institution}</td>
      <td class="cell-actions">
        <button class="btn remove-btn">Remove</button>
      </td>`;
    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = {
            type: 'course_institution',
            item,
            name: `association for "${item.institution}"`
        };
        showModal(`Remove ${pendingRemove.name}?`);
    };
}

async function setupInstitutionsAddForm(panel) {
    await populateDropdown(panel.querySelector('[name=institution_id]'), '/institutions/', 'institution');
    setupPanelAddForm(panel, {
        loadFn: loadInstitutions,
        addCallback: (formData) => apiFetch(`/courses/${courseId}/institutions/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                institution_id: parseInt(formData.get('institution_id')),
            })
        }),
    });
}


// --- DECISION LETTERS PANEL ---
async function loadDecisionLetters(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = `<tr><th>Link</th><th></th></tr>`;
  try {
    const letters = await apiFetch(`/courses/${courseId}/decision-letters/`);
    tbody.innerHTML = '';
    if (!letters.length) {
      tbody.innerHTML = `<tr><td colspan="2">No decision letters associated.</td></tr>`;
    } else {
      letters.forEach(item => {
        const tr = document.createElement('tr');
        tr.dataset.letterId = item.id;
        renderDecisionLetterRow(tr, item);
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="2">Could not load decision letters: ${err.message}</td></tr>`;
  }
  setupDecisionLettersAddForm(panel);
}

function renderDecisionLetterRow(tr, item) {
    tr.innerHTML = `
      <td>${renderAsConditionalLink(item.link)}</td>
      <td class="cell-actions">
        <button class="btn edit-btn">Edit</button>
        <button class="btn remove-btn">Remove</button>
      </td>`;
    tr.querySelector('.edit-btn').onclick = () => startEditDecisionLetterRow(tr, item);
    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = {
            type: 'decision_letter',
            item,
            name: `decision letter link "${(item.link || '').substring(0, 40)}..."`
        };
        showModal(`Remove ${pendingRemove.name}?`);
    };
}

function startEditDecisionLetterRow(tr, item) {
    tr.innerHTML = `
      <td><input name="link" type="text" value="${item.link || ''}"></td>
      <td class="cell-actions">
        <button class="btn save-btn">Save</button>
        <button class="btn cancel-btn">Cancel</button>
      </td>`;
    tr.querySelector('.cancel-btn').onclick = () => renderDecisionLetterRow(tr, item);
    tr.querySelector('.save-btn').onclick = async () => {
        const data = { link: tr.querySelector('[name=link]').value.trim() };
        try {
            const updatedItem = await apiFetch(`/courses/${courseId}/decision-letters/${item.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            renderDecisionLetterRow(tr, updatedItem);
        } catch (err) { showError(err); renderDecisionLetterRow(tr, item); }
    };
}

function setupDecisionLettersAddForm(panel) {
    setupPanelAddForm(panel, {
        loadFn: loadDecisionLetters,
        addCallback: (formData) => apiFetch(`/courses/${courseId}/decision-letters/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ link: formData.get('link').trim() })
        }),
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
    if (type === 'course_teacher') {
      await apiFetch(`/courses/${courseId}/teachers/${item.id}`, { method: 'DELETE' });
      await loadTeachers(document.getElementById('panel-content-teachers'));
    } else if (type === 'course_student') {
      await apiFetch(`/courses/${courseId}/students/${item.phd_student_id}`, { method: 'DELETE' });
      await loadStudents(document.getElementById('panel-content-students'));
    } else if (type === 'course_institution') {
      await apiFetch(`/courses/${courseId}/institutions/${item.id}`, { method: 'DELETE' });
      await loadInstitutions(document.getElementById('panel-content-institutions'));
    } else if (type === 'decision_letter') {
      await apiFetch(`/courses/${courseId}/decision-letters/${item.id}`, { method: 'DELETE' });
      await loadDecisionLetters(document.getElementById('panel-content-letters'));
    }
    pendingRemove = null;
    modal.classList.add('hidden');
  } catch (err) {
    showError(err);
  }
}

function renderAsConditionalLink(link) {
  if (!link) return '';
  if (link.startsWith('http://') || link.startsWith('https://')) {
    return `<a href="${link}" target="_blank" rel="noopener noreferrer">${link}</a>`;
  }
  return `<span>${link}</span>`;
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
