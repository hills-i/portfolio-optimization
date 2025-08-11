from flask import Flask
from config import config

def create_app(config_name='default'):
    """Flask アプリケーションファクトリー"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # APIブループリントの登録
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # メインルートの登録
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    return app