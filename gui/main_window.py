"""
PyQt6メインウィンドウ
プロジェクト管理システムの統合UI
"""

import sys
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout, QHBoxLayout, QWidget,
    QMenuBar, QToolBar, QStatusBar, QMessageBox, QApplication,
    QLabel, QPushButton, QProgressBar, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QAction, QIcon, QKeySequence
from typing import Optional

from .project_tab import ProjectTab
from .gantt_chart import GanttChart
from .notification_tab import NotificationTab
from .dialogs import DialogManager


class MainWindow(QMainWindow):
    """プロジェクト管理システム メインウィンドウ"""
    
    # シグナル定義
    data_updated = pyqtSignal()
    notification_received = pyqtSignal(str)  # 通知ID
    
    def __init__(self, project_management_system):
        """
        メインウィンドウの初期化
        
        Args:
            project_management_system: プロジェクト管理システムインスタンス
        """
        super().__init__()
        self.pms = project_management_system
        self.dialog_manager = DialogManager(self, project_management_system)
        
        # UI状態
        self.current_project_id = None
        self.auto_refresh_enabled = True
        self.refresh_interval = 30  # 秒
        
        # タイマー
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._auto_refresh_data)
        self.refresh_timer.start(self.refresh_interval * 1000)
        
        # ステータス更新タイマー
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status_bar)
        self.status_timer.start(5000)  # 5秒間隔
        
        self._setup_ui()
        self._connect_signals()
        self._load_initial_data()
        
        # ウィンドウ設定
        self.setWindowTitle("プロジェクト管理システム v1.0.0")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # 中央に配置
        self._center_window()
    
    def _setup_ui(self):
        """UI要素を設定"""
        # メニューバー
        self._create_menu_bar()
        
        # ツールバー
        self._create_tool_bar()
        
        # 中央ウィジェット
        self._create_central_widget()
        
        # ステータスバー
        self._create_status_bar()
    
    def _create_menu_bar(self):
        """メニューバーを作成"""
        menubar = self.menuBar()
        
        # ファイルメニュー
        file_menu = menubar.addMenu('ファイル(&F)')
        
        new_project_action = QAction('新規プロジェクト(&N)', self)
        new_project_action.setShortcut(QKeySequence.StandardKey.New)
        new_project_action.setStatusTip('新しいプロジェクトを作成')
        new_project_action.triggered.connect(self._create_new_project)
        file_menu.addAction(new_project_action)
        
        file_menu.addSeparator()
        
        refresh_action = QAction('データ更新(&R)', self)
        refresh_action.setShortcut(QKeySequence.StandardKey.Refresh)
        refresh_action.setStatusTip('データを最新状態に更新')
        refresh_action.triggered.connect(self._refresh_all_data)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('終了(&X)', self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.setStatusTip('アプリケーションを終了')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 編集メニュー
        edit_menu = menubar.addMenu('編集(&E)')
        
        settings_action = QAction('設定(&S)', self)
        settings_action.setStatusTip('システム設定を変更')
        settings_action.triggered.connect(self._show_settings)
        edit_menu.addAction(settings_action)
        
        # 表示メニュー
        view_menu = menubar.addMenu('表示(&V)')
        
        self.auto_refresh_action = QAction('自動更新(&A)', self)
        self.auto_refresh_action.setCheckable(True)
        self.auto_refresh_action.setChecked(self.auto_refresh_enabled)
        self.auto_refresh_action.setStatusTip('データの自動更新を有効/無効')
        self.auto_refresh_action.triggered.connect(self._toggle_auto_refresh)
        view_menu.addAction(self.auto_refresh_action)
        
        # ヘルプメニュー
        help_menu = menubar.addMenu('ヘルプ(&H)')
        
        about_action = QAction('バージョン情報(&A)', self)
        about_action.setStatusTip('バージョン情報を表示')
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_tool_bar(self):
        """ツールバーを作成"""
        toolbar = self.addToolBar('メイン')
        toolbar.setMovable(False)
        
        # 新規作成ボタン
        new_project_btn = toolbar.addAction('新規プロジェクト')
        new_project_btn.setStatusTip('新しいプロジェクトを作成')
        new_project_btn.triggered.connect(self._create_new_project)
        
        toolbar.addSeparator()
        
        # 更新ボタン
        refresh_btn = toolbar.addAction('更新')
        refresh_btn.setStatusTip('データを最新状態に更新')
        refresh_btn.triggered.connect(self._refresh_all_data)
        
        toolbar.addSeparator()
        
        # 自動更新状態表示
        self.auto_refresh_label = QLabel('自動更新: ON')
        toolbar.addWidget(self.auto_refresh_label)
        
        # 右側にスペーサー
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy(), spacer.sizePolicy().verticalPolicy())
        toolbar.addWidget(spacer)
        
        # システム状態表示
        self.system_status_label = QLabel('システム: 正常')
        self.system_status_label.setStyleSheet("color: green; font-weight: bold;")
        toolbar.addWidget(self.system_status_label)
    
    def _create_central_widget(self):
        """中央ウィジェットを作成"""
        # タブウィジェット作成
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.setMovable(True)
        
        # プロジェクトタブ
        self.project_tab = ProjectTab(self, self.pms, self.dialog_manager)
        self.tab_widget.addTab(self.project_tab, "プロジェクト管理")
        
        # ガントチャートタブ
        self.gantt_tab = GanttChart(self, self.pms)
        self.tab_widget.addTab(self.gantt_tab, "ガントチャート")
        
        # 通知タブ
        self.notification_tab = NotificationTab(self, self.pms)
        self.tab_widget.addTab(self.notification_tab, "通知管理")
        
        self.setCentralWidget(self.tab_widget)
    
    def _create_status_bar(self):
        """ステータスバーを作成"""
        status_bar = self.statusBar()
        
        # メインメッセージエリア
        self.main_status_label = QLabel("システム準備完了")
        status_bar.addWidget(self.main_status_label)
        
        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        status_bar.addPermanentWidget(self.progress_bar)
        
        # 統計情報
        self.stats_label = QLabel("")
        status_bar.addPermanentWidget(self.stats_label)
        
        # 通知カウント
        self.notification_count_label = QLabel("通知: 0")
        status_bar.addPermanentWidget(self.notification_count_label)
        
        # 最終更新時刻
        self.last_updated_label = QLabel("")
        status_bar.addPermanentWidget(self.last_updated_label)
    
    def _center_window(self):
        """ウィンドウを画面中央に配置"""
        screen_geometry = QApplication.primaryScreen().geometry()
        window_geometry = self.geometry()
        
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())
    
    def _connect_signals(self):
        """シグナル接続"""
        # タブ間のデータ連携
        self.project_tab.project_selected.connect(self.gantt_tab.set_current_project)
        self.project_tab.data_changed.connect(self.gantt_tab.refresh_chart)
        self.project_tab.data_changed.connect(self.notification_tab.refresh_notifications)
        
        # ダイアログとの連携
        self.dialog_manager.project_saved.connect(self._on_project_saved)
        self.dialog_manager.project_updated.connect(self._on_project_updated)
        
        # 通知との連携
        self.notification_tab.notification_selected.connect(self._on_notification_selected)
        
        # データ更新シグナル
        self.data_updated.connect(self.project_tab.refresh_data)
        self.data_updated.connect(self.gantt_tab.refresh_chart)
        self.data_updated.connect(self.notification_tab.refresh_notifications)
        
        # タブ変更時の処理
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
    
    def _load_initial_data(self):
        """初期データを読み込み"""
        try:
            self._refresh_all_data()
            self.main_status_label.setText("初期データ読み込み完了")
            
        except Exception as e:
            QMessageBox.critical(
                self, "初期化エラー",
                f"初期データの読み込みに失敗しました：\n{str(e)}"
            )
            self.main_status_label.setText("初期化エラー")
    
    def _create_new_project(self):
        """新規プロジェクトを作成"""
        try:
            result = self.dialog_manager.show_project_dialog(None, 'create')
            if result:
                self._refresh_all_data()
                self.main_status_label.setText("新規プロジェクトを作成しました")
                
        except Exception as e:
            QMessageBox.critical(
                self, "作成エラー",
                f"プロジェクトの作成に失敗しました：\n{str(e)}"
            )
    
    def _refresh_all_data(self):
        """全データを更新"""
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # データ更新シグナル発行
            self.data_updated.emit()
            
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
            
            # ステータス更新
            from datetime import datetime
            self.last_updated_label.setText(f"更新: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            self.progress_bar.setVisible(False)
            QMessageBox.warning(
                self, "更新エラー",
                f"データの更新中にエラーが発生しました：\n{str(e)}"
            )
    
    def _auto_refresh_data(self):
        """自動データ更新"""
        if self.auto_refresh_enabled:
            self._refresh_all_data()
    
    def _toggle_auto_refresh(self, checked):
        """自動更新の有効/無効切り替え"""
        self.auto_refresh_enabled = checked
        
        if self.auto_refresh_enabled:
            self.refresh_timer.start(self.refresh_interval * 1000)
            self.auto_refresh_label.setText('自動更新: ON')
            self.auto_refresh_label.setStyleSheet("color: green;")
        else:
            self.refresh_timer.stop()
            self.auto_refresh_label.setText('自動更新: OFF')
            self.auto_refresh_label.setStyleSheet("color: red;")
    
    def _update_status_bar(self):
        """ステータスバーを更新"""
        try:
            # システム統計取得
            stats = self.pms.get_system_statistics()
            
            # 統計表示
            stats_text = (
                f"プロジェクト: {stats['projects']['total']} "
                f"タスク: {stats['tasks']['total']} "
                f"完了率: {stats['projects'].get('completion_rate', 0):.1f}%"
            )
            self.stats_label.setText(stats_text)
            
            # 通知カウント更新
            if hasattr(self.pms, 'notification_manager'):
                unread_count = len(self.pms.notification_manager.get_unread_notifications())
                self.notification_count_label.setText(f"通知: {unread_count}")
                
                if unread_count > 0:
                    self.notification_count_label.setStyleSheet("color: red; font-weight: bold;")
                else:
                    self.notification_count_label.setStyleSheet("color: green;")
            
            # システム状態チェック
            if self.pms.validate_data_integrity():
                self.system_status_label.setText('システム: 正常')
                self.system_status_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.system_status_label.setText('システム: 警告')
                self.system_status_label.setStyleSheet("color: orange; font-weight: bold;")
            
        except Exception as e:
            self.system_status_label.setText('システム: エラー')
            self.system_status_label.setStyleSheet("color: red; font-weight: bold;")
    
    def _show_settings(self):
        """設定画面を表示"""
        QMessageBox.information(
            self, "設定",
            "設定画面は将来のバージョンで実装予定です。"
        )
    
    def _show_about(self):
        """バージョン情報を表示"""
        QMessageBox.about(
            self, "バージョン情報",
            """
プロジェクト管理システム v1.0.0

エンタープライズレベルのプロジェクト管理ソフトウェア

主要機能:
• 4階層プロジェクト管理
• 自動進捗計算
• リアルタイム通知
• 高度ガントチャート
• Excel連携機能

© 2025 プロジェクト管理システム開発チーム
            """
        )
    
    @pyqtSlot(str)
    def _on_project_saved(self, project_id):
        """プロジェクト保存時の処理"""
        self._refresh_all_data()
        self.main_status_label.setText("プロジェクトを保存しました")
    
    @pyqtSlot(str)
    def _on_project_updated(self, project_id):
        """プロジェクト更新時の処理"""
        self._refresh_all_data()
        self.main_status_label.setText("プロジェクトを更新しました")
    
    @pyqtSlot(str)
    def _on_notification_selected(self, notification_id):
        """通知選択時の処理"""
        try:
            if hasattr(self.pms, 'notification_manager'):
                notification = self.pms.notification_manager.get_notification(notification_id)
                if notification:
                    # 対象エンティティに移動
                    if notification.entity_type == "Project":
                        self.tab_widget.setCurrentIndex(0)  # プロジェクトタブ
                        self.project_tab.select_project_by_id(notification.entity_id)
                    
                    self.main_status_label.setText(f"通知を選択: {notification.message}")
                    
        except Exception as e:
            QMessageBox.warning(
                self, "通知エラー",
                f"通知の処理中にエラーが発生しました：\n{str(e)}"
            )
    
    @pyqtSlot(int)
    def _on_tab_changed(self, index):
        """タブ変更時の処理"""
        tab_names = ["プロジェクト管理", "ガントチャート", "通知管理"]
        if 0 <= index < len(tab_names):
            self.main_status_label.setText(f"{tab_names[index]}タブを表示中")
    
    def set_current_project(self, project_id):
        """現在のプロジェクトを設定"""
        self.current_project_id = project_id
        
        # 全タブに通知
        self.project_tab.select_project_by_id(project_id)
        self.gantt_tab.set_current_project(project_id)
    
    def closeEvent(self, event):
        """アプリケーション終了時の処理"""
        try:
            # タイマー停止
            self.refresh_timer.stop()
            self.status_timer.stop()
            
            # データ保存確認
            reply = QMessageBox.question(
                self, "終了確認",
                "プロジェクト管理システムを終了しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 最終保存
                try:
                    # システム終了処理があれば実行
                    pass
                except:
                    pass
                
                event.accept()
            else:
                event.ignore()
                
        except Exception as e:
            # エラーがあっても終了を継続
            event.accept()


def main():
    """スタンドアロンテスト用メイン関数"""
    app = QApplication(sys.argv)
    
    try:
        # プロジェクト管理システムを初期化
        from core.manager import ProjectManagementSystem
        pms = ProjectManagementSystem()
        
        # メインウィンドウ作成・表示
        window = MainWindow(pms)
        window.show()
        
        sys.exit(app.exec())
        
    except ImportError:
        QMessageBox.critical(
            None, "モジュールエラー",
            "core.manager モジュールが見つかりません。\n"
            "main.py から起動してください。"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()