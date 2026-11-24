import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pain_miner.client import FixtureArchiveClient  # noqa: E402

TOPIC = "invoicing software"


@pytest.fixture
def fixture_client():
    return FixtureArchiveClient(ROOT / "fixtures")
