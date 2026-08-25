# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成 2.5K/4K 屏幕与 150% 缩放下靶心图居中自适应与高 DPI 适配。

---

## 2. 当前状态
- [x] **高分屏 (2520*1680, 150% 缩放) 靶心图居中与自适应放大修复**：
  - 修复 PlotWidget.resizeEvent 绕过 QtAgg 原生高 DPI 机制导致的 1/1.5 画布缩小问题；
  - 靶心图显式设置 anchor='C' 和 adjustable='box'，在宽屏下实现水平垂直绝对居中并最大化充满画布；
  - 入口全局启用 Qt 原生 PassThrough 高 DPI 缩放策略；
- [x] **全量测试与回归测试 PASS**，PyInstaller 编译并部署至 F:\\TestTools\\pos_handling\\dist\\。

---

## 3. 当前任务
- 无（高 DPI 与靶心图居中自适应已全面交付上线）

---

## 4. 关键设计决策
- super().resizeEvent 配合 Matplotlib Qt 后端处理 Device Pixel Ratio；
- ax.set_anchor('C') 实现等比例正方图表居中。

---

## 5. 修改记录
- main.py
- plot_widget.py
- walkthrough.md
- handoff.md

---

## 6. 已知问题
无已知未修复的 P0、P1、P2 级别问题。

---

## 7. 下一步任务
1. [第二梯队 - 优先级高] Phase 2: 在线瓦片本地自动缓存 (Tile Caching - exe同级目录)。
2. [第二梯队 - 优先级高] Phase 3: 百万级 LOD 视口动态降采样渲染。
3. [第二梯队 - 优先级中] TTFF 首次定位时间与 RTK 重捕获 (Re-Fix Time) 自动化分析。

---

## 8. 测试状态
- 2520x1680 150% DPI 靶心图居中测试：PASS
- 独立进程健康运行测试：PASS
- 全量 9 大 Tab 回归测试：PASS
- PyInstaller 编译与部署：PASS
