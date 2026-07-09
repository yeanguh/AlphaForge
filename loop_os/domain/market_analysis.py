from __future__ import annotations


def price_change_pct(latest: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round((latest - previous) / previous * 100, 4)


def valuation_band(pe: float | None) -> str:
    if pe is None or pe <= 0:
        return "unknown"
    if pe < 15:
        return "low"
    if pe <= 35:
        return "normal"
    return "high"
