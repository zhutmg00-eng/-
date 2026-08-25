"""碳资产盘点报告生成器（PDF）

使用 reportlab 生成专业碳资产盘点报告，包含封面、执行摘要、
分车型排放明细、配额与成本分析、政策建议等章节。
"""
import os
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ============================================================
# 中文字体注册
# ============================================================
FONT_REGISTERED = False
FONT_NAME = "Helvetica"  # 默认 fallback

_FONT_PATHS = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "msyh.ttc"),
    os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "simsun.ttc"),
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _register_chinese_font():
    """尝试注册中文字体，失败则回退到 Helvetica"""
    global FONT_REGISTERED, FONT_NAME

    for fpath in _FONT_PATHS:
        if os.path.exists(fpath):
            try:
                # 注册字体名
                pdfmetrics.registerFont(TTFont("ChinaFont", fpath))
                FONT_NAME = "ChinaFont"
                FONT_REGISTERED = True
                return
            except Exception:
                continue

    # 字体注册失败，记录标记
    FONT_NAME = "Helvetica"
    FONT_REGISTERED = False


# 初始化注册
_register_chinese_font()

# ============================================================
# 样式定义
# ============================================================
_FONT = FONT_NAME


def _make_styles():
    """返回自定义段落样式"""
    styles = getSampleStyleSheet()

    # 封面标题样式
    styles.add(ParagraphStyle(
        name="CoverTitle",
        fontName=_FONT,
        fontSize=28,
        leading=36,
        alignment=TA_CENTER,
        spaceAfter=20,
    ))

    # 封面副标题
    styles.add(ParagraphStyle(
        name="CoverSub",
        fontName=_FONT,
        fontSize=14,
        leading=20,
        alignment=TA_CENTER,
        spaceAfter=10,
        textColor=HexColor("#555555"),
    ))

    # 一级标题
    styles.add(ParagraphStyle(
        name="SectionTitle",
        fontName=_FONT,
        fontSize=16,
        leading=22,
        spaceBefore=12,
        spaceAfter=8,
        textColor=HexColor("#1B5E20"),
        borderPadding=(0, 0, 2, 0),
    ))

    # 二级标题
    styles.add(ParagraphStyle(
        name="SubSectionTitle",
        fontName=_FONT,
        fontSize=13,
        leading=18,
        spaceBefore=8,
        spaceAfter=4,
        textColor=HexColor("#333333"),
    ))

    # 正文
    styles.add(ParagraphStyle(
        name="BodyTextCN",
        fontName=_FONT,
        fontSize=10,
        leading=16,
        alignment=TA_LEFT,
        spaceAfter=4,
    ))

    # 表格标题
    styles.add(ParagraphStyle(
        name="TableCaption",
        fontName=_FONT,
        fontSize=10,
        leading=14,
        spaceBefore=6,
        spaceAfter=4,
        textColor=HexColor("#666666"),
    ))

    return styles


# ============================================================
# 表格辅助函数
# ============================================================
_HEADER_BG = HexColor("#2E7D32")
_HEADER_FG = white
_ROW_BG = HexColor("#F1F8E9")
_ROW_ALT_BG = white
_TEXT_FG = HexColor("#333333")


def _build_table_style(col_count=5):
    """返回通用表格样式"""
    style_cmds = [
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#C8E6C9")),
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), _HEADER_FG),
        ("FONTNAME", (0, 0), (-1, 0), _FONT),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTNAME", (0, 1), (-1, -1), _FONT),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_ROW_BG, _ROW_ALT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    return style_cmds


def _fmt_number(val, decimals=2):
    """格式化数字"""
    if val is None:
        return "-"
    return f"{val:,.{decimals}f}"


# ============================================================
# 页眉页脚（闭包形式，捕获 company_name）
# ============================================================
def _make_page_callbacks(company_name):
    """创建页眉页脚回调函数"""
    def _footer(canvas, doc):
        """页脚：页码"""
        canvas.saveState()
        canvas.setFont(_FONT, 8)
        canvas.setFillColor(HexColor("#999999"))
        page_text = f"第 {doc.page} 页"
        canvas.drawCentredString(A4[0] / 2, 15 * mm, page_text)
        canvas.restoreState()

    def _header(canvas, doc):
        """页眉：企业名称"""
        canvas.saveState()
        canvas.setFont(_FONT, 8)
        canvas.setFillColor(HexColor("#1B5E20"))
        left_text = company_name or ""
        canvas.drawString(15 * mm, A4[1] - 12 * mm, left_text)
        canvas.restoreState()

    return _header, _footer


# ============================================================
# 报告生成核心函数
# ============================================================
def generate_carbon_report(
    company_name: str,
    total_emission_t: float,
    total_vehicles: int,
    emission_by_type: dict,
    total_quota_t: float,
    gap_t: float,
    gap_status: str,
    compliance_cost: dict,
    llm_answer: str = "",
    output_path: str = None,
) -> str:
    """
    生成碳资产盘点 PDF 报告

    Args:
        company_name: 企业名称
        total_emission_t: 总排放量（吨CO₂）
        total_vehicles: 总车辆数
        emission_by_type: 分车型排放明细 dict
        total_quota_t: 总配额（吨CO₂）
        gap_t: 配额缺口（正=缺口，负=盈余）
        gap_status: 缺口状态字符串
        compliance_cost: 合规成本估算 dict
        llm_answer: 政策建议（可选）
        output_path: 输出路径（可选）

    Returns:
        生成的 PDF 文件路径
    """
    # ---- 输出路径 ----
    if output_path is None:
        from src.config import DATA_DIR
        reports_dir = DATA_DIR / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        safe_name = (company_name or "企业").replace("/", "_")
        output_path = str(reports_dir / f"{safe_name}_报告_{date_str}.pdf")

    # ---- 构建 PDF ----
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
    )

    styles = _make_styles()
    elements = []
    width = A4[0] - 36 * mm  # 可用内容宽度

    # ---- 中文不可用提示 ----
    if not FONT_REGISTERED:
        elements.append(Paragraph(
            "（中文暂用英文字体渲染）",
            ParagraphStyle("Note", fontName="Helvetica", fontSize=8, textColor=HexColor("#999999")),
        ))
        elements.append(Spacer(1, 10 * mm))

    # ============================================================
    # 第1页 封面
    # ============================================================
    elements.append(Spacer(1, 60 * mm))
    elements.append(Paragraph("碳资产盘点报告", styles["CoverTitle"]))
    elements.append(Spacer(1, 15 * mm))
    elements.append(HRFlowable(width="60%", thickness=1, color=HexColor("#2E7D32")))
    elements.append(Spacer(1, 20 * mm))
    elements.append(Paragraph(f"企业名称：{company_name}", styles["CoverSub"]))
    elements.append(Paragraph(f"报告日期：{datetime.now().strftime('%Y年%m月%d日')}", styles["CoverSub"]))
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph(f"总排放量：{_fmt_number(total_emission_t)} tCO₂", styles["CoverSub"]))
    elements.append(Paragraph(f"总车辆数：{total_vehicles} 辆", styles["CoverSub"]))
    elements.append(Spacer(1, 60 * mm))
    elements.append(Paragraph(
        "本报告由碳资产管理与合规决策助手自动生成",
        ParagraphStyle("Footer", fontName=_FONT, fontSize=9, textColor=HexColor("#999999"), alignment=TA_CENTER),
    ))
    elements.append(PageBreak())

    # ============================================================
    # 第2页 执行摘要
    # ============================================================
    elements.append(Paragraph("一、执行摘要", styles["SectionTitle"]))
    elements.append(Spacer(1, 6 * mm))

    # 核心指标表格
    core_data = [
        ["指标", "数值"],
        ["年度碳排放总量", f"{_fmt_number(total_emission_t)} tCO₂"],
        ["总车辆数", f"{total_vehicles} 辆"],
        ["碳配额总量", f"{_fmt_number(total_quota_t)} tCO₂"],
        ["配额缺口/盈余", f"{_fmt_number(gap_t)} tCO₂（{gap_status}）"],
    ]

    # 合规成本核心指标
    cost_title = compliance_cost.get("合规需求", "")
    if cost_title == "需购买配额":
        core_data.append(["预估合规成本（参考价）", f"{_fmt_number(compliance_cost.get('预估合规成本_参考价', 0), 0)} 元"])
        core_data.append(["参考碳价", f"{_fmt_number(compliance_cost.get('当前碳价_元每吨', 0))} 元/tCO₂"])
    elif cost_title == "配额盈余":
        core_data.append(["预估收益区间", f"{_fmt_number(compliance_cost.get('预估收益_low', 0), 0)} ~ {_fmt_number(compliance_cost.get('预估收益_high', 0), 0)} 元"])
    else:
        core_data.append(["合规成本", "暂无数据"])

    t = Table(core_data, colWidths=[3.5 * cm, width - 3.5 * cm])
    t.setStyle(_build_table_style(2))
    elements.append(t)
    elements.append(Spacer(1, 8 * mm))

    # 关键结论
    if gap_t > 0:
        elements.append(Paragraph(
            f"<b>结论：</b>企业当前存在 <b>{_fmt_number(gap_t)} tCO₂</b> 的配额缺口，"
            f"需通过购买配额或实施减排措施来满足合规要求。",
            styles["BodyTextCN"],
        ))
    elif gap_t < 0:
        elements.append(Paragraph(
            f"<b>结论：</b>企业当前存在 <b>{_fmt_number(abs(gap_t))} tCO₂</b> 的配额盈余，"
            f"可在碳市场出售盈余配额获取收益。",
            styles["BodyTextCN"],
        ))
    else:
        elements.append(Paragraph(
            "<b>结论：</b>企业当前配额与排放基本平衡。",
            styles["BodyTextCN"],
        ))

    elements.append(PageBreak())

    # ============================================================
    # 第3页 分车型排放明细
    # ============================================================
    elements.append(Paragraph("二、分车型排放明细", styles["SectionTitle"]))
    elements.append(Spacer(1, 6 * mm))

    emission_data = [["车型", "排放量 (tCO₂)", "占比 (%)", "车辆数 (辆)", "排放因子 (kg/km)"]]
    for vtype, info in emission_by_type.items():
        emission_data.append([
            vtype,
            f"{_fmt_number(info.get('排放量_tCO2', 0))}",
            f"{info.get('占比', 0)}",
            str(info.get("车辆数", 0)),
            f"{info.get('排放因子_kg_per_km', 0)}",
        ])

    t2 = Table(emission_data, colWidths=[3 * cm, 2.5 * cm, 1.8 * cm, 2 * cm, 2.7 * cm])
    t2.setStyle(_build_table_style(5))
    elements.append(t2)
    elements.append(Spacer(1, 8 * mm))

    # 按燃料类型分组说明
    fuel_groups = {}
    for vtype, info in emission_by_type.items():
        fuel = info.get("燃料类型", "未知")
        if fuel not in fuel_groups:
            fuel_groups[fuel] = {"排放量": 0, "车辆数": 0}
        fuel_groups[fuel]["排放量"] += info.get("排放量_tCO2", 0)
        fuel_groups[fuel]["车辆数"] += info.get("车辆数", 0)

    if fuel_groups and total_emission_t > 0:
        elements.append(Paragraph("按燃料类型汇总", styles["SubSectionTitle"]))
        fuel_data = [["燃料类型", "排放量 (tCO₂)", "占比 (%)", "车辆数 (辆)"]]
        for fuel, vals in fuel_groups.items():
            fuel_data.append([
                fuel,
                f"{_fmt_number(vals['排放量'])}",
                f"{round(vals['排放量'] / total_emission_t * 100, 1)}",
                str(vals["车辆数"]),
            ])
        t3 = Table(fuel_data, colWidths=[3 * cm, 3 * cm, 2 * cm, 2.5 * cm])
        t3.setStyle(_build_table_style(4))
        elements.append(t3)

    elements.append(PageBreak())

    # ============================================================
    # 第4页 配额与成本分析
    # ============================================================
    elements.append(Paragraph("三、配额与成本分析", styles["SectionTitle"]))
    elements.append(Spacer(1, 6 * mm))

    # 配额对比表
    quota_data = [["项目", "数值 (tCO₂)"],
                  ["碳配额总量", f"{_fmt_number(total_quota_t)}"],
                  ["实际排放量", f"{_fmt_number(total_emission_t)}"],
                  ["配额缺口/盈余", f"{_fmt_number(gap_t)}（{gap_status}）"]]
    t4 = Table(quota_data, colWidths=[4 * cm, width - 4 * cm])
    t4.setStyle(_build_table_style(2))
    elements.append(t4)
    elements.append(Spacer(1, 8 * mm))

    # 分车型配额明细
    elements.append(Paragraph("分车型配额明细", styles["SubSectionTitle"]))

    # 从 emission_by_type 获取车辆数
    fleet_summary = {}
    for vtype, info in emission_by_type.items():
        fleet_summary[vtype] = info.get("车辆数", 0)

    # 配额基准值
    from src.engine.quota import QUOTA_BENCHMARK
    quota_detail_data = [["车型", "车辆数 (辆)", "配额基准 (t/辆)", "配额 (tCO₂)", "排放量 (tCO₂)", "差额 (tCO₂)"]]
    for vtype, info in emission_by_type.items():
        count = info.get("车辆数", 0)
        benchmark = QUOTA_BENCHMARK.get(vtype, 0)
        type_quota = count * benchmark
        type_emission = info.get("排放量_tCO2", 0)
        diff = type_quota - type_emission
        quota_detail_data.append([
            vtype,
            str(count),
            f"{_fmt_number(benchmark)}",
            f"{_fmt_number(type_quota)}",
            f"{_fmt_number(type_emission)}",
            f"{_fmt_number(diff)}",
        ])

    t5 = Table(quota_detail_data, colWidths=[3 * cm, 1.8 * cm, 2 * cm, 2 * cm, 2 * cm, 2.2 * cm])
    t5.setStyle(_build_table_style(6))
    elements.append(t5)
    elements.append(Spacer(1, 8 * mm))

    # 碳价与成本
    elements.append(Paragraph("碳价与合规成本", styles["SubSectionTitle"]))

    cost_table_data = [["指标", "数值"]]
    cost_title = compliance_cost.get("合规需求", "")
    if cost_title == "需购买配额":
        cost_table_data.append(["配额缺口", f"{_fmt_number(compliance_cost.get('配额缺口_t', gap_t))} tCO₂"])
        cost_table_data.append(["当前碳价", f"{_fmt_number(compliance_cost.get('当前碳价_元每吨', 0))} 元/tCO₂"])
        cost_table_data.append(["近90日均价", f"{_fmt_number(compliance_cost.get('近90日均价_元每吨', 0))} 元/tCO₂"])
        cost_table_data.append(["碳价波动率", compliance_cost.get("碳价波动率", "-")])
        cost_table_data.append(["预估合规成本（参考价）", f"{_fmt_number(compliance_cost.get('预估合规成本_参考价', 0), 0)} 元"])
        cost_table_data.append(["预估合规成本区间",
                                f"{_fmt_number(compliance_cost.get('预估合规成本区间_low', 0), 0)} ~ "
                                f"{_fmt_number(compliance_cost.get('预估合规成本区间_high', 0), 0)} 元"])
    elif cost_title == "配额盈余":
        cost_table_data.append(["盈余量", f"{_fmt_number(compliance_cost.get('盈余量_t', abs(gap_t)))} tCO₂"])
        cost_table_data.append(["参考碳价", f"{_fmt_number(compliance_cost.get('参考碳价_元每吨', 0))} 元/tCO₂"])
        cost_table_data.append(["预估收益区间",
                                f"{_fmt_number(compliance_cost.get('预估收益_low', 0), 0)} ~ "
                                f"{_fmt_number(compliance_cost.get('预估收益_high', 0), 0)} 元"])
    else:
        cost_table_data.append(["合规需求", cost_title])

    t6 = Table(cost_table_data, colWidths=[4 * cm, width - 4 * cm])
    t6.setStyle(_build_table_style(2))
    elements.append(t6)

    elements.append(PageBreak())

    # ============================================================
    # 第5页 政策建议（可选）
    # ============================================================
    if llm_answer and llm_answer.strip():
        elements.append(Paragraph("四、政策建议", styles["SectionTitle"]))
        elements.append(Spacer(1, 6 * mm))

        # 按段落分割
        for line in llm_answer.strip().split("\n"):
            line = line.strip()
            if line:
                elements.append(Paragraph(line, styles["BodyTextCN"]))

    # ============================================================
    # 生成 PDF
    # ============================================================
    header_cb, footer_cb = _make_page_callbacks(company_name)
    doc.build(
        elements,
        onFirstPage=header_cb,
        onLaterPages=header_cb,
    )

    return output_path
