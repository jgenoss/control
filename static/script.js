// Global variables and configuration
let TRM_RATE = 4076.32; // COP per USD - will be updated from API
let transactions = [];
let currentChart = null;
let trendsChart = null;
let comparisonChart = null;
let exchangeRateCache = {};
let isLoadingExchangeRate = false;
let conversionTimeout = null;

// Authentication state
let userSession = window.userSession || { isAuthenticated: false };

// API Functions for authenticated requests
async function loadTransactions() {
    try {
        const response = await fetch('/api/transactions');
        if (response.ok) {
            transactions = await response.json();
            updateDashboard();
            updateCategoryFilters();
            updateTransactionHistory();
            updateReports();
        } else {
            console.error('Failed to load transactions');
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
    }
}

async function saveTransaction(transaction) {
    try {
        const response = await fetch('/api/transactions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(transaction)
        });
        
        const result = await response.json();
        if (result.success) {
            showNotification(result.message, 'success');
            await loadTransactions(); // Reload to get updated data
            return true;
        } else {
            showNotification(result.message, 'error');
            return false;
        }
    } catch (error) {
        console.error('Error saving transaction:', error);
        showNotification('Error al guardar la transacción', 'error');
        return false;
    }
}

async function deleteTransactionFromServer(id) {
    try {
        const response = await fetch(`/api/transactions/${id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        if (result.success) {
            showNotification(result.message, 'success');
            await loadTransactions(); // Reload to get updated data
            return true;
        } else {
            showNotification(result.message, 'error');
            return false;
        }
    } catch (error) {
        console.error('Error deleting transaction:', error);
        showNotification('Error al eliminar la transacción', 'error');
        return false;
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Set current date for form inputs
    setCurrentDate();
    
    // Check if user is authenticated and load accordingly
    if (userSession.isAuthenticated) {
        loadTransactions();
    } else {
        // Load from localStorage for non-authenticated users
        transactions = JSON.parse(localStorage.getItem('transactions')) || [];
        updateDashboard();
        updateCategoryFilters();
        updateTransactionHistory();
        updateReports();
    }
    
    // Initialize TRM rate
    initializeTRM();
    
    // Initialize event listeners
    setupEventListeners();
    
    // Initialize charts
    initializeCharts();
    
    // Setup form conversions
    setupFormConversions();
}

function setCurrentDate() {
    const today = new Date().toISOString().split('T')[0];
    const incomeDate = document.getElementById('incomeDate');
    const expenseDate = document.getElementById('expenseDate');
    
    if (incomeDate) incomeDate.value = today;
    if (expenseDate) expenseDate.value = today;
}

function setupEventListeners() {
    // Form submissions
    const incomeForm = document.getElementById('incomeForm');
    const expenseForm = document.getElementById('expenseForm');
    
    if (incomeForm) {
        incomeForm.addEventListener('submit', handleIncomeSubmit);
    }
    
    if (expenseForm) {
        expenseForm.addEventListener('submit', handleExpenseSubmit);
    }
    
    // Real-time conversion updates with debouncing
    const incomeAmount = document.getElementById('incomeAmount');
    const incomeCurrency = document.getElementById('incomeCurrency');
    const expenseAmount = document.getElementById('expenseAmount');
    const expenseCurrency = document.getElementById('expenseCurrency');
    
    if (incomeAmount && incomeCurrency) {
        // Format input as currency
        incomeAmount.addEventListener('input', handleCurrencyInput);
        incomeAmount.addEventListener('blur', handleCurrencyBlur);
        incomeAmount.addEventListener('focus', handleCurrencyFocus);
        
        // Update conversion and formatting when currency changes
        incomeCurrency.addEventListener('change', function() {
            formatCurrencyInput(incomeAmount, incomeCurrency.value);
            updateCurrencySymbol('incomeAmountSymbol', incomeCurrency.value);
            updateIncomeConversion();
        });
        
        // Debounced conversion update
        incomeAmount.addEventListener('input', debounceConversion(updateIncomeConversion, 800));
    }
    
    if (expenseAmount && expenseCurrency) {
        // Format input as currency
        expenseAmount.addEventListener('input', handleCurrencyInput);
        expenseAmount.addEventListener('blur', handleCurrencyBlur);
        expenseAmount.addEventListener('focus', handleCurrencyFocus);
        
        // Update conversion and formatting when currency changes
        expenseCurrency.addEventListener('change', function() {
            formatCurrencyInput(expenseAmount, expenseCurrency.value);
            updateCurrencySymbol('expenseAmountSymbol', expenseCurrency.value);
            updateExpenseConversion();
        });
        
        // Debounced conversion update
        expenseAmount.addEventListener('input', debounceConversion(updateExpenseConversion, 800));
    }
    
    // Initial currency formatting
    if (incomeAmount && incomeCurrency) {
        formatCurrencyInput(incomeAmount, incomeCurrency.value);
        updateCurrencySymbol('incomeAmountSymbol', incomeCurrency.value);
    }
    if (expenseAmount && expenseCurrency) {
        formatCurrencyInput(expenseAmount, expenseCurrency.value);
        updateCurrencySymbol('expenseAmountSymbol', expenseCurrency.value);
    }
    
    // Responsive chart handling
    window.addEventListener('resize', handleResize);
    
    // Touch events for mobile navigation
    setupTouchNavigation();
}

function setupTouchNavigation() {
    const navTabs = document.querySelectorAll('.nav-tab, .mobile-nav-item');
    
    navTabs.forEach(tab => {
        tab.addEventListener('touchstart', function(e) {
            e.currentTarget.style.transform = 'scale(0.95)';
        }, { passive: true });
        
        tab.addEventListener('touchend', function(e) {
            e.currentTarget.style.transform = 'scale(1)';
        }, { passive: true });
    });
}

function handleResize() {
    // Debounce resize events
    clearTimeout(window.resizeTimeout);
    window.resizeTimeout = setTimeout(() => {
        // Resize charts
        if (currentChart) {
            currentChart.resize();
        }
        if (trendsChart) {
            trendsChart.resize();
        }
        if (comparisonChart) {
            comparisonChart.resize();
        }
        
        // Update responsive elements
        updateResponsiveElements();
    }, 150);
}

function updateResponsiveElements() {
    const isMobile = window.innerWidth < 768;
    
    // Adjust chart heights for mobile
    const chartWrappers = document.querySelectorAll('.chart-wrapper');
    chartWrappers.forEach(wrapper => {
        if (isMobile) {
            wrapper.style.height = '200px';
        } else {
            wrapper.style.height = '300px';
        }
    });
    
    // Adjust transaction item layout
    const transactionItems = document.querySelectorAll('.transaction-item');
    transactionItems.forEach(item => {
        if (isMobile) {
            item.style.flexDirection = 'column';
            item.style.alignItems = 'flex-start';
        } else {
            item.style.flexDirection = 'row';
            item.style.alignItems = 'center';
        }
    });
}

function showTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all nav tabs
    const navTabs = document.querySelectorAll('.nav-tab, .mobile-nav-item');
    navTabs.forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab content
    const selectedTab = document.getElementById(tabName);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Add active class to selected nav tabs
    const selectedNavTabs = document.querySelectorAll(`[data-tab="${tabName}"]`);
    selectedNavTabs.forEach(tab => {
        tab.classList.add('active');
    });
    
    // Handle tab-specific actions
    switch(tabName) {
        case 'dashboard':
            updateDashboard();
            break;
        case 'history':
            updateTransactionHistory();
            break;
        case 'reports':
            updateReports();
            break;
    }
    
    // Scroll to top on mobile
    if (window.innerWidth < 768) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

async function handleIncomeSubmit(e) {
    e.preventDefault();
    
    const amountInput = document.getElementById('incomeAmount');
    const amount = getRawValue(amountInput);
    const currency = document.getElementById('incomeCurrency').value;
    const description = document.getElementById('incomeDescription').value;
    const date = document.getElementById('incomeDate').value;
    
    if (!amount || !currency || !description || !date) {
        showNotification('Por favor, completa todos los campos', 'error');
        return;
    }
    
    // Show loading state
    const submitBtn = document.querySelector('#incomeForm button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i><span>Obteniendo tipo de cambio...</span>';
    submitBtn.disabled = true;
    
    try {
        // Get exchange rate for the specific date
        const exchangeRate = await getExchangeRateForDate(date);
        
        const transaction = {
            id: Date.now(),
            type: 'income',
            amount: amount,
            currency: currency,
            description: description,
            date: date,
            category: 'Ingreso',
            exchangeRate: exchangeRate,
            usdAmount: currency === 'USD' ? amount : amount / exchangeRate
        };
        
        if (userSession.isAuthenticated) {
            const apiTransaction = {
                type: 'income',
                amount: amount,
                currency: currency,
                category: 'Ingreso',
                description: description,
                date: date,
                exchange_rate: exchangeRate
            };
            const success = await saveTransaction(apiTransaction);
            if (!success) return;
        } else {
            transactions.push(transaction);
            saveTransactions();
            updateDashboard();
        }
        
        // Clear form
        document.getElementById('incomeForm').reset();
        setCurrentDate();
        updateIncomeConversion();
        
        showNotification(`Ingreso registrado con TRM $${formatNumber(exchangeRate, 2)}`, 'success');
        
    } catch (error) {
        console.error('Error al obtener tipo de cambio:', error);
        showNotification('Error al obtener el tipo de cambio. Intenta nuevamente.', 'error');
    } finally {
        // Restore button state
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

async function handleExpenseSubmit(e) {
    e.preventDefault();
    
    const amountInput = document.getElementById('expenseAmount');
    const amount = getRawValue(amountInput);
    const currency = document.getElementById('expenseCurrency').value;
    const category = document.getElementById('expenseCategory').value;
    const description = document.getElementById('expenseDescription').value;
    const date = document.getElementById('expenseDate').value;
    
    if (!amount || !currency || !category || !description || !date) {
        showNotification('Por favor, completa todos los campos', 'error');
        return;
    }
    
    // Show loading state
    const submitBtn = document.querySelector('#expenseForm button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i><span>Obteniendo tipo de cambio...</span>';
    submitBtn.disabled = true;
    
    try {
        // Get exchange rate for the specific date
        const exchangeRate = await getExchangeRateForDate(date);
        
        const transaction = {
            id: Date.now(),
            type: 'expense',
            amount: amount,
            currency: currency,
            description: description,
            date: date,
            category: category,
            exchangeRate: exchangeRate,
            usdAmount: currency === 'USD' ? amount : amount / exchangeRate
        };
        
        if (userSession.isAuthenticated) {
            const apiTransaction = {
                type: 'expense',
                amount: amount,
                currency: currency,
                category: category,
                description: description,
                date: date,
                exchange_rate: exchangeRate
            };
            const success = await saveTransaction(apiTransaction);
            if (!success) return;
        } else {
            transactions.push(transaction);
            saveTransactions();
            updateDashboard();
        }
        
        // Clear form
        document.getElementById('expenseForm').reset();
        setCurrentDate();
        updateExpenseConversion();
        
        showNotification(`Gasto registrado con TRM $${formatNumber(exchangeRate, 2)}`, 'success');
        
    } catch (error) {
        console.error('Error al obtener tipo de cambio:', error);
        showNotification('Error al obtener el tipo de cambio. Intenta nuevamente.', 'error');
    } finally {
        // Restore button state
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

async function updateIncomeConversion() {
    const amountInput = document.getElementById('incomeAmount');
    const amount = getRawValue(amountInput) || 0;
    const currency = document.getElementById('incomeCurrency').value;
    const conversionDiv = document.getElementById('incomeConversion');
    
    if (amount > 0 && conversionDiv) {
        // Show loading state
        conversionDiv.innerHTML = '<i class="bi bi-hourglass-split"></i> Obteniendo tipo de cambio actual...';
        
        try {
            const currentRate = await getCurrentExchangeRate();
            const exchangeRate = currentRate || TRM_RATE;
            
            if (currency === 'COP') {
                const usdAmount = amount / exchangeRate;
                conversionDiv.innerHTML = `
                    <strong>COP $${formatNumber(amount)}</strong> equivale a 
                    <strong>USD $${formatNumber(usdAmount, 2)}</strong>
                    <br><small>TRM: $${formatNumber(exchangeRate, 2)}</small>
                `;
            } else {
                const copAmount = amount * exchangeRate;
                conversionDiv.innerHTML = `
                    <strong>USD $${formatNumber(amount, 2)}</strong> equivale a 
                    <strong>COP $${formatNumber(copAmount)}</strong>
                    <br><small>TRM: $${formatNumber(exchangeRate, 2)}</small>
                `;
            }
        } catch (error) {
            conversionDiv.innerHTML = `
                Error al obtener tipo de cambio. Usando TRM base: $${formatNumber(TRM_RATE, 2)}
            `;
        }
    } else if (conversionDiv) {
        conversionDiv.textContent = 'Ingresa un monto para ver la conversión';
    }
}

async function updateExpenseConversion() {
    const amountInput = document.getElementById('expenseAmount');
    const amount = getRawValue(amountInput) || 0;
    const currency = document.getElementById('expenseCurrency').value;
    const conversionDiv = document.getElementById('expenseConversion');
    
    if (amount > 0 && conversionDiv) {
        // Show loading state
        conversionDiv.innerHTML = '<i class="bi bi-hourglass-split"></i> Obteniendo tipo de cambio actual...';
        
        try {
            const currentRate = await getCurrentExchangeRate();
            const exchangeRate = currentRate || TRM_RATE;
            
            if (currency === 'COP') {
                const usdAmount = amount / exchangeRate;
                conversionDiv.innerHTML = `
                    <strong>COP $${formatNumber(amount)}</strong> equivale a 
                    <strong>USD $${formatNumber(usdAmount, 2)}</strong>
                    <br><small>TRM: $${formatNumber(exchangeRate, 2)}</small>
                `;
            } else {
                const copAmount = amount * exchangeRate;
                conversionDiv.innerHTML = `
                    <strong>USD $${formatNumber(amount, 2)}</strong> equivale a 
                    <strong>COP $${formatNumber(copAmount)}</strong>
                    <br><small>TRM: $${formatNumber(exchangeRate, 2)}</small>
                `;
            }
        } catch (error) {
            conversionDiv.innerHTML = `
                Error al obtener tipo de cambio. Usando TRM base: $${formatNumber(TRM_RATE, 2)}
            `;
        }
    } else if (conversionDiv) {
        conversionDiv.textContent = 'Ingresa un monto para ver la conversión';
    }
}

function setupFormConversions() {
    updateIncomeConversion();
    updateExpenseConversion();
}

// Debounce function to limit API calls
function debounceConversion(func, delay) {
    return function(...args) {
        clearTimeout(conversionTimeout);
        conversionTimeout = setTimeout(() => func.apply(this, args), delay);
    };
}

// Migration function for existing transactions
function migrateExistingTransactions() {
    let migrationNeeded = false;
    
    transactions.forEach(transaction => {
        if (!transaction.exchangeRate) {
            // Add the current TRM_RATE as the exchange rate for old transactions
            transaction.exchangeRate = TRM_RATE;
            
            // Recalculate USD amount if needed
            if (!transaction.usdAmount) {
                transaction.usdAmount = transaction.currency === 'USD' 
                    ? transaction.amount 
                    : transaction.amount / transaction.exchangeRate;
            }
            
            migrationNeeded = true;
        }
    });
    
    if (migrationNeeded) {
        saveTransactions();
        console.log('Migrated existing transactions to include exchange rates');
    }
}

// Exchange Impact Analysis
function updateExchangeImpact() {
    const exchangeImpactDiv = document.getElementById('exchangeImpact');
    if (!exchangeImpactDiv || transactions.length === 0) {
        if (exchangeImpactDiv) {
            exchangeImpactDiv.innerHTML = '<p class="text-center text-muted">No hay transacciones para analizar</p>';
        }
        return;
    }

    // Calculate average exchange rate used
    const ratesUsed = transactions
        .filter(t => t.exchangeRate)
        .map(t => t.exchangeRate);
    
    if (ratesUsed.length === 0) {
        exchangeImpactDiv.innerHTML = '<p class="text-center text-muted">No hay datos de tipo de cambio</p>';
        return;
    }

    const avgRate = ratesUsed.reduce((sum, rate) => sum + rate, 0) / ratesUsed.length;
    const minRate = Math.min(...ratesUsed);
    const maxRate = Math.max(...ratesUsed);
    
    // Calculate what total balance would be with current vs historical rates
    const balanceWithCurrentRate = transactions.reduce((sum, transaction) => {
        let usdAmount;
        if (transaction.currency === 'USD') {
            usdAmount = transaction.amount;
        } else {
            usdAmount = transaction.amount / TRM_RATE; // Using current rate
        }
        
        return transaction.type === 'income' 
            ? sum + usdAmount 
            : sum - usdAmount;
    }, 0);

    const balanceWithHistoricalRates = transactions.reduce((sum, transaction) => {
        return transaction.type === 'income' 
            ? sum + transaction.usdAmount 
            : sum - transaction.usdAmount;
    }, 0);

    const rateDifference = balanceWithCurrentRate - balanceWithHistoricalRates;
    const percentageDifference = balanceWithHistoricalRates !== 0 
        ? ((rateDifference / Math.abs(balanceWithHistoricalRates)) * 100) 
        : 0;

    let impactClass = 'impact-neutral';
    let impactIcon = '➖';
    if (rateDifference > 0) {
        impactClass = 'impact-positive';
        impactIcon = '📈';
    } else if (rateDifference < 0) {
        impactClass = 'impact-negative';
        impactIcon = '📉';
    }

    exchangeImpactDiv.innerHTML = `
        <div class="impact-content">
            <div class="impact-item impact-neutral">
                <div class="impact-value">$${formatNumber(avgRate, 2)}</div>
                <div class="impact-label">TRM Promedio</div>
            </div>
            <div class="impact-item impact-neutral">
                <div class="impact-value">$${formatNumber(minRate, 2)} - $${formatNumber(maxRate, 2)}</div>
                <div class="impact-label">Rango TRM</div>
            </div>
            <div class="impact-item ${impactClass}">
                <div class="impact-value">${impactIcon} $${formatNumber(Math.abs(rateDifference), 2)}</div>
                <div class="impact-label">
                    ${rateDifference >= 0 ? 'Ganancia' : 'Pérdida'} por variación TRM
                </div>
            </div>
            <div class="impact-item ${impactClass}">
                <div class="impact-value">${formatNumber(Math.abs(percentageDifference), 1)}%</div>
                <div class="impact-label">Impacto porcentual</div>
            </div>
        </div>
        <div style="margin-top: 1rem; padding: 1rem; background: #f8f9fa; border-radius: 8px; font-size: 0.875rem; color: #6c757d;">
            <strong>Explicación:</strong> ${
                rateDifference > 0 
                    ? `Si convirtieras todas tus transacciones al TRM actual (${formatNumber(TRM_RATE, 2)}), tendrías $${formatNumber(rateDifference, 2)} USD más que con los tipos de cambio históricos.`
                    : rateDifference < 0 
                    ? `Si convirtieras todas tus transacciones al TRM actual (${formatNumber(TRM_RATE, 2)}), tendrías $${formatNumber(Math.abs(rateDifference), 2)} USD menos que con los tipos de cambio históricos.`
                    : 'El TRM actual es similar al promedio histórico de tus transacciones.'
            }
        </div>
    `;
}

// Currency Input Formatting Functions
function handleCurrencyInput(e) {
    const input = e.target;
    const currency = getCurrencyForInput(input);
    
    // Remove all non-numeric characters except decimal point
    let value = input.value.replace(/[^\d.]/g, '');
    
    // Ensure only one decimal point
    const parts = value.split('.');
    if (parts.length > 2) {
        value = parts[0] + '.' + parts.slice(1).join('');
    }
    
    // Limit decimal places based on currency
    if (parts.length === 2) {
        const decimals = currency === 'USD' ? 2 : 0;
        parts[1] = parts[1].substring(0, decimals);
        value = parts[0] + (parts[1] ? '.' + parts[1] : '');
    }
    
    // Store raw value for calculations
    input.dataset.rawValue = value;
    
    // Format for display (but don't format while typing)
    input.value = value;
}

function handleCurrencyBlur(e) {
    const input = e.target;
    const currency = getCurrencyForInput(input);
    const rawValue = input.dataset.rawValue || input.value;
    
    if (rawValue && !isNaN(rawValue)) {
        const numericValue = parseFloat(rawValue);
        input.value = formatCurrencyDisplay(numericValue, currency);
    }
}

function handleCurrencyFocus(e) {
    const input = e.target;
    const rawValue = input.dataset.rawValue || '';
    
    // Show raw number for editing
    if (rawValue) {
        input.value = rawValue;
    }
}

function formatCurrencyInput(input, currency) {
    const currentValue = input.dataset.rawValue || input.value;
    if (currentValue && !isNaN(currentValue)) {
        const numericValue = parseFloat(currentValue);
        
        // Update placeholder based on currency
        if (currency === 'USD') {
            input.placeholder = 'Ej: 400.50';
            input.step = '0.01';
        } else {
            input.placeholder = 'Ej: 1500000';
            input.step = '1';
        }
        
        // If not focused, show formatted value
        if (document.activeElement !== input) {
            input.value = formatCurrencyDisplay(numericValue, currency);
        }
    } else {
        // Update placeholder for empty input
        if (currency === 'USD') {
            input.placeholder = 'Ej: 400.50';
            input.step = '0.01';
        } else {
            input.placeholder = 'Ej: 1500000';
            input.step = '1';
        }
    }
}

function formatCurrencyDisplay(amount, currency) {
    if (currency === 'USD') {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    } else {
        return new Intl.NumberFormat('es-CO', {
            style: 'currency',
            currency: 'COP',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount);
    }
}

function getCurrencyForInput(input) {
    const inputId = input.id;
    if (inputId.includes('income')) {
        const currencySelect = document.getElementById('incomeCurrency');
        return currencySelect ? currencySelect.value : 'COP';
    } else if (inputId.includes('expense')) {
        const currencySelect = document.getElementById('expenseCurrency');
        return currencySelect ? currencySelect.value : 'COP';
    }
    return 'COP';
}

function getRawValue(input) {
    // Get the numeric value from formatted input
    const rawValue = input.dataset.rawValue;
    if (rawValue && !isNaN(rawValue)) {
        return parseFloat(rawValue);
    }
    
    // Fallback: extract number from formatted value
    const value = input.value.replace(/[^\d.]/g, '');
    return value ? parseFloat(value) : 0;
}

function updateCurrencySymbol(symbolId, currency) {
    const symbolElement = document.getElementById(symbolId);
    if (symbolElement) {
        symbolElement.textContent = currency === 'USD' ? 'USD $' : 'COP $';
    }
    
    // Update input class for styling
    const inputId = symbolId.replace('Symbol', '');
    const inputElement = document.getElementById(inputId);
    if (inputElement) {
        inputElement.classList.remove('usd', 'cop');
        inputElement.classList.add(currency.toLowerCase());
    }
}

// Exchange Rate API Functions
async function fetchTRM() {
    try {
        const res = await fetch("https://open.er-api.com/v6/latest/USD");
        const data = await res.json();
        const trm = data.rates.COP;
        return trm;
    } catch (e) {
        console.error("Error obteniendo TRM:", e);
        return null;
    }
}

async function initializeTRM() {
    // Show loading state
    const trmElement = document.querySelector('.trm-info');
    if (trmElement) {
        trmElement.innerHTML = `
            <i class="bi bi-hourglass-split"></i> Obteniendo TRM actual...
        `;
    }
    
    const trm = await fetchTRM();
    if (trm) {
        window.TRM_RATE = trm;
        TRM_RATE = trm;
        if (trmElement) {
            trmElement.innerHTML = `
                <strong>TRM Actual:</strong> $${trm.toLocaleString('es-CO')} COP por USD
                <br><small>Actualizado: ${new Date().toLocaleDateString('es-CO')}</small>
            `;
        }
        updateDashboard();
        updateReports();
    } else {
        // Show error state
        if (trmElement) {
            trmElement.innerHTML = `
                <strong>TRM Base:</strong> $${TRM_RATE.toLocaleString('es-CO')} COP por USD
                <br><small>Error al actualizar - usando valor base</small>
            `;
        }
    }
}

async function getCurrentExchangeRate() {
    try {
        return await fetchTRM();
    } catch (error) {
        console.error('Error fetching current exchange rate:', error);
        return null;
    }
}

async function getExchangeRateForDate(date) {
    // Check cache first
    if (exchangeRateCache[date]) {
        return exchangeRateCache[date];
    }
    
    if (isLoadingExchangeRate) {
        // Wait for current request to complete
        await new Promise(resolve => setTimeout(resolve, 1000));
        if (exchangeRateCache[date]) {
            return exchangeRateCache[date];
        }
    }
    
    isLoadingExchangeRate = true;
    
    try {
        // For current/recent dates, use the current TRM
        const today = new Date();
        const requestDate = new Date(date);
        const daysDiff = Math.abs(today - requestDate) / (1000 * 60 * 60 * 24);
        
        let rate;
        if (daysDiff <= 7) {
            // Use current rate for recent dates (within a week)
            rate = await fetchTRM();
        } else {
            // For older dates, use current rate as approximation
            rate = await fetchTRM();
        }
        
        if (!rate) {
            rate = TRM_RATE;
        }
        
        // Cache the result
        exchangeRateCache[date] = rate;
        isLoadingExchangeRate = false;
        
        return rate;
        
    } catch (error) {
        console.error('Error fetching exchange rate for date:', date, error);
        isLoadingExchangeRate = false;
        return TRM_RATE; // Fallback to current rate
    }
}

// Manual TRM refresh function
async function refreshTRM() {
    const refreshBtn = document.querySelector('.trm-refresh-btn');
    const trmElement = document.querySelector('.trm-content');
    
    if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.classList.add('loading');
    }
    
    if (trmElement) {
        trmElement.innerHTML = `
            <i class="bi bi-hourglass-split"></i> Actualizando TRM...
        `;
    }
    
    try {
        // Clear cache to force fresh fetch
        exchangeRateCache = {};
        
        const trm = await fetchTRM();
        if (trm) {
            window.TRM_RATE = trm;
            TRM_RATE = trm;
            
            if (trmElement) {
                trmElement.innerHTML = `
                    <strong>TRM Actual:</strong> $${trm.toLocaleString('es-CO')} COP por USD
                    <br><small>Actualizado: ${new Date().toLocaleDateString('es-CO')}</small>
                `;
            }
            
            // Update dashboard with new rates
            updateDashboard();
            updateReports();
            
            showNotification(`TRM actualizado: $${trm.toLocaleString('es-CO')}`, 'success');
        } else {
            throw new Error('No se pudo obtener el TRM');
        }
    } catch (error) {
        console.error('Error refreshing TRM:', error);
        if (trmElement) {
            trmElement.innerHTML = `
                <strong>TRM Base:</strong> $${TRM_RATE.toLocaleString('es-CO')} COP por USD
                <br><small>Error al actualizar</small>
            `;
        }
        showNotification('Error al actualizar TRM', 'error');
    } finally {
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.classList.remove('loading');
        }
    }
}

function updateDashboard() {
    const currentMonth = new Date().getMonth();
    const currentYear = new Date().getFullYear();
    
    // Calculate totals using the USD amount stored with each transaction
    const totalBalance = transactions.reduce((sum, transaction) => {
        return transaction.type === 'income' 
            ? sum + transaction.usdAmount 
            : sum - transaction.usdAmount;
    }, 0);
    
    // Calculate monthly totals and their COP equivalents using original exchange rates
    const monthlyIncomeTransactions = transactions.filter(t => {
        const transactionDate = new Date(t.date);
        return t.type === 'income' && 
               transactionDate.getMonth() === currentMonth && 
               transactionDate.getFullYear() === currentYear;
    });
    
    const monthlyExpenseTransactions = transactions.filter(t => {
        const transactionDate = new Date(t.date);
        return t.type === 'expense' && 
               transactionDate.getMonth() === currentMonth && 
               transactionDate.getFullYear() === currentYear;
    });
    
    const monthlyIncome = monthlyIncomeTransactions.reduce((sum, t) => sum + t.usdAmount, 0);
    const monthlyExpenses = monthlyExpenseTransactions.reduce((sum, t) => sum + t.usdAmount, 0);
    
    // Calculate COP equivalents using the original transaction rates when possible
    const monthlyIncomeCOP = monthlyIncomeTransactions.reduce((sum, t) => {
        if (t.currency === 'COP') {
            return sum + t.amount; // Original COP amount
        } else {
            const rate = t.exchangeRate || TRM_RATE;
            return sum + (t.amount * rate); // USD to COP using original rate
        }
    }, 0);
    
    const monthlyExpensesCOP = monthlyExpenseTransactions.reduce((sum, t) => {
        if (t.currency === 'COP') {
            return sum + t.amount; // Original COP amount
        } else {
            const rate = t.exchangeRate || TRM_RATE;
            return sum + (t.amount * rate); // USD to COP using original rate
        }
    }, 0);
    
    // For total balance COP, we need to convert using current rate since it's a mixed calculation
    const totalBalanceCOP = transactions.reduce((sum, transaction) => {
        const rate = transaction.exchangeRate || TRM_RATE;
        let copAmount;
        
        if (transaction.currency === 'COP') {
            copAmount = transaction.amount;
        } else {
            copAmount = transaction.amount * rate;
        }
        
        return transaction.type === 'income' 
            ? sum + copAmount 
            : sum - copAmount;
    }, 0);
    
    // Update UI
    updateElement('totalBalance', `$${formatNumber(totalBalance, 2)}`);
    updateElement('balanceCOP', `COP $${formatNumber(totalBalanceCOP)}`);
    updateElement('monthlyIncome', `$${formatNumber(monthlyIncome, 2)}`);
    updateElement('monthlyIncomeConv', `COP $${formatNumber(monthlyIncomeCOP)}`);
    updateElement('monthlyExpenses', `$${formatNumber(monthlyExpenses, 2)}`);
    updateElement('monthlyExpensesConv', `COP $${formatNumber(monthlyExpensesCOP)}`);
    
    // Update recent transactions
    updateRecentTransactions();
    
    // Update exchange impact analysis
    updateExchangeImpact();
    
    // Update expense chart
    updateExpenseChart();
}

function updateRecentTransactions() {
    const recentTransactionsDiv = document.getElementById('recentTransactions');
    if (!recentTransactionsDiv) return;
    
    const recentTransactions = transactions
        .sort((a, b) => new Date(b.date) - new Date(a.date))
        .slice(0, 5);
    
    if (recentTransactions.length === 0) {
        recentTransactionsDiv.innerHTML = `
            <div class="text-center p-4 text-muted">
                <i class="bi bi-inbox" style="font-size: 2rem; margin-bottom: 1rem; display: block;"></i>
                No hay transacciones registradas
            </div>
        `;
        return;
    }
    
    recentTransactionsDiv.innerHTML = recentTransactions
        .map(transaction => createTransactionHTML(transaction))
        .join('');
}

function createTransactionHTML(transaction) {
    const isIncome = transaction.type === 'income';
    const amountClass = isIncome ? 'income' : 'expense';
    const amountPrefix = isIncome ? '+' : '-';
    const exchangeRate = transaction.exchangeRate || TRM_RATE;
    
    // Calculate both currency amounts for display
    let originalAmount, convertedAmount, originalCurrency, convertedCurrency;
    
    if (transaction.currency === 'USD') {
        originalAmount = transaction.amount;
        originalCurrency = 'USD';
        convertedAmount = transaction.amount * exchangeRate;
        convertedCurrency = 'COP';
    } else {
        originalAmount = transaction.amount;
        originalCurrency = 'COP';
        convertedAmount = transaction.amount / exchangeRate;
        convertedCurrency = 'USD';
    }
    
    return `
        <div class="transaction-item">
            <div class="transaction-info">
                <div class="transaction-category">${transaction.category}</div>
                <div class="transaction-description">${transaction.description}</div>
                <div class="transaction-date">${formatDate(transaction.date)}</div>
                <div class="transaction-rate">TRM: $${formatNumber(exchangeRate, 2)}</div>
                <div class="transaction-conversion">
                    ${originalCurrency} $${formatNumber(originalAmount, originalCurrency === 'USD' ? 2 : 0)} 
                    → ${convertedCurrency} $${formatNumber(convertedAmount, convertedCurrency === 'USD' ? 2 : 0)}
                </div>
            </div>
            <div class="transaction-amount ${amountClass}">
                ${amountPrefix}$${formatNumber(transaction.usdAmount, 2)} USD
                <button class="delete-btn" onclick="deleteTransaction(${transaction.id})" title="Eliminar">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        </div>
    `;
}

async function deleteTransaction(id) {
    if (confirm('¿Estás seguro de que quieres eliminar esta transacción?')) {
        if (userSession.isAuthenticated) {
            const success = await deleteTransactionFromServer(id);
            if (success) {
                // Transaction list will be automatically reloaded by deleteTransactionFromServer
            }
        } else {
            transactions = transactions.filter(t => t.id !== id);
            saveTransactions();
            updateDashboard();
            updateTransactionHistory();
            updateReports();
            showNotification('Transacción eliminada', 'success');
        }
    }
}

function initializeCharts() {
    updateExpenseChart();
}

function updateExpenseChart() {
    const canvas = document.getElementById('expenseChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const currentMonth = new Date().getMonth();
    const currentYear = new Date().getFullYear();
    
    // Get current month expenses by category
    const monthlyExpenses = transactions
        .filter(t => {
            const transactionDate = new Date(t.date);
            return t.type === 'expense' && 
                   transactionDate.getMonth() === currentMonth && 
                   transactionDate.getFullYear() === currentYear;
        });
    
    const categoryTotals = {};
    monthlyExpenses.forEach(expense => {
        categoryTotals[expense.category] = (categoryTotals[expense.category] || 0) + expense.usdAmount;
    });
    
    const categories = Object.keys(categoryTotals);
    const amounts = Object.values(categoryTotals);
    
    // Destroy existing chart
    if (currentChart) {
        currentChart.destroy();
    }
    
    if (categories.length === 0) {
        // Show empty state
        ctx.fillStyle = '#6c757d';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('No hay gastos este mes', canvas.width / 2, canvas.height / 2);
        return;
    }
    
    // Create responsive chart
    currentChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: categories,
            datasets: [{
                data: amounts,
                backgroundColor: [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
                    '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF',
                    '#4BC0C0', '#FF6384'
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: window.innerWidth < 768 ? 'bottom' : 'right',
                    labels: {
                        boxWidth: 12,
                        padding: window.innerWidth < 768 ? 8 : 15,
                        font: {
                            size: window.innerWidth < 768 ? 10 : 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = amounts.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label}: $${formatNumber(context.parsed, 2)} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function updateTransactionHistory() {
    const historyDiv = document.getElementById('transactionHistory');
    if (!historyDiv) return;
    
    let filteredTransactions = [...transactions];
    
    // Apply filters if they exist
    const monthFilter = document.getElementById('filterMonth')?.value;
    const typeFilter = document.getElementById('filterType')?.value;
    const categoryFilter = document.getElementById('filterCategory')?.value;
    
    if (monthFilter) {
        filteredTransactions = filteredTransactions.filter(t => {
            const transactionMonth = new Date(t.date).getMonth() + 1;
            return transactionMonth.toString().padStart(2, '0') === monthFilter;
        });
    }
    
    if (typeFilter) {
        filteredTransactions = filteredTransactions.filter(t => t.type === typeFilter);
    }
    
    if (categoryFilter) {
        filteredTransactions = filteredTransactions.filter(t => t.category === categoryFilter);
    }
    
    // Sort by date (newest first)
    filteredTransactions.sort((a, b) => new Date(b.date) - new Date(a.date));
    
    if (filteredTransactions.length === 0) {
        historyDiv.innerHTML = `
            <div class="text-center p-4 text-muted">
                <i class="bi bi-search" style="font-size: 2rem; margin-bottom: 1rem; display: block;"></i>
                No se encontraron transacciones con los filtros aplicados
            </div>
        `;
        return;
    }
    
    historyDiv.innerHTML = filteredTransactions
        .map(transaction => createTransactionHTML(transaction))
        .join('');
}

function updateCategoryFilters() {
    const categoryFilter = document.getElementById('filterCategory');
    if (!categoryFilter) return;
    
    const categories = [...new Set(transactions.map(t => t.category))];
    const currentValue = categoryFilter.value;
    
    categoryFilter.innerHTML = '<option value="">Todas las categorías</option>';
    categories.forEach(category => {
        const option = document.createElement('option');
        option.value = category;
        option.textContent = category;
        if (category === currentValue) {
            option.selected = true;
        }
        categoryFilter.appendChild(option);
    });
}

function applyFilters() {
    updateTransactionHistory();
    showNotification('Filtros aplicados', 'info');
}

function updateReports() {
    updateMonthlySummary();
    updateTrendsChart();
    updateComparisonChart();
}

function updateMonthlySummary() {
    const summaryDiv = document.getElementById('monthlySummary');
    if (!summaryDiv) return;
    
    const monthlyData = {};
    
    transactions.forEach(transaction => {
        const date = new Date(transaction.date);
        const monthKey = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}`;
        
        if (!monthlyData[monthKey]) {
            monthlyData[monthKey] = { income: 0, expenses: 0 };
        }
        
        if (transaction.type === 'income') {
            monthlyData[monthKey].income += transaction.usdAmount;
        } else {
            monthlyData[monthKey].expenses += transaction.usdAmount;
        }
    });
    
    const sortedMonths = Object.keys(monthlyData).sort().reverse().slice(0, 6);
    
    if (sortedMonths.length === 0) {
        summaryDiv.innerHTML = `
            <div class="text-center p-4 text-muted">
                <i class="bi bi-calendar-x" style="font-size: 2rem; margin-bottom: 1rem; display: block;"></i>
                No hay datos para mostrar el resumen mensual
            </div>
        `;
        return;
    }
    
    summaryDiv.innerHTML = sortedMonths.map(month => {
        const data = monthlyData[month];
        const balance = data.income - data.expenses;
        const [year, monthNum] = month.split('-');
        const monthName = new Date(year, monthNum - 1).toLocaleDateString('es-ES', { month: 'long', year: 'numeric' });
        
        return `
            <div class="summary-card">
                <h4 style="margin-bottom: 1rem; text-transform: capitalize;">${monthName}</h4>
                <div style="margin-bottom: 0.5rem;">
                    <strong style="color: var(--success-color);">Ingresos:</strong> $${formatNumber(data.income, 2)}
                </div>
                <div style="margin-bottom: 0.5rem;">
                    <strong style="color: var(--danger-color);">Gastos:</strong> $${formatNumber(data.expenses, 2)}
                </div>
                <div>
                    <strong style="color: ${balance >= 0 ? 'var(--success-color)' : 'var(--danger-color)'};">
                        Balance: $${formatNumber(balance, 2)}
                    </strong>
                </div>
            </div>
        `;
    }).join('');
}

function updateTrendsChart() {
    const canvas = document.getElementById('trendsChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Get last 6 months of data
    const monthlyExpenses = {};
    const currentDate = new Date();
    
    // Initialize last 6 months
    for (let i = 5; i >= 0; i--) {
        const date = new Date(currentDate.getFullYear(), currentDate.getMonth() - i, 1);
        const monthKey = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}`;
        monthlyExpenses[monthKey] = 0;
    }
    
    // Calculate expenses for each month
    transactions
        .filter(t => t.type === 'expense')
        .forEach(transaction => {
            const date = new Date(transaction.date);
            const monthKey = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}`;
            if (monthlyExpenses.hasOwnProperty(monthKey)) {
                monthlyExpenses[monthKey] += transaction.usdAmount;
            }
        });
    
    const labels = Object.keys(monthlyExpenses).map(key => {
        const [year, month] = key.split('-');
        return new Date(year, month - 1).toLocaleDateString('es-ES', { month: 'short' });
    });
    
    const data = Object.values(monthlyExpenses);
    
    // Destroy existing chart
    if (trendsChart) {
        trendsChart.destroy();
    }
    
    trendsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Gastos Mensuales (USD)',
                data: data,
                borderColor: '#e74c3c',
                backgroundColor: 'rgba(231, 76, 60, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#e74c3c',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: window.innerWidth >= 768
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Gastos: $${formatNumber(context.parsed.y, 2)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + formatNumber(value, 2);
                        }
                    }
                }
            }
        }
    });
}

function updateComparisonChart() {
    const canvas = document.getElementById('comparisonChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Get last 6 months of data
    const monthlyData = {};
    const currentDate = new Date();
    
    // Initialize last 6 months
    for (let i = 5; i >= 0; i--) {
        const date = new Date(currentDate.getFullYear(), currentDate.getMonth() - i, 1);
        const monthKey = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}`;
        monthlyData[monthKey] = { income: 0, expenses: 0 };
    }
    
    // Calculate data for each month
    transactions.forEach(transaction => {
        const date = new Date(transaction.date);
        const monthKey = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}`;
        if (monthlyData.hasOwnProperty(monthKey)) {
            if (transaction.type === 'income') {
                monthlyData[monthKey].income += transaction.usdAmount;
            } else {
                monthlyData[monthKey].expenses += transaction.usdAmount;
            }
        }
    });
    
    const labels = Object.keys(monthlyData).map(key => {
        const [year, month] = key.split('-');
        return new Date(year, month - 1).toLocaleDateString('es-ES', { month: 'short' });
    });
    
    const incomeData = Object.values(monthlyData).map(d => d.income);
    const expenseData = Object.values(monthlyData).map(d => d.expenses);
    
    // Destroy existing chart
    if (comparisonChart) {
        comparisonChart.destroy();
    }
    
    comparisonChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Ingresos',
                    data: incomeData,
                    backgroundColor: 'rgba(39, 174, 96, 0.8)',
                    borderColor: '#27ae60',
                    borderWidth: 1
                },
                {
                    label: 'Gastos',
                    data: expenseData,
                    backgroundColor: 'rgba(231, 76, 60, 0.8)',
                    borderColor: '#e74c3c',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: window.innerWidth < 768 ? 'top' : 'right'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: $${formatNumber(context.parsed.y, 2)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + formatNumber(value, 2);
                        }
                    }
                }
            }
        }
    });
}

// Utility functions
function saveTransactions() {
    if (userSession.isAuthenticated) {
        // For authenticated users, data is saved via API
        return;
    } else {
        // For non-authenticated users, save to localStorage
        localStorage.setItem('transactions', JSON.stringify(transactions));
    }
}

function formatNumber(number, decimals = 0) {
    return new Intl.NumberFormat('es-CO', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(number);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

function updateElement(id, content) {
    const element = document.getElementById(id);
    if (element) {
        element.innerHTML = content;
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="bi bi-${getNotificationIcon(type)}"></i>
            <span>${message}</span>
        </div>
    `;
    
    // Style the notification
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${getNotificationColor(type)};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 9999;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        max-width: 300px;
        animation: slideIn 0.3s ease-out;
    `;
    
    // Add animation styles if not already added
    if (!document.getElementById('notification-styles')) {
        const styles = document.createElement('style');
        styles.id = 'notification-styles';
        styles.textContent = `
            @keyframes slideIn {
                from {
                    transform: translateX(100%);
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
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(styles);
    }
    
    document.body.appendChild(notification);
    
    // Remove notification after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

function getNotificationIcon(type) {
    switch(type) {
        case 'success': return 'check-circle';
        case 'error': return 'x-circle';
        case 'warning': return 'exclamation-triangle';
        default: return 'info-circle';
    }
}

function getNotificationColor(type) {
    switch(type) {
        case 'success': return '#27ae60';
        case 'error': return '#e74c3c';
        case 'warning': return '#f39c12';
        default: return '#3498db';
    }
}

// Service Worker registration for PWA capabilities (optional enhancement)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // Only register service worker if we have one
        navigator.serviceWorker.getRegistrations().then(function(registrations) {
            // Service worker would be implemented separately if needed
        });
    });
}

// Export functions for testing (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        formatNumber,
        formatDate,
        TRM_RATE
    };
}
