# Multi-Claude-Code-Agent (MCA)

多模型并行代理分析工具 - 并发调用多个配置了不同底层模型核心的 Claude Code Agent，为用户提供更全面、多维度的参考答案。

## 功能特点

- **多模型并发支持**：同时连接 copilotcode-13、lyra-flash-6、cortex-15、cortex-12 等多个模型
- **独立配置管理**：每个 Agent 拥有独立的端口、系统提示词配置
- **自动代理管理**：自动启动和关闭代理进程，遵循"用时起，完时停"原则
- **容错处理**：采用部分成功模式，单个 Agent 失败不影响其他 Agent 执行
- **格式化输出**：清晰分隔各模型结果，便于对比分析

## 系统要求

- Python >= 3.13
- `ccc` 命令行工具（需提前安装并配置在 PATH 中）
- `claude-agent-sdk >= 0.1.27`

## 安装

### 使用 uv 安装（推荐）

```bash
# 克隆项目
git clone <repository-url>
cd multi-claude-code-agent  # 注意：进入项目根目录，不是 multi_claude_code_agent 子目录

# 安装依赖
uv sync

# 以可编辑模式安装
uv pip install -e .
```

### 验证安装

```bash
mca --version
# 输出: mca 0.1.0
```  

## 全局安装  
```bash
uv tool install --editable .
```  

## 使用方法

### 命令概览

```bash
mca --help
```

输出：
```
usage: mca [-h] [--version] {analyze,init,version} ...

多模型并行代理分析工具 (Multi-Model Agent Analyzer)

positional arguments:
  {analyze,init,version}
                        可用命令
    analyze             并发分析问题
    init                初始化默认配置文件
    version             显示版本信息

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
```

### 1. 初始化配置文件

首次使用前，可以生成一个默认配置文件：

```bash
# 在当前目录生成配置文件
mca init

# 指定输出路径
mca init --output ./my_config.json
```

生成的配置文件 `agents_config.json` 示例：

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

### 2. 并发分析问题

使用 `analyze` 命令并发调用多个模型分析同一个问题：

```bash
# 基本用法
mca analyze "如何优化这段代码的性能？"

# 指定工作目录
mca analyze "分析这个项目的架构设计" --cwd ./src

# 使用自定义配置文件
mca analyze "解释这个函数的作用" --config ./my_config.json

# 不显示执行摘要
mca analyze "代码审查建议" --no-summary
```

### 3. 查看版本信息

```bash
mca version
# 或
mca --version
```

## 输出格式

分析结果会以清晰的格式展示各模型的回答：

```text
模型 [copilotcode-13] 的回答：
--------------------------------------------------
[回答内容...]

==================================================

模型 [lyra-flash-6] 的回答：
--------------------------------------------------
[回答内容...]

==================================================

模型 [cortex-15] 的回答：
--------------------------------------------------
[回答内容...]

==================================================

模型 [cortex-12] 的回答：
--------------------------------------------------
[回答内容...]

==================================================
执行摘要
--------------------------------------------------
总计: 4 个模型
成功: 4
失败: 0
超时: 0
==================================================
```

## 配置说明

### 配置文件字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 模型名称/标识，用于日志显示和代理启动参数 |
| `port` | integer | 是 | 代理服务监听端口 (如 4900, 4901, 4902, 4903) |
| `system_prompt` | string | 否 | 针对该模型优化的系统提示词 |
| `enabled` | boolean | 否 | 是否启用该 Agent，默认为 `true` |

### 禁用特定模型

将配置中的 `enabled` 设置为 `false` 即可禁用该模型：

```json
{
  "name": "cortex-12",
  "port": 4903,
  "system_prompt": "...",
  "enabled": false
}
```

### 自定义系统提示词

可以根据需求修改 `system_prompt` 字段，优化模型的响应风格：

```json
{
  "name": "copilotcode-13",
  "port": 4900,
  "system_prompt": "你是一个专业的代码审查专家，专注于发现潜在的安全漏洞和性能问题。请用中文回答。",
  "enabled": true
}
```

## 退出码

| 退出码 | 说明 |
|--------|------|
| 0 | 所有 Agent 执行成功 |
| 1 | 所有 Agent 执行失败或配置错误 |
| 2 | 部分 Agent 执行成功 |

## 常见问题

### Q: 提示 "ccc 命令未找到"

确保 `ccc` 命令已安装并在系统 PATH 中可用：

```bash
which ccc
# 应输出 ccc 的安装路径
```

### Q: 代理启动超时

默认超时时间为 30 秒。如果网络较慢，可能需要等待更长时间。检查：
1. 网络连接是否正常
2. 端口是否被其他程序占用

### Q: 部分模型执行失败

工具采用部分成功模式，单个 Agent 失败不会影响其他 Agent。检查失败 Agent 的错误信息，通常是代理启动失败或执行超时。

## 项目结构

```
multi-claude-code-agent/
├── multi_claude_code_agent/
│   ├── __init__.py          # 包初始化，定义版本号
│   ├── cli.py                # CLI 入口模块
│   ├── config/
│   │   ├── __init__.py
│   │   ├── agents_config.json # 默认配置文件
│   │   └── config_manager.py  # 配置管理模块
│   ├── constants/
│   │   ├── __init__.py
│   │   └── defaults.py        # 常量定义
│   ├── core/
│   │   ├── __init__.py
│   │   ├── agent.py           # Agent 封装模块
│   │   ├── orchestrator.py    # 任务编排模块
│   │   └── proxy_manager.py   # 代理管理模块
│   └── utils/
│       ├── __init__.py
│       └── formatter.py       # 输出格式化模块
├── docs/
│   └── spec.md               # 规格说明书
├── pyproject.toml            # 项目配置
└── README.md                 # 本文件
```

## 开发

### 添加新模型

1. 编辑配置文件，添加新的 Agent 配置项
2. 确保端口不与现有配置冲突
3. 运行 `mca analyze` 测试新模型

### 运行开发版本

```bash
# 安装开发依赖
uv sync

# 以可编辑模式安装
uv pip install -e .

# 运行
mca analyze "测试问题"
```

## License

MIT
