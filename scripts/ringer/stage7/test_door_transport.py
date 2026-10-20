from urllib.error import HTTPError

from door_transport import SpendBudget, counted_provider

from storygame.runtime.cloudflare import NarrationProviderError


def test_counted_provider_preserves_provider_error_after_http_failure() -> None:
    class FakeProvider:
        def _request(self, _payload: dict[str, object]) -> object:
            error = HTTPError("https://example.invalid", 503, "Service Unavailable", {}, None)
            raise error

    provider = FakeProvider()
    budget = SpendBudget(2)

    try:
        with counted_provider(provider, budget):
            try:
                provider._request({"_request_budget": "narration"})
            except HTTPError as error:
                raise NarrationProviderError("narration service rejected the turn", 502) from error
    except NarrationProviderError as error:
        assert error.status_code == 502
    else:
        raise AssertionError("the provider error was not raised")

    assert budget.events == [
        {
            "kind": "cloudflare",
            "sequence": 1,
            "status": "failed",
            "detail": "narration",
            "error": "HTTPError",
        }
    ]
