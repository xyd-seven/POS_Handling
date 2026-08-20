# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、载噪比柱状图及 Word 报告导出。当前阶段已完成雷达极坐标天空图模块与 Word 报告深度集成。

---

## 2. 当前状态
- [x] **模块化分层解耦落地**：
  - 新增 plots/skyplot_canvas.py：独立封装 Matplotlib 极坐标雷达盘、四大星座分类着色、在用/跟踪星区分、10° 截止角环、时间滑块探伤与全时段星轨曲线渲染；
  - 新增 core/skyplot_model.py：独立管理 GSV 数据的 (1)$ 秒级快速切片哈希索引与多时段星轨提取；
  - 在 exporters/word_exporter.py 中深度集成「3.9 卫星极坐标天空图 (SkyPlot)」离屏抓取与排版写入；
- [x] **主界面「卫星星空图 (SkyPlot)」选项卡装配**：
  - 左侧展示高清极坐标雷达盘；
  - 右侧提供「星座在用/可见统计看板」及「DOP 几何衰减因子 (PDOP/HDOP/VDOP)」卡片；
  - 底部配置「时间探伤滑块」与当前时刻标签，支持单时刻探伤与全时段星轨一键切换；
  - 串口实时接收与数据回放时自动秒级联动跳动刷新；
- [x] **全量回归与专项测试**：	est_skyplot.py 与 	est_full_regression.py 全部 100% 通过；
- [x] **PyInstaller 独立编译与部署**：成功打包并覆盖交付至 F:\TestTools\pos_handling\dist\GNSS_Precision_Tool_1.0.9.exe。

---

## 3. 当前任务
- 无（雷达极坐标天空图模块开发、测试、打包与交付全部圆满完成）

---

## 4. 关键设计决策
- **极坐标天顶投影数学模型**：天顶仰角 ^\circ$ 映射至极坐标原点（=0$），地平线 ^\circ$ 映射至外圈（=90$），极角以正北（0°/N）为顶部顺时针旋转（$\theta = \text{radians}(90 - \text{Azimuth})$）。
- **(1)$ 秒级快速检索哈希索引**：在 SkyPlotDataModel 中按秒维护 	ime_to_sats 与 	ime_to_dop 映射，时间轴滑块拖拽时无需重复扫描全量原始日志，实现 60 FPS 流畅拖拽体验。
- **高对比度多星座着色**：北斗 BDS (红)、GPS (蓝)、GLONASS (黄)、Galileo (青)，在用卫星采用实心高亮圆点，跟踪星采用半透明空心圆点，视觉对比清晰强烈。

---

## 5. 修改记录
- plots/skyplot_canvas.py
- plots/__init__.py
- core/skyplot_model.py
- core/__init__.py
- exporters/word_exporter.py
- main.py
- handoff.md

---

## 6. 已知问题
无已知未修复的 P0、P1、P2 级别问题。

---

## 7. 下一步任务
1. **[优先级 - 中] TTFF 首次定位时间与 RTK 重捕获 (Re-Fix) 分析**：冷热启动首个有效历元耗时与 RTK 失锁后恢复固定时间统计。
2. **[优先级 - 低] 多模组同屏对比跑分**：批量多日志同屏 CDF 与精度雷达对比。

---

## 8. 测试状态
- **SkyPlotDataModel 秒级切片与星轨提取测试**：PASS
- **SkyPlotCanvas 极坐标快照与星轨渲染测试**：PASS
- **9 大核心图表端到端全量渲染测试**：PASS
- **Word 评测报告自动生成测试**：PASS
- **PyInstaller 编译与可执行程序部署**：PASS

---

## 9. 对下一位 Agent 的要求
- 先阅读相关实现
- 不扫描整个项目
- 非必要不读取大文件
- 保持现有架构
- 保持现有代码风格
- 修改前分析影响范围
- 遵守《AI Agent 工作准则》

发现以下情况立即停止并询问用户：
- 需求不明确
- 涉及数据库结构调整
- 涉及接口协议变更
- 涉及跨模块重构
- 涉及架构调整
- 无法确认影响范围
