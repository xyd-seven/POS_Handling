# -*- coding: utf-8 -*-
"""
雷达极坐标天空图 (SkyPlot) 与 3D 空间立体天球穹顶 (3D SkyDome) 绘图组件
支持 2D 极坐标雷达盘、全时段抗跳变星轨及 3D 高性能水晶天穹多维可视化。
"""
import math
import numpy as np
import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from mpl_toolkits.mplot3d import Axes3D
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
        self.current_mode = 'polar' # 'polar' 或 '3d'
        self._last_elev_azim_3d = (28, -55) # 默认最佳透视视角
        self._3d_dynamic_artists = [] # 动态元素集合（卫星散点、落地线、文本），用于极速增量刷新
        self.init_polar_axes()

    def init_polar_axes(self):
        self.figure.clear()
        self.current_mode = 'polar'
        self._3d_dynamic_artists.clear()
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

    def init_3d_axes(self):
        # 记忆视角
        if self.current_mode == '3d' and hasattr(self.ax, 'elev') and hasattr(self.ax, 'azim'):
            if self.ax.elev is not None and self.ax.azim is not None:
                self._last_elev_azim_3d = (self.ax.elev, self.ax.azim)

        self.figure.clear()
        self.current_mode = '3d'
        self._3d_dynamic_artists.clear()
        self.ax = self.figure.add_subplot(111, projection='3d')
        self.figure.patch.set_facecolor('#0B1120')
        self.ax.set_facecolor('#0B1120')

        # 隐藏 3D 方形边框和底色面板
        self.ax.xaxis.set_pane_color((0.04, 0.07, 0.13, 0.0))
        self.ax.yaxis.set_pane_color((0.04, 0.07, 0.13, 0.0))
        self.ax.zaxis.set_pane_color((0.04, 0.07, 0.13, 0.0))
        self.ax.grid(False)
        self.ax.set_axis_off()

        # 设置显示范围与视角
        self.ax.set_xlim(-1.08, 1.08)
        self.ax.set_ylim(-1.08, 1.08)
        self.ax.set_zlim(-0.04, 1.08)
        self.ax.view_init(elev=self._last_elev_azim_3d[0], azim=self._last_elev_azim_3d[1])

        # 拉近相机距离并消除四周多余空白，让 3D 天穹饱满填充整个大屏幕
        try:
            self.ax.dist = 6.8
            self.ax.set_box_aspect([1.0, 1.0, 0.72])
        except Exception:
            pass
        self.figure.subplots_adjust(left=-0.10, right=1.10, bottom=-0.10, top=1.08)

        # 构建静态天球骨架与发光半球曲面 (常驻图层)
        self._build_static_3d_dome_layer()

    def _build_static_3d_dome_layer(self):
        """
        构建 3D 静态天穹网格、半透明发光曲面、地平底盘与球心观测站基座
        """
        # 1. 绘制半透明发光水晶天穹曲面 (Glass Dome Surface with subtle gradient)
        u_surf = np.linspace(0, 2 * np.pi, 36)
        v_surf = np.linspace(0, np.pi / 2, 16)
        U_surf, V_surf = np.meshgrid(u_surf, v_surf)
        X_surf = np.cos(V_surf) * np.sin(U_surf)
        Y_surf = np.cos(V_surf) * np.cos(U_surf)
        Z_surf = np.sin(V_surf)

        # 柔和科技蓝微光半球曲面
        self.ax.plot_surface(X_surf, Y_surf, Z_surf, color='#0284C7', alpha=0.07, shade=True, antialiased=True, zorder=1)

        # 2. 仰角同心纬度圈 (Elevation Rings: 0°, 30°, 60°)
        u_ring = np.linspace(0, 2 * np.pi, 60)
        for elev_deg in [0, 30, 60]:
            elev_rad = np.deg2rad(elev_deg)
            r_ring = np.cos(elev_rad)
            z_ring = np.sin(elev_rad)
            x_ring = r_ring * np.sin(u_ring)
            y_ring = r_ring * np.cos(u_ring)
            self.ax.plot(x_ring, y_ring, z_ring, color='#38BDF8' if elev_deg == 0 else '#334155', 
                         linestyle='-' if elev_deg == 0 else '--', linewidth=1.2 if elev_deg == 0 else 0.8, alpha=0.7, zorder=2)
            if elev_deg > 0:
                self.ax.text(0, r_ring, z_ring, f" {elev_deg}°", color='#94A3B8', fontsize=8, fontweight='bold', zorder=2)

        # 3. 10° 空间截止角红色虚线环 (Mask 10°)
        elev_mask = np.deg2rad(10)
        r_mask = np.cos(elev_mask)
        z_mask = np.sin(elev_mask)
        self.ax.plot(r_mask * np.sin(u_ring), r_mask * np.cos(u_ring), z_mask, color='#EF4444', linestyle=':', linewidth=1.2, alpha=0.65, zorder=2)

        # 4. 方位角经线射线 (Azimuth Meridians: 0°, 45°, 90°, ...)
        v_line = np.linspace(0, np.pi / 2, 20)
        for azim_deg in [0, 45, 90, 135, 180, 225, 270, 315]:
            azim_rad = np.deg2rad(azim_deg)
            x_line = np.cos(v_line) * np.sin(azim_rad)
            y_line = np.cos(v_line) * np.cos(azim_rad)
            z_line = np.sin(v_line)
            self.ax.plot(x_line, y_line, z_line, color='#334155', linestyle=':', linewidth=0.7, alpha=0.5, zorder=2)

        # 5. 地平底盘网格参考十字线与地平底面圆盘
        self.ax.plot([-1.05, 1.05], [0, 0], [0, 0], color='#1E293B', linestyle='-', linewidth=1.0, zorder=2)
        self.ax.plot([0, 0], [-1.05, 1.05], [0, 0], color='#1E293B', linestyle='-', linewidth=1.0, zorder=2)

        # 6. 四大主方位与天顶文字标识
        self.ax.text(0, 1.14, 0, "N (0°)", color='#38BDF8', fontsize=11, fontweight='bold', ha='center', va='center', zorder=3)
        self.ax.text(1.14, 0, 0, "E (90°)", color='#E2E8F0', fontsize=10, fontweight='bold', ha='center', va='center', zorder=3)
        self.ax.text(0, -1.14, 0, "S (180°)", color='#E2E8F0', fontsize=10, fontweight='bold', ha='center', va='center', zorder=3)
        self.ax.text(-1.14, 0, 0, "W (270°)", color='#E2E8F0', fontsize=10, fontweight='bold', ha='center', va='center', zorder=3)
        self.ax.text(0, 0, 1.06, "Zenith (90°)", color='#94A3B8', fontsize=9.5, fontweight='bold', ha='center', va='bottom', zorder=3)

        # 7. 球心地面观测站地标基座 [⊕]
        self.ax.scatter([0], [0], [0], s=80, color='#38BDF8', marker='o', edgecolors='#FFFFFF', linewidths=1.2, alpha=0.9, zorder=4)
        self.ax.text(0, 0, -0.04, "Antenna", color='#64748B', fontsize=7.5, fontweight='bold', ha='center', va='top', zorder=4)

    def render_snapshot(self, sats_dict, dop_dict=None, title_prefix=""):
        """
        渲染 2D 单时刻极坐标快照
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

            if elev <= 0.01 and azim <= 0.01:
                continue

            r = max(0.0, min(90.0, 90.0 - elev))
            theta = np.deg2rad(azim)

            color = self.CONSTELLATION_COLORS.get(sys_prefix, '#94A3B8')
            sat_name = f"{lbl_char}{prn:02d}"

            if is_used:
                self.ax.scatter(theta, r, s=280, color=color, edgecolors='#FFFFFF', linewidths=1.8, zorder=5)
                self.ax.text(theta, r, sat_name, color='#FFFFFF', fontsize=9.0, fontweight='bold',
                             ha='center', va='center', zorder=6)
            else:
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
        渲染 2D 全时段星轨运动图
        """
        self.init_polar_axes()

        theta_ring = np.linspace(0, 2*np.pi, 200)
        self.ax.plot(theta_ring, [80]*len(theta_ring), color='#EF4444', linestyle=':', linewidth=1.2, alpha=0.6)

        if not sat_tracks_dict:
            self.ax.text(0, 45, "无星轨轨迹数据", color='#94A3B8', fontsize=12, 
                         fontweight='bold', ha='center', va='center',
                         bbox=dict(boxstyle='round,pad=0.6', facecolor='#1E293B', edgecolor='#475569', alpha=0.9))
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
            lbl_char = 'B' if sys_prefix == 'BD' else ('G' if sys_prefix == 'GPS' else ('R' if sys_prefix == 'GL' else 'E'))

            sub_segments = []
            cur_seg = [valid_points[0]]

            for i in range(1, len(valid_points)):
                prev_t, prev_el, prev_az, _ = valid_points[i-1]
                t, el, az, _ = valid_points[i]

                dt = abs(t - prev_t)
                d_az = abs(az - prev_az)
                d_el = abs(el - prev_el)

                if d_az > 180:
                    d_az = 360 - d_az

                if dt > 30.0 or d_az > 25.0 or d_el > 20.0:
                    if len(cur_seg) > 1:
                        sub_segments.append(cur_seg)
                    cur_seg = [valid_points[i]]
                else:
                    cur_seg.append(valid_points[i])

            if len(cur_seg) > 1:
                sub_segments.append(cur_seg)

            for seg in sub_segments:
                azims = [p[2] for p in seg]
                elevs = [p[1] for p in seg]
                thetas = np.deg2rad(azims)
                radii = [90.0 - el for el in elevs]
                self.ax.plot(thetas, radii, color=color, linewidth=2.0, alpha=0.8, zorder=3)

            last_pt = valid_points[-1]
            last_theta = np.deg2rad(last_pt[2])
            last_r = 90.0 - last_pt[1]
            self.ax.scatter(last_theta, last_r, s=180, color=color, edgecolors='#FFFFFF', linewidths=1.2, zorder=5)
            self.ax.text(last_theta, last_r, f"{lbl_char}{prn:02d}", color='#FFFFFF', fontsize=8.0, fontweight='bold', ha='center', va='center', zorder=6)

        self.ax.set_title("全时段卫星运动星轨图 (Sky Tracks)", color='#F8FAFC', fontsize=12, fontweight='bold', pad=18)
        self.canvas.draw_idle()

    def render_3d_skydome(self, sats_dict, dop_dict=None, sat_tracks_dict=None, title_prefix="", show_tracks=True):
        """
        渲染 3D 空间立体水晶天穹 (3D SkyDome) - 支持增量图层更新与垂直落地虚线
        """
        if self.current_mode != '3d':
            self.init_3d_axes()
        else:
            # 增量清除上一帧的动态元素 (卫星散点、落地垂线、地面光斑与文字)，无需重构半球曲面与底盘网格
            for artist in self._3d_dynamic_artists:
                try:
                    artist.remove()
                except Exception:
                    pass
            self._3d_dynamic_artists.clear()

        # 1. 绘制 3D 空间立体星轨 (如果开启)
        if sat_tracks_dict and show_tracks:
            for sat_key, raw_track in sat_tracks_dict.items():
                if not raw_track:
                    continue
                valid_pts = [pt for pt in raw_track if pt[1] > 0.01 and pt[2] > 0.01 and 0 <= pt[1] <= 90]
                if not valid_pts:
                    continue

                sys_prefix, _ = sat_key
                color = self.CONSTELLATION_COLORS.get(sys_prefix, '#94A3B8')

                sub_segs = []
                c_seg = [valid_pts[0]]
                for i in range(1, len(valid_pts)):
                    prev_t, prev_el, prev_az, _ = valid_pts[i-1]
                    t, el, az, _ = valid_pts[i]
                    d_az = abs(az - prev_az)
                    if d_az > 180: d_az = 360 - d_az
                    if abs(t - prev_t) > 30.0 or d_az > 25.0:
                        if len(c_seg) > 1: sub_segs.append(c_seg)
                        c_seg = [valid_pts[i]]
                    else:
                        c_seg.append(valid_pts[i])
                if len(c_seg) > 1: sub_segs.append(c_seg)

                for seg in sub_segs:
                    if len(seg) > 80:
                        step = max(1, len(seg) // 80)
                        seg = seg[::step]
                    az_rad = np.deg2rad([p[2] for p in seg])
                    el_rad = np.deg2rad([p[1] for p in seg])
                    x_3d = np.cos(el_rad) * np.sin(az_rad)
                    y_3d = np.cos(el_rad) * np.cos(az_rad)
                    z_3d = np.sin(el_rad)
                    line_art = self.ax.plot(x_3d, y_3d, z_3d, color=color, linewidth=1.8, alpha=0.75, zorder=4)[0]
                    self._3d_dynamic_artists.append(line_art)

        # 2. 绘制当前时刻 3D 发光卫星球体、垂直落地虚线 (Drop Lines) 与地面光斑 (Footprints)
        if sats_dict:
            for sat_key, sat_info in sats_dict.items():
                sys_prefix = sat_info.get('sys_prefix', 'GPS')
                prn = sat_info.get('prn', 0)
                lbl_char = sat_info.get('lbl_char', 'G')
                elev = sat_info.get('elevation', 0.0)
                azim = sat_info.get('azimuth', 0.0)
                is_used = sat_info.get('is_used', False)

                if elev <= 0.01 and azim <= 0.01:
                    continue

                el_rad = np.deg2rad(elev)
                az_rad = np.deg2rad(azim)
                x = np.cos(el_rad) * np.sin(az_rad)
                y = np.cos(el_rad) * np.cos(az_rad)
                z = np.sin(el_rad)

                color = self.CONSTELLATION_COLORS.get(sys_prefix, '#94A3B8')
                sat_name = f"{lbl_char}{prn:02d}"

                # A. 绘制垂直落地投影虚线 (Drop Line: 从 (x, y, z) 直落到 (x, y, 0))
                drop_line = self.ax.plot([x, x], [y, y], [0, z], color=color, linestyle=':', linewidth=0.9, alpha=0.45, zorder=3)[0]
                self._3d_dynamic_artists.append(drop_line)

                # B. 绘制地面投影光环 (Ground Footprint: 增强空间高度感知)
                ground_spot = self.ax.scatter([x], [y], [0], s=32, facecolors='none', edgecolors=color, linewidths=1.0, alpha=0.55, zorder=3)
                self._3d_dynamic_artists.append(ground_spot)

                # C. 绘制 3D 卫星主体与文字标签 (尺寸放大更清晰)
                if is_used:
                    sat_dot = self.ax.scatter([x], [y], [z], s=280, color=color, edgecolors='#FFFFFF', linewidths=1.8, alpha=1.0, zorder=6)
                    sat_txt = self.ax.text(x, y, z + 0.045, sat_name, color='#FFFFFF', fontsize=9.5, fontweight='bold', ha='center', va='bottom', zorder=7)
                else:
                    sat_dot = self.ax.scatter([x], [y], [z], s=180, facecolors='none', edgecolors=color, linewidths=1.5, alpha=0.85, zorder=5)
                    sat_txt = self.ax.text(x, y, z + 0.035, sat_name, color='#94A3B8', fontsize=9.0, fontweight='bold', ha='center', va='bottom', zorder=7)

                self._3d_dynamic_artists.append(sat_dot)
                self._3d_dynamic_artists.append(sat_txt)

        title_str = f"{title_prefix} 3D 空间立体天穹 (3D SkyDome)" if title_prefix else "3D 空间立体天穹 (3D SkyDome)"
        if dop_dict:
            pdop = dop_dict.get('pdop', 1.0)
            hdop = dop_dict.get('hdop', 1.0)
            title_str += f"  [PDOP: {pdop:.1f} | HDOP: {hdop:.1f}]"

        self.ax.set_title(title_str, color='#F8FAFC', fontsize=12, fontweight='bold', pad=12)
        self.canvas.draw_idle()
