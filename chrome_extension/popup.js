// API Configuration
const API_URL = 'http://localhost:5001/api/convert';

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
    statusIndicator: document.getElementById('statusIndicator'),
    lineCount: document.getElementById('lineCount'),
    charCount: document.getElementById('charCount'),
    outputLineCount: document.getElementById('outputLineCount'),
    analysisInfo: document.getElementById('analysisInfo'),
    arrays1d: document.getElementById('arrays1d'),
    arrays2d: document.getElementById('arrays2d'),
    vizType: document.getElementById('vizType'),
    hasSorting: document.getElementById('hasSorting')
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

// Current example index
let currentExampleIndex = 0;
const exampleKeys = Object.keys(EXAMPLES);

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadSavedInput();
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
    updateStats();
    saveInput();
}

// Load example
function handleExample() {
    const exampleKey = exampleKeys[currentExampleIndex];
    elements.pythonInput.value = EXAMPLES[exampleKey];

    // Cycle to next example
    currentExampleIndex = (currentExampleIndex + 1) % exampleKeys.length;

    updateStats();
    saveInput();

    // Show notification
    showNotification(`Loaded: ${formatExampleName(exampleKey)}`);
}

// Format example name
function formatExampleName(key) {
    return key.replace(/([A-Z])/g, ' $1').trim();
}

// Check server status
async function checkServerStatus() {
    try {
        const response = await fetch('http://localhost:5000/health', {
            method: 'GET',
            mode: 'cors'
        });

        if (response.ok) {
            updateStatus('connected', 'Server Connected');
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

    // Show loading
    elements.convertBtn.style.display = 'none';
    elements.loadingSpinner.classList.add('active');

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ code })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Conversion failed');
        }

        // Display results
        displayResults(data);

    } catch (error) {
        console.error('Conversion error:', error);
        showError(error.message || 'Failed to connect to server. Make sure the Python server is running on localhost:5000');
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

    // Show analysis info if available
    if (data.analysis) {
        displayAnalysis(data.analysis);
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
    // Create notification element
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

    // Remove after 3 seconds
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
`;
document.head.appendChild(style);