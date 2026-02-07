"""
visualizer.py のテスト
"""
import pytest
import json
import numpy as np
import pandas as pd


class TestCreateEfficientFrontierPlot:

    def test_returns_valid_json(self, app_context, loaded_calculator, sample_mc_results):
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()

        ef = loaded_calculator.calculate_efficient_frontier(20)
        mc_data = sample_mc_results.to_dict('records')
        ef_data = ef.to_dict('records')

        result = vis.create_efficient_frontier_plot(mc_data, ef_data)
        parsed = json.loads(result)
        assert 'data' in parsed

    def test_with_optimal_portfolios(self, app_context, loaded_calculator, sample_mc_results):
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()

        ef = loaded_calculator.calculate_efficient_frontier(20)
        max_sharpe = loaded_calculator.optimize_portfolio()

        optimal = {}
        if max_sharpe['success']:
            optimal['max_sharpe'] = max_sharpe

        result = vis.create_efficient_frontier_plot(
            sample_mc_results.to_dict('records'),
            ef.to_dict('records'),
            optimal
        )
        parsed = json.loads(result)
        assert 'data' in parsed

    def test_without_optimal_portfolios(self, app_context, loaded_calculator, sample_mc_results):
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()

        ef = loaded_calculator.calculate_efficient_frontier(20)
        result = vis.create_efficient_frontier_plot(
            sample_mc_results.to_dict('records'),
            ef.to_dict('records'),
            None
        )
        parsed = json.loads(result)
        assert 'data' in parsed


class TestCreateAssetAllocationPlot:

    def test_returns_valid_json(self, app_context):
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()

        weights = {'AAPL': 0.4, 'GOOGL': 0.35, 'MSFT': 0.25}
        result = vis.create_asset_allocation_plot(weights)
        parsed = json.loads(result)
        assert 'data' in parsed

    def test_with_title(self, app_context):
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()

        weights = {'AAPL': 0.5, 'GOOGL': 0.5}
        result = vis.create_asset_allocation_plot(weights, title='Test Allocation')
        parsed = json.loads(result)
        assert 'data' in parsed

    def test_small_weights_grouped(self, app_context):
        """0.5% 未満は 'Others' にグループ化"""
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()

        weights = {'AAPL': 0.90, 'GOOGL': 0.09, 'TINY': 0.004, 'TINY2': 0.006}
        result = vis.create_asset_allocation_plot(weights)
        parsed = json.loads(result)
        assert 'data' in parsed

    def test_empty_weights(self, app_context):
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()
        result = vis.create_asset_allocation_plot({})
        parsed = json.loads(result)
        assert 'data' in parsed


class TestCreateCorrelationHeatmap:

    def test_returns_valid_json(self, app_context, loaded_calculator):
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()

        corr = loaded_calculator.calculate_correlation_matrix()
        result = vis.create_correlation_heatmap(corr.to_dict())
        parsed = json.loads(result)
        assert 'data' in parsed


class TestCreateRiskReturnScatter:

    def test_returns_valid_json(self, app_context, loaded_calculator):
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()

        stats = loaded_calculator.calculate_asset_statistics()
        result = vis.create_risk_return_scatter(stats)
        parsed = json.loads(result)
        assert 'data' in parsed


class TestCreateRiskContributionPlot:

    def test_returns_valid_json(self, app_context, loaded_calculator):
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()

        weights = np.array([0.4, 0.35, 0.25])
        risk_decomp = loaded_calculator.risk_decomposition(weights)
        result = vis.create_risk_contribution_plot(risk_decomp)
        parsed = json.loads(result)
        assert 'data' in parsed


class TestCreateSummaryDashboard:

    def test_returns_all_chart_types(self, app_context, sample_analysis_results):
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()

        charts = vis.create_summary_dashboard(sample_analysis_results)
        assert isinstance(charts, dict)
        # 主要キーが存在すること
        expected_keys = ['efficient_frontier', 'correlation_matrix', 'risk_return_scatter']
        for key in expected_keys:
            assert key in charts, f"Missing chart key: {key}"

    def test_all_charts_valid_json(self, app_context, sample_analysis_results):
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()

        charts = vis.create_summary_dashboard(sample_analysis_results)
        for key, chart_json in charts.items():
            parsed = json.loads(chart_json)
            assert 'data' in parsed, f"Chart {key} missing 'data' key"

    def test_partial_results(self, app_context):
        """一部データのみでもエラーにならないこと"""
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()

        partial = {'correlation_matrix': {'A': {'A': 1.0, 'B': 0.5}, 'B': {'A': 0.5, 'B': 1.0}}}
        charts = vis.create_summary_dashboard(partial)
        assert 'correlation_matrix' in charts


class TestCreateWorkingEfficientFrontierPlot:

    def test_returns_valid_json(self, app_context, loaded_calculator):
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()

        ef = loaded_calculator.calculate_efficient_frontier(20)
        stats = loaded_calculator.calculate_asset_statistics()
        result = vis.create_working_efficient_frontier_plot(
            ef.to_dict('records'),
            stats
        )
        parsed = json.loads(result)
        assert 'data' in parsed

    def test_with_optimal_portfolios(self, app_context, loaded_calculator):
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()

        ef = loaded_calculator.calculate_efficient_frontier(20)
        stats = loaded_calculator.calculate_asset_statistics()
        opt = loaded_calculator.optimize_portfolio()
        min_var = loaded_calculator.optimize_min_variance_portfolio()

        optimal = {}
        if opt['success']:
            optimal['max_sharpe'] = opt
        if min_var['success']:
            optimal['min_variance'] = min_var

        result = vis.create_working_efficient_frontier_plot(
            ef.to_dict('records'), stats, optimal
        )
        parsed = json.loads(result)
        assert 'data' in parsed

    def test_empty_ef_data(self, app_context):
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()

        result = vis.create_working_efficient_frontier_plot([], {})
        parsed = json.loads(result)
        assert 'data' in parsed
