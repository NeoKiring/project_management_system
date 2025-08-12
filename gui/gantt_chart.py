"""
高度ガントチャート
プロジェクト管理システムの可視化コンポーネント
"""

import sys
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QPushButton, QComboBox, QLabel, QSlider, QSpinBox,
    QSplitter, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QMessageBox, QToolBar, QMenu, QApplication, QGraphicsView,
    QGraphicsScene, QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem,
    QGraphicsLineItem, QStyleOptionGraphicsItem, QGraphicsProxyWidget
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QRect, QRectF, QPointF, QSizeF,
    pyqtSlot, QPropertyAnimation, QEasingCurve
)
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QBrush, QPen, QLinearGradient,
    QFontMetrics, QPixmap, QIcon, QPalette, QAction
)


class TimeScale:
    """時間スケール定義"""
    DAY = "日"
    WEEK = "週"
    MONTH = "月"
    
    @classmethod
    def get_all(cls):
        return [cls.DAY, cls.WEEK, cls.MONTH]


class GanttBarItem(QGraphicsRectItem):
    """ガントバーアイテム"""
    
    def __init__(self, entity_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.entity_data = entity_data
        self.entity_type = entity_data.get('type', 'Task')
        self.entity_name = entity_data.get('name', '')
        self.start_date = entity_data.get('start_date')
        self.end_date = entity_data.get('end_date')
        self.progress = entity_data.get('progress', 0.0)
        self.is_overdue = entity_data.get('is_overdue', False)
        
        # バーの設定
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setToolTip(self._create_tooltip())
        
        # 色設定
        self._setup_colors()
    
    def _setup_colors(self):
        """色設定"""
        # エンティティタイプ別の基本色
        type_colors = {
            'Project': QColor(70, 130, 180),    # Steel Blue
            'Phase': QColor(60, 179, 113),      # Medium Sea Green
            'Process': QColor(255, 165, 0),     # Orange
            'Task': QColor(135, 206, 235)       # Sky Blue
        }
        
        base_color = type_colors.get(self.entity_type, QColor(128, 128, 128))
        
        # 期限超過の場合は赤系に
        if self.is_overdue:
            base_color = QColor(220, 20, 60)  # Crimson
        
        # グラデーション作成
        gradient = QLinearGradient(0, 0, 0, 1)
        gradient.setCoordinateMode(QLinearGradient.CoordinateMode.ObjectBoundingMode)
        gradient.setColorAt(0.0, base_color.lighter(120))
        gradient.setColorAt(1.0, base_color.darker(110))
        
        self.setBrush(QBrush(gradient))
        
        # 境界線
        pen_color = base_color.darker(140)
        self.setPen(QPen(pen_color, 1))
    
    def _create_tooltip(self) -> str:
        """ツールチップ作成"""
        tooltip = f"<b>{self.entity_type}: {self.entity_name}</b><br>"
        tooltip += f"進捗: {self.progress:.1f}%<br>"
        
        if self.start_date:
            tooltip += f"開始: {self.start_date}<br>"
        if self.end_date:
            tooltip += f"終了: {self.end_date}<br>"
        
        if self.is_overdue:
            tooltip += "<font color='red'><b>期限超過</b></font>"
        
        return tooltip
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        """カスタム描画"""
        # 基本バー描画
        super().paint(painter, option, widget)
        
        # 進捗率表示
        if self.progress > 0:
            rect = self.rect()
            progress_width = rect.width() * (self.progress / 100.0)
            
            # 進捗バー
            progress_rect = QRectF(rect.x(), rect.y(), progress_width, rect.height())
            progress_color = QColor(34, 139, 34, 180)  # Forest Green with transparency
            painter.fillRect(progress_rect, QBrush(progress_color))
            
            # 進捗率テキスト
            if rect.width() > 50:  # 十分な幅がある場合のみ
                painter.setPen(QPen(QColor(255, 255, 255), 1))
                font = QFont("Arial", 8)
                painter.setFont(font)
                text = f"{self.progress:.0f}%"
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)


class GanttTimelineHeader(QWidget):
    """ガントチャートタイムラインヘッダー"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.start_date = date.today()
        self.end_date = date.today() + timedelta(days=30)
        self.scale = TimeScale.DAY
        self.pixels_per_day = 30
        
        self.setFixedHeight(60)
        self.setStyleSheet("background-color: #f0f0f0; border-bottom: 1px solid #ccc;")
    
    def set_date_range(self, start_date: date, end_date: date):
        """日付範囲設定"""
        self.start_date = start_date
        self.end_date = end_date
        self.update()
    
    def set_scale(self, scale: str, pixels_per_day: int):
        """スケール設定"""
        self.scale = scale
        self.pixels_per_day = pixels_per_day
        self.update()
    
    def paintEvent(self, event):
        """ヘッダー描画"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        
        # 背景
        painter.fillRect(rect, QBrush(QColor(240, 240, 240)))
        
        # 現在の日付範囲
        current_date = self.start_date
        x_offset = 0
        
        font = QFont("Arial", 8)
        painter.setFont(font)
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        
        if self.scale == TimeScale.DAY:
            self._draw_day_scale(painter, rect)
        elif self.scale == TimeScale.WEEK:
            self._draw_week_scale(painter, rect)
        elif self.scale == TimeScale.MONTH:
            self._draw_month_scale(painter, rect)
        
        # 今日の線
        today_x = self._date_to_x(date.today())
        if 0 <= today_x <= rect.width():
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.drawLine(today_x, 0, today_x, rect.height())
    
    def _draw_day_scale(self, painter: QPainter, rect: QRect):
        """日スケール描画"""
        current_date = self.start_date
        
        while current_date <= self.end_date:
            x = self._date_to_x(current_date)
            if x > rect.width():
                break
            
            # 縦線
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.drawLine(x, 0, x, rect.height())
            
            # 日付テキスト
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            
            # 月/日を2段表示
            month_text = current_date.strftime("%m月")
            day_text = current_date.strftime("%d")
            
            painter.drawText(x + 2, 15, month_text)
            painter.drawText(x + 2, 35, day_text)
            
            # 週末は背景色変更
            if current_date.weekday() >= 5:  # 土日
                painter.fillRect(x, 0, self.pixels_per_day, rect.height(), 
                               QBrush(QColor(255, 240, 240, 100)))
            
            current_date += timedelta(days=1)
    
    def _draw_week_scale(self, painter: QPainter, rect: QRect):
        """週スケール描画"""
        current_date = self.start_date
        week_start = current_date - timedelta(days=current_date.weekday())
        
        while week_start <= self.end_date:
            x = self._date_to_x(week_start)
            if x > rect.width():
                break
            
            # 縦線
            painter.setPen(QPen(QColor(150, 150, 150), 1))
            painter.drawLine(x, 0, x, rect.height())
            
            # 週テキスト
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            week_text = f"{week_start.strftime('%m/%d')}週"
            painter.drawText(x + 5, 25, week_text)
            
            week_start += timedelta(weeks=1)
    
    def _draw_month_scale(self, painter: QPainter, rect: QRect):
        """月スケール描画"""
        current_date = self.start_date
        
        # 月初に調整
        month_start = current_date.replace(day=1)
        
        while month_start <= self.end_date:
            x = self._date_to_x(month_start)
            if x > rect.width():
                break
            
            # 縦線
            painter.setPen(QPen(QColor(100, 100, 100), 2))
            painter.drawLine(x, 0, x, rect.height())
            
            # 月テキスト
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            month_text = month_start.strftime("%Y年%m月")
            painter.drawText(x + 5, 30, month_text)
            
            # 次の月
            if month_start.month == 12:
                month_start = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_start = month_start.replace(month=month_start.month + 1)
    
    def _date_to_x(self, target_date: date) -> int:
        """日付をX座標に変換"""
        days_diff = (target_date - self.start_date).days
        return days_diff * self.pixels_per_day


class GanttTreeWidget(QTreeWidget):
    """ガントチャート用ツリーウィジェット"""
    
    item_selected = pyqtSignal(str, str)  # entity_id, entity_type
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_tree()
    
    def _setup_tree(self):
        """ツリー設定"""
        self.setHeaderLabels(["名前", "期間", "進捗"])
        
        # 列幅設定
        header = self.header()
        header.resizeSection(0, 200)  # 名前
        header.resizeSection(1, 120)  # 期間  
        header.resizeSection(2, 80)   # 進捗
        
        # ツリー設定
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(True)
        self.setExpandsOnDoubleClick(False)
        
        # 選択
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.itemSelectionChanged.connect(self._on_selection_changed)
    
    def _on_selection_changed(self):
        """選択変更処理"""
        selected_items = self.selectedItems()
        if selected_items:
            item = selected_items[0]
            entity_id = item.data(0, Qt.ItemDataRole.UserRole)
            entity_type = item.data(1, Qt.ItemDataRole.UserRole)
            if entity_id and entity_type:
                self.item_selected.emit(entity_id, entity_type)


class GanttChart(QWidget):
    """
    高度ガントチャート
    プロジェクト管理システムの可視化コンポーネント
    """
    
    # シグナル定義
    project_selected = pyqtSignal(str)  # project_id
    
    def __init__(self, parent, project_management_system):
        """
        ガントチャートの初期化
        
        Args:
            parent: 親ウィンドウ
            project_management_system: プロジェクト管理システム
        """
        super().__init__(parent)
        self.parent_window = parent
        self.pms = project_management_system
        
        # 状態管理
        self.current_project_id: Optional[str] = None
        self.time_scale = TimeScale.DAY
        self.pixels_per_day = 30
        self.start_date = date.today()
        self.end_date = date.today() + timedelta(days=30)
        
        # UI要素
        self.tree_widget: Optional[GanttTreeWidget] = None
        self.graphics_view: Optional[QGraphicsView] = None
        self.graphics_scene: Optional[QGraphicsScene] = None
        self.timeline_header: Optional[GanttTimelineHeader] = None
        
        # データキャッシュ
        self.entity_items: Dict[str, GanttBarItem] = {}
        self.tree_items: Dict[str, QTreeWidgetItem] = {}
        
        self._setup_ui()
        self._connect_signals()
        self._load_initial_data()
        
        # 自動更新タイマー
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_chart)
        self.refresh_timer.start(30000)  # 30秒間隔
    
    def _setup_ui(self):
        """UI要素を設定"""
        layout = QVBoxLayout(self)
        
        # ツールバー
        self._create_toolbar(layout)
        
        # メインコンテンツ
        self._create_main_content(layout)
    
    def _create_toolbar(self, parent_layout):
        """ツールバーを作成"""
        toolbar_frame = QFrame()
        toolbar_layout = QHBoxLayout(toolbar_frame)
        
        # 時間スケール選択
        toolbar_layout.addWidget(QLabel("表示:"))
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(TimeScale.get_all())
        self.scale_combo.setCurrentText(self.time_scale)
        self.scale_combo.currentTextChanged.connect(self._on_scale_changed)
        toolbar_layout.addWidget(self.scale_combo)
        
        # ズームスライダー
        toolbar_layout.addWidget(QLabel("ズーム:"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(5)
        self.zoom_slider.setMaximum(100)
        self.zoom_slider.setValue(self.pixels_per_day)
        self.zoom_slider.setMaximumWidth(150)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        toolbar_layout.addWidget(self.zoom_slider)
        
        # ズーム値表示
        self.zoom_label = QLabel(f"{self.pixels_per_day}px/日")
        toolbar_layout.addWidget(self.zoom_label)
        
        toolbar_layout.addStretch()
        
        # 操作ボタン
        self.refresh_btn = QPushButton("更新")
        self.refresh_btn.clicked.connect(self.refresh_chart)
        toolbar_layout.addWidget(self.refresh_btn)
        
        self.fit_btn = QPushButton("全体表示")
        self.fit_btn.clicked.connect(self._fit_to_window)
        toolbar_layout.addWidget(self.fit_btn)
        
        self.today_btn = QPushButton("今日")
        self.today_btn.clicked.connect(self._go_to_today)
        toolbar_layout.addWidget(self.today_btn)
        
        parent_layout.addWidget(toolbar_frame)
    
    def _create_main_content(self, parent_layout):
        """メインコンテンツを作成"""
        # 水平スプリッター
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左側: ツリービュー
        self.tree_widget = GanttTreeWidget()
        self.tree_widget.setMaximumWidth(300)
        splitter.addWidget(self.tree_widget)
        
        # 右側: ガントチャート
        self._create_gantt_area(splitter)
        
        # 分割比率設定
        splitter.setSizes([300, 700])
        
        parent_layout.addWidget(splitter)
    
    def _create_gantt_area(self, parent):
        """ガントチャートエリアを作成"""
        gantt_frame = QFrame()
        gantt_layout = QVBoxLayout(gantt_frame)
        gantt_layout.setContentsMargins(0, 0, 0, 0)
        
        # タイムラインヘッダー
        self.timeline_header = GanttTimelineHeader()
        gantt_layout.addWidget(self.timeline_header)
        
        # グラフィックビュー
        self.graphics_scene = QGraphicsScene()
        self.graphics_view = QGraphicsView(self.graphics_scene)
        
        # スクロール設定
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.graphics_view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        
        gantt_layout.addWidget(self.graphics_view)
        
        parent.addWidget(gantt_frame)
    
    def _connect_signals(self):
        """シグナル接続"""
        if self.tree_widget:
            self.tree_widget.item_selected.connect(self._on_tree_item_selected)
    
    def _load_initial_data(self):
        """初期データを読み込み"""
        self.refresh_chart()
    
    @pyqtSlot(str)
    def set_current_project(self, project_id: str):
        """
        現在のプロジェクトを設定
        
        Args:
            project_id: プロジェクトID
        """
        self.current_project_id = project_id
        self.refresh_chart()
    
    @pyqtSlot()
    def refresh_chart(self):
        """チャートを更新"""
        try:
            if not self.current_project_id or not self.pms:
                self._show_no_project_selected()
                return
            
            self._load_project_data()
            self._update_date_range()
            self._populate_tree()
            self._draw_gantt_bars()
            self._update_timeline_header()
            
        except Exception as e:
            QMessageBox.warning(
                self, "チャート更新エラー",
                f"ガントチャートの更新中にエラーが発生しました：\n{str(e)}"
            )
    
    def _show_no_project_selected(self):
        """プロジェクト未選択時の表示"""
        if self.tree_widget:
            self.tree_widget.clear()
        
        if self.graphics_scene:
            self.graphics_scene.clear()
            
            # メッセージ表示
            text_item = self.graphics_scene.addText(
                "プロジェクトが選択されていません。\n"
                "プロジェクト管理タブでプロジェクトを選択してください。",
                QFont("Arial", 12)
            )
            text_item.setPos(50, 50)
    
    def _load_project_data(self):
        """プロジェクトデータを読み込み"""
        if not self.current_project_id:
            return
        
        try:
            # プロジェクトデータ取得
            self.project = self.pms.get_project(self.current_project_id)
            if not self.project:
                return
            
            # 階層データ取得
            self.phases = self.pms.get_phases_by_project(self.current_project_id)
            self.all_processes = []
            self.all_tasks = []
            
            for phase in self.phases:
                processes = self.pms.get_processes_by_phase(phase.id)
                self.all_processes.extend(processes)
                
                for process in processes:
                    tasks = self.pms.get_tasks_by_process(process.id)
                    self.all_tasks.extend(tasks)
        
        except Exception as e:
            QMessageBox.critical(
                self, "データ読み込みエラー",
                f"プロジェクトデータの読み込みに失敗しました：\n{str(e)}"
            )
    
    def _update_date_range(self):
        """日付範囲を更新"""
        if not hasattr(self, 'project') or not self.project:
            return
        
        # プロジェクトの日付範囲を取得
        date_range = self.project.get_date_range(self.pms.phase_manager)
        
        # 開始日・終了日設定
        if date_range.get('start_date'):
            self.start_date = date_range['start_date'] - timedelta(days=7)
        else:
            self.start_date = date.today() - timedelta(days=7)
        
        if date_range.get('end_date'):
            self.end_date = date_range['end_date'] + timedelta(days=7)
        else:
            self.end_date = date.today() + timedelta(days=30)
        
        # 最小期間確保
        if (self.end_date - self.start_date).days < 30:
            self.end_date = self.start_date + timedelta(days=30)
    
    def _populate_tree(self):
        """ツリーにデータを投入"""
        if not self.tree_widget:
            return
        
        self.tree_widget.clear()
        self.tree_items.clear()
        
        if not hasattr(self, 'project') or not self.project:
            return
        
        try:
            # プロジェクトアイテム
            project_item = self._create_project_tree_item(self.project)
            self.tree_widget.addTopLevelItem(project_item)
            self.tree_items[self.project.id] = project_item
            
            # フェーズアイテム
            for phase in getattr(self, 'phases', []):
                phase_item = self._create_phase_tree_item(phase)
                project_item.addChild(phase_item)
                self.tree_items[phase.id] = phase_item
                
                # プロセスアイテム
                processes = self.pms.get_processes_by_phase(phase.id)
                for process in processes:
                    process_item = self._create_process_tree_item(process)
                    phase_item.addChild(process_item)
                    self.tree_items[process.id] = process_item
                    
                    # タスクアイテム
                    tasks = self.pms.get_tasks_by_process(process.id)
                    for task in tasks:
                        task_item = self._create_task_tree_item(task)
                        process_item.addChild(task_item)
                        self.tree_items[task.id] = task_item
            
            # 展開
            self.tree_widget.expandAll()
        
        except Exception as e:
            QMessageBox.warning(
                self, "ツリー作成エラー",
                f"ツリーの作成中にエラーが発生しました：\n{str(e)}"
            )
    
    def _create_project_tree_item(self, project) -> QTreeWidgetItem:
        """プロジェクトツリーアイテム作成"""
        item = QTreeWidgetItem()
        item.setText(0, project.name)
        
        # 期間
        date_range = project.get_date_range(self.pms.phase_manager)
        start_str = date_range['start_date'].strftime('%m/%d') if date_range.get('start_date') else ""
        end_str = date_range['end_date'].strftime('%m/%d') if date_range.get('end_date') else ""
        period_str = f"{start_str} - {end_str}" if start_str or end_str else "未設定"
        item.setText(1, period_str)
        
        # 進捗
        item.setText(2, f"{project.progress:.1f}%")
        
        # メタデータ
        item.setData(0, Qt.ItemDataRole.UserRole, project.id)
        item.setData(1, Qt.ItemDataRole.UserRole, "Project")
        
        # スタイル
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)
        
        return item
    
    def _create_phase_tree_item(self, phase) -> QTreeWidgetItem:
        """フェーズツリーアイテム作成"""
        item = QTreeWidgetItem()
        item.setText(0, f"  {phase.name}")
        
        # 期間
        date_range = phase.get_date_range(self.pms.process_manager)
        start_str = date_range['start_date'].strftime('%m/%d') if date_range.get('start_date') else ""
        end_str = phase.end_date.strftime('%m/%d') if phase.end_date else ""
        period_str = f"{start_str} - {end_str}" if start_str or end_str else "未設定"
        item.setText(1, period_str)
        
        # 進捗
        item.setText(2, f"{phase.progress:.1f}%")
        
        # メタデータ
        item.setData(0, Qt.ItemDataRole.UserRole, phase.id)
        item.setData(1, Qt.ItemDataRole.UserRole, "Phase")
        
        return item
    
    def _create_process_tree_item(self, process) -> QTreeWidgetItem:
        """プロセスツリーアイテム作成"""
        item = QTreeWidgetItem()
        item.setText(0, f"    {process.name}")
        
        # 期間
        start_str = process.start_date.strftime('%m/%d') if process.start_date else ""
        end_str = process.end_date.strftime('%m/%d') if process.end_date else ""
        period_str = f"{start_str} - {end_str}" if start_str or end_str else "未設定"
        item.setText(1, period_str)
        
        # 進捗
        item.setText(2, f"{process.progress:.1f}%")
        
        # メタデータ
        item.setData(0, Qt.ItemDataRole.UserRole, process.id)
        item.setData(1, Qt.ItemDataRole.UserRole, "Process")
        
        return item
    
    def _create_task_tree_item(self, task) -> QTreeWidgetItem:
        """タスクツリーアイテム作成"""
        item = QTreeWidgetItem()
        item.setText(0, f"      {task.name}")
        item.setText(1, "")  # タスクは期間なし
        item.setText(2, f"{task.get_completion_percentage():.0f}%")
        
        # メタデータ
        item.setData(0, Qt.ItemDataRole.UserRole, task.id)
        item.setData(1, Qt.ItemDataRole.UserRole, "Task")
        
        return item
    
    def _draw_gantt_bars(self):
        """ガントバーを描画"""
        if not self.graphics_scene:
            return
        
        self.graphics_scene.clear()
        self.entity_items.clear()
        
        if not hasattr(self, 'project') or not self.project:
            return
        
        try:
            row_height = 30
            current_y = 10
            
            # プロジェクトバー
            project_bar = self._create_gantt_bar(self.project, "Project", current_y)
            if project_bar:
                self.graphics_scene.addItem(project_bar)
                self.entity_items[self.project.id] = project_bar
            current_y += row_height + 5
            
            # フェーズバー
            for phase in getattr(self, 'phases', []):
                phase_bar = self._create_gantt_bar(phase, "Phase", current_y)
                if phase_bar:
                    self.graphics_scene.addItem(phase_bar)
                    self.entity_items[phase.id] = phase_bar
                current_y += row_height + 5
                
                # プロセスバー
                processes = self.pms.get_processes_by_phase(phase.id)
                for process in processes:
                    process_bar = self._create_gantt_bar(process, "Process", current_y)
                    if process_bar:
                        self.graphics_scene.addItem(process_bar)
                        self.entity_items[process.id] = process_bar
                    current_y += row_height + 5
                    
                    # タスクは期間がないため、バーは描画しない
                    tasks = self.pms.get_tasks_by_process(process.id)
                    for task in tasks:
                        current_y += 20  # タスク分のスペース
            
            # シーンサイズ調整
            scene_width = max(1000, (self.end_date - self.start_date).days * self.pixels_per_day)
            scene_height = max(400, current_y + 50)
            self.graphics_scene.setSceneRect(0, 0, scene_width, scene_height)
        
        except Exception as e:
            QMessageBox.warning(
                self, "ガントバー描画エラー",
                f"ガントバーの描画中にエラーが発生しました：\n{str(e)}"
            )
    
    def _create_gantt_bar(self, entity, entity_type: str, y_position: int) -> Optional[GanttBarItem]:
        """ガントバーアイテム作成"""
        # 日付取得
        start_date = None
        end_date = None
        
        if entity_type == "Project":
            date_range = entity.get_date_range(self.pms.phase_manager)
            start_date = date_range.get('start_date')
            end_date = date_range.get('end_date')
        elif entity_type == "Phase":
            date_range = entity.get_date_range(self.pms.process_manager)
            start_date = date_range.get('start_date')
            end_date = entity.end_date
        elif entity_type == "Process":
            start_date = entity.start_date
            end_date = entity.end_date
        
        # 日付が設定されていない場合はバーを描画しない
        if not start_date or not end_date:
            return None
        
        # X座標計算
        start_x = (start_date - self.start_date).days * self.pixels_per_day
        end_x = (end_date - self.start_date).days * self.pixels_per_day
        width = max(end_x - start_x, 10)  # 最小幅確保
        
        # バーデータ作成
        bar_data = {
            'type': entity_type,
            'name': entity.name,
            'start_date': start_date.strftime('%Y/%m/%d'),
            'end_date': end_date.strftime('%Y/%m/%d'),
            'progress': getattr(entity, 'progress', 0.0),
            'is_overdue': entity.is_overdue() if hasattr(entity, 'is_overdue') else False
        }
        
        # ガントバー作成
        bar_item = GanttBarItem(bar_data)
        bar_item.setRect(start_x, y_position, width, 25)
        
        return bar_item
    
    def _update_timeline_header(self):
        """タイムラインヘッダーを更新"""
        if self.timeline_header:
            self.timeline_header.set_date_range(self.start_date, self.end_date)
            self.timeline_header.set_scale(self.time_scale, self.pixels_per_day)
    
    def _on_scale_changed(self, scale: str):
        """スケール変更処理"""
        self.time_scale = scale
        
        # スケールに応じてピクセル数調整
        if scale == TimeScale.MONTH:
            self.pixels_per_day = min(self.pixels_per_day, 10)
        elif scale == TimeScale.WEEK:
            self.pixels_per_day = min(self.pixels_per_day, 20)
        
        self.zoom_slider.setValue(self.pixels_per_day)
        self._update_timeline_header()
        self._draw_gantt_bars()
    
    def _on_zoom_changed(self, value: int):
        """ズーム変更処理"""
        self.pixels_per_day = value
        self.zoom_label.setText(f"{value}px/日")
        self._update_timeline_header()
        self._draw_gantt_bars()
    
    def _fit_to_window(self):
        """ウィンドウに合わせて表示"""
        if self.graphics_view and self.graphics_scene:
            self.graphics_view.fitInView(
                self.graphics_scene.sceneRect(),
                Qt.AspectRatioMode.KeepAspectRatio
            )
    
    def _go_to_today(self):
        """今日の位置にスクロール"""
        if self.graphics_view:
            today_x = (date.today() - self.start_date).days * self.pixels_per_day
            center_point = QPointF(today_x, self.graphics_view.sceneRect().height() / 2)
            self.graphics_view.centerOn(center_point)
    
    @pyqtSlot(str, str)
    def _on_tree_item_selected(self, entity_id: str, entity_type: str):
        """ツリーアイテム選択処理"""
        # 対応するガントバーをハイライト
        if entity_id in self.entity_items:
            bar_item = self.entity_items[entity_id]
            bar_item.setSelected(True)
            
            # ビューをバーの位置にスクロール
            if self.graphics_view:
                bar_rect = bar_item.sceneBoundingRect()
                self.graphics_view.ensureVisible(bar_rect)
        
        # プロジェクト選択シグナル発行
        if entity_type == "Project":
            self.project_selected.emit(entity_id)


def main():
    """スタンドアロンテスト用メイン関数"""
    app = QApplication(sys.argv)
    
    try:
        # プロジェクト管理システムを初期化
        from core.manager import ProjectManagementSystem
        pms = ProjectManagementSystem()
        
        # サンプルプロジェクト作成
        project = pms.create_project("テストプロジェクト", "ガントチャートテスト用")
        phase = pms.create_phase("テストフェーズ", "テストフェーズです", project.id)
        process = pms.create_process("テストプロセス", "担当者A", "テストプロセスです", phase.id)
        
        # 日付設定
        from datetime import date, timedelta
        process.set_dates(date.today(), date.today() + timedelta(days=10))
        process.set_progress(30.0)
        
        # ガントチャート作成・表示
        gantt_chart = GanttChart(None, pms)
        gantt_chart.set_current_project(project.id)
        gantt_chart.show()
        
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