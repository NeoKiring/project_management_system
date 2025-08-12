"""
システム設定管理
環境設定・ユーザー設定・通知設定の一元管理
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class LogLevel(Enum):
    """ログレベル定義"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Theme(Enum):
    """UIテーマ定義"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


@dataclass
class DatabaseSettings:
    """データベース設定"""
    data_directory: str = "data"
    auto_backup: bool = True
    backup_interval_hours: int = 24
    backup_retention_days: int = 30
    max_file_size_mb: int = 100
    enable_compression: bool = False


@dataclass
class LoggingSettings:
    """ログ設定"""
    level: str = LogLevel.INFO.value
    max_file_size_mb: int = 100
    backup_count: int = 5
    retention_days: int = 30
    enable_console_output: bool = True
    enable_file_output: bool = True
    enable_audit_log: bool = True
    enable_performance_log: bool = True


@dataclass
class NotificationSettings:
    """通知設定"""
    enabled: bool = True
    deadline_warning_days: int = 7
    progress_delay_threshold: float = 50.0
    insufficient_progress_days: int = 3
    insufficient_progress_threshold: float = 30.0
    check_interval_hours: int = 24
    retention_days: int = 90
    enable_deadline_approaching: bool = True
    enable_deadline_overdue: bool = True
    enable_progress_delay: bool = True
    enable_progress_insufficient: bool = True


@dataclass
class UISettings:
    """UI設定"""
    theme: str = Theme.LIGHT.value
    language: str = "ja"
    auto_save_interval_seconds: int = 300
    default_page_size: int = 50
    enable_animations: bool = True
    show_tooltips: bool = True
    confirm_delete_operations: bool = True


@dataclass
class PerformanceSettings:
    """パフォーマンス設定"""
    max_memory_entries: int = 10000
    cache_enabled: bool = True
    cache_size_limit: int = 1000
    batch_size: int = 100
    query_timeout_seconds: int = 30
    enable_threading: bool = True
    max_worker_threads: int = 4


@dataclass
class SecuritySettings:
    """セキュリティ設定"""
    enable_user_authentication: bool = False
    session_timeout_minutes: int = 60
    password_min_length: int = 8
    enable_audit_trail: bool = True
    enable_data_encryption: bool = False
    allowed_file_extensions: List[str] = None
    
    def __post_init__(self):
        if self.allowed_file_extensions is None:
            self.allowed_file_extensions = ['.json', '.xlsx', '.csv', '.txt']


@dataclass
class ExternalIntegrationSettings:
    """外部連携設定"""
    excel_import_enabled: bool = True
    excel_export_enabled: bool = True
    auto_detect_format: bool = True
    default_date_format: str = "%Y-%m-%d"
    default_encoding: str = "utf-8"
    max_import_rows: int = 10000


class SystemSettings:
    """
    システム設定統合管理クラス
    """
    
    def __init__(self, config_file: str = None):
        """
        設定管理の初期化
        
        Args:
            config_file: 設定ファイルパス
        """
        self.config_file = Path(config_file) if config_file else Path("data/settings.json")
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # デフォルト設定
        self.database = DatabaseSettings()
        self.logging = LoggingSettings()
        self.notifications = NotificationSettings()
        self.ui = UISettings()
        self.performance = PerformanceSettings()
        self.security = SecuritySettings()
        self.external = ExternalIntegrationSettings()
        
        # システム情報
        self.system_info = {
            'version': '1.0.0',
            'created_at': datetime.now().isoformat(),
            'last_modified': datetime.now().isoformat(),
            'config_file': str(self.config_file)
        }
        
        # 設定読み込み
        self.load_settings()
    
    def load_settings(self) -> bool:
        """
        設定ファイルから設定を読み込み
        
        Returns:
            読み込み成功の可否
        """
        try:
            if not self.config_file.exists():
                # 設定ファイルが存在しない場合はデフォルト設定を保存
                self.save_settings()
                return True
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 各セクションの設定を読み込み
            if 'database' in data:
                self.database = DatabaseSettings(**data['database'])
            
            if 'logging' in data:
                self.logging = LoggingSettings(**data['logging'])
            
            if 'notifications' in data:
                self.notifications = NotificationSettings(**data['notifications'])
            
            if 'ui' in data:
                self.ui = UISettings(**data['ui'])
            
            if 'performance' in data:
                self.performance = PerformanceSettings(**data['performance'])
            
            if 'security' in data:
                self.security = SecuritySettings(**data['security'])
            
            if 'external' in data:
                self.external = ExternalIntegrationSettings(**data['external'])
            
            if 'system_info' in data:
                self.system_info.update(data['system_info'])
            
            return True
            
        except (json.JSONDecodeError, FileNotFoundError, TypeError, KeyError) as e:
            # 読み込みエラーの場合はデフォルト設定を使用
            print(f"設定読み込みエラー（デフォルト設定を使用）: {e}")
            return False
        except Exception as e:
            print(f"予期しない設定読み込みエラー: {e}")
            return False
    
    def save_settings(self) -> bool:
        """
        設定をファイルに保存
        
        Returns:
            保存成功の可否
        """
        try:
            # システム情報を更新
            self.system_info['last_modified'] = datetime.now().isoformat()
            
            settings_data = {
                'database': asdict(self.database),
                'logging': asdict(self.logging),
                'notifications': asdict(self.notifications),
                'ui': asdict(self.ui),
                'performance': asdict(self.performance),
                'security': asdict(self.security),
                'external': asdict(self.external),
                'system_info': self.system_info
            }
            
            # 一時ファイルに書き込み後、アトミックに移動
            temp_file = self.config_file.with_suffix('.tmp')
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, ensure_ascii=False, indent=2)
            
            # アトミック移動
            if os.name == 'nt':  # Windows
                if self.config_file.exists():
                    self.config_file.unlink()
                temp_file.rename(self.config_file)
            else:  # Unix系
                temp_file.rename(self.config_file)
            
            return True
            
        except Exception as e:
            print(f"設定保存エラー: {e}")
            # 一時ファイルのクリーンアップ
            if 'temp_file' in locals() and temp_file.exists():
                temp_file.unlink()
            return False
    
    def reset_to_defaults(self) -> bool:
        """
        設定をデフォルトにリセット
        
        Returns:
            リセット成功の可否
        """
        try:
            self.database = DatabaseSettings()
            self.logging = LoggingSettings()
            self.notifications = NotificationSettings()
            self.ui = UISettings()
            self.performance = PerformanceSettings()
            self.security = SecuritySettings()
            self.external = ExternalIntegrationSettings()
            
            self.system_info['last_modified'] = datetime.now().isoformat()
            
            return self.save_settings()
            
        except Exception as e:
            print(f"設定リセットエラー: {e}")
            return False
    
    def update_setting(self, section: str, key: str, value: Any) -> bool:
        """
        個別設定を更新
        
        Args:
            section: 設定セクション（database, logging, notifications等）
            key: 設定キー
            value: 設定値
            
        Returns:
            更新成功の可否
        """
        try:
            section_obj = getattr(self, section, None)
            if section_obj is None:
                return False
            
            if hasattr(section_obj, key):
                setattr(section_obj, key, value)
                return self.save_settings()
            
            return False
            
        except Exception as e:
            print(f"設定更新エラー: {e}")
            return False
    
    def get_setting(self, section: str, key: str, default: Any = None) -> Any:
        """
        個別設定を取得
        
        Args:
            section: 設定セクション
            key: 設定キー
            default: デフォルト値
            
        Returns:
            設定値
        """
        try:
            section_obj = getattr(self, section, None)
            if section_obj is None:
                return default
            
            return getattr(section_obj, key, default)
            
        except Exception:
            return default
    
    def export_settings(self, file_path: str) -> bool:
        """
        設定をファイルにエクスポート
        
        Args:
            file_path: エクスポート先ファイルパス
            
        Returns:
            エクスポート成功の可否
        """
        try:
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'source_system': 'ProjectManagementSystem',
                'version': self.system_info.get('version', '1.0.0'),
                'settings': {
                    'database': asdict(self.database),
                    'logging': asdict(self.logging),
                    'notifications': asdict(self.notifications),
                    'ui': asdict(self.ui),
                    'performance': asdict(self.performance),
                    'security': asdict(self.security),
                    'external': asdict(self.external)
                }
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"設定エクスポートエラー: {e}")
            return False
    
    def import_settings(self, file_path: str, selective: bool = True) -> bool:
        """
        設定をファイルからインポート
        
        Args:
            file_path: インポート元ファイルパス
            selective: 選択的インポート（Trueの場合、既存設定を保持）
            
        Returns:
            インポート成功の可否
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if 'settings' not in import_data:
                return False
            
            settings = import_data['settings']
            
            # 選択的インポート
            if selective:
                # 既存設定をベースに、インポートデータで上書き
                if 'database' in settings:
                    for key, value in settings['database'].items():
                        if hasattr(self.database, key):
                            setattr(self.database, key, value)
                
                if 'logging' in settings:
                    for key, value in settings['logging'].items():
                        if hasattr(self.logging, key):
                            setattr(self.logging, key, value)
                
                if 'notifications' in settings:
                    for key, value in settings['notifications'].items():
                        if hasattr(self.notifications, key):
                            setattr(self.notifications, key, value)
                
                if 'ui' in settings:
                    for key, value in settings['ui'].items():
                        if hasattr(self.ui, key):
                            setattr(self.ui, key, value)
                
                if 'performance' in settings:
                    for key, value in settings['performance'].items():
                        if hasattr(self.performance, key):
                            setattr(self.performance, key, value)
                
                if 'security' in settings:
                    for key, value in settings['security'].items():
                        if hasattr(self.security, key):
                            setattr(self.security, key, value)
                
                if 'external' in settings:
                    for key, value in settings['external'].items():
                        if hasattr(self.external, key):
                            setattr(self.external, key, value)
            else:
                # 完全置換
                if 'database' in settings:
                    self.database = DatabaseSettings(**settings['database'])
                if 'logging' in settings:
                    self.logging = LoggingSettings(**settings['logging'])
                if 'notifications' in settings:
                    self.notifications = NotificationSettings(**settings['notifications'])
                if 'ui' in settings:
                    self.ui = UISettings(**settings['ui'])
                if 'performance' in settings:
                    self.performance = PerformanceSettings(**settings['performance'])
                if 'security' in settings:
                    self.security = SecuritySettings(**settings['security'])
                if 'external' in settings:
                    self.external = ExternalIntegrationSettings(**settings['external'])
            
            return self.save_settings()
            
        except Exception as e:
            print(f"設定インポートエラー: {e}")
            return False
    
    def validate_settings(self) -> Dict[str, List[str]]:
        """
        設定の妥当性を検証
        
        Returns:
            検証結果（エラーメッセージのリスト）
        """
        errors = {}
        
        # データベース設定の検証
        db_errors = []
        if self.database.backup_interval_hours < 1:
            db_errors.append("バックアップ間隔は1時間以上である必要があります")
        if self.database.backup_retention_days < 1:
            db_errors.append("バックアップ保持期間は1日以上である必要があります")
        if self.database.max_file_size_mb < 1:
            db_errors.append("最大ファイルサイズは1MB以上である必要があります")
        if db_errors:
            errors['database'] = db_errors
        
        # ログ設定の検証
        log_errors = []
        valid_levels = [level.value for level in LogLevel]
        if self.logging.level not in valid_levels:
            log_errors.append(f"無効なログレベル: {self.logging.level}")
        if self.logging.max_file_size_mb < 1:
            log_errors.append("ログファイルサイズは1MB以上である必要があります")
        if self.logging.backup_count < 1:
            log_errors.append("バックアップ数は1以上である必要があります")
        if log_errors:
            errors['logging'] = log_errors
        
        # 通知設定の検証
        notif_errors = []
        if self.notifications.deadline_warning_days < 0:
            notif_errors.append("期限警告日数は0以上である必要があります")
        if not (0 <= self.notifications.progress_delay_threshold <= 100):
            notif_errors.append("進捗遅延しきい値は0-100の範囲である必要があります")
        if not (0 <= self.notifications.insufficient_progress_threshold <= 100):
            notif_errors.append("進捗不足しきい値は0-100の範囲である必要があります")
        if self.notifications.check_interval_hours < 1:
            notif_errors.append("チェック間隔は1時間以上である必要があります")
        if notif_errors:
            errors['notifications'] = notif_errors
        
        # UI設定の検証
        ui_errors = []
        valid_themes = [theme.value for theme in Theme]
        if self.ui.theme not in valid_themes:
            ui_errors.append(f"無効なテーマ: {self.ui.theme}")
        if self.ui.auto_save_interval_seconds < 60:
            ui_errors.append("自動保存間隔は60秒以上である必要があります")
        if self.ui.default_page_size < 10:
            ui_errors.append("デフォルトページサイズは10以上である必要があります")
        if ui_errors:
            errors['ui'] = ui_errors
        
        # パフォーマンス設定の検証
        perf_errors = []
        if self.performance.max_memory_entries < 100:
            perf_errors.append("メモリ最大エントリ数は100以上である必要があります")
        if self.performance.batch_size < 1:
            perf_errors.append("バッチサイズは1以上である必要があります")
        if self.performance.max_worker_threads < 1:
            perf_errors.append("ワーカースレッド数は1以上である必要があります")
        if perf_errors:
            errors['performance'] = perf_errors
        
        # セキュリティ設定の検証
        sec_errors = []
        if self.security.session_timeout_minutes < 5:
            sec_errors.append("セッションタイムアウトは5分以上である必要があります")
        if self.security.password_min_length < 4:
            sec_errors.append("パスワード最小長は4文字以上である必要があります")
        if sec_errors:
            errors['security'] = sec_errors
        
        return errors
    
    def get_all_settings(self) -> Dict[str, Any]:
        """全設定を辞書として取得"""
        return {
            'database': asdict(self.database),
            'logging': asdict(self.logging),
            'notifications': asdict(self.notifications),
            'ui': asdict(self.ui),
            'performance': asdict(self.performance),
            'security': asdict(self.security),
            'external': asdict(self.external),
            'system_info': self.system_info
        }
    
    def create_backup(self, backup_path: str = None) -> str:
        """
        設定のバックアップを作成
        
        Args:
            backup_path: バックアップファイルパス
            
        Returns:
            作成されたバックアップファイルパス
        """
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"settings_backup_{timestamp}.json"
        
        try:
            self.export_settings(backup_path)
            return backup_path
        except Exception as e:
            print(f"設定バックアップエラー: {e}")
            return ""
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"SystemSettings(config_file='{self.config_file}')"
    
    def __repr__(self) -> str:
        """詳細文字列表現"""
        return f"SystemSettings(config_file='{self.config_file}', " \
               f"version='{self.system_info.get('version', '1.0.0')}')"


# グローバル設定インスタンス
_global_settings: Optional[SystemSettings] = None


def get_settings(config_file: str = None) -> SystemSettings:
    """
    グローバル設定インスタンスを取得
    
    Args:
        config_file: 設定ファイルパス（初回のみ使用）
        
    Returns:
        設定インスタンス
    """
    global _global_settings
    
    if _global_settings is None:
        _global_settings = SystemSettings(config_file)
    
    return _global_settings


def reset_global_settings() -> None:
    """グローバル設定インスタンスをリセット"""
    global _global_settings
    _global_settings = None