"""
Anthropic API 封装模块

提供 LLMClient 类，负责：
1. 调用 Anthropic Chat API（含 tool use）
2. 处理 tool_use 循环：收到 tool_use 块 → 执行工具 → 返回 tool_result → 继续对话
3. 支持"终止工具"模式：当 Claude 调用指定工具时，视为结构化输出并终止循环
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import anthropic
from rich.console import Console

console = Console()

# 最大 tool_use 循环轮次，防止无限循环
MAX_TOOL_ROUNDS = 10


class LLMClient:
    """
    Anthropic API 的薄封装层。

    参数:
        api_key:     Anthropic API Key
        model:       模型名称，如 'claude-sonnet-4-5'
        max_tokens:  单次调用最大输出 token 数
        temperature: 采样温度，知识类任务建议 0.3
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-5",
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> None:
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def run_tool_loop(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_dispatcher: Callable[[str, dict[str, Any]], str],
        system: Optional[str] = None,
        terminal_tool: Optional[str] = None,
    ) -> tuple[Optional[str], Optional[dict[str, Any]]]:
        """
        执行 tool_use 循环，直到 Claude 返回纯文本或调用终止工具。

        流程：
            发送消息 → 收到响应
            ├─ 有 tool_use 块 且 是终止工具 → 返回 (None, tool_input)
            ├─ 有 tool_use 块 且 是普通工具 → 执行并追加 tool_result → 继续循环
            └─ 无 tool_use 块（纯文本）      → 返回 (text, None)

        参数:
            messages:        初始消息列表（[{"role": "user", "content": "..."}]）
            tools:           Claude 工具 schema 列表
            tool_dispatcher: 接收 (tool_name, tool_input) 并返回结果字符串的函数
            system:          系统 prompt（可选）
            terminal_tool:   终止工具名称；Claude 调用该工具时停止循环并返回其输入

        返回:
            (final_text, terminal_tool_input)
            - 纯文本结束时：(text, None)
            - 终止工具结束时：(None, tool_input_dict)
        """
        current_messages = list(messages)

        for round_num in range(MAX_TOOL_ROUNDS):
            # 构造 API 调用参数
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "tools": tools,
                "messages": current_messages,
            }
            if system:
                kwargs["system"] = system

            # 调用 Anthropic API
            try:
                response = self.client.messages.create(**kwargs)
            except anthropic.AuthenticationError:
                raise RuntimeError("Anthropic API Key 无效，请检查 .env 文件中的 ANTHROPIC_API_KEY")
            except anthropic.RateLimitError:
                raise RuntimeError("Anthropic API 请求频率超限，请稍后重试")
            except anthropic.APIError as e:
                raise RuntimeError(f"Anthropic API 调用失败: {e}") from e

            # 解析响应内容块
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            text_blocks = [b for b in response.content if b.type == "text"]

            # 没有 tool_use → 纯文本结束
            if not tool_use_blocks:
                final_text = "\n".join(b.text for b in text_blocks)
                return final_text, None

            # 检查是否有终止工具
            if terminal_tool:
                terminal_blocks = [b for b in tool_use_blocks if b.name == terminal_tool]
                if terminal_blocks:
                    # 取第一个终止工具调用的输入作为结构化输出
                    return None, terminal_blocks[0].input

            # 执行所有普通工具，收集 tool_result
            tool_results = []
            for block in tool_use_blocks:
                console.print(f"  [dim]工具调用: {block.name}[/dim]")
                result_text = tool_dispatcher(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })

            # 将本轮 assistant 回复和 tool_result 追加到消息列表
            current_messages.append({"role": "assistant", "content": response.content})
            current_messages.append({"role": "user", "content": tool_results})

        # 超过最大轮次
        raise RuntimeError(f"tool_use 循环超过最大轮次 ({MAX_TOOL_ROUNDS})，可能存在无限调用问题")

    def simple_chat(
        self,
        user_message: str,
        system: Optional[str] = None,
    ) -> str:
        """
        不带工具的简单单轮对话。

        参数:
            user_message: 用户消息文本
            system:       系统 prompt（可选）

        返回:
            Claude 的文本回复
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": user_message}],
        }
        if system:
            kwargs["system"] = system

        try:
            response = self.client.messages.create(**kwargs)
        except anthropic.APIError as e:
            raise RuntimeError(f"Anthropic API 调用失败: {e}") from e

        return "\n".join(b.text for b in response.content if b.type == "text")
