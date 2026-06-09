# -*- coding: utf-8 -*-
"""
VCOM (精度分析与转换工具 Qt版) - 主运行模块 (双向网格与双误差曲线切换版)
"""
import sys
import os
import json
import math
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                             QVBoxLayout, QPushButton, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QTableWidget,
                             QTableWidgetItem, QTabWidget, QGroupBox, QSplitter,
                             QHeaderView, QFileDialog, QMessageBox, QMenuBar,
                             QComboBox, QCheckBox, QProgressDialog, QGridLayout)
from PySide6.QtCore import Qt, Signal, QThread, QPointF, QRectF
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter, QFont, QPen, QBrush

# 引入 Matplotlib 导航工具栏以支持缩放和拖拽
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from gnss_parser import (parse_log_line, convert_pogos_to_gga, calculate_metrics,
                    time_str_to_seconds, seconds_to_time_str, gps_tow_to_utc_time, interpolate_dynamic_truth)
from plot_widget import PlotWidget
from ui_main import QSS_STYLE, SegmentListItemWidget
from settings_dialog import SettingsDialog

class LogParserThread(QThread):
    progress_updated = Signal(int)
    finished_parsing = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, filepath, leap_secs, strict_checksum=False, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.leap_secs = leap_secs
        self.strict_checksum = strict_checksum
        self.is_cancelled = False

    def run(self):
        try:
            file_size = os.path.getsize(self.filepath)
            processed_size = 0
            file_epochs = []
            sentence_types = {}
            first_time_sec = None
            last_time_sec = None
            first_time_str = ''
            last_time_str = ''
            gga_map = {}
            last_time_sec_for_gsa = None
            last_emit_progress = -1
            
            with open(self.filepath, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    if self.is_cancelled:
                        break
                    
                    line_len = len(line.encode('utf-8', errors='replace'))
                    processed_size += line_len
                    
                    if not line.startswith('$'):
                        continue
                        
                    comma_idx = line.find(',')
                    if comma_idx != -1:
                        stype = line[:comma_idx]
                        sentence_types[stype] = sentence_types.get(stype, 0) + 1
                        
                    epoch = parse_log_line(line, self.leap_secs, self.strict_checksum)
                    if epoch:
                        if epoch['type'] in ['GGA', 'POGOS', 'PODRS', 'RMC']:
                            epoch['file_id'] = self.filepath
                            file_epochs.append(epoch)
                            last_time_sec_for_gsa = epoch['utc_time_sec']
                            if first_time_sec is None:
                                first_time_sec = epoch['utc_time_sec']
                                first_time_str = epoch['time_str']
                            last_time_sec = epoch['utc_time_sec']
                            last_time_str = epoch['time_str']
                            
                            if epoch['type'] == 'GGA':
                                sec_in_day = int(epoch['utc_time_sec']) % 86400
                                if sec_in_day not in gga_map:
                                    gga_map[sec_in_day] = {}
                                gga_map[sec_in_day].update({
                                    'quality': epoch['quality'],
                                    'num_sats': epoch['num_sats'],
                                    'hdop': epoch['hdop']
                                })
                        elif epoch['type'] == 'GSA' and last_time_sec_for_gsa is not None:
                            sec_in_day = int(last_time_sec_for_gsa) % 86400
                            if sec_in_day not in gga_map:
                                gga_map[sec_in_day] = {}
                            gga_map[sec_in_day].update({
                                'vdop': epoch['vdop'],
                                'pdop': epoch['pdop']
                            })
                            
                    if processed_size % (1024 * 100) < line_len:  # Update roughly every 100KB
                        progress = int((processed_size / file_size) * 100) if file_size > 0 else 0
                        if progress > last_emit_progress:
                            self.progress_updated.emit(progress)
                            last_emit_progress = progress
            
            for ep in file_epochs:
                sec_in_day = int(ep['utc_time_sec']) % 86400
                if sec_in_day in gga_map:
                    if ep['type'] in ['POGOS', 'PODRS']:
                        if 'quality' in gga_map[sec_in_day]:
                            ep['quality'] = gga_map[sec_in_day]['quality']
                        if 'num_sats' in gga_map[sec_in_day]:
                            ep['num_sats'] = gga_map[sec_in_day]['num_sats']
                        if 'hdop' in gga_map[sec_in_day]:
                            ep['hdop'] = gga_map[sec_in_day]['hdop']
                    
                    if 'vdop' in gga_map[sec_in_day]:
                        ep['vdop'] = gga_map[sec_in_day]['vdop']
                    if 'pdop' in gga_map[sec_in_day]:
                        ep['pdop'] = gga_map[sec_in_day]['pdop']

            if file_epochs:
                from gnss_parser import unwrap_times
                unwrapped = unwrap_times([ep['utc_time_sec'] for ep in file_epochs])
                for i, ep in enumerate(file_epochs):
                    ep['utc_time_sec'] = unwrapped[i]
                first_time_sec = file_epochs[0]['utc_time_sec']
                last_time_sec = file_epochs[-1]['utc_time_sec']

            self.progress_updated.emit(100)
            result = {
                'file_epochs': file_epochs,
                'first_time_sec': first_time_sec,
                'last_time_sec': last_time_sec,
                'first_time_str': first_time_str,
                'last_time_str': last_time_str,
                'sentence_types': sentence_types
            }
            self.finished_parsing.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))

def create_switch_icons():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    res_dir = os.path.join(base_dir, "resources")
    # Make sure resources directory exists
    os.makedirs(res_dir, exist_ok=True)
    # switch_off.png (36x20)
    pix_off = QPixmap(36, 20)
    pix_off.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pix_off)
    painter.setRenderHint(QPainter.Antialiasing)
    # Draw capsule background
    painter.setPen(QPen(QColor("#475569"), 1.5))
    painter.setBrush(QBrush(QColor("#1E293B")))
    painter.drawRoundedRect(QRectF(1, 1, 34, 18), 9, 9)
    # Draw knob
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor("#64748B")))
    painter.drawEllipse(QRectF(3, 3, 14, 14))
    painter.end()
    try:
        pix_off.save(os.path.join(res_dir, "switch_off.png"), "PNG")
    except Exception:
        pass
        
    # switch_on.png (36x20)
    pix_on = QPixmap(36, 20)
    pix_on.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pix_on)
    painter.setRenderHint(QPainter.Antialiasing)
    # Draw capsule background
    painter.setPen(QPen(QColor("#0EA5E9"), 1.5))
    painter.setBrush(QBrush(QColor("#0F172A")))
    painter.drawRoundedRect(QRectF(1, 1, 34, 18), 9, 9)
    # Draw knob (glowing neon blue)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor("#38BDF8")))
    painter.drawEllipse(QRectF(19, 3, 14, 14))
    painter.end()
    try:
        pix_on.save(os.path.join(res_dir, "switch_on.png"), "PNG")
    except Exception:
        pass

def create_app_icon():
    # Create a 256x256 high-resolution icon
    pixmap = QPixmap(256, 256)
    pixmap.fill(QColor("#0B1120")) # Dark background matching QSS QMainWindow
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # Draw a stylish target/orbit (satellite positioning theme)
    # Circle 1 (Outer orbit)
    pen = QPen(QColor("#1E293B"), 4)
    painter.setPen(pen)
    painter.drawEllipse(QRectF(28, 28, 200, 200))
    
    # Circle 2 (Inner orbit)
    pen.setColor(QColor("#334155"))
    pen.setWidth(2)
    painter.setPen(pen)
    painter.drawEllipse(QRectF(56, 56, 144, 144))
    
    # Crosshair lines
    painter.drawLine(QPointF(128, 10), QPointF(128, 246))
    painter.drawLine(QPointF(10, 128), QPointF(246, 128))
    
    # Draw a stylish "V" (for VCOM) in the center
    font = QFont("Outfit", 96, QFont.Bold)
    painter.setFont(font)
    painter.setPen(QColor("#60A5FA")) # Electric blue
    painter.drawText(QRectF(0, 0, 256, 240), Qt.AlignCenter, "V")
    
    # Draw a glowing center dot
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor("#EF4444"))) # Red target dot
    painter.drawEllipse(QPointF(128, 128), 12, 12)
    
    painter.end()
    
    # Save physical icon files to the resources directory for PyInstaller
    base_dir = os.path.dirname(os.path.abspath(__file__))
    res_dir = os.path.join(base_dir, "resources")
    os.makedirs(res_dir, exist_ok=True)
    if not os.path.exists(os.path.join(res_dir, "icon.png")):
        try:
            pixmap.save(os.path.join(res_dir, "icon.png"), "PNG")
        except Exception:
            pass
    if not os.path.exists(os.path.join(res_dir, "icon.ico")):
        try:
            pixmap.save(os.path.join(res_dir, "icon.ico"), "ICO")
        except Exception:
            pass
            
    # Also generate modern switch toggle PNGs for checkboxes
    create_switch_icons()
            
    return QIcon(pixmap)

def is_system_dark_mode():
    """读取 Windows 注册表以精准获取操作系统真实的深色/浅色模式"""
    import platform
    if platform.system() == "Windows":
        try:
            import winreg
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return value == 0  # 0 表示深色模式 (AppsUseLightTheme = 0)
        except Exception:
            pass
    # 针对非 Windows 系统或读取失败的备用方案
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QPalette
        app = QApplication.instance()
        if app:
            bg_color = app.palette().color(QPalette.ColorRole.Window)
            return bg_color.lightness() < 128
    except Exception:
        pass
    return False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VCOM定位精度分析工具")
        self.setWindowIcon(create_app_icon())
        self.resize(1180, 720)
        self.setStyleSheet(QSS_STYLE)
        
        self.app_config = {}
        self.parser_thread = None
        self.dynamic_parser_thread = None
        
        # 数据状态管理
        self.raw_lines = []
        self.parsed_epochs = []
        self.file_epochs_map = {}  # 字典映射 file_id -> epochs list 以加速筛选
        self.sentence_types = {}
        self.time_range = {'start': 0, 'end': 0}
        
        self.truth_mode = 'auto' # 'auto' 或 'manual'
        self.truth = {'lat': 0.0, 'lon': 0.0, 'alt': 0.0}
        
        self.segments = []
        self.segment_counter = 0
        self.default_colors = [
            '#2563EB', '#EF4444', '#16A34A', '#D97706', '#9333EA', '#0D9488',
            '#F97316', '#EC4899', '#78350F', '#84CC16', '#4338CA', '#4B5563'
        ]
        self.first_time_str = ''
        self.last_time_str = ''
        self.time_zone = 'UTC'
        self.show_absolute_alt = False  # 是否显示高程绝对值误差
        self.show_raw_alt = False  # 是否显示高程绝对物理值 (而不是误差绝对值)
        self.show_extrema = True  # 是否显示最值标注
        self.x_axis_mode = '历元数'  # 是否使用时间轴对齐 X 轴
        
        # 初始化 UI
        self.init_ui()
        self.setAcceptDrops(True)
        self.load_config()
        self.pending_parse_queue = []
        self.total_queue_count = 0

    def get_leap_seconds(self):
        try:
            return int(self.txt_leap.text())
        except ValueError:
            return 18
        
    def init_ui(self):
        # 1. 顶部菜单栏
        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)
        file_menu = self.menu_bar.addMenu("文件")
        file_menu.addAction("打开日志", self.on_import_clicked)
        file_menu.addAction("退出", self.close)
        settings_menu = self.menu_bar.addMenu("设置")
        settings_menu.addAction("首选项...", self.on_settings_clicked)
        self.menu_bar.addMenu("帮助")

        # 主中央分割窗
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.main_splitter)
        
        # 2. 左侧工作区 (包含 Tab 嵌套画布及工具栏)
        self.left_widget = QWidget()
        left_layout = QVBoxLayout(self.left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        self.tab_widget = QTabWidget()

        # 定义白色图表卡片内嵌工具栏样式，采用浅色背景以契合白色图表卡片，确保深色(黑色)图标在任何系统模式下都清晰可见
        TOOLBAR_STYLE = """
        QToolBar {
            background-color: #F8FAFC;
            border: none;
            border-bottom: 1px solid #E2E8F0;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        }
        QToolBar QToolButton {
            background-color: transparent;
            border: none;
            border-radius: 4px;
            padding: 4px;
            margin: 2px;
        }
        QToolBar QToolButton:hover {
            background-color: #E2E8F0;
        }
        QToolBar QToolButton:pressed {
            background-color: #CBD5E1;
        }
        QToolBar QToolButton:disabled {
            background-color: transparent;
            opacity: 0.5;
        }
        QToolBar QLabel {
            color: #475569;
            font-size: 11px;
            font-weight: bold;
            padding-left: 10px;
            background-color: transparent;
        }
        QToolBar::separator {
            width: 1px;
            background-color: #E2E8F0;
            margin-top: 4px;
            margin-bottom: 4px;
            margin-left: 6px;
            margin-right: 6px;
        }
        """


        # A. 靶心图容器页
        self.tab_scatter = QWidget()
        layout_scatter = QVBoxLayout(self.tab_scatter)
        layout_scatter.setContentsMargins(12, 12, 12, 12)
        layout_scatter.setSpacing(0)
        
        # 创建白卡容器
        self.card_scatter = QWidget()
        self.card_scatter.setStyleSheet("background-color: #FFFFFF; border: 1px solid #334155; border-radius: 8px;")
        card_layout_scatter = QVBoxLayout(self.card_scatter)
        card_layout_scatter.setContentsMargins(0, 0, 0, 0)
        card_layout_scatter.setSpacing(0)
        
        self.canvas_scatter = PlotWidget(self.card_scatter)
        self.canvas_scatter.setStyleSheet("background-color: #FFFFFF; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;")
        self.toolbar_scatter = NavigationToolbar(self.canvas_scatter, self.card_scatter)
        self.toolbar_scatter.setStyleSheet(TOOLBAR_STYLE)
        
        card_layout_scatter.addWidget(self.toolbar_scatter)
        card_layout_scatter.addWidget(self.canvas_scatter)
        layout_scatter.addWidget(self.card_scatter)
        
        # B. 定位质量图容器页
        self.tab_status = QWidget()
        layout_status = QVBoxLayout(self.tab_status)
        layout_status.setContentsMargins(12, 12, 12, 12)
        layout_status.setSpacing(0)
        
        # 创建白卡容器
        self.card_status = QWidget()
        self.card_status.setStyleSheet("background-color: #FFFFFF; border: 1px solid #334155; border-radius: 8px;")
        card_layout_status = QVBoxLayout(self.card_status)
        card_layout_status.setContentsMargins(0, 0, 0, 0)
        card_layout_status.setSpacing(0)
        
        self.canvas_status = PlotWidget(self.card_status)
        self.canvas_status.setStyleSheet("background-color: #FFFFFF; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;")
        self.toolbar_status = NavigationToolbar(self.canvas_status, self.card_status)
        self.toolbar_status.setStyleSheet(TOOLBAR_STYLE)
        
        card_layout_status.addWidget(self.toolbar_status)
        card_layout_status.addWidget(self.canvas_status)
        layout_status.addWidget(self.card_status)
        
        # C. 水平误差历元图容器页
        self.tab_epoch_h = QWidget()
        layout_epoch_h = QVBoxLayout(self.tab_epoch_h)
        layout_epoch_h.setContentsMargins(12, 12, 12, 12)
        layout_epoch_h.setSpacing(0)
        
        # 创建白卡容器
        self.card_epoch_h = QWidget()
        self.card_epoch_h.setStyleSheet("background-color: #FFFFFF; border: 1px solid #334155; border-radius: 8px;")
        card_layout_epoch_h = QVBoxLayout(self.card_epoch_h)
        card_layout_epoch_h.setContentsMargins(0, 0, 0, 0)
        card_layout_epoch_h.setSpacing(0)
        
        self.canvas_epoch_h = PlotWidget(self.card_epoch_h)
        self.canvas_epoch_h.setStyleSheet("background-color: #FFFFFF; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;")
        self.toolbar_epoch_h = NavigationToolbar(self.canvas_epoch_h, self.card_epoch_h)
        self.toolbar_epoch_h.setStyleSheet(TOOLBAR_STYLE)
        
        card_layout_epoch_h.addWidget(self.toolbar_epoch_h)
        card_layout_epoch_h.addWidget(self.canvas_epoch_h)
        layout_epoch_h.addWidget(self.card_epoch_h)
 
        # D. 高程误差历元图容器页
        self.tab_epoch_v = QWidget()
        layout_epoch_v = QVBoxLayout(self.tab_epoch_v)
        layout_epoch_v.setContentsMargins(12, 12, 12, 12)
        layout_epoch_v.setSpacing(0)
        
        # 创建白卡容器
        self.card_epoch_v = QWidget()
        self.card_epoch_v.setStyleSheet("background-color: #FFFFFF; border: 1px solid #334155; border-radius: 8px;")
        card_layout_epoch_v = QVBoxLayout(self.card_epoch_v)
        card_layout_epoch_v.setContentsMargins(0, 0, 0, 0)
        card_layout_epoch_v.setSpacing(0)
        
        self.canvas_epoch_v = PlotWidget(self.card_epoch_v)
        self.canvas_epoch_v.setStyleSheet("background-color: #FFFFFF; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;")
        self.toolbar_epoch_v = NavigationToolbar(self.canvas_epoch_v, self.card_epoch_v)
        self.toolbar_epoch_v.setStyleSheet(TOOLBAR_STYLE)
        
        card_layout_epoch_v.addWidget(self.toolbar_epoch_v)
        card_layout_epoch_v.addWidget(self.canvas_epoch_v)
        layout_epoch_v.addWidget(self.card_epoch_v)
        
        # E. 绝对轨迹投影页
        self.tab_trajectory = QWidget()
        layout_trajectory = QVBoxLayout(self.tab_trajectory)
        layout_trajectory.setContentsMargins(12, 12, 12, 12)
        layout_trajectory.setSpacing(0)
        
        self.card_trajectory = QWidget()
        self.card_trajectory.setStyleSheet("background-color: #FFFFFF; border: 1px solid #334155; border-radius: 8px;")
        card_layout_trajectory = QVBoxLayout(self.card_trajectory)
        card_layout_trajectory.setContentsMargins(0, 0, 0, 0)
        card_layout_trajectory.setSpacing(0)
        
        self.canvas_trajectory = PlotWidget(self.card_trajectory)
        self.canvas_trajectory.setStyleSheet("background-color: #FFFFFF; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;")
        self.toolbar_trajectory = NavigationToolbar(self.canvas_trajectory, self.card_trajectory)
        self.toolbar_trajectory.setStyleSheet(TOOLBAR_STYLE)
        
        card_layout_trajectory.addWidget(self.toolbar_trajectory)
        card_layout_trajectory.addWidget(self.canvas_trajectory)
        layout_trajectory.addWidget(self.card_trajectory)

        # 添加选项卡
        self.tab_widget.addTab(self.tab_scatter, "靶心图")
        self.tab_widget.addTab(self.tab_epoch_h, "水平位置误差历元分布图")
        self.tab_widget.addTab(self.tab_epoch_v, "高程误差历元分布图")
        self.tab_widget.addTab(self.tab_status, "定位质量图")
        self.tab_widget.addTab(self.tab_trajectory, "绝对轨迹图")
        
        # E. 精度统计对比页
        self.tab_metrics = QWidget()
        layout_metrics = QVBoxLayout(self.tab_metrics)
        layout_metrics.setContentsMargins(15, 15, 15, 15)
        
        self.table_metrics = QTableWidget(0, 11)
        self.table_metrics.setHorizontalHeaderLabels([
            "分段名称", "有效对齐率 (%)", "总历元数", "固定率", "CEP50 (m)", "CEP68 (m)", "CEP95 (m)", 
            "RMS(水平) (m)", "RMS(高程) (m)", "最大水平偏差 (m)", "最大高程偏差 (m)"
        ])
        self.table_metrics.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_metrics.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_metrics.verticalHeader().setVisible(False)
        self.table_metrics.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                color: #0F172A;
                gridline-color: #E2E8F0;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                font-size: 13px;
            }
            QTableWidget::item {
                color: #0F172A;
            }
            QHeaderView::section {
                background-color: #F1F5F9;
                color: #0F172A;
                font-weight: bold;
                padding: 6px;
                border: 1px solid #E2E8F0;
            }
        """)
        layout_metrics.addWidget(self.table_metrics)
        self.tab_widget.addTab(self.tab_metrics, "精度统计对比")
        
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        left_layout.addWidget(self.tab_widget)
        
        self.main_splitter.addWidget(self.left_widget)
        
        # 3. 右侧属性侧边栏 (深色)
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setObjectName("sidebar_container")
        sidebar_layout = QVBoxLayout(self.sidebar_widget)
        sidebar_layout.setContentsMargins(8, 8, 8, 8)
        sidebar_layout.setSpacing(10)
        
        # 3.1 参考位置卡片
        self.group_ref = QGroupBox("参考位置")
        ref_layout = QVBoxLayout(self.group_ref)
        ref_layout.setContentsMargins(8, 12, 8, 8)
        ref_layout.setSpacing(6)
        
        # Auto / Manual 切换按钮
        switch_layout = QHBoxLayout()
        switch_layout.setSpacing(2)
        
        self.btn_ref_auto = QPushButton("自动(均值)")
        self.btn_ref_auto.setObjectName("btn_ref_auto")
        self.btn_ref_auto.setProperty("active", True)
        self.btn_ref_auto.clicked.connect(self.set_ref_mode_auto)
        
        self.btn_ref_manual = QPushButton("自定义")
        self.btn_ref_manual.setObjectName("btn_ref_manual")
        self.btn_ref_manual.setProperty("active", False)
        self.btn_ref_manual.clicked.connect(self.set_ref_mode_manual)
        
        self.btn_ref_dynamic = QPushButton("动态文件")
        self.btn_ref_dynamic.setObjectName("btn_ref_dynamic")
        self.btn_ref_dynamic.setProperty("active", False)
        self.btn_ref_dynamic.clicked.connect(self.set_ref_mode_dynamic)
        
        switch_layout.addWidget(self.btn_ref_auto)
        switch_layout.addWidget(self.btn_ref_manual)
        switch_layout.addWidget(self.btn_ref_dynamic)
        ref_layout.addLayout(switch_layout)
        
        # 历史输入坐标下拉框
        row_history = QHBoxLayout()
        row_history.setSpacing(6)
        lbl_history = QLabel("历史参考坐标：")
        lbl_history.setStyleSheet("color:#94A3B8; font-size:12px; font-weight:bold;")
        self.cmb_history = QComboBox()
        self.cmb_history.setFixedHeight(28)
        self.cmb_history.setDisabled(True)  # 默认Auto模式下禁用
        self.cmb_history.currentIndexChanged.connect(self.on_history_coordinate_selected)
        row_history.addWidget(lbl_history)
        row_history.addWidget(self.cmb_history)
        ref_layout.addLayout(row_history)
        
        # 经纬高输入框
        self.inputs_layout = QVBoxLayout()
        self.inputs_layout.setSpacing(4)
        
        # 备注名称
        row_name = QHBoxLayout()
        row_name.addWidget(QLabel("备注 (可选)："))
        self.txt_ref_name = QLineEdit("")
        self.txt_ref_name.setAlignment(Qt.AlignLeft)
        self.txt_ref_name.setPlaceholderText("例如: 静态测试点 A")
        self.txt_ref_name.setDisabled(True)
        self.txt_ref_name.editingFinished.connect(self.on_manual_truth_changed)
        row_name.addWidget(self.txt_ref_name)
        self.inputs_layout.addLayout(row_name)
        
        # 纬度
        row_lat = QHBoxLayout()
        row_lat.addWidget(QLabel("纬度 (度)："))
        self.txt_lat = QLineEdit("0.00000000")
        self.txt_lat.setAlignment(Qt.AlignLeft)
        self.txt_lat.setDisabled(True)
        self.txt_lat.editingFinished.connect(self.on_manual_truth_changed)
        row_lat.addWidget(self.txt_lat)
        self.inputs_layout.addLayout(row_lat)
        
        # 经度
        row_lon = QHBoxLayout()
        row_lon.addWidget(QLabel("经度 (度)："))
        self.txt_lon = QLineEdit("0.00000000")
        self.txt_lon.setAlignment(Qt.AlignLeft)
        self.txt_lon.setDisabled(True)
        self.txt_lon.editingFinished.connect(self.on_manual_truth_changed)
        row_lon.addWidget(self.txt_lon)
        self.inputs_layout.addLayout(row_lon)
        
        # 高程
        row_alt = QHBoxLayout()
        row_alt.addWidget(QLabel("高程 (米)："))
        self.txt_alt = QLineEdit("0.000")
        self.txt_alt.setAlignment(Qt.AlignLeft)
        self.txt_alt.setDisabled(True)
        self.txt_alt.editingFinished.connect(self.on_manual_truth_changed)
        row_alt.addWidget(self.txt_alt)
        self.inputs_layout.addLayout(row_alt)
        self.inputs_widget = QWidget()
        self.inputs_widget.setLayout(self.inputs_layout)
        ref_layout.addWidget(self.inputs_widget)
        
        # 动态真值输入区
        self.dynamic_layout = QVBoxLayout()
        self.dynamic_layout.setSpacing(4)
        self.lbl_dynamic_file = QLabel("未加载动态真值文件")
        self.lbl_dynamic_file.setWordWrap(True)
        self.lbl_dynamic_file.setStyleSheet("color:#38BDF8;")
        
        dyn_btn_layout = QHBoxLayout()
        dyn_btn_layout.setSpacing(4)
        self.btn_load_dynamic = QPushButton("导入真值")
        self.btn_load_dynamic.clicked.connect(self.on_load_dynamic_clicked)
        self.btn_clear_dynamic = QPushButton("清除真值")
        self.btn_clear_dynamic.setEnabled(False)
        self.btn_clear_dynamic.clicked.connect(self.on_clear_dynamic_clicked)
        
        dyn_btn_layout.addWidget(self.btn_load_dynamic)
        dyn_btn_layout.addWidget(self.btn_clear_dynamic)
        
        self.dynamic_layout.addWidget(self.lbl_dynamic_file)
        self.dynamic_layout.addLayout(dyn_btn_layout)
        
        self.dynamic_widget = QWidget()
        self.dynamic_widget.setLayout(self.dynamic_layout)
        self.dynamic_widget.hide()
        ref_layout.addWidget(self.dynamic_widget)
        
        # 闰秒
        row_leap = QHBoxLayout()
        row_leap.addWidget(QLabel("GPS-UTC 闰秒："))
        self.txt_leap = QLineEdit("18")
        self.txt_leap.setFixedWidth(50)
        self.txt_leap.setAlignment(Qt.AlignCenter)
        self.txt_leap.editingFinished.connect(self.recompute_all)
        row_leap.addWidget(self.txt_leap)
        self.inputs_layout.addLayout(row_leap)
        
        sidebar_layout.addWidget(self.group_ref)
        
        # 3.2 文件/分析时段列表卡片
        self.group_file = QGroupBox("文件 / 分析分段")
        file_layout = QVBoxLayout(self.group_file)
        file_layout.setContentsMargins(8, 12, 8, 8)
        file_layout.setSpacing(6)
        
        # 动作区分割与小图标化：采用网格布局，将按钮压缩成 3 列 2 行，提高横向空间利用率
        actions_grid = QGridLayout()
        actions_grid.setSpacing(4)
        actions_grid.setContentsMargins(0, 4, 0, 4)
        
        self.btn_import = QPushButton("➕ 导入日志")
        self.btn_import.setToolTip("导入 GNSS 定位日志文件，支持 $GNGGA、$POGOS、$PODRS 等格式。")
        self.btn_import.clicked.connect(self.on_import_clicked)
        actions_grid.addWidget(self.btn_import, 0, 0)
        
        self.btn_add_segment = QPushButton("➕ 新增分段")
        self.btn_add_segment.setToolTip("在下方列表中新增一个自定义的分析时段。")
        self.btn_add_segment.clicked.connect(self.on_add_segment_clicked)
        actions_grid.addWidget(self.btn_add_segment, 0, 1)
        
        self.btn_export_raw = QPushButton("✂️ 数据截取")
        self.btn_export_raw.setToolTip("截取当前分析时段内的定位日志，并另存为新文件。")
        self.btn_export_raw.clicked.connect(self.on_export_raw_clicked)
        actions_grid.addWidget(self.btn_export_raw, 0, 2)
        
        self.btn_export_gga = QPushButton("🌐 格式转换")
        self.btn_export_gga.setToolTip("将当前时段内的 POGOS 或 PODRS 格式数据转换并导出为标准的 GGA 语句文件。")
        self.btn_export_gga.clicked.connect(self.on_export_gga_clicked)
        actions_grid.addWidget(self.btn_export_gga, 1, 0)
        
        self.btn_export_kml = QPushButton("🧭 导出 KML")
        self.btn_export_kml.setToolTip("根据当前时段的数据生成 KML 轨迹文件，可在 Google Earth 等地图中查看。")
        self.btn_export_kml.clicked.connect(self.on_export_kml_clicked)
        actions_grid.addWidget(self.btn_export_kml, 1, 1)
        
        self.btn_export_report = QPushButton("📄 导出 Word")
        self.btn_export_report.setToolTip("将当前时段的定位精度分析结果与图表自动生成为 Word 格式报告。")
        self.btn_export_report.clicked.connect(self.on_export_report_clicked)
        actions_grid.addWidget(self.btn_export_report, 1, 2)
        
        file_layout.addLayout(actions_grid)
        
        # 设置区网格对齐 (2-Column Key-Value Grid)：左右两列排布下拉框与复选框切换开关
        options_layout = QGridLayout()
        options_layout.setSpacing(6)
        options_layout.setContentsMargins(0, 4, 0, 4)
        
        # 左列：时间下拉框
        row_tz = QHBoxLayout()
        row_tz.setSpacing(2)
        lbl_tz = QLabel("时间:")
        lbl_tz.setStyleSheet("color:#94A3B8; font-size:12px; font-weight:bold;")
        self.cmb_timezone = QComboBox()
        self.cmb_timezone.addItems(["UTC 时间", "北京时间 (UTC+8)"])
        self.cmb_timezone.setFixedWidth(110)
        self.cmb_timezone.setFixedHeight(28)
        self.cmb_timezone.currentTextChanged.connect(self.on_timezone_changed)
        row_tz.addWidget(lbl_tz)
        row_tz.addWidget(self.cmb_timezone)
        row_tz.addStretch()
        options_layout.addLayout(row_tz, 0, 0)
        
        # 右列：X轴下拉框
        row_xaxis = QHBoxLayout()
        row_xaxis.setSpacing(2)
        lbl_xaxis = QLabel("X轴:")
        lbl_xaxis.setStyleSheet("color:#94A3B8; font-size:12px; font-weight:bold;")
        self.cmb_xaxis = QComboBox()
        self.cmb_xaxis.addItems(["历元数", "时间轴"])
        self.cmb_xaxis.setFixedWidth(90)
        self.cmb_xaxis.setFixedHeight(28)
        self.cmb_xaxis.currentTextChanged.connect(self.on_xaxis_changed)
        row_xaxis.addWidget(lbl_xaxis)
        row_xaxis.addWidget(self.cmb_xaxis)
        row_xaxis.addStretch()
        options_layout.addLayout(row_xaxis, 0, 1)
        
        # 复选开关：左列 - 高程误差绝对值，右列 - 显示高程值
        self.cb_abs_alt = QCheckBox("高程误差绝对值")
        self.cb_abs_alt.setToolTip("开启后，高程误差将以绝对值（去除正负号）进行计算与展示。")
        self.cb_abs_alt.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: bold;")
        self.cb_abs_alt.setChecked(False)
        self.cb_abs_alt.stateChanged.connect(self.on_alt_mode_changed)
        options_layout.addWidget(self.cb_abs_alt, 1, 0)
        
        self.cb_raw_alt = QCheckBox("显示高程值")
        self.cb_raw_alt.setToolTip("开启后，图表将直接展示高程的绝对物理值，而非相对于真值的误差值。")
        self.cb_raw_alt.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: bold;")
        self.cb_raw_alt.setChecked(False)
        self.cb_raw_alt.stateChanged.connect(self.on_raw_alt_changed)
        options_layout.addWidget(self.cb_raw_alt, 1, 1)
        
        self.cb_show_extrema = QCheckBox("显示极值")
        self.cb_show_extrema.setToolTip("在误差分布图上自动标注最大误差值与最小误差值点。")
        self.cb_show_extrema.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: bold;")
        self.cb_show_extrema.setChecked(True)
        self.cb_show_extrema.stateChanged.connect(self.on_extrema_mode_changed)
        options_layout.addWidget(self.cb_show_extrema, 2, 0)
        
        self.cb_show_sats = QCheckBox("显示卫星与DOP")
        self.cb_show_sats.setToolTip("在下方开启双联屏，联动分析在用卫星数与 DOP 变化趋势。")
        self.cb_show_sats.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: bold;")
        self.cb_show_sats.setChecked(False)
        self.cb_show_sats.stateChanged.connect(self.on_show_sats_changed)
        options_layout.addWidget(self.cb_show_sats, 2, 1)
        
        file_layout.addLayout(options_layout)
        
        # 文件列表
        self.list_segments = QListWidget()
        file_layout.addWidget(self.list_segments)
        
        sidebar_layout.addWidget(self.group_file)
        
        # 状态指示
        self.lbl_status = QLabel("等待导入 GNSS 日志...")
        self.lbl_status.setStyleSheet("color:#64748B; font-size:10px;")
        sidebar_layout.addWidget(self.lbl_status)
        
        self.sidebar_widget.setMinimumWidth(320)
        self.sidebar_widget.setMaximumWidth(450)
        self.main_splitter.addWidget(self.sidebar_widget)
        self.main_splitter.setSizes([860, 320])
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        
        # 初始化工具栏样式 (适配系统浅色/深色主题)
        self.update_toolbar_styles()

    def showEvent(self, event):
        super().showEvent(event)
        # Ensure right sidebar defaults to the minimum functional width (320px) on startup or resize
        sidebar_w = 320
        left_w = self.width() - sidebar_w - self.main_splitter.handleWidth()
        self.main_splitter.setSizes([left_w, sidebar_w])

    def update_toolbar_styles(self):
        """根据系统深浅色主题动态更新绘图工具栏样式"""
        is_dark = is_system_dark_mode()

        if is_dark:
            # 系统深色模式下，Matplotlib 加载的 symbolic 图标为白色，需要深色底工具栏背景
            style = """
            QToolBar {
                background-color: #1E293B;
                border: none;
                border-bottom: 1px solid #334155;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QToolBar QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
                margin: 2px;
            }
            QToolBar QToolButton:hover {
                background-color: #334155;
            }
            QToolBar QToolButton:pressed {
                background-color: #0F172A;
            }
            QToolBar QToolButton:disabled {
                background-color: transparent;
                opacity: 0.5;
            }
            QToolBar QLabel {
                color: #94A3B8;
                font-size: 11px;
                font-weight: bold;
                padding-left: 10px;
                background-color: transparent;
            }
            QToolBar::separator {
                width: 1px;
                background-color: #334155;
                margin-top: 4px;
                margin-bottom: 4px;
                margin-left: 6px;
                margin-right: 6px;
            }
            """
        else:
            # 系统浅色模式下，Matplotlib 加载的 symbolic 图标为深色，需要浅色底工具栏背景
            style = """
            QToolBar {
                background-color: #F8FAFC;
                border: none;
                border-bottom: 1px solid #E2E8F0;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QToolBar QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
                margin: 2px;
            }
            QToolBar QToolButton:hover {
                background-color: #E2E8F0;
            }
            QToolBar QToolButton:pressed {
                background-color: #CBD5E1;
            }
            QToolBar QToolButton:disabled {
                background-color: transparent;
                opacity: 0.5;
            }
            QToolBar QLabel {
                color: #475569;
                font-size: 11px;
                font-weight: bold;
                padding-left: 10px;
                background-color: transparent;
            }
            QToolBar::separator {
                width: 1px;
                background-color: #E2E8F0;
                margin-top: 4px;
                margin-bottom: 4px;
                margin-left: 6px;
                margin-right: 6px;
            }
            """

        for attr in ['toolbar_scatter', 'toolbar_status', 'toolbar_epoch_h', 'toolbar_epoch_v', 'toolbar_trajectory']:
            if hasattr(self, attr):
                getattr(self, attr).setStyleSheet(style)

    def changeEvent(self, event):
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.ThemeChange):
            self.update_toolbar_styles()
        super().changeEvent(event)


    # 4. 参考位置模式切换控制
    def set_ref_mode_auto(self):
        self.truth_mode = 'auto'
        self.btn_ref_auto.setProperty("active", True)
        self.btn_ref_manual.setProperty("active", False)
        self.btn_ref_dynamic.setProperty("active", False)
        self.btn_ref_auto.style().unpolish(self.btn_ref_auto)
        self.btn_ref_auto.style().polish(self.btn_ref_auto)
        self.btn_ref_manual.style().unpolish(self.btn_ref_manual)
        self.btn_ref_manual.style().polish(self.btn_ref_manual)
        self.btn_ref_dynamic.style().unpolish(self.btn_ref_dynamic)
        self.btn_ref_dynamic.style().polish(self.btn_ref_dynamic)
        
        self.inputs_widget.show()
        self.dynamic_widget.hide()
        
        self.txt_lat.setDisabled(True)
        self.txt_lon.setDisabled(True)
        self.txt_alt.setDisabled(True)
        self.txt_ref_name.setDisabled(True)
        self.cmb_history.setDisabled(True)
        self.set_avg_point_as_truth()
        self.save_config()

    def set_ref_mode_manual(self):
        self.truth_mode = 'manual'
        self.btn_ref_auto.setProperty("active", False)
        self.btn_ref_manual.setProperty("active", True)
        self.btn_ref_dynamic.setProperty("active", False)
        self.btn_ref_auto.style().unpolish(self.btn_ref_auto)
        self.btn_ref_auto.style().polish(self.btn_ref_auto)
        self.btn_ref_manual.style().unpolish(self.btn_ref_manual)
        self.btn_ref_manual.style().polish(self.btn_ref_manual)
        self.btn_ref_dynamic.style().unpolish(self.btn_ref_dynamic)
        self.btn_ref_dynamic.style().polish(self.btn_ref_dynamic)
        
        self.inputs_widget.show()
        self.dynamic_widget.hide()
        
        self.txt_lat.setEnabled(True)
        self.txt_lon.setEnabled(True)
        self.txt_alt.setEnabled(True)
        self.txt_ref_name.setEnabled(True)
        self.cmb_history.setEnabled(True)
        self.on_manual_truth_changed()

    def set_ref_mode_dynamic(self):
        self.truth_mode = 'dynamic'
        self.truth['mode'] = 'dynamic'
        self.btn_ref_auto.setProperty("active", False)
        self.btn_ref_manual.setProperty("active", False)
        self.btn_ref_dynamic.setProperty("active", True)
        self.btn_ref_auto.style().unpolish(self.btn_ref_auto)
        self.btn_ref_auto.style().polish(self.btn_ref_auto)
        self.btn_ref_manual.style().unpolish(self.btn_ref_manual)
        self.btn_ref_manual.style().polish(self.btn_ref_manual)
        self.btn_ref_dynamic.style().unpolish(self.btn_ref_dynamic)
        self.btn_ref_dynamic.style().polish(self.btn_ref_dynamic)
        
        self.inputs_widget.hide()
        self.dynamic_widget.show()
        
        self.recompute_all()
        self.save_config()

    def on_load_dynamic_clicked(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "选择真值文件", "", "All Files (*)")
        if not filepath:
            return
            
        self.lbl_dynamic_file.setText(f"正在加载:\n{os.path.basename(filepath)}")
        
        leap_secs = self.get_leap_seconds()
        strict = self.app_config.get('strict_nmea_checksum', False)
        
        self.dynamic_parser_thread = LogParserThread(filepath, leap_secs, strict, self)
        self.dynamic_parser_thread.finished_parsing.connect(lambda res: self.on_dynamic_parse_finished(res, filepath))
        self.dynamic_parser_thread.error_occurred.connect(self.on_dynamic_parse_error)
        self.dynamic_parser_thread.start()

    def on_dynamic_parse_error(self, err_msg):
        QMessageBox.critical(self, "解析错误", f"动态真值文件解析失败: {err_msg}")
        self.lbl_dynamic_file.setText("加载失败")
        self.truth['epochs'] = None
        self.recompute_all()

    def on_dynamic_parse_finished(self, result, filepath):
        file_epochs = result['file_epochs']
        if not file_epochs:
            QMessageBox.warning(self, "警告", "未能在文件中提取到有效的 GGA/RMC 轨迹数据！")
            self.lbl_dynamic_file.setText("未加载有效的真值文件")
            self.truth['epochs'] = None
            self.recompute_all()
            return
            
        # 去重：优先保留 GGA 语句，因为 GGA 包含高度和更详细的质量状态信息
        best_epochs = {}
        for ep in file_epochs:
            t = ep['utc_time_sec']
            if t not in best_epochs:
                best_epochs[t] = ep
            else:
                # 若已存在且为 RMC，新来的是 GGA 时，进行替换
                if best_epochs[t]['type'] == 'RMC' and ep['type'] == 'GGA':
                    best_epochs[t] = ep
                    
        # 按时间排序转回列表
        dedup_epochs = [best_epochs[t] for t in sorted(best_epochs.keys())]
            
        self.truth['mode'] = 'dynamic'
        self.truth['file_id'] = filepath
        self.truth['epochs'] = dedup_epochs
        
        self.lbl_dynamic_file.setText(f"真值加载成功 ({len(dedup_epochs)}个点):\n{os.path.basename(filepath)}")
        self.btn_clear_dynamic.setEnabled(True)
        self.recompute_all()
        self.save_config()

    def on_clear_dynamic_clicked(self):
        self.truth['epochs'] = None
        self.truth['file_id'] = None
        self.lbl_dynamic_file.setText("未加载动态真值文件")
        self.btn_clear_dynamic.setEnabled(False)
        self.recompute_all()
        self.save_config()

    def on_manual_truth_changed(self):
        if self.truth_mode == 'manual':
            try:
                lat = float(self.txt_lat.text())
                lon = float(self.txt_lon.text())
                alt = float(self.txt_alt.text())
                name = self.txt_ref_name.text().strip()
                
                self.truth['lat'] = lat
                self.truth['lon'] = lon
                self.truth['alt'] = alt
                
                # 记录有效坐标到历史中，会自动更新下拉框并保存配置
                self.add_coordinate_to_history(lat, lon, alt, name)
                self.recompute_all()
            except ValueError:
                QMessageBox.warning(self, "输入错误", "请输入合法的经度、纬度或高程数值。")
    def cancel_parsing(self):
        self.pending_parse_queue.clear()
        if hasattr(self, 'parser_thread') and self.parser_thread:
            self.parser_thread.is_cancelled = True
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()

    def on_import_clicked(self):
        filepaths, _ = QFileDialog.getOpenFileNames(self, "导入定位原始日志", "", "All Files (*.*);;GNSS Logs (*.log *.txt *.nmea *.dat)")
        if not filepaths:
            return
            
        # Check Busy Guard
        if (hasattr(self, 'parser_thread') and self.parser_thread and self.parser_thread.isRunning()) or \
           (hasattr(self, 'dynamic_parser_thread') and self.dynamic_parser_thread and self.dynamic_parser_thread.isRunning()):
            QMessageBox.warning(self, "系统繁忙", "当前后台正有数据解析线程运行，请等待当前文件导入完成后再试。")
            return
            
        self.import_multiple_files(filepaths)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        filepaths = []
        for url in urls:
            local_path = url.toLocalFile()
            if local_path and os.path.isfile(local_path):
                filepaths.append(local_path)
                
        if not filepaths:
            return
            
        # Check Busy Guard
        if (hasattr(self, 'parser_thread') and self.parser_thread and self.parser_thread.isRunning()) or \
           (hasattr(self, 'dynamic_parser_thread') and self.dynamic_parser_thread and self.dynamic_parser_thread.isRunning()):
            QMessageBox.warning(self, "系统繁忙", "当前后台正有数据解析线程运行，请等待当前文件导入完成后再试。")
            return
            
        self.import_multiple_files(filepaths)

    def import_multiple_files(self, filepaths):
        self.pending_parse_queue = list(filepaths)
        self.total_queue_count = len(filepaths)
        
        if not self.pending_parse_queue:
            return
            
        self.progress_dialog = QProgressDialog("正在准备解析文件...", "取消", 0, 100, self)
        self.progress_dialog.setWindowTitle("导入日志")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)
        self.progress_dialog.canceled.connect(self.cancel_parsing)
        
        self.start_next_queued_parse()

    def start_next_queued_parse(self):
        if not self.pending_parse_queue:
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.close()
            return
            
        filepath = self.pending_parse_queue.pop(0)
        current_idx = self.total_queue_count - len(self.pending_parse_queue)
        
        self.lbl_status.setText(f"正在读取 ({current_idx}/{self.total_queue_count}): {os.path.basename(filepath)}")
        
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setLabelText(f"正在读取并解析 ({current_idx}/{self.total_queue_count}):\n{os.path.basename(filepath)}")
            self.progress_dialog.setValue(0)
            
        leap_secs = self.get_leap_seconds()
        strict = self.app_config.get('strict_nmea_checksum', False)
        
        self.parser_thread = LogParserThread(filepath, leap_secs, strict, self)
        self.parser_thread.progress_updated.connect(self.progress_dialog.setValue)
        self.parser_thread.finished_parsing.connect(lambda res: self.on_parse_finished(res, filepath))
        self.parser_thread.error_occurred.connect(self.on_parse_error)
        
        self.parser_thread.start()

    def on_parse_error(self, err_msg):
        self.pending_parse_queue.clear()
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        QMessageBox.critical(self, "读取错误", f"解析失败: {err_msg}")
        self.lbl_status.setText("导入失败")

    def on_parse_finished(self, result, filepath):
        if hasattr(self, 'parser_thread') and self.parser_thread and self.parser_thread.is_cancelled:
            return
            
        file_epochs = result['file_epochs']
        first_time_sec = result['first_time_sec']
        last_time_sec = result['last_time_sec']
        first_time_str = result['first_time_str']
        last_time_str = result['last_time_str']
        
        for stype, count in result['sentence_types'].items():
            self.sentence_types[stype] = self.sentence_types.get(stype, 0) + count
            
        if not file_epochs:
            QMessageBox.warning(self, "警告", f"文件 {os.path.basename(filepath)} 中未检测到任何有效的定位语句（$GNGGA、$POGOS 或 $PODRS）！")
            self.lbl_status.setText("导入失败：无有效定位数据")
            if self.pending_parse_queue:
                self.start_next_queued_parse()
            else:
                if hasattr(self, 'progress_dialog') and self.progress_dialog:
                    self.progress_dialog.close()
            return
            
        # Remove old epochs of this file from the global list to prevent duplicates
        self.parsed_epochs = [ep for ep in self.parsed_epochs if ep.get('file_id') != filepath]
        
        # Remove old segments associated with this file from both the list and the UI list widget safely
        seg_ids_to_remove = [s['id'] for s in self.segments if s.get('file_id') == filepath]
        for seg_id in seg_ids_to_remove:
            self.segments = [s for s in self.segments if s['id'] != seg_id]
            i = 0
            while i < self.list_segments.count():
                item = self.list_segments.item(i)
                widget = self.list_segments.itemWidget(item)
                if isinstance(widget, SegmentListItemWidget) and widget.seg_id == seg_id:
                    self.list_segments.takeItem(i)
                    continue
                i += 1

        self.parsed_epochs.extend(file_epochs)
        self.parsed_epochs.sort(key=lambda x: x['utc_time_sec'])
        self.file_epochs_map[filepath] = []
        self.file_epochs_map[filepath].extend(file_epochs)
        
        # 为了后面的 bisect 二分查找，必须保证 file_epochs 是按时间严格递增的
        self.file_epochs_map[filepath].sort(key=lambda x: x['utc_time_sec'])
        
        # 更新默认起止范围 (合并多文件的范围)
        if self.time_range['start'] == 0 or first_time_sec < self.time_range['start']:
            self.time_range['start'] = first_time_sec
            self.first_time_str = first_time_str
        if self.time_range['end'] == 0 or last_time_sec > self.time_range['end']:
            self.time_range['end'] = last_time_sec
            self.last_time_str = last_time_str
        self.lbl_status.setText(f"已导入: {os.path.basename(filepath)}")
        
        # 为导入的新文件自动添加一个分析时段，名称设为文件名
        filename_clean = os.path.splitext(os.path.basename(filepath))[0]
        self.add_segment_item(filename_clean, first_time_str, last_time_str, file_id=filepath)
        
        if self.truth_mode == 'auto':
            self.set_avg_point_as_truth()
        else:
            self.recompute_all()
            
        if self.pending_parse_queue:
            self.start_next_queued_parse()
        else:
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.close()

    def on_add_segment_clicked(self):
        if not self.parsed_epochs:
            QMessageBox.warning(self, "提示", "请先导入原始日志数据！")
            return
        
        # 默认使用最后一个时段的 file_id，如果没有，使用最后一个解析历元的 file_id
        last_file_id = self.segments[-1]['file_id'] if self.segments else self.parsed_epochs[-1]['file_id']
        file_epochs = [ep for ep in self.parsed_epochs if ep.get('file_id') == last_file_id]
        
        start_str = file_epochs[0]['time_str'] if file_epochs else self.first_time_str
        end_str = file_epochs[-1]['time_str'] if file_epochs else self.last_time_str
        
        self.add_segment_item(f"ID_{self.segment_counter + 1}", start_str, end_str, file_id=last_file_id)

    def set_avg_point_as_truth(self):
        if not self.parsed_epochs:
            return
        
        # 智能过滤：如果文件中存在标准 GGA 定位数据，优先仅用 GGA 计算参考平均值
        # 只有在完全没有标准 GGA 时，才平均私有 POGOS 数据，防止坐标系偏差导致真值漂移
        gga_epochs = [p for p in self.parsed_epochs if p['type'] == 'GGA']
        target_epochs = gga_epochs if gga_epochs else self.parsed_epochs
        
        sum_lat = sum(p['lat'] for p in target_epochs)
        sum_lon = sum(p['lon'] for p in target_epochs)
        sum_alt = sum(p['alt'] for p in target_epochs)
        n = len(target_epochs)
        if n == 0:
            self.truth['lat'] = 0.0
            self.truth['lon'] = 0.0
            self.truth['alt'] = 0.0
        else:
            self.truth['lat'] = sum_lat / n
            self.truth['lon'] = sum_lon / n
            self.truth['alt'] = sum_alt / n
        
        self.txt_lat.setText(f"{self.truth['lat']:.8f}")
        self.txt_lon.setText(f"{self.truth['lon']:.8f}")
        self.txt_alt.setText(f"{self.truth['alt']:.3f}")
        self.recompute_all()

    # 6. 分段时段管理与交互
    def add_segment_item(self, name, start_time, end_time, file_id=None):
        if not self.parsed_epochs:
            return
            
        seg_id = self.segment_counter
        self.segment_counter += 1
        
        if not file_id and self.segments:
            file_id = self.segments[-1]['file_id']
        elif not file_id:
            file_id = self.parsed_epochs[-1]['file_id']
            
        # 根据分段关联的具体 file_id 的历元类型判断其支持的协议数据源
        file_epochs = [ep for ep in self.parsed_epochs if ep.get('file_id') == file_id]
        has_gga = any(ep['type'] == 'GGA' for ep in file_epochs)
        has_pogos = any(ep['type'] == 'POGOS' for ep in file_epochs)
        has_podrs = any(ep['type'] == 'PODRS' for ep in file_epochs)
        if has_gga:
            default_src = 'GGA'
        elif has_pogos:
            default_src = 'POGOS'
        else:
            default_src = 'PODRS'
        
        # 寻找目前未被使用的颜色，避免颜色重复
        color = None
        used_colors = {s['color'].upper() for s in self.segments}
        for candidate in self.default_colors:
            if candidate.upper() not in used_colors:
                color = candidate
                break
        if not color:
            color = self.default_colors[seg_id % len(self.default_colors)]
        
        seg = {
            'id': seg_id,
            'name': name,
            'start_time': start_time,
            'end_time': end_time,
            'source_type': default_src,
            'color': color,
            'active': True,
            'metrics': None,
            'epochs': [],
            'file_id': file_id  # 关联的具体文件标志
        }
        self.segments.append(seg)
        
        display_start = self.get_display_time(start_time)
        display_end = self.get_display_time(end_time)
        item_widget = SegmentListItemWidget(seg_id, name, display_start, display_end, default_src, color, has_gga, has_pogos, has_podrs)
        
        item_widget.active_toggled.connect(self.on_seg_active_toggled)
        item_widget.name_changed.connect(self.on_seg_name_changed)
        item_widget.color_changed.connect(self.on_seg_color_changed)
        item_widget.time_changed.connect(self.on_seg_time_changed)
        item_widget.source_changed.connect(self.on_seg_source_changed)
        item_widget.delete_clicked.connect(self.on_seg_delete_clicked)
        
        list_item = QListWidgetItem(self.list_segments)
        list_item.setSizeHint(item_widget.sizeHint())
        self.list_segments.addItem(list_item)
        self.list_segments.setItemWidget(list_item, item_widget)
        
        self.recompute_all()

    def on_seg_active_toggled(self, seg_id, is_active):
        for s in self.segments:
            if s['id'] == seg_id:
                s['active'] = is_active
                break
        self.recompute_all()

    def on_seg_name_changed(self, seg_id, new_name):
        for s in self.segments:
            if s['id'] == seg_id:
                s['name'] = new_name
                break
        self.update_metrics_table()
        self.refresh_chart()

    def on_seg_color_changed(self, seg_id, color_hex):
        for s in self.segments:
            if s['id'] == seg_id:
                s['color'] = color_hex
                break
        self.recompute_all()

    def on_seg_time_changed(self, seg_id, start_str, end_str):
        for s in self.segments:
            if s['id'] == seg_id:
                s['start_time'] = self.get_utc_time(start_str)
                s['end_time'] = self.get_utc_time(end_str)
                break
        self.recompute_all()

    def on_timezone_changed(self, text):
        if "北京时间" in text:
            self.time_zone = 'Beijing'
        else:
            self.time_zone = 'UTC'
        self.save_config()
            
        for i in range(self.list_segments.count()):
            item = self.list_segments.item(i)
            widget = self.list_segments.itemWidget(item)
            if isinstance(widget, SegmentListItemWidget):
                seg_id = widget.seg_id
                seg = next((s for s in self.segments if s['id'] == seg_id), None)
                if seg:
                    display_start = self.get_display_time(seg['start_time'])
                    display_end = self.get_display_time(seg['end_time'])
                    widget.set_times(display_start, display_end)
        self.refresh_chart()

    def on_alt_mode_changed(self, state):
        if not hasattr(self, 'canvas_epoch_v') or self.canvas_epoch_v is None:
            return
        self.show_absolute_alt = self.cb_abs_alt.isChecked()
        self.refresh_chart()
        self.save_config()

    def on_raw_alt_changed(self, state):
        if not hasattr(self, 'canvas_epoch_v') or self.canvas_epoch_v is None:
            return
        self.show_raw_alt = self.cb_raw_alt.isChecked()
        self.refresh_chart()
        self.save_config()

    def on_extrema_mode_changed(self, state):
        if not hasattr(self, 'canvas_epoch_v') or self.canvas_epoch_v is None:
            return
        self.show_extrema = self.cb_show_extrema.isChecked()
        self.refresh_chart()
        self.save_config()

    def on_show_sats_changed(self, state):
        if not hasattr(self, 'canvas_epoch_v') or self.canvas_epoch_v is None:
            return
        self.refresh_chart()

    def on_xaxis_changed(self, text):
        self.x_axis_mode = text
        
        # 容错校验：若多个分段起止时间跨度过大（如超过4小时且实际数据稀疏），自动切换回历元数以防折线图被压缩成极细线条
        if self.x_axis_mode == "时间轴" and self.segments:
            active_segs = [s for s in self.segments if s.get('active') and s.get('epochs')]
            if len(active_segs) > 1:
                try:
                    min_sec = min(time_str_to_seconds(s['start_time']) for s in active_segs)
                    max_sec = max(time_str_to_seconds(s['end_time']) for s in active_segs)
                    total_span = max_sec - min_sec
                    sum_duration = sum(time_str_to_seconds(s['end_time']) - time_str_to_seconds(s['start_time']) for s in active_segs)
                    
                    if total_span > 14400 and (sum_duration / total_span) < 0.15:
                        QMessageBox.warning(self, "时间轴对齐警告", 
                                            "当前启用的多个分析分段起止时间相差过大（超过 4 小时）且互不连续。\n\n"
                                            "若强行使用时间轴对齐，曲线将被极度压缩。已自动帮您切换回「历元数」模式。")
                        self.cmb_xaxis.blockSignals(True)
                        self.cmb_xaxis.setCurrentText("历元数")
                        self.cmb_xaxis.blockSignals(False)
                        self.x_axis_mode = "历元数"
                except Exception:
                    pass
                    
        self.refresh_chart()
        self.save_config()

    def on_settings_clicked(self):
        if not hasattr(self, 'app_config'):
            self.app_config = {}
        dialog = SettingsDialog(self.app_config, self)
        if dialog.exec():
            new_settings = dialog.get_settings()
            self.app_config.update(new_settings)
            self.apply_new_settings()
            self.save_config()

    def apply_new_settings(self):
        thresh = self.app_config.get('downsample_threshold', 100000)
        self.canvas_scatter.downsample_threshold = thresh
        self.canvas_status.downsample_threshold = thresh
        self.canvas_epoch_h.downsample_threshold = thresh
        self.canvas_epoch_v.downsample_threshold = thresh
        self.canvas_trajectory.downsample_threshold = thresh
        
        dpi = self.app_config.get('export_dpi', 150)
        self.canvas_scatter.export_dpi = dpi
        self.canvas_status.export_dpi = dpi
        self.canvas_epoch_h.export_dpi = dpi
        self.canvas_epoch_v.export_dpi = dpi
        self.canvas_trajectory.export_dpi = dpi
        
        self.recompute_all()

    # --- 配置存储与坐标历史管理逻辑 ---
    def load_config(self):
        CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vcom_config.json")
        self.coordinate_history = []
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.app_config = json.load(f)
                
                # 读取配置
                self.time_zone = self.app_config.get("time_zone", "UTC")
                self.show_absolute_alt = self.app_config.get("show_absolute_alt", False)
                self.show_raw_alt = self.app_config.get("show_raw_alt", False)
                self.show_extrema = self.app_config.get("show_extrema", True)
                self.x_axis_mode = self.app_config.get("x_axis_mode", "历元数")
                self.truth_mode = self.app_config.get("truth_mode", "auto")
                
                # 坐标历史
                self.coordinate_history = self.app_config.get("coordinate_history", [])
                
                # 应用配置到UI
                if self.time_zone == 'Beijing':
                    self.cmb_timezone.setCurrentText("北京时间 (UTC+8)")
                else:
                    self.cmb_timezone.setCurrentText("UTC 时间")
                    
                self.cb_abs_alt.setChecked(self.show_absolute_alt)
                self.cb_raw_alt.setChecked(self.show_raw_alt)
                self.cb_show_extrema.setChecked(self.show_extrema)
                self.cmb_xaxis.setCurrentText(self.x_axis_mode)
                
                # 填充坐标下拉框
                self.update_history_combo()
                
                if self.truth_mode == 'manual':
                    # 如果上次是手动模式，填入最新历史坐标或默认值
                    self.set_ref_mode_manual()
                    if self.coordinate_history:
                        latest = self.coordinate_history[0]
                        self.txt_ref_name.setText(latest.get('name', ''))
                        self.txt_lat.setText(f"{latest['lat']:.8f}")
                        self.txt_lon.setText(f"{latest['lon']:.8f}")
                        self.txt_alt.setText(f"{latest['alt']:.3f}")
                        self.truth = latest.copy()
                else:
                    self.set_ref_mode_auto()
                    
                # 闰秒
                leap = self.app_config.get("leap_seconds", 18)
                self.txt_leap.setText(str(leap))
                
            except Exception as e:
                print(f"读取配置出错: {e}")
        else:
            # 默认配置
            self.set_ref_mode_auto()
            self.update_history_combo()
            
    def save_config(self):
        CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vcom_config.json")
        self.app_config.update({
            "time_zone": self.time_zone,
            "show_absolute_alt": self.show_absolute_alt,
            "show_raw_alt": self.show_raw_alt,
            "show_extrema": self.show_extrema,
            "x_axis_mode": self.x_axis_mode,
            "truth_mode": self.truth_mode,
            "leap_seconds": self.get_leap_seconds(),
            "coordinate_history": self.coordinate_history
        })
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.app_config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置出错: {e}")

    def add_coordinate_to_history(self, lat, lon, alt, name=""):
        # 查找是否已存在相同坐标（微小误差阈值内判为相同）
        exist_idx = -1
        for i, item in enumerate(self.coordinate_history):
            if abs(item['lat'] - lat) < 1e-8 and abs(item['lon'] - lon) < 1e-8 and abs(item['alt'] - alt) < 1e-3:
                exist_idx = i
                break
                
        coord = {"lat": lat, "lon": lon, "alt": alt, "name": name}
        if exist_idx != -1:
            if not name and 'name' in self.coordinate_history[exist_idx] and self.coordinate_history[exist_idx]['name']:
                coord['name'] = self.coordinate_history[exist_idx]['name']
            self.coordinate_history.pop(exist_idx)
        self.coordinate_history.insert(0, coord)
        
        # 限制个数为 10
        self.coordinate_history = self.coordinate_history[:10]
        
        # 更新下拉框并保存
        self.update_history_combo()
        self.save_config()

    def update_history_combo(self):
        # 阻止信号触发选择改变回调，防止死循环
        self.cmb_history.blockSignals(True)
        self.cmb_history.clear()
        self.cmb_history.addItem("--- 选择历史输入坐标 ---")
        for item in self.coordinate_history:
            name_str = f"[{item['name']}] " if item.get('name') else ""
            self.cmb_history.addItem(f"{name_str}纬:{item['lat']:.8f}, 经:{item['lon']:.8f}, 高:{item['alt']:.3f}")
        self.cmb_history.blockSignals(False)

    def on_history_coordinate_selected(self, index):
        if index <= 0 or not self.coordinate_history:
            return
        # 下拉框第0个元素是提示，真实坐标索引为 index - 1
        coord = self.coordinate_history[index - 1]
        self.txt_ref_name.setText(coord.get('name', ''))
        self.txt_lat.setText(f"{coord['lat']:.8f}")
        self.txt_lon.setText(f"{coord['lon']:.8f}")
        self.txt_alt.setText(f"{coord['alt']:.3f}")
        
        self.truth['lat'] = coord['lat']
        self.truth['lon'] = coord['lon']
        self.truth['alt'] = coord['alt']
        self.recompute_all()
        
        # 联动将所选坐标提到历史最前
        self.add_coordinate_to_history(coord['lat'], coord['lon'], coord['alt'], coord.get('name', ''))

    def get_display_time(self, utc_time_str):
        """将内部存储的 UTC 时间字符串转为当前应显示的时间字符串"""
        if self.time_zone == 'Beijing':
            try:
                parts = utc_time_str.split(':')
                h = int(parts[0])
                m = int(parts[1])
                s_part = parts[2]
                if '.' in s_part:
                    s_val = float(s_part)
                else:
                    s_val = int(s_part)
                h = (h + 8) % 24
                if isinstance(s_val, float):
                    return f"{h:02d}:{m:02d}:{s_val:05.2f}"
                else:
                    return f"{h:02d}:{m:02d}:{s_val:02d}"
            except Exception:
                return utc_time_str
        return utc_time_str

    def get_utc_time(self, display_time_str):
        """将当前编辑框显示的时间字符串转为内部存储的 UTC 时间字符串"""
        if self.time_zone == 'Beijing':
            try:
                parts = display_time_str.split(':')
                h = int(parts[0])
                m = int(parts[1])
                s_part = parts[2]
                if '.' in s_part:
                    s_val = float(s_part)
                else:
                    s_val = int(s_part)
                h = (h - 8 + 24) % 24
                if isinstance(s_val, float):
                    return f"{h:02d}:{m:02d}:{s_val:05.2f}"
                else:
                    return f"{h:02d}:{m:02d}:{s_val:02d}"
            except Exception:
                return display_time_str
        return display_time_str

    def on_seg_source_changed(self, seg_id, src_type):
        for s in self.segments:
            if s['id'] == seg_id:
                s['source_type'] = src_type
                break
        self.recompute_all()

    def on_seg_delete_clicked(self, seg_id):
        self.segments = [s for s in self.segments if s['id'] != seg_id]
        
        for i in range(self.list_segments.count()):
            item = self.list_segments.item(i)
            widget = self.list_segments.itemWidget(item)
            if isinstance(widget, SegmentListItemWidget) and widget.seg_id == seg_id:
                self.list_segments.takeItem(i)
                break
        self.recompute_all()

    # 7. 全局重算与渲染联动
    def check_xaxis_mode_availability(self):
        if not self.segments:
            model = self.cmb_xaxis.model()
            if model:
                item = model.item(1)
                if item:
                    item.setEnabled(True)
            return True
            
        active_segs = [s for s in self.segments if s.get('active') and s.get('epochs')]
        if len(active_segs) <= 1:
            model = self.cmb_xaxis.model()
            if model:
                item = model.item(1)
                if item:
                    item.setEnabled(True)
            return True
            
        try:
            segs_time = []
            for s in active_segs:
                t_start = time_str_to_seconds(s['start_time'])
                t_end = time_str_to_seconds(s['end_time'])
                segs_time.append((t_start, t_end))
            
            segs_time.sort(key=lambda x: x[0])
            
            # 检查是否有严重的时间不同步：空隙大于 1.5 小时 (5400 秒) 或者总跨度超过 4 小时 (14400 秒)
            has_gap = False
            for i in range(len(segs_time) - 1):
                gap = segs_time[i+1][0] - segs_time[i][1]
                if gap > 5400:
                    has_gap = True
                    break
            
            min_sec = segs_time[0][0]
            max_sec = max(st[1] for st in segs_time)
            if max_sec - min_sec > 14400:
                has_gap = True
                
            model = self.cmb_xaxis.model()
            if model:
                item = model.item(1)
                if item:
                    if has_gap:
                        item.setEnabled(False) # 禁用下拉列表中的“时间轴”
                        if self.cmb_xaxis.currentText() == "时间轴":
                            QMessageBox.warning(self, "X轴对齐限制", 
                                                "检测到启用的多个分段之间录制时间不一致且存在大跨度空隙（或超过4小时）。\n"
                                                "如果使用时间轴，图表曲线将被极度压缩。已自动为您切换为「历元数」模式。")
                            self.cmb_xaxis.blockSignals(True)
                            self.cmb_xaxis.setCurrentText("历元数")
                            self.cmb_xaxis.blockSignals(False)
                            self.x_axis_mode = "历元数"
                    else:
                        item.setEnabled(True)
        except Exception:
            pass
            
        return True

    def recompute_all(self):
        if not self.parsed_epochs:
            return
            
        def find_epoch_range(epochs, start_sec, end_sec):
            left, right = 0, len(epochs)
            while left < right:
                mid = (left + right) // 2
                if epochs[mid]['utc_time_sec'] < start_sec:
                    left = mid + 1
                else:
                    right = mid
            start_idx = left
            
            left, right = start_idx, len(epochs)
            while left < right:
                mid = (left + right) // 2
                if epochs[mid]['utc_time_sec'] <= end_sec:
                    left = mid + 1
                else:
                    right = mid
            return epochs[start_idx:left]
            
        for seg in self.segments:
            start_sec = time_str_to_seconds(seg['start_time'])
            end_sec = time_str_to_seconds(seg['end_time'])
            
            # 使用基于 file_id 的字典查询代替遍历数十万级别的全集列表
            file_epochs = self.file_epochs_map.get(seg.get('file_id'), [])
            
            # 使用二分查找 O(log N) 获取时间区间内的历元
            range_epochs = find_epoch_range(file_epochs, start_sec, end_sec)
            seg['epochs'] = [ep for ep in range_epochs if ep['type'] == seg['source_type']]
            
            dynamic_truth_array = None
            if self.truth_mode == 'auto':
                if seg['epochs']:
                    seg_truth = {
                        'lat': sum(p['lat'] for p in seg['epochs']) / len(seg['epochs']),
                        'lon': sum(p['lon'] for p in seg['epochs']) / len(seg['epochs']),
                        'alt': sum(p['alt'] for p in seg['epochs']) / len(seg['epochs'])
                    }
                else:
                    seg_truth = self.truth
            elif self.truth_mode == 'dynamic':
                seg_truth = self.truth
                if self.truth.get('epochs') and seg['epochs']:
                    dynamic_truth_array = interpolate_dynamic_truth(seg['epochs'], self.truth['epochs'])
                if not dynamic_truth_array:
                    QMessageBox.warning(self, "动态真值错误", f"分段 [{seg['name']}] 与动态真值时间无交集，无法完成指标计算。")
                    seg['epochs'] = []
                    seg['metrics'] = None
                    continue
            else:
                seg_truth = self.truth
            
            metrics, filtered_epochs = calculate_metrics(
                seg['epochs'], seg_truth,
                filter_outliers=self.app_config.get('filter_outliers', False),
                outlier_thresh=self.app_config.get('outlier_threshold', 50.0),
                dynamic_truth_array=dynamic_truth_array
            )
            seg['epochs'] = filtered_epochs
            seg['metrics'] = metrics
            
        # 联动检查X轴时间可用性并自动禁用
        self.check_xaxis_mode_availability()
        self.update_metrics_table()
        self.refresh_chart()

    def update_metrics_table(self):
        self.table_metrics.setRowCount(0)
        for seg in self.segments:
            m = seg['metrics']
            if not m:
                continue
                
            row = self.table_metrics.rowCount()
            self.table_metrics.insertRow(row)
            
            item_id = QTableWidgetItem(seg['name'])
            item_id.setForeground(QColor(seg['color']))
            
            align_rate = 100.0
            if m.get('original_count', 0) > 0:
                align_rate = (m['count'] / m['original_count']) * 100.0
                
            self.table_metrics.setItem(row, 0, item_id)
            self.table_metrics.setItem(row, 1, QTableWidgetItem(f"{align_rate:.1f}%"))
            self.table_metrics.setItem(row, 2, QTableWidgetItem(str(m['count'])))
            self.table_metrics.setItem(row, 3, QTableWidgetItem(f"{m['rtk_fix_rate']:.1f}%"))
            self.table_metrics.setItem(row, 4, QTableWidgetItem(f"{m['cep50']:.3f}"))
            self.table_metrics.setItem(row, 5, QTableWidgetItem(f"{m['cep68']:.3f}"))
            self.table_metrics.setItem(row, 6, QTableWidgetItem(f"{m['cep95']:.3f}"))
            self.table_metrics.setItem(row, 7, QTableWidgetItem(f"{m['rms_h']:.3f}"))
            self.table_metrics.setItem(row, 8, QTableWidgetItem(f"{m['rms_v']:.3f}"))
            self.table_metrics.setItem(row, 9, QTableWidgetItem(f"{m['max_h']:.3f}"))
            self.table_metrics.setItem(row, 10, QTableWidgetItem(f"{m['max_v']:.3f}"))

    def on_tab_changed(self, index):
        self.refresh_chart()

    def refresh_chart(self):
        index = self.tab_widget.currentIndex()
        if index == 0:
            self.canvas_scatter.render_data('scatter', self.segments, self.truth, self.time_zone)
        elif index == 1:
            self.canvas_epoch_h.render_data('epoch_h', self.segments, self.truth, self.time_zone, show_extrema=self.show_extrema, x_axis_mode=self.x_axis_mode, show_sats=self.cb_show_sats.isChecked())
        elif index == 2:
            self.canvas_epoch_v.render_data('epoch_v', self.segments, self.truth, self.time_zone, self.show_absolute_alt, show_extrema=self.show_extrema, x_axis_mode=self.x_axis_mode, show_sats=self.cb_show_sats.isChecked(), show_raw_alt=self.show_raw_alt)
        elif index == 3:
            self.canvas_status.render_data('status', self.segments, self.truth, self.time_zone)
        elif index == 4:
            self.canvas_trajectory.render_data('trajectory', self.segments, self.truth)

    # 8. 导出数据逻辑
    def on_export_raw_clicked(self):
        if not self.segments:
            return
            
        active_segs = [s for s in self.segments if s['active']]
        if not active_segs:
            QMessageBox.warning(self, "提示", "请在列表中勾选要导出的活跃分段。")
            return
            
        target_seg = active_segs[0]
        export_mode = self.app_config.get('export_dir_mode', '同源文件目录')
        default_dir = ""
        if export_mode == "记忆上次目录":
            default_dir = self.app_config.get('last_export_dir', "")
        if not default_dir and target_seg.get('file_id'):
            default_dir = os.path.dirname(target_seg['file_id'])
            
        default_path = os.path.join(default_dir, f"sliced_{target_seg['name']}.log")
        save_path, _ = QFileDialog.getSaveFileName(self, "导出截取原始数据", default_path, "GNSS Logs (*.log *.txt)")
        if not save_path:
            return
            
        if export_mode == "记忆上次目录":
            self.app_config['last_export_dir'] = os.path.dirname(save_path)
            self.save_config()
            
        start_sec = time_str_to_seconds(target_seg['start_time'])
        end_sec = time_str_to_seconds(target_seg['end_time'])
        leap_secs = self.get_leap_seconds()
        
        try:
            file_size = os.path.getsize(target_seg['file_id'])
            processed = 0
            
            from PySide6.QtWidgets import QProgressDialog, QApplication
            progress = QProgressDialog("正在导出原始数据...", "取消", 0, 100, self)
            progress.setWindowTitle("导出进度")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            with open(target_seg['file_id'], 'r', encoding='utf-8', errors='ignore') as f_in, \
                 open(save_path, 'w', encoding='utf-8') as f_out:
                for line in f_in:
                    if progress.wasCanceled():
                        break
                        
                    processed += len(line.encode('utf-8', errors='ignore'))
                    if processed % (1024 * 50) < 100:  # ~50KB update
                        pct = int((processed / file_size) * 100) if file_size > 0 else 0
                        progress.setValue(pct)
                        QApplication.processEvents()
                        
                    if not line.startswith('$'):
                        continue
                        
                    parts = line.strip().split(',')
                    stype = parts[0]
                    utc_time_sec = -1
                    
                    if stype.endswith('GGA') and len(parts) > 1:
                        utc_time_sec = time_str_to_seconds(parts[1])
                    elif (stype == '$POGOS' or stype == '$PODRS') and len(parts) > 2:
                        try:
                            tow = float(parts[2])
                            utc_time_sec = time_str_to_seconds(gps_tow_to_utc_time(tow, leap_secs))
                        except ValueError:
                            pass
                            
                    if utc_time_sec != -1 and start_sec <= utc_time_sec <= end_sec:
                        f_out.write(line)
                        
            progress.setValue(100)
                        
            QMessageBox.information(self, "导出成功", f"文件已成功保存到:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def on_export_gga_clicked(self):
        active_segs = [s for s in self.segments if s['active']]
        if not active_segs:
            QMessageBox.warning(self, "提示", "请在列表中勾选要转换的活跃分段。")
            return
            
        target_seg = active_segs[0]
        export_mode = self.app_config.get('export_dir_mode', '同源文件目录')
        default_dir = ""
        if export_mode == "记忆上次目录":
            default_dir = self.app_config.get('last_export_dir', "")
        if not default_dir and target_seg.get('file_id'):
            default_dir = os.path.dirname(target_seg['file_id'])
            
        default_path = os.path.join(default_dir, f"converted_{target_seg['name']}.nmea")
        save_path, _ = QFileDialog.getSaveFileName(self, "格式转换导出为标准 NMEA GGA", default_path, "NMEA Files (*.nmea *.gga)")
        if not save_path:
            return
            
        if export_mode == "记忆上次目录":
            self.app_config['last_export_dir'] = os.path.dirname(save_path)
            self.save_config()
            
        start_sec = time_str_to_seconds(target_seg['start_time'])
        end_sec = time_str_to_seconds(target_seg['end_time'])
        leap_secs = self.get_leap_seconds()
        
        try:
            file_size = os.path.getsize(target_seg['file_id'])
            processed = 0
            
            from PySide6.QtWidgets import QProgressDialog, QApplication
            progress = QProgressDialog("正在转换导出 GGA...", "取消", 0, 100, self)
            progress.setWindowTitle("转换进度")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            with open(target_seg['file_id'], 'r', encoding='utf-8', errors='ignore') as f_in, \
                 open(save_path, 'w', encoding='utf-8') as f_out:
                for line in f_in:
                    if progress.wasCanceled():
                        break
                        
                    processed += len(line.encode('utf-8', errors='ignore'))
                    if processed % (1024 * 50) < 100:
                        pct = int((processed / file_size) * 100) if file_size > 0 else 0
                        progress.setValue(pct)
                        QApplication.processEvents()
                        
                    if line.startswith('$POGOS'):
                        epoch = parse_log_line(line, leap_secs)
                        if epoch and epoch['utc_time_sec'] >= start_sec and epoch['utc_time_sec'] <= end_sec:
                            gga = convert_pogos_to_gga(line, 'GN', leap_secs)
                            if gga:
                                f_out.write(gga + '\n')
                                
            progress.setValue(100)
                                
            QMessageBox.information(self, "导出成功", f"格式转换已成功保存到:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"转换保存失败: {str(e)}")

    def on_export_kml_clicked(self):
        active_segs = [s for s in self.segments if s.get('active', True) and s.get('epochs')]
        if not active_segs and not (self.truth_mode == 'dynamic' and self.truth.get('epochs')):
            QMessageBox.warning(self, "提示", "没有可导出的有效轨迹数据（请确保已加载测试分段或动态真值）。")
            return
            
        default_dir = self.app_config.get('last_export_dir', "")
        if not default_dir and active_segs and active_segs[0].get('file_id'):
            default_dir = os.path.dirname(active_segs[0]['file_id'])
            
        default_path = os.path.join(default_dir, "trajectory_export.kml")
        save_path, _ = QFileDialog.getSaveFileName(self, "导出 KML 轨迹", default_path, "KML Files (*.kml)")
        if not save_path:
            return
            
        self.app_config['last_export_dir'] = os.path.dirname(save_path)
        self.save_config()
        
        kml_header = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>GNSS Trajectory Export</name>
'''
        kml_footer = '''  </Document>
</kml>
'''
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(kml_header)
                
                # 导出动态真值
                if self.truth_mode == 'dynamic' and self.truth.get('epochs'):
                    f.write('    <Folder>\n      <name>Dynamic Truth</name>\n')
                    # 1. 写入真值连续轨迹线 (LineString)
                    f.write('      <Placemark>\n')
                    f.write('        <name>Dynamic Truth (真值轨迹线)</name>\n')
                    f.write('        <Style>\n          <LineStyle>\n            <color>ff000000</color>\n            <width>3</width>\n          </LineStyle>\n        </Style>\n')
                    f.write('        <LineString>\n')
                    f.write('          <altitudeMode>absolute</altitudeMode>\n')
                    f.write('          <coordinates>\n')
                    for ep in self.truth['epochs']:
                        if ep['lat'] == 0.0 or ep['lon'] == 0.0 or math.isnan(ep['lat']) or math.isnan(ep['lon']) or math.isnan(ep.get('alt', 0.0)):
                            continue
                        f.write(f'            {ep["lon"]},{ep["lat"]},{ep.get("alt", 0.0)}\n')
                    f.write('          </coordinates>\n')
                    f.write('        </LineString>\n')
                    f.write('      </Placemark>\n')
                    
                    # 2. 写入稀疏化的位置标志点 (Placemark)
                    truth_count = len(self.truth['epochs'])
                    step_t = max(1, truth_count // 1000)
                    for i in range(0, truth_count, step_t):
                        ep = self.truth['epochs'][i]
                        if ep['lat'] == 0.0 or ep['lon'] == 0.0 or math.isnan(ep['lat']) or math.isnan(ep['lon']) or math.isnan(ep.get('alt', 0.0)):
                            continue
                        is_key = (i == 0 or i >= truth_count - step_t)
                        label_scale = 1.0 if is_key else 0.0
                        pt_name = "真值起点" if i == 0 else ("真值终点" if i >= truth_count - step_t else f"真值点 {i}")
                        
                        f.write('      <Placemark>\n')
                        f.write(f'        <name>{pt_name}</name>\n')
                        f.write(f'        <Style>\n          <LabelStyle>\n            <scale>{label_scale}</scale>\n          </LabelStyle>\n')
                        f.write('          <IconStyle>\n            <color>ff000000</color>\n            <scale>0.4</scale>\n          </IconStyle>\n        </Style>\n')
                        time_str = ep.get('time_str', '')
                        if time_str and len(time_str) >= 6:
                            clean_time = time_str.replace(':', '')
                            if len(clean_time) >= 6:
                                iso_time = f"2024-01-01T{clean_time[:2]}:{clean_time[2:4]}:{clean_time[4:6]}Z"
                                f.write(f'        <TimeStamp><when>{iso_time}</when></TimeStamp>\n')
                        f.write('        <Point>\n')
                        f.write(f'          <coordinates>{ep["lon"]},{ep["lat"]},{ep.get("alt", 0.0)}</coordinates>\n')
                        f.write('        </Point>\n')
                        f.write('      </Placemark>\n')
                    f.write('    </Folder>\n')
                
                # 导出各个测试分段
                for seg in active_segs:
                    color_hex = seg['color'].lstrip('#')
                    if len(color_hex) == 6:
                        # KML 颜色为 aabbggrr，Matplotlib 为 #rrggbb
                        r, g, b = color_hex[0:2], color_hex[2:4], color_hex[4:6]
                        kml_color = f"ff{b}{g}{r}"
                    else:
                        kml_color = "ffff0000"
                        
                    f.write(f'    <Folder>\n      <name>{seg["name"]}</name>\n')
                    
                    # 1. 写入测试分段轨迹线 (LineString)
                    f.write('      <Placemark>\n')
                    f.write(f'        <name>{seg["name"]} (轨迹线)</name>\n')
                    f.write(f'        <Style>\n          <LineStyle>\n            <color>{kml_color}</color>\n            <width>3</width>\n          </LineStyle>\n        </Style>\n')
                    f.write('        <LineString>\n')
                    f.write('          <altitudeMode>absolute</altitudeMode>\n')
                    f.write('          <coordinates>\n')
                    for ep in seg['epochs']:
                        if ep['lat'] == 0.0 or ep['lon'] == 0.0 or math.isnan(ep['lat']) or math.isnan(ep['lon']) or math.isnan(ep.get('alt', 0.0)):
                            continue
                        f.write(f'            {ep["lon"]},{ep["lat"]},{ep.get("alt", 0.0)}\n')
                    f.write('          </coordinates>\n')
                    f.write('        </LineString>\n')
                    f.write('      </Placemark>\n')
                    
                    # 2. 写入稀疏化的位置标志点 (Placemark)
                    seg_count = len(seg['epochs'])
                    step_s = max(1, seg_count // 1000)
                    for i in range(0, seg_count, step_s):
                        ep = seg['epochs'][i]
                        if ep['lat'] == 0.0 or ep['lon'] == 0.0 or math.isnan(ep['lat']) or math.isnan(ep['lon']) or math.isnan(ep.get('alt', 0.0)):
                            continue
                        is_key = (i == 0 or i >= seg_count - step_s)
                        label_scale = 1.0 if is_key else 0.0
                        pt_name = f"{seg['name']}_起点" if i == 0 else (f"{seg['name']}_终点" if i >= seg_count - step_s else f"点 {i}")
                        
                        f.write('      <Placemark>\n')
                        f.write(f'        <name>{pt_name}</name>\n')
                        f.write(f'        <Style>\n          <LabelStyle>\n            <scale>{label_scale}</scale>\n          </LabelStyle>\n')
                        f.write(f'          <IconStyle>\n            <color>{kml_color}</color>\n            <scale>0.4</scale>\n          </IconStyle>\n        </Style>\n')
                        time_str = ep.get('time_str', '')
                        if time_str and len(time_str) >= 6:
                            clean_time = time_str.replace(':', '')
                            if len(clean_time) >= 6:
                                iso_time = f"2024-01-01T{clean_time[:2]}:{clean_time[2:4]}:{clean_time[4:6]}Z"
                                f.write(f'        <TimeStamp><when>{iso_time}</when></TimeStamp>\n')
                        f.write('        <Point>\n')
                        f.write(f'          <coordinates>{ep["lon"]},{ep["lat"]},{ep.get("alt", 0.0)}</coordinates>\n')
                        f.write('        </Point>\n')
                        f.write('      </Placemark>\n')
                    f.write('    </Folder>\n')
                
                f.write(kml_footer)
            QMessageBox.information(self, "导出成功", f"KML 轨迹已成功导出至:\n{save_path}")
        except PermissionError:
            QMessageBox.critical(self, "错误", "目标文件被占用！请确认是否在 Google Earth 中打开了该文件，关闭后再试。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"KML 导出失败: {str(e)}")

    def on_export_report_clicked(self):
        try:
            import docx
            from docx.shared import Inches
            from datetime import datetime
        except ImportError:
            QMessageBox.warning(self, "提示", "未检测到 python-docx 模块。请在终端运行: pip install python-docx")
            return
            
        if not self.segments:
            QMessageBox.warning(self, "提示", "没有测试数据可供导出。")
            return
            
        save_path, _ = QFileDialog.getSaveFileName(self, "导出 Word 报告", "测试报告.docx", "Word Documents (*.docx)")
        if not save_path:
            return
            
        try:
            doc = docx.Document()
            doc.add_heading('GNSS 定位精度测试报告', 0)
            
            doc.add_heading('1. 测试概览', level=1)
            doc.add_paragraph(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 添加表格数据 (精度指标)
            doc.add_heading('2. 精度指标对比', level=1)
            table = doc.add_table(rows=1, cols=self.table_metrics.columnCount())
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            for j in range(self.table_metrics.columnCount()):
                hdr_cells[j].text = self.table_metrics.horizontalHeaderItem(j).text()
                
            for i in range(self.table_metrics.rowCount()):
                row_cells = table.add_row().cells
                for j in range(self.table_metrics.columnCount()):
                    item = self.table_metrics.item(i, j)
                    row_cells[j].text = item.text() if item else ""
                    
            # 导出图表截图
            doc.add_heading('3. 图表分析', level=1)
            import io
            
            def add_plot_to_doc(canvas, title):
                doc.add_heading(title, level=2)
                buf = io.BytesIO()
                canvas.figure.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                buf.seek(0)
                doc.add_picture(buf, width=Inches(6.0))
                buf.close()
                
            # 强制渲染所有图表，防止用户未点击的选项卡截图为空白
            self.canvas_scatter.render_data('scatter', self.segments, self.truth, self.time_zone)
            self.canvas_trajectory.render_data('trajectory', self.segments, self.truth)
            self.canvas_status.render_data('status', self.segments, self.truth, self.time_zone)
            self.canvas_epoch_h.render_data('epoch_h', self.segments, self.truth, self.time_zone, show_extrema=self.show_extrema, x_axis_mode=self.x_axis_mode, show_sats=self.cb_show_sats.isChecked())
            self.canvas_epoch_v.render_data('epoch_v', self.segments, self.truth, self.time_zone, self.show_absolute_alt, show_extrema=self.show_extrema, x_axis_mode=self.x_axis_mode, show_sats=self.cb_show_sats.isChecked(), show_raw_alt=self.show_raw_alt)
                
            add_plot_to_doc(self.canvas_trajectory, '3.1 绝对二维轨迹投影图')
            add_plot_to_doc(self.canvas_scatter, '3.2 定位偏差分布图 (靶心图)')
            add_plot_to_doc(self.canvas_status, '3.3 定位解状态分布')
            add_plot_to_doc(self.canvas_epoch_h, '3.4 水平位置误差分布')
            add_plot_to_doc(self.canvas_epoch_v, '3.5 高程位置误差分布')
            
            doc.save(save_path)
            QMessageBox.information(self, "导出成功", f"Word 报告已成功导出至:\n{save_path}")
        except PermissionError:
            QMessageBox.critical(self, "错误", "目标 Word 文件正被另一程序(如 Microsoft Word)打开，请关闭后重试。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"报告生成失败: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
