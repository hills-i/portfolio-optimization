from flask import request, jsonify, current_app
from app.api import bp
from app.utils.validator import InputValidator
from app.utils.data_fetcher import DataFetcher
from app.utils.calculator import PortfolioCalculator
from app.utils.visualizer import PortfolioVisualizer
import logging
import traceback
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

def create_validation_config():
    """バリデーション用の設定オブジェクトを作成"""
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
    """入力データの検証"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': '入力データが必要です'}), 400
        
        validator = InputValidator(create_validation_config())
        result = validator.validate_all_inputs(data)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Input validation error: {str(e)}")
        return jsonify({'error': '入力検証中にエラーが発生しました'}), 500

@bp.route('/ticker/validate', methods=['POST'])
def validate_tickers():
    """ティッカーシンボルの存在確認"""
    try:
        data = request.get_json()
        tickers = data.get('tickers', [])
        
        if not tickers:
            return jsonify({'error': 'ティッカーシンボルが必要です'}), 400
        
        fetcher = DataFetcher(timeout=current_app.config.get('DATA_FETCH_TIMEOUT', 30))
        validation_result = fetcher.validate_tickers(tickers)
        
        return jsonify({
            'valid_tickers': validation_result,
            'all_valid': all(validation_result.values())
        })
        
    except Exception as e:
        logger.error(f"Ticker validation error: {str(e)}")
        return jsonify({'error': 'ティッカー検証中にエラーが発生しました'}), 500

@bp.route('/ticker/info', methods=['POST'])
def get_ticker_info():
    """ティッカーの詳細情報取得"""
    try:
        data = request.get_json()
        ticker = data.get('ticker')
        
        if not ticker:
            return jsonify({'error': 'ティッカーシンボルが必要です'}), 400
        
        fetcher = DataFetcher()
        info = fetcher.get_ticker_info(ticker)
        
        return jsonify(info)
        
    except Exception as e:
        logger.error(f"Ticker info error: {str(e)}")
        return jsonify({'error': 'ティッカー情報の取得中にエラーが発生しました'}), 500

@bp.route('/analyze', methods=['POST'])
def analyze_portfolio():
    """ポートフォリオ分析のメイン処理"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': '分析データが必要です'}), 400
        
        # 入力検証
        validator = InputValidator(create_validation_config())
        validation_result = validator.validate_all_inputs(data)
        
        if not validation_result['valid']:
            return jsonify({
                'error': '入力データに問題があります',
                'validation_errors': validation_result['errors']
            }), 400
        
        # パラメータ抽出
        tickers = data.get('tickers', [])
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        risk_free_rate = data.get('risk_free_rate', current_app.config.get('DEFAULT_RISK_FREE_RATE', 0.005))
        simulation_count = data.get('simulation_count', current_app.config.get('DEFAULT_SIMULATION_COUNT', 10000))
        target_return = data.get('target_return')  # オプション
        
        # データ取得
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
                'error': 'データ取得に失敗しました',
                'details': fetch_result['errors'],
                'warnings': fetch_result.get('warnings', [])
            }), 400
        
        # ポートフォリオ計算
        try:
            logger.info("Initializing portfolio calculator")
            calculator = PortfolioCalculator()
            
            logger.info(f"Loading data: shape={fetch_result['data'].shape}")
            if not calculator.load_data(fetch_result['data'], risk_free_rate):
                return jsonify({'error': 'データの読み込みに失敗しました'}), 500
            logger.info("Data loaded successfully")
        except Exception as e:
            logger.error(f"Portfolio calculation setup failed: {str(e)}")
            raise
        
        # 分析結果の初期化
        results = {
            'success': True,
            'metadata': fetch_result['metadata'],
            'warnings': fetch_result.get('warnings', [])
        }
        
        # 個別資産の統計情報
        asset_stats = calculator.calculate_asset_statistics()
        results['asset_statistics'] = asset_stats
        
        # 相関行列
        correlation_matrix = calculator.calculate_correlation_matrix()
        results['correlation_matrix'] = correlation_matrix.to_dict()
        
        # モンテカルロシミュレーション
        try:
            logger.info(f"Running Monte Carlo simulation with {simulation_count} iterations")
            mc_results = calculator.monte_carlo_simulation(simulation_count)
            logger.info(f"Monte Carlo simulation completed: {len(mc_results)} results")
        except Exception as e:
            logger.error(f"Monte Carlo simulation failed: {str(e)}")
            raise
        results['monte_carlo'] = {
            'simulations': mc_results.to_dict('records'),
            'summary_stats': {
                'mean_return': mc_results['expected_return'].mean(),
                'mean_risk': mc_results['risk'].mean(),
                'mean_sharpe': mc_results['sharpe_ratio'].mean(),
                'max_sharpe': mc_results['sharpe_ratio'].max(),
                'min_risk': mc_results['risk'].min()
            }
        }
        
        # 最適ポートフォリオの計算
        # 1. 最大シャープレシオポートフォリオ
        max_sharpe_result = calculator.optimize_portfolio()
        if max_sharpe_result['success']:
            results['optimal_portfolios'] = {
                'max_sharpe': max_sharpe_result
            }
            
            # リスク分解分析
            weights_array = np.array(list(max_sharpe_result['weights'].values()))
            risk_decomp = calculator.risk_decomposition(weights_array)
            results['optimal_portfolios']['max_sharpe']['risk_decomposition'] = risk_decomp
        
        # 2. 目標リターン指定時の最小リスクポートフォリオ
        if target_return is not None:
            min_risk_result = calculator.optimize_portfolio(target_return=target_return)
            if min_risk_result['success']:
                results['optimal_portfolios']['target_return'] = min_risk_result
                
                # リスク分解分析
                weights_array = np.array(list(min_risk_result['weights'].values()))
                risk_decomp = calculator.risk_decomposition(weights_array)
                results['optimal_portfolios']['target_return']['risk_decomposition'] = risk_decomp
        
        # 3. 最小分散ポートフォリオ（目標リターン=最小期待リターン）
        min_expected_return = min(asset_stats[asset]['expected_return'] for asset in asset_stats)
        min_var_result = calculator.optimize_portfolio(target_return=min_expected_return)
        if min_var_result['success']:
            if 'optimal_portfolios' not in results:
                results['optimal_portfolios'] = {}
            results['optimal_portfolios']['min_variance'] = min_var_result
        
        # 効率的フロンティア
        try:
            logger.info("Calculating efficient frontier")
            efficient_frontier = calculator.calculate_efficient_frontier(num_portfolios=30)
            results['efficient_frontier'] = efficient_frontier.to_dict('records')
        except Exception as e:
            logger.warning(f"Efficient frontier calculation failed: {str(e)}")
            results['warnings'].append('効率的フロンティアの計算に失敗しました')
        
        logger.info("Portfolio analysis completed successfully")
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Portfolio analysis error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': 'ポートフォリオ分析中にエラーが発生しました',
            'details': str(e),
            'type': type(e).__name__
        }), 500

@bp.route('/visualize', methods=['POST'])
def create_visualizations():
    """可視化グラフの作成"""
    try:
        data = request.get_json()
        analysis_results = data.get('results')
        chart_types = data.get('chart_types', ['efficient_frontier'])  # 生成するグラフタイプ
        
        if not analysis_results:
            return jsonify({'error': '分析結果データが必要です'}), 400
        
        visualizer = PortfolioVisualizer()
        charts = {}
        
        # 要求された各グラフを生成
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
                
                elif chart_type == 'asset_allocation':
                    if ('optimal_portfolios' in analysis_results and 
                        'max_sharpe' in analysis_results['optimal_portfolios']):
                        max_sharpe_weights = analysis_results['optimal_portfolios']['max_sharpe']['weights']
                        charts[chart_type] = visualizer.create_asset_allocation_plot(
                            max_sharpe_weights,
                            "最適ポートフォリオ資産配分（最大シャープレシオ）"
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
                    # 全てのグラフを生成
                    charts = visualizer.create_summary_dashboard(analysis_results)
                    
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
        return jsonify({'error': '可視化処理中にエラーが発生しました'}), 500

@bp.route('/export', methods=['POST'])
def export_results():
    """結果のエクスポート"""
    try:
        data = request.get_json()
        export_format = data.get('format', 'json')  # json, csv
        results_data = data.get('results')
        
        if not results_data:
            return jsonify({'error': 'エクスポートするデータが必要です'}), 400
        
        if export_format == 'csv':
            # CSV形式でのエクスポート処理
            # 実装は将来的に追加
            return jsonify({'error': 'CSV出力は現在実装中です'}), 501
        
        # JSON形式（デフォルト）
        return jsonify({
            'success': True,
            'data': results_data,
            'export_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({'error': 'エクスポート中にエラーが発生しました'}), 500

@bp.route('/health', methods=['GET'])
def health_check():
    """API健康性チェック"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })