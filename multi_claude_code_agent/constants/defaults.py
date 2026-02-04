"""
默认常量定义

包含端口、超时时间、默认 Prompt 等常量。
"""

# 代理端口配置
DEFAULT_PORTS = {
    "copilotcode-13": 4900,
    "lyra-flash-6": 4901,
    "cortex-15": 4902,
    "cortex-12": 4903,
}

# 端口范围
PORT_RANGE_START = 4900
PORT_RANGE_END = 4903

# 超时配置（单位：秒）
PROXY_STARTUP_TIMEOUT = 30  # 代理启动超时
HEALTH_CHECK_INTERVAL = 0.5  # 健康检查间隔
AGENT_EXECUTION_TIMEOUT = 500  # Agent 执行超时,单位s

# 健康检查配置
HEALTH_CHECK_MAX_RETRIES = 60  # 最大重试次数 (30秒 / 0.5秒)

# 默认系统提示词
DEFAULT_SYSTEM_PROMPTS = {
    "copilotcode-13": "You are an expert analyst. Provide comprehensive and well-structured analysis with a focus on practical solutions, using Chinese.",
    "lyra-flash-6": "You are an expert analyst. Provide comprehensive and well-structured analysis with a focus on practical solutions, using Chinese.",
    "cortex-15": "You are an expert analyst. Provide comprehensive and well-structured analysis with a focus on practical solutions, using Chinese.",
    "cortex-12": "You are an expert analyst. Provide comprehensive and well-structured analysis with a focus on practical solutions, using Chinese.",
}

# 模型固定值（实际模型由后端代理决定）
FIXED_MODEL_NAME = "claude-opus-4.5"

# 权限模式
PERMISSION_MODE = "plan"

# CLI 相关常量
CLI_COMMAND_NAME = "mca"
DEFAULT_CONFIG_FILENAME = "agents_config.json"

# 输出格式常量
OUTPUT_SEPARATOR = "=" * 50
OUTPUT_SUBSEPARATOR = "-" * 50
