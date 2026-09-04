# -*- coding: utf-8 -*-
"""
Interactive Standalone HTML GNSS Report Exporter (Pro Edition v9)
- Isolated Fullscreen Modal: uses a dedicated clean overlay modal for chart zoom, completely preventing any CSS Grid collapse or side-effect on sibling charts
- High-contrast axis ticks & split lines in both dark and light modes
- Supports Epoch Alignment and Time Alignment dual-mode
- High elevation absolute error support
- Solid lines for all ENU subplots
- Multi-segment overlay with software colors, map legend, and 1:1 circular bullseye
"""

import os
import json
import math
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog, QApplication
from coord_transform import wgs84_to_gcj02

HTML_REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GNSS 定位精度测试与综合评定报告 - __REPORT_TITLE__</title>
    <!-- Leaflet & ECharts CDN -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        :root[data-theme="dark"] {
            --bg-main: #0B1120;
            --bg-card: #1E293B;
            --bg-subtle: #0F172A;
            --border: #334155;
            --border-hover: #38BDF8;
            --text-main: #F8FAFC;
            --text-sub: #94A3B8;
            --text-muted: #64748B;
            --brand: #38BDF8;
            --success: #10B981;
            --warning: #F59E0B;
            --danger: #EF4444;
            --chart-split: #334155;
            --chart-axis: #64748B;
            --table-hover: rgba(56, 189, 248, 0.06);
            --legend-bg: rgba(15, 23, 42, 0.88);
            --modal-bg: rgba(11, 17, 32, 0.95);
        }

        :root[data-theme="light"] {
            --bg-main: #F1F5F9;
            --bg-card: #FFFFFF;
            --bg-subtle: #F8FAFC;
            --border: #CBD5E1;
            --border-hover: #0284C7;
            --text-main: #0F172A;
            --text-sub: #475569;
            --text-muted: #94A3B8;
            --brand: #0284C7;
            --success: #059669;
            --warning: #D97706;
            --danger: #DC2626;
            --chart-split: #CBD5E1;
            --chart-axis: #475569;
            --table-hover: rgba(2, 132, 199, 0.05);
            --legend-bg: rgba(255, 255, 255, 0.94);
            --modal-bg: rgba(241, 245, 249, 0.96);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            line-height: 1.6;
            padding: 20px;
            transition: background-color 0.25s, color 0.25s;
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
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.06);
        }
        .header-title h1 { font-size: 24px; color: var(--text-main); margin-bottom: 6px; }
        .header-title p { font-size: 13px; color: var(--text-sub); }
        .header-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .theme-toggle-btn {
            background: var(--bg-subtle);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 7px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            outline: none;
            transition: all 0.2s;
        }
        .theme-toggle-btn:hover {
            border-color: var(--brand);
            color: var(--brand);
        }
        .header-badge {
            background: rgba(56, 189, 248, 0.12);
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
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .kpi-card:hover { transform: translateY(-2px); }
        .kpi-label { font-size: 12px; color: var(--text-sub); margin-bottom: 8px; font-weight: 500; }
        .kpi-value { font-size: 28px; font-weight: 700; font-family: "Consolas", monospace; }
        .kpi-unit { font-size: 14px; font-weight: 400; color: var(--text-sub); margin-left: 4px; }
        .kpi-sub-badge {
            font-size: 11px;
            font-weight: 400;
            color: var(--text-sub);
            margin-left: 4px;
            vertical-align: middle;
        }
        .kpi-breakdown {
            margin-top: 8px;
            padding-top: 6px;
            border-top: 1px dashed var(--border);
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .kpi-sub-item {
            font-size: 11px;
            color: var(--text-main);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .kpi-dot {
            display: inline-block;
            width: 7px;
            height: 7px;
            border-radius: 50%;
            margin-right: 5px;
            flex-shrink: 0;
        }
        .kpi-sub-name {
            color: var(--text-sub);
            margin-right: auto;
            max-width: 110px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .kpi-sub-val {
            font-weight: 600;
            color: var(--text-main);
        }
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
            box-shadow: 0 4px 16px rgba(0,0,0,0.05);
        }
        .section-title {
            font-size: 17px;
            font-weight: 600;
            color: var(--text-main);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 12px;
            margin-bottom: 16px;
        }
        .section-title-left {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .top-controls {
            display: flex;
            align-items: center;
            gap: 16px;
            font-size: 13px;
            font-weight: normal;
            color: var(--text-main);
        }
        .top-controls label {
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
        }
        .top-controls select {
            background: var(--bg-subtle);
            color: var(--text-main);
            border: 1px solid var(--border);
            padding: 5px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
            outline: none;
            cursor: pointer;
        }

        /* Map Container & Legend */
        #map-placeholder {
            width: 100%;
            height: 520px;
        }
        #map-wrapper {
            position: relative;
            width: 100%;
            height: 100%;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid var(--border);
            cursor: pointer;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        #map-wrapper:hover {
            border-color: var(--brand);
            box-shadow: 0 0 12px rgba(56, 189, 248, 0.15);
        }
        #map-wrapper:hover .zoom-hint {
            color: var(--brand);
        }
        #map-container {
            width: 100%;
            height: 100%;
            background: var(--bg-subtle);
        }
        .map-legend {
            position: absolute;
            bottom: 24px;
            left: 24px;
            z-index: 1000;
            background: var(--legend-bg);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 12px;
            color: var(--text-main);
            box-shadow: 0 4px 16px rgba(0,0,0,0.15);
            max-width: 360px;
            pointer-events: none;
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
        th { background: var(--bg-subtle); color: var(--brand); padding: 12px 10px; border: 1px solid var(--border); font-weight: 600; }
        td { padding: 10px; border: 1px solid var(--border); font-family: "Consolas", monospace; color: var(--text-main); }
        tr:nth-child(even) { background: var(--bg-subtle); }
        tr:hover { background: var(--table-hover); }

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
            position: relative;
            background: var(--bg-subtle);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
            height: 440px;
            cursor: pointer;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        .chart-box:hover {
            border-color: var(--brand);
            box-shadow: 0 0 12px rgba(56, 189, 248, 0.15);
        }
        .chart-box-tall {
            height: 560px;
        }
        .bullseye-container {
            position: relative;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 440px;
            background: var(--bg-subtle);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
            cursor: pointer;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        .bullseye-container:hover {
            border-color: var(--brand);
            box-shadow: 0 0 12px rgba(56, 189, 248, 0.15);
        }
        #chart-scatter {
            width: 100%;
            height: 100%;
            max-width: 440px;
            max-height: 440px;
        }
        .zoom-hint {
            position: absolute;
            top: 10px;
            right: 14px;
            font-size: 11px;
            color: var(--text-muted);
            pointer-events: none;
            user-select: none;
            transition: color 0.2s;
        }
        .chart-box:hover .zoom-hint, .bullseye-container:hover .zoom-hint {
            color: var(--brand);
        }

        /* 🌟 独立的全屏模态遮罩层 (Isolated Modal Overlay) - 绝不影响原页面 Grid 布局 */
        .chart-modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: 999999;
            background: var(--modal-bg);
            backdrop-filter: blur(12px);
            padding: 20px 30px;
        }
        .modal-dialog {
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 12px;
        }
        .modal-title {
            font-size: 17px;
            font-weight: 600;
            color: var(--text-main);
        }
        .modal-close-btn {
            background: var(--bg-card);
            border: 1px solid var(--brand);
            color: var(--brand);
            padding: 6px 18px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 4px 16px rgba(0,0,0,0.15);
            transition: all 0.2s;
        }
        .modal-close-btn:hover {
            background: var(--brand);
            color: #FFFFFF;
        }
        .modal-chart-body {
            flex: 1;
            width: 100%;
            height: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        #modal-chart-canvas {
            width: 100%;
            height: 100%;
        }

        /* Footer */
        .report-footer {
            text-align: center;
            font-size: 12px;
            color: var(--text-sub);
            padding: 24px 0;
        }

        /* 📱 移动端专属响应式规则 (屏幕宽度 <= 768px 生效，电脑端 100% 完全忽略) */
        @media (max-width: 768px) {
            body { padding: 10px 8px; }
            .container { width: 100%; max-width: 100%; margin: 0; }
            
            .report-header {
                flex-direction: column;
                align-items: flex-start;
                gap: 12px;
                padding: 14px 16px;
            }
            .header-title h1 { font-size: 18px; }
            .header-title p { font-size: 11px; }
            .header-actions {
                width: 100%;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .header-badge { font-size: 11px; padding: 4px 10px; }
            .theme-toggle-btn { font-size: 12px; padding: 6px 12px; }

            /* KPI 仪表盘在手机上优雅排为双列四格 */
            .kpi-grid {
                grid-template-columns: 1fr 1fr;
                gap: 10px;
            }
            .kpi-card { padding: 10px 12px; }
            .kpi-label { font-size: 11px; margin-bottom: 4px; }
            .kpi-value { font-size: 20px; }
            .kpi-unit { font-size: 11px; }

            .section-card {
                padding: 14px 12px;
                margin-bottom: 14px;
                border-radius: 10px;
            }
            .section-title {
                font-size: 14px;
                flex-direction: column;
                align-items: flex-start;
                gap: 8px;
            }
            .top-controls {
                width: 100%;
                flex-wrap: wrap;
                gap: 8px;
                font-size: 12px;
            }

            /* 图表黄金适度高度，避免占满整屏 */
            #map-placeholder { height: 320px; }
            .chart-box { height: 300px; padding: 8px; }
            .chart-box-tall { height: 380px; padding: 8px; }
            .bullseye-container { height: 300px; padding: 8px; }
            #chart-scatter { max-width: 280px; max-height: 280px; }

            /* 触控友好：放大标签常驻为半透明胶囊按钮，支持手指直接点击 */
            .zoom-hint {
                display: inline-block;
                top: 8px;
                right: 8px;
                font-size: 11px;
                padding: 3px 8px;
                border-radius: 12px;
                background: var(--bg-card);
                border: 1px solid var(--border);
                color: var(--brand);
                pointer-events: auto;
                cursor: pointer;
            }

            /* 全屏模态弹窗手机端贴合 */
            .chart-modal-overlay { padding: 10px 8px; }
            .modal-title { font-size: 14px; }
            .modal-close-btn { padding: 8px 14px; font-size: 12px; }

            table { font-size: 11px; }
            th, td { padding: 8px 6px; }
        }
    </style>
</head>
<body>
    <!-- 独立全屏大图弹窗 -->
    <div id="chart-modal-overlay" class="chart-modal-overlay" ondblclick="closeChartModal()">
        <div class="modal-dialog">
            <div class="modal-header">
                <div id="modal-chart-title" class="modal-title">图表全屏分析</div>
                <button class="modal-close-btn" onclick="closeChartModal()">✕ 还原默认视图 (ESC / 双击)</button>
            </div>
            <div class="modal-chart-body">
                <div id="modal-chart-canvas"></div>
            </div>
        </div>
    </div>

    <div class="container">
        <!-- Header -->
        <div class="report-header">
            <div class="header-title">
                <h1>🛰️ GNSS 定位精度测试与综合评定报告</h1>
                <p>测试对象: __REPORT_TITLE__  |  报告生成时间: __GEN_TIME__  |  分段总数: __SEG_COUNT__  |  数据历元总数: __TOTAL_EPOCHS__</p>
            </div>
            <div class="header-actions">
                <button class="theme-toggle-btn" onclick="toggleTheme()">
                    <span id="theme-icon">🌙</span> <span id="theme-text">深色模式</span>
                </button>
                <div class="header-badge">
                    POS_Handling 专业评定
                </div>
            </div>
        </div>

        <!-- KPI Executive Dashboard -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">RTK 固定解比例 (Fix Rate)</div>
                __FIX_RATE_BLOCK__
            </div>
            <div class="kpi-card">
                <div class="kpi-label">水平精度 RMS (1σ)</div>
                __H_RMS_BLOCK__
            </div>
            <div class="kpi-card">
                <div class="kpi-label">水平 95% 置信度误差</div>
                __H_95_BLOCK__
            </div>
            <div class="kpi-card">
                <div class="kpi-label">高程精度 RMS (1σ)</div>
                __V_RMS_BLOCK__
            </div>
            <div class="kpi-card">
                <div class="kpi-label">最大水平偏差 (Max Error)</div>
                __MAX_H_ERR_BLOCK__
            </div>
        </div>

        <!-- Section 1: 空间轨迹 -->
        <div class="section-card">
            <div class="section-title">
                <div class="section-title-left">
                    🗺️ 空间二维运行轨迹与解状态投影 (多文件对比)
                </div>
                <div class="top-controls">
                    <label>
                        <input type="checkbox" id="chk-rtk-color" onchange="updateMapDisplay()"> 按 RTK 状态着色
                    </label>
                    <label>
                        显示样式:
                        <select id="sel-map-mode" onchange="updateMapDisplay()">
                            <option value="line_only" selected>纯线条 (Pure Line)</option>
                            <option value="line_points">点连线 (Line + Points)</option>
                            <option value="points_only">纯散点 (Points Only)</option>
                        </select>
                    </label>
                </div>
            </div>
            <div id="map-placeholder">
                <div id="map-wrapper" ondblclick="zoomMap()" title="双击放大全屏地图">
                    <span class="zoom-hint" onclick="event.stopPropagation(); zoomMap();">⛶ 放大地图</span>
                    <div id="map-container"></div>
                    <div id="map-legend" class="map-legend"></div>
                </div>
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

        <!-- Section 3: 误差曲线大看板 -->
        <div class="section-card">
            <div class="section-title">
                <div class="section-title-left">📈 误差时序历元分布与联合分析 (💡 双击任意图表放大全屏 / 再次双击还原)</div>
                <div class="top-controls">
                    <label>
                        <b>X 轴对齐基准:</b>
                        <select id="sel-xaxis-mode" onchange="switchXAxisMode(this.value)">
                            <option value="epoch" __SELECT_EPOCH__>🔢 相对历元对齐 (从第1点拉齐对比)</option>
                            <option value="time" __SELECT_TIME__>⏱️ 绝对时间对齐 (按真实UTC/TOW时刻)</option>
                        </select>
                    </label>
                </div>
            </div>

            <!-- 第一行：水平误差与垂直误差 -->
            <div class="charts-row-2col">
                <div class="chart-box" id="box-epoch-h" ondblclick="zoomChart('echH', '水平位置误差历元分布图 (2D Error)')">
                    <span class="zoom-hint" onclick="event.stopPropagation(); this.parentElement.ondblclick && this.parentElement.ondblclick();">⛶ 放大</span>
                    <div id="chart-epoch-h" style="width:100%; height:100%;"></div>
                </div>
                <div class="chart-box" id="box-epoch-v" ondblclick="zoomChart('echV', '高程位置误差历元分布图 (Vertical Error)')">
                    <span class="zoom-hint" onclick="event.stopPropagation(); this.parentElement.ondblclick && this.parentElement.ondblclick();">⛶ 放大</span>
                    <div id="chart-epoch-v" style="width:100%; height:100%;"></div>
                </div>
            </div>

            <!-- 第二行：三向 ENU 误差 -->
            <div class="charts-row-full">
                <div class="chart-box chart-box-tall" id="box-epoch-enu" ondblclick="zoomChart('echENU', 'ENU 三向位置误差历元曲线 (E / N / U 分层独立展示)')">
                    <span class="zoom-hint" onclick="event.stopPropagation(); this.parentElement.ondblclick && this.parentElement.ondblclick();">⛶ 放大</span>
                    <div id="chart-epoch-enu" style="width:100%; height:100%;"></div>
                </div>
            </div>

            <!-- 第三行：自适应正圆靶心图 与 CDF 累积分布图 -->
            <div class="charts-row-2col">
                <div class="bullseye-container" id="box-scatter" ondblclick="zoomChart('echScatter', '定位偏差散点分布 (靶心图 · 1:1正圆)')">
                    <span class="zoom-hint" onclick="event.stopPropagation(); this.parentElement.ondblclick && this.parentElement.ondblclick();">⛶ 放大</span>
                    <div id="chart-scatter"></div>
                </div>
                <div class="chart-box" id="box-cdf" ondblclick="zoomChart('echCDF', '误差累积概率分布曲线 (CDF)')">
                    <span class="zoom-hint" onclick="event.stopPropagation(); this.parentElement.ondblclick && this.parentElement.ondblclick();">⛶ 放大</span>
                    <div id="chart-cdf" style="width:100%; height:100%;"></div>
                </div>
            </div>

            <!-- 第四行：运行速度曲线 -->
            <div class="charts-row-full">
                <div class="chart-box" id="box-speed" ondblclick="zoomChart('echSpeed', '对地运行速度时序曲线')">
                    <span class="zoom-hint" onclick="event.stopPropagation(); this.parentElement.ondblclick && this.parentElement.ondblclick();">⛶ 放大</span>
                    <div id="chart-speed" style="width:100%; height:100%;"></div>
                </div>
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
        var globalEpochline = __GLOBAL_EPOCHLINE_JSON__;
        var maxLimit = __SCATTER_LIMIT__ || 1.0;
        var currentXAxisMode = '__DEFAULT_XAXIS_MODE__';
        var currentTheme = 'light';
        var isAbsAlt = __IS_ABS_ALT__;

        // 1. 初始化 Leaflet 轨迹地图
        var map = L.map('map-container', { zoomControl: true, attributionControl: false, doubleClickZoom: false }).setView([39.9, 116.4], 13);
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

            for (var s = 0; s < segmentsData.length; s++) {
                var seg = segmentsData[s];
                var pts = seg.points;
                if (!pts || pts.length === 0) continue;

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
                        var allLatLngs = pts.map(function(p) { return [p.lat, p.lon]; });
                        L.polyline(allLatLngs, { color: seg.color, weight: 3.5, opacity: 0.9 }).addTo(mapLayersGroup);
                    }
                }

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

        // 2. 初始化 ECharts 动态图表
        var legendNames = segmentsData.map(function(s) { return s.name; });

        var echH = echarts.init(document.getElementById('chart-epoch-h'));
        var echV = echarts.init(document.getElementById('chart-epoch-v'));
        var echENU = echarts.init(document.getElementById('chart-epoch-enu'));
        var echScatter = echarts.init(document.getElementById('chart-scatter'));
        var echCDF = echarts.init(document.getElementById('chart-cdf'));
        var echSpeed = echarts.init(document.getElementById('chart-speed'));

        var chartsMap = {
            'echH': echH, 'echV': echV, 'echENU': echENU,
            'echScatter': echScatter, 'echCDF': echCDF, 'echSpeed': echSpeed
        };

        function getThemeColors() {
            var isDark = (currentTheme === 'dark');
            return {
                title: isDark ? '#F8FAFC' : '#0F172A',
                axis: isDark ? '#64748B' : '#475569',
                axisText: isDark ? '#CBD5E1' : '#334155',
                split: isDark ? '#334155' : '#CBD5E1',
                legend: isDark ? '#CBD5E1' : '#334155',
                circleGrid: isDark ? '#475569' : '#94A3B8'
            };
        }

        function renderAllCharts(mode) {
            var isTime = (mode === 'time');
            var currentXData = isTime ? globalTimeline : globalEpochline;
            var xAxisName = isTime ? '时刻' : '历元号';
            var tc = getThemeColors();

            // A. 水平误差图
            var seriesH = segmentsData.map(function(s) {
                return {
                    name: s.name, type: 'line', connectNulls: true, data: isTime ? s.h_time_series : s.h_epoch_series,
                    lineStyle: { color: s.color, width: 1.8 },
                    itemStyle: { color: s.color },
                    showSymbol: false
                };
            });
            echH.setOption({
                backgroundColor: 'transparent',
                title: { text: '水平位置误差历元分布图 (2D Error · ' + (isTime ? '时间对齐' : '历元对齐') + ')', left: 'center', top: 8, textStyle: { fontSize: 15, color: tc.title } },
                tooltip: { trigger: 'axis' },
                legend: { top: 32, data: legendNames, textStyle: { color: tc.legend } },
                dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 4 }],
                grid: { left: (window.innerWidth <= 768 ? 42 : 60), right: (window.innerWidth <= 768 ? 16 : 30), top: 65, bottom: 42 },
                xAxis: { type: 'category', data: currentXData, name: xAxisName, axisTick: { show: true }, axisLine: { show: true, lineStyle: { color: tc.axis } }, axisLabel: { color: tc.axisText, fontWeight: 500 } },
                yAxis: { type: 'value', name: '偏差 (m)', nameLocation: 'end', nameGap: 10, axisTick: { show: true, lineStyle: { color: tc.axis } }, axisLine: { show: true, lineStyle: { color: tc.axis } }, splitLine: { lineStyle: { color: tc.split, width: 1 } }, axisLabel: { color: tc.axisText, fontWeight: 500 } },
                series: seriesH
            }, true);

            // B. 高程误差图
            var seriesV = segmentsData.map(function(s) {
                return {
                    name: s.name, type: 'line', connectNulls: true, data: isTime ? s.v_time_series : s.v_epoch_series,
                    lineStyle: { color: s.color, width: 1.8 },
                    itemStyle: { color: s.color },
                    showSymbol: false
                };
            });
            var vTitle = (isAbsAlt ? '高程位置误差绝对值历元分布图 (|Vertical Error| · ' : '高程位置误差历元分布图 (Vertical Error · ') + (isTime ? '时间对齐' : '历元对齐') + ')';
            echV.setOption({
                backgroundColor: 'transparent',
                title: { text: vTitle, left: 'center', top: 8, textStyle: { fontSize: 15, color: tc.title } },
                tooltip: { trigger: 'axis' },
                legend: { top: 32, data: legendNames, textStyle: { color: tc.legend } },
                dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 4 }],
                grid: { left: (window.innerWidth <= 768 ? 42 : 60), right: (window.innerWidth <= 768 ? 16 : 30), top: 65, bottom: 42 },
                xAxis: { type: 'category', data: currentXData, name: xAxisName, axisTick: { show: true }, axisLine: { show: true, lineStyle: { color: tc.axis } }, axisLabel: { color: tc.axisText, fontWeight: 500 } },
                yAxis: { type: 'value', name: isAbsAlt ? '高程绝对偏差 (m)' : '高程偏差 (m)', nameLocation: 'end', nameGap: 10, axisTick: { show: true, lineStyle: { color: tc.axis } }, axisLine: { show: true, lineStyle: { color: tc.axis } }, splitLine: { lineStyle: { color: tc.split, width: 1 } }, axisLabel: { color: tc.axisText, fontWeight: 500 } },
                series: seriesV
            }, true);

            // C. ENU 三向误差图 (全实线)
            var seriesENU = [];
            for (var s = 0; s < segmentsData.length; s++) {
                var seg = segmentsData[s];
                seriesENU.push({
                    name: seg.name + ' - dE', type: 'line', connectNulls: true, xAxisIndex: 0, yAxisIndex: 0,
                    data: isTime ? seg.de_time_series : seg.de_epoch_series,
                    lineStyle: { color: seg.color, width: 1.6 }, itemStyle: { color: seg.color }, showSymbol: false
                });
                seriesENU.push({
                    name: seg.name + ' - dN', type: 'line', connectNulls: true, xAxisIndex: 1, yAxisIndex: 1,
                    data: isTime ? seg.dn_time_series : seg.dn_epoch_series,
                    lineStyle: { color: seg.color, width: 1.6 }, itemStyle: { color: seg.color }, showSymbol: false
                });
                seriesENU.push({
                    name: seg.name + ' - dU', type: 'line', connectNulls: true, xAxisIndex: 2, yAxisIndex: 2,
                    data: isTime ? seg.du_time_series : seg.du_epoch_series,
                    lineStyle: { color: seg.color, width: 1.6 }, itemStyle: { color: seg.color }, showSymbol: false
                });
            }
            echENU.setOption({
                backgroundColor: 'transparent',
                title: { text: 'ENU 三向位置误差历元曲线 (E / N / U 分层独立展示 · ' + (isTime ? '时间对齐' : '历元对齐') + ')', left: 'center', top: 8, textStyle: { fontSize: 15, color: tc.title } },
                tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
                axisPointer: { link: [{ xAxisIndex: 'all' }] },
                legend: { top: 32, data: legendNames, textStyle: { color: tc.legend } },
                dataZoom: [
                    { type: 'inside', xAxisIndex: [0, 1, 2] },
                    { type: 'slider', xAxisIndex: [0, 1, 2], height: 16, bottom: 4 }
                ],
                grid: [
                    { left: (window.innerWidth <= 768 ? 44 : 65), right: (window.innerWidth <= 768 ? 16 : 30), top: 65, height: '23%' },
                    { left: (window.innerWidth <= 768 ? 44 : 65), right: (window.innerWidth <= 768 ? 16 : 30), top: '42%', height: '23%' },
                    { left: (window.innerWidth <= 768 ? 44 : 65), right: (window.innerWidth <= 768 ? 16 : 30), top: '70%', height: '23%' }
                ],
                xAxis: [
                    { gridIndex: 0, type: 'category', data: currentXData, axisLabel: { show: false }, axisTick: { show: false } },
                    { gridIndex: 1, type: 'category', data: currentXData, axisLabel: { show: false }, axisTick: { show: false } },
                    { gridIndex: 2, type: 'category', data: currentXData, name: xAxisName, axisTick: { show: true }, axisLine: { show: true, lineStyle: { color: tc.axis } }, axisLabel: { color: tc.axisText, fontWeight: 500 } }
                ],
                yAxis: [
                    { gridIndex: 0, type: 'value', name: '东向 dE (m)', nameLocation: 'middle', nameGap: 45, splitLine: { lineStyle: { color: tc.split } }, axisLabel: { color: tc.axisText } },
                    { gridIndex: 1, type: 'value', name: '北向 dN (m)', nameLocation: 'middle', nameGap: 45, splitLine: { lineStyle: { color: tc.split } }, axisLabel: { color: tc.axisText } },
                    { gridIndex: 2, type: 'value', name: '天向 dU (m)', nameLocation: 'middle', nameGap: 45, splitLine: { lineStyle: { color: tc.split } }, axisLabel: { color: tc.axisText } }
                ],
                series: seriesENU
            }, true);

            // F. 运行速度图
            var seriesSpeed = segmentsData.map(function(s) {
                return {
                    name: s.name, type: 'line', connectNulls: true, data: isTime ? s.speed_time_series : s.speed_epoch_series,
                    lineStyle: { color: s.color, width: 1.8 },
                    itemStyle: { color: s.color },
                    showSymbol: false
                };
            });
            echSpeed.setOption({
                backgroundColor: 'transparent',
                title: { text: '对地运行速度时序曲线 (' + (isTime ? '时间对齐' : '历元对齐') + ')', left: 'center', top: 8, textStyle: { fontSize: 15, color: tc.title } },
                tooltip: { trigger: 'axis' },
                legend: { top: 32, data: legendNames, textStyle: { color: tc.legend } },
                dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 4 }],
                grid: { left: (window.innerWidth <= 768 ? 42 : 60), right: (window.innerWidth <= 768 ? 16 : 30), top: 65, bottom: 42 },
                xAxis: { type: 'category', data: currentXData, name: xAxisName, axisTick: { show: true }, axisLine: { show: true, lineStyle: { color: tc.axis } }, axisLabel: { color: tc.axisText, fontWeight: 500 } },
                yAxis: { type: 'value', name: '速度 (m/s)', nameLocation: 'end', nameGap: 10, axisTick: { show: true, lineStyle: { color: tc.axis } }, axisLine: { show: true, lineStyle: { color: tc.axis } }, splitLine: { lineStyle: { color: tc.split, width: 1 } }, axisLabel: { color: tc.axisText, fontWeight: 500 } },
                series: seriesSpeed
            }, true);
        }

        // 靶心图与 CDF 初始化 (100% 严谨对齐软件端优雅对数整步长与 45 度轻量排印)
        function renderScatterAndCDF() {
            var tc = getThemeColors();

            var scatterSeries = [];
            var ringScaleItems = [];

            // 1. 移植软件端核心算法：以 10 为底的指数对数步长算法，实现等间距圆圈网格线完美自适应
            var rawStep = maxLimit / 5.0;
            if (rawStep <= 0) rawStep = 0.01;
            var exponent = Math.floor(Math.log10(rawStep));
            var fraction = rawStep / Math.pow(10, exponent);
            var niceStep = 1.0;
            if (fraction < 1.5) niceStep = 1.0;
            else if (fraction < 3.0) niceStep = 2.0;
            else if (fraction < 7.0) niceStep = 5.0;
            else niceStep = 10.0;
            var step = niceStep * Math.pow(10, exponent);

            // 2. 绘制规整同心圆环，并在右下角 45 度对角线优雅附着标尺数字 (与软件端完全一致)
            for (var r = step; r < maxLimit; r += step) {
                var circlePts = [];
                for (var a = 0; a <= 360; a += 3) {
                    var rad = a * Math.PI / 180;
                    circlePts.push([round(r * Math.cos(rad), 4), round(r * Math.sin(rad), 4)]);
                }
                scatterSeries.push({
                    name: '标尺网格',
                    type: 'line',
                    data: circlePts,
                    lineStyle: { type: 'dashed', color: tc.circleGrid, width: 0.8 },
                    showSymbol: false,
                    silent: true,
                    tooltip: { show: false }
                });

                // 标尺文字格式化：整数不带多余小数，小数最多保留 2 位
                var scaleLabel = (step >= 1 ? round(r, 1).toString() : round(r, 3).toString()) + 'm';
                ringScaleItems.push({
                    name: scaleLabel,
                    value: [round(r * 0.7071, 4), round(-r * 0.7071, 4)]
                });
            }

            // 3. 圆格标尺文字系列 (纯文本模板 '{b}'，全屏克隆绝对不丢失、无厚重白底框)
            if (ringScaleItems.length > 0) {
                scatterSeries.push({
                    name: '圆格标尺',
                    type: 'scatter',
                    data: ringScaleItems,
                    symbolSize: 0.01,
                    label: {
                        show: true,
                        formatter: '{b}',
                        position: 'inside',
                        color: tc.axisText,
                        fontSize: 10,
                        fontWeight: 500
                    },
                    silent: true,
                    tooltip: { show: false }
                });
            }

            // 4. 四向指南针方位指示 N, S, E, W (极简排印，与软件端 100% 一致，绝不遮挡图例)
            var compassDistance = maxLimit * 0.95;
            var compassItems = [
                { name: 'N', value: [0, compassDistance] },
                { name: 'S', value: [0, -compassDistance] },
                { name: 'E', value: [compassDistance, 0] },
                { name: 'W', value: [-compassDistance, 0] }
            ];
            scatterSeries.push({
                name: '指南针',
                type: 'scatter',
                data: compassItems,
                symbolSize: 0.01,
                label: {
                    show: true,
                    formatter: '{b}',
                    position: 'inside',
                    color: tc.title,
                    fontSize: 11,
                    fontWeight: 'bold'
                },
                silent: true,
                tooltip: { show: false }
            });

            // 数据散点系列
            for (var s = 0; s < segmentsData.length; s++) {
                var seg = segmentsData[s];
                scatterSeries.push({
                    name: seg.name,
                    type: 'scatter',
                    symbolSize: 5,
                    data: seg.scatter_pts,
                    itemStyle: { color: seg.color, opacity: 0.85 }
                });
            }

            echScatter.setOption({
                backgroundColor: 'transparent',
                title: { text: '定位偏差散点分布 (靶心图 · 1:1正圆)', left: 'center', top: 4, textStyle: { fontSize: 14, color: tc.title } },
                tooltip: {
                    formatter: function(p) {
                        if (!p.data || p.seriesName === '标尺网格' || p.seriesName === '圆形标尺刻度' || p.seriesName === '罗盘方位') return '';
                        return '<b>' + p.seriesName + '</b><br/>dE: ' + p.data[0] + 'm<br/>dN: ' + p.data[1] + 'm';
                    }
                },
                legend: { top: 26, data: legendNames, textStyle: { color: tc.legend, fontSize: 11 } },
                grid: { left: 25, right: 25, top: 45, bottom: 25 },
                xAxis: {
                    type: 'value', min: -maxLimit, max: maxLimit,
                    axisLine: { onZero: true, lineStyle: { color: tc.axis, width: 1.5 } },
                    axisTick: { show: false },
                    axisLabel: { show: false },   // 隐藏杂乱的直角坐标系标签，直接由圆形标尺刻度指示
                    splitLine: { show: false }
                },
                yAxis: {
                    type: 'value', min: -maxLimit, max: maxLimit,
                    axisLine: { onZero: true, lineStyle: { color: tc.axis, width: 1.5 } },
                    axisTick: { show: false },
                    axisLabel: { show: false },   // 隐藏杂乱的直角坐标系标签，直接由圆形标尺刻度指示
                    splitLine: { show: false }
                },
                series: scatterSeries
            }, true);

            // CDF 图
            var seriesCDF = segmentsData.map(function(s) {
                return {
                    name: s.name, type: 'line', data: s.cdf_pts,
                    lineStyle: { color: s.color, width: 2 },
                    itemStyle: { color: s.color },
                    showSymbol: false
                };
            });
            echCDF.setOption({
                backgroundColor: 'transparent',
                title: { text: '误差累积概率分布曲线 (CDF)', left: 'center', top: 8, textStyle: { fontSize: 15, color: tc.title } },
                tooltip: {
                    trigger: 'axis', formatter: function(params) {
                        var res = '误差: ' + params[0].value[0] + 'm<br/>';
                        for (var i = 0; i < params.length; i++) {
                            res += params[i].marker + params[i].seriesName + ': ' + params[i].value[1] + '%<br/>';
                        }
                        return res;
                    }
                },
                legend: { top: 32, data: legendNames, textStyle: { color: tc.legend } },
                grid: { left: (window.innerWidth <= 768 ? 42 : 60), right: (window.innerWidth <= 768 ? 16 : 30), top: 65, bottom: 42 },
                xAxis: { type: 'value', name: '水平误差 (m)', splitLine: { lineStyle: { color: tc.split } }, axisLabel: { color: tc.axisText } },
                yAxis: { type: 'value', name: '累积概率 (%)', max: 100, splitLine: { lineStyle: { color: tc.split } }, axisLabel: { color: tc.axisText } },
                series: seriesCDF
            }, true);
        }

        function round(val, d) {
            var m = Math.pow(10, d);
            return Math.round(val * m) / m;
        }

        function switchXAxisMode(mode) {
            currentXAxisMode = mode;
            renderAllCharts(mode);
        }

        function toggleTheme() {
            var htmlRoot = document.documentElement;
            if (currentTheme === 'dark') {
                currentTheme = 'light';
                htmlRoot.setAttribute('data-theme', 'light');
                document.getElementById('theme-icon').innerText = '🌙';
                document.getElementById('theme-text').innerText = '深色模式';
            } else {
                currentTheme = 'dark';
                htmlRoot.setAttribute('data-theme', 'dark');
                document.getElementById('theme-icon').innerText = '☀️';
                document.getElementById('theme-text').innerText = '浅色模式';
            }
            renderAllCharts(currentXAxisMode);
            renderScatterAndCDF();
            updateMapDisplay();
        }

        // =========================================================================
        // 🌟 核心升级：专用全屏模态弹窗系统 (完全隔离，彻底杜绝 Grid 塌陷和兄弟图挤压)
        // =========================================================================
        var modalOverlay = document.getElementById('chart-modal-overlay');
        var modalCanvas = document.getElementById('modal-chart-canvas');
        var modalTitle = document.getElementById('modal-chart-title');
        var modalChartInstance = null;
        var isMapInModal = false;

        function zoomMap() {
            isMapInModal = true;
            modalTitle.innerText = '🗺️ 空间二维运行轨迹与解状态投影 [全屏大地图]';
            modalCanvas.style.width = '100%';
            modalCanvas.style.height = '100%';
            modalCanvas.style.display = 'none';

            var mapWrapper = document.getElementById('map-wrapper');
            document.querySelector('.modal-chart-body').appendChild(mapWrapper);
            modalOverlay.style.display = 'block';

            setTimeout(function() {
                map.invalidateSize();
            }, 60);
        }

        function zoomChart(chartKey, titleText) {
            isMapInModal = false;
            modalCanvas.style.display = 'block';
            var sourceChart = chartsMap[chartKey];
            if (!sourceChart) return;

            modalTitle.innerText = titleText + ' [全屏沉浸大图]';
            modalOverlay.style.display = 'block';

            // 针对靶心图锁定 1:1 正方比例，避免宽屏下拉伸变形
            if (chartKey === 'echScatter') {
                modalCanvas.style.width = 'min(82vh, 82vw)';
                modalCanvas.style.height = 'min(82vh, 82vw)';
            } else {
                modalCanvas.style.width = '100%';
                modalCanvas.style.height = '100%';
            }

            if (!modalChartInstance) {
                modalChartInstance = echarts.init(modalCanvas);
            }

            // 克隆原图表的完整配置，并为全屏状态加粗线条与散点
            var opt = JSON.parse(JSON.stringify(sourceChart.getOption()));

            if (opt.series) {
                for (var i = 0; i < opt.series.length; i++) {
                    var s = opt.series[i];
                    if (s.type === 'line' && s.lineStyle && s.name !== '标尺网格') {
                        s.lineStyle.width = (s.lineStyle.width || 1.8) + 1.2; // 全屏线条加粗至 3.0px
                    } else if (s.type === 'scatter') {
                        s.symbolSize = 7.5; // 散点加粗至 7.5px
                    }
                }
            }

            modalChartInstance.setOption(opt, true);
            setTimeout(function() {
                modalChartInstance.resize();
            }, 30);
        }

        function closeChartModal() {
            if (isMapInModal) {
                var mapWrapper = document.getElementById('map-wrapper');
                document.getElementById('map-placeholder').appendChild(mapWrapper);
                isMapInModal = false;
                setTimeout(function() {
                    map.invalidateSize();
                }, 60);
            }
            modalOverlay.style.display = 'none';
            if (modalChartInstance) {
                modalChartInstance.clear();
            }
            for (var k in chartsMap) {
                chartsMap[k].resize();
            }
        }

        window.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' || e.keyCode === 27) {
                closeChartModal();
            }
        });

        // 初始渲染
        renderAllCharts(currentXAxisMode);
        renderScatterAndCDF();

        window.addEventListener('resize', function() {
            for (var k in chartsMap) {
                chartsMap[k].resize();
            }
            if (modalChartInstance && modalOverlay.style.display === 'block') {
                modalChartInstance.resize();
            }
            if (map) map.invalidateSize();
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

        # 1. 继承软件当前界面的设置
        color_by_status_checked = False
        if hasattr(parent_window, 'gis_map_widget') and hasattr(parent_window.gis_map_widget, 'cb_color_by_status'):
            color_by_status_checked = parent_window.gis_map_widget.cb_color_by_status.isChecked()
        checked_rtk_attr = "checked" if color_by_status_checked else ""

        desktop_xaxis_mode = getattr(parent_window, 'x_axis_mode', '历元数')
        default_xaxis_mode = "time" if desktop_xaxis_mode == "时间轴" else "epoch"
        select_epoch_attr = "selected" if default_xaxis_mode == "epoch" else ""
        select_time_attr = "selected" if default_xaxis_mode == "time" else ""

        show_absolute_alt = getattr(parent_window, 'show_absolute_alt', False)
        if hasattr(parent_window, 'cb_abs_alt') and hasattr(parent_window.cb_abs_alt, 'isChecked'):
            show_absolute_alt = parent_window.cb_abs_alt.isChecked()

        # 2. 统计指标提取与各分段明细对照
        total_epochs = sum(len(s.get('epochs', [])) for s in active_segs)
        seg_kpi_list = []
        for s_idx, s in enumerate(active_segs):
            s_name = s.get('name', f"分段_{s_idx+1}")
            s_color = s.get('color', '#38BDF8')
            m = s.get('metrics', {})
            fr = m.get('rtk_fix_rate', m.get('fix_rate', 100.0))
            hr = m.get('rms_h', m.get('h_rms', 0.0))
            c95 = m.get('cep95', m.get('h_95', 0.0))
            vr = m.get('rms_v', m.get('v_rms', 0.0))
            mh = m.get('max_h', m.get('h_max', 0.0))
            seg_kpi_list.append({
                'name': s_name,
                'color': s_color,
                'fix_rate': float(fr) if fr is not None else 100.0,
                'h_rms': float(hr) if hr is not None else 0.0,
                'h_95': float(c95) if c95 is not None else 0.0,
                'v_rms': float(vr) if vr is not None else 0.0,
                'max_h': float(mh) if mh is not None else 0.0,
            })

        if table_metrics and table_metrics.rowCount() > 0:
            col_map = {}
            for col_i in range(table_metrics.columnCount()):
                hdr = table_metrics.horizontalHeaderItem(col_i)
                if hdr:
                    col_map[hdr.text().strip()] = col_i

            for row_i in range(table_metrics.rowCount()):
                name_item = table_metrics.item(row_i, 0)
                r_name = name_item.text().strip() if name_item else ""
                matched_kpi = None
                for it in seg_kpi_list:
                    if it['name'] == r_name:
                        matched_kpi = it
                        break
                if not matched_kpi and row_i < len(seg_kpi_list):
                    matched_kpi = seg_kpi_list[row_i]
                
                if matched_kpi:
                    for k in ["固定率", "固定解比例", "RTK固定率", "Fix Rate"]:
                        if k in col_map:
                            it = table_metrics.item(row_i, col_map[k])
                            if it and it.text().strip():
                                try: matched_kpi['fix_rate'] = float(it.text().rstrip('%').strip())
                                except Exception: pass
                    for k in ["水平RMS(m)", "水平 RMS (m)", "H_RMS"]:
                        if k in col_map:
                            it = table_metrics.item(row_i, col_map[k])
                            if it and it.text().strip():
                                try: matched_kpi['h_rms'] = float(it.text().rstrip('m').strip())
                                except Exception: pass
                    for k in ["水平95%(m)", "水平 95% (m)", "95%"]:
                        if k in col_map:
                            it = table_metrics.item(row_i, col_map[k])
                            if it and it.text().strip():
                                try: matched_kpi['h_95'] = float(it.text().rstrip('m').strip())
                                except Exception: pass
                    for k in ["高程RMS(m)", "高程 RMS (m)", "V_RMS"]:
                        if k in col_map:
                            it = table_metrics.item(row_i, col_map[k])
                            if it and it.text().strip():
                                try: matched_kpi['v_rms'] = float(it.text().rstrip('m').strip())
                                except Exception: pass
                    for k in ["最大水平偏差(m)", "最大偏差", "Max H"]:
                        if k in col_map:
                            it = table_metrics.item(row_i, col_map[k])
                            if it and it.text().strip():
                                try: matched_kpi['max_h'] = float(it.text().rstrip('m').strip())
                                except Exception: pass

        # 渲染顶部 KPI 卡片：单分段直接显示数值；多分段时显示均值及各分段专属彩色对比胶囊
        is_multi_seg = len(seg_kpi_list) > 1

        def build_kpi_block(key, unit, val_color_cls, is_max=False, fmt=".3f"):
            if not seg_kpi_list:
                return f'<div class="kpi-value {val_color_cls}">0.000<span class="kpi-unit">{unit}</span></div>'
            vals = [item[key] for item in seg_kpi_list]
            main_v = max(vals) if is_max else (sum(vals) / len(vals))
            main_str = f"{main_v:.2f}" if unit == "%" else f"{main_v:{fmt}}"
            
            sub_tag = ('<span class="kpi-sub-badge">(最大值)</span>' if is_max else '<span class="kpi-sub-badge">(均值)</span>') if is_multi_seg else ''
            html = f'<div class="kpi-value {val_color_cls}">{main_str}<span class="kpi-unit">{unit}</span>{sub_tag}</div>'
            if is_multi_seg:
                html += '<div class="kpi-breakdown">'
                for it in seg_kpi_list:
                    sub_v_str = f"{it[key]:.2f}{unit}" if unit == "%" else f"{it[key]:{fmt}}{unit}"
                    html += f'<div class="kpi-sub-item"><span class="kpi-dot" style="background:{it["color"]};"></span><span class="kpi-sub-name" title="{it["name"]}">{it["name"]}</span><span class="kpi-sub-val">{sub_v_str}</span></div>'
                html += '</div>'
            return html

        fix_rate_block = build_kpi_block('fix_rate', '%', 'color-success')
        h_rms_block = build_kpi_block('h_rms', 'm', 'color-brand')
        h_95_block = build_kpi_block('h_95', 'm', 'color-brand')
        v_rms_block = build_kpi_block('v_rms', 'm', 'color-warning')
        max_h_block = build_kpi_block('max_h', 'm', 'color-warning', is_max=True)

        progress.setValue(30)
        QApplication.processEvents()

        # 3. 生成表格 HTML
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

        # 4. 构造多分段数据：毫秒级时间戳归一化与高精度插值采样 (彻底解决 1Hz/10Hz 混排断线)
        import numpy as np

        def norm_time_str(raw_time_str):
            if not raw_time_str: return ""
            t = raw_time_str.strip()
            if ':' in t:
                pts = t.split(':')
                try:
                    h = int(pts[0])
                    m = int(pts[1])
                    s = float(pts[2]) if len(pts) > 2 else 0.0
                    return f"{h:02d}:{m:02d}:{s:06.3f}"
                except Exception:
                    return t
            return t

        # 收集所有有效时间戳并归一化
        all_timestamps_dict = {}
        for s in active_segs:
            for ep in s.get('epochs', []):
                t_raw = ep.get('time_str')
                if t_raw:
                    t_norm = norm_time_str(t_raw)
                    t_sec = ep.get('utc_time_sec', 0.0)
                    if t_norm not in all_timestamps_dict:
                        all_timestamps_dict[t_norm] = t_sec

        if not all_timestamps_dict:
            max_len = max(len(s.get('epochs', [])) for s in active_segs) if active_segs else 0
            raw_timeline = [str(i+1) for i in range(max_len)]
            raw_timeline_secs = [float(i+1) for i in range(max_len)]
        else:
            raw_timeline = sorted(all_timestamps_dict.keys(), key=lambda k: all_timestamps_dict[k])
            raw_timeline_secs = [all_timestamps_dict[k] for k in raw_timeline]

        time_step = max(1, len(raw_timeline) // 4000)
        filtered_timeline = raw_timeline[::time_step]
        filtered_timeline_secs = np.array(raw_timeline_secs[::time_step], dtype=float)

        max_epoch_len = max(len(s.get('epochs', [])) for s in active_segs) if active_segs else 0
        epoch_step = max(1, max_epoch_len // 4000)
        filtered_epochline = [str(i) for i in range(1, max_epoch_len + 1, epoch_step)]

        segments_payload = []
        global_max_scatter = 0.01

        for s_idx, s in enumerate(active_segs):
            s_name = s.get('name', f"分段_{s_idx+1}")
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

            seg_times = []
            h_raw_list, v_raw_list, de_raw_list, dn_raw_list, du_raw_list, sp_raw_list = [], [], [], [], [], []

            scatter_pts = []
            s_map_points = []
            seg_all_h = []

            for i, ep in enumerate(epochs):
                t_str = ep.get('time_str', str(i+1))
                t_sec = ep.get('utc_time_sec', 0.0)
                seg_times.append(t_sec)

                h_val = h_err_list[i] if i < len(h_err_list) else None
                v_val = v_err_list[i] if i < len(v_err_list) else None
                if v_val is not None and show_absolute_alt:
                    v_val = abs(v_val)

                de = de_list[i] if i < len(de_list) else None
                dn = dn_list[i] if i < len(dn_list) else None
                du = du_list[i] if i < len(du_list) else None
                sp = speed_test_list[i] if i < len(speed_test_list) else ep.get('speed', 0.0)

                h_val_r = round(h_val, 4) if h_val is not None else None
                v_val_r = round(v_val, 4) if v_val is not None else None
                de_r = round(de, 4) if de is not None else None
                dn_r = round(dn, 4) if dn is not None else None
                du_r = round(du, 4) if du is not None else None
                sp_r = round(float(sp), 2) if sp is not None else 0.0

                if h_val is not None:
                    seg_all_h.append(h_val)

                if de is not None and dn is not None:
                    dist = (de**2 + dn**2)**0.5
                    global_max_scatter = max(global_max_scatter, dist)
                    if len(scatter_pts) < 1500 and (i % max(1, len(epochs)//1500) == 0):
                        scatter_pts.append([round(de, 4), round(dn, 4)])

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

                h_raw_list.append(h_val_r)
                v_raw_list.append(v_val_r)
                de_raw_list.append(de_r)
                dn_raw_list.append(dn_r)
                du_raw_list.append(du_r)
                sp_raw_list.append(sp_r)

            # 高精度插值采样：将该分段平滑投影到全局时间线上
            def interp_to_timeline(raw_vals):
                valid_mask = [v is not None for v in raw_vals]
                if not any(valid_mask) or len(seg_times) < 1 or len(filtered_timeline_secs) < 1:
                    return [None] * len(filtered_timeline)
                
                v_times = np.array([seg_times[j] for j in range(len(raw_vals)) if valid_mask[j]], dtype=float)
                v_arr = np.array([raw_vals[j] for j in range(len(raw_vals)) if valid_mask[j]], dtype=float)
                if len(v_times) == 0:
                    return [None] * len(filtered_timeline)

                sort_idx = np.argsort(v_times)
                v_times = v_times[sort_idx]
                v_arr = v_arr[sort_idx]

                # 剔除重复时间
                diffs = np.diff(v_times)
                umask = np.insert(diffs > 0, 0, True)
                v_times = v_times[umask]
                v_arr = v_arr[umask]

                if len(v_times) == 1:
                    res = []
                    t0 = v_times[0]
                    val0 = round(float(v_arr[0]), 4)
                    for gt in filtered_timeline_secs:
                        res.append(val0 if abs(gt - t0) <= 1.0 else None)
                    return res

                interp_res = np.interp(filtered_timeline_secs, v_times, v_arr, left=np.nan, right=np.nan)
                out = []
                t_min, t_max = v_times[0], v_times[-1]
                for k_i, val in enumerate(interp_res):
                    gt = filtered_timeline_secs[k_i]
                    if np.isnan(val) or gt < (t_min - 0.5) or gt > (t_max + 0.5):
                        out.append(None)
                    else:
                        out.append(round(float(val), 4))
                return out

            h_time_series = interp_to_timeline(h_raw_list)
            v_time_series = interp_to_timeline(v_raw_list)
            de_time_series = interp_to_timeline(de_raw_list)
            dn_time_series = interp_to_timeline(dn_raw_list)
            du_time_series = interp_to_timeline(du_raw_list)
            speed_time_series = interp_to_timeline(sp_raw_list)

            h_epoch_series = [h_raw_list[idx-1] if (idx-1) < len(h_raw_list) else None for idx in [int(ep) for ep in filtered_epochline]]
            v_epoch_series = [v_raw_list[idx-1] if (idx-1) < len(v_raw_list) else None for idx in [int(ep) for ep in filtered_epochline]]
            de_epoch_series = [de_raw_list[idx-1] if (idx-1) < len(de_raw_list) else None for idx in [int(ep) for ep in filtered_epochline]]
            dn_epoch_series = [dn_raw_list[idx-1] if (idx-1) < len(dn_raw_list) else None for idx in [int(ep) for ep in filtered_epochline]]
            du_epoch_series = [du_raw_list[idx-1] if (idx-1) < len(du_raw_list) else None for idx in [int(ep) for ep in filtered_epochline]]
            speed_epoch_series = [sp_raw_list[idx-1] if (idx-1) < len(sp_raw_list) else None for idx in [int(ep) for ep in filtered_epochline]]

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
                'h_time_series': h_time_series,
                'v_time_series': v_time_series,
                'de_time_series': de_time_series,
                'dn_time_series': dn_time_series,
                'du_time_series': du_time_series,
                'speed_time_series': speed_time_series,
                'h_epoch_series': h_epoch_series,
                'v_epoch_series': v_epoch_series,
                'de_epoch_series': de_epoch_series,
                'dn_epoch_series': dn_epoch_series,
                'du_epoch_series': du_epoch_series,
                'speed_epoch_series': speed_epoch_series,
                'scatter_pts': scatter_pts,
                'cdf_pts': cdf_pts
            })

        scatter_limit = round(global_max_scatter * 1.15, 3)

        progress.setValue(80)
        QApplication.processEvents()

        # 5. 组装并写入 HTML 文件
        html_content = HTML_REPORT_TEMPLATE
        html_content = html_content.replace('__REPORT_TITLE__', title_name)
        html_content = html_content.replace('__GEN_TIME__', gen_time)
        html_content = html_content.replace('__SEG_COUNT__', str(len(active_segs)))
        html_content = html_content.replace('__TOTAL_EPOCHS__', str(total_epochs))
        html_content = html_content.replace('__FIX_RATE_BLOCK__', fix_rate_block)
        html_content = html_content.replace('__H_RMS_BLOCK__', h_rms_block)
        html_content = html_content.replace('__H_95_BLOCK__', h_95_block)
        html_content = html_content.replace('__V_RMS_BLOCK__', v_rms_block)
        html_content = html_content.replace('__MAX_H_ERR_BLOCK__', max_h_block)
        html_content = html_content.replace('__SELECT_EPOCH__', select_epoch_attr)
        html_content = html_content.replace('__SELECT_TIME__', select_time_attr)
        html_content = html_content.replace('__DEFAULT_XAXIS_MODE__', default_xaxis_mode)
        html_content = html_content.replace('__IS_ABS_ALT__', 'true' if show_absolute_alt else 'false')
        html_content = html_content.replace('__METRICS_TABLE_HTML__', table_html)
        html_content = html_content.replace('__SEGMENTS_PAYLOAD_JSON__', json.dumps(segments_payload))
        html_content = html_content.replace('__GLOBAL_TIMELINE_JSON__', json.dumps(filtered_timeline))
        html_content = html_content.replace('__GLOBAL_EPOCHLINE_JSON__', json.dumps(filtered_epochline))
        html_content = html_content.replace('__SCATTER_LIMIT__', str(scatter_limit))

        progress.setValue(95)
        QApplication.processEvents()

        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        progress.setValue(100)
        QMessageBox.information(parent_window, "成功", f"交互式 HTML 评定报告已成功生成:\n{save_path}\n可直接使用任意浏览器双击打开！")

    except Exception as e:
        QMessageBox.critical(parent_window, "导出失败", f"生成 HTML 报告时发生错误:\n{e}")
