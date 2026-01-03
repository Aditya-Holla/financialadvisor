// Product Page JavaScript - Chat Interface
// Wrapped in IIFE to avoid variable conflicts

(function() {
    'use strict';

    // API Configuration
    // Load from config.js if available, otherwise use default
    const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

    // Supabase Configuration - will be read when DOM is ready
    let SUPABASE_CONFIG = null;
    let supabase = null;
    let currentSession = null;

    // Function to initialize Supabase client
    function initializeSupabase() {
        SUPABASE_CONFIG = {
            url: window.SUPABASE_URL || 'YOUR_SUPABASE_URL',
            anonKey: window.SUPABASE_ANON_KEY || 'YOUR_SUPABASE_ANON_KEY'
        };
        
        console.log('Product page - Reading config:', {
            url: SUPABASE_CONFIG.url,
            anonKeySet: SUPABASE_CONFIG.anonKey !== 'YOUR_SUPABASE_ANON_KEY',
            supabaseLib: typeof window.supabase !== 'undefined',
            windowUrl: window.SUPABASE_URL,
            windowAnonKey: window.SUPABASE_ANON_KEY ? 'Set' : 'Not set'
        });
        
        try {
            if (typeof window.supabase !== 'undefined' && SUPABASE_CONFIG.url !== 'YOUR_SUPABASE_URL' && SUPABASE_CONFIG.anonKey !== 'YOUR_SUPABASE_ANON_KEY') {
                supabase = window.supabase.createClient(SUPABASE_CONFIG.url, SUPABASE_CONFIG.anonKey);
                console.log('✓ Product page - Supabase client initialized successfully');
                return true;
            } else {
                console.warn('Product page - Supabase initialization skipped:', {
                    libraryLoaded: typeof window.supabase !== 'undefined',
                    urlSet: SUPABASE_CONFIG.url !== 'YOUR_SUPABASE_URL',
                    anonKeySet: SUPABASE_CONFIG.anonKey !== 'YOUR_SUPABASE_ANON_KEY'
                });
                return false;
            }
        } catch (e) {
            console.error('Failed to initialize Supabase:', e);
            return false;
        }
    }

    // State
    let messageHistory = [];

    // DOM Elements
    const messagesContainer = document.getElementById('messagesContainer');
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const clearChatBtn = document.getElementById('clearChatBtn');
    const switchUserBtn = document.getElementById('switchUserBtn');
    const sidebar = document.getElementById('sidebar');
    const closeSidebarBtn = document.getElementById('closeSidebarBtn');
    const userEmail = document.getElementById('userEmail');

    // Initialize
    document.addEventListener('DOMContentLoaded', async () => {
        // Small delay to ensure config.js has loaded
        setTimeout(async () => {
            // Initialize Supabase client
            const initialized = initializeSupabase();
            
            if (!initialized) {
                console.error('Supabase client not initialized. Check config.js and browser console.');
                // Still try to check auth, but it will redirect to login
            }
            
            // Check authentication
            await checkAuth();
            
            // Load message history from localStorage
            loadMessageHistory();

            // Setup event listeners
            setupEventListeners();
        }, 100); // 100ms delay
    });

async function checkAuth() {
    if (!supabase) {
        // Redirect to login if Supabase not configured
        window.location.href = 'login.html';
        return;
    }
    
    try {
        // Use Supabase's built-in session management
        const { data: { session }, error } = await supabase.auth.getSession();
        
        if (error) {
            console.error('Session check error:', error);
            throw error;
        }
        
        if (session && session.access_token) {
            // Store session for API calls
            currentSession = session;
            localStorage.setItem('supabase_session', JSON.stringify(session));
            localStorage.setItem('supabase_access_token', session.access_token);
            
            // Get user info
            const { data: { user } } = await supabase.auth.getUser();
            if (userEmail) {
                userEmail.textContent = user?.email || 'Online';
            }
            
            console.log('✓ Session validated, user:', user?.email);
            return;
        }
        
        // No valid session - redirect to login
        console.warn('No valid session found, redirecting to login');
        window.location.href = 'login.html';
    } catch (error) {
        console.error('Auth check error:', error);
        window.location.href = 'login.html';
    }
}

function setupEventListeners() {
    // Send button
    sendButton.addEventListener('click', sendMessage);
    
    // Enter key to send, Shift+Enter for new line
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendButton.disabled) {
                sendMessage();
            }
        }
    });

    // Enable/disable send button based on input
    messageInput.addEventListener('input', () => {
        sendButton.disabled = messageInput.value.trim().length === 0;
    });

    // Clear chat
    clearChatBtn.addEventListener('click', clearChat);

    // Switch user
    switchUserBtn.addEventListener('click', switchUser);

    // Close sidebar
    closeSidebarBtn?.addEventListener('click', () => {
        sidebar.classList.remove('open');
    });
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message || !currentSession) {
        if (!currentSession) {
            window.location.href = 'login.html';
        }
        return;
    }

    // Clear input
    messageInput.value = '';
    sendButton.disabled = true;

    // Add user message to UI
    addMessage('user', message);

    // Show typing indicator
    const typingId = showTypingIndicator();

    // Show loading overlay
    showLoading();

    try {
        // Check if user wants to generate a recommendation
        const messageLower = message.toLowerCase();
        const wantsRecommendation = messageLower.includes('generate') || 
                                   messageLower.includes('recommendation') ||
                                   messageLower.includes('invest') ||
                                   messageLower.includes('i want to invest') ||
                                   messageLower.includes('create') ||
                                   messageLower.includes('new recommendation');
        
        let recommendationId = null;
        
        // If user wants a recommendation, generate one first
        if (wantsRecommendation) {
            try {
                // Extract amount if mentioned (e.g., "invest $5000" or "invest 5000")
                const amountMatch = message.match(/\$?([\d,]+(?:\.\d{2})?)/);
                const amount = amountMatch ? parseFloat(amountMatch[1].replace(/,/g, '')) : null;
                
                const generateResponse = await fetch(`${API_BASE_URL}/recommendations/generate`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${currentSession.access_token}`
                    },
                    body: JSON.stringify({
                        type: 'invest',
                        amount: amount,
                        timeframe: 'immediate'
                    })
                });
                
                if (generateResponse.ok) {
                    const generateData = await generateResponse.json();
                    recommendationId = generateData.recommendation_id;
                    console.log('Generated recommendation:', recommendationId);
                } else {
                    const errorData = await generateResponse.json();
                    // Better error message extraction
                    let errorMessage = 'Failed to generate recommendation';
                    if (errorData.message) {
                        errorMessage = errorData.message;
                    } else if (errorData.code) {
                        errorMessage = `${errorData.code}: ${errorData.message || 'Unknown error'}`;
                    } else if (errorData.detail) {
                        errorMessage = errorData.detail;
                    }
                    throw new Error(errorMessage);
                }
            } catch (error) {
                console.error('Error generating recommendation:', error);
                removeTypingIndicator(typingId);
                hideLoading();
                sendButton.disabled = false;
                addMessage('advisor', `I encountered an error generating a recommendation: ${error.message}. Please try again or check if you have a profile set up.`, {
                    type: 'error'
                });
                return;
            }
        }
        
        // Call chat endpoint to get explanation
        // Use the newly generated recommendation ID, or get latest if none
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${currentSession.access_token}`
            },
            body: JSON.stringify({
                recommendation_id: recommendationId || null
            })
        });

        if (!response.ok) {
            if (response.status === 401) {
                // Session expired - redirect to login
                localStorage.removeItem('supabase_session');
                localStorage.removeItem('supabase_access_token');
                window.location.href = 'login.html';
                throw new Error('Authentication required');
            }
            const errorData = await response.json();
            // Better error message extraction
            let errorMessage = 'Failed to get response';
            if (errorData.message) {
                errorMessage = errorData.message;
            } else if (errorData.code) {
                errorMessage = `${errorData.code}: ${errorData.message || 'Unknown error'}`;
            } else if (errorData.detail) {
                errorMessage = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
            }
            throw new Error(errorMessage);
        }

        const data = await response.json();

        // Remove typing indicator
        removeTypingIndicator(typingId);

        // Backend returns { explanation: "..." } format
        // Check if it's the new format (explanation) or old format (message)
        const advisorMessage = data.explanation || data.message || 'I received your message.';
        const responseType = data.type || 'conversation';
        const isBlocked = data.data?.blocked || false;

        addMessage('advisor', advisorMessage, {
            type: responseType,
            blocked: isBlocked,
            recommendationId: data.recommendation_id,
            data: data.data
        });

        // If it's a recommendation, show sidebar
        if (responseType === 'recommendation' && data.recommendation_id) {
            showRecommendationDetails(data);
        }

    } catch (error) {
        console.error('Error sending message:', error);
        removeTypingIndicator(typingId);
        addMessage('advisor', `I'm sorry, I encountered an error: ${error.message}. Please try again.`, {
            type: 'error'
        });
        showToast('Error: ' + error.message, 'error');
    } finally {
        hideLoading();
        sendButton.disabled = false;
    }
}

function addMessage(role, text, metadata = {}) {
    // Remove welcome message if it exists
    const welcomeMsg = messagesContainer.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.dataset.timestamp = new Date().toISOString();

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? '👤' : '🤖';

    const content = document.createElement('div');
    content.className = 'message-content';

    const textDiv = document.createElement('p');
    textDiv.className = 'message-text';
    textDiv.textContent = text;

    content.appendChild(textDiv);

    // Add metadata if available
    if (metadata.type) {
        const metaDiv = document.createElement('div');
        metaDiv.className = 'message-meta';
        
        const badge = document.createElement('span');
        badge.className = `message-type-badge ${metadata.type}`;
        badge.textContent = metadata.blocked ? 'Blocked' : metadata.type;
        metaDiv.appendChild(badge);

        if (metadata.recommendationId) {
            const recLink = document.createElement('span');
            recLink.textContent = `ID: ${metadata.recommendationId.substring(0, 8)}...`;
            metaDiv.appendChild(recLink);
        }

        content.appendChild(metaDiv);
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);

    messagesContainer.appendChild(messageDiv);
    scrollToBottom();

    // Save to history
    messageHistory.push({
        role,
        text,
        metadata,
        timestamp: new Date().toISOString()
    });
    saveMessageHistory();
}

function showTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message advisor';
    typingDiv.id = 'typing-indicator';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = '🤖';
    
    const content = document.createElement('div');
    content.className = 'typing-indicator';
    content.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
    
    typingDiv.appendChild(avatar);
    typingDiv.appendChild(content);
    messagesContainer.appendChild(typingDiv);
    scrollToBottom();
    
    return 'typing-indicator';
}

function removeTypingIndicator(id) {
    const indicator = document.getElementById(id);
    if (indicator) {
        indicator.remove();
    }
}

function showRecommendationDetails(data) {
    const sidebarContent = document.getElementById('sidebarContent');
    sidebarContent.innerHTML = '';

    if (data.recommendation_id) {
        const card = document.createElement('div');
        card.className = 'recommendation-card';
        
        card.innerHTML = `
            <h4>Recommendation Details</h4>
            <div class="recommendation-detail">
                <strong>Status:</strong> ${data.data?.recommendation?.status || 'N/A'}
            </div>
            <div class="recommendation-detail">
                <strong>Decision:</strong> ${data.data?.recommendation?.decision || 'N/A'}
            </div>
            <div class="recommendation-detail">
                <strong>ID:</strong> ${data.recommendation_id.substring(0, 20)}...
            </div>
        `;
        
        sidebarContent.appendChild(card);
        sidebar.classList.add('open');
    }
}

function switchUser() {
    if (confirm('Switch to a different user? This will log you out and clear your chat history.')) {
        // Sign out from Supabase
        if (supabase) {
            supabase.auth.signOut();
        }
        
        // Clear session and message history
        localStorage.removeItem('supabase_session');
        localStorage.removeItem('supabase_access_token');
        localStorage.removeItem('messageHistory');
        
        // Reset state
        currentSession = null;
        messageHistory = [];
        
        // Redirect to login
        window.location.href = 'login.html';
    }
}

function clearChat() {
    if (confirm('Are you sure you want to clear the chat history?')) {
        messagesContainer.innerHTML = '';
        messageHistory = [];
        localStorage.removeItem('messageHistory');
        
        // Show welcome message again
        const welcomeMsg = document.createElement('div');
        welcomeMsg.className = 'welcome-message';
        welcomeMsg.innerHTML = `
            <div class="welcome-content">
                <h3>Welcome! 👋</h3>
                <p>I'm your financial advisor. I can help you with:</p>
                <ul>
                    <li>💬 Answering financial questions</li>
                    <li>📊 Generating investment recommendations</li>
                    <li>🎓 Explaining financial concepts</li>
                    <li>🛡️ Understanding safety guardrails</li>
                </ul>
            </div>
        `;
        messagesContainer.appendChild(welcomeMsg);
        
        showToast('Chat cleared', 'success');
    }
}

function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function showLoading() {
    loadingOverlay.classList.add('show');
}

function hideLoading() {
    loadingOverlay.classList.remove('show');
}

function saveMessageHistory() {
    localStorage.setItem('messageHistory', JSON.stringify(messageHistory));
}

function loadMessageHistory() {
    const saved = localStorage.getItem('messageHistory');
    if (saved) {
        try {
            messageHistory = JSON.parse(saved);
            // Optionally restore messages to UI
            // For now, we'll just keep it in memory
        } catch (e) {
            console.error('Failed to load message history:', e);
        }
    }
}

function showToast(message, type = 'info') {
    // Simple toast notification
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        background: ${type === 'error' ? 'var(--accent-danger)' : 'var(--accent-success)'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        z-index: 3000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

})(); // End of IIFE - prevents variable conflicts

