"""
データ永続化基盤
シングルトンパターンによるJSON形式データストア
"""

import json
import os
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import threading
import tempfile


class DataStoreError(Exception):
    """データストア例外クラス"""
    pass


class DataStore:
    """
    データストアクラス（シングルトン）
    JSON形式でデータを永続化
    """
    
    _instance: Optional['DataStore'] = None
    _lock = threading.Lock()
    
    def __new__(cls, data_dir: str = None) -> 'DataStore':
        """シングルトンインスタンスを取得"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, data_dir: str = None):
        """
        データストアの初期化
        
        Args:
            data_dir: データディレクトリパス
        """
        if self._initialized:
            return
        
        self.data_dir = Path(data_dir) if data_dir else Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # データファイルパス
        self.projects_file = self.data_dir / "projects.json"
        self.phases_file = self.data_dir / "phases.json"
        self.processes_file = self.data_dir / "processes.json"
        self.tasks_file = self.data_dir / "tasks.json"
        self.notifications_file = self.data_dir / "notifications.json"
        self.settings_file = self.data_dir / "settings.json"
        self.metadata_file = self.data_dir / "metadata.json"
        
        # ロック機構
        self._file_locks = {
            'projects': threading.RLock(),
            'phases': threading.RLock(),
            'processes': threading.RLock(),
            'tasks': threading.RLock(),
            'notifications': threading.RLock(),
            'settings': threading.RLock(),
            'metadata': threading.RLock()
        }
        
        # メタデータ管理
        self.metadata = self._load_metadata()
        
        self._initialized = True
    
    def _load_metadata(self) -> Dict[str, Any]:
        """メタデータを読み込み"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                # メタデータ読み込み失敗時はデフォルト値を使用
                pass
        
        # デフォルトメタデータ
        default_metadata = {
            'created_at': datetime.now().isoformat(),
            'last_modified': datetime.now().isoformat(),
            'version': '1.0.0',
            'file_versions': {
                'projects': 1,
                'phases': 1,
                'processes': 1,
                'tasks': 1,
                'notifications': 1,
                'settings': 1
            },
            'backup_count': 0
        }
        
        self._save_metadata(default_metadata)
        return default_metadata
    
    def _save_metadata(self, metadata: Dict[str, Any]) -> None:
        """メタデータを保存"""
        metadata['last_modified'] = datetime.now().isoformat()
        
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except IOError as e:
            raise DataStoreError(f"メタデータ保存エラー: {e}")
    
    def _load_json_file(self, file_path: Path, entity_type: str) -> Dict[str, Any]:
        """
        JSONファイルを安全に読み込み
        
        Args:
            file_path: ファイルパス
            entity_type: エンティティタイプ（ロック用）
            
        Returns:
            読み込まれたデータ
        """
        with self._file_locks[entity_type]:
            if not file_path.exists():
                return {}
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
            except (json.JSONDecodeError, IOError) as e:
                # バックアップファイルから復旧を試行
                backup_path = self._get_backup_path(file_path)
                if backup_path.exists():
                    try:
                        with open(backup_path, 'r', encoding='utf-8') as f:
                            return json.load(f)
                    except (json.JSONDecodeError, IOError):
                        pass
                
                raise DataStoreError(f"ファイル読み込みエラー {file_path}: {e}")
    
    def _save_json_file(self, file_path: Path, data: Dict[str, Any], entity_type: str) -> None:
        """
        JSONファイルを安全に保存
        
        Args:
            file_path: ファイルパス
            data: 保存するデータ
            entity_type: エンティティタイプ（ロック用）
        """
        with self._file_locks[entity_type]:
            # バックアップを作成
            if file_path.exists():
                backup_path = self._get_backup_path(file_path)
                shutil.copy2(file_path, backup_path)
            
            # 一時ファイルに書き込み後、アトミックに移動
            temp_file = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode='w', 
                    encoding='utf-8', 
                    dir=file_path.parent,
                    delete=False,
                    suffix='.tmp'
                ) as f:
                    temp_file = Path(f.name)
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                # アトミックに移動
                if os.name == 'nt':  # Windows
                    if file_path.exists():
                        file_path.unlink()
                    temp_file.rename(file_path)
                else:  # Unix系
                    temp_file.rename(file_path)
                
                # メタデータを更新
                self.metadata['file_versions'][entity_type] += 1
                self._save_metadata(self.metadata)
                
            except (IOError, OSError) as e:
                # 一時ファイルのクリーンアップ
                if temp_file and temp_file.exists():
                    temp_file.unlink()
                raise DataStoreError(f"ファイル保存エラー {file_path}: {e}")
    
    def _get_backup_path(self, file_path: Path) -> Path:
        """バックアップファイルパスを取得"""
        return file_path.with_suffix(f'{file_path.suffix}.backup')
    
    # プロジェクト関連操作
    def load_projects(self) -> Dict[str, Dict[str, Any]]:
        """プロジェクトデータを読み込み"""
        return self._load_json_file(self.projects_file, 'projects')
    
    def save_projects(self, projects: Dict[str, Dict[str, Any]]) -> None:
        """プロジェクトデータを保存"""
        self._save_json_file(self.projects_file, projects, 'projects')
    
    def save_project(self, project_id: str, project_data: Dict[str, Any]) -> None:
        """単一プロジェクトを保存"""
        projects = self.load_projects()
        projects[project_id] = project_data
        self.save_projects(projects)
    
    def delete_project(self, project_id: str) -> bool:
        """プロジェクトを削除"""
        projects = self.load_projects()
        if project_id in projects:
            del projects[project_id]
            self.save_projects(projects)
            return True
        return False
    
    # フェーズ関連操作
    def load_phases(self) -> Dict[str, Dict[str, Any]]:
        """フェーズデータを読み込み"""
        return self._load_json_file(self.phases_file, 'phases')
    
    def save_phases(self, phases: Dict[str, Dict[str, Any]]) -> None:
        """フェーズデータを保存"""
        self._save_json_file(self.phases_file, phases, 'phases')
    
    def save_phase(self, phase_id: str, phase_data: Dict[str, Any]) -> None:
        """単一フェーズを保存"""
        phases = self.load_phases()
        phases[phase_id] = phase_data
        self.save_phases(phases)
    
    def delete_phase(self, phase_id: str) -> bool:
        """フェーズを削除"""
        phases = self.load_phases()
        if phase_id in phases:
            del phases[phase_id]
            self.save_phases(phases)
            return True
        return False
    
    # プロセス関連操作
    def load_processes(self) -> Dict[str, Dict[str, Any]]:
        """プロセスデータを読み込み"""
        return self._load_json_file(self.processes_file, 'processes')
    
    def save_processes(self, processes: Dict[str, Dict[str, Any]]) -> None:
        """プロセスデータを保存"""
        self._save_json_file(self.processes_file, processes, 'processes')
    
    def save_process(self, process_id: str, process_data: Dict[str, Any]) -> None:
        """単一プロセスを保存"""
        processes = self.load_processes()
        processes[process_id] = process_data
        self.save_processes(processes)
    
    def delete_process(self, process_id: str) -> bool:
        """プロセスを削除"""
        processes = self.load_processes()
        if process_id in processes:
            del processes[process_id]
            self.save_processes(processes)
            return True
        return False
    
    # タスク関連操作
    def load_tasks(self) -> Dict[str, Dict[str, Any]]:
        """タスクデータを読み込み"""
        return self._load_json_file(self.tasks_file, 'tasks')
    
    def save_tasks(self, tasks: Dict[str, Dict[str, Any]]) -> None:
        """タスクデータを保存"""
        self._save_json_file(self.tasks_file, tasks, 'tasks')
    
    def save_task(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """単一タスクを保存"""
        tasks = self.load_tasks()
        tasks[task_id] = task_data
        self.save_tasks(tasks)
    
    def delete_task(self, task_id: str) -> bool:
        """タスクを削除"""
        tasks = self.load_tasks()
        if task_id in tasks:
            del tasks[task_id]
            self.save_tasks(tasks)
            return True
        return False
    
    # 通知関連操作
    def load_notifications(self) -> Dict[str, Dict[str, Any]]:
        """通知データを読み込み"""
        return self._load_json_file(self.notifications_file, 'notifications')
    
    def save_notifications(self, notifications: Dict[str, Dict[str, Any]]) -> None:
        """通知データを保存"""
        self._save_json_file(self.notifications_file, notifications, 'notifications')
    
    def save_notification(self, notification_id: str, notification_data: Dict[str, Any]) -> None:
        """単一通知を保存"""
        notifications = self.load_notifications()
        notifications[notification_id] = notification_data
        self.save_notifications(notifications)
    
    def delete_notification(self, notification_id: str) -> bool:
        """通知を削除"""
        notifications = self.load_notifications()
        if notification_id in notifications:
            del notifications[notification_id]
            self.save_notifications(notifications)
            return True
        return False
    
    # 設定関連操作
    def load_settings(self) -> Dict[str, Any]:
        """設定データを読み込み"""
        return self._load_json_file(self.settings_file, 'settings')
    
    def save_settings(self, settings: Dict[str, Any]) -> None:
        """設定データを保存"""
        self._save_json_file(self.settings_file, settings, 'settings')
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """設定値を取得"""
        settings = self.load_settings()
        return settings.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> None:
        """設定値を保存"""
        settings = self.load_settings()
        settings[key] = value
        self.save_settings(settings)
    
    # バックアップ・復旧操作
    def create_full_backup(self, backup_dir: str = None) -> str:
        """
        全データのバックアップを作成
        
        Args:
            backup_dir: バックアップディレクトリ
            
        Returns:
            バックアップディレクトリパス
        """
        if not backup_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = f"backup_{timestamp}"
        
        backup_path = Path(backup_dir)
        backup_path.mkdir(exist_ok=True)
        
        # 全データファイルをコピー
        files_to_backup = [
            self.projects_file,
            self.phases_file,
            self.processes_file,
            self.tasks_file,
            self.notifications_file,
            self.settings_file,
            self.metadata_file
        ]
        
        for file_path in files_to_backup:
            if file_path.exists():
                shutil.copy2(file_path, backup_path / file_path.name)
        
        # バックアップメタデータを更新
        self.metadata['backup_count'] += 1
        self._save_metadata(self.metadata)
        
        return str(backup_path)
    
    def restore_from_backup(self, backup_dir: str) -> bool:
        """
        バックアップからデータを復旧
        
        Args:
            backup_dir: バックアップディレクトリ
            
        Returns:
            復旧成功の可否
        """
        backup_path = Path(backup_dir)
        if not backup_path.exists():
            return False
        
        # 復旧前に現在のデータをバックアップ
        self.create_full_backup(f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # バックアップファイルを復旧
        files_to_restore = [
            'projects.json',
            'phases.json',
            'processes.json',
            'tasks.json',
            'notifications.json',
            'settings.json',
            'metadata.json'
        ]
        
        try:
            for filename in files_to_restore:
                backup_file = backup_path / filename
                target_file = self.data_dir / filename
                
                if backup_file.exists():
                    shutil.copy2(backup_file, target_file)
            
            # メタデータを再読み込み
            self.metadata = self._load_metadata()
            return True
            
        except (IOError, OSError) as e:
            raise DataStoreError(f"バックアップ復旧エラー: {e}")
    
    # データ整合性チェック
    def validate_data_integrity(self) -> Dict[str, Any]:
        """
        データ整合性をチェック
        
        Returns:
            整合性チェック結果
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'statistics': {}
        }
        
        try:
            # 各データファイルの読み込みテスト
            projects = self.load_projects()
            phases = self.load_phases()
            processes = self.load_processes()
            tasks = self.load_tasks()
            notifications = self.load_notifications()
            
            # 統計情報
            result['statistics'] = {
                'projects': len(projects),
                'phases': len(phases),
                'processes': len(processes),
                'tasks': len(tasks),
                'notifications': len(notifications)
            }
            
            # 参照整合性チェック
            # フェーズ→プロジェクト参照チェック
            for phase_id, phase_data in phases.items():
                project_id = phase_data.get('parent_project_id')
                if project_id and project_id not in projects:
                    result['errors'].append(f"フェーズ {phase_id} が存在しないプロジェクト {project_id} を参照")
            
            # プロセス→フェーズ参照チェック
            for process_id, process_data in processes.items():
                phase_id = process_data.get('parent_phase_id')
                if phase_id and phase_id not in phases:
                    result['errors'].append(f"プロセス {process_id} が存在しないフェーズ {phase_id} を参照")
            
            # タスク→プロセス参照チェック
            for task_id, task_data in tasks.items():
                process_id = task_data.get('parent_process_id')
                if process_id and process_id not in processes:
                    result['errors'].append(f"タスク {task_id} が存在しないプロセス {process_id} を参照")
            
            if result['errors']:
                result['valid'] = False
            
        except DataStoreError as e:
            result['valid'] = False
            result['errors'].append(f"データ読み込みエラー: {e}")
        
        return result
    
    # ユーティリティメソッド
    def get_data_statistics(self) -> Dict[str, Any]:
        """データ統計情報を取得"""
        try:
            projects = self.load_projects()
            phases = self.load_phases()
            processes = self.load_processes()
            tasks = self.load_tasks()
            notifications = self.load_notifications()
            
            # ファイルサイズ
            file_sizes = {}
            for name, file_path in [
                ('projects', self.projects_file),
                ('phases', self.phases_file),
                ('processes', self.processes_file),
                ('tasks', self.tasks_file),
                ('notifications', self.notifications_file),
                ('settings', self.settings_file)
            ]:
                if file_path.exists():
                    file_sizes[name] = file_path.stat().st_size
                else:
                    file_sizes[name] = 0
            
            return {
                'counts': {
                    'projects': len(projects),
                    'phases': len(phases),
                    'processes': len(processes),
                    'tasks': len(tasks),
                    'notifications': len(notifications)
                },
                'file_sizes': file_sizes,
                'total_size': sum(file_sizes.values()),
                'metadata': self.metadata.copy(),
                'data_dir': str(self.data_dir)
            }
            
        except DataStoreError:
            return {'error': 'データ読み込みエラー'}
    
    def cleanup_orphaned_data(self) -> Dict[str, int]:
        """孤立データをクリーンアップ"""
        result = {
            'deleted_phases': 0,
            'deleted_processes': 0,
            'deleted_tasks': 0,
            'deleted_notifications': 0
        }
        
        try:
            projects = self.load_projects()
            phases = self.load_phases()
            processes = self.load_processes()
            tasks = self.load_tasks()
            notifications = self.load_notifications()
            
            # 孤立フェーズを削除
            orphaned_phases = [
                phase_id for phase_id, phase_data in phases.items()
                if phase_data.get('parent_project_id') not in projects
            ]
            for phase_id in orphaned_phases:
                del phases[phase_id]
                result['deleted_phases'] += 1
            
            if orphaned_phases:
                self.save_phases(phases)
            
            # 孤立プロセスを削除
            orphaned_processes = [
                process_id for process_id, process_data in processes.items()
                if process_data.get('parent_phase_id') not in phases
            ]
            for process_id in orphaned_processes:
                del processes[process_id]
                result['deleted_processes'] += 1
            
            if orphaned_processes:
                self.save_processes(processes)
            
            # 孤立タスクを削除
            orphaned_tasks = [
                task_id for task_id, task_data in tasks.items()
                if task_data.get('parent_process_id') not in processes
            ]
            for task_id in orphaned_tasks:
                del tasks[task_id]
                result['deleted_tasks'] += 1
            
            if orphaned_tasks:
                self.save_tasks(tasks)
            
            # 孤立通知を削除（対象エンティティが存在しない通知）
            all_entity_ids = set(projects.keys()) | set(phases.keys()) | set(processes.keys()) | set(tasks.keys())
            orphaned_notifications = [
                notification_id for notification_id, notification_data in notifications.items()
                if notification_data.get('entity_id') not in all_entity_ids
            ]
            for notification_id in orphaned_notifications:
                del notifications[notification_id]
                result['deleted_notifications'] += 1
            
            if orphaned_notifications:
                self.save_notifications(notifications)
            
        except DataStoreError:
            pass  # エラーは無視して続行
        
        return result
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"DataStore(data_dir='{self.data_dir}')"
    
    def __repr__(self) -> str:
        """詳細文字列表現"""
        stats = self.get_data_statistics()
        return f"DataStore(data_dir='{self.data_dir}', counts={stats.get('counts', {})})"