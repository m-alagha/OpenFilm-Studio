from __future__ import annotations

import json
import socket
from decimal import Decimal
from pathlib import Path

import pytest

from app.providers import (
    ErrorCode,
    JobState,
    MockVideoProvider,
    ProviderError,
    VideoRequest,
)


def make_request(**overrides: object) -> VideoRequest:
    fields: dict[str, object] = {
        "prompt": "A quiet harbour at dawn.",
        "duration_s": 5,
        "resolution": "720p",
        "aspect_ratio": "16:9",
    }
    fields.update(overrides)
    return VideoRequest(**fields)  # type: ignore[arg-type]


def run_to_completion(provider: MockVideoProvider, job_id: str) -> JobState:
    for _ in range(10):
        state = provider.poll(job_id).state
        if state is not JobState.RUNNING:
            return state
    raise AssertionError("mock job never finished")


def test_capabilities_are_mock_and_conservative() -> None:
    caps = MockVideoProvider().capabilities()
    assert caps.is_mock
    assert not caps.supports_audio_input
    assert not caps.supports_reference_video
    assert not caps.supports_balance_query


def test_estimate_is_zero_and_labelled_mock() -> None:
    estimate = MockVideoProvider().estimate_cost(make_request())
    assert estimate.amount_usd == Decimal("0")
    assert estimate.is_mock
    assert "mock" in estimate.basis


def test_end_to_end_download_is_deterministic(tmp_path: Path) -> None:
    outputs = []
    for run in ("a", "b"):
        provider = MockVideoProvider()
        job_id = provider.submit(make_request())
        assert run_to_completion(provider, job_id) is JobState.SUCCEEDED
        out = provider.download(job_id, tmp_path / run)
        outputs.append(out.read_bytes())
        body = json.loads(out.read_text(encoding="utf-8"))
        assert body["mock"] is True
        assert out.name.endswith(".mock.json")
    assert outputs[0] == outputs[1]


def test_duplicate_submit_returns_same_job() -> None:
    provider = MockVideoProvider()
    assert provider.submit(make_request()) == provider.submit(make_request())


def test_idempotency_key_distinguishes_jobs() -> None:
    provider = MockVideoProvider()
    a = provider.submit(make_request(idempotency_key="take-1"))
    b = provider.submit(make_request(idempotency_key="take-2"))
    assert a != b


@pytest.mark.parametrize(
    "overrides",
    [
        {"prompt": "   "},
        {"duration_s": 0},
        {"duration_s": 16},
        {"resolution": "8k"},
        {"aspect_ratio": "4:3"},
        {"reference_image_paths": tuple(Path(f"r{i}.png") for i in range(7))},
        {"reference_video_paths": (Path("clip.mp4"),)},
        {"audio_reference_paths": (Path("voice.wav"),)},
    ],
)
def test_unsupported_requests_are_rejected(overrides: dict[str, object]) -> None:
    with pytest.raises(ProviderError) as info:
        MockVideoProvider().submit(make_request(**overrides))
    assert info.value.code is ErrorCode.UNSUPPORTED_FEATURE


def test_simulated_failure_surfaces_normalized_error() -> None:
    provider = MockVideoProvider(fail_with=ErrorCode.QUOTA)
    job_id = provider.submit(make_request())
    assert run_to_completion(provider, job_id) is JobState.FAILED
    status = provider.poll(job_id)
    assert status.error is not None
    assert status.error.code is ErrorCode.QUOTA


def test_download_before_success_fails(tmp_path: Path) -> None:
    provider = MockVideoProvider(polls_until_done=5)
    job_id = provider.submit(make_request())
    with pytest.raises(ProviderError):
        provider.download(job_id, tmp_path)


def test_cancel_and_unknown_job() -> None:
    provider = MockVideoProvider()
    job_id = provider.submit(make_request())
    provider.cancel(job_id)
    assert provider.poll(job_id).state is JobState.CANCELLED
    with pytest.raises(ProviderError):
        provider.poll("mock-does-not-exist")


def test_network_guard_is_active() -> None:
    with pytest.raises(AssertionError, match="network access"):
        socket.create_connection(("example.com", 443))
