"""
外部連携層統合インターフェース
Excel連携機能の統合API
"""

import os
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from ..core.logger import ProjectLogger, LogCategory
from ..core.error_handler import handle_errors, ValidationError, RecoveryStrategy
from ..config.settings import get_settings

# 条件付きインポート
try:
    from .excel_importer import ExcelImporter, ImportResult, ExcelFormatType
    IMPORT_AVAILABLE = True
except ImportError:
    ExcelImporter = None
    ImportResult = None
    ExcelFormatType = None
    IMPORT_AVAILABLE = False

try:
    from .excel_exporter import ExcelExporter, ExportResult, ExportFormat, ExportOptions
    EXPORT_AVAILABLE = True
except ImportError:
    ExcelExporter = None
    ExportResult = None
    ExportFormat = None
    ExportOptions = None
    EXPORT_AVAILABLE = False


class ExcelManager:
    """
    Excel連携統合管理クラス
    インポート・エクスポート機能を統合したシンプルなAPI
    """
    
    def __init__(self, project_management_system=None):
        """
        Excel管理の初期化
        
        Args:
            project_management_system: プロジェクト管理システムのインスタンス
        """
        self.pms = project_management_system
        self.logger = ProjectLogger()
        self.settings = get_settings()
        
        # インポーター・エクスポーター初期化
        self.importer = None
        self.exporter = None
        
        if IMPORT_AVAILABLE:
            try:
                self.importer = ExcelImporter(self.pms)
            except Exception as e:
                self.logger.warning(
                    LogCategory.SYSTEM,
                    f"Excelインポーター初期化失敗: {e}",
                    module="external"
                )
        
        if EXPORT_AVAILABLE:
            try:
                self.exporter = ExcelExporter(self.pms)
            except Exception as e:
                self.logger.warning(
                    LogCategory.SYSTEM,
                    f"Excelエクスポーター初期化失敗: {e}",
                    module="external"
                )
        
        # 機能利用可能性チェック
        self.import_enabled = self.importer is not None
        self.export_enabled = self.exporter is not None
        
        self.logger.info(
            LogCategory.SYSTEM,
            f"Excel連携管理初期化完了 (インポート: {'有効' if self.import_enabled else '無効'}, "
            f"エクスポート: {'有効' if self.export_enabled else '無効'})",
            module="external"
        )
    
    # ==================== インポート機能 ====================
    
    @handle_errors(recovery_strategy=RecoveryStrategy.NONE)
    def import_excel(self, file_path: str, 
                    format_type: str = None,
                    project_name: str = None,
                    auto_detect: bool = True,
                    **options) -> Optional['ImportResult']:
        """
        Excelファイルからデータをインポート
        
        Args:
            file_path: Excelファイルパス
            format_type: フォーマット種別（Noneの場合は自動検出）
            project_name: プロジェクト名（指定しない場合は自動生成）
            auto_detect: フォーマット自動検出を使用するか
            **options: その他のインポートオプション
            
        Returns:
            インポート結果（失敗時はNone）
        """
        if not self.import_enabled:
            self.logger.error(
                LogCategory.ERROR,
                "Excelインポート機能が利用できません（openpyxlライブラリが必要）",
                module="external"
            )
            return None
        
        # ファイル存在チェック
        if not os.path.exists(file_path):
            self.logger.error(
                LogCategory.ERROR,
                f"インポート対象ファイルが見つかりません: {file_path}",
                module="external"
            )
            return None
        
        # ファイルサイズチェック
        file_size = os.path.getsize(file_path)
        max_size = self.settings.external.max_import_rows * 1024  # 概算
        if file_size > max_size * 1000:  # 大きすぎる場合は警告
            self.logger.warning(
                LogCategory.PERFORMANCE,
                f"大容量ファイルのインポート: {file_size:,} bytes",
                module="external",
                file_path=file_path
            )
        
        # インポートオプション設定
        import_options = options.copy()
        if project_name:
            import_options['project_name'] = project_name
        
        # フォーマット自動検出
        if auto_detect and not format_type:
            format_type = None  # インポーターに自動検出させる
        
        self.logger.info(
            LogCategory.DATA,
            f"Excelインポート実行: {file_path} (フォーマット: {format_type or '自動検出'})",
            module="external",
            file_size=file_size,
            options=import_options
        )
        
        # インポート実行
        try:
            result = self.importer.import_from_file(file_path, format_type, import_options)
            
            if result.success:
                self.logger.info(
                    LogCategory.DATA,
                    f"Excelインポート成功: {sum(result.imported_counts.values())}個のエンティティ",
                    module="external",
                    imported_counts=result.imported_counts,
                    processing_time=result.processing_time
                )
            else:
                self.logger.error(
                    LogCategory.ERROR,
                    f"Excelインポート失敗: {len(result.errors)}個のエラー",
                    module="external",
                    errors=result.errors[:5]  # 最初の5個のエラーのみログ
                )
            
            return result
            
        except Exception as e:
            self.logger.error(
                LogCategory.ERROR,
                f"Excelインポート例外: {e}",
                module="external",
                exception=e,
                file_path=file_path
            )
            return None
    
    def get_supported_import_formats(self) -> List[str]:
        """対応インポートフォーマット一覧を取得"""
        if not self.import_enabled:
            return []
        
        return [
            ExcelFormatType.STANDARD,
            ExcelFormatType.MSPROJECT,
            ExcelFormatType.SIMPLE,
            ExcelFormatType.CUSTOM
        ]
    
    def detect_excel_format(self, file_path: str) -> Optional[str]:
        """Excelファイルのフォーマットを検出"""
        if not self.import_enabled:
            return None
        
        try:
            import openpyxl
            workbook = openpyxl.load_workbook(file_path, read_only=True)
            detected_format = self.importer.detector.detect_format(workbook)
            workbook.close()
            return detected_format
        except Exception as e:
            self.logger.error(
                LogCategory.ERROR,
                f"フォーマット検出エラー: {e}",
                module="external",
                file_path=file_path
            )
            return None
    
    # ==================== エクスポート機能 ====================
    
    @handle_errors(recovery_strategy=RecoveryStrategy.NONE)
    def export_excel(self, file_path: str,
                    format_type: str = None,
                    project_ids: List[str] = None,
                    include_completed: bool = True,
                    **options) -> Optional['ExportResult']:
        """
        データをExcelファイルにエクスポート
        
        Args:
            file_path: 出力ファイルパス
            format_type: エクスポートフォーマット
            project_ids: エクスポート対象プロジェクトID（Noneの場合は全プロジェクト）
            include_completed: 完了プロジェクトを含むか
            **options: その他のエクスポートオプション
            
        Returns:
            エクスポート結果（失敗時はNone）
        """
        if not self.export_enabled:
            self.logger.error(
                LogCategory.ERROR,
                "Excelエクスポート機能が利用できません（xlsxwriter または openpyxl ライブラリが必要）",
                module="external"
            )
            return None
        
        # デフォルトフォーマット設定
        if not format_type:
            format_type = ExportFormat.STANDARD
        
        # エクスポートオプション作成
        export_options = ExportOptions()
        export_options.include_completed = include_completed
        
        if project_ids:
            export_options.project_ids = project_ids
        
        # カスタムオプション適用
        for key, value in options.items():
            if hasattr(export_options, key):
                setattr(export_options, key, value)
        
        # 出力ディレクトリ作成
        output_dir = Path(file_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(
            LogCategory.DATA,
            f"Excelエクスポート実行: {file_path} (フォーマット: {format_type})",
            module="external",
            project_count=len(project_ids) if project_ids else "全て",
            options=export_options.to_dict()
        )
        
        # エクスポート実行
        try:
            result = self.exporter.export_to_file(file_path, format_type, export_options)
            
            if result.success:
                self.logger.info(
                    LogCategory.DATA,
                    f"Excelエクスポート成功: {result.file_size:,} bytes, "
                    f"{sum(result.exported_counts.values())}個のエンティティ",
                    module="external",
                    exported_counts=result.exported_counts,
                    processing_time=result.processing_time
                )
            else:
                self.logger.error(
                    LogCategory.ERROR,
                    f"Excelエクスポート失敗: {len(result.errors)}個のエラー",
                    module="external",
                    errors=result.errors
                )
            
            return result
            
        except Exception as e:
            self.logger.error(
                LogCategory.ERROR,
                f"Excelエクスポート例外: {e}",
                module="external",
                exception=e,
                file_path=file_path
            )
            return None
    
    def get_supported_export_formats(self) -> List[str]:
        """対応エクスポートフォーマット一覧を取得"""
        if not self.export_enabled:
            return []
        
        return [
            ExportFormat.STANDARD,
            ExportFormat.MSPROJECT,
            ExportFormat.SIMPLE,
            ExportFormat.CUSTOM
        ]
    
    def create_export_options(self, **kwargs) -> Optional['ExportOptions']:
        """エクスポートオプションを作成"""
        if not self.export_enabled:
            return None
        
        options = ExportOptions()
        
        for key, value in kwargs.items():
            if hasattr(options, key):
                setattr(options, key, value)
        
        return options
    
    # ==================== 一括処理機能 ====================
    
    def bulk_import(self, file_paths: List[str], **options) -> Dict[str, 'ImportResult']:
        """複数ファイルの一括インポート"""
        if not self.import_enabled:
            return {}
        
        results = {}
        
        for file_path in file_paths:
            try:
                result = self.import_excel(file_path, **options)
                results[file_path] = result
            except Exception as e:
                self.logger.error(
                    LogCategory.ERROR,
                    f"一括インポートエラー: {file_path} - {e}",
                    module="external"
                )
                results[file_path] = None
        
        success_count = sum(1 for r in results.values() if r and r.success)
        
        self.logger.info(
            LogCategory.DATA,
            f"一括インポート完了: {success_count}/{len(file_paths)}件成功",
            module="external"
        )
        
        return results
    
    def bulk_export(self, base_path: str, format_types: List[str], **options) -> Dict[str, 'ExportResult']:
        """複数フォーマットでの一括エクスポート"""
        if not self.export_enabled:
            return {}
        
        results = {}
        base_path = Path(base_path)
        
        for format_type in format_types:
            try:
                file_path = base_path.with_suffix(f'.{format_type}.xlsx')
                result = self.export_excel(str(file_path), format_type, **options)
                results[format_type] = result
            except Exception as e:
                self.logger.error(
                    LogCategory.ERROR,
                    f"一括エクスポートエラー: {format_type} - {e}",
                    module="external"
                )
                results[format_type] = None
        
        success_count = sum(1 for r in results.values() if r and r.success)
        
        self.logger.info(
            LogCategory.DATA,
            f"一括エクスポート完了: {success_count}/{len(format_types)}件成功",
            module="external"
        )
        
        return results
    
    # ==================== 統計・ユーティリティ ====================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Excel連携統計を取得"""
        stats = {
            'import_enabled': self.import_enabled,
            'export_enabled': self.export_enabled,
            'supported_import_formats': self.get_supported_import_formats(),
            'supported_export_formats': self.get_supported_export_formats()
        }
        
        if self.import_enabled and self.importer:
            stats['import_statistics'] = self.importer.get_import_statistics()
        
        if self.export_enabled and self.exporter:
            stats['export_statistics'] = self.exporter.get_export_statistics()
        
        return stats
    
    def validate_file_format(self, file_path: str) -> Dict[str, Any]:
        """ファイルフォーマットの妥当性を検証"""
        result = {
            'valid': False,
            'file_exists': False,
            'is_excel': False,
            'detected_format': None,
            'file_size': 0,
            'errors': []
        }
        
        try:
            # ファイル存在チェック
            if not os.path.exists(file_path):
                result['errors'].append("ファイルが存在しません")
                return result
            
            result['file_exists'] = True
            result['file_size'] = os.path.getsize(file_path)
            
            # Excelファイルチェック
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in ['.xlsx', '.xls']:
                result['errors'].append(f"対応していないファイル形式: {file_ext}")
                return result
            
            result['is_excel'] = True
            
            # フォーマット検出
            if self.import_enabled:
                detected_format = self.detect_excel_format(file_path)
                result['detected_format'] = detected_format
            
            # ファイルサイズチェック
            max_size = self.settings.external.max_import_rows * 1024
            if result['file_size'] > max_size:
                result['errors'].append(f"ファイルサイズが大きすぎます: {result['file_size']:,} bytes")
            
            result['valid'] = len(result['errors']) == 0
            
        except Exception as e:
            result['errors'].append(f"検証エラー: {str(e)}")
        
        return result
    
    def get_format_info(self, format_type: str) -> Dict[str, Any]:
        """フォーマット情報を取得"""
        format_info = {
            ExcelFormatType.STANDARD: {
                'name': '標準フォーマット',
                'description': 'スケジュール+入力シート構成',
                'sheets': ['スケジュール', '入力データ'],
                'hierarchy': True,
                'recommended_for': '詳細なプロジェクト管理'
            },
            ExcelFormatType.MSPROJECT: {
                'name': 'MS Project類似',
                'description': 'Tasks+Resources構成',
                'sheets': ['Tasks', 'Resources'],
                'hierarchy': False,
                'recommended_for': 'MS Projectからの移行'
            },
            ExcelFormatType.SIMPLE: {
                'name': 'シンプルフォーマット',
                'description': '単一シート形式',
                'sheets': ['データ'],
                'hierarchy': False,
                'recommended_for': '簡単なタスク管理'
            },
            ExcelFormatType.CUSTOM: {
                'name': 'カスタムフォーマット',
                'description': '柔軟な構造対応',
                'sheets': ['カスタムデータ'],
                'hierarchy': True,
                'recommended_for': '特殊な要件'
            }
        }
        
        return format_info.get(format_type, {})
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"ExcelManager(import={'有効' if self.import_enabled else '無効'}, " \
               f"export={'有効' if self.export_enabled else '無効'})"


# ==================== 便利関数 ====================

def create_excel_manager(project_management_system=None) -> ExcelManager:
    """Excel管理インスタンスを作成"""
    return ExcelManager(project_management_system)


def check_excel_dependencies() -> Dict[str, bool]:
    """Excel連携の依存関係をチェック"""
    dependencies = {
        'openpyxl': False,
        'xlsxwriter': False
    }
    
    try:
        import openpyxl
        dependencies['openpyxl'] = True
    except ImportError:
        pass
    
    try:
        import xlsxwriter
        dependencies['xlsxwriter'] = True
    except ImportError:
        pass
    
    return dependencies


def install_excel_dependencies() -> str:
    """Excel連携に必要な依存関係のインストール方法を返す"""
    return (
        "Excel連携機能を使用するには以下のライブラリが必要です:\n"
        "\n"
        "インポート機能:\n"
        "  pip install openpyxl\n"
        "\n"
        "エクスポート機能（推奨）:\n"
        "  pip install xlsxwriter\n"
        "\n"
        "エクスポート機能（代替）:\n"
        "  pip install openpyxl\n"
        "\n"
        "すべてインストール:\n"
        "  pip install openpyxl xlsxwriter"
    )


# パッケージレベルでエクスポート
__all__ = [
    'ExcelManager',
    'create_excel_manager',
    'check_excel_dependencies', 
    'install_excel_dependencies'
]

# 条件付きエクスポート
if IMPORT_AVAILABLE:
    __all__.extend(['ExcelImporter', 'ImportResult', 'ExcelFormatType'])

if EXPORT_AVAILABLE:
    __all__.extend(['ExcelExporter', 'ExportResult', 'ExportFormat', 'ExportOptions'])


# パッケージ初期化時のログ
_logger = ProjectLogger()
_logger.info(
    LogCategory.SYSTEM,
    f"外部連携層パッケージ初期化完了 "
    f"(インポート: {'利用可能' if IMPORT_AVAILABLE else '利用不可'}, "
    f"エクスポート: {'利用可能' if EXPORT_AVAILABLE else '利用不可'})",
    module="external.__init__",
    dependencies=check_excel_dependencies()
)