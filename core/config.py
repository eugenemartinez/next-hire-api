import os
from typing import List, Tuple, Union # Keep Tuple if used elsewhere, otherwise can remove
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

class Settings(BaseSettings):
    PROJECT_NAME: str = "NextHire"
    API_V1_STR: str = "/api"

    DEBUG_MODE: bool = False

    DATABASE_URL: SecretStr # Default removed, will be loaded from .env

    REDIS_URL: str = ""

    CORS_ALLOWED_ORIGINS: Union[str, List[str]] = "http://localhost:3000"

    DEFAULT_POSTER_ADJECTIVES: List[str] = [
        "Agile", "Bright", "Creative", "Dynamic", "Efficient", "Focused",
        "Global", "Honest", "Innovative", "Keen", "Logical", "Methodical",
        "Noble", "Optimal", "Positive", "Qualified", "Resourceful", "Strategic",
        "Technical", "Unique", "Versatile", "Wise", "Xenial", "Youthful", "Zealous"
    ]
    DEFAULT_POSTER_NOUNS: List[str] = [
        "Achiever", "Analyst", "Architect", "Artisan", "Builder", "Catalyst",
        "Champion", "Consultant", "Creator", "Developer", "Director", "Engineer",
        "Expert", "Facilitator", "Guru", "Innovator", "Leader", "Manager",
        "Mentor", "Negotiator", "Optimizer", "Originator", "Pioneer", "Planner",
        "Producer", "Professional", "Programmer", "Strategist", "Specialist", "Thinker",
        "Visionary", "Wizard"
    ]

    # Pydantic V2 configuration
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"), # Explicitly point to .env
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=True # Pydantic's default is case_sensitive=False for env vars
    )

    # Helper property to get CORS origins as a list of strings
    @property
    def cors_origins_list(self) -> List[str]:
        origins = self.CORS_ALLOWED_ORIGINS
        if isinstance(origins, str):
            return [origin.strip() for origin in origins.split(",") if origin.strip()]
        elif isinstance(origins, list):
            return [str(origin).strip() for origin in origins if str(origin).strip()]
        return []


settings = Settings()

# Example of how to use DEBUG_MODE for logging (we'll integrate Structlog later)
if settings.DEBUG_MODE:
    print("DEBUG MODE IS ON")
    # Configure more verbose logging, etc.
else:
    print("DEBUG MODE IS OFF")
    # Configure production logging

# Print loaded CORS origins for verification during startup
print(f"Allowed CORS origins: {settings.cors_origins_list}")
