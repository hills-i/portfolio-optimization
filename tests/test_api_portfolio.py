"""
Tests for api/portfolio.py (all 8 endpoints).
"""
import pytest
import json
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import datetime


# ──────────────────────────────────────────────
# POST /api/validate
# ──────────────────────────────────────────────
class TestValidateInputsEndpoint:

    def test_valid_input(self, client):
        resp = client.post('/api/validate', json={
            'tickers': ['AAPL', 'GOOGL'],
            'start_date': '2022-01-01',
            'end_date': '2024-01-01',
            'simulation_count': 10000
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['valid'] is True

    def test_invalid_input(self, client):
        resp = client.post('/api/validate', json={
            'tickers': ['AAPL'],  # too few
            'start_date': '2022-01-01',
            'end_date': '2024-01-01',
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['valid'] is False

    def test_no_json_body(self, client):
        resp = client.post('/api/validate',
                           data='',
                           content_type='application/json')
        # data='' → request.get_json() returns None → 400
        assert resp.status_code in (400, 500)

    def test_empty_json(self, client):
        resp = client.post('/api/validate', json={})
        # {} is falsy (empty dict) → `not data` is True → 400 with error key
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'error' in data


# ──────────────────────────────────────────────
# POST /api/ticker/validate
# ──────────────────────────────────────────────
class TestValidateTickersEndpoint:

    @patch('app.api.portfolio.DataFetcher')
    def test_valid_tickers(self, mock_fetcher_cls, client):
        mock_instance = MagicMock()
        mock_instance.validate_tickers.return_value = {'AAPL': True, 'GOOGL': True}
        mock_fetcher_cls.return_value = mock_instance

        resp = client.post('/api/ticker/validate', json={'tickers': ['AAPL', 'GOOGL']})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['all_valid'] is True

    @patch('app.api.portfolio.DataFetcher')
    def test_some_invalid(self, mock_fetcher_cls, client):
        mock_instance = MagicMock()
        mock_instance.validate_tickers.return_value = {'AAPL': True, 'BAD': False}
        mock_fetcher_cls.return_value = mock_instance

        resp = client.post('/api/ticker/validate', json={'tickers': ['AAPL', 'BAD']})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['all_valid'] is False

    def test_empty_tickers(self, client):
        resp = client.post('/api/ticker/validate', json={'tickers': []})
        assert resp.status_code == 400


# ──────────────────────────────────────────────
# POST /api/ticker/info
# ──────────────────────────────────────────────
class TestGetTickerInfoEndpoint:

    @patch('app.api.portfolio.DataFetcher')
    def test_success(self, mock_fetcher_cls, client):
        mock_instance = MagicMock()
        mock_instance.get_ticker_info.return_value = {
            'success': True, 'name': 'Apple Inc.', 'sector': 'Technology',
            'industry': 'Consumer Electronics', 'country': 'US',
            'currency': 'USD', 'market_cap': 3e12, 'beta': 1.2
        }
        mock_fetcher_cls.return_value = mock_instance

        resp = client.post('/api/ticker/info', json={'ticker': 'AAPL'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['name'] == 'Apple Inc.'

    def test_missing_ticker(self, client):
        resp = client.post('/api/ticker/info', json={})
        assert resp.status_code == 400


# ──────────────────────────────────────────────
# POST /api/analyze
# ──────────────────────────────────────────────
class TestAnalyzePortfolioEndpoint:

    def _make_fetch_result(self):
        """Mock return value for DataFetcher.fetch_stock_data."""
        np.random.seed(42)
        dates = pd.bdate_range(start='2023-01-02', periods=100)
        df = pd.DataFrame({
            'AAPL': 150 * np.cumprod(1 + np.random.normal(0.0005, 0.015, 100)),
            'GOOGL': 140 * np.cumprod(1 + np.random.normal(0.0005, 0.015, 100)),
        }, index=dates)
        return {
            'success': True,
            'data': df,
            'errors': [],
            'warnings': [],
            'metadata': {
                'tickers_requested': ['AAPL', 'GOOGL'],
                'tickers_success': ['AAPL', 'GOOGL'],
                'tickers_failed': [],
                'start_date': '2023-01-01',
                'end_date': '2023-12-31',
                'total_records': 100
            }
        }

    def test_no_json_body(self, client):
        resp = client.post('/api/analyze',
                           data='',
                           content_type='application/json')
        assert resp.status_code in (400, 500)

    def test_validation_failure(self, client):
        resp = client.post('/api/analyze', json={
            'tickers': ['AAPL'],  # too few
            'start_date': '2022-01-01',
            'end_date': '2024-01-01'
        })
        assert resp.status_code == 400

    @patch('app.api.portfolio.DataFetcher')
    def test_data_fetch_failure(self, mock_fetcher_cls, client):
        mock_instance = MagicMock()
        mock_instance.fetch_stock_data.return_value = {
            'success': False,
            'errors': ['No data'],
            'warnings': [],
            'data': None,
            'metadata': {'tickers_requested': ['AAPL', 'GOOGL'], 'tickers_success': [], 'tickers_failed': ['AAPL', 'GOOGL']}
        }
        mock_fetcher_cls.return_value = mock_instance

        resp = client.post('/api/analyze', json={
            'tickers': ['AAPL', 'GOOGL'],
            'start_date': '2022-01-01',
            'end_date': '2024-01-01'
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'error' in data

    @patch('app.api.portfolio.DataFetcher')
    def test_successful_analysis(self, mock_fetcher_cls, client):
        mock_instance = MagicMock()
        mock_instance.fetch_stock_data.return_value = self._make_fetch_result()
        mock_fetcher_cls.return_value = mock_instance

        resp = client.post('/api/analyze', json={
            'tickers': ['AAPL', 'GOOGL'],
            'start_date': '2022-01-01',
            'end_date': '2024-01-01',
            'simulation_count': 1000,  # MIN_SIMULATION_COUNT
            'risk_free_rate': 0.01
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'monte_carlo' in data
        assert 'asset_statistics' in data
        assert 'correlation_matrix' in data
        assert data['risk_metric_metadata']['var'] == {
            'method': 'parametric_normal',
            'horizon': 'annual',
            'unit': 'return_rate',
            'confidence_levels': [0.95, 0.99],
            'negative_loss_floor': 0.0
        }

    @patch('app.api.portfolio.DataFetcher')
    def test_analysis_with_target_return(self, mock_fetcher_cls, client):
        mock_instance = MagicMock()
        mock_instance.fetch_stock_data.return_value = self._make_fetch_result()
        mock_fetcher_cls.return_value = mock_instance

        resp = client.post('/api/analyze', json={
            'tickers': ['AAPL', 'GOOGL'],
            'start_date': '2022-01-01',
            'end_date': '2024-01-01',
            'simulation_count': 1000,
            'target_return': 0.1
        })
        assert resp.status_code == 200
        data = resp.get_json()
        if 'optimal_portfolios' in data and 'target_return' in data.get('optimal_portfolios', {}):
            assert data['optimal_portfolios']['target_return']['success'] is True

    @patch('app.api.portfolio.DataFetcher')
    def test_analysis_with_infeasible_target_return_reports_error(self, mock_fetcher_cls, client):
        mock_instance = MagicMock()
        mock_instance.fetch_stock_data.return_value = self._make_fetch_result()
        mock_fetcher_cls.return_value = mock_instance

        resp = client.post('/api/analyze', json={
            'tickers': ['AAPL', 'GOOGL'],
            'start_date': '2022-01-01',
            'end_date': '2024-01-01',
            'simulation_count': 1000,
            'target_return': 1.0
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'target_return' not in data['optimal_portfolios']

        target_error = data['optimization_errors']['target_return']
        assert target_error['optimization_type'] == 'min_risk'
        assert target_error['target_return'] == 1.0
        assert target_error['target_return_achieved'] is False
        assert target_error['optimizer_success'] is False
        assert target_error['target_return_gap'] < 0
        assert 'optimizer_message' in target_error
        assert 'Target return optimization failed or was infeasible' in data['warnings']

    @patch('app.api.portfolio.DataFetcher')
    def test_analysis_with_language(self, mock_fetcher_cls, client):
        mock_instance = MagicMock()
        mock_instance.fetch_stock_data.return_value = self._make_fetch_result()
        mock_fetcher_cls.return_value = mock_instance

        resp = client.post('/api/analyze', json={
            'tickers': ['AAPL', 'GOOGL'],
            'start_date': '2022-01-01',
            'end_date': '2024-01-01',
            'simulation_count': 1000,
            'language': 'ja'
        })
        assert resp.status_code == 200


# ──────────────────────────────────────────────
# POST /api/compare-simulations
# ──────────────────────────────────────────────
class TestCompareSimulationsEndpoint:

    def test_no_json_body(self, client):
        resp = client.post('/api/compare-simulations',
                           data='',
                           content_type='application/json')
        assert resp.status_code in (400, 500)

    def test_validation_failure(self, client):
        resp = client.post('/api/compare-simulations', json={
            'tickers': ['AAPL'],  # too few
            'start_date': '2022-01-01',
            'end_date': '2024-01-01'
        })
        assert resp.status_code == 400

    @patch('app.api.portfolio.DataFetcher')
    def test_successful_comparison(self, mock_fetcher_cls, client):
        np.random.seed(42)
        dates = pd.bdate_range(start='2023-01-02', periods=100)
        df = pd.DataFrame({
            'AAPL': 150 * np.cumprod(1 + np.random.normal(0.0005, 0.015, 100)),
            'GOOGL': 140 * np.cumprod(1 + np.random.normal(0.0005, 0.015, 100)),
        }, index=dates)

        mock_instance = MagicMock()
        mock_instance.fetch_stock_data.return_value = {
            'success': True, 'data': df, 'errors': [], 'warnings': [],
            'metadata': {'tickers_requested': ['AAPL', 'GOOGL'], 'tickers_success': ['AAPL', 'GOOGL'],
                         'tickers_failed': [], 'start_date': '2023-01-01', 'end_date': '2023-12-31', 'total_records': 100}
        }
        mock_fetcher_cls.return_value = mock_instance

        resp = client.post('/api/compare-simulations', json={
            'tickers': ['AAPL', 'GOOGL'],
            'start_date': '2022-01-01',
            'end_date': '2024-01-01',
            'simulation_counts': [100, 200]
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'comparison_results' in data

    @patch('app.api.portfolio.DataFetcher')
    def test_data_fetch_failure(self, mock_fetcher_cls, client):
        mock_instance = MagicMock()
        mock_instance.fetch_stock_data.return_value = {
            'success': False, 'errors': ['No data'], 'warnings': [], 'data': None,
            'metadata': {}
        }
        mock_fetcher_cls.return_value = mock_instance

        resp = client.post('/api/compare-simulations', json={
            'tickers': ['AAPL', 'GOOGL'],
            'start_date': '2022-01-01',
            'end_date': '2024-01-01'
        })
        assert resp.status_code == 400


# ──────────────────────────────────────────────
# POST /api/visualize
# ──────────────────────────────────────────────
class TestVisualizeEndpoint:

    def test_no_results(self, client):
        resp = client.post('/api/visualize', json={
            'results': None,
            'chart_types': ['correlation_matrix']
        })
        assert resp.status_code == 400

    def test_correlation_chart(self, client, sample_analysis_results):
        resp = client.post('/api/visualize', json={
            'results': sample_analysis_results,
            'chart_types': ['correlation_matrix']
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'charts' in data

    def test_risk_return_scatter(self, client, sample_analysis_results):
        resp = client.post('/api/visualize', json={
            'results': sample_analysis_results,
            'chart_types': ['risk_return_scatter']
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True

    def test_all_chart_types(self, client, sample_analysis_results):
        resp = client.post('/api/visualize', json={
            'results': sample_analysis_results,
            'chart_types': ['all'],
            'language': 'en'
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['chart_count'] > 0

    def test_with_language_ja(self, client, sample_analysis_results):
        resp = client.post('/api/visualize', json={
            'results': sample_analysis_results,
            'chart_types': ['correlation_matrix'],
            'language': 'ja'
        })
        assert resp.status_code == 200

    def test_unknown_chart_type_ignored(self, client, sample_analysis_results):
        resp = client.post('/api/visualize', json={
            'results': sample_analysis_results,
            'chart_types': ['nonexistent_chart']
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True


# ──────────────────────────────────────────────
# POST /api/export
# ──────────────────────────────────────────────
class TestExportEndpoint:

    def test_json_export(self, client):
        resp = client.post('/api/export', json={
            'format': 'json',
            'results': {'some': 'data'}
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'export_time' in data

    def test_csv_not_implemented(self, client):
        resp = client.post('/api/export', json={
            'format': 'csv',
            'results': {'some': 'data'}
        })
        assert resp.status_code == 501

    def test_no_results(self, client):
        resp = client.post('/api/export', json={
            'format': 'json'
        })
        assert resp.status_code == 400

    def test_default_format_is_json(self, client):
        resp = client.post('/api/export', json={
            'results': {'some': 'data'}
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True

    def test_with_language(self, client):
        resp = client.post('/api/export', json={
            'results': {'some': 'data'},
            'language': 'ja'
        })
        assert resp.status_code == 200


# ──────────────────────────────────────────────
# GET /api/health
# ──────────────────────────────────────────────
class TestHealthCheckEndpoint:

    def test_health_check(self, client):
        resp = client.get('/api/health')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert data['version'] == '1.0.0'
