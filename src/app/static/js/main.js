// メインJavaScript - 共通機能

// グローバル変数
let currentResults = null;
let tickerCount = 0;

// アプリケーション初期化
function initializeApp() {
    setupDateDefaults();
    setupRangeSliders();
    setupTooltips();
    addInitialTickers();
    setupFormValidation();
}

// 日付のデフォルト値設定
function setupDateDefaults() {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setFullYear(endDate.getFullYear() - 3); // 3年前をデフォルト

    document.getElementById('endDate').valueAsDate = endDate;
    document.getElementById('startDate').valueAsDate = startDate;
}

// レンジスライダーの設定
function setupRangeSliders() {
    // 無リスク金利
    const riskFreeRateRange = document.getElementById('riskFreeRateRange');
    const riskFreeRateValue = document.getElementById('riskFreeRateValue');
    const riskFreeRate = document.getElementById('riskFreeRate');
    
    riskFreeRateRange.addEventListener('input', function() {
        const value = this.value;
        riskFreeRateValue.textContent = value;
        riskFreeRate.value = (value / 100).toString(); // パーセントを小数に変換
    });

    // 目標リターン
    const targetReturnRange = document.getElementById('targetReturnRange');
    const targetReturnValue = document.getElementById('targetReturnValue');
    const targetReturn = document.getElementById('targetReturn');
    
    targetReturnRange.addEventListener('input', function() {
        const value = this.value;
        targetReturnValue.textContent = value;
        targetReturn.value = (value / 100).toString(); // パーセントを小数に変換
    });

    // 目標リターンの有効/無効切り替え
    document.getElementById('enableTargetReturn').addEventListener('change', function() {
        const targetReturnGroup = document.getElementById('targetReturnGroup');
        if (this.checked) {
            targetReturnGroup.style.display = 'block';
        } else {
            targetReturnGroup.style.display = 'none';
        }
    });

    // シミュレーション回数
    const simulationCountRange = document.getElementById('simulationCountRange');
    const simulationCountValue = document.getElementById('simulationCountValue');
    const simulationCount = document.getElementById('simulationCount');
    
    simulationCountRange.addEventListener('input', function() {
        const value = this.value;
        simulationCountValue.textContent = parseInt(value).toLocaleString();
        simulationCount.value = value;
    });
}

// ツールチップの設定
function setupTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// 初期ティッカー入力フィールドを追加
function addInitialTickers() {
    addTickerInput('AAPL');
    addTickerInput('MSFT');
    addTickerInput('GOOGL');
}

// ティッカー入力フィールドを追加
function addTickerInput(defaultValue = '') {
    if (tickerCount >= 20) {
        showError('最大20銘柄まで入力可能です');
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
               placeholder="例: AAPL" 
               value="${defaultValue}"
               maxlength="10"
               style="text-transform: uppercase;">
        <div class="ticker-validation-icon">
            <!-- バリデーション結果のアイコン -->
        </div>
        <button type="button" class="btn btn-outline-danger btn-sm" onclick="removeTickerInput(this)">
            <i class="bi bi-trash"></i>
        </button>
    `;
    
    tickerInputs.appendChild(inputGroup);
    
    // リアルタイムバリデーション
    const input = inputGroup.querySelector('input');
    input.addEventListener('input', function() {
        validateTicker(this);
    });
    
    input.addEventListener('blur', function() {
        validateTickerExists(this);
    });

    // 最低2銘柄になったら削除ボタンを有効化
    updateRemoveButtons();
}

// ティッカー入力フィールドを削除
function removeTickerInput(button) {
    if (tickerCount <= 2) {
        showError('最低2銘柄が必要です');
        return;
    }
    
    button.closest('.ticker-input').remove();
    tickerCount--;
    updateRemoveButtons();
}

// 削除ボタンの有効/無効を更新
function updateRemoveButtons() {
    const removeButtons = document.querySelectorAll('.ticker-input button');
    removeButtons.forEach(button => {
        button.disabled = tickerCount <= 2;
    });
}

// ティッカーの形式バリデーション
function validateTicker(input) {
    const ticker = input.value.trim().toUpperCase();
    const icon = input.nextElementSibling;
    
    if (!ticker) {
        input.classList.remove('is-valid', 'is-invalid');
        icon.innerHTML = '';
        return false;
    }
    
    // 基本的な形式チェック（英数字、ドット、ハイフン）
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

// ティッカーの存在確認（API呼び出し）
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
            body: JSON.stringify({ tickers: [ticker] })
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

// フォームバリデーションの設定
function setupFormValidation() {
    const form = document.getElementById('portfolioForm');
    form.addEventListener('submit', handleFormSubmit);
}

// フォーム送信処理
async function handleFormSubmit(event) {
    event.preventDefault();
    
    if (!validateForm()) {
        return;
    }
    
    // 分析開始時にプレースホルダーを非表示
    const placeholderArea = document.getElementById('placeholderArea');
    placeholderArea.classList.remove('d-flex');
    placeholderArea.style.display = 'none';
    
    const formData = getFormData();
    await performAnalysis(formData);
}

// フォーム全体のバリデーション
function validateForm() {
    let isValid = true;
    const errors = [];
    
    // ティッカーの検証
    const tickers = getTickers();
    if (tickers.length < 2) {
        errors.push('最低2銘柄が必要です');
        isValid = false;
    } else if (tickers.length > 20) {
        errors.push('最大20銘柄まで入力可能です');
        isValid = false;
    }
    
    // 重複チェック
    const uniqueTickers = [...new Set(tickers)];
    if (uniqueTickers.length !== tickers.length) {
        errors.push('重複するティッカーシンボルがあります');
        isValid = false;
    }
    
    // 日付の検証
    const startDate = new Date(document.getElementById('startDate').value);
    const endDate = new Date(document.getElementById('endDate').value);
    const today = new Date();
    
    if (startDate >= endDate) {
        errors.push('開始日は終了日より前の日付を指定してください');
        isValid = false;
    }
    
    if (endDate > today) {
        errors.push('終了日に未来の日付は指定できません');
        isValid = false;
    }
    
    const diffTime = Math.abs(endDate - startDate);
    const diffYears = diffTime / (1000 * 60 * 60 * 24 * 365);
    
    if (diffYears < 1) {
        errors.push('分析期間は最低1年必要です');
        isValid = false;
    } else if (diffYears > 10) {
        errors.push('分析期間は最大10年まで可能です');
        isValid = false;
    }
    
    if (!isValid) {
        showError('入力エラー: ' + errors.join(', '));
    }
    
    return isValid;
}

// ティッカーリストを取得
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

// フォームデータを取得
function getFormData() {
    const data = {
        tickers: getTickers(),
        start_date: document.getElementById('startDate').value,
        end_date: document.getElementById('endDate').value,
        risk_free_rate: parseFloat(document.getElementById('riskFreeRate').value),
        simulation_count: parseInt(document.getElementById('simulationCount').value)
    };
    
    // 目標リターンが有効な場合
    if (document.getElementById('enableTargetReturn').checked) {
        data.target_return = parseFloat(document.getElementById('targetReturn').value);
    }
    
    return data;
}

// ポートフォリオ分析実行
async function performAnalysis(formData) {
    try {
        showProgress('分析を開始しています...', 0);
        
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        updateProgress('データを処理中...', 50);
        
        const result = await response.json();
        
        if (!response.ok) {
            const errorMsg = result.error || 'サーバーエラーが発生しました';
            const details = result.details ? ` (詳細: ${result.details})` : '';
            throw new Error(errorMsg + details);
        }
        
        updateProgress('結果を表示中...', 80);
        
        // 結果を保存
        currentResults = result;
        
        // 結果表示
        await displayResults(result);
        
        updateProgress('完了', 100);
        
        setTimeout(() => {
            hideProgress();
        }, 500);
        
    } catch (error) {
        hideProgress();
        console.error('Analysis error:', error);
        showError('分析中にエラーが発生しました: ' + error.message);
        // プレースホルダーは再表示しない（結果エリアがある場合）
        if (!document.getElementById('resultsArea').classList.contains('show')) {
            const placeholderArea = document.getElementById('placeholderArea');
            placeholderArea.classList.add('d-flex');
            placeholderArea.style.display = 'flex';
        }
    }
}

// 結果の表示
async function displayResults(results) {
    // 警告メッセージの表示
    if (results.warnings && results.warnings.length > 0) {
        showWarnings(results.warnings);
    }
    
    // サマリーカードの更新
    updateSummaryCards(results);
    
    // 分析時刻の表示
    document.getElementById('analysisTime').textContent = 
        '分析実行: ' + new Date().toLocaleString('ja-JP');
    
    // グラフの生成と表示
    await generateCharts(results);
    
    // データテーブルの更新
    updateDataTables(results);
    
    // 結果エリアを表示
    document.getElementById('resultsArea').classList.add('show');
    
    // 結果エリアまでスクロール
    document.getElementById('resultsArea').scrollIntoView({ 
        behavior: 'smooth',
        block: 'start'
    });
}

// 警告メッセージの表示
function showWarnings(warnings) {
    warnings.forEach(warning => {
        console.warn('Warning:', warning);
    });
    
    // TODO: 警告メッセージのUIを実装
}

// フォームのリセット
function resetForm() {
    document.getElementById('portfolioForm').reset();
    
    // ティッカー入力をクリア
    document.getElementById('tickerInputs').innerHTML = '';
    tickerCount = 0;
    
    // 結果エリアを隠す
    document.getElementById('resultsArea').classList.remove('show');
    const placeholderArea = document.getElementById('placeholderArea');
    placeholderArea.classList.add('d-flex');
    placeholderArea.style.display = 'flex';
    
    // デフォルト値を再設定
    setupDateDefaults();
    addInitialTickers();
    
    // バリデーションクラスをクリア
    document.querySelectorAll('.is-valid, .is-invalid').forEach(el => {
        el.classList.remove('is-valid', 'is-invalid');
    });
}

// 結果のエクスポート
async function exportResults(format = 'json') {
    if (!currentResults) {
        showError('エクスポートする結果がありません');
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
                results: currentResults
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // ファイルダウンロード
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
        showError('エクスポート中にエラーが発生しました: ' + error.message);
    }
}

// 数値フォーマット関数
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