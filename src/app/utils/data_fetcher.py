import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging
from flask_babel import gettext as _

logger = logging.getLogger(__name__)

class DataFetcher:
    """金融データ取得クラス"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    def fetch_stock_data(self, 
                        tickers: List[str], 
                        start_date: str, 
                        end_date: str,
                        progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        株価データの取得
        
        Args:
            tickers: ティッカーシンボルのリスト
            start_date: 開始日 (YYYY-MM-DD形式)
            end_date: 終了日 (YYYY-MM-DD形式)
            progress_callback: 進捗コールバック関数
            
        Returns:
            Dict: 取得結果
                - success: bool
                - data: pd.DataFrame (成功時)
                - errors: List[str] (失敗時)
                - warnings: List[str]
                - metadata: Dict (取得情報)
        """
        result = {
            'success': False,
            'data': None,
            'errors': [],
            'warnings': [],
            'metadata': {
                'tickers_requested': tickers.copy(),
                'tickers_success': [],
                'tickers_failed': [],
                'start_date': start_date,
                'end_date': end_date,
                'total_records': 0
            }
        }
        
        try:
            if progress_callback:
                progress_callback(_('Starting data retrieval...'), 0)
            
            # ティッカーシンボルを大文字に統一
            tickers = [ticker.upper() for ticker in tickers]
            
            # データ取得
            stock_data = {}
            successful_tickers = []
            failed_tickers = []
            
            for i, ticker in enumerate(tickers):
                try:
                    if progress_callback:
                        progress = int((i / len(tickers)) * 70)  # 70%まで
                        progress_callback(_('Retrieving data for %s...') % ticker, progress)
                    
                    # yfinanceでデータ取得
                    stock = yf.Ticker(ticker)
                    hist = stock.history(start=start_date, end=end_date, timeout=self.timeout)
                    
                    if hist.empty:
                        failed_tickers.append(ticker)
                        logger.warning(f"No data found for ticker: {ticker}")
                        continue
                    
                    # 終値データのみ抽出
                    closes = hist['Close']
                    closes = closes.dropna()
                    
                    if len(closes) < 20:  # 最低20日分のデータが必要
                        failed_tickers.append(ticker)
                        result['warnings'].append(_('%s: Insufficient data (days retrieved: %d)') % (ticker, len(closes)))
                        continue
                    
                    stock_data[ticker] = closes
                    successful_tickers.append(ticker)
                    
                except Exception as e:
                    failed_tickers.append(ticker)
                    logger.error(f"Error fetching data for {ticker}: {str(e)}")
                    continue
            
            if progress_callback:
                progress_callback(_('Consolidating data...'), 75)
            
            # 成功したティッカーが少なすぎる場合
            if len(successful_tickers) < 2:
                result['errors'].append(_('Less than 2 assets have valid data available'))
                result['metadata']['tickers_success'] = successful_tickers
                result['metadata']['tickers_failed'] = failed_tickers
                return result
            
            # データフレームの作成
            price_data = pd.DataFrame(stock_data)
            
            # 欠損データの処理
            price_data = self._handle_missing_data(price_data)
            
            if progress_callback:
                progress_callback(_('Preprocessing data...'), 90)
            
            # データ品質チェック
            quality_issues = self._check_data_quality(price_data)
            result['warnings'].extend(quality_issues)
            
            # 成功時の結果設定
            result['success'] = True
            result['data'] = price_data
            result['metadata'].update({
                'tickers_success': successful_tickers,
                'tickers_failed': failed_tickers,
                'total_records': len(price_data),
                'date_range_actual': {
                    'start': price_data.index.min().strftime('%Y-%m-%d'),
                    'end': price_data.index.max().strftime('%Y-%m-%d')
                }
            })
            
            # 失敗したティッカーについての警告
            if failed_tickers:
                result['warnings'].append(_('Failed to retrieve data for the following assets: %s') % ', '.join(failed_tickers))
            
            if progress_callback:
                progress_callback(_('Data retrieval completed'), 100)
            
            logger.info(f"Successfully fetched data for {len(successful_tickers)} tickers")
            
        except Exception as e:
            result['errors'].append(_('Error occurred during data retrieval: %s') % str(e))
            logger.error(f"Data fetching failed: {str(e)}")
        
        return result
    
    def _handle_missing_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        欠損データの処理
        
        Args:
            data: 価格データのDataFrame
            
        Returns:
            pd.DataFrame: 処理後のDataFrame
        """
        # 前方補完
        data = data.ffill()
        
        # 後方補完（最初の値が欠損の場合）
        data = data.bfill()
        
        # 共通の日付のみ抽出（全銘柄でデータが存在する日付）
        data = data.dropna(axis=0, how='any')
        
        return data
    
    def _check_data_quality(self, data: pd.DataFrame) -> List[str]:
        """
        データ品質のチェック
        
        Args:
            data: 価格データのDataFrame
            
        Returns:
            List[str]: 品質に関する警告メッセージのリスト
        """
        warnings = []
        
        # 各銘柄について品質チェック
        for ticker in data.columns:
            prices = data[ticker]
            
            # 価格の極端な変動チェック
            returns = prices.pct_change().dropna()
            extreme_returns = returns[abs(returns) > 0.5]  # 50%以上の変動
            
            if len(extreme_returns) > 0:
                warnings.append(_('%s: Extreme price movements detected (%d days)') % (ticker, len(extreme_returns)))
            
            # ゼロ価格のチェック
            zero_prices = (prices <= 0).sum()
            if zero_prices > 0:
                warnings.append(_('%s: Zero or negative prices detected (%d days)') % (ticker, zero_prices))
            
            # データの連続性チェック
            date_gaps = pd.date_range(start=data.index.min(), end=data.index.max(), freq='D')
            business_days = pd.bdate_range(start=data.index.min(), end=data.index.max())
            
            missing_ratio = 1 - (len(data) / len(business_days))
            if missing_ratio > 0.1:  # 10%以上のデータ欠損
                warnings.append(_('%s: High data missing ratio detected (missing: %s)') % (ticker, f'{missing_ratio:.1%}'))
        
        return warnings
    
    def get_ticker_info(self, ticker: str) -> Dict[str, Any]:
        """
        ティッカーの基本情報を取得
        
        Args:
            ticker: ティッカーシンボル
            
        Returns:
            Dict: ティッカー情報
        """
        try:
            stock = yf.Ticker(ticker.upper())
            info = stock.info
            
            return {
                'success': True,
                'name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'country': info.get('country', 'Unknown'),
                'currency': info.get('currency', 'USD'),
                'market_cap': info.get('marketCap'),
                'beta': info.get('beta')
            }
        except Exception as e:
            logger.error(f"Error getting ticker info for {ticker}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_tickers(self, tickers: List[str]) -> Dict[str, bool]:
        """
        ティッカーシンボルの存在確認
        
        Args:
            tickers: ティッカーシンボルのリスト
            
        Returns:
            Dict: {ticker: is_valid} の辞書
        """
        result = {}
        
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker.upper())
                # 直近1週間のデータを試しに取得
                test_data = stock.history(period="1wk", timeout=10)
                result[ticker] = not test_data.empty
            except:
                result[ticker] = False
        
        return result