# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成全界面 100% 彻底无死角浅色模式交付。

---

## 2. 当前状态
- [x] **方向 5：HTML 报告【单图双击全屏沉浸放大 / 双击还原】全面交付上线**：
  1. **全图表全覆盖**：水平误差、高程误差、ENU 三向误差、1:1 正圆靶心图、CDF 累积图、速度曲线以及空间轨迹地图，全部支持双击放大；
  2. **沉浸式视口自适应**：双击后瞬间切换为 100vw × 100vh 全屏模式，ECharts 与 Leaflet 地图毫秒级自适应重绘，曲线细节纤毫毕现；
  3. **三重退出机制**：支持再次双击原位还原、点击右上角悬浮按钮还原、键盘按 `ESC` 键还原；
  4. **视觉悬浮微反馈**：鼠标悬停在图表卡片右上角时呈现精致的 `⛶ 双击放大` 提示与品牌青蓝发光描边。
- [x] **全量测试与回归测试 PASS**，PyInstaller onedir 编译并部署至 `F:\TestTools\pos_handling\dist\main\`。

---

## 3. 当前任务
- 无（单图双击放大沉浸式交互已全面交付）

---

## 4. 关键设计决策
- 采用非侵入式 Fixed Overlay 全屏扩展方案，无需依赖浏览器的危险原生全屏权限；
- 窗口大小变动时自动触发图表 `resize()`，保证大屏高分辨率下的渲染精度。

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
- 图表双击全屏事件与 DOM 结构验证：PASS
- 全屏放大与还原自适应重绘验证：PASS
- ESC 键退出全屏事件验证：PASS
- PyInstaller onedir 编译与部署：PASS

---

## 9. 编译打包与交付规范 (Packaging & Delivery Convention)
- **编译命令**：`py -m PyInstaller main.spec -y`
- **交付目标路径**：直接复制生成的 `dist/main` 绿色文件夹至 `F:\TestTools\pos_handling\dist\main\`
- **启动路径**：`F:\TestTools\pos_handling\dist\main\main.exe`（无需任何解压，双击即秒开）
