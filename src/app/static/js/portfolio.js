// ポートフォリオ分析専用JavaScript

// サマリーカードの更新
function updateSummaryCards(results) {
    const summaryCards = document.getElementById('summaryCards');
    
    if (!results.optimal_portfolios || !results.optimal_portfolios.max_sharpe) {
        summaryCards.innerHTML = '<div class="col-12"><p class="text-warning">最適ポートフォリオの計算に失敗しました</p></div>';
        return;
    }
    
    const maxSharpe = results.optimal_portfolios.max_sharpe.metrics;
    const monteCarloStats = results.monte_carlo.summary_stats;
    
    summaryCards.innerHTML = `
        <div class="col-lg-3 col-md-6 mb-3">
            <div class="card metrics-card bg-primary text-white">
                <div class="card-body text-center">
                    <div class="metrics-value">${formatPercent(maxSharpe.expected_return)}</div>
                    <div class="metrics-label">期待リターン</div>
                    <small>最適ポートフォリオ</small>
                </div>
            </div>
        </div>
        <div class="col-lg-3 col-md-6 mb-3">
            <div class="card metrics-card bg-info text-white">
                <div class="card-body text-center">
                    <div class="metrics-value">${formatPercent(maxSharpe.risk)}</div>
                    <div class="metrics-label">リスク</div>
                    <small>年率標準偏差</small>
                </div>
            </div>
        </div>
        <div class="col-lg-3 col-md-6 mb-3">
            <div class="card metrics-card bg-success text-white">
                <div class="card-body text-center">
                    <div class="metrics-value">${formatNumber(maxSharpe.sharpe_ratio)}</div>
                    <div class="metrics-label">シャープレシオ</div>
                    <small>リスク調整後リターン</small>
                </div>
            </div>
        </div>
        <div class="col-lg-3 col-md-6 mb-3">
            <div class="card metrics-card bg-warning text-dark">
                <div class="card-body text-center">
                    <div class="metrics-value">${formatLargeNumber(results.monte_carlo.simulations.length)}</div>
                    <div class="metrics-label">シミュレーション</div>
                    <small>実行回数</small>
                </div>
            </div>
        </div>
    `;
}

// グラフの生成と表示
async function generateCharts(results) {
    try {
        // バックエンドに可視化リクエストを送信
        const response = await fetch('/api/visualize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                results: results,
                chart_types: ['all']  // 全てのグラフを生成
            })
        });
        
        const visualizationResult = await response.json();
        
        if (!response.ok) {
            throw new Error(visualizationResult.error || 'グラフ生成に失敗しました');
        }
        
        const charts = visualizationResult.charts;
        
        // 各グラフを表示
        if (charts.efficient_frontier) {
            const frontierData = JSON.parse(charts.efficient_frontier);
            Plotly.newPlot('frontierChart', frontierData.data, frontierData.layout, {
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
            });
        }
        
        if (charts.asset_allocation) {
            const allocationData = JSON.parse(charts.asset_allocation);
            Plotly.newPlot('allocationChart', allocationData.data, allocationData.layout, {
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
            });
        }
        
        if (charts.risk_contribution) {
            const riskContribData = JSON.parse(charts.risk_contribution);
            Plotly.newPlot('riskContributionChart', riskContribData.data, riskContribData.layout, {
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
            });
        }
        
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
        
        // エラー時は代替表示
        const errorMessage = `
            <div class="alert alert-warning text-center">
                <i class="bi bi-exclamation-triangle me-2"></i>
                グラフの生成中にエラーが発生しました: ${error.message}
            </div>
        `;
        
        document.getElementById('frontierChart').innerHTML = errorMessage;
    }
}

// データテーブルの更新
function updateDataTables(results) {
    // 最適ポートフォリオ配分テーブル
    updatePortfolioTable(results);
    
    // 個別資産統計テーブル
    updateStatsTable(results);
}

// ポートフォリオ配分テーブルの更新
function updatePortfolioTable(results) {
    const tbody = document.querySelector('#portfolioTable tbody');
    
    if (!results.optimal_portfolios || !results.optimal_portfolios.max_sharpe) {
        tbody.innerHTML = '<tr><td colspan="2" class="text-center text-muted">データなし</td></tr>';
        return;
    }
    
    const weights = results.optimal_portfolios.max_sharpe.weights;
    
    // 配分でソート
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
}

// 個別資産統計テーブルの更新
function updateStatsTable(results) {
    const tbody = document.querySelector('#statsTable tbody');
    
    if (!results.asset_statistics) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">データなし</td></tr>';
        return;
    }
    
    const stats = results.asset_statistics;
    
    // シャープレシオでソート
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

// ポートフォリオ詳細モーダル（将来拡張用）
function showPortfolioDetails(portfolioType) {
    if (!currentResults || !currentResults.optimal_portfolios) {
        showError('表示するデータがありません');
        return;
    }
    
    const portfolio = currentResults.optimal_portfolios[portfolioType];
    if (!portfolio) {
        showError('指定されたポートフォリオが見つかりません');
        return;
    }
    
    // TODO: 詳細モーダルの実装
}

// グラフの再描画（ウィンドウサイズ変更時）
function redrawCharts() {
    const chartIds = ['frontierChart', 'allocationChart', 'riskContributionChart', 
                     'correlationChart', 'assetsChart'];
    
    chartIds.forEach(chartId => {
        const element = document.getElementById(chartId);
        if (element && element.data) {
            Plotly.Plots.resize(element);
        }
    });
}

// ウィンドウリサイズイベントリスナー
window.addEventListener('resize', function() {
    setTimeout(redrawCharts, 300);
});

// タブ切り替え時のグラフリサイズ
document.addEventListener('shown.bs.tab', function(event) {
    setTimeout(() => {
        redrawCharts();
        
        // 相関分析タブの特別処理
        const activeTab = event.target.getAttribute('data-bs-target');
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

// パフォーマンス分析（将来拡張用）
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

// 分散投資スコア計算
function calculateDiversificationScore(weights) {
    const values = Object.values(weights);
    const numAssets = values.length;
    
    // ハーフィンダール指数の逆数で計算
    const herfindahlIndex = values.reduce((sum, weight) => sum + Math.pow(weight, 2), 0);
    const effectiveAssets = 1 / herfindahlIndex;
    
    return effectiveAssets / numAssets; // 0-1のスコア
}

// リスクレベル分類
function classifyRiskLevel(risk) {
    if (risk < 0.10) return 'Low';
    if (risk < 0.20) return 'Medium';
    if (risk < 0.35) return 'High';
    return 'Very High';
}

// エクスポート用のチャートデータ取得
function getChartsForExport() {
    const charts = {};
    const chartIds = ['frontierChart', 'allocationChart', 'riskContributionChart', 
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

// アラート表示（結果に基づく推奨事項）
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
        
        // インサイトを表示する要素があれば表示
        const insightContainer = document.getElementById('insights');
        if (insightContainer) {
            insightContainer.innerHTML = insightHtml;
        }
    }
}

// インサイト生成
function generateInsights(results) {
    const insights = [];
    
    if (!results.optimal_portfolios || !results.optimal_portfolios.max_sharpe) {
        return insights;
    }
    
    const portfolio = results.optimal_portfolios.max_sharpe;
    const weights = portfolio.weights;
    const metrics = portfolio.metrics;
    
    // 集中度チェック
    const maxWeight = Math.max(...Object.values(weights));
    if (maxWeight > 0.5) {
        insights.push({
            type: 'warning',
            icon: 'exclamation-triangle',
            title: '集中リスク',
            message: `最大配分が${formatPercent(maxWeight)}と高く、集中リスクがあります`
        });
    }
    
    // シャープレシオチェック
    if (metrics.sharpe_ratio < 0.5) {
        insights.push({
            type: 'info',
            icon: 'info-circle',
            title: 'シャープレシオ',
            message: 'シャープレシオが低いため、リスクに対するリターンが限定的です'
        });
    } else if (metrics.sharpe_ratio > 1.5) {
        insights.push({
            type: 'success',
            icon: 'check-circle',
            title: '優秀なパフォーマンス',
            message: 'シャープレシオが高く、効率的なポートフォリオです'
        });
    }
    
    // リスクレベルチェック
    const riskLevel = classifyRiskLevel(metrics.risk);
    if (riskLevel === 'Very High') {
        insights.push({
            type: 'danger',
            icon: 'exclamation-triangle',
            title: '高リスク',
            message: 'ポートフォリオのリスクが非常に高いレベルです'
        });
    }
    
    return insights;
}
