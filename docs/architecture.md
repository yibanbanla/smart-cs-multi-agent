# 架构设计文档

## 1. 系统总体架构

### 1.1 架构概览

系统采用 Supervisor 编排模式，由一个中心 Agent 负责路由、状态维护、错误兜底和结果汇总。

```text
                          ┌─────────────────────────┐
                          │     用户 (Web/App/API)   │
                          └────────────┬────────────┘
                                       │ HTTP
                                       ▼
                          ┌─────────────────────────┐
                          │   API Gateway (FastAPI) │
                          │   认证 | 限流 | 日志      │
                          └────────────┬────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                   │
                    ▼                  ▼                   ▼
            ┌──────────┐     ┌──────────────┐    ┌──────────────┐
            │ 短期记忆   │     │  Supervisor  │    │ 全链路追踪    │
            │  (Redis)  │◄───►│   编排 Agent  │───►│OpenTelemetry │
            └──────────┘     └──────┬───────┘    └──────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
            ┌──────────┐   ┌──────────┐   ┌──────────────┐
            │ 意图路由   │   │ 知识检索  │   │   合规审查    │
            │  Agent    │   │  Agent   │   │    Agent     │
            └──────────┘   └────┬─────┘   └──────────────┘
                                 │
                                 ▼
                        ┌────────────────┐
                        │ MCP 工具协议层  │
                        │ 订单 / 工单 /   │
                        │ 风控 / 知识查询 │
                        └────────────────┘
```

### 1.2 编排流程

```text
用户请求
    │
    ▼
[Supervisor] ──── 分析意图 ──── [意图路由 Agent]
    │
    ├── knowledge_rag ───────► [知识检索 Agent]
    ├── ticket_handler ──────► [工单处理 Agent]
    └── compliance_check ────► [合规审查 Agent]
                                      │
                                      ▼
                            [Supervisor 汇总最终响应]
```

## 2. 核心组件设计

### 2.1 Agent 职责

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| Supervisor | 编排调度、结果汇总 | 用户消息 + 全局 State | 路由决策 + 最终回复 |
| 意图路由 | 意图分类 | 用户消息 | intent 标签 |
| 知识检索 | RAG 问答 | 用户问题 | 基于文档的回答 |
| 工单处理 | 工单 CRUD | 用户需求 | 工单号 + 状态 |
| 合规审查 | 内容审查 | Agent 输出内容 | 通过/不通过 |

### 2.2 State 设计

```python
class AgentState(TypedDict):
    messages: list[BaseMessage]
    user_id: str
    session_id: str
    intent: str
    sub_results: dict[str, Any]
    compliance_passed: bool
    final_response: str
    current_agent: str
    retry_count: int
```

### 2.3 分层记忆

```text
┌──────────────────────────────────────────────┐
│                  应用层                       │
├──────────────────────────────────────────────┤
│ 工作记忆 (Working Memory)                    │
│ ├── 存储: 进程内存                           │
│ ├── 生命周期: 单次请求                       │
│ └── 用途: 当前推理状态、路由上下文            │
├──────────────────────────────────────────────┤
│ 短期记忆 (Short-term Memory)                 │
│ ├── 存储: Redis                              │
│ ├── 生命周期: TTL 30 分钟                    │
│ └── 用途: 多轮对话上下文                     │
├──────────────────────────────────────────────┤
│ 长期记忆 (Long-term Memory)                  │
│ ├── 存储: FAISS                              │
│ ├── 生命周期: 持久化                         │
│ └── 用途: 知识库、历史工单、用户画像          │
└──────────────────────────────────────────────┘
```

## 3. RAG 检索流程

```text
用户问题
  ↓
Query 改写
  ↓
Embedding 向量化
  ↓
向量检索 Top-K
  ↓
重排序
  ↓
上下文注入
  ↓
LLM 生成
  ↓
合规审查
  ↓
最终回答
```

## 4. MCP 工具协议

系统通过 MCP 风格接口统一描述和调用外部工具。

```json
{
  "name": "order_query",
  "description": "查询订单信息",
  "inputSchema": {
    "type": "object",
    "properties": {
      "order_id": { "type": "string" }
    }
  }
}
```

当前工具包括：

- `order_query`
- `knowledge_search`
- `ticket_create`
- `risk_check`

## 5. 全链路追踪

### Span 层级

```text
[Root] user_request
  ├── supervisor.route_decision
  ├── knowledge_rag.process
  │   ├── rag.query_rewrite
  │   ├── rag.vector_search
  │   └── rag.generate_answer
  ├── compliance_checker.process
  │   ├── compliance.rule_check
  │   └── compliance.llm_check
  └── supervisor.synthesize
```

### 关键指标

| 指标 | 说明 | 告警阈值 |
|------|------|---------|
| P99 延迟 | 99% 请求响应时间 | > 5s |
| Agent 错误率 | 各 Agent 失败比例 | > 5% |
| Token 消耗/请求 | 平均每请求 Token 数 | > 5000 |
| 路由准确率 | 意图路由正确率 | < 85% |
| 合规通过率 | 审查通过比例 | 异常波动需关注 |

## 6. 技术选型说明

### 6.1 为什么选 LangGraph

- 显式 State 管理，适合多步骤协作
- 条件边与图编排能力强
- 支持检查点与恢复
- 与 Python 生态结合自然，便于接入 RAG 和观测体系

### 6.2 为什么选 FastAPI

- 异步支持完善
- 接口定义简洁
- 文档自动生成

### 6.3 为什么选 FAISS + Redis

- FAISS 适合本地开发和轻量知识库检索
- Redis 适合存放会话级短期上下文
- 两者组合足以支撑当前项目的验证和演示场景
