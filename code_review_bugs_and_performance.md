# 当前代码 BUG 与性能优化走读报告

## 1. 走读范围

- `main.py`：主窗口、日志导入、串口实时解析、回放、导出、图表刷新。
- `gnss_parser.py`：NMEA、POGOS/PODRS、BK 二进制协议解析与流式分包。
- `plot_widget.py`：Matplotlib 多图表绘制与 resize 防抖。
- `ui_main.py`：分段时间输入校验。

本次仅做静态代码走读，未修改业务代码，未运行全量测试。

## 2. 已确认 BUG / 正确性风险

### BUG-01：`CNoPlotCanvas` 初始化逻辑疑似缩进错误，部分能力依赖首次 resize 才生效

- 位置：`main.py`，`CNoPlotCanvas.__init__` / `_handle_delayed_resize` 附近。
- 现象：坐标轴样式、国旗图标加载、`rendered_sats` 初始化、鼠标移动事件绑定等逻辑位于 `_handle_delayed_resize()` 内，而不是 `__init__()` 内。
- 影响：
  - 首次 resize 前，`flag_images` 可能不存在，`render_cno()` 绘制时无法显示国旗图标。
  - 鼠标悬浮事件绑定可能延迟到 resize 后才建立。
  - 每次 resize 后都会重新加载图标并重复绑定 `motion_notify_event`，可能造成重复回调和额外开销。
- 建议：将一次性初始化逻辑移回 `__init__()`；`_handle_delayed_resize()` 只负责尺寸更新和 `draw_idle()`。

### BUG-02：跨午夜分段在 UI 中允许，但统计查询按普通时间区间处理，可能返回空数据

- 位置：
  - `ui_main.py`：`SegmentListItemWidget.on_time_changed()` 允许开始时间大于结束时间的跨午夜范围。
  - `main.py`：`MainWindow.recompute_all()` 使用 `find_epoch_range(file_epochs, start_sec, end_sec)`，默认 `start_sec <= end_sec`。
- 现象：例如 `23:50:00 -> 00:10:00`，UI 认为是合法跨午夜；但 `recompute_all()` 中 `start_sec=85800`、`end_sec=600`，二分区间查询会得到空范围。
- 影响：跨天日志或夜间测试分段可能无法统计、绘图或导出有效数据。
- 建议：在数据已做 `unwrap_times()` 后，分段时间也应映射到同一连续时间轴；或者对跨午夜范围拆分为两段查询后合并。

### BUG-03：高倍速回放会跳过中间分包，实时分析数据可能缺失

- 位置：`main.py`，`MainWindow.replay_tick()`。
- 现象：当一次 tick 需要处理的分包数超过 20 时，代码将 `self.replay_index` 直接推进到 `target_index - 20`，只处理最后 20 个分包。
- 影响：
  - 控制台节流是合理的，但跳过 `parse_raw_chunk()` 会导致中间定位历元没有进入 `realtime_raw_epochs` / `parsed_epochs`。
  - 高倍速回放结束后的轨迹、指标和图表可能不是完整回放结果。
- 建议：区分“UI 刷新节流”和“数据解析完整性”。高倍速时可以跳过控制台输出和减少重绘，但不应跳过数据解析；如必须跳过，应在 UI 上明确标识为预览模式。

### BUG-04：回放滑块跳转只解析目标分包，不能恢复目标时刻前的累计状态

- 位置：`main.py`，`MainWindow.on_slider_released()`。
- 现象：释放滑块后会清空实时缓存，然后仅解析当前 `replay_index` 对应的一个分包。
- 影响：
  - 定位基本信息和 C/N0 能显示目标块附近状态，但轨迹/指标只包含单块数据。
  - 若用户期望“跳转到某时刻并保留此前已回放轨迹”，结果会与预期不一致。
- 建议：明确回放语义。如果是“定位预览”，当前实现可以保留但需文档/UI 提示；如果是“恢复到目标时刻累计状态”，需要从起点重放到目标或建立分包级快照/索引。

### BUG-05：GGA/GSA/POGOS 状态关联按整秒取模，跨天或高频数据可能串扰

- 位置：`main.py`，`LogParserThread.run()`。
- 现象：`gga_map` 使用 `int(utc_time_sec) % 86400` 作为键，把 GGA 的质量、卫星数、HDOP 与 GSA 的 VDOP/PDOP 关联到 POGOS/PODRS。
- 影响：
  - 同一秒内多条不同状态数据会互相覆盖。
  - 跨午夜、多天日志中同一日内秒会复用，可能把不同日期的数据错误关联。
- 建议：使用解包后的连续时间轴或更精细的时间键；若要关联最近 GGA/GSA，应按时间邻近查找并设置最大容忍窗口。

### BUG-06：原始导出 / GGA 转换导出不支持跨午夜分段

- 位置：
  - `main.py`，`on_export_raw_clicked()`。
  - `main.py`，`on_export_gga_clicked()`。
- 现象：导出判断使用 `start_sec <= utc_time_sec <= end_sec`，没有处理 `start_sec > end_sec` 的跨午夜场景。
- 影响：跨午夜分段导出的原始日志或转换 GGA 文件可能为空或缺失后半段。
- 建议：复用分段查询逻辑，统一处理跨午夜和解包时间轴；避免导入统计与导出逻辑各自实现时间过滤。

### BUG-07：录制文件写入异常被静默吞掉，用户无法知道录制失败

- 位置：`main.py`，`handle_serial_read()`。
- 现象：`self.record_file.write(data)` 失败后仅 `pass`。
- 影响：磁盘满、权限变化、U 盘拔出等情况下，界面仍可能显示录制中，但数据没有可靠写入。
- 建议：记录错误并停止录制状态，提示用户保存失败；错误信息保留英文异常内容，便于定位。

## 3. 性能优化点

### PERF-01：串口控制台长度检查使用 `toPlainText()`，高频数据下开销较大

- 位置：`main.py`，`parse_raw_chunk()`。
- 现象：每帧都执行 `len(self.txt_console.toPlainText()) > 50000`，会复制整个控制台文本。
- 影响：串口高频输出或回放时，文本越长，检查越慢，容易造成 UI 卡顿。
- 建议：维护独立字符计数，或使用 `QTextDocument.maximumBlockCount` 限制行数，避免每次复制全文。

### PERF-02：实时数据每个定位历元都触发全量 `recompute_all()`

- 位置：`main.py`，`handle_serial_read()`。
- 现象：只要 `parse_raw_chunk()` 返回新定位历元，就立即调用 `recompute_all()`，而 `recompute_all()` 会遍历所有分段、计算指标、刷新表格和当前图表。
- 影响：高频串口或高倍速回放下，CPU 与 UI 绘制压力较大。
- 建议：对实时统计增加定时节流，例如 2Hz 或 1Hz；数据仍完整入库，指标和图表按节流周期刷新。

### PERF-03：`process_live_epoch()` 多次列表推导维护实时窗口，复杂度随缓存长度增长

- 位置：`main.py`，`process_live_epoch()`。
- 现象：每个实时历元都会从 `realtime_raw_epochs` 和 `parsed_epochs` 中过滤、重建列表。
- 影响：虽然有 6000/2000 上限，但在高频场景仍会持续产生额外分配和遍历。
- 建议：使用 `collections.deque(maxlen=...)` 维护实时窗口；按源类型维护辅助缓存，减少重复过滤。

### PERF-04：回放预分包将日志内容全部常驻内存

- 位置：`main.py`，`load_replay_file()`。
- 现象：`self.replay_blocks` 保存 `(time, block_bytes)`，等于把完整日志按块读入内存。
- 影响：大日志文件会占用大量内存，且预分包阶段耗时较长。
- 建议：保存文件 offset、长度、时间索引，播放时按需 seek 读取；必要时对索引做轻量缓存。

### PERF-05：C/N0 图每次渲染完整清轴并重建所有柱、文字、国旗对象

- 位置：`main.py`，`CNoPlotCanvas.render_cno()`。
- 现象：每次调用都会 `ax.clear()`、重新创建 bar/text/AnnotationBbox，并执行 `tight_layout()`。
- 影响：卫星通道较多时，即使已有 2Hz 限频，resize 或实时刷新仍可能卡顿。
- 建议：短期可跳过无变化数据的重绘；中期可复用 bar/text artist，仅更新高度、颜色和标签。

### PERF-06：报告导出强制渲染所有图表，可能阻塞 UI

- 位置：`main.py`，`on_export_report_clicked()`。
- 现象：导出 Word 前同步调用 5 个 canvas 的 `render_data()` 和 `savefig()`。
- 影响：大数据集下报告导出期间主界面明显冻结。
- 建议：用进度对话框分阶段提示；必要时放到后台线程生成图片，但 Qt/Matplotlib 线程安全需要谨慎设计。

### PERF-07：绘图 downsample 阈值偏高，10 万点以内仍全量绘制 marker/line

- 位置：`plot_widget.py`，`PlotWidget.downsample_threshold = 100000`。
- 现象：10 万点以内直接绘制完整曲线；5 千点以内还显示 marker。
- 影响：中大型日志切换 tab、缩放窗口、导出报告时绘制耗时明显。
- 建议：根据画布像素宽度动态降采样，而不是固定 10 万点阈值；marker 阈值也可按屏幕密度动态决定。

### PERF-08：配置保存每次完整写 JSON，坐标历史增长后仍无上限

- 位置：`main.py`，`save_config()` / `add_coordinate_to_history()`。
- 影响：当前风险较低，但长期使用后配置文件和下拉列表可能膨胀。
- 建议：限制坐标历史最大数量，例如 20 或 50 条。

## 4. 建议处理顺序

1. 优先修复 BUG-01、BUG-02、BUG-03：分别影响 C/N0 功能完整性、跨天统计正确性、高倍速回放数据完整性。
2. 随后处理 BUG-06、BUG-07：导出一致性和录制可靠性。
3. 性能优化优先做 PERF-01、PERF-02、PERF-04：投入较小，收益较明显。
4. PERF-05、PERF-06、PERF-07 涉及绘图策略，建议单独设计并用大日志压测验证。

## 5. 风险说明

- 本报告基于静态走读，未构造样例日志进行复现。
- 部分回放行为涉及产品语义：例如“seek 后是否应恢复累计轨迹”。如果现有设计只要求显示目标块即时状态，则 BUG-04 可降级为交互说明问题。
- 涉及跨午夜的修复会影响统计、绘图、导出三条链路，建议先补测试用例再改代码。
