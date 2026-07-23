from parser import parse_line, aggregate, to_prometheus, RouteMetrics

GOOD_LINE = '127.0.0.1 - - [10/Oct/2023:13:55:36 +0000] "GET /api/health HTTP/1.1" 200 512 0.014\n'
ERROR_LINE = '127.0.0.1 - - [10/Oct/2023:13:55:37 +0000] "GET /api/health HTTP/1.1" 500 128 0.201\n'
GARBAGE_LINE = 'this is not a log line at all\n'


def test_parse_line_extracts_fields():
    result = parse_line(GOOD_LINE)
    assert result == {"path": "/api/health", "status": 200, "duration": 0.014}


def test_parse_line_returns_none_for_garbage():
    assert parse_line(GARBAGE_LINE) is None


def test_route_metrics_error_rate():
    m = RouteMetrics()
    m.record(200, 0.01)
    m.record(500, 0.02)
    assert m.count == 2
    assert m.error_count == 1
    assert m.error_rate == 0.5


def test_route_metrics_zero_requests_no_division_error():
    m = RouteMetrics()
    assert m.error_rate == 0.0
    assert m.p50 == 0.0


def test_percentiles_are_sane():
    m = RouteMetrics()
    for d in [0.01, 0.02, 0.03, 0.04, 0.5]:
        m.record(200, d)
    assert m.p50 <= m.p99
    assert m.p99 == 0.5


def test_aggregate_skips_garbage_lines(capsys):
    routes = aggregate([GOOD_LINE, GARBAGE_LINE, ERROR_LINE])
    assert "/api/health" in routes
    assert routes["/api/health"].count == 2
    captured = capsys.readouterr()
    assert "skipped 1" in captured.err


def test_prometheus_output_format():
    routes = aggregate([GOOD_LINE, ERROR_LINE])
    output = to_prometheus(routes)
    assert "http_requests_total{path=\"/api/health\"} 2" in output
    assert "http_error_rate{path=\"/api/health\"} 0.5000" in output
    assert "# TYPE http_requests_total counter" in output