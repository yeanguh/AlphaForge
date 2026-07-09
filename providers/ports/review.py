from __future__ import annotations

from typing import Any, Protocol

from loop_os.schemas.provider import ProviderResult


class ReviewPort(Protocol):
    def smoke(self, live: bool = False) -> ProviderResult:
        ...

    def review_packet(self, packet: dict[str, Any]) -> dict[str, Any]:
        ...
