// API configuration
const API_BASE_URL = 'http://localhost:8000';

// State management
const state = {
    selectedFile: null,
    currentJobId: null,
    isDarkMode: localStorage.getItem('theme') === 'dark',
};

// DOM Elements
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const analyzeBtn = document.getElementById('analyzeBtn');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const changeFileBtn = document.getElementById('changeFile');
const themeToggle = document.getElementById('themeToggle');
const statusSection = document.getElementById('statusSection');
const resultsSection = document.getElementById('resultsSection');
const historySection = document.getElementById('historySection');
const uploadSection = document.querySelector('.upload-section');
const errorToast = document.getElementById('errorToast');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeTheme();
    setupEventListeners();
    loadHistory();
});

// Theme Management
function initializeTheme() {
    document.documentElement.setAttribute('data-theme', state.isDarkMode ? 'dark' : 'light');
    updateThemeToggle();
}

function updateThemeToggle() {
    themeToggle.textContent = state.isDarkMode ? '☀️' : '🌙';
}

themeToggle.addEventListener('click', () => {
    state.isDarkMode = !state.isDarkMode;
    localStorage.setItem('theme', state.isDarkMode ? 'dark' : 'light');
    initializeTheme();
});

// Event Listeners
function setupEventListeners() {
    // Drag and drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.parentElement.classList.add('drag-over');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.parentElement.classList.remove('drag-over');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.parentElement.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            selectFile(files[0]);
        }
    });

    // File input
    uploadZone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            selectFile(e.target.files[0]);
        }
    });

    // Change file button
    changeFileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    // Analyze button
    analyzeBtn.addEventListener('click', analyzeFile);

    // Result actions
    document.getElementById('newAnalysisBtn')?.addEventListener('click', resetUI);
    document.getElementById('copyResultsBtn')?.addEventListener('click', copyResults);
    document.getElementById('downloadResultsBtn')?.addEventListener('click', downloadResults);
    document.getElementById('refreshHistory')?.addEventListener('click', loadHistory);
}

// File Selection
function selectFile(file) {
    // Validate file
    const validExtensions = ['.log', '.txt', '.json'];
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();

    if (!validExtensions.includes(fileExt)) {
        showError('Invalid file type. Please upload .log, .txt, or .json files.');
        return;
    }

    state.selectedFile = file;
    fileInput.files = new DataTransfer().items.add(file).files;

    // Update UI
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    uploadZone.style.display = 'none';
    fileInfo.style.display = 'flex';
    analyzeBtn.disabled = false;
}

// Analyze File
async function analyzeFile() {
    if (!state.selectedFile) {
        showError('Please select a file first.');
        return;
    }

    const formData = new FormData();
    formData.append('file', state.selectedFile);

    try {
        analyzeBtn.classList.add('loading');
        statusSection.style.display = 'block';
        resultsSection.style.display = 'none';

        const response = await fetch(`${API_BASE_URL}/analyze`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }

        const data = await response.json();
        state.currentJobId = data.job_id;

        // Simulate progress
        await simulateProgress();

        // Display results
        displayResults(data);
        statusSection.style.display = 'none';
        resultsSection.style.display = 'block';

        // Reload history
        loadHistory();
    } catch (error) {
        console.error('Analysis error:', error);
        showError(`Analysis failed: ${error.message}`);
        statusSection.style.display = 'none';
    } finally {
        analyzeBtn.classList.remove('loading');
    }
}

// Simulate Progress
async function simulateProgress() {
    return new Promise((resolve) => {
        setTimeout(resolve, 2000);
    });
}

// Display Results
function displayResults(data) {
    // Summary
    const summaryBadge = document.getElementById('summaryBadge');
    const summaryText = document.getElementById('summaryText');
    summaryBadge.textContent = 'Analysis Complete';
    summaryText.textContent = data.summary;

    // Issues
    const issuesList = document.getElementById('issuesList');
    const issuesCount = document.getElementById('issuesCount');
    issuesCount.textContent = data.issues.length;
    issuesCount.classList.toggle('error', data.issues.length > 0);

    if (data.issues.length > 0) {
        issuesList.innerHTML = data.issues.map((issue) => `
            <div class="issue-item ${issue.severity.toLowerCase() === 'critical' || issue.severity.toLowerCase() === 'error' ? 'error' : ''}">
                <div class="issue-header">
                    <div class="issue-title">
                        <span>${escapeHtml(issue.pattern_name)}</span>
                        <span class="severity-badge severity-${issue.severity.toLowerCase()}">${issue.severity}</span>
                    </div>
                </div>
                <div class="issue-meta">
                    <span>📊 Occurrences: <strong>${issue.count}</strong></span>
                    ${issue.first_seen ? `<span>⏱️ First: ${issue.first_seen}</span>` : ''}
                    ${issue.last_seen ? `<span>⏱️ Last: ${issue.last_seen}</span>` : ''}
                </div>
                ${issue.sample_messages && issue.sample_messages.length > 0 ? `
                    <div class="issue-samples">
                        <strong>Sample Messages:</strong>
                        ${issue.sample_messages.map((msg) => `
                            <div class="sample-message">${escapeHtml(msg)}</div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `).join('');
    } else {
        issuesList.innerHTML = '<p style="color: var(--text-secondary); text-align: center;">No issues detected! ✨</p>';
    }

    // Fixes
    const fixesList = document.getElementById('fixesList');
    const fixesCount = document.getElementById('fixesCount');
    fixesCount.textContent = data.suggested_fixes.length;
    fixesCount.classList.toggle('success', data.suggested_fixes.length > 0);

    if (data.suggested_fixes.length > 0) {
        fixesList.innerHTML = data.suggested_fixes.map((fix) => `
            <div class="fix-item">
                <div class="fix-issue-name">
                    <span>🔧 ${escapeHtml(fix.issue_name)}</span>
                </div>
                <p style="margin: 0.5rem 0; color: var(--text-primary);">${escapeHtml(fix.fix)}</p>
            </div>
        `).join('');
    } else {
        fixesList.innerHTML = '<p style="color: var(--text-secondary); text-align: center;">No fixes needed.</p>';
    }

    // Store full results for export
    window.lastResults = data;
}

// Load History
async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE_URL}/history`);
        if (!response.ok) throw new Error('Failed to fetch history');

        const jobs = await response.json();
        const historyList = document.getElementById('historyList');
        const historyEmpty = document.getElementById('historyEmpty');

        if (jobs.length === 0) {
            historyList.innerHTML = '';
            historyEmpty.style.display = 'block';
        } else {
            historyEmpty.style.display = 'none';
            historyList.innerHTML = jobs.map((job) => `
                <div class="history-item" onclick="loadPastAnalysis('${job.id}')">
                    <div class="history-filename">📄 ${escapeHtml(job.filename)}</div>
                    <div class="history-meta">
                        <div class="history-status">
                            ✓ ${job.status}
                        </div>
                        <div>${formatDate(job.created_at)}</div>
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('History error:', error);
    }
}

// Load Past Analysis
async function loadPastAnalysis(jobId) {
    try {
        const response = await fetch(`${API_BASE_URL}/results/${jobId}`);
        if (!response.ok) throw new Error('Failed to load analysis');

        const data = await response.json();
        uploadSection.scrollIntoView({ behavior: 'smooth' });
        displayResults(data);
        statusSection.style.display = 'none';
        resultsSection.style.display = 'block';
    } catch (error) {
        console.error('Load analysis error:', error);
        showError(`Failed to load analysis: ${error.message}`);
    }
}

// Export Functions
function copyResults() {
    if (!window.lastResults) return;

    const text =
        `LogInsight AI - Analysis Report\n` +
        `${'='.repeat(50)}\n\n` +
        `SUMMARY:\n${window.lastResults.summary}\n\n` +
        `ISSUES FOUND: ${window.lastResults.issues.length}\n` +
        window.lastResults.issues
            .map((i) => `- ${i.pattern_name} [${i.severity}]: ${i.count} occurrences`)
            .join('\n') +
        `\n\nSUGGESTED FIXES:\n` +
        window.lastResults.suggested_fixes
            .map((f) => `• ${f.issue_name}\n  ${f.fix}`)
            .join('\n\n');

    navigator.clipboard.writeText(text).then(() => {
        showSuccess('Results copied to clipboard!');
    });
}

function downloadResults() {
    if (!window.lastResults) return;

    const json = JSON.stringify(window.lastResults, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `loginsight-analysis-${new Date().getTime()}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

// Reset UI
function resetUI() {
    state.selectedFile = null;
    state.currentJobId = null;
    fileInput.value = '';
    fileInfo.style.display = 'none';
    uploadZone.style.display = 'flex';
    resultsSection.style.display = 'none';
    analyzeBtn.disabled = true;
    analyzeBtn.classList.remove('loading');
}

// Utilities
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;

    return date.toLocaleDateString();
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
    };
    return text.replace(/[&<>"']/g, (m) => map[m]);
}

function showError(message) {
    errorToast.textContent = message;
    errorToast.classList.add('show', 'error');
    setTimeout(() => {
        errorToast.classList.remove('show');
    }, 4000);
}

function showSuccess(message) {
    errorToast.textContent = message;
    errorToast.classList.add('show', 'success');
    setTimeout(() => {
        errorToast.classList.remove('show');
    }, 3000);
}
