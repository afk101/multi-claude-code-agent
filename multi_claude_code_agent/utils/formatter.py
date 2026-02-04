"""
输出格式化模块

负责汇总展示结果，按规范格式输出。
"""

from ..constants import OUTPUT_SEPARATOR, OUTPUT_SUBSEPARATOR
from ..core.agent import AgentResult


class OutputFormatter:
    """
    输出格式化器

    负责将 Agent 执行结果格式化为用户友好的输出。
    """

    def __init__(self):
        """
        初始化输出格式化器。
        """
        self.separator = OUTPUT_SEPARATOR
        self.subseparator = OUTPUT_SUBSEPARATOR

    def format_single_result(self, result: AgentResult) -> str:
        """
        格式化单个 Agent 的执行结果。

        :param result: Agent 执行结果
        :return: 格式化后的字符串
        """
        lines = [
            f"模型 [{result.model}] 的回答：",
            self.subseparator,
        ]

        if result.status == "success":
            lines.append(result.result or "(无内容)")
        else:
            # 处理错误或超时情况
            status_text = "执行超时" if result.status == "timeout" else "执行失败"
            error_msg = result.error or "未知错误"
            lines.append(f"[{status_text}] {error_msg}")

        return "\n".join(lines)

    def format_all_results(self, results: list[AgentResult]) -> str:
        """
        格式化所有 Agent 的执行结果。

        :param results: Agent 执行结果列表
        :return: 格式化后的字符串
        """
        if not results:
            return "没有任何执行结果。"

        formatted_parts = []

        for i, result in enumerate(results):
            formatted_parts.append(self.format_single_result(result))

            # 在结果之间添加分隔符（最后一个结果后不添加）
            if i < len(results) - 1:
                formatted_parts.append("")
                formatted_parts.append(self.separator)
                formatted_parts.append("")

        return "\n".join(formatted_parts)

    def format_summary(self, results: list[AgentResult]) -> str:
        """
        格式化执行结果摘要。

        :param results: Agent 执行结果列表
        :return: 格式化后的摘要字符串
        """
        total = len(results)
        success_count = sum(1 for r in results if r.status == "success")
        error_count = sum(1 for r in results if r.status == "error")
        timeout_count = sum(1 for r in results if r.status == "timeout")

        lines = [
            self.separator,
            "执行摘要",
            self.subseparator,
            f"总计: {total} 个模型",
            f"成功: {success_count}",
            f"失败: {error_count}",
            f"超时: {timeout_count}",
            self.separator,
        ]

        return "\n".join(lines)


def format_results(results: list[AgentResult], include_summary: bool = True) -> str:
    """
    格式化结果的便捷函数。

    :param results: Agent 执行结果列表
    :param include_summary: 是否包含摘要
    :return: 格式化后的字符串
    """
    formatter = OutputFormatter()

    output_parts = [formatter.format_all_results(results)]

    if include_summary:
        output_parts.append("")
        output_parts.append(formatter.format_summary(results))

    return "\n".join(output_parts)
