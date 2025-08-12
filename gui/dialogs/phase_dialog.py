"""
フェーズ編集ダイアログ
フェーズの作成・編集・詳細表示
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QDateEdit, QCheckBox, QPushButton, QLabel, QGroupBox,
    QListWidget, QListWidgetItem, QMessageBox, QTabWidget,
    QWidget, QScrollArea, QFrame, QProgressBar
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QIcon
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from ...models.phase import Phase


class PhaseDialog(QDialog):
    """フェーズ編集ダイアログクラス"""
    
    # シグナル定義
    phase_saved = pyqtSignal(str)  # フェーズID
    phase_updated = pyqtSignal(str)  # フェーズID
    
    def __init__(self, parent=None, project_management_system=None,
                 phase: Optional[Phase] = None, project_id: str = None, 
                 mode: str = 'edit'):
        """
        フェーズダイアログの初期化
        
        Args:
            parent: 親ウィンドウ
            project_management_system: プロジェクト管理システム
            phase: 編集対象フェーズ（Noneの場合は新規作成）
            project_id: 親プロジェクトID（新規作成時）
            mode: 'edit', 'create', 'view'
        """
        super().__init__(parent)
        self.pms = project_management_system
        self.phase = phase
        self.project_id = project_id or (phase.parent_project_id if phase else None)
        self.mode = mode
        self.is_new_phase = phase is None
        
        # UI状態
        self.is_modified = False
        
        # 親プロジェクトの情報取得
        self.parent_project = None
        if self.project_id and self.pms:
            self.parent_project = self.pms.get_project(self.project_id)
        
        self._setup_ui()
        self._connect_signals()
        self.reset_form()
        
        # ウィンドウ設定
        self.setModal(True)
        self.resize(550, 600)
        
        # タイトル設定
        project_name = self.parent_project.name if self.parent_project else "不明"
        if self.mode == 'create':
            self.setWindowTitle(f"新規フェーズ作成 - プロジェクト: {project_name}")
        elif self.mode == 'view':
            self.setWindowTitle(f"フェーズ詳細: {phase.name if phase else ''}")
        else:
            self.setWindowTitle(f"フェーズ編集: {phase.name if phase else ''}")
    
    def _setup_ui(self):
        """UI要素を設定"""
        layout = QVBoxLayout(self)
        
        # 親プロジェクト情報表示
        if self.parent_project:
            project_info = QLabel(f"所属プロジェクト: {self.parent_project.name}")
            project_info.setStyleSheet("font-weight: bold; color: #0066cc; padding: 5px;")
            layout.addWidget(project_info)
        
        # タブウィジェット作成
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 基本情報タブ
        self._create_basic_tab()
        
        # プロセス管理タブ
        self._create_processes_tab()
        
        # 統計・進捗タブ
        self._create_statistics_tab()
        
        # ボタン
        self._create_buttons(layout)
    
    def _create_basic_tab(self):
        """基本情報タブを作成"""
        basic_widget = QWidget()
        layout = QFormLayout(basic_widget)
        layout.setSpacing(10)
        
        # フェーズ名（必須）
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("フェーズ名を入力してください（必須）")
        layout.addRow("フェーズ名 *:", self.name_edit)
        
        # 説明
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("フェーズの説明")
        layout.addRow("説明:", self.description_edit)
        
        # 期間設定
        date_group = QGroupBox("期間設定")
        date_layout = QFormLayout(date_group)
        
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate().addDays(30))
        date_layout.addRow("終了日:", self.end_date_edit)
        
        layout.addRow(date_group)
        
        # 優先度・重要度
        priority_layout = QHBoxLayout()
        
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 5)
        self.priority_spin.setValue(3)
        self.priority_spin.setToolTip("1:最高 → 5:最低")
        priority_layout.addWidget(self.priority_spin)
        
        layout.addRow("優先度:", priority_layout)
        
        # マイルストーン
        self.milestone_edit = QLineEdit()
        self.milestone_edit.setPlaceholderText("マイルストーン名（任意）")
        layout.addRow("マイルストーン:", self.milestone_edit)
        
        # 進捗情報表示（読み取り専用）
        progress_group = QGroupBox("進捗情報")
        progress_layout = QFormLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addRow("進捗率:", self.progress_bar)
        
        self.progress_label = QLabel("0.0%")
        self.progress_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        progress_layout.addRow("詳細進捗:", self.progress_label)
        
        self.status_label = QLabel("未着手")
        progress_layout.addRow("ステータス:", self.status_label)
        
        layout.addRow(progress_group)
        
        # 備考
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(100)
        self.notes_edit.setPlaceholderText("フェーズに関する備考・メモ")
        layout.addRow("備考:", self.notes_edit)
        
        self.tab_widget.addTab(basic_widget, "基本情報")
    
    def _create_processes_tab(self):
        """プロセス管理タブを作成"""
        processes_widget = QWidget()
        layout = QVBoxLayout(processes_widget)
        
        # 成果物管理
        deliverables_group = QGroupBox("成果物管理")
        deliverables_layout = QVBoxLayout(deliverables_group)
        
        # 追加用入力
        add_layout = QHBoxLayout()
        self.deliverable_input = QLineEdit()
        self.deliverable_input.setPlaceholderText("成果物名を入力")
        add_layout.addWidget(self.deliverable_input)
        
        self.add_deliverable_btn = QPushButton("追加")
        self.add_deliverable_btn.clicked.connect(self._add_deliverable)
        add_layout.addWidget(self.add_deliverable_btn)
        
        deliverables_layout.addLayout(add_layout)
        
        # リスト表示
        self.deliverable_list = QListWidget()
        self.deliverable_list.setMaximumHeight(120)
        deliverables_layout.addWidget(self.deliverable_list)
        
        self.remove_deliverable_btn = QPushButton("選択項目を削除")
        self.remove_deliverable_btn.clicked.connect(self._remove_deliverable)
        deliverables_layout.addWidget(self.remove_deliverable_btn)
        
        layout.addWidget(deliverables_group)
        
        # プロセス統計（既存フェーズの場合）
        if not self.is_new_phase:
            process_group = QGroupBox("プロセス統計")
            process_layout = QFormLayout(process_group)
            
            self.process_count_label = QLabel("0")
            process_layout.addRow("プロセス数:", self.process_count_label)
            
            self.completed_processes_label = QLabel("0")
            process_layout.addRow("完了プロセス:", self.completed_processes_label)
            
            self.process_completion_label = QLabel("0.0%")
            process_layout.addRow("プロセス完了率:", self.process_completion_label)
            
            layout.addWidget(process_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(processes_widget, "成果物・プロセス")
    
    def _create_statistics_tab(self):
        """統計・進捗タブを作成"""
        stats_widget = QWidget()
        layout = QVBoxLayout(stats_widget)
        
        # 作成・更新情報
        info_group = QGroupBox("フェーズ情報")
        info_layout = QFormLayout(info_group)
        
        self.created_label = QLabel("")
        info_layout.addRow("作成日時:", self.created_label)
        
        self.updated_label = QLabel("")
        info_layout.addRow("最終更新:", self.updated_label)
        
        self.id_label = QLabel("")
        self.id_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info_layout.addRow("フェーズID:", self.id_label)
        
        layout.addWidget(info_group)
        
        # 期間・期限情報
        schedule_group = QGroupBox("スケジュール分析")
        schedule_layout = QFormLayout(schedule_group)
        
        self.calculated_start_label = QLabel("")
        schedule_layout.addRow("算出開始日:", self.calculated_start_label)
        
        self.calculated_end_label = QLabel("")
        schedule_layout.addRow("算出終了日:", self.calculated_end_label)
        
        self.remaining_label = QLabel("")
        schedule_layout.addRow("残り日数:", self.remaining_label)
        
        self.overdue_label = QLabel("")
        schedule_layout.addRow("期限状況:", self.overdue_label)
        
        layout.addWidget(schedule_group)
        
        # 工数情報（フェーズが存在する場合のみ）
        if not self.is_new_phase:
            hours_group = QGroupBox("工数統計")
            hours_layout = QFormLayout(hours_group)
            
            self.estimated_hours_label = QLabel("")
            hours_layout.addRow("予想工数合計:", self.estimated_hours_label)
            
            self.actual_hours_label = QLabel("")
            hours_layout.addRow("実績工数合計:", self.actual_hours_label)
            
            self.efficiency_label = QLabel("")
            hours_layout.addRow("効率性:", self.efficiency_label)
            
            layout.addWidget(hours_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(stats_widget, "統計情報")
    
    def _create_buttons(self, layout):
        """ボタン群を作成"""
        button_layout = QHBoxLayout()
        
        # 左側ボタン
        if not self.is_new_phase and self.mode != 'view':
            self.refresh_btn = QPushButton("データ更新")
            self.refresh_btn.clicked.connect(self._refresh_data)
            button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        
        # 右側ボタン
        if self.mode != 'view':
            self.save_btn = QPushButton("保存")
            self.save_btn.clicked.connect(self._save_phase)
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
            self.end_date_edit.dateChanged.connect(self._on_data_changed)
            self.priority_spin.valueChanged.connect(self._on_data_changed)
            self.milestone_edit.textChanged.connect(self._on_data_changed)
            self.notes_edit.textChanged.connect(self._on_data_changed)
            
            # Enterキーでの追加
            self.deliverable_input.returnPressed.connect(self._add_deliverable)
    
    def _on_data_changed(self):
        """データ変更時の処理"""
        self.is_modified = True
        if hasattr(self, 'save_btn'):
            self.save_btn.setText("保存 *")
    
    def _add_deliverable(self):
        """成果物を追加"""
        text = self.deliverable_input.text().strip()
        if text:
            self.deliverable_list.addItem(text)
            self.deliverable_input.clear()
            self._on_data_changed()
    
    def _remove_deliverable(self):
        """選択された成果物を削除"""
        current_row = self.deliverable_list.currentRow()
        if current_row >= 0:
            self.deliverable_list.takeItem(current_row)
            self._on_data_changed()
    
    def _refresh_data(self):
        """データを最新状態に更新"""
        if self.phase and self.pms:
            updated_phase = self.pms.get_phase(self.phase.id)
            if updated_phase:
                self.phase = updated_phase
                self.load_phase_data()
                
                QMessageBox.information(
                    self, "更新完了", 
                    "フェーズデータを最新状態に更新しました。"
                )
    
    def _save_phase(self):
        """フェーズを保存"""
        try:
            # バリデーション
            if not self._validate_input():
                return
            
            # データ収集
            phase_data = self._collect_form_data()
            
            if self.is_new_phase:
                # 新規作成
                phase = self.pms.create_phase(
                    phase_data['name'],
                    self.project_id,
                    phase_data['description']
                )
                
                # 追加属性設定
                self._apply_additional_data(phase, phase_data)
                
                # 更新
                self.pms.update_phase(phase)
                
                self.phase = phase
                self.phase_saved.emit(phase.id)
                
                QMessageBox.information(
                    self, "作成完了",
                    f"フェーズ「{phase.name}」を作成しました。"
                )
                
            else:
                # 既存更新
                self._apply_form_data_to_phase(phase_data)
                
                success = self.pms.update_phase(self.phase)
                if success:
                    self.phase_updated.emit(self.phase.id)
                    
                    QMessageBox.information(
                        self, "更新完了",
                        f"フェーズ「{self.phase.name}」を更新しました。"
                    )
                else:
                    QMessageBox.critical(
                        self, "更新エラー",
                        "フェーズの更新に失敗しました。"
                    )
                    return
            
            self.is_modified = False
            self.save_btn.setText("保存")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self, "保存エラー",
                f"フェーズの保存中にエラーが発生しました：\n{str(e)}"
            )
    
    def _validate_input(self) -> bool:
        """入力値バリデーション"""
        # フェーズ名必須チェック
        if not self.name_edit.text().strip():
            QMessageBox.warning(
                self, "入力エラー",
                "フェーズ名は必須入力です。"
            )
            self.tab_widget.setCurrentIndex(0)
            self.name_edit.setFocus()
            return False
        
        # プロジェクトID必須チェック
        if not self.project_id:
            QMessageBox.critical(
                self, "設定エラー",
                "親プロジェクトが設定されていません。"
            )
            return False
        
        return True
    
    def _collect_form_data(self) -> Dict[str, Any]:
        """フォームデータを収集"""
        deliverables = []
        for i in range(self.deliverable_list.count()):
            deliverables.append(self.deliverable_list.item(i).text())
        
        return {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'end_date': self.end_date_edit.date().toPython() if self.end_date_edit.date().isValid() else None,
            'priority': self.priority_spin.value(),
            'milestone': self.milestone_edit.text().strip(),
            'notes': self.notes_edit.toPlainText().strip(),
            'deliverables': deliverables
        }
    
    def _apply_additional_data(self, phase: Phase, data: Dict[str, Any]):
        """追加データをフェーズに適用"""
        phase.set_end_date(data['end_date'])
        phase.priority = data['priority']
        phase.milestone = data['milestone']
        phase.notes = data['notes']
        phase.deliverables = data['deliverables']
    
    def _apply_form_data_to_phase(self, data: Dict[str, Any]):
        """フォームデータを既存フェーズに適用"""
        self.phase.name = data['name']
        self.phase.description = data['description']
        self.phase.set_end_date(data['end_date'])
        self.phase.priority = data['priority']
        self.phase.milestone = data['milestone']
        self.phase.notes = data['notes']
        self.phase.deliverables = data['deliverables']
    
    def load_phase_data(self):
        """フェーズデータをフォームに読み込み"""
        if not self.phase:
            return
        
        # 基本情報
        self.name_edit.setText(self.phase.name)
        self.description_edit.setPlainText(self.phase.description)
        
        # 日付
        if self.phase.end_date:
            self.end_date_edit.setDate(QDate(self.phase.end_date))
        
        # 詳細情報
        self.priority_spin.setValue(self.phase.priority)
        self.milestone_edit.setText(self.phase.milestone)
        self.notes_edit.setPlainText(self.phase.notes)
        
        # 進捗情報
        self.progress_bar.setValue(int(self.phase.progress))
        self.progress_label.setText(f"{self.phase.progress:.1f}%")
        self.status_label.setText(self.phase.get_status())
        
        # 成果物
        self.deliverable_list.clear()
        for deliverable in self.phase.deliverables:
            self.deliverable_list.addItem(deliverable)
        
        # 統計情報
        self._update_statistics()
    
    def _update_statistics(self):
        """統計情報を更新"""
        if not self.phase:
            return
        
        # 作成・更新情報
        self.created_label.setText(self.phase.created_at.strftime("%Y/%m/%d %H:%M"))
        self.updated_label.setText(self.phase.updated_at.strftime("%Y/%m/%d %H:%M"))
        self.id_label.setText(self.phase.id)
        
        # 期間情報
        if self.pms:
            date_range = self.phase.get_date_range(self.pms.process_manager)
            
            start_date = date_range.get('start_date')
            if start_date:
                self.calculated_start_label.setText(start_date.strftime("%Y/%m/%d"))
            else:
                self.calculated_start_label.setText("算出不可")
            
            end_date = date_range.get('end_date')
            if end_date:
                self.calculated_end_label.setText(end_date.strftime("%Y/%m/%d"))
            else:
                self.calculated_end_label.setText("算出不可")
        
        # 残り日数
        remaining = self.phase.get_remaining_days()
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
        if self.phase.is_overdue():
            self.overdue_label.setText("期限超過")
            self.overdue_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.overdue_label.setText("正常")
            self.overdue_label.setStyleSheet("color: green;")
        
        # プロセス統計
        if self.pms and hasattr(self, 'process_count_label'):
            stats = self.phase.get_process_statistics(self.pms.process_manager)
            self.process_count_label.setText(str(stats['total']))
            self.completed_processes_label.setText(str(stats['completed']))
            self.process_completion_label.setText(f"{stats['completion_rate']:.1f}%")
            
            # 工数統計
            if hasattr(self, 'estimated_hours_label'):
                estimated = self.phase.calculate_total_estimated_hours(self.pms.process_manager)
                actual = self.phase.calculate_total_actual_hours(self.pms.process_manager)
                
                if estimated:
                    self.estimated_hours_label.setText(f"{estimated:.1f}時間")
                else:
                    self.estimated_hours_label.setText("未設定")
                
                if actual:
                    self.actual_hours_label.setText(f"{actual:.1f}時間")
                else:
                    self.actual_hours_label.setText("未設定")
                
                if estimated and actual and estimated > 0:
                    efficiency = actual / estimated
                    if efficiency <= 1.0:
                        self.efficiency_label.setText(f"{efficiency:.2f} (効率的)")
                        self.efficiency_label.setStyleSheet("color: green;")
                    else:
                        self.efficiency_label.setText(f"{efficiency:.2f} (超過)")
                        self.efficiency_label.setStyleSheet("color: red;")
                else:
                    self.efficiency_label.setText("算出不可")
                    self.efficiency_label.setStyleSheet("color: gray;")
    
    def reset_form(self):
        """フォームをリセット"""
        if self.is_new_phase:
            # 新規作成時のデフォルト値設定
            self.name_edit.clear()
            self.description_edit.clear()
            self.end_date_edit.setDate(QDate.currentDate().addDays(30))
            self.priority_spin.setValue(3)
            self.milestone_edit.clear()
            self.notes_edit.clear()
            self.deliverable_list.clear()
            
            # 進捗情報初期化
            self.progress_bar.setValue(0)
            self.progress_label.setText("0.0%")
            self.status_label.setText("未着手")
            
            # 統計タブを無効化
            if self.tab_widget.count() > 2:
                self.tab_widget.setTabEnabled(2, False)
        else:
            # 既存フェーズデータ読み込み
            self.load_phase_data()
            if self.tab_widget.count() > 2:
                self.tab_widget.setTabEnabled(2, True)
        
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
