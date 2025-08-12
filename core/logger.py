"""
ログ管理システム
包括的ログ機能・監査証跡・統計情報を提供
"""

import json
import logging
import logging.handlers
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from enum import Enum
import threading
import uuid
import traceback


class LogLevel:
    """ログレベル定義"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory:
    """ログカテゴリ定義"""
    SYSTEM = "SYSTEM"
    DATA = "DATA"
    USER = "USER"
    PERFORMANCE = "PERFORMANCE"
    SECURITY = "SECURITY"
    AUDIT = "AUDIT"
    ERROR = "ERROR"


class AuditAction:
    """監査アクション定義"""
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    BACKUP = "BACKUP"
    RESTORE = "RESTORE"


class LogEntry:
    """ログエントリクラス"""
    
    def __init__(self,
                 level: str,
                 category: str,
                 message: str,
                 module: str = None,
                 function: str = None,
                 user: str = None):
        """
        ログエントリの初期化
        
        Args:
            level: ログレベル
            category: ログカテゴリ
            message: ログメッセージ
            module: モジュール名
            function: 関数名
            user: ユーザー名
        """
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.now()
        self.level = level
        self.category = category
        self.message = message
        self.module = module or "unknown"
        self.function = function or "unknown"
        self.user = user or "system"
        self.metadata: Dict[str, Any] = {}
        self.session_id: Optional[str] = None
        self.request_id: Optional[str] = None
    
    def add_metadata(self, key: str, value: Any) -> None:
        """メタデータを追加"""
        self.metadata[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'level': self.level,
            'category': self.category,
            'message': self.message,
            'module': self.module,
            'function': self.function,
            'user': self.user,
            'metadata': self.metadata.copy(),
            'session_id': self.session_id,
            'request_id': self.request_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        """辞書から復元"""
        entry = cls(
            data['level'],
            data['category'],
            data['message'],
            data.get('module'),
            data.get('function'),
            data.get('user')
        )
        
        entry.id = data['id']
        entry.timestamp = datetime.fromisoformat(data['timestamp'])
        entry.metadata = data.get('metadata', {}).copy()
        entry.session_id = data.get('session_id')
        entry.request_id = data.get('request_id')
        
        return entry


class AuditEntry:
    """監査エントリクラス"""
    
    def __init__(self,
                 action: str,
                 entity_type: str,
                 entity_id: str,
                 entity_name: str,
                 user: str,
                 details: str = ""):
        """
        監査エントリの初期化
        
        Args:
            action: 実行されたアクション
            entity_type: 対象エンティティタイプ
            entity_id: 対象エンティティID
            entity_name: 対象エンティティ名
            user: 実行ユーザー
            details: 詳細情報
        """
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.now()
        self.action = action
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.entity_name = entity_name
        self.user = user
        self.details = details
        self.before_data: Optional[Dict[str, Any]] = None
        self.after_data: Optional[Dict[str, Any]] = None
        self.metadata: Dict[str, Any] = {}
        self.success = True
        self.error_message: Optional[str] = None
    
    def set_data_change(self, before: Dict[str, Any], after: Dict[str, Any]) -> None:
        """変更前後のデータを設定"""
        self.before_data = before.copy() if before else None
        self.after_data = after.copy() if after else None
    
    def set_error(self, error_message: str) -> None:
        """エラー情報を設定"""
        self.success = False
        self.error_message = error_message
    
    def add_metadata(self, key: str, value: Any) -> None:
        """メタデータを追加"""
        self.metadata[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'entity_name': self.entity_name,
            'user': self.user,
            'details': self.details,
            'before_data': self.before_data,
            'after_data': self.after_data,
            'metadata': self.metadata.copy(),
            'success': self.success,
            'error_message': self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditEntry':
        """辞書から復元"""
        entry = cls(
            data['action'],
            data['entity_type'],
            data['entity_id'],
            data['entity_name'],
            data['user'],
            data.get('details', '')
        )
        
        entry.id = data['id']
        entry.timestamp = datetime.fromisoformat(data['timestamp'])
        entry.before_data = data.get('before_data')
        entry.after_data = data.get('after_data')
        entry.metadata = data.get('metadata', {}).copy()
        entry.success = data.get('success', True)
        entry.error_message = data.get('error_message')
        
        return entry


class LogStatistics:
    """ログ統計クラス"""
    
    def __init__(self):
        self.reset()
    
    def reset(self) -> None:
        """統計をリセット"""
        self.start_time = datetime.now()
        self.level_counts = {level: 0 for level in [
            LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, 
            LogLevel.ERROR, LogLevel.CRITICAL
        ]}
        self.category_counts = {category: 0 for category in [
            LogCategory.SYSTEM, LogCategory.DATA, LogCategory.USER,
            LogCategory.PERFORMANCE, LogCategory.SECURITY, 
            LogCategory.AUDIT, LogCategory.ERROR
        ]}
        self.module_counts: Dict[str, int] = {}
        self.user_counts: Dict[str, int] = {}
        self.total_entries = 0
        self.error_count = 0
        self.last_error: Optional[datetime] = None
    
    def update(self, entry: LogEntry) -> None:
        """統計を更新"""
        self.total_entries += 1
        
        # レベル別カウント
        self.level_counts[entry.level] = self.level_counts.get(entry.level, 0) + 1
        
        # カテゴリ別カウント
        self.category_counts[entry.category] = self.category_counts.get(entry.category, 0) + 1
        
        # モジュール別カウント
        self.module_counts[entry.module] = self.module_counts.get(entry.module, 0) + 1
        
        # ユーザー別カウント
        self.user_counts[entry.user] = self.user_counts.get(entry.user, 0) + 1
        
        # エラー統計
        if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            self.error_count += 1
            self.last_error = entry.timestamp
    
    def get_summary(self) -> Dict[str, Any]:
        """統計サマリーを取得"""
        uptime = datetime.now() - self.start_time
        
        return {
            'start_time': self.start_time.isoformat(),
            'uptime_seconds': uptime.total_seconds(),
            'total_entries': self.total_entries,
            'error_count': self.error_count,
            'error_rate': (self.error_count / self.total_entries) * 100 if self.total_entries > 0 else 0,
            'last_error': self.last_error.isoformat() if self.last_error else None,
            'level_counts': self.level_counts.copy(),
            'category_counts': self.category_counts.copy(),
            'top_modules': dict(sorted(self.module_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            'top_users': dict(sorted(self.user_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        }


class ProjectLogger:
    """
    プロジェクト管理システム専用ログ管理クラス
    """
    
    _instance: Optional['ProjectLogger'] = None
    _lock = threading.Lock()
    
    def __new__(cls, log_dir: str = None) -> 'ProjectLogger':
        """シングルトンインスタンスを取得"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, log_dir: str = None):
        """
        ログ管理システムの初期化
        
        Args:
            log_dir: ログディレクトリパス
        """
        if self._initialized:
            return
        
        self.log_dir = Path(log_dir) if log_dir else Path("data/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # ログファイルパス
        self.application_log = self.log_dir / "application.log"
        self.audit_log = self.log_dir / "audit.log"
        self.performance_log = self.log_dir / "performance.log"
        self.error_log = self.log_dir / "error.log"
        
        # ログエントリの保存
        self.log_entries: List[LogEntry] = []
        self.audit_entries: List[AuditEntry] = []
        
        # 統計管理
        self.statistics = LogStatistics()
        
        # スレッドセーフティ
        self._lock_entries = threading.RLock()
        
        # 設定
        self.max_entries_in_memory = 10000
        self.max_log_file_size = 100 * 1024 * 1024  # 100MB
        self.backup_count = 5
        self.retention_days = 30
        
        # Pythonの標準ログ設定
        self._setup_python_logging()
        
        # 現在のユーザー・セッション情報
        self.current_user = "system"
        self.current_session_id: Optional[str] = None
        
        self._initialized = True
        
        # 初期化ログ
        self.info(LogCategory.SYSTEM, "ログ管理システムが初期化されました")
    
    def _setup_python_logging(self) -> None:
        """Python標準ログの設定"""
        # アプリケーションログ
        app_handler = logging.handlers.RotatingFileHandler(
            self.application_log,
            maxBytes=self.max_log_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        app_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        app_handler.setFormatter(app_formatter)
        
        # エラーログ
        error_handler = logging.handlers.RotatingFileHandler(
            self.error_log,
            maxBytes=self.max_log_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(app_formatter)
        
        # ルートロガー設定
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(app_handler)
        root_logger.addHandler(error_handler)
        
        # コンソールハンドラー（開発時用）
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    def set_user_context(self, user: str, session_id: str = None) -> None:
        """ユーザーコンテキストを設定"""
        self.current_user = user
        self.current_session_id = session_id or str(uuid.uuid4())
    
    def _create_log_entry(self, level: str, category: str, message: str, 
                         module: str = None, function: str = None) -> LogEntry:
        """ログエントリを作成"""
        entry = LogEntry(level, category, message, module, function, self.current_user)
        entry.session_id = self.current_session_id
        return entry
    
    def _log(self, level: str, category: str, message: str, 
             module: str = None, function: str = None, **metadata) -> None:
        """内部ログ処理"""
        with self._lock_entries:
            entry = self._create_log_entry(level, category, message, module, function)
            
            # メタデータを追加
            for key, value in metadata.items():
                entry.add_metadata(key, value)
            
            # メモリ内保存
            self.log_entries.append(entry)
            
            # メモリ制限チェック
            if len(self.log_entries) > self.max_entries_in_memory:
                self.log_entries = self.log_entries[-self.max_entries_in_memory//2:]
            
            # 統計更新
            self.statistics.update(entry)
            
            # Python標準ログに出力
            logger = logging.getLogger(module or 'ProjectManager')
            log_message = f"[{category}] {message}"
            
            if metadata:
                log_message += f" | {json.dumps(metadata, ensure_ascii=False, default=str)}"
            
            if level == LogLevel.DEBUG:
                logger.debug(log_message)
            elif level == LogLevel.INFO:
                logger.info(log_message)
            elif level == LogLevel.WARNING:
                logger.warning(log_message)
            elif level == LogLevel.ERROR:
                logger.error(log_message)
            elif level == LogLevel.CRITICAL:
                logger.critical(log_message)
    
    # 公開ログメソッド
    def debug(self, category: str, message: str, module: str = None, **metadata) -> None:
        """デバッグログ"""
        self._log(LogLevel.DEBUG, category, message, module, **metadata)
    
    def info(self, category: str, message: str, module: str = None, **metadata) -> None:
        """情報ログ"""
        self._log(LogLevel.INFO, category, message, module, **metadata)
    
    def warning(self, category: str, message: str, module: str = None, **metadata) -> None:
        """警告ログ"""
        self._log(LogLevel.WARNING, category, message, module, **metadata)
    
    def error(self, category: str, message: str, module: str = None, 
              exception: Exception = None, **metadata) -> None:
        """エラーログ"""
        if exception:
            metadata['exception_type'] = type(exception).__name__
            metadata['exception_message'] = str(exception)
            metadata['traceback'] = traceback.format_exc()
        
        self._log(LogLevel.ERROR, category, message, module, **metadata)
    
    def critical(self, category: str, message: str, module: str = None, 
                 exception: Exception = None, **metadata) -> None:
        """クリティカルログ"""
        if exception:
            metadata['exception_type'] = type(exception).__name__
            metadata['exception_message'] = str(exception)
            metadata['traceback'] = traceback.format_exc()
        
        self._log(LogLevel.CRITICAL, category, message, module, **metadata)
    
    # 監査ログ
    def audit(self, action: str, entity_type: str, entity_id: str, 
             entity_name: str, details: str = "", 
             before_data: Dict[str, Any] = None, 
             after_data: Dict[str, Any] = None, **metadata) -> None:
        """監査ログ"""
        with self._lock_entries:
            entry = AuditEntry(action, entity_type, entity_id, entity_name, 
                              self.current_user, details)
            
            if before_data or after_data:
                entry.set_data_change(before_data, after_data)
            
            for key, value in metadata.items():
                entry.add_metadata(key, value)
            
            self.audit_entries.append(entry)
            
            # 監査ログファイルに出力
            audit_logger = logging.getLogger('audit')
            audit_logger.info(json.dumps(entry.to_dict(), ensure_ascii=False, default=str))
    
    # パフォーマンスログ
    def performance(self, operation: str, duration_ms: float, 
                   details: Dict[str, Any] = None, **metadata) -> None:
        """パフォーマンスログ"""
        perf_data = {
            'operation': operation,
            'duration_ms': duration_ms,
            'details': details or {}
        }
        perf_data.update(metadata)
        
        self._log(LogLevel.INFO, LogCategory.PERFORMANCE, 
                 f"操作 '{operation}' が {duration_ms:.2f}ms で完了", 
                 'performance', **perf_data)
    
    # 検索・フィルタリング
    def get_logs(self, level: str = None, category: str = None, 
                module: str = None, user: str = None,
                start_time: datetime = None, end_time: datetime = None,
                limit: int = 1000) -> List[LogEntry]:
        """ログエントリを検索"""
        with self._lock_entries:
            filtered_logs = []
            
            for entry in reversed(self.log_entries):  # 新しい順
                # フィルタリング条件チェック
                if level and entry.level != level:
                    continue
                if category and entry.category != category:
                    continue
                if module and entry.module != module:
                    continue
                if user and entry.user != user:
                    continue
                if start_time and entry.timestamp < start_time:
                    continue
                if end_time and entry.timestamp > end_time:
                    continue
                
                filtered_logs.append(entry)
                
                if len(filtered_logs) >= limit:
                    break
            
            return filtered_logs
    
    def get_audit_logs(self, action: str = None, entity_type: str = None,
                      user: str = None, start_time: datetime = None,
                      end_time: datetime = None, limit: int = 1000) -> List[AuditEntry]:
        """監査ログを検索"""
        with self._lock_entries:
            filtered_audits = []
            
            for entry in reversed(self.audit_entries):  # 新しい順
                # フィルタリング条件チェック
                if action and entry.action != action:
                    continue
                if entity_type and entry.entity_type != entity_type:
                    continue
                if user and entry.user != user:
                    continue
                if start_time and entry.timestamp < start_time:
                    continue
                if end_time and entry.timestamp > end_time:
                    continue
                
                filtered_audits.append(entry)
                
                if len(filtered_audits) >= limit:
                    break
            
            return filtered_audits
    
    # 統計・レポート
    def get_statistics(self) -> Dict[str, Any]:
        """ログ統計を取得"""
        return self.statistics.get_summary()
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """エラーサマリーを取得"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_errors = [
            entry for entry in self.log_entries
            if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]
            and entry.timestamp >= cutoff_time
        ]
        
        error_counts = {}
        module_errors = {}
        
        for entry in recent_errors:
            # エラーメッセージ別
            error_counts[entry.message] = error_counts.get(entry.message, 0) + 1
            
            # モジュール別
            module_errors[entry.module] = module_errors.get(entry.module, 0) + 1
        
        return {
            'period_hours': hours,
            'total_errors': len(recent_errors),
            'unique_errors': len(error_counts),
            'top_errors': dict(sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            'errors_by_module': dict(sorted(module_errors.items(), key=lambda x: x[1], reverse=True))
        }
    
    # クリーンアップ
    def cleanup_old_logs(self) -> Dict[str, int]:
        """古いログをクリーンアップ"""
        cutoff_time = datetime.now() - timedelta(days=self.retention_days)
        
        with self._lock_entries:
            # メモリ内ログのクリーンアップ
            old_log_count = len([e for e in self.log_entries if e.timestamp < cutoff_time])
            self.log_entries = [e for e in self.log_entries if e.timestamp >= cutoff_time]
            
            old_audit_count = len([e for e in self.audit_entries if e.timestamp < cutoff_time])
            self.audit_entries = [e for e in self.audit_entries if e.timestamp >= cutoff_time]
        
        return {
            'deleted_logs': old_log_count,
            'deleted_audits': old_audit_count
        }
    
    # エクスポート・インポート
    def export_logs(self, file_path: str, format: str = 'json',
                   start_time: datetime = None, end_time: datetime = None) -> bool:
        """ログをエクスポート"""
        try:
            logs_to_export = self.get_logs(
                start_time=start_time, 
                end_time=end_time, 
                limit=None
            )
            
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'period': {
                    'start': start_time.isoformat() if start_time else None,
                    'end': end_time.isoformat() if end_time else None
                },
                'log_count': len(logs_to_export),
                'logs': [log.to_dict() for log in logs_to_export]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if format.lower() == 'json':
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                else:
                    # CSV形式（簡易版）
                    f.write("timestamp,level,category,module,user,message\n")
                    for log in logs_to_export:
                        f.write(f"{log.timestamp.isoformat()},{log.level},{log.category},{log.module},{log.user},\"{log.message}\"\n")
            
            self.audit(AuditAction.EXPORT, "Logs", "all", "システムログ", 
                      f"ログをエクスポート: {file_path}")
            return True
            
        except Exception as e:
            self.error(LogCategory.ERROR, f"ログエクスポートエラー: {e}", exception=e)
            return False
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"ProjectLogger(log_dir='{self.log_dir}', entries={len(self.log_entries)})"