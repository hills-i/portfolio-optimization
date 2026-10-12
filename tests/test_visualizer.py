"""
Tests for visualizer.py.
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
        """Weights below 0.5% are grouped into 'Others'."""
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
        # Ensure the primary chart keys are present.
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
        """Partial data should not raise an error."""
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


class TestCustomPortfolioTrace:

    @staticmethod
    def _custom_portfolio(calc):
        weights = np.array([0.5, 0.3, 0.2])
        return {
            'weights': dict(zip(calc.mean_returns.index, weights)),
            'metrics': calc.calculate_portfolio_metrics(weights)
        }

    @staticmethod
    def _trace_names(chart_json):
        return [trace.get('name') for trace in json.loads(chart_json)['data']]

    def test_efficient_frontier_plot_adds_marker(self, app_context, loaded_calculator, sample_mc_results):
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()
        ef_data = loaded_calculator.calculate_efficient_frontier(20).to_dict('records')
        custom = self._custom_portfolio(loaded_calculator)

        result = vis.create_efficient_frontier_plot(
            sample_mc_results.to_dict('records'), ef_data, None, custom
        )

        traces = [t for t in json.loads(result)['data'] if t.get('name') == 'Fixed Weights']
        assert len(traces) == 1
        assert traces[0]['x'] == [pytest.approx(custom['metrics']['risk'])]
        assert traces[0]['y'] == [pytest.approx(custom['metrics']['expected_return'])]

    def test_working_efficient_frontier_plot_adds_marker(self, app_context, loaded_calculator):
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()
        ef_data = loaded_calculator.calculate_efficient_frontier(20).to_dict('records')
        stats = loaded_calculator.calculate_asset_statistics()

        result = vis.create_working_efficient_frontier_plot(
            ef_data, stats, None, self._custom_portfolio(loaded_calculator)
        )

        assert self._trace_names(result).count('Fixed Weights') == 1

    def test_no_marker_without_custom_portfolio(self, app_context, sample_analysis_results):
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()

        charts = vis.create_summary_dashboard(sample_analysis_results)

        assert 'Fixed Weights' not in self._trace_names(charts['efficient_frontier'])
        assert 'Fixed Weights' not in self._trace_names(charts['mathematical_efficient_frontier'])

    def test_summary_dashboard_passes_custom_portfolio(self, app_context, loaded_calculator,
                                                      sample_analysis_results):
        from app.utils.visualizer import PortfolioVisualizer
        vis = PortfolioVisualizer()
        results = {
            **sample_analysis_results,
            'custom_portfolio': self._custom_portfolio(loaded_calculator)
        }

        charts = vis.create_summary_dashboard(results)

        assert 'Fixed Weights' in self._trace_names(charts['efficient_frontier'])
        assert 'Fixed Weights' in self._trace_names(charts['mathematical_efficient_frontier'])
