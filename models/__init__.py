# ====================
# models/__init__.py
# ====================
"""
データモデルパッケージ
プロジェクト管理システムのエンティティクラス
"""

from .base import BaseEntity, EntityManager, ProjectStatus, TaskStatus
from .project import Project, ProjectManager
from .phase import Phase, PhaseManager
from .process import Process, ProcessManager
from .task import Task, TaskManager
from .notification import (
    Notification, NotificationManager, NotificationGenerator,
    NotificationSettings, NotificationType, NotificationPriority
)

__version__ = "1.0.0"

__all__ = [
    # 基底クラス
    'BaseEntity',
    'EntityManager',
    'ProjectStatus',
    'TaskStatus',
    
    # エンティティクラス
    'Project',
    'Phase',
    'Process',
    'Task',
    'Notification',
    
    # 管理クラス
    'ProjectManager',
    'PhaseManager',
    'ProcessManager',
    'TaskManager',
    'NotificationManager',
    'NotificationGenerator',
    
    # 設定・定数
    'NotificationSettings',
    'NotificationType',
    'NotificationPriority'
]
