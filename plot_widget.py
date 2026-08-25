from theme_manager import ThemeManager
# -*- coding: utf-8 -*-
"""
Matplotlib 嵌入 Qt(PySide6) 的图表展示组件 (双向自适应格网与Tab拆分版)
"""
import sys
import math
import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as patches
import matplotlib.gridspec as gridspec

# 设置中文及负号显示支持
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

class PlotWidget(FigureCanvas):
    sig_hover_time = Signal(float)   # 鼠标悬停时间信号 (UTC 秒)
    sig_click_time = Signal(float)   # 鼠标点击时间信号 (UTC 秒)

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#FFFFFF')
        self.gs_split = gridspec.GridSpec(2, 1)
        self.gs_full = gridspec.GridSpec(1, 1)
        self.ax = self.fig.add_subplot(111)
        self.ax_sats = None
        self.ax_sats_twin = None
        self.is_maximized = False
        self.maximized_ax = None
        self.cursor_artists = []
        self.cursor_time = None
        self.enable_time_sync = False
        self.current_segments = []
        self.current_x_mode = '历元数'
        self.current_tab_name = 'epoch_h'
        self.show_confidence_rings = False
        self.enable_time_sync = False
        super().__init__(self.fig)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.fig.canvas.mpl_connect('button_press_event', self.on_mouse_click)
        self.setParent(parent)
        self.downsample_threshold = 100000
        self.min_downsample_points = 2000
        self.max_downsample_points = 50000
        self.theme_manager = ThemeManager()
        self.theme_manager.sig_theme_changed.connect(self.apply_theme)

    def resizeEvent(self, event):
        # 必须调用 FigureCanvasQTAgg 的原生 resizeEvent，以正确适配 Windows 高分屏 (150%/200% DPI 缩放)
        super().resizeEvent(event)
        if getattr(self, 'cursor_time', None) is not None and getattr(self, 'ax', None) is not None:
            self.draw_idle()
        
    def on_mouse_move(self, event):
        if not getattr(self, 'enable_time_sync', False) or event.inaxes is None or event.xdata is None:
            return
        # 仅在时序图 (X 轴表示历元秒) 上分发
        self.sig_hover_time.emit(float(event.xdata))

    def on_mouse_click(self, event):
        if not getattr(self, 'enable_time_sync', False) or event.inaxes is None or event.xdata is None:
            return
        if event.button == 1 and not event.dblclick:
            x_val = float(event.xdata)
            t_sec = x_val
            if getattr(self, 'current_x_mode', '历元数') == '历元数' and getattr(self, 'current_segments', None):
                for s in self.current_segments:
                    if s.get('active', True) and s.get('epochs'):
                        epochs = s['epochs']
                        idx = int(round(x_val)) - 1
                        if 0 <= idx < len(epochs):
                            t_sec = float(epochs[idx].get('utc_time_sec', epochs[idx].get('time', 0)))
                            break
            # 1. 本地立即 0 延迟刷新当前图表的时间线 Overlay
            self.update_cursor_overlay(t_sec)
            # 2. 发射信号广播给其它 Tab 和天空图
            self.sig_click_time.emit(t_sec)


    def apply_theme(self, tokens=None):
        if tokens is None:
            tokens = ThemeManager().get_tokens()
        self.fig.patch.set_facecolor(tokens['plot_fig_bg'])
        for ax in self.fig.axes:
            if ax is not None:
                ax.set_facecolor(tokens['plot_ax_bg'])
                ax.tick_params(colors=tokens['plot_text'], labelcolor=tokens['plot_text'])
                for spine in ax.spines.values():
                    spine.set_color(tokens['plot_spine'])
                if hasattr(ax, 'title') and ax.title:
                    ax.title.set_color(tokens['plot_text'])
                if hasattr(ax, 'xaxis') and ax.xaxis.label:
                    ax.xaxis.label.set_color(tokens['plot_text'])
                if hasattr(ax, 'yaxis') and ax.yaxis.label:
                    ax.yaxis.label.set_color(tokens['plot_text'])
                leg = ax.get_legend()
                if leg:
                    leg.get_frame().set_facecolor(tokens['plot_legend_bg'])
                    leg.get_frame().set_edgecolor(tokens['plot_legend_border'])
                    for text in leg.get_texts():
                        text.set_color(tokens['plot_text'])
                    if leg.get_title():
                        leg.get_title().set_color(tokens['plot_text'])
        self.draw_idle()

    def clear_canvas(self):
        self.fig.clear()
        self.ax = None
        self.ax_sats = None
        self.ax_sats_twin = None
        self.is_maximized = False
        self.maximized_ax = None
        
        # Connect double-click event if not already connected
        if not hasattr(self, 'cid_dblclick'):
            self.cid_dblclick = self.fig.canvas.mpl_connect('button_press_event', self.on_double_click)

    def _target_plot_points(self):
        width_px = max(1, int(self.figure.bbox.width))
        target = width_px * 4
        return max(self.min_downsample_points, min(self.max_downsample_points, target))

    def _downsample_minmax(self, x_values, y_values):
        total_pts = len(y_values)
        target_points = self._target_plot_points()
        if total_pts <= target_points:
            return x_values, y_values

        chunk_size = max(1, total_pts // max(1, target_points // 2))
        n_chunks = total_pts // chunk_size
        trunc_pts = n_chunks * chunk_size
        y_trunc = y_values[:trunc_pts].reshape((n_chunks, chunk_size))

        max_idx = np.argmax(y_trunc, axis=1) + np.arange(n_chunks) * chunk_size
        min_idx = np.argmin(y_trunc, axis=1) + np.arange(n_chunks) * chunk_size

        indices = np.sort(np.concatenate([max_idx, min_idx]))
        if indices[0] != 0:
            indices = np.insert(indices, 0, 0)
        if indices[-1] != total_pts - 1:
            indices = np.append(indices, total_pts - 1)
        indices = np.unique(indices)

        return x_values[indices], y_values[indices]
            
    def on_double_click(self, event):
        if not event.dblclick or not getattr(self, 'ax_sats', None):
            return
            
        ax_twin = getattr(self, 'ax_sats_twin', None)
        
        if self.is_maximized:
            # Restore split view
            self.ax.set_subplotspec(self.gs_split[0, 0])
            self.ax_sats.set_subplotspec(self.gs_split[1, 0])
            if ax_twin:
                ax_twin.set_subplotspec(self.gs_split[1, 0])
                
            self.ax.set_visible(True)
            self.ax_sats.set_visible(True)
            if ax_twin:
                ax_twin.set_visible(True)
                
            self.is_maximized = False
            self.maximized_ax = None
        else:
            # Maximize the clicked view
            target_ax = event.inaxes
            
            # 如果用户双击在了图表外的空白处(title, 坐标轴标签等)，通过 Y 像素坐标来暴力推断
            if target_ax is None:
                if event.y > self.fig.bbox.height * 0.45:
                    target_ax = self.ax
                else:
                    target_ax = self.ax_sats
                    
            if target_ax == self.ax:
                self.ax.set_subplotspec(self.gs_full[0, 0])
                self.ax_sats.set_visible(False)
                if ax_twin:
                    ax_twin.set_visible(False)
                self.is_maximized = True
                self.maximized_ax = self.ax
            elif target_ax in [self.ax_sats, ax_twin]:
                self.ax_sats.set_subplotspec(self.gs_full[0, 0])
                if ax_twin:
                    ax_twin.set_subplotspec(self.gs_full[0, 0])
                self.ax.set_visible(False)
                self.is_maximized = True
                self.maximized_ax = self.ax_sats
            else:
                return
                
        # Draw idle is needed for relayout 
        self.fig.canvas.draw_idle()
        
    def _remove_existing_cursor_artists(self):
        for artist in list(getattr(self, 'cursor_artists', [])):
            try:
                artist.remove()
            except Exception:
                pass
        self.cursor_artists = []

    def update_cursor_overlay(self, cursor_time=None):
        if cursor_time is not None:
            self.cursor_time = cursor_time
        if not getattr(self, 'enable_time_sync', False) or self.cursor_time is None:
            self._remove_existing_cursor_artists()
            self.fig.canvas.draw_idle()
            return

        target_axes = []
        tab_name = getattr(self, 'current_tab_name', 'epoch_h')
        if tab_name == 'epoch_enu':
            for a in [getattr(self, 'ax_e', None), getattr(self, 'ax_n', None), getattr(self, 'ax_u', None)]:
                if a is not None:
                    target_axes.append(a)
        elif tab_name == 'speed':
            for a in [getattr(self, 'ax_speed', None), getattr(self, 'ax_speed_err', None)]:
                if a is not None:
                    target_axes.append(a)
        else:
            if getattr(self, 'ax', None) is not None:
                target_axes.append(self.ax)
            if getattr(self, 'ax_sats', None) is not None:
                target_axes.append(self.ax_sats)

        if not target_axes:
            return

        self._remove_existing_cursor_artists()

        cx = None
        target_info = None
        segments = getattr(self, 'current_segments', [])
        x_axis_mode = getattr(self, 'current_x_mode', '历元数')

        for s in segments:
            if s.get('active', True) and s.get('epochs'):
                epochs = s['epochs']
                m = s.get('metrics', {})
                t_list = [ep.get('utc_time_sec', ep.get('time', 0)) for ep in epochs]
                if t_list:
                    t_arr = np.array(t_list)
                    idx = int(np.argmin(np.abs(t_arr - self.cursor_time)))
                    if abs(t_arr[idx] - self.cursor_time) <= 5.0:
                        ep = epochs[idx]
                        sec = int(ep.get('utc_time_sec', ep.get('time', 0))) % 86400
                        time_str = f"{sec//3600:02d}:{(sec%3600)//60:02d}:{sec%60:02d}"
                        q = ep.get('quality', 1)
                        q_map = {4: "RTK固定(4)", 5: "RTK浮点(5)", 2: "差分(2)", 1: "单点(1)", 0: "无效(0)"}
                        q_str = q_map.get(q, f"状态({q})")
                        
                        err_str = ""
                        if tab_name == 'epoch_h' and m.get('h_errors') and idx < len(m['h_errors']):
                            err_str = f"误差: {m['h_errors'][idx]:.3f}m"
                        elif tab_name == 'epoch_v' and m.get('v_errors') and idx < len(m['v_errors']):
                            err_str = f"误差: {m['v_errors'][idx]:+.3f}m"
                        elif tab_name == 'speed':
                            v_err = m.get('speed_errors', [])
                            if v_err and idx < len(v_err):
                                err_str = f"误差: {v_err[idx]:+.2f}m/s"
                        elif tab_name == 'epoch_enu' and m.get('de') and m.get('dn') and m.get('v_errors'):
                            if idx < len(m['de']) and idx < len(m['dn']) and idx < len(m['v_errors']):
                                err_str = f"E:{m['de'][idx]:+.2f} N:{m['dn'][idx]:+.2f} U:{m['v_errors'][idx]:+.2f}m"
                        
                        if x_axis_mode == '时间轴':
                            cx = t_arr[idx]
                        else:
                            cx = idx + 1
                            
                        target_info = {
                            'epoch': idx + 1,
                            'time_str': time_str,
                            'err_str': err_str,
                            'quality_str': q_str
                        }
                        break

        if cx is not None:
            for i, ax_item in enumerate(target_axes):
                orig_xlim = ax_item.get_xlim()
                # 如果坐标轴范围未初始化或异常，使用合理范围
                if orig_xlim == (0.0, 1.0) and segments:
                    max_len = max([len(s.get('epochs', [])) for s in segments if s.get('active', True)] or [1])
                    if x_axis_mode == '历元数':
                        orig_xlim = (0, max_len + 1)
                        ax_item.set_xlim(orig_xlim)
                        
                if orig_xlim[0] <= cx <= orig_xlim[1]:
                    try:
                        line = ax_item.axvline(x=cx, color='#F59E0B', linestyle='--', linewidth=1.8, alpha=0.9, zorder=10)
                        self.cursor_artists.append(line)
                        if target_info and i == 0:
                            parts = [f"#{target_info['epoch']}", target_info['time_str']]
                            if target_info['err_str']:
                                parts.append(target_info['err_str'])
                            parts.append(target_info['quality_str'])
                            txt = " | ".join(parts)
                            
                            ylim = ax_item.get_ylim()
                            y_pos = ylim[1] - (ylim[1] - ylim[0]) * 0.08
                            ha = 'left' if cx < (orig_xlim[0] + orig_xlim[1]) / 2 else 'right'
                            bubble = ax_item.text(cx, y_pos, txt, color='#0F172A', fontsize=9, fontweight='bold',
                                                 bbox=dict(boxstyle="round,pad=0.25", fc='#FEF3C7', ec='#F59E0B', lw=1.0, alpha=0.95),
                                                 zorder=11, ha=ha)
                            self.cursor_artists.append(bubble)
                    except Exception:
                        pass
                ax_item.set_xlim(orig_xlim)
        
        self.fig.canvas.draw_idle()

    def _draw_cursor_line(self, ax, cursor_time, segments, x_axis_mode, tab_name='epoch_h'):
        self.update_cursor_overlay(cursor_time)

    def render_data(self, tab, segments, truth=None, time_zone='UTC', show_absolute_alt=False, show_extrema=True, x_axis_mode='历元数', show_sats=False, show_raw_alt=False, show_stats=True, speed_unit='m/s', cdf_mode='horizontal', show_quantiles=True, show_confidence_rings=False, cursor_time=None, enable_time_sync=False):
        self.clear_canvas()
        
        # 在最开头完整初始化并记录当前图表的所有状态
        self.enable_time_sync = enable_time_sync
        self.cursor_time = cursor_time
        self.current_segments = segments
        self.current_x_mode = x_axis_mode
        self.current_tab_name = tab
        
        if tab == 'epoch_enu':
            axs = self.fig.subplots(3, 1, sharex=True)
            self.ax_e = axs[0]
            self.ax_n = axs[1]
            self.ax_u = axs[2]
            for a in axs:
                a.set_facecolor('#FFFFFF')
            self.draw_epoch_enu(segments, truth, time_zone, x_axis_mode, show_stats)
            self.update_cursor_overlay(cursor_time)
            self.fig.subplots_adjust(left=0.08, right=0.98, top=0.96, bottom=0.08, hspace=0.15)
            self.draw()
            return

        if tab == 'speed':
            axs = self.fig.subplots(2, 1, sharex=True)
            self.ax_speed = axs[0]
            self.ax_speed_err = axs[1]
            for a in axs:
                a.set_facecolor('#FFFFFF')
            self.draw_speed_comparison(segments, truth, time_zone, x_axis_mode, speed_unit, show_stats)
            self.update_cursor_overlay(cursor_time)
            self.fig.subplots_adjust(left=0.08, right=0.98, top=0.95, bottom=0.09, hspace=0.18)
            self.draw()
            return

        if tab == 'cdf':
            self.ax = self.fig.add_subplot(1, 1, 1)
            self.ax.set_facecolor('#FFFFFF')
            self.draw_cdf(segments, truth, cdf_mode, speed_unit, show_quantiles)
            self.fig.subplots_adjust(left=0.08, right=0.98, top=0.94, bottom=0.10)
            self.draw()
            return
            
        if tab in ['epoch_h', 'epoch_v'] and show_sats:
            self.ax = self.fig.add_subplot(self.gs_split[0, 0])
            self.ax_sats = self.fig.add_subplot(self.gs_split[1, 0], sharex=self.ax)
            self.ax.set_facecolor('#FFFFFF')
            self.ax_sats.set_facecolor('#FFFFFF')
        else:
            self.ax = self.fig.add_subplot(111)
            self.ax.set_facecolor('#FFFFFF')
        
        self.enable_time_sync = enable_time_sync
        self.cursor_time = cursor_time
        self.current_segments = segments
        self.current_x_mode = x_axis_mode
        self.current_tab_name = tab

        if tab == 'scatter':
            self.draw_scatter(segments, truth, show_confidence_rings=show_confidence_rings, cursor_time=cursor_time)
        elif tab == 'status':
            self.draw_status(segments)
        elif tab == 'epoch_h':
            self.draw_epoch_horizontal(segments, time_zone, show_extrema, x_axis_mode, show_sats)
            self._draw_cursor_line(self.ax, cursor_time, segments, x_axis_mode, tab)
        elif tab == 'epoch_v':
            self.draw_epoch_vertical(segments, time_zone, show_absolute_alt, show_extrema, x_axis_mode, show_sats, show_raw_alt)
            self._draw_cursor_line(self.ax, cursor_time, segments, x_axis_mode, tab)
        elif tab == 'trajectory':
            self.draw_trajectory_2d(segments, truth)
            
        if tab != 'status' and hasattr(self, 'ax') and self.ax is not None:
            try:
                import matplotlib.ticker as ticker
                y_formatter = ticker.ScalarFormatter(useOffset=False)
                y_formatter.set_scientific(False)
                self.ax.yaxis.set_major_formatter(y_formatter)
            except Exception:
                pass
            
        if tab == 'scatter':
            # 极大化靶心圆在画布中的填充比例，去除不必要的空白边距
            self.fig.subplots_adjust(left=0.01, right=0.99, top=0.92, bottom=0.01)
        elif tab == 'status':
            self.fig.subplots_adjust(left=0.20, right=0.95, top=0.88, bottom=0.25)
        elif tab == 'trajectory':
            self.fig.subplots_adjust(left=0.1, right=0.95, top=0.92, bottom=0.1)
        else:
            if show_sats:
                self.fig.subplots_adjust(left=0.1, right=0.88, top=0.92, bottom=0.12, hspace=0.35)
            else:
                self.fig.subplots_adjust(left=0.1, right=0.95, top=0.92, bottom=0.15)
        self.apply_theme()
        self.draw()

    def draw_trajectory_2d(self, segments, truth):
        """
        绘制绝对二维轨迹投影图
        """
        active_segments = [s for s in segments if s.get('active', True) and s.get('metrics') and s.get('epochs')]
        
        has_data = False
        
        # 如果是动态真值，先画黑色虚线真值轨迹
        if truth and truth.get('mode') == 'dynamic' and truth.get('epochs'):
            t_lons = [ep['lon'] for ep in truth['epochs']]
            t_lats = [ep['lat'] for ep in truth['epochs']]
            
            total_pts = len(t_lons)
            if total_pts > self.downsample_threshold:
                step = max(1, total_pts // (self.downsample_threshold // 2))
                plot_x = t_lons[::step]
                plot_y = t_lats[::step]
            else:
                plot_x = t_lons
                plot_y = t_lats
                
            self.ax.plot(plot_x, plot_y, color='black', linestyle='--', linewidth=1.5, marker='.', markersize=3, label="动态参考真值 (Truth)", zorder=10)
            has_data = True
            
        for seg in active_segments:
            epochs = seg['epochs']
            if not epochs:
                continue
                
            lons = [ep['lon'] for ep in epochs]
            lats = [ep['lat'] for ep in epochs]
            
            total_pts = len(lons)
            if total_pts > self.downsample_threshold:
                step = max(1, total_pts // (self.downsample_threshold // 2))
                plot_x = lons[::step]
                plot_y = lats[::step]
            else:
                plot_x = lons
                plot_y = lats
                
            self.ax.plot(plot_x, plot_y, color=seg['color'], linestyle='-', linewidth=2.0, marker='.', markersize=4, alpha=1.0, label=seg['name'])
            has_data = True
            
        if not has_data:
            self.ax.text(0.5, 0.5, "暂无轨迹数据可供绘制", ha='center', va='center', fontsize=12, color='#64748B')
            return
            
        self.ax.grid(True, axis='both', color='#CBD5E1', linestyle='--', linewidth=0.5)
        self.ax.set_title("绝对二维轨迹投影图 (经纬度)", fontsize=14, fontweight='bold', pad=10)
        self.ax.set_xlabel("经度 (Longitude)", fontsize=11, color='#475569')
        self.ax.set_ylabel("纬度 (Latitude)", fontsize=11, color='#475569')
        
        self.ax.tick_params(axis='both', labelsize=10)
        
        # 禁用科学计数法，防止经纬度被压缩为 offset
        self.ax.ticklabel_format(useOffset=False, style='plain')
        
        # 修正墨卡托投影比例（防止图形被拉伸）
        y_lim = self.ax.get_ylim()
        mean_lat = (y_lim[0] + y_lim[1]) / 2.0
        aspect_ratio = 1.0 / math.cos(math.radians(mean_lat))
        self.ax.set_aspect(aspect_ratio)
        
        self.ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=5, fontsize=10, frameon=True, facecolor='#FFFFFF', edgecolor='#CBD5E1')

    def draw_scatter(self, segments, truth, show_confidence_rings=False, cursor_time=None):
        """
        绘制自适应高精度靶心图
        """
        max_dist = 0.01  # 最小底限 1 厘米
        active_segments = [s for s in segments if s.get('active', True) and s.get('metrics')]
        
        # 按精度散布范围（如 CEP68）从大到小对分段进行排序，确保高精度的密集点集（小范围）绘制在低精度点集（大范围）的上方，不会被覆盖
        active_segments = sorted(active_segments, key=lambda s: s['metrics'].get('cep68', 0), reverse=True)
        
        for seg in active_segments:
            m = seg['metrics']
            de_list = m.get('de', [])
            dn_list = m.get('dn', [])
            if not de_list:
                continue
                
            e_coords = de_list
            n_coords = dn_list
            
            if e_coords:
                e_arr = np.array(e_coords)
                n_arr = np.array(n_coords)
                dists = np.hypot(e_arr, n_arr)
                if len(dists) > 0:
                    max_dist = max(max_dist, float(np.max(dists)))
                    
            self.ax.scatter(e_coords, n_coords, s=25, color=seg['color'], marker='x',
                            linewidths=1.8, alpha=1.0, label=seg['name'], zorder=3)
            
            # 去掉 CEP68 的圆圈标线
            pass
            
        limit = max_dist * 1.15
        self.ax.set_xlim(-limit, limit)
        self.ax.set_ylim(-limit, limit)
        
        # --- 核心算法：以 10 为底的指数对数步长算法，实现等间距圆圈网格线完美自适应 ---
        raw_step = limit / 5.0
        if raw_step <= 0:
            raw_step = 0.01
        exponent = math.floor(math.log10(raw_step))
        fraction = raw_step / (10 ** exponent)
        if fraction < 1.5:
            nice_step = 1.0
        elif fraction < 3.0:
            nice_step = 2.0
        elif fraction < 7.0:
            nice_step = 5.0
        else:
            nice_step = 10.0
        step = nice_step * (10 ** exponent)
        # --------------------------------------------------------------------------
        
        circles_to_draw = np.arange(step, limit, step)
        for r in circles_to_draw:
            # 调深网格线颜色：从 #CBD5E1 改为 #94A3B8
            grid_circle = patches.Circle((0, 0), r, fill=False, color='#94A3B8', linestyle='-', linewidth=0.7, zorder=1)
            self.ax.add_patch(grid_circle)
            
            # 圆格标尺文字显示 (放置于下方偏右 45 度位置)
            anno_x = r * 0.707
            anno_y = -r * 0.707
            self.ax.text(anno_x, anno_y, f"{r:.3f}m", color='#475569', fontsize=10, ha='center', va='center')
            
        # 调深轴线颜色：从 #94A3B8 改为 #475569
        self.ax.axhline(0, color='#475569', linewidth=1.0, linestyle='-', zorder=1)
        self.ax.axvline(0, color='#475569', linewidth=1.0, linestyle='-', zorder=1)
        
        # 隐藏外框方形 Spine 以及坐标轴刻度和标签以匹配千寻的清爽界面
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        
        # 在圆环四周边缘添加指南针方向标签 N, S, E, W
        self.ax.text(0, limit * 0.98, "N", ha='center', va='top', fontsize=12, fontweight='bold', color='#0F172A')
        self.ax.text(0, -limit * 0.98, "S", ha='center', va='bottom', fontsize=12, fontweight='bold', color='#0F172A')
        self.ax.text(limit * 0.98, 0, "E", ha='right', va='center', fontsize=12, fontweight='bold', color='#0F172A')
        self.ax.text(-limit * 0.98, 0, "W", ha='left', va='center', fontsize=12, fontweight='bold', color='#0F172A')
        
        # --- 置信圆环绘制 (CEP 50%, R95 95%, 2DRMS 98%) ---
        if show_confidence_rings and active_segments:
            all_de = []
            all_dn = []
            for s in active_segments:
                m = s.get('metrics', {})
                all_de.extend(m.get('de', []))
                all_dn.extend(m.get('dn', []))
            if all_de and all_dn:
                arr_de = np.array(all_de)
                arr_dn = np.array(all_dn)
                d_2d = np.hypot(arr_de, arr_dn)
                c_50 = float(np.percentile(d_2d, 50))
                r_95 = float(np.percentile(d_2d, 95))
                rms_2d = float(np.sqrt(np.mean(d_2d**2)))
                drms_98 = 2.0 * rms_2d

                c_68 = float(np.percentile(d_2d, 68.3))
                # 1. 绘制 50% 置信圆 (CEP50) 绿色虚线
                circle_cep = patches.Circle((0, 0), c_50, fill=False, color='#10B981', linestyle='--', linewidth=1.5, zorder=4, label=f'50%: {c_50:.3f}m')
                self.ax.add_patch(circle_cep)
                
                # 2. 绘制 68% 置信圆 (2D-RMS / 68%) 橙色虚线
                circle_68 = patches.Circle((0, 0), c_68, fill=False, color='#F59E0B', linestyle='--', linewidth=1.6, zorder=4, label=f'68%: {c_68:.3f}m')
                self.ax.add_patch(circle_68)

                # 3. 绘制 95% 置信圆 (R95 / 95%) 蓝色点划线
                circle_r95 = patches.Circle((0, 0), r_95, fill=False, color='#3B82F6', linestyle='-.', linewidth=1.6, zorder=4, label=f'95%: {r_95:.3f}m')
                self.ax.add_patch(circle_r95)

        # --- 高亮联动选中的历元点 ---
        if cursor_time is not None and active_segments:
            for s in active_segments:
                m = s.get('metrics', {})
                times = s.get('times', [])
                de_list = m.get('de', [])
                dn_list = m.get('dn', [])
                if times and len(times) == len(de_list):
                    t_arr = np.array(times)
                    idx = np.argmin(np.abs(t_arr - cursor_time))
                    if abs(t_arr[idx] - cursor_time) <= 1.5:
                        hl_e = de_list[idx]
                        hl_n = dn_list[idx]
                        self.ax.scatter([hl_e], [hl_n], s=160, color='#F59E0B', marker='o', edgecolors='#FFFFFF', linewidths=2.0, zorder=6, label='当前选中点')
                        break

        self.ax.set_title("定位偏差分布图 (靶心图)", fontsize=14, fontweight='bold', pad=10)
        self.ax.grid(False)
        if active_segments:
            self.ax.legend(loc='upper right', framealpha=0.9, fontsize=9)
        self.ax.set_aspect('equal', adjustable='box', anchor='C')
        self.ax.set_anchor('C')

    def draw_status(self, segments):
        active_segments = [s for s in segments if s.get('active', True) and s.get('epochs')]
        
        if not active_segments:
            self.ax.text(0.5, 0.5, "暂无数据以进行定位质量分析", ha='center', va='center', fontsize=12, color='#64748B')
            for spine in self.ax.spines.values():
                spine.set_visible(False)
            self.ax.set_xticks([])
            self.ax.set_yticks([])
            return

        quality_map = {
            4: ('RTK固定解 (4)', '#10B981', 'RTK固定'),
            5: ('RTK浮点解 (5)', '#F59E0B', 'RTK浮点'),
            2: ('伪距差分 (2)', '#3B82F6', '伪距差分'),
            1: ('单点定位 (1)', '#94A3B8', '单点定位'),
            0: ('无效解 (0)', '#EF4444', '无效解')
        }
        quality_keys = [4, 5, 2, 1, 0]

        num_segs = len(active_segments)
        
        # 针对多分段场景动态分配子图
        if num_segs > 1:
            self.fig.clear()
            cols = min(num_segs, 3)
            rows = (num_segs + cols - 1) // cols
            
            for idx, seg in enumerate(active_segments):
                ax_sub = self.fig.add_subplot(rows, cols, idx + 1)
                ax_sub.set_facecolor('#FFFFFF')
                self._draw_single_status_pie(ax_sub, seg, quality_map, quality_keys, is_multi=True)
                
            self.fig.subplots_adjust(left=0.03, right=0.97, top=0.91, bottom=0.18, wspace=0.15, hspace=0.30)
        else:
            # 单分段呈现大号实心饼图与右侧统计面板
            self.ax.clear()
            self.ax.set_facecolor('#FFFFFF')
            seg = active_segments[0]
            self._draw_single_status_pie(self.ax, seg, quality_map, quality_keys, is_multi=False)
            self.fig.subplots_adjust(left=0.08, right=0.95, top=0.92, bottom=0.08)

    def _draw_single_status_pie(self, ax, seg, quality_map, quality_keys, is_multi=False):
        qualities = np.array([ep.get('quality', 0) for ep in seg['epochs']])
        total = len(qualities)
        if total == 0:
            ax.text(0.5, 0.5, f"{seg['name']}\n暂无历元数据", ha='center', va='center', fontsize=12, color='#64748B')
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.set_xticks([])
            ax.set_yticks([])
            return

        counts = {}
        for k in quality_keys:
            if k == 0:
                counts[0] = np.sum(~np.isin(qualities, quality_keys[:-1]))
            else:
                counts[k] = np.sum(qualities == k)

        sizes = []
        colors = []
        labels = []
        legend_labels = []

        for k in quality_keys:
            cnt = counts[k]
            pct = (cnt / total) * 100.0 if total > 0 else 0.0
            name, color, short_name = quality_map[k]
            if cnt > 0:
                sizes.append(cnt)
                colors.append(color)
                # 只有占比大于 4% 才在扇区内显示名称与百分比
                if pct >= 5.0:
                    labels.append(f"{short_name}\n{pct:.1f}%")
                elif pct >= 3.0:
                    labels.append(f"{pct:.1f}%")
                else:
                    labels.append("")
                legend_labels.append(f"{name}: {cnt:,} ({pct:.2f}%)")

        # 绘制完整实心圆形饼图 (Full Solid Pie Chart)
        wedges, texts = ax.pie(
            sizes,
            labels=labels,
            labeldistance=0.62,
            colors=colors,
            startangle=90,
            counterclock=False,
            wedgeprops=dict(edgecolor='white', linewidth=1.5),
            textprops=dict(color='white', fontsize=11 if not is_multi else 10, fontweight='bold')
        )

        ax.set_aspect('equal')
        title_fs = 13 if not is_multi else 12
        seg_name = seg.get('name', '待测分段')
        ax.set_title(f"{seg_name} 定位解状态占比分布", fontsize=title_fs, fontweight='bold', pad=12, color='#0F172A')

        if not is_multi:
            # 单图模式下在右侧绘制详细统计卡片
            ax.legend(
                wedges,
                legend_labels,
                title=f"历元统计汇总: {total:,} pts",
                title_fontsize=12,
                loc='center left',
                bbox_to_anchor=(1.05, 0.5),
                fontsize=11,
                frameon=True,
                facecolor='#F8FAFC',
                edgecolor='#CBD5E1',
                borderpad=1.0,
                labelspacing=0.8
            )
        else:
            # 多图模式下在下方绘制清晰放大的统计卡片
            ax.legend(
                wedges,
                legend_labels,
                title=f"总历元数: {total:,} pts",
                title_fontsize=11,
                loc='upper center',
                bbox_to_anchor=(0.5, -0.06),
                fontsize=10.5,
                ncol=2 if len(legend_labels) > 2 else 1,
                frameon=True,
                facecolor='#F8FAFC',
                edgecolor='#E2E8F0',
                borderpad=0.6,
                labelspacing=0.5
            )

    def draw_epoch_horizontal(self, segments, time_zone='UTC', show_extrema=True, x_axis_mode='历元数', show_sats=False):
        """
        绘制水平位置误差历元分布图 (可选择历元数或时间轴展示)
        """
        active_segments = [s for s in segments if s.get('active', True) and s.get('metrics') and s.get('epochs')]
        
        if not active_segments:
            self.ax.text(0.5, 0.5, "暂无数据以进行水平历元曲线绘制", ha='center', va='center', fontsize=12, color='#64748B')
            return
            
        for seg in active_segments:
            epochs = seg['epochs']
            m = seg['metrics']
            h_errors_list = m.get('h_errors', [])
            if not h_errors_list:
                continue
                
            h_errors = np.array(h_errors_list)
            
            if x_axis_mode == '时间轴':
                x = np.array([ep['utc_time_sec'] for ep in epochs[:len(h_errors)]])
            else:
                x = np.arange(1, len(h_errors) + 1)
                
            plot_x, plot_y = self._downsample_minmax(x, h_errors)
            
            marker_style = 'o' if len(plot_x) <= 5000 else 'none'
            self.ax.plot(plot_x, plot_y, color=seg['color'], marker=marker_style, markersize=4, 
                         markeredgecolor='none', label=seg['name'], linewidth=2.0, alpha=1.0)
                         
            # 标注并突出显示最大值与最小值点
            if show_extrema and len(h_errors) > 0:
                max_idx = np.argmax(h_errors)
                min_idx = np.argmin(h_errors)
                
                # 时间格式化辅助函数
                def get_x_label(x_val):
                    if x_axis_mode == '时间轴':
                        val = x_val
                        if time_zone == 'Beijing':
                            val += 8 * 3600
                        secs = int(val) % 86400
                        return f"{secs // 3600:02d}:{(secs % 3600) // 60:02d}:{secs % 60:02d}"
                    return str(int(x_val))
                
                # 最大值 (红点高亮)
                x_max = x[max_idx]
                y_max = h_errors[max_idx]
                self.ax.plot(x_max, y_max, marker='o', markersize=6, color='#EF4444', markeredgecolor='black', zorder=5)
                self.ax.annotate(f"[{get_x_label(x_max)}, {y_max:.4f}]", (x_max, y_max), textcoords="offset points", 
                                 xytext=(5, 5), ha='left', fontsize=10, color='#0F172A', fontweight='bold',
                                 bbox=dict(boxstyle="round,pad=0.2", fc='#FFEBEB', ec='#EF4444', lw=0.5, alpha=0.85))
                
                # 最小值 (绿点高亮)
                x_min = x[min_idx]
                y_min = h_errors[min_idx]
                self.ax.plot(x_min, y_min, marker='o', markersize=6, color='#10B981', markeredgecolor='black', zorder=5)
                self.ax.annotate(f"[{get_x_label(x_min)}, {y_min:.4f}]", (x_min, y_min), textcoords="offset points", 
                                 xytext=(5, -12), ha='left', fontsize=10, color='#0F172A', fontweight='bold',
                                 bbox=dict(boxstyle="round,pad=0.2", fc='#EBFDF5', ec='#10B981', lw=0.5, alpha=0.85))
        
        # 格式化 X 轴刻度及标签
        if x_axis_mode == '时间轴':
            from matplotlib.ticker import FuncFormatter
            def make_time_formatter(tz):
                def formatter(x_val, pos):
                    val = x_val
                    if tz == 'Beijing':
                        val += 8 * 3600
                    secs = int(val) % 86400
                    return f"{secs // 3600:02d}:{(secs % 3600) // 60:02d}:{secs % 60:02d}"
                return formatter
            self.ax.xaxis.set_major_formatter(FuncFormatter(make_time_formatter(time_zone)))
            self.ax.tick_params(axis='x', rotation=15, labelsize=10, colors='#0F172A')
            self.ax.set_xlabel("时间", fontsize=11)
        else:
            import matplotlib.ticker as ticker
            self.ax.xaxis.set_major_formatter(ticker.ScalarFormatter())
            self.ax.tick_params(axis='x', rotation=0, labelsize=10, colors='#0F172A')
            self.ax.set_xlabel("历元数 (Epoch)", fontsize=11)
            
        self.ax.tick_params(axis='y', labelsize=10, colors='#0F172A')
        self.ax.set_title("水平位置误差历元分布图", fontsize=14, fontweight='bold', pad=10)
        self.ax.set_ylabel("水平偏差 (m)", fontsize=11)
        self.ax.grid(True, which='both', color='#94A3B8', linestyle='--', linewidth=0.7)
        self.ax.legend(loc='upper right', fontsize=10)
        if active_segments:
            max_len = max([len(s.get('epochs', [])) for s in active_segments] or [1])
            if x_axis_mode == '历元数':
                self.ax.set_xlim(0, max_len + 1)
        
        if show_sats and hasattr(self, 'ax_sats') and self.ax_sats:
            self._draw_sats_subplot(active_segments, x_axis_mode, time_zone, dop_type='HDOP')

    def draw_epoch_vertical(self, segments, time_zone='UTC', show_absolute_alt=False, show_extrema=True, x_axis_mode='历元数', show_sats=False, show_raw_alt=False):
        """
        绘制高程位置误差历元分布图 (可选择历元数或时间轴展示)
        """
        active_segments = [s for s in segments if s.get('active', True) and s.get('metrics') and s.get('epochs')]
        
        if not active_segments:
            self.ax.text(0.5, 0.5, "暂无数据以进行高程历元曲线绘制", ha='center', va='center', fontsize=12, color='#64748B')
            return
            
        for seg in active_segments:
            epochs = seg['epochs']
            m = seg['metrics']
            v_errors_list = m.get('v_errors', [])
            if not v_errors_list:
                continue
                
            if show_raw_alt:
                u_errors = np.array([ep['alt'] for ep in epochs])
            else:
                u_errors = np.array(v_errors_list)
                if show_absolute_alt:
                    u_errors = np.abs(u_errors)
            
            if x_axis_mode == '时间轴':
                x = np.array([ep['utc_time_sec'] for ep in epochs[:len(u_errors)]])
            else:
                x = np.arange(1, len(u_errors) + 1)
                
            plot_x, plot_y = self._downsample_minmax(x, u_errors)
            
            marker_style = 'o' if len(plot_x) <= 5000 else 'none'
            self.ax.plot(plot_x, plot_y, color=seg['color'], marker=marker_style, markersize=4, 
                         markeredgecolor='none', label=seg['name'], linewidth=2.0, alpha=1.0)
                         
            # 标注并突出显示最大值与最小值点
            if show_extrema and len(u_errors) > 0:
                max_idx = np.argmax(u_errors)
                min_idx = np.argmin(u_errors)
                
                # 时间格式化辅助函数
                def get_x_label(x_val):
                    if x_axis_mode == '时间轴':
                        val = x_val
                        if time_zone == 'Beijing':
                            val += 8 * 3600
                        secs = int(val) % 86400
                        return f"{secs // 3600:02d}:{(secs % 3600) // 60:02d}:{secs % 60:02d}"
                    return str(int(x_val))
                
                # 最大值 (红点高亮)
                x_max = x[max_idx]
                y_max = u_errors[max_idx]
                self.ax.plot(x_max, y_max, marker='o', markersize=6, color='#EF4444', markeredgecolor='black', zorder=5)
                self.ax.annotate(f"[{get_x_label(x_max)}, {y_max:.4f}]", (x_max, y_max), textcoords="offset points", 
                                 xytext=(5, 5), ha='left', fontsize=10, color='#0F172A', fontweight='bold',
                                 bbox=dict(boxstyle="round,pad=0.2", fc='#FFEBEB', ec='#EF4444', lw=0.5, alpha=0.85))
                
                # 最小值 (绿点高亮)
                x_min = x[min_idx]
                y_min = u_errors[min_idx]
                self.ax.plot(x_min, y_min, marker='o', markersize=6, color='#10B981', markeredgecolor='black', zorder=5)
                self.ax.annotate(f"[{get_x_label(x_min)}, {y_min:.4f}]", (x_min, y_min), textcoords="offset points", 
                                 xytext=(5, -12), ha='left', fontsize=10, color='#0F172A', fontweight='bold',
                                 bbox=dict(boxstyle="round,pad=0.2", fc='#EBFDF5', ec='#10B981', lw=0.5, alpha=0.85))
        
        if not show_absolute_alt:
            self.ax.axhline(0, color='#475569', linewidth=1.0, linestyle='-', zorder=1)
            
        # 格式化 X 轴刻度及标签
        if x_axis_mode == '时间轴':
            from matplotlib.ticker import FuncFormatter
            def make_time_formatter(tz):
                def formatter(x_val, pos):
                    val = x_val
                    if tz == 'Beijing':
                        val += 8 * 3600
                    secs = int(val) % 86400
                    return f"{secs // 3600:02d}:{(secs % 3600) // 60:02d}:{secs % 60:02d}"
                return formatter
            self.ax.xaxis.set_major_formatter(FuncFormatter(make_time_formatter(time_zone)))
            self.ax.tick_params(axis='x', rotation=15, labelsize=10, colors='#0F172A')
            self.ax.set_xlabel("时间", fontsize=11)
        else:
            import matplotlib.ticker as ticker
            self.ax.xaxis.set_major_formatter(ticker.ScalarFormatter())
            self.ax.tick_params(axis='x', rotation=0, labelsize=10, colors='#0F172A')
            self.ax.set_xlabel("历元数 (Epoch)", fontsize=11)
            
        if show_raw_alt:
            title_str = "高程值分布图"
            y_label_str = "高程值 (m)"
        else:
            title_str = "高程误差绝对值分布图" if show_absolute_alt else "高程误差历元分布图"
            y_label_str = "高程绝对误差 (m)" if show_absolute_alt else "高程偏差 (m)"
            
        self.ax.tick_params(axis='y', labelsize=10, colors='#0F172A')
        self.ax.set_title(title_str, fontsize=14, fontweight='bold', pad=10)
        self.ax.set_ylabel(y_label_str, fontsize=11)
        
        self.ax.grid(True, which='both', color='#94A3B8', linestyle='--', linewidth=0.7)
        self.ax.legend(loc='upper right', fontsize=10)
        if active_segments:
            max_len = max([len(s.get('epochs', [])) for s in active_segments] or [1])
            if x_axis_mode == '历元数':
                self.ax.set_xlim(0, max_len + 1)
        
        if show_sats and hasattr(self, 'ax_sats') and self.ax_sats:
            self._draw_sats_subplot(active_segments, x_axis_mode, time_zone, dop_type='VDOP')

    def _draw_sats_subplot(self, segments, x_axis_mode, time_zone, dop_type='HDOP'):
        ax1 = self.ax_sats
        ax2 = ax1.twinx()
        self.ax_sats_twin = ax2
        
        has_data = False
        actual_dop_type = dop_type
        for seg in segments:
            epochs = seg['epochs']
            if not epochs:
                continue
            
            sats = np.array([ep.get('num_sats', 0) for ep in epochs])
            has_vdop = any('vdop' in ep for ep in epochs)
            
            if dop_type == 'VDOP':
                if has_vdop:
                    dop = np.array([ep.get('vdop', 0.0) for ep in epochs])
                    actual_dop_type = 'VDOP'
                else:
                    dop = np.array([ep.get('hdop', 0.0) for ep in epochs])
                    actual_dop_type = 'HDOP(无VDOP)'
            else:
                dop = np.array([ep.get('hdop', 0.0) for ep in epochs])
                actual_dop_type = 'HDOP'
            
            # 过滤掉 0 值。因为底层 POGOS 和 GGA 时间戳可能有微小误差未合并，导致历元交替闪烁出现 0
            valid_idx = (sats > 0)
            if not np.any(valid_idx):
                continue
                
            has_data = True
            if x_axis_mode == '时间轴':
                x = np.array([ep['utc_time_sec'] for ep in epochs])
            else:
                x = np.arange(1, len(epochs) + 1)
                
            x_valid = x[valid_idx]
            sats_valid = sats[valid_idx]
            dop_valid = dop[valid_idx]
                
            total_pts = len(sats_valid)
            target_points = self._target_plot_points()
            if total_pts > target_points:
                step = max(1, total_pts // target_points)
                if x_valid[-1] != x_valid[::step][-1]:
                    plot_x = np.concatenate([x_valid[::step], [x_valid[-1]]])
                    plot_sats = np.concatenate([sats_valid[::step], [sats_valid[-1]]])
                    plot_dop = np.concatenate([dop_valid[::step], [dop_valid[-1]]])
                else:
                    plot_x = x_valid[::step]
                    plot_sats = sats_valid[::step]
                    plot_dop = dop_valid[::step]
            else:
                plot_x = x_valid
                plot_sats = sats_valid
                plot_dop = dop_valid
                
            ax1.plot(plot_x, plot_sats, color='#047857', marker='none', linestyle='-', linewidth=1.5, alpha=0.9, label="在用卫星数")
            ax2.plot(plot_x, plot_dop, color='#1D4ED8', marker='none', linestyle='-', linewidth=1.2, alpha=0.7, label=actual_dop_type)
            ax2.fill_between(plot_x, plot_dop, 0, color='#1D4ED8', alpha=0.1)
            
            # 锁定 Y 轴从 0 开始，避免微小波动占满全屏的视觉错觉
            sats_max = np.max(plot_sats)
            dop_max = np.max(plot_dop)
            ax1.set_ylim(0, max(20, sats_max + 5))
            ax2.set_ylim(0, max(5, dop_max * 1.5))
            
            break # Just plot the first valid segment for sats to avoid clutter
            
        if not has_data:
            ax1.text(0.5, 0.5, "未包含有效的卫星/DOP信息", ha='center', va='center', transform=ax1.transAxes, fontsize=10, color='#64748B')
            ax1.set_yticks([])
            ax2.set_yticks([])
        else:
            ax1.set_ylabel("在用卫星数 (颗)", fontsize=11, fontweight='bold', color='#047857')
            ax2.set_ylabel(actual_dop_type, fontsize=11, fontweight='bold', color='#1D4ED8')
            ax1.tick_params(axis='y', labelcolor='#047857', labelsize=10)
            ax2.tick_params(axis='y', labelcolor='#1D4ED8', labelsize=10)
            ax1.grid(True, axis='y', color='#E2E8F0', linestyle='--', linewidth=0.5)
            
        if x_axis_mode == '时间轴':
            from matplotlib.ticker import FuncFormatter
            def make_time_formatter(tz):
                def formatter(x_val, pos):
                    val = x_val
                    if tz == 'Beijing':
                        val += 8 * 3600
                    secs = int(val) % 86400
                    return f"{secs // 3600:02d}:{(secs % 3600) // 60:02d}:{secs % 60:02d}"
                return formatter
            ax1.xaxis.set_major_formatter(FuncFormatter(make_time_formatter(time_zone)))
            ax1.tick_params(axis='x', rotation=15, labelsize=10, colors='#0F172A')
        else:
            import matplotlib.ticker as ticker
            ax1.xaxis.set_major_formatter(ticker.ScalarFormatter())
            ax1.tick_params(axis='x', rotation=0, labelsize=10, colors='#0F172A')

    def draw_epoch_enu(self, segments, truth=None, time_zone='UTC', x_axis_mode='历元数', show_stats=True):
        """
        绘制 ENU 三向误差历元分布图 (E-W, N-S, U-D)
        """
        active_segments = [s for s in segments if s.get('active', True) and s.get('metrics') and s.get('epochs')]
        
        if not active_segments:
            self.ax_n.text(0.5, 0.5, "暂无 ENU 三向误差数据 (请确保已导入轨迹并选择对比参考真值)", 
                           ha='center', va='center', fontsize=12, color='#64748B')
            for ax in [self.ax_e, self.ax_n, self.ax_u]:
                for spine in ax.spines.values():
                    spine.set_visible(False)
                ax.set_xticks([])
                ax.set_yticks([])
            return

        has_valid_data = False
        all_e_errors = []
        all_n_errors = []
        all_u_errors = []

        for seg in active_segments:
            epochs = seg['epochs']
            m = seg['metrics']
            de_list = m.get('de', [])
            dn_list = m.get('dn', [])
            du_list = m.get('v_errors', [])
            
            if not de_list or not dn_list or not du_list:
                continue
                
            n_pts = min(len(epochs), len(de_list), len(dn_list), len(du_list))
            if n_pts == 0:
                continue
                
            has_valid_data = True
            de = np.array(de_list[:n_pts])
            dn = np.array(dn_list[:n_pts])
            du = np.array(du_list[:n_pts])
            
            if x_axis_mode == '时间轴':
                x = np.array([ep['utc_time_sec'] for ep in epochs[:n_pts]])
            else:
                x = np.arange(1, n_pts + 1)
                
            all_e_errors.extend(de)
            all_n_errors.extend(dn)
            all_u_errors.extend(du)
            
            # 降采样
            plot_x_e, plot_y_e = self._downsample_minmax(x, de)
            plot_x_n, plot_y_n = self._downsample_minmax(x, dn)
            plot_x_u, plot_y_u = self._downsample_minmax(x, du)
            
            marker_style = 'o' if len(plot_x_e) <= 5000 else 'none'
            seg_color = seg.get('color', '#EF4444')
            
            self.ax_e.plot(plot_x_e, plot_y_e, color=seg_color, marker=marker_style, markersize=3, 
                           markeredgecolor='none', linewidth=1.2, alpha=0.9, label=seg['name'])
            self.ax_n.plot(plot_x_n, plot_y_n, color=seg_color, marker=marker_style, markersize=3, 
                           markeredgecolor='none', linewidth=1.2, alpha=0.9, label=seg['name'])
            self.ax_u.plot(plot_x_u, plot_y_u, color=seg_color, marker=marker_style, markersize=3, 
                           markeredgecolor='none', linewidth=1.2, alpha=0.9, label=seg['name'])

        if not has_valid_data:
            self.ax_n.text(0.5, 0.5, "暂无有效的 ENU 误差数据", ha='center', va='center', fontsize=12, color='#64748B')
            for ax in [self.ax_e, self.ax_n, self.ax_u]:
                for spine in ax.spines.values():
                    spine.set_visible(False)
                ax.set_xticks([])
                ax.set_yticks([])
            return

        def calc_stats(errs):
            arr = np.array(errs)
            valid = arr[np.isfinite(arr)]
            if len(valid) == 0:
                return 0.0, 0.0, 0.0
            ave = float(np.mean(valid))
            std = float(np.std(valid))
            rms = float(np.sqrt(np.mean(valid**2)))
            return ave, std, rms

        ave_e, std_e, rms_e = calc_stats(all_e_errors)
        ave_n, std_n, rms_n = calc_stats(all_n_errors)
        ave_u, std_u, rms_u = calc_stats(all_u_errors)

        for ax, ylabel in zip([self.ax_e, self.ax_n, self.ax_u], ['E-W (m)', 'N-S (m)', 'U-D (m)']):
            ax.axhline(0, color='#475569', linewidth=0.8, linestyle='-', zorder=1)
            ax.grid(True, which='both', color='#CBD5E1', linestyle='--', linewidth=0.6)
            ax.set_ylabel(ylabel, fontsize=11, fontweight='bold', color='#0F172A')
            ax.tick_params(axis='y', labelsize=10, colors='#0F172A')
            # 隐藏上方子图的 X 轴刻度标签，保持整洁
            if ax != self.ax_u:
                ax.tick_params(axis='x', labelbottom=False)

        if show_stats:
            stats_box_props = dict(boxstyle="square,pad=0.25", fc='#F8FAFC', ec='#94A3B8', lw=0.5, alpha=0.85)
            
            ori_str = ""
            if truth and isinstance(truth, dict) and 'lat' in truth and 'lon' in truth:
                lat_deg = truth.get('lat', 0.0)
                lon_deg = truth.get('lon', 0.0)
                alt_m = truth.get('alt', 0.0)
                # 仅当参考位置为有效的静态非零坐标时才展示 ORI，动态轨迹对比时省略以保持三图排版一致
                if abs(lat_deg) > 1e-4 or abs(lon_deg) > 1e-4:
                    lat_hemi = 'N' if lat_deg >= 0 else 'S'
                    lon_hemi = 'E' if lon_deg >= 0 else 'W'
                    ori_str = f"ORI={abs(lat_deg):.8f}°{lat_hemi} {abs(lon_deg):.8f}°{lon_hemi} {alt_m:.4f}m\n"
            
            text_e = f"{ori_str}AVE={ave_e:+.4f}m STD={std_e:.4f}m RMS={rms_e:.4f}m"
            text_n = f"AVE={ave_n:+.4f}m STD={std_n:.4f}m RMS={rms_n:.4f}m"
            text_u = f"AVE={ave_u:+.4f}m STD={std_u:.4f}m RMS={rms_u:.4f}m"
            
            self.ax_e.text(0.985, 0.92, text_e, transform=self.ax_e.transAxes, ha='right', va='top', 
                           fontsize=9, fontfamily='monospace', color='#0F172A', bbox=stats_box_props, zorder=10)
            self.ax_n.text(0.985, 0.92, text_n, transform=self.ax_n.transAxes, ha='right', va='top', 
                           fontsize=9, fontfamily='monospace', color='#0F172A', bbox=stats_box_props, zorder=10)
            self.ax_u.text(0.985, 0.92, text_u, transform=self.ax_u.transAxes, ha='right', va='top', 
                           fontsize=9, fontfamily='monospace', color='#0F172A', bbox=stats_box_props, zorder=10)

        if x_axis_mode == '时间轴':
            from matplotlib.ticker import FuncFormatter
            def make_time_formatter(tz):
                def formatter(x_val, pos):
                    val = x_val
                    if tz == 'Beijing':
                        val += 8 * 3600
                    secs = int(val) % 86400
                    return f"{secs // 3600:02d}:{(secs % 3600) // 60:02d}:{secs % 60:02d}"
                return formatter
            self.ax_u.xaxis.set_major_formatter(FuncFormatter(make_time_formatter(time_zone)))
            self.ax_u.tick_params(axis='x', rotation=0, labelsize=10, colors='#0F172A')
            self.ax_u.set_xlabel("时间", fontsize=11, fontweight='bold', color='#0F172A')
        else:
            import matplotlib.ticker as ticker
            self.ax_u.xaxis.set_major_formatter(ticker.ScalarFormatter())
            self.ax_u.tick_params(axis='x', rotation=0, labelsize=10, colors='#0F172A')
            self.ax_u.set_xlabel("历元数 (Epoch)", fontsize=11, fontweight='bold', color='#0F172A')
            if active_segments:
                max_len = max([len(s.get('epochs', [])) for s in active_segments] or [1])
                for a in [self.ax_e, self.ax_n, self.ax_u]:
                    a.set_xlim(0, max_len + 1)

    def draw_speed_comparison(self, segments, truth=None, time_zone='UTC', x_axis_mode='历元数', speed_unit='m/s', show_stats=True):
        """
        绘制速度与动态真值对比图 (双子图: 上子图速度跟踪对比, 下子图速度误差分布)
        """
        active_segments = [s for s in segments if s.get('active', True) and s.get('metrics') and s.get('epochs')]
        
        scale = 3.6 if speed_unit == 'km/h' else 1.0
        unit_str = 'km/h' if speed_unit == 'km/h' else 'm/s'
        
        if not active_segments:
            self.ax_speed.text(0.5, 0.5, "暂无速度对比数据 (请导入轨迹并加载参考真值)", 
                               ha='center', va='center', fontsize=12, color='#64748B')
            for ax in [self.ax_speed, self.ax_speed_err]:
                for spine in ax.spines.values():
                    spine.set_visible(False)
                ax.set_xticks([])
                ax.set_yticks([])
            return

        has_valid_data = False
        all_speed_errors = []
        has_truth_speed = False

        for seg in active_segments:
            epochs = seg['epochs']
            m = seg['metrics']
            v_test = m.get('speed_test') or m.get('speed') or m.get('velocities') or []
            v_truth = m.get('speed_truth', [])
            v_err = m.get('speed_errors', [])
            
            if not v_test:
                continue
                
            n_pts = min(len(epochs), len(v_test))
            if n_pts == 0:
                continue
                
            has_valid_data = True
            v_test_arr = np.array(v_test[:n_pts]) * scale
            
            if x_axis_mode == '时间轴':
                x = np.array([ep['utc_time_sec'] for ep in epochs[:n_pts]])
            else:
                x = np.arange(1, n_pts + 1)
                
            plot_x, plot_y_test = self._downsample_minmax(x, v_test_arr)
            marker_style = 'o' if len(plot_x) <= 5000 else 'none'
            seg_color = seg.get('color', '#EF4444')
            
            self.ax_speed.plot(plot_x, plot_y_test, color=seg_color, marker=marker_style, markersize=3, 
                               markeredgecolor='none', linewidth=1.3, alpha=0.9, label=f"{seg['name']} 待测速度")
            
            if v_truth and len(v_truth) >= n_pts and np.any(np.array(v_truth[:n_pts]) > 0.001):
                has_truth_speed = True
                v_truth_arr = np.array(v_truth[:n_pts]) * scale
                plot_x_t, plot_y_truth = self._downsample_minmax(x, v_truth_arr)
                self.ax_speed.plot(plot_x_t, plot_y_truth, color='#64748B', linestyle='--', linewidth=1.2, 
                                   alpha=0.85, label='动态真值速度')
            
            if v_err and len(v_err) >= n_pts:
                v_err_arr = np.array(v_err[:n_pts]) * scale
                all_speed_errors.extend(v_err_arr)
                plot_x_e, plot_y_err = self._downsample_minmax(x, v_err_arr)
                self.ax_speed_err.plot(plot_x_e, plot_y_err, color=seg_color, marker=marker_style, markersize=3, 
                                       markeredgecolor='none', linewidth=1.2, alpha=0.9, label=seg['name'])

        if not has_valid_data:
            self.ax_speed.text(0.5, 0.5, "暂无可用的速度数据", ha='center', va='center', fontsize=12, color='#64748B')
            for ax in [self.ax_speed, self.ax_speed_err]:
                for spine in ax.spines.values():
                    spine.set_visible(False)
                ax.set_xticks([])
                ax.set_yticks([])
            return

        # 格式化上子图
        self.ax_speed.grid(True, which='both', color='#CBD5E1', linestyle='--', linewidth=0.6)
        self.ax_speed.set_ylabel(f"速度 ({unit_str})", fontsize=11, fontweight='bold', color='#0F172A')
        self.ax_speed.tick_params(axis='y', labelsize=10, colors='#0F172A')
        self.ax_speed.tick_params(axis='x', labelbottom=False)
        self.ax_speed.legend(loc='upper left', fontsize=9, framealpha=0.9)

        # 格式化下子图
        self.ax_speed_err.axhline(0, color='#475569', linewidth=0.8, linestyle='-', zorder=1)
        self.ax_speed_err.grid(True, which='both', color='#CBD5E1', linestyle='--', linewidth=0.6)
        self.ax_speed_err.set_ylabel(f"速度误差 ΔV ({unit_str})", fontsize=11, fontweight='bold', color='#0F172A')
        self.ax_speed_err.tick_params(axis='y', labelsize=10, colors='#0F172A')

        if not has_truth_speed:
            self.ax_speed_err.text(0.5, 0.5, "未加载动态真值速度，仅展示待测设备速度波形", 
                                   transform=self.ax_speed_err.transAxes, ha='center', va='center', 
                                   fontsize=10, color='#64748B')

        if show_stats and all_speed_errors:
            valid_err = np.array(all_speed_errors)[np.isfinite(all_speed_errors)]
            if len(valid_err) > 0:
                ave_v = float(np.mean(valid_err))
                std_v = float(np.std(valid_err))
                rms_v = float(np.sqrt(np.mean(valid_err**2)))
                max_v = float(np.max(np.abs(valid_err)))
                
                stats_box_props = dict(boxstyle="square,pad=0.25", fc='#F8FAFC', ec='#94A3B8', lw=0.5, alpha=0.85)
                text_stats = f"AVE={ave_v:+.3f}{unit_str}  STD={std_v:.3f}{unit_str}  RMS={rms_v:.3f}{unit_str}  MAX={max_v:.3f}{unit_str}"
                self.ax_speed_err.text(0.985, 0.90, text_stats, transform=self.ax_speed_err.transAxes, ha='right', va='top', 
                                       fontsize=9, fontfamily='monospace', color='#0F172A', bbox=stats_box_props, zorder=10)

        if x_axis_mode == '时间轴':
            from matplotlib.ticker import FuncFormatter
            def make_time_formatter(tz):
                def formatter(x_val, pos):
                    val = x_val
                    if tz == 'Beijing':
                        val += 8 * 3600
                    secs = int(val) % 86400
                    return f"{secs // 3600:02d}:{(secs % 3600) // 60:02d}:{secs % 60:02d}"
                return formatter
            self.ax_speed_err.xaxis.set_major_formatter(FuncFormatter(make_time_formatter(time_zone)))
            self.ax_speed_err.tick_params(axis='x', rotation=0, labelsize=10, colors='#0F172A')
            self.ax_speed_err.set_xlabel("时间", fontsize=11, fontweight='bold', color='#0F172A')
        else:
            import matplotlib.ticker as ticker
            self.ax_speed_err.xaxis.set_major_formatter(ticker.ScalarFormatter())
            self.ax_speed_err.tick_params(axis='x', rotation=0, labelsize=10, colors='#0F172A')
            self.ax_speed_err.set_xlabel("历元数 (Epoch)", fontsize=11, fontweight='bold', color='#0F172A')
            if active_segments:
                max_len = max([len(s.get('epochs', [])) for s in active_segments] or [1])
                for a in [self.ax_speed, self.ax_speed_err]:
                    a.set_xlim(0, max_len + 1)

    def draw_cdf(self, segments, truth=None, cdf_mode='horizontal', speed_unit='m/s', show_quantiles=True):
        """
        绘制定位误差累积分布曲线 (CDF, Cumulative Distribution Function)
        支持水平、高程、3D、速度 4 种维度，多模组曲线叠加，标准分位数参考线及交点标注。
        """
        active_segs = [s for s in segments if s.get('active')]
        if not active_segs:
            self.ax.text(0.5, 0.5, "请选择或导入有效的数据分段以绘制累积分布曲线 (CDF)", 
                         transform=self.ax.transAxes, ha='center', va='center', fontsize=12, color='#64748B')
            self.ax.set_axis_off()
            return

        mode_titles = {
            'horizontal': "水平位置误差累积分布函数 (Horizontal Error CDF)",
            'vertical': "高程绝对误差累积分布函数 (Vertical Error CDF)",
            '3d': "三维空间误差累积分布函数 (3D Position Error CDF)",
            'speed': f"地面速度误差累积分布函数 (Speed Error CDF - {speed_unit})"
        }
        unit_str = speed_unit if cdf_mode == 'speed' else "m"
        x_label_str = {
            'horizontal': "水平位置误差 (m)",
            'vertical': "高程绝对误差 (m)",
            '3d': "三维空间误差 (m)",
            'speed': f"速度绝对误差 ({speed_unit})"
        }[cdf_mode]

        self.ax.set_title(mode_titles.get(cdf_mode, "误差累积分布函数 (CDF)"), fontsize=14, fontweight='bold', color='#0F172A', pad=14)
        self.ax.grid(True, which='both', color='#CBD5E1', linestyle='--', linewidth=0.7)
        self.ax.set_xlabel(x_label_str, fontsize=12, fontweight='bold', color='#0F172A')
        self.ax.set_ylabel("累积概率百分比 (Cumulative Probability, %)", fontsize=12, fontweight='bold', color='#0F172A')

        global_max_err = 0.1
        summary_lines = []

        # 关键分位数定义 (采用高对比度、清晰深色系)
        quantiles = [
            (50.0, '50% (CEP50)', '#1E293B'),
            (68.3, '68.3% (1σ)', '#1E293B'),
            (95.0, '95% (2σ)', '#C2410C'),
            (99.0, '99%', '#B91C1C')
        ]

        if show_quantiles:
            for q_val, q_name, q_color in quantiles:
                self.ax.axhline(y=q_val, color=q_color, linestyle='--', linewidth=1.1, alpha=0.75, zorder=2)
                self.ax.text(0.012, q_val + 0.7, q_name, color=q_color, fontsize=10, fontweight='bold',
                             transform=self.ax.get_yaxis_transform(), va='bottom', zorder=3,
                             bbox=dict(boxstyle="round,pad=0.15", fc='#FFFFFF', ec=q_color, lw=0.6, alpha=0.85))

        for seg in active_segs:
            metrics = seg.get('metrics')
            if not metrics:
                continue

            # 提取误差数据
            if cdf_mode == 'horizontal':
                raw_err = metrics.get('h_errors')
            elif cdf_mode == 'vertical':
                v_arr = metrics.get('v_errors')
                raw_err = np.abs(v_arr) if v_arr is not None else None
            elif cdf_mode == '3d':
                raw_err = metrics.get('errors_3d')
                if raw_err is None:
                    h_arr = metrics.get('h_errors')
                    v_arr = metrics.get('v_errors')
                    if h_arr is not None and v_arr is not None:
                        raw_err = np.sqrt(np.array(h_arr)**2 + np.array(v_arr)**2)
            elif cdf_mode == 'speed':
                sp_arr = metrics.get('speed_errors')
                if sp_arr is not None:
                    scale = 3.6 if speed_unit == 'km/h' else 1.0
                    raw_err = np.abs(np.array(sp_arr)) * scale
                else:
                    raw_err = None
            else:
                raw_err = None

            if raw_err is None or len(raw_err) == 0:
                continue

            err_arr = np.array(raw_err, dtype=float)
            err_arr = err_arr[np.isfinite(err_arr)]
            if len(err_arr) == 0:
                continue

            err_sorted = np.sort(err_arr)
            n_pts = len(err_sorted)
            prob = (np.arange(1, n_pts + 1) / n_pts) * 100.0

            # 动态降采样，防止极大数据卡顿
            if n_pts > self.downsample_threshold:
                step = n_pts // self.downsample_threshold
                plot_err = err_sorted[::step]
                plot_prob = prob[::step]
            else:
                plot_err = err_sorted
                plot_prob = prob

            # 绘制加粗清晰的 CDF 曲线
            self.ax.plot(plot_err, plot_prob, label=seg['name'], color=seg['color'], linewidth=2.4, alpha=0.92, zorder=4)
            global_max_err = max(global_max_err, float(err_sorted[-1]))

            # 计算分位数
            p50 = float(np.percentile(err_sorted, 50.0))
            p68 = float(np.percentile(err_sorted, 68.3))
            p95 = float(np.percentile(err_sorted, 95.0))
            p99 = float(np.percentile(err_sorted, 99.0))
            p_max = float(err_sorted[-1])

            # 在 50%, 68.3%, 95%, 99% 上打点并标注清晰大字号数值
            if show_quantiles:
                offsets = {
                    50.0: (8, -12),
                    68.3: (8, -8),
                    95.0: (8, -12),
                    99.0: (8, 6)
                }
                for q_val, _, _ in quantiles:
                    val_at_q = float(np.percentile(err_sorted, q_val))
                    self.ax.plot(val_at_q, q_val, marker='o', markersize=6.5, color=seg['color'], 
                                 markeredgecolor='#FFFFFF', markeredgewidth=1.4, zorder=5)
                    
                    xy_off = offsets.get(q_val, (8, -8))
                    q_tag = "68%" if q_val == 68.3 else f"{int(q_val)}%"
                    self.ax.annotate(f"{q_tag}: {val_at_q:.2f}{unit_str}", (val_at_q, q_val),
                                     textcoords="offset points", xytext=xy_off,
                                     fontsize=10.5, fontweight='bold', color='#0F172A',
                                     bbox=dict(boxstyle="round,pad=0.35", fc='#FFFFFF', ec=seg['color'], lw=1.3, alpha=0.95),
                                     zorder=6)

            summary_lines.append(f"[{seg['name']}]  50%:{p50:.2f}{unit_str} | 68%:{p68:.2f}{unit_str} | 95%:{p95:.2f}{unit_str} | 99%:{p99:.2f}{unit_str} | Max:{p_max:.2f}{unit_str}")

        # 坐标轴范围与刻度
        self.ax.set_xlim(left=0, right=max(global_max_err * 1.08, 0.5))
        self.ax.set_ylim(bottom=0, top=103.5)
        self.ax.set_yticks([0, 20, 40, 50, 60, 68.3, 80, 95, 99, 100])
        self.ax.tick_params(axis='both', labelsize=11, colors='#0F172A')

        if len(active_segs) > 1:
            self.ax.legend(loc='lower right', framealpha=0.92, facecolor='#FFFFFF', edgecolor='#64748B', fontsize=10.5)

        # 右上角统计卡片 (大字号、高对比度深色文字)
        if summary_lines:
            stats_box_props = dict(boxstyle="square,pad=0.4", fc='#F8FAFC', ec='#475569', lw=0.8, alpha=0.92)
            text_stats = "\n".join(summary_lines[:5])
            self.ax.text(0.985, 0.98, text_stats, transform=self.ax.transAxes, ha='right', va='top', 
                         fontsize=10.5, fontweight='bold', color='#0F172A', bbox=stats_box_props, zorder=10)
