# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成 Windows 原生 Edge WebView2 引擎升级与体积暴降至 78MB。

---

## 2. 当前状态
- [x] **Windows 原生 Edge WebView2 引擎升级**：
  - 彻底拔除 QtWebEngineCore (140MB+)，改用 Windows 操作系统原生自带的 Microsoft Edge WebView2 运行时；
  - 单文件 EXE 体积由 245MB 骤降至 78.6MB (缩减 68%)，启动提速至瞬间秒开；
- [x] **GIS 地图与全量功能 100% 完好**：
  - 高德矢量/高德卫星/谷歌纯卫星/天地图WMTS 自由切换；
  - RTK 分段着色、参考真值对比、全局多图时间双向联动、双模无缝切换；
- [x] **全量测试与回归测试 PASS**，PyInstaller 编译并部署至 F:\\TestTools\\pos_handling\\dist\\。

---

## 3. 当前任务
- 无（Windows 原生 Edge WebView2 引擎升级与极致瘦身已全面交付上线）

---

## 4. 关键设计决策
- 基于 Windows 原生 Edge WebView2 渲染引擎 + QWidget 嵌入容器；
- main.spec 彻底剔除 QtWebEngine。

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
- WebView2 嵌入与 JS 双向通信测试：PASS
- 全量 9 大 Tab 回归测试：PASS
- PyInstaller 编译与部署：PASS
