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
            exchange_timezones = set()

            for i, ticker in enumerate(tickers):
                try:
                    if progress_callback:
                        progress = int((i / len(tickers)) * 70)  # Up to 70%
                        progress_callback(_('Retrieving data for %s...') % ticker, progress)

                    # Retrieve split- and dividend-adjusted prices (total return basis).
                    stock = yf.Ticker(ticker)
                    hist = stock.history(start=start_date, end=end_date, auto_adjust=True, timeout=self.timeout)

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

                    # yfinance indexes prices at local midnight in the exchange time zone.
                    # Align by calendar date so that assets from different exchanges
                    # (e.g. Tokyo and New York) share the same index.
                    if isinstance(closes.index, pd.DatetimeIndex):
                        if closes.index.tz is not None:
                            exchange_timezones.add(str(closes.index.tz))
                            closes.index = closes.index.tz_localize(None)
                        closes.index = closes.index.normalize()
                        closes = closes[~closes.index.duplicated(keep='last')]

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
            raw_price_data = pd.DataFrame(stock_data)

            if progress_callback:
                progress_callback(_('Preprocessing data...'), 90)

            # Run data quality checks on each asset's own trading days.
            quality_issues = self._check_data_quality(raw_price_data)
            result['warnings'].extend(quality_issues)

            # Exclude assets whose prices never change: their variance is zero,
            # which makes Sharpe ratios and correlations undefined. Do this before
            # aligning dates so they do not shorten the common period.
            constant_tickers = [
                ticker for ticker in raw_price_data.columns
                if raw_price_data[ticker].dropna().nunique() <= 1
            ]
            for ticker in constant_tickers:
                result['warnings'].append(_('%s: No price variation in the analysis period') % ticker)
                successful_tickers.remove(ticker)
                failed_tickers.append(ticker)
            raw_price_data = raw_price_data.drop(columns=constant_tickers)

            # Handle missing data.
            price_data = self._handle_missing_data(raw_price_data)

            if len(successful_tickers) < 2:
                result['errors'].append(_('Less than 2 assets have valid data available'))
                result['metadata']['tickers_success'] = successful_tickers
                result['metadata']['tickers_failed'] = failed_tickers
                return result

            if len(price_data) < 20:
                result['errors'].append(
                    _('Insufficient overlapping data across assets (common trading days: %d)') % len(price_data)
                )
                result['metadata']['tickers_success'] = successful_tickers
                result['metadata']['tickers_failed'] = failed_tickers
                return result

            # Warn when the common period is shorter than the available history,
            # e.g. because one asset was listed later than the others.
            earliest_start = raw_price_data.apply(lambda s: s.first_valid_index()).min()
            if price_data.index.min() - earliest_start > timedelta(days=7):
                result['warnings'].append(
                    _('Analysis period was shortened to the date range common to all assets (%(start)s to %(end)s)') % {
                        'start': price_data.index.min().strftime('%Y-%m-%d'),
                        'end': price_data.index.max().strftime('%Y-%m-%d')
                    }
                )

            if len(exchange_timezones) > 1:
                result['warnings'].append(
                    _('Assets trade on exchanges in different time zones. Daily correlations may be underestimated, and returns are measured in each asset\'s local currency.')
                )

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
            # Constant-price assets already have their own warning.
            fetch_failed_tickers = [t for t in failed_tickers if t not in constant_tickers]
            if fetch_failed_tickers:
                result['warnings'].append(_('Failed to retrieve data for the following assets: %s') % ', '.join(fetch_failed_tickers))
            
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
        # Keep only dates where every ticker has data. Filling gaps instead
        # (ffill/bfill) would create artificial zero returns on holidays and
        # before an asset's listing date, understating volatility and correlation.
        # Dropping a date folds its move into the next common day's return.
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
        
        # Run quality checks for each ticker on its own trading days.
        for ticker in data.columns:
            prices = data[ticker].dropna()
            if prices.empty:
                continue
            
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
            business_days = pd.bdate_range(start=prices.index.min(), end=prices.index.max())

            missing_ratio = 1 - (len(prices) / len(business_days))
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
