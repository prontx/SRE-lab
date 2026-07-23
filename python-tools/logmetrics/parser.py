"""
Parses common log line, aggregates into RED-style metrics (rate, errors,
duration), and emits Prometheus text-exposition format.

Usage:
    python parser.py access.log > metrics.prom
"""
import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field

# Matches: combined/common log format
# 127.0.0.1 - - [10/Oct/2023:13:55:36 +0000] "GET /api/health HTTP/1.1" 200 512 0.014
LOG_PATTERN = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) \S+" '
    r'(?P<status>\d{3}) (?P<size>\d+|-) (?P<duration>[\d.]+)?'
)


@dataclass
class RouteMetrics:
    count: int = 0
    error_count: int = 0
    durations: list = field(default_factory=list)

    def record(self, status: int, duration: float | None) -> None:
        self.count += 1
        if status >= 500:
            self.error_count += 1
        if duration is not None:
            self.durations.append(duration)

    @property
    def error_rate(self) -> float:
        return self.error_count / self.count if self.count else 0.0

    @property
    def p50(self) -> float:
        return _percentile(self.durations, 0.5)

    @property
    def p99(self) -> float:
        return _percentile(self.durations, 0.99)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = int(len(s) * pct)
    return s[min(idx, len(s) - 1)]


def parse_line(line: str) -> dict | None:
    """Parse one log line into its fields, or None if it doesn't match."""
    m = LOG_PATTERN.match(line)
    if not m:
        return None
    d = m.groupdict()
    return {
        "path": d["path"],
        "status": int(d["status"]),
        "duration": float(d["duration"]) if d["duration"] else None,
    }


def aggregate(lines: list[str]) -> dict[str, RouteMetrics]:
    routes: dict[str, RouteMetrics] = defaultdict(RouteMetrics)
    skipped = 0
    for line in lines:
        parsed = parse_line(line)
        if parsed is None:
            skipped += 1
            continue
        routes[parsed["path"]].record(parsed["status"], parsed["duration"])
    if skipped:
        print(f"# skipped {skipped} unparseable line(s)", file=sys.stderr)
    return dict(routes)


def to_prometheus(routes: dict[str, RouteMetrics]) -> str:
    lines = []
    lines.append("# HELP http_requests_total Total requests per route")
    lines.append("# TYPE http_requests_total counter")
    for path, m in routes.items():
        lines.append(f'http_requests_total{{path="{path}"}} {m.count}')

    lines.append("# HELP http_error_rate Fraction of requests with 5xx status")
    lines.append("# TYPE http_error_rate gauge")
    for path, m in routes.items():
        lines.append(f'http_error_rate{{path="{path}"}} {m.error_rate:.4f}')

    lines.append("# HELP http_request_duration_seconds Request latency percentiles")
    lines.append("# TYPE http_request_duration_seconds gauge")
    for path, m in routes.items():
        lines.append(f'http_request_duration_seconds{{path="{path}",quantile="0.5"}} {m.p50:.4f}')
        lines.append(f'http_request_duration_seconds{{path="{path}",quantile="0.99"}} {m.p99:.4f}')

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logfile")
    args = parser.parse_args()

    with open(args.logfile) as f:
        routes = aggregate(f.readlines())

    print(to_prometheus(routes), end="")


if __name__ == "__main__":
    main()