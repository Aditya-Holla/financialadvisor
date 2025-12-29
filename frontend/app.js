// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// Token management
let authToken = localStorage.getItem('authToken') || '';

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    if (authToken) {
        document.getElementById('tokenInput').value = authToken;
        checkAuth();
    }
});

// Section navigation
function showSection(sectionId) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Show selected section
    document.getElementById(sectionId).classList.add('active');
    
    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    event.target.closest('.nav-item')?.classList.add('active');
    
    // Update page title
    const titles = {
        'dashboard': 'Dashboard',
        'recommendations': 'Recommendations',
        'explain': 'Explanations',
        'profile': 'Profile'
    };
    document.getElementById('pageTitle').textContent = titles[sectionId] || 'Dashboard';
}

// Set token
function setToken() {
    const token = document.getElementById('tokenInput').value.trim();
    if (token) {
        authToken = token;
        localStorage.setItem('authToken', token);
        showToast('Token saved successfully', 'success');
        checkAuth();
    } else {
        showToast('Please enter a token', 'error');
    }
}

// Check authentication
async function checkAuth() {
    if (!authToken) {
        updateAuthBadge(false);
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/me`, {
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Accept': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();
            updateAuthBadge(true, data.email || data.user_id);
            updateDashboardStats(data);
            showToast(`Authenticated as ${data.email || data.user_id}`, 'success');
        } else {
            updateAuthBadge(false);
            const error = await response.json();
            showToast(`Auth failed: ${error.message || 'Unauthorized'}`, 'error');
        }
    } catch (error) {
        updateAuthBadge(false);
        showToast(`Error: ${error.message}`, 'error');
    }
}

function updateAuthBadge(authenticated, userInfo = '') {
    const badge = document.getElementById('authStatusBadge');
    if (authenticated) {
        badge.classList.add('authenticated');
        badge.innerHTML = `
            <span class="status-dot"></span>
            <span>${userInfo || 'Authenticated'}</span>
        `;
    } else {
        badge.classList.remove('authenticated');
        badge.innerHTML = `
            <span class="status-dot"></span>
            <span>Not authenticated</span>
        `;
    }
}

function updateDashboardStats(userData) {
    if (userData) {
        document.getElementById('statUserId').textContent = userData.user_id || '-';
        document.getElementById('statEmail').textContent = userData.email || '-';
        document.getElementById('statBroker').textContent = userData.broker_linked ? 'Linked' : 'Not Linked';
    }
}

// Load user info
async function loadUserInfo() {
    const card = document.getElementById('profileCard');
    card.innerHTML = '<div class="loading">Loading profile...</div>';

    try {
        const response = await fetch(`${API_BASE_URL}/me`, {
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Accept': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();
            card.innerHTML = `
                <div class="data-display">
                    <div class="data-item">
                        <span class="data-label">User ID</span>
                        <span class="data-value">${data.user_id || '-'}</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Email</span>
                        <span class="data-value">${data.email || '-'}</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Broker Linked</span>
                        <span class="data-value">${data.broker_linked ? 'Yes' : 'No'}</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Last Sync</span>
                        <span class="data-value">${data.last_sync || 'Never'}</span>
                    </div>
                </div>
                <div class="json-display" style="margin-top: 24px;">${JSON.stringify(data, null, 2)}</div>
            `;
            showToast('Profile loaded successfully', 'success');
        } else {
            const error = await response.json();
            card.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><h3>Error</h3><p>${error.message || 'Failed to load profile'}</p></div>`;
            showToast(`Error: ${error.message || 'Failed to load profile'}`, 'error');
        }
    } catch (error) {
        card.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><h3>Error</h3><p>${error.message}</p></div>`;
        showToast(`Error: ${error.message}`, 'error');
    }
}

// Generate recommendation
async function generateRecommendation() {
    const card = document.getElementById('recommendationCard');
    card.innerHTML = '<div class="loading">Generating recommendation...</div>';

    try {
        const response = await fetch(`${API_BASE_URL}/recommendations/generate`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({})
        });

        if (response.ok) {
            const data = await response.json();
            const statusClass = data.decision === 'approve' ? 'approved' : 
                              data.decision === 'reject' ? 'rejected' : 'pending';
            
            card.innerHTML = `
                <div class="data-display">
                    <div class="data-item">
                        <span class="data-label">Recommendation ID</span>
                        <span class="data-value">${data.recommendation_id}</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Decision</span>
                        <span class="data-value">
                            <span class="status-badge ${statusClass}">${data.decision}</span>
                        </span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Status</span>
                        <span class="data-value">${data.status}</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Created At</span>
                        <span class="data-value">${new Date(data.created_at).toLocaleString()}</span>
                    </div>
                </div>
                <div class="json-display" style="margin-top: 24px;">${JSON.stringify(data, null, 2)}</div>
            `;
            
            // Update dashboard stat
            document.getElementById('statRecommendation').textContent = data.decision || '-';
            
            showToast('Recommendation generated successfully', 'success');
        } else {
            const error = await response.json();
            card.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><h3>Error</h3><p>${error.message || 'Failed to generate recommendation'}</p></div>`;
            showToast(`Error: ${error.message || 'Failed to generate recommendation'}`, 'error');
        }
    } catch (error) {
        card.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><h3>Error</h3><p>${error.message}</p></div>`;
        showToast(`Error: ${error.message}`, 'error');
    }
}

// Get latest recommendation
async function getLatestRecommendation() {
    const card = document.getElementById('recommendationCard');
    card.innerHTML = '<div class="loading">Loading latest recommendation...</div>';

    try {
        const response = await fetch(`${API_BASE_URL}/recommendations/latest`, {
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Accept': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();
            const statusClass = data.decision === 'approve' ? 'approved' : 
                              data.decision === 'reject' ? 'rejected' : 'pending';
            
            card.innerHTML = `
                <div class="data-display">
                    <div class="data-item">
                        <span class="data-label">Recommendation ID</span>
                        <span class="data-value">${data.recommendation_id}</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Decision</span>
                        <span class="data-value">
                            <span class="status-badge ${statusClass}">${data.decision}</span>
                        </span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Status</span>
                        <span class="data-value">${data.status}</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Guardrail Status</span>
                        <span class="data-value">${data.guardrail_status || 'N/A'}</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Has Proposal</span>
                        <span class="data-value">${data.has_proposal ? 'Yes' : 'No'}</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Created At</span>
                        <span class="data-value">${new Date(data.created_at).toLocaleString()}</span>
                    </div>
                </div>
                <div class="json-display" style="margin-top: 24px;">${JSON.stringify(data, null, 2)}</div>
            `;
            
            showToast('Latest recommendation loaded', 'success');
        } else {
            const error = await response.json();
            card.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><h3>Error</h3><p>${error.message || 'Failed to load recommendation'}</p></div>`;
            showToast(`Error: ${error.message || 'Failed to load recommendation'}`, 'error');
        }
    } catch (error) {
        card.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><h3>Error</h3><p>${error.message}</p></div>`;
        showToast(`Error: ${error.message}`, 'error');
    }
}

// Get explanation
async function getExplanation() {
    const card = document.getElementById('explanationCard');
    card.innerHTML = '<div class="loading">Getting explanation...</div>';

    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({})
        });

        if (response.ok) {
            const data = await response.json();
            card.innerHTML = `
                <div class="explanation-text">
                    ${data.explanation || 'No explanation available'}
                </div>
            `;
            showToast('Explanation generated', 'success');
        } else {
            const error = await response.json();
            card.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><h3>Error</h3><p>${error.message || 'Failed to get explanation'}</p></div>`;
            showToast(`Error: ${error.message || 'Failed to get explanation'}`, 'error');
        }
    } catch (error) {
        card.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><h3>Error</h3><p>${error.message}</p></div>`;
        showToast(`Error: ${error.message}`, 'error');
    }
}

// Toast notifications
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'success' ? '✅' : '❌';
    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
