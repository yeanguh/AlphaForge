from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class EvidenceCard:
    id: str
    source_name: str
    source_type: str
    title: str
    url: str | None = None
    source_url: str | None = None
    raw_path: str | None = None
    claim_id: str | None = None
    freshness: str | None = None
    related_companies: list[str] = field(default_factory=list)
    related_themes: list[str] = field(default_factory=list)
    observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    claims: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.source_url is None and self.url:
            self.source_url = self.url
        if self.claim_id is None and self.id:
            self.claim_id = f"{self.id}:claim:0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.id:
            errors.append("evidence.id is required")
        if not self.source_name:
            errors.append("evidence.source_name is required")
        if not self.source_type:
            errors.append("evidence.source_type is required")
        if not self.title:
            errors.append("evidence.title is required")
        if not any(str(claim).strip() for claim in self.claims):
            errors.append("evidence.claims must include at least one non-empty claim")
        has_source_locator = bool(self.url or self.source_url or self.raw_path or self.raw)
        if not has_source_locator:
            errors.append("evidence must include url, source_url, raw_path, or raw payload")
        return errors
