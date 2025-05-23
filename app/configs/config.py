import os
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class LangfuseConfig(BaseModel):
    """Configuration for Langfuse."""
    public_key: str = Field(default="")
    secret_key: str = Field(default="")
    host: str = Field(default="https://cloud.langfuse.com")

class OllamaConfig(BaseModel):
    """Configuration for Ollama."""
    base_url: str = Field(default="http://localhost:11434")
    llm_model: str = Field(default="llama3.2")
    embedding_model: str = Field(default="nomic-embed-text-v1.5")
    docker_url: Optional[str] = Field(default=None)  # URL for Ollama running in Docker

class ChromaConfig(BaseModel):
    """Configuration for ChromaDB."""
    persist_directory: str = Field(default="./chroma_db")
    collection_name: Optional[str] = Field(default=None)
    host: Optional[str] = Field(default=None)  # Host for ChromaDB running in Docker
    port: Optional[int] = Field(default=8000)  # Port for ChromaDB running in Docker

class AgentConfig(BaseModel):
    """Configuration for the LLM Agent."""
    langfuse: LangfuseConfig = Field(default_factory=LangfuseConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    chroma: ChromaConfig = Field(default_factory=ChromaConfig)
    
    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load configuration from environment variables."""
        return cls(
            langfuse=LangfuseConfig(
                public_key=os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
                secret_key=os.environ.get("LANGFUSE_SECRET_KEY", ""),
                host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
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

# Default configuration
config = AgentConfig.from_env()
