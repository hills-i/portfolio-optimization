import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm
from typing import List, Dict, Any, Optional, Tuple
import logging
from flask_babel import gettext as _

logger = logging.getLogger(__name__)

class PortfolioCalculator:
    """ポートフォリオ計算クラス"""
    
    def __init__(self):
        self.returns = None
        self.mean_returns = None
        self.cov_matrix = None
        self.risk_free_rate = 0.0
    
    def load_data(self, price_data: pd.DataFrame, risk_free_rate: float = 0.0) -> bool:
        """
        価格データの読み込みと前処理
        
        Args:
            price_data: 価格データのDataFrame
            risk_free_rate: 無リスク金利 (年率)
            
        Returns:
            bool: 処理成功フラグ
        """
        try:
            # 日次リターンの計算
            self.returns = price_data.pct_change().dropna()
            
            # 年率換算の期待リターン計算（252営業日）
            self.mean_returns = self.returns.mean() * 252
            
            # 共分散行列計算（年率換算）
            self.cov_matrix = self.returns.cov() * 252
            
            self.risk_free_rate = risk_free_rate
            
            logger.info(f"Portfolio data loaded successfully: {len(self.returns.columns)} assets, {len(self.returns)} days")
            return True
            
        except Exception as e:
            logger.error(f"Error loading portfolio data: {str(e)}")
            return False
    
    def calculate_portfolio_metrics(self, weights: np.ndarray) -> Dict[str, float]:
        """
        ポートフォリオの基本メトリクス計算
        
        Args:
            weights: 資産配分（合計=1）
            
        Returns:
            Dict: ポートフォリオメトリクス
        """
        # 期待リターン
        expected_return = np.sum(self.mean_returns * weights)
        
        # リスク（標準偏差）
        portfolio_variance = np.dot(weights.T, np.dot(self.cov_matrix, weights))
        portfolio_risk = np.sqrt(portfolio_variance)
        
        # シャープレシオ
        excess_return = expected_return - self.risk_free_rate
        sharpe_ratio = excess_return / portfolio_risk if portfolio_risk > 0 else 0
        
        return {
            'expected_return': expected_return,
            'risk': portfolio_risk,
            'sharpe_ratio': sharpe_ratio,
            'variance': portfolio_variance
        }
    
    def monte_carlo_simulation(self, num_simulations: int = 10000) -> pd.DataFrame:
        """
        モンテカルロシミュレーション
        
        Args:
            num_simulations: シミュレーション回数
            
        Returns:
            pd.DataFrame: シミュレーション結果
        """
        if self.returns is None:
            raise ValueError(_('Data not loaded. Call load_data() first.'))
        
        num_assets = len(self.mean_returns)
        results = []
        
        logger.info(f"Starting Monte Carlo simulation with {num_simulations} iterations")
        
        for i in range(num_simulations):
            # ランダムな重みを生成
            weights = np.random.random(num_assets)
            weights = weights / np.sum(weights)  # 正規化
            
            # デバッグ用：最初の5回のシミュレーションの重みをログ出力
            if i < 5:
                weight_info = {asset: f"{weight:.3f}" for asset, weight in zip(self.mean_returns.index, weights)}
                logger.info(f"Simulation {i+1} weights: {weight_info}")
            
            # ポートフォリオメトリクス計算
            metrics = self.calculate_portfolio_metrics(weights)
            
            # 結果を保存
            result = {
                'expected_return': metrics['expected_return'],
                'risk': metrics['risk'],
                'sharpe_ratio': metrics['sharpe_ratio']
            }
            
            # 各資産の配分も保存
            for j, asset in enumerate(self.mean_returns.index):
                result[f'weight_{asset}'] = weights[j]
            
            results.append(result)
        
        df = pd.DataFrame(results)
        logger.info("Monte Carlo simulation completed successfully")
        
        return df
    
    def monte_carlo_simulation_returns(self, num_simulations: int = 10000, time_horizon: int = 252) -> pd.DataFrame:
        """
        真のモンテカルロシミュレーション（将来リターンを確率的に予測）
        
        Args:
            num_simulations: シミュレーション回数
            time_horizon: 予測期間（営業日数、デフォルト1年=252日）
            
        Returns:
            pd.DataFrame: シミュレーション結果
        """
        if self.returns is None:
            raise ValueError(_('Data not loaded. Call load_data() first.'))
        
        num_assets = len(self.mean_returns)
        results = []
        
        logger.info(f"Starting return-based Monte Carlo simulation with {num_simulations} iterations")
        
        # 固定された最適配分を使用（比較のため）
        optimal_result = self.optimize_portfolio()
        if optimal_result['success']:
            optimal_weights = np.array(list(optimal_result['weights'].values()))
        else:
            # フォールバック：等配分
            optimal_weights = np.ones(num_assets) / num_assets
            
        logger.info(f"Using fixed weights for return simulation: {dict(zip(self.mean_returns.index, optimal_weights))}")
        
        for i in range(num_simulations):
            # 将来リターンをランダムに生成（多変量正規分布から）
            simulated_returns = np.random.multivariate_normal(
                self.mean_returns.values / 252,  # 日次リターンに変換
                self.cov_matrix.values / 252,    # 日次共分散に変換
                time_horizon
            )
            
            # 累積リターンを計算
            cumulative_returns = np.prod(1 + simulated_returns, axis=0) - 1
            
            # ポートフォリオリターンを計算
            portfolio_return = np.dot(optimal_weights, cumulative_returns)
            
            # 日次リターンの標準偏差からポートフォリオリスクを計算
            portfolio_variance = np.dot(optimal_weights.T, np.dot(self.cov_matrix, optimal_weights))
            portfolio_risk = np.sqrt(portfolio_variance)
            
            # シャープレシオ
            sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_risk if portfolio_risk > 0 else 0
            
            result = {
                'simulated_return': portfolio_return,
                'risk': portfolio_risk,
                'sharpe_ratio': sharpe_ratio,
                'simulation_type': 'return_based'
            }
            
            # デバッグ用：最初の5回の結果をログ出力
            if i < 5:
                logger.info(f"Return simulation {i+1}: return={portfolio_return:.4f}, risk={portfolio_risk:.4f}")
            
            results.append(result)
        
        df = pd.DataFrame(results)
        logger.info("Return-based Monte Carlo simulation completed successfully")
        
        return df
    
    def optimize_min_variance_portfolio(self) -> Dict[str, Any]:
        """
        最小分散ポートフォリオ最適化（制約なし）
        
        Returns:
            Dict: 最適化結果
        """
        if self.returns is None:
            raise ValueError(_('Data not loaded. Call load_data() first.'))
        
        num_assets = len(self.mean_returns)
        
        # 初期推定値（等重み）
        initial_weights = np.ones(num_assets) / num_assets
        
        # 制約条件
        constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]  # 重みの合計=1
        
        # 境界条件（0 <= 重み <= 1、空売り制限）
        bounds = tuple((0, 1) for _ in range(num_assets))
        
        try:
            # 分散最小化（リターン制約なし）
            def objective(weights):
                return np.dot(weights, np.dot(self.cov_matrix, weights))  # ポートフォリオ分散
            
            result = minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000}
            )
            
            if not result.success:
                logger.warning(f"Min variance optimization failed: {result.message}")
                raise ValueError(_('Optimization failed'))
            
            optimal_weights = result.x
            
            # 最適解のメトリクス計算
            optimal_metrics = self.calculate_portfolio_metrics(optimal_weights)
            
            # 結果をまとめる
            optimization_result = {
                'success': True,
                'optimization_type': "min_variance",
                'weights': {asset: weight for asset, weight in zip(self.mean_returns.index, optimal_weights)},
                'metrics': optimal_metrics,
                'target_return': None,
                'optimizer_success': result.success,
                'optimizer_message': result.message
            }
            
            logger.info(f"Min variance optimization successful. Risk: {optimal_metrics['risk']:.4f}")
            return optimization_result
            
        except Exception as e:
            logger.error(f"Min variance optimization failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'optimization_type': "min_variance"
            }
    
    def optimize_portfolio(self, target_return: Optional[float] = None) -> Dict[str, Any]:
        """
        ポートフォリオ最適化
        
        Args:
            target_return: 目標リターン（指定時は最小リスクポートフォリオ、未指定時は最大シャープレシオ）
            
        Returns:
            Dict: 最適化結果
        """
        if self.returns is None:
            raise ValueError(_('Data not loaded. Call load_data() first.'))
        
        num_assets = len(self.mean_returns)
        
        # 初期値（等配分）
        initial_weights = np.array([1.0 / num_assets] * num_assets)
        
        # 制約条件
        constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]  # 重みの合計=1
        
        # 目標リターン制約（指定時）
        if target_return is not None:
            constraints.append({
                'type': 'eq',
                'fun': lambda x: np.sum(self.mean_returns * x) - target_return
            })
        
        # 境界条件（0 <= 重み <= 1、空売り制限）
        bounds = tuple((0, 1) for _ in range(num_assets))
        
        try:
            if target_return is None:
                # 最大シャープレシオポートフォリオ
                def objective(weights):
                    metrics = self.calculate_portfolio_metrics(weights)
                    return -metrics['sharpe_ratio']  # 最大化のため負値
                
                optimization_type = "max_sharpe"
            else:
                # 最小分散ポートフォリオ
                def objective(weights):
                    metrics = self.calculate_portfolio_metrics(weights)
                    return metrics['variance']
                
                optimization_type = "min_risk"
            
            # 最適化実行
            result = minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'disp': False, 'maxiter': 1000}
            )
            
            if not result.success:
                logger.warning(f"Optimization may not have converged: {result.message}")
            
            # 最適な重み
            optimal_weights = result.x
            
            # 最適ポートフォリオのメトリクス計算
            optimal_metrics = self.calculate_portfolio_metrics(optimal_weights)
            
            # 結果をまとめる
            optimization_result = {
                'success': True,
                'optimization_type': optimization_type,
                'weights': {asset: weight for asset, weight in zip(self.mean_returns.index, optimal_weights)},
                'metrics': optimal_metrics,
                'target_return': target_return,
                'optimizer_success': result.success,
                'optimizer_message': result.message
            }
            
            logger.info(f"Portfolio optimization completed: {optimization_type}")
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"Portfolio optimization failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def calculate_efficient_frontier(self, num_portfolios: int = 50) -> pd.DataFrame:
        """
        効率的フロンティアの計算
        
        Args:
            num_portfolios: 計算するポートフォリオ数
            
        Returns:
            pd.DataFrame: 効率的フロンティアのデータ
        """
        if self.returns is None:
            raise ValueError(_('Data not loaded. Call load_data() first.'))
        
        logger.info(f"Calculating efficient frontier with {num_portfolios} portfolios")
        
        # リターンの範囲を設定
        min_ret = self.mean_returns.min()
        max_ret = self.mean_returns.max()
        target_returns = np.linspace(min_ret, max_ret, num_portfolios)
        
        efficient_portfolios = []
        
        for target_ret in target_returns:
            try:
                result = self.optimize_portfolio(target_return=target_ret)
                
                if result['success']:
                    portfolio = {
                        'target_return': target_ret,
                        'expected_return': result['metrics']['expected_return'],
                        'risk': result['metrics']['risk'],
                        'sharpe_ratio': result['metrics']['sharpe_ratio']
                    }
                    
                    # 各資産の配分も追加
                    for asset, weight in result['weights'].items():
                        portfolio[f'weight_{asset}'] = weight
                    
                    efficient_portfolios.append(portfolio)
                    
            except Exception as e:
                logger.warning(f"Failed to optimize for target return {target_ret:.4f}: {str(e)}")
                continue
        
        if not efficient_portfolios:
            raise ValueError(_('Failed to calculate efficient frontier'))
        
        df = pd.DataFrame(efficient_portfolios)
        logger.info("Efficient frontier calculation completed successfully")
        
        return df
    
    def calculate_asset_statistics(self) -> Dict[str, Dict[str, float]]:
        """
        個別資産の統計情報計算
        
        Returns:
            Dict: 各資産の統計情報
        """
        if self.returns is None:
            raise ValueError(_('Data not loaded. Call load_data() first.'))
        
        stats = {}
        
        for asset in self.mean_returns.index:
            asset_returns = self.returns[asset]
            
            stats[asset] = {
                'expected_return': self.mean_returns[asset],
                'risk': np.sqrt(self.cov_matrix.loc[asset, asset]),
                'sharpe_ratio': (self.mean_returns[asset] - self.risk_free_rate) / np.sqrt(self.cov_matrix.loc[asset, asset]),
                'skewness': asset_returns.skew(),
                'kurtosis': asset_returns.kurtosis(),
                'min_return': asset_returns.min(),
                'max_return': asset_returns.max(),
                'var_95': asset_returns.quantile(0.05),  # 95% VaR
                'var_99': asset_returns.quantile(0.01)   # 99% VaR
            }
        
        return stats
    
    def calculate_correlation_matrix(self) -> pd.DataFrame:
        """
        相関行列の計算
        
        Returns:
            pd.DataFrame: 相関行列
        """
        if self.returns is None:
            raise ValueError(_('Data not loaded. Call load_data() first.'))
        
        return self.returns.corr()
    
    def risk_decomposition(self, weights) -> Dict[str, Any]:
        """
        リスク分解分析
        
        Args:
            weights: ポートフォリオの重み
            
        Returns:
            Dict: リスク分解の結果
        """
        if self.returns is None:
            raise ValueError(_('Data not loaded. Call load_data() first.'))
        
        # weightsをNumPy配列に変換
        weights = np.array(weights)
        
        # ポートフォリオの分散
        portfolio_variance = np.dot(weights.T, np.dot(self.cov_matrix, weights))
        
        # 各資産のマージナルリスク貢献度
        marginal_contrib = np.dot(self.cov_matrix, weights) / np.sqrt(portfolio_variance)
        
        # 各資産の実際のリスク貢献度
        risk_contrib = weights * marginal_contrib
        
        # パーセンテージでの貢献度
        risk_contrib_pct = risk_contrib / np.sum(risk_contrib)
        
        result = {
            'portfolio_risk': np.sqrt(portfolio_variance),
            'asset_contributions': {
                asset: {
                    'absolute': risk_contrib[i],
                    'percentage': risk_contrib_pct[i]
                }
                for i, asset in enumerate(self.mean_returns.index)
            }
        }
        
        return result
    
    def analyze_monte_carlo_results(self, mc_results: pd.DataFrame) -> Dict[str, Any]:
        """
        モンテカルロシミュレーション結果の詳細分析
        
        Args:
            mc_results: モンテカルロシミュレーションのDataFrame
            
        Returns:
            Dict: 詳細分析結果
        """
        analysis = {}
        
        # 基本統計量
        analysis['basic_stats'] = {
            'total_simulations': int(len(mc_results)),
            'return_stats': {
                'mean': float(mc_results['expected_return'].mean()),
                'std': float(mc_results['expected_return'].std()),
                'min': float(mc_results['expected_return'].min()),
                'max': float(mc_results['expected_return'].max()),
                'median': float(mc_results['expected_return'].median())
            },
            'risk_stats': {
                'mean': float(mc_results['risk'].mean()),
                'std': float(mc_results['risk'].std()),
                'min': float(mc_results['risk'].min()),
                'max': float(mc_results['risk'].max()),
                'median': float(mc_results['risk'].median())
            },
            'sharpe_stats': {
                'mean': float(mc_results['sharpe_ratio'].mean()),
                'std': float(mc_results['sharpe_ratio'].std()),
                'min': float(mc_results['sharpe_ratio'].min()),
                'max': float(mc_results['sharpe_ratio'].max()),
                'median': float(mc_results['sharpe_ratio'].median())
            }
        }
        
        # パーセンタイル分析
        percentiles = [5, 10, 25, 75, 90, 95]
        analysis['percentiles'] = {}
        for p in percentiles:
            analysis['percentiles'][f'p{p}'] = {
                'return': float(mc_results['expected_return'].quantile(p/100)),
                'risk': float(mc_results['risk'].quantile(p/100)),
                'sharpe': float(mc_results['sharpe_ratio'].quantile(p/100))
            }
        
        # VaR計算（95%と99%信頼水準）
        analysis['var_analysis'] = {
            'return_var_95': float(mc_results['expected_return'].quantile(0.05)),
            'return_var_99': float(mc_results['expected_return'].quantile(0.01)),
            'risk_var_95': float(mc_results['risk'].quantile(0.95)),  # リスクの場合は上側
            'risk_var_99': float(mc_results['risk'].quantile(0.99))
        }
        
        # 信頼区間
        analysis['confidence_intervals'] = {
            'return_ci_95': [
                float(mc_results['expected_return'].quantile(0.025)),
                float(mc_results['expected_return'].quantile(0.975))
            ],
            'return_ci_99': [
                float(mc_results['expected_return'].quantile(0.005)),
                float(mc_results['expected_return'].quantile(0.995))
            ],
            'risk_ci_95': [
                float(mc_results['risk'].quantile(0.025)),
                float(mc_results['risk'].quantile(0.975))
            ],
            'sharpe_ci_95': [
                float(mc_results['sharpe_ratio'].quantile(0.025)),
                float(mc_results['sharpe_ratio'].quantile(0.975))
            ]
        }
        
        # 効率性指標
        analysis['efficiency_metrics'] = {
            'portfolios_above_rf': int(len(mc_results[mc_results['expected_return'] > self.risk_free_rate])),
            'portfolios_positive_sharpe': int(len(mc_results[mc_results['sharpe_ratio'] > 0])),
            'best_sharpe_portfolio': {
                'return': float(mc_results.loc[mc_results['sharpe_ratio'].idxmax(), 'expected_return']),
                'risk': float(mc_results.loc[mc_results['sharpe_ratio'].idxmax(), 'risk']),
                'sharpe': float(mc_results['sharpe_ratio'].max())
            },
            'min_risk_portfolio': {
                'return': float(mc_results.loc[mc_results['risk'].idxmin(), 'expected_return']),
                'risk': float(mc_results['risk'].min()),
                'sharpe': float(mc_results.loc[mc_results['risk'].idxmin(), 'sharpe_ratio'])
            }
        }
        
        # リスク・リターンの散布分析
        analysis['scatter_analysis'] = {
            'risk_return_correlation': float(mc_results['expected_return'].corr(mc_results['risk'])),
            'risk_clusters': self._analyze_risk_clusters(mc_results),
            'return_distribution': self._analyze_return_distribution(mc_results)
        }
        
        return analysis
    
    def _analyze_risk_clusters(self, mc_results: pd.DataFrame) -> Dict[str, Any]:
        """リスクレベル別のクラスタ分析"""
        risk_quartiles = mc_results['risk'].quantile([0.25, 0.5, 0.75]).tolist()
        
        clusters = {
            'low_risk': mc_results[mc_results['risk'] <= risk_quartiles[0]],
            'medium_low_risk': mc_results[(mc_results['risk'] > risk_quartiles[0]) & 
                                        (mc_results['risk'] <= risk_quartiles[1])],
            'medium_high_risk': mc_results[(mc_results['risk'] > risk_quartiles[1]) & 
                                         (mc_results['risk'] <= risk_quartiles[2])],
            'high_risk': mc_results[mc_results['risk'] > risk_quartiles[2]]
        }
        
        cluster_stats = {}
        for cluster_name, cluster_data in clusters.items():
            if len(cluster_data) > 0:
                cluster_stats[cluster_name] = {
                    'count': int(len(cluster_data)),
                    'avg_return': float(cluster_data['expected_return'].mean()),
                    'avg_sharpe': float(cluster_data['sharpe_ratio'].mean()),
                    'risk_range': [float(cluster_data['risk'].min()), float(cluster_data['risk'].max())]
                }
        
        return cluster_stats
    
    def _analyze_return_distribution(self, mc_results: pd.DataFrame) -> Dict[str, Any]:
        """リターン分布の分析"""
        from scipy import stats
        
        returns = mc_results['expected_return'].values
        
        # 正規性検定
        shapiro_stat, shapiro_p = stats.shapiro(returns[:5000])  # サンプルサイズ制限
        
        # 歪度と尖度
        skewness = stats.skew(returns)
        kurtosis = stats.kurtosis(returns)
        
        return {
            'normality_test': {
                'shapiro_statistic': float(shapiro_stat),
                'shapiro_p_value': float(shapiro_p),
                'is_normal': bool(shapiro_p > 0.05)
            },
            'distribution_shape': {
                'skewness': float(skewness),
                'kurtosis': float(kurtosis),
                'interpretation': {
                    'skew_direction': 'right' if skewness > 0 else 'left' if skewness < 0 else 'symmetric',
                    'tail_heaviness': 'heavy' if kurtosis > 0 else 'light' if kurtosis < 0 else 'normal'
                }
            }
        }
    
    def compare_simulation_counts(self, counts: List[int]) -> Dict[str, Any]:
        """
        異なるシミュレーション回数での結果比較
        
        Args:
            counts: 比較するシミュレーション回数のリスト
            
        Returns:
            Dict: 比較結果
        """
        if self.returns is None:
            raise ValueError(_('Data not loaded. Call load_data() first.'))
        
        comparison_results = {}
        
        for count in counts:
            logger.info(f"Running simulation with {count} iterations for comparison")
            mc_results = self.monte_carlo_simulation(count)
            analysis = self.analyze_monte_carlo_results(mc_results)
            
            comparison_results[str(count)] = {
                'simulation_count': count,
                'basic_stats': analysis['basic_stats'],
                'confidence_intervals': analysis['confidence_intervals'],
                'best_sharpe': analysis['efficiency_metrics']['best_sharpe_portfolio'],
                'computation_time': None  # 実際の実装では時間測定を追加
            }
        
        # 収束性分析
        comparison_results['convergence_analysis'] = self._analyze_convergence(comparison_results)
        
        return comparison_results
    
    def _analyze_convergence(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """シミュレーション回数による収束性分析"""
        convergence = {}
        
        counts = [int(k) for k in results.keys() if k.isdigit()]
        counts.sort()
        
        # 平均値の収束
        mean_returns = [results[str(c)]['basic_stats']['return_stats']['mean'] for c in counts]
        mean_risks = [results[str(c)]['basic_stats']['risk_stats']['mean'] for c in counts]
        
        convergence['mean_convergence'] = {
            'return_stability': self._calculate_stability(mean_returns),
            'risk_stability': self._calculate_stability(mean_risks),
            'recommended_min_count': self._recommend_min_simulations(counts, mean_returns, mean_risks)
        }
        
        return convergence
    
    def _calculate_stability(self, values: List[float]) -> Dict[str, float]:
        """値の安定性を計算"""
        if len(values) < 2:
            return {'coefficient_of_variation': 0, 'max_change': 0}
        
        mean_val = np.mean(values)
        std_val = np.std(values)
        cv = std_val / mean_val if mean_val != 0 else float('inf')
        
        changes = [abs(values[i] - values[i-1]) for i in range(1, len(values))]
        max_change = max(changes) if changes else 0
        
        return {
            'coefficient_of_variation': cv,
            'max_change': max_change
        }
    
    def _recommend_min_simulations(self, counts: List[int], returns: List[float], risks: List[float]) -> int:
        """最小推奨シミュレーション回数を計算"""
        threshold = 0.001  # 1%以下の変動を安定とみなす
        
        for i in range(1, len(counts)):
            return_change = abs(returns[i] - returns[i-1]) / abs(returns[i-1]) if returns[i-1] != 0 else 0
            risk_change = abs(risks[i] - risks[i-1]) / abs(risks[i-1]) if risks[i-1] != 0 else 0
            
            if return_change < threshold and risk_change < threshold:
                return counts[i]
        
        return counts[-1] if counts else 1000