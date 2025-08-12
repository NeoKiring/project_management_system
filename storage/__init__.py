# ====================
# storage/__init__.py
# ====================
"""
永続化層パッケージ
データストレージ機能
"""

from .data_store import DataStore, DataStoreError

__version__ = "1.0.0"

__all__ = [
    'DataStore',
    'DataStoreError'
]
