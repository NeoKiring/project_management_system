"""
フェーズモデル
プロセスを管理する上位階層
"""

from datetime import datetime, date
from typing import Dict, Any, Optional, List
from .base import BaseEntity
from .process import Process, ProcessStatus


class PhaseStatus:
    """フェーズステータス定義"""
    NOT_STARTED = "未着手"
    IN_PROGRESS = "進行中"
    COMPLETED = "完了"


class Phase(BaseEntity):
    """
    フェーズクラス
    複数のプロセスを管理する上位階層
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        フェーズの初期化
        
        Args:
            name: フェーズ名
            description: フェーズ説明
        """
        super().__init__(name, description)
        self.parent_project_id: Optional[str] = None
        self.end_date: Optional[date] = None
        self.progress: float = 0.0  # 0-100の進捗率（自動計算）
        self.processes: List[str] = []  # プロセスIDのリスト
        self.notes: str = ""
        self.priority: int = 3  # 1(高) ~ 5(低)
        self.milestone: str = ""  # マイルストーン名
        self.deliverables: List[str] = []  # 成果物リスト
    
    def set_end_date(self, end_date: Optional[date]) -> bool:
        """
        終了日を設定
        
        Args:
            end_date: 終了日
            
        Returns:
            設定成功の可否
        """
        self.end_date = end_date
        self.update_timestamp()
        return True
    
    def calculate_progress_from_processes(self, process_manager) -> float:
        """
        プロセスの工数ベースで進捗率を自動計算
        
        Args:
            process_manager: プロセス管理オブジェクト
            
        Returns:
            計算された進捗率
        """
        if not self.processes:
            return 0.0
        
        total_estimated_hours = 0.0
        weighted_progress = 0.0
        
        for process_id in self.processes:
            process = process_manager.get_process(process_id)
            if process:
                # 予想工数をウェイトとして使用（未設定の場合は1.0とする）
                weight = process.estimated_hours if process.estimated_hours else 1.0
                total_estimated_hours += weight
                weighted_progress += process.progress * weight
        
        if total_estimated_hours > 0:
            calculated_progress = weighted_progress / total_estimated_hours
            return round(calculated_progress, 1)
        
        # 予想工数が全て未設定の場合は単純平均
        process_count = len([p for p in self.processes 
                           if process_manager.get_process(p) is not None])
        if process_count > 0:
            simple_average = sum(process_manager.get_process(pid).progress 
                               for pid in self.processes 
                               if process_manager.get_process(pid)) / process_count
            return round(simple_average, 1)
        
        return 0.0
    
    def update_progress_from_processes(self, process_manager) -> bool:
        """
        プロセスから進捗率を更新
        
        Args:
            process_manager: プロセス管理オブジェクト
            
        Returns:
            更新成功の可否
        """
        old_progress = self.progress
        self.progress = self.calculate_progress_from_processes(process_manager)
        
        if old_progress != self.progress:
            self.update_timestamp()
            return True
        return False
    
    def get_status(self) -> str:
        """
        進捗率に基づくステータスを取得
        
        Returns:
            フェーズステータス
        """
        if self.progress == 0.0:
            return PhaseStatus.NOT_STARTED
        elif self.progress == 100.0:
            return PhaseStatus.COMPLETED
        else:
            return PhaseStatus.IN_PROGRESS
    
    def add_process(self, process_id: str) -> bool:
        """
        プロセスを追加
        
        Args:
            process_id: プロセスID
            
        Returns:
            追加成功の可否
        """
        if process_id not in self.processes:
            self.processes.append(process_id)
            self.update_timestamp()
            return True
        return False
    
    def remove_process(self, process_id: str) -> bool:
        """
        プロセスを削除
        
        Args:
            process_id: プロセスID
            
        Returns:
            削除成功の可否
        """
        if process_id in self.processes:
            self.processes.remove(process_id)
            self.update_timestamp()
            return True
        return False
    
    def add_deliverable(self, deliverable: str) -> bool:
        """
        成果物を追加
        
        Args:
            deliverable: 成果物名
            
        Returns:
            追加成功の可否
        """
        deliverable = deliverable.strip()
        if deliverable and deliverable not in self.deliverables:
            self.deliverables.append(deliverable)
            self.update_timestamp()
            return True
        return False
    
    def remove_deliverable(self, deliverable: str) -> bool:
        """
        成果物を削除
        
        Args:
            deliverable: 成果物名
            
        Returns:
            削除成功の可否
        """
        if deliverable in self.deliverables:
            self.deliverables.remove(deliverable)
            self.update_timestamp()
            return True
        return False
    
    def calculate_total_estimated_hours(self, process_manager) -> Optional[float]:
        """
        プロセスの予想工数合計を計算
        
        Args:
            process_manager: プロセス管理オブジェクト
            
        Returns:
            予想工数合計（未設定の場合はNone）
        """
        total_hours = 0.0
        has_estimation = False
        
        for process_id in self.processes:
            process = process_manager.get_process(process_id)
            if process and process.estimated_hours is not None:
                total_hours += process.estimated_hours
                has_estimation = True
        
        return total_hours if has_estimation else None
    
    def calculate_total_actual_hours(self, process_manager) -> Optional[float]:
        """
        プロセスの実績工数合計を計算
        
        Args:
            process_manager: プロセス管理オブジェクト
            
        Returns:
            実績工数合計（未設定の場合はNone）
        """
        total_hours = 0.0
        has_actual = False
        
        for process_id in self.processes:
            process = process_manager.get_process(process_id)
            if process and process.actual_hours is not None:
                total_hours += process.actual_hours
                has_actual = True
        
        return total_hours if has_actual else None
    
    def get_date_range(self, process_manager) -> Dict[str, Optional[date]]:
        """
        フェーズの期間を子プロセスから自動算出
        
        Args:
            process_manager: プロセス管理オブジェクト
            
        Returns:
            開始日と終了日
        """
        start_dates = []
        end_dates = []
        
        for process_id in self.processes:
            process = process_manager.get_process(process_id)
            if process:
                if process.start_date:
                    start_dates.append(process.start_date)
                if process.end_date:
                    end_dates.append(process.end_date)
        
        return {
            'start_date': min(start_dates) if start_dates else None,
            'end_date': max(end_dates) if end_dates else self.end_date
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
    
    def get_process_statistics(self, process_manager) -> Dict[str, Any]:
        """
        フェーズ内のプロセス統計を取得
        
        Args:
            process_manager: プロセス管理オブジェクト
            
        Returns:
            プロセス統計情報
        """
        total_processes = len(self.processes)
        if total_processes == 0:
            return {'total': 0}
        
        completed_processes = 0
        in_progress_processes = 0
        overdue_processes = 0
        
        for process_id in self.processes:
            process = process_manager.get_process(process_id)
            if process:
                status = process.get_status()
                if status == ProcessStatus.COMPLETED:
                    completed_processes += 1
                elif status == ProcessStatus.IN_PROGRESS:
                    in_progress_processes += 1
                
                if process.is_overdue():
                    overdue_processes += 1
        
        return {
            'total': total_processes,
            'completed': completed_processes,
            'in_progress': in_progress_processes,
            'not_started': total_processes - completed_processes - in_progress_processes,
            'overdue': overdue_processes,
            'completion_rate': (completed_processes / total_processes) * 100 if total_processes > 0 else 0
        }
    
    def _to_dict_additional(self) -> Dict[str, Any]:
        """フェーズ固有属性を辞書に変換"""
        return {
            'parent_project_id': self.parent_project_id,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'progress': self.progress,
            'processes': self.processes.copy(),
            'notes': self.notes,
            'priority': self.priority,
            'milestone': self.milestone,
            'deliverables': self.deliverables.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Phase':
        """辞書からフェーズを復元"""
        phase = cls(data['name'], data.get('description', ''))
        
        # 基底属性を復元
        phase.id = data['id']
        phase.created_at = datetime.fromisoformat(data['created_at'])
        phase.updated_at = datetime.fromisoformat(data['updated_at'])
        
        # フェーズ固有属性を復元
        phase.parent_project_id = data.get('parent_project_id')
        phase.end_date = date.fromisoformat(data['end_date']) if data.get('end_date') else None
        phase.progress = data.get('progress', 0.0)
        phase.processes = data.get('processes', []).copy()
        phase.notes = data.get('notes', '')
        phase.priority = data.get('priority', 3)
        phase.milestone = data.get('milestone', '')
        phase.deliverables = data.get('deliverables', []).copy()
        
        return phase
    
    def _validate_additional(self) -> bool:
        """フェーズ固有の妥当性検証"""
        # 進捗率の妥当性
        if not (0.0 <= self.progress <= 100.0):
            return False
        
        # 優先度の妥当性
        if not (1 <= self.priority <= 5):
            return False
        
        return True
    
    def get_summary(self, process_manager=None) -> Dict[str, Any]:
        """フェーズサマリーを取得"""
        summary = {
            'name': self.name,
            'progress': self.progress,
            'status': self.get_status(),
            'process_count': len(self.processes),
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_overdue': self.is_overdue(),
            'remaining_days': self.get_remaining_days(),
            'priority': self.priority,
            'milestone': self.milestone,
            'deliverable_count': len(self.deliverables)
        }
        
        if process_manager:
            # 期間情報
            date_range = self.get_date_range(process_manager)
            summary.update(date_range)
            
            # 工数情報
            summary.update({
                'total_estimated_hours': self.calculate_total_estimated_hours(process_manager),
                'total_actual_hours': self.calculate_total_actual_hours(process_manager)
            })
            
            # プロセス統計
            process_stats = self.get_process_statistics(process_manager)
            summary.update({f'process_{key}': value for key, value in process_stats.items()})
        
        return summary
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"Phase(name='{self.name}', progress={self.progress}%, processes={len(self.processes)})"


class PhaseManager:
    """フェーズ管理クラス"""
    
    def __init__(self):
        self.phases: Dict[str, Phase] = {}
    
    def create_phase(self, name: str, description: str = "", project_id: str = None) -> Phase:
        """
        新しいフェーズを作成
        
        Args:
            name: フェーズ名
            description: フェーズ説明
            project_id: 親プロジェクトID
            
        Returns:
            作成されたフェーズ
        """
        phase = Phase(name, description)
        if project_id:
            phase.parent_project_id = project_id
        
        self.phases[phase.id] = phase
        return phase
    
    def get_phase(self, phase_id: str) -> Optional[Phase]:
        """フェーズを取得"""
        return self.phases.get(phase_id)
    
    def get_phases_by_project(self, project_id: str) -> List[Phase]:
        """プロジェクトIDでフェーズを取得"""
        return [phase for phase in self.phases.values() 
                if phase.parent_project_id == project_id]
    
    def get_overdue_phases(self) -> List[Phase]:
        """期限超過フェーズを取得"""
        return [phase for phase in self.phases.values() 
                if phase.is_overdue()]
    
    def update_phase(self, phase: Phase) -> bool:
        """フェーズを更新"""
        if phase.validate() and phase.id in self.phases:
            phase.update_timestamp()
            self.phases[phase.id] = phase
            return True
        return False
    
    def delete_phase(self, phase_id: str) -> bool:
        """フェーズを削除"""
        if phase_id in self.phases:
            del self.phases[phase_id]
            return True
        return False
    
    def get_all_phases(self) -> List[Phase]:
        """全フェーズを取得"""
        return list(self.phases.values())
    
    def get_phase_statistics(self) -> Dict[str, Any]:
        """フェーズ統計を取得"""
        total = len(self.phases)
        if total == 0:
            return {'total': 0}
        
        completed = len([p for p in self.phases.values() if p.get_status() == PhaseStatus.COMPLETED])
        in_progress = len([p for p in self.phases.values() if p.get_status() == PhaseStatus.IN_PROGRESS])
        overdue = len(self.get_overdue_phases())
        
        return {
            'total': total,
            'completed': completed,
            'in_progress': in_progress,
            'not_started': total - completed - in_progress,
            'overdue': overdue,
            'completion_rate': (completed / total) * 100 if total > 0 else 0
        }