#!/usr/bin/env python3
"""
プロジェクト管理システム メインエントリーポイント
アプリケーション起動・初期化・例外ハンドリング
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from core.manager import ProjectManagementSystem
    from core.notification_manager import NotificationService
    from core.logger import ProjectLogger, LogCategory
    from core.error_handler import get_error_handler, SystemError
    from config.settings import get_settings, SystemSettings
except ImportError as e:
    print(f"モジュールインポートエラー: {e}")
    print("必要な依存関係がインストールされていない可能性があります。")
    print("pip install -r requirements.txt を実行してください。")
    sys.exit(1)


class ApplicationManager:
    """
    アプリケーション管理クラス
    起動・初期化・シャットダウンの制御
    """
    
    def __init__(self):
        self.settings: Optional[SystemSettings] = None
        self.pms: Optional[ProjectManagementSystem] = None
        self.notification_service: Optional[NotificationService] = None
        self.logger: Optional[ProjectLogger] = None
        self.error_handler = get_error_handler()
        self.is_initialized = False
    
    def initialize(self, config_file: str = None, data_dir: str = None) -> bool:
        """
        アプリケーションを初期化
        
        Args:
            config_file: 設定ファイルパス
            data_dir: データディレクトリパス
            
        Returns:
            初期化成功の可否
        """
        try:
            print("プロジェクト管理システムを初期化しています...")
            
            # 設定読み込み
            self.settings = get_settings(config_file)
            if data_dir:
                self.settings.database.data_directory = data_dir
            
            # データディレクトリ作成
            data_path = Path(self.settings.database.data_directory)
            data_path.mkdir(parents=True, exist_ok=True)
            
            # ログディレクトリ作成
            log_path = data_path / "logs"
            log_path.mkdir(exist_ok=True)
            
            # ログ管理システム初期化
            self.logger = ProjectLogger(log_dir=str(log_path))
            
            # Python標準ログレベル設定
            log_level = getattr(logging, self.settings.logging.level, logging.INFO)
            logging.getLogger().setLevel(log_level)
            
            self.logger.info(
                LogCategory.SYSTEM,
                "アプリケーション初期化開始",
                module="main",
                config_file=config_file,
                data_dir=str(data_path)
            )
            
            # プロジェクト管理システム初期化
            self.pms = ProjectManagementSystem(data_dir=str(data_path))
            
            # 通知サービス初期化
            self.notification_service = NotificationService()
            self.notification_service.set_project_management_system(self.pms)
            
            # 通知設定を適用
            self.notification_service.update_settings(**vars(self.settings.notifications))
            
            # データ整合性チェック
            if not self.pms.validate_data_integrity():
                self.logger.warning(
                    LogCategory.DATA,
                    "データ整合性の問題が検出されました",
                    module="main"
                )
                
                # 孤立データクリーンアップ
                cleanup_result = self.pms.cleanup_orphaned_data()
                if any(cleanup_result.values()):
                    self.logger.info(
                        LogCategory.DATA,
                        f"孤立データをクリーンアップしました: {cleanup_result}",
                        module="main"
                    )
            
            self.is_initialized = True
            
            # 初期化完了ログ
            stats = self.pms.get_system_statistics()
            self.logger.info(
                LogCategory.SYSTEM,
                f"初期化完了 - Projects: {stats['projects']['total']}, "
                f"Phases: {stats['phases']['total']}, "
                f"Processes: {stats['processes']['total']}, "
                f"Tasks: {stats['tasks']['total']}",
                module="main",
                statistics=stats
            )
            
            print("初期化が完了しました。")
            return True
            
        except Exception as e:
            error_msg = f"初期化エラー: {e}"
            print(error_msg)
            
            if self.logger:
                self.logger.critical(
                    LogCategory.SYSTEM,
                    error_msg,
                    module="main",
                    exception=e
                )
            
            self.error_handler.handle_error(
                SystemError(error_msg, component="ApplicationManager", original_exception=e)
            )
            
            return False
    
    def start_background_services(self) -> None:
        """バックグラウンドサービスを開始"""
        if not self.is_initialized or not self.notification_service:
            return
        
        try:
            # 通知サービス開始
            if self.settings.notifications.enabled:
                success = self.notification_service.start_background_service()
                if success:
                    self.logger.info(
                        LogCategory.SYSTEM,
                        "バックグラウンド通知サービス開始",
                        module="main"
                    )
                else:
                    self.logger.warning(
                        LogCategory.SYSTEM,
                        "バックグラウンド通知サービス開始に失敗",
                        module="main"
                    )
        
        except Exception as e:
            self.logger.error(
                LogCategory.SYSTEM,
                f"バックグラウンドサービス開始エラー: {e}",
                module="main",
                exception=e
            )
    
    def stop_background_services(self) -> None:
        """バックグラウンドサービスを停止"""
        if not self.is_initialized or not self.notification_service:
            return
        
        try:
            # 通知サービス停止
            success = self.notification_service.stop_background_service()
            if success:
                self.logger.info(
                    LogCategory.SYSTEM,
                    "バックグラウンド通知サービス停止",
                    module="main"
                )
        
        except Exception as e:
            self.logger.error(
                LogCategory.SYSTEM,
                f"バックグラウンドサービス停止エラー: {e}",
                module="main",
                exception=e
            )
    
    def run_cli(self) -> int:
        """
        CLIモードでアプリケーションを実行
        
        Returns:
            終了コード
        """
        try:
            from cli.cli_interface import CLIInterface
            
            cli = CLIInterface(self.pms, self.notification_service)
            return cli.run()
            
        except ImportError:
            print("CLIインターフェースが利用できません")
            return 1
        except Exception as e:
            if self.logger:
                self.logger.error(
                    LogCategory.SYSTEM,
                    f"CLI実行エラー: {e}",
                    module="main",
                    exception=e
                )
            print(f"CLI実行エラー: {e}")
            return 1
    
    def run_gui(self) -> int:
        """
        GUIモードでアプリケーションを実行
        
        Returns:
            終了コード
        """
        try:
            print("GUIモードは現在開発中です。CLIモードを使用してください。")
            return self.run_cli()
            
        except Exception as e:
            if self.logger:
                self.logger.error(
                    LogCategory.SYSTEM,
                    f"GUI実行エラー: {e}",
                    module="main",
                    exception=e
                )
            print(f"GUI実行エラー: {e}")
            return 1
    
    def shutdown(self) -> None:
        """アプリケーションを終了"""
        if not self.is_initialized:
            return
        
        try:
            if self.logger:
                self.logger.info(
                    LogCategory.SYSTEM,
                    "アプリケーション終了処理開始",
                    module="main"
                )
            
            # バックグラウンドサービス停止
            self.stop_background_services()
            
            # エラー統計出力
            if self.error_handler:
                error_stats = self.error_handler.get_error_statistics()
                if error_stats['total_errors'] > 0:
                    print(f"セッション中のエラー: {error_stats['total_errors']}件")
                    
                    if self.logger:
                        self.logger.info(
                            LogCategory.SYSTEM,
                            "セッション終了時エラー統計",
                            module="main",
                            error_statistics=error_stats
                        )
            
            if self.logger:
                self.logger.info(
                    LogCategory.SYSTEM,
                    "アプリケーション終了",
                    module="main"
                )
            
            print("プロジェクト管理システムを終了しました。")
            
        except Exception as e:
            print(f"終了処理エラー: {e}")
    
    def __enter__(self):
        """コンテキストマネージャー開始"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー終了"""
        self.shutdown()


def create_argument_parser() -> argparse.ArgumentParser:
    """コマンドライン引数パーサーを作成"""
    parser = argparse.ArgumentParser(
        description="プロジェクト管理システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  %(prog)s                    # CLIモードで起動
  %(prog)s --gui              # GUIモードで起動
  %(prog)s --config custom.json --data-dir /path/to/data
  %(prog)s --check-only       # データ整合性チェックのみ実行
  %(prog)s --version          # バージョン情報を表示
        """
    )
    
    parser.add_argument(
        '--gui',
        action='store_true',
        help='GUIモードで起動（デフォルト: CLI）'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        metavar='FILE',
        help='設定ファイルパス（デフォルト: data/settings.json）'
    )
    
    parser.add_argument(
        '--data-dir',
        type=str,
        metavar='DIR',
        help='データディレクトリパス（デフォルト: data）'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='ログレベルを指定'
    )
    
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='データ整合性チェックのみ実行して終了'
    )
    
    parser.add_argument(
        '--no-background',
        action='store_true',
        help='バックグラウンドサービスを無効化'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    return parser


def check_environment() -> bool:
    """実行環境をチェック"""
    try:
        # Python バージョンチェック
        if sys.version_info < (3, 7):
            print("エラー: Python 3.7以上が必要です")
            return False
        
        # 書き込み権限チェック
        test_file = Path("data") / "test_write.tmp"
        try:
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text("test")
            test_file.unlink()
        except (OSError, PermissionError):
            print("エラー: データディレクトリへの書き込み権限がありません")
            return False
        
        return True
        
    except Exception as e:
        print(f"環境チェックエラー: {e}")
        return False


def main() -> int:
    """メイン関数"""
    try:
        # 環境チェック
        if not check_environment():
            return 1
        
        # 引数解析
        parser = create_argument_parser()
        args = parser.parse_args()
        
        # アプリケーション管理者でコンテキスト管理
        with ApplicationManager() as app:
            # 初期化
            if not app.initialize(
                config_file=args.config,
                data_dir=args.data_dir
            ):
                return 1
            
            # ログレベル上書き
            if args.log_level and app.logger:
                app.settings.logging.level = args.log_level
                log_level = getattr(logging, args.log_level)
                logging.getLogger().setLevel(log_level)
            
            # データチェックのみモード
            if args.check_only:
                print("データ整合性をチェックしています...")
                
                is_valid = app.pms.validate_data_integrity()
                if is_valid:
                    print("データ整合性: OK")
                    return 0
                else:
                    print("データ整合性: エラーが検出されました")
                    return 1
            
            # バックグラウンドサービス開始
            if not args.no_background:
                app.start_background_services()
            
            # モード選択して実行
            if args.gui:
                return app.run_gui()
            else:
                return app.run_cli()
    
    except KeyboardInterrupt:
        print("\n\nプログラムが中断されました")
        return 0
    
    except Exception as e:
        print(f"予期しないエラー: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())