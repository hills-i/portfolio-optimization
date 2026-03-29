import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging
from flask_babel import gettext as _

logger = logging.getLogger(__name__)

class DataFetcher:
    """Fetcher for financial market data."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    def fetch_stock_data(self, 
                        tickers: List[str], 
                        start_date: str, 
                        end_date: str,
                        progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Fetch stock price data.
        
        Args:
            tickers: List of ticker symbols.
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.
            progress_callback: Optional progress callback function.
            
        Returns:
            Dict: Retrieval result.
                - success: bool
                - data: pd.DataFrame (on success)
                - errors: List[str] (on failure)
                - warnings: List[str]
                - metadata: Dict (retrieval metadata)
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
            
            # Normalize ticker symbols to uppercase.
            tickers = [ticker.upper() for ticker in tickers]
            
            # Retrieve data
            stock_data = {}
            successful_tickers = []
            failed_tickers = []
            
            for i, ticker in enumerate(tickers):
                try:
                    if progress_callback:
                        progress = int((i / len(tickers)) * 70)  # Up to 70%
                        progress_callback(_('Retrieving data for %s...') % ticker, progress)
                    
                    # Retrieve data with yfinance.
                    stock = yf.Ticker(ticker)
                    hist = stock.history(start=start_date, end=end_date, timeout=self.timeout)
                    
                    if hist.empty:
                        failed_tickers.append(ticker)
                        logger.warning(f"No data found for ticker: {ticker}")
                        continue
                    
                    # Keep only closing prices.
                    closes = hist['Close']
                    closes = closes.dropna()
                    
                    if len(closes) < 20:  # At least 20 days of data are required.
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
            
            # Stop if too few tickers were fetched successfully.
            if len(successful_tickers) < 2:
                result['errors'].append(_('Less than 2 assets have valid data available'))
                result['metadata']['tickers_success'] = successful_tickers
                result['metadata']['tickers_failed'] = failed_tickers
                return result
            
            # Build the DataFrame.
            price_data = pd.DataFrame(stock_data)
            
            # Handle missing data.
            price_data = self._handle_missing_data(price_data)
            
            if progress_callback:
                progress_callback(_('Preprocessing data...'), 90)
            
            # Run data quality checks.
            quality_issues = self._check_data_quality(price_data)
            result['warnings'].extend(quality_issues)
            
            # Populate the success result.
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
            
            # Add warnings for failed tickers.
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
        Handle missing data.
        
        Args:
            data: Price data DataFrame.
            
        Returns:
            pd.DataFrame: Processed DataFrame.
        """
        # Forward fill.
        data = data.ffill()
        
        # Backward fill for cases where the first value is missing.
        data = data.bfill()
        
        # Keep only dates where every ticker has data.
        data = data.dropna(axis=0, how='any')
        
        return data
    
    def _check_data_quality(self, data: pd.DataFrame) -> List[str]:
        """
        Check data quality.
        
        Args:
            data: Price data DataFrame.
            
        Returns:
            List[str]: Warning messages related to data quality.
        """
        warnings = []
        
        # Run quality checks for each ticker.
        for ticker in data.columns:
            prices = data[ticker]
            
            # Check for extreme price movements.
            returns = prices.pct_change().dropna()
            extreme_returns = returns[abs(returns) > 0.5]  # Price moves above 50%
            
            if len(extreme_returns) > 0:
                warnings.append(_('%s: Extreme price movements detected (%d days)') % (ticker, len(extreme_returns)))
            
            # Check for zero prices.
            zero_prices = (prices <= 0).sum()
            if zero_prices > 0:
                warnings.append(_('%s: Zero or negative prices detected (%d days)') % (ticker, zero_prices))
            
            # Check data continuity.
            business_days = pd.bdate_range(start=data.index.min(), end=data.index.max())
            
            missing_ratio = 1 - (len(data) / len(business_days))
            if missing_ratio > 0.1:  # More than 10% missing business days
                warnings.append(_('%s: High data missing ratio detected (missing: %s)') % (ticker, f'{missing_ratio:.1%}'))
        
        return warnings
    
    def get_ticker_info(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch basic information for a ticker.
        
        Args:
            ticker: Ticker symbol.
            
        Returns:
            Dict: Ticker information.
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
        Check whether ticker symbols exist.
        
        Args:
            tickers: List of ticker symbols.
            
        Returns:
            Dict: Mapping of {ticker: is_valid}.
        """
        result = {}
        
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker.upper())
                # Try fetching one week of recent data.
                test_data = stock.history(period="1wk", timeout=10)
                result[ticker] = not test_data.empty
            except Exception:
                result[ticker] = False
        
        return result
