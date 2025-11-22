import { apiFetch } from './main.js';

const ROLE_DISPLAY = { 1: 'Researcher', 2: 'PhD Student', 3: 'Postdoc' };
const ROLE_PATHS = { 1: 'researchers', 2: 'phd-students', 3: 'postdocs' };

// --- DOM Elements ---
const detailsSection = document.getElementById('phd-student-details-section');
const modal = document.getElementById('modal-confirm');
const modalText = document.getElementById('modal-text');
const modalConfirmBtn = document.getElementById('modal-confirm-btn');
const modalCancelBtn = document.getElementById('modal-cancel-btn');

// --- State ---
let phdStudentId = null;
let phdStudentData = {};
let pendingRemove = null;

// --- Initialization ---
(async function init() {
  const pathParts = window.location.pathname.split('/').filter(p => p);
  phdStudentId = parseInt(pathParts[pathParts.length - 1], 10);

  if (!phdStudentId) {
    return showError("Could not determine a valid PhD Student ID from the URL.");
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
    phdStudentData = await apiFetch(`/phd-students/${phdStudentId}/`);
    if (!phdStudentData || !phdStudentData.person_role) {
      throw new Error("Failed to load PhD student data.");
    }
    renderMainDetails();
  } catch (err) {
    showError(err);
  }
}

function renderMainDetails(isEdit = false) {
  const { person_role: role } = phdStudentData;
  const person = role.person;

  if (isEdit) {
    detailsSection.innerHTML = `
      <div class="details-box-content">
        <div class="detail-top-section">
            <div class="detail-column">
                <div class="detail-item"><strong>Name:</strong> <span>${person.first_name} ${person.last_name}</span></div>
                <div class="detail-item-group">
                    <label class="detail-item"><strong>Start Date</strong><input name="start_date" type="date" value="${role.start_date?.split('T')[0] || ''}"></label>
                    <label class="detail-item"><strong>End Date</strong><input name="end_date" type="date" value="${role.end_date?.split('T')[0] || ''}"></label>
                </div>
            </div>
            <div class="detail-column">
                <div class="detail-item-group">
                    <div class="detail-item"><strong>Email:</strong> <span>${person.email}</span></div>
                    <label class="detail-item"><strong>Personal Link</strong><input name="link" type="url" value="${phdStudentData.link || ''}"></label>
                </div>
                <label class="detail-item"><strong>Notes</strong><textarea name="notes">${phdStudentData.notes || ''}</textarea></label>
            </div>
        </div>
        <div class="detail-bottom-section">
            <label class="detail-item"><strong>Cohort Number</strong><input name="cohort_number" type="number" min="0" max="99" value="${phdStudentData.cohort_number || ''}"></label>
            <label class="detail-item"><span class="checkbox-label"><input name="is_affiliated" type="checkbox" ${phdStudentData.is_affiliated ? 'checked' : ''}> Affiliated?</span></label>
            <label class="detail-item"><strong>Department</strong><input name="department" type="text" value="${phdStudentData.department || ''}"></label>
            <label class="detail-item"><strong>Forskningsutbildningsämne</strong><input name="discipline" type="text" value="${phdStudentData.discipline || ''}"></label>
            
            <label class="detail-item"><strong>Planned Defense Date</strong><input name="planned_defense_date" type="date" value="${phdStudentData.planned_defense_date?.split('T')[0] || ''}"></label>
            <label class="detail-item"><span class="checkbox-label"><input name="is_graduated" type="checkbox" ${phdStudentData.is_graduated ? 'checked' : ''}> Graduated?</span></label>
            <label class="detail-item" style="grid-column: 3 / 5;"><strong>PhD Project Title</strong><input name="phd_project_title" type="text" value="${phdStudentData.phd_project_title || ''}"></label>
            
            <label class="detail-item" style="grid-column: 1 / 3;"><strong>Current Title</strong><input name="current_title" type="text" value="${phdStudentData.current_title || ''}"></label>
            <label class="detail-item" style="grid-column: 3 / 5;"><strong>Current Organization</strong><input name="current_organization" type="text" value="${phdStudentData.current_organization || ''}"></label>
        </div>
      </div>
      <div class="details-box-actions">
        <button class="btn save-btn">Save</button>
        <button class="btn cancel-btn">Cancel</button>
      </div>
    `;
    detailsSection.querySelector('.save-btn').onclick = saveMainDetails;
    detailsSection.querySelector('.cancel-btn').onclick = () => renderMainDetails(false);
  } else {
    detailsSection.innerHTML = `
      <button class="btn btn-edit-main">Edit</button>
      <div class="details-box-content">
        <div class="detail-top-section">
            <div class="detail-column">
                <div class="detail-item"><strong>Name:</strong> <span>${person.first_name} ${person.last_name}</span></div>
                <div class="detail-item-group">
                    <div class="detail-item"><strong>Start Date:</strong> <span>${role.start_date?.split('T')[0] || ''}</span></div>
                    <div class="detail-item"><strong>End Date:</strong> <span>${role.end_date?.split('T')[0] || ''}</span></div>
                </div>
            </div>
            <div class="detail-column">
                <div class="detail-item-group">
                    <div class="detail-item"><strong>Email:</strong> <span>${person.email}</span></div>
                    <div class="detail-item"><strong>Personal Link:</strong> ${renderAsConditionalLink(phdStudentData.link)}</div>
                </div>
                <div class="detail-item"><strong>Notes:</strong> <span>${phdStudentData.notes || ''}</span></div>
            </div>
        </div>
        <div class="detail-bottom-section">
            <div class="detail-item"><strong>Cohort Number:</strong> <span>${phdStudentData.cohort_number ?? ''}</span></div>
            <div class="detail-item"><strong>Affiliated?</strong> <input type="checkbox" disabled ${phdStudentData.is_affiliated ? 'checked' : ''}></div>
            <div class="detail-item"><strong>Department:</strong> <span>${phdStudentData.department || ''}</span></div>
            <div class="detail-item"><strong>Forskningsutbildningsämne:</strong> <span>${phdStudentData.discipline || ''}</span></div>

            <div class="detail-item"><strong>Planned Defense Date:</strong> <span>${phdStudentData.planned_defense_date?.split('T')[0] || ''}</span></div>
            <div class="detail-item"><strong>Graduated?</strong> <input type="checkbox" disabled ${phdStudentData.is_graduated ? 'checked' : ''}></div>
            <div class="detail-item" style="grid-column: 3 / 5;"><strong>PhD Project Title:</strong> <span>${phdStudentData.phd_project_title || ''}</span></div>
            
            <div class="detail-item" style="grid-column: 1 / 3;"><strong>Current Title:</strong> <span>${phdStudentData.current_title || ''}</span></div>
            <div class="detail-item" style="grid-column: 3 / 5;"><strong>Current Organization:</strong> <span>${phdStudentData.current_organization || ''}</span></div>
        </div>
      </div>
    `;
    detailsSection.querySelector('.btn-edit-main').onclick = () => renderMainDetails(true);
  }
}

async function saveMainDetails() {
    const form = detailsSection; // Context is the whole details box
    const studentData = {
        link: form.querySelector('[name="link"]').value.trim() || null,
        notes: form.querySelector('[name="notes"]').value.trim() || null,
        cohort_number: parseInt(form.querySelector('[name="cohort_number"]').value, 10) || null,
        is_affiliated: form.querySelector('[name="is_affiliated"]').checked,
        department: form.querySelector('[name="department"]').value.trim() || null,
        discipline: form.querySelector('[name="discipline"]').value.trim() || null,
        phd_project_title: form.querySelector('[name="phd_project_title"]').value.trim() || null,
        planned_defense_date: form.querySelector('[name="planned_defense_date"]').value || null,
        is_graduated: form.querySelector('[name="is_graduated"]').checked,
        current_title: form.querySelector('[name="current_title"]').value.trim() || null,
        current_organization: form.querySelector('[name="current_organization"]').value.trim() || null,
    };
    const roleData = {
        start_date: form.querySelector('[name="start_date"]').value || null,
        end_date: form.querySelector('[name="end_date"]').value || null,
    };
    try {
        await apiFetch(`/phd-students/${phdStudentId}/`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(studentData) });
        await apiFetch(`/person-roles/${phdStudentData.person_role_id}/`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(roleData) });
        await loadAndRenderMainDetails();
    } catch (err) {
        showError(err);
    }
}

// --- Panel Management ---
const panelLoaders = {
  courses: loadCourses,
  activities: loadActivities,
  supervisors: loadSupervisors,
  projects: loadProjects,
  institutions: loadInstitutions,
  fields: loadFields,
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
      // If panel is being collapsed, remove its 'loaded' status to force a fresh
      // reload on next open. This discards any inline-edit states.
      delete contentDiv.dataset.loaded;
      const tableContent = contentDiv.querySelector('.data-table');
      if (tableContent) tableContent.innerHTML = '<thead></thead><tbody></tbody>';
    } else if (!contentDiv.dataset.loaded) {
      // If panel is being expanded and hasn't been loaded yet, load it.
      panelLoaders[panelName](contentDiv);
      contentDiv.dataset.loaded = 'true';
    }
}

function setupPanelAddForm(panel, config) {
  const { addCallback, loadFn } = config;
  const showFormBtn = panel.querySelector('.btn-show-add-form');
  const addForm = panel.querySelector('.item-add-form');
  const cancelBtn = addForm.querySelector('.cancel-btn');

  showFormBtn.onclick = () => { addForm.classList.toggle('hidden'); };

  cancelBtn.onclick = () => {
    addForm.reset();
    addForm.classList.add('hidden');
    showFormBtn.classList.remove('hidden');

    // THE FIX: Find the first select element (the filter) and trigger its change event.
    const firstSelect = addForm.querySelector('select');
    if (firstSelect) {
      firstSelect.dispatchEvent(new Event('change'));
    }
  };

  addForm.onsubmit = async (e) => {
    e.preventDefault();
    try {
      await addCallback(new FormData(addForm));
      addForm.reset();
      addForm.classList.add('hidden');
      showFormBtn.classList.remove('hidden');

      // Also trigger the event after a successful save for good measure.
      const firstSelect = addForm.querySelector('select');
      if (firstSelect) {
        firstSelect.dispatchEvent(new Event('change'));
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
      <th class="cell-center">Completed?</th>
      <th>Grade</th>
      <th>Title</th>
      <th>Term</th>
      <th class="cell-center">Credits</th>
      <th></th>
    </tr>`;
  try {
    const courseLinks = await apiFetch(`/phd-students/${phdStudentId}/courses/`);

    // Enrich each link with the full course details
    const enrichedData = await Promise.all(courseLinks.map(async (link) => {
      const courseDetails = await apiFetch(`/courses/${link.course_id}`);
      return { ...link, course: courseDetails };
    }));

    tbody.innerHTML = '';
    if (!enrichedData.length) {
      tbody.innerHTML = `<tr><td colspan="7">No courses associated with this student.</td></tr>`;
    } else {
      enrichedData.forEach(item => {
        const tr = document.createElement('tr');
        tr.dataset.courseId = item.course_id;
        renderCourseRow(tr, item);
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7">Could not load courses: ${err.message}</td></tr>`;
  }
  setupCoursesAddForm(panel);
}

function renderCourseRow(tr, item) {
    const course = item.course;
    let termLabel = '';
    if (course.course_term) {
      termLabel = `${course.course_term.season} ${course.course_term.year}`;
    } else if (course.grad_school_activity) {
      termLabel = `${course.grad_school_activity.activity_type.type} ${course.grad_school_activity.year}`;
    }

    tr.innerHTML = `
      <td><a href="/manage-courses/${course.id}/" class="go-to-btn">Go to Course</a></td>
      <td class="cell-center">${item.is_completed ? '✔' : '✘'}</td>
      <td>${(item.grade || '').toUpperCase()}</td>
      <td>${course.title}</td>
      <td>${termLabel}</td>
      <td class="cell-center">${course.credit_points || ''}</td>
      <td class="cell-actions">
        <button class="btn edit-btn">Edit</button>
        <button class="btn remove-btn">Remove</button>
      </td>`;

    tr.querySelector('.edit-btn').onclick = () => startEditCourseRow(tr, item);
    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = {
            type: 'course_student',
            item,
            name: `association for course "${course.title}"`
        };
        showModal(`Remove ${pendingRemove.name}?`);
    };
}

function startEditCourseRow(tr, item) {
    const course = item.course;
    let termLabel = '';
    if (course.course_term) {
      termLabel = `${course.course_term.season} ${course.course_term.year}`;
    } else if (course.grad_school_activity) {
      termLabel = `${course.grad_school_activity.activity_type.type} ${course.grad_school_activity.year}`;
    }

    tr.innerHTML = `
      <td><a href="/manage-courses/${course.id}/" class="go-to-btn">Go to Course</a></td>
      <td class="cell-center"><input name="is_completed" type="checkbox" ${item.is_completed ? 'checked' : ''}></td>
      <td>
        <select name="grade">
          <option value="" ${!item.grade ? 'selected' : ''}>N/A</option>
          <option value="pass" ${item.grade === 'pass' ? 'selected' : ''}>PASS</option>
          <option value="fail" ${item.grade === 'fail' ? 'selected' : ''}>FAIL</option>
        </select>
      </td>
      <td>${course.title}</td>
      <td>${termLabel}</td>
      <td class="cell-center">${course.credit_points || ''}</td>
      <td class="cell-actions">
        <button class="btn save-btn">Save</button>
        <button class="btn cancel-btn">Cancel</button>
      </td>`;

    tr.querySelector('.cancel-btn').onclick = () => renderCourseRow(tr, item);
    tr.querySelector('.save-btn').onclick = async () => {
        const data = {
            phd_student_id: item.phd_student_id,
            is_completed: tr.querySelector('[name=is_completed]').checked,
            grade: tr.querySelector('[name=grade]').value || null
        };
        try {
            const updatedItem = await apiFetch(`/courses/${item.course_id}/students/${item.phd_student_id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            renderCourseRow(tr, { ...item, ...updatedItem });
        } catch(err) {
            showError(err);
            renderCourseRow(tr, item);
        }
    };
}

async function setupCoursesAddForm(panel) {
    const addForm = panel.querySelector('.item-add-form');
    const termFilter = addForm.querySelector('[name=course_term_filter]');
    const activityFilter = addForm.querySelector('[name=course_activity_filter]');
    const courseSelect = addForm.querySelector('[name=course_id]');

    const allTerms = await apiFetch('/course-terms/');
    const allActivities = await apiFetch('/grad-school-activities/');

    termFilter.innerHTML = '<option value="">All Active Terms</option>';
    allTerms
        .filter(t => t.is_active)
        .forEach(t => {
            const opt = new Option(`${t.season} ${t.year}`, t.id);
            termFilter.add(opt);
        });

    activityFilter.innerHTML = '<option value="">All GS Activities</option>';
    allActivities.forEach(a => {
        const opt = new Option(`${a.activity_type.type} ${a.year}`, a.id);
        activityFilter.add(opt);
    });

    const updateCoursesDropdown = async () => {
        const params = new URLSearchParams();
        params.set('is_active_term', 'true');

        const termId = termFilter.value;
        const activityId = activityFilter.value;

        if (termId) params.set('term_id', termId);
        if (activityId) params.set('activity_id', activityId);

        const courses = await apiFetch(`/courses/?${params}`);

        courses.sort((a, b) => (a.title || '').localeCompare(b.title || ''));

        courseSelect.innerHTML = '<option value="">Select a course...</option>';
        courses.forEach(course => {
            let termLabel = '';
            if (course.course_term) termLabel = `${course.course_term.season} ${course.course_term.year}`;
            else if (course.grad_school_activity) termLabel = `${course.grad_school_activity.activity_type.type} ${course.grad_school_activity.year}`;
            const opt = new Option(`${course.title} (${termLabel})`, course.id);
            courseSelect.add(opt);
        });
    };

    termFilter.onchange = () => {
        if (termFilter.value) activityFilter.value = '';
        updateCoursesDropdown();
    };
    activityFilter.onchange = () => {
        if (activityFilter.value) termFilter.value = '';
        updateCoursesDropdown();
    };

    await updateCoursesDropdown();

    setupPanelAddForm(panel, {
        loadFn: loadCourses,
        addCallback: (formData) => apiFetch(`/courses/${formData.get('course_id')}/students/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                phd_student_id: phdStudentId,
                is_completed: formData.get('is_completed') === 'on',
                grade: formData.get('grade') || null
            })
        }),
    });
}

// --- ACTIVITIES PANEL ---
async function loadActivities(panel) {
    // This function will kick off loading for both subsections in parallel
    const gsaPromise = loadGradSchoolActivities(panel);
    const abroadPromise = loadAbroadActivities(panel);
    await Promise.all([gsaPromise, abroadPromise]);

    // Set up the "Add" forms after the initial data is loaded
    setupGradSchoolAddForm(panel);
    setupAbroadAddForm(panel);
}

// --- Subsection: Grad School Activities ---
async function loadGradSchoolActivities(panel) {
    const tbody = panel.querySelector('.gsa-table tbody');
    panel.querySelector('.gsa-table thead').innerHTML = `
        <tr>
            <th></th>
            <th class="cell-center">Completed?</th>
            <th>Grade</th>
            <th>Activity Type</th>
            <th>Year</th>
            <th>Description</th>
            <th></th>
        </tr>`;
    try {
        const activities = await apiFetch(`/phd-students/${phdStudentId}/activities/?activity_type=grad_school`);
        tbody.innerHTML = '';
        if (!activities.length) {
            tbody.innerHTML = `<tr><td colspan="7">No Grad School Activities associated.</td></tr>`;
        } else {
            activities.forEach(item => {
                const tr = document.createElement('tr');
                tr.dataset.activityId = item.id;
                renderGradSchoolRow(tr, item);
                tbody.appendChild(tr);
            });
        }
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7">Could not load activities: ${err.message}</td></tr>`;
    }
}

function renderGradSchoolRow(tr, item) {
    const activity = item.activity;
    tr.innerHTML = `
        <td><a href="/manage-grad-school-activities/${activity.id}/" class="go-to-btn">Go to Activity</a></td>
        <td class="cell-center">${item.is_completed ? '✔' : '✘'}</td>
        <td>${(item.grade || '').toUpperCase()}</td>
        <td>${activity.activity_type.type}</td>
        <td>${activity.year}</td>
        <td>${activity.description || ''}</td>
        <td class="cell-actions">
            <button class="btn edit-btn">Edit</button>
            <button class="btn remove-btn">Remove</button>
        </td>`;
    tr.querySelector('.edit-btn').onclick = () => startEditGradSchoolRow(tr, item);
    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = { type: 'student_activity', item, name: `Grad School Activity "${activity.activity_type.type} ${activity.year}"` };
        showModal(`Remove ${pendingRemove.name}?`);
    };
}

function startEditGradSchoolRow(tr, item) {
    const activity = item.activity;
    tr.innerHTML = `
        <td><a href="/manage-grad-school-activities/${activity.id}/" class="go-to-btn">Go to Activity</a></td>
        <td class="cell-center"><input name="is_completed" type="checkbox" ${item.is_completed ? 'checked' : ''}></td>
        <td>
            <select name="grade">
                <option value="" ${!item.grade ? 'selected' : ''}>N/A</option>
                <option value="pass" ${item.grade === 'pass' ? 'selected' : ''}>PASS</option>
                <option value="fail" ${item.grade === 'fail' ? 'selected' : ''}>FAIL</option>
            </select>
        </td>
        <td>${activity.activity_type.type}</td>
        <td>${activity.year}</td>
        <td>${activity.description || ''}</td>
        <td class="cell-actions">
            <button class="btn save-btn">Save</button>
            <button class="btn cancel-btn">Cancel</button>
        </td>`;
    tr.querySelector('.cancel-btn').onclick = () => renderGradSchoolRow(tr, item);
    tr.querySelector('.save-btn').onclick = async () => {
        const data = {
            phd_student_id: phdStudentId,
            activity_id: item.activity.id,
            is_completed: tr.querySelector('[name=is_completed]').checked,
            grade: tr.querySelector('[name=grade]').value || null,
        };
        try {
            const updated = await apiFetch(`/phd-students/${phdStudentId}/activities/${item.id}/grad`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            renderGradSchoolRow(tr, updated);
        } catch (err) { showError(err); renderGradSchoolRow(tr, item); }
    };
}

async function setupGradSchoolAddForm(panel) {
    const form = panel.querySelector('.add-gsa-form');
    const typeFilter = form.querySelector('[name=gsa_type_filter]');
    const activitySelect = form.querySelector('[name=gsa_id]');

    await populateDropdown(typeFilter, '/grad-school-activity-types/', 'type', null, 'All Types');

    const updateActivityList = async () => {
        const typeId = typeFilter.value;
        const endpoint = typeId ? `/grad-school-activities/?activity_type_id=${typeId}` : '/grad-school-activities/';
        await populateDropdown(activitySelect, endpoint, item => `${item.activity_type.type} ${item.year}`);
    };

    typeFilter.onchange = updateActivityList;
    await updateActivityList();

    form.querySelector('.cancel-btn').onclick = () => { form.reset(); form.classList.add('hidden'); panel.querySelector('.btn-show-add-gsa-form').classList.remove('hidden'); };
    panel.querySelector('.btn-show-add-gsa-form').onclick = () => { form.classList.remove('hidden'); panel.querySelector('.btn-show-add-gsa-form').classList.add('hidden'); };

    form.onsubmit = async (e) => {
        e.preventDefault();
        const data = {
            phd_student_id: phdStudentId,
            activity_id: parseInt(form.querySelector('[name=gsa_id]').value),
            is_completed: form.querySelector('[name=is_completed]').checked,
            grade: form.querySelector('[name=grade]').value || null,
        };
        try {
            await apiFetch(`/phd-students/${phdStudentId}/activities/grad-school`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            form.reset(); form.classList.add('hidden'); panel.querySelector('.btn-show-add-gsa-form').classList.remove('hidden');
            await loadGradSchoolActivities(panel);
        } catch(err) { showError(err); }
    };
}


// --- Subsection: Activities Abroad ---
async function loadAbroadActivities(panel) {
    const tbody = panel.querySelector('.abroad-table tbody');
    panel.querySelector('.abroad-table thead').innerHTML = `
        <tr>
            <th class="col-description">Description</th>
            <th class="col-dates">Start Date</th>
            <th class="col-dates">End Date</th>
            <th class="col-location">City</th>
            <th class="col-location">Country</th>
            <th class="col-host">Host Institution</th>
            <th></th>
        </tr>`;
    try {
        const activities = await apiFetch(`/phd-students/${phdStudentId}/activities/?activity_type=abroad`);
        tbody.innerHTML = '';
        if (!activities.length) {
            tbody.innerHTML = `<tr><td colspan="7">No Semester Abroad associated.</td></tr>`;
        } else {
            activities.forEach(item => {
                const tr = document.createElement('tr');
                tr.dataset.activityId = item.id;
                renderAbroadRow(tr, item);
                tbody.appendChild(tr);
            });
        }
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7">Could not load activities: ${err.message}</td></tr>`;
    }
}

function renderAbroadRow(tr, item) {
    tr.innerHTML = `
        <td class="col-description">${item.description || ''}</td>
        <td class="col-dates">${item.start_date?.split('T')[0] || ''}</td>
        <td class="col-dates">${item.end_date?.split('T')[0] || ''}</td>
        <td class="col-location">${item.city || ''}</td>
        <td class="col-location">${item.country || ''}</td>
        <td class="col-host">${item.host_institution || ''}</td>
        <td class="cell-actions">
            <button class="btn edit-btn">Edit</button>
            <button class="btn remove-btn">Remove</button>
        </td>`;
    tr.querySelector('.edit-btn').onclick = () => startEditAbroadRow(tr, item);
    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = { type: 'student_activity', item, name: `Semester Abroad "${(item.description || '').substring(0, 30)}..."` };
        showModal(`Remove ${pendingRemove.name}?`);
    };
}

function startEditAbroadRow(tr, item) {
    tr.innerHTML = `
        <td class="col-description"><input name="description" type="text" value="${item.description || ''}"></td>
        <td class="col-dates"><input name="start_date" type="date" value="${item.start_date?.split('T')[0] || ''}"></td>
        <td class="col-dates"><input name="end_date" type="date" value="${item.end_date?.split('T')[0] || ''}"></td>
        <td class="col-location"><input name="city" type="text" value="${item.city || ''}"></td>
        <td class="col-location"><input name="country" type="text" value="${item.country || ''}"></td>
        <td class="col-host"><input name="host_institution" type="text" value="${item.host_institution || ''}"></td>
        <td class="cell-actions">
            <button class="btn save-btn">Save</button>
            <button class="btn cancel-btn">Cancel</button>
        </td>`;
    tr.querySelector('.cancel-btn').onclick = () => renderAbroadRow(tr, item);
    tr.querySelector('.save-btn').onclick = async () => {
        const data = {
            phd_student_id: phdStudentId,
            description: tr.querySelector('[name=description]').value.trim() || null,
            start_date: tr.querySelector('[name=start_date]').value || null,
            end_date: tr.querySelector('[name=end_date]').value || null,
            city: tr.querySelector('[name=city]').value.trim() || null,
            country: tr.querySelector('[name=country]').value.trim() || null,
            host_institution: tr.querySelector('[name=host_institution]').value.trim() || null,
        };
        try {
            const updated = await apiFetch(`/phd-students/${phdStudentId}/activities/${item.id}/abroad`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            renderAbroadRow(tr, updated);
        } catch (err) { showError(err); renderAbroadRow(tr, item); }
    };
}

function setupAbroadAddForm(panel) {
    const form = panel.querySelector('.add-abroad-form');
    form.querySelector('.cancel-btn').onclick = () => { form.reset(); form.classList.add('hidden'); panel.querySelector('.btn-show-add-abroad-form').classList.remove('hidden'); };
    panel.querySelector('.btn-show-add-abroad-form').onclick = () => { form.classList.remove('hidden'); panel.querySelector('.btn-show-add-abroad-form').classList.add('hidden'); };

    form.onsubmit = async (e) => {
        e.preventDefault();
        const data = {
            phd_student_id: phdStudentId,
            description: form.querySelector('[name=description]').value.trim() || null,
            start_date: form.querySelector('[name=start_date]').value || null,
            end_date: form.querySelector('[name=end_date]').value || null,
            city: form.querySelector('[name=city]').value.trim() || null,
            country: form.querySelector('[name=country]').value.trim() || null,
            host_institution: form.querySelector('[name=host_institution]').value.trim() || null,
        };
        try {
            await apiFetch(`/phd-students/${phdStudentId}/activities/abroad`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            form.reset(); form.classList.add('hidden'); panel.querySelector('.btn-show-add-abroad-form').classList.remove('hidden');
            await loadAbroadActivities(panel);
        } catch(err) { showError(err); }
    };
}


// --- SUPERVISORS PANEL ---
async function loadSupervisors(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = `
    <tr>
      <th></th>
      <th class="cell-center">Main Supervisor?</th>
      <th>Role</th>
      <th>Name</th>
      <th></th>
    </tr>`;
  try {
    const supervisions = await apiFetch(`/person-roles/${phdStudentData.person_role_id}/supervisors/`);

    // Enrich each supervision with supervisor details
    const enrichedData = await Promise.all(supervisions.map(async (supervision) => {
      const supervisorRole = await apiFetch(`/person-roles/${supervision.supervisor_role_id}`);
      const subRolePath = ROLE_PATHS[supervisorRole.role.id];

      let subRoleId = null;
      if (subRolePath) {
        const subRoleData = await apiFetch(`/${subRolePath}/?person_role_id=${supervisorRole.id}`);
        if (subRoleData.length > 0) {
          subRoleId = subRoleData[0].id;
        }
      }
      return { ...supervision, supervisorRole, subRolePath, subRoleId };
    }));

    tbody.innerHTML = '';
    if (!enrichedData.length) {
      tbody.innerHTML = `<tr><td colspan="5">No supervisors associated.</td></tr>`;
    } else {
      enrichedData.forEach(item => {
        const tr = document.createElement('tr');
        tr.dataset.supervisionId = item.id;
        renderSupervisorRow(tr, item);
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5">Could not load supervisors: ${err.message}</td></tr>`;
  }
  setupSupervisorsAddForm(panel);
}

function renderSupervisorRow(tr, item) {
    const supervisor = item.supervisorRole.person;
    const roleName = ROLE_DISPLAY[item.supervisorRole.role.id] || item.supervisorRole.role.role;
    const profileLink = item.subRoleId ? `<a href="/manage-${item.subRolePath}/${item.subRoleId}/" class="go-to-btn">Go to Profile</a>` : '';

    tr.innerHTML = `
      <td>${profileLink}</td>
      <td class="cell-center">${item.is_main ? '✔' : '✘'}</td>
      <td>${roleName}</td>
      <td>${supervisor.first_name} ${supervisor.last_name}</td>
      <td class="cell-actions">
        <button class="btn edit-btn">Edit</button>
        <button class="btn remove-btn">Remove</button>
      </td>`;
    tr.querySelector('.edit-btn').onclick = () => startEditSupervisorRow(tr, item);
    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = {
            type: 'supervision',
            item,
            name: `supervision by ${supervisor.first_name} ${supervisor.last_name}`
        };
        showModal(`Remove ${pendingRemove.name}?`);
    };
}

function startEditSupervisorRow(tr, item) {
    const supervisor = item.supervisorRole.person;
    const roleName = ROLE_DISPLAY[item.supervisorRole.role.id] || item.supervisorRole.role.role;
    const profileLink = item.subRoleId ? `<a href="/manage-${item.subRolePath}/${item.subRoleId}/" class="go-to-btn">Go to Profile</a>` : '';

    tr.innerHTML = `
      <td>${profileLink}</td>
      <td class="cell-center"><input type="checkbox" name="is_main" ${item.is_main ? 'checked' : ''}></td>
      <td>${roleName}</td>
      <td>${supervisor.first_name} ${supervisor.last_name}</td>
      <td class="cell-actions">
        <button class="btn save-btn">Save</button>
        <button class="btn cancel-btn">Cancel</button>
      </td>`;
    tr.querySelector('.cancel-btn').onclick = () => renderSupervisorRow(tr, item);
    tr.querySelector('.save-btn').onclick = async () => {
        const data = {
            supervisor_role_id: item.supervisor_role_id,
            student_role_id: item.student_role_id,
            is_main: tr.querySelector('[name=is_main]').checked
        };
        try {
            const updatedItem = await apiFetch(`/person-roles/${item.student_role_id}/supervisors/${item.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            renderSupervisorRow(tr, { ...item, ...updatedItem });
        } catch (err) {
            showError(err);
            renderSupervisorRow(tr, item);
        }
    };
}

async function setupSupervisorsAddForm(panel) {
    const addForm = panel.querySelector('.item-add-form');
    const roleFilterSelect = addForm.querySelector('[name=supervisor_role_filter]');
    const supervisorSelect = addForm.querySelector('[name=supervisor_role_id]');

    const populateSupervisors = async () => {
        const rolePath = roleFilterSelect.value; // 'researchers' or 'postdocs'
        const url = `/${rolePath}/?is_active=true`;
        const activeSupervisors = await apiFetch(url);

        supervisorSelect.innerHTML = '<option value="">Select a person...</option>';
        activeSupervisors.forEach(supervisor => {
           const person = supervisor.person_role.person;
           const option = new Option(`${person.first_name} ${person.last_name}`, supervisor.person_role.id);
           supervisorSelect.add(option);
        });
    };

    roleFilterSelect.onchange = populateSupervisors;
    await populateSupervisors(); // Initial population

    setupPanelAddForm(panel, {
        loadFn: loadSupervisors,
        addCallback: (formData) => apiFetch(`/person-roles/${phdStudentData.person_role_id}/supervisors/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_role_id: phdStudentData.person_role_id,
                supervisor_role_id: parseInt(formData.get('supervisor_role_id')),
                is_main: formData.get('is_main') === 'on'
            })
        }),
    });
}


// --- PROJECTS PANEL ---
async function loadProjects(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = `
    <tr>
      <th></th>
      <th class="cell-center">Active?</th>
      <th class="cell-center">PI?</th>
      <th class="cell-center">Contact Person?</th>
      <th>Project #</th>
      <th>Call Type</th>
      <th>Title</th>
      <th>Start</th>
      <th>End</th>
      <th></th>
    </tr>`;
  try {
    const projectLinks = await apiFetch(`/person-roles/${phdStudentData.person_role_id}/projects/`);
    const enrichedData = await Promise.all(projectLinks.map(async (link) => {
      const projectDetails = await apiFetch(`/projects/${link.project_id}/`);
      return { ...link, project: projectDetails };
    }));
    tbody.innerHTML = '';
    if (!enrichedData.length) {
      tbody.innerHTML = `<tr><td colspan="9">No projects associated.</td></tr>`;
    } else {
      enrichedData.forEach(item => {
        const tr = document.createElement('tr');
        tr.dataset.projectId = item.project.id;
        renderProjectRow(tr, item);
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9">Could not load project data: ${err.message}</td></tr>`;
  }
  setupProjectsAddForm(panel);
}
function renderProjectRow(tr, item) {
  tr.innerHTML = `
    <td><a href="/manage-projects/${item.project.id}/" class="go-to-btn">Go to Project</a></td>
    <td class="cell-center">${item.is_active ? '✔' : '✘'}</td>
    <td class="cell-center">${item.is_principal_investigator ? '✔' : '✘'}</td>
    <td class="cell-center">${item.is_contact_person ? '✔' : '✘'}</td>
    <td>${item.project.project_number}</td>
    <td>${item.project.call_type.type}</td>
    <td>${item.project.title}</td>
    <td>${item.project.start_date?.split('T')[0] || ''}</td>
    <td>${item.project.end_date?.split('T')[0] || ''}</td>
    <td class="cell-actions">
      <button class="btn edit-btn">Edit</button>
      <button class="btn remove-btn">Remove</button>
    </td>`;
  tr.querySelector('.edit-btn').onclick = () => startEditProjectRow(tr, item);
  tr.querySelector('.remove-btn').onclick = () => {
    pendingRemove = { type: 'project', item };
    showModal(`Remove association for project "${item.project.title}"?`);
  };
}
function startEditProjectRow(tr, item) {
  tr.innerHTML = `
    <td><a href="/manage-projects/${item.project.id}/" class="go-to-btn">Go to Project</a></td>
    <td class="cell-center"><input type="checkbox" name="is_active" ${item.is_active ? 'checked' : ''}></td>
    <td class="cell-center"><input type="checkbox" name="is_pi" ${item.is_principal_investigator ? 'checked' : ''}></td>
    <td class="cell-center"><input type="checkbox" name="is_contact_person" ${item.is_contact_person ? 'checked' : ''}></td>
    <td>${item.project.project_number}</td>
    <td>${item.project.call_type.type}</td>
    <td>${item.project.title}</td>
    <td>${item.project.start_date?.split('T')[0] || ''}</td>
    <td>${item.project.end_date?.split('T')[0] || ''}</td>
    <td class="cell-actions">
      <button class="btn save-btn">Save</button>
      <button class="btn cancel-btn">Cancel</button>
    </td>`;
  tr.querySelector('.cancel-btn').onclick = () => renderProjectRow(tr, item);
  tr.querySelector('.save-btn').onclick = async () => {
    const data = {
        person_role_id: phdStudentData.person_role_id,
        is_active: tr.querySelector('[name=is_active]').checked,
        is_principal_investigator: tr.querySelector('[name=is_pi]').checked,
        is_contact_person: tr.querySelector('[name=is_contact_person]').checked
    };
    try {
      const updatedItem = await apiFetch(`/projects/${item.project.id}/people-roles/${phdStudentData.person_role_id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
      renderProjectRow(tr, { ...item, ...updatedItem });
    } catch (err) { showError(err); renderProjectRow(tr, item); }
  };
}
async function setupProjectsAddForm(panel) {
    const addForm = panel.querySelector('.item-add-form');
    const callTypeSelect = addForm.querySelector('[name=project_call_type_filter]');
    const statusSelect = addForm.querySelector('[name=project_status_filter]');
    const projectSelect = addForm.querySelector('[name=project_id]');

    const updateProjectDropdown = async () => {
        const params = new URLSearchParams();
        const callTypeId = callTypeSelect.value;
        const projectStatus = statusSelect.value;

        if (callTypeId) params.set('call_type_id', callTypeId);
        if (projectStatus) params.set('project_status', projectStatus);

        const projects = await apiFetch(`/projects/?${params}`);

        projects.sort((a, b) => (a.project_number || '').localeCompare(b.project_number || ''));

        projectSelect.innerHTML = '<option value="">Select a project...</option>';
        projects.forEach(p => {
            const opt = new Option(`[${p.project_number}] ${p.title}`, p.id);
            projectSelect.add(opt);
        });
    };

    await populateDropdown(callTypeSelect, '/project-call-types/', 'type', '', 'All call types');

    callTypeSelect.onchange = updateProjectDropdown;
    statusSelect.onchange = updateProjectDropdown;

    await updateProjectDropdown();

    setupPanelAddForm(panel, {
      loadFn: loadProjects,
      addCallback: (formData) => apiFetch(`/projects/${formData.get('project_id')}/people-roles/`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ person_role_id: phdStudentData.person_role_id, is_principal_investigator: formData.get('is_pi') === 'on', is_contact_person: formData.get('is_contact_person') === 'on' })
      }),
    });
}


// --- INSTITUTIONS PANEL ---
async function loadInstitutions(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = '<tr><th>Institution</th><th>Start Date</th><th>End Date</th><th></th></tr>';
  try {
    const institutionLinks = await apiFetch(`/person-roles/${phdStudentData.person_role_id}/institutions/`);
    const enrichedData = await Promise.all(institutionLinks.map(async (link) => {
        const details = await apiFetch(`/institutions/${link.institution_id}`);
        return { ...link, institution: details };
    }));

    tbody.innerHTML = '';
    if (!enrichedData.length) {
      tbody.innerHTML = `<tr><td colspan="4">No institutions associated.</td></tr>`;
    } else {
      enrichedData.forEach(item => {
        const tr = document.createElement('tr');
        tr.dataset.institutionId = item.institution.id;
        renderInstitutionRow(tr, item);
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4">Could not load institutions: ${err.message}</td></tr>`;
  }
  setupInstitutionsAddForm(panel);
}
function renderInstitutionRow(tr, item) {
    tr.innerHTML = `
      <td>${item.institution.institution}</td>
      <td>${item.start_date?.split('T')[0] || ''}</td>
      <td>${item.end_date?.split('T')[0] || ''}</td>
      <td class="cell-actions">
        <button class="btn edit-btn">Edit</button>
        <button class="btn remove-btn">Remove</button>
      </td>`;
    tr.querySelector('.edit-btn').onclick = () => startEditInstitutionRow(tr, item);
    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = { type: 'institution', item };
        showModal(`Remove association for "${item.institution.institution}"?`);
    };
}
function startEditInstitutionRow(tr, item) {
    tr.innerHTML = `
      <td>${item.institution.institution}</td>
      <td><input type="date" name="start_date" value="${item.start_date?.split('T')[0] || ''}"></td>
      <td><input type="date" name="end_date" value="${item.end_date?.split('T')[0] || ''}"></td>
      <td class="cell-actions">
        <button class="btn save-btn">Save</button>
        <button class="btn cancel-btn">Cancel</button>
      </td>`;
    tr.querySelector('.cancel-btn').onclick = () => renderInstitutionRow(tr, item);
    tr.querySelector('.save-btn').onclick = async () => {
        const data = {
            institution_id: item.institution.id,
            start_date: tr.querySelector('[name=start_date]').value || null,
            end_date: tr.querySelector('[name=end_date]').value || null
        };
        try {
            const updatedLink = await apiFetch(`/person-roles/${phdStudentData.person_role_id}/institutions/${item.institution.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            renderInstitutionRow(tr, { ...item, ...updatedLink });
        } catch(err) {
            showError(err);
            renderInstitutionRow(tr, item);
        }
    };
}
async function setupInstitutionsAddForm(panel) {
    await populateDropdown(panel.querySelector('[name=institution_id]'), '/institutions/', 'institution');
    setupPanelAddForm(panel, {
        loadFn: loadInstitutions,
        addCallback: (formData) => apiFetch(`/person-roles/${phdStudentData.person_role_id}/institutions/`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                institution_id: parseInt(formData.get('institution_id')),
                start_date: formData.get('start_date') || null,
                end_date: formData.get('end_date') || null
            })
        }),
    });
}


// --- ACADEMIC FIELDS PANEL ---
async function loadFields(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = `<tr><th>Field (Branch)</th><th></th></tr>`;
  try {
    const fields = await apiFetch(`/person-roles/${phdStudentData.person_role_id}/fields/`);
    // Enrich each field with its branch name
    const enrichedData = await Promise.all(fields.map(async (field) => {
      const branch = await apiFetch(`/branches/${field.branch_id}`);
      return { ...field, branch };
    }));

    tbody.innerHTML = '';
    if (!enrichedData.length) {
      tbody.innerHTML = `<tr><td colspan="2">No academic fields associated.</td></tr>`;
    } else {
      enrichedData.forEach(item => {
        const tr = document.createElement('tr');
        tr.dataset.fieldId = item.id;
        renderFieldRow(tr, item);
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="2">Could not load academic fields: ${err.message}</td></tr>`;
  }
  setupFieldsAddForm(panel);
}

function renderFieldRow(tr, item) {
    tr.innerHTML = `
      <td>${item.field} (${item.branch.branch})</td>
      <td class="cell-actions">
        <button class="btn remove-btn">Remove</button>
      </td>`;
    tr.querySelector('.remove-btn').onclick = () => {
        pendingRemove = {
            type: 'field',
            item,
            name: `association for field "${item.field}"`
        };
        showModal(`Remove ${pendingRemove.name}?`);
    };
}

async function setupFieldsAddForm(panel) {
    const addForm = panel.querySelector('.item-add-form');
    const branchSelect = addForm.querySelector('[name=field_branch_filter]');
    const fieldSelect = addForm.querySelector('[name=field_id]');

    await populateDropdown(branchSelect, '/branches/', 'branch', null, 'All Branches');

    branchSelect.onchange = () => {
      const branchId = branchSelect.value;
      const endpoint = branchId ? `/fields/?branch_id=${branchId}` : '/fields/';
      populateDropdown(fieldSelect, endpoint, 'field');
    };
    branchSelect.dispatchEvent(new Event('change'));

    setupPanelAddForm(panel, {
        loadFn: loadFields,
        addCallback: (formData) => apiFetch(`/person-roles/${phdStudentData.person_role_id}/fields/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                field_id: parseInt(formData.get('field_id'))
            })
        }),
    });
}


// --- DECISION LETTERS PANEL ---
async function loadDecisionLetters(panel) {
  const tbody = panel.querySelector('tbody');
  panel.querySelector('thead').innerHTML = `<tr><th>Link</th><th></th></tr>`;
  try {
    const letters = await apiFetch(`/person-roles/${phdStudentData.person_role_id}/decision-letters/`);
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
        const data = {
            link: tr.querySelector('[name=link]').value.trim()
        };
        try {
            const updatedItem = await apiFetch(`/person-roles/${phdStudentData.person_role_id}/decision-letters/${item.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            renderDecisionLetterRow(tr, updatedItem);
        } catch (err) {
            showError(err);
            renderDecisionLetterRow(tr, item);
        }
    };
}

function setupDecisionLettersAddForm(panel) {
    setupPanelAddForm(panel, {
        loadFn: loadDecisionLetters,
        addCallback: (formData) => apiFetch(`/person-roles/${phdStudentData.person_role_id}/decision-letters/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                link: formData.get('link').trim()
            })
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
    if (type === 'course_student') {
      // FIX: Use the main phdStudentId from the page's state for robustness.
      await apiFetch(`/courses/${item.course_id}/students/${phdStudentId}`, { method: 'DELETE' });
      await loadCourses(document.getElementById('panel-content-courses'));
    } else if (type === 'student_activity') { // Add this 'else if' block
      await apiFetch(`/phd-students/${phdStudentId}/activities/${item.id}`, { method: 'DELETE' });
      // Reload the entire panel to refresh both subsections
      await loadActivities(document.getElementById('panel-content-activities'));
    } else if (type === 'supervision') { // Add this 'else if' block
      await apiFetch(`/person-roles/${item.student_role_id}/supervisors/${item.id}`, { method: 'DELETE' });
      await loadSupervisors(document.getElementById('panel-content-supervisors'));
    } else if (type === 'project') {
      await apiFetch(`/projects/${item.project.id}/people-roles/${phdStudentData.person_role_id}`, { method: 'DELETE' });
      await loadProjects(document.getElementById('panel-content-projects'));
    } else if (type === 'institution') {
      await apiFetch(`/person-roles/${phdStudentData.person_role_id}/institutions/${item.institution.id}`, { method: 'DELETE' });
      await loadInstitutions(document.getElementById('panel-content-institutions'));
    } else if (type === 'field') {
      await apiFetch(`/person-roles/${phdStudentData.person_role_id}/fields/${item.id}`, { method: 'DELETE' });
      await loadFields(document.getElementById('panel-content-fields'));
    } else if (type === 'decision_letter') {
      await apiFetch(`/person-roles/${phdStudentData.person_role_id}/decision-letters/${item.id}`, { method: 'DELETE' });
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
