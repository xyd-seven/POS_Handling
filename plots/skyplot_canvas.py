# -*- coding: utf-8 -*-
"""
雷达极坐标天空图 (SkyPlot) 独立 Matplotlib 绘图组件
支持四大星座着色、在用/跟踪星区分、等仰角同心环、时间滑块探伤与全时段星轨渲染。
"""
import math
import numpy as np
import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt

class SkyPlotCanvas(QWidget):
    CONSTELLATION_COLORS = {
        'BD': '#EF4444',     # 北斗 BDS (鲜艳红)
        'GPS': '#3B82F6',    # GPS (亮蓝)
        'GL': '#F59E0B',     # GLONASS (琥珀黄)
        'GA': '#06B6D4',     # Galileo (青蓝)
        'QZSS': '#10B981',   # QZSS (翡翠绿)
        'SBAS': '#8B5CF6'    # SBAS (紫色)
    }

    def __init__(self, parent=None, width=6, height=6, dpi=100):
        super().__init__(parent)
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        self.ax = None
        self.init_polar_axes()

    def init_polar_axes(self):
        self.figure.clear()
        self.ax = self.figure.add_subplot(111, projection='polar')
        self.figure.patch.set_facecolor('#0B1120')
        self.ax.set_facecolor('#0F172A')

        # 设置正北为顶部，顺时针方向递增 (N -> E -> S -> W)
        self.ax.set_theta_zero_location('N')
        self.ax.set_theta_direction(-1)

        # 极径范围：0 (天顶 90°) ~ 90 (地平线 0°)
        self.ax.set_ylim(0, 90)
        self.ax.set_yticks([30, 60, 80, 90])
        self.ax.set_yticklabels(['60°', '30°', '10°', '0°'], color='#94A3B8', fontsize=9, fontweight='bold')
        self.ax.tick_params(axis='y', colors='#64748B')

        # 方位角刻度
        self.ax.set_xticks(np.deg2rad([0, 45, 90, 135, 180, 225, 270, 315]))
        self.ax.set_xticklabels(['N (0°)', '45°', 'E (90°)', '135°', 'S (180°)', '225°', 'W (270°)', '315°'], 
                                color='#E2E8F0', fontsize=10, fontweight='bold')

        # 网格与边框美化
        self.ax.grid(True, color='#334155', linestyle='--', linewidth=0.8, alpha=0.7)
        self.ax.spines['polar'].set_color('#475569')
        self.ax.spines['polar'].set_linewidth(1.5)

    def render_snapshot(self, sats_dict, dop_dict=None, title_prefix=""):
        """
        渲染单时刻天空图快照
        """
        self.init_polar_axes()

        # 绘制 10° 截止角保护环 (淡红辅助线)
        theta_ring = np.linspace(0, 2*np.pi, 200)
        self.ax.plot(theta_ring, [80]*len(theta_ring), color='#EF4444', linestyle=':', linewidth=1.2, alpha=0.6, label='Mask 10°')

        if not sats_dict:
            self.ax.text(0, 45, "未检测到可见卫星 (GSV) 数据", color='#94A3B8', fontsize=12, 
                         fontweight='bold', ha='center', va='center',
                         bbox=dict(boxstyle='round,pad=0.6', facecolor='#1E293B', edgecolor='#475569', alpha=0.9))
            self.canvas.draw_idle()
            return

        for sat_key, sat_info in sats_dict.items():
            sys_prefix = sat_info.get('sys_prefix', 'GPS')
            prn = sat_info.get('prn', 0)
            lbl_char = sat_info.get('lbl_char', 'G')
            elev = sat_info.get('elevation', 0.0)
            azim = sat_info.get('azimuth', 0.0)
            is_used = sat_info.get('is_used', False)

            r = max(0.0, min(90.0, 90.0 - elev))
            theta = np.deg2rad(azim)

            color = self.CONSTELLATION_COLORS.get(sys_prefix, '#94A3B8')
            sat_name = f"{lbl_char}{prn:02d}"

            if is_used:
                # 在用卫星: 实心高亮圆点 + 白色加粗字
                self.ax.scatter(theta, r, s=280, color=color, edgecolors='#FFFFFF', linewidths=1.8, zorder=5)
                self.ax.text(theta, r, sat_name, color='#FFFFFF', fontsize=9.0, fontweight='bold',
                             ha='center', va='center', zorder=6)
            else:
                # 跟踪未在用: 半透明空心圆点 + 浅色字
                self.ax.scatter(theta, r, s=220, facecolors='none', edgecolors=color, linewidths=1.5, linestyle='--', alpha=0.85, zorder=4)
                self.ax.text(theta, r, sat_name, color='#CBD5E1', fontsize=8.5, fontweight='bold',
                             ha='center', va='center', zorder=6)

        pdop_str = f"PDOP: {dop_dict.get('pdop', 1.0):.1f}" if dop_dict else ""
        hdop_str = f"HDOP: {dop_dict.get('hdop', 1.0):.1f}" if dop_dict else ""
        title_str = f"{title_prefix} 极坐标天空图 (SkyPlot)" if title_prefix else "极坐标天空图 (SkyPlot)"
        if pdop_str and hdop_str:
            title_str += f"  [{pdop_str} | {hdop_str}]"

        self.ax.set_title(title_str, color='#F8FAFC', fontsize=12, fontweight='bold', pad=18)
        self.canvas.draw_idle()

    def render_tracks(self, sat_tracks_dict):
        """
        渲染全时段星轨运动图
        """
        self.init_polar_axes()

        # 绘制 10° 截止角保护环
        theta_ring = np.linspace(0, 2*np.pi, 200)
        self.ax.plot(theta_ring, [80]*len(theta_ring), color='#EF4444', linestyle=':', linewidth=1.2, alpha=0.6)

        if not sat_tracks_dict:
            self.ax.text(0, 45, "无星轨轨迹数据", color='#94A3B8', fontsize=12, 
                         fontweight='bold', ha='center', va='center',
                         bbox=dict(boxstyle='round,pad=0.6', facecolor='#1E293B', edgecolor='#475569', alpha=0.9))
            self.canvas.draw_idle()
            return

        for sat_key, track_points in sat_tracks_dict.items():
            if not track_points:
                continue
            sys_prefix, prn = sat_key
            color = self.CONSTELLATION_COLORS.get(sys_prefix, '#94A3B8')

            azims = [p[2] for p in track_points]
            elevs = [p[1] for p in track_points]

            thetas = np.deg2rad(azims)
            radii = [90.0 - el for el in elevs]

            # 绘制弧线
            self.ax.plot(thetas, radii, color=color, linewidth=2.0, alpha=0.75, zorder=3)

            # 在轨迹终点标出卫星名
            lbl_char = 'B' if sys_prefix == 'BD' else ('G' if sys_prefix == 'GPS' else ('R' if sys_prefix == 'GL' else 'E'))
            self.ax.scatter(thetas[-1], radii[-1], s=180, color=color, edgecolors='#FFFFFF', linewidths=1.2, zorder=5)
            self.ax.text(thetas[-1], radii[-1], f"{lbl_char}{prn:02d}", color='#FFFFFF', fontsize=8.0, fontweight='bold', ha='center', va='center', zorder=6)

        self.ax.set_title("全时段卫星运动星轨图 (Sky Tracks)", color='#F8FAFC', fontsize=12, fontweight='bold', pad=18)
        self.canvas.draw_idle()
