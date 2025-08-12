"""
プロジェクトモデル
階層構造の最上位レベル
"""

from datetime import datetime, date
from typing import Dict, Any, Optional, List
from .base import BaseEntity, ProjectStatus
from .phase import Phase, PhaseStatus


class Project(BaseEntity):
    """
    プロジェクトクラス
    複数のフェーズを管理する最上位階層
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        プロジェクトの初期化
        
        Args:
            name: プロジェクト名
            description: プロジェクト説明
        """
        super().__init__(name, description)
        self.status: str = ProjectStatus.NOT_STARTED
        self.is_status_manual: bool = False  # 自動状態判定をデフォルトに
        self.start_date: Optional[date] = None
        self.end_date: Optional[date] = None
        self.progress: float = 0.0  # 0-100の進捗率（自動計算）
        self.phases: List[str] = []  # フェーズIDのリスト
        self.notes: str = ""
        self.priority: int = 3  # 1(高) ~ 5(低)
        self.budget: Optional[float] = None  # 予算
        self.actual_cost: Optional[float] = None  # 実績コスト
        self.manager: str = ""  # プロジェクトマネージャー
        self.stakeholders: List[str] = []  # ステークホルダーリスト
        self.tags: List[str] = []  # タグリスト
        self.risk_level: int = 2  # 1(低) ~ 3(高)
    
    def set_status(self, new_status: str, is_manual: bool = True) -> bool:
        """
        プロジェクトステータスを設定
        
        Args:
            new_status: 新しいステータス
            is_manual: 手動設定かどうか
            
        Returns:
            設定成功の可否
        """
        if not ProjectStatus.is_valid(new_status):
            return False
        
        self.status = new_status
        self.is_status_manual = is_manual
        self.update_timestamp()
        return True
    
    def calculate_status_from_phases(self, phase_manager) -> str:
        """
        フェーズから自動ステータス判定
        
        Args:
            phase_manager: フェーズ管理オブジェクト
            
        Returns:
            計算されたステータス
        """
        if not self.phases:
            return ProjectStatus.NOT_STARTED
        
        phase_statuses = []
        for phase_id in self.phases:
            phase = phase_manager.get_phase(phase_id)
            if phase:
                phase_statuses.append(phase.get_status())
        
        if not phase_statuses:
            return ProjectStatus.NOT_STARTED
        
        # 全フェーズが完了なら完了
        if all(status == PhaseStatus.COMPLETED for status in phase_statuses):
            return ProjectStatus.COMPLETED
        
        # 1つでも進行中があれば進行中
        if any(status == PhaseStatus.IN_PROGRESS for status in phase_statuses):
            return ProjectStatus.IN_PROGRESS
        
        # 全て未着手なら未着手
        if all(status == PhaseStatus.NOT_STARTED for status in phase_statuses):
            return ProjectStatus.NOT_STARTED
        
        # その他の場合（一部完了、一部未着手）は進行中
        return ProjectStatus.IN_PROGRESS
    
    def update_status_from_phases(self, phase_manager) -> bool:
        """
        フェーズからステータスを自動更新（自動モードの場合）
        
        Args:
            phase_manager: フェーズ管理オブジェクト
            
        Returns:
            更新成功の可否
        """
        if not self.is_status_manual:
            calculated_status = self.calculate_status_from_phases(phase_manager)
            if calculated_status != self.status:
                return self.set_status(calculated_status, False)
        return True
    
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
    
    def calculate_progress_from_phases(self, phase_manager) -> float:
        """
        フェーズの期間ベースで進捗率を自動計算
        
        Args:
            phase_manager: フェーズ管理オブジェクト
            
        Returns:
            計算された進捗率
        """
        if not self.phases:
            return 0.0
        
        # 期間をウェイトとして使用
        total_weight = 0.0
        weighted_progress = 0.0
        
        for phase_id in self.phases:
            phase = phase_manager.get_phase(phase_id)
            if phase:
                # フェーズの期間を計算（終了日-開始日、未設定なら1日とする）
                date_range = phase.get_date_range(None)  # プロセス管理は今回は使わない
                
                if phase.end_date:
                    if date_range.get('start_date'):
                        duration = (phase.end_date - date_range['start_date']).days + 1
                    else:
                        duration = 1  # 開始日未設定なら1日とする
                else:
                    duration = 1  # 終了日未設定なら1日とする
                
                weight = max(duration, 1)  # 最小1日
                total_weight += weight
                weighted_progress += phase.progress * weight
        
        if total_weight > 0:
            calculated_progress = weighted_progress / total_weight
            return round(calculated_progress, 1)
        
        # 期間ベースの計算ができない場合は単純平均
        phase_count = len([p for p in self.phases 
                          if phase_manager.get_phase(p) is not None])
        if phase_count > 0:
            simple_average = sum(phase_manager.get_phase(pid).progress 
                               for pid in self.phases 
                               if phase_manager.get_phase(pid)) / phase_count
            return round(simple_average, 1)
        
        return 0.0
    
    def update_progress_from_phases(self, phase_manager) -> bool:
        """
        フェーズから進捗率を更新
        
        Args:
            phase_manager: フェーズ管理オブジェクト
            
        Returns:
            更新成功の可否
        """
        old_progress = self.progress
        self.progress = self.calculate_progress_from_phases(phase_manager)
        
        if old_progress != self.progress:
            self.update_timestamp()
            return True
        return False
    
    def add_phase(self, phase_id: str) -> bool:
        """
        フェーズを追加
        
        Args:
            phase_id: フェーズID
            
        Returns:
            追加成功の可否
        """
        if phase_id not in self.phases:
            self.phases.append(phase_id)
            self.update_timestamp()
            return True
        return False
    
    def remove_phase(self, phase_id: str) -> bool:
        """
        フェーズを削除
        
        Args:
            phase_id: フェーズID
            
        Returns:
            削除成功の可否
        """
        if phase_id in self.phases:
            self.phases.remove(phase_id)
            self.update_timestamp()
            return True
        return False
    
    def get_date_range(self, phase_manager) -> Dict[str, Optional[date]]:
        """
        プロジェクトの期間を子フェーズから自動算出
        
        Args:
            phase_manager: フェーズ管理オブジェクト
            
        Returns:
            開始日と終了日
        """
        start_dates = []
        end_dates = []
        
        for phase_id in self.phases:
            phase = phase_manager.get_phase(phase_id)
            if phase:
                date_range = phase.get_date_range(None)
                if date_range.get('start_date'):
                    start_dates.append(date_range['start_date'])
                if date_range.get('end_date'):
                    end_dates.append(date_range['end_date'])
        
        # 手動設定の日付も考慮
        if self.start_date:
            start_dates.append(self.start_date)
        if self.end_date:
            end_dates.append(self.end_date)
        
        return {
            'start_date': min(start_dates) if start_dates else self.start_date,
            'end_date': max(end_dates) if end_dates else self.end_date
        }
    
    def add_stakeholder(self, stakeholder: str) -> bool:
        """
        ステークホルダーを追加
        
        Args:
            stakeholder: ステークホルダー名
            
        Returns:
            追加成功の可否
        """
        stakeholder = stakeholder.strip()
        if stakeholder and stakeholder not in self.stakeholders:
            self.stakeholders.append(stakeholder)
            self.update_timestamp()
            return True
        return False
    
    def remove_stakeholder(self, stakeholder: str) -> bool:
        """
        ステークホルダーを削除
        
        Args:
            stakeholder: ステークホルダー名
            
        Returns:
            削除成功の可否
        """
        if stakeholder in self.stakeholders:
            self.stakeholders.remove(stakeholder)
            self.update_timestamp()
            return True
        return False
    
    def add_tag(self, tag: str) -> bool:
        """
        タグを追加
        
        Args:
            tag: タグ名
            
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
            tag: タグ名
            
        Returns:
            削除成功の可否
        """
        if tag in self.tags:
            self.tags.remove(tag)
            self.update_timestamp()
            return True
        return False
    
    def set_budget(self, budget: float) -> bool:
        """
        予算を設定
        
        Args:
            budget: 予算額
            
        Returns:
            設定成功の可否
        """
        if budget >= 0:
            self.budget = budget
            self.update_timestamp()
            return True
        return False
    
    def set_actual_cost(self, cost: float) -> bool:
        """
        実績コストを設定
        
        Args:
            cost: 実績コスト
            
        Returns:
            設定成功の可否
        """
        if cost >= 0:
            self.actual_cost = cost
            self.update_timestamp()
            return True
        return False
    
    def get_budget_ratio(self) -> Optional[float]:
        """
        予算対実績比率を取得
        
        Returns:
            比率（Noneの場合は計算不可）
        """
        if self.budget and self.actual_cost and self.budget > 0:
            return self.actual_cost / self.budget
        return None
    
    def is_overdue(self) -> bool:
        """
        期限超過かどうか
        
        Returns:
            期限超過の可否
        """
        if self.end_date and self.status != ProjectStatus.COMPLETED:
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
    
    def get_duration_days(self) -> Optional[int]:
        """
        プロジェクト期間（日数）を取得
        
        Returns:
            期間日数（未設定の場合はNone）
        """
        if self.start_date and self.end_date:
            delta = self.end_date - self.start_date
            return delta.days + 1
        return None
    
    def get_phase_statistics(self, phase_manager) -> Dict[str, Any]:
        """
        プロジェクト内のフェーズ統計を取得
        
        Args:
            phase_manager: フェーズ管理オブジェクト
            
        Returns:
            フェーズ統計情報
        """
        total_phases = len(self.phases)
        if total_phases == 0:
            return {'total': 0}
        
        completed_phases = 0
        in_progress_phases = 0
        overdue_phases = 0
        
        for phase_id in self.phases:
            phase = phase_manager.get_phase(phase_id)
            if phase:
                status = phase.get_status()
                if status == PhaseStatus.COMPLETED:
                    completed_phases += 1
                elif status == PhaseStatus.IN_PROGRESS:
                    in_progress_phases += 1
                
                if phase.is_overdue():
                    overdue_phases += 1
        
        return {
            'total': total_phases,
            'completed': completed_phases,
            'in_progress': in_progress_phases,
            'not_started': total_phases - completed_phases - in_progress_phases,
            'overdue': overdue_phases,
            'completion_rate': (completed_phases / total_phases) * 100 if total_phases > 0 else 0
        }
    
    def _to_dict_additional(self) -> Dict[str, Any]:
        """プロジェクト固有属性を辞書に変換"""
        return {
            'status': self.status,
            'is_status_manual': self.is_status_manual,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'progress': self.progress,
            'phases': self.phases.copy(),
            'notes': self.notes,
            'priority': self.priority,
            'budget': self.budget,
            'actual_cost': self.actual_cost,
            'manager': self.manager,
            'stakeholders': self.stakeholders.copy(),
            'tags': self.tags.copy(),
            'risk_level': self.risk_level
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """辞書からプロジェクトを復元"""
        project = cls(data['name'], data.get('description', ''))
        
        # 基底属性を復元
        project.id = data['id']
        project.created_at = datetime.fromisoformat(data['created_at'])
        project.updated_at = datetime.fromisoformat(data['updated_at'])
        
        # プロジェクト固有属性を復元
        project.status = data.get('status', ProjectStatus.NOT_STARTED)
        project.is_status_manual = data.get('is_status_manual', False)
        project.start_date = date.fromisoformat(data['start_date']) if data.get('start_date') else None
        project.end_date = date.fromisoformat(data['end_date']) if data.get('end_date') else None
        project.progress = data.get('progress', 0.0)
        project.phases = data.get('phases', []).copy()
        project.notes = data.get('notes', '')
        project.priority = data.get('priority', 3)
        project.budget = data.get('budget')
        project.actual_cost = data.get('actual_cost')
        project.manager = data.get('manager', '')
        project.stakeholders = data.get('stakeholders', []).copy()
        project.tags = data.get('tags', []).copy()
        project.risk_level = data.get('risk_level', 2)
        
        return project
    
    def _validate_additional(self) -> bool:
        """プロジェクト固有の妥当性検証"""
        # ステータスの妥当性
        if not ProjectStatus.is_valid(self.status):
            return False
        
        # 進捗率の妥当性
        if not (0.0 <= self.progress <= 100.0):
            return False
        
        # 日付の妥当性
        if self.start_date and self.end_date and self.start_date > self.end_date:
            return False
        
        # 予算・コストの妥当性
        if self.budget is not None and self.budget < 0:
            return False
        
        if self.actual_cost is not None and self.actual_cost < 0:
            return False
        
        # 優先度の妥当性
        if not (1 <= self.priority <= 5):
            return False
        
        # リスクレベルの妥当性
        if not (1 <= self.risk_level <= 3):
            return False
        
        return True
    
    def get_summary(self, phase_manager=None) -> Dict[str, Any]:
        """プロジェクトサマリーを取得"""
        summary = {
            'name': self.name,
            'status': self.status,
            'progress': self.progress,
            'phase_count': len(self.phases),
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_overdue': self.is_overdue(),
            'remaining_days': self.get_remaining_days(),
            'duration_days': self.get_duration_days(),
            'priority': self.priority,
            'risk_level': self.risk_level,
            'manager': self.manager,
            'stakeholder_count': len(self.stakeholders),
            'tag_count': len(self.tags),
            'budget': self.budget,
            'actual_cost': self.actual_cost,
            'budget_ratio': self.get_budget_ratio(),
            'is_status_manual': self.is_status_manual
        }
        
        if phase_manager:
            # 期間情報（自動算出）
            date_range = self.get_date_range(phase_manager)
            summary.update({
                'calculated_start_date': date_range['start_date'].isoformat() if date_range['start_date'] else None,
                'calculated_end_date': date_range['end_date'].isoformat() if date_range['end_date'] else None
            })
            
            # フェーズ統計
            phase_stats = self.get_phase_statistics(phase_manager)
            summary.update({f'phase_{key}': value for key, value in phase_stats.items()})
        
        return summary
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"Project(name='{self.name}', status='{self.status}', progress={self.progress}%)"


class ProjectManager:
    """プロジェクト管理クラス"""
    
    def __init__(self):
        self.projects: Dict[str, Project] = {}
    
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
        project = Project(name, description)
        if manager:
            project.manager = manager
        
        self.projects[project.id] = project
        return project
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """プロジェクトを取得"""
        return self.projects.get(project_id)
    
    def get_projects_by_status(self, status: str) -> List[Project]:
        """ステータスでプロジェクトを取得"""
        return [project for project in self.projects.values() 
                if project.status == status]
    
    def get_projects_by_manager(self, manager: str) -> List[Project]:
        """マネージャーでプロジェクトを取得"""
        return [project for project in self.projects.values() 
                if project.manager == manager]
    
    def get_overdue_projects(self) -> List[Project]:
        """期限超過プロジェクトを取得"""
        return [project for project in self.projects.values() 
                if project.is_overdue()]
    
    def get_projects_by_tag(self, tag: str) -> List[Project]:
        """タグでプロジェクトを取得"""
        return [project for project in self.projects.values() 
                if tag in project.tags]
    
    def update_project(self, project: Project) -> bool:
        """プロジェクトを更新"""
        if project.validate() and project.id in self.projects:
            project.update_timestamp()
            self.projects[project.id] = project
            return True
        return False
    
    def delete_project(self, project_id: str) -> bool:
        """プロジェクトを削除"""
        if project_id in self.projects:
            del self.projects[project_id]
            return True
        return False
    
    def get_all_projects(self) -> List[Project]:
        """全プロジェクトを取得"""
        return list(self.projects.values())
    
    def get_project_statistics(self) -> Dict[str, Any]:
        """プロジェクト統計を取得"""
        total = len(self.projects)
        if total == 0:
            return {'total': 0}
        
        status_counts = {}
        priority_counts = {}
        risk_counts = {}
        
        overdue_count = 0
        total_budget = 0.0
        total_actual_cost = 0.0
        budget_projects = 0
        
        for project in self.projects.values():
            # ステータス別カウント
            status_counts[project.status] = status_counts.get(project.status, 0) + 1
            
            # 優先度別カウント
            priority_counts[project.priority] = priority_counts.get(project.priority, 0) + 1
            
            # リスクレベル別カウント
            risk_counts[project.risk_level] = risk_counts.get(project.risk_level, 0) + 1
            
            # 期限超過カウント
            if project.is_overdue():
                overdue_count += 1
            
            # 予算統計
            if project.budget is not None:
                total_budget += project.budget
                budget_projects += 1
            
            if project.actual_cost is not None:
                total_actual_cost += project.actual_cost
        
        completed = status_counts.get(ProjectStatus.COMPLETED, 0)
        completion_rate = (completed / total) * 100 if total > 0 else 0
        
        return {
            'total': total,
            'completion_rate': completion_rate,
            'overdue': overdue_count,
            'status_counts': status_counts,
            'priority_counts': priority_counts,
            'risk_counts': risk_counts,
            'total_budget': total_budget if budget_projects > 0 else None,
            'total_actual_cost': total_actual_cost,
            'average_budget': total_budget / budget_projects if budget_projects > 0 else None,
            'budget_projects': budget_projects
        }