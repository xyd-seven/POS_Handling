# Hand Off - VCOM定位精度分析工具交接文档

## 1. 项目目标
本软件是基于 PySide6 (Qt) 开发的 GNSS/NMEA 定位精度分析与格式转换的桌面工具。当前阶段已完成算法健壮性修复、性能降采样优化与系统主题自适应工具栏，最终目标是提供一个高性能、轻量、高可读的定位质量分析与转换工具。

---

## 2. 当前状态
- `[x]` 修复 `plot_widget.py` 图表长度不匹配及 `log10(0)` 崩溃问题
- `[x]` 修复 `gnss_parser.py` 里的 numpy 多维数组布尔判定及跨零点时间 unwrap 逻辑
- `[x]` 解决 Windows 浅色/深色模式下 Matplotlib 导航工具栏按钮由于前景色冲突而无法看清的 Bug
- `[x]` 通过读取 Windows 注册表精确识别系统真实明暗主题，实现工具栏背景实时联动重绘
- `[x]` 完成 VCOM 桌面程序的自动化编译与 PyInstaller 二进制打包交付
- `[x]` 确认支持各类 XXGGA（如 $GPGGA, $GBGGA, $GNGGA）格式的 NMEA 语句解析

---

## 3. 当前任务
目前所有既定功能和已知 Bug（包括浅色/深色模式显示、跨午夜 unwrap 时间、大点数降采样优化、XXGGA兼容等）均已开发、测试并打包完成。当前没有正在处理的挂起任务。

---

## 4. 关键设计决策
* **注册表主题检测机制**：由于主窗口加载了全局深色 QSS 样式表，会导致 Qt 的 `self.palette()` 被污染（永远返回深色），从而无法检测真实的系统主题。因此设计了通过 Python 内置 `winreg` 模块直接读取 Windows 注册表项 `AppsUseLightTheme` 的检测机制。在 `changeEvent` 中监听 `ThemeChange` 与 `PaletteChange` 事件，实现了实时联动。
* **图表降采样算法 (Min-Max)**：当单次绘制数据点过大时，如果全量渲染会导致 UI 频繁卡顿。设计了 Min-Max 块降采样算法，分块求出局部极值进行绘制，既在不丢失最大最小偏差极值的前提下将渲染点数削减至安全阈值，又保障了拖拽和缩放的帧率。

---

## 5. 修改记录
* **修改文件**：
  - `f:/TestTools/pos_handling/main.py`
  - `f:/TestTools/pos_handling/ui_main.py`
  - `f:/TestTools/pos_handling/plot_widget.py`
  - `f:/TestTools/pos_handling/gnss_parser.py`
* **新增文件**：
  - `f:/TestTools/pos_handling/AI Coding Project Rules.md`
* **删除文件**：
  - 无

---

## 6. 已知问题
无已知未修复的 P0、P1、P2 级别问题。

---

## 7. 下一步任务
1. **[优先级 - 低] 跨平台自适应增强**：在非 Windows 系统（如 Linux/macOS）上可能需要进一步丰富 `is_system_dark_mode()` 的备用判定。
2. **[优先级 - 低] 扩展 NMEA 格式兼容**：若用户未来引入全新私有格式协议，需在 `gnss_parser.py` 中扩展对应字段映射。

---

## 8. 测试状态
* **Windows 浅色/深色主题实时联动切换测试**：PASS
* **XXGGA（$GPGGA/$GBGGA/$GNGGA）多卫星系统语句解析测试**：PASS
* **多线程大日志文件解析及 UI 响应测试**：PASS
* **打包后 VCOM.exe 独立运行测试**：PASS

---

## 9. 对下一位 Agent 的要求
* 先阅读相关实现
* 不扫描整个项目
* 非必要不读取大文件
* 保持现有架构
* 保持现有代码风格
* 修改前分析影响范围
* 遵守《AI Agent 工作准则》与 `AI Coding Project Rules.md`

发现以下情况立即停止并询问用户：
* 需求不明确
* 涉及数据库结构调整
* 涉及接口协议变更
* 涉及跨模块重构
* 涉及架构调整
* 无法确认影响范围
