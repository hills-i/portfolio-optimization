"""
Tests for calculator.py.
"""
import pytest
import numpy as np
import pandas as pd
from scipy.stats import norm
from unittest.mock import patch, MagicMock


# ==========================================================
# load_data
# ==========================================================
class TestLoadData:

    def test_load_data_success(self, app_context, sample_price_data):
        from app.utils.calculator import PortfolioCalculator
        calc = PortfolioCalculator()
        assert calc.load_data(sample_price_data, risk_free_rate=0.01) is True
        assert calc.returns is not None
        assert calc.mean_returns is not None
        assert calc.cov_matrix is not None
        assert calc.risk_free_rate == 0.01

    def test_load_data_shape(self, app_context, sample_price_data):
        from app.utils.calculator import PortfolioCalculator
        calc = PortfolioCalculator()
        calc.load_data(sample_price_data)
        # Daily returns have one fewer row than the input data because of dropna.
        assert len(calc.returns) == len(sample_price_data) - 1
        assert len(calc.returns.columns) == 3

    def test_mean_returns_annualized(self, app_context, sample_price_data):
        from app.utils.calculator import PortfolioCalculator
        calc = PortfolioCalculator()
        calc.load_data(sample_price_data)
        daily_returns = sample_price_data.pct_change().dropna()
        expected = daily_returns.mean() * 252
        pd.testing.assert_series_equal(calc.mean_returns, expected)

    def test_cov_matrix_annualized(self, app_context, sample_price_data):
        from app.utils.calculator import PortfolioCalculator
        calc = PortfolioCalculator()
        calc.load_data(sample_price_data)
        daily_returns = sample_price_data.pct_change().dropna()
        expected = daily_returns.cov() * 252
        pd.testing.assert_frame_equal(calc.cov_matrix, expected)

    def test_load_data_empty_df(self, app_context):
        """An empty DataFrame should not raise an error (0-column DataFrame)."""
        from app.utils.calculator import PortfolioCalculator
        calc = PortfolioCalculator()
        result = calc.load_data(pd.DataFrame())
        # An empty DataFrame still returns True because pct_change().dropna() succeeds.
        assert result is True
        assert len(calc.returns.columns) == 0


# ==========================================================
# calculate_portfolio_metrics
# ==========================================================
class TestCalculatePortfolioMetrics:

    def test_equal_weights(self, app_context, loaded_calculator):
        weights = np.array([1/3, 1/3, 1/3])
        metrics = loaded_calculator.calculate_portfolio_metrics(weights)

        assert 'expected_return' in metrics
        assert 'risk' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'variance' in metrics
        assert 'annual_return_p05' in metrics
        assert 'annual_return_p01' in metrics
        assert 'var_95' in metrics
        assert 'var_99' in metrics
        assert metrics['risk'] >= 0
        assert metrics['variance'] >= 0
        # variance = risk^2
        assert abs(metrics['variance'] - metrics['risk'] ** 2) < 1e-10

    def test_downside_metrics_calculation(self, app_context):
        from app.utils.calculator import PortfolioCalculator
        metrics = PortfolioCalculator.calculate_annual_normal_downside_metrics(0.10, 0.20)

        expected_p05 = 0.10 - abs(norm.ppf(0.05)) * 0.20
        expected_p01 = 0.10 - abs(norm.ppf(0.01)) * 0.20

        assert abs(metrics['annual_return_p05'] - expected_p05) < 1e-12
        assert abs(metrics['annual_return_p01'] - expected_p01) < 1e-12
        assert abs(metrics['var_95'] - max(0.0, -expected_p05)) < 1e-12
        assert abs(metrics['var_99'] - max(0.0, -expected_p01)) < 1e-12

    def test_downside_metrics_floor_negative_loss_at_zero(self, app_context):
        from app.utils.calculator import PortfolioCalculator
        metrics = PortfolioCalculator.calculate_annual_normal_downside_metrics(0.50, 0.01)

        assert metrics['annual_return_p05'] > 0
        assert metrics['annual_return_p01'] > 0
        assert metrics['var_95'] == 0.0
        assert metrics['var_99'] == 0.0

    def test_concentrated_weight(self, app_context, loaded_calculator):
        """Allocate 100% to a single asset."""
        weights = np.array([1.0, 0.0, 0.0])
        metrics = loaded_calculator.calculate_portfolio_metrics(weights)
        # Return and risk should match the single asset.
        assert abs(metrics['expected_return'] - loaded_calculator.mean_returns.iloc[0]) < 1e-10
        asset_risk = np.sqrt(loaded_calculator.cov_matrix.iloc[0, 0])
        assert abs(metrics['risk'] - asset_risk) < 1e-10

    def test_sharpe_ratio_calculation(self, app_context, loaded_calculator):
        weights = np.array([0.5, 0.3, 0.2])
        metrics = loaded_calculator.calculate_portfolio_metrics(weights)
        expected_sharpe = (metrics['expected_return'] - loaded_calculator.risk_free_rate) / metrics['risk']
        assert abs(metrics['sharpe_ratio'] - expected_sharpe) < 1e-10


# ==========================================================
# monte_carlo_simulation
# ==========================================================
class TestMonteCarloSimulation:

    def test_result_shape(self, app_context, loaded_calculator):
        np.random.seed(42)
        result = loaded_calculator.monte_carlo_simulation(100)
        assert len(result) == 100
        assert 'expected_return' in result.columns
        assert 'risk' in result.columns
        assert 'sharpe_ratio' in result.columns

    def test_weight_columns_present(self, app_context, loaded_calculator):
        np.random.seed(42)
        result = loaded_calculator.monte_carlo_simulation(10)
        weight_cols = [c for c in result.columns if c.startswith('weight_')]
        assert len(weight_cols) == 3

    def test_weights_sum_to_one(self, app_context, loaded_calculator):
        np.random.seed(42)
        result = loaded_calculator.monte_carlo_simulation(50)
        weight_cols = [c for c in result.columns if c.startswith('weight_')]
        sums = result[weight_cols].sum(axis=1)
        np.testing.assert_array_almost_equal(sums.values, np.ones(50), decimal=10)

    def test_reproducibility(self, app_context, loaded_calculator):
        np.random.seed(42)
        r1 = loaded_calculator.monte_carlo_simulation(50)
        np.random.seed(42)
        r2 = loaded_calculator.monte_carlo_simulation(50)
        pd.testing.assert_frame_equal(r1, r2)

    def test_raises_without_data(self, app_context):
        from app.utils.calculator import PortfolioCalculator
        calc = PortfolioCalculator()
        with pytest.raises(ValueError):
            calc.monte_carlo_simulation(10)


# ==========================================================
# optimize_portfolio
# ==========================================================
class TestOptimizePortfolio:

    def test_max_sharpe(self, app_context, loaded_calculator):
        result = loaded_calculator.optimize_portfolio()
        assert result['success'] is True
        assert result['optimization_type'] == 'max_sharpe'
        assert 'weights' in result
        assert 'metrics' in result
        # Weights sum to about 1.
        total = sum(result['weights'].values())
        assert abs(total - 1.0) < 1e-6

    def test_min_risk_with_target(self, app_context, loaded_calculator):
        # Set the target to the midpoint of mean_returns.
        target = float(loaded_calculator.mean_returns.mean())
        result = loaded_calculator.optimize_portfolio(target_return=target)
        assert result['success'] is True
        assert result['optimization_type'] == 'min_risk'
        assert result['target_return'] == target
        assert result['target_return_achieved'] is True

    def test_infeasible_target_is_marked_unachieved(self, app_context, loaded_calculator):
        result = loaded_calculator.optimize_portfolio(target_return=0.8)
        assert result['success'] is True
        assert result['target_return'] == 0.8
        assert result['target_return_achieved'] is False
        assert result['optimizer_success'] is False
        assert result['target_return_gap'] < 0

    def test_weights_non_negative(self, app_context, loaded_calculator):
        result = loaded_calculator.optimize_portfolio()
        if result['success']:
            for w in result['weights'].values():
                assert w >= -1e-10  # No short-selling allowed.

    def test_raises_without_data(self, app_context):
        from app.utils.calculator import PortfolioCalculator
        calc = PortfolioCalculator()
        with pytest.raises(ValueError):
            calc.optimize_portfolio()


# ==========================================================
# optimize_min_variance_portfolio
# ==========================================================
class TestOptimizeMinVariancePortfolio:

    def test_success(self, app_context, loaded_calculator):
        result = loaded_calculator.optimize_min_variance_portfolio()
        assert result['success'] is True
        assert result['optimization_type'] == 'min_variance'
        total = sum(result['weights'].values())
        assert abs(total - 1.0) < 1e-6

    def test_min_variance_has_lowest_risk(self, app_context, loaded_calculator):
        """Minimum-variance portfolio should be lower risk than equal weights in most cases."""
        mv_result = loaded_calculator.optimize_min_variance_portfolio()
        equal_w = np.array([1/3, 1/3, 1/3])
        equal_metrics = loaded_calculator.calculate_portfolio_metrics(equal_w)
        # Minimum-variance risk should be less than or equal to equal-weight risk.
        assert mv_result['metrics']['risk'] <= equal_metrics['risk'] + 1e-6


# ==========================================================
# calculate_efficient_frontier
# ==========================================================
class TestCalculateEfficientFrontier:

    def test_returns_dataframe(self, app_context, loaded_calculator):
        ef = loaded_calculator.calculate_efficient_frontier(num_portfolios=20)
        assert isinstance(ef, pd.DataFrame)
        assert 'expected_return' in ef.columns
        assert 'risk' in ef.columns
        assert 'sharpe_ratio' in ef.columns

    def test_num_portfolios(self, app_context, loaded_calculator):
        ef = loaded_calculator.calculate_efficient_frontier(num_portfolios=10)
        # Not every optimization must succeed, but at least some portfolios should be generated.
        assert len(ef) > 0
        assert len(ef) <= 10

    def test_raises_without_data(self, app_context):
        from app.utils.calculator import PortfolioCalculator
        calc = PortfolioCalculator()
        with pytest.raises(ValueError):
            calc.calculate_efficient_frontier()


# ==========================================================
# calculate_asset_statistics
# ==========================================================
class TestCalculateAssetStatistics:

    def test_all_assets_present(self, app_context, loaded_calculator):
        stats = loaded_calculator.calculate_asset_statistics()
        assert 'AAPL' in stats
        assert 'GOOGL' in stats
        assert 'MSFT' in stats

    def test_stat_keys(self, app_context, loaded_calculator):
        stats = loaded_calculator.calculate_asset_statistics()
        for asset, s in stats.items():
            assert 'expected_return' in s
            assert 'risk' in s
            assert 'sharpe_ratio' in s
            assert 'skewness' in s
            assert 'kurtosis' in s
            assert 'min_return' in s
            assert 'max_return' in s
            assert 'annual_return_p05' in s
            assert 'annual_return_p01' in s
            assert 'var_95' in s
            assert 'var_99' in s

    def test_risk_positive(self, app_context, loaded_calculator):
        stats = loaded_calculator.calculate_asset_statistics()
        for asset, s in stats.items():
            assert s['risk'] > 0

    def test_var_and_return_quantile_ordering(self, app_context, loaded_calculator):
        stats = loaded_calculator.calculate_asset_statistics()
        for asset, s in stats.items():
            assert s['var_99'] >= s['var_95']
            assert s['var_95'] >= 0
            assert s['var_99'] >= 0
            assert s['annual_return_p01'] <= s['annual_return_p05']

    def test_raises_without_data(self, app_context):
        from app.utils.calculator import PortfolioCalculator
        calc = PortfolioCalculator()
        with pytest.raises(ValueError):
            calc.calculate_asset_statistics()


# ==========================================================
# calculate_correlation_matrix
# ==========================================================
class TestCalculateCorrelationMatrix:

    def test_diagonal_is_one(self, app_context, loaded_calculator):
        corr = loaded_calculator.calculate_correlation_matrix()
        for asset in corr.columns:
            assert abs(corr.loc[asset, asset] - 1.0) < 1e-10

    def test_symmetric(self, app_context, loaded_calculator):
        corr = loaded_calculator.calculate_correlation_matrix()
        pd.testing.assert_frame_equal(corr, corr.T)

    def test_values_between_neg1_and_1(self, app_context, loaded_calculator):
        corr = loaded_calculator.calculate_correlation_matrix()
        assert (corr.values >= -1.0 - 1e-10).all()
        assert (corr.values <= 1.0 + 1e-10).all()


# ==========================================================
# risk_decomposition
# ==========================================================
class TestRiskDecomposition:

    def test_contributions_sum_to_100pct(self, app_context, loaded_calculator):
        weights = np.array([0.4, 0.35, 0.25])
        result = loaded_calculator.risk_decomposition(weights)
        total_pct = sum(c['percentage'] for c in result['asset_contributions'].values())
        assert abs(total_pct - 1.0) < 1e-6

    def test_portfolio_risk_positive(self, app_context, loaded_calculator):
        weights = np.array([1/3, 1/3, 1/3])
        result = loaded_calculator.risk_decomposition(weights)
        assert result['portfolio_risk'] > 0

    def test_all_assets_present(self, app_context, loaded_calculator):
        weights = np.array([0.5, 0.3, 0.2])
        result = loaded_calculator.risk_decomposition(weights)
        assert len(result['asset_contributions']) == 3


# ==========================================================
# analyze_monte_carlo_results
# ==========================================================
class TestAnalyzeMonteCarloResults:

    def test_basic_stats(self, app_context, loaded_calculator, sample_mc_results):
        analysis = loaded_calculator.analyze_monte_carlo_results(sample_mc_results)
        assert 'basic_stats' in analysis
        assert analysis['basic_stats']['total_simulations'] == len(sample_mc_results)

    def test_percentiles(self, app_context, loaded_calculator, sample_mc_results):
        analysis = loaded_calculator.analyze_monte_carlo_results(sample_mc_results)
        assert 'percentiles' in analysis
        assert 'p5' in analysis['percentiles']
        assert 'p95' in analysis['percentiles']

    def test_confidence_intervals(self, app_context, loaded_calculator, sample_mc_results):
        analysis = loaded_calculator.analyze_monte_carlo_results(sample_mc_results)
        ci = analysis['confidence_intervals']
        # In the 95% CI, lower should be less than upper.
        assert ci['return_ci_95'][0] < ci['return_ci_95'][1]
        assert ci['risk_ci_95'][0] < ci['risk_ci_95'][1]

    def test_efficiency_metrics(self, app_context, loaded_calculator, sample_mc_results):
        analysis = loaded_calculator.analyze_monte_carlo_results(sample_mc_results)
        em = analysis['efficiency_metrics']
        assert 'best_sharpe_portfolio' in em
        assert 'min_risk_portfolio' in em
        assert em['portfolios_above_rf'] >= 0

    def test_scatter_analysis(self, app_context, loaded_calculator, sample_mc_results):
        analysis = loaded_calculator.analyze_monte_carlo_results(sample_mc_results)
        sa = analysis['scatter_analysis']
        assert 'risk_return_correlation' in sa
        assert 'risk_clusters' in sa
        assert 'return_distribution' in sa

    def test_return_distribution_normality(self, app_context, loaded_calculator, sample_mc_results):
        analysis = loaded_calculator.analyze_monte_carlo_results(sample_mc_results)
        dist = analysis['scatter_analysis']['return_distribution']
        assert 'normality_test' in dist
        assert 'distribution_shape' in dist


# ==========================================================
# compare_simulation_counts
# ==========================================================
class TestCompareSimulationCounts:

    def test_basic_comparison(self, app_context, loaded_calculator):
        np.random.seed(42)
        counts = [100, 500]
        result = loaded_calculator.compare_simulation_counts(counts)
        assert '100' in result
        assert '500' in result
        assert 'convergence_analysis' in result

    def test_convergence_analysis(self, app_context, loaded_calculator):
        np.random.seed(42)
        counts = [100, 500, 1000]
        result = loaded_calculator.compare_simulation_counts(counts)
        conv = result['convergence_analysis']
        assert 'mean_convergence' in conv
        assert 'return_stability' in conv['mean_convergence']
        assert 'recommended_min_count' in conv['mean_convergence']


# ==========================================================
# _calculate_stability / _recommend_min_simulations
# ==========================================================
class TestHelperMethods:

    def test_calculate_stability(self, app_context, loaded_calculator):
        result = loaded_calculator._calculate_stability([0.1, 0.1001, 0.1002])
        assert result['coefficient_of_variation'] >= 0
        assert result['max_change'] >= 0

    def test_calculate_stability_single_value(self, app_context, loaded_calculator):
        result = loaded_calculator._calculate_stability([0.1])
        assert result['coefficient_of_variation'] == 0
        assert result['max_change'] == 0

    def test_calculate_stability_zero_mean(self, app_context, loaded_calculator):
        # mean=0 -> cv=inf
        result = loaded_calculator._calculate_stability([0.1, -0.1])
        assert result['coefficient_of_variation'] == float('inf') or result['coefficient_of_variation'] > 0

    def test_recommend_min_simulations(self, app_context, loaded_calculator):
        counts = [100, 500, 1000, 5000]
        returns = [0.10, 0.1001, 0.10005, 0.10003]
        risks = [0.20, 0.2001, 0.20005, 0.20003]
        result = loaded_calculator._recommend_min_simulations(counts, returns, risks)
        assert result in counts

    def test_recommend_min_simulations_empty(self, app_context, loaded_calculator):
        result = loaded_calculator._recommend_min_simulations([], [], [])
        assert result == 1000  # default fallback
