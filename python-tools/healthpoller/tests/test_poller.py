import responses
from poller import EndpointState, check_endpoint


def make_state(**overrides):
    defaults = dict(name="svc", url="http://svc.local/health", failure_threshold=3)
    defaults.update(overrides)
    return EndpointState(**defaults)


@responses.activate
def test_success_resets_failure_count():
    state = make_state(consecutive_failures=2)
    responses.add(responses.GET, state.url, status=200)
    check_endpoint(state)
    assert state.consecutive_failures == 0
    assert state.is_down is False


@responses.activate
def test_failure_increments_counter():
    state = make_state()
    responses.add(responses.GET, state.url, status=500)
    check_endpoint(state)
    assert state.consecutive_failures == 1
    assert state.is_down is False  # below threshold


@responses.activate
def test_marks_down_at_threshold():
    state = make_state(failure_threshold=2)
    responses.add(responses.GET, state.url, status=500)
    responses.add(responses.GET, state.url, status=500)
    check_endpoint(state)
    check_endpoint(state)
    assert state.is_down is True


@responses.activate
def test_recovery_after_down():
    state = make_state(failure_threshold=1, consecutive_failures=1, is_down=True)
    responses.add(responses.GET, state.url, status=200)
    check_endpoint(state)
    assert state.is_down is False


def test_timeout_counts_as_failure(monkeypatch):
    import requests
    state = make_state()

    def raise_timeout(*a, **kw):
        raise requests.exceptions.Timeout()

    monkeypatch.setattr("poller.requests.get", raise_timeout)
    check_endpoint(state)
    assert state.consecutive_failures == 1