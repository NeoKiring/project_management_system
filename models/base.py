"""
基底エンティティクラス
プロジェクト管理システムの全エンティティの基底クラス
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import json


class BaseEntity(ABC):
    """
    全エンティティの基底クラス
    共通属性と基本操作を提供
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        基底エンティティの初期化
        
        Args:
            name: エンティティ名
            description: 説明（オプション）
        """
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.description: str = description
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
    
    def update_timestamp(self) -> None:
        """更新時刻を現在時刻に更新"""
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        エンティティを辞書形式に変換
        
        Returns:
            エンティティの辞書表現
        """
        base_dict = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        # サブクラスの追加属性を取得
        additional_dict = self._to_dict_additional()
        base_dict.update(additional_dict)
        
        return base_dict
    
    @abstractmethod
    def _to_dict_additional(self) -> Dict[str, Any]:
        """
        サブクラス固有の属性を辞書に変換
        サブクラスで実装必須
        
        Returns:
            サブクラス固有属性の辞書
        """
        pass
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseEntity':
        """
        辞書からエンティティを復元
        
        Args:
            data: エンティティの辞書表現
            
        Returns:
            復元されたエンティティ
        """
        # 基底クラスでは実装せず、サブクラスで実装
        raise NotImplementedError("サブクラスで実装してください")
    
    def validate(self) -> bool:
        """
        エンティティの妥当性検証
        
        Returns:
            妥当性チェック結果
        """
        if not self.name or not self.name.strip():
            return False
        
        if not self.id:
            return False
            
        # サブクラス固有の検証
        return self._validate_additional()
    
    @abstractmethod
    def _validate_additional(self) -> bool:
        """
        サブクラス固有の妥当性検証
        サブクラスで実装必須
        
        Returns:
            妥当性チェック結果
        """
        pass
    
    def clone(self) -> 'BaseEntity':
        """
        エンティティの複製を作成（新しいIDで）
        
        Returns:
            複製されたエンティティ
        """
        data = self.to_dict()
        # 新しいIDを生成
        data['id'] = str(uuid.uuid4())
        data['created_at'] = datetime.now().isoformat()
        data['updated_at'] = datetime.now().isoformat()
        
        return self.from_dict(data)
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"{self.__class__.__name__}(id={self.id[:8]}, name='{self.name}')"
    
    def __repr__(self) -> str:
        """詳細文字列表現"""
        return f"{self.__class__.__name__}(id='{self.id}', name='{self.name}', created_at='{self.created_at}')"
    
    def __eq__(self, other) -> bool:
        """等価性比較（IDベース）"""
        if not isinstance(other, BaseEntity):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """ハッシュ値（IDベース）"""
        return hash(self.id)


class EntityManager(ABC):
    """
    エンティティ管理の基底クラス
    CRUD操作の共通インターフェースを提供
    """
    
    def __init__(self):
        self._entities: Dict[str, BaseEntity] = {}
    
    def add(self, entity: BaseEntity) -> bool:
        """
        エンティティを追加
        
        Args:
            entity: 追加するエンティティ
            
        Returns:
            追加成功の可否
        """
        if not entity.validate():
            return False
            
        if entity.id in self._entities:
            return False  # 既に存在
            
        self._entities[entity.id] = entity
        return True
    
    def get(self, entity_id: str) -> Optional[BaseEntity]:
        """
        IDでエンティティを取得
        
        Args:
            entity_id: エンティティID
            
        Returns:
            エンティティ（存在しない場合はNone）
        """
        return self._entities.get(entity_id)
    
    def update(self, entity: BaseEntity) -> bool:
        """
        エンティティを更新
        
        Args:
            entity: 更新するエンティティ
            
        Returns:
            更新成功の可否
        """
        if not entity.validate():
            return False
            
        if entity.id not in self._entities:
            return False  # 存在しない
            
        entity.update_timestamp()
        self._entities[entity.id] = entity
        return True
    
    def delete(self, entity_id: str) -> bool:
        """
        エンティティを削除
        
        Args:
            entity_id: 削除するエンティティID
            
        Returns:
            削除成功の可否
        """
        if entity_id in self._entities:
            del self._entities[entity_id]
            return True
        return False
    
    def list_all(self) -> list[BaseEntity]:
        """
        全エンティティを取得
        
        Returns:
            エンティティのリスト
        """
        return list(self._entities.values())
    
    def count(self) -> int:
        """
        エンティティ数を取得
        
        Returns:
            エンティティの総数
        """
        return len(self._entities)
    
    def clear(self) -> None:
        """全エンティティを削除"""
        self._entities.clear()
    
    def find_by_name(self, name: str) -> list[BaseEntity]:
        """
        名前でエンティティを検索
        
        Args:
            name: 検索する名前
            
        Returns:
            マッチするエンティティのリスト
        """
        return [entity for entity in self._entities.values() 
                if name.lower() in entity.name.lower()]


class StatusEnum:
    """ステータス管理用の基底クラス"""
    
    @classmethod
    def get_all_values(cls) -> list[str]:
        """全ステータス値を取得"""
        return [value for key, value in cls.__dict__.items() 
                if not key.startswith('_') and not callable(value)]
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """ステータス値の妥当性チェック"""
        return value in cls.get_all_values()


class ProjectStatus(StatusEnum):
    """プロジェクトステータス定義"""
    NOT_STARTED = "未着手"
    IN_PROGRESS = "進行中"
    COMPLETED = "完了"
    SUSPENDED = "中止"
    ON_HOLD = "保留"


class TaskStatus(StatusEnum):
    """タスクステータス定義"""
    NOT_STARTED = "未着手"
    IN_PROGRESS = "進行中"
    COMPLETED = "完了"
    CANNOT_HANDLE = "対応不能"