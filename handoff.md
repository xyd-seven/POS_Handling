# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成全部 4 组时序图（水平误差、高程误差、ENU三向误差、速度对比）全子图时间线与数据气泡同步联动。

---

## 2. 当前状态
- [x] ENU 三向误差图全子图（E-W, N-S, U-D）垂直时间线与复合数据气泡（E:+X.XX N:+X.XX U:+X.XXm）；
- [x] 速度对比图全子图（待测速度跟踪, 速度误差分布）垂直时间线与速度误差气泡（误差: +X.XXm/s）；
- [x] 水平位置误差图与高程误差图 0 延迟即刻刷新时间线与专属误差气泡；
- [x] 非破坏性 Overlay 架构，彻底根除 Matplotlib Canvas 销毁死锁；
- [x] 坐标轴严格防拉伸安全锁与 50%/68%/95% 置信圆环；
- [x] 全量测试 PASS，可执行程序已编译部署至 F:\TestTools\pos_handling\dist\GNSS_Precision_Tool_1.0.9.exe。

---

## 3. 当前任务
- 无（全部图表时间联动与数据气泡已全面上线交付）

---

## 4. 关键设计决策
- 在 
ender_data 开头完整记录状态，并在 update_cursor_overlay 自动遍历当前多子图结构（E/N/U, Speed/Speed_Err），实现多子图统一画线与气泡对齐。

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
- ENU 三向误差图 Overlay 测试：PASS
- 速度对比图 Overlay 测试：PASS
- PyInstaller 编译部署：PASS
