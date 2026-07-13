from __future__ import annotations

import json
import urllib.parse
import urllib.request


UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def get_text(url: str, params: dict[str, str] | None = None, timeout: int = 15, encoding: str | None = None) -> str:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    referer = "https://quote.eastmoney.com/" if "eastmoney.com" in url else "https://finance.sina.com.cn/"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Referer": referer,
            "Accept": "application/json,text/plain,*/*",
            "Connection": "close",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return raw.decode(encoding or "utf-8", errors="replace")


def get_json(url: str, params: dict[str, str] | None = None, timeout: int = 15) -> dict:
    return json.loads(get_text(url, params=params, timeout=timeout))
