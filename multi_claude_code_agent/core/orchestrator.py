"""
任务编排模块

负责并发初始化和执行多个 Agent 任务。
"""

import asyncio
import logging

from ..config.config_manager import AgentConfig
from .agent import AgentResult, AgentWrapper

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    任务编排器

    负责并发执行多个 Agent 任务，采用部分成功模式。
    """

    def __init__(self, agent_configs: list[AgentConfig], cwd: str):
        """
        初始化任务编排器。

        :param agent_configs: Agent 配置列表
        :param cwd: 工作目录
        """
        self.agent_configs = agent_configs
        self.cwd = cwd

    async def _run_agent(self, agent_config: AgentConfig, query: str) -> AgentResult:
        """
        运行单个 Agent。

        :param agent_config: Agent 配置
        :param query: 用户查询
        :return: Agent 执行结果
        """
        wrapper = AgentWrapper(agent_config, self.cwd)
        return await wrapper.run(query)

    async def run_all(self, query: str) -> list[AgentResult]:
        """
        并发执行所有 Agent。

        采用部分成功模式：即使某些 Agent 执行失败，
        也会继续执行其他 Agent 并返回所有结果。

        :param query: 用户查询
        :return: 所有 Agent 的执行结果列表
        """
        if not self.agent_configs:
            logger.warning("没有配置任何 Agent")
            return []

        logger.info(f"开始并发执行 {len(self.agent_configs)} 个 Agent...")

        # 创建所有 Agent 的执行任务
        tasks = [
            self._run_agent(config, query)
            for config in self.agent_configs
        ]

        # 并发执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=False)

        # 统计执行结果
        success_count = sum(1 for r in results if r.status == "success")
        error_count = sum(1 for r in results if r.status == "error")
        timeout_count = sum(1 for r in results if r.status == "timeout")

        logger.info(
            f"执行完成: {success_count} 成功, {error_count} 失败, {timeout_count} 超时"
        )

        return results

    def get_successful_results(self, results: list[AgentResult]) -> list[AgentResult]:
        """
        获取成功的执行结果。

        :param results: 所有执行结果
        :return: 成功的执行结果列表
        """
        return [r for r in results if r.status == "success"]

    def get_failed_results(self, results: list[AgentResult]) -> list[AgentResult]:
        """
        获取失败的执行结果（包括错误和超时）。

        :param results: 所有执行结果
        :return: 失败的执行结果列表
        """
        return [r for r in results if r.status != "success"]


async def run_parallel_analysis(
    agent_configs: list[AgentConfig],
    query: str,
    cwd: str,
) -> list[AgentResult]:
    """
    运行并行分析的便捷函数。

    :param agent_configs: Agent 配置列表
    :param query: 用户查询
    :param cwd: 工作目录
    :return: 所有 Agent 的执行结果列表
    """
    orchestrator = Orchestrator(agent_configs, cwd)
    return await orchestrator.run_all(query)
