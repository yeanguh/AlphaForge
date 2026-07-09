from __future__ import annotations

from pathlib import Path

from loop_os.schemas.provider import ProviderResult


ROOT = Path(__file__).resolve().parents[2]
SUBMODULE = ROOT / "external" / "Vibe-Research"


def smoke(live: bool = False) -> ProviderResult:
    readme = SUBMODULE / "README.md"
    if not readme.exists():
        return ProviderResult("Vibe-Research", "error", "README missing", errors=[str(readme)])
    return ProviderResult("Vibe-Research", "ok", "UI/reference provider submodule readable", {"path": str(SUBMODULE)})
