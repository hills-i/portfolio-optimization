"""
Tests for validator.py.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch


# ──────────────────────────────────────────────
# validate_tickers
# ──────────────────────────────────────────────
class TestValidateTickers:

    def _make_validator(self, mock_config):
        from app.utils.validator import InputValidator
        return InputValidator(mock_config)

    # --- Valid cases ---
    def test_valid_two_tickers(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_tickers(['AAPL', 'GOOGL'])
        assert r['valid'] is True
        assert r['errors'] == []

    def test_valid_max_tickers(self, app_context, mock_config):
        tickers = [f'T{i:02d}' for i in range(20)]  # Exactly MAX_ASSETS=20.
        v = self._make_validator(mock_config)
        r = v.validate_tickers(tickers)
        assert r['valid'] is True

    def test_valid_ticker_with_dot(self, app_context, mock_config):
        """Ticker with a dot, such as a Japanese stock symbol."""
        v = self._make_validator(mock_config)
        r = v.validate_tickers(['7203.T', 'AAPL'])
        assert r['valid'] is True

    def test_valid_numeric_ticker(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_tickers(['7203', 'AAPL'])
        assert r['valid'] is True

    # --- Invalid cases ---
    def test_empty_list(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_tickers([])
        assert r['valid'] is False
        assert len(r['errors']) >= 1

    def test_single_ticker(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_tickers(['AAPL'])
        assert r['valid'] is False  # MIN_ASSETS=2

    def test_too_many_tickers(self, app_context, mock_config):
        tickers = [f'T{i:02d}' for i in range(21)]
        v = self._make_validator(mock_config)
        r = v.validate_tickers(tickers)
        assert r['valid'] is False

    def test_duplicate_tickers(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_tickers(['AAPL', 'AAPL'])
        # Duplicate tickers should fail validation.
        assert r['valid'] is False

    def test_invalid_format_lowercase(self, app_context, mock_config):
        """Lowercase input stays valid because the validator normalizes with upper()."""
        v = self._make_validator(mock_config)
        # The validator uppercases input before applying the pattern match.
        r = v.validate_tickers(['aapl', 'googl'])
        assert r['valid'] is True  # Matches after upper() normalization.

    def test_invalid_format_too_long(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_tickers(['ABCDEFGHI', 'AAPL'])  # 9 characters > 8.
        assert r['valid'] is False

    def test_invalid_format_special_chars(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_tickers(['AA@PL', 'GOOGL'])
        assert r['valid'] is False

    def test_duplicate_different_case(self, app_context, mock_config):
        """Duplicate tickers with different letter case."""
        v = self._make_validator(mock_config)
        r = v.validate_tickers(['AAPL', 'aapl'])
        assert r['valid'] is False  # Duplicates are detected after upper() normalization.


# ──────────────────────────────────────────────
# validate_date_range
# ──────────────────────────────────────────────
class TestValidateDateRange:

    def _make_validator(self, mock_config):
        from app.utils.validator import InputValidator
        return InputValidator(mock_config)

    # --- Valid cases ---
    def test_valid_two_years(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_date_range('2022-01-01', '2024-01-01')
        assert r['valid'] is True

    def test_valid_exactly_one_year(self, app_context, mock_config):
        """Exactly one year (MIN_ANALYSIS_YEARS)."""
        v = self._make_validator(mock_config)
        r = v.validate_date_range('2023-01-01', '2024-01-02')  # 366 days ~= 1 year.
        assert r['valid'] is True

    # --- Invalid cases ---
    def test_start_after_end(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_date_range('2024-06-01', '2024-01-01')
        assert r['valid'] is False

    def test_start_equals_end(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_date_range('2024-01-01', '2024-01-01')
        assert r['valid'] is False

    def test_period_too_short(self, app_context, mock_config):
        """Less than one year."""
        v = self._make_validator(mock_config)
        r = v.validate_date_range('2024-01-01', '2024-06-01')
        assert r['valid'] is False

    def test_future_end_date(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        future = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        r = v.validate_date_range('2023-01-01', future)
        assert r['valid'] is False

    def test_invalid_date_format(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_date_range('01-01-2024', '06-01-2024')
        assert r['valid'] is False

    def test_invalid_date_string(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_date_range('not-a-date', '2024-01-01')
        assert r['valid'] is False

    def test_very_old_start_date_gives_warning(self, app_context, mock_config):
        """A start date more than 31 years ago should trigger a warning."""
        v = self._make_validator(mock_config)
        old_date = (datetime.now() - timedelta(days=32 * 365)).strftime('%Y-%m-%d')
        recent = '2024-01-01'
        r = v.validate_date_range(old_date, recent)
        # Periods over MAX_ANALYSIS_YEARS=31 may fail validation.
        # A start date older than 31 years may either exceed the max period or produce a warning.
        assert len(r['warnings']) > 0 or r['valid'] is False

    def test_period_exceeds_max(self, app_context, mock_config):
        """Period exceeds MAX_ANALYSIS_YEARS=31."""
        v = self._make_validator(mock_config)
        r = v.validate_date_range('1990-01-01', '2024-01-01')  # 34 years.
        assert r['valid'] is False


# ──────────────────────────────────────────────
# validate_target_return
# ──────────────────────────────────────────────
class TestValidateTargetReturn:

    def _make_validator(self, mock_config):
        from app.utils.validator import InputValidator
        return InputValidator(mock_config)

    def test_valid_positive(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_target_return(0.1)
        assert r['valid'] is True

    def test_valid_zero(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_target_return(0.0)
        assert r['valid'] is True

    def test_boundary_min(self, app_context, mock_config):
        """-0.5 is still valid."""
        v = self._make_validator(mock_config)
        r = v.validate_target_return(-0.5)
        assert r['valid'] is True

    def test_boundary_max(self, app_context, mock_config):
        """1.0 is still valid."""
        v = self._make_validator(mock_config)
        r = v.validate_target_return(1.0)
        assert r['valid'] is True

    def test_below_min(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_target_return(-0.51)
        assert r['valid'] is False

    def test_above_max(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_target_return(1.01)
        assert r['valid'] is False

    def test_warning_high_return(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_target_return(0.31)
        assert r['valid'] is True
        assert len(r['warnings']) > 0

    def test_warning_low_return(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_target_return(-0.21)
        assert r['valid'] is True
        assert len(r['warnings']) > 0

    def test_no_warning_normal(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_target_return(0.1)
        assert r['warnings'] == []


# ──────────────────────────────────────────────
# validate_risk_free_rate
# ──────────────────────────────────────────────
class TestValidateRiskFreeRate:

    def _make_validator(self, mock_config):
        from app.utils.validator import InputValidator
        return InputValidator(mock_config)

    def test_valid_normal(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_risk_free_rate(0.01)
        assert r['valid'] is True

    def test_boundary_zero(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_risk_free_rate(0.0)
        assert r['valid'] is True

    def test_boundary_max(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_risk_free_rate(0.1)
        assert r['valid'] is True

    def test_negative(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_risk_free_rate(-0.01)
        assert r['valid'] is False

    def test_above_max(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_risk_free_rate(0.11)
        assert r['valid'] is False


# ──────────────────────────────────────────────
# validate_simulation_count
# ──────────────────────────────────────────────
class TestValidateSimulationCount:

    def _make_validator(self, mock_config):
        from app.utils.validator import InputValidator
        return InputValidator(mock_config)

    def test_valid_default(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_simulation_count(10000)
        assert r['valid'] is True

    def test_boundary_min(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_simulation_count(1000)
        assert r['valid'] is True

    def test_boundary_max(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_simulation_count(50000)
        assert r['valid'] is True

    def test_below_min(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_simulation_count(999)
        assert r['valid'] is False

    def test_above_max(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_simulation_count(50001)
        assert r['valid'] is False

    def test_warning_high_count(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_simulation_count(30001)
        assert r['valid'] is True
        assert len(r['warnings']) > 0

    def test_no_warning_at_30000(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        r = v.validate_simulation_count(30000)
        assert r['warnings'] == []


# ──────────────────────────────────────────────
# validate_all_inputs
# ──────────────────────────────────────────────
class TestValidateAllInputs:

    def _make_validator(self, mock_config):
        from app.utils.validator import InputValidator
        return InputValidator(mock_config)

    def test_valid_all_fields(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        inputs = {
            'tickers': ['AAPL', 'GOOGL'],
            'start_date': '2022-01-01',
            'end_date': '2024-01-01',
            'target_return': 0.1,
            'risk_free_rate': 0.01,
            'simulation_count': 10000
        }
        r = v.validate_all_inputs(inputs)
        assert r['valid'] is True
        assert 'field_results' in r

    def test_missing_tickers(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        inputs = {
            'start_date': '2022-01-01',
            'end_date': '2024-01-01'
        }
        r = v.validate_all_inputs(inputs)
        assert r['valid'] is False

    def test_missing_start_date(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        inputs = {
            'tickers': ['AAPL', 'GOOGL'],
            'end_date': '2024-01-01'
        }
        r = v.validate_all_inputs(inputs)
        assert r['valid'] is False

    def test_missing_end_date(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        inputs = {
            'tickers': ['AAPL', 'GOOGL'],
            'start_date': '2022-01-01'
        }
        r = v.validate_all_inputs(inputs)
        assert r['valid'] is False

    def test_optional_fields_omitted(self, app_context, mock_config):
        """Optional fields may be omitted."""
        v = self._make_validator(mock_config)
        inputs = {
            'tickers': ['AAPL', 'GOOGL'],
            'start_date': '2022-01-01',
            'end_date': '2024-01-01'
        }
        r = v.validate_all_inputs(inputs)
        assert r['valid'] is True

    def test_target_return_none_ignored(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        inputs = {
            'tickers': ['AAPL', 'GOOGL'],
            'start_date': '2022-01-01',
            'end_date': '2024-01-01',
            'target_return': None
        }
        r = v.validate_all_inputs(inputs)
        assert r['valid'] is True
        assert 'target_return' not in r.get('field_results', {})

    def test_multiple_errors_aggregated(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        inputs = {
            'tickers': ['AAPL'],  # too few
            'start_date': '2024-06-01',
            'end_date': '2024-01-01',  # start > end
        }
        r = v.validate_all_inputs(inputs)
        assert r['valid'] is False
        assert len(r['errors']) >= 2

    def test_warnings_aggregated(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        inputs = {
            'tickers': ['AAPL', 'GOOGL'],
            'start_date': '2022-01-01',
            'end_date': '2024-01-01',
            'target_return': 0.5,  # warns high
            'simulation_count': 40000  # warns high
        }
        r = v.validate_all_inputs(inputs)
        assert r['valid'] is True
        assert len(r['warnings']) >= 2

    def test_empty_tickers_list(self, app_context, mock_config):
        v = self._make_validator(mock_config)
        inputs = {
            'tickers': [],
            'start_date': '2022-01-01',
            'end_date': '2024-01-01'
        }
        r = v.validate_all_inputs(inputs)
        assert r['valid'] is False
