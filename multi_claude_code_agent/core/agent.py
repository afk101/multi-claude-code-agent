"""
Agent 封装模块

封装 claude-agent-sdk 的调用逻辑，包含容错处理。
"""

import asyncio
import logging
from dataclasses import dataclass

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import AssistantMessage, TextBlock

from ..config.config_manager import AgentConfig
from ..constants import AGENT_EXECUTION_TIMEOUT, FIXED_MODEL_NAME, PERMISSION_MODE, ALLOWED_TOOLS

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """
    Agent 执行结果

    存储单个 Agent 的执行结果信息。
    """
    model: str
    status: str  # "success" | "error" | "timeout"
    result: str | None = None
    error: str | None = None


class AgentWrapper:
    """
    Agent 封装类

    封装 claude-agent-sdk 的调用逻辑，提供统一的接口和容错处理。
    """

    def __init__(self, agent_config: AgentConfig, cwd: str):
        """
        初始化 Agent 封装。

        :param agent_config: Agent 配置
        :param cwd: 工作目录
        """
        self.agent_config = agent_config
        self.cwd = cwd

    def _build_options(self) -> ClaudeAgentOptions:
        """
        构建 Agent 选项。

        :return: ClaudeAgentOptions 实例
        """
        options = ClaudeAgentOptions(
            model=FIXED_MODEL_NAME,  # 固定值，实际模型由后端代理决定
            permission_mode=PERMISSION_MODE,  # 设置为 acceptEdits 模式
            allowed_tools=ALLOWED_TOOLS,  # 显式设置允许的工具
            system_prompt=self.agent_config.system_prompt,
            continue_conversation=False,
            cwd=self.cwd,
            include_partial_messages=True,
            env={
                # 关键：通过端口区分不同的代理服务
                "ANTHROPIC_BASE_URL": f"http://localhost:{self.agent_config.port}"
            }
        )
        return options

    async def _execute_query(self, query: str) -> str:
        """
        执行查询并收集响应。

        :param query: 用户查询
        :return: 完整的响应文本
        """
        options = self._build_options()
        full_response: list[str] = []

        async with ClaudeSDKClient(options=options) as client:
            # 发送查询
            await client.query(query)

            # 处理响应，只关注 AssistantMessage 中的 TextBlock
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            if block.text:
                                full_response.append(block.text)

        # 拼接所有文本作为最终结果
        return "".join(full_response)

    async def run(self, query: str, timeout: float | None = None) -> AgentResult:
        """
        运行 Agent 并返回结果。

        采用部分成功模式：如果执行失败或超时，不会抛出异常，
        而是返回包含错误信息的 AgentResult。

        :param query: 用户查询
        :param timeout: 超时时间（秒），默认使用 AGENT_EXECUTION_TIMEOUT
        :return: Agent 执行结果
        """
        if timeout is None:
            timeout = AGENT_EXECUTION_TIMEOUT

        logger.info(f"Agent [{self.agent_config.name}] 开始执行查询...")

        try:
            # 使用 asyncio.timeout 进行超时控制
            async with asyncio.timeout(timeout):
                result_text = await self._execute_query(query)

            logger.info(f"Agent [{self.agent_config.name}] 执行成功")

            return AgentResult(
                model=self.agent_config.name,
                status="success",
                result=result_text,
            )

        except asyncio.TimeoutError:
            error_msg = f"执行超时（{timeout}秒）"
            logger.warning(f"Agent [{self.agent_config.name}] {error_msg}")

            return AgentResult(
                model=self.agent_config.name,
                status="timeout",
                error=error_msg,
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Agent [{self.agent_config.name}] 执行出错: {error_msg}")

            return AgentResult(
                model=self.agent_config.name,
                status="error",
                error=error_msg,
            )


async def run_single_agent(agent_config: AgentConfig, user_query: str, cwd: str) -> AgentResult:
    """
    运行单个 Agent 的便捷函数。

    :param agent_config: Agent 配置
    :param user_query: 用户查询
    :param cwd: 工作目录
    :return: Agent 执行结果
    """
    wrapper = AgentWrapper(agent_config, cwd)
    return await wrapper.run(user_query)
