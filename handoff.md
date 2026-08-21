# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成用户专属天地图 WMTS 官方标准协议密钥配置与部署。

---

## 2. 当前状态
- [x] 用户专属天地图 Key 与标准 WMTS 规范配置上线（支持 img_w, cia_w, vec_w, cva_w）；
- [x] 填入用户专属授权 Key：8e50f8cdd0450027d98d635238363e11；
- [x] 为 Web 容器配置 baseUrl 注入合法请求来源；
- [x] 全量测试 PASS，可执行程序已编译部署至 F:\TestTools\pos_handling\dist\GNSS_Precision_Tool_1.0.9.exe。

---

## 3. 当前任务
- 无（天地图官方密钥与协议已配置上线交付）

---

## 4. 关键设计决策
- 天地图 WMTS 协议规范 + 专属 Key 授权；
- WebEngine baseUrl 注入合法来源。

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
- 天地图配置验证：PASS
- PyInstaller 编译与部署：PASS
