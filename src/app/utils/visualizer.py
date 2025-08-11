import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import json

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
                colorbar=dict(title="シャープレシオ"),
                showscale=True
            ),
            name='モンテカルロシミュレーション',
            hovertemplate='<b>リスク:</b> %{x:.3f}<br>' +
                         '<b>リターン:</b> %{y:.3f}<br>' +
                         '<b>シャープレシオ:</b> %{marker.color:.3f}<extra></extra>'
        ))
        
        # 効率的フロンティア
        if efficient_frontier_data:
            ef_df = pd.DataFrame(efficient_frontier_data)
            
            fig.add_trace(go.Scatter(
                x=ef_df['risk'],
                y=ef_df['expected_return'],
                mode='lines',
                line=dict(color=self.COLORS['danger'], width=3),
                name='効率的フロンティア',
                hovertemplate='<b>リスク:</b> %{x:.3f}<br>' +
                             '<b>リターン:</b> %{y:.3f}<extra></extra>'
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
                    'max_sharpe': '最大シャープレシオ',
                    'min_variance': '最小分散',
                    'target_return': '目標リターン達成'
                }
                
                fig.add_trace(go.Scatter(
                    x=[portfolio['metrics']['risk']],
                    y=[portfolio['metrics']['expected_return']],
                    mode='markers',
                    marker=marker,
                    name=display_names.get(name, name),
                    hovertemplate=f'<b>{display_names.get(name, name)}</b><br>' +
                                 '<b>リスク:</b> %{x:.3f}<br>' +
                                 '<b>リターン:</b> %{y:.3f}<br>' +
                                 f'<b>シャープレシオ:</b> {portfolio["metrics"]["sharpe_ratio"]:.3f}<extra></extra>'
                ))
        
        # レイアウト設定
        fig.update_layout(
            title=dict(
                text='効率的フロンティア',
                font=dict(size=16, **self.font_config)
            ),
            xaxis=dict(
                title='リスク（標準偏差）'
            ),
            yaxis=dict(
                title='期待リターン'
            ),
            template='plotly_white',
            showlegend=True,
            hovermode='closest'
        )
        
        return fig.to_json()
    
    def create_asset_allocation_plot(self, weights: Dict[str, float], title: str = "資産配分") -> str:
        """
        資産配分の円グラフ作成
        
        Args:
            weights: 資産配分 {asset: weight}
            title: グラフタイトル
            
        Returns:
            str: Plotly図表のJSON文字列
        """
        # 重みが0.01未満の資産は「その他」にまとめる
        threshold = 0.01
        main_assets = {k: v for k, v in weights.items() if v >= threshold}
        other_assets = {k: v for k, v in weights.items() if v < threshold}
        
        if other_assets:
            main_assets['その他'] = sum(other_assets.values())
        
        assets = list(main_assets.keys())
        values = list(main_assets.values())
        percentages = [v * 100 for v in values]
        
        # カラーパレット生成
        colors = px.colors.qualitative.Set3[:len(assets)]
        
        fig = go.Figure(data=[go.Pie(
            labels=assets,
            values=percentages,
            hole=0.4,
            marker=dict(colors=colors),
            textinfo='label+percent',
            textfont=dict(size=10),
            hovertemplate='<b>%{label}</b><br>' +
                         '配分: %{percent}<br>' +
                         '重み: %{value:.2f}%<extra></extra>'
        )])
        
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=16, **self.font_config),
                x=0.5
            ),
            template='plotly_white',
            showlegend=True,
            legend=dict(
                font=dict(size=10)
            )
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
            colorbar=dict(title="相関係数"),
            text=text_values,
            texttemplate='%{text}',
            textfont=dict(size=12, color='white'),
            hovertemplate='<b>%{y} vs %{x}</b><br>相関係数: %{z:.3f}<extra></extra>'
        ))
        
        fig.update_layout(
            title=dict(text='資産間相関行列', font=dict(size=16)),
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
                colorbar=dict(title="シャープレシオ"),
                showscale=True
            ),
            text=assets,
            textposition='top center',
            textfont=dict(size=10),
            name='個別資産',
            hovertemplate='<b>%{text}</b><br>' +
                         'リスク: %{x:.3f}<br>' +
                         'リターン: %{y:.3f}<br>' +
                         'シャープレシオ: %{marker.color:.3f}<extra></extra>'
        ))
        
        fig.update_layout(
            title=dict(
                text='個別資産のリスク・リターン特性',
                font=dict(size=16, **self.font_config)
            ),
            xaxis=dict(
                title='リスク（標準偏差）',
            ),
            yaxis=dict(
                title='期待リターン',
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
                         'リスク貢献度: %{y:.1f}%<extra></extra>'
        ))
        
        fig.update_layout(
            title=dict(
                text='リスク貢献度分析',
                font=dict(size=16, **self.font_config)
            ),
            xaxis=dict(
                title='資産',
            ),
            yaxis=dict(
                title='リスク貢献度（%）',
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
        
        # 資産配分（最大シャープレシオポートフォリオ）
        if 'optimal_portfolios' in analysis_results and 'max_sharpe' in analysis_results['optimal_portfolios']:
            max_sharpe_weights = analysis_results['optimal_portfolios']['max_sharpe']['weights']
            charts['asset_allocation'] = self.create_asset_allocation_plot(
                max_sharpe_weights, 
                "最適ポートフォリオ資産配分（最大シャープレシオ）"
            )
        
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
        
        # リスク貢献度
        if ('optimal_portfolios' in analysis_results and 
            'max_sharpe' in analysis_results['optimal_portfolios'] and
            'risk_decomposition' in analysis_results['optimal_portfolios']['max_sharpe']):
            
            charts['risk_contribution'] = self.create_risk_contribution_plot(
                analysis_results['optimal_portfolios']['max_sharpe']['risk_decomposition']
            )
        
        return charts