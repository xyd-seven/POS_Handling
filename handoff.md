# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成全界面 100% 彻底无死角浅色模式交付。

---

## 2. 当前状态
- [x] **图表字体粗体放大与载噪比浅色背景交付**：
  - 误差图/分布图标题放大至 16px 粗体，XY 轴名称放大至 13px 粗体，刻度放大至 11.5px 加黑；
  - 彻底修复 CNoPlotCanvas 浅色模式背景硬编码判定，统一呈现为浅云米白 (#F8FAFC)；
- [x] **全量测试与回归测试 PASS**，PyInstaller 编译并部署至 `F:\TestTools\pos_handling\dist\main.exe`。

---

## 3. 当前任务
- 无（图表字号放大与载噪比浅色背景已全面交付上线）

---

## 4. 关键设计决策
- 图表字体层次（标题 16px -> 轴名 13px -> 刻度 11.5px）确保在各类分辨率下清晰醒目；
- 载噪比柱状图遵循全局语义化 tokens['name'] == 'light' 分发。

---

## 5. 修改记录
- plot_widget.py
- main.py
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
- 图表标题与坐标轴字号放大验证：PASS
- 载噪比浅色模式 #F8FAFC 底色验证：PASS
- 独立进程健康运行测试：PASS
- 全量 9 大 Tab 回归测试：PASS
- PyInstaller 编译与交付部署：PASS

---

## 9. 编译打包与交付规范 (Packaging & Delivery Convention)
- **编译命令**：`py -m PyInstaller main.spec -y`
- **交付目标路径**：直接复制生成的 `dist/main.exe` 至 `F:\TestTools\pos_handling\dist\main.exe`
- **规则要求**：
  1. **保持原名**：保持为 `main.exe`，无需重命名版本号；
  2. **无需打包压缩包**：无需生成额外的绿色版 `.zip` 压缩文件。
