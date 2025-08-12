"""
タスクモデル
プロジェクト管理システムの最小作業単位
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from .base import BaseEntity, TaskStatus


class StatusChange:
    """タスクステータス変更履歴"""
    
    def __init__(self, old_status: str, new_status: str, changed_by: str = "system"):
        self.id: str = f"{datetime.now().timestamp()}"
        self.old_status: str = old_status
        self.new_status: str = new_status
        self.changed_at: datetime = datetime.now()
        self.changed_by: str = changed_by
        self.comment: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'id': self.id,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'changed_at': self.changed_at.isoformat(),
            'changed_by': self.changed_by,
            'comment': self.comment
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StatusChange':
        """辞書から復元"""
        change = cls(
            data['old_status'],
            data['new_status'],
            data.get('changed_by', 'system')
        )
        change.id = data['id']
        change.changed_at = datetime.fromisoformat(data['changed_at'])
        change.comment = data.get('comment', '')
        return change


class Task(BaseEntity):
    """
    タスククラス
    プロジェクト管理システムの最小作業単位
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        タスクの初期化
        
        Args:
            name: タスク名
            description: タスク説明
        """
        super().__init__(name, description)
        self.status: str = TaskStatus.NOT_STARTED
        self.status_history: List[StatusChange] = []
        self.parent_process_id: Optional[str] = None
        self.priority: int = 3  # 1(高) ~ 5(低)
        self.estimated_hours: Optional[float] = None
        self.actual_hours: Optional[float] = None
        self.notes: str = ""
        self.tags: List[str] = []
        
        # 初期ステータス履歴を記録
        self._add_status_change("", self.status)
    
    def set_status(self, new_status: str, changed_by: str = "user", comment: str = "") -> bool:
        """
        タスクステータスを変更
        
        Args:
            new_status: 新しいステータス
            changed_by: 変更者
            comment: 変更コメント
            
        Returns:
            変更成功の可否
        """
        if not TaskStatus.is_valid(new_status):
            return False
        
        if new_status == self.status:
            return True  # 同じステータスなので変更なし
        
        old_status = self.status
        self.status = new_status
        self.update_timestamp()
        
        # ステータス変更履歴を記録
        change = self._add_status_change(old_status, new_status, changed_by)
        if comment:
            change.comment = comment
        
        return True
    
    def _add_status_change(self, old_status: str, new_status: str, changed_by: str = "system") -> StatusChange:
        """ステータス変更履歴を追加"""
        change = StatusChange(old_status, new_status, changed_by)
        self.status_history.append(change)
        return change
    
    def is_completed(self) -> bool:
        """完了状態かどうか"""
        return self.status == TaskStatus.COMPLETED
    
    def is_cannot_handle(self) -> bool:
        """対応不能状態かどうか"""
        return self.status == TaskStatus.CANNOT_HANDLE
    
    def is_actionable(self) -> bool:
        """実行可能状態かどうか（対応不能以外）"""
        return not self.is_cannot_handle()
    
    def get_completion_percentage(self) -> float:
        """
        完了率を取得
        
        Returns:
            完了率（0.0-100.0）
        """
        if self.is_completed():
            return 100.0
        elif self.is_cannot_handle():
            return 0.0  # 対応不能は進捗計算から除外
        else:
            return 0.0  # 未完了は0%
    
    def set_priority(self, priority: int) -> bool:
        """
        優先度を設定
        
        Args:
            priority: 優先度（1-5）
            
        Returns:
            設定成功の可否
        """
        if 1 <= priority <= 5:
            self.priority = priority
            self.update_timestamp()
            return True
        return False
    
    def add_tag(self, tag: str) -> bool:
        """
        タグを追加
        
        Args:
            tag: 追加するタグ
            
        Returns:
            追加成功の可否
        """
        tag = tag.strip()
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.update_timestamp()
            return True
        return False
    
    def remove_tag(self, tag: str) -> bool:
        """
        タグを削除
        
        Args:
            tag: 削除するタグ
            
        Returns:
            削除成功の可否
        """
        if tag in self.tags:
            self.tags.remove(tag)
            self.update_timestamp()
            return True
        return False
    
    def set_estimated_hours(self, hours: float) -> bool:
        """
        予想工数を設定
        
        Args:
            hours: 予想工数
            
        Returns:
            設定成功の可否
        """
        if hours >= 0:
            self.estimated_hours = hours
            self.update_timestamp()
            return True
        return False
    
    def set_actual_hours(self, hours: float) -> bool:
        """
        実績工数を設定
        
        Args:
            hours: 実績工数
            
        Returns:
            設定成功の可否
        """
        if hours >= 0:
            self.actual_hours = hours
            self.update_timestamp()
            return True
        return False
    
    def get_efficiency_ratio(self) -> Optional[float]:
        """
        効率性比率を取得（実績/予想）
        
        Returns:
            効率性比率（Noneの場合は計算不可）
        """
        if self.estimated_hours and self.actual_hours and self.estimated_hours > 0:
            return self.actual_hours / self.estimated_hours
        return None
    
    def _to_dict_additional(self) -> Dict[str, Any]:
        """タスク固有属性を辞書に変換"""
        return {
            'status': self.status,
            'status_history': [change.to_dict() for change in self.status_history],
            'parent_process_id': self.parent_process_id,
            'priority': self.priority,
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'notes': self.notes,
            'tags': self.tags.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """辞書からタスクを復元"""
        task = cls(data['name'], data.get('description', ''))
        
        # 基底属性を復元
        task.id = data['id']
        task.created_at = datetime.fromisoformat(data['created_at'])
        task.updated_at = datetime.fromisoformat(data['updated_at'])
        
        # タスク固有属性を復元
        task.status = data.get('status', TaskStatus.NOT_STARTED)
        task.parent_process_id = data.get('parent_process_id')
        task.priority = data.get('priority', 3)
        task.estimated_hours = data.get('estimated_hours')
        task.actual_hours = data.get('actual_hours')
        task.notes = data.get('notes', '')
        task.tags = data.get('tags', []).copy()
        
        # ステータス履歴を復元
        task.status_history = []
        for change_data in data.get('status_history', []):
            task.status_history.append(StatusChange.from_dict(change_data))
        
        return task
    
    def _validate_additional(self) -> bool:
        """タスク固有の妥当性検証"""
        # ステータスの妥当性
        if not TaskStatus.is_valid(self.status):
            return False
        
        # 優先度の妥当性
        if not (1 <= self.priority <= 5):
            return False
        
        # 工数の妥当性
        if self.estimated_hours is not None and self.estimated_hours < 0:
            return False
        
        if self.actual_hours is not None and self.actual_hours < 0:
            return False
        
        return True
    
    def get_status_summary(self) -> Dict[str, Any]:
        """ステータスサマリーを取得"""
        return {
            'current_status': self.status,
            'is_completed': self.is_completed(),
            'is_actionable': self.is_actionable(),
            'completion_percentage': self.get_completion_percentage(),
            'priority': self.priority,
            'status_changes': len(self.status_history),
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'efficiency_ratio': self.get_efficiency_ratio()
        }
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"Task(name='{self.name}', status='{self.status}', priority={self.priority})"


class TaskManager:
    """タスク管理クラス"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
    
    def create_task(self, name: str, description: str = "", process_id: str = None) -> Task:
        """
        新しいタスクを作成
        
        Args:
            name: タスク名
            description: タスク説明
            process_id: 親プロセスID
            
        Returns:
            作成されたタスク
        """
        task = Task(name, description)
        if process_id:
            task.parent_process_id = process_id
        
        self.tasks[task.id] = task
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """タスクを取得"""
        return self.tasks.get(task_id)
    
    def get_tasks_by_process(self, process_id: str) -> List[Task]:
        """プロセスIDでタスクを取得"""
        return [task for task in self.tasks.values() 
                if task.parent_process_id == process_id]
    
    def get_tasks_by_status(self, status: str) -> List[Task]:
        """ステータスでタスクを取得"""
        return [task for task in self.tasks.values() 
                if task.status == status]
    
    def get_tasks_by_priority(self, priority: int) -> List[Task]:
        """優先度でタスクを取得"""
        return [task for task in self.tasks.values() 
                if task.priority == priority]
    
    def update_task(self, task: Task) -> bool:
        """タスクを更新"""
        if task.validate() and task.id in self.tasks:
            task.update_timestamp()
            self.tasks[task.id] = task
            return True
        return False
    
    def delete_task(self, task_id: str) -> bool:
        """タスクを削除"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False
    
    def get_all_tasks(self) -> List[Task]:
        """全タスクを取得"""
        return list(self.tasks.values())
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """タスク統計を取得"""
        total = len(self.tasks)
        if total == 0:
            return {'total': 0}
        
        status_counts = {}
        priority_counts = {}
        
        for task in self.tasks.values():
            # ステータス別カウント
            status_counts[task.status] = status_counts.get(task.status, 0) + 1
            
            # 優先度別カウント
            priority_counts[task.priority] = priority_counts.get(task.priority, 0) + 1
        
        completed = status_counts.get(TaskStatus.COMPLETED, 0)
        completion_rate = (completed / total) * 100 if total > 0 else 0
        
        return {
            'total': total,
            'completion_rate': completion_rate,
            'status_counts': status_counts,
            'priority_counts': priority_counts
        }