"""
Tests for config.py.
"""
import os
import pytest


class TestConfig:
    """Tests for the base Config settings."""

    def test_secret_key_comes_from_environment(self):
        from config import Config
        assert Config.SECRET_KEY == os.environ.get('SECRET_KEY')

    def test_default_risk_free_rate(self):
        from config import Config
        assert Config.DEFAULT_RISK_FREE_RATE == 0.01

    def test_default_simulation_count(self):
        from config import Config
        assert Config.DEFAULT_SIMULATION_COUNT == 10000

    def test_simulation_count_bounds(self):
        from config import Config
        assert Config.MIN_SIMULATION_COUNT == 1000
        assert Config.MAX_SIMULATION_COUNT == 50000

    def test_asset_bounds(self):
        from config import Config
        assert Config.MIN_ASSETS == 2
        assert Config.MAX_ASSETS == 20

    def test_analysis_years_bounds(self):
        from config import Config
        assert Config.MIN_ANALYSIS_YEARS == 1
        assert Config.MAX_ANALYSIS_YEARS == 31

    def test_data_fetch_timeout(self):
        from config import Config
        assert Config.DATA_FETCH_TIMEOUT == 30

    def test_session_timeout(self):
        from config import Config
        assert Config.SESSION_TIMEOUT == 3600


class TestDevelopmentConfig:
    def test_debug_is_true(self):
        from config import DevelopmentConfig
        assert DevelopmentConfig.DEBUG is True

    def test_has_development_secret_key_default(self):
        from config import DEV_SECRET_KEY, DevelopmentConfig
        assert DevelopmentConfig.SECRET_KEY is not None
        if os.environ.get('SECRET_KEY') is None:
            assert DevelopmentConfig.SECRET_KEY == DEV_SECRET_KEY

    def test_inherits_config(self):
        from config import DevelopmentConfig, Config
        assert issubclass(DevelopmentConfig, Config)


class TestProductionConfig:
    def test_debug_is_false(self):
        from config import ProductionConfig
        assert ProductionConfig.DEBUG is False

    def test_secret_key_must_come_from_environment(self):
        from config import ProductionConfig
        assert ProductionConfig.SECRET_KEY == os.environ.get('SECRET_KEY')

    def test_inherits_config(self):
        from config import ProductionConfig, Config
        assert issubclass(ProductionConfig, Config)


class TestConfigDict:
    def test_config_keys(self):
        from config import config
        assert 'development' in config
        assert 'production' in config
        assert 'default' in config

    def test_config_values(self):
        from config import config, DevelopmentConfig, ProductionConfig
        assert config['development'] is DevelopmentConfig
        assert config['production'] is ProductionConfig
        assert config['default'] is DevelopmentConfig
