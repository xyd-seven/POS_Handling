# -*- coding: utf-8 -*-
"""
Interactive Standalone HTML GNSS Report Exporter (Multi-Segment Edition v3)
- Fully supports multiple imported files/segments
- Strictly matches line colors defined in desktop software for each file
- Shows dynamic interactive legends on both map and all error charts
- Multi-series overlay comparison for horizontal, vertical, ENU, scatter, CDF, and speed
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

        /* Map Container & Legend */
        #map-wrapper {
            position: relative;
            width: 100%;
            height: 520px;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid var(--border);
        }
        #map-container {
            width: 100%;
            height: 100%;
            background: #0F172A;
        }
        .map-legend {
            position: absolute;
            bottom: 24px;
            left: 24px;
            z-index: 1000;
            background: rgba(15, 23, 42, 0.88);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 12px;
            color: var(--text-main);
            box-shadow: 0 4px 16px rgba(0,0,0,0.4);
            max-width: 360px;
        }
        .map-legend-title {
            font-weight: bold;
            margin-bottom: 6px;
            color: var(--brand);
            font-size: 12px;
        }
        .map-legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
        }
        .map-legend-color {
            width: 14px;
            height: 4px;
            border-radius: 2px;
            display: inline-block;
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
            height: 440px;
        }
        .chart-box-tall {
            height: 560px;
        }
        .bullseye-container {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 440px;
            background: #0F172A;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
        }
        #chart-scatter {
            width: 420px;
            height: 420px;
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
                <p>测试对象: __REPORT_TITLE__  |  报告生成时间: __GEN_TIME__  |  分段总数: __SEG_COUNT__  |  数据历元总数: __TOTAL_EPOCHS__</p>
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

        <!-- Section 1: 空间轨迹 (支持多分段文件对比、软件配置颜色、图例及交互控制) -->
        <div class="section-card">
            <div class="section-title">
                <div class="section-title-left">
                    🗺️ 空间二维运行轨迹与解状态投影 (多文件对比)
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
            <div id="map-wrapper">
                <div id="map-container"></div>
                <div id="map-legend" class="map-legend"></div>
            </div>
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

        <!-- Section 3: 误差曲线大看板 (多文件多曲线颜色同步对比) -->
        <div class="section-card">
            <div class="section-title">
                <div class="section-title-left">📈 误差时序历元分布与联合分析 (各文件采用软件设置专属颜色 · 点击图例隐藏/显示)</div>
            </div>

            <!-- 第一行：水平误差与垂直误差 (宽屏 2 列大图) -->
            <div class="charts-row-2col">
                <div class="chart-box" id="chart-epoch-h"></div>
                <div class="chart-box" id="chart-epoch-v"></div>
            </div>

            <!-- 第二行：三向 ENU 误差 (三层独立垂直展开，各文件多线对比) -->
            <div class="charts-row-full">
                <div class="chart-box chart-box-tall" id="chart-epoch-enu"></div>
            </div>

            <!-- 第三行：自适应正圆靶心图 (多文件散点) 与 CDF 累积分布图 (多文件曲线) -->
            <div class="charts-row-2col">
                <div class="bullseye-container">
                    <div id="chart-scatter"></div>
                </div>
                <div class="chart-box" id="chart-cdf"></div>
            </div>

            <!-- 第四行：运行速度曲线 -->
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
        var segmentsData = __SEGMENTS_PAYLOAD_JSON__;
        var globalTimeline = __GLOBAL_TIMELINE_JSON__;
        var maxLimit = __SCATTER_LIMIT__ || 1.0;

        // 1. 初始化 Leaflet 轨迹地图
        var map = L.map('map-container', { zoomControl: true, attributionControl: false }).setView([39.9, 116.4], 13);
        L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
            subdomains: ['1','2','3','4'], maxZoom: 18
        }).addTo(map);

        var mapLayersGroup = L.layerGroup().addTo(map);

        function updateMapDisplay() {
            mapLayersGroup.clearLayers();
            var legendEl = document.getElementById('map-legend');
            var isColorByStatus = document.getElementById('chk-rtk-color').checked;
            var displayMode = document.getElementById('sel-map-mode').value;
            var statusColors = { 4: '#10B981', 5: '#F59E0B', 1: '#38BDF8', 2: '#6366F1' };

            // 渲染图例
            var legendHtml = '';
            if (isColorByStatus) {
                legendHtml += '<div class="map-legend-title">定位解状态图例:</div>';
                legendHtml += '<div class="map-legend-item"><span class="map-legend-color" style="background:#10B981;"></span> RTK固定解 (Fix)</div>';
                legendHtml += '<div class="map-legend-item"><span class="map-legend-color" style="background:#F59E0B;"></span> RTK浮点解 (Float)</div>';
                legendHtml += '<div class="map-legend-item"><span class="map-legend-color" style="background:#38BDF8;"></span> 单点解 (Single)</div>';
            } else {
                legendHtml += '<div class="map-legend-title">轨迹分段与文件图例:</div>';
                for (var s = 0; s < segmentsData.length; s++) {
                    var seg = segmentsData[s];
                    legendHtml += '<div class="map-legend-item"><span class="map-legend-color" style="background:' + seg.color + ';"></span> ' + seg.name + '</div>';
                }
            }
            legendEl.innerHTML = legendHtml;

            // 逐分段绘制轨迹
            for (var s = 0; s < segmentsData.length; s++) {
                var seg = segmentsData[s];
                var pts = seg.points;
                if (!pts || pts.length === 0) continue;

                // A. 绘制折线
                if (displayMode !== 'points_only') {
                    if (isColorByStatus) {
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
                                L.polyline(currLine, { color: color, weight: 3.5, opacity: 0.9 }).addTo(mapLayersGroup);
                                currQuality = p.status;
                                currLine = [currLine[currLine.length - 1], [p.lat, p.lon]];
                            }
                        }
                        if (currLine.length > 0) {
                            var color = statusColors[currQuality] || '#94A3B8';
                            L.polyline(currLine, { color: color, weight: 3.5, opacity: 0.9 }).addTo(mapLayersGroup);
                        }
                    } else {
                        // 使用各分段在软件中的专属颜色
                        var allLatLngs = pts.map(function(p) { return [p.lat, p.lon]; });
                        L.polyline(allLatLngs, { color: seg.color, weight: 3.5, opacity: 0.9 }).addTo(mapLayersGroup);
                    }
                }

                // B. 绘制采样点
                if (displayMode !== 'line_only') {
                    var step = Math.max(1, Math.floor(pts.length / 500));
                    for (var i = 0; i < pts.length; i += step) {
                        var p = pts[i];
                        var dotColor = isColorByStatus ? (statusColors[p.status] || '#94A3B8') : seg.color;
                        var circle = L.circleMarker([p.lat, p.lon], {
                            radius: 3.5, fillColor: dotColor, color: '#FFFFFF', weight: 0.5, fillOpacity: 0.9
                        }).addTo(mapLayersGroup);
                        circle.bindPopup(
                            "<b>文件/分段:</b> " + seg.name + "<br/>" +
                            "<b>序号:</b> " + (i+1) + "<br/>" +
                            "<b>时间:</b> " + p.time + "<br/>" +
                            "<b>解状态:</b> " + (p.status == 4 ? 'RTK固定解' : (p.status == 5 ? 'RTK浮点解' : '单点解')) + "<br/>" +
                            "<b>水平误差:</b> " + (p.h_err !== null ? p.h_err.toFixed(3) + 'm' : 'N/A')
                        );
                    }
                }
            }
        }

        // 初始地图视口缩放
        var allBounds = [];
        for (var s = 0; s < segmentsData.length; s++) {
            var pts = segmentsData[s].points;
            for (var i = 0; i < pts.length; i++) {
                allBounds.push([pts[i].lat, pts[i].lon]);
            }
        }
        if (allBounds.length > 0) {
            updateMapDisplay();
            var poly = L.polyline(allBounds);
            map.fitBounds(poly.getBounds(), { padding: [35, 35] });
        }

        // 2. 初始化 ECharts 动态图表 (全支持多分段对比)
        var legendNames = segmentsData.map(function(s) { return s.name; });

        // A. 水平位置误差分布图 (多文件多曲线对比)
        var seriesH = segmentsData.map(function(s) {
            return {
                name: s.name, type: 'line', data: s.h_series,
                lineStyle: { color: s.color, width: 1.8 },
                itemStyle: { color: s.color },
                showSymbol: false
            };
        });
        var echH = echarts.init(document.getElementById('chart-epoch-h'), 'dark');
        echH.setOption({
            backgroundColor: 'transparent',
            title: { text: '水平位置误差历元分布图 (2D Error)', left: 'center', top: 8, textStyle: { fontSize: 15, color: '#F8FAFC' } },
            tooltip: { trigger: 'axis' },
            legend: { top: 32, data: legendNames, textStyle: { color: '#94A3B8' } },
            dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 4 }],
            grid: { left: 60, right: 30, top: 65, bottom: 42 },
            xAxis: { type: 'category', data: globalTimeline, axisLine: { lineStyle: { color: '#475569' } } },
            yAxis: { type: 'value', name: '偏差 (m)', nameLocation: 'end', nameGap: 10, splitLine: { lineStyle: { color: '#334155' } } },
            series: seriesH
        });

        // B. 高程位置误差分布图 (多文件多曲线对比)
        var seriesV = segmentsData.map(function(s) {
            return {
                name: s.name, type: 'line', data: s.v_series,
                lineStyle: { color: s.color, width: 1.8 },
                itemStyle: { color: s.color },
                showSymbol: false
            };
        });
        var echV = echarts.init(document.getElementById('chart-epoch-v'), 'dark');
        echV.setOption({
            backgroundColor: 'transparent',
            title: { text: '高程位置误差历元分布图 (Vertical Error)', left: 'center', top: 8, textStyle: { fontSize: 15, color: '#F8FAFC' } },
            tooltip: { trigger: 'axis' },
            legend: { top: 32, data: legendNames, textStyle: { color: '#94A3B8' } },
            dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 4 }],
            grid: { left: 60, right: 30, top: 65, bottom: 42 },
            xAxis: { type: 'category', data: globalTimeline, axisLine: { lineStyle: { color: '#475569' } } },
            yAxis: { type: 'value', name: '高程偏差 (m)', nameLocation: 'end', nameGap: 10, splitLine: { lineStyle: { color: '#334155' } } },
            series: seriesV
        });

        // C. ENU 三向误差图 (三层独立展开，每层均支持多文件对比)
        var seriesENU = [];
        for (var s = 0; s < segmentsData.length; s++) {
            var seg = segmentsData[s];
            // 东向层
            seriesENU.push({
                name: seg.name + ' - dE', type: 'line', xAxisIndex: 0, yAxisIndex: 0,
                data: seg.de_series, lineStyle: { color: seg.color, width: 1.6 },
                itemStyle: { color: seg.color }, showSymbol: false
            });
            // 北向层
            seriesENU.push({
                name: seg.name + ' - dN', type: 'line', xAxisIndex: 1, yAxisIndex: 1,
                data: seg.dn_series, lineStyle: { color: seg.color, width: 1.6, type: 'dashed' },
                itemStyle: { color: seg.color }, showSymbol: false
            });
            // 天向层
            seriesENU.push({
                name: seg.name + ' - dU', type: 'line', xAxisIndex: 2, yAxisIndex: 2,
                data: seg.du_series, lineStyle: { color: seg.color, width: 1.6, type: 'dotted' },
                itemStyle: { color: seg.color }, showSymbol: false
            });
        }
        var echENU = echarts.init(document.getElementById('chart-epoch-enu'), 'dark');
        echENU.setOption({
            backgroundColor: 'transparent',
            title: { text: 'ENU 三向位置误差历元曲线 (E / N / U 分层独立展示 · 多文件对比)', left: 'center', top: 8, textStyle: { fontSize: 15, color: '#F8FAFC' } },
            tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
            axisPointer: { link: [{ xAxisIndex: 'all' }] },
            legend: { top: 32, data: legendNames, textStyle: { color: '#94A3B8' } },
            dataZoom: [
                { type: 'inside', xAxisIndex: [0, 1, 2] },
                { type: 'slider', xAxisIndex: [0, 1, 2], height: 16, bottom: 4 }
            ],
            grid: [
                { left: 65, right: 30, top: 65, height: '23%' },
                { left: 65, right: 30, top: '42%', height: '23%' },
                { left: 65, right: 30, top: '70%', height: '23%' }
            ],
            xAxis: [
                { gridIndex: 0, type: 'category', data: globalTimeline, axisLabel: { show: false }, axisTick: { show: false } },
                { gridIndex: 1, type: 'category', data: globalTimeline, axisLabel: { show: false }, axisTick: { show: false } },
                { gridIndex: 2, type: 'category', data: globalTimeline, axisLine: { lineStyle: { color: '#475569' } } }
            ],
            yAxis: [
                { gridIndex: 0, type: 'value', name: '东向 dE (m)', nameLocation: 'middle', nameGap: 45, splitLine: { lineStyle: { color: '#334155' } } },
                { gridIndex: 1, type: 'value', name: '北向 dN (m)', nameLocation: 'middle', nameGap: 45, splitLine: { lineStyle: { color: '#334155' } } },
                { gridIndex: 2, type: 'value', name: '天向 dU (m)', nameLocation: 'middle', nameGap: 45, splitLine: { lineStyle: { color: '#334155' } } }
            ],
            series: seriesENU
        });

        // D. 靶心散点图 (正圆 1:1，多文件不同颜色对比)
        var circleGraphics = [];
        var circleSteps = [0.2, 0.4, 0.6, 0.8, 1.0];
        for (var i = 0; i < circleSteps.length; i++) {
            circleGraphics.push({
                type: 'circle',
                shape: { cx: 210, cy: 210, r: 170 * circleSteps[i] },
                style: { stroke: '#475569', fill: 'none', lineWidth: 0.8, lineDash: [3, 3] }
            });
        }
        var seriesScatter = segmentsData.map(function(s) {
            return {
                name: s.name, type: 'scatter', symbolSize: 5,
                data: s.scatter_pts,
                itemStyle: { color: s.color, opacity: 0.85 }
            };
        });
        var echScatter = echarts.init(document.getElementById('chart-scatter'), 'dark');
        echScatter.setOption({
            backgroundColor: 'transparent',
            title: { text: '定位偏差散点分布 (靶心图 · 1:1正圆)', left: 'center', top: 4, textStyle: { fontSize: 14, color: '#F8FAFC' } },
            tooltip: { formatter: function(p) { return '<b>' + p.seriesName + '</b><br/>dE: ' + p.data[0] + 'm<br/>dN: ' + p.data[1] + 'm'; } },
            legend: { top: 26, data: legendNames, textStyle: { color: '#94A3B8', fontSize: 11 } },
            grid: { left: 40, right: 40, top: 48, bottom: 40 },
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
            series: seriesScatter
        });

        // E. CDF 误差累积分布曲线 (多文件对比)
        var seriesCDF = segmentsData.map(function(s) {
            return {
                name: s.name, type: 'line', data: s.cdf_pts,
                lineStyle: { color: s.color, width: 2 },
                itemStyle: { color: s.color },
                showSymbol: false
            };
        });
        var echCDF = echarts.init(document.getElementById('chart-cdf'), 'dark');
        echCDF.setOption({
            backgroundColor: 'transparent',
            title: { text: '误差累积概率分布曲线 (CDF)', left: 'center', top: 8, textStyle: { fontSize: 15, color: '#F8FAFC' } },
            tooltip: { trigger: 'axis', formatter: function(params) {
                var res = '误差: ' + params[0].value[0] + 'm<br/>';
                for (var i = 0; i < params.length; i++) {
                    res += params[i].marker + params[i].seriesName + ': ' + params[i].value[1] + '%<br/>';
                }
                return res;
            } },
            legend: { top: 32, data: legendNames, textStyle: { color: '#94A3B8' } },
            grid: { left: 60, right: 30, top: 65, bottom: 42 },
            xAxis: { type: 'value', name: '水平误差 (m)', splitLine: { lineStyle: { color: '#334155' } } },
            yAxis: { type: 'value', name: '累积概率 (%)', max: 100, splitLine: { lineStyle: { color: '#334155' } } },
            series: seriesCDF
        });

        // F. 速度时序曲线 (多文件对比)
        var seriesSpeed = segmentsData.map(function(s) {
            return {
                name: s.name, type: 'line', data: s.speed_series,
                lineStyle: { color: s.color, width: 1.8 },
                itemStyle: { color: s.color },
                showSymbol: false
            };
        });
        var echSpeed = echarts.init(document.getElementById('chart-speed'), 'dark');
        echSpeed.setOption({
            backgroundColor: 'transparent',
            title: { text: '对地运行速度时序曲线 (多文件对比)', left: 'center', top: 8, textStyle: { fontSize: 15, color: '#F8FAFC' } },
            tooltip: { trigger: 'axis' },
            legend: { top: 32, data: legendNames, textStyle: { color: '#94A3B8' } },
            dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 4 }],
            grid: { left: 60, right: 30, top: 65, bottom: 42 },
            xAxis: { type: 'category', data: globalTimeline },
            yAxis: { type: 'value', name: '速度 (m/s)', nameLocation: 'end', nameGap: 10, splitLine: { lineStyle: { color: '#334155' } } },
            series: seriesSpeed
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

        title_name = "、".join([s.get('name', f'分段{i+1}') for i, s in enumerate(active_segs)])
        gen_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 检查主软件当前是否勾选了“按RTK状态着色”
        color_by_status_checked = False
        if hasattr(parent_window, 'gis_map_widget') and hasattr(parent_window.gis_map_widget, 'cb_color_by_status'):
            color_by_status_checked = parent_window.gis_map_widget.cb_color_by_status.isChecked()
        checked_rtk_attr = "checked" if color_by_status_checked else ""

        # 1. 汇总指标卡片数据
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

        # 3. 构造多分段结构化数据 (Multi-Segment Datasets)
        # 先建立统一的全局时间刻度或历元轴
        all_timestamps = []
        for s in active_segs:
            epochs = s.get('epochs', [])
            for ep in epochs:
                t_str = ep.get('time_str')
                if t_str and t_str not in all_timestamps:
                    all_timestamps.append(t_str)

        if not all_timestamps:
            max_len = max(len(s.get('epochs', [])) for s in active_segs) if active_segs else 0
            global_timeline = [str(i+1) for i in range(max_len)]
        else:
            global_timeline = sorted(all_timestamps)

        # 降采样限制最大 4000 点
        step = max(1, len(global_timeline) // 4000)
        filtered_timeline = global_timeline[::step]
        time_index_map = {t: idx for idx, t in enumerate(filtered_timeline)}

        segments_payload = []
        global_max_scatter = 0.01

        for s_idx, s in enumerate(active_segs):
            s_name = s.get('name', f"分段_{s_idx+1}")
            # 严格使用软件中的配色
            s_color = s.get('color', '#38BDF8')
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

            # 构建时序曲线数据字典
            h_dict, v_dict, de_dict, dn_dict, du_dict, sp_dict = {}, {}, {}, {}, {}, {}
            scatter_pts = []
            s_map_points = []
            seg_all_h = []

            for i, ep in enumerate(epochs):
                t_str = ep.get('time_str', str(i+1))
                h_val = h_err_list[i] if i < len(h_err_list) else None
                v_val = v_err_list[i] if i < len(v_err_list) else None
                de = de_list[i] if i < len(de_list) else None
                dn = dn_list[i] if i < len(dn_list) else None
                du = du_list[i] if i < len(du_list) else None

                if h_val is not None:
                    seg_all_h.append(h_val)

                if de is not None and dn is not None:
                    dist = (de**2 + dn**2)**0.5
                    global_max_scatter = max(global_max_scatter, dist)
                    if len(scatter_pts) < 1500 and (i % max(1, len(epochs)//1500) == 0):
                        scatter_pts.append([round(de, 4), round(dn, 4)])

                # 地图轨迹点做 GCJ-02 转换
                raw_lat = float(ep.get('lat', 0.0))
                raw_lon = float(ep.get('lon', 0.0))
                if abs(raw_lat) > 1e-4 and abs(raw_lon) > 1e-4:
                    gcj_lat, gcj_lon = wgs84_to_gcj02(raw_lat, raw_lon)
                    s_map_points.append({
                        'lat': gcj_lat,
                        'lon': gcj_lon,
                        'time': t_str,
                        'status': ep.get('quality', ep.get('status', 1)),
                        'h_err': h_val
                    })

                # 时序聚合
                h_dict[t_str] = round(h_val, 4) if h_val is not None else None
                v_dict[t_str] = round(v_val, 4) if v_val is not None else None
                de_dict[t_str] = round(de, 4) if de is not None else None
                dn_dict[t_str] = round(dn, 4) if dn is not None else None
                du_dict[t_str] = round(du, 4) if du is not None else None
                sp = speed_test_list[i] if i < len(speed_test_list) else ep.get('speed', 0.0)
                sp_dict[t_str] = round(float(sp), 2) if sp is not None else 0.0

            # 对齐到 filtered_timeline
            h_series = [h_dict.get(t) for t in filtered_timeline]
            v_series = [v_dict.get(t) for t in filtered_timeline]
            de_series = [de_dict.get(t) for t in filtered_timeline]
            dn_series = [dn_dict.get(t) for t in filtered_timeline]
            du_series = [du_dict.get(t) for t in filtered_timeline]
            speed_series = [sp_dict.get(t) for t in filtered_timeline]

            # 计算各分段的 CDF
            cdf_pts = []
            if seg_all_h:
                sorted_errs = sorted(seg_all_h)
                N_err = len(sorted_errs)
                cdf_step = max(1, N_err // 150)
                for k in range(0, N_err, cdf_step):
                    cdf_pts.append([round(sorted_errs[k], 4), round((k + 1) / N_err * 100, 2)])
                cdf_pts.append([round(sorted_errs[-1], 4), 100.0])

            segments_payload.append({
                'name': s_name,
                'color': s_color,
                'points': s_map_points,
                'h_series': h_series,
                'v_series': v_series,
                'de_series': de_series,
                'dn_series': dn_series,
                'du_series': du_series,
                'speed_series': speed_series,
                'scatter_pts': scatter_pts,
                'cdf_pts': cdf_pts
            })

        scatter_limit = round(global_max_scatter * 1.15, 3)

        progress.setValue(80)
        QApplication.processEvents()

        # 4. 组装并写入 HTML 文件
        html_content = HTML_REPORT_TEMPLATE
        html_content = html_content.replace('__REPORT_TITLE__', title_name)
        html_content = html_content.replace('__GEN_TIME__', gen_time)
        html_content = html_content.replace('__SEG_COUNT__', str(len(active_segs)))
        html_content = html_content.replace('__TOTAL_EPOCHS__', str(total_epochs))
        html_content = html_content.replace('__FIX_RATE__', fix_rate_val)
        html_content = html_content.replace('__H_RMS__', h_rms_val)
        html_content = html_content.replace('__H_95__', h_95_val)
        html_content = html_content.replace('__V_RMS__', v_rms_val)
        html_content = html_content.replace('__MAX_H_ERR__', max_h_val)
        html_content = html_content.replace('__CHECKED_RTK_COLOR__', checked_rtk_attr)
        html_content = html_content.replace('__METRICS_TABLE_HTML__', table_html)
        html_content = html_content.replace('__SEGMENTS_PAYLOAD_JSON__', json.dumps(segments_payload))
        html_content = html_content.replace('__GLOBAL_TIMELINE_JSON__', json.dumps(filtered_timeline))
        html_content = html_content.replace('__SCATTER_LIMIT__', str(scatter_limit))

        progress.setValue(95)
        QApplication.processEvents()

        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        progress.setValue(100)
        QMessageBox.information(parent_window, "成功", f"交互式 HTML 评定报告已成功生成:\n{save_path}\n可直接使用任意浏览器双击打开！")

    except Exception as e:
        QMessageBox.critical(parent_window, "导出失败", f"生成 HTML 报告时发生错误:\n{e}")
