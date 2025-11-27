import { apiFetch, openEmailListModal } from './main.js';

// --- Endpoints ---
const REPORT_ENDPOINT      = '/reports/supervisions/';
const PHDS_ENDPOINT        = '/phd-students/';
const POSTDOCS_ENDPOINT    = '/postdocs/';
const RESEARCHERS_ENDPOINT = '/researchers/';
const ROLES_ENDPOINT       = '/roles/';

const supervisorTotalCount = document.getElementById('supervisor-total-count');

// --- DOM Elements ---
// Supervisor Filters
const filterSearch      = document.getElementById('filter-search');
const filterSupStatus   = document.getElementById('filter-sup-status');
const filterSupRole     = document.getElementById('filter-sup-role');
const filterMain        = document.getElementById('filter-main');

// Supervisee Filters
const filterStuStatus   = document.getElementById('filter-stu-status');
const filterStuRole     = document.getElementById('filter-stu-role');
const filterCohort      = document.getElementById('filter-cohort');

// Actions & Table
const btnExportExcel    = document.getElementById('btn-export-excel');
const btnExportEmails   = document.getElementById('btn-export-emails');
const tbody             = document.getElementById('supervisors-tbody');

// Modal Elements
const modal             = document.getElementById('modal-confirm');
const modalText         = document.getElementById('modal-text');
const modalCancelBtn    = document.getElementById('modal-cancel-btn');

// --- State ---
// Maps person_role_id -> { type: 'researcher'|'postdoc', id: entity_id, path: string }
const entityMap = new Map();

/** * Initialization
 */
;(async function init() {
    try {
        // 1. Load Metadata (Roles, Cohorts, Entity Map) in parallel
        await Promise.all([
            loadRoles(),
            loadCohorts(),
            loadEntityMap()
        ]);

        // 2. Setup Event Listeners
        setupFilters();
        if (modalCancelBtn) modalCancelBtn.onclick = () => modal.classList.add('hidden');

        // 3. Initial Load
        loadReport();

    } catch (err) {
        showError(err);
    }
})();

/**
 * Helper to pretty-print role names
 * e.g., 'phd_student' -> 'PhD Student'
 */
function formatRoleName(role) {
    if (!role) return '';
    const lower = role.toLowerCase();

    if (lower === 'phd_student' || lower === 'phd student') return 'PhD Student';
    if (lower === 'postdoc') return 'Postdoc';
    if (lower === 'researcher') return 'Researcher';

    // Fallback: Capitalize first letter
    return role.charAt(0).toUpperCase() + role.slice(1);
}

/**
 * Pre-fetch Researchers and Postdocs to map PersonRole IDs to specific Entity IDs.
 */
async function loadEntityMap() {
    try {
        const [researchers, postdocs] = await Promise.all([
            apiFetch(RESEARCHERS_ENDPOINT),
            apiFetch(POSTDOCS_ENDPOINT)
        ]);

        researchers.forEach(r => {
            entityMap.set(r.person_role_id, { type: 'researcher', id: r.id, path: 'manage-researchers' });
        });

        postdocs.forEach(p => {
            entityMap.set(p.person_role_id, { type: 'postdoc', id: p.id, path: 'manage-postdocs' });
        });
    } catch (err) {
        console.error("Failed to load entity map. Links might be broken.", err);
    }
}

/**
 * Fetch generic Roles to populate the Dropdowns with correct IDs and formatted names.
 */
async function loadRoles() {
    try {
        const roles = await apiFetch(ROLES_ENDPOINT); // Returns list of {id, role, ...}

        // Populate Supervisor Role Filter (Researcher OR Postdoc)
        roles.forEach(r => {
            const name = r.role.toLowerCase();
            if (name.includes('researcher') || name.includes('postdoc')) {
                const displayName = formatRoleName(r.role);
                filterSupRole.append(new Option(displayName, r.id));
            }
        });

        // Populate Supervisee Role Filter (PhD Student OR Postdoc)
        roles.forEach(r => {
            const name = r.role.toLowerCase();
            if (name.includes('phd') || name.includes('student') || name.includes('postdoc')) {
                const displayName = formatRoleName(r.role);
                filterStuRole.append(new Option(displayName, r.id));
            }
        });

    } catch (err) {
        console.warn("Could not load roles dynamically.", err);
    }
}

/**
 * Load Cohorts from both PhDs and Postdocs, merge, and sort.
 */
async function loadCohorts() {
    try {
        const [phds, postdocs] = await Promise.all([
            apiFetch(PHDS_ENDPOINT),
            apiFetch(POSTDOCS_ENDPOINT)
        ]);

        const phdCohorts = phds.map(s => s.cohort_number).filter(n => n != null);
        const pdCohorts  = postdocs.map(s => s.cohort_number).filter(n => n != null);

        // Merge, Unique, Sort
        const allCohorts = Array.from(new Set([...phdCohorts, ...pdCohorts]))
                                .sort((a, b) => a - b);

        filterCohort.innerHTML = '<option value="">All cohorts</option>';
        allCohorts.forEach(n => filterCohort.append(new Option(n, n)));

    } catch (err) {
        console.error("Failed to load cohorts", err);
    }
}

function setupFilters() {
    // Debounce search input
    filterSearch.oninput = debounce(loadReport, 300);

    // Immediate reload for selects
    [
        filterSupStatus, filterSupRole, filterMain,
        filterStuStatus, filterStuRole, filterCohort
    ].forEach(el => el.onchange = loadReport);
}

/**
 * Main Logic: Fetch data, Aggregate, and Render
 */
async function loadReport() {
    try {
        const p = buildQueryParams();

        // Fetch Raw Supervisions (Links)
        const supervisions = await apiFetch(`${REPORT_ENDPOINT}?${p.toString()}`);

        // Process Data (Client-side Aggregation)
        const supervisors = aggregateSupervisors(supervisions);

        renderTable(supervisors);

    } catch (err) {
        showError(err);
    }
}

/**
 * Aggregates a list of Supervision Links into a list of Unique Supervisors.
 * Logic: If they are Main in ANY of the links, they are marked as Main.
 */
function aggregateSupervisors(supervisionList) {
    const map = new Map();

    supervisionList.forEach(link => {
        const supId = link.supervisor_role_id;

        if (!map.has(supId)) {
            // New entry
            map.set(supId, {
                raw_link: link, // Keep reference for person details
                is_main_aggregated: link.is_main
            });
        } else {
            // Existing entry - Update Main Flag (OR logic)
            const existing = map.get(supId);
            existing.is_main_aggregated = existing.is_main_aggregated || link.is_main;
        }
    });

    return Array.from(map.values());
}

function renderTable(list) {
    supervisorTotalCount.textContent = `(${list.length})`;

    tbody.innerHTML = '';

    if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:#666; padding: 2rem;">No supervisors found matching criteria.</td></tr>';
        return;
    }

    list.forEach(item => {
        const pr = item.raw_link.supervisor; // Nested PersonRole object
        const person = pr.person;

        // Format the Role Name
        const roleName = formatRoleName(pr.role.role);

        const start = pr.start_date?.split('T')[0] || '';
        const end   = pr.end_date?.split('T')[0]   || '';

        // Determine "Go to Profile" Link
        let profileBtn = '';
        const entityInfo = entityMap.get(pr.id);

        if (entityInfo) {
            profileBtn = `<a class="go-btn" href="/${entityInfo.path}/${entityInfo.id}/">Go to profile</a>`;
        } else {
            profileBtn = `<span style="color:#ccc; font-size:0.8rem;">No profile</span>`;
        }

        // Main Checkmark
        const mainIcon = item.is_main_aggregated
            ? '<span class="checkmark">✔</span>'
            : '<span class="crossmark">✘</span>';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${profileBtn}</td>
            <td class="cell-center">${mainIcon}</td>
            <td>${roleName}</td>
            <td>${person.first_name} ${person.last_name}</td>
            <td>${person.email}</td>
            <td>${start}</td>
            <td>${end}</td>
        `;
        tbody.append(tr);
    });
}

// --- Exports ---

btnExportExcel.onclick = () => {
    const p = buildQueryParams();
    // Assuming backend endpoint exists
    const exportUrl = `${REPORT_ENDPOINT}export/excel?${p.toString()}`;
    window.location.href = exportUrl;
};

btnExportEmails.onclick = async () => {
    try {
        const p = buildQueryParams();
        // Assuming backend endpoint exists
        const data = await apiFetch(`${REPORT_ENDPOINT}export/emails?${p.toString()}`);
        openEmailListModal(data);
    } catch (err) {
        showError(err);
    }
};

function buildQueryParams() {
    const p = new URLSearchParams();
    if (filterSearch.value.trim())  p.set('search_supervisor', filterSearch.value.trim());

    // Supervisor Filters
    if (filterSupStatus.value)      p.set('is_active_supervisor', filterSupStatus.value);
    if (filterSupRole.value)        p.set('supervisor_role_id', filterSupRole.value);
    if (filterMain.value)           p.set('is_main', filterMain.value);

    // Supervisee Filters
    if (filterStuStatus.value)      p.set('is_active_student', filterStuStatus.value);
    if (filterStuRole.value)        p.set('supervisee_role_id', filterStuRole.value);
    if (filterCohort.value)         p.set('cohort_number', filterCohort.value);

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

function debounce(fn, delay) {
    let t;
    return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), delay);
    };
}
