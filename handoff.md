# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成谷歌卫星底图 WGS84 零偏差校准与数据导入全生命周期自轮询即刻渲染。

---

## 2. 当前状态
- [x] **谷歌混合卫星图源 WGS84 零偏差校准**：
  - 修正 google_sat 为 isGcj: false（WGS84 原生坐标系），杜绝错误偏移，真实车道/道路严丝合缝；
  - 高德路网/卫星图保持 isGcj: true 自动火星坐标系纠偏转换；
- [x] **初次直接切入 Tab 8 毫秒级自动渲染居中（彻底无需切换笛卡尔）**：
  - 
ecompute_all 在全局数据变更时即刻向 GIS 地图推送数据；
  - 
ender_trajectories 引入带自动轮询重试的 JavaScript 包装器，无论 Web 引擎何时就绪均能秒级画出轨迹并调用 itBounds；
- [x] **全量测试与回归测试 PASS**，PyInstaller 编译并部署至 F:\TestTools\pos_handling\dist\GNSS_Precision_Tool_1.0.9.exe。

---

## 3. 当前任务
- 无（谷歌卫星坐标校准与初次直接居中渲染已全面上线交付）

---

## 4. 关键设计决策
- 谷歌卫星图、天地图、OSM 统一为 isGcj: false；高德地图为 isGcj: true；
- JS 端 	ryExecute 自轮询保障异步 Web 页面随时即刻接收渲染指令。

---

## 5. 修改记录
- gis_map_widget.py
- main.py
- handoff.md

---

## 6. 已知问题
无已知未修复的 P0、P1、P2 级别问题。

---

## 7. 下一步任务
1. [第二梯队 - 优先级高] TTFF 首次定位时间与 RTK 重捕获 (Re-Fix Time) 自动化分析。
2. [第二梯队 - 优先级中] 离线 MBTiles 格式离线底图包文件拖拽加载支持。

---

## 8. 测试状态
- 谷歌卫星 WGS84 坐标测试：PASS
- 初次切入 Tab 8 自动渲染与居中测试：PASS
- PyInstaller 编译与部署：PASS
