"""
プロセスモデル
タスクを管理する中間階層
"""

from datetime import datetime, date
from typing import Dict, Any, Optional, List
from .base import BaseEntity
from .task import Task, TaskStatus


class ProcessStatus:
    """プロセスステータス定義"""
    NOT_STARTED = "未着手"
    IN_PROGRESS = "進行中"
    COMPLETED = "完了"


class Process(BaseEntity):
    """
    プロセスクラス
    複数のタスクを管理する中間階層
    """
    
    def __init__(self, name: str, description: str = "", assignee: str = ""):
        """
        プロセスの初期化
        
        Args:
            name: プロセス名
            description: プロセス説明
            assignee: 担当者（必須）
        """
        super().__init__(name, description)
        self.assignee: str = assignee  # 必須項目
        self.parent_phase_id: Optional[str] = None
        self.start_date: Optional[date] = None
        self.end_date: Optional[date] = None
        self.estimated_hours: Optional[float] = None
        self.actual_hours: Optional[float] = None
        self.progress: float = 0.0  # 0-100の進捗率
        self.is_progress_manual: bool = True  # 手動進捗管理かどうか
        self.tasks: List[str] = []  # タスクIDのリスト
        self.notes: str = ""
        self.priority: int = 3  # 1(高) ~ 5(低)
    
    def set_assignee(self, assignee: str) -> bool:
        """
        担当者を設定
        
        Args:
            assignee: 担当者名
            
        Returns:
            設定成功の可否
        """
        if assignee and assignee.strip():
            self.assignee = assignee.strip()
            self.update_timestamp()
            return True
        return False
    
    def set_dates(self, start_date: Optional[date], end_date: Optional[date]) -> bool:
        """
        期間を設定
        
        Args:
            start_date: 開始日
            end_date: 終了日
            
        Returns:
            設定成功の可否
        """
        # 日付の妥当性チェック
        if start_date and end_date and start_date > end_date:
            return False
        
        self.start_date = start_date
        self.end_date = end_date
        self.update_timestamp()
        return True
    
    def set_progress(self, progress: float, is_manual: bool = True) -> bool:
        """
        進捗率を設定
        
        Args:
            progress: 進捗率（0-100）
            is_manual: 手動設定かどうか
            
        Returns:
            設定成功の可否
        """
        if 0.0 <= progress <= 100.0:
            self.progress = progress
            self.is_progress_manual = is_manual
            self.update_timestamp()
            return True
        return False
    
    def calculate_progress_from_tasks(self, task_manager) -> float:
        """
        タスクから進捗率を自動計算
        
        Args:
            task_manager: タスク管理オブジェクト
            
        Returns:
            計算された進捗率
        """
        if not self.tasks:
            return 0.0
        
        actionable_tasks = []
        completed_tasks = 0
        
        for task_id in self.tasks:
            task = task_manager.get_task(task_id)
            if task and task.is_actionable():  # 対応不能タスクは除外
                actionable_tasks.append(task)
                if task.is_completed():
                    completed_tasks += 1
        
        if not actionable_tasks:
            return 0.0
        
        calculated_progress = (completed_tasks / len(actionable_tasks)) * 100.0
        return round(calculated_progress, 1)
    
    def update_progress_from_tasks(self, task_manager) -> bool:
        """
        タスクから進捗率を更新（自動計算モードの場合）
        
        Args:
            task_manager: タスク管理オブジェクト
            
        Returns:
            更新成功の可否
        """
        if not self.is_progress_manual:
            calculated_progress = self.calculate_progress_from_tasks(task_manager)
            return self.set_progress(calculated_progress, False)
        return True
    
    def get_status(self) -> str:
        """
        進捗率に基づくステータスを取得
        
        Returns:
            プロセスステータス
        """
        if self.progress == 0.0:
            return ProcessStatus.NOT_STARTED
        elif self.progress == 100.0:
            return ProcessStatus.COMPLETED
        else:
            return ProcessStatus.IN_PROGRESS
    
    def add_task(self, task_id: str) -> bool:
        """
        タスクを追加
        
        Args:
            task_id: タスクID
            
        Returns:
            追加成功の可否
        """
        if task_id not in self.tasks:
            self.tasks.append(task_id)
            self.update_timestamp()
            return True
        return False
    
    def remove_task(self, task_id: str) -> bool:
        """
        タスクを削除
        
        Args:
            task_id: タスクID
            
        Returns:
            削除成功の可否
        """
        if task_id in self.tasks:
            self.tasks.remove(task_id)
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
    
    def calculate_total_task_hours(self, task_manager) -> Dict[str, Optional[float]]:
        """
        タスクの合計工数を計算
        
        Args:
            task_manager: タスク管理オブジェクト
            
        Returns:
            予想工数と実績工数の合計
        """
        estimated_total = 0.0
        actual_total = 0.0
        estimated_count = 0
        actual_count = 0
        
        for task_id in self.tasks:
            task = task_manager.get_task(task_id)
            if task:
                if task.estimated_hours is not None:
                    estimated_total += task.estimated_hours
                    estimated_count += 1
                
                if task.actual_hours is not None:
                    actual_total += task.actual_hours
                    actual_count += 1
        
        return {
            'estimated_total': estimated_total if estimated_count > 0 else None,
            'actual_total': actual_total if actual_count > 0 else None,
            'estimated_count': estimated_count,
            'actual_count': actual_count
        }
    
    def is_overdue(self) -> bool:
        """
        期限超過かどうか
        
        Returns:
            期限超過の可否
        """
        if self.end_date and self.progress < 100.0:
            return date.today() > self.end_date
        return False
    
    def get_remaining_days(self) -> Optional[int]:
        """
        残り日数を取得
        
        Returns:
            残り日数（期限未設定の場合はNone）
        """
        if self.end_date:
            delta = self.end_date - date.today()
            return delta.days
        return None
    
    def _to_dict_additional(self) -> Dict[str, Any]:
        """プロセス固有属性を辞書に変換"""
        return {
            'assignee': self.assignee,
            'parent_phase_id': self.parent_phase_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'progress': self.progress,
            'is_progress_manual': self.is_progress_manual,
            'tasks': self.tasks.copy(),
            'notes': self.notes,
            'priority': self.priority
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Process':
        """辞書からプロセスを復元"""
        process = cls(
            data['name'],
            data.get('description', ''),
            data.get('assignee', '')
        )
        
        # 基底属性を復元
        process.id = data['id']
        process.created_at = datetime.fromisoformat(data['created_at'])
        process.updated_at = datetime.fromisoformat(data['updated_at'])
        
        # プロセス固有属性を復元
        process.parent_phase_id = data.get('parent_phase_id')
        process.start_date = date.fromisoformat(data['start_date']) if data.get('start_date') else None
        process.end_date = date.fromisoformat(data['end_date']) if data.get('end_date') else None
        process.estimated_hours = data.get('estimated_hours')
        process.actual_hours = data.get('actual_hours')
        process.progress = data.get('progress', 0.0)
        process.is_progress_manual = data.get('is_progress_manual', True)
        process.tasks = data.get('tasks', []).copy()
        process.notes = data.get('notes', '')
        process.priority = data.get('priority', 3)
        
        return process
    
    def _validate_additional(self) -> bool:
        """プロセス固有の妥当性検証"""
        # 担当者必須チェック
        if not self.assignee or not self.assignee.strip():
            return False
        
        # 進捗率の妥当性
        if not (0.0 <= self.progress <= 100.0):
            return False
        
        # 日付の妥当性
        if self.start_date and self.end_date and self.start_date > self.end_date:
            return False
        
        # 工数の妥当性
        if self.estimated_hours is not None and self.estimated_hours < 0:
            return False
        
        if self.actual_hours is not None and self.actual_hours < 0:
            return False
        
        # 優先度の妥当性
        if not (1 <= self.priority <= 5):
            return False
        
        return True
    
    def get_summary(self, task_manager=None) -> Dict[str, Any]:
        """プロセスサマリーを取得"""
        summary = {
            'name': self.name,
            'assignee': self.assignee,
            'progress': self.progress,
            'status': self.get_status(),
            'task_count': len(self.tasks),
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_overdue': self.is_overdue(),
            'remaining_days': self.get_remaining_days(),
            'priority': self.priority,
            'is_progress_manual': self.is_progress_manual
        }
        
        if task_manager:
            task_hours = self.calculate_total_task_hours(task_manager)
            summary.update(task_hours)
            
            # タスク統計
            completed_tasks = 0
            actionable_tasks = 0
            for task_id in self.tasks:
                task = task_manager.get_task(task_id)
                if task:
                    if task.is_actionable():
                        actionable_tasks += 1
                        if task.is_completed():
                            completed_tasks += 1
            
            summary.update({
                'actionable_tasks': actionable_tasks,
                'completed_tasks': completed_tasks,
                'task_completion_rate': (completed_tasks / actionable_tasks * 100) if actionable_tasks > 0 else 0
            })
        
        return summary
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"Process(name='{self.name}', assignee='{self.assignee}', progress={self.progress}%)"


class ProcessManager:
    """プロセス管理クラス"""
    
    def __init__(self):
        self.processes: Dict[str, Process] = {}
    
    def create_process(self, name: str, assignee: str, description: str = "", phase_id: str = None) -> Process:
        """
        新しいプロセスを作成
        
        Args:
            name: プロセス名
            assignee: 担当者
            description: プロセス説明
            phase_id: 親フェーズID
            
        Returns:
            作成されたプロセス
        """
        process = Process(name, description, assignee)
        if phase_id:
            process.parent_phase_id = phase_id
        
        self.processes[process.id] = process
        return process
    
    def get_process(self, process_id: str) -> Optional[Process]:
        """プロセスを取得"""
        return self.processes.get(process_id)
    
    def get_processes_by_phase(self, phase_id: str) -> List[Process]:
        """フェーズIDでプロセスを取得"""
        return [process for process in self.processes.values() 
                if process.parent_phase_id == phase_id]
    
    def get_processes_by_assignee(self, assignee: str) -> List[Process]:
        """担当者でプロセスを取得"""
        return [process for process in self.processes.values() 
                if process.assignee == assignee]
    
    def get_overdue_processes(self) -> List[Process]:
        """期限超過プロセスを取得"""
        return [process for process in self.processes.values() 
                if process.is_overdue()]
    
    def update_process(self, process: Process) -> bool:
        """プロセスを更新"""
        if process.validate() and process.id in self.processes:
            process.update_timestamp()
            self.processes[process.id] = process
            return True
        return False
    
    def delete_process(self, process_id: str) -> bool:
        """プロセスを削除"""
        if process_id in self.processes:
            del self.processes[process_id]
            return True
        return False
    
    def get_all_processes(self) -> List[Process]:
        """全プロセスを取得"""
        return list(self.processes.values())
    
    def get_process_statistics(self) -> Dict[str, Any]:
        """プロセス統計を取得"""
        total = len(self.processes)
        if total == 0:
            return {'total': 0}
        
        completed = len([p for p in self.processes.values() if p.get_status() == ProcessStatus.COMPLETED])
        in_progress = len([p for p in self.processes.values() if p.get_status() == ProcessStatus.IN_PROGRESS])
        overdue = len(self.get_overdue_processes())
        
        # 担当者別統計
        assignee_counts = {}
        for process in self.processes.values():
            assignee_counts[process.assignee] = assignee_counts.get(process.assignee, 0) + 1
        
        return {
            'total': total,
            'completed': completed,
            'in_progress': in_progress,
            'not_started': total - completed - in_progress,
            'overdue': overdue,
            'completion_rate': (completed / total) * 100 if total > 0 else 0,
            'assignee_counts': assignee_counts
        }