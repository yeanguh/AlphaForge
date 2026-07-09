import json
import tempfile
import unittest
from pathlib import Path

from loop_os.domain.evidence_service import rebuild_all_claim_indexes, write_evidence
from loop_os.schemas.evidence import EvidenceCard


class EvidenceContractTest(unittest.TestCase):
    def test_evidence_requires_claim_and_source_locator(self) -> None:
        card = EvidenceCard(id="ev-1", source_name="test", source_type="news", title="标题")
        errors = card.validate()
        self.assertIn("evidence.claims must include at least one non-empty claim", errors)
        self.assertIn("evidence must include url, source_url, raw_path, or raw payload", errors)

    def test_write_evidence_creates_claim_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = {
                "started_at": "2026-07-09T00:00:00+00:00",
                "a_share_quotes": [{"symbol": "688017", "name": "绿的谐波", "price": 120.0, "pe": 80, "pb": 8, "valuation_band": "high"}],
                "agent_review": {"decision": "watch", "agent_provider": "deterministic", "reason": "test"},
            }

            evidence_ids = write_evidence(root, 1, payload)
            self.assertTrue(evidence_ids)
            claim_indexes = list((root / "evidence").glob("*/claim-index.json"))
            self.assertEqual(len(claim_indexes), 1)
            claim_index = json.loads(claim_indexes[0].read_text(encoding="utf-8"))
            self.assertTrue(claim_index["claims"])
            first_claim = next(iter(claim_index["claims"].values()))
            self.assertIn("evidence_id", first_claim)
            self.assertIn("created_at", first_claim)

    def test_write_evidence_preserves_earlier_same_day_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_payload = {
                "started_at": "2026-07-09T00:00:00+00:00",
                "a_share_quotes": [{"symbol": "688017", "name": "绿的谐波", "price": 120.0, "pe": 80, "pb": 8, "valuation_band": "high"}],
                "agent_review": {"decision": "watch", "agent_provider": "deterministic", "reason": "first"},
            }
            second_payload = {
                "started_at": "2026-07-09T01:00:00+00:00",
                "a_share_quotes": [{"symbol": "000837", "name": "秦川机床", "price": 9.0, "pe": 40, "pb": 3, "valuation_band": "normal"}],
                "agent_review": {"decision": "watch", "agent_provider": "deterministic", "reason": "second"},
            }

            first_ids = set(write_evidence(root, 1, first_payload))
            second_ids = set(write_evidence(root, 2, second_payload))
            claim_index_path = next((root / "evidence").glob("*/claim-index.json"))
            claim_index = json.loads(claim_index_path.read_text(encoding="utf-8"))
            indexed_evidence_ids = {claim["evidence_id"] for claim in claim_index["claims"].values()}

            self.assertTrue(first_ids.issubset(indexed_evidence_ids))
            self.assertTrue(second_ids.issubset(indexed_evidence_ids))

    def test_rebuild_all_claim_indexes_backfills_missing_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence_dir = root / "evidence" / "2026-07-08"
            evidence_dir.mkdir(parents=True)
            (evidence_dir / "ev-old.json").write_text(
                json.dumps(
                    {
                        "id": "ev-old",
                        "source_name": "test",
                        "source_type": "news",
                        "title": "old",
                        "claims": ["old claim"],
                        "raw": {"ok": True},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            rebuilt = rebuild_all_claim_indexes(root)
            self.assertEqual(rebuilt, [evidence_dir / "claim-index.json"])
            claim_index = json.loads((evidence_dir / "claim-index.json").read_text(encoding="utf-8"))
            self.assertEqual(claim_index["claims"]["ev-old:claim:0"]["evidence_id"], "ev-old")
