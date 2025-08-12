"""
通知管理システム
バックグラウンド通知チェック・配信制御・設定管理
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor

from ..models.notification import (
    Notification, NotificationManager, NotificationGenerator, 
    NotificationSettings, NotificationType, NotificationPriority
)
from ..core.logger import ProjectLogger, LogCategory
from ..core.error_handler import handle_errors, RecoveryStrategy


class NotificationService:
    """
    通知サービス
    バックグラウンド処理・自動通知チェック・配信制御
    """
    
    def __init__(self, project_management_system=None):
        """
        通知サービスの初期化
        
        Args:
            project_management_system: プロジェクト管理システムのインスタンス
        """
        self.pms = project_management_system  # 循環参照を避けるため遅延設定
        self.logger = ProjectLogger()
        
        # 通知管理
        self.notification_manager = NotificationManager()
        self.settings = NotificationSettings()
        
        # バックグラウンド処理制御
        self.is_running = False
        self.check_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # 配信先コールバック
        self.notification_handlers: List[Callable[[Notification], None]] = []
        
        # 統計情報
        self.stats = {
            'total_generated': 0,
            'total_delivered': 0,
            'last_check_time': None,
            'last_cleanup_time': None,
            'errors': 0
        }
        
        self.logger.info(
            LogCategory.SYSTEM,
            "通知サービスが初期化されました",
            module="core.notification_manager"
        )
    
    def set_project_management_system(self, pms) -> None:
        """プロジェクト管理システムの参照を設定"""
        self.pms = pms
    
    # ==================== 設定管理 ====================
    
    def update_settings(self, **kwargs) -> None:
        """
        通知設定を更新
        
        Args:
            **kwargs: 設定項目（deadline_warning_days, progress_delay_threshold等）
        """
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
                
                self.logger.info(
                    LogCategory.SYSTEM,
                    f"通知設定更新: {key} = {value}",
                    module="core.notification_manager",
                    setting_key=key,
                    setting_value=value
                )
        
        # 通知生成エンジンの設定も更新
        if hasattr(self, 'notification_generator'):
            self.notification_generator.settings = self.settings
    
    def get_settings(self) -> Dict[str, Any]:
        """通知設定を取得"""
        return self.settings.to_dict()
    
    def enable_notification_type(self, notification_type: str) -> None:
        """指定通知タイプを有効化"""
        self.settings.enabled_types[notification_type] = True
        self.logger.info(
            LogCategory.SYSTEM,
            f"通知タイプ有効化: {notification_type}",
            module="core.notification_manager"
        )
    
    def disable_notification_type(self, notification_type: str) -> None:
        """指定通知タイプを無効化"""
        self.settings.enabled_types[notification_type] = False
        self.logger.info(
            LogCategory.SYSTEM,
            f"通知タイプ無効化: {notification_type}",
            module="core.notification_manager"
        )
    
    # ==================== 通知ハンドラー管理 ====================
    
    def add_notification_handler(self, handler: Callable[[Notification], None]) -> None:
        """
        通知配信ハンドラーを追加
        
        Args:
            handler: 通知を受け取るコールバック関数
        """
        self.notification_handlers.append(handler)
        self.logger.info(
            LogCategory.SYSTEM,
            f"通知ハンドラー追加: {handler.__name__}",
            module="core.notification_manager"
        )
    
    def remove_notification_handler(self, handler: Callable[[Notification], None]) -> bool:
        """
        通知配信ハンドラーを削除
        
        Args:
            handler: 削除するハンドラー
            
        Returns:
            削除成功の可否
        """
        try:
            self.notification_handlers.remove(handler)
            self.logger.info(
                LogCategory.SYSTEM,
                f"通知ハンドラー削除: {handler.__name__}",
                module="core.notification_manager"
            )
            return True
        except ValueError:
            return False
    
    def _deliver_notification(self, notification: Notification) -> None:
        """
        通知を配信（全ハンドラーに送信）
        
        Args:
            notification: 配信する通知
        """
        delivered_count = 0
        
        for handler in self.notification_handlers:
            try:
                handler(notification)
                delivered_count += 1
            except Exception as e:
                self.logger.error(
                    LogCategory.ERROR,
                    f"通知配信エラー: {handler.__name__} - {e}",
                    module="core.notification_manager",
                    exception=e,
                    notification_id=notification.id
                )
                self.stats['errors'] += 1
        
        if delivered_count > 0:
            self.stats['total_delivered'] += delivered_count
            self.logger.debug(
                LogCategory.SYSTEM,
                f"通知配信完了: {notification.type} - {notification.entity_name} "
                f"({delivered_count}箇所に配信)",
                module="core.notification_manager",
                notification_id=notification.id,
                delivery_count=delivered_count
            )
    
    # ==================== 手動通知操作 ====================
    
    @handle_errors(recovery_strategy=RecoveryStrategy.NONE)
    def create_manual_notification(self, notification_type: str, entity_id: str,
                                 entity_type: str, entity_name: str, message: str,
                                 priority: str = NotificationPriority.MEDIUM) -> Notification:
        """
        手動通知を作成
        
        Args:
            notification_type: 通知タイプ
            entity_id: 対象エンティティID
            entity_type: 対象エンティティタイプ
            entity_name: 対象エンティティ名
            message: 通知メッセージ
            priority: 優先度
            
        Returns:
            作成された通知
        """
        notification = Notification(
            notification_type,
            entity_id,
            entity_type,
            entity_name,
            message,
            priority
        )
        
        # 手動作成フラグを追加
        notification.add_metadata('manual_creation', True)
        notification.add_metadata('created_by', self.logger.current_user)
        
        # 通知を追加
        self.notification_manager.add_notification(notification)
        
        # データ永続化
        if self.pms:
            self.pms.data_store.save_notification(notification.id, notification.to_dict())
        
        # 配信
        self._deliver_notification(notification)
        
        self.logger.info(
            LogCategory.USER,
            f"手動通知作成: {notification_type} - {entity_name}",
            module="core.notification_manager",
            notification_id=notification.id
        )
        
        return notification
    
    def mark_notification_as_read(self, notification_id: str) -> bool:
        """通知を既読にマーク"""
        success = self.notification_manager.mark_as_read(notification_id)
        
        if success and self.pms:
            notification = self.notification_manager.get_notification(notification_id)
            if notification:
                self.pms.data_store.save_notification(notification_id, notification.to_dict())
                
                self.logger.info(
                    LogCategory.USER,
                    f"通知既読: {notification.entity_name}",
                    module="core.notification_manager",
                    notification_id=notification_id
                )
        
        return success
    
    def acknowledge_notification(self, notification_id: str) -> bool:
        """通知を確認済みにマーク"""
        success = self.notification_manager.acknowledge(notification_id)
        
        if success and self.pms:
            notification = self.notification_manager.get_notification(notification_id)
            if notification:
                self.pms.data_store.save_notification(notification_id, notification.to_dict())
                
                self.logger.info(
                    LogCategory.USER,
                    f"通知確認: {notification.entity_name}",
                    module="core.notification_manager",
                    notification_id=notification_id
                )
        
        return success
    
    def dismiss_notification(self, notification_id: str) -> bool:
        """通知を却下にマーク"""
        success = self.notification_manager.dismiss(notification_id)
        
        if success and self.pms:
            notification = self.notification_manager.get_notification(notification_id)
            if notification:
                self.pms.data_store.save_notification(notification_id, notification.to_dict())
                
                self.logger.info(
                    LogCategory.USER,
                    f"通知却下: {notification.entity_name}",
                    module="core.notification_manager",
                    notification_id=notification_id
                )
        
        return success
    
    def bulk_mark_as_read(self, notification_ids: List[str]) -> int:
        """複数通知を一括既読"""
        success_count = 0
        
        for notification_id in notification_ids:
            if self.mark_notification_as_read(notification_id):
                success_count += 1
        
        self.logger.info(
            LogCategory.USER,
            f"一括既読処理: {success_count}/{len(notification_ids)}件成功",
            module="core.notification_manager",
            success_count=success_count,
            total_count=len(notification_ids)
        )
        
        return success_count
    
    # ==================== 自動通知チェック ====================
    
    @handle_errors(recovery_strategy=RecoveryStrategy.IGNORE)
    def check_and_generate_notifications(self) -> int:
        """
        全エンティティの通知チェック・生成
        
        Returns:
            生成された通知数
        """
        if not self.pms:
            self.logger.warning(
                LogCategory.SYSTEM,
                "プロジェクト管理システムが設定されていません",
                module="core.notification_manager"
            )
            return 0
        
        generated_count = 0
        
        try:
            # 通知生成エンジンの設定を更新
            generator = NotificationGenerator(self.settings)
            
            # プロジェクト通知チェック
            for project in self.pms.get_all_projects():
                notifications = generator.check_project_notifications(
                    project, self.pms.phase_manager
                )
                
                for notification in notifications:
                    if self.notification_manager.add_notification(notification):
                        # データ永続化
                        self.pms.data_store.save_notification(notification.id, notification.to_dict())
                        
                        # 配信
                        self._deliver_notification(notification)
                        
                        generated_count += 1
                        self.stats['total_generated'] += 1
            
            # フェーズ通知チェック
            for phase in self.pms.phase_manager.get_all_phases():
                notifications = generator.check_phase_notifications(
                    phase, self.pms.process_manager
                )
                
                for notification in notifications:
                    if self.notification_manager.add_notification(notification):
                        self.pms.data_store.save_notification(notification.id, notification.to_dict())
                        self._deliver_notification(notification)
                        generated_count += 1
                        self.stats['total_generated'] += 1
            
            # プロセス通知チェック
            for process in self.pms.process_manager.get_all_processes():
                notifications = generator.check_process_notifications(
                    process, self.pms.task_manager
                )
                
                for notification in notifications:
                    if self.notification_manager.add_notification(notification):
                        self.pms.data_store.save_notification(notification.id, notification.to_dict())
                        self._deliver_notification(notification)
                        generated_count += 1
                        self.stats['total_generated'] += 1
            
            self.stats['last_check_time'] = datetime.now()
            
            if generated_count > 0:
                self.logger.info(
                    LogCategory.SYSTEM,
                    f"通知チェック完了: {generated_count}件の新規通知を生成",
                    module="core.notification_manager",
                    generated_count=generated_count
                )
            else:
                self.logger.debug(
                    LogCategory.SYSTEM,
                    "通知チェック完了: 新規通知なし",
                    module="core.notification_manager"
                )
            
        except Exception as e:
            self.logger.error(
                LogCategory.ERROR,
                f"通知チェックエラー: {e}",
                module="core.notification_manager",
                exception=e
            )
            self.stats['errors'] += 1
        
        return generated_count
    
    # ==================== バックグラウンド処理 ====================
    
    def start_background_service(self) -> bool:
        """
        バックグラウンド通知サービスを開始
        
        Returns:
            開始成功の可否
        """
        if self.is_running:
            self.logger.warning(
                LogCategory.SYSTEM,
                "バックグラウンドサービスは既に実行中です",
                module="core.notification_manager"
            )
            return False
        
        self.is_running = True
        self.stop_event.clear()
        
        self.check_thread = threading.Thread(
            target=self._background_check_loop,
            name="NotificationService",
            daemon=True
        )
        self.check_thread.start()
        
        self.logger.info(
            LogCategory.SYSTEM,
            f"バックグラウンド通知サービス開始 (チェック間隔: {self.settings.check_interval_hours}時間)",
            module="core.notification_manager",
            check_interval=self.settings.check_interval_hours
        )
        
        return True
    
    def stop_background_service(self) -> bool:
        """
        バックグラウンド通知サービスを停止
        
        Returns:
            停止成功の可否
        """
        if not self.is_running:
            return False
        
        self.is_running = False
        self.stop_event.set()
        
        if self.check_thread and self.check_thread.is_alive():
            self.check_thread.join(timeout=5.0)
        
        self.logger.info(
            LogCategory.SYSTEM,
            "バックグラウンド通知サービス停止",
            module="core.notification_manager"
        )
        
        return True
    
    def _background_check_loop(self) -> None:
        """バックグラウンド通知チェックループ"""
        self.logger.info(
            LogCategory.SYSTEM,
            "バックグラウンド通知チェック開始",
            module="core.notification_manager"
        )
        
        while self.is_running and not self.stop_event.is_set():
            try:
                # 通知チェック実行
                self.check_and_generate_notifications()
                
                # 古い通知のクリーンアップ（1日1回）
                if self._should_run_cleanup():
                    self._run_cleanup()
                
                # 設定された間隔まで待機
                interval_seconds = self.settings.check_interval_hours * 3600
                
                # 停止イベントを待機（タイムアウト付き）
                if self.stop_event.wait(timeout=interval_seconds):
                    break  # 停止シグナルを受信
                
            except Exception as e:
                self.logger.error(
                    LogCategory.ERROR,
                    f"バックグラウンド処理エラー: {e}",
                    module="core.notification_manager",
                    exception=e
                )
                self.stats['errors'] += 1
                
                # エラー時は5分待機してリトライ
                if not self.stop_event.wait(timeout=300):
                    continue
        
        self.logger.info(
            LogCategory.SYSTEM,
            "バックグラウンド通知チェック終了",
            module="core.notification_manager"
        )
    
    def _should_run_cleanup(self) -> bool:
        """クリーンアップが必要かどうか"""
        if not self.stats['last_cleanup_time']:
            return True
        
        last_cleanup = self.stats['last_cleanup_time']
        return (datetime.now() - last_cleanup).total_seconds() > 86400  # 24時間
    
    def _run_cleanup(self) -> None:
        """古い通知のクリーンアップを実行"""
        try:
            deleted_count = self.notification_manager.cleanup_old_notifications()
            self.stats['last_cleanup_time'] = datetime.now()
            
            self.logger.info(
                LogCategory.SYSTEM,
                f"通知クリーンアップ完了: {deleted_count}件削除",
                module="core.notification_manager",
                deleted_count=deleted_count
            )
            
        except Exception as e:
            self.logger.error(
                LogCategory.ERROR,
                f"通知クリーンアップエラー: {e}",
                module="core.notification_manager",
                exception=e
            )
    
    # ==================== 検索・フィルタリング ====================
    
    def get_notifications(self, filter_options: Dict[str, Any] = None) -> List[Notification]:
        """
        通知を検索・フィルタリング
        
        Args:
            filter_options: フィルタオプション
                - type: 通知タイプ
                - priority: 優先度
                - entity_type: エンティティタイプ
                - entity_id: エンティティID
                - status: ステータス（unread, read, active, acknowledged, dismissed）
                - limit: 最大件数
                
        Returns:
            フィルタされた通知リスト
        """
        if not filter_options:
            return self.notification_manager.get_all_notifications()
        
        notifications = self.notification_manager.get_all_notifications()
        
        # タイプフィルタ
        if filter_options.get('type'):
            notifications = [n for n in notifications if n.type == filter_options['type']]
        
        # 優先度フィルタ
        if filter_options.get('priority'):
            notifications = [n for n in notifications if n.priority == filter_options['priority']]
        
        # エンティティタイプフィルタ
        if filter_options.get('entity_type'):
            notifications = [n for n in notifications if n.entity_type == filter_options['entity_type']]
        
        # エンティティIDフィルタ
        if filter_options.get('entity_id'):
            notifications = [n for n in notifications if n.entity_id == filter_options['entity_id']]
        
        # ステータスフィルタ
        status = filter_options.get('status')
        if status == 'unread':
            notifications = [n for n in notifications if not n.is_read()]
        elif status == 'read':
            notifications = [n for n in notifications if n.is_read()]
        elif status == 'active':
            notifications = [n for n in notifications if n.is_active()]
        elif status == 'acknowledged':
            notifications = [n for n in notifications if n.is_acknowledged()]
        elif status == 'dismissed':
            notifications = [n for n in notifications if n.is_dismissed()]
        
        # 件数制限
        limit = filter_options.get('limit')
        if limit and isinstance(limit, int) and limit > 0:
            notifications = notifications[:limit]
        
        return notifications
    
    def get_notification_summary(self) -> Dict[str, Any]:
        """通知サマリーを取得"""
        stats = self.notification_manager.get_notification_statistics()
        
        return {
            'notification_counts': stats,
            'service_stats': self.stats.copy(),
            'background_service': {
                'is_running': self.is_running,
                'check_interval_hours': self.settings.check_interval_hours,
                'last_check': self.stats['last_check_time'].isoformat() if self.stats['last_check_time'] else None
            },
            'settings': self.get_settings()
        }
    
    # ==================== 通知エクスポート ====================
    
    def export_notifications(self, file_path: str, 
                           start_date: datetime = None,
                           end_date: datetime = None) -> bool:
        """
        通知をファイルにエクスポート
        
        Args:
            file_path: エクスポート先ファイルパス
            start_date: 開始日時
            end_date: 終了日時
            
        Returns:
            エクスポート成功の可否
        """
        try:
            import json
            
            notifications = self.notification_manager.get_all_notifications()
            
            # 期間フィルタ
            if start_date or end_date:
                filtered_notifications = []
                for notification in notifications:
                    if start_date and notification.created_at < start_date:
                        continue
                    if end_date and notification.created_at > end_date:
                        continue
                    filtered_notifications.append(notification)
                notifications = filtered_notifications
            
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'period': {
                    'start': start_date.isoformat() if start_date else None,
                    'end': end_date.isoformat() if end_date else None
                },
                'notification_count': len(notifications),
                'notifications': [notification.to_dict() for notification in notifications]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(
                LogCategory.USER,
                f"通知エクスポート完了: {file_path} ({len(notifications)}件)",
                module="core.notification_manager",
                file_path=file_path,
                notification_count=len(notifications)
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                LogCategory.ERROR,
                f"通知エクスポートエラー: {e}",
                module="core.notification_manager",
                exception=e
            )
            return False
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"NotificationService(running={self.is_running}, " \
               f"notifications={len(self.notification_manager.notifications)}, " \
               f"handlers={len(self.notification_handlers)})"