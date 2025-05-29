import os
from typing import Optional
from pydantic import BaseModel, Field

class LangfuseConfig(BaseModel):
    """Configuration for Langfuse tracing."""
    public_key: str = Field(default="")
    secret_key: str = Field(default="")
    host: str = Field(default="https://cloud.langfuse.com")
    environment: str = Field(default="dev")

class OllamaConfig(BaseModel):
    """Configuration for Ollama LLM server."""
    base_url: str = Field(default="http://localhost:11434")
    llm_model: str = Field(default="llama3.2")
    embedding_model: str = Field(default="nomic-embed-text-v1.5")
    docker_url: Optional[str] = Field(default=None)

class ChromaConfig(BaseModel):
    """Configuration for ChromaDB vector store."""
    persist_directory: str = Field(default="./chroma_db")
    collection_name: Optional[str] = Field(default=None)
    host: Optional[str] = Field(default=None)
    port: int = Field(default=8000)

class SupervisorConfig(BaseModel):
    """Configuration for Supervisor API."""
    slack_token: str = Field(default="")
    slack_app_token: str = Field(default="")
    slack_signing_secret: str = Field(default="")
    langfuse: LangfuseConfig = Field(default_factory=LangfuseConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    chroma: ChromaConfig = Field(default_factory=ChromaConfig)

    @classmethod
    def from_env(cls) -> "SupervisorConfig":
        return cls(
            slack_token=os.environ.get("SLACK_TOKEN", ""),
            slack_app_token=os.environ.get("SLACK_APP_TOKEN", ""),
            slack_signing_secret=os.environ.get("SLACK_SIGNING_SECRET", ""),
            langfuse=LangfuseConfig(
                public_key=os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
                secret_key=os.environ.get("LANGFUSE_SECRET_KEY", ""),
                host=os.environ.get("LANGFUSE_HOST", ""),
                environment=os.environ.get("LANGFUSE_ENVIRONMENT", "dev")
            ),
            ollama=OllamaConfig(
                base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
                llm_model=os.environ.get("OLLAMA_LLM_MODEL", "llama3.2"),
                embedding_model=os.environ.get("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text-v1.5"),
                docker_url=os.environ.get("OLLAMA_DOCKER_URL", None)
            ),
            chroma=ChromaConfig(
                persist_directory=os.environ.get("CHROMA_PERSIST_DIRECTORY", "./chroma_db"),
                collection_name=os.environ.get("CHROMA_COLLECTION_NAME", None),
                host=os.environ.get("CHROMA_HOST", None),
                port=int(os.environ.get("CHROMA_PORT", "8000"))
            )
        )

# Instantiate configuration
config = SupervisorConfig.from_env()
