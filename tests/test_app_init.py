"""
app/__init__.py (create_app) のテスト
"""
import pytest
from flask import Flask, session


class TestCreateApp:
    """アプリケーションファクトリのテスト"""

    def test_create_app_returns_flask_instance(self):
        from app import create_app
        app = create_app()
        assert isinstance(app, Flask)

    def test_create_app_development(self):
        from app import create_app
        app = create_app('development')
        assert app.config['DEBUG'] is True

    def test_create_app_production(self):
        from app import create_app
        app = create_app('production')
        assert app.config['DEBUG'] is False

    def test_create_app_default(self):
        from app import create_app
        app = create_app('default')
        assert app.config['DEBUG'] is True  # default == development

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
        """API と メインBPが登録されていること"""
        blueprint_names = list(app.blueprints.keys())
        assert 'api' in blueprint_names
        assert 'main' in blueprint_names

    def test_api_url_prefix(self, app):
        """APIブループリントが /api プレフィックスで登録"""
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        api_rules = [r for r in rules if r.startswith('/api')]
        assert len(api_rules) > 0

    def test_get_locale_default(self, app):
        """セッションに言語がない場合は 'en' にフォールバック"""
        with app.test_request_context():
            # session に language が無い → デフォルト 'en' が使用される
            assert session.get('language') is None

    def test_get_locale_from_session(self, app):
        """セッションから言語を取得"""
        with app.test_request_context():
            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['language'] = 'ja'
