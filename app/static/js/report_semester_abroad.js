import { apiFetch, openEmailListModal } from './main.js';

// --- Endpoints ---
const REPORT_ENDPOINT = '/reports/semester-abroad-data/';

// --- DOM Elements ---
// Filters
const filterStudentStatus  = document.getElementById('filter-student-status');
const filterActivityStatus = document.getElementById('filter-activity-status');

// Actions & Table
const btnExportExcel       = document.getElementById('btn-export-excel');
const tbody                = document.getElementById('abroad-tbody');

// Modal Elements
const modal                = document.getElementById('modal-confirm');
const modalText            = document.getElementById('modal-text');
const modalCancelBtn       = document.getElementById('modal-cancel-btn');

/**
 * Initialization
 */
;(function init() {
    try {
        // 1. Setup Event Listeners
        setupFilters();
        if (modalCancelBtn) modalCancelBtn.onclick = () => modal.classList.add('hidden');

        // 2. Initial Load
        loadReport();

    } catch (err) {
        showError(err);
    }
})();

function setupFilters() {
    // Reload report immediately on change
    filterStudentStatus.onchange = loadReport;
    filterActivityStatus.onchange = loadReport;
}

/**
 * Main Logic: Fetch data and Render
 */
async function loadReport() {
    try {
        const p = buildQueryParams();

        // Fetch Data
        const activities = await apiFetch(`${REPORT_ENDPOINT}?${p.toString()}`);

        renderTable(activities);

    } catch (err) {
        showError(err);
    }
}

function renderTable(list) {
    tbody.innerHTML = '';

    if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:#666; padding: 2rem;">No activities found matching criteria.</td></tr>';
        return;
    }

    list.forEach(item => {
        // Access nested data from the Schema
        const student = item.student;
        const person  = student.person_role.person;

        const start = item.start_date?.split('T')[0] || '';
        const end   = item.end_date?.split('T')[0]   || '';

        // "Go to Student" Link
        // We link directly to the PhD Student management page
        const profileBtn = `<a class="go-btn" href="/manage-phd-students/${student.id}/">Go to student</a>`;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${profileBtn}</td>
            <td>${item.host_institution || '-'}</td>
            <td>${item.city || '-'}</td>
            <td>${item.country || '-'}</td>
            <td>${person.first_name} ${person.last_name}</td>
            <td>${start}</td>
            <td>${end}</td>
        `;
        tbody.append(tr);
    });
}

// --- Exports ---

btnExportExcel.onclick = () => {
    const p = buildQueryParams();
    const exportUrl = `${REPORT_ENDPOINT}export/excel?${p.toString()}`;
    window.location.href = exportUrl;
};

function buildQueryParams() {
    const p = new URLSearchParams();

    // Student Status
    if (filterStudentStatus.value) {
        p.set('is_active_student', filterStudentStatus.value);
    }

    // Activity Status
    if (filterActivityStatus.value) {
        p.set('activity_status', filterActivityStatus.value);
    }

    return p;
}

// --- Utilities ---

function showError(err) {
    if (modalText) {
        modalText.textContent = err.message || String(err);
        const confirmBtn = document.getElementById('modal-confirm-btn');
        if(confirmBtn) confirmBtn.style.display = 'none';
        if(modalCancelBtn) modalCancelBtn.textContent = 'OK';
        modal.classList.remove('hidden');
    } else {
        alert(err.message || String(err));
    }
}
