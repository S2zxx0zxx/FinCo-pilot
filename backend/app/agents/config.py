from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import CREDENTIALS_DIRECTORY


class AgentSettings(BaseSettings):
    # Master switch. When false, the router is not mounted, MCP servers are
    # not contacted, and no background tasks run.
    enabled: bool = False

    # Built-in MCP server URL. The mcp-server container speaks JSON-RPC 2.0.
    # This is the internal address the backend uses to reach the container.
    builtin_mcp_url: str = "http://mcp-server:8765/mcp"

    # Public URL external agents use to reach the built-in MCP server, shown
    # in the UI token panel. Leave blank to have the frontend derive it from
    # the browser location (``<protocol>//<hostname>:8765/mcp``). Set this
    # when the MCP server is exposed behind an ingress/reverse proxy on a
    # custom host, subpath, or standard 80/443 port instead of ``:8765``.
    # Example: "https://fincopilot.example.com/mcp".
    external_mcp_url: str = ""

    # Comma-separated extra MCP servers users can plug in (URL[|name]).
    # Example: "http://my-tools:9000/mcp|my-tools,http://other:9001/mcp"
    extra_mcp_servers: str = ""

    # Shared secret used to mint short-lived JWTs for MCP calls. Distinct
    # from the main app secret so revocation is independent.
    mcp_jwt_secret: SecretStr = SecretStr("change-me-in-production")
    mcp_jwt_ttl_seconds: int = 600

    # Operator-level inference defaults. Secret values are typed as SecretStr
    # and can come from /run/secrets through the same Pydantic settings source
    # as the core application. Runtime code must not bypass this with os.getenv.
    default_provider: str = "ollama"
    default_model: str = ""
    ollama_base_url: str = "http://ollama:11434"
    openai_api_key: SecretStr = SecretStr("")
    anthropic_api_key: SecretStr = SecretStr("")
    openai_compat_base_url: str = ""
    openai_compat_api_key: SecretStr = SecretStr("")

    # TTL for long-lived tokens minted via the UI for external agents
    # (Claude Desktop, n8n, custom clients). The feature itself follows
    # `enabled` — if agents are on, the mint endpoint is mounted and the
    # mcp-server container publishes port 8765.
    mcp_external_ttl_days: int = 90

    # Embedding dimension for the knowledge_chunks vector column. Locked at
    # migration time. 1536 covers OpenAI text-embedding-3-small (default) and
    # nomic-embed-text via Matryoshka padding/truncation.
    embedding_dim: int = 1536

    # Built-in FinCo Copilot is separate from Advanced Agents. This
    # is an operational abuse/capacity ceiling, not a pricing promise.
    core_copilot_daily_messages: int = 50
    # Hard ceiling per model round for the first-party Copilot. Tool-calling
    # may require multiple rounds, but no single response can run unbounded.
    core_copilot_max_output_tokens: int = 1200

    # Default RAG parameters (overridable per agent in the DB row).
    default_top_n: int = 6
    default_similarity_threshold: float = 0.25

    # Embedding provider/model. Both MCP-server and Celery worker honor
    # these. Switching requires re-embedding existing docs (their
    # embeddings are tied to the model that produced them).
    #
    # Default `native` uses fastembed with a small multilingual model
    # bundled in-process — works zero-config (no Ollama/OpenAI/etc).
    # Users can switch to ollama/openai/openai_compatible for higher
    # quality or faster inference.
    embedding_provider: str = "native"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_native_cache_dir: str = "/app/data/embedding_models"
    embedding_ollama_base_url: str = "http://ollama:11434"
    embedding_openai_base_url: str = "https://api.openai.com/v1"
    embedding_openai_api_key: SecretStr = SecretStr("")

    # Where uploaded knowledge files live on disk (per-instance).
    knowledge_storage_path: str = "/app/data/agent_knowledge"
    knowledge_max_file_size_mb: int = 25

    @model_validator(mode="after")
    def validate_production_secret(self):
        from app.core.config import get_settings

        if self.external_mcp_url:
            from urllib.parse import urlsplit
            value = self.external_mcp_url.strip()
            self.external_mcp_url = value
            try:
                parsed = urlsplit(value)
                valid = (parsed.scheme in ("https", "http") and parsed.hostname
                         and not parsed.username and not parsed.password
                         and not parsed.query and not parsed.fragment
                         and parsed.path
                         and all(32 < ord(c) < 127 and c not in "'\"`$\\<>|{}" for c in value))
                _ = parsed.port
            except ValueError:
                valid = False
            if not valid or (get_settings().is_production and parsed.scheme != "https"):
                raise ValueError("AGENTS_EXTERNAL_MCP_URL must be a credential-free endpoint URL; production requires HTTPS")

        if self.enabled and get_settings().is_production:
            mcp_secret = self.mcp_jwt_secret.get_secret_value()
            if mcp_secret == "change-me-in-production" or len(mcp_secret) < 32:
                raise ValueError("Production agents require a unique AGENTS_MCP_JWT_SECRET of at least 32 characters")
        if not 1 <= self.mcp_external_ttl_days <= 90:
            raise ValueError("AGENTS_MCP_EXTERNAL_TTL_DAYS must be between 1 and 90")
        if not 1 <= self.core_copilot_daily_messages <= 1000:
            raise ValueError("AGENTS_CORE_COPILOT_DAILY_MESSAGES must be between 1 and 1000")
        if not 128 <= self.core_copilot_max_output_tokens <= 8192:
            raise ValueError(
                "AGENTS_CORE_COPILOT_MAX_OUTPUT_TOKENS must be between 128 and 8192"
            )
        return self

    # Same env_file pair as the main Settings: the CWD-relative ".env" for
    # backward compatibility plus the anchored backend/.env, so the API and the
    # Celery worker/beat read the same file whatever directory they start from.
    model_config = SettingsConfigDict(
        env_file=(".env", Path(__file__).resolve().parents[2] / ".env"),
        env_prefix="AGENTS_",
        secrets_dir=CREDENTIALS_DIRECTORY,
        extra="ignore",
    )


@lru_cache
def get_agent_settings() -> AgentSettings:
    return AgentSettings()
