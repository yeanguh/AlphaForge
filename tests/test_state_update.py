import json
import tempfile
import unittest
from pathlib import Path

from loop_os.domain.state_update import (
    _id,
    apply_state_transition,
    build_state_transition_draft,
    validate_state_transition,
)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_evidence_index(root: Path, evidence_ids: list[str]) -> None:
    evidence_dir = root / "evidence" / "2026-07-09"
    evidence_dir.mkdir(parents=True)
    _write_json(evidence_dir / "raw-index.json", {"schema_version": "1.0", "evidence_ids": evidence_ids})


class StateUpdateTest(unittest.TestCase):
    def test_transition_is_validated_before_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            state.mkdir()
            _write_json(state / "research-state.json", {"schema_version": "1.0", "themes": []})
            _write_json(state / "catalysts.json", {"schema_version": "1.0", "catalysts": []})
            _write_json(state / "watchlist.json", {"schema_version": "1.0", "watchlist": []})
            _write_json(state / "paper-portfolio.json", {"schema_version": "1.0", "cash": None, "positions": [], "reviews": []})
            _write_json(state / "system-health.json", {"schema_version": "1.0"})

            payload = {
                "status": "ok",
                "research_pipeline": {
                    "selected_industry_chain": {
                        "selected_theme": "physical_ai",
                        "score": 4,
                        "supporting_public_items": [{"title": "机器人产业链催化", "source": "public"}],
                    },
                    "hotspot_scoring": {"ranked_themes": [{"theme": "physical_ai", "score": 4}]},
                    "trade_decision_engine": {"decisions": [{"symbol": "688017", "action": "watch"}]},
                },
                "a_share_quotes": [{"symbol": "688017", "name": "绿的谐波", "price": 120.0, "change_pct": 1.2}],
                "agent_review": {"decision": "watch"},
                "tradingagents_review": {"portfolio_rating": "Neutral", "trader_action": "wait"},
            }
            _write_evidence_index(root, ["ev-1", "ev-2"])

            draft = build_state_transition_draft(root, "run-1", 1, payload, ["ev-1", "ev-2"])
            self.assertEqual(validate_state_transition(root, draft), [])
            self.assertEqual(json.loads((state / "research-state.json").read_text(encoding="utf-8")).get("loops"), None)

            summary = apply_state_transition(root, "run-1", 1, payload, ["ev-1", "ev-2"])
            self.assertTrue(summary["validated"])
            self.assertTrue(summary["committed"])
            committed = json.loads((state / "research-state.json").read_text(encoding="utf-8"))
            self.assertEqual(committed["loops"]["full_loop"]["last_run_id"], "run-1")

    def test_transition_rejects_missing_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            state.mkdir()
            _write_json(state / "research-state.json", {"schema_version": "1.0", "themes": []})
            _write_json(state / "catalysts.json", {"schema_version": "1.0", "catalysts": []})
            _write_json(state / "watchlist.json", {"schema_version": "1.0", "watchlist": []})
            _write_json(state / "paper-portfolio.json", {"schema_version": "1.0", "cash": None, "positions": [], "reviews": []})
            _write_json(state / "system-health.json", {"schema_version": "1.0"})

            payload = {
                "status": "ok",
                "research_pipeline": {"selected_industry_chain": {"selected_theme": "robotics", "supporting_public_items": [{"title": "催化"}]}},
                "a_share_quotes": [{"symbol": "688017"}],
            }
            draft = build_state_transition_draft(root, "run-1", 1, payload, [])
            errors = validate_state_transition(root, draft)
            self.assertTrue(any("missing evidence_ids" in error for error in errors))

    def test_transition_rejects_nonexistent_evidence_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            state.mkdir()
            _write_json(state / "research-state.json", {"schema_version": "1.0", "themes": []})
            _write_json(state / "catalysts.json", {"schema_version": "1.0", "catalysts": []})
            _write_json(state / "watchlist.json", {"schema_version": "1.0", "watchlist": []})
            _write_json(state / "paper-portfolio.json", {"schema_version": "1.0", "cash": None, "positions": [], "reviews": []})
            _write_json(state / "system-health.json", {"schema_version": "1.0"})
            _write_evidence_index(root, ["ev-real"])

            payload = {
                "status": "ok",
                "research_pipeline": {"selected_industry_chain": {"selected_theme": "robotics", "supporting_public_items": [{"title": "催化"}]}},
                "a_share_quotes": [{"symbol": "688017"}],
            }
            draft = build_state_transition_draft(root, "run-1", 1, payload, ["ev-does-not-exist"])
            errors = validate_state_transition(root, draft)
            self.assertTrue(any("references missing evidence_id ev-does-not-exist" in error for error in errors))

    def test_confirmed_catalyst_is_not_downgraded_to_validating(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            state.mkdir()
            title = "机器人产业链催化"
            catalyst_id = _id("cat", title)
            _write_json(state / "research-state.json", {"schema_version": "1.0", "themes": []})
            _write_json(
                state / "catalysts.json",
                {
                    "schema_version": "1.0",
                    "catalysts": [
                        {
                            "id": catalyst_id,
                            "title": title,
                            "status": "confirmed",
                            "evidence_ids": ["ev-old"],
                            "next_action": "track_pricing",
                        }
                    ],
                },
            )
            _write_json(state / "watchlist.json", {"schema_version": "1.0", "watchlist": []})
            _write_json(state / "paper-portfolio.json", {"schema_version": "1.0", "cash": None, "positions": [], "reviews": []})
            _write_json(state / "system-health.json", {"schema_version": "1.0"})
            _write_evidence_index(root, ["ev-new"])

            payload = {
                "status": "ok",
                "research_pipeline": {
                    "selected_industry_chain": {
                        "selected_theme": "physical_ai",
                        "supporting_public_items": [{"title": title, "source": "public"}],
                    }
                },
            }
            draft = build_state_transition_draft(root, "run-1", 1, payload, ["ev-new"])
            catalyst = next(item for item in draft.states["catalysts_state"]["catalysts"] if item["id"] == catalyst_id)
            self.assertEqual(catalyst["status"], "confirmed")
            self.assertEqual(validate_state_transition(root, draft), [])
