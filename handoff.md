# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成交互式 WebGIS 真实路况与卫星地图轨迹叠加（方案 A）。

---

## 2. 当前状态
- [x] **交互式 WebGIS 真实路况与高清卫星地图轨迹叠加 (GISMapWidget)**：
  - 基于 PySide6.QtWebEngineWidgets + Leaflet.js 现代地图引擎；
  - 支持多源高清底图开箱即用无缝切换：高德矢量路网 (免Key)、高德高清卫星 (免Key)、天地图高清卫星、天地图矢量路网、OpenStreetMap、CartoDB 暗黑底图；
  - 内置高精度 WGS84 <-> GCJ-02 坐标纠偏转换算法 (coord_transform.py)，高德等国内地图路网与轨迹严丝合缝；
  - 待测轨迹按 RTK 状态着色（绿=RTK固定4、黄=RTK浮点5、蓝=差分2、红=单点1/无效0），失锁飘移一目了然；
  - 支持参考真值基准线（深蓝色半透明轨迹）同屏贴合对比；
  - 车辆/历元动态呼吸脉冲光标定位与历元信息气泡；
  - 双向多图时间联动：时序图点击 <-> 地图定位光标毫秒级瞬移与气泡弹出；
  - 一键自由切换：🌐 GIS真实路况地图 <-> 📊 笛卡尔经纬度投影图；
- [x] **定位精度指标与靶心图 HUD / 置信圆**：50%/68%/95% 置信圆环，右上角半透明 HUD 卡片；
- [x] **全量测试与回归测试 PASS**，PyInstaller 编译并部署至 F:\TestTools\pos_handling\dist\GNSS_Precision_Tool_1.0.9.exe。

---

## 3. 当前任务
- 无（GIS 真实路况地图轨迹叠加已全面上线交付）

---

## 4. 关键设计决策
- coord_transform.py 实现 WGS84 -> GCJ-02 精确纠偏；
- gis_map_widget.py 封装 QWebEngineView 与 QWebChannel，底图免 Key / 预置 Key 零配置开箱即用。

---

## 5. 修改记录
- coord_transform.py (新增)
- gis_map_widget.py (新增)
- main.py (修改)
- main.spec (修改)
- handoff.md (修改)

---

## 6. 已知问题
无已知未修复的 P0、P1、P2 级别问题。

---

## 7. 下一步任务
1. [第二梯队 - 优先级高] TTFF 首次定位时间与 RTK 重捕获 (Re-Fix Time) 自动化分析。
2. [第二梯队 - 优先级中] 离线 MBTiles 格式离线底图包文件拖拽加载支持。

---

## 8. 测试状态
- 坐标纠偏算法精度测试：PASS
- GISMapWidget 数据序列化与 RTK 切分测试：PASS
- MainWindow GIS 地图双模与光标时间联动测试：PASS
- PyInstaller 编译与可执行程序部署：PASS
