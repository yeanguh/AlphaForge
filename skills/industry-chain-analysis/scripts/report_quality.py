#!/usr/bin/env python3
"""Validate industry-chain report artifacts before delivery.

The checker is intentionally lightweight and deterministic. It does not judge
whether an investment thesis is "right"; it checks whether the report has the
stable structure, evidence trail, visual assets, and opportunity framing that
the industry-chain-analysis skill promises.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REQUIRED_SECTIONS = [
    "核心结论",
    "研究对象、边界与口径",
    "行业背景与需求驱动",
    "产业链全景图谱",
    "上游材料、部件与制程要素挖掘",
    "产业链核心环节价值分布",
    "竞争格局与核心壁垒",
    "A股公司映射与核心地位判断",
    "投资线索、交易跟踪与目标价情景",
    "催化因素与产业传导路径",
    "风险提示",
    "数据来源、证据强度与待核验事项",
]

FORBIDDEN_REPORT_PATTERNS = [
    "公共数据适配器留痕",
    "适配器留痕",
    "render_source_trail",
    "health-check",
    "RemoteDisconnected",
    "Traceback",
    "stock_zyjs",
    "baostock",
    "adata",
]

COMPANY_MAPPING_HEADER = "| 公司 | 代码 | 环节 | 细分领域 | 产业占比/暴露度 | 核心技术/产品 | 卡脖子相关性 | 环节地位 | 证据与备注 |"
CORE_VALUE_HEADER = "| 产业链环节 | 细分领域/关键产品 | BOM成本占比/价值占比 | 核心技术壁垒 | 卡脖子程度 | 代表A股公司 | 公司环节地位 | 证据口径/备注 |"
UPSTREAM_HEADER = "| 上游层级 | 细分材料/部件 | 对目标产业的作用 | 价值/稀缺性 | 卡脖子程度 | A股候选 | 纳入主线判断 |"
OPPORTUNITY_HEADERS = [
    "| 机会类型 | 产业链逻辑 | 代表A股公司 | 验证里程碑 | 风险 |",
    "| 公司 | 代码 | 产业链结论 | 财务质量 | 当前估值 | 技术面/趋势 | 买点区间 | 止损/失效条件 | 目标价/空间 | 综合判断 |",
]
SOURCE_SUMMARY_HEADERS = [
    "| 结论/数据 | 来源 | 日期 | 置信度 |",
    "| Claim | Source | Date | Confidence |",
]

OPPORTUNITY_TERMS = [
    "投资线索",
    "利润传导",
    "受益顺序",
    "核心环节龙头",
    "关键技术突破者",
    "重要配套",
    "间接受益",
    "待验证",
]

CONCLUSION_SIGNAL_TERMS = [
    "价值",
    "核心",
    "机会",
    "风险",
    "瓶颈",
    "弹性",
    "受益",
    "不确定",
]


@dataclass
class CheckResult:
    name: str
    passed: bool
    evidence: str
    severity: str = "error"


def _headings(report_text: str) -> list[tuple[int, str]]:
    headings: list[tuple[int, str]] = []
    for line_no, line in enumerate(report_text.splitlines(), start=1):
        match = re.match(r"^##\s+\d+\.\s+(.+?)\s*$", line)
        if match:
            headings.append((line_no, match.group(1)))
    return headings


def _section_body(report_text: str, section_name: str) -> str:
    lines = report_text.splitlines()
    start: int | None = None
    end = len(lines)
    for idx, line in enumerate(lines):
        match = re.match(r"^##\s+\d+\.\s+(.+?)\s*$", line)
        if not match:
            continue
        if match.group(1) == section_name:
            start = idx + 1
            continue
        if start is not None:
            end = idx
            break
    if start is None:
        return ""
    return "\n".join(lines[start:end]).strip()


def _markdown_images(report_text: str) -> list[str]:
    return re.findall(r"!\[[^\]]*\]\(([^)]+)\)", report_text)


def _source_entries(source_data: dict[str, Any]) -> list[dict[str, Any]]:
    entries = source_data.get("sources", [])
    return entries if isinstance(entries, list) else []


def _check_sections(report_text: str) -> CheckResult:
    headings = _headings(report_text)
    heading_names = [name for _, name in headings]
    missing = [name for name in REQUIRED_SECTIONS if name not in heading_names]
    positions = [heading_names.index(name) for name in REQUIRED_SECTIONS if name in heading_names]
    ordered = positions == sorted(positions)
    passed = not missing and ordered
    evidence = "sections ok" if passed else f"missing={missing}; ordered={ordered}; headings={heading_names}"
    return CheckResult("stable_report_sections", passed, evidence)


def _check_tables(report_text: str) -> list[CheckResult]:
    return [
        CheckResult(
            "canonical_company_mapping_table",
            COMPANY_MAPPING_HEADER in report_text,
            "9-column A-share mapping header present" if COMPANY_MAPPING_HEADER in report_text else "missing canonical 9-column header",
        ),
        CheckResult(
            "core_value_distribution_table",
            CORE_VALUE_HEADER in report_text,
            "core value table header present" if CORE_VALUE_HEADER in report_text else "missing core value distribution header",
        ),
        CheckResult(
            "upstream_discovery_table",
            UPSTREAM_HEADER in report_text,
            "upstream table header present" if UPSTREAM_HEADER in report_text else "missing upstream discovery header",
        ),
    ]


def _check_visuals(report_text: str, report_path: Path) -> CheckResult:
    images = _markdown_images(report_text)
    existing: list[str] = []
    missing: list[str] = []
    for image in images:
        if image.startswith(("http://", "https://")):
            existing.append(image)
            continue
        path = Path(image)
        if not path.is_absolute():
            path = report_path.parent / path
        if path.exists() and path.stat().st_size > 0:
            existing.append(str(path))
        else:
            missing.append(str(path))
    passed = bool(existing) and not missing
    evidence = f"existing_images={existing}; missing_images={missing}"
    return CheckResult("rendered_visual_assets", passed, evidence)


def _local_image_paths(report_text: str, report_path: Path) -> list[Path]:
    paths: list[Path] = []
    for image in _markdown_images(report_text):
        if image.startswith(("http://", "https://")):
            continue
        path = Path(image)
        if not path.is_absolute():
            path = report_path.parent / path
        paths.append(path)
    return paths


def _check_image_file_quality(report_text: str, report_path: Path) -> CheckResult:
    paths = _local_image_paths(report_text, report_path)
    if not paths:
        return CheckResult("valid_image_files", False, "no local images found")
    checked: list[str] = []
    failures: list[str] = []
    try:
        from PIL import Image
    except Exception as exc:  # noqa: BLE001
        return CheckResult("valid_image_files", False, f"Pillow unavailable: {type(exc).__name__}: {exc}")

    for path in paths:
        try:
            with Image.open(path) as image:
                width, height = image.size
                image.verify()
            if width < 900 or height < 600:
                failures.append(f"{path}: too small {width}x{height}")
            else:
                checked.append(f"{path}: {width}x{height}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{path}: {type(exc).__name__}: {exc}")
    passed = bool(checked) and not failures
    return CheckResult(
        "valid_image_files",
        passed,
        f"checked={checked}; failures={failures}",
    )


def _check_relative_image_refs(report_text: str) -> CheckResult:
    images = _markdown_images(report_text)
    absolute = []
    remote = []
    outside_assets = []
    for image in images:
        if image.startswith(("http://", "https://")):
            remote.append(image)
        elif Path(image).is_absolute():
            absolute.append(image)
        elif not image.startswith("assets/"):
            outside_assets.append(image)
    passed = bool(images) and not absolute and not remote and not outside_assets
    return CheckResult(
        "relative_markdown_image_refs",
        passed,
        "all image refs are relative assets paths"
        if passed
        else f"absolute={absolute}; remote={remote}; outside_assets={outside_assets}; total_images={len(images)}",
    )


def _check_forbidden_logs(report_text: str) -> CheckResult:
    found = [pattern for pattern in FORBIDDEN_REPORT_PATTERNS if pattern in report_text]
    return CheckResult(
        "no_adapter_logs_in_report",
        not found,
        "no forbidden runtime patterns" if not found else f"found={found}",
    )


def _check_source_confidence(source_data: dict[str, Any]) -> list[CheckResult]:
    entries = _source_entries(source_data)
    high = [e for e in entries if e.get("status") == "ok" and e.get("confidence") == "High"]
    medium_or_high = [
        e for e in entries
        if e.get("status") in {"ok", "fallback"} and e.get("confidence") in {"High", "Medium"}
    ]
    primaryish = [
        e for e in entries
        if e.get("tool") in {"filing", "web", "sec-edgar", "akshare"} and e.get("status") in {"ok", "fallback"}
    ]
    return [
        CheckResult(
            "source_trail_present",
            len(entries) >= 5,
            f"source_entries={len(entries)}",
        ),
        CheckResult(
            "high_confidence_sources",
            len(high) >= 2,
            f"high_confidence_ok_sources={len(high)}",
        ),
        CheckResult(
            "medium_or_high_evidence_base",
            len(medium_or_high) >= 5,
            f"medium_or_high_sources={len(medium_or_high)}",
        ),
        CheckResult(
            "filing_or_authoritative_evidence",
            len(primaryish) >= 3,
            f"authoritative_like_sources={len(primaryish)}",
        ),
    ]


def _check_opportunity_framing(report_text: str) -> CheckResult:
    found = [term for term in OPPORTUNITY_TERMS if term in report_text]
    passed = len(found) >= 4
    return CheckResult(
        "investment_opportunity_framing",
        passed,
        f"found_terms={found}",
    )


def _check_core_conclusion_depth(report_text: str) -> CheckResult:
    body = _section_body(report_text, "核心结论")
    numbered = re.findall(r"^\s*\d+[.、]\s+", body, flags=re.MULTILINE)
    found_terms = [term for term in CONCLUSION_SIGNAL_TERMS if term in body]
    passed = len(numbered) >= 3 and len(found_terms) >= 3
    return CheckResult(
        "core_conclusion_depth",
        passed,
        f"numbered_points={len(numbered)}; signal_terms={found_terms}",
    )


def _check_opportunity_table(report_text: str) -> CheckResult:
    found = [header for header in OPPORTUNITY_HEADERS if header in report_text]
    return CheckResult(
        "investment_opportunity_table",
        bool(found),
        f"found={found}" if found else "missing opportunity table or trading follow-through table",
    )


def _check_source_summary_table(report_text: str) -> CheckResult:
    found = [header for header in SOURCE_SUMMARY_HEADERS if header in report_text]
    return CheckResult(
        "claim_level_source_summary",
        bool(found),
        f"found={found}" if found else "missing claim-level source summary table",
    )


def validate(report_path: Path, source_data_path: Path | None = None) -> dict[str, Any]:
    report_text = report_path.read_text(encoding="utf-8")
    if source_data_path is None:
        source_data_path = report_path.parent / "source_data.json"
    source_data: dict[str, Any] = {}
    if source_data_path.exists():
        source_data = json.loads(source_data_path.read_text(encoding="utf-8"))

    checks: list[CheckResult] = [
        _check_sections(report_text),
        _check_core_conclusion_depth(report_text),
        _check_visuals(report_text, report_path),
        _check_image_file_quality(report_text, report_path),
        _check_relative_image_refs(report_text),
        _check_forbidden_logs(report_text),
        _check_opportunity_framing(report_text),
        _check_opportunity_table(report_text),
        _check_source_summary_table(report_text),
        *_check_tables(report_text),
        *_check_source_confidence(source_data),
    ]
    score = sum(1 for check in checks if check.passed)
    passed = all(check.passed or check.severity == "warning" for check in checks)
    return {
        "report": str(report_path),
        "source_data": str(source_data_path),
        "passed": passed,
        "score": score,
        "total": len(checks),
        "checks": [asdict(check) for check in checks],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate industry-chain report quality.")
    parser.add_argument("report", help="Path to report.md")
    parser.add_argument("--source-data", help="Path to source_data.json; defaults to report directory.")
    parser.add_argument("--output", help="Optional path to write quality_report.json")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = validate(Path(args.report), Path(args.source_data) if args.source_data else None)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
