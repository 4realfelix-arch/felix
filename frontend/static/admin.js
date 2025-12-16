/**
 * Felix Admin Dashboard
 * Manages users, sessions, features, and system health
 */

const tokenKey = 'felix-admin-token';
let adminToken = localStorage.getItem(tokenKey) || '';

// The admin dashboard input placeholder suggests "admin: felix2024", but that value isn't
// a real token. If we auto-load it from localStorage, it can confuse the auth flow and
// cause the page to think it has a token when it doesn't.
if (adminToken === 'admin: felix2024') {
    adminToken = '';
}

// DOM Elements
const tokenInput = document.getElementById('tokenInput');
const saveTokenBtn = document.getElementById('saveToken');
const refreshBtn = document.getElementById('refresh');
const messageArea = document.getElementById('messageArea');

// Stats
const statusValue = document.getElementById('statusValue');
const sessionsValue = document.getElementById('sessionsValue');
const usersValue = document.getElementById('usersValue');
const toolsValue = document.getElementById('toolsValue');

// Services
const sttStatus = document.getElementById('sttStatus');
const llmStatus = document.getElementById('llmStatus');
const ttsStatus = document.getElementById('ttsStatus');
const comfyStatus = document.getElementById('comfyStatus');

// Lists
const eventsList = document.getElementById('eventsList');
const eventCount = document.getElementById('eventCount');
const usersList = document.getElementById('usersList');
const userCount = document.getElementById('userCount');
const sessionsTableBody = document.querySelector('#sessionsTable tbody');
const sessionCount = document.getElementById('sessionCount');
const logsList = document.getElementById('logsList');
const logCount = document.getElementById('logCount');

// Create user form
const createUserForm = document.getElementById('createUserForm');
const newUsername = document.getElementById('newUsername');
const newPassword = document.getElementById('newPassword');
const newIsAdmin = document.getElementById('newIsAdmin');

const REFRESH_MS = 10000;
let refreshTimer = null;

// Initialize
if (tokenInput && adminToken) {
    tokenInput.value = adminToken;
}

// Navigation
document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const section = tab.dataset.section;
        
        // Update active tab
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        
        // Show section
        document.querySelectorAll('.admin-section').forEach(s => s.classList.remove('active'));
        document.getElementById(`section${capitalize(section)}`).classList.add('active');
        
        // Load section-specific data
        if (section === 'users') loadUsers();
        if (section === 'sessions') loadSessions();
        if (section === 'logs') loadLogs();
    });
});

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

// Messages
function showMessage(text, type = 'success') {
    const msg = document.createElement('div');
    msg.className = `message ${type}`;
    msg.textContent = text;
    messageArea.innerHTML = '';
    messageArea.appendChild(msg);
    setTimeout(() => msg.remove(), 5000);
}

// Helpers
function formatTimestamp(ts) {
    if (!ts && ts !== 0) return '—';
    const date = new Date(ts * 1000);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatSince(ts) {
    if (!ts && ts !== 0) return '—';
    const diffMs = Date.now() - ts * 1000;
    const diffSec = Math.max(0, Math.floor(diffMs / 1000));
    if (diffSec < 60) return `${diffSec}s ago`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    return `${diffHr}h ago`;
}

function formatDate(isoStr) {
    if (!isoStr) return '—';
    const date = new Date(isoStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function statusBadge(status) {
    const isOk = status === 'ok' || status === 'ready' || status === 'running';
    return `<span class="status-dot ${isOk ? 'online' : 'offline'}"></span> ${status || 'unknown'}`;
}

// API
async function fetchAdmin(path, options = {}) {
    const headers = { ...options.headers };

    // The placeholder value "admin: felix2024" is not a server token.
    // Only attach header auth when we have something that looks like a real session token.
    const looksLikeSessionToken = typeof adminToken === 'string' && adminToken.length >= 20 && !adminToken.includes(':');
    
    if (looksLikeSessionToken) {
        // Support both schemes:
        //  - Cookie-based sessions (preferred for browser login)
        //  - Header token auth (for pasted session tokens / legacy usage)
        headers['X-Admin-Token'] = adminToken;
        headers['Authorization'] = `Bearer ${adminToken}`;
    }
    
    // Always include cookies so a normal Felix login can authorize admin calls.
    // IMPORTANT: spread options first so credentials can't be overwritten.
    const res = await fetch(path, { ...options, credentials: 'include', headers });

    if (!res.ok) {
        if (res.status === 401) {
            throw new Error('Unauthorized: Login on the main app first (admin/felix2024). If you pasted a token, make sure it is a real session token (not "admin: felix2024").');
        }
        if (res.status === 403) {
            throw new Error('Forbidden: Admin privileges required. Make sure your account has admin rights.');
        }
        const text = await res.text();
        throw new Error(text || `Request failed (${res.status})`);
    }

    // Return the Response so callers can decide whether they want JSON/text.
    return res;
}

// Health & Overview
async function loadHealth() {
    try {
        const health = await (await fetchAdmin('/api/admin/health')).json();
        
        statusValue.textContent = health.status || 'unknown';
        statusValue.className = `stat-value ${health.status === 'ok' ? 'success' : 'warning'}`;
        
        sessionsValue.textContent = health.active_sessions || 0;
        toolsValue.textContent = health.tools_registered || 0;
        
        sttStatus.innerHTML = statusBadge(health.stt);
        llmStatus.innerHTML = statusBadge(health.llm);
        ttsStatus.innerHTML = statusBadge(health.tts);
        comfyStatus.innerHTML = statusBadge(health.comfyui);
        
    } catch (err) {
        console.error('Failed to load health:', err);
        statusValue.textContent = 'error';
        statusValue.className = 'stat-value danger';
    }
}

async function loadEvents() {
    try {
        const data = await (await fetchAdmin('/api/admin/events')).json();
        const events = data.events || [];
        
        eventCount.textContent = events.length;
        
        if (events.length === 0) {
            eventsList.innerHTML = '<div class="empty-state">No events yet</div>';
            return;
        }
        
        eventsList.innerHTML = events.slice(-20).reverse().map(ev => {
            const { type, timestamp, ...rest } = ev;
            return `
                <div class="log-item">
                    <div class="meta">
                        <span>${formatTimestamp(timestamp)}</span>
                        <span class="level info">${type}</span>
                    </div>
                </div>
            `;
        }).join('');
        
    } catch (err) {
        console.error('Failed to load events:', err);
    }
}

// Users
async function loadUsers() {
    try {
        const data = await (await fetchAdmin('/api/auth/users')).json();
        const users = data.users || [];
        
        usersValue.textContent = users.length;
        userCount.textContent = `${users.length} users`;
        
        if (users.length === 0) {
            usersList.innerHTML = '<div class="empty-state">No users found</div>';
            return;
        }
        
        usersList.innerHTML = users.map(user => `
            <div class="user-row" data-username="${user.username}">
                <div class="user-info">
                    <div class="user-avatar">${user.username.charAt(0).toUpperCase()}</div>
                    <div class="user-details">
                        <h4>${user.username}</h4>
                        <p>Created: ${formatDate(user.created_at)} • Last login: ${formatDate(user.last_login)}</p>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span class="user-badge ${user.is_admin ? 'admin' : 'user'}">${user.is_admin ? 'Admin' : 'User'}</span>
                    <div class="user-actions">
                        <button class="btn btn-sm btn-danger delete-user" data-username="${user.username}">Delete</button>
                    </div>
                </div>
            </div>
        `).join('');
        
        // Add delete handlers
        document.querySelectorAll('.delete-user').forEach(btn => {
            btn.addEventListener('click', () => deleteUser(btn.dataset.username));
        });
        
    } catch (err) {
        console.error('Failed to load users:', err);
        usersList.innerHTML = `<div class="message error">${err.message}</div>`;
    }
}

async function createUser(username, password, isAdmin) {
    try {
        await fetchAdmin('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, is_admin: isAdmin })
        });
        
        showMessage(`User "${username}" created successfully!`, 'success');
        loadUsers();
        
        // Clear form
        newUsername.value = '';
        newPassword.value = '';
        newIsAdmin.checked = false;
        
    } catch (err) {
        showMessage(err.message, 'error');
    }
}

async function deleteUser(username) {
    if (!confirm(`Are you sure you want to delete user "${username}"?`)) return;
    
    try {
        await fetchAdmin(`/api/auth/users/${username}`, { method: 'DELETE' });
        showMessage(`User "${username}" deleted.`, 'success');
        loadUsers();
    } catch (err) {
        showMessage(err.message, 'error');
    }
}

// Sessions
async function loadSessions() {
    try {
        const data = await (await fetchAdmin('/api/admin/sessions')).json();
        const sessions = data.sessions || [];
        
        sessionCount.textContent = `${sessions.length} active`;
        
        if (sessions.length === 0) {
            sessionsTableBody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--admin-text-muted);">No active sessions</td></tr>';
            return;
        }
        
        sessionsTableBody.innerHTML = sessions
            .sort((a, b) => (b.last_activity || 0) - (a.last_activity || 0))
            .map(s => {
                const counts = s.history_counts || {};
                return `
                    <tr>
                        <td><code>${s.client_id?.substring(0, 12)}...</code></td>
                        <td>${s.username || '—'}</td>
                        <td>${s.state}</td>
                        <td>${formatSince(s.last_activity)}</td>
                        <td>U:${counts.user || 0} A:${counts.assistant || 0} T:${counts.tool || 0}</td>
                    </tr>
                `;
            }).join('');
        
    } catch (err) {
        console.error('Failed to load sessions:', err);
    }
}

// Logs
async function loadLogs() {
    try {
        const data = await (await fetchAdmin('/api/admin/logs')).json();
        const logs = data.logs || [];
        
        logCount.textContent = logs.length;
        
        if (logs.length === 0) {
            logsList.innerHTML = '<div class="empty-state">No logs yet</div>';
            return;
        }
        
        logsList.innerHTML = logs.slice(-50).reverse().map(log => {
            const { level, message, timestamp } = log;
            return `
                <div class="log-item">
                    <div class="meta">
                        <span>${formatTimestamp(timestamp)}</span>
                        <span class="level ${level?.toLowerCase()}">${level || 'info'}</span>
                    </div>
                    <div>${message || '—'}</div>
                </div>
            `;
        }).join('');
        
    } catch (err) {
        console.error('Failed to load logs:', err);
    }
}

// Refresh all data
async function refreshAll() {
    // Token is optional when auth is enabled: cookie sessions can authorize admin calls.
    // If auth is disabled, the admin token is still required.
    if (!adminToken) {
        refreshBtn.querySelector('svg + span')?.remove();
    }
    
    try {
        refreshBtn.disabled = true;
        
        await Promise.all([
            loadHealth(),
            loadEvents(),
            loadUsers(),
        ]);
        
        // Load section-specific data based on active tab
        const activeTab = document.querySelector('.nav-tab.active');
        if (activeTab) {
            const section = activeTab.dataset.section;
            if (section === 'sessions') await loadSessions();
            if (section === 'logs') await loadLogs();
        }
        
    } catch (err) {
        console.error('Refresh failed:', err);
        showMessage(err.message, 'error');
    } finally {
        refreshBtn.disabled = false;
    }
}

function startPolling() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(refreshAll, REFRESH_MS);
}

// Event Listeners
saveTokenBtn?.addEventListener('click', () => {
    adminToken = tokenInput.value.trim();
    if (adminToken) {
        localStorage.setItem(tokenKey, adminToken);
        showMessage('Connected! Loading data...', 'success');
        refreshAll();
        startPolling();
    }
});

refreshBtn?.addEventListener('click', () => refreshAll());

createUserForm?.addEventListener('submit', (e) => {
    e.preventDefault();
    const username = newUsername.value.trim();
    const password = newPassword.value;
    const isAdmin = newIsAdmin.checked;
    
    if (!username || !password) {
        showMessage('Username and password are required', 'error');
        return;
    }
    
    createUser(username, password, isAdmin);
});

// Initial load
if (adminToken) {
    refreshAll();
    startPolling();
}
