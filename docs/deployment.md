# 部署指南

## 1. 本地开发环境

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入你的 LiteLLM API Key
python -m api.main
```

访问地址：

- Swagger UI：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

## 2. Docker 部署

### 单服务启动

```bash
docker build -t smart-cs-python .
docker run -p 8000:8000 --env-file .env smart-cs-python
```

### Docker Compose 一键启动

```bash
docker-compose up -d
```

默认会启动：

- `python-agent`
- `redis`
- `jaeger`

## 3. API 接口说明

### POST /api/chat

请求示例：

```json
{
  "message": "我想了解一下退款流程",
  "user_id": "user_001",
  "session_id": "optional-session-id"
}
```

响应示例：

```json
{
  "response": "关于退款流程，购买后 7 天内可申请无理由退款。",
  "session_id": "xxx",
  "intent": "knowledge_rag",
  "compliance_passed": true
}
```

### 其他接口

- `GET /api/history/{session_id}`：对话历史
- `GET /api/tools`：MCP 工具列表
- `POST /api/tools/call`：调用 MCP 工具
- `GET /api/metrics`：系统指标
- `GET /health`：健康检查

## 4. 环境变量说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| LITELLM_API_KEY | LiteLLM / OpenAI 兼容接口密钥 | 无 |
| LITELLM_PROFILE | 默认启用的聊天模型 profile | qwen_chat_27b |
| LITELLM_CHAT_PROFILE | 聊天模型 profile | qwen_chat_27b |
| LITELLM_EMBEDDING_PROFILE | 向量模型 profile | qwen_embedding_8b |
| LITELLM_RERANK_PROFILE | 重排模型 profile | qwen_rerank_8b |
| REDIS_URL | Redis 地址 | redis://localhost:6379/0 |
| FAISS_INDEX_PATH | FAISS 索引目录 | ./vector_store/faiss_index |
| OTEL_SERVICE_NAME | 追踪服务名 | smart-cs-multi-agent |
| OTEL_EXPORTER_OTLP_ENDPOINT | OTLP 端点 | http://localhost:4317 |

## 5. 部署建议

- 如需切换模型或代理地址，修改 [llm/model_config.json](D:/develop/smart-cs-multi-agent/llm/model_config.json)
- 如果希望不同环境切不同模型，优先使用环境变量 `LITELLM_PROFILE`
- 如果 chat、embedding、rerank 需要分别切换，使用 `LITELLM_CHAT_PROFILE`、`LITELLM_EMBEDDING_PROFILE`、`LITELLM_RERANK_PROFILE`
- 本地开发优先使用 FAISS + Redis
- 生产环境建议将 Redis、向量索引和追踪后端拆分为独立服务
- 如果不需要链路追踪，可关闭 Jaeger 和 OTLP 上报
