import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, List, Any, Optional
from flask_babel import gettext as _

class PortfolioVisualizer:
    """Portfolio visualization class."""
    
    # Color palette
    COLORS = {
        'primary': '#1f77b4',
        'secondary': '#ff7f0e', 
        'success': '#2ca02c',
        'danger': '#d62728',
        'warning': '#ff9800',
        'info': '#17a2b8',
        'dark': '#343a40'
    }
    
    def __init__(self):
        # Font configuration
        self.font_config = dict(
            family="Arial, sans-serif"
        )
        
    def create_efficient_frontier_plot(self, 
                                     monte_carlo_data: List[Dict],
                                     efficient_frontier_data: List[Dict],
                                     optimal_portfolios: Optional[Dict] = None) -> str:
        """
        Create an efficient frontier plot.
        
        Args:
            monte_carlo_data: Monte Carlo simulation results.
            efficient_frontier_data: Efficient frontier data.
            optimal_portfolios: Optimal portfolios.
            
        Returns:
            str: Plotly chart JSON string.
        """
        fig = go.Figure()
        
        # Scatter plot for Monte Carlo simulation results.
        mc_df = pd.DataFrame(monte_carlo_data)
        
        fig.add_trace(go.Scatter(
            x=mc_df['risk'],
            y=mc_df['expected_return'],
            mode='markers',
            marker=dict(
                size=4,
                color=mc_df['sharpe_ratio'],
                colorscale='Viridis',
                opacity=0.6,
                colorbar=dict(title=_('Sharpe Ratio')),
                showscale=True
            ),
            name=_('Monte Carlo Simulation'),
            hovertemplate='<b>' + _('Risk') + ':</b> %{x:.3f}<br>' +
                         '<b>' + _('Return') + ':</b> %{y:.3f}<br>' +
                         '<b>' + _('Sharpe Ratio') + ':</b> %{marker.color:.3f}<extra></extra>'
        ))
        
        # Efficient frontier
        if efficient_frontier_data:
            ef_df = pd.DataFrame(efficient_frontier_data)
            
            fig.add_trace(go.Scatter(
                x=ef_df['risk'],
                y=ef_df['expected_return'],
                mode='lines',
                line=dict(color=self.COLORS['danger'], width=3),
                name=_('Efficient Frontier'),
                hovertemplate='<b>' + _('Risk') + ':</b> %{x:.3f}<br>' +
                             '<b>' + _('Return') + ':</b> %{y:.3f}<extra></extra>'
            ))
        
        # Markers for optimal portfolios
        if optimal_portfolios:
            for name, portfolio in optimal_portfolios.items():
                marker_config = {
                    'max_sharpe': dict(symbol='star', color=self.COLORS['warning'], size=15),
                    'min_variance': dict(symbol='diamond', color=self.COLORS['success'], size=12),
                    'target_return': dict(symbol='circle', color=self.COLORS['info'], size=12)
                }
                
                marker = marker_config.get(name, dict(symbol='circle', color=self.COLORS['primary'], size=10))
                
                display_names = {
                    'max_sharpe': _('Maximum Sharpe Ratio'),
                    'min_variance': _('Minimum Variance'),
                    'target_return': _('Target Return Achievement')
                }
                
                fig.add_trace(go.Scatter(
                    x=[portfolio['metrics']['risk']],
                    y=[portfolio['metrics']['expected_return']],
                    mode='markers',
                    marker=marker,
                    name=display_names.get(name, name),
                    hovertemplate=f'<b>{display_names.get(name, name)}</b><br>' +
                                 '<b>' + _('Risk') + ':</b> %{x:.3f}<br>' +
                                 '<b>' + _('Return') + ':</b> %{y:.3f}<br>' +
                                 f'<b>' + _('Sharpe Ratio') + ':</b> {portfolio["metrics"]["sharpe_ratio"]:.3f}<extra></extra>'
                ))
        
        # Layout configuration
        fig.update_layout(
            title=dict(
                text=_('Efficient Frontier'),
                font=dict(size=16, **self.font_config)
            ),
            xaxis=dict(
                title=_('Risk (Standard Deviation)')
            ),
            yaxis=dict(
                title=_('Expected Return')
            ),
            template='plotly_white',
            showlegend=True,
            hovermode='closest'
        )
        
        return fig.to_json()
    
    def create_asset_allocation_plot(self, weights: Dict[str, float], title: str = None) -> str:
        """
        Create a pie chart for asset allocation.
        
        Args:
            weights: Asset allocation as {asset: weight}.
            title: Chart title.
            
        Returns:
            str: Plotly chart JSON string.
        """
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Creating allocation plot: {title}")
        logger.info(f"Input weights: {weights}")
        
        # Check the total weight.
        total_weight = sum(weights.values()) if weights else 0
        logger.info(f"Total weight: {total_weight}")
        
        if not weights or total_weight <= 0:
            logger.warning("Invalid weights provided for allocation chart")
            # Fallback for empty data.
            weights = {_('No Data'): 1.0}
        # Group assets below 0.005 (0.5%) into "Others".
        threshold = 0.005
        main_assets = {k: v for k, v in weights.items() if v >= threshold}
        other_assets = {k: v for k, v in weights.items() if v < threshold}
        
        # Only add "Others" when the combined value is meaningful.
        if other_assets and sum(other_assets.values()) >= 0.001:  # Only when 0.1% or more
            main_assets[_('Others')] = sum(other_assets.values())
        
        assets = list(main_assets.keys())
        values = list(main_assets.values())
        percentages = [v * 100 for v in values]
        
        # Generate the color palette.
        colors = px.colors.qualitative.Set3[:len(assets)]
        
        fig = go.Figure(data=[go.Pie(
            labels=assets,
            values=percentages,
            hole=0.3,
            marker=dict(colors=colors, line=dict(color='white', width=2)),
            textinfo='label+percent',
            textfont=dict(size=11, color='white'),
            textposition='inside',
            pull=0.05,  # Separate slightly for readability.
            hovertemplate='<b>%{label}</b><br>' +
                         _('Allocation') + ': %{percent}<br>' +
                         _('Weight') + ': %{value:.2f}%<extra></extra>'
        )])
        
        # Set default title if none provided
        if title is None:
            title = _('Asset Allocation')
            
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=16, **self.font_config),
                x=0.5,
                y=0.95
            ),
            template='plotly_white',
            showlegend=True,
            legend=dict(
                font=dict(size=11),
                orientation="v",
                x=1.02,
                y=0.5
            ),
            margin=dict(l=20, r=100, t=60, b=20),
            width=400,
            height=380,
            autosize=False
        )
        
        return fig.to_json()
    
    def create_correlation_heatmap(self, correlation_matrix: Dict[str, Dict[str, float]]) -> str:
        """
        Create a heatmap for the correlation matrix.
        
        Args:
            correlation_matrix: Correlation matrix data.
            
        Returns:
            str: Plotly chart JSON string.
        """
        # Convert to a DataFrame.
        df = pd.DataFrame(correlation_matrix)
        
        # Handle NaN values if needed.
        df = df.fillna(0)
        
        # Convert to Python lists to avoid JSON serialization issues with NumPy arrays.
        z_values = df.values.tolist()
        x_labels = list(df.columns)
        y_labels = list(df.index)
        
        # Prepare a 2D list of values for text display.
        text_values = [[round(val, 3) for val in row] for row in z_values]
        
        # Create the heatmap.
        fig = go.Figure(data=go.Heatmap(
            z=z_values,
            x=x_labels,
            y=y_labels,
            colorscale='RdBu_r',
            zmin=-1,
            zmax=1,
            showscale=True,
            colorbar=dict(title=_('Correlation Coefficient')),
            text=text_values,
            texttemplate='%{text}',
            textfont=dict(size=12, color='white'),
            hovertemplate='<b>%{y} vs %{x}</b><br>' + _('Correlation Coefficient') + ': %{z:.3f}<extra></extra>'
        ))
        
        fig.update_layout(
            title=dict(text=_('Asset Correlation Matrix'), font=dict(size=16)),
            xaxis=dict(title='', side='bottom'),
            yaxis=dict(title='', autorange='reversed'),
            width=500,
            height=400
        )
        
        return fig.to_json()
    
    def create_risk_return_scatter(self, asset_stats: Dict[str, Dict[str, float]]) -> str:
        """
        Create a risk-return scatter plot for individual assets.
        
        Args:
            asset_stats: Asset statistics.
            
        Returns:
            str: Plotly chart JSON string.
        """
        assets = []
        returns = []
        risks = []
        sharpe_ratios = []
        
        for asset, stats in asset_stats.items():
            assets.append(asset)
            returns.append(stats['expected_return'])
            risks.append(stats['risk'])
            sharpe_ratios.append(stats['sharpe_ratio'])
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=risks,
            y=returns,
            mode='markers+text',
            marker=dict(
                size=12,
                color=sharpe_ratios,
                colorscale='Viridis',
                colorbar=dict(title=_('Sharpe Ratio')),
                showscale=True
            ),
            text=assets,
            textposition='top center',
            textfont=dict(size=10),
            name=_('Individual Assets'),
            hovertemplate='<b>%{text}</b><br>' +
                         _('Risk') + ': %{x:.3f}<br>' +
                         _('Return') + ': %{y:.3f}<br>' +
                         _('Sharpe Ratio') + ': %{marker.color:.3f}<extra></extra>'
        ))
        
        fig.update_layout(
            title=dict(
                text=_('Risk-Return Characteristics of Individual Assets'),
                font=dict(size=16, **self.font_config)
            ),
            xaxis=dict(
                title=_('Risk (Standard Deviation)'),
            ),
            yaxis=dict(
                title=_('Expected Return'),
            ),
            template='plotly_white',
            showlegend=False
        )
        
        return fig.to_json()
    
    def create_risk_contribution_plot(self, risk_decomposition: Dict[str, Any]) -> str:
        """
        Create a bar chart for risk contribution.
        
        Args:
            risk_decomposition: Risk decomposition result.
            
        Returns:
            str: Plotly chart JSON string.
        """
        assets = list(risk_decomposition['asset_contributions'].keys())
        contributions = [risk_decomposition['asset_contributions'][asset]['percentage'] * 100 
                        for asset in assets]
        
        # Sort in descending order.
        sorted_data = sorted(zip(assets, contributions), key=lambda x: x[1], reverse=True)
        assets_sorted = [x[0] for x in sorted_data]
        contributions_sorted = [x[1] for x in sorted_data]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=assets_sorted,
            y=contributions_sorted,
            marker=dict(color=self.COLORS['primary']),
            text=[f'{c:.1f}%' for c in contributions_sorted],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>' +
                         _('Risk Contribution') + ': %{y:.1f}%<extra></extra>'
        ))
        
        fig.update_layout(
            title=dict(
                text=_('Risk Contribution Analysis'),
                font=dict(size=16, **self.font_config)
            ),
            xaxis=dict(
                title=_('Assets'),
            ),
            yaxis=dict(
                title=_('Risk Contribution (%)'),
            ),
            template='plotly_white',
            showlegend=False
        )
        
        return fig.to_json()
    
    def create_summary_dashboard(self, analysis_results: Dict[str, Any]) -> Dict[str, str]:
        """
        Create a summary dashboard for analysis results.

        Args:
            analysis_results: Full analysis result data.

        Returns:
            Dict[str, str]: JSON strings for each chart.
        """
        charts = {}
        
        # Efficient frontier (Monte Carlo based)
        if 'monte_carlo' in analysis_results and 'efficient_frontier' in analysis_results:
            charts['efficient_frontier'] = self.create_efficient_frontier_plot(
                analysis_results['monte_carlo']['simulations'],
                analysis_results['efficient_frontier'],
                analysis_results.get('optimal_portfolios')
            )

        # Efficient frontier from mathematical optimization
        if ('efficient_frontier' in analysis_results and
            'asset_statistics' in analysis_results):
            charts['mathematical_efficient_frontier'] = self.create_working_efficient_frontier_plot(
                analysis_results['efficient_frontier'],
                analysis_results['asset_statistics'],
                analysis_results.get('optimal_portfolios')
            )
        
        # Asset allocation (all portfolio types)
        if 'optimal_portfolios' in analysis_results:
            optimal_portfolios = analysis_results['optimal_portfolios']
            
            # Maximum Sharpe ratio
            if 'max_sharpe' in optimal_portfolios:
                charts['asset_allocation_max_sharpe'] = self.create_asset_allocation_plot(
                    optimal_portfolios['max_sharpe']['weights'], 
                    _('Optimal Portfolio Asset Allocation (Maximum Sharpe Ratio)')
                )
            
            # Minimum variance
            if 'min_variance' in optimal_portfolios:
                charts['asset_allocation_min_variance'] = self.create_asset_allocation_plot(
                    optimal_portfolios['min_variance']['weights'], 
                    _('Optimal Portfolio Asset Allocation (Minimum Variance)')
                )
            
            # Target return achievement
            if 'target_return' in optimal_portfolios:
                charts['asset_allocation_target_return'] = self.create_asset_allocation_plot(
                    optimal_portfolios['target_return']['weights'], 
                    _('Optimal Portfolio Asset Allocation (Target Return Achievement)')
                )
            
            # Keep the legacy key for backward compatibility.
            if 'max_sharpe' in optimal_portfolios:
                charts['asset_allocation'] = charts['asset_allocation_max_sharpe']
        
        # Correlation matrix
        if 'correlation_matrix' in analysis_results:
            charts['correlation_matrix'] = self.create_correlation_heatmap(
                analysis_results['correlation_matrix']
            )
        
        # Risk-return chart for individual assets
        if 'asset_statistics' in analysis_results:
            charts['risk_return_scatter'] = self.create_risk_return_scatter(
                analysis_results['asset_statistics']
            )
        
        # Risk contribution (all portfolio types)
        if 'optimal_portfolios' in analysis_results:
            optimal_portfolios = analysis_results['optimal_portfolios']
            
            # Risk contribution for maximum Sharpe ratio
            if ('max_sharpe' in optimal_portfolios and
                'risk_decomposition' in optimal_portfolios['max_sharpe']):
                charts['risk_contribution_max_sharpe'] = self.create_risk_contribution_plot(
                    optimal_portfolios['max_sharpe']['risk_decomposition']
                )
                # For backward compatibility
                charts['risk_contribution'] = charts['risk_contribution_max_sharpe']
            
            # Risk contribution for minimum variance
            if ('min_variance' in optimal_portfolios and
                'risk_decomposition' in optimal_portfolios['min_variance']):
                charts['risk_contribution_min_variance'] = self.create_risk_contribution_plot(
                    optimal_portfolios['min_variance']['risk_decomposition']
                )
            
            # Risk contribution for target return
            if ('target_return' in optimal_portfolios and
                'risk_decomposition' in optimal_portfolios['target_return']):
                charts['risk_contribution_target_return'] = self.create_risk_contribution_plot(
                    optimal_portfolios['target_return']['risk_decomposition']
                )
        
        return charts

    def create_working_efficient_frontier_plot(self,
                                              efficient_frontier_data: List[Dict],
                                              asset_statistics: Dict[str, Dict[str, float]],
                                              optimal_portfolios: Optional[Dict] = None) -> str:
        """
        Create an efficient frontier plot with lines and interactive detail.

        Args:
            efficient_frontier_data: Efficient frontier data.
            asset_statistics: Statistics for individual assets.
            optimal_portfolios: Optimal portfolios (optional).

        Returns:
            str: Plotly chart JSON string.
        """
        fig = go.Figure()

        # Efficient frontier with a filtered smooth line and Sharpe-ratio markers.
        if efficient_frontier_data and len(efficient_frontier_data) > 0:
            ef_df = pd.DataFrame(efficient_frontier_data)

            if 'risk' in ef_df.columns and 'expected_return' in ef_df.columns:
                # 1. Sort by risk.
                ef_df = ef_df.sort_values('risk').reset_index(drop=True)

                # 2. Keep only the portion where return increases monotonically.
                filtered_points = []
                max_return_so_far = -float('inf')

                for _idx, row in ef_df.iterrows():
                    current_return = row['expected_return']
                    if current_return > max_return_so_far:
                        max_return_so_far = current_return
                        filtered_points.append(row.to_dict())

                if len(filtered_points) >= 2:  # Need at least 2 points.
                    filtered_df = pd.DataFrame(filtered_points)

                    # 1. Efficient frontier line
                    fig.add_trace(go.Scatter(
                        x=filtered_df['risk'].tolist(),
                        y=filtered_df['expected_return'].tolist(),
                        mode='lines',
                        line=dict(color='red', width=4),
                        name=_('Efficient Frontier'),
                        hovertemplate=_('Risk') + ': %{x:.4f}<br>' + _('Return') + ': %{y:.4f}<extra></extra>'
                    ))

                    # 2. Sharpe-ratio markers with asset allocation details

                    # Build custom hover text including asset allocations.
                    hover_texts = []
                    for _idx, row in filtered_df.iterrows():
                        # Basic information
                        hover_text = f"<b>{_('Efficient Frontier Point')}</b><br>"
                        hover_text += f"{_('Risk')}: {row['risk']:.4f}<br>"
                        hover_text += f"{_('Return')}: {row['expected_return']:.4f}<br>"
                        hover_text += f"{_('Sharpe Ratio')}: {row['sharpe_ratio']:.3f}<br>"
                        hover_text += f"<br><b>{_('Asset Allocation')}:</b><br>"

                        # Add each asset allocation.
                        total_weight = 0
                        for col in filtered_df.columns:
                            if col.startswith('weight_'):
                                asset_name = col.replace('weight_', '')
                                weight = row[col]
                                if weight > 0.001:  # Show only allocations above 0.1%.
                                    hover_text += f"{asset_name}: {weight*100:.1f}%<br>"
                                    total_weight += weight

                        # Group the remaining tiny allocations into Others.
                        if total_weight < 0.999:  # When displayed weight is below 99.9%
                            hover_text += f"{_('Others')}: {(1-total_weight)*100:.1f}%<br>"

                        hover_texts.append(hover_text)

                    fig.add_trace(go.Scatter(
                        x=filtered_df['risk'].tolist(),
                        y=filtered_df['expected_return'].tolist(),
                        mode='markers',
                        marker=dict(
                            size=8,  # Slightly larger for readability.
                            color=filtered_df['sharpe_ratio'].tolist(),
                            colorscale='Viridis',
                            colorbar=dict(
                                title=_('Sharpe Ratio'),
                                x=1.15,  # Place to the right of the legend.
                                len=0.6,  # Adjust the height.
                                thickness=15  # Adjust the width.
                            ),
                            showscale=True,
                            line=dict(width=1, color='white')
                        ),
                        name=_('Frontier Points'),
                        showlegend=False,
                        text=hover_texts,
                        hovertemplate='%{text}<extra></extra>'
                    ))

        # Individual assets
        if asset_statistics:
            assets = list(asset_statistics.keys())
            asset_returns = [asset_statistics[asset]['expected_return'] for asset in assets]
            asset_risks = [asset_statistics[asset]['risk'] for asset in assets]

            fig.add_trace(go.Scatter(
                x=asset_risks,
                y=asset_returns,
                mode='markers+text',
                marker=dict(size=12, color='blue', symbol='diamond'),
                text=assets,
                textposition='top center',
                name=_('Assets')
            ))

        # Optimal portfolios (show all types)
        if optimal_portfolios:
            portfolio_configs = {
                'max_sharpe': {
                    'symbol': 'star',
                    'color': 'gold',
                    'size': 20,
                    'name': _('Maximum Sharpe Ratio')
                },
                'min_variance': {
                    'symbol': 'square',
                    'color': 'green',
                    'size': 16,
                    'name': _('Minimum Variance')
                },
                'target_return': {
                    'symbol': 'circle',
                    'color': 'purple',
                    'size': 14,
                    'name': _('Target Return Achievement')
                }
            }

            for portfolio_type, portfolio in optimal_portfolios.items():
                if portfolio_type in portfolio_configs:
                    config = portfolio_configs[portfolio_type]

                    # Build hover text for the optimal portfolio asset allocation.
                    hover_text = f"<b>{config['name']}</b><br>"
                    hover_text += f"{_('Risk')}: {portfolio['metrics']['risk']:.4f}<br>"
                    hover_text += f"{_('Return')}: {portfolio['metrics']['expected_return']:.4f}<br>"
                    hover_text += f"{_('Sharpe Ratio')}: {portfolio['metrics']['sharpe_ratio']:.3f}<br>"
                    hover_text += f"<br><b>{_('Asset Allocation')}:</b><br>"

                    # Sort asset allocations by weight before displaying them.
                    weights = portfolio['weights']
                    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)

                    total_displayed = 0
                    for asset_name, weight in sorted_weights:
                        if weight > 0.001:  # Show only allocations above 0.1%.
                            hover_text += f"{asset_name}: {weight*100:.1f}%<br>"
                            total_displayed += weight

                    # Group the remaining tiny allocations into Others.
                    if total_displayed < 0.999:  # When displayed weight is below 99.9%
                        hover_text += f"{_('Others')}: {(1-total_displayed)*100:.1f}%<br>"

                    fig.add_trace(go.Scatter(
                        x=[portfolio['metrics']['risk']],
                        y=[portfolio['metrics']['expected_return']],
                        mode='markers',
                        marker=dict(
                            symbol=config['symbol'],
                            size=config['size'],
                            color=config['color'],
                            line=dict(width=2, color='white')
                        ),
                        name=config['name'],
                        text=[hover_text],
                        hovertemplate='%{text}<extra></extra>'
                    ))

        fig.update_layout(
            title=_('Mathematical Efficient Frontier'),
            xaxis_title=_('Risk (Standard Deviation)'),
            yaxis_title=_('Expected Return'),
            template='plotly_white',
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02,  # Place the legend on the right.
                font=dict(size=12)
            ),
            margin=dict(l=60, r=200, t=60, b=60),  # Increase the right margin.
            width=1000,  # Make the chart wider.
            height=600
        )

        return fig.to_json()
