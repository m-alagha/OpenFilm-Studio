from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import smoke


def test_smoke_run_writes_mock_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = smoke.run(tmp_path)
    assert out.parent == tmp_path
    assert json.loads(out.read_text(encoding="utf-8"))["mock"] is True
    assert "estimate: $0" in capsys.readouterr().out


def test_smoke_main_without_args(capsys: pytest.CaptureFixture[str]) -> None:
    assert smoke.main(["smoke"]) == 0
    assert "MOCK SMOKE TEST PASSED" in capsys.readouterr().out
