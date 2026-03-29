import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / '.env')

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///portfolio.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session settings
    SESSION_TIMEOUT = 3600  # 1 hour
    
    # Data retrieval settings
    DATA_FETCH_TIMEOUT = 30  # 30 seconds
    
    # Calculation settings
    DEFAULT_RISK_FREE_RATE = 0.01  # 1% (reference value based on 10-year Japanese government bonds)
    DEFAULT_SIMULATION_COUNT = 10000
    MIN_SIMULATION_COUNT = 1000
    MAX_SIMULATION_COUNT = 50000
    
    # Validation settings
    MIN_ASSETS = 2
    MAX_ASSETS = 20
    MIN_ANALYSIS_YEARS = 1
    MAX_ANALYSIS_YEARS = 31

class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True

class LocalConfig(Config):
    """Local runtime configuration."""
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'local': LocalConfig,
    'default': DevelopmentConfig
}
