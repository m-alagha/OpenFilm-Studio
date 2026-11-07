"""Video provider contract and adapters.

Only the mock provider exists at M0. Real adapters are added at M5, and only for
operations verified in docs/PROVIDER_CAPABILITIES.md.
"""

from app.providers.base import (
    Capabilities,
    CostEstimate,
    ErrorCode,
    JobState,
    JobStatus,
    ProviderError,
    VideoProvider,
    VideoRequest,
)
from app.providers.mock import MockVideoProvider

__all__ = [
    "Capabilities",
    "CostEstimate",
    "ErrorCode",
    "JobState",
    "JobStatus",
    "MockVideoProvider",
    "ProviderError",
    "VideoProvider",
    "VideoRequest",
]
