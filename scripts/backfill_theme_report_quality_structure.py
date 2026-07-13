from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loop_os.domain.report_review_agent import review_report_text  # noqa: E402


VALUE_HEADER = (
    "产业链环节",
    "细分领域/关键产品",
    "BOM成本占比/价值占比",
    "核心技术壁垒",
    "卡脖子程度",
    "代表A股公司",
    "公司环节地位",
    "证据口径/备注",
)
MAPPING_HEADER = (
    "公司",
    "代码",
    "环节",
    "细分领域",
    "产业占比/暴露度",
    "核心技术/产品",
    "卡脖子相关性",
    "环节地位",
    "证据与备注",
)
BOTTLENECK_HEADER = ("候选环节", "不可替代", "供给刚性", "寡头垄断", "机构低配", "反证条件")
SOURCE_HEADER = ("结论/数据", "来源", "日期", "置信度")
CHAIN_HEADER = ("环节", "事实映射", "供需变化方向", "瓶颈/卡口", "A股映射")
BATTLE_HEADER = ("瓶颈节点", "当前三家核心公司", "为什么卡", "升级信号", "反证信号", "节点结论")
VALUATION_HEADER = ("公司", "代码", "产业链位置", "当前估值", "财务/订单信号", "催化", "买点条件", "失效条件")
CORE_TRACKING_HEADER = ("公司", "代码", "产业链位置", "估值", "财务质量", "趋势结构", "关键位", "买入条件", "止损/失效", "卖出/目标")
CHOKEPOINT_HEADER = ("公司", "代码", "卡口环节", "直接性", "财务信号", "研报/公告信号", "估值压力", "反证条件")


@dataclass(frozen=True)
class BackfillResult:
    path: Path
    changed: bool
    inserted: tuple[str, ...]


def _split_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _is_separator(line: str) -> bool:
    cells = _split_row(line)
    return bool(cells) and all(set(cell.replace(":", "").strip()) <= {"-"} and "-" in cell for cell in cells)


def _find_table(text: str, header: tuple[str, ...], *, min_matches: int | None = None) -> list[dict[str, str]]:
    min_matches = min_matches if min_matches is not None else len(header)
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        columns = _split_row(line)
        if sum(1 for column in header if column in columns) < min_matches:
            continue
        if idx + 1 >= len(lines) or not _is_separator(lines[idx + 1]):
            continue
        rows: list[dict[str, str]] = []
        pos = idx + 2
        while pos < len(lines) and lines[pos].lstrip().startswith("|"):
            cells = _split_row(lines[pos])
            if len(cells) >= 2:
                rows.append({columns[i]: cells[i] if i < len(cells) else "" for i in range(len(columns))})
            pos += 1
        return rows
    return []


def _has_header(text: str, header: tuple[str, ...], *, min_matches: int | None = None) -> bool:
    return bool(_find_table(text, header, min_matches=min_matches))


def _table(header: tuple[str, ...], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in rows:
        cleaned = [cell.replace("\n", " ").replace("|", "/").strip() or "待核验" for cell in row]
        lines.append("| " + " | ".join(cleaned) + " |")
    return "\n".join(lines)


def _company_names(value: str) -> list[str]:
    names: list[str] = []
    for raw in value.replace("/", "、").replace("，", "、").replace(",", "、").split("、"):
        name = raw.strip()
        if name and name not in names:
            names.append(name)
    return names


def _bottleneck_degree(barrier: str, conclusion: str = "") -> str:
    text = barrier + conclusion
    if any(token in text for token in ("绝对核心", "High", "高", "卡口", "瓶颈", "供给刚性", "认证", "良率")):
        return "高"
    if any(token in text for token in ("Medium", "中", "重要")):
        return "中"
    return "待核验"


def build_value_distribution(text: str) -> str | None:
    rows = _find_table(text, CHAIN_HEADER)
    if not rows:
        return None
    rendered_rows: list[list[str]] = []
    for row in rows:
        barrier = row.get("瓶颈/卡口", "")
        reps = row.get("A股映射", "")
        rendered_rows.append(
            [
                row.get("环节", "待核验"),
                row.get("事实映射", "待核验"),
                f"价值占比待核验；供需方向：{row.get('供需变化方向', '待核验')}",
                barrier or "待核验",
                _bottleneck_degree(barrier),
                reps or "待核验",
                "卡口候选/重要配套，需用收入占比、订单和客户认证继续校验",
                "结构化回填；证据来自本报告既有产业链跟踪表。",
            ]
        )
    return "### 产业链核心环节价值分布\n\n" + _table(VALUE_HEADER, rendered_rows)


def build_bottleneck_standards(text: str) -> str | None:
    rows = _find_table(text, BATTLE_HEADER, min_matches=5)
    if not rows:
        return None
    rendered_rows: list[list[str]] = []
    for row in rows:
        why = row.get("为什么卡", "")
        conclusion = row.get("节点结论", "")
        signal = row.get("升级信号", "")
        rendered_rows.append(
            [
                row.get("瓶颈节点", "待核验"),
                "客户认证/设计绑定/可靠性要求待继续核验；" + why,
                "扩产、良率、交期或交付弹性待继续核验；" + why,
                "供应集中度待继续核验；当前核心公司：" + row.get("当前三家核心公司", "待核验"),
                "估值、覆盖和持仓拥挤度待继续核验；升级信号：" + signal,
                row.get("反证信号", "") or "替代路线成熟、客户切换、产能过剩或毛利压缩。",
            ]
        )
    return "### 四标准瓶颈校验\n\n" + _table(BOTTLENECK_HEADER, rendered_rows)


def _mapping_source_rows(text: str) -> list[dict[str, str]]:
    for header in (VALUATION_HEADER, CORE_TRACKING_HEADER, CHOKEPOINT_HEADER):
        rows = _find_table(text, header, min_matches=6)
        if rows:
            return rows
    return []


def _battle_index(text: str) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for row in _find_table(text, BATTLE_HEADER, min_matches=5):
        node = row.get("瓶颈节点", "")
        for name in _company_names(row.get("当前三家核心公司", "")):
            index[name] = row
        if node:
            index[node] = row
    return index


def build_company_mapping(text: str) -> str | None:
    rows = _mapping_source_rows(text)
    if not rows:
        return None
    battle = _battle_index(text)
    rendered_rows: list[list[str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        company = row.get("公司", "")
        code = row.get("代码", "")
        if not company or not code or (company, code) in seen:
            continue
        seen.add((company, code))
        link = row.get("产业链位置") or row.get("卡口环节") or "待核验"
        battle_row = battle.get(company) or battle.get(link) or {}
        invalidation = row.get("失效条件") or row.get("止损/失效") or row.get("反证条件") or battle_row.get("反证信号", "")
        evidence = row.get("财务/订单信号") or row.get("财务质量") or row.get("研报/公告信号") or "待用公告、财报或订单继续核验"
        rendered_rows.append(
            [
                company,
                code,
                link,
                link,
                "已进入本报告跟踪池；精确收入/订单占比待公告或财报核验",
                link,
                _bottleneck_degree(battle_row.get("为什么卡", ""), battle_row.get("节点结论", "")),
                battle_row.get("节点结论") or row.get("直接性") or "核心/配套地位待继续校验",
                f"结构化回填；既有证据：{evidence}；反证/失效：{invalidation or '待补充可观察反证'}",
            ]
        )
    if not rendered_rows:
        return None
    return "### A股公司映射与核心地位判断\n\n" + _table(MAPPING_HEADER, rendered_rows)


def build_source_summary(text: str) -> str | None:
    source_rows = _find_table(text, ("事实类型", "硬事实/线索", "来源", "证据强度"), min_matches=3)
    rendered_rows: list[list[str]] = []
    for row in source_rows[:12]:
        rendered_rows.append(
            [
                row.get("硬事实/线索") or row.get("事实类型") or "报告既有事实线索",
                row.get("来源") or "本报告既有来源表",
                row.get("数值/时间") or "待核验",
                row.get("证据强度") or "Medium",
            ]
        )
    if not rendered_rows:
        rendered_rows = [["结构化回填表格", "本报告既有产业链、估值、瓶颈与来源章节", "报告日期", "Medium"]]
    return "### Claim-level 来源摘要\n\n" + _table(SOURCE_HEADER, rendered_rows)


def _insert_after_section(text: str, section_title: str, block: str) -> str:
    marker = f"\n## {section_title}"
    idx = text.find(marker)
    if idx == -1:
        return text.rstrip() + "\n\n" + block.rstrip() + "\n"
    next_idx = text.find("\n## ", idx + len(marker))
    if next_idx == -1:
        return text.rstrip() + "\n\n" + block.rstrip() + "\n"
    return text[:next_idx].rstrip() + "\n\n" + block.rstrip() + "\n" + text[next_idx:]


def _insert_before_section(text: str, section_title: str, block: str) -> str:
    marker = f"\n## {section_title}"
    idx = text.find(marker)
    if idx == -1:
        return text.rstrip() + "\n\n" + block.rstrip() + "\n"
    return text[:idx].rstrip() + "\n\n" + block.rstrip() + "\n" + text[idx:]


def backfill_text(text: str, *, root: Path, report_path: Path, theme_key: str) -> tuple[str, tuple[str, ...]]:
    inserted: list[str] = []
    review = review_report_text(root=root, text=text, report_path=report_path, theme_key=theme_key)
    titles = {finding["title"] for finding in review["findings"]}
    new_text = text

    if "缺少核心环节价值分布表" in titles and not _has_header(new_text, VALUE_HEADER, min_matches=6):
        block = build_value_distribution(new_text)
        if block:
            new_text = _insert_after_section(new_text, "产业链跟踪", block)
            inserted.append("value_distribution")

    if "瓶颈判断缺少四标准校验" in titles:
        block = build_bottleneck_standards(new_text)
        if block:
            new_text = _insert_after_section(new_text, "投资机会挖掘", block)
            inserted.append("bottleneck_standards")

    if "缺少A股九列公司映射表" in titles and not _has_header(new_text, MAPPING_HEADER):
        block = build_company_mapping(new_text)
        if block:
            new_text = _insert_before_section(new_text, "核心个股交易跟踪", block)
            inserted.append("company_mapping")

    if "证据强度缺少 claim-level 来源表" in titles and not _has_header(new_text, SOURCE_HEADER):
        block = build_source_summary(new_text)
        if block:
            new_text = _insert_after_section(new_text, "数据来源与证据强度", block)
            inserted.append("source_summary")

    return new_text, tuple(inserted)


def backfill_report(path: Path, *, root: Path = ROOT, dry_run: bool = False) -> BackfillResult:
    text = path.read_text(encoding="utf-8")
    theme_key = path.parent.name
    new_text, inserted = backfill_text(text, root=root, report_path=path, theme_key=theme_key)
    changed = new_text != text
    if changed and not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return BackfillResult(path=path, changed=changed, inserted=inserted)


def theme_report_paths(root: Path = ROOT) -> list[Path]:
    return sorted((root / "reports" / "themes").glob("*/report.md"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill machine-reviewable quality structures into canonical theme reports.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files.")
    parser.add_argument("reports", nargs="*", type=Path, help="Specific report.md paths. Defaults to reports/themes/*/report.md.")
    args = parser.parse_args(argv)

    paths = args.reports or theme_report_paths(ROOT)
    for path in paths:
        result = backfill_report(path, root=ROOT, dry_run=args.dry_run)
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        status = "changed" if result.changed else "ok"
        suffix = f" ({', '.join(result.inserted)})" if result.inserted else ""
        print(f"{status}: {rel}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
