"""Offline mock smoke test: ``python -m app.smoke [output_dir]``.

Runs estimate -> submit -> poll -> download against the mock provider.
No network, no credentials, no cost.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from app.providers import JobState, MockVideoProvider, VideoRequest


def run(output_dir: Path) -> Path:
    provider = MockVideoProvider()
    provider.validate_credentials()
    request = VideoRequest(
        prompt="A lighthouse keeper walks along a stormy cliff at dusk.",
        duration_s=8,
        resolution="720p",
        aspect_ratio="16:9",
    )
    estimate = provider.estimate_cost(request)
    print(f"estimate: ${estimate.amount_usd} ({estimate.basis})")
    job_id = provider.submit(request)
    print(f"submitted: {job_id}")
    while True:
        status = provider.poll(job_id)
        print(f"poll: {status.state} {status.progress:.0%}")
        if status.state is not JobState.RUNNING:
            break
    if status.state is not JobState.SUCCEEDED:
        raise SystemExit(f"mock job ended in {status.state}")
    out = provider.download(job_id, output_dir)
    print(f"downloaded: {out}")
    return out


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        run(Path(argv[1]))
    else:
        with tempfile.TemporaryDirectory() as tmp:
            run(Path(tmp))
    print("MOCK SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
