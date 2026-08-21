# -*- coding: utf-8 -*-
"""
Interactive GIS Map Trajectory Widget (Official QtWebEngine Architecture)
Built on top of PySide6.QtWebEngineWidgets and Leaflet.js.
Supports multiple online base maps (AMap, Tianditu, OSM, CartoDB), auto GCJ-02 correction,
RTK status trajectory rendering, fit bounds, and bi-directional time sync.
100% thread-safe and immune to modal dialog deadlocks.
"""

import json
import os
from PySide6.QtCore import QObject, Signal, Slot, QUrl, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QCheckBox, QPushButton, QLabel, QFrame
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebChannel import QWebChannel

from coord_transform import wgs84_to_gcj02


class MapBridge(QObject):
    """
    Bridge object exposed to JavaScript for bi-directional communication.
    """
    point_clicked = Signal(float)  # Sends epoch TOW to Python

    @Slot(float)
    def onPointClicked(self, tow):
        self.point_clicked.emit(tow)


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

        if (typeof QWebChannel !== 'undefined') {
            new QWebChannel(qt.webChannelTransport, function(channel) {
                pyBridge = channel.objects.pyBridge;
            });
        }

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
                maxZoom: cfg.maxZoom || 18,
                errorTileUrl: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" style="background:%230F172A"><text x="50%25" y="50%25" fill="%2364748B" font-size="12" text-anchor="middle" dominant-baseline="middle">图源不可用(可切换底图)</text></svg>'
            }).addTo(map);

            if (cfg.annotUrl) {
                currentAnnotLayer = L.tileLayer(cfg.annotUrl, {
                    subdomains: cfg.subdomains || 'abc',
                    maxZoom: cfg.maxZoom || 18
                }).addTo(map);
            }
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
                    dashArray: '8, 6',
                    lineCap: 'round',
                    lineJoin: 'round'
                });
                truthLine.bindTooltip('<span style="color:#60A5FA;font-weight:bold;">参考真值基准轨迹</span>', {sticky: true});
                truthLayerGroup.addLayer(truthLine);
            }

            // 2. 绘制各待测分段轨迹 (Test Segments)
            if (payload.showTest && payload.test_segments && payload.test_segments.length > 0) {
                for (var sIdx = 0; sIdx < payload.test_segments.length; sIdx++) {
                    var seg = payload.test_segments[sIdx];
                    if (!seg.lines) continue;

                    for (var lIdx = 0; lIdx < seg.lines.length; lIdx++) {
                        var lineData = seg.lines[lIdx];
                        var pts = lineData.pts;
                        if (!pts || pts.length === 0) continue;

                        var latLngs = [];
                        for (var pIdx = 0; pIdx < pts.length; pIdx++) {
                            var pt = pts[pIdx];
                            var lat = isGcj ? pt.gcj_lat : pt.wgs_lat;
                            var lon = isGcj ? pt.gcj_lon : pt.wgs_lon;
                            latLngs.push([lat, lon]);
                            allLatLngs.push([lat, lon]);
                        }

                        var poly = L.polyline(latLngs, {
                            color: lineData.color,
                            weight: 3.5,
                            opacity: 0.95,
                            lineCap: 'round',
                            lineJoin: 'round'
                        });

                        (function(segName, lineStatus) {
                            poly.bindTooltip(
                                '<div style="font-family:Segoe UI, sans-serif;">' +
                                '<b>' + segName + '</b><br/>' +
                                '<span style="color:' + lineStatus.color + ';">● ' + lineStatus.label + '</span>' +
                                '</div>',
                                {sticky: true}
                            );
                            poly.on('click', function(e) {
                                if (pyBridge) pyBridge.onPointClicked(0);
                            });
                        })(seg.name, {label: lineData.label, color: lineData.color});

                        testLayerGroup.addLayer(poly);
                    }
                }
            }

            // 3. 视野全局自适应居中
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

        function setVehicleCursor(lat, lon, popupHtml, autoPan) {
            if (!map) return;
            var renderLat = lat;
            var renderLon = lon;

            if (cursorMarker) {
                cursorMarker.setLatLng([renderLat, renderLon]);
            } else {
                var pulseIcon = L.divIcon({
                    className: 'pulse-marker',
                    iconSize: [16, 16],
                    iconAnchor: [8, 8]
                });
                cursorMarker = L.marker([renderLat, renderLon], {
                    icon: pulseIcon,
                    zIndexOffset: 1000
                }).addTo(map);
            }

            if (popupHtml) {
                cursorMarker.bindPopup(popupHtml, {
                    className: 'custom-popup',
                    offset: [0, -10],
                    autoClose: false,
                    closeOnClick: false
                }).openPopup();
            }

            if (autoPan) {
                map.panTo([renderLat, renderLon], { animate: true, duration: 0.5 });
            }
        }

        function fitBoundsNow() {
            if (window.rawTrajectoryData) {
                renderTrajectories(Object.assign({}, window.rawTrajectoryData, {autoFit: true}));
            } else if (map) {
                map.invalidateSize(true);
            }
        }
    </script>
</body>
</html>
"""


class GISMapWidget(QWidget):
    sig_time_clicked = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_page_loaded = False
        self.cached_segments = None
        self.cached_truth = None
        self.raw_payload = None

        self.bridge = MapBridge()
        self.bridge.point_clicked.connect(self.sig_time_clicked)

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
                font-size: 12px;
                font-weight: 500;
            }
            QComboBox {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 12px;
            }
            QComboBox::drop-down { border: none; }
            QCheckBox {
                color: #CBD5E1;
                font-size: 12px;
                spacing: 4px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
            }
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #0369A1; }
            QPushButton:pressed { background-color: #075985; }
        """)

        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(4, 2, 4, 2)
        tb_layout.setSpacing(12)

        tb_layout.addWidget(QLabel("底图图源:"))
        self.combo_map_type = QComboBox()
        self.combo_map_type.addItem("高德矢量路网 (免Key/推荐)", "amap_vec")
        self.combo_map_type.addItem("高德高清卫星 (免Key/推荐)", "amap_sat")
        self.combo_map_type.addItem("谷歌纯高清卫星 (免Key/无偏移路网)", "google_sat")
        self.combo_map_type.addItem("天地图官方卫星 (专属Key)", "tdt_sat")
        self.combo_map_type.addItem("天地图官方路网 (专属Key)", "tdt_vec")
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

        # 官方原生 QWebEngineView 容器
        self.web_view = QWebEngineView(self)
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

        self.channel = QWebChannel(self)
        self.channel.registerObject('pyBridge', self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        self.web_view.page().loadFinished.connect(self.on_load_finished)
        self.web_view.setHtml(HTML_TEMPLATE, QUrl("http://127.0.0.1/"))

        layout.addWidget(self.web_view, 1)

    def on_load_finished(self, ok):
        self.is_page_loaded = True
        if self.cached_segments is not None:
            self.render_trajectories(self.cached_segments, self.cached_truth, auto_fit=True)

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, 'cached_segments', None) is not None:
            self.render_trajectories(self.cached_segments, self.cached_truth, auto_fit=True)
        QTimer.singleShot(50, lambda: self.web_view.page().runJavaScript("if (window.map) { map.invalidateSize(true); fitBoundsNow(); }"))
        QTimer.singleShot(200, lambda: self.web_view.page().runJavaScript("if (window.map) { map.invalidateSize(true); fitBoundsNow(); }"))
        QTimer.singleShot(500, lambda: self.web_view.page().runJavaScript("if (window.map) { map.invalidateSize(true); fitBoundsNow(); }"))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, 'is_page_loaded', False):
            self.web_view.page().runJavaScript("if (window.map) { map.invalidateSize(); }")

    def on_map_type_changed(self):
        map_type = self.combo_map_type.currentData()
        self.web_view.page().runJavaScript(f"switchBaseMap('{map_type}');")

    def fit_bounds(self):
        self.web_view.page().runJavaScript("fitBoundsNow();")

    def render_trajectories(self, segments, truth=None, auto_fit=True):
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

        # 2. 转换各待测分段
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
                        curr_line_pts = [pt_obj]
                    elif curr_quality == q:
                        curr_line_pts.append(pt_obj)
                    else:
                        color_hex, label = status_colors.get(curr_quality, ("#EF4444", f"状态({curr_quality})"))
                        seg_data['lines'].append({
                            'color': color_hex,
                            'label': label,
                            'pts': curr_line_pts
                        })
                        curr_quality = q
                        curr_line_pts = [curr_line_pts[-1], pt_obj]
                else:
                    curr_line_pts.append(pt_obj)

            if curr_line_pts:
                color_hex = s.get('color', '#3B82F6') if not self.cb_color_by_status.isChecked() else status_colors.get(curr_quality, ("#EF4444", f"状态({curr_quality})"))[0]
                label = s.get('name', '轨迹') if not self.cb_color_by_status.isChecked() else status_colors.get(curr_quality, ("#EF4444", f"状态({curr_quality})"))[1]
                seg_data['lines'].append({
                    'color': color_hex,
                    'label': label,
                    'pts': curr_line_pts
                })

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

    def set_cursor_time(self, tow, segments):
        if tow is None or not segments:
            return

        target_pt = None
        closest_diff = float('inf')

        for s in segments:
            if not s.get('active', True) or not s.get('epochs'):
                continue
            for ep in s['epochs']:
                ep_tow = ep.get('utc_time_sec', ep.get('time', 0))
                diff = abs(ep_tow - tow)
                if diff < closest_diff:
                    closest_diff = diff
                    w_lat = ep.get('lat', 0.0)
                    w_lon = ep.get('lon', 0.0)
                    g_lat, g_lon = wgs84_to_gcj02(w_lat, w_lon)
                    target_pt = {
                        'wgs_lat': w_lat, 'wgs_lon': w_lon,
                        'gcj_lat': g_lat, 'gcj_lon': g_lon,
                        'tow': ep_tow,
                        'quality': ep.get('quality', 1),
                        'h_err': ep.get('h_error', None),
                        'name': s.get('name', '待测轨迹')
                    }

        if target_pt and closest_diff < 5.0:
            is_gcj = (self.combo_map_type.currentData() in ['amap_vec', 'amap_sat'])
            render_lat = target_pt['gcj_lat'] if is_gcj else target_pt['wgs_lat']
            render_lon = target_pt['gcj_lon'] if is_gcj else target_pt['wgs_lon']

            status_map = {4: 'RTK固定解(4)', 5: 'RTK浮点解(5)', 2: '差分解(2)', 1: '单点解(1)', 0: '无效解(0)'}
            q_desc = status_map.get(target_pt['quality'], f'状态({target_pt["quality"]})')
            h_err_str = f"{target_pt['h_err']:.3f}m" if target_pt['h_err'] is not None else "--"

            popup_html = f"""
            <div style='font-family:Segoe UI, sans-serif; min-width: 140px;'>
                <div style='font-weight:bold; color:#38BDF8; margin-bottom:4px;'>{target_pt['name']}</div>
                <div><b>时间:</b> {target_pt['tow']:.1f}s</div>
                <div><b>状态:</b> <span style='color:#F59E0B;'>{q_desc}</span></div>
                <div><b>水平误差:</b> <span style='color:#10B981;'>{h_err_str}</span></div>
                <div><b>纬度:</b> {target_pt['wgs_lat']:.7f}°</div>
                <div><b>经度:</b> {target_pt['wgs_lon']:.7f}°</div>
            </div>
            """
            popup_json = json.dumps(popup_html, ensure_ascii=False)
            self.web_view.page().runJavaScript(f"setVehicleCursor({render_lat}, {render_lon}, {popup_json}, false);")

    def update_map_display(self):
        if self.cached_segments is not None:
            self.render_trajectories(self.cached_segments, self.cached_truth, auto_fit=False)
