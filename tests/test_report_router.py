import tempfile
import unittest
from pathlib import Path

from loop_os.report_router import (
    CHANGE_LOG_NAME,
    LOOP_LOG_HEADER,
    WATCH_POOL_HEADER,
    REVISION_HEADER,
    STRENGTH_MAIN_THRESHOLD,
    resolve_theme_key,
    theme_tier,
    route_cycle_reports,
)


def _strong_payload(**overrides):
    """A cycle payload whose candidate strength clears STRENGTH_MAIN_THRESHOLD."""
    payload = {
        "run_id": "run-A",
        "cycle": 1,
        "status": "ok",
        "started_at": "2026-07-09T00:00:00+00:00",
        "finished_at": "2026-07-09T00:05:00+00:00",
        "errors": [],
        "evidence_ids": [f"ev-{i}" for i in range(8)],
        "industry_reports": [
            {"org": "券商A", "title": "机器人减速器深度"},
            {"org": "券商B", "title": "丝杠国产替代"},
        ],
        "news": {"headlines": [{"source": "S1", "title": "人形机器人量产提速"}]},
        "agent_review": {
            "roles": ["bull", "bear"],
            "reason": "产业链进入订单验证期",
            "next_actions": ["核验收入占比", "补估值分位"],
        },
        "stock_supplements": {
            "600519": {
                "symbol": "600519",
                "fundamental": {},
                "fund_flow": {},
                "dragon_tiger": {"rows": []},
                "catalysts": ["Q1营收+43%"],
                "risks": ["估值偏高"],
            }
        },
        "research_pipeline": {
            "selected_industry_chain": {
                "selected_theme": "ai_physical_ai",
                "score": 34,
                "stage": "industry-chain-mapper",
                "next_verifications": ["验证订单来源"],
                "bottleneck_screen": {
                    "candidates": [
                        {"link": "精密传动", "companies": "绿的谐波", "invalidation": "订单不及预期"}
                    ]
                },
            },
            "stock_analyzer": [
                {
                    "symbol": "600519",
                    "name": "贵州茅台",
                    "business_model": "白酒龙头",
                    "valuation": {"pe": 18.1, "pb": 6.4, "band": "normal", "score": 4, "method": "PE/PB snapshot"},
                    "catalyst": [],
                    "risk": [],
                }
            ],
            "trade_decision_engine": {
                "decisions": [
                    {"symbol": "600519", "action": "watch", "passed_conditions": 5, "min_risk_reward": 2.0}
                ]
            },
            "company_mapping": {"600519": "sample"},
        },
    }
    payload.update(overrides)
    return payload


class ReportRouterTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        # 方案 A:themes 统一取代 industry。预置一份已迁移的人工正文主题报告,
        # loop 应在其正文之上追加证据日志 / 观察池 / 判断修正,而永不覆盖人工正文。
        self.theme_report = self.root / "reports" / "themes" / "physical-ai" / "report.md"
        self.theme_report.parent.mkdir(parents=True)
        self.theme_report.write_text(
            "# Physical AI 主题最终报告\n\n## 0. 核心结论\n\n人工撰写的正文结论。\n",
            encoding="utf-8",
        )
        # 遗留 industry 报告:方案 A 下已迁移为来源,日常 loop 绝不触碰它(验证 loop 不写 industry)
        ind = self.root / "reports" / "industry" / "physical-ai-chain-analysis-2026-07-09"
        ind.mkdir(parents=True)
        (ind / "report.md").write_text(
            "# 物理AI产业链报告(人工深度版)\n\n## 0. 核心结论\n\n产业链人工正文。\n",
            encoding="utf-8",
        )
        self.legacy_industry_report = ind / "report.md"
        # cycle dir must live under root for update_rolling_report's relative_to()
        self.cycle_dir = self.root / "runs" / "run-A" / "cycle-001"
        self.cycle_dir.mkdir(parents=True)
        (self.cycle_dir / "report.md").write_text("# 单轮候选报告\n\n过程内容。\n", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # -- 主题解析:alias / tier --
    def test_theme_resolution_and_tier(self) -> None:
        self.assertEqual(resolve_theme_key("ai_physical_ai"), "physical-ai")
        self.assertEqual(theme_tier("physical-ai"), "core")
        self.assertEqual(theme_tier("quantum-computing"), "emerging")
        self.assertEqual(theme_tier("edge-ai"), "watch")
        self.assertIsNone(resolve_theme_key(""))

    # -- 失败轮次只留在 runs/ --
    def test_failed_cycle_writes_no_final_report(self) -> None:
        payload = _strong_payload(status="error", errors=["boom"])
        res = route_cycle_reports(root=self.root, payload=payload, cycle_dir=self.cycle_dir, issues=["status=error"])
        self.assertEqual(res["routed"], [])
        self.assertTrue(res["skipped"])
        self.assertEqual(res["skipped"][0]["reason"], "failed_cycle_stays_in_runs")
        # 主题报告仍是人工正文,失败轮次不得追加证据日志
        body = self.theme_report.read_text(encoding="utf-8")
        self.assertIn("人工撰写的正文结论", body)
        self.assertNotIn(LOOP_LOG_HEADER, body)
        self.assertFalse((self.root / "reports" / "stocks").exists() and any((self.root / "reports" / "stocks").iterdir()))

    def test_blocking_issue_treated_as_failed(self) -> None:
        payload = _strong_payload()
        res = route_cycle_reports(
            root=self.root, payload=payload, cycle_dir=self.cycle_dir, issues=["agent_review_not_usable"]
        )
        self.assertEqual(res["routed"], [])

    # -- 强证据 -> themes 主题报告 + 个股 + 周报,日志进入 change log --
    def test_strong_cycle_routes_to_final_reports(self) -> None:
        payload = _strong_payload()
        res = route_cycle_reports(root=self.root, payload=payload, cycle_dir=self.cycle_dir, issues=[])
        self.assertGreaterEqual(res["strength"], STRENGTH_MAIN_THRESHOLD)
        self.assertFalse(res["to_watch_pool"])
        self.assertEqual(res["theme_key"], "physical-ai")
        self.assertEqual(res["tier"], "core")
        scopes = {r.get("scope") for r in res["routed"]}
        self.assertIn("theme:physical-ai", scopes)
        self.assertIn("stock:600519", scopes)
        self.assertIn("weekly", scopes)

        # theme: 人工正文保留;loop 日志进入旁路 change log,不污染最终报告
        th = self.theme_report.read_text(encoding="utf-8")
        self.assertIn("人工撰写的正文结论", th)  # 人工正文被保留,不被覆盖
        self.assertNotIn(LOOP_LOG_HEADER, th)
        self.assertNotIn(WATCH_POOL_HEADER, th)
        change_log = self.theme_report.with_name(CHANGE_LOG_NAME).read_text(encoding="utf-8")
        self.assertIn(LOOP_LOG_HEADER, change_log)
        self.assertNotIn(WATCH_POOL_HEADER, change_log)
        self.assertIn("ai_physical_ai", change_log)

        # 方案 A:遗留 reports/industry/ 已迁移,日常 loop 绝不再触碰(人工深度版原样保留)
        legacy = self.legacy_industry_report.read_text(encoding="utf-8")
        self.assertIn("产业链人工正文", legacy)
        self.assertNotIn(LOOP_LOG_HEADER, legacy)

        # 个股最终报告
        stock = self.root / "reports" / "stocks" / "600519" / "report.md"
        self.assertTrue(stock.exists())
        stext = stock.read_text(encoding="utf-8")
        self.assertIn("贵州茅台", stext)
        self.assertNotIn("PE 18.1", stext)
        stock_log = stock.with_name(CHANGE_LOG_NAME).read_text(encoding="utf-8")
        self.assertIn("PE 18.1", stock_log)

        # 周报累积文件
        weekly = self.root / "reports" / "weekly" / "2026-W28.md"
        self.assertTrue(weekly.exists())
        weekly_log = self.root / "reports" / "weekly" / "2026-W28_change_log.md"
        self.assertIn("复核结论", weekly_log.read_text(encoding="utf-8"))

        # daily 降级为增量 inbox
        inbox = self.root / "reports" / "daily" / "latest-full-loop.md"
        self.assertTrue(inbox.exists())

    def test_new_theme_report_seeds_benchmark_research_frame(self) -> None:
        payload = _strong_payload()
        payload["research_pipeline"]["selected_industry_chain"]["selected_theme"] = "ai_compute_infra"
        report = self.root / "reports" / "themes" / "ai-compute-infra" / "report.md"

        route_cycle_reports(root=self.root, payload=payload, cycle_dir=self.cycle_dir, issues=[])

        text = report.read_text(encoding="utf-8")
        self.assertIn("## 一句话结论", text)
        self.assertIn("## 市场盘点", text)
        self.assertIn("### 产能变化", text)
        self.assertIn("## 产业链跟踪", text)
        self.assertIn("## 投资机会挖掘", text)
        self.assertIn("## A股可交易标的估值对比", text)
        self.assertNotIn(LOOP_LOG_HEADER, text)
        self.assertIn(LOOP_LOG_HEADER, report.with_name(CHANGE_LOG_NAME).read_text(encoding="utf-8"))

    def test_theme_report_absorbs_better_deep_draft_sections(self) -> None:
        payload = _strong_payload()
        payload["research_pipeline"]["selected_industry_chain"]["selected_theme"] = "ai_compute_infra"
        payload["theme_deep_report"] = {"draft": "runs/run-A/cycle-001/deep-draft.md", "returncode": 0}
        report = self.root / "reports" / "themes" / "ai-compute-infra" / "report.md"
        report.parent.mkdir(parents=True)
        report.write_text(
            "# AI 算力基础设施主题最终报告\n\n"
            "## 研究课题\n\n待补:旧占位。\n\n"
            "## 一句话结论\n\n待补:旧占位。\n\n"
            "## 市场盘点\n\n待补:旧占位。\n\n"
            "## 核心逻辑\n\n待补:旧占位。\n\n"
            "## 关键数据\n\n待补:旧占位。\n\n"
            "## 产业链跟踪\n\n待补:旧占位。\n\n"
            "## 投资机会挖掘\n\n待补:旧占位。\n\n"
            "## A股可交易标的估值对比\n\n待补:旧占位。\n\n"
            "## 核心个股交易跟踪\n\n待补:旧占位。\n\n"
            "## 产业链 / 竞争格局\n\n待补:旧占位。\n\n"
            "## 标的分层与入场条件\n\n待补:旧占位。\n\n"
            "## 风险、反证与退出条件\n\n待补:旧占位。\n\n"
            "## 数据来源与证据强度\n\n待补:旧占位。\n",
            encoding="utf-8",
        )
        (report.parent / "assets").mkdir()
        for name in ("theme-chain-map.svg", "theme-bottleneck-priority.svg", "theme-stock-valuation.svg"):
            (report.parent / "assets" / name).write_text("<svg></svg>", encoding="utf-8")
        draft = self.root / "runs" / "run-A" / "cycle-001" / "deep-draft.md"
        draft.write_text(
            "# AI 算力基础设施主题最终报告\n\n"
            "## 研究课题\n\n这里是更完整的研究课题，围绕供需、订单、价格、资本开支和国产替代持续验证。\n\n"
            "## 一句话结论\n\n方向谨慎看多；置信度中等；优先看先进封装和高速互连卡口。证据:ev-chain-1。\n\n"
            "## 市场盘点\n\n### 技术突破\n\n- AI 集群扩容带来封装、网络、液冷多环节验证。\n\n"
            "## 核心逻辑\n\n1. 需求侧看资本开支。2. 供给侧看认证和良率。3. 标的筛选看收入暴露。\n\n"
            "## 关键数据\n\n| 数据 | 数值/变化 | 来源 | 日期 | 置信度 |\n| --- | --- | --- | --- | --- |\n| evidence | 8 | ev-chain-1 | today | Medium |\n\n"
            "## 产业链跟踪\n\n![产业链图谱](assets/theme-chain-map.svg)\n\n### 产业链核心环节价值分布\n\n"
            "| 产业链环节 | 细分领域/关键产品 | BOM成本占比/价值占比 | 核心技术壁垒 | 卡脖子程度 | 代表A股公司 | 公司环节地位 | 证据口径/备注 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| 上游 | 先进封装材料与设备 | 待验证 | 认证/良率 | High | 兴森科技 | 卡口候选 | ev-chain-1 |\n\n"
            "### 供需链路跟踪\n\n| 环节 | 事实映射 | 供需变化方向 | 瓶颈/卡口 | A股映射 |\n| --- | --- | --- | --- | --- |\n| 上游 | 先进封装 | 上行 | 认证 | 兴森科技 |\n\n"
            "### 瓶颈四标准校验\n\n| 候选环节 | 不可替代 | 供给刚性 | 寡头垄断 | 机构低配 | 反证条件 |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| 先进封装材料与设备 | 待验证 | 是 | 待验证 | 待验证 | 收入暴露不足 |\n\n"
            "## 投资机会挖掘\n\n### 瓶颈识别\n\n![卡口优先级](assets/theme-bottleneck-priority.svg)\n\n- 先进封装材料与设备是第一候选。\n\n### 可交易标的筛选\n\n- 直接暴露优先。\n\n"
            "## A股可交易标的估值对比\n\n![A股候选估值图](assets/theme-stock-valuation.svg)\n\n| 公司 | 代码 | 产业链位置 | 当前估值 | 财务/订单信号 | 催化 | 买点条件 | 失效条件 |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n| 兴森科技 | 002436 | 封装基板 | 待验证 | 待公告验证 | 订单 | 放量 | 无收入暴露 |\n\n"
            "## 核心个股交易跟踪\n\n| 公司 | 代码 | 产业链位置 | 估值 | 财务质量 | 趋势结构 | 关键位 | 建议买点 | 止损/失效 | 建议卖点/目标 |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n| 兴森科技 | 002436 | 封装基板 | PE 50 | 营收同比 10% | 短线强势；风险收益比2.0 | 支撑 10；压力 12 | 建议买点：10附近企稳 | 跌破10 | 建议卖点：接近12 |\n\n"
            "## 产业链 / 竞争格局\n\n### A股公司映射与核心地位判断\n\n"
            "| 公司 | 代码 | 环节 | 细分领域 | 产业占比/暴露度 | 核心技术/产品 | 卡脖子相关性 | 环节地位 | 证据与备注 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| 兴森科技 | 002436 | 上游 | 封装基板 | 待公告验证 | IC封装基板 | High/待验证 | 卡口候选 | ev-chain-1 |\n\n"
            "### 竞争格局与反证条件\n\n上游卡口强于泛主题映射，竞争格局需要持续验证。\n\n"
            "## 标的分层与入场条件\n\n- 核心环节龙头：订单确认后升级。\n\n"
            "## 风险、反证与退出条件\n\n- 若订单、价格或收入占比无法验证，则退出主线。\n\n"
            "## 数据来源与证据强度\n\n| 结论/数据 | 来源 | 日期 | 置信度 |\n| --- | --- | --- | --- |\n| 产业链 | ev-chain-1 | today | Medium |\n",
            encoding="utf-8",
        )

        res = route_cycle_reports(root=self.root, payload=payload, cycle_dir=self.cycle_dir, issues=[])

        theme_outcome = next(r for r in res["routed"] if r.get("scope") == "theme:ai-compute-infra")
        self.assertTrue(theme_outcome["draft_absorption"]["absorbed"])
        text = report.read_text(encoding="utf-8")
        self.assertIn("方向谨慎看多", text)
        self.assertIn("先进封装材料与设备是第一候选", text)
        self.assertNotIn(LOOP_LOG_HEADER, text)
        self.assertIn(LOOP_LOG_HEADER, report.with_name(CHANGE_LOG_NAME).read_text(encoding="utf-8"))

    def test_physical_ai_report_absorbs_better_deep_draft_sections(self) -> None:
        payload = _strong_payload()
        payload["theme_deep_report"] = {"draft": "runs/run-A/cycle-001/physical-draft.md", "returncode": 0}
        (self.theme_report.parent / "assets").mkdir(exist_ok=True)
        (self.theme_report.parent / "assets" / "physical-ai-chain-map.png").write_text("png", encoding="utf-8")
        self.theme_report.write_text(
            "# Physical AI 主题最终报告\n\n"
            "## 0. 核心结论\n\n人工结论。\n\n"
            "## 1. 研究对象、边界与口径\n\n旧正文。\n\n"
            "## 2. 行业背景与需求驱动\n\n旧正文。\n\n"
            "## 2.5 硬事实台账与证据密度\n\n旧正文。\n\n"
            "## 3. 产业链全景图谱\n\n旧图谱。\n\n"
            "## 4. 上游材料、部件与制程要素挖掘\n\n旧正文。\n\n"
            "## 5. 产业链核心环节价值分布\n\n旧正文。\n\n"
            "## 6. 竞争格局与核心壁垒\n\n旧正文。\n\n"
            "## 7. A股公司映射与核心地位判断\n\n旧正文。\n\n"
            "## 8. 投资线索、交易跟踪与目标价情景\n\n旧正文。\n\n"
            "## 9. 催化因素与产业传导路径\n\n旧正文。\n\n"
            "## 10. 风险提示\n\n旧正文。\n\n"
            "## 11. 数据来源、证据强度与待核验事项\n\n旧正文。\n",
            encoding="utf-8",
        )
        draft = self.root / "runs" / "run-A" / "cycle-001" / "physical-draft.md"
        draft.write_text(
            "# Physical AI 主题最终报告\n\n"
            "## 0. 核心结论\n\n人工结论。\n\n"
            "## 1. 研究对象、边界与口径\n\n旧正文。\n\n"
            "## 2. 行业背景与需求驱动\n\n旧正文。\n\n"
            "## 2.5 硬事实台账与证据密度\n\n### 硬事实台账\n\n| 事实类型 | 硬事实/线索 | 涉及节点 | 涉及公司 | 数值/时间 | 来源 | 证据强度 | 交易含义 |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n| 收入占比/财务 | 绿的谐波营收同比42%，归母净利同比61% | 减速器/精密传动 | 绿的谐波 | 42%、61% | 财报 | 财报级/High | 财务兑现 |\n\n### 证据密度评分\n\n| 维度 | 数量/评分 | 口径 | 含义 |\n| --- | --- | --- | --- |\n| 证据密度评分 | 70 | 硬事实台账 | 结构已成型 |\n\n"
            "## 3. 产业链全景图谱\n\n![产业链投研拆解图](assets/physical-ai-chain-map.png)\n\n"
            "### 核心节点三公司校验\n\n"
            "| 产业链节点 | 至少三家核心受益/候选公司 | 为什么重要 | 反证风险 |\n"
            "| --- | --- | --- | --- |\n"
            "| 减速器/精密传动 | 绿的谐波、双环传动、中大力德 | 卡口 | 订单不足 |\n\n"
            "## 4. 上游材料、部件与制程要素挖掘\n\n旧正文。\n\n"
            "## 5. 产业链核心环节价值分布\n\n| 产业链环节 | 细分领域/关键产品 | BOM成本占比/价值占比 | 核心技术壁垒 | 卡脖子程度 | 代表A股公司 | 公司环节地位 | 证据口径/备注 |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n| 减速器 | 核心三公司 | 高 | 寿命 | 高 | 绿的谐波、双环传动、中大力德 | 卡口 | 需订单 |\n\n"
            "## 6. 竞争格局与核心壁垒\n\n旧正文。\n\n"
            "## 7. A股公司映射与核心地位判断\n\n| 公司 | 代码 | 环节 | 细分领域 | 产业占比/暴露度 | 核心技术/产品 | 卡脖子相关性 | 环节地位 | 证据与备注 |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n| 绿的谐波 | 688017 | 上游 | 减速器 | 高 | 谐波减速器 | 高 | 龙头 | 支撑399，压力419 |\n\n"
            "## 8. 投资线索、交易跟踪与目标价情景\n\n"
            "| 公司 | 代码 | 产业链结论 | 财务质量 | 当前估值 | 技术面/趋势 | 买入条件 | 止损/失效条件 | 卖出/目标 | 综合判断 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| 绿的谐波 | 688017 | 减速器 | 营收同比42%，归母净利同比61%，毛利率高 | PE高 | MA5/10/20/60=441/419/399/320；支撑399；压力419；风险收益比1.2 | 等待买入触发：当前未进入买入候选 | 跌破345 | 未设技术目标：尚未进入买入候选 | 观察名单，等待结构修复 |\n\n"
            "## 9. 催化因素与产业传导路径\n\n旧正文。\n\n"
            "## 10. 风险提示\n\n旧正文。\n\n"
            "## 11. 数据来源、证据强度与待核验事项\n\n旧正文。\n",
            encoding="utf-8",
        )

        res = route_cycle_reports(root=self.root, payload=payload, cycle_dir=self.cycle_dir, issues=[])

        theme_outcome = next(r for r in res["routed"] if r.get("scope") == "theme:physical-ai")
        self.assertTrue(theme_outcome["draft_absorption"]["absorbed"])
        self.assertEqual(theme_outcome["draft_absorption"]["frame"], "physical-ai")
        text = self.theme_report.read_text(encoding="utf-8")
        self.assertIn("核心节点三公司校验", text)
        self.assertIn("等待买入触发：当前未进入买入候选", text)
        self.assertNotIn(LOOP_LOG_HEADER, text)

    def test_existing_lightweight_theme_report_backfills_benchmark_frame(self) -> None:
        payload = _strong_payload()
        payload["research_pipeline"]["selected_industry_chain"]["selected_theme"] = "ai_compute_infra"
        report = self.root / "reports" / "themes" / "ai-compute-infra" / "report.md"
        report.parent.mkdir(parents=True)
        report.write_text(
            "# AI 算力基础设施主题最终报告\n\n"
            f"{LOOP_LOG_HEADER}\n\n"
            "<!-- research-os-curation:theme:ai-compute-infra:run-A:1 -->\n"
            "#### old increment\n",
            encoding="utf-8",
        )

        res = route_cycle_reports(root=self.root, payload=payload, cycle_dir=self.cycle_dir, issues=[])

        theme_outcome = next(r for r in res["routed"] if r.get("scope") == "theme:ai-compute-infra")
        self.assertEqual(theme_outcome["mode"], "frame_backfill_only")
        text = report.read_text(encoding="utf-8")
        self.assertIn("## 市场盘点", text)
        self.assertIn("## 投资机会挖掘", text)
        self.assertNotIn(LOOP_LOG_HEADER, text)
        change_log = report.with_name(CHANGE_LOG_NAME).read_text(encoding="utf-8")
        self.assertEqual(change_log.count("research-os-curation:theme:ai-compute-infra:run-A:1"), 1)

    # -- emerging 主题即使 strength 达标也默认进观察池(需事件才升正文) --
    def test_emerging_theme_defaults_to_watch_pool(self) -> None:
        payload = _strong_payload()
        payload["research_pipeline"]["selected_industry_chain"]["selected_theme"] = "quantum"
        res = route_cycle_reports(root=self.root, payload=payload, cycle_dir=self.cycle_dir, issues=[])
        self.assertEqual(res["theme_key"], "quantum-computing")
        self.assertEqual(res["tier"], "emerging")
        theme_report = self.root / "reports" / "themes" / "quantum-computing" / "report.md"
        self.assertTrue(theme_report.exists())
        txt = theme_report.read_text(encoding="utf-8")
        self.assertNotIn(WATCH_POOL_HEADER, txt)
        self.assertIn(WATCH_POOL_HEADER, theme_report.with_name(CHANGE_LOG_NAME).read_text(encoding="utf-8"))

    # -- 低质量线索 -> 观察池,不进正文 --
    def test_weak_cycle_goes_to_watch_pool(self) -> None:
        weak = {
            "run_id": "run-W",
            "cycle": 2,
            "status": "ok",
            "started_at": "2026-07-09T00:00:00+00:00",
            "finished_at": "2026-07-09T00:05:00+00:00",
            "errors": [],
            "evidence_ids": [],
            "industry_reports": [],
            "news": {"headlines": [{"source": "S", "title": "边缘线索"}]},
            "agent_review": {},
            "stock_supplements": {},
            "research_pipeline": {"selected_industry_chain": {"selected_theme": "ai_physical_ai"}},
        }
        res = route_cycle_reports(root=self.root, payload=weak, cycle_dir=self.cycle_dir, issues=["missing_evidence_ids"])
        self.assertLess(res["strength"], STRENGTH_MAIN_THRESHOLD)
        self.assertTrue(res["to_watch_pool"])
        th = self.theme_report.read_text(encoding="utf-8")
        self.assertIn("人工撰写的正文结论", th)  # 正文结论不被覆盖
        self.assertNotIn(WATCH_POOL_HEADER, th)
        change_log = self.theme_report.with_name(CHANGE_LOG_NAME).read_text(encoding="utf-8")
        self.assertIn(WATCH_POOL_HEADER, change_log)
        self.assertIn("边缘线索", change_log)

    # -- 修正旧判断:软标记(删除线)沉淀,人工正文保留 --
    def test_revision_soft_marks_old_claim(self) -> None:
        payload = _strong_payload()
        payload["agent_review"]["invalidations"] = [
            {"claim": "减速器国产化率已达60%", "reason": "最新调研显示不足40%"}
        ]
        res = route_cycle_reports(root=self.root, payload=payload, cycle_dir=self.cycle_dir, issues=[])
        theme_outcome = next(r for r in res["routed"] if r.get("scope") == "theme:physical-ai")
        self.assertEqual(theme_outcome["revisions"], 1)
        th = self.theme_report.read_text(encoding="utf-8")
        self.assertNotIn(REVISION_HEADER, th)
        self.assertIn("人工撰写的正文结论", th)  # 正文永不物理删除
        change_log = self.theme_report.with_name(CHANGE_LOG_NAME).read_text(encoding="utf-8")
        self.assertIn(REVISION_HEADER, change_log)
        self.assertIn("~~减速器国产化率已达60%~~", change_log)

    # -- 幂等:同一轮重复路由不重复追加 --
    def test_idempotent(self) -> None:
        payload = _strong_payload()
        route_cycle_reports(root=self.root, payload=payload, cycle_dir=self.cycle_dir, issues=[])
        res2 = route_cycle_reports(root=self.root, payload=payload, cycle_dir=self.cycle_dir, issues=[])
        self.assertTrue(all(r.get("status") == "skipped" for r in res2["routed"]))
        change_log = self.theme_report.with_name(CHANGE_LOG_NAME).read_text(encoding="utf-8")
        self.assertEqual(change_log.count("research-os-curation:theme:physical-ai:run-A:1"), 1)

    def test_legacy_embedded_loop_log_is_migrated_to_change_log(self) -> None:
        self.theme_report.write_text(
            "# Physical AI 主题最终报告\n\n"
            "## 0. 核心结论\n\n人工正文。\n\n"
            f"{LOOP_LOG_HEADER}\n\n"
            "<!-- research-os-curation:theme:physical-ai:old-run:1 -->\n"
            "#### old\n\n"
            "- 历史增量。\n",
            encoding="utf-8",
        )

        res = route_cycle_reports(root=self.root, payload=_strong_payload(), cycle_dir=self.cycle_dir, issues=[])

        theme_outcome = next(r for r in res["routed"] if r.get("scope") == "theme:physical-ai")
        self.assertTrue(theme_outcome["migrated_legacy_log"])
        body = self.theme_report.read_text(encoding="utf-8")
        self.assertIn("人工正文", body)
        self.assertNotIn(LOOP_LOG_HEADER, body)
        change_log = self.theme_report.with_name(CHANGE_LOG_NAME).read_text(encoding="utf-8")
        self.assertIn("research-os-curation:theme:physical-ai:old-run:1", change_log)
        self.assertIn("research-os-curation:theme:physical-ai:run-A:1", change_log)


if __name__ == "__main__":
    unittest.main()
