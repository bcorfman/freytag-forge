from __future__ import annotations

import urllib.request

import pytest


@pytest.fixture(autouse=True)
def _block_outbound_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _blocked_urlopen(*args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("Outbound network is disabled in tests. Mock urllib.request.urlopen in this test.")

    monkeypatch.setattr(urllib.request, "urlopen", _blocked_urlopen)
