# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Model Choices
INSIGHT_MODEL = "claude-sonnet-4-20250514"
SYNTHESIS_MODEL = "gpt-4o"
BASE_MODEL_OPTIONS = {
    "Claude": {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
    "GPT": {"provider": "openai", "model": "gpt-4o"},
}

# Observer Settings
OBSERVER_SENSITIVITY = "balanced"  # aggressive | balanced | conservative
MAX_INSIGHTS_PER_INTERACTION = 2
SILENCE_AFTER_IGNORES = 3
MAX_CONTEXT_TOKENS = 800

# Paths
DB_PATH = "database/nextstep.db"
REPORTS_DIR = "reports"
PROMPTS_DIR = "prompts"
PROFILES_DIR = "profiles"
