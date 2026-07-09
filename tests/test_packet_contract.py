import unittest

from loop_os.schemas.packet import build_packet, validate_packet


class PacketContractTest(unittest.TestCase):
    def test_provider_packet_minimal_contract(self) -> None:
        packet = build_packet(
            "ProviderPacket",
            "a_stock_data",
            provider="a-stock-data",
            freshness="latest_available",
            evidence_ids=["ev-1"],
            raw_refs=["data/raw/provider/sample.json"],
        )

        self.assertEqual(validate_packet(packet, "ProviderPacket"), [])

    def test_packet_rejects_external_raw_ref(self) -> None:
        packet = build_packet(
            "ResearchPacket",
            "hotspot-scoring",
            selected_theme="physical_ai",
            raw_refs=["/Users/bytedance/private.json"],
        )

        errors = validate_packet(packet, "ResearchPacket")
        self.assertTrue(any("must stay inside repository" in error for error in errors))

    def test_review_packet_cannot_mutate_state(self) -> None:
        packet = build_packet(
            "ReviewPacket",
            "tradingagents_astock",
            reviewer="TradingAgents-astock",
            state_mutation_allowed=True,
        )

        errors = validate_packet(packet, "ReviewPacket")
        self.assertIn("ReviewPacket must not allow state mutation", errors)

    def test_candidate_packet_requires_symbol(self) -> None:
        packet = build_packet("CandidatePacket", "stock-analyzer")

        errors = validate_packet(packet, "CandidatePacket")
        self.assertIn("CandidatePacket.symbol is required", errors)

