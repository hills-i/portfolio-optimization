from flask import Flask, session, g
from flask_babel import Babel
from config import config

def create_app(config_name='default'):
    """Flask アプリケーションファクトリー"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Babel設定
    app.config['LANGUAGES'] = {
        'en': 'English',
        'ja': '日本語'
    }
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_DEFAULT_TIMEZONE'] = 'UTC'
    
    def get_locale():
        # セッションから言語を取得
        if 'language' in session:
            return session['language']
        return app.config['BABEL_DEFAULT_LOCALE']
    
    babel = Babel()
    babel.init_app(app, locale_selector=get_locale)
    
    # Make sure gettext is available in templates
    from flask_babel import gettext, ngettext
    app.jinja_env.globals.update(_=gettext, ngettext=ngettext)
    
    # APIブループリントの登録
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # メインルートの登録
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    return app