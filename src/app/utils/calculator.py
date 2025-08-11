import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm
from typing import List, Dict, Any, Optional, Tuple
import logging

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
            raise ValueError("Data not loaded. Call load_data() first.")
        
        num_assets = len(self.mean_returns)
        results = []
        
        logger.info(f"Starting Monte Carlo simulation with {num_simulations} iterations")
        
        for i in range(num_simulations):
            # ランダムな重みを生成
            weights = np.random.random(num_assets)
            weights = weights / np.sum(weights)  # 正規化
            
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
    
    def optimize_portfolio(self, target_return: Optional[float] = None) -> Dict[str, Any]:
        """
        ポートフォリオ最適化
        
        Args:
            target_return: 目標リターン（指定時は最小リスクポートフォリオ、未指定時は最大シャープレシオ）
            
        Returns:
            Dict: 最適化結果
        """
        if self.returns is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
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
            raise ValueError("Data not loaded. Call load_data() first.")
        
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
            raise ValueError("Failed to calculate efficient frontier")
        
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
            raise ValueError("Data not loaded. Call load_data() first.")
        
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
            raise ValueError("Data not loaded. Call load_data() first.")
        
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
            raise ValueError("Data not loaded. Call load_data() first.")
        
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