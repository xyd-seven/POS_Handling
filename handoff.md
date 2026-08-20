# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成非破坏性 Overlay 架构、当前页面 0 毫秒点击刷新及各图表专属误差值气泡展示。

---

## 2. 当前状态
- [x] 非破坏性 Overlay 架构改造：彻底废除点击事件中的 ig.clear()，采用常驻 cursor_artists 局部更新机制，彻底根除死锁；
- [x] 当前折线图点击 0 延迟即刻刷新时间线（无需切换 Tab，点击瞬间垂直虚线与数据气泡毫秒级瞬移）；
- [x] 垂直时间线 Data Callout 气泡展示各图表对应的精准误差值：
  - 水平位置误差图：#历元 | 时间 | 误差: X.XXXm | 解状态
  - 高程误差图：#历元 | 时间 | 误差: +X.XXXm | 解状态
  - ENU 三向误差图：#历元 | 时间 | E:+X.XX N:+X.XX U:+X.XXm | 解状态
  - 速度对比图：#历元 | 时间 | 误差: +X.XXm/s | 解状态
- [x] 坐标轴严格防拉伸安全锁与 50%/68%/95% 置信圆环；
- [x] 全量测试 PASS，可执行程序已编译部署至 F:\TestTools\pos_handling\dist\GNSS_Precision_Tool_1.0.9.exe。

---

## 3. 当前任务
- 无（Overlay 局部即时刷新与专属误差气泡已全面上线交付）

---

## 4. 关键设计决策
- 维护 self.cursor_artists 列表，点击时仅 rtist.remove() 并重绘线段和气泡，最后调用 draw_idle()，从根本上杜绝画布销毁死锁。

---

## 5. 修改记录
- plot_widget.py
- main.py
- handoff.md

---

## 6. 已知问题
无已知未修复的 P0、P1、P2 级别问题。

---

## 7. 下一步任务
1. [第二梯队 - 优先级高] TTFF 首次定位时间与 RTK 重捕获 (Re-Fix Time) 自动化分析。
2. [第二梯队 - 优先级高] 离线/在线 GIS 真实路况地图轨迹叠加。

---

## 8. 测试状态
- Overlay 架构局部即刻刷新测试：PASS
- 各图表误差气泡测试：PASS
- PyInstaller 编译部署：PASS
