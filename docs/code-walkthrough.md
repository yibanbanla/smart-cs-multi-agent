# 代码讲解文档

> 本文档聚焦当前仓库中的 Python 实现，帮助你快速理解核心模块和它们之间的协作关系。

---

## 1. Supervisor 编排

文件：[agents/supervisor.py](D:/develop/smart-cs-multi-agent/agents/supervisor.py)

### 1.1 State 定义

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    session_id: str
    intent: str
    sub_results: dict[str, Any]
    compliance_passed: bool
    final_response: str
    current_agent: str
    retry_count: int
```

这个状态对象是整个图编排的共享数据总线。每个节点都从这里读取上下文，并把自己的结果写回去。

### 1.2 Graph 构建

```python
graph = StateGraph(AgentState)

graph.add_node("supervisor_route", supervisor.route_decision)
graph.add_node("knowledge_rag", knowledge_agent.process)
graph.add_node("ticket_handler", ticket_agent.process)
graph.add_node("compliance_check", compliance_agent.process)
graph.add_node("synthesize", supervisor.synthesize_response)
```

这里的关键点有两个：

- `supervisor_route` 是统一入口，负责路由决策
- `compliance_check` 是汇聚节点，确保业务回复会经过审查

### 1.3 路由逻辑

`route_to_agent()` 根据 `intent` 字段把状态送往不同业务节点。这样做的好处是路由规则集中，后续扩展新的业务 Agent 时改动面更小。

## 2. RAG 知识检索

文件：[agents/knowledge_rag.py](D:/develop/smart-cs-multi-agent/agents/knowledge_rag.py)

典型流程如下：

```python
original_query = messages[-1].content
rewritten_query = await self.rewrite_query(original_query)
raw_docs = await self.retrieve_documents(rewritten_query, top_k=5)
reranked_docs = await self.rerank_documents(rewritten_query, raw_docs, top_k=3)
answer = await self.generate_answer(original_query, reranked_docs)
```

这个实现把检索拆成了改写、召回、重排、生成四步，目的很明确：先提高召回率，再压缩上下文，最后生成更稳的答案。

## 3. 合规审查

文件：[agents/compliance_checker.py](D:/develop/smart-cs-multi-agent/agents/compliance_checker.py)

项目里的合规审查走的是两阶段思路：

1. 规则引擎先做低成本快筛
2. LLM 再做语义级深审

这样可以兼顾响应速度与准确性，也更符合金融客服场景对兜底能力的要求。

## 4. MCP 工具服务

文件：[mcp/mcp_server.py](D:/develop/smart-cs-multi-agent/mcp/mcp_server.py)

### 4.1 工具注册

```python
@server.register(
    name="order_query",
    description="查询订单信息",
    input_schema={...},
    category="order",
)
async def order_query(order_id: str = "", user_id: str = "") -> dict:
    ...
```

工具用装饰器声明，注册信息和处理函数绑定在一起，后续做工具发现和调用都比较顺。

### 4.2 JSON-RPC 处理

```python
if method == "tools/list":
    result = self.list_tools(category=params.get("category"))
elif method == "tools/call":
    call_result = await self.call_tool(tool_name, arguments)
```

这部分承担的是 MCP 风格协议层，把统一入口映射到具体工具执行。

## 5. FastAPI 入口

文件：[api/main.py](D:/develop/smart-cs-multi-agent/api/main.py)

应用启动时会初始化：

- OpenTelemetry 追踪
- Supervisor 图
- 工作记忆、短期记忆、长期记忆
- MCP 工具集

`/api/chat` 是主入口，它会：

1. 接收用户消息
2. 写入短期记忆
3. 构造初始 State
4. 调用 LangGraph 图执行
5. 返回最终回复

## 6. 追踪能力

文件：[tracing/otel_config.py](D:/develop/smart-cs-multi-agent/tracing/otel_config.py)

项目通过装饰器给 Agent 调用打点，核心收益是：

- 定位慢节点
- 查看路由链路
- 统计失败率和耗时
- 辅助排查线上问题

## 7. 阅读顺序建议

第一次看这个项目，推荐顺序：

1. [api/main.py](D:/develop/smart-cs-multi-agent/api/main.py)
2. [agents/supervisor.py](D:/develop/smart-cs-multi-agent/agents/supervisor.py)
3. [agents/knowledge_rag.py](D:/develop/smart-cs-multi-agent/agents/knowledge_rag.py)
4. [agents/compliance_checker.py](D:/develop/smart-cs-multi-agent/agents/compliance_checker.py)
5. [mcp/mcp_server.py](D:/develop/smart-cs-multi-agent/mcp/mcp_server.py)
