// Main JavaScript - Common functionality

// Global variables
let currentResults = null;
let tickerCount = 0;
let currentLanguage = 'en'; // Default language

// Get current language from URL or session
function getCurrentLanguage() {
    const pathParts = window.location.pathname.split('/');
    if (pathParts.length > 1 && (pathParts[1] === 'en' || pathParts[1] === 'ja')) {
        return pathParts[1];
    }
    return 'en'; // Default to English
}

// Set current language on page load
document.addEventListener('DOMContentLoaded', function() {
    currentLanguage = getCurrentLanguage();
});

// Application initialization
function initializeApp() {
    setupDateDefaults();
    setupRangeSliders();
    setupTooltips();
    addInitialTickers();
    setupFormValidation();
}

// Set date default values
function setupDateDefaults() {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setFullYear(endDate.getFullYear() - 30); // Default to 30 years ago
    startDate.setDate(endDate.getDate() + 1); 
    document.getElementById('endDate').valueAsDate = endDate;
    document.getElementById('startDate').valueAsDate = startDate;
}

// Range slider configuration
function setupRangeSliders() {
    // Risk-free rate
    const riskFreeRateRange = document.getElementById('riskFreeRateRange');
    const riskFreeRateValue = document.getElementById('riskFreeRateValue');
    const riskFreeRate = document.getElementById('riskFreeRate');
    
    riskFreeRateRange.addEventListener('input', function() {
        const value = this.value;
        riskFreeRateValue.textContent = value;
        riskFreeRate.value = (value / 100).toString(); // Convert percentage to decimal
    });

    // Target return
    const targetReturnRange = document.getElementById('targetReturnRange');
    const targetReturnValue = document.getElementById('targetReturnValue');
    const targetReturn = document.getElementById('targetReturn');
    
    targetReturnRange.addEventListener('input', function() {
        const value = this.value;
        targetReturnValue.textContent = value;
        targetReturn.value = (value / 100).toString(); // Convert percentage to decimal
    });

    // Enable/disable target return toggle
    document.getElementById('enableTargetReturn').addEventListener('change', function() {
        const targetReturnGroup = document.getElementById('targetReturnGroup');
        if (this.checked) {
            targetReturnGroup.style.display = 'block';
        } else {
            targetReturnGroup.style.display = 'none';
        }
    });

    // Simulation count
    const simulationCountRange = document.getElementById('simulationCountRange');
    const simulationCountValue = document.getElementById('simulationCountValue');
    const simulationCount = document.getElementById('simulationCount');
    
    simulationCountRange.addEventListener('input', function() {
        const value = this.value;
        simulationCountValue.textContent = parseInt(value).toLocaleString();
        simulationCount.value = value;
    });
}

// Tooltip configuration
function setupTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Add initial ticker input fields
function addInitialTickers() {
    addTickerInput('SPY');
    addTickerInput('ACWI');
    addTickerInput('AGG');
    addTickerInput('BND');
    addTickerInput('FRI');
    addTickerInput('GLD');
}

// Add ticker input field
function addTickerInput(defaultValue = '') {
    if (tickerCount >= 20) {
        showError('Maximum 20 assets can be entered');
        return;
    }

    tickerCount++;
    const tickerInputs = document.getElementById('tickerInputs');
    
    const inputGroup = document.createElement('div');
    inputGroup.className = 'ticker-input';
    inputGroup.innerHTML = `
        <input type="text" 
               class="form-control ticker-field" 
               name="ticker_${tickerCount}" 
               placeholder="e.g. AAPL" 
               value="${defaultValue}"
               maxlength="10"
               style="text-transform: uppercase;">
        <div class="ticker-validation-icon">
            <!-- Validation result icon -->
        </div>
        <button type="button" class="btn btn-outline-danger btn-sm" onclick="removeTickerInput(this)">
            <i class="bi bi-trash"></i>
        </button>
    `;
    
    tickerInputs.appendChild(inputGroup);
    
    // Real-time validation
    const input = inputGroup.querySelector('input');
    input.addEventListener('input', function() {
        validateTicker(this);
    });
    
    input.addEventListener('blur', function() {
        validateTickerExists(this);
    });

    // Enable remove buttons when there are at least 2 assets
    updateRemoveButtons();
}

// Remove ticker input field
function removeTickerInput(button) {
    if (tickerCount <= 2) {
        showError('At least 2 assets are required');
        return;
    }
    
    button.closest('.ticker-input').remove();
    tickerCount--;
    updateRemoveButtons();
}

// Update enable/disable state of remove buttons
function updateRemoveButtons() {
    const removeButtons = document.querySelectorAll('.ticker-input button');
    removeButtons.forEach(button => {
        button.disabled = tickerCount <= 2;
    });
}

// Ticker format validation
function validateTicker(input) {
    const ticker = input.value.trim().toUpperCase();
    const icon = input.nextElementSibling;
    
    if (!ticker) {
        input.classList.remove('is-valid', 'is-invalid');
        icon.innerHTML = '';
        return false;
    }
    
    // Basic format check (alphanumeric, dots, hyphens)
    const tickerPattern = /^[A-Z0-9\.\-]{1,10}$/;
    
    if (tickerPattern.test(ticker)) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        icon.innerHTML = '<i class="bi bi-check-circle text-success"></i>';
        return true;
    } else {
        input.classList.remove('is-valid');
        input.classList.add('is-invalid');
        icon.innerHTML = '<i class="bi bi-x-circle text-danger"></i>';
        return false;
    }
}

// Ticker existence validation (API call)
async function validateTickerExists(input) {
    const ticker = input.value.trim().toUpperCase();
    if (!ticker || !validateTicker(input)) return;
    
    const icon = input.nextElementSibling;
    icon.innerHTML = '<div class="loading-spinner"></div>';
    
    try {
        const response = await fetch('/api/ticker/validate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ tickers: [ticker], language: currentLanguage })
        });
        
        const result = await response.json();
        
        if (result.valid_tickers && result.valid_tickers[ticker]) {
            input.classList.remove('is-invalid');
            input.classList.add('is-valid');
            icon.innerHTML = '<i class="bi bi-check-circle text-success"></i>';
        } else {
            input.classList.remove('is-valid');
            input.classList.add('is-invalid');
            icon.innerHTML = '<i class="bi bi-x-circle text-danger"></i>';
        }
    } catch (error) {
        console.error('Ticker validation error:', error);
        icon.innerHTML = '<i class="bi bi-question-circle text-warning"></i>';
    }
}

// Form validation setup
function setupFormValidation() {
    const form = document.getElementById('portfolioForm');
    form.addEventListener('submit', handleFormSubmit);
}

// Form submission processing
async function handleFormSubmit(event) {
    event.preventDefault();
    
    if (!validateForm()) {
        return;
    }
    
    // Hide placeholder when analysis starts
    const placeholderArea = document.getElementById('placeholderArea');
    placeholderArea.classList.remove('d-flex');
    placeholderArea.style.display = 'none';
    
    const formData = getFormData();
    await performAnalysis(formData);
}

// Overall form validation
function validateForm() {
    let isValid = true;
    const errors = [];
    
    // Ticker validation
    const tickers = getTickers();
    if (tickers.length < 2) {
        errors.push('At least 2 assets are required');
        isValid = false;
    } else if (tickers.length > 20) {
        errors.push('Maximum 20 assets can be entered');
        isValid = false;
    }
    
    // Duplicate check
    const uniqueTickers = [...new Set(tickers)];
    if (uniqueTickers.length !== tickers.length) {
        errors.push('Duplicate ticker symbols found');
        isValid = false;
    }
    
    // Date validation
    const startDate = new Date(document.getElementById('startDate').value);
    const endDate = new Date(document.getElementById('endDate').value);
    const today = new Date();
    
    if (startDate >= endDate) {
        errors.push('Start date must be before end date');
        isValid = false;
    }
    
    if (endDate > today) {
        errors.push('End date cannot be in the future');
        isValid = false;
    }
    
    const diffTime = Math.abs(endDate - startDate);
    const diffYears = diffTime / (1000 * 60 * 60 * 24 * 365.25 + 24);
    
    if (diffYears < 1) {
        errors.push('Analysis period must be at least 1 year');
        isValid = false;
    } else if (diffYears > 30) {
        errors.push('Analysis period can be up to 30 years');
        isValid = false;
    }
    
    if (!isValid) {
        showError('Input Error: ' + errors.join(', '));
    }
    
    return isValid;
}

// Get ticker list
function getTickers() {
    const inputs = document.querySelectorAll('.ticker-field');
    const tickers = [];
    
    inputs.forEach(input => {
        const ticker = input.value.trim().toUpperCase();
        if (ticker) {
            tickers.push(ticker);
        }
    });
    
    return tickers;
}

// Get selected tickers (compatibility function for portfolio.js)
function getSelectedTickers() {
    return getTickers();
}

// Get form data
function getFormData() {
    const data = {
        tickers: getTickers(),
        start_date: document.getElementById('startDate').value,
        end_date: document.getElementById('endDate').value,
        risk_free_rate: parseFloat(document.getElementById('riskFreeRate').value),
        simulation_count: parseInt(document.getElementById('simulationCount').value)
    };
    
    // When target return is enabled
    if (document.getElementById('enableTargetReturn').checked) {
        data.target_return = parseFloat(document.getElementById('targetReturn').value);
    }
    
    return data;
}

// Execute portfolio analysis
async function performAnalysis(formData) {
    try {
        showProgress('Starting analysis...', 0);
        
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({...formData, language: currentLanguage})
        });
        
        updateProgress('Processing data...', 50);
        
        const result = await response.json();
        
        if (!response.ok) {
            const errorMsg = result.error || 'Server error occurred';
            const details = result.details ? ` (Details: ${result.details})` : '';
            const errorWarnings = result.validation_errors ? `Validation errors: ${result.validation_errors.join(', ')}` : '';
            throw new Error(errorMsg + details + errorWarnings);
        }
        
        updateProgress('Displaying results...', 80);
        
        // Save results
        currentResults = result;
        
        // Display results
        await displayResults(result);
        
        updateProgress('Complete', 100);
        
        setTimeout(() => {
            hideProgress();
        }, 500);
        
    } catch (error) {
        hideProgress();
        console.error('Analysis error:', error);
        showError('An error occurred during analysis: ' + error.message);
        // Don't re-show placeholder if results area exists
        if (!document.getElementById('resultsArea').classList.contains('show')) {
            const placeholderArea = document.getElementById('placeholderArea');
            placeholderArea.classList.add('d-flex');
            placeholderArea.style.display = 'flex';
        }
    }
}

// Display results
async function displayResults(results) {
    // Display warning messages
    if (results.warnings && results.warnings.length > 0) {
        showWarnings(results.warnings);
    }
    
    // Update summary cards
    updateSummaryCards(results);
    
    // Display analysis time
    document.getElementById('analysisTime').textContent = 
        'Analysis completed: ' + new Date().toLocaleString();
    
    // Generate and display charts
    await generateCharts(results);
    
    // Update data tables
    updateDataTables(results);
    
    // Display simulation details
    displaySimulationDetails(results);
    
    // Show results area
    document.getElementById('resultsArea').classList.add('show');
    
    // Scroll to results area
    document.getElementById('resultsArea').scrollIntoView({ 
        behavior: 'smooth',
        block: 'start'
    });
}

// Display warning messages
function showWarnings(warnings) {
    warnings.forEach(warning => {
        console.warn('Warning:', warning);
    });
    
    // TODO: Implement warning message UI
}

// Reset form
function resetForm() {
    document.getElementById('portfolioForm').reset();
    
    // Clear ticker inputs
    document.getElementById('tickerInputs').innerHTML = '';
    tickerCount = 0;
    
    // Hide results area
    document.getElementById('resultsArea').classList.remove('show');
    const placeholderArea = document.getElementById('placeholderArea');
    placeholderArea.classList.add('d-flex');
    placeholderArea.style.display = 'flex';
    
    // Reset default values
    setupDateDefaults();
    addInitialTickers();
    
    // Clear validation classes
    document.querySelectorAll('.is-valid, .is-invalid').forEach(el => {
        el.classList.remove('is-valid', 'is-invalid');
    });
}

// Export results
async function exportResults(format = 'json') {
    if (!currentResults) {
        showError('No results to export');
        return;
    }
    
    try {
        const response = await fetch('/api/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                format: format,
                results: currentResults,
                language: currentLanguage
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // File download
            const blob = new Blob([JSON.stringify(result.data, null, 2)], {
                type: 'application/json'
            });
            
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `portfolio-analysis-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } else {
            throw new Error(result.error);
        }
        
    } catch (error) {
        console.error('Export error:', error);
        showError('An error occurred during export: ' + error.message);
    }
}

// Number formatting functions
function formatPercent(value, decimals = 2) {
    return (value * 100).toFixed(decimals) + '%';
}

function formatNumber(value, decimals = 4) {
    return parseFloat(value).toFixed(decimals);
}

function formatLargeNumber(value) {
    if (value >= 1000) {
        return (value / 1000).toFixed(0) + 'K';
    }
    return value.toLocaleString();
}