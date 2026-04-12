"""
配置加载模块

负责从 .env 文件加载 API key,从 config.yaml 加载运行时配置,
并将两者合并为统一的 AppConfig 对象供全局使用。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console

console = Console()

# 项目根目录(此文件位于 exam_in_mind/ 下,上一级即根目录)
ROOT_DIR = Path(__file__).parent.parent


class EnvSettings(BaseSettings):
    """从 .env 文件读取 API Key(敏感信息)。"""

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,   # 系统环境变量为空字符串时忽略,改用 .env 文件中的值
        extra="ignore",
    )

    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    brave_search_api_key: Optional[str] = Field(default=None, alias="BRAVE_SEARCH_API_KEY")


class LLMConfig:
    """LLM 相关配置。"""

    def __init__(self, data: dict) -> None:
        self.model: str = data.get("model", "claude-sonnet-4-5")
        self.max_tokens: int = data.get("max_tokens", 4096)
        self.temperature: float = data.get("temperature", 0.3)


class SearchConfig:
    """搜索相关配置。"""

    def __init__(self, data: dict) -> None:
        self.enabled: bool = data.get("enabled", True)
        self.provider: str = data.get("provider", "brave")
        self.results_per_query: int = data.get("results_per_query", 5)


class TreeConfig:
    """知识树构建参数。"""

    def __init__(self, data: dict) -> None:
        self.max_depth: int = data.get("max_depth", 3)
        self.level_1_count_hint: str = data.get("level_1_count_hint", "8-12")
        self.level_2_count_hint: str = data.get("level_2_count_hint", "4-8")
        self.level_3_count_hint: str = data.get("level_3_count_hint", "3-6")


class OutputConfig:
    """输出相关配置。"""

    def __init__(self, data: dict) -> None:
        self.base_dir: str = data.get("base_dir", "./output")
        self.formats: list[str] = data.get("formats", ["mkdocs", "markdown"])
        self.language: str = data.get("language", "zh")


class LoggingConfig:
    """日志相关配置。"""

    def __init__(self, data: dict) -> None:
        self.level: str = data.get("level", "INFO")
        self.file: str = data.get("file", "run.log")


class AppConfig:
    """
    应用全局配置对象,合并 .env 与 config.yaml 的所有设置。

    参数:
        yaml_path: config.yaml 文件路径,默认为项目根目录下的 config.yaml
        verbose: 是否打印详细配置信息

    属性:
        anthropic_api_key: Anthropic API Key
        brave_search_api_key: Brave Search API Key
        llm: LLM 配置
        search: 搜索配置
        tree: 知识树参数
        output: 输出配置
        logging: 日志配置
    """

    def __init__(
        self,
        yaml_path: Optional[Path] = None,
        verbose: bool = False,
    ) -> None:
        # 1. 加载 .env 中的 API key
        env = EnvSettings()
        self.anthropic_api_key: Optional[str] = env.anthropic_api_key
        self.brave_search_api_key: Optional[str] = env.brave_search_api_key

        # 2. 加载 config.yaml
        yaml_path = yaml_path or (ROOT_DIR / "config.yaml")
        raw = self._load_yaml(yaml_path)

        self.llm = LLMConfig(raw.get("llm", {}))
        self.search = SearchConfig(raw.get("search", {}))
        self.tree = TreeConfig(raw.get("tree", {}))
        self.output = OutputConfig(raw.get("output", {}))
        self.logging = LoggingConfig(raw.get("logging", {}))

        # 3. 打印加载结果(verbose 模式)
        if verbose:
            self._print_summary()

    def _load_yaml(self, path: Path) -> dict:
        """加载 YAML 配置文件,文件不存在时返回空字典并提示。"""
        if not path.exists():
            console.print(f"[yellow]警告: 未找到配置文件 {path},使用默认值。[/yellow]")
            return {}
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def validate_api_keys(self, require_brave: bool = True) -> bool:
        """
        校验 API key 是否已配置。

        参数:
            require_brave: 是否要求 Brave Search API key

        返回:
            所有必需 key 均已配置时返回 True,否则打印提示并返回 False
        """
        ok = True

        if not self.anthropic_api_key:
            console.print(
                "[red]错误: 未找到 ANTHROPIC_API_KEY。[/red]\n"
                "请复制 .env.example 为 .env 并填写你的 API key。"
            )
            ok = False

        if require_brave and not self.brave_search_api_key:
            console.print(
                "[yellow]警告: 未找到 BRAVE_SEARCH_API_KEY。[/yellow]\n"
                "搜索功能将被禁用,考纲将由模型内置知识生成。"
            )
            # Brave key 缺失降级处理,不阻断流程

        return ok

    def _print_summary(self) -> None:
        """打印当前配置摘要(verbose 模式使用)。"""
        console.print("\n[bold cyan]=== Exam-in-Mind 配置摘要 ===[/bold cyan]")
        console.print(f"  模型         : [green]{self.llm.model}[/green]")
        console.print(f"  最大 token   : {self.llm.max_tokens}")
        console.print(f"  温度         : {self.llm.temperature}")
        console.print(f"  搜索启用     : {self.search.enabled}")
        console.print(f"  输出目录     : {self.output.base_dir}")
        console.print(f"  输出语言     : {self.output.language}")
        console.print(f"  知识树深度   : {self.tree.max_depth}")
        console.print(
            f"  Anthropic Key: {'[green]已配置[/green]' if self.anthropic_api_key else '[red]未配置[/red]'}"
        )
        console.print(
            f"  Brave Key    : {'[green]已配置[/green]' if self.brave_search_api_key else '[yellow]未配置[/yellow]'}"
        )
        console.print()
