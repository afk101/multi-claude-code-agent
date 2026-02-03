# 多模型并行代理分析工具 (Multi-Model Agent Analyzer) 规格说明书

## 1. 项目概述

本项目旨在开发一个命令行界面 (CLI) 工具，用于并发调用多个配置了不同底层模型核心的 Claude Code Agent。通过并行分析同一个问题，该工具能够聚合来自 "copilotcode-13", "lyra-flash-6", "cortex-15", "cortex-12" 等不同模型的观点和解决方案，为用户提供更全面、多维度的参考答案。

## 2. 核心需求

### 2.1 多模型并发支持
工具需支持同时连接并操作以下四种核心模型（通过不同的本地代理端口）：
- **Model A**: "copilotcode-13"
- **Model B**: "lyra-flash-6"
- **Model C**: "cortex-15"
- **Model D**: "cortex-12"

### 2.2 独立配置管理
每个 Agent 必须拥有独立的配置，包括：
- **Port**: 代理服务监听端口 (如 4900, 4901, 4902, 4903)。
- **System Prompt**: 针对该模型优化的系统提示词。
- **Model Core**: 对应的模型标识（用于日志或显示）。

### 2.3 核心技术栈
- **语言**: Python
- **核心依赖**: `claude-agent-sdk >= 0.1.27` （已安装）
- **运行模式**: CLI 命令行工具

## 3. 系统架构设计

系统遵循 SOLID 原则设计，模块职责单一。

### 3.1 模块划分

1.  **CLI Entrypoint (`multi_claude_code_agent/cli.py`)**: 负责解析参数，调用 ProxyManager 启动服务，然后调用 Orchestrator。
2.  **Proxy Manager (`core/proxy_manager.py`)**: **[新增]** 负责管理 `ccc` 代理进程的生命周期（启动、健康检查、优雅关闭）。
3.  **Config Manager (`config/`)**: 负责读取和验证 Agent 配置。
4.  **Agent Orchestrator (`core/orchestrator.py`)**: 负责并发初始化和执行多个 Agent 任务。
5.  **Agent Wrapper (`core/agent.py`)**: 封装 `claude-agent-sdk` 的调用逻辑。
6.  **Output Formatter (`utils/formatter.py`)**: 负责汇总展示结果。

### 3.2 数据流
User Input (CLI) -> Config Loader -> **Start Proxies (Proxy Manager)** -> **Wait for Ready** -> Orchestrator -> [Async Parallel Execution] -> Aggregation -> Console Output -> **Stop Proxies (Proxy Manager)**

## 4. 详细设计

### 4.1 配置文件设计 (`config/agents_config.json`)

```json
{
  "agents": [
    {
      "name": "copilotcode-13",
      "port": 4900,
      "system_prompt": "You are an expert analyst powered by copilotcode-13...",
      "enabled": true
    },
    {
      "name": "lyra-flash-6",
      "port": 4901,
      "system_prompt": "You are a fast and precise coding assistant...",
      "enabled": true
    },
    {
      "name": "cortex-15",
      "port": 4902,
      "system_prompt": "You are a deep thinking architecture expert...",
      "enabled": true
    },
    {
      "name": "cortex-12",
      "port": 4903,
      "system_prompt": "You are a balanced coding companion...",
      "enabled": true
    }
  ]
}
```

### 4.2 Agent 初始化与容错逻辑

基于 `claude-agent-sdk` 的封装。

**容错策略**：采用**部分成功**模式。
如果某个 Agent 启动失败或运行超时，系统**不应崩溃**，而是记录错误日志，并继续执行其他 Agent。最终结果中应包含成功 Agent 的回答，并将失败的 Agent 标记为"执行失败"。

```python
# 伪代码示例
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import AssistantMessage, TextBlock

async def run_single_agent(agent_config, user_query, cwd):
    try:
        # 构建 Agent 选项
        options = ClaudeAgentOptions(
            model="claude-opus-4.5",  # 固定值，实际模型由后端代理决定
            permission_mode="plan",   # 仅进行计划和分析模式
            system_prompt=agent_config["system_prompt"],
            continue_conversation=False,
            cwd=cwd,
            include_partial_messages=True,
            env={
                # 关键：通过端口区分不同的代理服务
                "ANTHROPIC_BASE_URL": f"http://localhost:{agent_config['port']}"
            }
        )

        full_response = []

        # 使用上下文管理器模式
        async with ClaudeSDKClient(options=options) as client:
            # 发送查询
            await client.query(user_query)

            # 处理响应，只关注 AssistantMessage 中的 TextBlock
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            if block.text:
                                full_response.append(block.text)

            # 拼接所有文本作为最终结果
            final_text = "".join(full_response)

            return {
                "model": agent_config["name"],
                "status": "success",
                "result": final_text
            }
    except Exception as e:
        return {
            "model": agent_config["name"],
            "status": "error",
            "error": str(e)
        }
```

### 4.3 CLI 接口与发布 (Bin 功能)

为了实现类似 npm `bin` 的功能（即安装后直接在终端使用命令），我们将在 `pyproject.toml` 中配置 Entry Point。

#### 4.3.1 命令定义
我们将定义命令 `mca` (Multi-Claude-Agent) 作为主入口。

使用示例：
```bash
mca analyze "如何优化这段代码？" --cwd ./src
```

#### 4.3.2 配置实现
在 `pyproject.toml` 中添加 `[project.scripts]`：

```toml
[project.scripts]
mca = "multi_claude_code_agent.cli:main"
```

这意味着系统需要一个 `multi_claude_code_agent/cli.py` 文件，其中包含一个 `main()` 函数作为入口点。

#### 4.3.3 参数解析
支持的子命令和参数：
- `analyze <prompt>`: 并发分析问题
  - `--cwd`: 指定工作目录 (可选，若未提供则默认继承当前终端执行时的路径)
  - `--config`: 指定配置文件路径 (可选)
- `init`: 初始化默认配置文件
- `version`: 显示版本信息

#### 4.3.4 输出格式规范
最终聚合输出需清晰分隔各模型结果：

```text
模型 [copilotcode-13] 的回答：
--------------------------------------------------
[回答内容...]

==================================================

模型 [lyra-flash-6] 的回答：
--------------------------------------------------
[回答内容...]

==================================================

...
```

## 5. 基础设施依赖与代理管理

### 5.1 自动代理管理 (Proxy Lifecycle)
工具负责全生命周期管理，遵循“用时起，完时停”原则。

1.  **启动阶段**:
    *   **环境**: 系统环境中 `ccc` 命令已可用且配置正确，无需进行存在性检查，不需要特定目录。
    *   读取配置中定义的模型和端口。
    *   **启动命令构造**:
        *   模型参数映射：Config 中的 `name` 字段值同时赋予 `BIG_MODEL`, `MIDDLE_MODEL`, `SMALL_MODEL`。
        *   调用方式：参数直接作为列表传递给 `subprocess`，而非环境变量。
        *   示例命令数组：
          ```python
          cmd = [
              "ccc",
              f"BIG_MODEL={name}",
              f"MIDDLE_MODEL={name}",
              f"SMALL_MODEL={name}",
              f"PORT={port}",
              "-auto"
          ]
          ```
    *   为每个配置并发启动子进程。
    *   **健康检查**: 轮询端口（如 `localhost:4900`）直到服务就绪或超时（默认超时 30秒）。若单个代理启动失败，记录错误但不中断整体流程（除非所有代理都失败）。
2.  **执行阶段**:
    *   所有成功启动的代理就绪后，开始执行 Agent 分析任务。
3.  **关闭阶段**:
    *   无论任务成功与否（包括 Ctrl+C 中断），都必须确保所有子进程被终止 (SIGTERM/SIGKILL)。
    *   使用 `atexit` 或 `try...finally` 块确保清理逻辑被执行。

### 5.2 外部命令依赖
- 系统需安装 `ccc` 命令行工具，并确保在 PATH 中可用。

## 6. 开发规范  
- **包管理**: 必须使用 `uv` 管理项目依赖。安装依赖请使用 `uv add <package>`，严禁使用 `pip`。  
- **常量**: 端口、默认 Prompt 等常量定义在 `constants/` 目录下。
- **扩展性**: 代码结构应允许轻松添加新的模型配置，而无需修改核心逻辑。
