# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成全界面 100% 彻底无死角浅色模式交付。

---

## 2. 当前状态
- [x] **onedir 绿色文件夹版极速秒开与载噪比图层置顶交付**：
  - main.spec 重构为 onedir (COLLECT) 规范，消除 200MB 运行解压 I/O 阻塞，启动时间缩短至 1 秒以内；
  - 载噪比立柱设置 bar_item.setZValue(20)，彻底根除 Y 轴水平网格线穿透立柱的瑕疵；
- [x] **全量测试与回归测试 PASS**，PyInstaller 编译并部署至 `F:\TestTools\pos_handling\dist\main\`。

---

## 3. 当前任务
- 无（onedir 绿色极速启动版本已全面交付上线）

---

## 4. 关键设计决策
- 生产环境采用 onedir 预解压目录结构保证秒开；
- 载噪比立柱 Z-Value 强制置顶。

---

## 5. 修改记录
- main.py
- main.spec
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
- onedir 冷启动速度基准测试（< 1s）：PASS
- 载噪比立柱 Z-Value 置顶验证：PASS
- 独立进程健康运行测试：PASS
- 全量 9 大 Tab 回归测试：PASS
- PyInstaller onedir 编译与部署：PASS

---

## 9. 编译打包与交付规范 (Packaging & Delivery Convention)
- **编译命令**：`py -m PyInstaller main.spec -y`
- **交付目标路径**：直接复制生成的 `dist/main` 绿色文件夹至 `F:\TestTools\pos_handling\dist\main\`
- **启动路径**：`F:\TestTools\pos_handling\dist\main\main.exe`（无需任何解压，双击即秒开）
