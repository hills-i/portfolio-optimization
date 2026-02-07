from flask import request, jsonify, current_app, session
from flask_babel import force_locale
from app.api import bp
from app.utils.validator import InputValidator
from app.utils.data_fetcher import DataFetcher
from app.utils.calculator import PortfolioCalculator
from app.utils.visualizer import PortfolioVisualizer
import logging
import traceback
import numpy as np
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@contextmanager
def api_locale_context(language=None):
    """Context manager to set locale for API calls"""
    if language and language in ['en', 'ja']:
        session['language'] = language
        with force_locale(language):
            yield
    else:
        # Use existing session language or default
        locale = session.get('language', 'en')
        with force_locale(locale):
            yield

def create_validation_config():
    """Create validation configuration object"""
    class ValidationConfig:
        MIN_ASSETS = current_app.config.get('MIN_ASSETS', 2)
        MAX_ASSETS = current_app.config.get('MAX_ASSETS', 20)
        MIN_ANALYSIS_YEARS = current_app.config.get('MIN_ANALYSIS_YEARS', 1)
        MAX_ANALYSIS_YEARS = current_app.config.get('MAX_ANALYSIS_YEARS', 10)
        MIN_SIMULATION_COUNT = current_app.config.get('MIN_SIMULATION_COUNT', 1000)
        MAX_SIMULATION_COUNT = current_app.config.get('MAX_SIMULATION_COUNT', 50000)
    
    return ValidationConfig()

@bp.route('/validate', methods=['POST'])
def validate_inputs():
    """Validate input data"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Input data is required'}), 400
        
        validator = InputValidator(create_validation_config())
        result = validator.validate_all_inputs(data)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Input validation error: {str(e)}")
        return jsonify({'error': 'An error occurred during input validation'}), 500

@bp.route('/ticker/validate', methods=['POST'])
def validate_tickers():
    """Validate ticker symbol existence"""
    try:
        data = request.get_json()
        tickers = data.get('tickers', [])
        
        if not tickers:
            return jsonify({'error': 'Ticker symbols are required'}), 400
        
        fetcher = DataFetcher(timeout=current_app.config.get('DATA_FETCH_TIMEOUT', 30))
        validation_result = fetcher.validate_tickers(tickers)
        
        return jsonify({
            'valid_tickers': validation_result,
            'all_valid': all(validation_result.values())
        })
        
    except Exception as e:
        logger.error(f"Ticker validation error: {str(e)}")
        return jsonify({'error': 'An error occurred during ticker validation'}), 500

@bp.route('/ticker/info', methods=['POST'])
def get_ticker_info():
    """Get ticker detailed information"""
    try:
        data = request.get_json()
        ticker = data.get('ticker')
        
        if not ticker:
            return jsonify({'error': 'Ticker symbol is required'}), 400
        
        fetcher = DataFetcher()
        info = fetcher.get_ticker_info(ticker)
        
        return jsonify(info)
        
    except Exception as e:
        logger.error(f"Ticker info error: {str(e)}")
        return jsonify({'error': 'An error occurred while retrieving ticker information'}), 500

@bp.route('/analyze', methods=['POST'])
def analyze_portfolio():
    """Main portfolio analysis processing"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Analysis data is required'}), 400
        
        # Get language parameter and set session language
        language = data.get('language', 'en')
        if language and language in ['en', 'ja']:
            session['language'] = language
        
        # Input validation
        validator = InputValidator(create_validation_config())
        validation_result = validator.validate_all_inputs(data)
        
        if not validation_result['valid']:
            return jsonify({
                'error': 'There are issues with the input data',
                'validation_errors': validation_result['errors']
            }), 400
        
        # Parameter extraction
        tickers = data.get('tickers', [])
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        target_return = data.get('target_return')  # Optional
        
        try:
            risk_free_rate = float(data.get('risk_free_rate', current_app.config.get('DEFAULT_RISK_FREE_RATE', 0.005)))
            simulation_count = int(data.get('simulation_count', current_app.config.get('DEFAULT_SIMULATION_COUNT', 10000)))
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid parameter types for risk_free_rate or simulation_count'}), 400
        
        # Data retrieval
        logger.info(f"Starting portfolio analysis for tickers: {tickers}")
        logger.info(f"Date range: {start_date} to {end_date}")
        logger.info(f"Parameters: risk_free_rate={risk_free_rate}, simulation_count={simulation_count}")
        
        try:
            fetcher = DataFetcher(timeout=current_app.config.get('DATA_FETCH_TIMEOUT', 30))
            fetch_result = fetcher.fetch_stock_data(tickers, start_date, end_date)
            logger.info(f"Data fetch completed: success={fetch_result['success']}")
        except Exception as e:
            logger.error(f"Data fetch failed: {str(e)}")
            raise
        
        if not fetch_result['success']:
            return jsonify({
                'error': 'Failed to retrieve data',
                'details': fetch_result['errors'],
                'warnings': fetch_result.get('warnings', [])
            }), 400
        
        # Portfolio calculation
        try:
            logger.info("Initializing portfolio calculator")
            calculator = PortfolioCalculator()
            
            logger.info(f"Loading data: shape={fetch_result['data'].shape}")
            if not calculator.load_data(fetch_result['data'], risk_free_rate):
                return jsonify({'error': 'Failed to load data'}), 500
            logger.info("Data loaded successfully")
        except Exception as e:
            logger.error(f"Portfolio calculation setup failed: {str(e)}")
            raise
        
        # Initialize analysis results
        results = {
            'success': True,
            'metadata': fetch_result['metadata'],
            'warnings': fetch_result.get('warnings', [])
        }
        
        # Individual asset statistics
        asset_stats = calculator.calculate_asset_statistics()
        results['asset_statistics'] = asset_stats
        
        # Correlation matrix
        correlation_matrix = calculator.calculate_correlation_matrix()
        results['correlation_matrix'] = correlation_matrix.to_dict()
        
        # Monte Carlo simulation
        try:
            logger.info(f"Running Monte Carlo simulation with {simulation_count} iterations")
            mc_results = calculator.monte_carlo_simulation(simulation_count)
            logger.info(f"Monte Carlo simulation completed: {len(mc_results)} results")
            
            # Execute detailed analysis
            detailed_analysis = calculator.analyze_monte_carlo_results(mc_results)
            
        except Exception as e:
            logger.error(f"Monte Carlo simulation failed: {str(e)}")
            raise
        
        results['monte_carlo'] = {
            'simulations': mc_results.to_dict('records'),
            'detailed_analysis': detailed_analysis,
            'summary_stats': {
                'mean_return': mc_results['expected_return'].mean(),
                'mean_risk': mc_results['risk'].mean(),
                'mean_sharpe': mc_results['sharpe_ratio'].mean(),
                'max_sharpe': mc_results['sharpe_ratio'].max(),
                'min_risk': mc_results['risk'].min()
            }
        }
        
        # Optimal portfolio calculation
        # 1. Maximum Sharpe ratio portfolio
        max_sharpe_result = calculator.optimize_portfolio()
        if max_sharpe_result['success']:
            results['optimal_portfolios'] = {
                'max_sharpe': max_sharpe_result
            }
            
            # Risk decomposition analysis
            weights_array = np.array(list(max_sharpe_result['weights'].values()))
            risk_decomp = calculator.risk_decomposition(weights_array)
            results['optimal_portfolios']['max_sharpe']['risk_decomposition'] = risk_decomp
        
        # 2. Minimum risk portfolio with target return
        if target_return is not None:
            min_risk_result = calculator.optimize_portfolio(target_return=target_return)
            if min_risk_result['success']:
                results['optimal_portfolios']['target_return'] = min_risk_result
                
                # Risk decomposition analysis
                weights_array = np.array(list(min_risk_result['weights'].values()))
                risk_decomp = calculator.risk_decomposition(weights_array)
                results['optimal_portfolios']['target_return']['risk_decomposition'] = risk_decomp
        
        # 3. Minimum variance portfolio (pure minimum variance without constraints)
        # Minimize variance without target return constraint
        try:
            # First try constraint-free minimum variance portfolio
            min_var_result = calculator.optimize_min_variance_portfolio()
        except Exception as e:
            # Fallback to traditional method
            logger.warning(f"Using fallback min variance calculation: {e}")
            min_expected_return = min(asset_stats[asset]['expected_return'] for asset in asset_stats)
            min_var_result = calculator.optimize_portfolio(target_return=min_expected_return)
        if min_var_result['success']:
            if 'optimal_portfolios' not in results:
                results['optimal_portfolios'] = {}
            results['optimal_portfolios']['min_variance'] = min_var_result
            
            # Risk decomposition analysis
            weights_array = np.array(list(min_var_result['weights'].values()))
            risk_decomp = calculator.risk_decomposition(weights_array)
            results['optimal_portfolios']['min_variance']['risk_decomposition'] = risk_decomp
        
        # Efficient frontier
        try:
            logger.info("Calculating efficient frontier")
            efficient_frontier = calculator.calculate_efficient_frontier(num_portfolios=30)
            results['efficient_frontier'] = efficient_frontier.to_dict('records')
        except Exception as e:
            logger.warning(f"Efficient frontier calculation failed: {str(e)}")
            results['warnings'].append('Failed to calculate efficient frontier')
        
        logger.info("Portfolio analysis completed successfully")


        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Portfolio analysis error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': 'An error occurred during portfolio analysis',
        }), 500

@bp.route('/compare-simulations', methods=['POST'])
def compare_simulation_counts():
    """Compare results across different simulation counts"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Comparison data is required'}), 400
        
        # Get language parameter and set session language
        language = data.get('language', 'en')
        if language and language in ['en', 'ja']:
            session['language'] = language
        
        # Input validation
        validator = InputValidator(create_validation_config())
        validation_result = validator.validate_all_inputs(data)
        
        if not validation_result['valid']:
            return jsonify({
                'error': 'There are issues with the input data',
                'validation_errors': validation_result['errors']
            }), 400
        
        # Parameter extraction
        tickers = data.get('tickers', [])
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        try:
            risk_free_rate = float(data.get('risk_free_rate', current_app.config.get('DEFAULT_RISK_FREE_RATE', 0.005)))
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid parameter type for risk_free_rate'}), 400
        
        simulation_counts = data.get('simulation_counts', [100, 1000, 5000, 10000])
        
        # Validate simulation_counts
        max_simulation_count = current_app.config.get('MAX_SIMULATION_COUNT', 50000)
        if not isinstance(simulation_counts, list) or len(simulation_counts) == 0 or len(simulation_counts) > 10:
            return jsonify({'error': 'simulation_counts must be a list of 1-10 items'}), 400
        try:
            simulation_counts = [int(c) for c in simulation_counts]
        except (TypeError, ValueError):
            return jsonify({'error': 'All simulation_counts must be integers'}), 400
        if any(c <= 0 or c > max_simulation_count for c in simulation_counts):
            return jsonify({'error': f'Each simulation count must be between 1 and {max_simulation_count}'}), 400
        
        # Data retrieval
        logger.info(f"Starting simulation comparison for tickers: {tickers}")
        logger.info(f"Comparing simulation counts: {simulation_counts}")
        
        try:
            fetcher = DataFetcher(timeout=current_app.config.get('DATA_FETCH_TIMEOUT', 30))
            fetch_result = fetcher.fetch_stock_data(tickers, start_date, end_date)
        except Exception as e:
            logger.error(f"Data fetch failed: {str(e)}")
            raise
        
        if not fetch_result['success']:
            return jsonify({
                'error': 'Failed to retrieve data',
                'details': fetch_result['errors']
            }), 400
        
        # Execute comparison analysis
        try:
            calculator = PortfolioCalculator()
            if not calculator.load_data(fetch_result['data'], risk_free_rate):
                return jsonify({'error': 'Failed to load data'}), 500
            
            comparison_results = calculator.compare_simulation_counts(simulation_counts)
            
        except Exception as e:
            logger.error(f"Simulation comparison failed: {str(e)}")
            raise
        
        return jsonify({
            'success': True,
            'comparison_results': comparison_results,
            'metadata': fetch_result['metadata']
        })
        
    except Exception:
        logger.exception("Simulation comparison error")
        return jsonify({
            'error': 'An error occurred during simulation comparison'
        }), 500

@bp.route('/visualize', methods=['POST'])
def create_visualizations():
    """Create visualization charts"""
    try:
        data = request.get_json()
        analysis_results = data.get('results')
        chart_types = data.get('chart_types', ['efficient_frontier', 'mathematical_efficient_frontier'])  # Chart types to generate
        language = data.get('language', 'en')  # Get language parameter


        # Handle 'all' chart type request
        if chart_types == ['all']:
            # Use create_summary_dashboard for 'all' request
            chart_types = ['all']

        if not analysis_results:
            return jsonify({'error': 'Analysis result data is required'}), 400
        
        # Use locale context for chart generation
        with api_locale_context(language):
            visualizer = PortfolioVisualizer()
            charts = {}
            
            # Generate each requested chart
            for chart_type in chart_types:
                try:
                    if chart_type == 'efficient_frontier':
                        if ('monte_carlo' in analysis_results and
                            'efficient_frontier' in analysis_results):
                            charts[chart_type] = visualizer.create_efficient_frontier_plot(
                                analysis_results['monte_carlo']['simulations'],
                                analysis_results['efficient_frontier'],
                                analysis_results.get('optimal_portfolios')
                            )

                    elif chart_type == 'mathematical_efficient_frontier':
                        if ('efficient_frontier' in analysis_results and
                            'asset_statistics' in analysis_results):
                            # 機能追加版を使用
                            charts[chart_type] = visualizer.create_working_efficient_frontier_plot(
                                analysis_results['efficient_frontier'],
                                analysis_results['asset_statistics'],
                                analysis_results.get('optimal_portfolios')
                            )
                    
                    elif chart_type == 'asset_allocation':
                        if ('optimal_portfolios' in analysis_results and 
                            'max_sharpe' in analysis_results['optimal_portfolios']):
                            max_sharpe_weights = analysis_results['optimal_portfolios']['max_sharpe']['weights']
                            charts[chart_type] = visualizer.create_asset_allocation_plot(
                                max_sharpe_weights,
                                "Optimal Portfolio Asset Allocation (Max Sharpe Ratio)"
                            )
                    
                    elif chart_type == 'correlation_matrix':
                        if 'correlation_matrix' in analysis_results:
                            charts[chart_type] = visualizer.create_correlation_heatmap(
                                analysis_results['correlation_matrix']
                            )
                    
                    elif chart_type == 'risk_return_scatter':
                        if 'asset_statistics' in analysis_results:
                            charts[chart_type] = visualizer.create_risk_return_scatter(
                                analysis_results['asset_statistics']
                            )
                    
                    elif chart_type == 'risk_contribution':
                        if ('optimal_portfolios' in analysis_results and 
                            'max_sharpe' in analysis_results['optimal_portfolios'] and
                            'risk_decomposition' in analysis_results['optimal_portfolios']['max_sharpe']):
                            charts[chart_type] = visualizer.create_risk_contribution_plot(
                                analysis_results['optimal_portfolios']['max_sharpe']['risk_decomposition']
                            )
                    
                    elif chart_type == 'all':
                        # Generate all charts
                        charts = visualizer.create_summary_dashboard(analysis_results)
                        logger.info(f"Generated chart keys: {list(charts.keys())}")
                    
                        
                except Exception as e:
                    logger.warning(f"Failed to create chart {chart_type}: {str(e)}")
                    continue
        
        return jsonify({
            'success': True,
            'charts': charts,
            'chart_count': len(charts)
        })
        
    except Exception as e:
        logger.error(f"Visualization error: {str(e)}")
        return jsonify({'error': 'An error occurred during visualization processing'}), 500

@bp.route('/export', methods=['POST'])
def export_results():
    """Export results"""
    try:
        data = request.get_json()
        export_format = data.get('format', 'json')  # json, csv
        results_data = data.get('results')
        language = data.get('language', 'en')
        
        # Set session language
        if language and language in ['en', 'ja']:
            session['language'] = language
        
        if not results_data:
            return jsonify({'error': 'Data to export is required'}), 400
        
        if export_format == 'csv':
            # CSV format export processing
            # Implementation to be added in the future
            return jsonify({'error': 'CSV export is currently under development'}), 501
        
        # JSON format (default)
        return jsonify({
            'success': True,
            'data': results_data,
            'export_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({'error': 'An error occurred during export'}), 500

@bp.route('/health', methods=['GET'])
def health_check():
    """API health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })