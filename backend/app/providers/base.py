"""Provider-neutral video generation contract.

Mirrors docs/API_INTEGRATION.md. Capabilities are declared per provider and never
assumed: anything a provider does not declare is treated as unsupported.
"""

from __future__ import annotations

import abc
import enum
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path


class ErrorCode(enum.StrEnum):
    AUTH = "AUTH"
    BILLING = "BILLING"
    QUOTA = "QUOTA"
    UNSUPPORTED_FEATURE = "UNSUPPORTED_FEATURE"
    POLICY = "POLICY"
    TIMEOUT = "TIMEOUT"
    PROVIDER = "PROVIDER"
    NETWORK = "NETWORK"


class ProviderError(Exception):
    """Normalized provider error. Messages must already be redacted."""

    def __init__(self, code: ErrorCode, message: str, *, retryable: bool = False) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.retryable = retryable


@dataclass(frozen=True)
class Capabilities:
    provider_id: str
    model_id: str
    is_mock: bool
    min_duration_s: int
    max_duration_s: int
    resolutions: tuple[str, ...]
    aspect_ratios: tuple[str, ...]
    max_reference_images: int = 0
    supports_reference_video: bool = False
    supports_audio_input: bool = False
    supports_native_audio_output: bool = False
    supports_cancel: bool = False
    supports_balance_query: bool = False


@dataclass(frozen=True)
class VideoRequest:
    prompt: str
    duration_s: int
    resolution: str
    aspect_ratio: str
    reference_image_paths: tuple[Path, ...] = ()
    reference_video_paths: tuple[Path, ...] = ()
    audio_reference_paths: tuple[Path, ...] = ()
    idempotency_key: str | None = None


@dataclass(frozen=True)
class CostEstimate:
    """amount_usd is None when the price is unknown; the UI must say so."""

    amount_usd: Decimal | None
    is_mock: bool
    basis: str


class JobState(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobStatus:
    job_id: str
    state: JobState
    progress: float = 0.0
    error: ProviderError | None = None
    metadata: dict[str, str] = field(default_factory=dict)


def check_request(request: VideoRequest, caps: Capabilities) -> None:
    """Reject requests that use features the provider has not declared."""

    def unsupported(message: str) -> ProviderError:
        return ProviderError(ErrorCode.UNSUPPORTED_FEATURE, message)

    if not request.prompt.strip():
        raise unsupported("prompt must not be empty")
    if not caps.min_duration_s <= request.duration_s <= caps.max_duration_s:
        raise unsupported(
            f"duration {request.duration_s}s outside {caps.min_duration_s}-{caps.max_duration_s}s"
        )
    if request.resolution not in caps.resolutions:
        raise unsupported(f"resolution {request.resolution!r} not supported")
    if request.aspect_ratio not in caps.aspect_ratios:
        raise unsupported(f"aspect ratio {request.aspect_ratio!r} not supported")
    if len(request.reference_image_paths) > caps.max_reference_images:
        raise unsupported(f"at most {caps.max_reference_images} reference images")
    if request.reference_video_paths and not caps.supports_reference_video:
        raise unsupported("reference video input not supported")
    if request.audio_reference_paths and not caps.supports_audio_input:
        raise unsupported("audio/voice reference input not supported")


class VideoProvider(abc.ABC):
    @abc.abstractmethod
    def capabilities(self) -> Capabilities: ...

    @abc.abstractmethod
    def validate_credentials(self) -> None:
        """Raise ProviderError(AUTH) if credentials are missing or invalid."""

    @abc.abstractmethod
    def estimate_cost(self, request: VideoRequest) -> CostEstimate: ...

    @abc.abstractmethod
    def submit(self, request: VideoRequest) -> str:
        """Submit a generation and return a job id."""

    @abc.abstractmethod
    def poll(self, job_id: str) -> JobStatus: ...

    @abc.abstractmethod
    def download(self, job_id: str, dest_dir: Path) -> Path: ...

    def cancel(self, job_id: str) -> None:
        raise ProviderError(ErrorCode.UNSUPPORTED_FEATURE, "cancel not supported")
