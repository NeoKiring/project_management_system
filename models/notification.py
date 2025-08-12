"""
通知モデル
プロジェクト管理システムの通知機能
"""

import uuid
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum


class NotificationType:
    """通知種別定義"""
    DEADLINE_APPROACHING = "期限接近"
    DEADLINE_OVERDUE = "期限超過"
    PROGRESS_DELAY = "進捗遅延"
    PROGRESS_INSUFFICIENT = "進捗不足"


class NotificationPriority:
    """通知優先度定義"""
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


class NotificationSettings:
    """通知設定クラス"""
    
    def __init__(self):
        # 期限接近通知の設定（デフォルト7日前）
        self.deadline_warning_days = 7
        
        # 進捗遅延通知の設定（デフォルト50%しきい値）
        self.progress_delay_threshold = 50.0
        
        # 進捗不足通知の設定（期限3日前で進捗30%未満）
        self.insufficient_progress_days = 3
        self.insufficient_progress_threshold = 30.0
        
        # チェック間隔設定
        self.check_interval_hours = 24  # 24時間ごと
        
        # 通知保持期間（日数）
        self.retention_days = 90
        
        # 通知有効化設定
        self.enabled_types = {
            NotificationType.DEADLINE_APPROACHING: True,
            NotificationType.DEADLINE_OVERDUE: True,
            NotificationType.PROGRESS_DELAY: True,
            NotificationType.PROGRESS_INSUFFICIENT: True
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """設定を辞書に変換"""
        return {
            'deadline_warning_days': self.deadline_warning_days,
            'progress_delay_threshold': self.progress_delay_threshold,
            'insufficient_progress_days': self.insufficient_progress_days,
            'insufficient_progress_threshold': self.insufficient_progress_threshold,
            'check_interval_hours': self.check_interval_hours,
            'retention_days': self.retention_days,
            'enabled_types': self.enabled_types.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotificationSettings':
        """辞書から設定を復元"""
        settings = cls()
        settings.deadline_warning_days = data.get('deadline_warning_days', 7)
        settings.progress_delay_threshold = data.get('progress_delay_threshold', 50.0)
        settings.insufficient_progress_days = data.get('insufficient_progress_days', 3)
        settings.insufficient_progress_threshold = data.get('insufficient_progress_threshold', 30.0)
        settings.check_interval_hours = data.get('check_interval_hours', 24)
        settings.retention_days = data.get('retention_days', 90)
        settings.enabled_types = data.get('enabled_types', {
            NotificationType.DEADLINE_APPROACHING: True,
            NotificationType.DEADLINE_OVERDUE: True,
            NotificationType.PROGRESS_DELAY: True,
            NotificationType.PROGRESS_INSUFFICIENT: True
        })
        return settings


class Notification:
    """
    通知クラス
    プロジェクト管理システムの通知機能
    """
    
    def __init__(self, 
                 notification_type: str,
                 entity_id: str,
                 entity_type: str,
                 entity_name: str,
                 message: str,
                 priority: str = NotificationPriority.MEDIUM):
        """
        通知の初期化
        
        Args:
            notification_type: 通知種別
            entity_id: 対象エンティティID
            entity_type: 対象エンティティタイプ
            entity_name: 対象エンティティ名
            message: 通知メッセージ
            priority: 通知優先度
        """
        self.id: str = str(uuid.uuid4())
        self.type: str = notification_type
        self.entity_id: str = entity_id
        self.entity_type: str = entity_type  # "Project", "Phase", "Process", "Task"
        self.entity_name: str = entity_name
        self.message: str = message
        self.priority: str = priority
        self.created_at: datetime = datetime.now()
        self.read_at: Optional[datetime] = None
        self.acknowledged_at: Optional[datetime] = None
        self.dismissed_at: Optional[datetime] = None
        self.metadata: Dict[str, Any] = {}
    
    def mark_as_read(self) -> None:
        """通知を既読にマーク"""
        if not self.read_at:
            self.read_at = datetime.now()
    
    def acknowledge(self) -> None:
        """通知を確認済みにマーク"""
        if not self.acknowledged_at:
            self.acknowledged_at = datetime.now()
            self.mark_as_read()  # 確認時に自動で既読にする
    
    def dismiss(self) -> None:
        """通知を却下（無視）にマーク"""
        if not self.dismissed_at:
            self.dismissed_at = datetime.now()
            self.mark_as_read()  # 却下時に自動で既読にする
    
    def is_read(self) -> bool:
        """既読状態かどうか"""
        return self.read_at is not None
    
    def is_acknowledged(self) -> bool:
        """確認済み状態かどうか"""
        return self.acknowledged_at is not None
    
    def is_dismissed(self) -> bool:
        """却下状態かどうか"""
        return self.dismissed_at is not None
    
    def is_active(self) -> bool:
        """アクティブ状態かどうか（未確認かつ未却下）"""
        return not self.is_acknowledged() and not self.is_dismissed()
    
    def get_age_hours(self) -> float:
        """通知の経過時間（時間）"""
        delta = datetime.now() - self.created_at
        return delta.total_seconds() / 3600
    
    def get_age_days(self) -> float:
        """通知の経過時間（日数）"""
        return self.get_age_hours() / 24
    
    def add_metadata(self, key: str, value: Any) -> None:
        """メタデータを追加"""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """メタデータを取得"""
        return self.metadata.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """通知を辞書形式に変換"""
        return {
            'id': self.id,
            'type': self.type,
            'entity_id': self.entity_id,
            'entity_type': self.entity_type,
            'entity_name': self.entity_name,
            'message': self.message,
            'priority': self.priority,
            'created_at': self.created_at.isoformat(),
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'dismissed_at': self.dismissed_at.isoformat() if self.dismissed_at else None,
            'metadata': self.metadata.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Notification':
        """辞書から通知を復元"""
        notification = cls(
            data['type'],
            data['entity_id'],
            data['entity_type'],
            data['entity_name'],
            data['message'],
            data.get('priority', NotificationPriority.MEDIUM)
        )
        
        notification.id = data['id']
        notification.created_at = datetime.fromisoformat(data['created_at'])
        notification.read_at = datetime.fromisoformat(data['read_at']) if data.get('read_at') else None
        notification.acknowledged_at = datetime.fromisoformat(data['acknowledged_at']) if data.get('acknowledged_at') else None
        notification.dismissed_at = datetime.fromisoformat(data['dismissed_at']) if data.get('dismissed_at') else None
        notification.metadata = data.get('metadata', {}).copy()
        
        return notification
    
    def __str__(self) -> str:
        """文字列表現"""
        status = "未読"
        if self.is_acknowledged():
            status = "確認済み"
        elif self.is_dismissed():
            status = "却下"
        elif self.is_read():
            status = "既読"
        
        return f"Notification({self.type}, {self.entity_name}, {status})"
    
    def __repr__(self) -> str:
        """詳細文字列表現"""
        return f"Notification(id='{self.id}', type='{self.type}', entity='{self.entity_name}', priority='{self.priority}')"


class NotificationGenerator:
    """通知生成エンジン"""
    
    def __init__(self, settings: NotificationSettings = None):
        self.settings = settings or NotificationSettings()
        self.last_check: Optional[datetime] = None
    
    def check_project_notifications(self, project, phase_manager=None) -> List[Notification]:
        """
        プロジェクトの通知をチェック
        
        Args:
            project: プロジェクトオブジェクト
            phase_manager: フェーズ管理オブジェクト
            
        Returns:
            生成された通知のリスト
        """
        notifications = []
        
        # 期限接近通知
        if self.settings.enabled_types.get(NotificationType.DEADLINE_APPROACHING, True):
            deadline_notification = self._check_deadline_approaching(project)
            if deadline_notification:
                notifications.append(deadline_notification)
        
        # 期限超過通知
        if self.settings.enabled_types.get(NotificationType.DEADLINE_OVERDUE, True):
            overdue_notification = self._check_deadline_overdue(project)
            if overdue_notification:
                notifications.append(overdue_notification)
        
        # 進捗遅延通知
        if self.settings.enabled_types.get(NotificationType.PROGRESS_DELAY, True):
            delay_notification = self._check_progress_delay(project)
            if delay_notification:
                notifications.append(delay_notification)
        
        # 進捗不足通知
        if self.settings.enabled_types.get(NotificationType.PROGRESS_INSUFFICIENT, True):
            insufficient_notification = self._check_progress_insufficient(project)
            if insufficient_notification:
                notifications.append(insufficient_notification)
        
        return notifications
    
    def check_phase_notifications(self, phase, process_manager=None) -> List[Notification]:
        """
        フェーズの通知をチェック
        
        Args:
            phase: フェーズオブジェクト
            process_manager: プロセス管理オブジェクト
            
        Returns:
            生成された通知のリスト
        """
        notifications = []
        
        # 期限接近通知
        if self.settings.enabled_types.get(NotificationType.DEADLINE_APPROACHING, True):
            deadline_notification = self._check_deadline_approaching(phase)
            if deadline_notification:
                notifications.append(deadline_notification)
        
        # 期限超過通知
        if self.settings.enabled_types.get(NotificationType.DEADLINE_OVERDUE, True):
            overdue_notification = self._check_deadline_overdue(phase)
            if overdue_notification:
                notifications.append(overdue_notification)
        
        # 進捗遅延通知
        if self.settings.enabled_types.get(NotificationType.PROGRESS_DELAY, True):
            delay_notification = self._check_progress_delay(phase)
            if delay_notification:
                notifications.append(delay_notification)
        
        # 進捗不足通知
        if self.settings.enabled_types.get(NotificationType.PROGRESS_INSUFFICIENT, True):
            insufficient_notification = self._check_progress_insufficient(phase)
            if insufficient_notification:
                notifications.append(insufficient_notification)
        
        return notifications
    
    def check_process_notifications(self, process, task_manager=None) -> List[Notification]:
        """
        プロセスの通知をチェック
        
        Args:
            process: プロセスオブジェクト
            task_manager: タスク管理オブジェクト
            
        Returns:
            生成された通知のリスト
        """
        notifications = []
        
        # 期限接近通知
        if self.settings.enabled_types.get(NotificationType.DEADLINE_APPROACHING, True):
            deadline_notification = self._check_deadline_approaching(process)
            if deadline_notification:
                notifications.append(deadline_notification)
        
        # 期限超過通知
        if self.settings.enabled_types.get(NotificationType.DEADLINE_OVERDUE, True):
            overdue_notification = self._check_deadline_overdue(process)
            if overdue_notification:
                notifications.append(overdue_notification)
        
        # 進捗遅延通知
        if self.settings.enabled_types.get(NotificationType.PROGRESS_DELAY, True):
            delay_notification = self._check_progress_delay(process)
            if delay_notification:
                notifications.append(delay_notification)
        
        # 進捗不足通知
        if self.settings.enabled_types.get(NotificationType.PROGRESS_INSUFFICIENT, True):
            insufficient_notification = self._check_progress_insufficient(process)
            if insufficient_notification:
                notifications.append(insufficient_notification)
        
        return notifications
    
    def _check_deadline_approaching(self, entity) -> Optional[Notification]:
        """期限接近通知をチェック"""
        end_date = getattr(entity, 'end_date', None)
        if not end_date:
            return None
        
        # 完了済みは通知不要
        if hasattr(entity, 'status') and entity.status == "完了":
            return None
        if hasattr(entity, 'progress') and entity.progress >= 100.0:
            return None
        
        days_until_deadline = (end_date - date.today()).days
        
        if 0 <= days_until_deadline <= self.settings.deadline_warning_days:
            entity_type = entity.__class__.__name__
            
            if days_until_deadline == 0:
                message = f"{entity_type}「{entity.name}」の期限が本日です。"
                priority = NotificationPriority.HIGH
            elif days_until_deadline == 1:
                message = f"{entity_type}「{entity.name}」の期限が明日です。"
                priority = NotificationPriority.HIGH
            else:
                message = f"{entity_type}「{entity.name}」の期限まで{days_until_deadline}日です。"
                priority = NotificationPriority.MEDIUM
            
            notification = Notification(
                NotificationType.DEADLINE_APPROACHING,
                entity.id,
                entity_type,
                entity.name,
                message,
                priority
            )
            
            notification.add_metadata('days_until_deadline', days_until_deadline)
            notification.add_metadata('end_date', end_date.isoformat())
            
            return notification
        
        return None
    
    def _check_deadline_overdue(self, entity) -> Optional[Notification]:
        """期限超過通知をチェック"""
        end_date = getattr(entity, 'end_date', None)
        if not end_date:
            return None
        
        # 完了済みは通知不要
        if hasattr(entity, 'status') and entity.status == "完了":
            return None
        if hasattr(entity, 'progress') and entity.progress >= 100.0:
            return None
        
        days_overdue = (date.today() - end_date).days
        
        if days_overdue > 0:
            entity_type = entity.__class__.__name__
            
            if days_overdue == 1:
                message = f"{entity_type}「{entity.name}」の期限が1日超過しています。"
            else:
                message = f"{entity_type}「{entity.name}」の期限が{days_overdue}日超過しています。"
            
            notification = Notification(
                NotificationType.DEADLINE_OVERDUE,
                entity.id,
                entity_type,
                entity.name,
                message,
                NotificationPriority.HIGH
            )
            
            notification.add_metadata('days_overdue', days_overdue)
            notification.add_metadata('end_date', end_date.isoformat())
            
            return notification
        
        return None
    
    def _check_progress_delay(self, entity) -> Optional[Notification]:
        """進捗遅延通知をチェック"""
        progress = getattr(entity, 'progress', None)
        if progress is None:
            return None
        
        # 完了済みは通知不要
        if progress >= 100.0:
            return None
        
        if progress < self.settings.progress_delay_threshold:
            entity_type = entity.__class__.__name__
            message = f"{entity_type}「{entity.name}」の進捗が{progress:.1f}%で遅延しています（しきい値: {self.settings.progress_delay_threshold}%）。"
            
            notification = Notification(
                NotificationType.PROGRESS_DELAY,
                entity.id,
                entity_type,
                entity.name,
                message,
                NotificationPriority.MEDIUM
            )
            
            notification.add_metadata('current_progress', progress)
            notification.add_metadata('threshold', self.settings.progress_delay_threshold)
            
            return notification
        
        return None
    
    def _check_progress_insufficient(self, entity) -> Optional[Notification]:
        """進捗不足通知をチェック"""
        end_date = getattr(entity, 'end_date', None)
        progress = getattr(entity, 'progress', None)
        
        if not end_date or progress is None:
            return None
        
        # 完了済みは通知不要
        if progress >= 100.0:
            return None
        
        days_until_deadline = (end_date - date.today()).days
        
        # 期限3日前（設定可能）で進捗30%未満（設定可能）
        if (days_until_deadline <= self.settings.insufficient_progress_days and 
            progress < self.settings.insufficient_progress_threshold):
            
            entity_type = entity.__class__.__name__
            message = f"{entity_type}「{entity.name}」の期限まで{days_until_deadline}日ですが、進捗が{progress:.1f}%と不足しています。"
            
            notification = Notification(
                NotificationType.PROGRESS_INSUFFICIENT,
                entity.id,
                entity_type,
                entity.name,
                message,
                NotificationPriority.HIGH
            )
            
            notification.add_metadata('days_until_deadline', days_until_deadline)
            notification.add_metadata('current_progress', progress)
            notification.add_metadata('threshold', self.settings.insufficient_progress_threshold)
            
            return notification
        
        return None


class NotificationManager:
    """通知管理クラス"""
    
    def __init__(self, settings: NotificationSettings = None):
        self.notifications: Dict[str, Notification] = {}
        self.settings = settings or NotificationSettings()
        self.generator = NotificationGenerator(self.settings)
        self.last_cleanup: Optional[datetime] = None
    
    def add_notification(self, notification: Notification) -> bool:
        """
        通知を追加
        
        Args:
            notification: 追加する通知
            
        Returns:
            追加成功の可否
        """
        # 重複チェック（同じエンティティ・同じタイプの通知が既に存在するか）
        existing = self.find_existing_notification(
            notification.entity_id,
            notification.type
        )
        
        if existing and existing.is_active():
            # アクティブな同種通知が既に存在する場合は追加しない
            return False
        
        self.notifications[notification.id] = notification
        return True
    
    def find_existing_notification(self, entity_id: str, notification_type: str) -> Optional[Notification]:
        """既存の通知を検索"""
        for notification in self.notifications.values():
            if (notification.entity_id == entity_id and 
                notification.type == notification_type):
                return notification
        return None
    
    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """通知を取得"""
        return self.notifications.get(notification_id)
    
    def get_notifications_by_entity(self, entity_id: str) -> List[Notification]:
        """エンティティIDで通知を取得"""
        return [notification for notification in self.notifications.values()
                if notification.entity_id == entity_id]
    
    def get_notifications_by_type(self, notification_type: str) -> List[Notification]:
        """タイプで通知を取得"""
        return [notification for notification in self.notifications.values()
                if notification.type == notification_type]
    
    def get_notifications_by_priority(self, priority: str) -> List[Notification]:
        """優先度で通知を取得"""
        return [notification for notification in self.notifications.values()
                if notification.priority == priority]
    
    def get_unread_notifications(self) -> List[Notification]:
        """未読通知を取得"""
        return [notification for notification in self.notifications.values()
                if not notification.is_read()]
    
    def get_active_notifications(self) -> List[Notification]:
        """アクティブ通知を取得"""
        return [notification for notification in self.notifications.values()
                if notification.is_active()]
    
    def mark_as_read(self, notification_id: str) -> bool:
        """通知を既読にマーク"""
        notification = self.get_notification(notification_id)
        if notification:
            notification.mark_as_read()
            return True
        return False
    
    def acknowledge(self, notification_id: str) -> bool:
        """通知を確認済みにマーク"""
        notification = self.get_notification(notification_id)
        if notification:
            notification.acknowledge()
            return True
        return False
    
    def dismiss(self, notification_id: str) -> bool:
        """通知を却下にマーク"""
        notification = self.get_notification(notification_id)
        if notification:
            notification.dismiss()
            return True
        return False
    
    def mark_all_as_read(self) -> int:
        """全通知を既読にマーク"""
        count = 0
        for notification in self.notifications.values():
            if not notification.is_read():
                notification.mark_as_read()
                count += 1
        return count
    
    def delete_notification(self, notification_id: str) -> bool:
        """通知を削除"""
        if notification_id in self.notifications:
            del self.notifications[notification_id]
            return True
        return False
    
    def cleanup_old_notifications(self) -> int:
        """古い通知を削除"""
        cutoff_date = datetime.now() - timedelta(days=self.settings.retention_days)
        
        old_notifications = [
            notification_id for notification_id, notification in self.notifications.items()
            if notification.created_at < cutoff_date
        ]
        
        for notification_id in old_notifications:
            del self.notifications[notification_id]
        
        self.last_cleanup = datetime.now()
        return len(old_notifications)
    
    def get_all_notifications(self) -> List[Notification]:
        """全通知を取得（作成日時の降順）"""
        return sorted(self.notifications.values(), 
                     key=lambda x: x.created_at, reverse=True)
    
    def get_notification_statistics(self) -> Dict[str, Any]:
        """通知統計を取得"""
        total = len(self.notifications)
        if total == 0:
            return {'total': 0}
        
        type_counts = {}
        priority_counts = {}
        status_counts = {'unread': 0, 'read': 0, 'acknowledged': 0, 'dismissed': 0, 'active': 0}
        
        for notification in self.notifications.values():
            # タイプ別カウント
            type_counts[notification.type] = type_counts.get(notification.type, 0) + 1
            
            # 優先度別カウント
            priority_counts[notification.priority] = priority_counts.get(notification.priority, 0) + 1
            
            # ステータス別カウント
            if notification.is_acknowledged():
                status_counts['acknowledged'] += 1
            elif notification.is_dismissed():
                status_counts['dismissed'] += 1
            elif notification.is_read():
                status_counts['read'] += 1
            else:
                status_counts['unread'] += 1
            
            if notification.is_active():
                status_counts['active'] += 1
        
        return {
            'total': total,
            'type_counts': type_counts,
            'priority_counts': priority_counts,
            'status_counts': status_counts
        }
    
    def clear_all_notifications(self) -> int:
        """全通知をクリア"""
        count = len(self.notifications)
        self.notifications.clear()
        return count