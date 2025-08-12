"""
エラーハンドリングシステム
デコレータパターンによる一元的エラー管理
"""

import functools
import traceback
import sys
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type, Union
from enum import Enum
import threading


class ErrorSeverity:
    """エラー重要度定義"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ErrorCategory:
    """エラーカテゴリ定義"""
    VALIDATION = "VALIDATION"      # バリデーションエラー
    DATA = "DATA"                  # データ関連エラー
    FILE_IO = "FILE_IO"           # ファイルI/Oエラー
    NETWORK = "NETWORK"           # ネットワークエラー
    PERMISSION = "PERMISSION"     # 権限エラー
    BUSINESS = "BUSINESS"         # ビジネスロジックエラー
    SYSTEM = "SYSTEM"             # システムエラー
    EXTERNAL = "EXTERNAL"         # 外部システムエラー
    USER = "USER"                 # ユーザーエラー


class RecoveryStrategy:
    """リカバリー戦略定義"""
    NONE = "NONE"                 # リカバリーなし
    RETRY = "RETRY"               # リトライ
    FALLBACK = "FALLBACK"         # フォールバック
    IGNORE = "IGNORE"             # 無視して続行
    ABORT = "ABORT"               # 処理中止


class ProjectManagementError(Exception):
    """プロジェクト管理システム基底例外クラス"""
    
    def __init__(self, 
                 message: str,
                 category: str = ErrorCategory.SYSTEM,
                 severity: str = ErrorSeverity.MEDIUM,
                 recovery_strategy: str = RecoveryStrategy.NONE,
                 details: Dict[str, Any] = None,
                 original_exception: Exception = None):
        """
        例外の初期化
        
        Args:
            message: エラーメッセージ
            category: エラーカテゴリ
            severity: エラー重要度
            recovery_strategy: リカバリー戦略
            details: 詳細情報
            original_exception: 元の例外
        """
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.recovery_strategy = recovery_strategy
        self.details = details or {}
        self.original_exception = original_exception
        self.timestamp = datetime.now()
        self.error_id = f"{self.timestamp.strftime('%Y%m%d_%H%M%S')}_{id(self)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'error_id': self.error_id,
            'timestamp': self.timestamp.isoformat(),
            'message': self.message,
            'category': self.category,
            'severity': self.severity,
            'recovery_strategy': self.recovery_strategy,
            'details': self.details.copy(),
            'original_exception': {
                'type': type(self.original_exception).__name__ if self.original_exception else None,
                'message': str(self.original_exception) if self.original_exception else None
            },
            'traceback': traceback.format_exc() if self.original_exception else None
        }


class ValidationError(ProjectManagementError):
    """バリデーションエラー"""
    
    def __init__(self, message: str, field: str = None, value: Any = None, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            recovery_strategy=RecoveryStrategy.NONE,
            **kwargs
        )
        if field:
            self.details['field'] = field
        if value is not None:
            self.details['value'] = str(value)


class DataError(ProjectManagementError):
    """データ関連エラー"""
    
    def __init__(self, message: str, data_type: str = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.DATA,
            severity=ErrorSeverity.MEDIUM,
            recovery_strategy=RecoveryStrategy.RETRY,
            **kwargs
        )
        if data_type:
            self.details['data_type'] = data_type


class FileIOError(ProjectManagementError):
    """ファイルI/Oエラー"""
    
    def __init__(self, message: str, file_path: str = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.FILE_IO,
            severity=ErrorSeverity.HIGH,
            recovery_strategy=RecoveryStrategy.FALLBACK,
            **kwargs
        )
        if file_path:
            self.details['file_path'] = file_path


class BusinessLogicError(ProjectManagementError):
    """ビジネスロジックエラー"""
    
    def __init__(self, message: str, entity_type: str = None, entity_id: str = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.BUSINESS,
            severity=ErrorSeverity.MEDIUM,
            recovery_strategy=RecoveryStrategy.NONE,
            **kwargs
        )
        if entity_type:
            self.details['entity_type'] = entity_type
        if entity_id:
            self.details['entity_id'] = entity_id


class SystemError(ProjectManagementError):
    """システムエラー"""
    
    def __init__(self, message: str, component: str = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            recovery_strategy=RecoveryStrategy.ABORT,
            **kwargs
        )
        if component:
            self.details['component'] = component


class ErrorHandler:
    """エラーハンドリング管理クラス"""
    
    def __init__(self):
        self.error_history: List[Dict[str, Any]] = []
        self.error_counts: Dict[str, int] = {}
        self.recovery_attempts: Dict[str, int] = {}
        self._lock = threading.RLock()
        self.max_history_size = 1000
        self.max_retry_attempts = 3
        
        # ログ管理システム（遅延インポート対応）
        self._logger = None
    
    @property
    def logger(self):
        """ログ管理システムのインスタンスを取得"""
        if self._logger is None:
            try:
                from .logger import ProjectLogger
                self._logger = ProjectLogger()
            except ImportError:
                # ログ管理システムが利用できない場合の代替処理
                import logging
                self._logger = logging.getLogger(__name__)
        return self._logger
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> Optional[Any]:
        """
        エラーを処理
        
        Args:
            error: 発生した例外
            context: コンテキスト情報
            
        Returns:
            リカバリー結果（該当する場合）
        """
        with self._lock:
            # ProjectManagementError以外の例外をラップ
            if not isinstance(error, ProjectManagementError):
                error = self._wrap_exception(error)
            
            # エラー履歴に記録
            error_record = self._create_error_record(error, context)
            self._add_to_history(error_record)
            
            # ログに記録
            self._log_error(error, context)
            
            # リカバリー戦略に基づく処理
            return self._execute_recovery_strategy(error, context)
    
    def _wrap_exception(self, error: Exception) -> ProjectManagementError:
        """標準例外をProjectManagementErrorにラップ"""
        error_mapping = {
            ValueError: (ErrorCategory.VALIDATION, ErrorSeverity.LOW),
            TypeError: (ErrorCategory.VALIDATION, ErrorSeverity.LOW),
            FileNotFoundError: (ErrorCategory.FILE_IO, ErrorSeverity.MEDIUM),
            PermissionError: (ErrorCategory.PERMISSION, ErrorSeverity.HIGH),
            OSError: (ErrorCategory.SYSTEM, ErrorSeverity.HIGH),
            KeyError: (ErrorCategory.DATA, ErrorSeverity.MEDIUM),
            AttributeError: (ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM),
            ImportError: (ErrorCategory.SYSTEM, ErrorSeverity.HIGH),
            MemoryError: (ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL),
        }
        
        category, severity = error_mapping.get(type(error), (ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM))
        
        return ProjectManagementError(
            message=str(error),
            category=category,
            severity=severity,
            original_exception=error
        )
    
    def _create_error_record(self, error: ProjectManagementError, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """エラー記録を作成"""
        record = error.to_dict()
        record['context'] = context or {}
        record['thread_id'] = threading.get_ident()
        record['process_id'] = threading.current_thread().name
        
        return record
    
    def _add_to_history(self, error_record: Dict[str, Any]) -> None:
        """エラー履歴に追加"""
        self.error_history.append(error_record)
        
        # カウント更新
        error_key = f"{error_record['category']}:{error_record['message']}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # 履歴サイズ制限
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size//2:]
    
    def _log_error(self, error: ProjectManagementError, context: Dict[str, Any] = None) -> None:
        """エラーをログに記録"""
        try:
            if hasattr(self.logger, 'error'):  # ProjectLogger
                self.logger.error(
                    error.category,
                    error.message,
                    module=context.get('module', 'error_handler') if context else 'error_handler',
                    exception=error.original_exception,
                    error_id=error.error_id,
                    severity=error.severity,
                    recovery_strategy=error.recovery_strategy,
                    context=context
                )
            else:  # 標準ログ
                self.logger.error(f"[{error.category}] {error.message}", exc_info=error.original_exception)
        except Exception:
            # ログ記録に失敗した場合は標準エラー出力
            print(f"ERROR: {error.message}", file=sys.stderr)
    
    def _execute_recovery_strategy(self, error: ProjectManagementError, context: Dict[str, Any] = None) -> Optional[Any]:
        """リカバリー戦略を実行"""
        strategy = error.recovery_strategy
        
        if strategy == RecoveryStrategy.RETRY:
            return self._attempt_retry(error, context)
        elif strategy == RecoveryStrategy.FALLBACK:
            return self._attempt_fallback(error, context)
        elif strategy == RecoveryStrategy.IGNORE:
            return self._ignore_error(error, context)
        elif strategy == RecoveryStrategy.ABORT:
            self._abort_operation(error, context)
        
        return None
    
    def _attempt_retry(self, error: ProjectManagementError, context: Dict[str, Any] = None) -> Optional[Any]:
        """リトライを試行"""
        retry_key = f"{error.category}:{context.get('function', 'unknown') if context else 'unknown'}"
        attempts = self.recovery_attempts.get(retry_key, 0)
        
        if attempts < self.max_retry_attempts:
            self.recovery_attempts[retry_key] = attempts + 1
            
            if hasattr(self.logger, 'warning'):
                self.logger.warning(
                    error.category,
                    f"リトライを実行します（{attempts + 1}/{self.max_retry_attempts}）: {error.message}",
                    retry_attempt=attempts + 1
                )
            
            return "RETRY"
        else:
            if hasattr(self.logger, 'error'):
                self.logger.error(
                    error.category,
                    f"最大リトライ回数に達しました: {error.message}",
                    max_attempts=self.max_retry_attempts
                )
            return None
    
    def _attempt_fallback(self, error: ProjectManagementError, context: Dict[str, Any] = None) -> Optional[Any]:
        """フォールバック処理を試行"""
        if hasattr(self.logger, 'warning'):
            self.logger.warning(
                error.category,
                f"フォールバック処理を実行します: {error.message}"
            )
        
        # コンテキストからフォールバック値を取得
        if context and 'fallback_value' in context:
            return context['fallback_value']
        
        return "FALLBACK"
    
    def _ignore_error(self, error: ProjectManagementError, context: Dict[str, Any] = None) -> Optional[Any]:
        """エラーを無視して続行"""
        if hasattr(self.logger, 'warning'):
            self.logger.warning(
                error.category,
                f"エラーを無視して続行します: {error.message}"
            )
        return "IGNORED"
    
    def _abort_operation(self, error: ProjectManagementError, context: Dict[str, Any] = None) -> None:
        """操作を中止"""
        if hasattr(self.logger, 'critical'):
            self.logger.critical(
                error.category,
                f"クリティカルエラーのため操作を中止します: {error.message}"
            )
        
        # クリティカルエラーの場合は例外を再発生
        raise error
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """エラー統計を取得"""
        with self._lock:
            total_errors = len(self.error_history)
            
            if total_errors == 0:
                return {'total_errors': 0}
            
            # カテゴリ別統計
            category_counts = {}
            severity_counts = {}
            recent_errors = []
            
            for record in self.error_history[-100:]:  # 最新100件
                category = record.get('category', 'UNKNOWN')
                severity = record.get('severity', 'UNKNOWN')
                
                category_counts[category] = category_counts.get(category, 0) + 1
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                
                # 最近のエラー（過去1時間）
                error_time = datetime.fromisoformat(record['timestamp'])
                if (datetime.now() - error_time).total_seconds() < 3600:
                    recent_errors.append(record)
            
            return {
                'total_errors': total_errors,
                'category_counts': category_counts,
                'severity_counts': severity_counts,
                'recent_errors_count': len(recent_errors),
                'top_errors': dict(sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                'recovery_attempts': self.recovery_attempts.copy()
            }
    
    def clear_history(self) -> int:
        """エラー履歴をクリア"""
        with self._lock:
            count = len(self.error_history)
            self.error_history.clear()
            self.error_counts.clear()
            self.recovery_attempts.clear()
            return count


# グローバルエラーハンドラーインスタンス
_global_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """グローバルエラーハンドラーを取得"""
    return _global_error_handler


# デコレータ関数群
def handle_errors(
    recovery_strategy: str = RecoveryStrategy.NONE,
    fallback_value: Any = None,
    log_errors: bool = True,
    reraise: bool = False
):
    """
    エラーハンドリングデコレータ
    
    Args:
        recovery_strategy: リカバリー戦略
        fallback_value: フォールバック値
        log_errors: エラーログ出力フラグ
        reraise: 例外再発生フラグ
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    'function': func.__name__,
                    'module': func.__module__,
                    'args': str(args) if args else None,
                    'kwargs': str(kwargs) if kwargs else None,
                    'fallback_value': fallback_value
                }
                
                if log_errors:
                    result = _global_error_handler.handle_error(e, context)
                    
                    if result == "RETRY":
                        # リトライの場合は関数を再実行
                        try:
                            return func(*args, **kwargs)
                        except Exception as retry_error:
                            if reraise:
                                raise retry_error
                            return fallback_value
                    elif result == "FALLBACK" or result == "IGNORED":
                        return fallback_value
                
                if reraise:
                    raise
                
                return fallback_value
        
        return wrapper
    return decorator


def validate_input(validation_func: Callable = None, error_message: str = None):
    """
    入力値検証デコレータ
    
    Args:
        validation_func: 検証関数
        error_message: エラーメッセージ
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if validation_func:
                try:
                    if not validation_func(*args, **kwargs):
                        raise ValidationError(
                            error_message or f"入力値の検証に失敗しました: {func.__name__}"
                        )
                except Exception as e:
                    if not isinstance(e, ValidationError):
                        raise ValidationError(
                            error_message or f"検証エラー: {str(e)}",
                            original_exception=e
                        )
                    raise
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def business_rule(rule_func: Callable = None, error_message: str = None):
    """
    ビジネスルール検証デコレータ
    
    Args:
        rule_func: ルール検証関数
        error_message: エラーメッセージ
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if rule_func:
                try:
                    if not rule_func(*args, **kwargs):
                        raise BusinessLogicError(
                            error_message or f"ビジネスルール違反: {func.__name__}"
                        )
                except Exception as e:
                    if not isinstance(e, BusinessLogicError):
                        raise BusinessLogicError(
                            error_message or f"ビジネスルールエラー: {str(e)}",
                            original_exception=e
                        )
                    raise
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def retry_on_failure(max_attempts: int = 3, delay_seconds: float = 1.0, 
                    exponential_backoff: bool = False):
    """
    失敗時リトライデコレータ
    
    Args:
        max_attempts: 最大試行回数
        delay_seconds: 遅延時間
        exponential_backoff: 指数バックオフ使用フラグ
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:  # 最後の試行でなければ待機
                        delay = delay_seconds
                        if exponential_backoff:
                            delay *= (2 ** attempt)
                        
                        time.sleep(delay)
                    
                    context = {
                        'function': func.__name__,
                        'attempt': attempt + 1,
                        'max_attempts': max_attempts
                    }
                    _global_error_handler.handle_error(e, context)
            
            # 全ての試行が失敗した場合
            raise last_exception
        
        return wrapper
    return decorator


def measure_performance(log_slow_operations: bool = True, threshold_ms: float = 1000.0):
    """
    パフォーマンス測定デコレータ
    
    Args:
        log_slow_operations: 遅い操作のログ出力フラグ
        threshold_ms: 遅い操作の閾値（ミリ秒）
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                
                if log_slow_operations and duration_ms > threshold_ms:
                    try:
                        if hasattr(_global_error_handler.logger, 'performance'):
                            _global_error_handler.logger.performance(
                                func.__name__,
                                duration_ms,
                                {
                                    'module': func.__module__,
                                    'threshold_ms': threshold_ms,
                                    'is_slow': True
                                }
                            )
                    except Exception:
                        pass  # パフォーマンスログ失敗は無視
        
        return wrapper
    return decorator