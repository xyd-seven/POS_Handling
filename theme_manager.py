# -*- coding: utf-8 -*-
"""
Theme Manager & Design System Hub (Single Source of Truth)
Provides semantic design tokens, comprehensive template-based QSS generation,
and reactive observer pattern (sig_theme_changed) for dark/light theme switching.
"""

from PySide6.QtCore import QObject, Signal

# 1. 语义化设计调色板 (Design Tokens)
DARK_TOKENS = {
    "name": "dark",
    # 全局背景与容器
    "bg_app": "#0B0F19",          # 主窗口全局背景 (深空玄青)
    "bg_card": "#111827",         # 卡片/图表/面板容器背景 (曜石深灰)
    "bg_subtle": "#1E293B",       # 次级容器/表头/工具栏底色
    "bg_hover": "#334155",        # 悬停高亮背景
    "bg_active": "#1E3A8A",       # 选中激活背景
    "bg_input": "#0F172A",        # 输入框/下拉框/终端背景
    
    # 边框与分割线
    "border_default": "#1F2937",  # 默认边框
    "border_subtle": "#334155",   # 次级分割线
    "border_focus": "#38BDF8",    # 聚焦高亮边框 (天青蓝)
    
    # 文字与图标
    "text_primary": "#F8FAFC",    # 主标题/核心读数 (高亮白)
    "text_secondary": "#94A3B8",  # 辅助说明/标签文字 (板岩灰)
    "text_muted": "#64748B",      # 弱化提示文字
    "text_inverse": "#0F172A",    # 反色文字
    
    # 品牌与状态强调色
    "brand_primary": "#0284C7",   # 品牌主色 (天青蓝)
    "brand_hover": "#0369A1",
    "color_success": "#10B981",   # 成功/RTK固定解 (翡翠绿)
    "color_warning": "#F59E0B",   # 警告/RTK浮点解 (琥珀黄)
    "color_danger": "#EF4444",    # 危险/单点/无效 (玫瑰红)
    "color_info": "#3B82F6",      # 提示/差分解 (天空蓝)
    
    # 图表画布专用配色 (深色模式下仍保持经典高对比护眼柔和卡片底色)
    "plot_fig_bg": "#F8FAFC",
    "plot_ax_bg": "#F8FAFC",
    "plot_grid": "#E2E8F0",
    "plot_spine": "#CBD5E1",
    "plot_text": "#0F172A",
    "plot_subtext": "#475569",
    "plot_legend_bg": "#FFFFFF",
    "plot_legend_border": "#CBD5E1",
}

LIGHT_TOKENS = {
    "name": "light",
    # 全局背景与容器 (室外强光高对比清爽且护眼柔和)
    "bg_app": "#F1F5F9",          # 主窗口全局背景 (清爽云灰)
    "bg_card": "#FFFFFF",         # 卡片/图表/面板容器背景 (纯白高光)
    "bg_subtle": "#F8FAFC",       # 次级容器/表头/工具栏底色
    "bg_hover": "#E2E8F0",        # 悬停高亮背景
    "bg_active": "#DBEAFE",       # 选中激活背景
    "bg_input": "#FFFFFF",        # 输入框/下拉框/终端背景 (纯白)
    
    # 边框与分割线
    "border_default": "#CBD5E1",  # 默认边框 (清晰中灰)
    "border_subtle": "#E2E8F0",   # 次级分割线
    "border_focus": "#0284C7",    # 聚焦高亮边框
    
    # 文字与图标 (深邃墨黑，确保强光下无反光、清晰可见)
    "text_primary": "#0F172A",    # 主标题/核心读数 (深邃墨黑)
    "text_secondary": "#334155",  # 辅助说明/标签文字 (加深板岩灰)
    "text_muted": "#64748B",      # 弱化提示文字
    "text_inverse": "#FFFFFF",    # 反色文字
    
    # 品牌与状态强调色
    "brand_primary": "#0284C7",   # 品牌主色 (天青蓝)
    "brand_hover": "#0369A1",
    "color_success": "#059669",   # 成功/RTK固定解 (墨绿)
    "color_warning": "#D97706",   # 警告/RTK浮点解 (深黄)
    "color_danger": "#DC2626",    # 危险/单点/无效 (鲜红)
    "color_info": "#2563EB",      # 提示/差分解 (宝蓝)
    
    # 图表画布专用配色 (柔和护眼浅米白底色)
    "plot_fig_bg": "#F8FAFC",
    "plot_ax_bg": "#F8FAFC",
    "plot_grid": "#E2E8F0",
    "plot_spine": "#94A3B8",
    "plot_text": "#0F172A",
    "plot_subtext": "#334155",
    "plot_legend_bg": "#F8FAFC",
    "plot_legend_border": "#CBD5E1",
}


# 2. 全覆盖、无死角模板化 QSS
QSS_TEMPLATE = """
/* 全局主窗口与基础控件 */
QMainWindow, QWidget#centralwidget {{
    background-color: {bg_app};
    color: {text_primary};
}}

QWidget {{
    font-family: 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', sans-serif;
    color: {text_primary};
}}

/* 侧边栏整体容器 */
QWidget#sidebar_container {{
    background-color: {bg_app};
    border-left: 1px solid {border_default};
}}

/* 菜单栏与状态栏 */
QMenuBar {{
    background-color: {bg_card};
    color: {text_primary};
    border-bottom: 1px solid {border_default};
    padding: 2px 4px;
}}
QMenuBar::item:selected {{
    background-color: {bg_hover};
    border-radius: 4px;
}}
QMenu {{
    background-color: {bg_card};
    color: {text_primary};
    border: 1px solid {border_subtle};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item:selected {{
    background-color: {brand_primary};
    color: #FFFFFF;
    border-radius: 4px;
}}

QStatusBar {{
    background-color: {bg_card};
    color: {text_secondary};
    border-top: 1px solid {border_default};
}}

/* 选项卡 TabWidget */
QTabWidget::pane {{
    border: 1px solid {border_default};
    background-color: {bg_card};
    border-radius: 6px;
}}
QTabBar::tab {{
    background-color: {bg_subtle};
    color: {text_secondary};
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid {border_default};
    border-bottom: none;
    font-weight: bold;
    font-size: 12px;
}}
QTabBar::tab:selected {{
    background-color: {bg_card};
    color: {brand_primary};
    font-weight: bold;
    border-bottom: 2px solid {brand_primary};
}}
QTabBar::tab:hover:!selected {{
    background-color: {bg_hover};
}}

/* 卡片与分组框 GroupBox */
QGroupBox {{
    font-weight: bold;
    font-size: 12px;
    border: 1px solid {border_default};
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 16px;
    background-color: {bg_card};
    color: {text_primary};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: 0px;
    padding: 0 6px;
    color: {brand_primary};
}}

/* 文本标签 */
QLabel {{
    color: {text_primary};
    font-size: 12px;
}}

/* 按钮 PushButton */
QPushButton {{
    background-color: {bg_subtle};
    color: {text_primary};
    border: 1px solid {border_default};
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: bold;
    font-size: 12px;
}}
QPushButton:hover {{
    background-color: {bg_hover};
    border-color: {border_focus};
}}
QPushButton:pressed {{
    background-color: {bg_active};
}}
QPushButton:disabled {{
    background-color: {bg_app};
    color: {text_muted};
    border-color: {border_subtle};
}}

/* 侧边栏 Auto/Manual 切换模式专用按钮 */
QPushButton#btn_ref_auto, QPushButton#btn_ref_manual, QPushButton#btn_ref_dynamic {{
    border: 1px solid {border_default};
    background-color: {bg_subtle};
    color: {text_secondary};
    padding: 6px 10px;
    border-radius: 4px;
    font-weight: bold;
    font-size: 11px;
}}
QPushButton#btn_ref_auto[active="true"], QPushButton#btn_ref_manual[active="true"], QPushButton#btn_ref_dynamic[active="true"] {{
    background-color: {bg_active};
    color: {brand_primary};
    font-weight: bold;
    border: 1px solid {brand_primary};
}}

/* 历史参考坐标删除专用按钮 */
QPushButton#btn_del_coord {{
    background-color: rgba(239, 68, 68, 0.12);
    border: 1px solid #EF4444;
    color: #EF4444;
    font-family: 'Segoe UI Symbol', Arial, sans-serif;
    font-size: 14px;
    font-weight: bold;
    border-radius: 4px;
    padding: 0px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
}}
QPushButton#btn_del_coord:hover {{
    background-color: #EF4444;
    color: #FFFFFF;
}}
QPushButton#btn_del_coord:disabled {{
    background-color: {bg_subtle};
    border: 1px solid {border_default};
    color: {text_muted};
    padding: 0px;
}}

/* 输入框与下拉框 */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {bg_input};
    color: {text_primary};
    border: 1px solid {border_default};
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 12px;
    selection-background-color: {brand_primary};
    selection-color: #FFFFFF;
}}
QLineEdit:focus, QComboBox:focus {{
    border-color: {border_focus};
}}
QLineEdit:disabled, QComboBox:disabled {{
    background-color: {bg_subtle};
    color: {text_muted};
    border-color: {border_subtle};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 4px;
}}
QComboBox QAbstractItemView {{
    background-color: {bg_card};
    color: {text_primary};
    border: 1px solid {border_default};
    selection-background-color: {brand_primary};
    selection-color: #FFFFFF;
}}

/* 串口终端 Console 与多行文本框 */
QPlainTextEdit, QTextEdit {{
    background-color: {bg_input};
    color: {text_primary};
    border: 1px solid {border_default};
    border-radius: 6px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    selection-background-color: {brand_primary};
    selection-color: #FFFFFF;
}}

/* 列表 QListWidget */
QListWidget {{
    background-color: {bg_input};
    border: 1px solid {border_default};
    border-radius: 6px;
    color: {text_primary};
}}
QListWidget::item:selected {{
    background-color: {bg_active};
    color: {text_primary};
    border-radius: 4px;
}}
QListWidget::item:hover:!selected {{
    background-color: {bg_hover};
    border-radius: 4px;
}}

/* 表格 QTableWidget */
QTableWidget {{
    background-color: {bg_card};
    color: {text_primary};
    gridline-color: {border_subtle};
    border: 1px solid {border_default};
    border-radius: 6px;
    font-size: 13px;
}}
QTableWidget::item {{
    color: {text_primary};
}}
QHeaderView::section {{
    background-color: {bg_subtle};
    color: {text_primary};
    font-weight: bold;
    padding: 6px;
    border: 1px solid {border_default};
}}

/* 滚动条 ScrollBar */
QScrollBar:vertical {{
    background-color: {bg_app};
    width: 8px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background-color: {border_default};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {text_secondary};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* NavigationToolbar 图表工具栏 */
QToolBar {{
    background-color: {bg_card};
    border-bottom: 1px solid {border_default};
    spacing: 6px;
    padding: 2px 6px;
}}
QToolButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px;
    color: {text_primary};
}}
QToolButton:hover {{
    background-color: {bg_hover};
    border-color: {border_subtle};
}}
"""


# 3. 统一主题单例中枢 (ThemeManager)
class ThemeManager(QObject):
    sig_theme_changed = Signal(dict)
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThemeManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        super().__init__()
        self._current_theme_name = "dark"
        self._themes = {
            "dark": DARK_TOKENS,
            "light": LIGHT_TOKENS
        }
        self._initialized = True

    @property
    def current_theme_name(self):
        return self._current_theme_name

    def get_tokens(self, theme_name=None):
        name = theme_name or self._current_theme_name
        return self._themes.get(name, DARK_TOKENS)

    def get_stylesheet(self, theme_name=None):
        tokens = self.get_tokens(theme_name)
        return QSS_TEMPLATE.format(**tokens)

    def set_theme(self, theme_name):
        if theme_name not in self._themes or theme_name == self._current_theme_name:
            if theme_name in self._themes:
                self.sig_theme_changed.emit(self.get_tokens(theme_name))
            return
        self._current_theme_name = theme_name
        tokens = self.get_tokens(theme_name)
        self.sig_theme_changed.emit(tokens)

    def toggle_theme(self):
        next_theme = "light" if self._current_theme_name == "dark" else "dark"
        self.set_theme(next_theme)
        return next_theme

    def register_theme(self, name, tokens_dict):
        self._themes[name] = tokens_dict
