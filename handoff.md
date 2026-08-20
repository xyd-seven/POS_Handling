# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成 GIS 地图顶栏高度锁定（消除黑框）与切 Tab / 启动时自动重新测算自适应缩放居中。

---

## 2. 当前状态
- [x] GIS 地图顶栏高度严格锁定 38px，彻底消除黑框占位问题，地图全屏铺满；
- [x] 直接切换到 Tab 8 即刻自动跳转并居中展示轨迹（showEvent 自动触发 invalidateSize 与 fitBounds）；
- [x] GIS 视图与笛卡尔视图双向来回无缝切换；
- [x] 全量测试 PASS，可执行程序已编译部署至 F:\TestTools\pos_handling\dist\GNSS_Precision_Tool_1.0.9.exe。

---

## 3. 当前任务
- 无（黑框问题与 Tab 8 初次进入自动居中已彻底修复上线）

---

## 4. 关键设计决策
- toolbar.setFixedHeight(38) + layout.addWidget(toolbar, 0) + layout.addWidget(web_view, 1)；
- showEvent + 定时器延时调用 map.invalidateSize() 与 fitBounds。

---

## 5. 修改记录
- gis_map_widget.py
- main.py
- handoff.md

---

## 6. 已知问题
无已知未修复的 P0、P1、P2 级别问题。

---

## 7. 下一步任务
1. [第二梯队 - 优先级高] TTFF 首次定位时间与 RTK 重捕获 (Re-Fix Time) 自动化分析。
2. [第二梯队 - 优先级中] 离线 MBTiles 格式离线底图包文件拖拽加载支持。

---

## 8. 测试状态
- 顶栏高度锁定测试：PASS
- showEvent 自动 invalidateSize 与 fitBounds 测试：PASS
- PyInstaller 编译与部署：PASS
