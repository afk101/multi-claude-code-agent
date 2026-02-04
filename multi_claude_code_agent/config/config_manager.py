"""
配置管理模块

负责读取和验证 Agent 配置。
"""

import json
import os
from pathlib import Path
from typing import Any

from ..constants import DEFAULT_PORTS, DEFAULT_CONFIG_FILENAME


class AgentConfig:
    """
    Agent 配置类

    封装单个 Agent 的配置信息。
    """

    def __init__(self, name: str, port: int, system_prompt: str, enabled: bool = True):
        """
        初始化 Agent 配置。

        :param name: Agent 名称/模型标识
        :param port: 代理服务监听端口
        :param system_prompt: 系统提示词
        :param enabled: 是否启用该 Agent
        """
        self.name = name
        self.port = port
        self.system_prompt = system_prompt
        self.enabled = enabled

    def to_dict(self) -> dict[str, Any]:
        """
        将配置转换为字典格式。

        :return: 配置字典
        """
        return {
            "name": self.name,
            "port": self.port,
            "system_prompt": self.system_prompt,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentConfig":
        """
        从字典创建 Agent 配置。

        :param data: 配置字典
        :return: AgentConfig 实例
        """
        return cls(
            name=data["name"],
            port=data["port"],
            system_prompt=data.get("system_prompt", ""),
            enabled=data.get("enabled", True),
        )


class ConfigManager:
    """
    配置管理器

    负责加载、验证和管理 Agent 配置。
    """

    def __init__(self, config_path: str | None = None):
        """
        初始化配置管理器。

        :param config_path: 配置文件路径，如果为 None 则使用默认路径
        """
        self.config_path = self._resolve_config_path(config_path)
        self.agents: list[AgentConfig] = []

    def _resolve_config_path(self, config_path: str | None) -> Path:
        """
        解析配置文件路径。

        :param config_path: 用户指定的配置文件路径
        :return: 解析后的配置文件路径
        """
        if config_path:
            return Path(config_path)

        # 默认使用包内的配置文件
        return Path(__file__).parent / DEFAULT_CONFIG_FILENAME

    def load(self) -> list[AgentConfig]:
        """
        加载配置文件。

        :return: Agent 配置列表
        :raises FileNotFoundError: 配置文件不存在
        :raises ValueError: 配置文件格式无效
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._validate_config(data)

        self.agents = [
            AgentConfig.from_dict(agent_data)
            for agent_data in data.get("agents", [])
        ]

        return self.agents

    def _validate_config(self, data: dict[str, Any]) -> None:
        """
        验证配置数据的有效性。

        :param data: 配置数据
        :raises ValueError: 配置数据无效
        """
        if not isinstance(data, dict):
            raise ValueError("配置文件格式无效：必须是 JSON 对象")

        if "agents" not in data:
            raise ValueError("配置文件格式无效：缺少 'agents' 字段")

        if not isinstance(data["agents"], list):
            raise ValueError("配置文件格式无效：'agents' 必须是数组")

        for i, agent_data in enumerate(data["agents"]):
            self._validate_agent_config(agent_data, i)

    def _validate_agent_config(self, agent_data: dict[str, Any], index: int) -> None:
        """
        验证单个 Agent 配置的有效性。

        :param agent_data: Agent 配置数据
        :param index: Agent 在列表中的索引
        :raises ValueError: Agent 配置无效
        """
        if not isinstance(agent_data, dict):
            raise ValueError(f"Agent #{index} 配置无效：必须是 JSON 对象")

        if "name" not in agent_data:
            raise ValueError(f"Agent #{index} 配置无效：缺少 'name' 字段")

        if "port" not in agent_data:
            raise ValueError(f"Agent #{index} 配置无效：缺少 'port' 字段")

        if not isinstance(agent_data["port"], int):
            raise ValueError(f"Agent #{index} 配置无效：'port' 必须是整数")

    def get_enabled_agents(self) -> list[AgentConfig]:
        """
        获取所有启用的 Agent 配置。

        :return: 启用的 Agent 配置列表
        """
        return [agent for agent in self.agents if agent.enabled]

    @staticmethod
    def create_default_config(output_path: str | None = None) -> Path:
        """
        创建默认配置文件。

        :param output_path: 输出路径，如果为 None 则输出到当前目录
        :return: 创建的配置文件路径
        """
        if output_path:
            path = Path(output_path)
        else:
            path = Path.cwd() / DEFAULT_CONFIG_FILENAME

        default_config = {
            "agents": [
                {
                    "name": name,
                    "port": port,
                    "system_prompt": "You are an expert analyst. Provide comprehensive and well-structured analysis with a focus on practical solutions, using Chinese.",
                    "enabled": True,
                }
                for name, port in DEFAULT_PORTS.items()
            ]
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)

        return path
