import os

class Config:
    """基本設定クラス"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # データベース設定
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///portfolio.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # セッション設定
    SESSION_TIMEOUT = 3600  # 1時間
    
    # データ取得設定
    DATA_FETCH_TIMEOUT = 30  # 30秒
    
    # 計算設定
    DEFAULT_RISK_FREE_RATE = 0.01  # 1% (日本国債10年物の参考値)
    DEFAULT_SIMULATION_COUNT = 10000
    MIN_SIMULATION_COUNT = 1000
    MAX_SIMULATION_COUNT = 50000
    
    # バリデーション設定
    MIN_ASSETS = 2
    MAX_ASSETS = 20
    MIN_ANALYSIS_YEARS = 1
    MAX_ANALYSIS_YEARS = 31

class DevelopmentConfig(Config):
    """開発環境設定"""
    DEBUG = True

class ProductionConfig(Config):
    """本番環境設定"""
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
