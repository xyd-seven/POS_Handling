# -*- coding: utf-8 -*-
"""
雷达极坐标天空图 (SkyPlot) 与 3D 空间立体天球穹顶 (3D SkyDome) 绘图组件
支持 2D 极坐标雷达盘、全时段抗跳变星轨及 3D 高性能水晶天穹多维可视化，深度适配深浅双主题。
"""
import math
import numpy as np
import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from mpl_toolkits.mplot3d import Axes3D
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt
from theme_manager import ThemeManager

class SkyPlotCanvas(QWidget):
    CONSTELLATION_COLORS = {
        'BD': '#EF4444',     # 北斗 BDS (鲜艳红)
        'GPS': '#2563EB',    # GPS (亮蓝)
        'GL': '#D97706',     # GLONASS (琥珀黄)
        'GA': '#0891B2',     # Galileo (青蓝)
        'QZSS': '#059669',   # QZSS (翡翠绿)
        'SBAS': '#7C3AED'    # SBAS (紫色)
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
        self.current_mode = 'polar' # 'polar' 或 '3d'
        self._last_elev_azim_3d = (28, -55)
        self._3d_dynamic_artists = []
        
        self.last_sats_dict = None
        self.last_dop_dict = None
        self.last_title_prefix = ""
        self.last_tracks_dict = None

        ThemeManager().sig_theme_changed.connect(self.apply_theme)
        self.init_polar_axes()

    def apply_theme(self, tokens=None):
        if tokens is None:
            tokens = ThemeManager().get_tokens()
        
        if self.current_mode == 'polar':
            self.figure.patch.set_facecolor(tokens['plot_fig_bg'])
            if self.ax:
                self.ax.set_facecolor(tokens['plot_ax_bg'])
                self.ax.spines['polar'].set_color(tokens['plot_spine'])
                self.ax.grid(True, color=tokens['plot_grid'], linestyle='--', linewidth=0.8, alpha=0.8)
                self.ax.tick_params(axis='y', colors=tokens['text_secondary'])
                self.ax.set_yticklabels(['60°', '30°', '10°', '0°'], color=tokens['text_secondary'], fontsize=9, fontweight='bold')
                self.ax.set_xticklabels(['N (0°)', '45°', 'E (90°)', '135°', 'S (180°)', '225°', 'W (270°)', '315°'], 
                                        color=tokens['text_primary'], fontsize=10, fontweight='bold')
        elif self.current_mode == '3d':
            self.figure.patch.set_facecolor(tokens['plot_fig_bg'])
            if self.ax:
                self.ax.set_facecolor(tokens['plot_fig_bg'])

        self.canvas.draw_idle()

    def init_polar_axes(self):
        tokens = ThemeManager().get_tokens()
        self.figure.clear()
        self.current_mode = 'polar'
        self._3d_dynamic_artists.clear()
        self.ax = self.figure.add_subplot(111, projection='polar')
        self.figure.patch.set_facecolor(tokens['plot_fig_bg'])
        self.ax.set_facecolor(tokens['plot_ax_bg'])

        # 设置正北为顶部，顺时针方向递增 (N -> E -> S -> W)
        self.ax.set_theta_zero_location('N')
        self.ax.set_theta_direction(-1)

        # 极径范围：0 (天顶 90°) ~ 90 (地平线 0°)
        self.ax.set_ylim(0, 90)
        self.ax.set_yticks([30, 60, 80, 90])
        self.ax.set_yticklabels(['60°', '30°', '10°', '0°'], color=tokens['text_secondary'], fontsize=9, fontweight='bold')
        self.ax.tick_params(axis='y', colors=tokens['text_secondary'])

        # 方位角刻度
        self.ax.set_xticks(np.deg2rad([0, 45, 90, 135, 180, 225, 270, 315]))
        self.ax.set_xticklabels(['N (0°)', '45°', 'E (90°)', '135°', 'S (180°)', '225°', 'W (270°)', '315°'], 
                                color=tokens['text_primary'], fontsize=10, fontweight='bold')

        # 网格与边框美化
        self.ax.grid(True, color=tokens['plot_grid'], linestyle='--', linewidth=0.8, alpha=0.8)
        self.ax.spines['polar'].set_color(tokens['plot_spine'])
        self.ax.spines['polar'].set_linewidth(1.5)

        # 显式重置 2D 极坐标边距
        self.figure.subplots_adjust(left=0.08, right=0.92, bottom=0.06, top=0.91)

    def init_3d_axes(self):
        tokens = ThemeManager().get_tokens()
        if self.current_mode == '3d' and hasattr(self.ax, 'elev') and hasattr(self.ax, 'azim'):
            if self.ax.elev is not None and self.ax.azim is not None:
                self._last_elev_azim_3d = (self.ax.elev, self.ax.azim)

        self.figure.clear()
        self.current_mode = '3d'
        self._3d_dynamic_artists.clear()
        self.ax = self.figure.add_subplot(111, projection='3d')
        self.figure.patch.set_facecolor(tokens['plot_fig_bg'])
        self.ax.set_facecolor(tokens['plot_fig_bg'])

        # 隐藏 3D 方形边框和底色面板
        self.ax.xaxis.set_pane_color((0.0, 0.0, 0.0, 0.0))
        self.ax.yaxis.set_pane_color((0.0, 0.0, 0.0, 0.0))
        self.ax.zaxis.set_pane_color((0.0, 0.0, 0.0, 0.0))
        self.ax.grid(False)
        self.ax.set_axis_off()

        # 设置显示范围与视角
        self.ax.set_xlim(-1.08, 1.08)
        self.ax.set_ylim(-1.08, 1.08)
        self.ax.set_zlim(-0.04, 1.08)
        self.ax.view_init(elev=self._last_elev_azim_3d[0], azim=self._last_elev_azim_3d[1])

        try:
            self.ax.dist = 7.5
            self.ax.set_box_aspect([1.0, 1.0, 0.75])
        except Exception:
            pass
        self.figure.subplots_adjust(left=-0.04, right=1.04, bottom=-0.04, top=1.04)

        self._build_static_3d_dome_layer(tokens)

    def _build_static_3d_dome_layer(self, tokens=None):
        if tokens is None:
            tokens = ThemeManager().get_tokens()
        # 1. 发光水晶半球
        u_surf = np.linspace(0, 2 * np.pi, 36)
        v_surf = np.linspace(0, np.pi / 2, 16)
        U_surf, V_surf = np.meshgrid(u_surf, v_surf)
        X_surf = np.cos(V_surf) * np.sin(U_surf)
        Y_surf = np.cos(V_surf) * np.cos(U_surf)
        Z_surf = np.sin(V_surf)

        self.ax.plot_surface(X_surf, Y_surf, Z_surf, color='#0284C7', alpha=0.08, shade=True, antialiased=True, zorder=1)

        # 2. 仰角圈
        u_ring = np.linspace(0, 2 * np.pi, 60)
        for elev_deg in [0, 30, 60]:
            elev_rad = np.deg2rad(elev_deg)
            r_ring = np.cos(elev_rad)
            z_ring = np.sin(elev_rad)
            x_ring = r_ring * np.sin(u_ring)
            y_ring = r_ring * np.cos(u_ring)
            self.ax.plot(x_ring, y_ring, z_ring, color='#0284C7' if elev_deg == 0 else tokens['plot_grid'], 
                         linestyle='-' if elev_deg == 0 else '--', linewidth=1.2 if elev_deg == 0 else 0.8, alpha=0.8, zorder=2)
            if elev_deg > 0:
                self.ax.text(0, r_ring, z_ring, f" {elev_deg}°", color=tokens['text_secondary'], fontsize=8, fontweight='bold', zorder=2)

        # 3. 10° 截止角
        elev_mask = np.deg2rad(10)
        r_mask = np.cos(elev_mask)
        z_mask = np.sin(elev_mask)
        self.ax.plot(r_mask * np.sin(u_ring), r_mask * np.cos(u_ring), z_mask, color='#EF4444', linestyle=':', linewidth=1.2, alpha=0.65, zorder=2)

        # 4. 经线
        v_line = np.linspace(0, np.pi / 2, 20)
        for azim_deg in [0, 45, 90, 135, 180, 225, 270, 315]:
            azim_rad = np.deg2rad(azim_deg)
            x_line = np.cos(v_line) * np.sin(azim_rad)
            y_line = np.cos(v_line) * np.cos(azim_rad)
            z_line = np.sin(v_line)
            self.ax.plot(x_line, y_line, z_line, color=tokens['plot_grid'], linestyle=':', linewidth=0.7, alpha=0.6, zorder=2)

        # 5. 十字线
        self.ax.plot([-1.05, 1.05], [0, 0], [0, 0], color=tokens['plot_grid'], linestyle='-', linewidth=1.0, zorder=2)
        self.ax.plot([0, 0], [-1.05, 1.05], [0, 0], color=tokens['plot_grid'], linestyle='-', linewidth=1.0, zorder=2)

        # 6. 方位文字
        self.ax.text(0, 1.14, 0, "N (0°)", color='#0284C7', fontsize=11, fontweight='bold', ha='center', va='center', zorder=3)
        self.ax.text(1.14, 0, 0, "E (90°)", color=tokens['text_primary'], fontsize=10, fontweight='bold', ha='center', va='center', zorder=3)
        self.ax.text(0, -1.14, 0, "S (180°)", color=tokens['text_primary'], fontsize=10, fontweight='bold', ha='center', va='center', zorder=3)
        self.ax.text(-1.14, 0, 0, "W (270°)", color=tokens['text_primary'], fontsize=10, fontweight='bold', ha='center', va='center', zorder=3)
        self.ax.text(0, 0, 1.06, "Zenith (90°)", color=tokens['text_secondary'], fontsize=9.5, fontweight='bold', ha='center', va='bottom', zorder=3)

        # 7. 观测基座
        self.ax.scatter([0], [0], [0], s=80, color='#0284C7', marker='o', edgecolors='#FFFFFF', linewidths=1.2, alpha=0.9, zorder=4)
        self.ax.text(0, 0, -0.04, "Antenna", color=tokens['text_muted'], fontsize=7.5, fontweight='bold', ha='center', va='top', zorder=4)

    def render_snapshot(self, sats_dict, dop_dict=None, title_prefix=""):
        self.last_sats_dict = sats_dict
        self.last_dop_dict = dop_dict
        self.last_title_prefix = title_prefix
        tokens = ThemeManager().get_tokens()

        self.init_polar_axes()

        # 10° 截止角
        theta_ring = np.linspace(0, 2*np.pi, 200)
        self.ax.plot(theta_ring, [80]*len(theta_ring), color='#EF4444', linestyle=':', linewidth=1.2, alpha=0.6, label='Mask 10°')

        if not sats_dict:
            self.ax.text(0, 45, "未检测到可见卫星 (GSV) 数据", color=tokens['text_muted'], fontsize=12, 
                         fontweight='bold', ha='center', va='center',
                         bbox=dict(boxstyle='round,pad=0.6', facecolor=tokens['plot_legend_bg'], edgecolor=tokens['plot_legend_border'], alpha=0.9))
            self.canvas.draw_idle()
            return

        for sat_key, sat_info in sats_dict.items():
            sys_prefix = sat_info.get('sys_prefix', 'GPS')
            prn = sat_info.get('prn', 0)
            lbl_char = sat_info.get('lbl_char', 'G')
            elev = sat_info.get('elevation', 0.0)
            azim = sat_info.get('azimuth', 0.0)
            is_used = sat_info.get('is_used', False)

            if elev <= 0.01 and azim <= 0.01:
                continue

            r = max(0.0, min(90.0, 90.0 - elev))
            theta = np.deg2rad(azim)

            color = self.CONSTELLATION_COLORS.get(sys_prefix, '#94A3B8')
            sat_name = f"{lbl_char}{prn:02d}"

            edge_col = '#0F172A' if tokens['name'] == 'light' else '#FFFFFF'
            txt_col = '#FFFFFF' if is_used else (tokens['text_primary'] if tokens['name'] == 'light' else '#CBD5E1')

            if is_used:
                self.ax.scatter(theta, r, s=280, color=color, edgecolors=edge_col, linewidths=1.8, zorder=5)
                self.ax.text(theta, r, sat_name, color='#FFFFFF', fontsize=9.0, fontweight='bold',
                             ha='center', va='center', zorder=6)
            else:
                self.ax.scatter(theta, r, s=220, facecolors='none', edgecolors=color, linewidths=1.6, linestyle='--', alpha=0.9, zorder=4)
                self.ax.text(theta, r, sat_name, color=txt_col, fontsize=8.5, fontweight='bold',
                             ha='center', va='center', zorder=6)

        pdop_str = f"PDOP: {dop_dict.get('pdop', 1.0):.1f}" if dop_dict else ""
        hdop_str = f"HDOP: {dop_dict.get('hdop', 1.0):.1f}" if dop_dict else ""
        title_str = f"{title_prefix} 极坐标天空图 (SkyPlot)" if title_prefix else "极坐标天空图 (SkyPlot)"
        if pdop_str and hdop_str:
            title_str += f"  [{pdop_str} | {hdop_str}]"

        self.ax.set_title(title_str, color=tokens['text_primary'], fontsize=12, fontweight='bold', pad=18)
        self.canvas.draw_idle()

    def render_tracks(self, sat_tracks_dict):
        self.last_tracks_dict = sat_tracks_dict
        tokens = ThemeManager().get_tokens()
        self.init_polar_axes()

        theta_ring = np.linspace(0, 2*np.pi, 200)
        self.ax.plot(theta_ring, [80]*len(theta_ring), color='#EF4444', linestyle=':', linewidth=1.2, alpha=0.6)

        if not sat_tracks_dict:
            self.ax.text(0, 45, "无星轨轨迹数据", color=tokens['text_muted'], fontsize=12, 
                         fontweight='bold', ha='center', va='center',
                         bbox=dict(boxstyle='round,pad=0.6', facecolor=tokens['plot_legend_bg'], edgecolor=tokens['plot_legend_border'], alpha=0.9))
            self.canvas.draw_idle()
            return

        for sat_key, raw_track in sat_tracks_dict.items():
            if not raw_track:
                continue

            valid_points = []
            for pt in raw_track:
                t, elev, azim, is_used = pt
                if elev <= 0.01 and azim <= 0.01:
                    continue
                if 0 <= elev <= 90 and 0 <= azim <= 360:
                    valid_points.append(pt)

            if not valid_points:
                continue

            sys_prefix, prn = sat_key
            color = self.CONSTELLATION_COLORS.get(sys_prefix, '#94A3B8')

            azims = np.array([pt[2] for pt in valid_points])
            elevs = np.array([pt[1] for pt in valid_points])
            rs = 90.0 - elevs
            thetas = np.deg2rad(azims)

            # 拆分穿越 0/360 度的星轨
            diffs = np.abs(np.diff(thetas))
            split_indices = np.where(diffs > np.pi)[0] + 1
            theta_segments = np.split(thetas, split_indices)
            r_segments = np.split(rs, split_indices)

            for t_seg, r_seg in zip(theta_segments, r_segments):
                if len(t_seg) > 0:
                    self.ax.plot(t_seg, r_seg, color=color, linewidth=1.8, alpha=0.8, zorder=3)

            # 起点终点标记
            first_theta, first_r = thetas[0], rs[0]
            last_theta, last_r = thetas[-1], rs[-1]
            lbl_char = sys_prefix[0] if sys_prefix else 'S'
            sat_name = f"{lbl_char}{prn:02d}"

            edge_col = '#0F172A' if tokens['name'] == 'light' else '#FFFFFF'
            self.ax.scatter([last_theta], [last_r], s=180, color=color, edgecolors=edge_col, linewidths=1.5, zorder=5)
            self.ax.text(last_theta, last_r, sat_name, color='#FFFFFF', fontsize=8.0, fontweight='bold',
                         ha='center', va='center', zorder=6)

        self.ax.set_title("全时段卫星运动星轨图 (Sky Tracks)", color=tokens['text_primary'], fontsize=12, fontweight='bold', pad=18)
        self.canvas.draw_idle()

    def render_3d_snapshot(self, sats_dict, dop_dict=None, sat_tracks_dict=None, show_tracks=True, title_prefix=""):
        tokens = ThemeManager().get_tokens()
        if self.current_mode != '3d' or self.ax is None:
            self.init_3d_axes()
        else:
            for artist in self._3d_dynamic_artists:
                try:
                    artist.remove()
                except Exception:
                    pass
            self._3d_dynamic_artists.clear()

        if not sats_dict:
            t_no = self.ax.text(0, 0, 0.4, "未检测到可见卫星 (GSV) 数据", color=tokens['text_muted'], fontsize=11, fontweight='bold', ha='center', va='center')
            self._3d_dynamic_artists.append(t_no)
            self.canvas.draw_idle()
            return

        for sat_key, sat_info in sats_dict.items():
            sys_prefix = sat_info.get('sys_prefix', 'GPS')
            prn = sat_info.get('prn', 0)
            lbl_char = sat_info.get('lbl_char', 'G')
            elev = sat_info.get('elevation', 0.0)
            azim = sat_info.get('azimuth', 0.0)
            is_used = sat_info.get('is_used', False)

            if elev <= 0.01 and azim <= 0.01:
                continue

            elev_rad = np.deg2rad(elev)
            azim_rad = np.deg2rad(azim)

            r_xy = np.cos(elev_rad)
            x = r_xy * np.sin(azim_rad)
            y = r_xy * np.cos(azim_rad)
            z = np.sin(elev_rad)

            color = self.CONSTELLATION_COLORS.get(sys_prefix, '#94A3B8')
            sat_name = f"{lbl_char}{prn:02d}"

            # 落地射线
            l_line, = self.ax.plot([0, x], [0, y], [0, z], color=color, linestyle='--', linewidth=0.8, alpha=0.5, zorder=4)
            self._3d_dynamic_artists.append(l_line)

            edge_col = '#0F172A' if tokens['name'] == 'light' else '#FFFFFF'
            if is_used:
                sc = self.ax.scatter([x], [y], [z], s=260, color=color, edgecolors=edge_col, linewidths=1.6, alpha=0.95, zorder=6)
                tx = self.ax.text(x, y, z, sat_name, color='#FFFFFF', fontsize=8.0, fontweight='bold', ha='center', va='center', zorder=7)
            else:
                sc = self.ax.scatter([x], [y], [z], s=180, facecolors='none', edgecolors=color, linewidths=1.4, linestyle='--', alpha=0.85, zorder=5)
                tx = self.ax.text(x, y, z, sat_name, color=tokens['text_primary'], fontsize=7.5, fontweight='bold', ha='center', va='center', zorder=7)

            self._3d_dynamic_artists.extend([sc, tx])

        self.canvas.draw_idle()
