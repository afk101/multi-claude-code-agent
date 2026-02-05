"""
CLI 入口模块

负责解析参数，调用 ProxyManager 启动服务，然后调用 Orchestrator。
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from . import __version__
from .config.config_manager import ConfigManager
from .constants import CLI_COMMAND_NAME
from .core.orchestrator import run_parallel_analysis
from .core.proxy_manager import ProxyManager
from .utils.formatter import format_results

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """
    创建命令行参数解析器。

    :return: ArgumentParser 实例
    """
    parser = argparse.ArgumentParser(
        prog=CLI_COMMAND_NAME,
        description="多模型并行代理分析工具 (Multi-Model Agent Analyzer)",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # analyze 子命令
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="并发分析问题",
    )
    analyze_parser.add_argument(
        "prompt",
        type=str,
        help="要分析的问题或提示",
    )
    analyze_parser.add_argument(
        "--cwd",
        type=str,
        default=None,
        help="指定工作目录（默认：当前目录）",
    )
    analyze_parser.add_argument(
        "--no-summary",
        action="store_true",
        help="不显示执行摘要",
    )

    # init 子命令
    init_parser = subparsers.add_parser(
        "init",
        help="初始化默认配置文件",
    )
    init_parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出路径（默认：当前目录）",
    )

    # version 子命令（作为子命令的替代方式）
    subparsers.add_parser(
        "version",
        help="显示版本信息",
    )

    return parser


async def run_analyze(args: argparse.Namespace) -> int:
    """
    执行分析命令。

    :param args: 命令行参数
    :return: 退出码
    """
    # 解析工作目录
    cwd = args.cwd if args.cwd else os.getcwd()
    cwd = str(Path(cwd).resolve())

    logger.info(f"工作目录: {cwd}")

    # 加载配置
    try:
        config_manager = ConfigManager(cwd=cwd)
        agents = config_manager.load()
        enabled_agents = config_manager.get_enabled_agents()
    except FileNotFoundError as e:
        logger.error(f"配置加载失败: {e}")
        print(f"错误: {e}")
        return 1
    except ValueError as e:
        logger.error(f"配置验证失败: {e}")
        print(f"错误: {e}")
        return 1

    if not enabled_agents:
        logger.error("没有启用的 Agent")
        print("错误: 配置中没有启用的 Agent")
        return 1

    logger.info(f"已加载 {len(enabled_agents)} 个启用的 Agent")

    # 创建代理管理器
    proxy_manager = ProxyManager()

    try:
        # 启动所有代理
        print(f"正在启动 {len(enabled_agents)} 个代理服务...")
        await proxy_manager.start_all_proxies(enabled_agents)

        # 检查是否有就绪的代理
        ready_proxies = proxy_manager.get_ready_proxies()
        failed_proxies = proxy_manager.get_failed_proxies()

        if failed_proxies:
            for proxy in failed_proxies:
                print(f"警告: 代理 [{proxy.name}] 启动失败: {proxy.error}")

        if not ready_proxies:
            print("错误: 所有代理都启动失败，无法继续执行")
            return 1

        print(f"{len(ready_proxies)} 个代理已就绪，开始分析...")

        # 只使用成功启动的代理对应的配置
        ready_agent_names = {p.name for p in ready_proxies}
        active_agents = [a for a in enabled_agents if a.name in ready_agent_names]

        # 执行并行分析
        results = await run_parallel_analysis(active_agents, args.prompt, cwd)

        # 格式化输出
        print()
        print(format_results(results, include_summary=not args.no_summary))

        # 根据结果返回退出码
        success_count = sum(1 for r in results if r.status == "success")
        if success_count == 0:
            return 1
        elif success_count < len(results):
            return 2  # 部分成功
        else:
            return 0

    finally:
        # 确保清理代理进程
        proxy_manager.stop_all_proxies()


def run_init(args: argparse.Namespace) -> int:
    """
    执行初始化命令。

    :param args: 命令行参数
    :return: 退出码
    """
    try:
        output_path = ConfigManager.create_default_config(args.output)
        print(f"配置文件已创建: {output_path}")
        return 0
    except Exception as e:
        logger.error(f"创建配置文件失败: {e}")
        print(f"错误: {e}")
        return 1


def run_version() -> int:
    """
    显示版本信息。

    :return: 退出码
    """
    print(f"{CLI_COMMAND_NAME} {__version__}")
    return 0


def main() -> None:
    """
    主入口函数。
    """
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    exit_code = 0

    if args.command == "analyze":
        exit_code = asyncio.run(run_analyze(args))
    elif args.command == "init":
        exit_code = run_init(args)
    elif args.command == "version":
        exit_code = run_version()
    else:
        parser.print_help()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
