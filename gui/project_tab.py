"""
プロジェクト管理タブ
4階層プロジェクト構造のツリービュー表示・CRUD操作
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLineEdit, QComboBox, QLabel, QGroupBox, QSplitter,
    QTextEdit, QMessageBox, QMenu, QHeaderView, QProgressBar,
    QFrame, QCheckBox, QDateEdit, QToolBar, QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QDate, pyqtSlot
from PyQt6.QtGui import QAction, QIcon, QFont, QBrush, QColor
from typing import Optional, Dict, List, Any
from datetime import date, datetime


class ProjectTreeWidget(QTreeWidget):
    """カスタムプロジェクトツリーウィジェット"""
    
    # シグナル定義
    item_double_clicked = pyqtSignal(str, str)  # entity_id, entity_type
    context_menu_requested = pyqtSignal(str, str, object)  # entity_id, entity_type, position
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_tree()
    
    def _setup_tree(self):
        """ツリーの基本設定"""
        # ヘッダー設定
        self.setHeaderLabels([
            "名前", "種別", "ステータス", "進捗率", "担当者", 
            "開始日", "終了日", "残り日数", "優先度"
        ])
        
        # 列幅設定
        header = self.header()
        header.resizeSection(0, 250)  # 名前
        header.resizeSection(1, 80)   # 種別
        header.resizeSection(2, 100)  # ステータス
        header.resizeSection(3, 80)   # 進捗率
        header.resizeSection(4, 120)  # 担当者
        header.resizeSection(5, 100)  # 開始日
        header.resizeSection(6, 100)  # 終了日
        header.resizeSection(7, 80)   # 残り日数
        header.resizeSection(8, 80)   # 優先度
        
        # ツリー設定
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(True)
        self.setItemsExpandable(True)
        self.setExpandsOnDoubleClick(False)
        self.setSortingEnabled(True)
        
        # 選択設定
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        
        # コンテキストメニュー
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # ダブルクリック
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
    
    def _show_context_menu(self, position):
        """コンテキストメニュー表示"""
        item = self.itemAt(position)
        if item:
            entity_id = item.data(0, Qt.ItemDataRole.UserRole)
            entity_type = item.data(1, Qt.ItemDataRole.UserRole)
            if entity_id and entity_type:
                global_pos = self.mapToGlobal(position)
                self.context_menu_requested.emit(entity_id, entity_type, global_pos)
    
    def _on_item_double_clicked(self, item, column):
        """アイテムダブルクリック処理"""
        entity_id = item.data(0, Qt.ItemDataRole.UserRole)
        entity_type = item.data(1, Qt.ItemDataRole.UserRole)
        if entity_id and entity_type:
            self.item_double_clicked.emit(entity_id, entity_type)


class ProjectTab(QWidget):
    """プロジェクト管理タブ"""
    
    # シグナル定義
    project_selected = pyqtSignal(str)  # project_id
    data_changed = pyqtSignal()
    
    def __init__(self, parent, project_management_system, dialog_manager):
        """
        プロジェクトタブの初期化
        
        Args:
            parent: 親ウィンドウ
            project_management_system: プロジェクト管理システム
            dialog_manager: ダイアログ管理
        """
        super().__init__(parent)
        self.parent_window = parent
        self.pms = project_management_system
        self.dialog_manager = dialog_manager
        
        # 状態管理
        self.current_project_id = None
        self.filter_settings = {
            'status': '',
            'assignee': '',
            'keyword': '',
            'overdue_only': False,
            'high_priority_only': False
        }
        
        # UI要素
        self.tree_widget = None
        self.detail_panel = None
        
        self._setup_ui()
        self._connect_signals()
        self._load_initial_data()
        
        # 自動更新タイマー
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(60000)  # 1分間隔
    
    def _setup_ui(self):
        """UI要素を設定"""
        layout = QVBoxLayout(self)
        
        # ツールバー
        self._create_toolbar(layout)
        
        # フィルタパネル
        self._create_filter_panel(layout)
        
        # メインコンテンツ
        self._create_main_content(layout)
        
        # ステータスパネル
        self._create_status_panel(layout)
    
    def _create_toolbar(self, parent_layout):
        """ツールバーを作成"""
        toolbar_frame = QFrame()
        toolbar_layout = QHBoxLayout(toolbar_frame)
        
        # 新規作成ボタン群
        create_group = QGroupBox("新規作成")
        create_layout = QHBoxLayout(create_group)
        
        self.create_project_btn = QPushButton("プロジェクト")
        self.create_project_btn.setToolTip("新規プロジェクトを作成")
        self.create_project_btn.clicked.connect(self._create_project)
        create_layout.addWidget(self.create_project_btn)
        
        self.create_phase_btn = QPushButton("フェーズ")
        self.create_phase_btn.setToolTip("選択したプロジェクトにフェーズを追加")
        self.create_phase_btn.clicked.connect(self._create_phase)
        self.create_phase_btn.setEnabled(False)
        create_layout.addWidget(self.create_phase_btn)
        
        self.create_process_btn = QPushButton("プロセス")
        self.create_process_btn.setToolTip("選択したフェーズにプロセスを追加")
        self.create_process_btn.clicked.connect(self._create_process)
        self.create_process_btn.setEnabled(False)
        create_layout.addWidget(self.create_process_btn)
        
        self.create_task_btn = QPushButton("タスク")
        self.create_task_btn.setToolTip("選択したプロセスにタスクを追加")
        self.create_task_btn.clicked.connect(self._create_task)
        self.create_task_btn.setEnabled(False)
        create_layout.addWidget(self.create_task_btn)
        
        toolbar_layout.addWidget(create_group)
        
        # 操作ボタン群
        action_group = QGroupBox("操作")
        action_layout = QHBoxLayout(action_group)
        
        self.edit_btn = QPushButton("編集")
        self.edit_btn.setToolTip("選択した項目を編集")
        self.edit_btn.clicked.connect(self._edit_selected)
        self.edit_btn.setEnabled(False)
        action_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("削除")
        self.delete_btn.setToolTip("選択した項目を削除")
        self.delete_btn.clicked.connect(self._delete_selected)
        self.delete_btn.setEnabled(False)
        action_layout.addWidget(self.delete_btn)
        
        self.copy_btn = QPushButton("複製")
        self.copy_btn.setToolTip("選択したプロジェクトを複製")
        self.copy_btn.clicked.connect(self._copy_selected)
        self.copy_btn.setEnabled(False)
        action_layout.addWidget(self.copy_btn)
        
        toolbar_layout.addWidget(action_group)
        
        # 表示制御ボタン群
        view_group = QGroupBox("表示")
        view_layout = QHBoxLayout(view_group)
        
        self.expand_all_btn = QPushButton("全展開")
        self.expand_all_btn.clicked.connect(self.tree_widget.expandAll if hasattr(self, 'tree_widget') else lambda: None)
        view_layout.addWidget(self.expand_all_btn)
        
        self.collapse_all_btn = QPushButton("全折り畳み")
        self.collapse_all_btn.clicked.connect(self.tree_widget.collapseAll if hasattr(self, 'tree_widget') else lambda: None)
        view_layout.addWidget(self.collapse_all_btn)
        
        self.refresh_btn = QPushButton("更新")
        self.refresh_btn.clicked.connect(self.refresh_data)
        view_layout.addWidget(self.refresh_btn)
        
        toolbar_layout.addWidget(view_group)
        
        toolbar_layout.addStretch()
        
        parent_layout.addWidget(toolbar_frame)
    
    def _create_filter_panel(self, parent_layout):
        """フィルタパネルを作成"""
        filter_frame = QFrame()
        filter_layout = QHBoxLayout(filter_frame)
        
        # キーワード検索
        filter_layout.addWidget(QLabel("検索:"))
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("プロジェクト名・担当者で検索")
        self.keyword_edit.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.keyword_edit)
        
        # ステータスフィルタ
        filter_layout.addWidget(QLabel("ステータス:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["全て", "未着手", "進行中", "完了", "保留", "中止"])
        self.status_combo.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.status_combo)
        
        # 担当者フィルタ
        filter_layout.addWidget(QLabel("担当者:"))
        self.assignee_combo = QComboBox()
        self.assignee_combo.setEditable(True)
        self.assignee_combo.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.assignee_combo)
        
        # 期限超過フィルタ
        self.overdue_check = QCheckBox("期限超過のみ")
        self.overdue_check.toggled.connect(self._apply_filters)
        filter_layout.addWidget(self.overdue_check)
        
        # 高優先度フィルタ
        self.priority_check = QCheckBox("高優先度のみ")
        self.priority_check.toggled.connect(self._apply_filters)
        filter_layout.addWidget(self.priority_check)
        
        # フィルタクリア
        clear_filter_btn = QPushButton("クリア")
        clear_filter_btn.clicked.connect(self._clear_filters)
        filter_layout.addWidget(clear_filter_btn)
        
        filter_layout.addStretch()
        
        parent_layout.addWidget(filter_frame)
    
    def _create_main_content(self, parent_layout):
        """メインコンテンツを作成"""
        # スプリッター
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # ツリーウィジェット
        self.tree_widget = ProjectTreeWidget()
        splitter.addWidget(self.tree_widget)
        
        # 詳細パネル
        self._create_detail_panel(splitter)
        
        # 分割比率設定
        splitter.setSizes([600, 400])
        
        parent_layout.addWidget(splitter)
    
    def _create_detail_panel(self, parent):
        """詳細パネルを作成"""
        self.detail_panel = QGroupBox("詳細情報")
        detail_layout = QVBoxLayout(self.detail_panel)
        
        # 基本情報表示
        self.detail_text = QTextEdit()
        self.detail_text.setMaximumHeight(300)
        self.detail_text.setReadOnly(True)
        detail_layout.addWidget(self.detail_text)
        
        # 統計情報
        stats_group = QGroupBox("統計情報")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(200)
        self.stats_text.setReadOnly(True)
        stats_layout.addWidget(self.stats_text)
        
        detail_layout.addWidget(stats_group)
        
        detail_layout.addStretch()
        
        parent.addWidget(self.detail_panel)
    
    def _create_status_panel(self, parent_layout):
        """ステータスパネルを作成"""
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        
        # プロジェクト統計
        self.project_count_label = QLabel("プロジェクト: 0")
        status_layout.addWidget(self.project_count_label)
        
        self.completion_label = QLabel("完了率: 0%")
        status_layout.addWidget(self.completion_label)
        
        self.overdue_label = QLabel("期限超過: 0")
        status_layout.addWidget(self.overdue_label)
        
        status_layout.addStretch()
        
        # 最終更新時刻
        self.last_update_label = QLabel("")
        status_layout.addWidget(self.last_update_label)
        
        parent_layout.addWidget(status_frame)
    
    def _connect_signals(self):
        """シグナル接続"""
        # ツリーウィジェット
        self.tree_widget.item_double_clicked.connect(self._on_item_double_clicked)
        self.tree_widget.context_menu_requested.connect(self._show_context_menu)
        self.tree_widget.itemSelectionChanged.connect(self._on_selection_changed)
        
        # ダイアログ管理
        self.dialog_manager.project_saved.connect(self._on_data_changed)
        self.dialog_manager.project_updated.connect(self._on_data_changed)
        
        # 拡張・折り畳みボタン（遅延バインディング）
        QTimer.singleShot(100, self._connect_tree_buttons)
    
    def _connect_tree_buttons(self):
        """ツリー操作ボタンの接続（遅延）"""
        if hasattr(self, 'tree_widget'):
            self.expand_all_btn.clicked.disconnect()
            self.collapse_all_btn.clicked.disconnect()
            self.expand_all_btn.clicked.connect(self.tree_widget.expandAll)
            self.collapse_all_btn.clicked.connect(self.tree_widget.collapseAll)
    
    def _load_initial_data(self):
        """初期データを読み込み"""
        self.refresh_data()
        self._update_assignee_filter()
    
    def refresh_data(self):
        """データを更新"""
        try:
            self._populate_tree()
            self._update_status_panel()
            self._update_detail_panel()
            
            # 最終更新時刻
            self.last_update_label.setText(f"更新: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            QMessageBox.warning(
                self, "データ更新エラー",
                f"データの更新中にエラーが発生しました：\n{str(e)}"
            )
    
    def _populate_tree(self):
        """ツリーにデータを投入"""
        self.tree_widget.clear()
        
        try:
            projects = self.pms.get_all_projects()
            
            for project in projects:
                if self._should_show_project(project):
                    project_item = self._create_project_item(project)
                    self.tree_widget.addTopLevelItem(project_item)
                    
                    # フェーズを追加
                    phases = self.pms.get_phases_by_project(project.id)
                    for phase in phases:
                        if self._should_show_phase(phase):
                            phase_item = self._create_phase_item(phase)
                            project_item.addChild(phase_item)
                            
                            # プロセスを追加
                            processes = self.pms.get_processes_by_phase(phase.id)
                            for process in processes:
                                if self._should_show_process(process):
                                    process_item = self._create_process_item(process)
                                    phase_item.addChild(process_item)
                                    
                                    # タスクを追加
                                    tasks = self.pms.get_tasks_by_process(process.id)
                                    for task in tasks:
                                        if self._should_show_task(task):
                                            task_item = self._create_task_item(task)
                                            process_item.addChild(task_item)
            
            # 展開状態の復元
            if self.current_project_id:
                self._expand_to_project(self.current_project_id)
            
        except Exception as e:
            QMessageBox.critical(
                self, "データ読み込みエラー",
                f"データの読み込み中にエラーが発生しました：\n{str(e)}"
            )
    
    def _create_project_item(self, project) -> QTreeWidgetItem:
        """プロジェクトアイテムを作成"""
        item = QTreeWidgetItem()
        
        # データ設定
        item.setText(0, project.name)
        item.setText(1, "プロジェクト")
        item.setText(2, project.status)
        item.setText(3, f"{project.progress:.1f}%")
        item.setText(4, project.manager)
        item.setText(5, project.start_date.strftime('%Y/%m/%d') if project.start_date else "")
        item.setText(6, project.end_date.strftime('%Y/%m/%d') if project.end_date else "")
        
        # 残り日数
        remaining = project.get_remaining_days()
        if remaining is not None:
            if remaining >= 0:
                item.setText(7, f"{remaining}日")
            else:
                item.setText(7, f"{abs(remaining)}日超過")
                item.setForeground(7, QBrush(QColor("red")))
        else:
            item.setText(7, "未設定")
        
        item.setText(8, str(project.priority))
        
        # メタデータ
        item.setData(0, Qt.ItemDataRole.UserRole, project.id)
        item.setData(1, Qt.ItemDataRole.UserRole, "Project")
        
        # スタイリング
        font = QFont()
        font.setBold(True)
        item.setFont(0, font)
        
        # ステータス色分け
        if project.status == "完了":
            item.setForeground(2, QBrush(QColor("green")))
        elif project.is_overdue():
            item.setForeground(2, QBrush(QColor("red")))
        elif project.status == "進行中":
            item.setForeground(2, QBrush(QColor("blue")))
        
        return item
    
    def _create_phase_item(self, phase) -> QTreeWidgetItem:
        """フェーズアイテムを作成"""
        item = QTreeWidgetItem()
        
        item.setText(0, f"  {phase.name}")
        item.setText(1, "フェーズ")
        item.setText(2, phase.get_status())
        item.setText(3, f"{phase.progress:.1f}%")
        item.setText(4, "")  # フェーズに担当者なし
        item.setText(5, "")  # 開始日は自動算出
        item.setText(6, phase.end_date.strftime('%Y/%m/%d') if phase.end_date else "")
        
        # 残り日数
        remaining = phase.get_remaining_days()
        if remaining is not None:
            if remaining >= 0:
                item.setText(7, f"{remaining}日")
            else:
                item.setText(7, f"{abs(remaining)}日超過")
                item.setForeground(7, QBrush(QColor("red")))
        else:
            item.setText(7, "未設定")
        
        item.setText(8, str(phase.priority))
        
        # メタデータ
        item.setData(0, Qt.ItemDataRole.UserRole, phase.id)
        item.setData(1, Qt.ItemDataRole.UserRole, "Phase")
        
        # スタイリング
        if phase.is_overdue():
            item.setForeground(2, QBrush(QColor("red")))
        
        return item
    
    def _create_process_item(self, process) -> QTreeWidgetItem:
        """プロセスアイテムを作成"""
        item = QTreeWidgetItem()
        
        item.setText(0, f"    {process.name}")
        item.setText(1, "プロセス")
        item.setText(2, process.get_status())
        item.setText(3, f"{process.progress:.1f}%")
        item.setText(4, process.assignee)
        item.setText(5, process.start_date.strftime('%Y/%m/%d') if process.start_date else "")
        item.setText(6, process.end_date.strftime('%Y/%m/%d') if process.end_date else "")
        
        # 残り日数
        remaining = process.get_remaining_days()
        if remaining is not None:
            if remaining >= 0:
                item.setText(7, f"{remaining}日")
            else:
                item.setText(7, f"{abs(remaining)}日超過")
                item.setForeground(7, QBrush(QColor("red")))
        else:
            item.setText(7, "未設定")
        
        item.setText(8, str(process.priority))
        
        # メタデータ
        item.setData(0, Qt.ItemDataRole.UserRole, process.id)
        item.setData(1, Qt.ItemDataRole.UserRole, "Process")
        
        # スタイリング
        if process.is_overdue():
            item.setForeground(2, QBrush(QColor("red")))
        
        return item
    
    def _create_task_item(self, task) -> QTreeWidgetItem:
        """タスクアイテムを作成"""
        item = QTreeWidgetItem()
        
        item.setText(0, f"      {task.name}")
        item.setText(1, "タスク")
        item.setText(2, task.status)
        item.setText(3, f"{task.get_completion_percentage():.0f}%")
        item.setText(4, "")  # タスクに担当者なし（プロセスレベル）
        item.setText(5, "")
        item.setText(6, "")
        item.setText(7, "")
        item.setText(8, str(task.priority))
        
        # メタデータ
        item.setData(0, Qt.ItemDataRole.UserRole, task.id)
        item.setData(1, Qt.ItemDataRole.UserRole, "Task")
        
        # ステータス色分け
        if task.status == "完了":
            item.setForeground(2, QBrush(QColor("green")))
        elif task.status == "対応不能":
            item.setForeground(2, QBrush(QColor("red")))
        elif task.status == "進行中":
            item.setForeground(2, QBrush(QColor("blue")))
        
        return item
    
    def _should_show_project(self, project) -> bool:
        """プロジェクトを表示すべきか判定"""
        # キーワードフィルタ
        keyword = self.filter_settings['keyword'].lower()
        if keyword and keyword not in project.name.lower() and keyword not in project.manager.lower():
            return False
        
        # ステータスフィルタ
        status = self.filter_settings['status']
        if status and status != project.status:
            return False
        
        # 期限超過フィルタ
        if self.filter_settings['overdue_only'] and not project.is_overdue():
            return False
        
        # 高優先度フィルタ
        if self.filter_settings['high_priority_only'] and project.priority > 2:
            return False
        
        return True
    
    def _should_show_phase(self, phase) -> bool:
        """フェーズを表示すべきか判定"""
        keyword = self.filter_settings['keyword'].lower()
        if keyword and keyword not in phase.name.lower():
            return False
        
        if self.filter_settings['overdue_only'] and not phase.is_overdue():
            return False
        
        if self.filter_settings['high_priority_only'] and phase.priority > 2:
            return False
        
        return True
    
    def _should_show_process(self, process) -> bool:
        """プロセスを表示すべきか判定"""
        keyword = self.filter_settings['keyword'].lower()
        if keyword and keyword not in process.name.lower() and keyword not in process.assignee.lower():
            return False
        
        assignee = self.filter_settings['assignee']
        if assignee and assignee != process.assignee:
            return False
        
        if self.filter_settings['overdue_only'] and not process.is_overdue():
            return False
        
        if self.filter_settings['high_priority_only'] and process.priority > 2:
            return False
        
        return True
    
    def _should_show_task(self, task) -> bool:
        """タスクを表示すべきか判定"""
        keyword = self.filter_settings['keyword'].lower()
        if keyword and keyword not in task.name.lower():
            return False
        
        if self.filter_settings['high_priority_only'] and task.priority > 2:
            return False
        
        return True
    
    def _apply_filters(self):
        """フィルタを適用"""
        # フィルタ設定更新
        self.filter_settings.update({
            'keyword': self.keyword_edit.text(),
            'status': self.status_combo.currentText() if self.status_combo.currentText() != "全て" else "",
            'assignee': self.assignee_combo.currentText() if self.assignee_combo.currentText() else "",
            'overdue_only': self.overdue_check.isChecked(),
            'high_priority_only': self.priority_check.isChecked()
        })
        
        # ツリー再構築
        self._populate_tree()
    
    def _clear_filters(self):
        """フィルタをクリア"""
        self.keyword_edit.clear()
        self.status_combo.setCurrentText("全て")
        self.assignee_combo.setCurrentText("")
        self.overdue_check.setChecked(False)
        self.priority_check.setChecked(False)
        
        self._apply_filters()
    
    def _update_assignee_filter(self):
        """担当者フィルタを更新"""
        try:
            assignees = set()
            processes = self.pms.get_all_processes()
            for process in processes:
                if process.assignee:
                    assignees.add(process.assignee)
            
            current_text = self.assignee_combo.currentText()
            self.assignee_combo.clear()
            self.assignee_combo.addItems([""] + sorted(list(assignees)))
            
            # 現在の選択を復元
            index = self.assignee_combo.findText(current_text)
            if index >= 0:
                self.assignee_combo.setCurrentIndex(index)
                
        except Exception:
            pass
    
    def _update_status_panel(self):
        """ステータスパネルを更新"""
        try:
            stats = self.pms.get_system_statistics()
            
            project_stats = stats.get('projects', {})
            self.project_count_label.setText(f"プロジェクト: {project_stats.get('total', 0)}")
            self.completion_label.setText(f"完了率: {project_stats.get('completion_rate', 0):.1f}%")
            self.overdue_label.setText(f"期限超過: {project_stats.get('overdue', 0)}")
            
        except Exception:
            self.project_count_label.setText("プロジェクト: エラー")
            self.completion_label.setText("完了率: エラー")
            self.overdue_label.setText("期限超過: エラー")
    
    def _update_detail_panel(self):
        """詳細パネルを更新"""
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            self.detail_text.clear()
            self.stats_text.clear()
            return
        
        item = selected_items[0]
        entity_id = item.data(0, Qt.ItemDataRole.UserRole)
        entity_type = item.data(1, Qt.ItemDataRole.UserRole)
        
        try:
            if entity_type == "Project":
                project = self.pms.get_project(entity_id)
                if project:
                    self._show_project_details(project)
            elif entity_type == "Phase":
                phase = self.pms.get_phase(entity_id)
                if phase:
                    self._show_phase_details(phase)
            elif entity_type == "Process":
                process = self.pms.get_process(entity_id)
                if process:
                    self._show_process_details(process)
            elif entity_type == "Task":
                task = self.pms.get_task(entity_id)
                if task:
                    self._show_task_details(task)
                    
        except Exception as e:
            self.detail_text.setText(f"詳細情報の取得に失敗しました：\n{str(e)}")
            self.stats_text.clear()
    
    def _show_project_details(self, project):
        """プロジェクト詳細を表示"""
        details = f"""
プロジェクト名: {project.name}
説明: {project.description}
プロジェクトマネージャー: {project.manager}
ステータス: {project.status}
進捗率: {project.progress:.1f}%
優先度: {project.priority}
リスクレベル: {project.risk_level}

期間: {project.start_date or '未設定'} ～ {project.end_date or '未設定'}
残り日数: {project.get_remaining_days() or '未設定'}
期限超過: {'はい' if project.is_overdue() else 'いいえ'}

予算: {f'{project.budget:,.0f}円' if project.budget else '未設定'}
実績コスト: {f'{project.actual_cost:,.0f}円' if project.actual_cost else '未設定'}

ステークホルダー: {', '.join(project.stakeholders) if project.stakeholders else 'なし'}
タグ: {', '.join(project.tags) if project.tags else 'なし'}

備考:
{project.notes or '（なし）'}
        """.strip()
        
        self.detail_text.setText(details)
        
        # 統計情報
        try:
            phase_stats = project.get_phase_statistics(self.pms.phase_manager)
            stats_text = f"""
フェーズ統計:
- 総数: {phase_stats['total']}
- 完了: {phase_stats['completed']}
- 進行中: {phase_stats['in_progress']}
- 未着手: {phase_stats['not_started']}
- 期限超過: {phase_stats['overdue']}
- 完了率: {phase_stats['completion_rate']:.1f}%
            """.strip()
            self.stats_text.setText(stats_text)
        except:
            self.stats_text.setText("統計情報の取得に失敗しました")
    
    def _show_phase_details(self, phase):
        """フェーズ詳細を表示"""
        details = f"""
フェーズ名: {phase.name}
説明: {phase.description}
ステータス: {phase.get_status()}
進捗率: {phase.progress:.1f}%
優先度: {phase.priority}

終了日: {phase.end_date or '未設定'}
残り日数: {phase.get_remaining_days() or '未設定'}
期限超過: {'はい' if phase.is_overdue() else 'いいえ'}

マイルストーン: {phase.milestone or '未設定'}

成果物:
{chr(10).join([f'- {d}' for d in phase.deliverables]) if phase.deliverables else '（なし）'}

備考:
{phase.notes or '（なし）'}
        """.strip()
        
        self.detail_text.setText(details)
        
        # プロセス統計
        try:
            process_stats = phase.get_process_statistics(self.pms.process_manager)
            stats_text = f"""
プロセス統計:
- 総数: {process_stats['total']}
- 完了: {process_stats['completed']}
- 進行中: {process_stats['in_progress']}
- 未着手: {process_stats['not_started']}
- 期限超過: {process_stats['overdue']}
- 完了率: {process_stats['completion_rate']:.1f}%
            """.strip()
            self.stats_text.setText(stats_text)
        except:
            self.stats_text.setText("統計情報の取得に失敗しました")
    
    def _show_process_details(self, process):
        """プロセス詳細を表示"""
        details = f"""
プロセス名: {process.name}
説明: {process.description}
担当者: {process.assignee}
ステータス: {process.get_status()}
進捗率: {process.progress:.1f}%
優先度: {process.priority}

期間: {process.start_date or '未設定'} ～ {process.end_date or '未設定'}
残り日数: {process.get_remaining_days() or '未設定'}
期限超過: {'はい' if process.is_overdue() else 'いいえ'}

予想工数: {f'{process.estimated_hours:.1f}時間' if process.estimated_hours else '未設定'}
実績工数: {f'{process.actual_hours:.1f}時間' if process.actual_hours else '未設定'}
効率性: {f'{process.get_efficiency_ratio():.2f}' if process.get_efficiency_ratio() else '未算出'}

進捗管理: {'手動' if process.is_progress_manual else '自動（タスクベース）'}

備考:
{process.notes or '（なし）'}
        """.strip()
        
        self.detail_text.setText(details)
        
        # タスク統計
        try:
            summary = process.get_summary(self.pms.task_manager)
            stats_text = f"""
タスク統計:
- 総数: {summary['task_count']}
- 実行可能: {summary.get('actionable_tasks', 0)}
- 完了: {summary.get('completed_tasks', 0)}
- 完了率: {summary.get('task_completion_rate', 0):.1f}%

工数統計:
- 予想工数合計: {f"{summary.get('estimated_total', 0):.1f}時間" if summary.get('estimated_total') else '未設定'}
- 実績工数合計: {f"{summary.get('actual_total', 0):.1f}時間" if summary.get('actual_total') else '未設定'}
            """.strip()
            self.stats_text.setText(stats_text)
        except:
            self.stats_text.setText("統計情報の取得に失敗しました")
    
    def _show_task_details(self, task):
        """タスク詳細を表示"""
        details = f"""
タスク名: {task.name}
説明: {task.description}
ステータス: {task.status}
完了率: {task.get_completion_percentage():.0f}%
優先度: {task.priority}

実行可能性: {'実行可能' if task.is_actionable() else '実行不可'}

予想工数: {f'{task.estimated_hours:.1f}時間' if task.estimated_hours else '未設定'}
実績工数: {f'{task.actual_hours:.1f}時間' if task.actual_hours else '未設定'}
効率性: {f'{task.get_efficiency_ratio():.2f}' if task.get_efficiency_ratio() else '未算出'}

タグ: {', '.join(task.tags) if task.tags else 'なし'}

備考:
{task.notes or '（なし）'}
        """.strip()
        
        self.detail_text.setText(details)
        
        # ステータス履歴
        try:
            history_text = "ステータス変更履歴:\n"
            for change in task.status_history[-5:]:  # 最新5件
                history_text += f"- {change.changed_at.strftime('%Y/%m/%d %H:%M')}: "
                history_text += f"{change.old_status or '新規'} → {change.new_status}"
                if change.comment:
                    history_text += f" ({change.comment})"
                history_text += "\n"
            
            self.stats_text.setText(history_text)
        except:
            self.stats_text.setText("ステータス履歴の取得に失敗しました")
    
    @pyqtSlot()
    def _on_selection_changed(self):
        """選択変更時の処理"""
        selected_items = self.tree_widget.selectedItems()
        
        # ボタン状態更新
        has_selection = len(selected_items) > 0
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        
        if has_selection:
            item = selected_items[0]
            entity_type = item.data(1, Qt.ItemDataRole.UserRole)
            
            # 作成ボタンの状態更新
            self.create_phase_btn.setEnabled(entity_type == "Project")
            self.create_process_btn.setEnabled(entity_type == "Phase")
            self.create_task_btn.setEnabled(entity_type == "Process")
            self.copy_btn.setEnabled(entity_type == "Project")
            
            # プロジェクト選択通知
            if entity_type == "Project":
                entity_id = item.data(0, Qt.ItemDataRole.UserRole)
                self.current_project_id = entity_id
                self.project_selected.emit(entity_id)
        else:
            self.create_phase_btn.setEnabled(False)
            self.create_process_btn.setEnabled(False)
            self.create_task_btn.setEnabled(False)
            self.copy_btn.setEnabled(False)
        
        # 詳細パネル更新
        self._update_detail_panel()
    
    @pyqtSlot(str, str)
    def _on_item_double_clicked(self, entity_id, entity_type):
        """アイテムダブルクリック処理"""
        self._edit_entity(entity_id, entity_type)
    
    @pyqtSlot(str, str, object)
    def _show_context_menu(self, entity_id, entity_type, position):
        """コンテキストメニュー表示"""
        menu = QMenu(self)
        
        # 編集
        edit_action = menu.addAction("編集")
        edit_action.triggered.connect(lambda: self._edit_entity(entity_id, entity_type))
        
        # 削除
        delete_action = menu.addAction("削除")
        delete_action.triggered.connect(lambda: self._delete_entity(entity_id, entity_type))
        
        menu.addSeparator()
        
        # 種別別メニュー
        if entity_type == "Project":
            copy_action = menu.addAction("プロジェクト複製")
            copy_action.triggered.connect(lambda: self._copy_project(entity_id))
            
            menu.addSeparator()
            
            add_phase_action = menu.addAction("フェーズ追加")
            add_phase_action.triggered.connect(lambda: self._create_phase(entity_id))
            
        elif entity_type == "Phase":
            add_process_action = menu.addAction("プロセス追加")
            add_process_action.triggered.connect(lambda: self._create_process(entity_id))
            
        elif entity_type == "Process":
            add_task_action = menu.addAction("タスク追加")
            add_task_action.triggered.connect(lambda: self._create_task(entity_id))
        
        menu.exec(position)
    
    def _create_project(self):
        """プロジェクト作成"""
        try:
            result = self.dialog_manager.show_project_dialog(None, 'create')
            if result:
                self._on_data_changed()
                
        except Exception as e:
            QMessageBox.critical(
                self, "作成エラー",
                f"プロジェクトの作成に失敗しました：\n{str(e)}"
            )
    
    def _create_phase(self, project_id=None):
        """フェーズ作成"""
        try:
            if not project_id:
                # 選択されたプロジェクトから取得
                selected_items = self.tree_widget.selectedItems()
                if selected_items:
                    item = selected_items[0]
                    if item.data(1, Qt.ItemDataRole.UserRole) == "Project":
                        project_id = item.data(0, Qt.ItemDataRole.UserRole)
            
            if not project_id:
                QMessageBox.warning(self, "選択エラー", "プロジェクトを選択してください。")
                return
            
            result = self.dialog_manager.show_phase_dialog(None, project_id, 'create')
            if result:
                self._on_data_changed()
                
        except Exception as e:
            QMessageBox.critical(
                self, "作成エラー",
                f"フェーズの作成に失敗しました：\n{str(e)}"
            )
    
    def _create_process(self, phase_id=None):
        """プロセス作成"""
        try:
            if not phase_id:
                selected_items = self.tree_widget.selectedItems()
                if selected_items:
                    item = selected_items[0]
                    if item.data(1, Qt.ItemDataRole.UserRole) == "Phase":
                        phase_id = item.data(0, Qt.ItemDataRole.UserRole)
            
            if not phase_id:
                QMessageBox.warning(self, "選択エラー", "フェーズを選択してください。")
                return
            
            result = self.dialog_manager.show_process_dialog(None, phase_id, 'create')
            if result:
                self._on_data_changed()
                
        except Exception as e:
            QMessageBox.critical(
                self, "作成エラー",
                f"プロセスの作成に失敗しました：\n{str(e)}"
            )
    
    def _create_task(self, process_id=None):
        """タスク作成"""
        try:
            if not process_id:
                selected_items = self.tree_widget.selectedItems()
                if selected_items:
                    item = selected_items[0]
                    if item.data(1, Qt.ItemDataRole.UserRole) == "Process":
                        process_id = item.data(0, Qt.ItemDataRole.UserRole)
            
            if not process_id:
                QMessageBox.warning(self, "選択エラー", "プロセスを選択してください。")
                return
            
            result = self.dialog_manager.show_task_dialog(None, process_id, 'create')
            if result:
                self._on_data_changed()
                
        except Exception as e:
            QMessageBox.critical(
                self, "作成エラー",
                f"タスクの作成に失敗しました：\n{str(e)}"
            )
    
    def _edit_selected(self):
        """選択項目を編集"""
        selected_items = self.tree_widget.selectedItems()
        if selected_items:
            item = selected_items[0]
            entity_id = item.data(0, Qt.ItemDataRole.UserRole)
            entity_type = item.data(1, Qt.ItemDataRole.UserRole)
            self._edit_entity(entity_id, entity_type)
    
    def _edit_entity(self, entity_id, entity_type):
        """エンティティを編集"""
        try:
            if entity_type == "Project":
                project = self.pms.get_project(entity_id)
                result = self.dialog_manager.show_project_dialog(project, 'edit')
            elif entity_type == "Phase":
                phase = self.pms.get_phase(entity_id)
                result = self.dialog_manager.show_phase_dialog(phase, mode='edit')
            elif entity_type == "Process":
                process = self.pms.get_process(entity_id)
                result = self.dialog_manager.show_process_dialog(process, mode='edit')
            elif entity_type == "Task":
                task = self.pms.get_task(entity_id)
                result = self.dialog_manager.show_task_dialog(task, mode='edit')
            else:
                return
            
            if result:
                self._on_data_changed()
                
        except Exception as e:
            QMessageBox.critical(
                self, "編集エラー",
                f"編集中にエラーが発生しました：\n{str(e)}"
            )
    
    def _delete_selected(self):
        """選択項目を削除"""
        selected_items = self.tree_widget.selectedItems()
        if selected_items:
            item = selected_items[0]
            entity_id = item.data(0, Qt.ItemDataRole.UserRole)
            entity_type = item.data(1, Qt.ItemDataRole.UserRole)
            self._delete_entity(entity_id, entity_type)
    
    def _delete_entity(self, entity_id, entity_type):
        """エンティティを削除"""
        try:
            # 確認ダイアログ
            entity_name = ""
            if entity_type == "Project":
                entity = self.pms.get_project(entity_id)
            elif entity_type == "Phase":
                entity = self.pms.get_phase(entity_id)
            elif entity_type == "Process":
                entity = self.pms.get_process(entity_id)
            elif entity_type == "Task":
                entity = self.pms.get_task(entity_id)
            else:
                return
            
            if entity:
                entity_name = entity.name
            
            reply = QMessageBox.question(
                self, "削除確認",
                f"{entity_type}「{entity_name}」を削除しますか？\n"
                "この操作は元に戻すことができません。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # 削除実行
            success = False
            if entity_type == "Project":
                success = self.pms.delete_project(entity_id)
            elif entity_type == "Phase":
                success = self.pms.delete_phase(entity_id)
            elif entity_type == "Process":
                success = self.pms.delete_process(entity_id)
            elif entity_type == "Task":
                success = self.pms.delete_task(entity_id)
            
            if success:
                self._on_data_changed()
                QMessageBox.information(self, "削除完了", f"{entity_type}を削除しました。")
            else:
                QMessageBox.warning(self, "削除エラー", "削除に失敗しました。")
                
        except Exception as e:
            QMessageBox.critical(
                self, "削除エラー",
                f"削除中にエラーが発生しました：\n{str(e)}"
            )
    
    def _copy_selected(self):
        """選択プロジェクトを複製"""
        selected_items = self.tree_widget.selectedItems()
        if selected_items:
            item = selected_items[0]
            entity_id = item.data(0, Qt.ItemDataRole.UserRole)
            entity_type = item.data(1, Qt.ItemDataRole.UserRole)
            if entity_type == "Project":
                self._copy_project(entity_id)
    
    def _copy_project(self, project_id):
        """プロジェクトを複製"""
        try:
            project = self.pms.get_project(project_id)
            if not project:
                return
            
            # 複製名の入力
            from PyQt6.QtWidgets import QInputDialog
            new_name, ok = QInputDialog.getText(
                self, "プロジェクト複製",
                "新しいプロジェクト名:",
                text=f"{project.name} (コピー)"
            )
            
            if not ok or not new_name.strip():
                return
            
            # 複製実行（将来実装）
            QMessageBox.information(
                self, "複製機能",
                "プロジェクト複製機能は将来のバージョンで実装予定です。"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, "複製エラー",
                f"複製中にエラーが発生しました：\n{str(e)}"
            )
    
    def _expand_to_project(self, project_id):
        """指定プロジェクトまで展開"""
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == project_id:
                item.setExpanded(True)
                self.tree_widget.setCurrentItem(item)
                break
    
    @pyqtSlot()
    def _on_data_changed(self):
        """データ変更時の処理"""
        self.refresh_data()
        self._update_assignee_filter()
        self.data_changed.emit()
    
    def select_project_by_id(self, project_id):
        """プロジェクトIDで選択"""
        self.current_project_id = project_id
        self._expand_to_project(project_id)