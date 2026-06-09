"""Configuration management for vn-real-estate-scout."""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "claude"))
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen2.5:7b"))

@dataclass
class Neo4jConfig:
    """Neo4j database configuration."""
    uri: str = field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    user: str = field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    password: str = field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", "neo4j_password"))

@dataclass
class ChromaDBConfig:
    """ChromaDB vector store configuration."""
    host: str = field(default_factory=lambda: os.getenv("CHROMADB_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("CHROMADB_PORT", "8000")))
    collection_name: str = "vn_realestate_listings"

@dataclass
class GoogleMapsConfig:
    """Google Maps API configuration."""
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("GOOGLE_MAPS_API_KEY"))

@dataclass
class MapboxConfig:
    """Mapbox API configuration."""
    access_token: Optional[str] = field(default_factory=lambda: os.getenv("MAPBOX_ACCESS_TOKEN"))

@dataclass
class ScraperConfig:
    """Scraper configuration."""
    rate_limit: int = field(default_factory=lambda: int(os.getenv("SCRAPER_RATE_LIMIT", "1")))
    delay_min: int = field(default_factory=lambda: int(os.getenv("SCRAPER_DELAY_MIN", "2")))
    delay_max: int = field(default_factory=lambda: int(os.getenv("SCRAPER_DELAY_MAX", "5")))

@dataclass
class SchedulerConfig:
    """Scheduler configuration."""
    enabled: bool = field(default_factory=lambda: os.getenv("SCHEDULER_ENABLED", "true").lower() == "true")
    interval_hours: int = field(default_factory=lambda: int(os.getenv("SCHEDULER_INTERVAL_HOURS", "4")))

@dataclass
class SecurityConfig:
    """Security configuration."""
    user_encryption_key: Optional[str] = field(default_factory=lambda: os.getenv("USER_ENCRYPTION_KEY"))

@dataclass
class AppConfig:
    """Application configuration."""
    env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_file_path: str = field(default_factory=lambda: os.getenv("LOG_FILE_PATH", "logs/agent.log"))

    @property
    def is_development(self) -> bool:
        return self.env == "development"

    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent.parent

# Project paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
USER_DATA_DIR = BASE_DIR / "user_data"
REPORTS_DIR = BASE_DIR / "reports"
MODELS_DIR = BASE_DIR / "models"

# Configuration instances
llm = LLMConfig()
neo4j = Neo4jConfig()
chromadb = ChromaDBConfig()
google_maps = GoogleMapsConfig()
mapbox = MapboxConfig()
scraper = ScraperConfig()
scheduler = SchedulerConfig()
security = SecurityConfig()
app = AppConfig()

# Create directories
for dir_path in [DATA_DIR, LOGS_DIR, USER_DATA_DIR, REPORTS_DIR, MODELS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
