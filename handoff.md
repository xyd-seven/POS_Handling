# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成全界面 100% 彻底无死角浅色模式交付。

---

## 2. 当前状态
- [x] **可见卫星载噪比监视器双击全屏/还原交互交付**：
  - CNoPlotCanvas 安装全局事件过滤器捕获左键双击事件并分发 `sig_double_clicked`；
  - 双击图表任意区域瞬时折叠/隐藏上方串口终端与状态卡片，载噪比柱状图独占全屏最大化显示；
  - 再次双击图表无缝平滑还原默认分割布局；
- [x] **全量测试与回归测试 PASS**，PyInstaller onedir 编译并部署至 `F:\TestTools\pos_handling\dist\main\`。

---

## 3. 当前任务
- 无（载噪比双击全屏/还原功能已全面交付上线）

---

## 4. 关键设计决策
- 载噪比双击全屏采用非模态原位最大化机制，避免多窗口切换闪烁，保障串口数据流持续渲染；
- 生产环境采用 onedir 预解压目录结构保证秒开；
- 瓦片缓存跟随程序安装目录，实现免占 C 盘且支持便携式离线地图包。

---

## 5. 修改记录
- main.py
- walkthrough.md
- handoff.md

---

## 6. 已知问题
无已知未修复的 P0、P1、P2 级别问题。

---

## 7. 下一步任务
1. [第二梯队 - 优先级高] Phase 3: 百万级 LOD 视口动态降采样渲染。
2. [第二梯队 - 优先级中] TTFF 首次定位时间与 RTK 重捕获 (Re-Fix Time) 自动化分析。

---

## 8. 测试状态
- 载噪比双击最大化与再次双击还原状态机测试：PASS
- 独立进程健康运行测试：PASS
- 全量 9 大 Tab 回归测试：PASS
- PyInstaller onedir 编译与部署：PASS

---

## 9. 编译打包与交付规范 (Packaging & Delivery Convention)
- **编译命令**：`py -m PyInstaller main.spec -y`
- **交付目标路径**：直接复制生成的 `dist/main` 绿色文件夹至 `F:\TestTools\pos_handling\dist\main\`
- **启动路径**：`F:\TestTools\pos_handling\dist\main\main.exe`（无需任何解压，双击即秒开）
