# 智能客服多Agent系统

> 面向金融/电商场景的 Python 多 Agent 客服项目，基于 LangGraph + FastAPI + MCP，附带架构说明、部署文档和面试材料。

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green)](https://github.com/langchain-ai/langgraph)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

## 项目简介

这是一个企业级风格的多 Agent 智能客服系统，核心目标是模拟真实业务中的咨询问答、知识检索、工单流转与合规审查流程。

系统采用 Supervisor 编排模式，由中心 Agent 负责路由和汇总，业务 Agent 分别处理知识检索、工单处理与合规检查。

## 核心能力

- Supervisor 统一编排多个业务 Agent
- 基于 RAG 的知识检索与回答生成
- 分层记忆系统：工作记忆、短期记忆、长期记忆
- MCP 工具协议：统一的工具注册、发现、调用接口
- OpenTelemetry 全链路追踪
- 面向金融场景的合规审查能力

## 技术栈

| 层次 | 技术选型 | 说明 |
|------|----------|------|
| 编排框架 | LangGraph | 多 Agent 状态编排 |
| API | FastAPI | REST 接口 |
| LLM | LiteLLM + OpenAI Compatible API | 路由、生成、审查 |
| 向量检索 | FAISS | 长期记忆与知识检索 |
| 缓存 | Redis | 短期记忆 |
| 追踪 | OpenTelemetry | 链路追踪与指标 |
| 协议 | MCP | 工具调用标准 |
| 容器 | Docker / Docker Compose | 本地部署 |

## 系统架构

```text
用户 (Web/App/API)
        │
        ▼
┌──────────────────────┐
│   API Gateway        │
│      FastAPI         │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│           Supervisor 编排 Agent          │
│  路由决策 / 状态维护 / 结果汇总 / 审查兜底 │
└──────┬──────────┬──────────┬─────────────┘
       │          │          │
       ▼          ▼          ▼
  ┌─────────┐┌─────────┐┌────────────┐
  │意图路由  ││知识检索  ││合规审查      │
  │Agent    ││Agent    ││Agent       │
  └─────────┘└─────────┘└────────────┘
                  │
                  ▼
           ┌──────────────────────┐
           │   MCP 工具协议层      │
           │ 订单查询 / 工单创建    │
           │ 风控检查 / 知识搜索    │
           └──────────────────────┘
```

## 快速开始

### 前置条件

- Python 3.11+
- 可选：Redis、Docker
- 一个可用的 LiteLLM / OpenAI 兼容接口密钥

### 方式一：本地运行

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# 编辑 .env，至少填写 LITELLM_API_KEY
python -m api.main
```

启动后可访问：

- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

### 方式二：Docker Compose

```bash
docker-compose up -d
```

启动后默认包含：

- 应用服务：`http://localhost:8000`
- Jaeger：`http://localhost:16686`

## 项目结构

```text
smart-cs-multi-agent/
├── README.md
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── llm.py
├── agents/
│   ├── supervisor.py
│   ├── intent_router.py
│   ├── knowledge_rag.py
│   ├── ticket_handler.py
│   └── compliance_checker.py
├── api/
│   └── main.py
├── mcp/
│   └── mcp_server.py
├── memory/
│   ├── working_memory.py
│   ├── short_term.py
│   └── long_term.py
├── tracing/
│   └── otel_config.py
└── docs/
    ├── architecture.md
    ├── code-walkthrough.md
    ├── deployment.md
    ├── project-plan.md
    └── interview/
```

## 模型配置

- 模型接入统一放在 [llm.py](D:/develop/smart-cs-multi-agent/llm.py)
- 模型参数统一放在 [llm/model_config.json](D:/develop/smart-cs-multi-agent/llm/model_config.json)

默认配置示例：

- 默认 chat profile：`qwen_chat_27b`
- 默认 embedding profile：`qwen_embedding_8b`
- 默认 rerank profile：`qwen_rerank_8b`
- 默认模型：`openai/Qwen/Qwen3.6-27B`
- 默认接口地址：`http://192.168.132.100:4000`
- 默认密钥环境变量：`LITELLM_API_KEY`

当前配置文件已支持多版本扩展，例如：

- `qwen_chat_27b`
- `qwen_embedding_8b`
- `qwen_rerank_8b`

切换默认模型有两种方式：

- 直接修改 [llm/model_config.json](D:/develop/smart-cs-multi-agent/llm/model_config.json) 里的 `default_profiles`
- 在环境变量中设置 `LITELLM_PROFILE`

如果要分别切三类模型，优先使用这些环境变量：

- `LITELLM_CHAT_PROFILE`
- `LITELLM_EMBEDDING_PROFILE`
- `LITELLM_RERANK_PROFILE`

## 关键代码入口

- 模型接入：[llm/llm.py](D:/develop/smart-cs-multi-agent/llm/llm.py)
- Supervisor 编排：[agents/supervisor.py](D:/develop/smart-cs-multi-agent/agents/supervisor.py)
- FastAPI 入口：[api/main.py](D:/develop/smart-cs-multi-agent/api/main.py)
- MCP 服务端：[mcp/mcp_server.py](D:/develop/smart-cs-multi-agent/mcp/mcp_server.py)
- 追踪配置：[tracing/otel_config.py](D:/develop/smart-cs-multi-agent/tracing/otel_config.py)

## 文档导航

- 架构设计：[docs/architecture.md](D:/develop/smart-cs-multi-agent/docs/architecture.md)
- 代码讲解：[docs/code-walkthrough.md](D:/develop/smart-cs-multi-agent/docs/code-walkthrough.md)
- 部署指南：[docs/deployment.md](D:/develop/smart-cs-multi-agent/docs/deployment.md)
- 面试材料：[docs/interview](D:/develop/smart-cs-multi-agent/docs/interview)

## 安全说明

- 项目不包含真实 API Key、Token 或密码
- 所有敏感配置通过环境变量注入
- `.env.example` 仅用于示例
- 不要将真实凭据提交到版本控制
