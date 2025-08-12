"""
タスク編集ダイアログ
タスクの作成・編集・詳細表示
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QDateEdit, QCheckBox, QPushButton, QLabel, QGroupBox,
    QListWidget, QListWidgetItem, QMessageBox, QTabWidget,
    QWidget, QScrollArea, QFrame, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QIcon
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from ...models.task import Task, TaskStatus


class TaskDialog(QDialog):
    """タスク編集ダイアログクラス"""
    
    # シグナル定義
    task_saved = pyqtSignal(str)  # タスクID
    task_updated = pyqtSignal(str)  # タスクID
    task_status_changed = pyqtSignal(str, str)  # タスクID、新ステータス
    
    def __init__(self, parent=None, project_management_system=None,
                 task: Optional[Task] = None, process_id: str = None, 
                 mode: str = 'edit'):
        """
        タスクダイアログの初期化
        
        Args:
            parent: 親ウィンドウ
            project_management_system: プロジェクト管理システム
            task: 編集対象タスク（Noneの場合は新規作成）
            process_id: 親プロセスID（新規作成時）
            mode: 'edit', 'create', 'view'
        """
        super().__init__(parent)
        self.pms = project_management_system
        self.task = task
        self.process_id = process_id or (task.parent_process_id if task else None)
        self.mode = mode
        self.is_new_task = task is None
        
        # UI状態
        self.is_modified = False
        
        # 親階層の情報取得
        self.parent_process = None
        self.parent_phase = None
        self.parent_project = None
        if self.process_id and self.pms:
            self.parent_process = self.pms.get_process(self.process_id)
            if self.parent_process and self.parent_process.parent_phase_id:
                self.parent_phase = self.pms.get_phase(self.parent_process.parent_phase_id)
                if self.parent_phase and self.parent_phase.parent_project_id:
                    self.parent_project = self.pms.get_project(self.parent_phase.parent_project_id)
        
        self._setup_ui()
        self._connect_signals()
        self.reset_form()
        
        # ウィンドウ設定
        self.setModal(True)
        self.resize(550, 600)
        
        # タイトル設定
        process_name = self.parent_process.name if self.parent_process else "不明"
        if self.mode == 'create':
            self.setWindowTitle(f"新規タスク作成 - プロセス: {process_name}")
        elif self.mode == 'view':
            self.setWindowTitle(f"タスク詳細: {task.name if task else ''}")
        else:
            self.setWindowTitle(f"タスク編集: {task.name if task else ''}")
    
    def _setup_ui(self):
        """UI要素を設定"""
        layout = QVBoxLayout(self)
        
        # 親階層情報表示
        if self.parent_project and self.parent_phase and self.parent_process:
            hierarchy_info = QLabel(
                f"プロジェクト: {self.parent_project.name} > "
                f"フェーズ: {self.parent_phase.name} > "
                f"プロセス: {self.parent_process.name}"
            )
            hierarchy_info.setStyleSheet("font-weight: bold; color: #0066cc; padding: 5px;")
            hierarchy_info.setWordWrap(True)
            layout.addWidget(hierarchy_info)
        
        # タブウィジェット作成
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 基本情報タブ
        self._create_basic_tab()
        
        # 工数・進捗タブ
        self._create_hours_tab()
        
        # ステータス履歴タブ
        self._create_history_tab()
        
        # 統計・分析タブ
        self._create_statistics_tab()
        
        # ボタン
        self._create_buttons(layout)
    
    def _create_basic_tab(self):
        """基本情報タブを作成"""
        basic_widget = QWidget()
        layout = QFormLayout(basic_widget)
        layout.setSpacing(10)
        
        # タスク名（必須）
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("タスク名を入力してください（必須）")
        layout.addRow("タスク名 *:", self.name_edit)
        
        # 説明
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("タスクの詳細説明")
        layout.addRow("説明:", self.description_edit)
        
        # ステータス管理
        status_group = QGroupBox("ステータス管理")
        status_layout = QFormLayout(status_group)
        
        self.status_combo = QComboBox()
        self.status_combo.addItems([
            TaskStatus.NOT_STARTED,
            TaskStatus.IN_PROGRESS,
            TaskStatus.COMPLETED,
            TaskStatus.CANNOT_HANDLE
        ])
        status_layout.addRow("ステータス:", self.status_combo)
        
        # ステータス変更コメント
        self.status_comment_edit = QLineEdit()
        self.status_comment_edit.setPlaceholderText("ステータス変更理由（任意）")
        status_layout.addRow("変更コメント:", self.status_comment_edit)
        
        layout.addRow(status_group)
        
        # 優先度・属性
        attrs_group = QGroupBox("属性設定")
        attrs_layout = QFormLayout(attrs_group)
        
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 5)
        self.priority_spin.setValue(3)
        self.priority_spin.setToolTip("1:最高 → 5:最低")
        attrs_layout.addRow("優先度:", self.priority_spin)
        
        layout.addRow(attrs_group)
        
        # タグ管理
        tags_group = QGroupBox("タグ管理")
        tags_layout = QVBoxLayout(tags_group)
        
        # 追加用入力
        tag_add_layout = QHBoxLayout()
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("タグを入力")
        tag_add_layout.addWidget(self.tag_input)
        
        self.add_tag_btn = QPushButton("追加")
        self.add_tag_btn.clicked.connect(self._add_tag)
        tag_add_layout.addWidget(self.add_tag_btn)
        
        tags_layout.addLayout(tag_add_layout)
        
        # タグリスト表示
        self.tag_list = QListWidget()
        self.tag_list.setMaximumHeight(100)
        tags_layout.addWidget(self.tag_list)
        
        self.remove_tag_btn = QPushButton("選択項目を削除")
        self.remove_tag_btn.clicked.connect(self._remove_tag)
        tags_layout.addWidget(self.remove_tag_btn)
        
        layout.addRow(tags_group)
        
        # 備考
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("タスクに関する備考・メモ")
        layout.addRow("備考:", self.notes_edit)
        
        self.tab_widget.addTab(basic_widget, "基本情報")
    
    def _create_hours_tab(self):
        """工数・進捗タブを作成"""
        hours_widget = QWidget()
        layout = QVBoxLayout(hours_widget)
        
        # 工数管理
        hours_group = QGroupBox("工数管理")
        hours_layout = QFormLayout(hours_group)
        
        self.estimated_hours_spin = QDoubleSpinBox()
        self.estimated_hours_spin.setRange(0, 999.9)
        self.estimated_hours_spin.setSuffix(" 時間")
        self.estimated_hours_spin.setDecimals(1)
        hours_layout.addRow("予想工数:", self.estimated_hours_spin)
        
        self.actual_hours_spin = QDoubleSpinBox()
        self.actual_hours_spin.setRange(0, 999.9)
        self.actual_hours_spin.setSuffix(" 時間")
        self.actual_hours_spin.setDecimals(1)
        hours_layout.addRow("実績工数:", self.actual_hours_spin)
        
        layout.addWidget(hours_group)
        
        # 進捗・効率性分析
        analysis_group = QGroupBox("効率性分析")
        analysis_layout = QFormLayout(analysis_group)
        
        self.completion_label = QLabel("未完了")
        self.completion_label.setStyleSheet("font-weight: bold;")
        analysis_layout.addRow("完了状況:", self.completion_label)
        
        self.efficiency_label = QLabel("未算出")
        analysis_layout.addRow("効率性比率:", self.efficiency_label)
        
        self.hours_variance_label = QLabel("未算出")
        analysis_layout.addRow("工数差異:", self.hours_variance_label)
        
        self.actionable_label = QLabel("実行可能")
        analysis_layout.addRow("実行可能性:", self.actionable_label)
        
        layout.addWidget(analysis_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(hours_widget, "工数・効率性")
    
    def _create_history_tab(self):
        """ステータス履歴タブを作成"""
        history_widget = QWidget()
        layout = QVBoxLayout(history_widget)
        
        # ステータス履歴テーブル
        history_group = QGroupBox("ステータス変更履歴")
        history_layout = QVBoxLayout(history_group)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "変更日時", "変更前", "変更後", "変更者", "コメント"
        ])
        
        # 列幅調整
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        history_layout.addWidget(self.history_table)
        
        # 履歴統計
        stats_layout = QHBoxLayout()
        
        self.total_changes_label = QLabel("変更回数: 0")
        stats_layout.addWidget(self.total_changes_label)
        
        stats_layout.addStretch()
        
        self.last_change_label = QLabel("最終変更: 未変更")
        stats_layout.addWidget(self.last_change_label)
        
        history_layout.addLayout(stats_layout)
        
        layout.addWidget(history_group)
        
        self.tab_widget.addTab(history_widget, "ステータス履歴")
    
    def _create_statistics_tab(self):
        """統計・分析タブを作成"""
        stats_widget = QWidget()
        layout = QVBoxLayout(stats_widget)
        
        # 基本情報
        info_group = QGroupBox("タスク情報")
        info_layout = QFormLayout(info_group)
        
        self.created_label = QLabel("")
        info_layout.addRow("作成日時:", self.created_label)
        
        self.updated_label = QLabel("")
        info_layout.addRow("最終更新:", self.updated_label)
        
        self.id_label = QLabel("")
        self.id_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info_layout.addRow("タスクID:", self.id_label)
        
        layout.addWidget(info_group)
        
        # 進捗分析
        progress_group = QGroupBox("進捗分析")
        progress_layout = QFormLayout(progress_group)
        
        self.completion_rate_label = QLabel("")
        progress_layout.addRow("完了率:", self.completion_rate_label)
        
        self.current_status_label = QLabel("")
        progress_layout.addRow("現在ステータス:", self.current_status_label)
        
        self.status_duration_label = QLabel("")
        progress_layout.addRow("現ステータス期間:", self.status_duration_label)
        
        layout.addWidget(progress_group)
        
        # タグ・分類情報
        if not self.is_new_task:
            classification_group = QGroupBox("分類情報")
            classification_layout = QFormLayout(classification_group)
            
            self.tag_count_label = QLabel("0")
            classification_layout.addRow("タグ数:", self.tag_count_label)
            
            self.priority_analysis_label = QLabel("")
            classification_layout.addRow("優先度分析:", self.priority_analysis_label)
            
            layout.addWidget(classification_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(stats_widget, "統計分析")
    
    def _create_buttons(self, layout):
        """ボタン群を作成"""
        button_layout = QHBoxLayout()
        
        # 左側ボタン
        if not self.is_new_task and self.mode != 'view':
            self.refresh_btn = QPushButton("データ更新")
            self.refresh_btn.clicked.connect(self._refresh_data)
            button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        
        # 右側ボタン
        if self.mode != 'view':
            self.save_btn = QPushButton("保存")
            self.save_btn.clicked.connect(self._save_task)
            self.save_btn.setDefault(True)
            button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("閉じる" if self.mode == 'view' else "キャンセル")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """シグナル接続"""
        if self.mode != 'view':
            # データ変更検知
            self.name_edit.textChanged.connect(self._on_data_changed)
            self.description_edit.textChanged.connect(self._on_data_changed)
            self.status_combo.currentTextChanged.connect(self._on_status_changed)
            self.status_comment_edit.textChanged.connect(self._on_data_changed)
            self.priority_spin.valueChanged.connect(self._on_data_changed)
            self.notes_edit.textChanged.connect(self._on_data_changed)
            self.estimated_hours_spin.valueChanged.connect(self._on_data_changed)
            self.actual_hours_spin.valueChanged.connect(self._on_data_changed)
            
            # 工数変更時の分析更新
            self.estimated_hours_spin.valueChanged.connect(self._update_efficiency_analysis)
            self.actual_hours_spin.valueChanged.connect(self._update_efficiency_analysis)
            
            # Enterキーでの追加
            self.tag_input.returnPressed.connect(self._add_tag)
    
    def _on_data_changed(self):
        """データ変更時の処理"""
        self.is_modified = True
        if hasattr(self, 'save_btn'):
            self.save_btn.setText("保存 *")
    
    def _on_status_changed(self):
        """ステータス変更時の処理"""
        self._update_completion_display()
        self._on_data_changed()
    
    def _update_completion_display(self):
        """完了状況表示を更新"""
        status = self.status_combo.currentText()
        
        if status == TaskStatus.COMPLETED:
            self.completion_label.setText("完了")
            self.completion_label.setStyleSheet("font-weight: bold; color: #00aa00;")
            self.actionable_label.setText("実行可能")
            self.actionable_label.setStyleSheet("color: green;")
        elif status == TaskStatus.CANNOT_HANDLE:
            self.completion_label.setText("対応不能")
            self.completion_label.setStyleSheet("font-weight: bold; color: #cc0000;")
            self.actionable_label.setText("実行不可")
            self.actionable_label.setStyleSheet("color: red;")
        elif status == TaskStatus.IN_PROGRESS:
            self.completion_label.setText("進行中")
            self.completion_label.setStyleSheet("font-weight: bold; color: #0066cc;")
            self.actionable_label.setText("実行可能")
            self.actionable_label.setStyleSheet("color: green;")
        else:
            self.completion_label.setText("未着手")
            self.completion_label.setStyleSheet("font-weight: bold; color: #666666;")
            self.actionable_label.setText("実行可能")
            self.actionable_label.setStyleSheet("color: green;")
    
    def _update_efficiency_analysis(self):
        """効率性分析を更新"""
        estimated = self.estimated_hours_spin.value()
        actual = self.actual_hours_spin.value()
        
        if estimated > 0 and actual > 0:
            efficiency = actual / estimated
            if efficiency <= 1.0:
                self.efficiency_label.setText(f"{efficiency:.2f} (効率的)")
                self.efficiency_label.setStyleSheet("color: green;")
            elif efficiency <= 1.5:
                self.efficiency_label.setText(f"{efficiency:.2f} (やや超過)")
                self.efficiency_label.setStyleSheet("color: orange;")
            else:
                self.efficiency_label.setText(f"{efficiency:.2f} (大幅超過)")
                self.efficiency_label.setStyleSheet("color: red;")
            
            # 工数差異
            variance = actual - estimated
            if variance == 0:
                self.hours_variance_label.setText("差異なし")
                self.hours_variance_label.setStyleSheet("color: green;")
            elif variance > 0:
                self.hours_variance_label.setText(f"+{variance:.1f}時間")
                self.hours_variance_label.setStyleSheet("color: red;")
            else:
                self.hours_variance_label.setText(f"{variance:.1f}時間")
                self.hours_variance_label.setStyleSheet("color: green;")
        else:
            self.efficiency_label.setText("未算出")
            self.efficiency_label.setStyleSheet("color: gray;")
            self.hours_variance_label.setText("未算出")
            self.hours_variance_label.setStyleSheet("color: gray;")
    
    def _add_tag(self):
        """タグを追加"""
        text = self.tag_input.text().strip()
        if text:
            self.tag_list.addItem(text)
            self.tag_input.clear()
            self._on_data_changed()
    
    def _remove_tag(self):
        """選択されたタグを削除"""
        current_row = self.tag_list.currentRow()
        if current_row >= 0:
            self.tag_list.takeItem(current_row)
            self._on_data_changed()
    
    def _refresh_data(self):
        """データを最新状態に更新"""
        if self.task and self.pms:
            updated_task = self.pms.get_task(self.task.id)
            if updated_task:
                self.task = updated_task
                self.load_task_data()
                
                QMessageBox.information(
                    self, "更新完了", 
                    "タスクデータを最新状態に更新しました。"
                )
    
    def _save_task(self):
        """タスクを保存"""
        try:
            # バリデーション
            if not self._validate_input():
                return
            
            # データ収集
            task_data = self._collect_form_data()
            
            if self.is_new_task:
                # 新規作成
                task = self.pms.create_task(
                    task_data['name'],
                    self.process_id,
                    task_data['description']
                )
                
                # 追加属性設定
                self._apply_additional_data(task, task_data)
                
                # 更新
                self.pms.update_task(task)
                
                self.task = task
                self.task_saved.emit(task.id)
                
                QMessageBox.information(
                    self, "作成完了",
                    f"タスク「{task.name}」を作成しました。"
                )
                
            else:
                # 既存更新
                old_status = self.task.status
                self._apply_form_data_to_task(task_data)
                
                # ステータス変更の場合
                if old_status != task_data['status']:
                    comment = task_data.get('status_comment', '')
                    success = self.pms.update_task_status(
                        self.task.id, 
                        task_data['status'],
                        comment
                    )
                    
                    if success:
                        self.task_status_changed.emit(self.task.id, task_data['status'])
                else:
                    success = self.pms.task_manager.update_task(self.task)
                
                if success:
                    self.task_updated.emit(self.task.id)
                    
                    QMessageBox.information(
                        self, "更新完了",
                        f"タスク「{self.task.name}」を更新しました。"
                    )
                else:
                    QMessageBox.critical(
                        self, "更新エラー",
                        "タスクの更新に失敗しました。"
                    )
                    return
            
            self.is_modified = False
            self.save_btn.setText("保存")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self, "保存エラー",
                f"タスクの保存中にエラーが発生しました：\n{str(e)}"
            )
    
    def _validate_input(self) -> bool:
        """入力値バリデーション"""
        # タスク名必須チェック
        if not self.name_edit.text().strip():
            QMessageBox.warning(
                self, "入力エラー",
                "タスク名は必須入力です。"
            )
            self.tab_widget.setCurrentIndex(0)
            self.name_edit.setFocus()
            return False
        
        # プロセスID必須チェック
        if not self.process_id:
            QMessageBox.critical(
                self, "設定エラー",
                "親プロセスが設定されていません。"
            )
            return False
        
        return True
    
    def _collect_form_data(self) -> Dict[str, Any]:
        """フォームデータを収集"""
        tags = []
        for i in range(self.tag_list.count()):
            tags.append(self.tag_list.item(i).text())
        
        return {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'status': self.status_combo.currentText(),
            'status_comment': self.status_comment_edit.text().strip(),
            'priority': self.priority_spin.value(),
            'notes': self.notes_edit.toPlainText().strip(),
            'estimated_hours': self.estimated_hours_spin.value() if self.estimated_hours_spin.value() > 0 else None,
            'actual_hours': self.actual_hours_spin.value() if self.actual_hours_spin.value() > 0 else None,
            'tags': tags
        }
    
    def _apply_additional_data(self, task: Task, data: Dict[str, Any]):
        """追加データをタスクに適用"""
        task.set_status(data['status'], "user", data.get('status_comment', ''))
        task.set_priority(data['priority'])
        task.notes = data['notes']
        
        if data['estimated_hours'] is not None:
            task.set_estimated_hours(data['estimated_hours'])
        if data['actual_hours'] is not None:
            task.set_actual_hours(data['actual_hours'])
        
        task.tags = data['tags']
    
    def _apply_form_data_to_task(self, data: Dict[str, Any]):
        """フォームデータを既存タスクに適用"""
        self.task.name = data['name']
        self.task.description = data['description']
        self.task.set_priority(data['priority'])
        self.task.notes = data['notes']
        
        if data['estimated_hours'] is not None:
            self.task.set_estimated_hours(data['estimated_hours'])
        else:
            self.task.estimated_hours = None
            
        if data['actual_hours'] is not None:
            self.task.set_actual_hours(data['actual_hours'])
        else:
            self.task.actual_hours = None
        
        self.task.tags = data['tags']
        
        # ステータス変更は別途処理されるため、ここでは設定しない
    
    def load_task_data(self):
        """タスクデータをフォームに読み込み"""
        if not self.task:
            return
        
        # 基本情報
        self.name_edit.setText(self.task.name)
        self.description_edit.setPlainText(self.task.description)
        
        # ステータス
        index = self.status_combo.findText(self.task.status)
        if index >= 0:
            self.status_combo.setCurrentIndex(index)
        
        # 属性
        self.priority_spin.setValue(self.task.priority)
        self.notes_edit.setPlainText(self.task.notes)
        
        # 工数
        if self.task.estimated_hours is not None:
            self.estimated_hours_spin.setValue(self.task.estimated_hours)
        if self.task.actual_hours is not None:
            self.actual_hours_spin.setValue(self.task.actual_hours)
        
        # タグ
        self.tag_list.clear()
        for tag in self.task.tags:
            self.tag_list.addItem(tag)
        
        # 表示更新
        self._update_completion_display()
        self._update_efficiency_analysis()
        
        # ステータス履歴
        self._update_status_history()
        
        # 統計情報
        self._update_statistics()
    
    def _update_status_history(self):
        """ステータス履歴を更新"""
        if not self.task or not self.task.status_history:
            self.history_table.setRowCount(0)
            self.total_changes_label.setText("変更回数: 0")
            self.last_change_label.setText("最終変更: 未変更")
            return
        
        # テーブル設定
        history = self.task.status_history
        self.history_table.setRowCount(len(history))
        
        for i, change in enumerate(history):
            # 変更日時
            self.history_table.setItem(i, 0, QTableWidgetItem(
                change.changed_at.strftime("%Y/%m/%d %H:%M")
            ))
            
            # 変更前ステータス
            self.history_table.setItem(i, 1, QTableWidgetItem(
                change.old_status if change.old_status else "新規作成"
            ))
            
            # 変更後ステータス
            self.history_table.setItem(i, 2, QTableWidgetItem(change.new_status))
            
            # 変更者
            self.history_table.setItem(i, 3, QTableWidgetItem(change.changed_by))
            
            # コメント
            self.history_table.setItem(i, 4, QTableWidgetItem(change.comment))
        
        # 統計更新
        self.total_changes_label.setText(f"変更回数: {len(history)}")
        
        if history:
            last_change = history[-1]
            self.last_change_label.setText(
                f"最終変更: {last_change.changed_at.strftime('%Y/%m/%d %H:%M')} "
                f"({last_change.changed_by})"
            )
    
    def _update_statistics(self):
        """統計情報を更新"""
        if not self.task:
            return
        
        # 基本情報
        self.created_label.setText(self.task.created_at.strftime("%Y/%m/%d %H:%M"))
        self.updated_label.setText(self.task.updated_at.strftime("%Y/%m/%d %H:%M"))
        self.id_label.setText(self.task.id)
        
        # 進捗分析
        completion_rate = self.task.get_completion_percentage()
        self.completion_rate_label.setText(f"{completion_rate:.0f}%")
        
        if completion_rate == 100.0:
            self.completion_rate_label.setStyleSheet("color: green; font-weight: bold;")
        elif completion_rate > 0:
            self.completion_rate_label.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.completion_rate_label.setStyleSheet("color: gray;")
        
        self.current_status_label.setText(self.task.status)
        
        # 現ステータス期間
        if self.task.status_history:
            last_change = self.task.status_history[-1]
            duration = datetime.now() - last_change.changed_at
            days = duration.days
            hours = duration.seconds // 3600
            
            if days > 0:
                self.status_duration_label.setText(f"{days}日{hours}時間")
            else:
                self.status_duration_label.setText(f"{hours}時間")
        else:
            self.status_duration_label.setText("作成以来")
        
        # 分類情報
        if hasattr(self, 'tag_count_label'):
            self.tag_count_label.setText(str(len(self.task.tags)))
            
            # 優先度分析
            priority = self.task.priority
            if priority == 1:
                priority_text = "最高優先度"
                priority_color = "color: red; font-weight: bold;"
            elif priority == 2:
                priority_text = "高優先度"
                priority_color = "color: orange; font-weight: bold;"
            elif priority == 3:
                priority_text = "標準優先度"
                priority_color = "color: gray;"
            elif priority == 4:
                priority_text = "低優先度"
                priority_color = "color: blue;"
            else:
                priority_text = "最低優先度"
                priority_color = "color: green;"
            
            self.priority_analysis_label.setText(priority_text)
            self.priority_analysis_label.setStyleSheet(priority_color)
    
    def reset_form(self):
        """フォームをリセット"""
        if self.is_new_task:
            # 新規作成時のデフォルト値設定
            self.name_edit.clear()
            self.description_edit.clear()
            self.status_combo.setCurrentText(TaskStatus.NOT_STARTED)
            self.status_comment_edit.clear()
            self.priority_spin.setValue(3)
            self.notes_edit.clear()
            self.estimated_hours_spin.setValue(0)
            self.actual_hours_spin.setValue(0)
            self.tag_list.clear()
            
            # 表示更新
            self._update_completion_display()
            self._update_efficiency_analysis()
            
            # 履歴・統計タブを無効化
            self.tab_widget.setTabEnabled(2, False)
            self.tab_widget.setTabEnabled(3, False)
        else:
            # 既存タスクデータ読み込み
            self.load_task_data()
            self.tab_widget.setTabEnabled(2, True)
            self.tab_widget.setTabEnabled(3, True)
        
        self.is_modified = False
        if hasattr(self, 'save_btn'):
            self.save_btn.setText("保存")
    
    def closeEvent(self, event):
        """ダイアログ終了時の確認"""
        if self.mode != 'view' and self.is_modified:
            reply = QMessageBox.question(
                self, "確認",
                "変更が保存されていません。閉じてもよろしいですか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        
        event.accept()
