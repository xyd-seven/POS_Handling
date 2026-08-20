# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成交互式 WebGIS 真实路况地图双向来回无缝切换与数据加载异步自动跳转自适应居中。

---

## 2. 当前状态
- [x] **GIS 视图与笛卡尔视图双向来回无缝切换**：
  - 在笛卡尔工具栏最右侧追加 🌐 切换至GIS地图视图 按钮，彻底解决切到笛卡尔后按钮丢失无法切回的问题；
  - 两边视图顶栏均提供直观对称的切换按钮，随时自由来回切换；
- [x] **数据导入后地图异步自动跳转并居中展示轨迹**：
  - 接入 QWebEngineView.loadFinished 监听与数据状态缓存机制；
  - 无论何时导入 NMEA/POSOL/RTK 日志，地图页面加载完成即刻自动执行 itBounds 将全局轨迹自适应缩放居中展示；
- [x] **全量测试与回归测试 PASS**，PyInstaller 编译并部署至 F:\TestTools\pos_handling\dist\GNSS_Precision_Tool_1.0.9.exe。

---

## 3. 当前任务
- 无（双向视图切换与数据自动居中跳转已全面上线交付）

---

## 4. 关键设计决策
- 在笛卡尔工具栏最右侧添加 tn_switch_to_gis；
- 在 GISMapWidget 中缓存数据并在 loadFinished 触发时自动渲染并调用 itBounds。

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
- 视图双向切换测试：PASS
- 异步加载完成后自动跳转与 fitBounds 测试：PASS
- PyInstaller 编译与可执行程序部署：PASS
