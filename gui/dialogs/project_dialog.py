"""
プロジェクト編集ダイアログ
プロジェクトの作成・編集・詳細表示
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QDateEdit, QCheckBox, QPushButton, QLabel, QGroupBox,
    QListWidget, QListWidgetItem, QMessageBox, QTabWidget,
    QWidget, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QIcon
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from ...models.project import Project
from ...models.base import ProjectStatus


class ProjectDialog(QDialog):
    """プロジェクト編集ダイアログクラス"""
    
    # シグナル定義
    project_saved = pyqtSignal(str)  # プロジェクトID
    project_updated = pyqtSignal(str)  # プロジェクトID
    
    def __init__(self, parent=None, project_management_system=None, 
                 project: Optional[Project] = None, mode: str = 'edit'):
        """
        プロジェクトダイアログの初期化
        
        Args:
            parent: 親ウィンドウ
            project_management_system: プロジェクト管理システム
            project: 編集対象プロジェクト（Noneの場合は新規作成）
            mode: 'edit', 'create', 'view'
        """
        super().__init__(parent)
        self.pms = project_management_system
        self.project = project
        self.mode = mode
        self.is_new_project = project is None
        
        # UI状態
        self.is_modified = False
        
        self._setup_ui()
        self._connect_signals()
        self.reset_form()
        
        # ウィンドウ設定
        self.setModal(True)
        self.resize(600, 700)
        
        # タイトル設定
        if self.mode == 'create':
            self.setWindowTitle("新規プロジェクト作成")
        elif self.mode == 'view':
            self.setWindowTitle(f"プロジェクト詳細: {project.name if project else ''}")
        else:
            self.setWindowTitle(f"プロジェクト編集: {project.name if project else ''}")
    
    def _setup_ui(self):
        """UI要素を設定"""
        layout = QVBoxLayout(self)
        
        # タブウィジェット作成
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 基本情報タブ
        self._create_basic_tab()
        
        # 詳細情報タブ
        self._create_details_tab()
        
        # ステークホルダー・タグタブ
        self._create_stakeholders_tab()
        
        # 統計・進捗タブ
        self._create_statistics_tab()
        
        # ボタン
        self._create_buttons(layout)
    
    def _create_basic_tab(self):
        """基本情報タブを作成"""
        basic_widget = QWidget()
        layout = QFormLayout(basic_widget)
        layout.setSpacing(10)
        
        # プロジェクト名（必須）
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("プロジェクト名を入力してください（必須）")
        layout.addRow("プロジェクト名 *:", self.name_edit)
        
        # 説明
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        self.description_edit.setPlaceholderText("プロジェクトの概要説明")
        layout.addRow("説明:", self.description_edit)
        
        # プロジェクトマネージャー
        self.manager_edit = QLineEdit()
        self.manager_edit.setPlaceholderText("担当PM名")
        layout.addRow("プロジェクトマネージャー:", self.manager_edit)
        
        # ステータス設定グループ
        status_group = QGroupBox("ステータス設定")
        status_layout = QFormLayout(status_group)
        
        self.status_combo = QComboBox()
        self.status_combo.addItems([
            ProjectStatus.NOT_STARTED,
            ProjectStatus.IN_PROGRESS, 
            ProjectStatus.COMPLETED,
            ProjectStatus.ON_HOLD,
            ProjectStatus.CANCELLED
        ])
        status_layout.addRow("ステータス:", self.status_combo)
        
        self.manual_status_check = QCheckBox("手動ステータス管理")
        self.manual_status_check.setToolTip("チェックするとフェーズから自動更新されません")
        status_layout.addRow("", self.manual_status_check)
        
        layout.addRow(status_group)
        
        # 期間設定グループ
        date_group = QGroupBox("期間設定")
        date_layout = QFormLayout(date_group)
        
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate())
        date_layout.addRow("開始日:", self.start_date_edit)
        
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate().addDays(30))
        date_layout.addRow("終了日:", self.end_date_edit)
        
        layout.addRow(date_group)
        
        self.tab_widget.addTab(basic_widget, "基本情報")
    
    def _create_details_tab(self):
        """詳細情報タブを作成"""
        details_widget = QWidget()
        layout = QFormLayout(details_widget)
        layout.setSpacing(10)
        
        # 優先度・リスクレベル
        priority_layout = QHBoxLayout()
        
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 5)
        self.priority_spin.setValue(3)
        self.priority_spin.setToolTip("1:最高 → 5:最低")
        priority_layout.addWidget(self.priority_spin)
        
        priority_layout.addWidget(QLabel("リスクレベル:"))
        self.risk_spin = QSpinBox()
        self.risk_spin.setRange(1, 3)
        self.risk_spin.setValue(2)
        self.risk_spin.setToolTip("1:低 → 3:高")
        priority_layout.addWidget(self.risk_spin)
        
        layout.addRow("優先度:", priority_layout)
        
        # 予算・コスト管理
        budget_group = QGroupBox("予算・コスト管理")
        budget_layout = QFormLayout(budget_group)
        
        self.budget_spin = QDoubleSpinBox()
        self.budget_spin.setRange(0, 999999999)
        self.budget_spin.setSuffix(" 円")
        self.budget_spin.setDecimals(0)
        budget_layout.addRow("予算:", self.budget_spin)
        
        self.actual_cost_spin = QDoubleSpinBox()
        self.actual_cost_spin.setRange(0, 999999999)
        self.actual_cost_spin.setSuffix(" 円")
        self.actual_cost_spin.setDecimals(0)
        budget_layout.addRow("実績コスト:", self.actual_cost_spin)
        
        layout.addRow(budget_group)
        
        # 進捗情報（読み取り専用）
        progress_group = QGroupBox("進捗情報")
        progress_layout = QFormLayout(progress_group)
        
        self.progress_label = QLabel("0.0%")
        self.progress_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        progress_layout.addRow("進捗率:", self.progress_label)
        
        self.phase_count_label = QLabel("0")
        progress_layout.addRow("フェーズ数:", self.phase_count_label)
        
        layout.addRow(progress_group)
        
        # 備考
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(150)
        self.notes_edit.setPlaceholderText("プロジェクトに関する備考・メモ")
        layout.addRow("備考:", self.notes_edit)
        
        self.tab_widget.addTab(details_widget, "詳細情報")
    
    def _create_stakeholders_tab(self):
        """ステークホルダー・タグタブを作成"""
        stake_widget = QWidget()
        layout = QVBoxLayout(stake_widget)
        
        # ステークホルダー管理
        stake_group = QGroupBox("ステークホルダー")
        stake_layout = QVBoxLayout(stake_group)
        
        # 追加用入力
        add_layout = QHBoxLayout()
        self.stakeholder_input = QLineEdit()
        self.stakeholder_input.setPlaceholderText("ステークホルダー名を入力")
        add_layout.addWidget(self.stakeholder_input)
        
        self.add_stakeholder_btn = QPushButton("追加")
        self.add_stakeholder_btn.clicked.connect(self._add_stakeholder)
        add_layout.addWidget(self.add_stakeholder_btn)
        
        stake_layout.addLayout(add_layout)
        
        # リスト表示
        self.stakeholder_list = QListWidget()
        self.stakeholder_list.setMaximumHeight(150)
        stake_layout.addWidget(self.stakeholder_list)
        
        self.remove_stakeholder_btn = QPushButton("選択項目を削除")
        self.remove_stakeholder_btn.clicked.connect(self._remove_stakeholder)
        stake_layout.addWidget(self.remove_stakeholder_btn)
        
        layout.addWidget(stake_group)
        
        # タグ管理
        tag_group = QGroupBox("タグ")
        tag_layout = QVBoxLayout(tag_group)
        
        # 追加用入力
        tag_add_layout = QHBoxLayout()
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("タグを入力")
        tag_add_layout.addWidget(self.tag_input)
        
        self.add_tag_btn = QPushButton("追加")
        self.add_tag_btn.clicked.connect(self._add_tag)
        tag_add_layout.addWidget(self.add_tag_btn)
        
        tag_layout.addLayout(tag_add_layout)
        
        # リスト表示
        self.tag_list = QListWidget()
        self.tag_list.setMaximumHeight(150)
        tag_layout.addWidget(self.tag_list)
        
        self.remove_tag_btn = QPushButton("選択項目を削除")
        self.remove_tag_btn.clicked.connect(self._remove_tag)
        tag_layout.addWidget(self.remove_tag_btn)
        
        layout.addWidget(tag_group)
        
        self.tab_widget.addTab(stake_widget, "関係者・タグ")
    
    def _create_statistics_tab(self):
        """統計・進捗タブを作成"""
        stats_widget = QWidget()
        layout = QVBoxLayout(stats_widget)
        
        # 作成・更新情報
        info_group = QGroupBox("プロジェクト情報")
        info_layout = QFormLayout(info_group)
        
        self.created_label = QLabel("")
        info_layout.addRow("作成日時:", self.created_label)
        
        self.updated_label = QLabel("")
        info_layout.addRow("最終更新:", self.updated_label)
        
        self.id_label = QLabel("")
        self.id_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info_layout.addRow("プロジェクトID:", self.id_label)
        
        layout.addWidget(info_group)
        
        # 期間・期限情報
        schedule_group = QGroupBox("スケジュール分析")
        schedule_layout = QFormLayout(schedule_group)
        
        self.duration_label = QLabel("")
        schedule_layout.addRow("プロジェクト期間:", self.duration_label)
        
        self.remaining_label = QLabel("")
        schedule_layout.addRow("残り日数:", self.remaining_label)
        
        self.overdue_label = QLabel("")
        schedule_layout.addRow("期限状況:", self.overdue_label)
        
        layout.addWidget(schedule_group)
        
        # フェーズ統計（プロジェクトが存在する場合のみ）
        if not self.is_new_project:
            phase_group = QGroupBox("フェーズ統計")
            phase_layout = QFormLayout(phase_group)
            
            self.phase_stats_label = QLabel("")
            phase_layout.addRow("フェーズ分析:", self.phase_stats_label)
            
            layout.addWidget(phase_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(stats_widget, "統計情報")
    
    def _create_buttons(self, layout):
        """ボタン群を作成"""
        button_layout = QHBoxLayout()
        
        # 左側ボタン（情報・機能系）
        if not self.is_new_project and self.mode != 'view':
            self.refresh_btn = QPushButton("データ更新")
            self.refresh_btn.clicked.connect(self._refresh_data)
            button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        
        # 右側ボタン（保存・キャンセル）
        if self.mode != 'view':
            self.save_btn = QPushButton("保存")
            self.save_btn.clicked.connect(self._save_project)
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
            self.manager_edit.textChanged.connect(self._on_data_changed)
            self.status_combo.currentTextChanged.connect(self._on_data_changed)
            self.manual_status_check.toggled.connect(self._on_data_changed)
            self.start_date_edit.dateChanged.connect(self._on_data_changed)
            self.end_date_edit.dateChanged.connect(self._on_data_changed)
            self.priority_spin.valueChanged.connect(self._on_data_changed)
            self.risk_spin.valueChanged.connect(self._on_data_changed)
            self.budget_spin.valueChanged.connect(self._on_data_changed)
            self.actual_cost_spin.valueChanged.connect(self._on_data_changed)
            self.notes_edit.textChanged.connect(self._on_data_changed)
            
            # Enterキーでの追加
            self.stakeholder_input.returnPressed.connect(self._add_stakeholder)
            self.tag_input.returnPressed.connect(self._add_tag)
    
    def _on_data_changed(self):
        """データ変更時の処理"""
        self.is_modified = True
        if hasattr(self, 'save_btn'):
            self.save_btn.setText("保存 *")
    
    def _add_stakeholder(self):
        """ステークホルダーを追加"""
        text = self.stakeholder_input.text().strip()
        if text:
            self.stakeholder_list.addItem(text)
            self.stakeholder_input.clear()
            self._on_data_changed()
    
    def _remove_stakeholder(self):
        """選択されたステークホルダーを削除"""
        current_row = self.stakeholder_list.currentRow()
        if current_row >= 0:
            self.stakeholder_list.takeItem(current_row)
            self._on_data_changed()
    
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
        if self.project and self.pms:
            # 最新のプロジェクトデータを取得
            updated_project = self.pms.get_project(self.project.id)
            if updated_project:
                self.project = updated_project
                self.load_project_data()
                
                QMessageBox.information(
                    self, "更新完了", 
                    "プロジェクトデータを最新状態に更新しました。"
                )
    
    def _save_project(self):
        """プロジェクトを保存"""
        try:
            # バリデーション
            if not self._validate_input():
                return
            
            # データ収集
            project_data = self._collect_form_data()
            
            if self.is_new_project:
                # 新規作成
                project = self.pms.create_project(
                    project_data['name'],
                    project_data['description'],
                    project_data['manager']
                )
                
                # 追加属性設定
                self._apply_additional_data(project, project_data)
                
                # 更新
                self.pms.update_project(project)
                
                self.project = project
                self.project_saved.emit(project.id)
                
                QMessageBox.information(
                    self, "作成完了",
                    f"プロジェクト「{project.name}」を作成しました。"
                )
                
            else:
                # 既存更新
                self._apply_form_data_to_project(project_data)
                
                success = self.pms.update_project(self.project)
                if success:
                    self.project_updated.emit(self.project.id)
                    
                    QMessageBox.information(
                        self, "更新完了",
                        f"プロジェクト「{self.project.name}」を更新しました。"
                    )
                else:
                    QMessageBox.critical(
                        self, "更新エラー",
                        "プロジェクトの更新に失敗しました。"
                    )
                    return
            
            self.is_modified = False
            self.save_btn.setText("保存")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self, "保存エラー",
                f"プロジェクトの保存中にエラーが発生しました：\n{str(e)}"
            )
    
    def _validate_input(self) -> bool:
        """入力値バリデーション"""
        # プロジェクト名必須チェック
        if not self.name_edit.text().strip():
            QMessageBox.warning(
                self, "入力エラー",
                "プロジェクト名は必須入力です。"
            )
            self.tab_widget.setCurrentIndex(0)
            self.name_edit.setFocus()
            return False
        
        # 日付順序チェック
        start_date = self.start_date_edit.date().toPython()
        end_date = self.end_date_edit.date().toPython()
        
        if start_date > end_date:
            QMessageBox.warning(
                self, "入力エラー",
                "開始日は終了日より前の日付を設定してください。"
            )
            self.tab_widget.setCurrentIndex(0)
            self.start_date_edit.setFocus()
            return False
        
        return True
    
    def _collect_form_data(self) -> Dict[str, Any]:
        """フォームデータを収集"""
        stakeholders = []
        for i in range(self.stakeholder_list.count()):
            stakeholders.append(self.stakeholder_list.item(i).text())
        
        tags = []
        for i in range(self.tag_list.count()):
            tags.append(self.tag_list.item(i).text())
        
        return {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'manager': self.manager_edit.text().strip(),
            'status': self.status_combo.currentText(),
            'is_status_manual': self.manual_status_check.isChecked(),
            'start_date': self.start_date_edit.date().toPython() if self.start_date_edit.date().isValid() else None,
            'end_date': self.end_date_edit.date().toPython() if self.end_date_edit.date().isValid() else None,
            'priority': self.priority_spin.value(),
            'risk_level': self.risk_spin.value(),
            'budget': self.budget_spin.value() if self.budget_spin.value() > 0 else None,
            'actual_cost': self.actual_cost_spin.value() if self.actual_cost_spin.value() > 0 else None,
            'notes': self.notes_edit.toPlainText().strip(),
            'stakeholders': stakeholders,
            'tags': tags
        }
    
    def _apply_additional_data(self, project: Project, data: Dict[str, Any]):
        """追加データをプロジェクトに適用"""
        project.set_status(data['status'], data['is_status_manual'])
        project.set_dates(data['start_date'], data['end_date'])
        project.priority = data['priority']
        project.risk_level = data['risk_level']
        
        if data['budget'] is not None:
            project.set_budget(data['budget'])
        if data['actual_cost'] is not None:
            project.set_actual_cost(data['actual_cost'])
        
        project.notes = data['notes']
        
        # ステークホルダー・タグ設定
        project.stakeholders = data['stakeholders']
        project.tags = data['tags']
    
    def _apply_form_data_to_project(self, data: Dict[str, Any]):
        """フォームデータを既存プロジェクトに適用"""
        self.project.name = data['name']
        self.project.description = data['description']
        self.project.manager = data['manager']
        self.project.set_status(data['status'], data['is_status_manual'])
        self.project.set_dates(data['start_date'], data['end_date'])
        self.project.priority = data['priority']
        self.project.risk_level = data['risk_level']
        
        if data['budget'] is not None:
            self.project.set_budget(data['budget'])
        else:
            self.project.budget = None
            
        if data['actual_cost'] is not None:
            self.project.set_actual_cost(data['actual_cost'])
        else:
            self.project.actual_cost = None
        
        self.project.notes = data['notes']
        self.project.stakeholders = data['stakeholders']
        self.project.tags = data['tags']
    
    def load_project_data(self):
        """プロジェクトデータをフォームに読み込み"""
        if not self.project:
            return
        
        # 基本情報
        self.name_edit.setText(self.project.name)
        self.description_edit.setPlainText(self.project.description)
        self.manager_edit.setText(self.project.manager)
        
        # ステータス
        index = self.status_combo.findText(self.project.status)
        if index >= 0:
            self.status_combo.setCurrentIndex(index)
        self.manual_status_check.setChecked(self.project.is_status_manual)
        
        # 日付
        if self.project.start_date:
            self.start_date_edit.setDate(QDate(self.project.start_date))
        if self.project.end_date:
            self.end_date_edit.setDate(QDate(self.project.end_date))
        
        # 詳細情報
        self.priority_spin.setValue(self.project.priority)
        self.risk_spin.setValue(self.project.risk_level)
        
        if self.project.budget is not None:
            self.budget_spin.setValue(self.project.budget)
        if self.project.actual_cost is not None:
            self.actual_cost_spin.setValue(self.project.actual_cost)
        
        self.notes_edit.setPlainText(self.project.notes)
        
        # 進捗情報
        self.progress_label.setText(f"{self.project.progress:.1f}%")
        self.phase_count_label.setText(str(len(self.project.phases)))
        
        # ステークホルダー・タグ
        self.stakeholder_list.clear()
        for stakeholder in self.project.stakeholders:
            self.stakeholder_list.addItem(stakeholder)
        
        self.tag_list.clear()
        for tag in self.project.tags:
            self.tag_list.addItem(tag)
        
        # 統計情報
        self._update_statistics()
    
    def _update_statistics(self):
        """統計情報を更新"""
        if not self.project:
            return
        
        # 作成・更新情報
        self.created_label.setText(self.project.created_at.strftime("%Y/%m/%d %H:%M"))
        self.updated_label.setText(self.project.updated_at.strftime("%Y/%m/%d %H:%M"))
        self.id_label.setText(self.project.id)
        
        # 期間情報
        duration = self.project.get_duration_days()
        if duration:
            self.duration_label.setText(f"{duration}日間")
        else:
            self.duration_label.setText("未設定")
        
        remaining = self.project.get_remaining_days()
        if remaining is not None:
            if remaining > 0:
                self.remaining_label.setText(f"{remaining}日")
                self.remaining_label.setStyleSheet("color: green;")
            elif remaining == 0:
                self.remaining_label.setText("本日が期限")
                self.remaining_label.setStyleSheet("color: orange; font-weight: bold;")
            else:
                self.remaining_label.setText(f"{abs(remaining)}日超過")
                self.remaining_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.remaining_label.setText("期限未設定")
            self.remaining_label.setStyleSheet("color: gray;")
        
        # 期限状況
        if self.project.is_overdue():
            self.overdue_label.setText("期限超過")
            self.overdue_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.overdue_label.setText("正常")
            self.overdue_label.setStyleSheet("color: green;")
        
        # フェーズ統計
        if self.pms and hasattr(self, 'phase_stats_label'):
            stats = self.project.get_phase_statistics(self.pms.phase_manager)
            stats_text = f"合計: {stats['total']}個, 完了: {stats['completed']}個, 進行中: {stats['in_progress']}個"
            if stats['overdue'] > 0:
                stats_text += f", 遅延: {stats['overdue']}個"
            self.phase_stats_label.setText(stats_text)
    
    def reset_form(self):
        """フォームをリセット"""
        if self.is_new_project:
            # 新規作成時のデフォルト値設定
            self.name_edit.clear()
            self.description_edit.clear()
            self.manager_edit.clear()
            self.status_combo.setCurrentText(ProjectStatus.NOT_STARTED)
            self.manual_status_check.setChecked(False)
            self.start_date_edit.setDate(QDate.currentDate())
            self.end_date_edit.setDate(QDate.currentDate().addDays(30))
            self.priority_spin.setValue(3)
            self.risk_spin.setValue(2)
            self.budget_spin.setValue(0)
            self.actual_cost_spin.setValue(0)
            self.notes_edit.clear()
            self.stakeholder_list.clear()
            self.tag_list.clear()
            
            # 統計タブは非表示または無効化
            if self.tab_widget.count() > 3:
                self.tab_widget.setTabEnabled(3, False)
        else:
            # 既存プロジェクトデータ読み込み
            self.load_project_data()
            if self.tab_widget.count() > 3:
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
