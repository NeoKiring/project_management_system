"""
通知管理タブ
通知の一覧表示・フィルタリング・一括操作・設定管理
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QComboBox, QLabel, QGroupBox, QSplitter,
    QTextEdit, QMessageBox, QHeaderView, QCheckBox, QSpinBox,
    QFrame, QToolBar, QMenu, QDialog, QFormLayout, QDialogButtonBox,
    QDoubleSpinBox, QTabWidget, QListWidget, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, pyqtSlot
from PyQt6.QtGui import QAction, QIcon, QFont, QBrush, QColor
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta


class NotificationSettingsDialog(QDialog):
    """通知設定ダイアログ"""
    
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.settings = settings
        self._setup_ui()
        self._load_settings()
        
        self.setWindowTitle("通知設定")
        self.setModal(True)
        self.resize(450, 500)
    
    def _setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # タブウィジェット
        tab_widget = QTabWidget()
        
        # 基本設定タブ
        basic_tab = QWidget()
        basic_layout = QFormLayout(basic_tab)
        
        self.deadline_warning_spin = QSpinBox()
        self.deadline_warning_spin.setRange(1, 30)
        self.deadline_warning_spin.setSuffix(" 日前")
        basic_layout.addRow("期限接近通知:", self.deadline_warning_spin)
        
        self.progress_delay_spin = QDoubleSpinBox()
        self.progress_delay_spin.setRange(10.0, 90.0)
        self.progress_delay_spin.setSuffix(" %")
        basic_layout.addRow("進捗遅延しきい値:", self.progress_delay_spin)
        
        self.insufficient_days_spin = QSpinBox()
        self.insufficient_days_spin.setRange(1, 14)
        self.insufficient_days_spin.setSuffix(" 日前")
        basic_layout.addRow("進捗不足チェック:", self.insufficient_days_spin)
        
        self.insufficient_threshold_spin = QDoubleSpinBox()
        self.insufficient_threshold_spin.setRange(10.0, 90.0)
        self.insufficient_threshold_spin.setSuffix(" %")
        basic_layout.addRow("進捗不足しきい値:", self.insufficient_threshold_spin)
        
        tab_widget.addTab(basic_tab, "基本設定")
        
        # システム設定タブ
        system_tab = QWidget()
        system_layout = QFormLayout(system_tab)
        
        self.check_interval_spin = QSpinBox()
        self.check_interval_spin.setRange(1, 168)
        self.check_interval_spin.setSuffix(" 時間")
        system_layout.addRow("チェック間隔:", self.check_interval_spin)
        
        self.retention_spin = QSpinBox()
        self.retention_spin.setRange(7, 365)
        self.retention_spin.setSuffix(" 日")
        system_layout.addRow("通知保持期間:", self.retention_spin)
        
        tab_widget.addTab(system_tab, "システム設定")
        
        # 通知種別設定タブ
        types_tab = QWidget()
        types_layout = QVBoxLayout(types_tab)
        
        types_layout.addWidget(QLabel("有効にする通知種別:"))
        
        self.type_checkboxes = {}
        from models.notification import NotificationType
        
        for notification_type in [
            NotificationType.DEADLINE_APPROACHING,
            NotificationType.DEADLINE_OVERDUE,
            NotificationType.PROGRESS_DELAY,
            NotificationType.PROGRESS_INSUFFICIENT
        ]:
            checkbox = QCheckBox(notification_type)
            self.type_checkboxes[notification_type] = checkbox
            types_layout.addWidget(checkbox)
        
        types_layout.addStretch()
        tab_widget.addTab(types_tab, "通知種別")
        
        layout.addWidget(tab_widget)
        
        # ボタン
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _load_settings(self):
        """設定を読み込み"""
        self.deadline_warning_spin.setValue(self.settings.deadline_warning_days)
        self.progress_delay_spin.setValue(self.settings.progress_delay_threshold)
        self.insufficient_days_spin.setValue(self.settings.insufficient_progress_days)
        self.insufficient_threshold_spin.setValue(self.settings.insufficient_progress_threshold)
        self.check_interval_spin.setValue(self.settings.check_interval_hours)
        self.retention_spin.setValue(self.settings.retention_days)
        
        for notification_type, checkbox in self.type_checkboxes.items():
            checkbox.setChecked(self.settings.enabled_types.get(notification_type, True))
    
    def get_settings(self):
        """更新された設定を取得"""
        from models.notification import NotificationSettings
        
        new_settings = NotificationSettings()
        new_settings.deadline_warning_days = self.deadline_warning_spin.value()
        new_settings.progress_delay_threshold = self.progress_delay_spin.value()
        new_settings.insufficient_progress_days = self.insufficient_days_spin.value()
        new_settings.insufficient_progress_threshold = self.insufficient_threshold_spin.value()
        new_settings.check_interval_hours = self.check_interval_spin.value()
        new_settings.retention_days = self.retention_spin.value()
        
        for notification_type, checkbox in self.type_checkboxes.items():
            new_settings.enabled_types[notification_type] = checkbox.isChecked()
        
        return new_settings


class NotificationTab(QWidget):
    """通知管理タブ"""
    
    # シグナル定義
    notification_selected = pyqtSignal(str)  # notification_id
    
    def __init__(self, parent, project_management_system):
        """
        通知タブの初期化
        
        Args:
            parent: 親ウィンドウ
            project_management_system: プロジェクト管理システム
        """
        super().__init__(parent)
        self.parent_window = parent
        self.pms = project_management_system
        
        # 通知管理システム取得
        self.notification_manager = getattr(self.pms, 'notification_manager', None)
        
        # フィルタ設定
        self.filter_settings = {
            'type': '',
            'priority': '',
            'status': '',
            'keyword': '',
            'date_from': None,
            'date_to': None
        }
        
        # UI要素
        self.notification_table = None
        self.detail_panel = None
        self.stats_panel = None
        
        self._setup_ui()
        self._connect_signals()
        self._load_initial_data()
        
        # 自動更新タイマー
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_notifications)
        self.refresh_timer.start(30000)  # 30秒間隔
    
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
        
        # 一括操作ボタン群
        bulk_group = QGroupBox("一括操作")
        bulk_layout = QHBoxLayout(bulk_group)
        
        self.mark_read_btn = QPushButton("選択を既読")
        self.mark_read_btn.setToolTip("選択した通知を既読にマーク")
        self.mark_read_btn.clicked.connect(self._mark_selected_as_read)
        self.mark_read_btn.setEnabled(False)
        bulk_layout.addWidget(self.mark_read_btn)
        
        self.acknowledge_btn = QPushButton("選択を確認済み")
        self.acknowledge_btn.setToolTip("選択した通知を確認済みにマーク")
        self.acknowledge_btn.clicked.connect(self._acknowledge_selected)
        self.acknowledge_btn.setEnabled(False)
        bulk_layout.addWidget(self.acknowledge_btn)
        
        self.dismiss_btn = QPushButton("選択を却下")
        self.dismiss_btn.setToolTip("選択した通知を却下")
        self.dismiss_btn.clicked.connect(self._dismiss_selected)
        self.dismiss_btn.setEnabled(False)
        bulk_layout.addWidget(self.dismiss_btn)
        
        self.delete_btn = QPushButton("選択を削除")
        self.delete_btn.setToolTip("選択した通知を削除")
        self.delete_btn.clicked.connect(self._delete_selected)
        self.delete_btn.setEnabled(False)
        bulk_layout.addWidget(self.delete_btn)
        
        toolbar_layout.addWidget(bulk_group)
        
        # 全体操作ボタン群
        all_group = QGroupBox("全体操作")
        all_layout = QHBoxLayout(all_group)
        
        self.mark_all_read_btn = QPushButton("全て既読")
        self.mark_all_read_btn.setToolTip("全ての通知を既読にマーク")
        self.mark_all_read_btn.clicked.connect(self._mark_all_as_read)
        all_layout.addWidget(self.mark_all_read_btn)
        
        self.cleanup_btn = QPushButton("古い通知削除")
        self.cleanup_btn.setToolTip("古い通知を削除")
        self.cleanup_btn.clicked.connect(self._cleanup_old_notifications)
        all_layout.addWidget(self.cleanup_btn)
        
        self.generate_btn = QPushButton("通知チェック")
        self.generate_btn.setToolTip("通知を手動でチェック・生成")
        self.generate_btn.clicked.connect(self._generate_notifications)
        all_layout.addWidget(self.generate_btn)
        
        toolbar_layout.addWidget(all_group)
        
        # 設定・表示ボタン群
        view_group = QGroupBox("設定・表示")
        view_layout = QHBoxLayout(view_group)
        
        self.settings_btn = QPushButton("設定")
        self.settings_btn.setToolTip("通知設定を変更")
        self.settings_btn.clicked.connect(self._show_settings)
        view_layout.addWidget(self.settings_btn)
        
        self.refresh_btn = QPushButton("更新")
        self.refresh_btn.setToolTip("通知一覧を更新")
        self.refresh_btn.clicked.connect(self.refresh_notifications)
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
        self.keyword_edit.setPlaceholderText("通知メッセージで検索")
        self.keyword_edit.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.keyword_edit)
        
        # 通知種別フィルタ
        filter_layout.addWidget(QLabel("種別:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "全て", "期限接近", "期限超過", "進捗遅延", "進捗不足"
        ])
        self.type_combo.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.type_combo)
        
        # 優先度フィルタ
        filter_layout.addWidget(QLabel("優先度:"))
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["全て", "高", "中", "低"])
        self.priority_combo.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.priority_combo)
        
        # ステータスフィルタ
        filter_layout.addWidget(QLabel("ステータス:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["全て", "未読", "既読", "確認済み", "却下", "アクティブ"])
        self.status_combo.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.status_combo)
        
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
        
        # 通知テーブル
        self._create_notification_table(splitter)
        
        # 右側パネル
        self._create_right_panel(splitter)
        
        # 分割比率設定
        splitter.setSizes([700, 400])
        
        parent_layout.addWidget(splitter)
    
    def _create_notification_table(self, parent):
        """通知テーブルを作成"""
        self.notification_table = QTableWidget()
        self.notification_table.setColumnCount(7)
        self.notification_table.setHorizontalHeaderLabels([
            "種別", "優先度", "対象", "メッセージ", "作成日時", "状態", "経過時間"
        ])
        
        # 列幅設定
        header = self.notification_table.horizontalHeader()
        header.resizeSection(0, 80)   # 種別
        header.resizeSection(1, 60)   # 優先度
        header.resizeSection(2, 150)  # 対象
        header.resizeSection(3, 300)  # メッセージ
        header.resizeSection(4, 140)  # 作成日時
        header.resizeSection(5, 80)   # 状態
        header.resizeSection(6, 100)  # 経過時間
        
        # テーブル設定
        self.notification_table.setAlternatingRowColors(True)
        self.notification_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.notification_table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.notification_table.setSortingEnabled(True)
        
        # 垂直ヘッダー非表示
        self.notification_table.verticalHeader().setVisible(False)
        
        parent.addWidget(self.notification_table)
    
    def _create_right_panel(self, parent):
        """右側パネルを作成"""
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 詳細情報パネル
        self.detail_panel = QGroupBox("通知詳細")
        detail_layout = QVBoxLayout(self.detail_panel)
        
        self.detail_text = QTextEdit()
        self.detail_text.setMaximumHeight(200)
        self.detail_text.setReadOnly(True)
        detail_layout.addWidget(self.detail_text)
        
        right_layout.addWidget(self.detail_panel)
        
        # 統計パネル
        self.stats_panel = QGroupBox("通知統計")
        stats_layout = QVBoxLayout(self.stats_panel)
        
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(200)
        self.stats_text.setReadOnly(True)
        stats_layout.addWidget(self.stats_text)
        
        right_layout.addWidget(self.stats_panel)
        
        right_layout.addStretch()
        
        parent.addWidget(right_panel)
    
    def _create_status_panel(self, parent_layout):
        """ステータスパネルを作成"""
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        
        # 通知統計
        self.total_count_label = QLabel("総数: 0")
        status_layout.addWidget(self.total_count_label)
        
        self.unread_count_label = QLabel("未読: 0")
        status_layout.addWidget(self.unread_count_label)
        
        self.active_count_label = QLabel("アクティブ: 0")
        status_layout.addWidget(self.active_count_label)
        
        self.high_priority_label = QLabel("高優先度: 0")
        status_layout.addWidget(self.high_priority_label)
        
        status_layout.addStretch()
        
        # 最終更新時刻
        self.last_update_label = QLabel("")
        status_layout.addWidget(self.last_update_label)
        
        parent_layout.addWidget(status_frame)
    
    def _connect_signals(self):
        """シグナル接続"""
        # テーブル選択変更
        self.notification_table.itemSelectionChanged.connect(self._on_selection_changed)
        
        # ダブルクリック
        self.notification_table.itemDoubleClicked.connect(self._on_item_double_clicked)
    
    def _load_initial_data(self):
        """初期データを読み込み"""
        self.refresh_notifications()
    
    def refresh_notifications(self):
        """通知データを更新"""
        try:
            if not self.notification_manager:
                self._show_no_notification_manager()
                return
            
            self._populate_notification_table()
            self._update_status_panel()
            self._update_statistics_panel()
            
            # 最終更新時刻
            self.last_update_label.setText(f"更新: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            QMessageBox.warning(
                self, "通知更新エラー",
                f"通知データの更新中にエラーが発生しました：\n{str(e)}"
            )
    
    def _show_no_notification_manager(self):
        """通知管理システムが無い場合の表示"""
        self.notification_table.setRowCount(1)
        self.notification_table.setColumnCount(1)
        self.notification_table.setHorizontalHeaderLabels(["通知システム"])
        
        item = QTableWidgetItem("通知管理システムが利用できません")
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notification_table.setItem(0, 0, item)
        
        self.detail_text.setText("通知管理システムが初期化されていません。")
        self.stats_text.setText("統計情報は利用できません。")
    
    def _populate_notification_table(self):
        """通知テーブルにデータを投入"""
        if not self.notification_manager:
            return
        
        notifications = self.notification_manager.get_all_notifications()
        filtered_notifications = [n for n in notifications if self._should_show_notification(n)]
        
        self.notification_table.setRowCount(len(filtered_notifications))
        
        for row, notification in enumerate(filtered_notifications):
            # 種別
            type_item = QTableWidgetItem(notification.type)
            self.notification_table.setItem(row, 0, type_item)
            
            # 優先度
            priority_item = QTableWidgetItem(notification.priority)
            if notification.priority == "高":
                priority_item.setForeground(QBrush(QColor("red")))
            elif notification.priority == "中":
                priority_item.setForeground(QBrush(QColor("orange")))
            self.notification_table.setItem(row, 1, priority_item)
            
            # 対象
            target_text = f"{notification.entity_type}: {notification.entity_name}"
            target_item = QTableWidgetItem(target_text)
            self.notification_table.setItem(row, 2, target_item)
            
            # メッセージ
            message_item = QTableWidgetItem(notification.message)
            self.notification_table.setItem(row, 3, message_item)
            
            # 作成日時
            created_item = QTableWidgetItem(notification.created_at.strftime("%Y/%m/%d %H:%M"))
            self.notification_table.setItem(row, 4, created_item)
            
            # 状態
            status = self._get_notification_status_text(notification)
            status_item = QTableWidgetItem(status)
            if notification.is_acknowledged():
                status_item.setForeground(QBrush(QColor("green")))
            elif notification.is_dismissed():
                status_item.setForeground(QBrush(QColor("gray")))
            elif not notification.is_read():
                status_item.setForeground(QBrush(QColor("red")))
                font = QFont()
                font.setBold(True)
                status_item.setFont(font)
            self.notification_table.setItem(row, 5, status_item)
            
            # 経過時間
            age_text = self._format_age(notification.get_age_hours())
            age_item = QTableWidgetItem(age_text)
            self.notification_table.setItem(row, 6, age_item)
            
            # メタデータ
            type_item.setData(Qt.ItemDataRole.UserRole, notification.id)
    
    def _get_notification_status_text(self, notification) -> str:
        """通知のステータステキストを取得"""
        if notification.is_acknowledged():
            return "確認済み"
        elif notification.is_dismissed():
            return "却下"
        elif notification.is_read():
            return "既読"
        else:
            return "未読"
    
    def _format_age(self, hours: float) -> str:
        """経過時間を人間に読みやすい形式でフォーマット"""
        if hours < 1:
            minutes = int(hours * 60)
            return f"{minutes}分前"
        elif hours < 24:
            return f"{int(hours)}時間前"
        else:
            days = int(hours / 24)
            return f"{days}日前"
    
    def _should_show_notification(self, notification) -> bool:
        """通知を表示すべきか判定"""
        # キーワードフィルタ
        keyword = self.filter_settings['keyword'].lower()
        if keyword and keyword not in notification.message.lower():
            return False
        
        # 種別フィルタ
        type_filter = self.filter_settings['type']
        if type_filter and type_filter != notification.type:
            return False
        
        # 優先度フィルタ
        priority_filter = self.filter_settings['priority']
        if priority_filter and priority_filter != notification.priority:
            return False
        
        # ステータスフィルタ
        status_filter = self.filter_settings['status']
        if status_filter:
            if status_filter == "未読" and notification.is_read():
                return False
            elif status_filter == "既読" and not notification.is_read():
                return False
            elif status_filter == "確認済み" and not notification.is_acknowledged():
                return False
            elif status_filter == "却下" and not notification.is_dismissed():
                return False
            elif status_filter == "アクティブ" and not notification.is_active():
                return False
        
        return True
    
    def _apply_filters(self):
        """フィルタを適用"""
        # フィルタ設定更新
        self.filter_settings.update({
            'keyword': self.keyword_edit.text(),
            'type': self.type_combo.currentText() if self.type_combo.currentText() != "全て" else "",
            'priority': self.priority_combo.currentText() if self.priority_combo.currentText() != "全て" else "",
            'status': self.status_combo.currentText() if self.status_combo.currentText() != "全て" else ""
        })
        
        # テーブル再構築
        self._populate_notification_table()
    
    def _clear_filters(self):
        """フィルタをクリア"""
        self.keyword_edit.clear()
        self.type_combo.setCurrentText("全て")
        self.priority_combo.setCurrentText("全て")
        self.status_combo.setCurrentText("全て")
        
        self._apply_filters()
    
    def _update_status_panel(self):
        """ステータスパネルを更新"""
        if not self.notification_manager:
            self.total_count_label.setText("総数: N/A")
            self.unread_count_label.setText("未読: N/A")
            self.active_count_label.setText("アクティブ: N/A")
            self.high_priority_label.setText("高優先度: N/A")
            return
        
        try:
            stats = self.notification_manager.get_notification_statistics()
            
            self.total_count_label.setText(f"総数: {stats['total']}")
            
            status_counts = stats.get('status_counts', {})
            unread_count = status_counts.get('unread', 0)
            active_count = status_counts.get('active', 0)
            
            self.unread_count_label.setText(f"未読: {unread_count}")
            self.active_count_label.setText(f"アクティブ: {active_count}")
            
            # 未読が多い場合は赤色表示
            if unread_count > 10:
                self.unread_count_label.setStyleSheet("color: red; font-weight: bold;")
            elif unread_count > 0:
                self.unread_count_label.setStyleSheet("color: orange; font-weight: bold;")
            else:
                self.unread_count_label.setStyleSheet("color: green;")
            
            priority_counts = stats.get('priority_counts', {})
            high_priority_count = priority_counts.get('高', 0)
            self.high_priority_label.setText(f"高優先度: {high_priority_count}")
            
            if high_priority_count > 0:
                self.high_priority_label.setStyleSheet("color: red; font-weight: bold;")
            else:
                self.high_priority_label.setStyleSheet("color: green;")
            
        except Exception:
            self.total_count_label.setText("総数: エラー")
            self.unread_count_label.setText("未読: エラー")
            self.active_count_label.setText("アクティブ: エラー")
            self.high_priority_label.setText("高優先度: エラー")
    
    def _update_statistics_panel(self):
        """統計パネルを更新"""
        if not self.notification_manager:
            self.stats_text.setText("通知管理システムが利用できません。")
            return
        
        try:
            stats = self.notification_manager.get_notification_statistics()
            
            stats_text = f"""
通知統計情報:

総通知数: {stats['total']}

種別別統計:
"""
            
            type_counts = stats.get('type_counts', {})
            for notification_type, count in type_counts.items():
                stats_text += f"- {notification_type}: {count}件\n"
            
            stats_text += "\n優先度別統計:\n"
            priority_counts = stats.get('priority_counts', {})
            for priority, count in priority_counts.items():
                stats_text += f"- {priority}優先度: {count}件\n"
            
            stats_text += "\nステータス別統計:\n"
            status_counts = stats.get('status_counts', {})
            for status, count in status_counts.items():
                status_name = {
                    'unread': '未読',
                    'read': '既読',
                    'acknowledged': '確認済み',
                    'dismissed': '却下',
                    'active': 'アクティブ'
                }.get(status, status)
                stats_text += f"- {status_name}: {count}件\n"
            
            self.stats_text.setText(stats_text.strip())
            
        except Exception as e:
            self.stats_text.setText(f"統計情報の取得に失敗しました：\n{str(e)}")
    
    @pyqtSlot()
    def _on_selection_changed(self):
        """選択変更時の処理"""
        selected_rows = set(item.row() for item in self.notification_table.selectedItems())
        has_selection = len(selected_rows) > 0
        
        # ボタン状態更新
        self.mark_read_btn.setEnabled(has_selection)
        self.acknowledge_btn.setEnabled(has_selection)
        self.dismiss_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        
        # 詳細パネル更新
        self._update_detail_panel()
    
    def _update_detail_panel(self):
        """詳細パネルを更新"""
        selected_rows = set(item.row() for item in self.notification_table.selectedItems())
        
        if not selected_rows or not self.notification_manager:
            self.detail_text.clear()
            return
        
        if len(selected_rows) == 1:
            # 単一選択の場合
            row = list(selected_rows)[0]
            type_item = self.notification_table.item(row, 0)
            if type_item:
                notification_id = type_item.data(Qt.ItemDataRole.UserRole)
                notification = self.notification_manager.get_notification(notification_id)
                if notification:
                    self._show_notification_details(notification)
        else:
            # 複数選択の場合
            self.detail_text.setText(f"{len(selected_rows)}件の通知が選択されています。")
    
    def _show_notification_details(self, notification):
        """通知詳細を表示"""
        details = f"""
通知ID: {notification.id}

種別: {notification.type}
優先度: {notification.priority}

対象エンティティ:
- 種別: {notification.entity_type}
- 名前: {notification.entity_name}
- ID: {notification.entity_id}

メッセージ:
{notification.message}

作成日時: {notification.created_at.strftime('%Y/%m/%d %H:%M:%S')}
経過時間: {self._format_age(notification.get_age_hours())}

ステータス:
- 既読: {'はい' if notification.is_read() else 'いいえ'}
- 確認済み: {'はい' if notification.is_acknowledged() else 'いいえ'}
- 却下: {'はい' if notification.is_dismissed() else 'いいえ'}
- アクティブ: {'はい' if notification.is_active() else 'いいえ'}

既読日時: {notification.read_at.strftime('%Y/%m/%d %H:%M:%S') if notification.read_at else '未読'}
確認日時: {notification.acknowledged_at.strftime('%Y/%m/%d %H:%M:%S') if notification.acknowledged_at else '未確認'}
却下日時: {notification.dismissed_at.strftime('%Y/%m/%d %H:%M:%S') if notification.dismissed_at else '未却下'}

メタデータ:
{str(notification.metadata) if notification.metadata else '（なし）'}
        """.strip()
        
        self.detail_text.setText(details)
    
    @pyqtSlot(QTableWidgetItem)
    def _on_item_double_clicked(self, item):
        """アイテムダブルクリック処理"""
        if not self.notification_manager:
            return
        
        notification_id = item.data(Qt.ItemDataRole.UserRole)
        if notification_id:
            notification = self.notification_manager.get_notification(notification_id)
            if notification:
                # 既読にマーク
                self.notification_manager.mark_as_read(notification_id)
                
                # 対象エンティティへのナビゲーション
                self.notification_selected.emit(notification_id)
                
                # 表示更新
                self.refresh_notifications()
    
    def _get_selected_notification_ids(self) -> List[str]:
        """選択された通知IDのリストを取得"""
        selected_rows = set(item.row() for item in self.notification_table.selectedItems())
        notification_ids = []
        
        for row in selected_rows:
            type_item = self.notification_table.item(row, 0)
            if type_item:
                notification_id = type_item.data(Qt.ItemDataRole.UserRole)
                if notification_id:
                    notification_ids.append(notification_id)
        
        return notification_ids
    
    def _mark_selected_as_read(self):
        """選択した通知を既読にマーク"""
        if not self.notification_manager:
            return
        
        notification_ids = self._get_selected_notification_ids()
        if not notification_ids:
            return
        
        count = 0
        for notification_id in notification_ids:
            if self.notification_manager.mark_as_read(notification_id):
                count += 1
        
        QMessageBox.information(self, "既読完了", f"{count}件の通知を既読にマークしました。")
        self.refresh_notifications()
    
    def _acknowledge_selected(self):
        """選択した通知を確認済みにマーク"""
        if not self.notification_manager:
            return
        
        notification_ids = self._get_selected_notification_ids()
        if not notification_ids:
            return
        
        count = 0
        for notification_id in notification_ids:
            if self.notification_manager.acknowledge(notification_id):
                count += 1
        
        QMessageBox.information(self, "確認完了", f"{count}件の通知を確認済みにマークしました。")
        self.refresh_notifications()
    
    def _dismiss_selected(self):
        """選択した通知を却下"""
        if not self.notification_manager:
            return
        
        notification_ids = self._get_selected_notification_ids()
        if not notification_ids:
            return
        
        reply = QMessageBox.question(
            self, "却下確認",
            f"{len(notification_ids)}件の通知を却下しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        count = 0
        for notification_id in notification_ids:
            if self.notification_manager.dismiss(notification_id):
                count += 1
        
        QMessageBox.information(self, "却下完了", f"{count}件の通知を却下しました。")
        self.refresh_notifications()
    
    def _delete_selected(self):
        """選択した通知を削除"""
        if not self.notification_manager:
            return
        
        notification_ids = self._get_selected_notification_ids()
        if not notification_ids:
            return
        
        reply = QMessageBox.question(
            self, "削除確認",
            f"{len(notification_ids)}件の通知を削除しますか？\n"
            "この操作は元に戻すことができません。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        count = 0
        for notification_id in notification_ids:
            if self.notification_manager.delete_notification(notification_id):
                count += 1
        
        QMessageBox.information(self, "削除完了", f"{count}件の通知を削除しました。")
        self.refresh_notifications()
    
    def _mark_all_as_read(self):
        """全ての通知を既読にマーク"""
        if not self.notification_manager:
            return
        
        reply = QMessageBox.question(
            self, "全件既読確認",
            "全ての通知を既読にマークしますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        count = self.notification_manager.mark_all_as_read()
        QMessageBox.information(self, "既読完了", f"{count}件の通知を既読にマークしました。")
        self.refresh_notifications()
    
    def _cleanup_old_notifications(self):
        """古い通知を削除"""
        if not self.notification_manager:
            return
        
        reply = QMessageBox.question(
            self, "古い通知削除確認",
            "古い通知を削除しますか？\n"
            "保持期間を過ぎた通知が削除されます。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        count = self.notification_manager.cleanup_old_notifications()
        QMessageBox.information(self, "削除完了", f"{count}件の古い通知を削除しました。")
        self.refresh_notifications()
    
    def _generate_notifications(self):
        """通知を手動生成"""
        if not hasattr(self.pms, 'notification_service'):
            QMessageBox.warning(self, "機能エラー", "通知生成機能が利用できません。")
            return
        
        try:
            # プログレスバー表示
            progress = QProgressBar()
            progress.setRange(0, 0)  # 不定プログレス
            self.parent_window.statusBar().addWidget(progress)
            
            # 通知生成実行
            generated_count = 0
            try:
                # 通知サービスから手動チェック実行
                self.pms.notification_service.check_and_generate_notifications()
                generated_count = len(self.notification_manager.get_unread_notifications())
            except Exception as e:
                QMessageBox.warning(
                    self, "通知生成エラー",
                    f"通知の生成中にエラーが発生しました：\n{str(e)}"
                )
            finally:
                self.parent_window.statusBar().removeWidget(progress)
            
            self.refresh_notifications()
            QMessageBox.information(
                self, "通知生成完了",
                f"通知チェックが完了しました。\n未読通知: {generated_count}件"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, "通知生成エラー",
                f"通知生成中にエラーが発生しました：\n{str(e)}"
            )
    
    def _show_settings(self):
        """通知設定を表示"""
        if not self.notification_manager:
            QMessageBox.warning(self, "機能エラー", "通知設定機能が利用できません。")
            return
        
        try:
            # 現在の設定を取得
            current_settings = getattr(self.notification_manager, 'settings', None)
            if not current_settings:
                from models.notification import NotificationSettings
                current_settings = NotificationSettings()
            
            # 設定ダイアログ表示
            dialog = NotificationSettingsDialog(self, current_settings)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_settings = dialog.get_settings()
                
                # 設定を適用
                if hasattr(self.pms, 'notification_service'):
                    self.pms.notification_service.update_settings(**vars(new_settings))
                
                QMessageBox.information(self, "設定完了", "通知設定を更新しました。")
                
        except Exception as e:
            QMessageBox.critical(
                self, "設定エラー",
                f"設定の更新中にエラーが発生しました：\n{str(e)}"
            )