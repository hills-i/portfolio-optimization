import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm
from typing import List, Dict, Any, Optional, Tuple
import logging
from flask_babel import gettext as _

logger = logging.getLogger(__name__)

class PortfolioCalculator:
    """Portfolio calculation class."""
    
    def __init__(self):
        self.returns = None
        self.mean_returns = None
        self.cov_matrix = None
        self.risk_free_rate = 0.0

    @staticmethod
    def calculate_annual_normal_downside_metrics(annual_mean: float, annual_std: float) -> Dict[str, float]:
        """
        Calculate annual lower-tail return quantiles and positive-loss VaR.

        VaR is reported as a nonnegative annual return-rate loss, not a
        currency amount.
        """
        annual_return_p05 = annual_mean - abs(norm.ppf(0.05)) * annual_std
        annual_return_p01 = annual_mean - abs(norm.ppf(0.01)) * annual_std

        return {
            'annual_return_p05': annual_return_p05,
            'annual_return_p01': annual_return_p01,
            'var_95': max(0.0, -annual_return_p05),
            'var_99': max(0.0, -annual_return_p01)
        }
    
    def load_data(self, price_data: pd.DataFrame, risk_free_rate: float = 0.0) -> bool:
        """
        Load and preprocess price data.
        
        Args:
            price_data: DataFrame containing price data.
            risk_free_rate: Annual risk-free rate.
            
        Returns:
            bool: Whether processing succeeded.
        """
        try:
            # Calculate daily returns.
            self.returns = price_data.pct_change().dropna()
            
            # Calculate annualized expected returns (252 trading days).
            self.mean_returns = self.returns.mean() * 252
            
            # Calculate the annualized covariance matrix.
            self.cov_matrix = self.returns.cov() * 252
            
            self.risk_free_rate = risk_free_rate
            
            logger.info(f"Portfolio data loaded successfully: {len(self.returns.columns)} assets, {len(self.returns)} days")
            return True
            
        except Exception as e:
            logger.error(f"Error loading portfolio data: {str(e)}")
            return False
    
    def calculate_portfolio_metrics(self, weights: np.ndarray) -> Dict[str, float]:
        """
        Calculate basic portfolio metrics.
        
        Args:
            weights: Asset weights that sum to 1.
            
        Returns:
            Dict: Portfolio metrics.
        """
        # Expected return
        expected_return = np.sum(self.mean_returns * weights)
        
        # Risk (standard deviation)
        portfolio_variance = np.dot(weights.T, np.dot(self.cov_matrix, weights))
        portfolio_risk = np.sqrt(portfolio_variance)
        
        # Sharpe ratio
        excess_return = expected_return - self.risk_free_rate
        sharpe_ratio = excess_return / portfolio_risk if portfolio_risk > 0 else 0
        
        return {
            'expected_return': expected_return,
            'risk': portfolio_risk,
            'sharpe_ratio': sharpe_ratio,
            'variance': portfolio_variance,
            **self.calculate_annual_normal_downside_metrics(expected_return, portfolio_risk)
        }
    
    def random_portfolio_simulation(self, num_simulations: int = 10000) -> pd.DataFrame:
        """
        Generate random-weight portfolio allocation samples.

        This samples allocation weights only. It does not simulate future
        return paths or assume a future-return distribution.
        
        Args:
            num_simulations: Number of random portfolios.
            
        Returns:
            pd.DataFrame: Random portfolio sample results.
        """
        if self.returns is None:
            raise ValueError(_('Data not loaded. Call load_data() first.'))
        
        num_assets = len(self.mean_returns)
        
        logger.info(f"Starting random portfolio simulation with {num_simulations} samples")
        
        # Vectorized generation of all random weights.
        weights_matrix = np.random.random((num_simulations, num_assets))
        weights_matrix = weights_matrix / weights_matrix.sum(axis=1, keepdims=True)
        
        # Log the first five simulation weights for debugging.
        for i in range(min(5, num_simulations)):
            weight_info = {asset: f"{weights_matrix[i, j]:.3f}" for j, asset in enumerate(self.mean_returns.index)}
            logger.info(f"Random portfolio sample {i+1} weights: {weight_info}")
        
        # Vectorized portfolio metric calculation.
        mean_returns_arr = self.mean_returns.values
        cov_matrix_arr = self.cov_matrix.values
        
        expected_returns = weights_matrix @ mean_returns_arr
        portfolio_variances = np.einsum('ij,jk,ik->i', weights_matrix, cov_matrix_arr, weights_matrix)
        portfolio_risks = np.sqrt(portfolio_variances)
        sharpe_ratios = np.where(
            portfolio_risks > 0,
            (expected_returns - self.risk_free_rate) / portfolio_risks,
            0
        )
        
        # Build the DataFrame.
        df = pd.DataFrame({
            'expected_return': expected_returns,
            'risk': portfolio_risks,
            'sharpe_ratio': sharpe_ratios
        })
        
        for j, asset in enumerate(self.mean_returns.index):
            df[f'weight_{asset}'] = weights_matrix[:, j]
        
        logger.info("Random portfolio simulation completed successfully")
        
        return df

    def monte_carlo_simulation(self, num_simulations: int = 10000) -> pd.DataFrame:
        """
        Deprecated alias for random_portfolio_simulation().

        The existing behavior samples random portfolio weights; it does not
        simulate future return paths.
        """
        return self.random_portfolio_simulation(num_simulations)
    
    def monte_carlo_simulation_returns(self, num_simulations: int = 10000, time_horizon: int = 252) -> pd.DataFrame:
        """
        Run a return-based Monte Carlo simulation for future returns.
        
        Args:
            num_simulations: Number of simulations.
            time_horizon: Forecast horizon in trading days (default: 1 year = 252).
            
        Returns:
            pd.DataFrame: Simulation results.
        """
        if self.returns is None:
            raise ValueError(_('Data not loaded. Call load_data() first.'))
        
        num_assets = len(self.mean_returns)
        results = []
        
        logger.info(f"Starting return-based Monte Carlo simulation with {num_simulations} iterations")
        
        # Use a fixed optimal allocation for comparison purposes.
        optimal_result = self.optimize_portfolio()
        if optimal_result['success']:
            optimal_weights = np.array(list(optimal_result['weights'].values()))
        else:
            # Fallback to equal weights.
            optimal_weights = np.ones(num_assets) / num_assets
            
        logger.info(f"Using fixed weights for return simulation: {dict(zip(self.mean_returns.index, optimal_weights))}")
        
        for i in range(num_simulations):
            # Randomly generate future returns from a multivariate normal distribution.
            simulated_returns = np.random.multivariate_normal(
                self.mean_returns.values / 252,  # Convert to daily returns.
                self.cov_matrix.values / 252,    # Convert to daily covariance.
                time_horizon
            )
            
            # Calculate cumulative returns.
            cumulative_returns = np.prod(1 + simulated_returns, axis=0) - 1
            
            # Calculate cumulative portfolio return.
            portfolio_return = np.dot(optimal_weights, cumulative_returns)
            
            # Annualize the cumulative return.
            years = time_horizon / 252
            annualized_return = (1 + portfolio_return) ** (1 / years) - 1 if years > 0 else portfolio_return
            
            # Annualized portfolio risk.
            portfolio_variance = np.dot(optimal_weights.T, np.dot(self.cov_matrix, optimal_weights))
            portfolio_risk = np.sqrt(portfolio_variance)
            
            # Sharpe ratio on an annualized basis.
            sharpe_ratio = (annualized_return - self.risk_free_rate) / portfolio_risk if portfolio_risk > 0 else 0
            
            result = {
                'simulated_return': annualized_return,
                'risk': portfolio_risk,
                'sharpe_ratio': sharpe_ratio,
                'simulation_type': 'return_based'
            }
            
            # Log the first five results for debugging.
            if i < 5:
                logger.info(f"Return simulation {i+1}: return={portfolio_return:.4f}, risk={portfolio_risk:.4f}")
            
            results.append(result)
        
        df = pd.DataFrame(results)
        logger.info("Return-based Monte Carlo simulation completed successfully")
        
        return df
    
    def optimize_min_variance_portfolio(self) -> Dict[str, Any]:
        """
        Optimize the minimum-variance portfolio.
        
        Returns:
            Dict: Optimization result.
        """
        if self.returns is None:
            raise ValueError(_('Data not loaded. Call load_data() first.'))
        
        num_assets = len(self.mean_returns)
        
        # Initial estimate (equal weights).
        initial_weights = np.ones(num_assets) / num_assets
        
        # Constraints
        constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]  # Weights must sum to 1.
        
        # Bounds (0 <= weight <= 1, no short selling).
        bounds = tuple((0, 1) for _ in range(num_assets))
        
        try:
            # Minimize variance without a return constraint.
            def objective(weights):
                return np.dot(weights, np.dot(self.cov_matrix, weights))  # Portfolio variance
            
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
            
            # Calculate metrics for the optimal solution.
            optimal_metrics = self.calculate_portfolio_metrics(optimal_weights)
            
            # Assemble the result.
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
        Optimize the portfolio.
        
        Args:
            target_return: Target return. If provided, optimize for minimum risk; otherwise, maximize Sharpe ratio.
            
        Returns:
            Dict: Optimization result.
        """
        if self.returns is None:
            raise ValueError(_('Data not loaded. Call load_data() first.'))
        
        num_assets = len(self.mean_returns)
        optimization_type = "max_sharpe" if target_return is None else "min_risk"

        if target_return is not None:
            tolerance = 1e-8
            min_feasible_return = float(self.mean_returns.min())
            max_feasible_return = float(self.mean_returns.max())

            if (
                target_return < min_feasible_return - tolerance or
                target_return > max_feasible_return + tolerance
            ):
                nearest_feasible_return = (
                    min_feasible_return
                    if target_return < min_feasible_return
                    else max_feasible_return
                )
                target_return_gap = float(nearest_feasible_return - target_return)
                message = _(
                    'Target return is outside the feasible long-only return range'
                )
                logger.warning(
                    "%s: target=%s, feasible_range=[%s, %s]",
                    message,
                    target_return,
                    min_feasible_return,
                    max_feasible_return
                )
                return {
                    'success': False,
                    'optimization_type': optimization_type,
                    'target_return': target_return,
                    'target_return_achieved': False,
                    'target_return_gap': target_return_gap,
                    'optimizer_success': False,
                    'optimizer_message': message,
                    'feasible_return_range': {
                        'min': min_feasible_return,
                        'max': max_feasible_return
                    }
                }
        
        # Initial value (equal weights).
        initial_weights = np.array([1.0 / num_assets] * num_assets)
        
        # Constraints
        constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]  # Weights must sum to 1.
        
        # Target return constraint (when provided).
        if target_return is not None:
            constraints.append({
                'type': 'eq',
                'fun': lambda x: np.sum(self.mean_returns * x) - target_return
            })
        
        # Bounds (0 <= weight <= 1, no short selling).
        bounds = tuple((0, 1) for _ in range(num_assets))
        
        try:
            if target_return is None:
                # Maximum Sharpe ratio portfolio
                def objective(weights):
                    metrics = self.calculate_portfolio_metrics(weights)
                    return -metrics['sharpe_ratio']  # Negate for maximization.
            else:
                # Minimum-variance portfolio
                def objective(weights):
                    metrics = self.calculate_portfolio_metrics(weights)
                    return metrics['variance']
            
            # Run the optimization.
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
            
            # Optimal weights
            optimal_weights = result.x
            
            # Calculate metrics for the optimal portfolio.
            optimal_metrics = self.calculate_portfolio_metrics(optimal_weights)

            target_return_achieved = None
            target_return_gap = None
            if target_return is not None:
                target_return_gap = float(optimal_metrics['expected_return'] - target_return)
                target_return_achieved = bool(
                    result.success and abs(target_return_gap) <= 1e-4
                )
            
            # Assemble the result.
            optimization_result = {
                'success': bool(result.success),
                'optimization_type': optimization_type,
                'weights': {asset: weight for asset, weight in zip(self.mean_returns.index, optimal_weights)},
                'metrics': optimal_metrics,
                'target_return': target_return,
                'target_return_achieved': target_return_achieved,
                'target_return_gap': target_return_gap,
                'optimizer_success': result.success,
                'optimizer_message': result.message
            }
            
            if result.success:
                logger.info(f"Portfolio optimization completed: {optimization_type}")
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"Portfolio optimization failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'optimization_type': optimization_type,
                'target_return': target_return,
                'optimizer_success': False,
                'optimizer_message': str(e)
            }
    
    def calculate_efficient_frontier(self, num_portfolios: int = 50) -> pd.DataFrame:
        """
        Calculate the efficient frontier.
        
        Args:
            num_portfolios: Number of portfolios to compute.
            
        Returns:
            pd.DataFrame: Efficient frontier data.
        """
        if self.returns is None:
            raise ValueError(_('Data not loaded. Call load_data() first.'))
        
        logger.info(f"Calculating efficient frontier with {num_portfolios} portfolios")
        
        # Define the return range.
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
                    
                    # Add per-asset weights as well.
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
        Calculate statistics for each asset.
        
        Returns:
            Dict: Statistics for each asset.
        """
        if self.returns is None:
            raise ValueError(_('Data not loaded. Call load_data() first.'))
        
        stats = {}
        
        for asset in self.mean_returns.index:
            asset_returns = self.returns[asset]
            
            annual_mean = self.mean_returns[asset]
            annual_std = np.sqrt(self.cov_matrix.loc[asset, asset])
            
            stats[asset] = {
                'expected_return': annual_mean,
                'risk': annual_std,
                'sharpe_ratio': (annual_mean - self.risk_free_rate) / annual_std,
                'skewness': asset_returns.skew(),
                'kurtosis': asset_returns.kurtosis(),
                'min_return': asset_returns.min(),
                'max_return': asset_returns.max(),
                **self.calculate_annual_normal_downside_metrics(annual_mean, annual_std)
            }
        
        return stats
    
    def calculate_correlation_matrix(self) -> pd.DataFrame:
        """
        Calculate the correlation matrix.
        
        Returns:
            pd.DataFrame: Correlation matrix.
        """
        if self.returns is None:
            raise ValueError(_('Data not loaded. Call load_data() first.'))
        
        return self.returns.corr()
    
    def risk_decomposition(self, weights) -> Dict[str, Any]:
        """
        Perform risk decomposition analysis.
        
        Args:
            weights: Portfolio weights.
            
        Returns:
            Dict: Risk decomposition result.
        """
        if self.returns is None:
            raise ValueError(_('Data not loaded. Call load_data() first.'))
        
        # Convert weights to a NumPy array.
        weights = np.array(weights)
        
        # Portfolio variance
        portfolio_variance = np.dot(weights.T, np.dot(self.cov_matrix, weights))
        
        # Marginal risk contribution of each asset
        marginal_contrib = np.dot(self.cov_matrix, weights) / np.sqrt(portfolio_variance)
        
        # Actual risk contribution of each asset
        risk_contrib = weights * marginal_contrib
        
        # Contribution percentages
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
    
    @staticmethod
    def random_portfolio_metadata() -> Dict[str, Any]:
        """Metadata describing the random-weight portfolio sample semantics."""
        return {
            'simulation_type': 'random_weight_allocation',
            'uses_return_paths': False,
            'distribution_assumption': 'none_for_future_returns',
            'canonical_result_key': 'random_portfolios'
        }

    def analyze_monte_carlo_results(self, mc_results: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform detailed analysis of Monte Carlo results.
        
        Args:
            mc_results: Monte Carlo simulation DataFrame.
            
        Returns:
            Dict: Detailed analysis results.
        """
        analysis = {
            'metadata': self.random_portfolio_metadata()
        }
        
        # Basic statistics
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
        
        # Percentile analysis
        percentiles = [5, 10, 25, 75, 90, 95]
        analysis['percentiles'] = {}
        for p in percentiles:
            analysis['percentiles'][f'p{p}'] = {
                'return': float(mc_results['expected_return'].quantile(p/100)),
                'risk': float(mc_results['risk'].quantile(p/100)),
                'sharpe': float(mc_results['sharpe_ratio'].quantile(p/100))
            }
        
        # Tail percentiles for allocation-distribution outcomes.
        allocation_tail_percentiles = {
            'return_p5': float(mc_results['expected_return'].quantile(0.05)),
            'return_p1': float(mc_results['expected_return'].quantile(0.01)),
            'risk_p95': float(mc_results['risk'].quantile(0.95)),
            'risk_p99': float(mc_results['risk'].quantile(0.99))
        }
        analysis['allocation_tail_percentiles'] = allocation_tail_percentiles
        analysis['tail_percentiles'] = allocation_tail_percentiles
        
        # Allocation distribution intervals across random-weight samples.
        allocation_distribution_intervals = {
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
        analysis['allocation_distribution_intervals'] = allocation_distribution_intervals
        analysis['confidence_intervals'] = allocation_distribution_intervals
        
        # Efficiency metrics
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
        
        # Risk/return scatter analysis
        analysis['scatter_analysis'] = {
            'risk_return_correlation': float(mc_results['expected_return'].corr(mc_results['risk'])),
            'risk_clusters': self._analyze_risk_clusters(mc_results),
            'return_distribution': self._analyze_return_distribution(mc_results)
        }
        
        return analysis
    
    def _analyze_risk_clusters(self, mc_results: pd.DataFrame) -> Dict[str, Any]:
        """Analyze clusters by risk level."""
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
        """Analyze the return distribution."""
        from scipy import stats
        
        returns = mc_results['expected_return'].values
        
        # Normality test
        shapiro_stat, shapiro_p = stats.shapiro(returns[:5000])  # Sample size limit
        
        # Skewness and kurtosis
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
        Compare results across different simulation counts.
        
        Args:
            counts: List of simulation counts to compare.
            
        Returns:
            Dict: Comparison result.
        """
        if self.returns is None:
            raise ValueError(_('Data not loaded. Call load_data() first.'))
        
        comparison_results = {}
        
        for count in counts:
            logger.info(f"Running simulation with {count} iterations for comparison")
            mc_results = self.random_portfolio_simulation(count)
            analysis = self.analyze_monte_carlo_results(mc_results)
            
            comparison_results[str(count)] = {
                'simulation_count': count,
                'metadata': self.random_portfolio_metadata(),
                'basic_stats': analysis['basic_stats'],
                'allocation_distribution_intervals': analysis['allocation_distribution_intervals'],
                'confidence_intervals': analysis['confidence_intervals'],
                'best_sharpe': analysis['efficiency_metrics']['best_sharpe_portfolio'],
                'computation_time': None  # Add time measurement in a fuller implementation.
            }
        
        # Convergence analysis
        comparison_results['convergence_analysis'] = self._analyze_convergence(comparison_results)
        
        return comparison_results
    
    def _analyze_convergence(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze convergence as simulation counts increase."""
        convergence = {}
        
        counts = [int(k) for k in results.keys() if k.isdigit()]
        counts.sort()
        
        # Convergence of mean values
        mean_returns = [results[str(c)]['basic_stats']['return_stats']['mean'] for c in counts]
        mean_risks = [results[str(c)]['basic_stats']['risk_stats']['mean'] for c in counts]
        
        convergence['mean_convergence'] = {
            'return_stability': self._calculate_stability(mean_returns),
            'risk_stability': self._calculate_stability(mean_risks),
            'recommended_min_count': self._recommend_min_simulations(counts, mean_returns, mean_risks)
        }
        
        return convergence
    
    def _calculate_stability(self, values: List[float]) -> Dict[str, float]:
        """Calculate the stability of a series of values."""
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
        """Calculate the minimum recommended simulation count."""
        threshold = 0.001  # Treat changes of 1% or less as stable.
        
        for i in range(1, len(counts)):
            return_change = abs(returns[i] - returns[i-1]) / abs(returns[i-1]) if returns[i-1] != 0 else 0
            risk_change = abs(risks[i] - risks[i-1]) / abs(risks[i-1]) if risks[i-1] != 0 else 0
            
            if return_change < threshold and risk_change < threshold:
                return counts[i]
        
        return counts[-1] if counts else 1000
