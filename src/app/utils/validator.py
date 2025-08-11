import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

class InputValidator:
    """入力データの検証クラス"""
    
    # ティッカーシンボルの正規表現パターン
    TICKER_PATTERN = re.compile(r'^[A-Z0-9]{1,8}(\.[A-Z]{1,3})?$')
    
    def __init__(self, config):
        self.config = config
    
    def validate_tickers(self, tickers: List[str]) -> Dict[str, Any]:
        """
        ティッカーシンボルの検証
        
        Args:
            tickers: ティッカーシンボルのリスト
            
        Returns:
            Dict: 検証結果
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 数量チェック
        if len(tickers) < self.config.MIN_ASSETS:
            result['valid'] = False
            result['errors'].append(f'最低{self.config.MIN_ASSETS}銘柄が必要です')
            
        if len(tickers) > self.config.MAX_ASSETS:
            result['valid'] = False
            result['errors'].append(f'最大{self.config.MAX_ASSETS}銘柄まで入力可能です')
        
        # 重複チェック
        unique_tickers = set(ticker.upper() for ticker in tickers)
        if len(unique_tickers) != len(tickers):
            result['valid'] = False
            result['errors'].append('重複するティッカーシンボルがあります')
        
        # 形式チェック
        invalid_tickers = []
        for ticker in tickers:
            if not self.TICKER_PATTERN.match(ticker.upper()):
                invalid_tickers.append(ticker)
        
        if invalid_tickers:
            result['valid'] = False
            result['errors'].append(f'無効な形式のティッカーシンボル: {", ".join(invalid_tickers)}')
        
        return result
    
    def validate_date_range(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        日付範囲の検証
        
        Args:
            start_date: 開始日 (YYYY-MM-DD形式)
            end_date: 終了日 (YYYY-MM-DD形式)
            
        Returns:
            Dict: 検証結果
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            # 開始日 < 終了日チェック
            if start >= end:
                result['valid'] = False
                result['errors'].append('開始日は終了日より前の日付を指定してください')
                return result
            
            # 期間の長さチェック
            period_years = (end - start).days / 365.25
            if period_years < self.config.MIN_ANALYSIS_YEARS:
                result['valid'] = False
                result['errors'].append(f'分析期間は最低{self.config.MIN_ANALYSIS_YEARS}年必要です')
            
            if period_years > self.config.MAX_ANALYSIS_YEARS:
                result['valid'] = False
                result['errors'].append(f'分析期間は最大{self.config.MAX_ANALYSIS_YEARS}年まで可能です')
            
            # 未来日付チェック
            today = datetime.now()
            if end > today:
                result['valid'] = False
                result['errors'].append('終了日に未来の日付は指定できません')
            
            # データ取得可能期間チェック（過去20年程度を想定）
            min_start_date = today - timedelta(days=20*365)
            if start < min_start_date:
                result['warnings'].append('開始日が古すぎる可能性があります。データが取得できない場合があります')
                
        except ValueError as e:
            result['valid'] = False
            result['errors'].append('日付形式が正しくありません (YYYY-MM-DD形式で入力してください)')
        
        return result
    
    def validate_target_return(self, target_return: float) -> Dict[str, Any]:
        """
        目標リターンの検証
        
        Args:
            target_return: 目標リターン (年率、小数点形式: 0.1 = 10%)
            
        Returns:
            Dict: 検証結果
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 範囲チェック (-50% ~ +100%)
        if target_return < -0.5:
            result['valid'] = False
            result['errors'].append('目標リターンは-50%以上を指定してください')
            
        if target_return > 1.0:
            result['valid'] = False
            result['errors'].append('目標リターンは100%以下を指定してください')
        
        # 警告レベルのチェック
        if target_return > 0.3:  # 30%超
            result['warnings'].append('目標リターンが非常に高く設定されています')
            
        if target_return < -0.2:  # -20%未満
            result['warnings'].append('目標リターンが非常に低く設定されています')
        
        return result
    
    def validate_risk_free_rate(self, risk_free_rate: float) -> Dict[str, Any]:
        """
        無リスク金利の検証
        
        Args:
            risk_free_rate: 無リスク金利 (年率、小数点形式: 0.01 = 1%)
            
        Returns:
            Dict: 検証結果
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 範囲チェック (0% ~ 10%)
        if risk_free_rate < 0:
            result['valid'] = False
            result['errors'].append('無リスク金利は0%以上を指定してください')
            
        if risk_free_rate > 0.1:
            result['valid'] = False
            result['errors'].append('無リスク金利は10%以下を指定してください')
        
        return result
    
    def validate_simulation_count(self, simulation_count: int) -> Dict[str, Any]:
        """
        シミュレーション回数の検証
        
        Args:
            simulation_count: シミュレーション回数
            
        Returns:
            Dict: 検証結果
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 範囲チェック
        if simulation_count < self.config.MIN_SIMULATION_COUNT:
            result['valid'] = False
            result['errors'].append(f'シミュレーション回数は最低{self.config.MIN_SIMULATION_COUNT:,}回必要です')
            
        if simulation_count > self.config.MAX_SIMULATION_COUNT:
            result['valid'] = False
            result['errors'].append(f'シミュレーション回数は最大{self.config.MAX_SIMULATION_COUNT:,}回まで可能です')
        
        # パフォーマンス警告
        if simulation_count > 30000:
            result['warnings'].append('シミュレーション回数が多いため、計算に時間がかかる可能性があります')
        
        return result
    
    def validate_all_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        全入力項目の総合検証
        
        Args:
            inputs: 入力データの辞書
                - tickers: List[str]
                - start_date: str
                - end_date: str  
                - target_return: float (optional)
                - risk_free_rate: float (optional)
                - simulation_count: int (optional)
                
        Returns:
            Dict: 総合検証結果
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'field_results': {}
        }
        
        # 必須項目のチェック
        required_fields = ['tickers', 'start_date', 'end_date']
        for field in required_fields:
            if field not in inputs or not inputs[field]:
                result['valid'] = False
                result['errors'].append(f'{field} は必須項目です')
        
        if not result['valid']:
            return result
        
        # 各項目の個別検証
        validations = [
            ('tickers', self.validate_tickers(inputs['tickers'])),
            ('date_range', self.validate_date_range(inputs['start_date'], inputs['end_date']))
        ]
        
        # オプション項目の検証
        if 'target_return' in inputs and inputs['target_return'] is not None:
            validations.append(('target_return', self.validate_target_return(inputs['target_return'])))
        
        if 'risk_free_rate' in inputs and inputs['risk_free_rate'] is not None:
            validations.append(('risk_free_rate', self.validate_risk_free_rate(inputs['risk_free_rate'])))
        
        if 'simulation_count' in inputs and inputs['simulation_count'] is not None:
            validations.append(('simulation_count', self.validate_simulation_count(inputs['simulation_count'])))
        
        # 結果の集約
        for field_name, validation_result in validations:
            result['field_results'][field_name] = validation_result
            
            if not validation_result['valid']:
                result['valid'] = False
                result['errors'].extend(validation_result['errors'])
            
            result['warnings'].extend(validation_result['warnings'])
        
        return result