# ====================
# core/__init__.py
# ====================
"""
コア機能パッケージ
ビジネスロジック・ログ・エラーハンドリング
"""

from .manager import ProjectManagementSystem
from .notification_manager import NotificationService
from .logger import (
    ProjectLogger, LogLevel, LogCategory, AuditAction,
    LogEntry, AuditEntry, LogStatistics
)
from .error_handler import (
    ProjectManagementError, ValidationError, DataError, 
    FileIOError, BusinessLogicError, SystemError,
    ErrorHandler, ErrorSeverity, ErrorCategory, RecoveryStrategy,
    handle_errors, validate_input, business_rule, 
    retry_on_failure, measure_performance,
    get_error_handler
)

__version__ = "1.0.0"

__all__ = [
    # 主要システムクラス
    'ProjectManagementSystem',
    'NotificationService',
    
    # ログ関連
    'ProjectLogger',
    'LogLevel',
    'LogCategory',
    'AuditAction',
    'LogEntry',
    'AuditEntry',
    'LogStatistics',
    
    # エラーハンドリング関連
    'ProjectManagementError',
    'ValidationError',
    'DataError',
    'FileIOError',
    'BusinessLogicError',
    'SystemError',
    'ErrorHandler',
    'ErrorSeverity',
    'ErrorCategory',
    'RecoveryStrategy',
    
    # デコレータ
    'handle_errors',
    'validate_input',
    'business_rule',
    'retry_on_failure',
    'measure_performance',
    
    # ユーティリティ
    'get_error_handler'
]
