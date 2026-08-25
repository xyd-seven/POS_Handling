# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
基于 PySide6 开发的 GNSS/NMEA 定位精度分析与格式转换桌面工具。支持多协议解析、动静态高精度对比、ENU三向误差、速度对比、误差累积分布 (CDF)、极坐标天空图 (SkyPlot)、3D 空间立体天球穹顶 (3D SkyDome)、载噪比柱状图及 Word 报告导出。当前阶段已完成配置文件 EXE 同级目录持久化存储与串口实时缓存生命周期彻底清理。

---

## 2. 当前状态
- [x] **配置文件 EXE 同级目录持久化上线**：
  - 动态识别 sys.frozen，vcom_config.json 永久写入 EXE 同级目录；
  - 自定义历史参考坐标、UI 布局与显示偏好重启永久保留；
  - 增加 AppData 权限安全回退；
- [x] **串口分段删除与重开缓存彻底清理上线**：
  - on_seg_delete_clicked 同步 clear 掉 realtime_raw_epochs 与 COM_REALTIME 映射；
  - 杜绝再次开启串口时残留历史旧数据；
- [x] **全量测试与回归测试 PASS**，PyInstaller 编译并部署至 F:\\TestTools\\pos_handling\\dist\\。

---

## 3. 当前任务
- 无（配置文件持久化与串口缓存清理已全面交付上线）

---

## 4. 关键设计决策
- get_app_config_file_path 定位 sys.executable 目录并带 AppData 回退；
- on_seg_delete_clicked 显式清理底层实时队列与全局历元映射。

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
1. [第二梯队 - 优先级高] Phase 2: 在线瓦片本地自动缓存 (Tile Caching - exe同级目录)。
2. [第二梯队 - 优先级高] Phase 3: 百万级 LOD 视口动态降采样渲染。
3. [第二梯队 - 优先级中] TTFF 首次定位时间与 RTK 重捕获 (Re-Fix Time) 自动化分析。

---

## 8. 测试状态
- 历史坐标跨实例保存与恢复测试：PASS
- 串口分段删除与缓存重置测试：PASS
- 独立进程健康运行测试：PASS
- 全量 9 大 Tab 回归测试：PASS
- PyInstaller 编译与部署：PASS
