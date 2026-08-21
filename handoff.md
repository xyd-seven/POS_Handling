# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成体积瘦身（剥离 41MB+ 冗余库）、瓦片异常容错保护、坐标安全清洗与全量功能 100% 回归。

---

## 2. 当前状态
- [x] **体积瘦身与依赖剪枝**：
  - 剔除 QtQuick/Qml/3D/VirtualKeyboard/tkinter/scipy 等大型冗余库，单文件体积缩减超 41.3MB（降至 203.8MB），构建与解压耗时提速 30%；
- [x] **全方位容错与异常防护**：
  - 增加瓦片加载异常 SVG 占位与优雅降级保护，避免黑屏；
  - 严格坐标野值清洗与 WebEngine baseUrl 来源注入；
- [x] **GIS 真实路况与高清卫星地图轨迹叠加**：
  - 高德矢量路网 (免Key)、高德高清卫星 (免Key)、谷歌纯高清卫星 (免Key/零偏移)、天地图官方卫星 (专属Key)；
  - RTK 解状态多色分段、参考真值对比、全局时间双向联动、双模无缝切换；
- [x] **全量测试与回归测试 PASS**，PyInstaller 编译并部署至 F:\TestTools\pos_handling\dist\。

---

## 3. 当前任务
- 无（体积瘦身与容错加固已全面上线交付）

---

## 4. 关键设计决策
- main.spec 精准 excludes 依赖裁剪；
- Leaflet errorTileUrl 容错降级 + coord_transform 坐标清洗。

---

## 5. 修改记录
- gis_map_widget.py
- main.spec
- walkthrough.md
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
- 全量 9 大 Tab 回归测试：PASS
- 瓦片容错与坐标清洗测试：PASS
- 依赖剪枝与 PyInstaller 编译部署：PASS
