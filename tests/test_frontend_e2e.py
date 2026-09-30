"""
Browser tests for the frontend JavaScript (main.js / portfolio.js).

Requires: pip install pytest-playwright && playwright install chromium
Skipped automatically when Playwright is not installed.
"""
import json
import threading

import numpy as np
import pandas as pd
import pytest

pytest.importorskip('playwright')

from werkzeug.serving import make_server


@pytest.fixture(scope='module')
def live_server():
    """Run the Flask app on a random local port for the browser to access."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv('SECRET_KEY', 'test-secret-key')
        from app import create_app
        app = create_app('development')

    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown()


@pytest.fixture
def app_page(page, live_server):
    """Index page with API calls stubbed so no external data is fetched."""
    page.route('**/api/ticker/validate', lambda route: route.fulfill(
        status=200, content_type='application/json',
        body=json.dumps({'valid': True, 'exists': True}),
    ))
    page.js_errors = []
    page.on('pageerror', lambda error: page.js_errors.append(str(error)))
    page.goto(f'{live_server}/en/')
    page.wait_for_selector('.ticker-field')
    return page


class FakeDataFetcher:
    """Replaces yfinance access in the live server with generated prices."""

    def __init__(self, *args, **kwargs):
        pass

    def fetch_stock_data(self, tickers, start_date, end_date):
        rng = np.random.default_rng(42)
        dates = pd.bdate_range(start='2023-01-02', periods=300)
        df = pd.DataFrame({
            ticker: 100 * np.cumprod(1 + rng.normal(0.0004 + 0.0002 * i, 0.01 + 0.003 * i, len(dates)))
            for i, ticker in enumerate(tickers)
        }, index=dates)
        return {
            'success': True,
            'data': df,
            'errors': [],
            'warnings': [],
            'metadata': {
                'tickers_requested': tickers,
                'tickers_success': tickers,
                'tickers_failed': [],
                'start_date': start_date,
                'end_date': end_date,
                'total_records': len(df),
            },
        }


@pytest.fixture
def analyzed_page(app_page, monkeypatch):
    """Page after a successful analysis using the real backend and fake prices."""
    monkeypatch.setattr('app.api.portfolio.DataFetcher', FakeDataFetcher)
    app_page.fill('#simulationCountRange', '1000')
    app_page.check('#enableTargetReturn')
    app_page.click('#portfolioForm button[type="submit"]')
    app_page.wait_for_selector('#resultsArea.show', timeout=60000)
    app_page.wait_for_selector('#frontierChart.js-plotly-plot', timeout=30000)
    return app_page


def capture_analyze_request(page):
    """Submit the form and return the JSON body sent to /api/analyze."""
    page.route('**/api/analyze', lambda route: route.fulfill(
        status=400, content_type='application/json',
        body=json.dumps({'error': 'stubbed'}),
    ))
    with page.expect_request('**/api/analyze') as request_info:
        page.click('#portfolioForm button[type="submit"]')
    return request_info.value.post_data_json


class TestFormSerialization:

    def test_default_risk_free_rate_is_sent_as_decimal(self, app_page):
        body = capture_analyze_request(app_page)

        assert body['risk_free_rate'] == pytest.approx(0.05)
        assert body['simulation_count'] == 10000
        assert 'target_return' not in body

    def test_slider_change_is_sent_without_double_conversion(self, app_page):
        app_page.fill('#riskFreeRateRange', '3')

        body = capture_analyze_request(app_page)

        assert app_page.text_content('#riskFreeRateValue') == '3'
        assert body['risk_free_rate'] == pytest.approx(0.03)

    def test_enabled_target_return_is_sent_as_decimal(self, app_page):
        app_page.check('#enableTargetReturn')
        app_page.fill('#targetReturnRange', '15')

        body = capture_analyze_request(app_page)

        assert body['target_return'] == pytest.approx(0.15)


class TestResetForm:

    def test_reset_restores_hidden_values_and_display(self, app_page):
        app_page.fill('#riskFreeRateRange', '3')
        app_page.check('#enableTargetReturn')
        app_page.fill('#targetReturnRange', '20')
        app_page.fill('#simulationCountRange', '30000')

        app_page.click('button[onclick="resetForm()"]')

        assert app_page.input_value('#riskFreeRate') == '0.05'
        assert app_page.text_content('#riskFreeRateValue') == '5'
        assert app_page.input_value('#targetReturn') == '0.1'
        assert app_page.text_content('#targetReturnValue') == '10'
        assert app_page.input_value('#simulationCount') == '10000'
        assert app_page.text_content('#simulationCountValue') == '10,000'
        assert app_page.is_hidden('#targetReturnGroup')


class TestErrorMessageEscaping:

    def test_comparison_error_is_rendered_as_text(self, app_page):
        payload = '<img src=x onerror="window.__xss = true">'
        app_page.route('**/api/compare-simulations', lambda route: route.fulfill(
            status=400, content_type='application/json',
            body=json.dumps({'success': False, 'error': payload}),
        ))

        app_page.evaluate('compareSimulations()')
        result = app_page.locator('#simulationComparisonResult .error-detail')
        result.wait_for(state='attached')

        assert result.text_content() == payload
        assert app_page.locator('#simulationComparisonResult img').count() == 0
        assert app_page.evaluate('window.__xss') is None


class TestSuccessfulAnalysis:

    def test_results_are_rendered(self, analyzed_page):
        page = analyzed_page

        assert page.locator('#summaryCards .card').count() > 0
        assert page.text_content('#analysisTime').startswith('Analysis completed')
        assert page.locator('#portfolioTableMaxSharpe tr').count() > 0
        assert page.locator('#portfolioTableTargetReturn tr').count() > 0
        assert page.locator('#statsTable tr').count() > 0
        assert page.text_content('#basicStatsContent').strip()
        assert page.js_errors == []

    def test_result_tabs_render_charts(self, analyzed_page):
        page = analyzed_page

        for tab in ['allocation', 'correlation', 'assets', 'simulation', 'data']:
            page.click(f'#{tab}-tab')
            page.wait_for_selector(f'#{tab}.active.show')
        for pill in ['min-variance-tab', 'target-return-tab', 'max-sharpe-tab']:
            page.click('#allocation-tab')
            page.click(f'#{pill}')

        page.click('#correlation-tab')
        page.wait_for_selector('#correlationChart.js-plotly-plot')
        assert page.locator('#allocationChartMaxSharpe.js-plotly-plot').count() == 1
        assert page.js_errors == []

    def test_simulation_comparison_renders_table(self, analyzed_page):
        page = analyzed_page
        page.click('#simulation-tab')

        page.click('button[onclick="compareSimulations()"]')
        page.wait_for_selector('#simulationComparisonResult table', timeout=60000)

        assert page.locator('#simulationComparisonResult tbody tr').count() == 4
        assert page.js_errors == []

    def test_export_downloads_json(self, analyzed_page):
        page = analyzed_page

        with page.expect_download() as download_info:
            page.click('button[onclick="exportResults(\'json\')"]')

        with open(download_info.value.path(), encoding='utf-8') as f:
            exported = json.load(f)
        assert exported
        assert page.js_errors == []
