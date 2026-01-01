// Login Page JavaScript - Supabase Authentication
// Wrapped in IIFE to avoid variable conflicts with other scripts

(function() {
    'use strict';
    
    // Supabase Configuration - will be read when DOM is ready (after config.js loads)
    let SUPABASE_CONFIG = null;
    let supabase = null;

// Function to initialize Supabase client (called after config.js has loaded)
function initializeSupabase() {
    // Read config from window (set by config.js)
    SUPABASE_CONFIG = {
        url: window.SUPABASE_URL || 'YOUR_SUPABASE_URL',
        anonKey: window.SUPABASE_ANON_KEY || 'YOUR_SUPABASE_ANON_KEY'
    };
    
    console.log('Reading config:', {
        url: SUPABASE_CONFIG.url,
        anonKeySet: SUPABASE_CONFIG.anonKey !== 'YOUR_SUPABASE_ANON_KEY',
        supabaseLib: typeof window.supabase !== 'undefined',
        windowUrl: window.SUPABASE_URL,
        windowAnonKey: window.SUPABASE_ANON_KEY ? 'Set' : 'Not set'
    });
    
    try {
        // Check if Supabase library is loaded and config is set
        if (typeof window.supabase !== 'undefined' && SUPABASE_CONFIG.url !== 'YOUR_SUPABASE_URL' && SUPABASE_CONFIG.anonKey !== 'YOUR_SUPABASE_ANON_KEY') {
            supabase = window.supabase.createClient(SUPABASE_CONFIG.url, SUPABASE_CONFIG.anonKey);
            console.log('✓ Supabase client initialized successfully');
            return true;
        } else {
            console.warn('Supabase initialization skipped:', {
                libraryLoaded: typeof window.supabase !== 'undefined',
                urlSet: SUPABASE_CONFIG.url !== 'YOUR_SUPABASE_URL',
                anonKeySet: SUPABASE_CONFIG.anonKey !== 'YOUR_SUPABASE_ANON_KEY',
                actualUrl: SUPABASE_CONFIG.url,
                actualAnonKey: SUPABASE_CONFIG.anonKey ? SUPABASE_CONFIG.anonKey.substring(0, 20) + '...' : 'NOT SET'
            });
            return false;
        }
    } catch (e) {
        console.error('Failed to initialize Supabase:', e);
        return false;
    }
}

// DOM Elements
const loginTab = document.getElementById('loginTab');
const signupTab = document.getElementById('signupTab');
const loginForm = document.getElementById('loginForm');
const signupForm = document.getElementById('signupForm');
const loginEmail = document.getElementById('loginEmail');
const loginPassword = document.getElementById('loginPassword');
const signupEmail = document.getElementById('signupEmail');
const signupPassword = document.getElementById('signupPassword');
const confirmPassword = document.getElementById('confirmPassword');
const loginBtn = document.getElementById('loginBtn');
const signupBtn = document.getElementById('signupBtn');
const loginError = document.getElementById('loginError');
const signupError = document.getElementById('signupError');
const signupSuccess = document.getElementById('signupSuccess');
const loadingOverlay = document.getElementById('loadingOverlay');
const switchToSignup = document.getElementById('switchToSignup');
const switchToLogin = document.getElementById('switchToLogin');
const footerSwitchToSignup = document.getElementById('footerSwitchToSignup');
const footerSwitchToLogin = document.getElementById('footerSwitchToLogin');
const testUserButtons = document.querySelectorAll('.test-user-btn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Small delay to ensure config.js and Supabase library have finished loading
    setTimeout(() => {
        // Initialize Supabase client (config.js should be loaded by now)
        const initialized = initializeSupabase();
        
        if (!initialized) {
            console.error('Supabase client not initialized. Check config.js and browser console.');
            showConfigError();
        } else {
            console.log('Supabase ready for authentication');
            
            // Check if already logged in
            checkExistingSession();
        }
        
        // Setup event listeners (always do this, even if Supabase not initialized)
        setupEventListeners();
    }, 100); // 100ms delay to ensure scripts have loaded
});

function setupEventListeners() {
    // Tab switching
    loginTab.addEventListener('click', () => switchTab('login'));
    signupTab.addEventListener('click', () => switchTab('signup'));
    switchToSignup?.addEventListener('click', (e) => {
        e.preventDefault();
        switchTab('signup');
    });
    switchToLogin?.addEventListener('click', (e) => {
        e.preventDefault();
        switchTab('login');
    });
    
    // Form submissions
    loginForm.addEventListener('submit', handleLogin);
    signupForm.addEventListener('submit', handleSignup);
    
    // Test user buttons
    testUserButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const email = btn.dataset.email;
            const password = btn.dataset.password;
            loginEmail.value = email;
            loginPassword.value = password;
            switchTab('login');
            handleLogin(new Event('submit'));
        });
    });
    
    // Forgot password
    document.getElementById('forgotPassword')?.addEventListener('click', (e) => {
        e.preventDefault();
        alert('Password reset functionality coming soon! For now, please contact support.');
    });
}

function switchTab(tab) {
    if (tab === 'login') {
        loginTab.classList.add('active');
        signupTab.classList.remove('active');
        loginForm.classList.add('active');
        signupForm.classList.remove('active');
        footerSwitchToSignup.style.display = 'block';
        footerSwitchToLogin.style.display = 'none';
    } else {
        loginTab.classList.remove('active');
        signupTab.classList.add('active');
        loginForm.classList.remove('active');
        signupForm.classList.add('active');
        footerSwitchToSignup.style.display = 'none';
        footerSwitchToLogin.style.display = 'block';
    }
    
    // Clear errors
    hideError('login');
    hideError('signup');
    hideSuccess();
}

async function handleLogin(e) {
    e.preventDefault();
    
    const email = loginEmail.value.trim();
    const password = loginPassword.value;
    
    if (!email || !password) {
        showError('login', 'Please enter both email and password');
        return;
    }
    
    if (!supabase) {
        console.error('Supabase client not initialized. Config:', SUPABASE_CONFIG);
        showError('login', 'Authentication service not configured. Please check your Supabase settings.');
        return;
    }
    
    setLoading(true);
    hideError('login');
    
    try {
        console.log('Attempting login for:', email);
        const { data, error } = await supabase.auth.signInWithPassword({
            email,
            password
        });
        
        if (error) {
            console.error('Supabase auth error:', error);
            throw error;
        }
        
        console.log('Login successful, session:', data.session ? 'received' : 'missing');
        
        if (data.session) {
            // Store session
            localStorage.setItem('supabase_session', JSON.stringify(data.session));
            localStorage.setItem('supabase_access_token', data.session.access_token);
            console.log('Session stored, redirecting to product page...');
            
            // Redirect to product page
            window.location.href = 'product.html';
        } else {
            throw new Error('No session received from Supabase');
        }
    } catch (error) {
        console.error('Login error:', error);
        showError('login', error.message || 'Failed to sign in. Please check your credentials.');
    } finally {
        setLoading(false);
    }
}

async function handleSignup(e) {
    e.preventDefault();
    
    const email = signupEmail.value.trim();
    const password = signupPassword.value;
    const confirm = confirmPassword.value;
    
    if (!email || !password || !confirm) {
        showError('signup', 'Please fill in all fields');
        return;
    }
    
    if (password.length < 6) {
        showError('signup', 'Password must be at least 6 characters');
        return;
    }
    
    if (password !== confirm) {
        showError('signup', 'Passwords do not match');
        return;
    }
    
    if (!supabase) {
        showError('signup', 'Authentication service not configured. Please check your Supabase settings.');
        return;
    }
    
    setLoading(true);
    hideError('signup');
    hideSuccess();
    
    try {
        const { data, error } = await supabase.auth.signUp({
            email,
            password
        });
        
        if (error) {
            throw error;
        }
        
        if (data.user) {
            // Check if email confirmation is required
            if (data.session) {
                // No email confirmation needed - auto sign in
                localStorage.setItem('supabase_session', JSON.stringify(data.session));
                localStorage.setItem('supabase_access_token', data.session.access_token);
                showSuccess('Account created! Redirecting...');
                setTimeout(() => {
                    window.location.href = 'product.html';
                }, 1500);
            } else {
                // Email confirmation required
                showSuccess('Account created! Please check your email to confirm your account.');
            }
        } else {
            throw new Error('Failed to create account');
        }
    } catch (error) {
        console.error('Signup error:', error);
        showError('signup', error.message || 'Failed to create account. Please try again.');
    } finally {
        setLoading(false);
    }
}

async function checkExistingSession() {
    if (!supabase) return;
    
    try {
        const sessionStr = localStorage.getItem('supabase_session');
        if (sessionStr) {
            const session = JSON.parse(sessionStr);
            // Check if session is still valid
            const { data: { user } } = await supabase.auth.getUser(session.access_token);
            if (user) {
                // Session is valid, redirect to product
                window.location.href = 'product.html';
            } else {
                // Session expired, clear it
                localStorage.removeItem('supabase_session');
                localStorage.removeItem('supabase_access_token');
            }
        }
    } catch (error) {
        // Session invalid, clear it
        localStorage.removeItem('supabase_session');
        localStorage.removeItem('supabase_access_token');
    }
}

function showError(form, message) {
    const errorEl = form === 'login' ? loginError : signupError;
    errorEl.textContent = message;
    errorEl.style.display = 'block';
}

function hideError(form) {
    const errorEl = form === 'login' ? loginError : signupError;
    errorEl.style.display = 'none';
}

function showSuccess(message) {
    signupSuccess.textContent = message;
    signupSuccess.style.display = 'block';
}

function hideSuccess() {
    signupSuccess.style.display = 'none';
}

function setLoading(loading) {
    if (loading) {
        loadingOverlay.classList.add('show');
        loginBtn.disabled = true;
        signupBtn.disabled = true;
        loginBtn.querySelector('.btn-text').style.display = 'none';
        loginBtn.querySelector('.btn-loader').style.display = 'inline-block';
        signupBtn.querySelector('.btn-text').style.display = 'none';
        signupBtn.querySelector('.btn-loader').style.display = 'inline-block';
    } else {
        loadingOverlay.classList.remove('show');
        loginBtn.disabled = false;
        signupBtn.disabled = false;
        loginBtn.querySelector('.btn-text').style.display = 'inline';
        loginBtn.querySelector('.btn-loader').style.display = 'none';
        signupBtn.querySelector('.btn-text').style.display = 'inline';
        signupBtn.querySelector('.btn-loader').style.display = 'none';
    }
}

function showConfigError() {
    const errorMsg = document.createElement('div');
    errorMsg.className = 'error-message';
    errorMsg.style.cssText = 'margin: 1rem 0; padding: 1rem; background: rgba(239, 68, 68, 0.1); border: 1px solid var(--accent-danger); border-radius: 0.5rem; color: var(--accent-danger);';
    errorMsg.innerHTML = `
        <strong>Configuration Error:</strong><br>
        Supabase is not configured. Please add the following to your HTML before the login.js script:<br>
        <code style="font-size: 0.75rem; background: rgba(0,0,0,0.3); padding: 0.25rem 0.5rem; border-radius: 0.25rem;">
        &lt;script&gt;<br>
        &nbsp;&nbsp;window.SUPABASE_URL = 'your-supabase-url';<br>
        &nbsp;&nbsp;window.SUPABASE_ANON_KEY = 'your-anon-key';<br>
        &lt;/script&gt;
        </code>
    `;
    document.querySelector('.form-card').insertBefore(errorMsg, document.querySelector('.tab-switcher'));
}

})(); // End of IIFE - prevents variable conflicts

