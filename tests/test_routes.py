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
