"""
Tests for routes.py.
"""
import pytest


class TestIndexRoute:
    """Tests for GET /."""

    def test_index_redirects_to_en(self, client):
        resp = client.get('/')
        assert resp.status_code == 302
        assert '/en/' in resp.headers['Location']

    def test_index_follow_redirect(self, client):
        resp = client.get('/', follow_redirects=True)
        assert resp.status_code == 200


class TestIndexLangRoute:
    """Tests for GET /<lang>/."""

    def test_en_returns_200(self, client):
        resp = client.get('/en/')
        assert resp.status_code == 200

    def test_ja_returns_200(self, client):
        resp = client.get('/ja/')
        assert resp.status_code == 200

    def test_invalid_lang_redirects(self, client):
        resp = client.get('/fr/')
        assert resp.status_code == 302
        assert '/en/' in resp.headers['Location']

    def test_session_language_set_en(self, client):
        with client.session_transaction() as sess:
            sess.clear()
        client.get('/en/')
        with client.session_transaction() as sess:
            assert sess.get('language') == 'en'

    def test_session_language_set_ja(self, client):
        client.get('/ja/')
        with client.session_transaction() as sess:
            assert sess.get('language') == 'ja'

    def test_invalid_lang_xx_redirects(self, client):
        resp = client.get('/xx/')
        assert resp.status_code == 302

    def test_empty_lang_not_found(self, client):
        """An empty lang parameter is treated as / and redirected."""
        resp = client.get('//')
        # Flask may redirect // to / or return 404.
        assert resp.status_code in (301, 302, 308, 404)

    def test_risk_free_rate_initial_display_matches_decimal_value(self, client):
        # Arrange / Act
        response = client.get('/en/')
        html = response.get_data(as_text=True)

        # Assert: 5% on screen is represented as 0.05 in the API field.
        assert 'id="riskFreeRateValue">5</span>%' in html
        assert 'id="riskFreeRate" name="risk_free_rate" value="0.05"' in html


class TestFrontendFormDataContract:
    """Regression tests for percentage-to-decimal form serialization."""

    def test_form_data_serializer_is_defined_only_once(self, client):
        # Arrange / Act
        main_js = client.get('/static/js/main.js').get_data(as_text=True)
        portfolio_js = client.get('/static/js/portfolio.js').get_data(as_text=True)
        scripts = main_js + portfolio_js

        # Assert
        assert scripts.count('function getPortfolioFormData()') == 1
        assert 'function getFormData()' not in scripts
        assert main_js.count('getPortfolioFormData()') == 2
        assert portfolio_js.count('getPortfolioFormData()') == 1

    def test_risk_free_rate_decimal_is_not_divided_again(self, client):
        # Arrange / Act
        main_js = client.get('/static/js/main.js').get_data(as_text=True)

        # Assert: the hidden field already contains a decimal rate such as 0.005.
        assert "risk_free_rate: parseFloat(document.getElementById('riskFreeRate').value)" in main_js
        assert "document.getElementById('riskFreeRate').value) / 100" not in main_js

    def test_form_reset_resynchronizes_risk_free_rate_display(self, client):
        # Arrange / Act
        main_js = client.get('/static/js/main.js').get_data(as_text=True)

        # Assert
        assert "['riskFreeRateRange', 'targetReturnRange', 'simulationCountRange']" in main_js
        assert "document.getElementById('enableTargetReturn').dispatchEvent(new Event('change'))" in main_js
