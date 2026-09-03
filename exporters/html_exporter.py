# -*- coding: utf-8 -*-
"""
Interactive Standalone HTML GNSS Report Exporter (Pro Edition v2)
1. Clean horizontal error curve without RMS/CEP95 mark lines
2. Triple-stacked separated ENU subplots (E, N, U) matching desktop software
3. True 1:1 aspect-ratio bullseye chart with concentric circle grid rings
4. Expanded widescreen canvas (up to 1800px) fully utilizing screen width
5. Interactive Leaflet map controls (toggle RTK coloring & switch between Pure Line / Points+Line / Points Only)
"""

import os
import json
import math
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog, QApplication
from coord_transform import wgs84_to_gcj02

HTML_REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GNSS 定位精度测试与综合评定报告 - __REPORT_TITLE__</title>
    <!-- Leaflet & ECharts CDN -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        :root {
            --bg-main: #0B1120;
            --bg-card: #1E293B;
            --bg-subtle: #334155;
            --border: #475569;
            --text-main: #F8FAFC;
            --text-sub: #94A3B8;
            --brand: #38BDF8;
            --success: #10B981;
            --warning: #F59E0B;
            --danger: #EF4444;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            line-height: 1.6;
            padding: 20px;
        }
        /* 宽屏容器自适应：充分利用左右两侧屏幕空间 */
        .container {
            width: 96%;
            max-width: 1800px;
            margin: 0 auto;
        }
        
        /* Header */
        .report-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 28px;
            background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .header-title h1 { font-size: 24px; color: var(--text-main); margin-bottom: 6px; }
        .header-title p { font-size: 13px; color: var(--text-sub); }
        .header-badge {
            background: rgba(56, 189, 248, 0.15);
            border: 1px solid var(--brand);
            color: var(--brand);
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: bold;
        }

        /* KPI Dashboard Grid */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
            margin-bottom: 20px;
        }
        .kpi-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px 20px;
            transition: transform 0.2s;
        }
        .kpi-card:hover { transform: translateY(-2px); }
        .kpi-label { font-size: 12px; color: var(--text-sub); margin-bottom: 8px; font-weight: 500; }
        .kpi-value { font-size: 28px; font-weight: 700; font-family: "Consolas", monospace; }
        .kpi-unit { font-size: 14px; font-weight: 400; color: var(--text-sub); margin-left: 4px; }
        .color-brand { color: var(--brand); }
        .color-success { color: var(--success); }
        .color-warning { color: var(--warning); }

        /* Section Cards */
        .section-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.25);
        }
        .section-title {
            font-size: 17px;
            font-weight: 600;
            color: var(--text-main);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            border-bottom: 1px solid var(--bg-subtle);
            padding-bottom: 12px;
            margin-bottom: 16px;
        }
        .section-title-left {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .map-controls {
            display: flex;
            align-items: center;
            gap: 16px;
            font-size: 13px;
            font-weight: normal;
            color: var(--text-main);
        }
        .map-controls label {
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
        }
        .map-controls select {
            background: #0F172A;
            color: var(--text-main);
            border: 1px solid var(--border);
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            outline: none;
        }

        /* Map Container */
        #map-container {
            width: 100%;
            height: 520px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: #0F172A;
        }

        /* Table */
        .table-responsive { width: 100%; overflow-x: auto; margin-top: 10px; }
        table { width: 100%; border-collapse: collapse; text-align: center; font-size: 13px; }
        th { background: #0F172A; color: var(--brand); padding: 12px 10px; border: 1px solid var(--border); font-weight: 600; }
        td { padding: 10px; border: 1px solid var(--border); font-family: "Consolas", monospace; }
        tr:nth-child(even) { background: rgba(255,255,255,0.02); }
        tr:hover { background: rgba(56, 189, 248, 0.05); }

        /* Charts Layout */
        .charts-row-2col {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        @media (max-width: 1100px) {
            .charts-row-2col { grid-template-columns: 1fr; }
        }
        .charts-row-full {
            margin-bottom: 20px;
        }
        .chart-box {
            background: #0F172A;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
            height: 420px;
        }
        .chart-box-tall {
            height: 540px;
        }
        /* 靶心图外层容器居中 */
        .bullseye-container {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 420px;
            background: #0F172A;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
        }
        #chart-scatter {
            width: 400px;
            height: 400px;
        }

        /* Footer */
        .report-footer {
            text-align: center;
            font-size: 12px;
            color: var(--text-sub);
            padding: 24px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="report-header">
            <div class="header-title">
                <h1>🛰️ GNSS 定位精度测试与综合评定报告</h1>
                <p>测试对象: __REPORT_TITLE__  |  报告生成时间: __GEN_TIME__  |  数据历元总数: __TOTAL_EPOCHS__</p>
            </div>
            <div class="header-badge">
                POS_Handling 专业评定
            </div>
        </div>

        <!-- KPI Executive Dashboard -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">RTK 固定解比例 (Fix Rate)</div>
                <div class="kpi-value color-success">__FIX_RATE__<span class="kpi-unit">%</span></div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">水平精度 RMS (1σ)</div>
                <div class="kpi-value color-brand">__H_RMS__<span class="kpi-unit">m</span></div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">水平 95% 置信度误差</div>
                <div class="kpi-value color-brand">__H_95__<span class="kpi-unit">m</span></div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">高程精度 RMS (1σ)</div>
                <div class="kpi-value color-warning">__V_RMS__<span class="kpi-unit">m</span></div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">最大水平偏差 (Max Error)</div>
                <div class="kpi-value color-warning">__MAX_H_ERR__<span class="kpi-unit">m</span></div>
            </div>
        </div>

        <!-- Section 1: 交互式轨迹地图 (带图层与显示模式交互控制器) -->
        <div class="section-card">
            <div class="section-title">
                <div class="section-title-left">
                    🗺️ 空间二维运行轨迹与解状态投影
                </div>
                <div class="map-controls">
                    <label>
                        <input type="checkbox" id="chk-rtk-color" __CHECKED_RTK_COLOR__ onchange="updateMapDisplay()"> 按 RTK 状态着色
                    </label>
                    <label>
                        显示样式:
                        <select id="sel-map-mode" onchange="updateMapDisplay()">
                            <option value="line_points" selected>点连线 (Line + Points)</option>
                            <option value="line_only">纯线条 (Pure Line)</option>
                            <option value="points_only">纯散点 (Points Only)</option>
                        </select>
                    </label>
                </div>
            </div>
            <div id="map-container"></div>
        </div>

        <!-- Section 2: 精度评定统计表 -->
        <div class="section-card">
            <div class="section-title">
                <div class="section-title-left">📊 分段定位精度综合评定明细表</div>
            </div>
            <div class="table-responsive">
                __METRICS_TABLE_HTML__
            </div>
        </div>

        <!-- Section 3: 误差曲线大看板 (宽屏大视野) -->
        <div class="section-card">
            <div class="section-title">
                <div class="section-title-left">📈 误差时序历元分布与联合分析 (支持区域框选缩放、十字光标悬停)</div>
            </div>

            <!-- 第一行：水平误差与垂直误差 (宽屏 2 列大图) -->
            <div class="charts-row-2col">
                <div class="chart-box" id="chart-epoch-h"></div>
                <div class="chart-box" id="chart-epoch-v"></div>
            </div>

            <!-- 第二行：三向 ENU 误差 (像专业软件一样三层独立纵向展开，全宽视野) -->
            <div class="charts-row-full">
                <div class="chart-box chart-box-tall" id="chart-epoch-enu"></div>
            </div>

            <!-- 第三行：自适应正圆靶心图 与 CDF 累积分布图 -->
            <div class="charts-row-2col">
                <div class="bullseye-container">
                    <div id="chart-scatter"></div>
                </div>
                <div class="chart-box" id="chart-cdf"></div>
            </div>

            <!-- 第四行：运行速度曲线 (全宽) -->
            <div class="charts-row-full">
                <div class="chart-box" id="chart-speed"></div>
            </div>
        </div>

        <div class="report-footer">
            Generated by POS_Handling High-Precision GNSS Positioning Evaluation System &bull; All Rights Reserved
        </div>
    </div>

    <!-- Script: Leaflet & ECharts Rendering -->
    <script>
        var mapPayload = __MAP_PAYLOAD_JSON__;
        var chartPayload = __CHART_PAYLOAD_JSON__;

        // 1. 初始化 Leaflet 轨迹地图
        var map = L.map('map-container', { zoomControl: true, attributionControl: false }).setView([39.9, 116.4], 13);
        L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
            subdomains: ['1','2','3','4'], maxZoom: 18
        }).addTo(map);

        var mapLayersGroup = L.layerGroup().addTo(map);

        function updateMapDisplay() {
            mapLayersGroup.clearLayers();
            if (!mapPayload || !mapPayload.points || mapPayload.points.length === 0) return;

            var isColorByStatus = document.getElementById('chk-rtk-color').checked;
            var displayMode = document.getElementById('sel-map-mode').value;
            var statusColors = { 4: '#10B981', 5: '#F59E0B', 1: '#38BDF8', 2: '#6366F1' };

            var pts = mapPayload.points;

            // A. 绘制线条 (如果不是纯散点模式)
            if (displayMode !== 'points_only') {
                if (isColorByStatus) {
                    // 按状态分段画彩色线
                    var currQuality = null;
                    var currLine = [];
                    for (var i = 0; i < pts.length; i++) {
                        var p = pts[i];
                        if (currQuality === null) {
                            currQuality = p.status;
                            currLine = [[p.lat, p.lon]];
                        } else if (currQuality === p.status) {
                            currLine.push([p.lat, p.lon]);
                        } else {
                            var color = statusColors[currQuality] || '#94A3B8';
                            L.polyline(currLine, { color: color, weight: 3, opacity: 0.9 }).addTo(mapLayersGroup);
                            currQuality = p.status;
                            currLine = [currLine[currLine.length - 1], [p.lat, p.lon]];
                        }
                    }
                    if (currLine.length > 0) {
                        var color = statusColors[currQuality] || '#94A3B8';
                        L.polyline(currLine, { color: color, weight: 3, opacity: 0.9 }).addTo(mapLayersGroup);
                    }
                } else {
                    // 统一主色线条
                    var allLatLngs = pts.map(function(p) { return [p.lat, p.lon]; });
                    L.polyline(allLatLngs, { color: '#38BDF8', weight: 3, opacity: 0.9 }).addTo(mapLayersGroup);
                }
            }

            // B. 绘制点标记 (如果不是纯线条模式)
            if (displayMode !== 'line_only') {
                var step = Math.max(1, Math.floor(pts.length / 600));
                for (var i = 0; i < pts.length; i += step) {
                    var p = pts[i];
                    var dotColor = isColorByStatus ? (statusColors[p.status] || '#94A3B8') : '#38BDF8';
                    var circle = L.circleMarker([p.lat, p.lon], {
                        radius: 3, fillColor: dotColor, color: '#FFFFFF', weight: 0.5, fillOpacity: 0.9
                    }).addTo(mapLayersGroup);
                    circle.bindPopup(
                        "<b>序号:</b> " + (i+1) + "<br/>" +
                        "<b>时间:</b> " + p.time + "<br/>" +
                        "<b>解状态:</b> " + (p.status == 4 ? 'RTK固定解' : (p.status == 5 ? 'RTK浮点解' : '单点解')) + "<br/>" +
                        "<b>水平误差:</b> " + (p.h_err ? p.h_err.toFixed(3) + 'm' : 'N/A')
                    );
                }
            }
        }

        // 初始地图轨迹绘制并缩放到最佳视口
        if (mapPayload && mapPayload.points && mapPayload.points.length > 0) {
            updateMapDisplay();
            var allLatLngs = mapPayload.points.map(function(p) { return [p.lat, p.lon]; });
            var poly = L.polyline(allLatLngs);
            map.fitBounds(poly.getBounds(), { padding: [30, 30] });
        }

        // 2. 初始化 ECharts 动态图表

        // A. 水平位置误差历元分布图 (不显示 RMS / 95% 虚线，纯净曲线)
        var echH = echarts.init(document.getElementById('chart-epoch-h'), 'dark');
        echH.setOption({
            backgroundColor: 'transparent',
            title: { text: '水平位置误差历元分布图 (2D Error)', left: 'center', top: 8, textStyle: { fontSize: 15, color: '#F8FAFC' } },
            tooltip: { trigger: 'axis' },
            dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 4 }],
            grid: { left: 60, right: 30, top: 55, bottom: 42 },
            xAxis: { type: 'category', data: chartPayload.x_axis, axisLine: { lineStyle: { color: '#475569' } } },
            yAxis: { type: 'value', name: '偏差 (m)', nameLocation: 'end', nameGap: 10, splitLine: { lineStyle: { color: '#334155' } } },
            series: [{
                name: '水平误差', type: 'line', data: chartPayload.h_err,
                lineStyle: { color: '#38BDF8', width: 1.6 },
                showSymbol: false
            }]
        });

        // B. 高程位置误差历元分布图
        var echV = echarts.init(document.getElementById('chart-epoch-v'), 'dark');
        echV.setOption({
            backgroundColor: 'transparent',
            title: { text: '高程位置误差历元分布图 (Vertical Error)', left: 'center', top: 8, textStyle: { fontSize: 15, color: '#F8FAFC' } },
            tooltip: { trigger: 'axis' },
            dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 4 }],
            grid: { left: 60, right: 30, top: 55, bottom: 42 },
            xAxis: { type: 'category', data: chartPayload.x_axis, axisLine: { lineStyle: { color: '#475569' } } },
            yAxis: { type: 'value', name: '高程偏差 (m)', nameLocation: 'end', nameGap: 10, splitLine: { lineStyle: { color: '#334155' } } },
            series: [{
                name: '高程误差', type: 'line', data: chartPayload.v_err,
                lineStyle: { color: '#F59E0B', width: 1.6 },
                showSymbol: false
            }]
        });

        // C. ENU 三向误差图 (仿软件经典三层独立子图垂直展开，不重叠不杂乱，共享时间轴联动)
        var echENU = echarts.init(document.getElementById('chart-epoch-enu'), 'dark');
        echENU.setOption({
            backgroundColor: 'transparent',
            title: { text: 'ENU 三向位置误差历元曲线 (E / N / U 分层独立展示)', left: 'center', top: 8, textStyle: { fontSize: 15, color: '#F8FAFC' } },
            tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
            axisPointer: { link: [{ xAxisIndex: 'all' }] },
            dataZoom: [
                { type: 'inside', xAxisIndex: [0, 1, 2] },
                { type: 'slider', xAxisIndex: [0, 1, 2], height: 16, bottom: 4 }
            ],
            grid: [
                { left: 65, right: 30, top: 55, height: '24%' },
                { left: 65, right: 30, top: '38%', height: '24%' },
                { left: 65, right: 30, top: '68%', height: '24%' }
            ],
            xAxis: [
                { gridIndex: 0, type: 'category', data: chartPayload.x_axis, axisLabel: { show: false }, axisTick: { show: false } },
                { gridIndex: 1, type: 'category', data: chartPayload.x_axis, axisLabel: { show: false }, axisTick: { show: false } },
                { gridIndex: 2, type: 'category', data: chartPayload.x_axis, axisLine: { lineStyle: { color: '#475569' } } }
            ],
            yAxis: [
                { gridIndex: 0, type: 'value', name: '东向 dE (m)', nameLocation: 'middle', nameGap: 45, splitLine: { lineStyle: { color: '#334155' } } },
                { gridIndex: 1, type: 'value', name: '北向 dN (m)', nameLocation: 'middle', nameGap: 45, splitLine: { lineStyle: { color: '#334155' } } },
                { gridIndex: 2, type: 'value', name: '天向 dU (m)', nameLocation: 'middle', nameGap: 45, splitLine: { lineStyle: { color: '#334155' } } }
            ],
            series: [
                { name: '东向 dE', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: chartPayload.de, lineStyle: { color: '#EF4444', width: 1.4 }, showSymbol: false },
                { name: '北向 dN', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: chartPayload.dn, lineStyle: { color: '#10B981', width: 1.4 }, showSymbol: false },
                { name: '天向 dU', type: 'line', xAxisIndex: 2, yAxisIndex: 2, data: chartPayload.du, lineStyle: { color: '#38BDF8', width: 1.4 }, showSymbol: false }
            ]
        });

        // D. 靶心散点图 (正圆等比例 1:1，带软件同款同心圆标尺网格与中心十字线)
        var echScatter = echarts.init(document.getElementById('chart-scatter'), 'dark');
        var maxLimit = chartPayload.scatter_limit || 1.0;
        
        // 构造等间距同心圆图形
        var circleGraphics = [];
        var circleSteps = [0.2, 0.4, 0.6, 0.8, 1.0];
        for (var i = 0; i < circleSteps.length; i++) {
            var rVal = maxLimit * circleSteps[i];
            circleGraphics.push({
                type: 'circle',
                shape: { cx: 200, cy: 200, r: 160 * circleSteps[i] },
                style: { stroke: '#475569', fill: 'none', lineWidth: 0.8, lineDash: [3, 3] }
            });
        }

        echScatter.setOption({
            backgroundColor: 'transparent',
            title: { text: '定位偏差散点分布 (靶心图 · 1:1等比例)', left: 'center', top: 4, textStyle: { fontSize: 14, color: '#F8FAFC' } },
            tooltip: { formatter: 'dE: {c[0]} m<br/>dN: {c[1]} m' },
            grid: { left: 40, right: 40, top: 40, bottom: 40 },
            xAxis: {
                type: 'value', min: -maxLimit, max: maxLimit,
                axisLine: { onZero: true, lineStyle: { color: '#64748B' } },
                splitLine: { show: false }
            },
            yAxis: {
                type: 'value', min: -maxLimit, max: maxLimit,
                axisLine: { onZero: true, lineStyle: { color: '#64748B' } },
                splitLine: { show: false }
            },
            graphic: circleGraphics,
            series: [{
                type: 'scatter', symbolSize: 5,
                data: chartPayload.scatter_pts,
                itemStyle: { color: '#38BDF8', opacity: 0.8 }
            }]
        });

        // E. CDF 误差累积分布曲线
        var echCDF = echarts.init(document.getElementById('chart-cdf'), 'dark');
        echCDF.setOption({
            backgroundColor: 'transparent',
            title: { text: '误差累积概率分布曲线 (CDF)', left: 'center', top: 8, textStyle: { fontSize: 15, color: '#F8FAFC' } },
            tooltip: { trigger: 'axis', formatter: '误差: {c[0]} m<br/>累积概率: {c[1]} %' },
            grid: { left: 60, right: 30, top: 55, bottom: 42 },
            xAxis: { type: 'value', name: '水平误差 (m)', splitLine: { lineStyle: { color: '#334155' } } },
            yAxis: { type: 'value', name: '累积概率 (%)', max: 100, splitLine: { lineStyle: { color: '#334155' } } },
            series: [{
                name: 'CDF', type: 'line', data: chartPayload.cdf_pts,
                lineStyle: { color: '#10B981', width: 2 },
                areaStyle: { color: 'rgba(16, 185, 129, 0.15)' },
                showSymbol: false
            }]
        });

        // F. 速度时序曲线
        var echSpeed = echarts.init(document.getElementById('chart-speed'), 'dark');
        echSpeed.setOption({
            backgroundColor: 'transparent',
            title: { text: '对地运行速度时序曲线', left: 'center', top: 8, textStyle: { fontSize: 15, color: '#F8FAFC' } },
            tooltip: { trigger: 'axis' },
            dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 4 }],
            grid: { left: 60, right: 30, top: 55, bottom: 42 },
            xAxis: { type: 'category', data: chartPayload.x_axis },
            yAxis: { type: 'value', name: '速度 (m/s)', nameLocation: 'end', nameGap: 10, splitLine: { lineStyle: { color: '#334155' } } },
            series: [{
                name: '运行速度', type: 'line', data: chartPayload.speed,
                lineStyle: { color: '#A855F7', width: 1.6 },
                showSymbol: false
            }]
        });

        window.addEventListener('resize', function() {
            echH.resize(); echV.resize(); echENU.resize(); echScatter.resize(); echCDF.resize(); echSpeed.resize();
        });
    </script>
</body>
</html>
"""

def export_html_report(parent_window, segments, truth, table_metrics, config=None):
    if not segments:
        QMessageBox.warning(parent_window, "提示", "没有测试数据可供导出。")
        return

    save_path, _ = QFileDialog.getSaveFileName(
        parent_window, "导出交互式 HTML 精度分析报告", "GNSS定位精度交互式报告.html", "HTML Files (*.html)"
    )
    if not save_path:
        return

    progress = QProgressDialog("正在生成交互式 HTML 报告...", "取消", 0, 100, parent_window)
    progress.setWindowTitle("导出 HTML 报告")
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumDuration(0)
    progress.setValue(10)
    QApplication.processEvents()

    try:
        active_segs = [s for s in segments if s.get('active', True)]
        if not active_segs:
            active_segs = segments

        title_name = active_segs[0].get('name', 'GNSS_Test_Report')
        gen_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 检查主软件当前是否勾选了“按RTK状态着色”
        color_by_status_checked = False
        if hasattr(parent_window, 'gis_map_widget') and hasattr(parent_window.gis_map_widget, 'cb_color_by_status'):
            color_by_status_checked = parent_window.gis_map_widget.cb_color_by_status.isChecked()
        checked_rtk_attr = "checked" if color_by_status_checked else ""

        # 1. 精准提炼指标看板核心数据
        total_epochs = sum(len(s.get('epochs', [])) for s in active_segs)
        
        fix_rates, h_rms_list, h_95_list, v_rms_list, max_h_list = [], [], [], [], []
        for s in active_segs:
            m = s.get('metrics', {})
            fr = m.get('rtk_fix_rate', m.get('fix_rate'))
            if fr is not None: fix_rates.append(float(fr))
            hr = m.get('rms_h', m.get('h_rms'))
            if hr is not None: h_rms_list.append(float(hr))
            c95 = m.get('cep95', m.get('h_95'))
            if c95 is not None: h_95_list.append(float(c95))
            vr = m.get('rms_v', m.get('v_rms'))
            if vr is not None: v_rms_list.append(float(vr))
            mh = m.get('max_h', m.get('h_max'))
            if mh is not None: max_h_list.append(float(mh))

        if table_metrics and (not h_rms_list or not fix_rates):
            col_map = {}
            for col_i in range(table_metrics.columnCount()):
                header_txt = table_metrics.horizontalHeaderItem(col_i).text() if table_metrics.horizontalHeaderItem(col_i) else ""
                col_map[header_txt] = col_i

            for row_i in range(table_metrics.rowCount()):
                for k in ["固定率", "RTK固定率", "Fix Rate"]:
                    if k in col_map:
                        item = table_metrics.item(row_i, col_map[k])
                        if item and item.text().endswith('%'):
                            try: fix_rates.append(float(item.text().rstrip('%')))
                            except Exception: pass
                for k in ["水平RMS(m)", "水平 RMS (m)", "H_RMS"]:
                    if k in col_map:
                        item = table_metrics.item(row_i, col_map[k])
                        if item:
                            try: h_rms_list.append(float(item.text().rstrip('m').strip()))
                            except Exception: pass
                for k in ["水平95%(m)", "水平 95% (m)", "95%"]:
                    if k in col_map:
                        item = table_metrics.item(row_i, col_map[k])
                        if item:
                            try: h_95_list.append(float(item.text().rstrip('m').strip()))
                            except Exception: pass
                for k in ["高程RMS(m)", "高程 RMS (m)", "V_RMS"]:
                    if k in col_map:
                        item = table_metrics.item(row_i, col_map[k])
                        if item:
                            try: v_rms_list.append(float(item.text().rstrip('m').strip()))
                            except Exception: pass
                for k in ["最大水平偏差(m)", "最大偏差", "Max H"]:
                    if k in col_map:
                        item = table_metrics.item(row_i, col_map[k])
                        if item:
                            try: max_h_list.append(float(item.text().rstrip('m').strip()))
                            except Exception: pass

        fix_rate_val = f"{sum(fix_rates)/len(fix_rates):.2f}" if fix_rates else "100.00"
        h_rms_val = f"{sum(h_rms_list)/len(h_rms_list):.3f}" if h_rms_list else "0.000"
        h_95_val = f"{sum(h_95_list)/len(h_95_list):.3f}" if h_95_list else "0.000"
        v_rms_val = f"{sum(v_rms_list)/len(v_rms_list):.3f}" if v_rms_list else "0.000"
        max_h_val = f"{max(max_h_list):.3f}" if max_h_list else "0.000"

        progress.setValue(30)
        QApplication.processEvents()

        # 2. 生成表格 HTML
        table_html = "<table><thead><tr>"
        col_count = table_metrics.columnCount() if table_metrics else 0
        row_count = table_metrics.rowCount() if table_metrics else 0
        for c in range(col_count):
            table_html += f"<th>{table_metrics.horizontalHeaderItem(c).text()}</th>"
        table_html += "</tr></thead><tbody>"

        for r in range(row_count):
            table_html += "<tr>"
            for c in range(col_count):
                it = table_metrics.item(r, c)
                table_html += f"<td>{it.text() if it else ''}</td>"
            table_html += "</tr>"
        table_html += "</tbody></table>"

        # 3. 构造地图数据与图表数据 Payload (做 GCJ-02 纠偏转换)
        map_points = []
        x_axis = []
        h_err_data = []
        v_err_data = []
        de_data = []
        dn_data = []
        du_data = []
        scatter_pts = []
        speed_data = []
        all_h_errors = []
        max_dist_scatter = 0.01

        step = max(1, total_epochs // 5000)
        curr_idx = 0

        for s in active_segs:
            epochs = s.get('epochs', [])
            metrics = s.get('metrics', {})

            de_list = metrics.get('de', metrics.get('de_list', []))
            dn_list = metrics.get('dn', metrics.get('dn_list', []))
            du_list = metrics.get('v_errors', metrics.get('du_list', []))
            h_err_list = metrics.get('h_errors', [])
            v_err_list = metrics.get('v_errors', [])
            speed_test_list = metrics.get('speed_test', [])

            if not de_list and 'enu_points' in metrics and metrics['enu_points']:
                de_list = [p.get('e', 0.0) for p in metrics['enu_points']]
                dn_list = [p.get('n', 0.0) for p in metrics['enu_points']]
                du_list = [p.get('u', 0.0) for p in metrics['enu_points']]

            for i, ep in enumerate(epochs):
                h_val = h_err_list[i] if i < len(h_err_list) else None
                if h_val is not None:
                    all_h_errors.append(h_val)

                if curr_idx % step == 0:
                    t_str = ep.get('time_str', str(curr_idx + 1))
                    x_axis.append(t_str)
                    h_err_data.append(round(h_val, 4) if h_val is not None else None)
                    
                    v_val = v_err_list[i] if i < len(v_err_list) else None
                    v_err_data.append(round(v_val, 4) if v_val is not None else None)

                    de = de_list[i] if i < len(de_list) else None
                    dn = dn_list[i] if i < len(dn_list) else None
                    du = du_list[i] if i < len(du_list) else None
                    de_data.append(round(de, 4) if de is not None else None)
                    dn_data.append(round(dn, 4) if dn is not None else None)
                    du_data.append(round(du, 4) if du is not None else None)

                    if de is not None and dn is not None:
                        dist = (de**2 + dn**2)**0.5
                        max_dist_scatter = max(max_dist_scatter, dist)
                        if len(scatter_pts) < 2500:
                            scatter_pts.append([round(de, 4), round(dn, 4)])

                    sp = speed_test_list[i] if i < len(speed_test_list) else ep.get('speed', 0.0)
                    speed_data.append(round(float(sp), 2) if sp is not None else 0.0)

                    # WGS-84 -> GCJ-02 火星坐标纠偏转换
                    raw_lat = float(ep.get('lat', 0.0))
                    raw_lon = float(ep.get('lon', 0.0))
                    gcj_lat, gcj_lon = wgs84_to_gcj02(raw_lat, raw_lon)

                    map_points.append({
                        'lat': gcj_lat,
                        'lon': gcj_lon,
                        'time': t_str,
                        'status': ep.get('quality', ep.get('status', 1)),
                        'h_err': h_val
                    })
                curr_idx += 1

        progress.setValue(70)
        QApplication.processEvents()

        # 计算 CDF 累积分布点
        cdf_pts = []
        if all_h_errors:
            sorted_errs = sorted(all_h_errors)
            N_err = len(sorted_errs)
            cdf_step = max(1, N_err // 200)
            for k in range(0, N_err, cdf_step):
                cdf_pts.append([round(sorted_errs[k], 4), round((k + 1) / N_err * 100, 2)])
            cdf_pts.append([round(sorted_errs[-1], 4), 100.0])

        scatter_limit = round(max_dist_scatter * 1.15, 3)

        map_payload_json = json.dumps({'points': map_points})
        chart_payload_json = json.dumps({
            'x_axis': x_axis,
            'h_err': h_err_data,
            'v_err': v_err_data,
            'de': de_data,
            'dn': dn_data,
            'du': du_data,
            'scatter_pts': scatter_pts,
            'scatter_limit': scatter_limit,
            'cdf_pts': cdf_pts,
            'speed': speed_data,
            'h_rms': float(h_rms_val) if h_rms_val != 'N/A' else 0,
            'h_95': float(h_95_val) if h_95_val != 'N/A' else 0
        })

        # 4. 组装并写入 HTML 文件
        html_content = HTML_REPORT_TEMPLATE
        html_content = html_content.replace('__REPORT_TITLE__', title_name)
        html_content = html_content.replace('__GEN_TIME__', gen_time)
        html_content = html_content.replace('__TOTAL_EPOCHS__', str(total_epochs))
        html_content = html_content.replace('__FIX_RATE__', fix_rate_val)
        html_content = html_content.replace('__H_RMS__', h_rms_val)
        html_content = html_content.replace('__H_95__', h_95_val)
        html_content = html_content.replace('__V_RMS__', v_rms_val)
        html_content = html_content.replace('__MAX_H_ERR__', max_h_val)
        html_content = html_content.replace('__CHECKED_RTK_COLOR__', checked_rtk_attr)
        html_content = html_content.replace('__METRICS_TABLE_HTML__', table_html)
        html_content = html_content.replace('__MAP_PAYLOAD_JSON__', map_payload_json)
        html_content = html_content.replace('__CHART_PAYLOAD_JSON__', chart_payload_json)

        progress.setValue(90)
        QApplication.processEvents()

        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        progress.setValue(100)
        QMessageBox.information(parent_window, "成功", f"交互式 HTML 评定报告已成功生成:\n{save_path}\n可直接使用任意浏览器双击打开！")

    except Exception as e:
        QMessageBox.critical(parent_window, "导出失败", f"生成 HTML 报告时发生错误:\n{e}")
