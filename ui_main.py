from theme_manager import ThemeManager
# -*- coding: utf-8 -*-
"""
VCOM Qt 界面布局与 QSS 样式表定义
"""
from PySide6.QtCore import Qt, Signal, QTime
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
                             QLabel, QLineEdit, QComboBox, QCheckBox, QListWidget,
                             QListWidgetItem, QTableWidget, QTableWidgetItem,
                             QTabWidget, QGroupBox, QSplitter, QHeaderView,
                             QColorDialog, QTimeEdit)
from PySide6.QtGui import QColor

# 工业级深色调 QSS 皮肤
QSS_STYLE = """
QMainWindow {
    background-color: #0B1120;
}

QWidget#sidebar_container {
    background-color: #0B1120;
    border-left: 1px solid #1E293B;
}

QGroupBox {
    background-color: #172033;
    border: 1px solid #1E293B;
    border-radius: 8px;
    margin-top: 24px;
    padding-top: 20px;
    font-size: 13px;
    font-weight: bold;
    color: #94A3B8;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: 0px;
    padding: 0 4px;
    color: #60A5FA;
}

QLabel {
    color: #94A3B8;
    font-size: 12px;
}

QLineEdit {
    background-color: #0B1120;
    border: 1px solid #1E293B;
    color: #E2E8F0;
    padding: 6px 10px;
    font-size: 12px;
    border-radius: 6px;
}

QLineEdit:focus {
    border: 1px solid #60A5FA;
    background-color: #0F172A;
}

QLineEdit:disabled {
    background-color: #172033;
    color: #475569;
}

QComboBox {
    background-color: #0B1120;
    border: 1px solid #1E293B;
    color: #E2E8F0;
    padding: 6px 10px;
    font-size: 9pt;
    border-radius: 6px;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #0F172A;
    color: #F8FAFC;
    selection-background-color: #1E293B;
    selection-color: #60A5FA;
    border: 1px solid #334155;
    border-radius: 4px;
    font-size: 9pt;
}

QPushButton {
    background-color: rgba(56, 189, 248, 0.1);
    border: 1px solid #334155;
    color: #F8FAFC;
    padding: 6px 12px;
    font-size: 11px;
    font-weight: bold;
    border-radius: 6px;
}

QPushButton:hover {
    background-color: rgba(56, 189, 248, 0.18);
    border-color: #38BDF8;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: rgba(56, 189, 248, 0.25);
    border-color: #0EA5E9;
}

QPushButton#btn_ref_auto, QPushButton#btn_ref_manual {
    border: 1px solid #1E293B;
    background-color: #0F172A;
    color: #94A3B8;
    padding: 8px 12px;
}

QPushButton#btn_ref_auto[active="true"], QPushButton#btn_ref_manual[active="true"] {
    background-color: #172554;
    color: #60A5FA;
    font-weight: bold;
    border: 1px solid #2563EB;
}

QCheckBox {
    spacing: 6px;
    color: #94A3B8;
    font-size: 11px;
    font-weight: bold;
}

QCheckBox::indicator {
    width: 36px;
    height: 20px;
}

QCheckBox::indicator:unchecked {
    image: url(resources/switch_off.png);
}

QCheckBox::indicator:checked {
    image: url(resources/switch_on.png);
}

QListWidget {
    background-color: transparent;
    border: none;
}

QTableWidget {
    background-color: #172033;
    border: 1px solid #1E293B;
    gridline-color: #1E293B;
    color: #F8FAFC;
    font-size: 11px;
    border-radius: 6px;
}

QTableWidget::item {
    padding: 8px;
}

QHeaderView::section {
    background-color: #0B1120;
    color: #94A3B8;
    border: 1px solid #1E293B;
    font-size: 11px;
    font-weight: bold;
    padding: 8px;
}

QTabWidget::pane {
    border: none;
    background-color: #0B1120;
}

QTabBar {
    background-color: transparent;
}

QTabBar::tab {
    background-color: #172033;
    color: #94A3B8;
    padding: 10px 20px;
    font-size: 13px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid #1E293B;
    border-bottom: none;
    margin-right: 6px;
}

QTabBar::tab:hover {
    color: #F8FAFC;
    background-color: #1E293B;
}

QTabBar::tab:selected {
    background-color: #0B1120;
    color: #60A5FA;
    font-weight: bold;
    border: 1px solid #1E293B;
    border-bottom: 2px solid #60A5FA;
}

QToolBar {
    background-color: #F8FAFC;
    border: none;
    border-bottom: 1px solid #E2E8F0;
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

QScrollBar:vertical {
    border: none;
    background-color: #1E293B;
    width: 16px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #94A3B8;
    min-height: 40px;
    border-radius: 6px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background-color: #CBD5E1;
}
QScrollBar::handle:vertical:pressed {
    background-color: #F1F5F9;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background-color: #1E293B;
}

QScrollBar:horizontal {
    border: none;
    background-color: #1E293B;
    height: 16px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background-color: #94A3B8;
    min-width: 40px;
    border-radius: 6px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #CBD5E1;
}
QScrollBar::handle:horizontal:pressed {
    background-color: #F1F5F9;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
    width: 0px;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background-color: #1E293B;
}

QSplitter::handle {
    background-color: #1E293B;
}
QSplitter::handle:hover {
    background-color: #38BDF8;
}
QSplitter::handle:pressed {
    background-color: #0EA5E9;
}
"""
import os
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_RES_DIR_URL = os.path.join(_BASE_DIR, "resources").replace("\\", "/")
QSS_STYLE = QSS_STYLE.replace("url(resources/", f"url({_RES_DIR_URL}/")


class TimeLineEdit(QLineEdit):
    """自定义 QLineEdit，双击时选中全部内容，方便整段修改时间"""
    def mouseDoubleClickEvent(self, e):
        super().mouseDoubleClickEvent(e)
        self.selectAll()

class SegmentListItemWidget(QWidget):
    """
    时段列表中自定义的每一个 Item 组件 (包含 checkbox、ID输入、Color原生选择、起止时间、源类型、删除按钮)
    """
    time_changed = Signal(int, str, str)     # seg_id, start_str, end_str
    name_changed = Signal(int, str)           # seg_id, new_name
    color_changed = Signal(int, str)          # seg_id, color_hex
    source_changed = Signal(int, str)         # seg_id, source_type
    active_toggled = Signal(int, bool)        # seg_id, is_active
    delete_clicked = Signal(int)              # seg_id

    def __init__(self, seg_id, name, start_time, end_time, source_type, color_hex, has_gga=True, has_pogos=True, has_podrs=True, parent=None):
        super().__init__(parent)
        self.seg_id = seg_id
        self.color_hex = color_hex
        
        # 记录该分段所关联文件的整段最原始起止时间，用于一键重置
        self.file_start = start_time.split('.')[0]
        self.file_end = end_time.split('.')[0]
        self.last_valid_start = self.file_start
        self.last_valid_end = self.file_end
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)
        
        # 1. 第一行: 勾选框、ID编辑框、取色器按钮、删除按钮 (ID编辑框自适应拉展)
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        
        self.cb_active = QCheckBox()
        self.cb_active.setChecked(True)
        self.cb_active.setFixedWidth(36)
        self.cb_active.stateChanged.connect(self.on_active_toggled)
        row1.addWidget(self.cb_active)
        
        self.txt_name = QLineEdit(name)
        self.txt_name.setFixedHeight(26)
        self.txt_name.setCursorPosition(0)
        self.txt_name.editingFinished.connect(self.on_name_changed)
        row1.addWidget(self.txt_name)
        
        self.btn_color = QPushButton()
        self.btn_color.setFixedSize(26, 26)
        self.update_color_button_style(color_hex)
        self.btn_color.clicked.connect(self.on_color_clicked)
        row1.addWidget(self.btn_color)
        
        self.btn_del = QPushButton("✖")
        self.btn_del.setFixedSize(26, 26)
        self.btn_del.setToolTip("删除该分段")
        self.btn_del.setStyleSheet("font-family: 'Segoe UI Symbol', Arial; background-color: rgba(248, 113, 113, 0.15); border: 1px solid #F87171; color: #F87171; font-size: 14px; font-weight: bold; border-radius: 4px; padding: 0px;")
        self.btn_del.clicked.connect(self.on_delete_clicked)
        row1.addWidget(self.btn_del)
        
        main_layout.addLayout(row1)
        
        # 2. 第二行: 起止时间编辑与数据源选择合并在同一行
        row2 = QHBoxLayout()
        row2.setSpacing(4)
        
        # 开始时间改用 QLineEdit，直接全选打字更方便
        self.txt_start = TimeLineEdit(self.file_start)
        self.txt_start.setFixedWidth(68)
        self.txt_start.setFixedHeight(26)
        self.txt_start.setAlignment(Qt.AlignCenter)
        self.txt_start.setPlaceholderText("HH:MM:SS")
        self.txt_start.setToolTip("输入格式：HH:MM:SS 或 HHMMSS，如 06:18:24 或 061824")
        self.txt_start.editingFinished.connect(self.on_time_changed)
        
        lbl_to = QLabel("至")
        lbl_to.setStyleSheet("color:#94A3B8; font-size:11px;")
        
        # 结束时间改用 QLineEdit
        self.txt_end = TimeLineEdit(self.file_end)
        self.txt_end.setFixedWidth(68)
        self.txt_end.setFixedHeight(26)
        self.txt_end.setAlignment(Qt.AlignCenter)
        self.txt_end.setPlaceholderText("HH:MM:SS")
        self.txt_end.setToolTip("输入格式：HH:MM:SS 或 HHMMSS，如 06:35:03 或 063503")
        self.txt_end.editingFinished.connect(self.on_time_changed)
        
        # 增加一键恢复全时段整段的微型重置按钮
        self.btn_reset = QPushButton("↻")
        self.btn_reset.setFixedSize(24, 24)
        self.btn_reset.setToolTip("一键重置为文件的完整时间段")
        self.btn_reset.setStyleSheet("font-family: 'Segoe UI Symbol', Arial; background-color: rgba(96, 165, 250, 0.15); border: 1px solid #60A5FA; color: #60A5FA; font-size: 16px; font-weight: bold; border-radius: 4px; padding: 0px;")
        self.btn_reset.clicked.connect(self.on_reset_clicked)
        
        self.cmb_src = QComboBox()
        self.cmb_src.setFixedWidth(80)
        self.cmb_src.setFixedHeight(26)
        if has_gga:
            self.cmb_src.addItem("GGA")
        if has_pogos:
            self.cmb_src.addItem("POGOS")
        if has_podrs:
            self.cmb_src.addItem("PODRS")
        self.cmb_src.setCurrentText(source_type)
        self.cmb_src.currentTextChanged.connect(self.on_source_changed)
        
        row2.addWidget(self.txt_start)
        row2.addWidget(lbl_to)
        row2.addWidget(self.txt_end)
        row2.addWidget(self.btn_reset)
        row2.addWidget(self.cmb_src)
        row2.addStretch()
        
        main_layout.addLayout(row2)
        
        # 设置整个 Item 容器的小边框
        self.setLayout(main_layout)
        ThemeManager().sig_theme_changed.connect(self.apply_theme)
        self.apply_theme(ThemeManager().get_tokens())

    def apply_theme(self, tokens=None):
        if tokens is None:
            tokens = ThemeManager().get_tokens()
        self.setStyleSheet(f"""
            SegmentListItemWidget {{
                background-color: {tokens['bg_card']};
                border: 1px solid {tokens['border_default']};
                border-radius: 8px;
            }}
            QLineEdit, QComboBox {{
                border: 1px solid {tokens['border_default']};
                border-radius: 6px;
                background-color: {tokens['bg_input']};
                font-size: 9pt;
                color: {tokens['text_primary']};
                padding: 4px 6px;
            }}
            TimeLineEdit {{
                font-size: 8pt;
                padding: 2px 4px;
            }}
            QLineEdit[invalid="true"] {{
                border: 1px solid #F87171;
                background-color: #FEE2E2;
            }}
            QLabel {{
                border: none;
                background-color: transparent;
                font-size: 12px;
                color: {tokens['text_secondary']};
            }}
            QCheckBox {{
                border: none;
                background-color: transparent;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1.5px solid {tokens['border_default']};
                background-color: {tokens['bg_input']};
                border-radius: 3px;
            }}
            QCheckBox::indicator:hover {{
                border-color: {tokens['brand_primary']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {tokens['brand_primary']};
                border-color: {tokens['brand_primary']};
                image: url({tokens['icon_check_url']});
            }}
            QComboBox QAbstractItemView {{
                background-color: {tokens['bg_card']};
                color: {tokens['text_primary']};
                selection-background-color: {tokens['bg_hover']};
                selection-color: {tokens['brand_primary']};
                border: 1px solid {tokens['border_default']};
                border-radius: 4px;
                font-size: 9pt;
            }}
        """)

    def update_color_button_style(self, color_hex):
        self.btn_color.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #FFFFFF;")

    def on_active_toggled(self, state):
        self.active_toggled.emit(self.seg_id, self.cb_active.isChecked())

    def on_name_changed(self):
        self.name_changed.emit(self.seg_id, self.txt_name.text().strip())

    def on_color_clicked(self):
        color = QColorDialog.getColor(QColor(self.color_hex), self, "选择图表线条与点集颜色")
        if color.isValid():
            self.color_hex = color.name()
            self.update_color_button_style(self.color_hex)
            self.color_changed.emit(self.seg_id, self.color_hex)

    def format_and_validate_time(self, raw_str):
        """
        验证并格式化时间字符串，如果格式错误，返回 None。
        """
        raw = raw_str.strip().replace('：', ':') # 容错中文冒号
        if not raw:
            return None
            
        # 提取点之前的主时间部分以去除毫秒/微秒
        if '.' in raw:
            parts_dot = raw.split('.')
            main_time = parts_dot[0].strip()
        else:
            main_time = raw
            
        # 1. 带有冒号的格式
        if ':' in main_time:
            parts = main_time.split(':')
            if len(parts) >= 2:
                try:
                    h = int(parts[0])
                    m = int(parts[1])
                    s = int(float(parts[2])) if len(parts) > 2 and parts[2] else 0
                    if 0 <= h < 24 and 0 <= m < 60 and 0 <= s < 60:
                        return f"{h:02d}:{m:02d}:{s:02d}"
                except ValueError:
                    pass
        # 2. 不带冒号的纯数字格式
        elif main_time.isdigit():
            # 补齐到最合理的长度
            if len(main_time) <= 2:
                main_time = main_time.zfill(2) + "0000"
            elif len(main_time) <= 4:
                main_time = main_time.zfill(4) + "00"
            elif len(main_time) < 6:
                main_time = main_time.zfill(6)
                
            if len(main_time) == 6:
                try:
                    h = int(main_time[:2])
                    m = int(main_time[2:4])
                    s = int(main_time[4:])
                    if 0 <= h < 24 and 0 <= m < 60 and 0 <= s < 60:
                        return f"{h:02d}:{m:02d}:{s:02d}"
                except ValueError:
                    pass
        return None

    def on_time_changed(self):
        start_input = self.txt_start.text().strip()
        end_input = self.txt_end.text().strip()
        
        valid_start = self.format_and_validate_time(start_input)
        valid_end = self.format_and_validate_time(end_input)
        
        start_err = (valid_start is None)
        end_err = (valid_end is None)
        
        # 设置样式属性以显示红色边框
        self.txt_start.setProperty("invalid", start_err)
        self.txt_start.style().unpolish(self.txt_start)
        self.txt_start.style().polish(self.txt_start)
        
        self.txt_end.setProperty("invalid", end_err)
        self.txt_end.style().unpolish(self.txt_end)
        self.txt_end.style().polish(self.txt_end)
        
        from PySide6.QtWidgets import QToolTip
        from PySide6.QtGui import QCursor
        
        if start_err or end_err:
            err_msg = []
            if start_err:
                err_msg.append("开始时间格式错误（支持 HH:MM:SS、HHMMSS、HHMM 等）")
            if end_err:
                err_msg.append("结束时间格式错误（支持 HH:MM:SS、HHMMSS、HHMM 等）")
            
            QToolTip.showText(QCursor.pos(), "\n".join(err_msg), self)
            
            # 恢复上一次的值
            if start_err:
                self.txt_start.setText(self.last_valid_start)
            if end_err:
                self.txt_end.setText(self.last_valid_end)
            return
            
        # 检查时间合理性 (开始 <= 结束，允许跨越午夜)
        from gnss_parser import time_str_to_seconds
        s_sec = time_str_to_seconds(valid_start)
        e_sec = time_str_to_seconds(valid_end)
        fs_sec = time_str_to_seconds(self.file_start)
        fe_sec = time_str_to_seconds(self.file_end)
        
        # 将输入时间转换为相对于文件开始时间的相对秒数，以支持跨越午夜的情况
        def get_relative_sec(t, fs, fe):
            if fs <= fe:
                return t - fs
            else:
                # 跨越午夜：在 fs 之后的为第一天，在 fe 之前的为第二天
                if t >= fs:
                    return t - fs
                else:
                    return (86400 - fs) + t
                    
        s_rel = get_relative_sec(s_sec, fs_sec, fe_sec)
        e_rel = get_relative_sec(e_sec, fs_sec, fe_sec)
        
        if s_rel > e_rel:
            self.txt_start.setProperty("invalid", True)
            self.txt_end.setProperty("invalid", True)
            self.txt_start.style().unpolish(self.txt_start)
            self.txt_start.style().polish(self.txt_start)
            self.txt_end.style().unpolish(self.txt_end)
            self.txt_end.style().polish(self.txt_end)
            
            QToolTip.showText(QCursor.pos(), "时间范围错误：开始时间不能晚于结束时间（跨天段除外）！", self)
            
            self.txt_start.setText(self.last_valid_start)
            self.txt_end.setText(self.last_valid_end)
            return
            
        # 清除错误状态
        self.txt_start.setProperty("invalid", False)
        self.txt_end.setProperty("invalid", False)
        self.txt_start.style().unpolish(self.txt_start)
        self.txt_start.style().polish(self.txt_start)
        self.txt_end.style().unpolish(self.txt_end)
        self.txt_end.style().polish(self.txt_end)
        
        self.last_valid_start = valid_start
        self.last_valid_end = valid_end
        
        # 回填格式化好、整齐的时间格式
        self.txt_start.setText(valid_start)
        self.txt_end.setText(valid_end)
        
        self.time_changed.emit(self.seg_id, valid_start, valid_end)

    def on_reset_clicked(self):
        self.txt_start.setText(self.file_start)
        self.txt_end.setText(self.file_end)
        self.last_valid_start = self.file_start
        self.last_valid_end = self.file_end
        
        # 重置时清除错误状态
        self.txt_start.setProperty("invalid", False)
        self.txt_end.setProperty("invalid", False)
        self.txt_start.style().unpolish(self.txt_start)
        self.txt_start.style().polish(self.txt_start)
        self.txt_end.style().unpolish(self.txt_end)
        self.txt_end.style().polish(self.txt_end)
        
        self.time_changed.emit(self.seg_id, self.file_start, self.file_end)

    def set_times(self, start_time, end_time):
        clean_start = start_time.split('.')[0]
        clean_end = end_time.split('.')[0]
        self.txt_start.setText(clean_start)
        self.txt_end.setText(clean_end)
        self.last_valid_start = clean_start
        self.last_valid_end = clean_end

    def on_source_changed(self, text):
        self.source_changed.emit(self.seg_id, text)

    def on_delete_clicked(self):
        self.delete_clicked.emit(self.seg_id)
