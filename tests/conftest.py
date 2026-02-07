"""
共通テストフィクスチャ
"""
import sys
import os
import pytest
import numpy as np
import pandas as pd

# src ディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def app():
    """テスト用Flaskアプリケーション"""
    from app import create_app
    app = create_app('development')
    app.config['TESTING'] = True
    app.config['SERVER_NAME'] = 'localhost'
    return app


@pytest.fixture
def client(app):
    """テスト用Flaskクライアント"""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """リクエストコンテキスト（flask_babel.gettext がsessionを参照するため必須）"""
    with app.test_request_context():
        yield


@pytest.fixture
def request_context(app):
    """リクエストコンテキスト（sessionを使用する場合）"""
    with app.test_request_context():
        yield


@pytest.fixture
def mock_config():
    """バリデーション用モックコンフィグ"""
    class MockConfig:
        MIN_ASSETS = 2
        MAX_ASSETS = 20
        MIN_ANALYSIS_YEARS = 1
        MAX_ANALYSIS_YEARS = 31
        MIN_SIMULATION_COUNT = 1000
        MAX_SIMULATION_COUNT = 50000
    return MockConfig()


@pytest.fixture
def sample_price_data():
    """テスト用株価データ（3銘柄×100日）"""
    np.random.seed(42)
    dates = pd.bdate_range(start='2024-01-02', periods=100)
    
    # ランダムウォークで模擬株価を生成
    prices = {}
    for ticker, start_price in [('AAPL', 150.0), ('GOOGL', 140.0), ('MSFT', 380.0)]:
        daily_returns = np.random.normal(0.0005, 0.02, 100)
        price_series = start_price * np.cumprod(1 + daily_returns)
        prices[ticker] = price_series

    df = pd.DataFrame(prices, index=dates)
    return df


@pytest.fixture
def sample_returns_data(sample_price_data):
    """テスト用日次リターンデータ"""
    return sample_price_data.pct_change().dropna()


@pytest.fixture
def loaded_calculator(sample_price_data):
    """データ読み込み済みのPortfolioCalculator"""
    from app.utils.calculator import PortfolioCalculator
    calc = PortfolioCalculator()
    calc.load_data(sample_price_data, risk_free_rate=0.01)
    return calc


@pytest.fixture
def sample_mc_results(loaded_calculator):
    """テスト用モンテカルロシミュレーション結果"""
    np.random.seed(42)
    return loaded_calculator.monte_carlo_simulation(500)


@pytest.fixture
def sample_analysis_results(loaded_calculator, sample_mc_results):
    """テスト用の完全な分析結果（API / Visualizer テスト用）"""
    np.random.seed(42)
    
    asset_stats = loaded_calculator.calculate_asset_statistics()
    correlation_matrix = loaded_calculator.calculate_correlation_matrix()
    detailed_analysis = loaded_calculator.analyze_monte_carlo_results(sample_mc_results)
    max_sharpe = loaded_calculator.optimize_portfolio()
    min_var = loaded_calculator.optimize_min_variance_portfolio()
    
    optimal_portfolios = {}
    if max_sharpe['success']:
        weights_array = np.array(list(max_sharpe['weights'].values()))
        max_sharpe['risk_decomposition'] = loaded_calculator.risk_decomposition(weights_array)
        optimal_portfolios['max_sharpe'] = max_sharpe
    if min_var['success']:
        weights_array = np.array(list(min_var['weights'].values()))
        min_var['risk_decomposition'] = loaded_calculator.risk_decomposition(weights_array)
        optimal_portfolios['min_variance'] = min_var
    
    try:
        ef = loaded_calculator.calculate_efficient_frontier(num_portfolios=20)
        ef_data = ef.to_dict('records')
    except Exception:
        ef_data = []
    
    return {
        'success': True,
        'asset_statistics': asset_stats,
        'correlation_matrix': correlation_matrix.to_dict(),
        'monte_carlo': {
            'simulations': sample_mc_results.to_dict('records'),
            'detailed_analysis': detailed_analysis,
            'summary_stats': {
                'mean_return': sample_mc_results['expected_return'].mean(),
                'mean_risk': sample_mc_results['risk'].mean(),
                'mean_sharpe': sample_mc_results['sharpe_ratio'].mean(),
                'max_sharpe': sample_mc_results['sharpe_ratio'].max(),
                'min_risk': sample_mc_results['risk'].min()
            }
        },
        'optimal_portfolios': optimal_portfolios,
        'efficient_frontier': ef_data,
        'metadata': {
            'tickers_requested': ['AAPL', 'GOOGL', 'MSFT'],
            'tickers_success': ['AAPL', 'GOOGL', 'MSFT'],
            'tickers_failed': [],
            'start_date': '2024-01-02',
            'end_date': '2024-05-31',
            'total_records': 100
        },
        'warnings': []
    }
