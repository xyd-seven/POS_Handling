# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已采用官方原生 QtWebEngine 工业级架构并完成深度依赖剪枝，彻底解决导入日志卡死问题。

---

## 2. 当前状态
- [x] **采用官方原生 QtWebEngine 工业级架构**：
  - 彻底杜绝 Windows Forms / COM 消息泵与 Qt 模态对话框的死锁冲突；
  - 导入日志、多文件批处理、大文件加载 100% 流畅丝滑、0 假死；
- [x] **深度依赖剪枝（瘦身超 41MB）**：
  - 剔除 QtQuick/QtQml/Qt3D/QtVirtualKeyboard/scipy/pandas 等 20+ 个大型冗余库，体积由 245MB 优化至 203.8MB；
- [x] **GIS 地图与全量功能 100% 完好**：
  - 高德矢量/高德卫星/谷歌纯卫星/天地图WMTS 自由切换，支持瓦片异常防黑屏保护；
  - RTK 分段着色、参考真值对比、全局多图时间双向联动、双模无缝切换；
- [x] **全量测试与回归测试 PASS**，PyInstaller 编译并部署至 F:\\TestTools\\pos_handling\\dist\\。

---

## 3. 当前任务
- 无（官方原生架构加固与深度剪枝已全面交付上线）

---

## 4. 关键设计决策
- 采用 PySide6 官方原生集成的 QWebEngineView + QWebChannel；
- main.spec 精准 excludes 依赖裁剪 + optimize=0 保障 NumPy 稳定。

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
- 日志导入与解析死锁防范测试：PASS
- 独立进程健康运行测试：PASS
- 全量 9 大 Tab 回归测试：PASS
- PyInstaller 编译与部署：PASS
