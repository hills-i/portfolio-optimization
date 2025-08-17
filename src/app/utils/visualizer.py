import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import json
from flask_babel import gettext as _

class PortfolioVisualizer:
    """ポートフォリオ可視化クラス"""
    
    # カラーパレット
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
        # 日本語フォント設定
        self.font_config = dict(
            family="Arial, sans-serif"
        )
        
    def create_efficient_frontier_plot(self, 
                                     monte_carlo_data: List[Dict],
                                     efficient_frontier_data: List[Dict],
                                     optimal_portfolios: Optional[Dict] = None) -> str:
        """
        効率的フロンティアのプロット作成
        
        Args:
            monte_carlo_data: モンテカルロシミュレーション結果
            efficient_frontier_data: 効率的フロンティアデータ  
            optimal_portfolios: 最適ポートフォリオ
            
        Returns:
            str: Plotly図表のJSON文字列
        """
        fig = go.Figure()
        
        # モンテカルロシミュレーション結果の散布図
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
        
        # 効率的フロンティア
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
        
        # 最適ポートフォリオのマーカー
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
        
        # レイアウト設定
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
        資産配分の円グラフ作成
        
        Args:
            weights: 資産配分 {asset: weight}
            title: グラフタイトル
            
        Returns:
            str: Plotly図表のJSON文字列
        """
        # デバッグ用ログ
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Creating allocation plot: {title}")
        logger.info(f"Input weights: {weights}")
        
        # 重みの合計をチェック
        total_weight = sum(weights.values()) if weights else 0
        logger.info(f"Total weight: {total_weight}")
        
        if not weights or total_weight <= 0:
            logger.warning("Invalid weights provided for allocation chart")
            # 空のデータの場合のフォールバック
            weights = {_('No Data'): 1.0}
        # 重みが0.005未満（0.5%未満）の資産は「その他」にまとめる
        threshold = 0.005
        main_assets = {k: v for k, v in weights.items() if v >= threshold}
        other_assets = {k: v for k, v in weights.items() if v < threshold}
        
        # 「その他」の合計が意味のある値の場合のみ追加
        if other_assets and sum(other_assets.values()) >= 0.001:  # 0.1%以上の場合のみ
            main_assets[_('Others')] = sum(other_assets.values())
        
        assets = list(main_assets.keys())
        values = list(main_assets.values())
        percentages = [v * 100 for v in values]
        
        # カラーパレット生成
        colors = px.colors.qualitative.Set3[:len(assets)]
        
        fig = go.Figure(data=[go.Pie(
            labels=assets,
            values=percentages,
            hole=0.3,
            marker=dict(colors=colors, line=dict(color='white', width=2)),
            textinfo='label+percent',
            textfont=dict(size=11, color='white'),
            textposition='inside',
            pull=0.05,  # 少し分離して見やすく
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
        相関行列のヒートマップ作成
        
        Args:
            correlation_matrix: 相関行列データ
            
        Returns:
            str: Plotly図表のJSON文字列
        """
        # DataFrameに変換
        df = pd.DataFrame(correlation_matrix)
        
        # 必要に応じてNaNを処理
        df = df.fillna(0)
        
        # Pythonリストとして取得（NumPy配列だとJSONシリアライズで問題が発生）
        z_values = df.values.tolist()
        x_labels = list(df.columns)
        y_labels = list(df.index)
        
        # テキスト表示用の値も2次元リストで準備
        text_values = [[round(val, 3) for val in row] for row in z_values]
        
        # ヒートマップを作成
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
        個別資産のリスク・リターン散布図
        
        Args:
            asset_stats: 資産統計情報
            
        Returns:
            str: Plotly図表のJSON文字列
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
        リスク貢献度の棒グラフ作成
        
        Args:
            risk_decomposition: リスク分解結果
            
        Returns:
            str: Plotly図表のJSON文字列
        """
        assets = list(risk_decomposition['asset_contributions'].keys())
        contributions = [risk_decomposition['asset_contributions'][asset]['percentage'] * 100 
                        for asset in assets]
        
        # 降順でソート
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
        分析結果の総合ダッシュボード作成
        
        Args:
            analysis_results: 分析結果の全データ
            
        Returns:
            Dict[str, str]: 各グラフのJSON文字列
        """
        charts = {}
        
        # 効率的フロンティア
        if 'monte_carlo' in analysis_results and 'efficient_frontier' in analysis_results:
            charts['efficient_frontier'] = self.create_efficient_frontier_plot(
                analysis_results['monte_carlo']['simulations'],
                analysis_results['efficient_frontier'],
                analysis_results.get('optimal_portfolios')
            )
        
        # 資産配分（全ポートフォリオタイプ）
        if 'optimal_portfolios' in analysis_results:
            optimal_portfolios = analysis_results['optimal_portfolios']
            
            # 最大シャープレシオ
            if 'max_sharpe' in optimal_portfolios:
                charts['asset_allocation_max_sharpe'] = self.create_asset_allocation_plot(
                    optimal_portfolios['max_sharpe']['weights'], 
                    _('Optimal Portfolio Asset Allocation (Maximum Sharpe Ratio)')
                )
            
            # 最小分散
            if 'min_variance' in optimal_portfolios:
                charts['asset_allocation_min_variance'] = self.create_asset_allocation_plot(
                    optimal_portfolios['min_variance']['weights'], 
                    _('Optimal Portfolio Asset Allocation (Minimum Variance)')
                )
            
            # 目標リターン達成
            if 'target_return' in optimal_portfolios:
                charts['asset_allocation_target_return'] = self.create_asset_allocation_plot(
                    optimal_portfolios['target_return']['weights'], 
                    _('Optimal Portfolio Asset Allocation (Target Return Achievement)')
                )
            
            # 後方互換性のために従来のキーも残す
            if 'max_sharpe' in optimal_portfolios:
                charts['asset_allocation'] = charts['asset_allocation_max_sharpe']
        
        # 相関行列
        if 'correlation_matrix' in analysis_results:
            charts['correlation_matrix'] = self.create_correlation_heatmap(
                analysis_results['correlation_matrix']
            )
        
        # 個別資産のリスク・リターン
        if 'asset_statistics' in analysis_results:
            charts['risk_return_scatter'] = self.create_risk_return_scatter(
                analysis_results['asset_statistics']
            )
        
        # リスク貢献度（全ポートフォリオタイプ）
        if 'optimal_portfolios' in analysis_results:
            optimal_portfolios = analysis_results['optimal_portfolios']
            
            # 最大シャープレシオのリスク貢献度
            if ('max_sharpe' in optimal_portfolios and
                'risk_decomposition' in optimal_portfolios['max_sharpe']):
                max_sharpe_risk_chart = self.create_risk_contribution_plot(
                    optimal_portfolios['max_sharpe']['risk_decomposition']
                )
                charts['risk_contribution'] = max_sharpe_risk_chart
                charts['risk_contribution_max_sharpe'] = max_sharpe_risk_chart
            
            # 最小分散のリスク貢献度
            if ('min_variance' in optimal_portfolios and
                'risk_decomposition' in optimal_portfolios['min_variance']):
                charts['risk_contribution_min_variance'] = self.create_risk_contribution_plot(
                    optimal_portfolios['min_variance']['risk_decomposition']
                )
            
            # 目標リターンのリスク貢献度
            if ('target_return' in optimal_portfolios and
                'risk_decomposition' in optimal_portfolios['target_return']):
                charts['risk_contribution_target_return'] = self.create_risk_contribution_plot(
                    optimal_portfolios['target_return']['risk_decomposition']
                )
        
        return charts