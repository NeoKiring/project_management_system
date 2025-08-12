"""
CLIインターフェース
対話式コマンドラインインターフェース
"""

import sys
import os
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
import traceback

try:
    from ..core.manager import ProjectManagementSystem
    from ..core.notification_manager import NotificationService
    from ..models.base import ProjectStatus, TaskStatus
    from ..models.notification import NotificationType, NotificationPriority
    from ..core.logger import LogCategory
    from ..core.error_handler import handle_errors, RecoveryStrategy
except ImportError:
    # 直接実行時の相対インポート対応
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from core.manager import ProjectManagementSystem
    from core.notification_manager import NotificationService
    from models.base import ProjectStatus, TaskStatus
    from models.notification import NotificationType, NotificationPriority
    from core.logger import LogCategory
    from core.error_handler import handle_errors, RecoveryStrategy


class CLIInterface:
    """
    コマンドラインインターフェース
    対話式メニューシステム
    """
    
    def __init__(self, pms: ProjectManagementSystem, notification_service: NotificationService):
        """
        CLIインターフェースの初期化
        
        Args:
            pms: プロジェクト管理システム
            notification_service: 通知サービス
        """
        self.pms = pms
        self.notification_service = notification_service
        self.logger = pms.logger
        
        # CLI状態管理
        self.current_project_id: Optional[str] = None
        self.current_phase_id: Optional[str] = None
        self.current_process_id: Optional[str] = None
        self.running = True
        
        # コマンド履歴
        self.command_history: List[str] = []
        
        # 表示設定
        self.page_size = 20
        self.show_details = False
        
        self.logger.info(
            LogCategory.SYSTEM,
            "CLIインターフェース初期化",
            module="cli.cli_interface"
        )
    
    def run(self) -> int:
        """
        CLIインターフェースを実行
        
        Returns:
            終了コード
        """
        try:
            self._show_welcome()
            self._show_help()
            
            while self.running:
                try:
                    command = self._get_user_input()
                    if command:
                        self.command_history.append(command)
                        self._execute_command(command)
                
                except KeyboardInterrupt:
                    print("\n操作が中断されました")
                    if self._confirm("終了しますか？"):
                        break
                except EOFError:
                    print("\n")
                    break
                except Exception as e:
                    print(f"エラー: {e}")
                    self.logger.error(
                        LogCategory.ERROR,
                        f"CLI実行エラー: {e}",
                        module="cli.cli_interface",
                        exception=e
                    )
            
            print("CLIを終了します。")
            return 0
            
        except Exception as e:
            print(f"重大なエラー: {e}")
            self.logger.critical(
                LogCategory.ERROR,
                f"CLI重大エラー: {e}",
                module="cli.cli_interface",
                exception=e
            )
            return 1
    
    def _show_welcome(self) -> None:
        """ウェルカムメッセージを表示"""
        print("=" * 60)
        print("プロジェクト管理システム CLI")
        print("=" * 60)
        
        # システム統計表示
        stats = self.pms.get_system_statistics()
        print(f"Projects: {stats['projects']['total']} | "
              f"Phases: {stats['phases']['total']} | "
              f"Processes: {stats['processes']['total']} | "
              f"Tasks: {stats['tasks']['total']}")
        
        # 通知統計表示
        notifications = self.notification_service.get_notifications({'status': 'active'})
        if notifications:
            print(f"🔔 アクティブ通知: {len(notifications)}件")
        
        print()
    
    def _show_help(self) -> None:
        """ヘルプメッセージを表示"""
        print("主要コマンド:")
        print("  help, h          - ヘルプを表示")
        print("  projects, p      - プロジェクト一覧")
        print("  create-project   - プロジェクト作成")
        print("  select <ID>      - プロジェクト選択")
        print("  phases           - フェーズ一覧（プロジェクト選択時）")
        print("  processes        - プロセス一覧（フェーズ選択時）")
        print("  tasks            - タスク一覧（プロセス選択時）")
        print("  status           - システム状態表示")
        print("  notifications, n - 通知管理")
        print("  settings         - 設定管理")
        print("  sample-data      - サンプルデータ作成")
        print("  exit, quit, q    - 終了")
        print()
    
    def _get_user_input(self) -> str:
        """ユーザー入力を取得"""
        # プロンプト表示
        prompt_parts = ["PM"]
        
        if self.current_project_id:
            project = self.pms.get_project(self.current_project_id)
            if project:
                prompt_parts.append(f"P:{project.name[:10]}")
        
        if self.current_phase_id:
            phase = self.pms.get_phase(self.current_phase_id)
            if phase:
                prompt_parts.append(f"Ph:{phase.name[:8]}")
        
        if self.current_process_id:
            process = self.pms.get_process(self.current_process_id)
            if process:
                prompt_parts.append(f"Pr:{process.name[:8]}")
        
        prompt = "[" + "|".join(prompt_parts) + "]> "
        return input(prompt).strip()
    
    @handle_errors(recovery_strategy=RecoveryStrategy.IGNORE)
    def _execute_command(self, command: str) -> None:
        """コマンドを実行"""
        if not command:
            return
        
        parts = command.lower().split()
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        # コマンド実行
        if cmd in ['help', 'h']:
            self._show_help()
        elif cmd in ['exit', 'quit', 'q']:
            self.running = False
        elif cmd in ['projects', 'p']:
            self._list_projects()
        elif cmd == 'create-project':
            self._create_project()
        elif cmd == 'select':
            self._select_project(args)
        elif cmd == 'phases':
            self._list_phases()
        elif cmd == 'create-phase':
            self._create_phase()
        elif cmd == 'select-phase':
            self._select_phase(args)
        elif cmd == 'processes':
            self._list_processes()
        elif cmd == 'create-process':
            self._create_process()
        elif cmd == 'select-process':
            self._select_process(args)
        elif cmd == 'tasks':
            self._list_tasks()
        elif cmd == 'create-task':
            self._create_task()
        elif cmd == 'update-task':
            self._update_task_status(args)
        elif cmd == 'status':
            self._show_system_status()
        elif cmd in ['notifications', 'n']:
            self._manage_notifications()
        elif cmd == 'settings':
            self._manage_settings()
        elif cmd == 'sample-data':
            self._create_sample_data()
        elif cmd == 'clear':
            os.system('cls' if os.name == 'nt' else 'clear')
        elif cmd == 'back':
            self._go_back()
        else:
            print(f"不明なコマンド: {command}")
            print("'help' でコマンド一覧を表示")
    
    # ==================== プロジェクト管理 ====================
    
    def _list_projects(self) -> None:
        """プロジェクト一覧を表示"""
        projects = self.pms.get_all_projects()
        
        if not projects:
            print("プロジェクトがありません。'create-project' で作成してください。")
            return
        
        print("\n=== プロジェクト一覧 ===")
        for i, project in enumerate(projects):
            status_mark = self._get_status_mark(project.status)
            print(f"{i+1:2d}. [{project.id[:8]}] {status_mark} {project.name}")
            print(f"     進捗: {project.progress:.1f}% | "
                  f"フェーズ: {len(project.phases)}個 | "
                  f"マネージャー: {project.manager or '未設定'}")
            
            if project.end_date:
                remaining = project.get_remaining_days()
                if remaining is not None:
                    if remaining < 0:
                        print(f"     期限: {project.end_date} (期限超過: {abs(remaining)}日)")
                    else:
                        print(f"     期限: {project.end_date} (残り: {remaining}日)")
            print()
    
    def _create_project(self) -> None:
        """プロジェクト作成"""
        print("\n=== プロジェクト作成 ===")
        
        name = input("プロジェクト名: ").strip()
        if not name:
            print("プロジェクト名は必須です")
            return
        
        description = input("説明（任意）: ").strip()
        manager = input("マネージャー（任意）: ").strip()
        
        try:
            project = self.pms.create_project(name, description, manager)
            print(f"✓ プロジェクト '{project.name}' を作成しました (ID: {project.id[:8]})")
            
            # 開始日・終了日設定
            if self._confirm("開始日・終了日を設定しますか？"):
                self._set_project_dates(project)
            
            # 自動選択
            if self._confirm("このプロジェクトを選択しますか？"):
                self.current_project_id = project.id
                print(f"プロジェクト '{project.name}' を選択しました")
            
        except Exception as e:
            print(f"プロジェクト作成エラー: {e}")
    
    def _select_project(self, args: List[str]) -> None:
        """プロジェクト選択"""
        if not args:
            print("使用法: select <プロジェクトID または番号>")
            return
        
        projects = self.pms.get_all_projects()
        if not projects:
            print("プロジェクトがありません")
            return
        
        target = args[0]
        project = None
        
        # ID または番号で検索
        try:
            # 番号での選択
            if target.isdigit():
                index = int(target) - 1
                if 0 <= index < len(projects):
                    project = projects[index]
            else:
                # IDでの選択
                project = self.pms.get_project(target)
        except (ValueError, IndexError):
            pass
        
        if project:
            self.current_project_id = project.id
            self.current_phase_id = None
            self.current_process_id = None
            print(f"プロジェクト '{project.name}' を選択しました")
        else:
            print("プロジェクトが見つかりません")
    
    def _set_project_dates(self, project) -> None:
        """プロジェクトの日付設定"""
        try:
            start_date_str = input("開始日 (YYYY-MM-DD, 空白でスキップ): ").strip()
            end_date_str = input("終了日 (YYYY-MM-DD, 空白でスキップ): ").strip()
            
            start_date = None
            end_date = None
            
            if start_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            
            if end_date_str:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            
            if project.set_dates(start_date, end_date):
                self.pms.update_project(project)
                print("✓ 日付を設定しました")
            else:
                print("❌ 日付の設定に失敗しました")
                
        except ValueError:
            print("日付形式が正しくありません (YYYY-MM-DD)")
    
    # ==================== フェーズ管理 ====================
    
    def _list_phases(self) -> None:
        """フェーズ一覧を表示"""
        if not self.current_project_id:
            print("プロジェクトを選択してください")
            return
        
        project = self.pms.get_project(self.current_project_id)
        if not project:
            print("選択されたプロジェクトが見つかりません")
            return
        
        if not project.phases:
            print("フェーズがありません。'create-phase' で作成してください。")
            return
        
        print(f"\n=== フェーズ一覧 (プロジェクト: {project.name}) ===")
        for i, phase_id in enumerate(project.phases):
            phase = self.pms.get_phase(phase_id)
            if phase:
                status_mark = self._get_status_mark(phase.get_status())
                print(f"{i+1:2d}. [{phase.id[:8]}] {status_mark} {phase.name}")
                print(f"     進捗: {phase.progress:.1f}% | "
                      f"プロセス: {len(phase.processes)}個")
                if phase.end_date:
                    print(f"     期限: {phase.end_date}")
                print()
    
    def _create_phase(self) -> None:
        """フェーズ作成"""
        if not self.current_project_id:
            print("プロジェクトを選択してください")
            return
        
        print("\n=== フェーズ作成 ===")
        
        name = input("フェーズ名: ").strip()
        if not name:
            print("フェーズ名は必須です")
            return
        
        description = input("説明（任意）: ").strip()
        
        try:
            phase = self.pms.create_phase(name, self.current_project_id, description)
            print(f"✓ フェーズ '{phase.name}' を作成しました (ID: {phase.id[:8]})")
            
            # 自動選択
            if self._confirm("このフェーズを選択しますか？"):
                self.current_phase_id = phase.id
                print(f"フェーズ '{phase.name}' を選択しました")
            
        except Exception as e:
            print(f"フェーズ作成エラー: {e}")
    
    def _select_phase(self, args: List[str]) -> None:
        """フェーズ選択"""
        if not self.current_project_id:
            print("プロジェクトを選択してください")
            return
        
        if not args:
            print("使用法: select-phase <フェーズID または番号>")
            return
        
        project = self.pms.get_project(self.current_project_id)
        if not project or not project.phases:
            print("フェーズがありません")
            return
        
        target = args[0]
        phase = None
        
        try:
            if target.isdigit():
                index = int(target) - 1
                if 0 <= index < len(project.phases):
                    phase = self.pms.get_phase(project.phases[index])
            else:
                phase = self.pms.get_phase(target)
        except (ValueError, IndexError):
            pass
        
        if phase:
            self.current_phase_id = phase.id
            self.current_process_id = None
            print(f"フェーズ '{phase.name}' を選択しました")
        else:
            print("フェーズが見つかりません")
    
    # ==================== プロセス管理 ====================
    
    def _list_processes(self) -> None:
        """プロセス一覧を表示"""
        if not self.current_phase_id:
            print("フェーズを選択してください")
            return
        
        phase = self.pms.get_phase(self.current_phase_id)
        if not phase:
            print("選択されたフェーズが見つかりません")
            return
        
        if not phase.processes:
            print("プロセスがありません。'create-process' で作成してください。")
            return
        
        print(f"\n=== プロセス一覧 (フェーズ: {phase.name}) ===")
        for i, process_id in enumerate(phase.processes):
            process = self.pms.get_process(process_id)
            if process:
                status_mark = self._get_status_mark(process.get_status())
                print(f"{i+1:2d}. [{process.id[:8]}] {status_mark} {process.name}")
                print(f"     進捗: {process.progress:.1f}% | "
                      f"担当者: {process.assignee} | "
                      f"タスク: {len(process.tasks)}個")
                if process.end_date:
                    print(f"     期限: {process.end_date}")
                print()
    
    def _create_process(self) -> None:
        """プロセス作成"""
        if not self.current_phase_id:
            print("フェーズを選択してください")
            return
        
        print("\n=== プロセス作成 ===")
        
        name = input("プロセス名: ").strip()
        if not name:
            print("プロセス名は必須です")
            return
        
        assignee = input("担当者: ").strip()
        if not assignee:
            print("担当者は必須です")
            return
        
        description = input("説明（任意）: ").strip()
        
        try:
            process = self.pms.create_process(name, assignee, self.current_phase_id, description)
            print(f"✓ プロセス '{process.name}' を作成しました (ID: {process.id[:8]})")
            
            # 自動選択
            if self._confirm("このプロセスを選択しますか？"):
                self.current_process_id = process.id
                print(f"プロセス '{process.name}' を選択しました")
            
        except Exception as e:
            print(f"プロセス作成エラー: {e}")
    
    def _select_process(self, args: List[str]) -> None:
        """プロセス選択"""
        if not self.current_phase_id:
            print("フェーズを選択してください")
            return
        
        if not args:
            print("使用法: select-process <プロセスID または番号>")
            return
        
        phase = self.pms.get_phase(self.current_phase_id)
        if not phase or not phase.processes:
            print("プロセスがありません")
            return
        
        target = args[0]
        process = None
        
        try:
            if target.isdigit():
                index = int(target) - 1
                if 0 <= index < len(phase.processes):
                    process = self.pms.get_process(phase.processes[index])
            else:
                process = self.pms.get_process(target)
        except (ValueError, IndexError):
            pass
        
        if process:
            self.current_process_id = process.id
            print(f"プロセス '{process.name}' を選択しました")
        else:
            print("プロセスが見つかりません")
    
    # ==================== タスク管理 ====================
    
    def _list_tasks(self) -> None:
        """タスク一覧を表示"""
        if not self.current_process_id:
            print("プロセスを選択してください")
            return
        
        process = self.pms.get_process(self.current_process_id)
        if not process:
            print("選択されたプロセスが見つかりません")
            return
        
        if not process.tasks:
            print("タスクがありません。'create-task' で作成してください。")
            return
        
        print(f"\n=== タスク一覧 (プロセス: {process.name}) ===")
        for i, task_id in enumerate(process.tasks):
            task = self.pms.get_task(task_id)
            if task:
                status_mark = self._get_status_mark(task.status)
                priority_mark = "🔥" if task.priority <= 2 else "🔸" if task.priority == 3 else "🔹"
                
                print(f"{i+1:2d}. [{task.id[:8]}] {status_mark} {priority_mark} {task.name}")
                print(f"     ステータス: {task.status} | 優先度: {task.priority}")
                
                if task.estimated_hours or task.actual_hours:
                    estimated = f"{task.estimated_hours:.1f}h" if task.estimated_hours else "未設定"
                    actual = f"{task.actual_hours:.1f}h" if task.actual_hours else "未設定"
                    print(f"     工数: 予想={estimated}, 実績={actual}")
                
                print()
    
    def _create_task(self) -> None:
        """タスク作成"""
        if not self.current_process_id:
            print("プロセスを選択してください")
            return
        
        print("\n=== タスク作成 ===")
        
        name = input("タスク名: ").strip()
        if not name:
            print("タスク名は必須です")
            return
        
        description = input("説明（任意）: ").strip()
        
        try:
            task = self.pms.create_task(name, self.current_process_id, description)
            print(f"✓ タスク '{task.name}' を作成しました (ID: {task.id[:8]})")
            
            # 優先度設定
            if self._confirm("優先度を設定しますか？ (1:高 - 5:低)"):
                try:
                    priority = int(input("優先度 (1-5): "))
                    if task.set_priority(priority):
                        self.pms.task_manager.update_task(task)
                        print(f"✓ 優先度を {priority} に設定しました")
                except ValueError:
                    print("優先度は1-5の数値で入力してください")
            
        except Exception as e:
            print(f"タスク作成エラー: {e}")
    
    def _update_task_status(self, args: List[str]) -> None:
        """タスクステータス更新"""
        if not self.current_process_id:
            print("プロセスを選択してください")
            return
        
        if not args:
            print("使用法: update-task <タスク番号> [新ステータス]")
            print("ステータス: 未着手, 進行中, 完了, 対応不能")
            return
        
        process = self.pms.get_process(self.current_process_id)
        if not process or not process.tasks:
            print("タスクがありません")
            return
        
        try:
            task_index = int(args[0]) - 1
            if not (0 <= task_index < len(process.tasks)):
                print("無効なタスク番号です")
                return
            
            task = self.pms.get_task(process.tasks[task_index])
            if not task:
                print("タスクが見つかりません")
                return
            
            # 新ステータス取得
            if len(args) > 1:
                new_status = args[1]
            else:
                print(f"現在のステータス: {task.status}")
                print("新しいステータス: 1)未着手 2)進行中 3)完了 4)対応不能")
                choice = input("選択 (1-4): ").strip()
                
                status_map = {
                    '1': TaskStatus.NOT_STARTED,
                    '2': TaskStatus.IN_PROGRESS,
                    '3': TaskStatus.COMPLETED,
                    '4': TaskStatus.CANNOT_HANDLE
                }
                
                new_status = status_map.get(choice)
                if not new_status:
                    print("無効な選択です")
                    return
            
            comment = input("変更コメント（任意）: ").strip()
            
            if self.pms.update_task_status(task.id, new_status, comment):
                print(f"✓ タスク '{task.name}' のステータスを '{new_status}' に更新しました")
            else:
                print("❌ ステータス更新に失敗しました")
            
        except (ValueError, IndexError):
            print("無効な引数です")
    
    # ==================== システム状態・統計 ====================
    
    def _show_system_status(self) -> None:
        """システム状態を表示"""
        print("\n=== システム状態 ===")
        
        # 基本統計
        stats = self.pms.get_system_statistics()
        print(f"プロジェクト数: {stats['projects']['total']}")
        print(f"フェーズ数: {stats['phases']['total']}")
        print(f"プロセス数: {stats['processes']['total']}")
        print(f"タスク数: {stats['tasks']['total']}")
        print()
        
        # プロジェクト統計
        if stats['projects']['total'] > 0:
            project_stats = stats['projects']
            print("=== プロジェクト統計 ===")
            print(f"完了率: {project_stats.get('completion_rate', 0):.1f}%")
            print(f"期限超過: {project_stats.get('overdue', 0)}件")
            
            # ステータス別
            status_counts = project_stats.get('status_counts', {})
            for status, count in status_counts.items():
                print(f"  {status}: {count}件")
            print()
        
        # 通知統計
        notification_summary = self.notification_service.get_notification_summary()
        notification_counts = notification_summary.get('notification_counts', {})
        total_notifications = notification_counts.get('total', 0)
        
        print("=== 通知統計 ===")
        print(f"総通知数: {total_notifications}")
        
        if total_notifications > 0:
            status_counts = notification_counts.get('status_counts', {})
            print(f"  未読: {status_counts.get('unread', 0)}件")
            print(f"  アクティブ: {status_counts.get('active', 0)}件")
            
            # 通知タイプ別
            type_counts = notification_counts.get('type_counts', {})
            for ntype, count in type_counts.items():
                print(f"  {ntype}: {count}件")
        print()
        
        # データ整合性
        is_valid = self.pms.validate_data_integrity()
        print(f"データ整合性: {'✓ OK' if is_valid else '❌ エラー'}")
    
    # ==================== 通知管理 ====================
    
    def _manage_notifications(self) -> None:
        """通知管理メニュー"""
        while True:
            print("\n=== 通知管理 ===")
            print("1. 通知一覧表示")
            print("2. 未読通知表示")
            print("3. 通知チェック実行")
            print("4. 通知設定確認")
            print("5. 戻る")
            
            choice = input("選択 (1-5): ").strip()
            
            if choice == '1':
                self._show_all_notifications()
            elif choice == '2':
                self._show_unread_notifications()
            elif choice == '3':
                self._check_notifications()
            elif choice == '4':
                self._show_notification_settings()
            elif choice == '5':
                break
            else:
                print("無効な選択です")
    
    def _show_all_notifications(self) -> None:
        """全通知を表示"""
        notifications = self.notification_service.get_notifications({'limit': 20})
        
        if not notifications:
            print("通知がありません")
            return
        
        print(f"\n=== 通知一覧 (最新{len(notifications)}件) ===")
        for i, notification in enumerate(notifications):
            status_mark = "🔔" if not notification.is_read() else "📖"
            priority_mark = "🔥" if notification.priority == NotificationPriority.HIGH else "🔸"
            
            print(f"{i+1:2d}. {status_mark} {priority_mark} [{notification.type}] {notification.entity_name}")
            print(f"     {notification.message}")
            print(f"     作成: {notification.created_at.strftime('%Y-%m-%d %H:%M')}")
            print()
    
    def _show_unread_notifications(self) -> None:
        """未読通知を表示"""
        notifications = self.notification_service.get_notifications({'status': 'unread'})
        
        if not notifications:
            print("未読通知はありません")
            return
        
        print(f"\n=== 未読通知 ({len(notifications)}件) ===")
        for i, notification in enumerate(notifications):
            priority_mark = "🔥" if notification.priority == NotificationPriority.HIGH else "🔸"
            
            print(f"{i+1:2d}. {priority_mark} [{notification.type}] {notification.entity_name}")
            print(f"     {notification.message}")
            print(f"     作成: {notification.created_at.strftime('%Y-%m-%d %H:%M')}")
            print()
        
        if self._confirm("全て既読にしますか？"):
            notification_ids = [n.id for n in notifications]
            count = self.notification_service.bulk_mark_as_read(notification_ids)
            print(f"✓ {count}件の通知を既読にしました")
    
    def _check_notifications(self) -> None:
        """通知チェックを実行"""
        print("通知チェックを実行しています...")
        count = self.notification_service.check_and_generate_notifications()
        print(f"✓ 通知チェック完了: {count}件の新規通知を生成")
    
    def _show_notification_settings(self) -> None:
        """通知設定を表示"""
        settings = self.notification_service.get_settings()
        
        print("\n=== 通知設定 ===")
        print(f"期限警告日数: {settings['deadline_warning_days']}日")
        print(f"進捗遅延しきい値: {settings['progress_delay_threshold']}%")
        print(f"チェック間隔: {settings['check_interval_hours']}時間")
        print(f"保持期間: {settings['retention_days']}日")
        print()
        
        print("有効な通知タイプ:")
        for ntype, enabled in settings['enabled_types'].items():
            status = "✓" if enabled else "✗"
            print(f"  {status} {ntype}")
    
    # ==================== 設定管理 ====================
    
    def _manage_settings(self) -> None:
        """設定管理メニュー"""
        print("\n=== 設定管理 ===")
        print("1. システム情報表示")
        print("2. ログ設定表示")
        print("3. データベース設定表示")
        print("4. 設定バックアップ作成")
        
        choice = input("選択 (1-4, 空白で戻る): ").strip()
        
        if choice == '1':
            self._show_system_info()
        elif choice == '2':
            self._show_log_settings()
        elif choice == '3':
            self._show_database_settings()
        elif choice == '4':
            self._create_settings_backup()
    
    def _show_system_info(self) -> None:
        """システム情報を表示"""
        settings = self.pms.settings if hasattr(self.pms, 'settings') else None
        
        print("\n=== システム情報 ===")
        print(f"Python: {sys.version}")
        print(f"データディレクトリ: {self.pms.data_store.data_dir}")
        
        if settings:
            print(f"設定ファイル: {settings.config_file}")
            print(f"バージョン: {settings.system_info.get('version', '1.0.0')}")
    
    def _show_log_settings(self) -> None:
        """ログ設定を表示"""
        print("\n=== ログ設定 ===")
        # ログ統計を表示
        log_stats = self.logger.get_statistics()
        print(f"総ログエントリ: {log_stats.get('total_entries', 0)}")
        print(f"エラー数: {log_stats.get('error_count', 0)}")
        print(f"エラー率: {log_stats.get('error_rate', 0):.2f}%")
    
    def _show_database_settings(self) -> None:
        """データベース設定を表示"""
        print("\n=== データベース設定 ===")
        data_stats = self.pms.data_store.get_data_statistics()
        
        print("ファイルサイズ:")
        for name, size in data_stats.get('file_sizes', {}).items():
            print(f"  {name}: {size:,} bytes")
        
        print(f"総サイズ: {data_stats.get('total_size', 0):,} bytes")
    
    def _create_settings_backup(self) -> None:
        """設定バックアップを作成"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"settings_backup_{timestamp}.json"
            
            # 設定エクスポート（設定管理システムがある場合）
            if hasattr(self.pms, 'settings'):
                if self.pms.settings.export_settings(backup_file):
                    print(f"✓ 設定バックアップを作成しました: {backup_file}")
                else:
                    print("❌ 設定バックアップの作成に失敗しました")
            else:
                print("設定管理システムが利用できません")
                
        except Exception as e:
            print(f"バックアップ作成エラー: {e}")
    
    # ==================== サンプルデータ ====================
    
    def _create_sample_data(self) -> None:
        """サンプルデータを作成"""
        print("\n=== サンプルデータ作成 ===")
        
        if not self._confirm("サンプルデータを作成しますか？"):
            return
        
        try:
            # サンプルプロジェクト作成
            project = self.pms.create_project(
                "サンプル Web システム開発",
                "ECサイトのリニューアルプロジェクト",
                "山田太郎"
            )
            
            # 開始日・終了日設定
            import datetime as dt
            today = dt.date.today()
            project.set_dates(today, today + dt.timedelta(days=90))
            self.pms.update_project(project)
            
            # フェーズ作成
            phase1 = self.pms.create_phase("要件定義・設計", project.id, "システム要件の整理と基本設計")
            phase2 = self.pms.create_phase("開発・テスト", project.id, "実装とテストの実行")
            phase3 = self.pms.create_phase("リリース・運用", project.id, "本番リリースと運用開始")
            
            # プロセス作成（フェーズ1）
            process1_1 = self.pms.create_process("要件整理", "佐藤次郎", phase1.id, "ユーザー要件の整理")
            process1_2 = self.pms.create_process("画面設計", "鈴木花子", phase1.id, "画面仕様の作成")
            
            # プロセス作成（フェーズ2）
            process2_1 = self.pms.create_process("バックエンド開発", "田中一郎", phase2.id, "サーバーサイド機能の実装")
            process2_2 = self.pms.create_process("フロントエンド開発", "高橋美咲", phase2.id, "ユーザーインターフェースの実装")
            
            # タスク作成
            task1 = self.pms.create_task("ユーザーヒアリング", process1_1.id, "現行システムの課題整理")
            task2 = self.pms.create_task("機能要件定義", process1_1.id, "新システムの機能要件")
            task3 = self.pms.create_task("ワイヤーフレーム作成", process1_2.id, "画面レイアウトの検討")
            task4 = self.pms.create_task("API設計", process2_1.id, "RESTful API の設計")
            task5 = self.pms.create_task("データベース設計", process2_1.id, "テーブル設計とER図作成")
            
            # 一部タスクのステータス更新
            self.pms.update_task_status(task1.id, TaskStatus.COMPLETED)
            self.pms.update_task_status(task2.id, TaskStatus.IN_PROGRESS)
            self.pms.update_task_status(task3.id, TaskStatus.IN_PROGRESS)
            
            # 工数設定
            task1.set_estimated_hours(8.0)
            task1.set_actual_hours(6.5)
            task2.set_estimated_hours(16.0)
            task2.set_actual_hours(12.0)
            task3.set_estimated_hours(12.0)
            task4.set_estimated_hours(20.0)
            task5.set_estimated_hours(24.0)
            
            # 優先度設定
            task1.set_priority(2)
            task2.set_priority(1)
            task3.set_priority(2)
            task4.set_priority(3)
            task5.set_priority(1)
            
            self.pms.task_manager.update_task(task1)
            self.pms.task_manager.update_task(task2)
            self.pms.task_manager.update_task(task3)
            self.pms.task_manager.update_task(task4)
            self.pms.task_manager.update_task(task5)
            
            print("✓ サンプルデータを作成しました")
            print(f"  プロジェクト: {project.name}")
            print(f"  フェーズ: 3個")
            print(f"  プロセス: 4個")
            print(f"  タスク: 5個")
            
            # 自動選択
            if self._confirm("作成したプロジェクトを選択しますか？"):
                self.current_project_id = project.id
                print(f"プロジェクト '{project.name}' を選択しました")
            
        except Exception as e:
            print(f"サンプルデータ作成エラー: {e}")
            self.logger.error(
                LogCategory.ERROR,
                f"サンプルデータ作成エラー: {e}",
                module="cli.cli_interface",
                exception=e
            )
    
    # ==================== ユーティリティ ====================
    
    def _get_status_mark(self, status: str) -> str:
        """ステータスマークを取得"""
        status_marks = {
            ProjectStatus.NOT_STARTED: "⚪",
            ProjectStatus.IN_PROGRESS: "🔄",
            ProjectStatus.COMPLETED: "✅",
            ProjectStatus.SUSPENDED: "⏸️",
            ProjectStatus.ON_HOLD: "⏸️",
            TaskStatus.NOT_STARTED: "⚪",
            TaskStatus.IN_PROGRESS: "🔄",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.CANNOT_HANDLE: "❌",
            "未着手": "⚪",
            "進行中": "🔄",
            "完了": "✅"
        }
        return status_marks.get(status, "❓")
    
    def _confirm(self, message: str) -> bool:
        """確認ダイアログ"""
        while True:
            response = input(f"{message} (y/n): ").strip().lower()
            if response in ['y', 'yes', 'はい']:
                return True
            elif response in ['n', 'no', 'いいえ']:
                return False
            else:
                print("y(はい) または n(いいえ) で入力してください")
    
    def _go_back(self) -> None:
        """階層を戻る"""
        if self.current_process_id:
            self.current_process_id = None
            print("プロセス選択を解除しました")
        elif self.current_phase_id:
            self.current_phase_id = None
            print("フェーズ選択を解除しました")
        elif self.current_project_id:
            self.current_project_id = None
            print("プロジェクト選択を解除しました")
        else:
            print("既にトップレベルです")
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"CLIInterface(project={self.current_project_id[:8] if self.current_project_id else None})"