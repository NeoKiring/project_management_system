"""
GUIダイアログ統合管理
各種データ編集ダイアログの統合インターフェース
"""

from .project_dialog import ProjectDialog
from .phase_dialog import PhaseDialog
from .process_dialog import ProcessDialog
from .task_dialog import TaskDialog

__all__ = [
    'ProjectDialog',
    'PhaseDialog', 
    'ProcessDialog',
    'TaskDialog'
]

class DialogManager:
    """ダイアログ管理クラス"""
    
    def __init__(self, parent_window, project_management_system):
        """
        ダイアログ管理の初期化
        
        Args:
            parent_window: 親ウィンドウ
            project_management_system: プロジェクト管理システム
        """
        self.parent = parent_window
        self.pms = project_management_system
        
        # ダイアログインスタンスキャッシュ
        self._dialog_cache = {}
    
    def get_project_dialog(self, project=None, mode='edit'):
        """プロジェクトダイアログを取得"""
        key = f"project_{mode}_{id(project) if project else 'new'}"
        
        if key not in self._dialog_cache:
            self._dialog_cache[key] = ProjectDialog(
                self.parent, self.pms, project, mode
            )
        
        return self._dialog_cache[key]
    
    def get_phase_dialog(self, phase=None, project_id=None, mode='edit'):
        """フェーズダイアログを取得"""
        key = f"phase_{mode}_{id(phase) if phase else 'new'}_{project_id}"
        
        if key not in self._dialog_cache:
            self._dialog_cache[key] = PhaseDialog(
                self.parent, self.pms, phase, project_id, mode
            )
        
        return self._dialog_cache[key]
    
    def get_process_dialog(self, process=None, phase_id=None, mode='edit'):
        """プロセスダイアログを取得"""
        key = f"process_{mode}_{id(process) if process else 'new'}_{phase_id}"
        
        if key not in self._dialog_cache:
            self._dialog_cache[key] = ProcessDialog(
                self.parent, self.pms, process, phase_id, mode
            )
        
        return self._dialog_cache[key]
    
    def get_task_dialog(self, task=None, process_id=None, mode='edit'):
        """タスクダイアログを取得"""
        key = f"task_{mode}_{id(task) if task else 'new'}_{process_id}"
        
        if key not in self._dialog_cache:
            self._dialog_cache[key] = TaskDialog(
                self.parent, self.pms, task, process_id, mode
            )
        
        return self._dialog_cache[key]
    
    def clear_cache(self):
        """ダイアログキャッシュをクリア"""
        for dialog in self._dialog_cache.values():
            if dialog is not None:
                dialog.close()
        self._dialog_cache.clear()
    
    def show_project_dialog(self, project=None, mode='edit'):
        """プロジェクトダイアログを表示"""
        dialog = self.get_project_dialog(project, mode)
        dialog.reset_form()  # フォームをリセット
        return dialog.exec()
    
    def show_phase_dialog(self, phase=None, project_id=None, mode='edit'):
        """フェーズダイアログを表示"""
        dialog = self.get_phase_dialog(phase, project_id, mode)
        dialog.reset_form()
        return dialog.exec()
    
    def show_process_dialog(self, process=None, phase_id=None, mode='edit'):
        """プロセスダイアログを表示"""
        dialog = self.get_process_dialog(process, phase_id, mode)
        dialog.reset_form()
        return dialog.exec()
    
    def show_task_dialog(self, task=None, process_id=None, mode='edit'):
        """タスクダイアログを表示"""
        dialog = self.get_task_dialog(task, process_id, mode)
        dialog.reset_form()
        return dialog.exec()
