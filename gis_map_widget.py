# -*- coding: utf-8 -*-
"""
Interactive GIS Map Trajectory Widget
Built on top of PySide6.QtWebEngineWidgets and Leaflet.js.
Supports multiple online base maps (AMap, Tianditu, OSM, CartoDB), auto GCJ-02 correction,
RTK status trajectory rendering, fit bounds, and bi-directional time sync.
"""

import json
import os
from PySide6.QtCore import QObject, Signal, Slot, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QCheckBox, QPushButton, QLabel, QFrame
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from coord_transform import wgs84_to_gcj02


HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>GIS Trajectory Map</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <style>
        html, body, #map { width: 100%; height: 100%; margin: 0; padding: 0; background: #0F172A; }
        .leaflet-control-attribution { display: none !important; }
        .custom-popup .leaflet-popup-content-wrapper {
            background: rgba(15, 23, 42, 0.92);
            color: #F8FAFC;
            border: 1px solid #38BDF8;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        }
        .custom-popup .leaflet-popup-tip { background: rgba(15, 23, 42, 0.92); }
        .pulse-marker {
            width: 16px;
            height: 16px;
            background: #F59E0B;
            border: 2px solid #FFFFFF;
            border-radius: 50%;
            box-shadow: 0 0 10px #F59E0B, 0 0 20px #F59E0B;
            animation: pulse-ring 1.5s infinite;
        }
        @keyframes pulse-ring {
            0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7); }
            70% { transform: scale(1.1); box-shadow: 0 0 0 12px rgba(245, 158, 11, 0); }
            100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
        }
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map', {
            zoomControl: true,
            attributionControl: false
        }).setView([39.9042, 116.4074], 12);

        var currentBaseLayer = null;
        var currentAnnotLayer = null;
        var currentMapType = 'amap_vec';
        var pyBridge = null;
        window.isMapReady = true;

        // Base Layer Definitions
        var baseLayers = {
            'amap_vec': {
                url: 'https://wprd0{s}.is.autonavi.com/appmaptile?x={x}&y={y}&z={z}&lang=zh_cn&size=1&scl=1&style=7',
                subdomains: ['1','2','3','4'],
                maxZoom: 18,
                isGcj: true
            },
            'amap_sat': {
                url: 'https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}',
                subdomains: ['1','2','3','4'],
                annotUrl: 'https://webst0{s}.is.autonavi.com/appmaptile?style=8&x={x}&y={y}&z={z}',
                maxZoom: 18,
                isGcj: true
            },
            'google_sat': {
                url: 'https://mt{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                subdomains: ['0','1','2','3'],
                maxZoom: 20,
                isGcj: false
            },
            'tdt_sat': {
                url: 'https://t{s}.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=8e50f8cdd0450027d98d635238363e11',
                subdomains: ['0','1','2','3','4','5','6','7'],
                annotUrl: 'https://t{s}.tianditu.gov.cn/cia_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cia&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=8e50f8cdd0450027d98d635238363e11',
                maxZoom: 18,
                isGcj: false
            },
            'tdt_vec': {
                url: 'https://t{s}.tianditu.gov.cn/vec_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=vec&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=8e50f8cdd0450027d98d635238363e11',
                subdomains: ['0','1','2','3','4','5','6','7'],
                annotUrl: 'https://t{s}.tianditu.gov.cn/cva_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cva&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=8e50f8cdd0450027d98d635238363e11',
                maxZoom: 18,
                isGcj: false
            },
            'osm': {
                url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                subdomains: ['a','b','c'],
                maxZoom: 19,
                isGcj: false
            },
            'carto_dark': {
                url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
                subdomains: ['a','b','c','d'],
                maxZoom: 19,
                isGcj: false
            }
        };

        function switchBaseMap(type) {
            currentMapType = type;
            if (currentBaseLayer) map.removeLayer(currentBaseLayer);
            if (currentAnnotLayer) map.removeLayer(currentAnnotLayer);

            var cfg = baseLayers[type] || baseLayers['amap_vec'];
            currentBaseLayer = L.tileLayer(cfg.url, {
                subdomains: cfg.subdomains || 'abc',
                maxZoom: cfg.maxZoom || 18
            }).addTo(map);

            if (cfg.annotUrl) {
                currentAnnotLayer = L.tileLayer(cfg.annotUrl, {
                    subdomains: cfg.subdomains || 'abc',
                    maxZoom: cfg.maxZoom || 18
                }).addTo(map);
            }
            // Re-render trajectories if map coordinate system changes
            if (window.rawTrajectoryData) {
                renderTrajectories(window.rawTrajectoryData);
            }
        }

        switchBaseMap('amap_vec');

        var truthLayerGroup = L.layerGroup().addTo(map);
        var testLayerGroup = L.layerGroup().addTo(map);
        var cursorMarker = null;

        function renderTrajectories(payload) {
            window.rawTrajectoryData = payload;
            if (map) { map.invalidateSize(); }
            truthLayerGroup.clearLayers();
            testLayerGroup.clearLayers();

            var isGcj = (baseLayers[currentMapType] && baseLayers[currentMapType].isGcj);
            var allLatLngs = [];

            // 1. 绘制参考真值轨迹 (Truth)
            if (payload.showTruth && payload.truth_pts && payload.truth_pts.length > 0) {
                var truthLatLngs = [];
                for (var i = 0; i < payload.truth_pts.length; i++) {
                    var p = payload.truth_pts[i];
                    var lat = isGcj ? p.gcj_lat : p.wgs_lat;
                    var lon = isGcj ? p.gcj_lon : p.wgs_lon;
                    truthLatLngs.push([lat, lon]);
                    allLatLngs.push([lat, lon]);
                }
                var truthLine = L.polyline(truthLatLngs, {
                    color: '#3B82F6',
                    weight: 4,
                    opacity: 0.85,
                    lineCap: 'round',
                    lineJoin: 'round'
                }).addTo(truthLayerGroup);
                truthLine.bindTooltip("<b>参考真值基准轨迹</b>", {sticky: true});
            }

            // 2. 绘制待测轨迹 (Test Segments)
            if (payload.showTest && payload.test_segments && payload.test_segments.length > 0) {
                for (var s = 0; s < payload.test_segments.length; s++) {
                    var seg = payload.test_segments[s];
                    if (!seg.lines || seg.lines.length === 0) continue;

                    for (var l = 0; l < seg.lines.length; l++) {
                        var lineData = seg.lines[l];
                        var latlngs = [];
                        for (var k = 0; k < lineData.pts.length; k++) {
                            var pt = lineData.pts[k];
                            var tLat = isGcj ? pt.gcj_lat : pt.wgs_lat;
                            var tLon = isGcj ? pt.gcj_lon : pt.wgs_lon;
                            latlngs.push([tLat, tLon]);
                            allLatLngs.push([tLat, tLon]);
                        }
                        var segLine = L.polyline(latlngs, {
                            color: payload.colorByStatus ? lineData.color : seg.color,
                            weight: 3.5,
                            opacity: 0.92,
                            lineCap: 'round',
                            lineJoin: 'round'
                        }).addTo(testLayerGroup);

                        (function(segName, lineStatus) {
                            segLine.bindTooltip("<b>" + segName + "</b><br>状态: " + lineStatus, {sticky: true});
                        })(seg.name, lineData.status_str);
                    }
                }
            }

            if (payload.autoFit && allLatLngs.length > 1) {
                var bounds = L.latLngBounds(allLatLngs);
                map.fitBounds(bounds, { padding: [40, 40], maxZoom: 18 });
                setTimeout(function() {
                    if (map) {
                        map.invalidateSize();
                        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 18 });
                    }
                }, 200);
            }
        }

        function setCursor(cursorData) {
            if (!cursorData || cursorData.wgs_lat === undefined) {
                if (cursorMarker) {
                    map.removeLayer(cursorMarker);
                    cursorMarker = null;
                }
                return;
            }
            var isGcj = (baseLayers[currentMapType] && baseLayers[currentMapType].isGcj);
            var lat = isGcj ? cursorData.gcj_lat : cursorData.wgs_lat;
            var lon = isGcj ? cursorData.gcj_lon : cursorData.wgs_lon;

            var pulseIcon = L.divIcon({
                className: 'pulse-marker',
                iconSize: [16, 16],
                iconAnchor: [8, 8]
            });

            if (!cursorMarker) {
                cursorMarker = L.marker([lat, lon], {icon: pulseIcon}).addTo(map);
            } else {
                cursorMarker.setLatLng([lat, lon]);
            }

            var html = "<div style='font-family: monospace; font-size: 11px; line-height: 1.5;'>" +
                       "<b style='color: #F59E0B; font-size: 12px;'>📍 历元 #" + cursorData.epoch + "</b><br>" +
                       "时间: " + cursorData.time_str + "<br>" +
                       "纬度: " + cursorData.wgs_lat.toFixed(7) + "°<br>" +
                       "经度: " + cursorData.wgs_lon.toFixed(7) + "°<br>" +
                       (cursorData.h_err !== undefined ? "水平误差: <b>" + cursorData.h_err.toFixed(3) + " m</b><br>" : "") +
                       "解状态: <span style='color: #10B981; font-weight: bold;'>" + cursorData.quality_str + "</span>" +
                       "</div>";
            cursorMarker.bindPopup(html, {className: 'custom-popup'}).openPopup();
        }

        function fitBoundsNow() {
            if (window.rawTrajectoryData) {
                renderTrajectories(Object.assign({}, window.rawTrajectoryData, {autoFit: true}));
            } else if (map) {
                map.invalidateSize(true);
            }
        }

        new QWebChannel(qt.webChannelTransport, function(channel) {
            pyBridge = channel.objects.pyBridge;
        });
    </script>
</body>
</html>
"""


class WebBridge(QObject):
    sig_point_clicked = Signal(float)

    @Slot(float)
    def onPointClicked(self, tow):
        self.sig_point_clicked.emit(tow)


class GISMapWidget(QWidget):
    sig_time_clicked = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.raw_payload = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部工具栏
        toolbar = QFrame(self)
        toolbar.setFixedHeight(38)
        toolbar.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border-bottom: 1px solid #334155;
                padding: 0px 8px;
            }
            QLabel {
                color: #94A3B8;
                font-weight: bold;
                font-size: 11px;
            }
            QComboBox, QPushButton {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #38BDF8;
            }
            QCheckBox {
                color: #E2E8F0;
                font-size: 11px;
                font-weight: bold;
                spacing: 4px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
            }
        """)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(6, 4, 6, 4)
        tb_layout.setSpacing(12)

        tb_layout.addWidget(QLabel("底图图源:"))
        self.combo_map_type = QComboBox()
        self.combo_map_type.addItem("高德矢量路网 (免Key/推荐)", "amap_vec")
        self.combo_map_type.addItem("高德高清卫星 (免Key/推荐)", "amap_sat")
        self.combo_map_type.addItem("谷歌纯高清卫星 (免Key/无偏移路网)", "google_sat")
        self.combo_map_type.addItem("天地图官方卫星 (DataServer)", "tdt_sat")
        self.combo_map_type.addItem("天地图官方路网 (DataServer)", "tdt_vec")
        self.combo_map_type.addItem("OpenStreetMap (开源)", "osm")
        self.combo_map_type.addItem("CartoDB 暗黑底图", "carto_dark")
        self.combo_map_type.currentIndexChanged.connect(self.on_map_type_changed)
        tb_layout.addWidget(self.combo_map_type)

        self.cb_show_test = QCheckBox("待测轨迹")
        self.cb_show_test.setChecked(True)
        self.cb_show_test.toggled.connect(self.update_map_display)
        tb_layout.addWidget(self.cb_show_test)

        self.cb_show_truth = QCheckBox("参考真值")
        self.cb_show_truth.setChecked(True)
        self.cb_show_truth.toggled.connect(self.update_map_display)
        tb_layout.addWidget(self.cb_show_truth)

        self.cb_color_by_status = QCheckBox("按RTK状态着色")
        self.cb_color_by_status.setChecked(True)
        self.cb_color_by_status.toggled.connect(self.update_map_display)
        tb_layout.addWidget(self.cb_color_by_status)

        tb_layout.addStretch()

        self.btn_fit_bounds = QPushButton("⛶ 视野全局居中")
        self.btn_fit_bounds.clicked.connect(self.fit_bounds)
        tb_layout.addWidget(self.btn_fit_bounds)

        layout.addWidget(toolbar, 0)

        # WebEngine 地图视图
        self.is_page_loaded = False
        self.cached_segments = None
        self.cached_truth = None

        self.web_view = QWebEngineView(self)
        self.bridge = WebBridge()
        self.bridge.sig_point_clicked.connect(self.sig_time_clicked.emit)

        self.channel = QWebChannel(self)
        self.channel.registerObject("pyBridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        self.web_view.loadFinished.connect(self.on_load_finished)
        self.web_view.setHtml(HTML_TEMPLATE, baseUrl=QUrl("http://127.0.0.1/"))
        layout.addWidget(self.web_view, 1)

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, 'cached_segments', None) is not None:
            self.render_trajectories(self.cached_segments, self.cached_truth, auto_fit=True)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, lambda: self.web_view.page().runJavaScript("if (window.map) { map.invalidateSize(true); fitBoundsNow(); }"))
        QTimer.singleShot(200, lambda: self.web_view.page().runJavaScript("if (window.map) { map.invalidateSize(true); fitBoundsNow(); }"))
        QTimer.singleShot(500, lambda: self.web_view.page().runJavaScript("if (window.map) { map.invalidateSize(true); fitBoundsNow(); }"))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, 'is_page_loaded', False):
            self.web_view.page().runJavaScript("if (window.map) { map.invalidateSize(); }")

    def on_load_finished(self, ok):
        self.is_page_loaded = True
        if self.cached_segments is not None:
            self.render_trajectories(self.cached_segments, self.cached_truth, auto_fit=True)

    def on_map_type_changed(self):
        map_type = self.combo_map_type.currentData()
        self.web_view.page().runJavaScript(f"switchBaseMap('{map_type}');")

    def fit_bounds(self):
        self.web_view.page().runJavaScript("fitBoundsNow();")

    def render_trajectories(self, segments, truth=None, auto_fit=True):
        """
        处理分段待测轨迹与参考真值，进行高精度 WGS84 -> GCJ-02 转换并推送至 Leaflet WebGIS。
        """
        self.cached_segments = segments
        self.cached_truth = truth

        payload = {
            'showTruth': self.cb_show_truth.isChecked(),
            'showTest': self.cb_show_test.isChecked(),
            'colorByStatus': self.cb_color_by_status.isChecked(),
            'autoFit': auto_fit,
            'truth_pts': [],
            'test_segments': []
        }

        # 1. 转换参考真值
        if truth and isinstance(truth, dict) and 'epochs' in truth:
            t_epochs = truth['epochs']
            step = max(1, len(t_epochs) // 3000)
            for ep in t_epochs[::step]:
                w_lat = ep.get('lat', 0.0)
                w_lon = ep.get('lon', 0.0)
                if abs(w_lat) > 1e-4 and abs(w_lon) > 1e-4:
                    g_lat, g_lon = wgs84_to_gcj02(w_lat, w_lon)
                    payload['truth_pts'].append({
                        'wgs_lat': w_lat, 'wgs_lon': w_lon,
                        'gcj_lat': g_lat, 'gcj_lon': g_lon
                    })

        # 2. 转换各待测分段 (按 RTK 状态智能切分子线段)
        status_colors = {
            4: ("#10B981", "RTK固定(4)"),
            5: ("#F59E0B", "RTK浮点(5)"),
            2: ("#3B82F6", "差分(2)"),
            1: ("#EF4444", "单点(1)"),
            0: ("#64748B", "无效解(0)")
        }

        active_segs = [s for s in segments if s.get('active', True) and s.get('epochs')]
        for s in active_segs:
            epochs = s['epochs']
            if not epochs:
                continue

            seg_data = {
                'name': s.get('name', 'Segment'),
                'color': s.get('color', '#3B82F6'),
                'lines': []
            }

            step = max(1, len(epochs) // 3000)
            curr_quality = None
            curr_line_pts = []

            for ep in epochs[::step]:
                w_lat = ep.get('lat', 0.0)
                w_lon = ep.get('lon', 0.0)
                if abs(w_lat) < 1e-4 or abs(w_lon) < 1e-4:
                    continue

                q = ep.get('quality', 1)
                g_lat, g_lon = wgs84_to_gcj02(w_lat, w_lon)
                pt_obj = {
                    'wgs_lat': w_lat, 'wgs_lon': w_lon,
                    'gcj_lat': g_lat, 'gcj_lon': g_lon,
                    'tow': ep.get('utc_time_sec', ep.get('time', 0))
                }

                if self.cb_color_by_status.isChecked():
                    if curr_quality is None:
                        curr_quality = q
                    elif curr_quality != q:
                        if curr_line_pts:
                            col, s_str = status_colors.get(curr_quality, ("#64748B", f"状态({curr_quality})"))
                            seg_data['lines'].append({'color': col, 'status_str': s_str, 'pts': curr_line_pts})
                            # 重叠一个点保证折线连续
                            curr_line_pts = [curr_line_pts[-1]]
                        curr_quality = q
                curr_line_pts.append(pt_obj)

            if curr_line_pts:
                col, s_str = status_colors.get(curr_quality or 1, ("#64748B", "单点(1)"))
                seg_data['lines'].append({'color': col, 'status_str': s_str, 'pts': curr_line_pts})

            payload['test_segments'].append(seg_data)

        self.raw_payload = payload
        json_str = json.dumps(payload, ensure_ascii=False)
        js_wrapper = f"""
        (function() {{
            var payloadData = {json_str};
            function tryExecute() {{
                if (window.isMapReady && window.renderTrajectories) {{
                    window.renderTrajectories(payloadData);
                }} else {{
                    setTimeout(tryExecute, 100);
                }}
            }}
            tryExecute();
        }})();
        """
        self.web_view.page().runJavaScript(js_wrapper)

    def update_map_display(self):
        if self.raw_payload:
            self.raw_payload['showTruth'] = self.cb_show_truth.isChecked()
            self.raw_payload['showTest'] = self.cb_show_test.isChecked()
            self.raw_payload['colorByStatus'] = self.cb_color_by_status.isChecked()
            json_str = json.dumps(self.raw_payload, ensure_ascii=False)
            self.web_view.page().runJavaScript(f"renderTrajectories({json_str});")

    def set_cursor_time(self, cursor_time, segments):
        """
        根据当前时间同步秒数，定位车辆脉冲光标
        """
        if cursor_time is None or not segments:
            self.web_view.page().runJavaScript("setCursor(null);")
            return

        for s in segments:
            if s.get('active', True) and s.get('epochs'):
                epochs = s['epochs']
                t_list = [ep.get('utc_time_sec', ep.get('time', 0)) for ep in epochs]
                if t_list:
                    import numpy as np
                    t_arr = np.array(t_list)
                    idx = int(np.argmin(np.abs(t_arr - cursor_time)))
                    if abs(t_arr[idx] - cursor_time) <= 4.0:
                        ep = epochs[idx]
                        w_lat = ep.get('lat', 0.0)
                        w_lon = ep.get('lon', 0.0)
                        if abs(w_lat) > 1e-4 and abs(w_lon) > 1e-4:
                            g_lat, g_lon = wgs84_to_gcj02(w_lat, w_lon)
                            sec = int(ep.get('utc_time_sec', ep.get('time', 0))) % 86400
                            time_str = f"{sec//3600:02d}:{(sec%3600)//60:02d}:{sec%60:02d}"
                            q = ep.get('quality', 1)
                            q_map = {4: "RTK固定(4)", 5: "RTK浮点(5)", 2: "差分(2)", 1: "单点(1)", 0: "无效(0)"}
                            
                            h_err = None
                            m = s.get('metrics', {})
                            if m.get('h_errors') and idx < len(m['h_errors']):
                                h_err = float(m['h_errors'][idx])

                            cursor_data = {
                                'epoch': idx + 1,
                                'time_str': time_str,
                                'wgs_lat': w_lat, 'wgs_lon': w_lon,
                                'gcj_lat': g_lat, 'gcj_lon': g_lon,
                                'quality_str': q_map.get(q, f"状态({q})"),
                                'h_err': h_err
                            }
                            json_str = json.dumps(cursor_data, ensure_ascii=False)
                            self.web_view.page().runJavaScript(f"setCursor({json_str});")
                            return
        self.web_view.page().runJavaScript("setCursor(null);")
