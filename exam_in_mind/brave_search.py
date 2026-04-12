"""
Brave Search API 封装模块

将 Brave Search API 包装为简单的 Python 函数。
支持直接运行：python -m exam_in_mind.brave_search "查询关键词"
"""

from __future__ import annotations

import sys
from typing import Optional

import httpx
from rich.console import Console

console = Console()

# Brave Search API 端点
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


def search(
    query: str,
    count: int = 5,
    api_key: Optional[str] = None,
) -> list[dict]:
    """
    调用 Brave Search API 搜索网页。

    参数:
        query: 搜索关键词
        count: 返回结果数量，默认 5，最大 20
        api_key: Brave Search API Key；若为 None，从环境变量读取

    返回:
        list[dict]，每项包含 title、url、description 三个字段。
        API 失败时返回空列表（不抛出异常），同时打印警告。
    """
    # 获取 API key
    # api_key=None 表示"未指定，从配置读取"；api_key="" 表示"明确不传 key"
    resolved_key = _get_api_key() if api_key is None else (api_key or None)
    if not resolved_key:
        console.print("[yellow]警告: 未找到 BRAVE_SEARCH_API_KEY，跳过搜索。[/yellow]")
        return []

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": resolved_key,
    }
    params = {
        "q": query,
        "count": min(count, 20),  # Brave API 上限为 20
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(BRAVE_SEARCH_URL, headers=headers, params=params)

        # 处理常见 HTTP 错误
        if response.status_code == 401:
            console.print("[red]Brave Search 错误: API key 无效（401）。[/red]")
            return []
        if response.status_code == 422:
            console.print("[red]Brave Search 错误: 请求参数有误（422）。[/red]")
            return []
        if response.status_code == 429:
            console.print("[yellow]Brave Search 警告: 请求频率超限（429），跳过本次搜索。[/yellow]")
            return []
        if response.status_code != 200:
            console.print(f"[yellow]Brave Search 警告: 返回状态码 {response.status_code}，跳过搜索。[/yellow]")
            return []

        data = response.json()
        return _parse_results(data)

    except httpx.TimeoutException:
        console.print("[yellow]Brave Search 警告: 请求超时，跳过搜索。[/yellow]")
        return []
    except httpx.RequestError as e:
        console.print(f"[yellow]Brave Search 警告: 网络错误 ({e})，跳过搜索。[/yellow]")
        return []
    except Exception as e:
        console.print(f"[yellow]Brave Search 警告: 未知错误 ({e})，跳过搜索。[/yellow]")
        return []


def _parse_results(data: dict) -> list[dict]:
    """
    解析 Brave Search API 返回的 JSON，提取 title/url/description。

    参数:
        data: Brave API 返回的原始 JSON dict

    返回:
        list[dict]，每项包含 title、url、description
    """
    results = []
    web_results = data.get("web", {}).get("results", [])

    for item in web_results:
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "description": item.get("description", ""),
        })

    return results


def _get_api_key() -> Optional[str]:
    """
    从配置系统读取 Brave Search API key。

    返回:
        API key 字符串，或 None
    """
    try:
        from exam_in_mind.config import AppConfig
        cfg = AppConfig()
        return cfg.brave_search_api_key or None
    except Exception:
        return None


def format_results_for_llm(results: list[dict]) -> str:
    """
    将搜索结果格式化为适合传给 LLM 的文本。

    参数:
        results: search() 返回的结果列表

    返回:
        格式化的字符串，每条结果包含标题、URL、摘要
    """
    if not results:
        return "（无搜索结果）"

    lines = []
    for i, item in enumerate(results, 1):
        lines.append(f"[{i}] {item['title']}")
        lines.append(f"    URL: {item['url']}")
        if item["description"]:
            lines.append(f"    摘要: {item['description']}")
        lines.append("")

    return "\n".join(lines).strip()


# 支持直接运行：python -m exam_in_mind.brave_search "查询词"
if __name__ == "__main__":
    # Windows UTF-8 输出修复
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    if len(sys.argv) < 2:
        console.print("[red]用法: python -m exam_in_mind.brave_search \"查询词\"[/red]")
        sys.exit(1)

    query_str = sys.argv[1]
    count_arg = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    console.print(f"搜索: [bold]{query_str}[/bold]（请求 {count_arg} 条）\n")
    items = search(query_str, count=count_arg)

    if not items:
        console.print("[yellow]未返回任何结果。[/yellow]")
    else:
        for idx, r in enumerate(items, 1):
            console.print(f"[bold cyan][{idx}][/bold cyan] {r['title']}")
            console.print(f"    [dim]{r['url']}[/dim]")
            if r["description"]:
                console.print(f"    {r['description']}")
            console.print()
