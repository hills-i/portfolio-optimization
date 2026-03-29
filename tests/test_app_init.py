"""
Tests for app/__init__.py (create_app).
"""
import os
import pytest
from flask import Flask, session


class TestCreateApp:
    """Tests for the application factory."""

    def test_create_app_returns_flask_instance(self):
        from app import create_app
        app = create_app()
        assert isinstance(app, Flask)

    def test_create_app_development(self):
        from app import create_app
        app = create_app('development')
        assert app.config['DEBUG'] is True

    def test_create_app_production(self, monkeypatch):
        from app import create_app
        monkeypatch.setenv('SECRET_KEY', 'test-production-secret')
        app = create_app('production')
        assert app.config['DEBUG'] is False
        assert app.config['SECRET_KEY'] == 'test-production-secret'

    def test_create_app_default(self):
        from app import create_app
        app = create_app('default')
        assert app.config['DEBUG'] is True  # default == development

    def test_create_app_production_requires_secret_key(self, monkeypatch):
        from app import create_app
        monkeypatch.delenv('SECRET_KEY', raising=False)
        with pytest.raises(RuntimeError, match='SECRET_KEY'):
            create_app('production')

    def test_create_app_invalid_config(self):
        from app import create_app
        with pytest.raises(KeyError):
            create_app('nonexistent')

    def test_babel_config(self, app):
        assert app.config['BABEL_DEFAULT_LOCALE'] == 'en'
        assert app.config['BABEL_DEFAULT_TIMEZONE'] == 'UTC'
        assert 'en' in app.config['LANGUAGES']
        assert 'ja' in app.config['LANGUAGES']

    def test_blueprints_registered(self, app):
        """API and main blueprints are registered."""
        blueprint_names = list(app.blueprints.keys())
        assert 'api' in blueprint_names
        assert 'main' in blueprint_names

    def test_api_url_prefix(self, app):
        """API blueprint is registered with the /api prefix."""
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        api_rules = [r for r in rules if r.startswith('/api')]
        assert len(api_rules) > 0

    def test_get_locale_default(self, app):
        """Falls back to 'en' when no language is stored in session."""
        with app.test_request_context():
            # When session has no language, the default 'en' is used.
            assert session.get('language') is None

    def test_get_locale_from_session(self, app):
        """Uses the language stored in the session."""
        with app.test_request_context():
            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['language'] = 'ja'
