from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_secrets.py"


@pytest.fixture(scope="module")
def scanner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_secrets", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_secrets"] = module
    spec.loader.exec_module(module)
    return module


def write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_detects_google_key(scanner: ModuleType, tmp_path: Path) -> None:
    path = write(tmp_path, "config.py", "KEY = '" + "AIza" + "B" * 35 + "'\n")
    assert scanner.scan([path])


def test_detects_real_looking_assignment(scanner: ModuleType, tmp_path: Path) -> None:
    path = write(tmp_path, "settings.txt", "GEMINI_API_KEY=" + "q1w2e3r4t5y6u7" + "\n")
    assert scanner.scan([path])


def test_detects_committed_env_file(scanner: ModuleType, tmp_path: Path) -> None:
    path = write(tmp_path, ".env", "NOTHING=1\n")
    assert scanner.scan([path])


def test_placeholders_in_env_example_pass(scanner: ModuleType, tmp_path: Path) -> None:
    lines = ["GEMINI_API_KEY" + "=", "OTHER_API_KEY" + "=your-key-here", ""]
    path = write(tmp_path, ".env.example", "\n".join(lines))
    assert scanner.scan([path]) == []


def test_repository_is_clean(scanner: ModuleType) -> None:
    repo = SCRIPT.parents[1]
    assert scanner.scan(scanner.git_files(repo)) == []
