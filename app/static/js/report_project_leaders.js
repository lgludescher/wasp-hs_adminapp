import { apiFetch, openEmailListModal } from './main.js';

// --- Endpoints ---
const REPORT_ENDPOINT      = '/reports/project-leaders/';
const ROLES_ENDPOINT       = '/roles/';
const CALL_TYPES_ENDPOINT  = '/project-call-types/';
const RESEARCHERS_ENDPOINT = '/researchers/';
const POSTDOCS_ENDPOINT    = '/postdocs/';
const PHDS_ENDPOINT        = '/phd-students/';

// --- DOM Elements ---
// Person Criteria
const filterSearch       = document.getElementById('filter-search');
const filterPersonStatus = document.getElementById('filter-person-status');
const filterPersonRole   = document.getElementById('filter-person-role');

// Membership Context
const filterMembership   = document.getElementById('filter-membership-role');

// Project Scope
const filterCallType     = document.getElementById('filter-call-type');
const filterProjStatus   = document.getElementById('filter-project-status');

// Actions & Table
const btnExportExcel     = document.getElementById('btn-export-excel');
const btnExportEmails    = document.getElementById('btn-export-emails');
const tbody              = document.getElementById('leaders-tbody');

// Modal Elements
const modal              = document.getElementById('modal-confirm');
const modalText          = document.getElementById('modal-text');
const modalCancelBtn     = document.getElementById('modal-cancel-btn');

// --- State ---
// Maps person_role_id -> { type: 'researcher'|'postdoc', id: entity_id, path: string }
const entityMap = new Map();

/** * Initialization
 */
;(async function init() {
    try {
        // 1. Load Metadata in parallel
        await Promise.all([
            loadRoles(),
            loadCallTypes(),
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
 */
function formatRoleName(role) {
    if (!role) return '';
    const lower = role.toLowerCase();

    if (lower === 'phd_student' || lower === 'phd student') return 'PhD Student';
    if (lower === 'postdoc') return 'Postdoc';
    if (lower === 'researcher') return 'Researcher';

    return role.charAt(0).toUpperCase() + role.slice(1);
}

/**
 * Pre-fetch Researchers and Postdocs for "Go to Profile" links.
 */
async function loadEntityMap() {
    try {
        const [researchers, postdocs, phds] = await Promise.all([
            apiFetch(RESEARCHERS_ENDPOINT),
            apiFetch(POSTDOCS_ENDPOINT),
            apiFetch(PHDS_ENDPOINT)
        ]);

        researchers.forEach(r => {
            entityMap.set(r.person_role_id, { type: 'researcher', id: r.id, path: 'manage-researchers' });
        });

        postdocs.forEach(p => {
            entityMap.set(p.person_role_id, { type: 'postdoc', id: p.id, path: 'manage-postdocs' });
        });

        phds.forEach(p => {
            entityMap.set(p.person_role_id, { type: 'phd', id: p.id, path: 'manage-phd-students' });
        });
    } catch (err) {
        console.error("Failed to load entity map.", err);
    }
}

/**
 * Populate Role Dropdown
 */
async function loadRoles() {
    try {
        const roles = await apiFetch(ROLES_ENDPOINT);
        roles.forEach(r => {
            // We include all roles or filter specific ones if needed.
            // For Leaders, usually Researchers and Postdocs, maybe PhDs.
            const displayName = formatRoleName(r.role);
            filterPersonRole.append(new Option(displayName, r.id));
        });
    } catch (err) {
        console.warn("Could not load roles.", err);
    }
}

/**
 * Populate Call Types Dropdown
 */
async function loadCallTypes() {
    try {
        const types = await apiFetch(CALL_TYPES_ENDPOINT);
        // Assuming types is list of {id, call_type, ...}
        types.forEach(t => {
            filterCallType.append(new Option(t.type, t.id));
        });
    } catch (err) {
        console.warn("Could not load call types.", err);
    }
}

function setupFilters() {
    filterSearch.oninput = debounce(loadReport, 300);

    // Immediate reload for all selects
    [
        filterPersonStatus, filterPersonRole,
        filterMembership,
        filterCallType, filterProjStatus
    ].forEach(el => el.onchange = loadReport);
}

/**
 * Main Logic: Fetch data, Aggregate, and Render
 */
async function loadReport() {
    try {
        const p = buildQueryParams();

        // Fetch Raw Data (Links)
        const links = await apiFetch(`${REPORT_ENDPOINT}?${p.toString()}`);

        // Process Data (Client-side Aggregation)
        const leaders = aggregateLeaders(links);

        renderTable(leaders);

    } catch (err) {
        showError(err);
    }
}

/**
 * Aggregates a list of Project Memberships into a list of Unique People.
 * Logic: Merges PI/Contact status using OR.
 */
function aggregateLeaders(links) {
    const map = new Map();

    links.forEach(link => {
        const prId = link.person_role_id;

        if (!map.has(prId)) {
            // New entry
            map.set(prId, {
                raw_link: link, // Keep reference for person details
                is_pi_aggregated: link.is_principal_investigator,
                is_contact_aggregated: link.is_contact_person
            });
        } else {
            // Existing entry - Update Flags
            const existing = map.get(prId);
            existing.is_pi_aggregated = existing.is_pi_aggregated || link.is_principal_investigator;
            existing.is_contact_aggregated = existing.is_contact_aggregated || link.is_contact_person;
        }
    });

    return Array.from(map.values());
}

function renderTable(list) {
    tbody.innerHTML = '';

    if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:#666; padding: 2rem;">No leaders found matching criteria.</td></tr>';
        return;
    }

    list.forEach(item => {
        const pr = item.raw_link.person_role;
        const person = pr.person;

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

        // Indicators
        const piIcon = item.is_pi_aggregated
            ? '<span class="checkmark">✔</span>'
            : '<span class="crossmark">✘</span>';

        const contactIcon = item.is_contact_aggregated
            ? '<span class="checkmark">✔</span>'
            : '<span class="crossmark">✘</span>';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${profileBtn}</td>
            <td class="cell-center">${piIcon}</td>
            <td class="cell-center">${contactIcon}</td>
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
    const exportUrl = `${REPORT_ENDPOINT}export/excel?${p.toString()}`;
    window.location.href = exportUrl;
};

btnExportEmails.onclick = async () => {
    try {
        const p = buildQueryParams();
        const data = await apiFetch(`${REPORT_ENDPOINT}export/emails?${p.toString()}`);
        openEmailListModal(data);
    } catch (err) {
        showError(err);
    }
};

function buildQueryParams() {
    const p = new URLSearchParams();
    if (filterSearch.value.trim())      p.set('search', filterSearch.value.trim());

    // Person Filters
    if (filterPersonStatus.value)       p.set('is_active_person_role', filterPersonStatus.value);
    if (filterPersonRole.value)         p.set('person_role_id', filterPersonRole.value);

    // Membership Filter (Translate Dropdown to Bools)
    if (filterMembership.value === 'pi') {
        p.set('is_pi_only', true);
    } else if (filterMembership.value === 'contact') {
        p.set('is_contact_only', true);
    }

    // Project Filters
    if (filterCallType.value)           p.set('call_type_id', filterCallType.value);
    if (filterProjStatus.value)         p.set('project_status', filterProjStatus.value);

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
