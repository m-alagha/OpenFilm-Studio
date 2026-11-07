"""Deterministic offline mock provider.

Makes no network calls, needs no credentials, costs nothing. Output is a JSON
placeholder (``*.mock.json``), never a fake video, so it cannot be mistaken for
real generated media.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

from app.providers.base import (
    Capabilities,
    CostEstimate,
    ErrorCode,
    JobState,
    JobStatus,
    ProviderError,
    VideoProvider,
    VideoRequest,
    check_request,
)

MOCK_CAPABILITIES = Capabilities(
    provider_id="mock",
    model_id="mock-video-v0",
    is_mock=True,
    min_duration_s=1,
    max_duration_s=15,
    resolutions=("360p", "720p", "1080p"),
    aspect_ratios=("16:9", "9:16"),
    max_reference_images=6,
    supports_reference_video=False,
    supports_audio_input=False,
    supports_native_audio_output=False,
    supports_cancel=True,
    supports_balance_query=False,
)


def request_hash(request: VideoRequest) -> str:
    payload = {
        "prompt": request.prompt,
        "duration_s": request.duration_s,
        "resolution": request.resolution,
        "aspect_ratio": request.aspect_ratio,
        "reference_images": [p.as_posix() for p in request.reference_image_paths],
        "idempotency_key": request.idempotency_key,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class MockVideoProvider(VideoProvider):
    def __init__(self, *, polls_until_done: int = 2, fail_with: ErrorCode | None = None) -> None:
        self._polls_until_done = polls_until_done
        self._fail_with = fail_with
        self._jobs: dict[str, VideoRequest] = {}
        self._poll_counts: dict[str, int] = {}
        self._cancelled: set[str] = set()

    def capabilities(self) -> Capabilities:
        return MOCK_CAPABILITIES

    def validate_credentials(self) -> None:
        return None  # The mock needs no credentials.

    def estimate_cost(self, request: VideoRequest) -> CostEstimate:
        check_request(request, MOCK_CAPABILITIES)
        return CostEstimate(Decimal("0"), is_mock=True, basis="mock provider: no charge")

    def submit(self, request: VideoRequest) -> str:
        check_request(request, MOCK_CAPABILITIES)
        job_id = "mock-" + request_hash(request)[:24]
        # Identical resubmits return the same job: no duplicate work or charge.
        if job_id not in self._jobs:
            self._jobs[job_id] = request
            self._poll_counts[job_id] = 0
        return job_id

    def _require(self, job_id: str) -> VideoRequest:
        try:
            return self._jobs[job_id]
        except KeyError:
            raise ProviderError(ErrorCode.PROVIDER, "unknown job id") from None

    def poll(self, job_id: str) -> JobStatus:
        self._require(job_id)
        if job_id in self._cancelled:
            return JobStatus(job_id, JobState.CANCELLED)
        self._poll_counts[job_id] += 1
        count = self._poll_counts[job_id]
        if count < self._polls_until_done:
            return JobStatus(job_id, JobState.RUNNING, progress=count / self._polls_until_done)
        if self._fail_with is not None:
            error = ProviderError(self._fail_with, "simulated mock failure")
            return JobStatus(job_id, JobState.FAILED, progress=1.0, error=error)
        return JobStatus(job_id, JobState.SUCCEEDED, progress=1.0)

    def download(self, job_id: str, dest_dir: Path) -> Path:
        request = self._require(job_id)
        if self.poll(job_id).state is not JobState.SUCCEEDED:
            raise ProviderError(ErrorCode.PROVIDER, "job has not succeeded")
        dest_dir.mkdir(parents=True, exist_ok=True)
        out = dest_dir / f"{job_id}.mock.json"
        body = {
            "mock": True,
            "notice": "Placeholder output from the offline mock provider. Not a video.",
            "job_id": job_id,
            "model_id": MOCK_CAPABILITIES.model_id,
            "request_sha256": request_hash(request),
            "duration_s": request.duration_s,
            "resolution": request.resolution,
            "aspect_ratio": request.aspect_ratio,
        }
        out.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return out

    def cancel(self, job_id: str) -> None:
        self._require(job_id)
        self._cancelled.add(job_id)
