import os

from flask import Flask, session, g
from flask_babel import Babel
from config import config

def create_app(config_name='default'):
    """Flask application factory."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    if not app.config['SECRET_KEY']:
        raise RuntimeError('SECRET_KEY environment variable is required')
    
    # Babel configuration
    app.config['LANGUAGES'] = {
        'en': 'English',
        'ja': '日本語'
    }
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_DEFAULT_TIMEZONE'] = 'UTC'
    
    def get_locale():
        # Read the language from the session.
        if 'language' in session:
            return session['language']
        return app.config['BABEL_DEFAULT_LOCALE']
    
    babel = Babel()
    babel.init_app(app, locale_selector=get_locale)
    
    # Make sure gettext is available in templates
    from flask_babel import gettext, ngettext
    app.jinja_env.globals.update(_=gettext, ngettext=ngettext)
    
    # Register the API blueprint.
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register the main routes.
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    return app
