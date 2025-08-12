"""
プロジェクト管理統合機能
全エンティティの統合管理・自動進捗更新・データ整合性保証
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date

from ..models.project import Project, ProjectManager
from ..models.phase import Phase, PhaseManager
from ..models.process import Process, ProcessManager
from ..models.task import Task, TaskManager
from ..models.notification import Notification, NotificationManager, NotificationGenerator
from ..storage.data_store import DataStore
from ..core.logger import ProjectLogger, LogCategory, AuditAction
from ..core.error_handler import (
    handle_errors, validate_input, business_rule, 
    BusinessLogicError, DataError, RecoveryStrategy
)


class ProjectManagementSystem:
    """
    プロジェクト管理システム統合クラス
    全エンティティの管理と業務ロジックの統合制御
    """
    
    def __init__(self, data_dir: str = None):
        """
        システムの初期化
        
        Args:
            data_dir: データディレクトリパス
        """
        # データストア初期化
        self.data_store = DataStore(data_dir)
        
        # ログ・エラーハンドリング
        self.logger = ProjectLogger()
        
        # 各エンティティ管理者
        self.project_manager = ProjectManager()
        self.phase_manager = PhaseManager()
        self.process_manager = ProcessManager()
        self.task_manager = TaskManager()
        self.notification_manager = NotificationManager()
        
        # 通知生成エンジン
        self.notification_generator = NotificationGenerator()
        
        # データ読み込み
        self._load_all_data()
        
        self.logger.info(
            LogCategory.SYSTEM,
            "プロジェクト管理システムが初期化されました",
            module="core.manager"
        )
    
    def _load_all_data(self) -> None:
        """全データを読み込み"""
        try:
            # プロジェクトデータ読み込み
            projects_data = self.data_store.load_projects()
            for project_id, project_data in projects_data.items():
                project = Project.from_dict(project_data)
                self.project_manager.projects[project_id] = project
            
            # フェーズデータ読み込み
            phases_data = self.data_store.load_phases()
            for phase_id, phase_data in phases_data.items():
                phase = Phase.from_dict(phase_data)
                self.phase_manager.phases[phase_id] = phase
            
            # プロセスデータ読み込み
            processes_data = self.data_store.load_processes()
            for process_id, process_data in processes_data.items():
                process = Process.from_dict(process_data)
                self.process_manager.processes[process_id] = process
            
            # タスクデータ読み込み
            tasks_data = self.data_store.load_tasks()
            for task_id, task_data in tasks_data.items():
                task = Task.from_dict(task_data)
                self.task_manager.tasks[task_id] = task
            
            # 通知データ読み込み
            notifications_data = self.data_store.load_notifications()
            for notification_id, notification_data in notifications_data.items():
                notification = Notification.from_dict(notification_data)
                self.notification_manager.notifications[notification_id] = notification
            
            self.logger.info(
                LogCategory.DATA,
                f"データ読み込み完了: Projects={len(self.project_manager.projects)}, "
                f"Phases={len(self.phase_manager.phases)}, "
                f"Processes={len(self.process_manager.processes)}, "
                f"Tasks={len(self.task_manager.tasks)}, "
                f"Notifications={len(self.notification_manager.notifications)}",
                module="core.manager"
            )
            
        except Exception as e:
            self.logger.error(
                LogCategory.DATA,
                f"データ読み込みエラー: {e}",
                module="core.manager",
                exception=e
            )
            raise DataError(f"データ読み込みに失敗しました: {e}", original_exception=e)
    
    # ==================== プロジェクト管理 ====================
    
    @handle_errors(recovery_strategy=RecoveryStrategy.NONE)
    @validate_input()
    def create_project(self, name: str, description: str = "", manager: str = "") -> Project:
        """
        新しいプロジェクトを作成
        
        Args:
            name: プロジェクト名
            description: プロジェクト説明
            manager: プロジェクトマネージャー
            
        Returns:
            作成されたプロジェクト
        """
        project = self.project_manager.create_project(name, description, manager)
        
        # データ永続化
        self.data_store.save_project(project.id, project.to_dict())
        
        # 監査ログ
        self.logger.audit(
            AuditAction.CREATE,
            "Project",
            project.id,
            project.name,
            f"プロジェクト作成: {description}"
        )
        
        self.logger.info(
            LogCategory.USER,
            f"プロジェクト作成: {project.name}",
            module="core.manager",
            project_id=project.id
        )
        
        return project
    
    @handle_errors(recovery_strategy=RecoveryStrategy.NONE)
    def update_project(self, project: Project) -> bool:
        """
        プロジェクトを更新
        
        Args:
            project: 更新するプロジェクト
            
        Returns:
            更新成功の可否
        """
        if not project.validate():
            raise BusinessLogicError("プロジェクトの妥当性検証に失敗しました", entity_type="Project", entity_id=project.id)
        
        old_data = self.project_manager.get_project(project.id)
        old_dict = old_data.to_dict() if old_data else None
        
        # 自動進捗更新（自動モードの場合）
        if not project.is_status_manual:
            project.update_status_from_phases(self.phase_manager)
            project.update_progress_from_phases(self.phase_manager)
        
        # 更新実行
        success = self.project_manager.update_project(project)
        
        if success:
            # データ永続化
            self.data_store.save_project(project.id, project.to_dict())
            
            # 監査ログ
            self.logger.audit(
                AuditAction.UPDATE,
                "Project",
                project.id,
                project.name,
                "プロジェクト更新",
                before_data=old_dict,
                after_data=project.to_dict()
            )
            
            # 通知チェック
            self._check_and_generate_notifications_for_project(project)
            
            self.logger.info(
                LogCategory.USER,
                f"プロジェクト更新: {project.name}",
                module="core.manager",
                project_id=project.id
            )
        
        return success
    
    @handle_errors(recovery_strategy=RecoveryStrategy.NONE)
    def delete_project(self, project_id: str) -> bool:
        """
        プロジェクトを削除（カスケード削除）
        
        Args:
            project_id: プロジェクトID
            
        Returns:
            削除成功の可否
        """
        project = self.project_manager.get_project(project_id)
        if not project:
            return False
        
        # カスケード削除: フェーズ→プロセス→タスク
        for phase_id in project.phases[:]:  # コピーして削除
            self.delete_phase(phase_id)
        
        # プロジェクト削除
        success = self.project_manager.delete_project(project_id)
        
        if success:
            # データ永続化
            self.data_store.delete_project(project_id)
            
            # 監査ログ
            self.logger.audit(
                AuditAction.DELETE,
                "Project",
                project_id,
                project.name,
                "プロジェクト削除（カスケード削除）"
            )
            
            self.logger.info(
                LogCategory.USER,
                f"プロジェクト削除: {project.name}",
                module="core.manager",
                project_id=project_id
            )
        
        return success
    
    # ==================== フェーズ管理 ====================
    
    @handle_errors(recovery_strategy=RecoveryStrategy.NONE)
    @validate_input()
    def create_phase(self, name: str, project_id: str, description: str = "") -> Phase:
        """
        新しいフェーズを作成
        
        Args:
            name: フェーズ名
            project_id: 親プロジェクトID
            description: フェーズ説明
            
        Returns:
            作成されたフェーズ
        """
        # プロジェクト存在チェック
        project = self.project_manager.get_project(project_id)
        if not project:
            raise BusinessLogicError("指定されたプロジェクトが存在しません", entity_type="Project", entity_id=project_id)
        
        phase = self.phase_manager.create_phase(name, description, project_id)
        
        # プロジェクトにフェーズを追加
        project.add_phase(phase.id)
        
        # データ永続化
        self.data_store.save_phase(phase.id, phase.to_dict())
        self.data_store.save_project(project.id, project.to_dict())
        
        # 監査ログ
        self.logger.audit(
            AuditAction.CREATE,
            "Phase",
            phase.id,
            phase.name,
            f"フェーズ作成: プロジェクト「{project.name}」"
        )
        
        self.logger.info(
            LogCategory.USER,
            f"フェーズ作成: {phase.name} (プロジェクト: {project.name})",
            module="core.manager",
            project_id=project_id,
            phase_id=phase.id
        )
        
        return phase
    
    @handle_errors(recovery_strategy=RecoveryStrategy.NONE)
    def update_phase(self, phase: Phase) -> bool:
        """
        フェーズを更新（自動進捗更新含む）
        
        Args:
            phase: 更新するフェーズ
            
        Returns:
            更新成功の可否
        """
        old_data = self.phase_manager.get_phase(phase.id)
        old_dict = old_data.to_dict() if old_data else None
        
        # 自動進捗更新
        phase.update_progress_from_processes(self.process_manager)
        
        success = self.phase_manager.update_phase(phase)
        
        if success:
            # データ永続化
            self.data_store.save_phase(phase.id, phase.to_dict())
            
            # 親プロジェクトの進捗も更新
            if phase.parent_project_id:
                project = self.project_manager.get_project(phase.parent_project_id)
                if project:
                    self.update_project(project)  # 再帰的更新
            
            # 監査ログ
            self.logger.audit(
                AuditAction.UPDATE,
                "Phase",
                phase.id,
                phase.name,
                "フェーズ更新",
                before_data=old_dict,
                after_data=phase.to_dict()
            )
            
            # 通知チェック
            self._check_and_generate_notifications_for_phase(phase)
        
        return success
    
    @handle_errors(recovery_strategy=RecoveryStrategy.NONE)
    def delete_phase(self, phase_id: str) -> bool:
        """
        フェーズを削除（カスケード削除）
        """
        phase = self.phase_manager.get_phase(phase_id)
        if not phase:
            return False
        
        # カスケード削除: プロセス→タスク
        for process_id in phase.processes[:]:
            self.delete_process(process_id)
        
        # 親プロジェクトからフェーズを削除
        if phase.parent_project_id:
            project = self.project_manager.get_project(phase.parent_project_id)
            if project:
                project.remove_phase(phase_id)
                self.data_store.save_project(project.id, project.to_dict())
        
        # フェーズ削除
        success = self.phase_manager.delete_phase(phase_id)
        
        if success:
            self.data_store.delete_phase(phase_id)
            
            self.logger.audit(
                AuditAction.DELETE,
                "Phase",
                phase_id,
                phase.name,
                "フェーズ削除（カスケード削除）"
            )
        
        return success
    
    # ==================== プロセス管理 ====================
    
    @handle_errors(recovery_strategy=RecoveryStrategy.NONE)
    @validate_input()
    def create_process(self, name: str, assignee: str, phase_id: str, description: str = "") -> Process:
        """
        新しいプロセスを作成
        """
        # フェーズ存在チェック
        phase = self.phase_manager.get_phase(phase_id)
        if not phase:
            raise BusinessLogicError("指定されたフェーズが存在しません", entity_type="Phase", entity_id=phase_id)
        
        process = self.process_manager.create_process(name, assignee, description, phase_id)
        
        # フェーズにプロセスを追加
        phase.add_process(process.id)
        
        # データ永続化
        self.data_store.save_process(process.id, process.to_dict())
        self.data_store.save_phase(phase.id, phase.to_dict())
        
        # 監査ログ
        self.logger.audit(
            AuditAction.CREATE,
            "Process",
            process.id,
            process.name,
            f"プロセス作成: フェーズ「{phase.name}」, 担当者「{assignee}」"
        )
        
        return process
    
    @handle_errors(recovery_strategy=RecoveryStrategy.NONE)
    def update_process(self, process: Process) -> bool:
        """
        プロセスを更新（自動進捗更新含む）
        """
        old_data = self.process_manager.get_process(process.id)
        old_dict = old_data.to_dict() if old_data else None
        
        # 自動進捗更新（自動モードの場合）
        if not process.is_progress_manual:
            process.update_progress_from_tasks(self.task_manager)
        
        success = self.process_manager.update_process(process)
        
        if success:
            # データ永続化
            self.data_store.save_process(process.id, process.to_dict())
            
            # 親フェーズの進捗も更新
            if process.parent_phase_id:
                phase = self.phase_manager.get_phase(process.parent_phase_id)
                if phase:
                    self.update_phase(phase)  # 再帰的更新
            
            # 監査ログ
            self.logger.audit(
                AuditAction.UPDATE,
                "Process",
                process.id,
                process.name,
                "プロセス更新",
                before_data=old_dict,
                after_data=process.to_dict()
            )
            
            # 通知チェック
            self._check_and_generate_notifications_for_process(process)
        
        return success
    
    @handle_errors(recovery_strategy=RecoveryStrategy.NONE)
    def delete_process(self, process_id: str) -> bool:
        """
        プロセスを削除（カスケード削除）
        """
        process = self.process_manager.get_process(process_id)
        if not process:
            return False
        
        # カスケード削除: タスク
        for task_id in process.tasks[:]:
            self.delete_task(task_id)
        
        # 親フェーズからプロセスを削除
        if process.parent_phase_id:
            phase = self.phase_manager.get_phase(process.parent_phase_id)
            if phase:
                phase.remove_process(process_id)
                self.data_store.save_phase(phase.id, phase.to_dict())
        
        # プロセス削除
        success = self.process_manager.delete_process(process_id)
        
        if success:
            self.data_store.delete_process(process_id)
            
            self.logger.audit(
                AuditAction.DELETE,
                "Process",
                process_id,
                process.name,
                "プロセス削除（カスケード削除）"
            )
        
        return success
    
    # ==================== タスク管理 ====================
    
    @handle_errors(recovery_strategy=RecoveryStrategy.NONE)
    @validate_input()
    def create_task(self, name: str, process_id: str, description: str = "") -> Task:
        """
        新しいタスクを作成
        """
        # プロセス存在チェック
        process = self.process_manager.get_process(process_id)
        if not process:
            raise BusinessLogicError("指定されたプロセスが存在しません", entity_type="Process", entity_id=process_id)
        
        task = self.task_manager.create_task(name, description, process_id)
        
        # プロセスにタスクを追加
        process.add_task(task.id)
        
        # データ永続化
        self.data_store.save_task(task.id, task.to_dict())
        self.data_store.save_process(process.id, process.to_dict())
        
        # 監査ログ
        self.logger.audit(
            AuditAction.CREATE,
            "Task",
            task.id,
            task.name,
            f"タスク作成: プロセス「{process.name}」"
        )
        
        return task
    
    @handle_errors(recovery_strategy=RecoveryStrategy.NONE)
    def update_task_status(self, task_id: str, new_status: str, comment: str = "") -> bool:
        """
        タスクステータスを更新（階層的進捗更新）
        
        Args:
            task_id: タスクID
            new_status: 新しいステータス
            comment: 変更コメント
            
        Returns:
            更新成功の可否
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            return False
        
        old_status = task.status
        
        # ステータス更新
        success = task.set_status(new_status, self.logger.current_user, comment)
        
        if success:
            # データ永続化
            self.data_store.save_task(task.id, task.to_dict())
            
            # 階層的進捗更新
            self._cascade_update_progress(task)
            
            # 監査ログ
            self.logger.audit(
                AuditAction.UPDATE,
                "Task",
                task.id,
                task.name,
                f"ステータス変更: {old_status} → {new_status}",
                after_data={'status': new_status, 'comment': comment}
            )
            
            self.logger.info(
                LogCategory.USER,
                f"タスクステータス更新: {task.name} ({old_status} → {new_status})",
                module="core.manager",
                task_id=task_id,
                old_status=old_status,
                new_status=new_status
            )
        
        return success
    
    @handle_errors(recovery_strategy=RecoveryStrategy.NONE)
    def delete_task(self, task_id: str) -> bool:
        """
        タスクを削除
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            return False
        
        # 親プロセスからタスクを削除
        if task.parent_process_id:
            process = self.process_manager.get_process(task.parent_process_id)
            if process:
                process.remove_task(task_id)
                self.data_store.save_process(process.id, process.to_dict())
        
        # タスク削除
        success = self.task_manager.delete_task(task_id)
        
        if success:
            self.data_store.delete_task(task_id)
            
            self.logger.audit(
                AuditAction.DELETE,
                "Task",
                task_id,
                task.name,
                "タスク削除"
            )
        
        return success
    
    # ==================== 階層的進捗更新 ====================
    
    def _cascade_update_progress(self, task: Task) -> None:
        """
        タスク変更をきっかけとした階層的進捗更新
        Task → Process → Phase → Project
        """
        # プロセス進捗更新
        if task.parent_process_id:
            process = self.process_manager.get_process(task.parent_process_id)
            if process:
                self.update_process(process)  # これが再帰的にフェーズ→プロジェクトを更新
    
    # ==================== 通知管理 ====================
    
    def _check_and_generate_notifications_for_project(self, project: Project) -> None:
        """プロジェクトの通知をチェック・生成"""
        notifications = self.notification_generator.check_project_notifications(
            project, self.phase_manager
        )
        
        for notification in notifications:
            self.notification_manager.add_notification(notification)
            self.data_store.save_notification(notification.id, notification.to_dict())
    
    def _check_and_generate_notifications_for_phase(self, phase: Phase) -> None:
        """フェーズの通知をチェック・生成"""
        notifications = self.notification_generator.check_phase_notifications(
            phase, self.process_manager
        )
        
        for notification in notifications:
            self.notification_manager.add_notification(notification)
            self.data_store.save_notification(notification.id, notification.to_dict())
    
    def _check_and_generate_notifications_for_process(self, process: Process) -> None:
        """プロセスの通知をチェック・生成"""
        notifications = self.notification_generator.check_process_notifications(
            process, self.task_manager
        )
        
        for notification in notifications:
            self.notification_manager.add_notification(notification)
            self.data_store.save_notification(notification.id, notification.to_dict())
    
    def check_all_notifications(self) -> int:
        """
        全エンティティの通知をチェック
        
        Returns:
            生成された通知数
        """
        generated_count = 0
        
        # 全プロジェクトをチェック
        for project in self.project_manager.get_all_projects():
            self._check_and_generate_notifications_for_project(project)
            generated_count += 1
        
        # 全フェーズをチェック
        for phase in self.phase_manager.get_all_phases():
            self._check_and_generate_notifications_for_phase(phase)
            generated_count += 1
        
        # 全プロセスをチェック
        for process in self.process_manager.get_all_processes():
            self._check_and_generate_notifications_for_process(process)
            generated_count += 1
        
        self.logger.info(
            LogCategory.SYSTEM,
            f"通知チェック完了: {generated_count}件のエンティティをチェック",
            module="core.manager"
        )
        
        return generated_count
    
    # ==================== データ整合性・統計 ====================
    
    @handle_errors(recovery_strategy=RecoveryStrategy.FALLBACK, fallback_value={})
    def get_system_statistics(self) -> Dict[str, Any]:
        """システム統計情報を取得"""
        project_stats = self.project_manager.get_project_statistics()
        phase_stats = self.phase_manager.get_phase_statistics()
        process_stats = self.process_manager.get_process_statistics()
        task_stats = self.task_manager.get_task_statistics()
        notification_stats = self.notification_manager.get_notification_statistics()
        data_stats = self.data_store.get_data_statistics()
        
        return {
            'system_info': {
                'initialized_at': datetime.now().isoformat(),
                'data_directory': str(self.data_store.data_dir)
            },
            'projects': project_stats,
            'phases': phase_stats,
            'processes': process_stats,
            'tasks': task_stats,
            'notifications': notification_stats,
            'data_store': data_stats
        }
    
    @handle_errors(recovery_strategy=RecoveryStrategy.FALLBACK, fallback_value=False)
    def validate_data_integrity(self) -> bool:
        """データ整合性を検証"""
        integrity_result = self.data_store.validate_data_integrity()
        
        if not integrity_result['valid']:
            self.logger.error(
                LogCategory.DATA,
                f"データ整合性エラー: {integrity_result['errors']}",
                module="core.manager",
                errors=integrity_result['errors']
            )
        
        return integrity_result['valid']
    
    def cleanup_orphaned_data(self) -> Dict[str, int]:
        """孤立データをクリーンアップ"""
        result = self.data_store.cleanup_orphaned_data()
        
        self.logger.info(
            LogCategory.DATA,
            f"孤立データクリーンアップ完了: {result}",
            module="core.manager",
            cleanup_result=result
        )
        
        return result
    
    # ==================== 検索・取得 ====================
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """プロジェクトを取得"""
        return self.project_manager.get_project(project_id)
    
    def get_phase(self, phase_id: str) -> Optional[Phase]:
        """フェーズを取得"""
        return self.phase_manager.get_phase(phase_id)
    
    def get_process(self, process_id: str) -> Optional[Process]:
        """プロセスを取得"""
        return self.process_manager.get_process(process_id)
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """タスクを取得"""
        return self.task_manager.get_task(task_id)
    
    def get_all_projects(self) -> List[Project]:
        """全プロジェクトを取得"""
        return self.project_manager.get_all_projects()
    
    def search_projects(self, name_query: str = None, manager: str = None, 
                       status: str = None) -> List[Project]:
        """プロジェクトを検索"""
        projects = self.get_all_projects()
        
        if name_query:
            projects = [p for p in projects if name_query.lower() in p.name.lower()]
        
        if manager:
            projects = [p for p in projects if p.manager == manager]
        
        if status:
            projects = [p for p in projects if p.status == status]
        
        return projects
    
    def __str__(self) -> str:
        """文字列表現"""
        stats = self.get_system_statistics()
        return f"ProjectManagementSystem(projects={stats['projects']['total']}, " \
               f"phases={stats['phases']['total']}, " \
               f"processes={stats['processes']['total']}, " \
               f"tasks={stats['tasks']['total']})"