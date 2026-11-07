"""The launcher reinstalls dependencies when a lockfile changes (e.g. after a git update)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "dev.py"


@pytest.fixture(scope="module")
def dev() -> ModuleType:
    spec = importlib.util.spec_from_file_location("openfilm_dev", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["openfilm_dev"] = module
    spec.loader.exec_module(module)
    return module


def test_install_needed_until_stamped_and_again_after_lock_change(
    dev: ModuleType, tmp_path: Path
) -> None:
    env_dir = tmp_path / "node_modules"
    env_dir.mkdir()
    lockfile = tmp_path / "package-lock.json"
    lockfile.write_text('{"v": 1}')
    assert dev.needs_install(env_dir, lockfile) is True
    dev.write_stamp(env_dir, lockfile)
    assert dev.needs_install(env_dir, lockfile) is False
    lockfile.write_text('{"v": 2}')  # e.g. after "git checkout v0.2.0"
    assert dev.needs_install(env_dir, lockfile) is True
