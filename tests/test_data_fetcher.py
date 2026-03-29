"""
Tests for data_fetcher.py.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestFetchStockData:
    """Tests for DataFetcher.fetch_stock_data."""

    def _make_fetcher(self):
        from app.utils.data_fetcher import DataFetcher
        return DataFetcher(timeout=10)

    def _mock_history(self, ticker, n_days=100, start_price=150.0):
        """Create a mock DataFrame returned by yfinance.history()."""
        dates = pd.bdate_range(start='2023-01-02', periods=n_days)
        np.random.seed(hash(ticker) % 2**31)
        prices = start_price * np.cumprod(1 + np.random.normal(0.0005, 0.015, n_days))
        return pd.DataFrame({'Close': prices, 'Open': prices * 0.99,
                             'High': prices * 1.01, 'Low': prices * 0.98,
                             'Volume': np.random.randint(1e6, 1e7, n_days)},
                            index=dates)

    # --- Valid cases ---
    @patch('app.utils.data_fetcher.yf.Ticker')
    def test_fetch_success(self, mock_ticker_cls, request_context):
        def side_effect(ticker):
            m = MagicMock()
            m.history.return_value = self._mock_history(ticker)
            return m

        mock_ticker_cls.side_effect = side_effect
        fetcher = self._make_fetcher()
        result = fetcher.fetch_stock_data(['AAPL', 'GOOGL', 'MSFT'], '2023-01-01', '2023-12-31')

        assert result['success'] is True
        assert isinstance(result['data'], pd.DataFrame)
        assert len(result['metadata']['tickers_success']) == 3
        assert len(result['metadata']['tickers_failed']) == 0

    @patch('app.utils.data_fetcher.yf.Ticker')
    def test_fetch_with_progress_callback(self, mock_ticker_cls, request_context):
        def side_effect(ticker):
            m = MagicMock()
            m.history.return_value = self._mock_history(ticker)
            return m

        mock_ticker_cls.side_effect = side_effect
        fetcher = self._make_fetcher()
        callback = MagicMock()
        fetcher.fetch_stock_data(['AAPL', 'GOOGL'], '2023-01-01', '2023-12-31',
                                 progress_callback=callback)
        assert callback.call_count > 0

    # --- Partial failure ---
    @patch('app.utils.data_fetcher.yf.Ticker')
    def test_partial_failure_still_success(self, mock_ticker_cls, request_context):
        """One out of three tickers fails, leaving two, so success stays true."""
        def side_effect(ticker):
            m = MagicMock()
            if ticker == 'BAD':
                m.history.return_value = pd.DataFrame()  # Empty data
            else:
                m.history.return_value = self._mock_history(ticker)
            return m

        mock_ticker_cls.side_effect = side_effect
        fetcher = self._make_fetcher()
        result = fetcher.fetch_stock_data(['AAPL', 'GOOGL', 'BAD'], '2023-01-01', '2023-12-31')

        assert result['success'] is True
        assert 'BAD' in result['metadata']['tickers_failed']
        assert len(result['warnings']) > 0

    # --- All fail ---
    @patch('app.utils.data_fetcher.yf.Ticker')
    def test_all_tickers_fail(self, mock_ticker_cls, request_context):
        def side_effect(ticker):
            m = MagicMock()
            m.history.return_value = pd.DataFrame()
            return m

        mock_ticker_cls.side_effect = side_effect
        fetcher = self._make_fetcher()
        result = fetcher.fetch_stock_data(['BAD1', 'BAD2'], '2023-01-01', '2023-12-31')

        assert result['success'] is False
        assert len(result['errors']) > 0

    # --- One of two tickers fails, leaving one, so success=False (< 2) ---
    @patch('app.utils.data_fetcher.yf.Ticker')
    def test_insufficient_tickers_after_failure(self, mock_ticker_cls, request_context):
        def side_effect(ticker):
            m = MagicMock()
            if ticker == 'BAD':
                m.history.return_value = pd.DataFrame()
            else:
                m.history.return_value = self._mock_history(ticker)
            return m

        mock_ticker_cls.side_effect = side_effect
        fetcher = self._make_fetcher()
        result = fetcher.fetch_stock_data(['AAPL', 'BAD'], '2023-01-01', '2023-12-31')

        assert result['success'] is False

    # --- Too little data (< 20 days) ---
    @patch('app.utils.data_fetcher.yf.Ticker')
    def test_insufficient_data_points(self, mock_ticker_cls, request_context):
        def side_effect(ticker):
            m = MagicMock()
            m.history.return_value = self._mock_history(ticker, n_days=10)
            return m

        mock_ticker_cls.side_effect = side_effect
        fetcher = self._make_fetcher()
        result = fetcher.fetch_stock_data(['AAPL', 'GOOGL'], '2023-01-01', '2023-01-15')
        # 10 days < 20, so both fail and success becomes False.
        assert result['success'] is False

    # --- Exception raised ---
    @patch('app.utils.data_fetcher.yf.Ticker')
    def test_exception_during_fetch(self, mock_ticker_cls, request_context):
        def side_effect(ticker):
            m = MagicMock()
            m.history.side_effect = Exception('Network error')
            return m

        mock_ticker_cls.side_effect = side_effect
        fetcher = self._make_fetcher()
        result = fetcher.fetch_stock_data(['AAPL', 'GOOGL'], '2023-01-01', '2023-12-31')
        assert result['success'] is False


class TestHandleMissingData:
    """Tests for DataFetcher._handle_missing_data."""

    def _make_fetcher(self):
        from app.utils.data_fetcher import DataFetcher
        return DataFetcher()

    def test_fills_nans(self, request_context):
        dates = pd.bdate_range(start='2024-01-02', periods=10)
        data = pd.DataFrame({
            'A': [100, np.nan, 102, 103, np.nan, 105, 106, 107, 108, 109],
            'B': [200, 201, np.nan, 203, 204, 205, 206, 207, 208, 209]
        }, index=dates)

        fetcher = self._make_fetcher()
        result = fetcher._handle_missing_data(data)

        assert result.isna().sum().sum() == 0

    def test_all_nan_column(self, request_context):
        dates = pd.bdate_range(start='2024-01-02', periods=5)
        data = pd.DataFrame({
            'A': [100, 101, 102, 103, 104],
            'B': [np.nan, np.nan, np.nan, np.nan, np.nan]
        }, index=dates)

        fetcher = self._make_fetcher()
        result = fetcher._handle_missing_data(data)
        # Even with bfill/ffill, an all-NaN column remains empty and dropna removes every row.
        assert len(result) == 0


class TestCheckDataQuality:
    """Tests for DataFetcher._check_data_quality."""

    def _make_fetcher(self):
        from app.utils.data_fetcher import DataFetcher
        return DataFetcher()

    def test_extreme_returns_detected(self, request_context):
        dates = pd.bdate_range(start='2024-01-02', periods=50)
        prices = [100] * 50
        prices[25] = 200  # 100% jump
        data = pd.DataFrame({'TEST': prices}, index=dates)

        fetcher = self._make_fetcher()
        warnings = fetcher._check_data_quality(data)
        # 100% jump should trigger extreme movement warning
        extreme_warnings = [w for w in warnings if 'Extreme' in str(w) or 'extreme' in str(w)]
        assert len(extreme_warnings) > 0

    def test_zero_prices_detected(self, request_context):
        dates = pd.bdate_range(start='2024-01-02', periods=20)
        prices = [100] * 20
        prices[10] = 0
        data = pd.DataFrame({'TEST': prices}, index=dates)

        fetcher = self._make_fetcher()
        warnings = fetcher._check_data_quality(data)
        zero_warnings = [w for w in warnings if 'Zero' in str(w) or 'zero' in str(w) or 'negative' in str(w)]
        assert len(zero_warnings) > 0

    def test_clean_data_no_warnings(self, request_context):
        dates = pd.bdate_range(start='2024-01-02', periods=50)
        np.random.seed(42)
        prices = 100 * np.cumprod(1 + np.random.normal(0.0005, 0.01, 50))
        data = pd.DataFrame({'TEST': prices}, index=dates)

        fetcher = self._make_fetcher()
        warnings = fetcher._check_data_quality(data)
        # Normal data should not trigger extreme or zero warnings.
        extreme_or_zero = [w for w in warnings if 'Extreme' in str(w) or 'Zero' in str(w)]
        assert len(extreme_or_zero) == 0


class TestGetTickerInfo:
    """Tests for DataFetcher.get_ticker_info."""

    @patch('app.utils.data_fetcher.yf.Ticker')
    def test_success(self, mock_ticker_cls, request_context):
        mock_instance = MagicMock()
        mock_instance.info = {
            'longName': 'Apple Inc.',
            'sector': 'Technology',
            'industry': 'Consumer Electronics',
            'country': 'United States',
            'currency': 'USD',
            'marketCap': 3000000000000,
            'beta': 1.2
        }
        mock_ticker_cls.return_value = mock_instance

        from app.utils.data_fetcher import DataFetcher
        fetcher = DataFetcher()
        result = fetcher.get_ticker_info('AAPL')

        assert result['success'] is True
        assert result['name'] == 'Apple Inc.'
        assert result['sector'] == 'Technology'

    @patch('app.utils.data_fetcher.yf.Ticker')
    def test_failure(self, mock_ticker_cls, request_context):
        mock_ticker_cls.side_effect = Exception('Not found')

        from app.utils.data_fetcher import DataFetcher
        fetcher = DataFetcher()
        result = fetcher.get_ticker_info('INVALID')

        assert result['success'] is False
        assert 'error' in result


class TestValidateTickers:
    """Tests for DataFetcher.validate_tickers."""

    @patch('app.utils.data_fetcher.yf.Ticker')
    def test_valid_tickers(self, mock_ticker_cls, request_context):
        def side_effect(ticker):
            m = MagicMock()
            m.history.return_value = pd.DataFrame({'Close': [100, 101]})
            return m

        mock_ticker_cls.side_effect = side_effect

        from app.utils.data_fetcher import DataFetcher
        fetcher = DataFetcher()
        result = fetcher.validate_tickers(['AAPL', 'GOOGL'])

        assert result['AAPL'] is True
        assert result['GOOGL'] is True

    @patch('app.utils.data_fetcher.yf.Ticker')
    def test_invalid_ticker(self, mock_ticker_cls, request_context):
        def side_effect(ticker):
            m = MagicMock()
            if ticker == 'INVALID':
                m.history.return_value = pd.DataFrame()
            else:
                m.history.return_value = pd.DataFrame({'Close': [100]})
            return m

        mock_ticker_cls.side_effect = side_effect

        from app.utils.data_fetcher import DataFetcher
        fetcher = DataFetcher()
        result = fetcher.validate_tickers(['AAPL', 'INVALID'])

        assert result['AAPL'] is True
        assert result['INVALID'] is False

    @patch('app.utils.data_fetcher.yf.Ticker')
    def test_exception_returns_false(self, mock_ticker_cls, request_context):
        def side_effect(ticker):
            raise Exception('Error')

        mock_ticker_cls.side_effect = side_effect

        from app.utils.data_fetcher import DataFetcher
        fetcher = DataFetcher()
        result = fetcher.validate_tickers(['AAPL'])

        assert result['AAPL'] is False
