import unittest
from pathlib import Path

from loop_os.schemas.state import REQUIRED_STATE_FILES, load_state_file


ROOT = Path(__file__).resolve().parents[1]


class StateFileTest(unittest.TestCase):
    def test_state_files_have_single_root_object(self) -> None:
        for name in REQUIRED_STATE_FILES:
            data = load_state_file(ROOT / "state" / name)
            self.assertIsInstance(data, dict)
            self.assertTrue(data["schema_version"])
