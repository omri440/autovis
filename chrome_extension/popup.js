// API Configuration
const API_URL = 'http://localhost:5001/api/convert';
const CONFIG_URL = 'http://localhost:5001/api/config';

// DOM Elements
const elements = {
    pythonInput: document.getElementById('pythonInput'),
    convertBtn: document.getElementById('convertBtn'),
    clearBtn: document.getElementById('clearBtn'),
    exampleBtn: document.getElementById('exampleBtn'),
    copyBtn: document.getElementById('copyBtn'),
    downloadBtn: document.getElementById('downloadBtn'),
    jsOutput: document.getElementById('jsOutput'),
    outputSection: document.getElementById('outputSection'),
    errorSection: document.getElementById('errorSection'),
    errorMessage: document.getElementById('errorMessage'),
    loadingSpinner: document.getElementById('loadingSpinner'),
    loadingText: document.getElementById('loadingText'),
    statusIndicator: document.getElementById('statusIndicator'),
    lineCount: document.getElementById('lineCount'),
    charCount: document.getElementById('charCount'),
    outputLineCount: document.getElementById('outputLineCount'),
    analysisInfo: document.getElementById('analysisInfo'),
    arrays1d: document.getElementById('arrays1d'),
    arrays2d: document.getElementById('arrays2d'),
    vizType: document.getElementById('vizType'),
    hasSorting: document.getElementById('hasSorting'),
    aiToggle: document.getElementById('aiToggle'),
    providerSelect: document.getElementById('providerSelect'),
    aiOptions: document.getElementById('aiOptions'),
    polishInfo: document.getElementById('polishInfo'),
    polishStatus: document.getElementById('polishStatus'),
    improvementText: document.getElementById('improvementText')
};

// Example algorithms
const EXAMPLES = {
    bubbleSort: `def bubbleSort(arr):
    n = len(arr)
    for i in range(n - 1):
        for j in range(n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr`,

    binarySearch: `def binarySearch(arr, target):
    left = 0
    right = len(arr) - 1

    while left <= right:
        mid = (left + right) // 2

        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1`,

    twoSum: `def twoSum(nums, target):
    hashmap = {}
    for i in range(len(nums)):
        complement = target - nums[i]
        if complement in hashmap:
            return [hashmap[complement], i]
        hashmap[nums[i]] = i
    return []`
};

let currentExampleIndex = 0;
const exampleKeys = Object.keys(EXAMPLES);

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadSavedInput();
    loadAISettings();
    updateStats();
    checkServerStatus();
    attachEventListeners();
});

// Event Listeners
function attachEventListeners() {
    elements.pythonInput.addEventListener('input', handleInputChange);
    elements.convertBtn.addEventListener('click', handleConvert);
    elements.clearBtn.addEventListener('click', handleClear);
    elements.exampleBtn.addEventListener('click', handleExample);
    elements.copyBtn.addEventListener('click', handleCopy);
    elements.downloadBtn.addEventListener('click', handleDownload);
    elements.aiToggle.addEventListener('change', handleAIToggle);
    elements.providerSelect.addEventListener('change', handleProviderChange);
}

// AI Settings Management
function handleAIToggle() {
    const enabled = elements.aiToggle.checked;
    elements.aiOptions.style.display = enabled ? 'block' : 'none';
    saveAISettings();

    if (enabled) {
        showNotification('AI polishing enabled');
    } else {
        showNotification('AI polishing disabled');
    }
}

function handleProviderChange() {
    saveAISettings();
    const provider = elements.providerSelect.value;
    showNotification(`Switched to ${getProviderName(provider)}`);
}

function getProviderName(provider) {
    const names = {
        'claude': 'Claude (Anthropic)',
        'openai': 'GPT-4 (OpenAI)',
        'local': 'Local LLM (Ollama)'
    };
    return names[provider] || provider;
}

function saveAISettings() {
    const settings = {
        enabled: elements.aiToggle.checked,
        provider: elements.providerSelect.value
    };
    chrome.storage.local.set({ aiSettings: settings });
}

function loadAISettings() {
    chrome.storage.local.get(['aiSettings'], (result) => {
        if (result.aiSettings) {
            elements.aiToggle.checked = result.aiSettings.enabled;
            elements.providerSelect.value = result.aiSettings.provider;
            elements.aiOptions.style.display = result.aiSettings.enabled ? 'block' : 'none';
        }
    });
}

// Input change handler
function handleInputChange() {
    updateStats();
    saveInput();
}

// Update statistics
function updateStats() {
    const code = elements.pythonInput.value;
    const lines = code.split('\n').length;
    const chars = code.length;

    elements.lineCount.textContent = `Lines: ${lines}`;
    elements.charCount.textContent = `Characters: ${chars}`;
}

// Save input to storage
function saveInput() {
    chrome.storage.local.set({ pythonCode: elements.pythonInput.value });
}

// Load saved input
function loadSavedInput() {
    chrome.storage.local.get(['pythonCode'], (result) => {
        if (result.pythonCode) {
            elements.pythonInput.value = result.pythonCode;
            updateStats();
        }
    });
}

// Clear input
function handleClear() {
    elements.pythonInput.value = '';
    elements.outputSection.style.display = 'none';
    elements.errorSection.style.display = 'none';
    elements.analysisInfo.style.display = 'none';
    elements.polishInfo.style.display = 'none';
    updateStats();
    saveInput();
}

// Load example
function handleExample() {
    const exampleKey = exampleKeys[currentExampleIndex];
    elements.pythonInput.value = EXAMPLES[exampleKey];

    currentExampleIndex = (currentExampleIndex + 1) % exampleKeys.length;

    updateStats();
    saveInput();
    showNotification(`Loaded: ${formatExampleName(exampleKey)}`);
}

// Format example name
function formatExampleName(key) {
    return key.replace(/([A-Z])/g, ' $1').trim();
}

// Check server status
async function checkServerStatus() {
    try {
        const response = await fetch('http://localhost:5001/health', {
            method: 'GET',
            mode: 'cors'
        });

        if (response.ok) {
            const data = await response.json();
            updateStatus('connected', 'Server Connected');

            // Update AI status in UI if available
            if (data.ai_polish_enabled) {
                console.log(`AI Polishing: ${data.ai_provider}`);
            }
        } else {
            updateStatus('warning', 'Server Issue');
        }
    } catch (error) {
        updateStatus('disconnected', 'Server Offline');
    }
}

// Update status indicator
function updateStatus(status, text) {
    const statusDot = elements.statusIndicator.querySelector('.status-dot');
    const statusText = elements.statusIndicator.querySelector('.status-text');

    statusDot.className = 'status-dot';
    statusText.textContent = text;

    const colors = {
        connected: '#10b981',
        warning: '#f59e0b',
        disconnected: '#ef4444'
    };

    statusDot.style.background = colors[status] || colors.disconnected;
}

// Handle conversion
async function handleConvert() {
    const code = elements.pythonInput.value.trim();

    if (!code) {
        showError('Please enter Python code to convert');
        return;
    }

    // Hide previous results
    elements.outputSection.style.display = 'none';
    elements.errorSection.style.display = 'none';
    elements.analysisInfo.style.display = 'none';
    elements.polishInfo.style.display = 'none';

    // Show loading
    elements.convertBtn.style.display = 'none';
    elements.loadingSpinner.classList.add('active');

    // Update loading text based on AI settings
    const aiEnabled = elements.aiToggle.checked;
    if (aiEnabled) {
        elements.loadingText.textContent = 'Processing with AI...';
    } else {
        elements.loadingText.textContent = 'Processing...';
    }

    try {
        const requestBody = {
            code: code,
            enable_polish: elements.aiToggle.checked,
            polish_provider: elements.providerSelect.value
        };

        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Conversion failed');
        }

        // Display results
        displayResults(data);

    } catch (error) {
        console.error('Conversion error:', error);
        showError(error.message || 'Failed to connect to server. Make sure the Python server is running on localhost:5001');
    } finally {
        // Hide loading
        elements.loadingSpinner.classList.remove('active');
        elements.convertBtn.style.display = 'block';
    }
}

// Display results
function displayResults(data) {
    // Show output
    elements.jsOutput.textContent = data.javascript;
    elements.outputSection.style.display = 'block';

    // Update line count
    const lines = data.javascript.split('\n').length;
    elements.outputLineCount.textContent = `Lines: ${lines}`;

    // Show analysis info
    if (data.analysis) {
        displayAnalysis(data.analysis);
    }

    // Show polishing info if available
    if (data.polishing) {
        displayPolishingInfo(data.polishing);
    }

    // Scroll to output
    elements.outputSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Display analysis
function displayAnalysis(analysis) {
    elements.arrays1d.textContent = analysis.vars_1d?.join(', ') || 'None';
    elements.arrays2d.textContent = analysis.vars_2d?.join(', ') || 'None';
    elements.vizType.textContent = analysis.viz_type || 'Unknown';
    elements.hasSorting.textContent = analysis.has_sorting ? 'Yes' : 'No';

    elements.analysisInfo.style.display = 'block';
}

// Display polishing info
function displayPolishingInfo(polishing) {
    if (!polishing.enabled) {
        elements.polishInfo.style.display = 'none';
        return;
    }

    if (polishing.was_polished) {
        elements.polishStatus.textContent = `AI Enhanced with ${getProviderName(polishing.provider)}`;

        // Show improvements if available
        if (polishing.improvements) {
            const imp = polishing.improvements;
            const changes = [];

            if (imp.polished_logger_calls > imp.original_logger_calls) {
                changes.push(`+${imp.polished_logger_calls - imp.original_logger_calls} log messages`);
            }
            if (imp.polished_comments > imp.original_comments) {
                changes.push(`+${imp.polished_comments - imp.original_comments} comments`);
            }

            if (changes.length > 0) {
                elements.improvementText.textContent = `Improvements: ${changes.join(', ')}`;
            } else {
                elements.improvementText.textContent = 'Code refined and optimized';
            }
        } else {
            elements.improvementText.textContent = 'Code refined by AI';
        }

        elements.polishInfo.style.display = 'block';
    } else {
        elements.polishInfo.style.display = 'none';
    }
}

// Show error
function showError(message) {
    elements.errorMessage.textContent = message;
    elements.errorSection.style.display = 'block';
    elements.errorSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Copy to clipboard
async function handleCopy() {
    const code = elements.jsOutput.textContent;

    try {
        await navigator.clipboard.writeText(code);
        showNotification('Copied to clipboard!');

        // Visual feedback
        elements.copyBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
            </svg>
            Copied!
        `;

        setTimeout(() => {
            elements.copyBtn.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                    <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
                </svg>
                Copy
            `;
        }, 2000);

    } catch (error) {
        showError('Failed to copy to clipboard');
    }
}

// Download JavaScript file
function handleDownload() {
    const code = elements.jsOutput.textContent;
    const filename = 'algorithm.js';

    const blob = new Blob([code], { type: 'text/javascript' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showNotification('Downloaded: ' + filename);
}

// Show notification
function showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--success);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }

    .ai-settings {
        margin-bottom: 16px;
    }

    .toggle-switch {
        position: relative;
        display: inline-block;
        width: 44px;
        height: 24px;
    }

    .toggle-switch input {
        opacity: 0;
        width: 0;
        height: 0;
    }

    .toggle-switch label {
        position: absolute;
        cursor: pointer;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: var(--bg-tertiary);
        transition: 0.3s;
        border-radius: 24px;
    }

    .toggle-switch label:before {
        position: absolute;
        content: "";
        height: 18px;
        width: 18px;
        left: 3px;
        bottom: 3px;
        background-color: white;
        transition: 0.3s;
        border-radius: 50%;
    }

    .toggle-switch input:checked + label {
        background-color: var(--primary);
    }

    .toggle-switch input:checked + label:before {
        transform: translateX(20px);
    }

    .ai-options {
        padding: 16px 20px;
        display: none;
    }

    .option-group {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 12px;
    }

    .option-group label {
        font-size: 13px;
        font-weight: 600;
        color: var(--text-secondary);
    }

    .provider-select {
        flex: 1;
        padding: 8px 12px;
        background: var(--code-bg);
        color: var(--text-primary);
        border: 1px solid var(--border);
        border-radius: 6px;
        font-size: 13px;
        font-family: inherit;
        cursor: pointer;
    }

    .ai-description {
        font-size: 12px;
        color: var(--text-muted);
        line-height: 1.5;
    }

    .polish-info {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid var(--success);
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 16px;
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .polish-badge {
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--success);
        font-weight: 600;
        font-size: 13px;
    }

    .polish-improvements {
        font-size: 12px;
        color: var(--text-secondary);
    }
`;
document.head.appendChild(style);