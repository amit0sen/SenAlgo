"""SenAlgo global configuration schema.

Supports 12+ LLM providers — NO mandatory API key required.
Default provider: Ollama (local, completely free).
Free alternatives: DeepSeek (ultra-cheap), Groq (free tier).

Free market data (NO API key needed):
  - yfinance      : US / HK equities, NSE/BSE
  - ccxt (OKX)   : Crypto — public API, no key
  - AKShare       : A-share Chinese equities
  - Fyers WebSocket: Real-time NSE/BSE tick data (Fyers account needed)
"""
from __future__ import annotations
import os
from pathlib import Path
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Provider catalogue
# ---------------------------------------------------------------------------
SUPPORTED_PROVIDERS = {
    "ollama":     "Local Ollama — no API key, runs on your machine (ollama.com)",
    "deepseek":   "DeepSeek — GPT-4-class quality at 1/30th the price",
    "groq":       "Groq — ultra-fast inference, generous free tier",
    "openrouter": "OpenRouter — 200+ models, pay-per-token",
    "gemini":     "Google Gemini (free tier available)",
    "openai":     "OpenAI GPT-4o / o1",
    "anthropic":  "Anthropic Claude",
    "dashscope":  "Alibaba DashScope / Qwen",
    "zhipu":      "Zhipu AI — GLM-4",
    "moonshot":   "Moonshot / Kimi",
    "minimax":    "MiniMax",
    "zai":        "Z.ai",
}

DEFAULT_MODELS = {
    "ollama":     "qwen2.5:14b",
    "deepseek":   "deepseek-chat",
    "groq":       "llama-3.3-70b-versatile",
    "openrouter": "deepseek/deepseek-chat",
    "gemini":     "gemini-2.0-flash",
    "openai":     "gpt-4o",
    "anthropic":  "claude-sonnet-4-6",
    "dashscope":  "qwen-max",
    "zhipu":      "glm-4",
    "moonshot":   "moonshot-v1-8k",
    "minimax":    "abab6.5-chat",
    "zai":        "z1-mini",
}

PROVIDER_BASE_URLS = {
    "ollama":     "http://localhost:11434/v1",
    "deepseek":   "https://api.deepseek.com/v1",
    "groq":       "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "gemini":     "https://generativelanguage.googleapis.com/v1beta/openai",
    "dashscope":  "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "zhipu":      "https://open.bigmodel.cn/api/paas/v4",
    "moonshot":   "https://api.moonshot.cn/v1",
    "minimax":    "https://api.minimax.chat/v1",
    "zai":        "https://api.z.ai/v1",
}


def _resolve_api_key(provider: str) -> str:
    """Pick the right env var for each provider. Returns '' for Ollama."""
    key_map = {
        "anthropic":  "ANTHROPIC_API_KEY",
        "openai":     "OPENAI_API_KEY",
        "deepseek":   "DEEPSEEK_API_KEY",
        "groq":       "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "gemini":     "GEMINI_API_KEY",
        "dashscope":  "DASHSCOPE_API_KEY",
        "zhipu":      "ZHIPU_API_KEY",
        "moonshot":   "MOONSHOT_API_KEY",
        "minimax":    "MINIMAX_API_KEY",
        "zai":        "ZAI_API_KEY",
    }
    env_var = key_map.get(provider, "")
    return os.getenv(env_var, "") if env_var else ""


class LLMConfig(BaseModel):
    provider: str = Field(
        default="ollama",
        description="LLM provider. Default = ollama (free/local). See SUPPORTED_PROVIDERS.",
    )
    model: str = Field(default="", description="Model name. Auto-selected per provider when empty.")
    api_key: str = Field(default="", description="API key (not needed for Ollama).")
    api_base: str = Field(default="", description="Override API base URL.")
    max_iterations: int = Field(default=50)
    temperature: float = Field(default=0.0)

    @property
    def resolved_model(self) -> str:
        return self.model or DEFAULT_MODELS.get(self.provider, "")

    @property
    def resolved_base(self) -> str:
        return self.api_base or PROVIDER_BASE_URLS.get(self.provider, "")


class SafetyConfig(BaseModel):
    paper_only: bool = Field(default=True)
    max_order_value: float = Field(default=50_000.0)
    daily_loss_cap: float = Field(default=5_000.0)
    kill_switch_path: Path = Field(default=Path.home() / ".senalgo" / "KILL_SWITCH")


class DataConfig(BaseModel):
    cache_enabled: bool = Field(default=False)
    cache_dir: Path = Field(default=Path.home() / ".senalgo" / "cache")
    default_equity_source: str = Field(default="yfinance")
    default_crypto_source: str = Field(default="ccxt_okx")
    default_india_source: str = Field(default="yfinance")
    fyers_client_id: str = Field(default="")
    fyers_access_token: str = Field(default="")
    fyers_enabled: bool = Field(default=False)


class ServerConfig(BaseModel):
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"]
    )


class SenAlgoConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)

    @classmethod
    def from_env(cls) -> "SenAlgoConfig":
        provider = os.getenv("SENALGO_LLM_PROVIDER", "ollama")
        return cls(
            llm=LLMConfig(
                provider=provider,
                model=os.getenv("SENALGO_MODEL", ""),
                api_key=_resolve_api_key(provider),
                api_base=os.getenv("SENALGO_API_BASE", ""),
                temperature=float(os.getenv("SENALGO_TEMPERATURE", "0.0")),
            ),
            safety=SafetyConfig(
                paper_only=os.getenv("SENALGO_PAPER_ONLY", "true").lower() == "true",
                max_order_value=float(os.getenv("SENALGO_MAX_ORDER_VALUE", "50000")),
                daily_loss_cap=float(os.getenv("SENALGO_DAILY_LOSS_CAP", "5000")),
            ),
            data=DataConfig(
                cache_enabled=os.getenv("SENALGO_DATA_CACHE", "false").lower() == "true",
                fyers_client_id=os.getenv("FYERS_CLIENT_ID", ""),
                fyers_access_token=os.getenv("FYERS_ACCESS_TOKEN", ""),
                fyers_enabled=bool(os.getenv("FYERS_ACCESS_TOKEN", "")),
            ),
            server=ServerConfig(
                host=os.getenv("SENALGO_HOST", "0.0.0.0"),
                port=int(os.getenv("SENALGO_PORT", "8000")),
            ),
        )
