# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                               QWidget, QLabel, QSpinBox, QCheckBox, QComboBox, 
                               QPushButton, QFormLayout, QGroupBox, QDialogButtonBox)
from PySide6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("全局设置 (Preferences)")
        self.setMinimumSize(540, 420)
        self.resize(600, 480)
        
        # 应用深色样式
        self.setStyleSheet("""
            QDialog {
                background-color: #0B1120;
                color: #F8FAFC;
            }
            QTabWidget::pane {
                border: 1px solid #1E293B;
                background-color: #0B1120;
                border-radius: 4px;
            }
            QTabBar::tab {
                background: #1E293B;
                color: #94A3B8;
                padding: 6px 16px;
                border: 1px solid transparent;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #0B1120;
                color: #F8FAFC;
                border: 1px solid #1E293B;
                border-bottom: 1px solid #0B1120;
            }
            QGroupBox {
                border: 1px solid #1E293B;
                border-radius: 6px;
                margin-top: 12px;
                font-weight: bold;
                color: #38BDF8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 4px;
                left: 10px;
            }
            QLabel {
                color: #F8FAFC;
            }
             QSpinBox, QComboBox {
                background-color: #0F172A;
                border: 1px solid #334155;
                color: #F8FAFC;
                padding: 6px;
                min-height: 24px;
                font-size: 10pt;
                border-radius: 4px;
            }
            QSpinBox:focus, QComboBox:focus {
                border: 1px solid #38BDF8;
            }
            QCheckBox {
                color: #F8FAFC;
            }
            QPushButton {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                padding: 6px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #334155;
                border: 1px solid #475569;
            }
            QPushButton[primary="true"] {
                background-color: #0284C7;
                border: 1px solid #0369A1;
            }
            QPushButton[primary="true"]:hover {
                background-color: #0369A1;
                border: 1px solid #0284C7;
            }
        """)
        
        self.config = config
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        self.tab_perf = QWidget()
        self.tab_io = QWidget()
        
        self.tabs.addTab(self.tab_perf, "📈 性能与图表")
        self.tabs.addTab(self.tab_io, "🗃️ 解析与导出")
        
        # --- 性能与图表 Tab ---
        perf_layout = QVBoxLayout(self.tab_perf)
        
        # 图表渲染组
        grp_render = QGroupBox("图表渲染设置")
        layout_render = QFormLayout(grp_render)
        
        self.sp_downsample = QSpinBox()
        self.sp_downsample.setRange(10000, 1000000)
        self.sp_downsample.setSingleStep(10000)
        self.sp_downsample.setSuffix(" 个点")
        layout_render.addRow("动态抽稀阈值:", self.sp_downsample)
        
        self.cb_dpi = QComboBox()
        self.cb_dpi.view().setStyleSheet("font-size: 10pt;")
        self.cb_dpi.addItems(["150 (常规)", "300 (高清)", "600 (超清)"])
        layout_render.addRow("导出图片分辨率:", self.cb_dpi)
        
        perf_layout.addWidget(grp_render)
        
        # 数据过滤组
        grp_filter = QGroupBox("数据异常过滤")
        layout_filter = QFormLayout(grp_filter)
        
        self.chk_outlier = QCheckBox("启用异常点过滤")
        self.chk_outlier.stateChanged.connect(self.on_outlier_toggled)
        layout_filter.addRow("", self.chk_outlier)
        
        self.sp_outlier_thresh = QSpinBox()
        self.sp_outlier_thresh.setRange(1, 100000)
        self.sp_outlier_thresh.setSingleStep(10)
        self.sp_outlier_thresh.setSuffix(" 米 (2D误差)")
        layout_filter.addRow("丢弃误差大于:", self.sp_outlier_thresh)
        
        perf_layout.addWidget(grp_filter)
        perf_layout.addStretch()
        
        # --- 解析与导出 Tab ---
        io_layout = QVBoxLayout(self.tab_io)
        
        grp_parse = QGroupBox("NMEA 解析行为")
        layout_parse = QFormLayout(grp_parse)
        self.chk_strict_nmea = QCheckBox("严格校验 Checksum (不匹配则丢弃)")
        layout_parse.addRow("", self.chk_strict_nmea)
        io_layout.addWidget(grp_parse)
        
        grp_export = QGroupBox("文件导出策略")
        layout_export = QFormLayout(grp_export)
        self.cb_export_dir = QComboBox()
        self.cb_export_dir.view().setStyleSheet("font-size: 10pt;")
        self.cb_export_dir.addItems(["同源文件目录", "记忆上次目录"])
        layout_export.addRow("默认保存目录:", self.cb_export_dir)
        io_layout.addWidget(grp_export)
        
        io_layout.addStretch()
        
        main_layout.addWidget(self.tabs)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("保存并应用")
        btn_save.setProperty("primary", True)
        btn_save.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        
        main_layout.addLayout(btn_layout)

    def on_outlier_toggled(self, state):
        self.sp_outlier_thresh.setEnabled(self.chk_outlier.isChecked())

    def load_settings(self):
        self.sp_downsample.setValue(self.config.get('downsample_threshold', 100000))
        
        dpi_val = self.config.get('export_dpi', 150)
        if dpi_val == 300:
            self.cb_dpi.setCurrentIndex(1)
        elif dpi_val == 600:
            self.cb_dpi.setCurrentIndex(2)
        else:
            self.cb_dpi.setCurrentIndex(0)
            
        is_filter = self.config.get('filter_outliers', False)
        self.chk_outlier.setChecked(is_filter)
        self.sp_outlier_thresh.setEnabled(is_filter)
        self.sp_outlier_thresh.setValue(self.config.get('outlier_threshold', 50))
        
        self.chk_strict_nmea.setChecked(self.config.get('strict_nmea_checksum', False))
        
        export_dir_mode = self.config.get('export_dir_mode', '同源文件目录')
        idx = self.cb_export_dir.findText(export_dir_mode)
        if idx >= 0:
            self.cb_export_dir.setCurrentIndex(idx)

    def get_settings(self):
        dpi_str = self.cb_dpi.currentText().split(' ')[0]
        return {
            'downsample_threshold': self.sp_downsample.value(),
            'export_dpi': int(dpi_str),
            'filter_outliers': self.chk_outlier.isChecked(),
            'outlier_threshold': self.sp_outlier_thresh.value(),
            'strict_nmea_checksum': self.chk_strict_nmea.isChecked(),
            'export_dir_mode': self.cb_export_dir.currentText()
        }
