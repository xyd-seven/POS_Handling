# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成全界面 100% 彻底无死角浅色模式交付。

---

## 2. 当前状态
- [x] **方向 5：HTML 报告【高程误差绝对值智能同步 + 三向 ENU 全实线平滑渲染】全面交付上线**：
  1. **高程误差绝对值 100% 同步**：导出时自动读取桌面端 `show_absolute_alt`（复选框 `cb_abs_alt`）状态，勾选时高程误差自动转换 `abs(v_val)`，标题自适应显示为 `高程位置误差绝对值历元分布图 (|Vertical Error| · ...)`，彻底消除负轴偏移；
  2. **三向 ENU 图全部统一为实线**：彻底移除北向 dN 的 `dashed`（虚线）与天向 dU 的 `dotted`（点虚线），三层独立子轴（东、北、天）全部采用纯实线展示，线条平滑清晰，彻底告别颗粒虚线感。
- [x] **全量测试与回归测试 PASS**，PyInstaller onedir 编译并部署至 `F:\TestTools\pos_handling\dist\main\`。

---

## 3. 当前任务
- 无（高程绝对值与三向全实线已全面交付）

---

## 4. 关键设计决策
- 高程误差绝对值在数据装填阶段即完成数学转换，并与图表标题状态标识联动；
- ENU 曲线由于已在纵向空间三层完全物理分离，全部采用实线更能准确呈现微小历元抖动。

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
- 桌面端高程绝对值开关继承与 abs() 转换验证：PASS
- ENU 三向曲线（dE, dN, dU）100% 纯实线样式验证：PASS
- PyInstaller onedir 编译与部署：PASS

---

## 9. 编译打包与交付规范 (Packaging & Delivery Convention)
- **编译命令**：`py -m PyInstaller main.spec -y`
- **交付目标路径**：直接复制生成的 `dist/main` 绿色文件夹至 `F:\TestTools\pos_handling\dist\main\`
- **启动路径**：`F:\TestTools\pos_handling\dist\main\main.exe`（无需任何解压，双击即秒开）
