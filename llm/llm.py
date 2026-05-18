"""
LiteLLM 模型接入层，同时支持 chat / embedding / rerank 三类模型
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import litellm
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage


DEFAULT_CONFIG_PATH = Path("llm/model_config.json")


class LiteLLMChatModel:
    """LiteLLM Chat 轻量包装。"""

    def __init__(
        self,
        model: str,
        api_base: str,
        api_key: str,
        temperature: float = 0,
        timeout: float = 30,
    ):
        self.model = model
        self.api_base = api_base
        self.api_key = api_key
        self.temperature = temperature
        self.timeout = timeout

    async def ainvoke(self, messages: list[BaseMessage]) -> AIMessage:
        response = await litellm.acompletion(
            model=self.model,
            api_base=self.api_base,
            api_key=self.api_key,
            temperature=self.temperature,
            timeout=self.timeout,
            messages=[self._to_litellm_message(message) for message in messages],
        )
        content = response.choices[0].message.content or ""
        return AIMessage(content=content)

    @staticmethod
    def _to_litellm_message(message: BaseMessage) -> dict[str, str]:
        if isinstance(message, SystemMessage):
            role = "system"
        elif isinstance(message, HumanMessage):
            role = "user"
        else:
            role = "assistant"
        return {"role": role, "content": str(message.content)}


class LiteLLMEmbeddingModel:
    """LiteLLM Embedding 轻量包装。"""

    def __init__(
        self,
        model: str,
        api_base: str,
        api_key: str,
        timeout: float = 30,
    ):
        self.model = model
        self.api_base = api_base
        self.api_key = api_key
        self.timeout = timeout

    async def aembed(self, inputs: str | list[str]) -> list[list[float]]:
        normalized_inputs = [inputs] if isinstance(inputs, str) else inputs
        response = await litellm.aembedding(
            model=self.model,
            api_base=self.api_base,
            api_key=self.api_key,
            timeout=self.timeout,
            input=normalized_inputs,
        )
        return [item["embedding"] for item in response.data]

    async def aembed_query(self, text: str) -> list[float]:
        return (await self.aembed(text))[0]


class LiteLLMRerankModel:
    """LiteLLM Rerank 轻量包装。"""

    def __init__(
        self,
        model: str,
        api_base: str,
        api_key: str,
        timeout: float = 30,
    ):
        self.model = model
        self.api_base = api_base
        self.api_key = api_key
        self.timeout = timeout

    async def arerank(
        self,
        query: str,
        documents: list[str] | list[dict[str, Any]],
        top_n: int | None = None,
        return_documents: bool = False,
    ) -> Any:
        return await litellm.arerank(
            model=self.model,
            api_base=self.api_base,
            api_key=self.api_key,
            timeout=self.timeout,
            query=query,
            documents=documents,
            top_n=top_n,
            return_documents=return_documents,
        )


def load_model_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """读取模型配置文件。"""
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_profile_config(config: dict[str, Any], profile_name: str) -> dict[str, Any]:
    """解析 profile，并合并公共 defaults。"""
    profiles = config.get("profiles", {})
    profile_config = profiles.get(profile_name)
    if profile_config is None:
        raise ValueError(f"未找到模型配置 profile: {profile_name}")

    defaults = config.get("defaults", {})
    return {**defaults, **profile_config}


def _resolve_profile_name(
    config: dict[str, Any],
    capability: str,
    profile: str | None = None,
) -> str:
    """解析某类能力对应的 profile 名称。"""
    if profile:
        return profile

    env_name = f"LITELLM_{capability.upper()}_PROFILE"
    env_value = os.getenv(env_name)
    if env_value:
        return env_value

    default_profiles = config.get("default_profiles", {})
    profile_name = default_profiles.get(capability)
    if profile_name:
        return profile_name

    raise ValueError(f"未找到 {capability} 的默认 profile 配置")


def _validate_profile_capability(profile_config: dict[str, Any], capability: str):
    """校验 profile 类型。"""
    profile_type = profile_config.get("type")
    if profile_type != capability:
        raise ValueError(f"profile 类型不匹配，期望 {capability}，实际为 {profile_type}")


def _get_api_key(profile_config: dict[str, Any]) -> str:
    """按配置读取 API Key。"""
    api_key_env = profile_config["api_key_env"]
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise ValueError(f"环境变量 {api_key_env} 未设置")
    return api_key


def create_llm(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    profile: str | None = None,
) -> LiteLLMChatModel:
    """按配置文件创建聊天模型。"""
    config = load_model_config(config_path)
    resolved_profile = profile or _resolve_profile_name(config, "chat")
    profile_config = _resolve_profile_config(config, resolved_profile)
    _validate_profile_capability(profile_config, "chat")

    return LiteLLMChatModel(
        model=profile_config["model"],
        api_base=profile_config["api_base"],
        api_key=_get_api_key(profile_config),
        temperature=profile_config.get("temperature", 0),
        timeout=profile_config.get("timeout", 30),
    )


def create_embedding_model(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    profile: str | None = None,
) -> LiteLLMEmbeddingModel:
    """按配置文件创建向量模型。"""
    config = load_model_config(config_path)
    resolved_profile = _resolve_profile_name(config, "embedding", profile)
    profile_config = _resolve_profile_config(config, resolved_profile)
    _validate_profile_capability(profile_config, "embedding")

    return LiteLLMEmbeddingModel(
        model=profile_config["model"],
        api_base=profile_config["api_base"],
        api_key=_get_api_key(profile_config),
        timeout=profile_config.get("timeout", 30),
    )


def create_rerank_model(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    profile: str | None = None,
) -> LiteLLMRerankModel:
    """按配置文件创建重排模型。"""
    config = load_model_config(config_path)
    resolved_profile = _resolve_profile_name(config, "rerank", profile)
    profile_config = _resolve_profile_config(config, resolved_profile)
    _validate_profile_capability(profile_config, "rerank")

    return LiteLLMRerankModel(
        model=profile_config["model"],
        api_base=profile_config["api_base"],
        api_key=_get_api_key(profile_config),
        timeout=profile_config.get("timeout", 30),
    )


def list_profiles(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    capability: str | None = None,
) -> dict[str, dict[str, Any]]:
    """列出全部或某类能力的 profile。"""
    config = load_model_config(config_path)
    profiles = config.get("profiles", {})
    if capability is None:
        return profiles
    return {
        name: profile_config
        for name, profile_config in profiles.items()
        if profile_config.get("type", "chat") == capability
    }
