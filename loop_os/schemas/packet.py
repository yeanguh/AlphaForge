from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


PACKET_TYPES = {
    "ProviderPacket": {"provider", "freshness"},
    "EvidencePacket": {"evidence_ids"},
    "ResearchPacket": {"selected_theme"},
    "CandidatePacket": {"symbol"},
    "ReviewPacket": {"reviewer"},
    "ReportSourcePacket": {"report_kind"},
}

ALLOWED_RAW_REF_PREFIXES = ("data/raw/", "runs/", "evidence/")


def build_packet(packet_type: str, source_stage: str, **fields: Any) -> dict[str, Any]:
    packet = {
        "packet_type": packet_type,
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_stage": source_stage,
        "evidence_ids": [],
        "claim_ids": [],
        "warnings": [],
        "errors": [],
        "raw_refs": [],
    }
    packet.update(fields)
    return packet


def validate_packet(packet: dict[str, Any], expected_type: str | None = None) -> list[str]:
    errors: list[str] = []
    packet_type = str(packet.get("packet_type") or expected_type or "")

    if expected_type and packet.get("packet_type") != expected_type:
        errors.append(f"packet_type must be {expected_type}")
    if packet_type not in PACKET_TYPES:
        errors.append(f"unknown packet_type {packet_type!r}")

    for field in ["packet_type", "schema_version", "generated_at", "source_stage"]:
        if not packet.get(field):
            errors.append(f"{field} is required")

    for field in PACKET_TYPES.get(packet_type, set()):
        if packet.get(field) in (None, "", []):
            errors.append(f"{packet_type}.{field} is required")

    errors.extend(_validate_id_list(packet, "evidence_ids"))
    errors.extend(_validate_id_list(packet, "claim_ids"))
    errors.extend(_validate_messages(packet, "warnings"))
    errors.extend(_validate_messages(packet, "errors"))
    errors.extend(_validate_raw_refs(packet))

    if packet_type == "ReviewPacket" and packet.get("state_mutation_allowed") is True:
        errors.append("ReviewPacket must not allow state mutation")

    return errors


def _validate_id_list(packet: dict[str, Any], field: str) -> list[str]:
    value = packet.get(field, [])
    if value is None:
        return []
    if not isinstance(value, list):
        return [f"{field} must be a list"]
    if any(not isinstance(item, str) or not item for item in value):
        return [f"{field} must contain non-empty strings"]
    return []


def _validate_messages(packet: dict[str, Any], field: str) -> list[str]:
    value = packet.get(field, [])
    if not isinstance(value, list):
        return [f"{field} must be a list"]
    if any(not isinstance(item, str) for item in value):
        return [f"{field} must contain strings"]
    return []


def _validate_raw_refs(packet: dict[str, Any]) -> list[str]:
    value = packet.get("raw_refs", [])
    if not isinstance(value, list):
        return ["raw_refs must be a list"]

    errors: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            errors.append("raw_refs must contain non-empty strings")
            continue
        if item.startswith("/") or ".." in item.split("/"):
            errors.append(f"raw_ref {item} must stay inside repository relative outputs")
            continue
        if not item.startswith(ALLOWED_RAW_REF_PREFIXES):
            errors.append(f"raw_ref {item} must start with one of {ALLOWED_RAW_REF_PREFIXES}")
    return errors

