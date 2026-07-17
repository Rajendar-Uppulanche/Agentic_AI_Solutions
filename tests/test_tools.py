import asyncio

from tools.ip_reputation import get_ip_reputation
from tools.registry import execute_tool
from tools.splunk import query_splunk


def test_get_ip_reputation_returns_mock():
    out = asyncio.run(get_ip_reputation("10.20.30.40"))
    assert "10.20.30.40" in out


def test_query_splunk_returns_summary():
    out = asyncio.run(query_splunk("index=security src_ip=10.0.0.1"))
    assert "events" in out


class _FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _FakeToolCall:
    def __init__(self, name, arguments):
        self.function = _FakeFunction(name, arguments)


def test_execute_tool_unknown_tool_returns_error_not_raise():
    tc = _FakeToolCall("does_not_exist", "{}")
    out = asyncio.run(execute_tool(tc))
    assert out.startswith("ERROR:")


def test_execute_tool_bad_json_returns_error_not_raise():
    tc = _FakeToolCall("get_ip_reputation", "{not valid json")
    out = asyncio.run(execute_tool(tc))
    assert out.startswith("ERROR:")
