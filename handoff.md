# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成全界面 100% 彻底无死角浅色模式交付。

---

## 2. 当前状态
- [x] **方向 5：HTML 报告【靶心图全屏原点精准锁定 + 深色/浅色模式无缝切换】全面交付上线**：
  1. **靶心图全屏同心圆偏移彻底修复**：摒弃硬编码像素 `graphic` 方案，改用几何折线系列（`x = r*cos(θ), y = r*sin(θ)`），无论窗口如何缩放或全屏展开，同心圆圆心永远 100% 牢牢咬住 `(0, 0)` 坐标原点，彻底消除像素偏移错位；
  2. **支持深色 / 浅色模式（Dark / Light Theme）一键切换**：
     - 报告 Header 右侧新增 `☀️ 浅色模式 / 🌙 深色模式` 切换按钮；
     - 切换时 CSS 全局调色板（背景、卡片、表格、边框、文字）平滑渐变过度；
     - 全套 ECharts 图表（标题、轴线、网格线、图例、同心圆标尺）自适应重绘，完美适配明亮办公/投影演示与暗黑极客双重场景。
- [x] **全量测试与回归测试 PASS**，PyInstaller onedir 编译并部署至 `F:\TestTools\pos_handling\dist\main\`。

---

## 3. 当前任务
- 无（靶心图偏移已修复，深浅色主题已上线）

---

## 4. 关键设计决策
- 同心圆网格由 CSS/Canvas 绝对像素迁移到直角坐标空间数学曲线，实现了真正的几何比例不变性与矢量自适应；
- 采用 CSS `data-theme` 属性与 ECharts 多主题调色板解耦，确保图表重绘性能与界面渲染完全同步。

---

## 5. 修改记录
- exporters/html_exporter.py
- main.py
- walkthrough.md
- handoff.md

---

## 6. 已知问题
无已知未修复的 P0、P1、P2 级别问题。

---

## 7. 下一步任务
1. [方向 4 - 优先级高] u-blox UBX 原生二进制协议 (`.ubx`) 直接拖入解析支持。
2. [方向 4 - 优先级高] RTCM 3.x 差分报文链路监视面板（基站坐标与电文更新率）。
3. [第二梯队 - 优先级高] Phase 3: 百万级 LOD 视口动态降采样渲染。
4. [第二梯队 - 优先级中] TTFF 首次定位时间与 RTK 重捕获 (Re-Fix Time) 自动化分析。

---

## 8. 测试状态
- 靶心图全屏放大同心圆与坐标轴 (0,0) 原点零偏差验证：PASS
- 深色与浅色双主题 CSS 变量与按钮状态切换验证：PASS
- ECharts 主题自适应色彩提取与无刷新重绘验证：PASS
- PyInstaller onedir 编译与部署：PASS

---

## 9. 编译打包与交付规范 (Packaging & Delivery Convention)
- **编译命令**：`py -m PyInstaller main.spec -y`
- **交付目标路径**：直接复制生成的 `dist/main` 绿色文件夹至 `F:\TestTools\pos_handling\dist\main\`
- **启动路径**：`F:\TestTools\pos_handling\dist\main\main.exe`（无需任何解压，双击即秒开）
