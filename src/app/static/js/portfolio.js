// Portfolio analysis specific JavaScript

// Update summary cards
function updateSummaryCards(results) {
    const summaryCards = document.getElementById('summaryCards');
    
    if (!results.optimal_portfolios || !results.optimal_portfolios.max_sharpe) {
        summaryCards.innerHTML = `<div class="col-12"><p class="text-warning">${_('Failed to calculate optimal portfolio')}</p></div>`;
        return;
    }
    
    const maxSharpe = results.optimal_portfolios.max_sharpe.metrics;
    const monteCarloStats = results.monte_carlo.summary_stats;
    
    summaryCards.innerHTML = `
        <div class="col-lg-3 col-md-6 mb-3">
            <div class="card metrics-card bg-primary text-white">
                <div class="card-body text-center">
                    <div class="metrics-value">${formatPercent(maxSharpe.expected_return)}</div>
                    <div class="metrics-label">${_('Expected Return')}</div>
                    <small>${_('Optimal Portfolio')}</small>
                </div>
            </div>
        </div>
        <div class="col-lg-3 col-md-6 mb-3">
            <div class="card metrics-card bg-info text-white">
                <div class="card-body text-center">
                    <div class="metrics-value">${formatPercent(maxSharpe.risk)}</div>
                    <div class="metrics-label">${_('Risk')}</div>
                    <small>${_('Annual Standard Deviation')}</small>
                </div>
            </div>
        </div>
        <div class="col-lg-3 col-md-6 mb-3">
            <div class="card metrics-card bg-success text-white">
                <div class="card-body text-center">
                    <div class="metrics-value">${formatNumber(maxSharpe.sharpe_ratio)}</div>
                    <div class="metrics-label">${_('Sharpe Ratio')}</div>
                    <small>${_('Risk-adjusted Return')}</small>
                </div>
            </div>
        </div>
        <div class="col-lg-3 col-md-6 mb-3">
            <div class="card metrics-card bg-warning text-dark">
                <div class="card-body text-center">
                    <div class="metrics-value">${formatLargeNumber(results.monte_carlo.simulations.length)}</div>
                    <div class="metrics-label">${_('Simulations')}</div>
                    <small>${_('Execution Count')}</small>
                </div>
            </div>
        </div>
    `;
}

// Generate and display charts
async function generateCharts(results) {
    try {
        // Send visualization request to backend
        const response = await fetch('/api/visualize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                results: results,
                chart_types: ['all'],  // Generate all charts
                language: currentLanguage
            })
        });
        
        const visualizationResult = await response.json();
        
        if (!response.ok) {
            throw new Error(visualizationResult.error || 'Chart generation failed');
        }
        
        const charts = visualizationResult.charts;
        
        // Display each chart - prioritize mathematical efficient frontier
        if (charts.mathematical_efficient_frontier) {
            const frontierData = JSON.parse(charts.mathematical_efficient_frontier);
            Plotly.newPlot('frontierChart', frontierData.data, frontierData.layout, {
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
            });
        } else if (charts.efficient_frontier) {
            const frontierData = JSON.parse(charts.efficient_frontier);
            Plotly.newPlot('frontierChart', frontierData.data, frontierData.layout, {
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
            });
        }
        
        // Reset tab state (to enable if target return exists)
        const targetReturnTab = document.getElementById('target-return-tab');
        const targetReturnDataTab = document.getElementById('target-return-data-tab');
        
        if (targetReturnTab) {
            targetReturnTab.classList.remove('disabled');
            targetReturnTab.removeAttribute('disabled');
        }
        if (targetReturnDataTab) {
            targetReturnDataTab.classList.remove('disabled');  
            targetReturnDataTab.removeAttribute('disabled');
        }

        // Asset allocation charts (all 3 types) and risk contribution charts
        const allocationChartConfigs = [
            { 
                allocationId: 'allocationChartMaxSharpe', 
                allocationKey: 'asset_allocation_max_sharpe',
                riskId: 'riskContributionChart',
                riskKey: 'risk_contribution_max_sharpe'
            },
            { 
                allocationId: 'allocationChartMinVariance', 
                allocationKey: 'asset_allocation_min_variance',
                riskId: 'minVarianceRiskContribution',
                riskKey: 'risk_contribution_min_variance'
            },
            { 
                allocationId: 'allocationChartTargetReturn', 
                allocationKey: 'asset_allocation_target_return',
                riskId: 'targetReturnRiskContribution', 
                riskKey: 'risk_contribution_target_return'
            }
        ];
        
        const plotConfig = {
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d', 'autoScale2d'],
            staticPlot: false
        };
        
        // Initial rendering is only for max Sharpe ratio (active tab)
        if (charts.asset_allocation_max_sharpe) {
            const allocationData = JSON.parse(charts.asset_allocation_max_sharpe);
            await Plotly.newPlot('allocationChartMaxSharpe', allocationData.data, allocationData.layout, plotConfig);
        }
        
        // Max Sharpe ratio risk contribution
        if (charts.risk_contribution || charts.risk_contribution_max_sharpe) {
            const riskKey = charts.risk_contribution_max_sharpe ? 'risk_contribution_max_sharpe' : 'risk_contribution';
            const riskContribData = JSON.parse(charts[riskKey]);
            await Plotly.newPlot('riskContributionChart', riskContribData.data, riskContribData.layout, plotConfig);
        }
        

        // Save remaining chart data to global variable (used when switching tabs)
        window.allocationChartsData = {};
        allocationChartConfigs.forEach(config => {
            if (charts[config.allocationKey]) {
                window.allocationChartsData[config.allocationId] = JSON.parse(charts[config.allocationKey]);
            }
            
            if (charts[config.riskKey]) {
                window.allocationChartsData[config.riskId] = JSON.parse(charts[config.riskKey]);
            }
        });



        // For backward compatibility
        if (charts.asset_allocation && !charts.asset_allocation_max_sharpe) {
            const allocationData = JSON.parse(charts.asset_allocation);
            await Plotly.newPlot('allocationChartMaxSharpe', allocationData.data, allocationData.layout, plotConfig);
        }
        
        // Set up tab event handlers
        setTimeout(() => {
            setupAllocationTabHandlers();
        }, 500);
        
        if (charts.correlation_matrix) {
            try {
                const correlationData = JSON.parse(charts.correlation_matrix);
                const correlationElement = document.getElementById('correlationChart');
                
                if (correlationElement) {
                    correlationElement.innerHTML = '';
                    correlationElement.correlationData = correlationData;
                    
                    Plotly.newPlot('correlationChart', 
                        correlationData.data, 
                        correlationData.layout, {
                            responsive: true,
                            displayModeBar: true,
                            modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
                        });
                }
            } catch (error) {
                console.error('Error plotting correlation chart:', error);
            }
        }
        
        if (charts.risk_return_scatter) {
            const assetsData = JSON.parse(charts.risk_return_scatter);
            Plotly.newPlot('assetsChart', assetsData.data, assetsData.layout, {
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
            });
        }
        
    } catch (error) {
        console.error('Chart generation error:', error);
        
        // Alternative display on error
        const errorMessage = `
            <div class="alert alert-warning text-center">
                <i class="bi bi-exclamation-triangle me-2"></i>
                An error occurred during chart generation: ${error.message}
            </div>
        `;
        
        document.getElementById('frontierChart').innerHTML = errorMessage;
    }
}

// Update data tables
function updateDataTables(results) {
    // Debug: Check results structure
    
    // Update tables for each portfolio type
    updatePortfolioTables(results);
    
    // Individual asset statistics table
    updateStatsTable(results);
}

// Update tables for each portfolio type
function updatePortfolioTables(results) {
    if (!results.optimal_portfolios) {
        console.warn('No optimal portfolios data available');
        return;
    }
    
    const portfolioTypes = [
        { key: 'max_sharpe', tableId: 'portfolioTableMaxSharpe', metricsId: 'metricsTableMaxSharpe' },
        { key: 'min_variance', tableId: 'portfolioTableMinVariance', metricsId: 'metricsTableMinVariance' },
        { key: 'target_return', tableId: 'portfolioTableTargetReturn', metricsId: 'metricsTableTargetReturn' }
    ];
    
    // First enable all tabs (reset)
    const targetReturnTab = document.getElementById('target-return-tab');
    const targetReturnDataTab = document.getElementById('target-return-data-tab');
    
    if (targetReturnTab) {
        targetReturnTab.classList.remove('disabled');
        targetReturnTab.removeAttribute('disabled');
    }
    if (targetReturnDataTab) {
        targetReturnDataTab.classList.remove('disabled');
        targetReturnDataTab.removeAttribute('disabled');
    }
    
    portfolioTypes.forEach(portfolio => {
        if (results.optimal_portfolios[portfolio.key]) {
            updateSinglePortfolioTable(
                results.optimal_portfolios[portfolio.key], 
                portfolio.tableId, 
                portfolio.metricsId
            );
        } else {
            // Display when no data
            const tbody = document.querySelector(`#${portfolio.tableId} tbody`);
            const metricsTbody = document.querySelector(`#${portfolio.metricsId} tbody`);
            
            if (tbody) {
                if (portfolio.key === 'target_return') {
                    tbody.innerHTML = '<tr><td colspan="2" class="text-center text-muted"><i class="bi bi-info-circle me-2"></i>Target return not set</td></tr>';
                } else {
                    tbody.innerHTML = '<tr><td colspan="2" class="text-center text-muted">No data</td></tr>';
                }
            }
            if (metricsTbody) {
                if (portfolio.key === 'target_return') {
                    metricsTbody.innerHTML = '<tr><td colspan="2" class="text-center text-muted"><i class="bi bi-info-circle me-2"></i>Target return not set</td></tr>';
                } else {
                    metricsTbody.innerHTML = '<tr><td colspan="2" class="text-center text-muted">No data</td></tr>';
                }
            }
            
            // For target return, also disable the tab
            if (portfolio.key === 'target_return') {
                const targetReturnDataTab = document.getElementById('target-return-data-tab');
                if (targetReturnDataTab) {
                    targetReturnDataTab.classList.add('disabled');
                    targetReturnDataTab.setAttribute('disabled', 'true');
                }
            }
        }
    });
    
    // Update old table for backward compatibility (if it still exists)
    const oldTable = document.querySelector('#portfolioTable tbody');
    if (oldTable && results.optimal_portfolios.max_sharpe) {
        updateSinglePortfolioTable(results.optimal_portfolios.max_sharpe, 'portfolioTable');
    }
}

// Update single portfolio table
function updateSinglePortfolioTable(portfolioData, tableId, metricsTableId = null) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    
    if (!tbody || !portfolioData.weights) {
        console.warn(`Table ${tableId} not found or no weights data`);
        return;
    }
    
    const weights = portfolioData.weights;
    
    // Sort by allocation
    const sortedWeights = Object.entries(weights)
        .sort((a, b) => b[1] - a[1])
        .map(([asset, weight]) => ({
            asset: asset,
            weight: weight
        }));
    
    tbody.innerHTML = sortedWeights.map(item => `
        <tr>
            <td><strong>${item.asset}</strong></td>
            <td>${formatPercent(item.weight)}</td>
        </tr>
    `).join('');
    
    // Also update metrics table
    if (metricsTableId && portfolioData.metrics) {
        updateMetricsTable(portfolioData.metrics, metricsTableId);
    }
}

// Update metrics table
function updateMetricsTable(metrics, tableId) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    
    if (!tbody) {
        console.warn(`Metrics table ${tableId} not found`);
        return;
    }
    
    const metricsData = [
        { label: _('Expected Return'), value: formatPercent(metrics.expected_return), class: 'metrics-positive' },
        { label: _('Risk (Standard Deviation)'), value: formatPercent(metrics.risk), class: 'metrics-neutral' },
        { label: _('Sharpe Ratio'), value: formatNumber(metrics.sharpe_ratio), class: metrics.sharpe_ratio > 0 ? 'metrics-positive' : 'metrics-negative' },
        { label: _('VaR (95%)'), value: metrics.var_95 ? formatPercent(metrics.var_95) : 'N/A', class: 'metrics-neutral' }
    ];
    
    tbody.innerHTML = metricsData.map(item => `
        <tr>
            <td><strong>${item.label}</strong></td>
            <td class="${item.class}">${item.value}</td>
        </tr>
    `).join('');
}

// Update individual asset statistics table
function updateStatsTable(results) {
    const tbody = document.querySelector('#statsTable tbody');
    
    if (!results.asset_statistics) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted">${_('No data')}</td></tr>`;
        return;
    }
    
    const stats = results.asset_statistics;
    
    // Sort by Sharpe ratio
    const sortedStats = Object.entries(stats)
        .sort((a, b) => b[1].sharpe_ratio - a[1].sharpe_ratio)
        .map(([asset, stat]) => ({
            asset: asset,
            ...stat
        }));
    
    tbody.innerHTML = sortedStats.map(item => {
        const sharpeClass = item.sharpe_ratio > 0 ? 'metrics-positive' : 'metrics-negative';
        
        return `
            <tr>
                <td><strong>${item.asset}</strong></td>
                <td>${formatPercent(item.expected_return)}</td>
                <td>${formatPercent(item.risk)}</td>
                <td class="${sharpeClass}">${formatNumber(item.sharpe_ratio)}</td>
            </tr>
        `;
    }).join('');
}

// Portfolio details modal (for future expansion)
function showPortfolioDetails(portfolioType) {
    if (!currentResults || !currentResults.optimal_portfolios) {
        showError('No data to display');
        return;
    }
    
    const portfolio = currentResults.optimal_portfolios[portfolioType];
    if (!portfolio) {
        showError('Specified portfolio not found');
        return;
    }
    
    // TODO: Implement details modal
}

// Redraw charts (on window resize)
function redrawCharts() {
    const chartIds = ['frontierChart', 'allocationChartMaxSharpe', 'allocationChartMinVariance',
                     'allocationChartTargetReturn', 'riskContributionChart', 
                     'correlationChart', 'assetsChart'];
    
    // Skip redrawing asset allocation charts as they are fixed size
    const allocationChartIds = ['allocationChartMaxSharpe', 'allocationChartMinVariance', 'allocationChartTargetReturn'];
    
    chartIds.forEach(chartId => {
        const element = document.getElementById(chartId);
        if (element && element.data) {
            // Disable auto-resize for asset allocation charts
            if (allocationChartIds.includes(chartId)) {
                // Asset allocation charts are fixed size, so no resize
                return;
            }
            
            try {
                Plotly.Plots.resize(element);
            } catch (error) {
                console.warn(`Chart resize failed for ${chartId}:`, error);
            }
        }
    });
}

// Window resize event listener (with debounce)
let resizeTimeout;
window.addEventListener('resize', function() {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(redrawCharts, 500); // Longer debounce time
});

// Chart resize and asset allocation chart processing on tab switch
document.addEventListener('shown.bs.tab', function(event) {
    setTimeout(() => {
        redrawCharts();
        
        const activeTab = event.target.getAttribute('data-bs-target');
        
        // Special handling for correlation analysis tab
        if (activeTab === '#correlation') {
            const correlationElement = document.getElementById('correlationChart');
            
            if (correlationElement && correlationElement.correlationData) {
                Plotly.newPlot('correlationChart', 
                    correlationElement.correlationData.data, 
                    correlationElement.correlationData.layout, {
                        responsive: true,
                        displayModeBar: true,
                        modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
                    });
            } else if (correlationElement && correlationElement.data) {
                Plotly.redraw('correlationChart');
            }
        }
    }, 100);
});

// Define chart rendering function for asset allocation tab switching
function setupAllocationTabHandlers() {
    // Set up Bootstrap 5 tab event listeners
    const allocationTabs = document.querySelectorAll('#allocationTabs button[data-bs-toggle="pill"]');
    
    allocationTabs.forEach((tab, index) => {
        
        // Bootstrap 5 pill tab event
        tab.addEventListener('shown.bs.tab', function(event) {
            
            if (!window.allocationChartsData) {
                console.warn('No allocation chart data available');
                return;
            }
            
            const activeTab = event.target.getAttribute('data-bs-target');
            const plotConfig = {
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d', 'autoScale2d'],
                staticPlot: false
            };
            
            setTimeout(() => {
                if (activeTab === '#min-variance-allocation') {
                    
                    // Minimum variance tab
                    if (window.allocationChartsData['allocationChartMinVariance']) {
                        const element = document.getElementById('allocationChartMinVariance');
                        if (element && !element.data) {
                            Plotly.newPlot('allocationChartMinVariance', 
                                window.allocationChartsData['allocationChartMinVariance'].data, 
                                window.allocationChartsData['allocationChartMinVariance'].layout, 
                                plotConfig).catch(error => {
                                    console.error('Error rendering allocationChartMinVariance:', error);
                                });
                        }
                    } else {
                        console.warn('No data for allocationChartMinVariance');
                    }
                    
                    if (window.allocationChartsData['minVarianceRiskContribution']) {
                        const element = document.getElementById('minVarianceRiskContribution');
                        if (element && !element.data) {
                            Plotly.newPlot('minVarianceRiskContribution', 
                                window.allocationChartsData['minVarianceRiskContribution'].data, 
                                window.allocationChartsData['minVarianceRiskContribution'].layout, 
                                plotConfig).catch(error => {
                                    console.error('Error rendering minVarianceRiskContribution:', error);
                                });
                        }
                    } else {
                        console.warn('No data for minVarianceRiskContribution');
                    }
                    
                } else if (activeTab === '#target-return-allocation') {
                    
                    // Target return tab
                    if (window.allocationChartsData['allocationChartTargetReturn']) {
                        const element = document.getElementById('allocationChartTargetReturn');
                        if (element && !element.data) {
                            Plotly.newPlot('allocationChartTargetReturn', 
                                window.allocationChartsData['allocationChartTargetReturn'].data, 
                                window.allocationChartsData['allocationChartTargetReturn'].layout, 
                                plotConfig);
                        }
                    } else {
                        console.warn('No data for allocationChartTargetReturn');
                        
                        // Disable target return tab (only if no data really exists)
                        const targetReturnTab = document.getElementById('target-return-tab');
                        if (targetReturnTab && !window.allocationChartsData) {
                            targetReturnTab.classList.add('disabled');
                            targetReturnTab.setAttribute('disabled', 'true');
                        }
                        // Display message when target return is not set
                        const element = document.getElementById('allocationChartTargetReturn');
                        if (element) {
                            element.innerHTML = `
                                <div class="text-center text-muted p-4">
                                    <i class="bi bi-info-circle" style="font-size: 2rem;"></i>
                                    <h6 class="mt-3">Target return not set</h6>
                                    <p class="small">When you specify a target return in analysis settings,<br>the target return achievement portfolio will be displayed.</p>
                                </div>
                            `;
                        }
                    }
                    
                    if (window.allocationChartsData['targetReturnRiskContribution']) {
                        const element = document.getElementById('targetReturnRiskContribution');
                        if (element && !element.data) {
                            Plotly.newPlot('targetReturnRiskContribution', 
                                window.allocationChartsData['targetReturnRiskContribution'].data, 
                                window.allocationChartsData['targetReturnRiskContribution'].layout, 
                                plotConfig);
                        }
                    } else {
                        console.warn('No data for targetReturnRiskContribution');
                        // Display message when no risk decomposition data
                        const element = document.getElementById('targetReturnRiskContribution');
                        if (element && !window.allocationChartsData['allocationChartTargetReturn']) {
                            element.innerHTML = `
                                <div class="text-center text-muted p-4">
                                    <i class="bi bi-info-circle" style="font-size: 2rem;"></i>
                                    <h6 class="mt-3">No risk decomposition data</h6>
                                    <p class="small">When target return portfolio is calculated,<br>risk decomposition chart will be displayed.</p>
                                </div>
                            `;
                        }
                    }
                }
            }, 150); // Longer delay
        });
        
        // Also add click event (fallback)
        tab.addEventListener('click', function(event) {
            
            // Wait for Bootstrap tab activation
            setTimeout(() => {
                const shownEvent = new CustomEvent('shown.bs.tab', { detail: event.target });
                event.target.dispatchEvent(shownEvent);
            }, 200);
        });
    });
    
}

// Performance analysis (for future expansion)
function analyzePerformance(results) {
    if (!results.optimal_portfolios) return null;
    
    const maxSharpe = results.optimal_portfolios.max_sharpe;
    const monteCarloStats = results.monte_carlo.summary_stats;
    
    return {
        efficiency: maxSharpe.metrics.sharpe_ratio / monteCarloStats.max_sharpe,
        diversification: calculateDiversificationScore(maxSharpe.weights),
        riskLevel: classifyRiskLevel(maxSharpe.metrics.risk)
    };
}

// Calculate diversification score
function calculateDiversificationScore(weights) {
    const values = Object.values(weights);
    const numAssets = values.length;
    
    // Calculate using inverse of Herfindahl index
    const herfindahlIndex = values.reduce((sum, weight) => sum + Math.pow(weight, 2), 0);
    const effectiveAssets = 1 / herfindahlIndex;
    
    return effectiveAssets / numAssets; // Score from 0-1
}

// Risk level classification
function classifyRiskLevel(risk) {
    if (risk < 0.10) return 'Low';
    if (risk < 0.20) return 'Medium';
    if (risk < 0.35) return 'High';
    return 'Very High';
}

// Get chart data for export
function getChartsForExport() {
    const charts = {};
    const chartIds = ['frontierChart', 'allocationChartMaxSharpe', 'allocationChartMinVariance',
                     'allocationChartTargetReturn', 'riskContributionChart', 
                     'correlationChart', 'assetsChart'];
    
    chartIds.forEach(chartId => {
        const element = document.getElementById(chartId);
        if (element && element.data) {
            charts[chartId] = {
                data: element.data,
                layout: element.layout
            };
        }
    });
    
    return charts;
}

// Display alerts (recommendations based on results)
function showInsights(results) {
    const insights = generateInsights(results);
    
    if (insights.length > 0) {
        const insightHtml = insights.map(insight => `
            <div class="alert alert-${insight.type} alert-dismissible fade show" role="alert">
                <i class="bi bi-${insight.icon} me-2"></i>
                <strong>${insight.title}:</strong> ${insight.message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `).join('');
        
        // Display if there's an element to show insights
        const insightContainer = document.getElementById('insights');
        if (insightContainer) {
            insightContainer.innerHTML = insightHtml;
        }
    }
}

// Generate insights
function generateInsights(results) {
    const insights = [];
    
    if (!results.optimal_portfolios || !results.optimal_portfolios.max_sharpe) {
        return insights;
    }
    
    const portfolio = results.optimal_portfolios.max_sharpe;
    const weights = portfolio.weights;
    const metrics = portfolio.metrics;
    
    // Concentration check
    const maxWeight = Math.max(...Object.values(weights));
    if (maxWeight > 0.5) {
        insights.push({
            type: 'warning',
            icon: 'exclamation-triangle',
            title: 'Concentration Risk',
            message: `Maximum allocation is ${formatPercent(maxWeight)}, indicating concentration risk`
        });
    }
    
    // Sharpe ratio check
    if (metrics.sharpe_ratio < 0.5) {
        insights.push({
            type: 'info',
            icon: 'info-circle',
            title: 'Sharpe Ratio',
            message: 'Sharpe ratio is low, indicating limited risk-adjusted returns'
        });
    } else if (metrics.sharpe_ratio > 1.5) {
        insights.push({
            type: 'success',
            icon: 'check-circle',
            title: 'Excellent Performance',
            message: 'High Sharpe ratio indicates an efficient portfolio'
        });
    }
    
    // Risk level check
    const riskLevel = classifyRiskLevel(metrics.risk);
    if (riskLevel === 'Very High') {
        insights.push({
            type: 'danger',
            icon: 'exclamation-triangle',
            title: 'High Risk',
            message: 'Portfolio risk is at a very high level'
        });
    }
    
    return insights;
}

// Display simulation detailed data
function displaySimulationDetails(results) {
    if (!results.monte_carlo || !results.monte_carlo.detailed_analysis) {
        // No detailed analysis data available
        return;
    }
    
    const analysis = results.monte_carlo.detailed_analysis;
    
    // Display basic statistics
    displayBasicStats(analysis.basic_stats);
    
    // Update percentiles table
    updatePercentilesTable(analysis.percentiles);
    
    // Display tail percentiles
    displayTailPercentiles(analysis.tail_percentiles);
    
    // Display confidence intervals
    displayConfidenceIntervals(analysis.confidence_intervals);
    
    // Display efficiency metrics
    displayEfficiencyMetrics(analysis.efficiency_metrics);
}

// Display basic statistics
function displayBasicStats(basicStats) {
    const container = document.getElementById('basicStatsContent');
    if (!container) return;
    
    const stats = [
        {
            title: _('Return Statistics'),
            data: basicStats.return_stats,
            suffix: '%',
            multiplier: 100
        },
        {
            title: _('Risk Statistics'), 
            data: basicStats.risk_stats,
            suffix: '%',
            multiplier: 100
        },
        {
            title: _('Sharpe Ratio Statistics'),
            data: basicStats.sharpe_stats,
            suffix: '',
            multiplier: 1
        }
    ];
    
    let html = '';
    stats.forEach(stat => {
        html += `
            <div class="col-lg-4 mb-3">
                <h6 class="text-muted">${stat.title}</h6>
                <ul class="list-unstyled small">
                    <li><strong>${_('Mean')}:</strong> ${(stat.data.mean * stat.multiplier).toFixed(2)}${stat.suffix}</li>
                    <li><strong>${_('Std Dev')}:</strong> ${(stat.data.std * stat.multiplier).toFixed(2)}${stat.suffix}</li>
                    <li><strong>${_('Min')}:</strong> ${(stat.data.min * stat.multiplier).toFixed(2)}${stat.suffix}</li>
                    <li><strong>${_('Max')}:</strong> ${(stat.data.max * stat.multiplier).toFixed(2)}${stat.suffix}</li>
                    <li><strong>${_('Median')}:</strong> ${(stat.data.median * stat.multiplier).toFixed(2)}${stat.suffix}</li>
                </ul>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Update percentiles table
function updatePercentilesTable(percentiles) {
    const tbody = document.querySelector('#percentilesTable tbody');
    if (!tbody) return;
    
    let html = '';
    const percentileKeys = ['p5', 'p10', 'p25', 'p75', 'p90', 'p95'];
    
    percentileKeys.forEach(key => {
        if (percentiles[key]) {
            const p = percentiles[key];
            html += `
                <tr>
                    <td>${key.replace('p', '') + '%'}</td>
                    <td>${(p.return * 100).toFixed(2)}%</td>
                    <td>${(p.risk * 100).toFixed(2)}%</td>
                    <td>${p.sharpe.toFixed(3)}</td>
                </tr>
            `;
        }
    });
    
    tbody.innerHTML = html;
}

// Display tail percentiles of allocation distribution
function displayTailPercentiles(tailPercentiles) {
    const container = document.getElementById('varAnalysisContent');
    if (!container) return;
    
    const html = `
        <div class="row">
            <div class="col-6">
                <h6 class="text-muted">${_('Return Lower Tail')}</h6>
                <ul class="list-unstyled small">
                    <li><strong>${_('5th Percentile')}:</strong> ${(tailPercentiles.return_p5 * 100).toFixed(2)}%</li>
                    <li><strong>${_('1st Percentile')}:</strong> ${(tailPercentiles.return_p1 * 100).toFixed(2)}%</li>
                </ul>
            </div>
            <div class="col-6">
                <h6 class="text-muted">${_('Risk Upper Tail')}</h6>
                <ul class="list-unstyled small">
                    <li><strong>${_('95th Percentile')}:</strong> ${(tailPercentiles.risk_p95 * 100).toFixed(2)}%</li>
                    <li><strong>${_('99th Percentile')}:</strong> ${(tailPercentiles.risk_p99 * 100).toFixed(2)}%</li>
                </ul>
            </div>
        </div>
        <div class="mt-2">
            <small class="text-muted">
                <i class="bi bi-info-circle me-1"></i>
                ${_('Percentile values from the distribution of simulated portfolio allocations')}
            </small>
        </div>
    `;
    
    container.innerHTML = html;
}

// Display confidence intervals
function displayConfidenceIntervals(confidenceIntervals) {
    const container = document.getElementById('confidenceIntervalsContent');
    if (!container) return;
    
    const html = `
        <div class="row">
            <div class="col-12 mb-3">
                <h6 class="text-muted">${_('95% Confidence Interval')}</h6>
                <ul class="list-unstyled small">
                    <li><strong>${_('Return')}:</strong> ${(confidenceIntervals.return_ci_95[0] * 100).toFixed(2)}% ~ ${(confidenceIntervals.return_ci_95[1] * 100).toFixed(2)}%</li>
                    <li><strong>${_('Risk')}:</strong> ${(confidenceIntervals.risk_ci_95[0] * 100).toFixed(2)}% ~ ${(confidenceIntervals.risk_ci_95[1] * 100).toFixed(2)}%</li>
                    <li><strong>${_('Sharpe Ratio')}:</strong> ${confidenceIntervals.sharpe_ci_95[0].toFixed(3)} ~ ${confidenceIntervals.sharpe_ci_95[1].toFixed(3)}</li>
                </ul>
            </div>
            <div class="col-12">
                <h6 class="text-muted">${_('99% Confidence Interval')}</h6>
                <ul class="list-unstyled small">
                    <li><strong>${_('Return')}:</strong> ${(confidenceIntervals.return_ci_99[0] * 100).toFixed(2)}% ~ ${(confidenceIntervals.return_ci_99[1] * 100).toFixed(2)}%</li>
                </ul>
            </div>
        </div>
        <div class="mt-2">
            <small class="text-muted">
                <i class="bi bi-info-circle me-1"></i>
                ${_('Confidence intervals show the range containing 95%/99% of simulation results')}
            </small>
        </div>
    `;
    
    container.innerHTML = html;
}

// Display efficiency metrics
function displayEfficiencyMetrics(efficiencyMetrics) {
    const container = document.getElementById('efficiencyMetricsContent');
    if (!container) return;
    
    const totalPortfolios = efficiencyMetrics.portfolios_above_rf + 
                          (efficiencyMetrics.total_simulations || 10000) - efficiencyMetrics.portfolios_above_rf;
    
    const html = `
        <div class="col-lg-3 col-md-6 mb-3">
            <div class="card bg-light h-100">
                <div class="card-body text-center">
                    <h5 class="text-primary">${efficiencyMetrics.portfolios_above_rf}</h5>
                    <small class="text-muted">${_('Portfolios Above Risk-Free Rate')}</small>
                </div>
            </div>
        </div>
        <div class="col-lg-3 col-md-6 mb-3">
            <div class="card bg-light h-100">
                <div class="card-body text-center">
                    <h5 class="text-success">${efficiencyMetrics.portfolios_positive_sharpe}</h5>
                    <small class="text-muted">${_('Positive Sharpe Ratio')}</small>
                </div>
            </div>
        </div>
        <div class="col-lg-3 col-md-6 mb-3">
            <div class="card bg-light h-100">
                <div class="card-body text-center">
                    <h5 class="text-info">${efficiencyMetrics.best_sharpe_portfolio.sharpe.toFixed(3)}</h5>
                    <small class="text-muted">${_('Best Sharpe Ratio')}</small>
                </div>
            </div>
        </div>
        <div class="col-lg-3 col-md-6 mb-3">
            <div class="card bg-light h-100">
                <div class="card-body text-center">
                    <h5 class="text-warning">${(efficiencyMetrics.min_risk_portfolio.risk * 100).toFixed(2)}%</h5>
                    <small class="text-muted">${_('Minimum Risk')}</small>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// Simulation count comparison function
function compareSimulations() {
    const button = document.querySelector('[onclick="compareSimulations()"]');
    const resultContainer = document.getElementById('simulationComparisonResult');
    
    if (!button || !resultContainer) return;
    
    // Disable button and show loading
    button.disabled = true;
    button.innerHTML = '<i class="bi bi-arrow-repeat me-2"></i>Running...';
    
    // Get current settings
    const formData = getFormData();
    if (!formData) {
        button.disabled = false;
        button.innerHTML = '<i class="bi bi-arrow-repeat me-2"></i>Run Simulation Count Comparison';
        return;
    }
    
    // Simulation counts to compare
    formData.simulation_counts = [100, 1000, 5000, 10000];
    
    fetch('/api/compare-simulations', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({...formData, language: currentLanguage})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayComparisonResults(data.comparison_results, resultContainer);
        } else {
            throw new Error(data.error || 'Comparison failed');
        }
    })
    .catch(error => {
        console.error('Simulation comparison error:', error);
        resultContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle me-2"></i>
                An error occurred during comparison processing: ${error.message}
            </div>
        `;
        resultContainer.style.display = 'block';
    })
    .finally(() => {
        button.disabled = false;
        button.innerHTML = '<i class="bi bi-arrow-repeat me-2"></i>Run Simulation Count Comparison';
    });
}

// Display comparison results
function displayComparisonResults(comparisonData, container) {
    if (!comparisonData || !container) return;
    
    const counts = Object.keys(comparisonData)
                         .filter(key => key !== 'convergence_analysis')
                         .map(k => parseInt(k))
                         .sort((a, b) => a - b);
    
    let html = `
        <div class="row">
            <div class="col-12">
                <h6>Differences in Results by Simulation Count</h6>
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Simulation Count</th>
                                <th>Average Return</th>
                                <th>Average Risk</th>
                                <th>Best Sharpe Ratio</th>
                                <th>95% CI Width (Return)</th>
                            </tr>
                        </thead>
                        <tbody>
    `;
    
    counts.forEach(count => {
        const data = comparisonData[count.toString()];
        if (data) {
            const returnStats = data.basic_stats.return_stats;
            const ciWidth = data.confidence_intervals.return_ci_95[1] - data.confidence_intervals.return_ci_95[0];
            
            html += `
                <tr>
                    <td><strong>${count.toLocaleString()}</strong></td>
                    <td>${(returnStats.mean * 100).toFixed(2)}%</td>
                    <td>${(data.basic_stats.risk_stats.mean * 100).toFixed(2)}%</td>
                    <td>${data.best_sharpe.sharpe.toFixed(3)}</td>
                    <td>${(ciWidth * 100).toFixed(2)}%</td>
                </tr>
            `;
        }
    });
    
    html += `
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    
    // Display convergence analysis
    if (comparisonData.convergence_analysis) {
        const convergence = comparisonData.convergence_analysis.mean_convergence;
        html += `
            <div class="row mt-4">
                <div class="col-12">
                    <div class="alert alert-info">
                        <h6><i class="bi bi-graph-up me-2"></i>Convergence Analysis</h6>
                        <p class="mb-1"><strong>Recommended Minimum Simulation Count:</strong> ${convergence.recommended_min_count.toLocaleString()} times</p>
                        <p class="mb-0"><small>Return Stability Coefficient: ${convergence.return_stability.coefficient_of_variation.toFixed(4)}</small></p>
                        <p class="mb-0"><small>Risk Stability Coefficient: ${convergence.risk_stability.coefficient_of_variation.toFixed(4)}</small></p>
                    </div>
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
    container.style.display = 'block';
}

// Common function to get form data
function getFormData() {
    const tickers = getSelectedTickers();
    const startDate = document.getElementById('startDate')?.value;
    const endDate = document.getElementById('endDate')?.value;
    const riskFreeRate = parseFloat(document.getElementById('riskFreeRate')?.value || 0.005) / 100;
    
    if (tickers.length === 0 || !startDate || !endDate) {
        alert('Required parameters are missing');
        return null;
    }
    
    const data = {
        tickers: tickers,
        start_date: startDate,
        end_date: endDate,
        risk_free_rate: riskFreeRate,
        simulation_count: parseInt(document.getElementById('simulationCount').value)
    };
    
    // When target return is enabled
    const enableTargetReturnCheckbox = document.getElementById('enableTargetReturn');
    const targetReturnInput = document.getElementById('targetReturn');
    
    if (enableTargetReturnCheckbox && enableTargetReturnCheckbox.checked && targetReturnInput) {
        data.target_return = parseFloat(targetReturnInput.value); // Already in decimal format
    }
    
    return data;
}
