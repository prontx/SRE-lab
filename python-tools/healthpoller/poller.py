"""
Polls a set of HTTP endpoints on an interval, tracks consecutive
failures per endpoint, and reports state transitions (healthy <-> down).

Usage:
    python poller.py --config endpoints.json --interval 10
"""
import argparse
import json
import logging
import time
from dataclasses import dataclass, field

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("healthpoller")


@dataclass
class EndpointState:
    name: str
    url: str
    timeout: float = 5.0
    failure_threshold: int = 3
    consecutive_failures: int = 0
    is_down: bool = False

    def record_success(self) -> None:
        if self.is_down:
            log.warning("RECOVERED: %s (%s)", self.name, self.url)
        self.consecutive_failures = 0
        self.is_down = False

    def record_failure(self, reason: str) -> None:
        self.consecutive_failures += 1
        log.warning(
            "check failed: %s (%s) — %s [%d/%d]",
            self.name, self.url, reason,
            self.consecutive_failures, self.failure_threshold,
        )
        if (
            self.consecutive_failures >= self.failure_threshold
            and not self.is_down
        ):
            self.is_down = True
            log.error("DOWN: %s (%s) after %d consecutive failures",
                       self.name, self.url, self.consecutive_failures)


def check_endpoint(state: EndpointState) -> None:
    """Perform one health check and update state. Never raises."""
    try:
        resp = requests.get(state.url, timeout=state.timeout)
        if resp.status_code == 200:
            state.record_success()
        else:
            state.record_failure(f"HTTP {resp.status_code}")
    except requests.exceptions.Timeout:
        state.record_failure("timeout")
    except requests.exceptions.ConnectionError as e:
        state.record_failure(f"connection error: {e}")
    except requests.exceptions.RequestException as e:
        state.record_failure(f"request error: {e}")


def load_endpoints(config_path: str) -> list[EndpointState]:
    with open(config_path) as f:
        raw = json.load(f)
    return [
        EndpointState(
            name=e["name"],
            url=e["url"],
            timeout=e.get("timeout", 5.0),
            failure_threshold=e.get("failure_threshold", 3),
        )
        for e in raw
    ]


def run(config_path: str, interval: float, iterations: int | None = None) -> None:
    endpoints = load_endpoints(config_path)
    log.info("monitoring %d endpoint(s), interval=%ss", len(endpoints), interval)

    count = 0
    while iterations is None or count < iterations:
        for ep in endpoints:
            check_endpoint(ep)
        count += 1
        if iterations is None or count < iterations:
            time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="path to endpoints JSON")
    parser.add_argument("--interval", type=float, default=10.0)
    parser.add_argument("--iterations", type=int, default=None,
                         help="stop after N rounds (omit to run forever)")
    args = parser.parse_args()
    run(args.config, args.interval, args.iterations)


if __name__ == "__main__":
    main()