from __future__ import annotations

from typing import Any, Protocol

from loop_os.schemas.provider import ProviderResult


class NewsPort(Protocol):
    def smoke(self, live: bool = False) -> ProviderResult:
        ...

    def fetch_headlines(self, max_sources: int = 24, max_items: int = 24) -> dict[str, Any]:
        ...
