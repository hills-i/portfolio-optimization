import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from flask_babel import gettext as _

class InputValidator:
    """Validator for input data."""
    
    # Regular expression pattern for ticker symbols.
    TICKER_PATTERN = re.compile(r'^[A-Z0-9]{1,8}(\.[A-Z]{1,3})?$')
    
    def __init__(self, config):
        self.config = config
    
    def validate_tickers(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Validate ticker symbols.
        
        Args:
            tickers: List of ticker symbols.
            
        Returns:
            Dict: Validation result.
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Count checks
        if len(tickers) < self.config.MIN_ASSETS:
            result['valid'] = False
            result['errors'].append(_('At least %d assets are required') % self.config.MIN_ASSETS)
            
        if len(tickers) > self.config.MAX_ASSETS:
            result['valid'] = False
            result['errors'].append(_('Maximum %d assets allowed') % self.config.MAX_ASSETS)
        
        # Duplicate check
        unique_tickers = set(ticker.upper() for ticker in tickers)
        if len(unique_tickers) != len(tickers):
            result['valid'] = False
            result['errors'].append(_('Duplicate ticker symbols found'))
        
        # Format check
        invalid_tickers = []
        for ticker in tickers:
            if not self.TICKER_PATTERN.match(ticker.upper()):
                invalid_tickers.append(ticker)
        
        if invalid_tickers:
            result['valid'] = False
            result['errors'].append(_('Invalid ticker symbol format: %s') % ', '.join(invalid_tickers))
        
        return result
    
    def validate_date_range(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Validate the date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.
            
        Returns:
            Dict: Validation result.
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Ensure the start date is earlier than the end date.
            if start >= end:
                result['valid'] = False
                result['errors'].append(_('Start date must be before end date'))
                return result
            
            # Check the duration length.
            period_years = (end - start).days / 365.25
            if period_years < self.config.MIN_ANALYSIS_YEARS:
                result['valid'] = False
                result['errors'].append(_('Analysis period must be at least %d year(s)') % self.config.MIN_ANALYSIS_YEARS)
            
            if period_years > self.config.MAX_ANALYSIS_YEARS:
                result['valid'] = False
                result['errors'].append(_('Analysis period cannot exceed %d years') % self.config.MAX_ANALYSIS_YEARS)
            
            # Check for future dates.
            today = datetime.now()
            if end > today:
                result['valid'] = False
                result['errors'].append(_('End date cannot be in the future'))
            
            # Check the likely data availability window (roughly the past 30 years).
            min_start_date = today - timedelta(days=31*365)
            if start < min_start_date:
                result['warnings'].append(_('Start date may be too old. Data may not be available'))
                
        except ValueError as e:
            result['valid'] = False
            result['errors'].append(_('Invalid date format (please use YYYY-MM-DD format)'))
        
        return result
    
    def validate_target_return(self, target_return: float) -> Dict[str, Any]:
        """
        Validate the target return.
        
        Args:
            target_return: Annual target return in decimal form (0.1 = 10%).
            
        Returns:
            Dict: Validation result.
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Range check (-50% to +100%)
        if target_return < -0.5:
            result['valid'] = False
            result['errors'].append(_('Target return must be -50% or higher'))
            
        if target_return > 1.0:
            result['valid'] = False
            result['errors'].append(_('Target return must be 100% or lower'))
        
        # Warning-level checks
        if target_return > 0.3:  # Above 30%
            result['warnings'].append(_('Target return is set very high'))
            
        if target_return < -0.2:  # Below -20%
            result['warnings'].append(_('Target return is set very low'))
        
        return result
    
    def validate_risk_free_rate(self, risk_free_rate: float) -> Dict[str, Any]:
        """
        Validate the risk-free rate.
        
        Args:
            risk_free_rate: Annual risk-free rate in decimal form (0.01 = 1%).
            
        Returns:
            Dict: Validation result.
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        min_rate = self.config.MIN_RISK_FREE_RATE
        max_rate = self.config.MAX_RISK_FREE_RATE

        if risk_free_rate < min_rate:
            result['valid'] = False
            result['errors'].append(_('Risk-free rate must be %(min_rate)s%% or higher') % {
                'min_rate': f'{min_rate * 100:g}'
            })
            
        if risk_free_rate > max_rate:
            result['valid'] = False
            result['errors'].append(_('Risk-free rate must be %(max_rate)s%% or lower') % {
                'max_rate': f'{max_rate * 100:g}'
            })

        if result['valid'] and risk_free_rate < 0.0:
            result['warnings'].append(_('Risk-free rate is negative'))

        if result['valid'] and risk_free_rate > 0.10:
            result['warnings'].append(_('Risk-free rate is unusually high'))
        
        return result
    
    def validate_simulation_count(self, simulation_count: int) -> Dict[str, Any]:
        """
        Validate the simulation count.
        
        Args:
            simulation_count: Number of simulations.
            
        Returns:
            Dict: Validation result.
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Range check
        if simulation_count < self.config.MIN_SIMULATION_COUNT:
            result['valid'] = False
            result['errors'].append(_('Simulation count must be at least %s') % f'{self.config.MIN_SIMULATION_COUNT:,}')
            
        if simulation_count > self.config.MAX_SIMULATION_COUNT:
            result['valid'] = False
            result['errors'].append(_('Simulation count cannot exceed %s') % f'{self.config.MAX_SIMULATION_COUNT:,}')
        
        # Performance warning
        if simulation_count > 30000:
            result['warnings'].append(_('High simulation count may result in longer calculation time'))
        
        return result
    
    def validate_all_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run validation across all input fields.
        
        Args:
            inputs: Dictionary containing input data.
                - tickers: List[str]
                - start_date: str
                - end_date: str  
                - target_return: float (optional)
                - risk_free_rate: float (optional)
                - simulation_count: int (optional)
                
        Returns:
            Dict: Combined validation result.
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'field_results': {}
        }
        
        # Required field checks
        required_fields = ['tickers', 'start_date', 'end_date']
        for field in required_fields:
            if field not in inputs or not inputs[field]:
                result['valid'] = False
                result['errors'].append(_('%s is required') % field)
        
        if not result['valid']:
            return result
        
        # Per-field validation
        validations = [
            ('tickers', self.validate_tickers(inputs['tickers'])),
            ('date_range', self.validate_date_range(inputs['start_date'], inputs['end_date']))
        ]
        
        # Optional field validation
        if 'target_return' in inputs and inputs['target_return'] is not None:
            validations.append(('target_return', self.validate_target_return(inputs['target_return'])))
        
        if 'risk_free_rate' in inputs and inputs['risk_free_rate'] is not None:
            validations.append(('risk_free_rate', self.validate_risk_free_rate(inputs['risk_free_rate'])))
        
        if 'simulation_count' in inputs and inputs['simulation_count'] is not None:
            validations.append(('simulation_count', self.validate_simulation_count(inputs['simulation_count'])))
        
        # Aggregate the results
        for field_name, validation_result in validations:
            result['field_results'][field_name] = validation_result
            
            if not validation_result['valid']:
                result['valid'] = False
                result['errors'].extend(validation_result['errors'])
            
            result['warnings'].extend(validation_result['warnings'])
        
        return result
