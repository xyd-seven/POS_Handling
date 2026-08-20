# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成 GIS 地图天地图 DataServer 修复、新增免Key谷歌高清混合卫星图及初次切入 Tab 8 毫秒级自动居中跳转。

---

## 2. 当前状态
- [x] **天地图与谷歌卫星高清图源全面就绪（彻底根除黑屏）**：
  - 升级天地图为官方标准的 DataServer 瓦片服务，并配置高可用 Token；
  - 增加「谷歌混合卫星 (免Key/高清)」图源，与高德矢量/高德卫星构成三大免 Key 高速图源；
- [x] **初次切入 Tab 8 即刻毫秒级自动跳转居中展示轨迹**：
  - 在 showEvent 中加入多阶段（50ms, 200ms, 500ms）invalidateSize(true) 与 itBoundsNow，无论从哪个 Tab 切入，地图 100% 自动对准轨迹；
- [x] **全量测试与回归测试 PASS**，PyInstaller 编译并部署至 F:\TestTools\pos_handling\dist\GNSS_Precision_Tool_1.0.9.exe。

---

## 3. 当前任务
- 无（地图瓦片与初次自动居中已全面上线交付）

---

## 4. 关键设计决策
- 天地图 DataServer 协议 + 谷歌卫星图源 + showEvent 多阶段自适应缩放。

---

## 5. 修改记录
- gis_map_widget.py
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
- 图源定义与天地图 DataServer 测试：PASS
- showEvent 自动渲染与 fitBounds 测试：PASS
- PyInstaller 编译与部署：PASS
