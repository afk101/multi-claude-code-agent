"""
代理管理模块

负责管理 ccc 代理进程的生命周期（启动、健康检查、优雅关闭）。
"""

import asyncio
import atexit
import logging
import signal
import socket
import subprocess
from dataclasses import dataclass
from typing import Any

from ..config.config_manager import AgentConfig
from ..constants import (
    HEALTH_CHECK_INTERVAL,
    HEALTH_CHECK_MAX_RETRIES,
    PROXY_STARTUP_TIMEOUT,
)

logger = logging.getLogger(__name__)


@dataclass
class ProxyProcess:
    """
    代理进程信息

    存储单个代理进程的相关信息。
    """
    name: str
    port: int
    process: subprocess.Popen | None = None
    is_ready: bool = False
    error: str | None = None


class ProxyManager:
    """
    代理进程管理器

    负责 ccc 代理进程的全生命周期管理，遵循"用时起，完时停"原则。
    """

    def __init__(self):
        """
        初始化代理管理器。
        """
        self._proxies: dict[str, ProxyProcess] = {}
        self._cleanup_registered = False

    def _build_proxy_command(self, agent_config: AgentConfig) -> list[str]:
        """
        构建代理启动命令。

        :param agent_config: Agent 配置
        :return: 命令参数列表
        """
        name = agent_config.name
        port = agent_config.port

        # 根据规格说明书构建命令：
        # 模型参数映射：Config 中的 name 字段值同时赋予 BIG_MODEL, MIDDLE_MODEL, SMALL_MODEL
        cmd = [
            "ccc",
            f"BIG_MODEL={name}",
            f"MIDDLE_MODEL={name}",
            f"SMALL_MODEL={name}",
            f"PORT={port}",
            "-auto"
        ]

        return cmd

    def _check_port_available(self, port: int) -> bool:
        """
        检查端口是否已被占用（服务是否就绪）。

        :param port: 端口号
        :return: 如果端口可连接（服务就绪）返回 True
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result == 0
        except socket.error:
            return False

    async def _wait_for_proxy_ready(self, proxy: ProxyProcess) -> bool:
        """
        等待代理服务就绪。

        :param proxy: 代理进程信息
        :return: 如果服务就绪返回 True
        """
        for _ in range(HEALTH_CHECK_MAX_RETRIES):
            # 检查进程是否还在运行
            if proxy.process and proxy.process.poll() is not None:
                proxy.error = f"代理进程异常退出，退出码: {proxy.process.returncode}"
                return False

            # 检查端口是否可连接
            if self._check_port_available(proxy.port):
                proxy.is_ready = True
                return True

            await asyncio.sleep(HEALTH_CHECK_INTERVAL)

        proxy.error = f"代理启动超时（{PROXY_STARTUP_TIMEOUT}秒）"
        return False

    async def start_proxy(self, agent_config: AgentConfig) -> ProxyProcess:
        """
        启动单个代理进程。

        :param agent_config: Agent 配置
        :return: 代理进程信息
        """
        proxy = ProxyProcess(
            name=agent_config.name,
            port=agent_config.port,
        )

        try:
            cmd = self._build_proxy_command(agent_config)
            logger.info(f"启动代理 [{agent_config.name}]: {' '.join(cmd)}")

            # 启动子进程，重定向输出以避免干扰主程序
            proxy.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,  # 创建新的进程组，便于清理
            )

            # 等待服务就绪
            is_ready = await self._wait_for_proxy_ready(proxy)

            if is_ready:
                logger.info(f"代理 [{agent_config.name}] 已就绪，端口: {agent_config.port}")
            else:
                logger.error(f"代理 [{agent_config.name}] 启动失败: {proxy.error}")

        except FileNotFoundError:
            proxy.error = "ccc 命令未找到，请确保已安装并在 PATH 中可用"
            logger.error(f"代理 [{agent_config.name}] 启动失败: {proxy.error}")
        except Exception as e:
            proxy.error = str(e)
            logger.error(f"代理 [{agent_config.name}] 启动失败: {proxy.error}")

        self._proxies[agent_config.name] = proxy
        return proxy

    async def start_all_proxies(self, agent_configs: list[AgentConfig]) -> dict[str, ProxyProcess]:
        """
        并发启动所有代理进程。

        :param agent_configs: Agent 配置列表
        :return: 代理进程字典
        """
        # 注册清理函数
        self._register_cleanup()

        # 并发启动所有代理
        tasks = [self.start_proxy(config) for config in agent_configs]
        await asyncio.gather(*tasks)

        return self._proxies

    def stop_proxy(self, proxy: ProxyProcess) -> None:
        """
        停止单个代理进程。

        :param proxy: 代理进程信息
        """
        if proxy.process is None:
            return

        try:
            # 首先尝试优雅关闭 (SIGTERM)
            proxy.process.terminate()
            try:
                proxy.process.wait(timeout=5)
                logger.info(f"代理 [{proxy.name}] 已优雅关闭")
            except subprocess.TimeoutExpired:
                # 如果超时，强制关闭 (SIGKILL)
                proxy.process.kill()
                proxy.process.wait()
                logger.warning(f"代理 [{proxy.name}] 被强制关闭")
        except Exception as e:
            logger.error(f"关闭代理 [{proxy.name}] 时出错: {e}")

    def stop_all_proxies(self) -> None:
        """
        停止所有代理进程。
        """
        logger.info("正在关闭所有代理进程...")

        for proxy in self._proxies.values():
            self.stop_proxy(proxy)

        self._proxies.clear()
        logger.info("所有代理进程已关闭")

    def _register_cleanup(self) -> None:
        """
        注册清理函数，确保在程序退出时关闭所有代理。
        """
        if self._cleanup_registered:
            return

        # 使用 atexit 确保正常退出时清理
        atexit.register(self.stop_all_proxies)

        # 处理 SIGTERM 和 SIGINT 信号
        def signal_handler(signum: int, frame: Any) -> None:
            logger.info(f"收到信号 {signum}，正在清理...")
            self.stop_all_proxies()
            # 重新发送信号以触发默认处理
            signal.signal(signum, signal.SIG_DFL)
            signal.raise_signal(signum)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        self._cleanup_registered = True

    def get_ready_proxies(self) -> list[ProxyProcess]:
        """
        获取所有已就绪的代理进程。

        :return: 已就绪的代理进程列表
        """
        return [proxy for proxy in self._proxies.values() if proxy.is_ready]

    def get_failed_proxies(self) -> list[ProxyProcess]:
        """
        获取所有启动失败的代理进程。

        :return: 启动失败的代理进程列表
        """
        return [proxy for proxy in self._proxies.values() if not proxy.is_ready]
