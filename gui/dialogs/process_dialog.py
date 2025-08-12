"""
プロセス編集ダイアログ
プロセスの作成・編集・詳細表示
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QDateEdit, QCheckBox, QPushButton, QLabel, QGroupBox,
    QListWidget, QListWidgetItem, QMessageBox, QTabWidget,
    QWidget, QScrollArea, QFrame, QProgressBar, QSlider
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QIcon
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from ...models.process import Process


class ProcessDialog(QDialog):
    """プロセス編集ダイアログクラス"""
    
    # シグナル定義
    process_saved = pyqtSignal(str)  # プロセスID
    process_updated = pyqtSignal(str)  # プロセスID
    
    def __init__(self, parent=None, project_management_system=None,
                 process: Optional[Process] = None, phase_id: str = None, 
                 mode: str = 'edit'):
        """
        プロセスダイアログの初期化
        
        Args:
            parent: 親ウィンドウ
            project_management_system: プロジェクト管理システム
            process: 編集対象プロセス（Noneの場合は新規作成）
            phase_id: 親フェーズID（新規作成時）
            mode: 'edit', 'create', 'view'
        """
        super().__init__(parent)
        self.pms = project_management_system
        self.process = process
        self.phase_id = phase_id or (process.parent_phase_id if process else None)
        self.mode = mode
        self.is_new_process = process is None
        
        # UI状態
        self.is_modified = False
        
        # 親フェーズ・プロジェクトの情報取得
        self.parent_phase = None
        self.parent_project = None
        if self.phase_id and self.pms:
            self.parent_phase = self.pms.get_phase(self.phase_id)
            if self.parent_phase and self.parent_phase.parent_project_id:
                self.parent_project = self.pms.get_project(self.parent_phase.parent_project_id)
        
        self._setup_ui()
        self._connect_signals()
        self.reset_form()
        
        # ウィンドウ設定
        self.setModal(True)
        self.resize(580, 650)
        
        # タイトル設定
        phase_name = self.parent_phase.name if self.parent_phase else "不明"
        if self.mode == 'create':
            self.setWindowTitle(f"新規プロセス作成 - フェーズ: {phase_name}")
        elif self.mode == 'view':
            self.setWindowTitle(f"プロセス詳細: {process.name if process else ''}")
        else:
            self.setWindowTitle(f"プロセス編集: {process.name if process else ''}")
    
    def _setup_ui(self):
        """UI要素を設定"""
        layout = QVBoxLayout(self)
        
        # 親情報表示
        if self.parent_phase and self.parent_project:
            hierarchy_info = QLabel(
                f"プロジェクト: {self.parent_project.name} > フェーズ: {self.parent_phase.name}"
            )
            hierarchy_info.setStyleSheet("font-weight: bold; color: #0066cc; padding: 5px;")
            layout.addWidget(hierarchy_info)
        
        # タブウィジェット作成
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 基本情報タブ
        self._create_basic_tab()
        
        # 進捗・工数タブ
        self._create_progress_tab()
        
        # タスク管理タブ
        self._create_tasks_tab()
        
        # 統計・分析タブ
        self._create_statistics_tab()
        
        # ボタン
        self._create_buttons(layout)
    
    def _create_basic_tab(self):
        """基本情報タブを作成"""
        basic_widget = QWidget()
        layout = QFormLayout(basic_widget)
        layout.setSpacing(10)
        
        # プロセス名（必須）
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("プロセス名を入力してください（必須）")
        layout.addRow("プロセス名 *:", self.name_edit)
        
        # 担当者（必須）
        self.assignee_edit = QLineEdit()
        self.assignee_edit.setPlaceholderText("担当者名を入力してください（必須）")
        layout.addRow("担当者 *:", self.assignee_edit)
        
        # 説明
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("プロセスの説明")
        layout.addRow("説明:", self.description_edit)
        
        # 期間設定
        date_group = QGroupBox("期間設定")
        date_layout = QFormLayout(date_group)
        
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate())
        self.start_date_edit.setSpecialValueText("未設定")
        date_layout.addRow("開始日:", self.start_date_edit)
        
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate().addDays(7))
        self.end_date_edit.setSpecialValueText("未設定")
        date_layout.addRow("終了日:", self.end_date_edit)
        
        layout.addRow(date_group)
        
        # 工数設定
        hours_group = QGroupBox("工数管理")
        hours_layout = QFormLayout(hours_group)
        
        self.estimated_hours_spin = QDoubleSpinBox()
        self.estimated_hours_spin.setRange(0, 9999.9)
        self.estimated_hours_spin.setSuffix(" 時間")
        self.estimated_hours_spin.setDecimals(1)
        hours_layout.addRow("予想工数:", self.estimated_hours_spin)
        
        self.actual_hours_spin = QDoubleSpinBox()
        self.actual_hours_spin.setRange(0, 9999.9)
        self.actual_hours_spin.setSuffix(" 時間")
        self.actual_hours_spin.setDecimals(1)
        hours_layout.addRow("実績工数:", self.actual_hours_spin)
        
        layout.addRow(hours_group)
        
        # 優先度
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 5)
        self.priority_spin.setValue(3)
        self.priority_spin.setToolTip("1:最高 → 5:最低")
        layout.addRow("優先度:", self.priority_spin)
        
        # 備考
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(100)
        self.notes_edit.setPlaceholderText("プロセスに関する備考・メモ")
        layout.addRow("備考:", self.notes_edit)
        
        self.tab_widget.addTab(basic_widget, "基本情報")
    
    def _create_progress_tab(self):
        """進捗・工数タブを作成"""
        progress_widget = QWidget()
        layout = QVBoxLayout(progress_widget)
        
        # 進捗管理設定
        progress_group = QGroupBox("進捗管理")
        progress_layout = QFormLayout(progress_group)
        
        # 進捗管理モード選択
        self.manual_progress_radio = QCheckBox("手動進捗管理")
        self.manual_progress_radio.setToolTip("チェックするとタスクから自動更新されません")
        progress_layout.addRow("管理モード:", self.manual_progress_radio)
        
        # 進捗率設定（スライダー + スピンボックス）
        progress_control_layout = QHBoxLayout()
        
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.setValue(0)
        self.progress_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.progress_slider.setTickInterval(10)
        progress_control_layout.addWidget(self.progress_slider)
        
        self.progress_spin = QDoubleSpinBox()
        self.progress_spin.setRange(0, 100.0)
        self.progress_spin.setSuffix(" %")
        self.progress_spin.setDecimals(1)
        self.progress_spin.setValue(0)
        progress_control_layout.addWidget(self.progress_spin)
        
        progress_layout.addRow("進捗率:", progress_control_layout)
        
        # 進捗率連動
        self.progress_slider.valueChanged.connect(
            lambda v: self.progress_spin.setValue(v)
        )
        self.progress_spin.valueChanged.connect(
            lambda v: self.progress_slider.setValue(int(v))
        )
        
        # ステータス表示
        self.status_label = QLabel("未着手")
        self.status_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        progress_layout.addRow("ステータス:", self.status_label)
        
        layout.addWidget(progress_group)
        
        # 工数分析
        hours_analysis_group = QGroupBox("工数分析")
        hours_analysis_layout = QFormLayout(hours_analysis_group)
        
        self.efficiency_label = QLabel("未算出")
        hours_analysis_layout.addRow("効率性比率:", self.efficiency_label)
        
        self.hours_variance_label = QLabel("未算出")
        hours_analysis_layout.addRow("工数差異:", self.hours_variance_label)
        
        layout.addWidget(hours_analysis_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(progress_widget, "進捗・工数")
    
    def _create_tasks_tab(self):
        """タスク管理タブを作成"""
        tasks_widget = QWidget()
        layout = QVBoxLayout(tasks_widget)
        
        # タスク統計（既存プロセスの場合）
        if not self.is_new_process:
            task_stats_group = QGroupBox("タスク統計")
            task_stats_layout = QFormLayout(task_stats_group)
            
            self.task_count_label = QLabel("0")
            task_stats_layout.addRow("タスク数:", self.task_count_label)
            
            self.completed_tasks_label = QLabel("0")
            task_stats_layout.addRow("完了タスク:", self.completed_tasks_label)
            
            self.actionable_tasks_label = QLabel("0")
            task_stats_layout.addRow("実行可能タスク:", self.actionable_tasks_label)
            
            self.task_completion_label = QLabel("0.0%")
            task_stats_layout.addRow("タスク完了率:", self.task_completion_label)
            
            layout.addWidget(task_stats_group)
            
            # タスク工数集計
            task_hours_group = QGroupBox("タスク工数集計")
            task_hours_layout = QFormLayout(task_hours_group)
            
            self.task_estimated_total_label = QLabel("未設定")
            task_hours_layout.addRow("予想工数合計:", self.task_estimated_total_label)
            
            self.task_actual_total_label = QLabel("未設定")
            task_hours_layout.addRow("実績工数合計:", self.task_actual_total_label)
            
            layout.addWidget(task_hours_group)
        
        else:
            # 新規プロセスの場合の説明
            info_label = QLabel(
                "プロセス作成後にタスクを追加・管理できます。\n"
                "タスクの完了状況から進捗率を自動計算することも可能です。"
            )
            info_label.setStyleSheet("color: #666; padding: 20px;")
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tasks_widget, "タスク管理")
    
    def _create_statistics_tab(self):
        """統計・分析タブを作成"""
        stats_widget = QWidget()
        layout = QVBoxLayout(stats_widget)
        
        # 作成・更新情報
        info_group = QGroupBox("プロセス情報")
        info_layout = QFormLayout(info_group)
        
        self.created_label = QLabel("")
        info_layout.addRow("作成日時:", self.created_label)
        
        self.updated_label = QLabel("")
        info_layout.addRow("最終更新:", self.updated_label)
        
        self.id_label = QLabel("")
        self.id_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info_layout.addRow("プロセスID:", self.id_label)
        
        layout.addWidget(info_group)
        
        # スケジュール分析
        schedule_group = QGroupBox("スケジュール分析")
        schedule_layout = QFormLayout(schedule_group)
        
        self.duration_label = QLabel("")
        schedule_layout.addRow("プロセス期間:", self.duration_label)
        
        self.remaining_label = QLabel("")
        schedule_layout.addRow("残り日数:", self.remaining_label)
        
        self.overdue_label = QLabel("")
        schedule_layout.addRow("期限状況:", self.overdue_label)
        
        layout.addWidget(schedule_group)
        
        # パフォーマンス分析（既存プロセスの場合のみ）
        if not self.is_new_process:
            performance_group = QGroupBox("パフォーマンス分析")
            performance_layout = QFormLayout(performance_group)
            
            self.daily_progress_label = QLabel("")
            performance_layout.addRow("1日あたり進捗:", self.daily_progress_label)
            
            self.estimated_completion_label = QLabel("")
            performance_layout.addRow("完了予想日:", self.estimated_completion_label)
            
            layout.addWidget(performance_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(stats_widget, "統計分析")
    
    def _create_buttons(self, layout):
        """ボタン群を作成"""
        button_layout = QHBoxLayout()
        
        # 左側ボタン
        if not self.is_new_process and self.mode != 'view':
            self.refresh_btn = QPushButton("データ更新")
            self.refresh_btn.clicked.connect(self._refresh_data)
            button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        
        # 右側ボタン
        if self.mode != 'view':
            self.save_btn = QPushButton("保存")
            self.save_btn.clicked.connect(self._save_process)
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
            self.assignee_edit.textChanged.connect(self._on_data_changed)
            self.description_edit.textChanged.connect(self._on_data_changed)
            self.start_date_edit.dateChanged.connect(self._on_data_changed)
            self.end_date_edit.dateChanged.connect(self._on_data_changed)
            self.estimated_hours_spin.valueChanged.connect(self._on_data_changed)
            self.actual_hours_spin.valueChanged.connect(self._on_data_changed)
            self.priority_spin.valueChanged.connect(self._on_data_changed)
            self.notes_edit.textChanged.connect(self._on_data_changed)
            self.manual_progress_radio.toggled.connect(self._on_data_changed)
            self.progress_spin.valueChanged.connect(self._on_data_changed)
            
            # 進捗率変更時のステータス更新
            self.progress_spin.valueChanged.connect(self._update_status_display)
            
            # 工数変更時の効率性更新
            self.estimated_hours_spin.valueChanged.connect(self._update_efficiency_display)
            self.actual_hours_spin.valueChanged.connect(self._update_efficiency_display)
    
    def _on_data_changed(self):
        """データ変更時の処理"""
        self.is_modified = True
        if hasattr(self, 'save_btn'):
            self.save_btn.setText("保存 *")
    
    def _update_status_display(self):
        """ステータス表示を更新"""
        progress = self.progress_spin.value()
        if progress == 0.0:
            status = "未着手"
            color = "#666666"
        elif progress == 100.0:
            status = "完了"
            color = "#00aa00"
        else:
            status = "進行中"
            color = "#0066cc"
        
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"font-weight: bold; color: {color};")
    
    def _update_efficiency_display(self):
        """効率性表示を更新"""
        estimated = self.estimated_hours_spin.value()
        actual = self.actual_hours_spin.value()
        
        if estimated > 0 and actual > 0:
            efficiency = actual / estimated
            if efficiency <= 1.0:
                self.efficiency_label.setText(f"{efficiency:.2f} (効率的)")
                self.efficiency_label.setStyleSheet("color: green;")
            elif efficiency <= 1.2:
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
    
    def _refresh_data(self):
        """データを最新状態に更新"""
        if self.process and self.pms:
            updated_process = self.pms.get_process(self.process.id)
            if updated_process:
                self.process = updated_process
                self.load_process_data()
                
                QMessageBox.information(
                    self, "更新完了", 
                    "プロセスデータを最新状態に更新しました。"
                )
    
    def _save_process(self):
        """プロセスを保存"""
        try:
            # バリデーション
            if not self._validate_input():
                return
            
            # データ収集
            process_data = self._collect_form_data()
            
            if self.is_new_process:
                # 新規作成
                process = self.pms.create_process(
                    process_data['name'],
                    process_data['assignee'],
                    process_data['description'],
                    self.phase_id
                )
                
                # 追加属性設定
                self._apply_additional_data(process, process_data)
                
                # 更新
                self.pms.update_process(process)
                
                self.process = process
                self.process_saved.emit(process.id)
                
                QMessageBox.information(
                    self, "作成完了",
                    f"プロセス「{process.name}」を作成しました。"
                )
                
            else:
                # 既存更新
                self._apply_form_data_to_process(process_data)
                
                success = self.pms.update_process(self.process)
                if success:
                    self.process_updated.emit(self.process.id)
                    
                    QMessageBox.information(
                        self, "更新完了",
                        f"プロセス「{self.process.name}」を更新しました。"
                    )
                else:
                    QMessageBox.critical(
                        self, "更新エラー",
                        "プロセスの更新に失敗しました。"
                    )
                    return
            
            self.is_modified = False
            self.save_btn.setText("保存")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self, "保存エラー",
                f"プロセスの保存中にエラーが発生しました：\n{str(e)}"
            )
    
    def _validate_input(self) -> bool:
        """入力値バリデーション"""
        # プロセス名必須チェック
        if not self.name_edit.text().strip():
            QMessageBox.warning(
                self, "入力エラー",
                "プロセス名は必須入力です。"
            )
            self.tab_widget.setCurrentIndex(0)
            self.name_edit.setFocus()
            return False
        
        # 担当者必須チェック
        if not self.assignee_edit.text().strip():
            QMessageBox.warning(
                self, "入力エラー",
                "担当者は必須入力です。"
            )
            self.tab_widget.setCurrentIndex(0)
            self.assignee_edit.setFocus()
            return False
        
        # 日付順序チェック
        if (self.start_date_edit.date().isValid() and 
            self.end_date_edit.date().isValid()):
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
        
        # フェーズID必須チェック
        if not self.phase_id:
            QMessageBox.critical(
                self, "設定エラー",
                "親フェーズが設定されていません。"
            )
            return False
        
        return True
    
    def _collect_form_data(self) -> Dict[str, Any]:
        """フォームデータを収集"""
        return {
            'name': self.name_edit.text().strip(),
            'assignee': self.assignee_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'start_date': self.start_date_edit.date().toPython() if self.start_date_edit.date().isValid() else None,
            'end_date': self.end_date_edit.date().toPython() if self.end_date_edit.date().isValid() else None,
            'estimated_hours': self.estimated_hours_spin.value() if self.estimated_hours_spin.value() > 0 else None,
            'actual_hours': self.actual_hours_spin.value() if self.actual_hours_spin.value() > 0 else None,
            'priority': self.priority_spin.value(),
            'notes': self.notes_edit.toPlainText().strip(),
            'progress': self.progress_spin.value(),
            'is_progress_manual': self.manual_progress_radio.isChecked()
        }
    
    def _apply_additional_data(self, process: Process, data: Dict[str, Any]):
        """追加データをプロセスに適用"""
        process.set_dates(data['start_date'], data['end_date'])
        if data['estimated_hours'] is not None:
            process.set_estimated_hours(data['estimated_hours'])
        if data['actual_hours'] is not None:
            process.set_actual_hours(data['actual_hours'])
        process.priority = data['priority']
        process.notes = data['notes']
        process.set_progress(data['progress'], data['is_progress_manual'])
    
    def _apply_form_data_to_process(self, data: Dict[str, Any]):
        """フォームデータを既存プロセスに適用"""
        self.process.name = data['name']
        self.process.set_assignee(data['assignee'])
        self.process.description = data['description']
        self.process.set_dates(data['start_date'], data['end_date'])
        
        if data['estimated_hours'] is not None:
            self.process.set_estimated_hours(data['estimated_hours'])
        else:
            self.process.estimated_hours = None
            
        if data['actual_hours'] is not None:
            self.process.set_actual_hours(data['actual_hours'])
        else:
            self.process.actual_hours = None
        
        self.process.priority = data['priority']
        self.process.notes = data['notes']
        self.process.set_progress(data['progress'], data['is_progress_manual'])
    
    def load_process_data(self):
        """プロセスデータをフォームに読み込み"""
        if not self.process:
            return
        
        # 基本情報
        self.name_edit.setText(self.process.name)
        self.assignee_edit.setText(self.process.assignee)
        self.description_edit.setPlainText(self.process.description)
        
        # 日付
        if self.process.start_date:
            self.start_date_edit.setDate(QDate(self.process.start_date))
        if self.process.end_date:
            self.end_date_edit.setDate(QDate(self.process.end_date))
        
        # 工数
        if self.process.estimated_hours is not None:
            self.estimated_hours_spin.setValue(self.process.estimated_hours)
        if self.process.actual_hours is not None:
            self.actual_hours_spin.setValue(self.process.actual_hours)
        
        # その他
        self.priority_spin.setValue(self.process.priority)
        self.notes_edit.setPlainText(self.process.notes)
        
        # 進捗
        self.progress_spin.setValue(self.process.progress)
        self.manual_progress_radio.setChecked(self.process.is_progress_manual)
        
        # 表示更新
        self._update_status_display()
        self._update_efficiency_display()
        
        # 統計情報
        self._update_statistics()
    
    def _update_statistics(self):
        """統計情報を更新"""
        if not self.process:
            return
        
        # 作成・更新情報
        self.created_label.setText(self.process.created_at.strftime("%Y/%m/%d %H:%M"))
        self.updated_label.setText(self.process.updated_at.strftime("%Y/%m/%d %H:%M"))
        self.id_label.setText(self.process.id)
        
        # 期間情報
        if self.process.start_date and self.process.end_date:
            duration = (self.process.end_date - self.process.start_date).days + 1
            self.duration_label.setText(f"{duration}日間")
        else:
            self.duration_label.setText("未設定")
        
        # 残り日数
        remaining = self.process.get_remaining_days()
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
        if self.process.is_overdue():
            self.overdue_label.setText("期限超過")
            self.overdue_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.overdue_label.setText("正常")
            self.overdue_label.setStyleSheet("color: green;")
        
        # タスク統計
        if self.pms and hasattr(self, 'task_count_label'):
            summary = self.process.get_summary(self.pms.task_manager)
            
            self.task_count_label.setText(str(summary['task_count']))
            self.completed_tasks_label.setText(str(summary.get('completed_tasks', 0)))
            self.actionable_tasks_label.setText(str(summary.get('actionable_tasks', 0)))
            self.task_completion_label.setText(f"{summary.get('task_completion_rate', 0):.1f}%")
            
            # タスク工数
            if summary.get('estimated_total'):
                self.task_estimated_total_label.setText(f"{summary['estimated_total']:.1f}時間")
            else:
                self.task_estimated_total_label.setText("未設定")
            
            if summary.get('actual_total'):
                self.task_actual_total_label.setText(f"{summary['actual_total']:.1f}時間")
            else:
                self.task_actual_total_label.setText("未設定")
            
            # パフォーマンス分析
            if hasattr(self, 'daily_progress_label'):
                if self.process.start_date and self.process.progress > 0:
                    days_elapsed = (date.today() - self.process.start_date).days + 1
                    if days_elapsed > 0:
                        daily_progress = self.process.progress / days_elapsed
                        self.daily_progress_label.setText(f"{daily_progress:.1f}%/日")
                        
                        # 完了予想日
                        if daily_progress > 0:
                            remaining_progress = 100 - self.process.progress
                            days_to_complete = remaining_progress / daily_progress
                            estimated_completion = date.today().replace() + timedelta(days=int(days_to_complete))
                            self.estimated_completion_label.setText(estimated_completion.strftime("%Y/%m/%d"))
                        else:
                            self.estimated_completion_label.setText("算出不可")
                    else:
                        self.daily_progress_label.setText("算出不可")
                        self.estimated_completion_label.setText("算出不可")
                else:
                    self.daily_progress_label.setText("未開始")
                    self.estimated_completion_label.setText("未開始")
    
    def reset_form(self):
        """フォームをリセット"""
        if self.is_new_process:
            # 新規作成時のデフォルト値設定
            self.name_edit.clear()
            self.assignee_edit.clear()
            self.description_edit.clear()
            self.start_date_edit.setDate(QDate.currentDate())
            self.end_date_edit.setDate(QDate.currentDate().addDays(7))
            self.estimated_hours_spin.setValue(0)
            self.actual_hours_spin.setValue(0)
            self.priority_spin.setValue(3)
            self.notes_edit.clear()
            self.progress_spin.setValue(0)
            self.manual_progress_radio.setChecked(True)
            
            # 表示更新
            self._update_status_display()
            self._update_efficiency_display()
            
            # 統計タブを無効化
            for i in range(2, self.tab_widget.count()):
                self.tab_widget.setTabEnabled(i, False)
        else:
            # 既存プロセスデータ読み込み
            self.load_process_data()
            for i in range(2, self.tab_widget.count()):
                self.tab_widget.setTabEnabled(i, True)
        
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
