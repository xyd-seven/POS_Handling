# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成 Windows 原生 Edge WebView2 引擎升级与 NumPy 2.x docstring 兼容性修复，最终生成 80MB 极速秒开版本。

---

## 2. 当前状态
- [x] **修复 NumPy 2.x docstring 启动异常**：
  - 将 main.spec 中的 optimize=2 调整为标准的 optimize=0，彻底消除 TypeError: argument docstring of add_docstring should be a str；
- [x] **Windows 原生 Edge WebView2 引擎全面上线**：
  - 彻底拔除 140MB+ 的 QtWebEngineCore，改用 Windows 操作系统原生自带的 Microsoft Edge WebView2 运行时；
  - 单文件 EXE 体积由 245MB 骤降至 80.3MB (缩减 67%)，启动提速至瞬间秒开；
- [x] **GIS 地图与全量功能 100% 完好**：
  - 高德矢量/高德卫星/谷歌纯卫星/天地图WMTS 自由切换；
  - RTK 分段着色、参考真值对比、全局多图时间双向联动、双模无缝切换；
- [x] **全量测试与回归测试 PASS**，PyInstaller 编译并部署至 F:\\TestTools\\pos_handling\\dist\\。

---

## 3. 当前任务
- 无（NumPy 启动异常与 WebView2 升级已全部完成交付）

---

## 4. 关键设计决策
- 基于 Windows 原生 Edge WebView2 渲染引擎 + QWidget 嵌入容器；
- main.spec 设置 optimize=0 兼容 NumPy 2.x。

---

## 5. 修改记录
- main.spec
- gis_map_widget.py
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
- NumPy 2.x 模块加载与启动测试：PASS
- 全量 9 大 Tab 回归测试：PASS
- PyInstaller 编译与部署：PASS
