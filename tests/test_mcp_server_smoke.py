import importlib.util

import pytest


def test_server_imports_if_sdk_present():
    if importlib.util.find_spec("mcp") is None:
        pytest.skip("mcp SDK not installed")
    import lethe.mcp.server as s
    assert s.mcp is not None
