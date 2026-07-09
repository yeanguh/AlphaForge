from __future__ import annotations

from typing import Any, Iterable, Protocol

from loop_os.schemas.provider import ProviderResult


class MarketDataPort(Protocol):
    def smoke(self, live: bool = False) -> ProviderResult:
        ...

    def fetch_quote(self, symbol: str) -> dict[str, Any]:
        ...

    def fetch_quotes(self, symbols: Iterable[str]) -> list[dict[str, Any]]:
        ...

    def fetch_price_history(self, symbol: str, days: int = 120) -> dict[str, Any]:
        ...

    def fetch_stock_supplement(self, symbol: str) -> dict[str, Any]:
        ...
