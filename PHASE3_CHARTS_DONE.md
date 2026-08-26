# Phase 3 — 可视化组件已完成 ✅

> 历史记录：当前“模拟碳预算/情景成本”口径及验证状态以 `README.md` 和 `HANDOVER.md` 为准。

**日期**: 2026-08-25

## 创建的文件

### `src/ui/components/charts.py`
基于 plotly 的图表绘制模块，包含 4 个图表函数：

| 函数 | 说明 |
|------|------|
| `plot_emission_pie(emission_by_type)` | 各车型碳排放占比环形图（绿色系配色） |
| `plot_quota_comparison(total_emission, total_quota, gap)` | 直接运营排放/模拟预算/差额柱状图对比 |
| `plot_carbon_price_stats(price_stats)` | 碳价水平线对比图（当前价/90日均价/最高/最低） |
| `plot_fleet_comparison(multi_results)` | 多企业分组柱状图对比 |

### `src/ui/components/__init__.py`
导出组件模块，方便 `from src.ui.components import *` 使用。

## 技术细节
- 文件顶部包含 `from __future__ import annotations`
- 所有函数均有中文 docstring
- 使用 `plotly.graph_objects`（go）创建 figure
- 环形图使用绿色系 `GREEN_PALETTE`
- 差额用红色（超出预算）/ 橙色（低于预算）区分
- 碳价图返回 `go.Figure | None`（空数据返回 None）
