"""
Brave Search 模块测试

测试范围：
1. 正常查询（mock HTTP 响应）
2. API key 错误处理（401 响应）
3. 限流处理（429 响应）
4. 网络超时处理
5. 结果格式化函数
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from exam_in_mind.brave_search import (
    format_results_for_llm,
    search,
    _parse_results,
)


# ── 测试数据 ──────────────────────────────────────────────────────────────────

MOCK_BRAVE_RESPONSE = {
    "web": {
        "results": [
            {
                "title": "AP Calculus BC – Course and Exam Description",
                "url": "https://apcentral.collegeboard.org/courses/ap-calculus-bc",
                "description": "The official AP Calculus BC CED from College Board.",
            },
            {
                "title": "AP Calculus BC Exam - AP Students",
                "url": "https://apstudents.collegeboard.org/courses/ap-calculus-bc/assessment",
                "description": "Learn about the AP Calculus BC exam format and scoring.",
            },
        ]
    }
}


# ── 正常查询测试 ──────────────────────────────────────────────────────────────

def test_search_returns_results():
    """正常查询应返回包含 title/url/description 的结果列表。"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_BRAVE_RESPONSE

    with patch("exam_in_mind.brave_search.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        results = search("AP Calculus BC official CED", count=5, api_key="fake-key")

    assert len(results) == 2
    assert results[0]["title"] == "AP Calculus BC – Course and Exam Description"
    assert results[0]["url"] == "https://apcentral.collegeboard.org/courses/ap-calculus-bc"
    assert "CED" in results[0]["description"]

    # 验证每条结果都有三个必需字段
    for item in results:
        assert "title" in item
        assert "url" in item
        assert "description" in item


# ── API Key 错误处理测试 ──────────────────────────────────────────────────────

def test_search_returns_empty_on_401():
    """API key 无效（401）时应返回空列表，不崩溃。"""
    mock_response = MagicMock()
    mock_response.status_code = 401

    with patch("exam_in_mind.brave_search.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        results = search("test query", api_key="invalid-key")

    assert results == []


# ── 限流处理测试 ──────────────────────────────────────────────────────────────

def test_search_returns_empty_on_429():
    """限流（429）时应返回空列表，不崩溃。"""
    mock_response = MagicMock()
    mock_response.status_code = 429

    with patch("exam_in_mind.brave_search.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        results = search("test query", api_key="fake-key")

    assert results == []


# ── 网络超时测试 ──────────────────────────────────────────────────────────────

def test_search_returns_empty_on_timeout():
    """网络超时时应返回空列表，不崩溃。"""
    import httpx

    with patch("exam_in_mind.brave_search.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.TimeoutException("timeout")
        mock_client_cls.return_value = mock_client

        results = search("test query", api_key="fake-key")

    assert results == []


# ── 无 API key 测试 ───────────────────────────────────────────────────────────

def test_search_returns_empty_without_api_key():
    """没有 API key 时应返回空列表，不崩溃。"""
    results = search("test query", api_key="")
    assert results == []


# ── 结果解析测试 ──────────────────────────────────────────────────────────────

def test_parse_results_handles_empty_web():
    """Brave 返回无 web.results 时，解析应返回空列表。"""
    results = _parse_results({})
    assert results == []

    results = _parse_results({"web": {}})
    assert results == []

    results = _parse_results({"web": {"results": []}})
    assert results == []


def test_parse_results_handles_missing_fields():
    """结果条目缺少字段时，应用空字符串填充，不崩溃。"""
    data = {
        "web": {
            "results": [
                {"title": "Only Title"},  # 缺 url 和 description
            ]
        }
    }
    results = _parse_results(data)
    assert len(results) == 1
    assert results[0]["title"] == "Only Title"
    assert results[0]["url"] == ""
    assert results[0]["description"] == ""


# ── 格式化函数测试 ────────────────────────────────────────────────────────────

def test_format_results_for_llm_empty():
    """空结果列表应返回占位文本。"""
    assert format_results_for_llm([]) == "（无搜索结果）"


def test_format_results_for_llm_normal():
    """正常结果应包含编号、标题、URL。"""
    results = [
        {"title": "Test Title", "url": "https://example.com", "description": "A description"},
    ]
    formatted = format_results_for_llm(results)
    assert "[1]" in formatted
    assert "Test Title" in formatted
    assert "https://example.com" in formatted
    assert "A description" in formatted
