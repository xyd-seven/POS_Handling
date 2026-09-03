# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成全界面 100% 彻底无死角浅色模式交付。

---

## 2. 当前状态
- [x] **方向 5：HTML 报告与主界面按钮排版 5 项问题彻底修复与交付**：
  1. **指标看板数值显示**：修复 metrics 键名映射（`rtk_fix_rate`, `rms_h`, `cep95`, `rms_v`, `max_h`），支持 table_metrics 兜底；
  2. **地图整体偏移纠偏**：引入 `wgs84_to_gcj02` 将 WGS-84 原始轨迹纠偏为火星坐标，与高德路网严丝合缝贴合；
  3. **三向误差/散点/速度数据填充**：对接 `de`, `dn`, `v_errors`, `speed_test` 与 `enu_points`，图表数据饱满展现；
  4. **图表标题与Y轴重合**：ECharts 主标题水平居中（`left: 'center'`），增加顶部 grid 留白，彻底消除重合；
  5. **操作按钮重新排版**：改用 4 行 2 列对称网格排布，每个按钮宽度提升近 1 倍，所有文字及英文字母完整展现，绝不截断。
- [x] **全量测试与回归测试 PASS**，PyInstaller onedir 编译并部署至 `F:\TestTools\pos_handling\dist\main\`。

---

## 3. 当前任务
- 无（5 项问题全部彻底修复并上线）

---

## 4. 关键设计决策
- 高德地图底图强制进行 GCJ-02 纠偏，保证国内路网贴合度；
- 侧边栏按钮采用 2 列等宽布局兼顾高 DPI 缩放下的字体完整性；
- HTML 报告图表主标题居中排布，保证与 Y 轴单位标签的视觉解耦。

---

## 5. 修改记录
- exporters/html_exporter.py
- exporters/excel_exporter.py
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
- HTML 指标看板数据提取与非零断言：PASS
- WGS84 转 GCJ02 火星坐标纠偏有效性：PASS
- ENU 三向、散点、速度图数据集填充完整性：PASS
- ECharts 居中标题与 Y 轴留白防重叠样式：PASS
- 侧边栏 4 行 2 列布局与完整无截断文字验证：PASS
- PyInstaller onedir 编译与部署：PASS

---

## 9. 编译打包与交付规范 (Packaging & Delivery Convention)
- **编译命令**：`py -m PyInstaller main.spec -y`
- **交付目标路径**：直接复制生成的 `dist/main` 绿色文件夹至 `F:\TestTools\pos_handling\dist\main\`
- **启动路径**：`F:\TestTools\pos_handling\dist\main\main.exe`（无需任何解压，双击即秒开）
