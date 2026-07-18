import logging
import os
import tempfile
from pathlib import Path

from platformdirs import user_data_dir

# Constants
IS_TESTING = os.getenv("TESTING", "false").lower() == "true"
IS_DOCKER = Path("/.dockerenv").exists() or os.getenv("DOCKER_CONTAINER") == "true"
IS_BROWSER_DEV = os.getenv("BROWSER_DEV_MODE", "false").lower() == "true"
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"

# Proxy auth configuration (for reverse proxy deployments)
PROXY_AUTH_ENABLED = os.getenv("PROXY_AUTH_ENABLED", "false").lower() == "true"
PROXY_AUTH_USER_HEADER = os.getenv("PROXY_AUTH_USER_HEADER", "X-Forwarded-User")
PROXY_AUTH_ALLOWED_USERS = [
    u.strip() for u in os.getenv("PROXY_AUTH_ALLOWED_USERS", "").split(",") if u.strip()
]

APP_NAME = "Obscura"
APP_DATA_NAME = "Obscura"
APP_AUTHOR = "Obscura"

# Hackathon MVP defaults. These are OpenAI-compatible hosted endpoints, so the
# application can be demonstrated without compiling inference engines or
# downloading multi-gigabyte models. API keys are always supplied by the user.
HOSTED_DEMO_LLM_BASE_URL = "https://openrouter.ai/api"
HOSTED_DEMO_LLM_MODEL = "google/gemma-4-26b-a4b-it"
HOSTED_DEMO_WHISPER_BASE_URL = "https://api.groq.com/openai"
HOSTED_DEMO_WHISPER_MODEL = "whisper-large-v3-turbo"


logger = logging.getLogger(__name__)


def get_app_directories():
    """Get appropriate directories based on environment"""
    if IS_DOCKER:
        logger.info("Running in Docker environment; setting up directories")
        data_dir = Path("/usr/src/app/data")
        build_dir = Path("/usr/src/app/build")
    else:
        # For Tauri desktop app
        logger.info("Running in desktop environment; setting up directories")
        logger.info(f"IS_DOCKER={IS_DOCKER}")
        data_dir = Path(user_data_dir(APP_DATA_NAME, APP_AUTHOR))
        logger.info("Data directory: %s", data_dir)
        build_dir = None  # No need to serve static files

    return data_dir, build_dir


# Get directories
DATA_DIR, BUILD_DIR = get_app_directories()

# Create directories if they don't exist
DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_temp_directory():
    """Get appropriate temporary directory based on environment"""
    if IS_DOCKER:
        temp_dir = Path("/usr/src/app/temp")
    else:
        # Use system temp directory with app-specific subdirectory
        temp_dir = Path(tempfile.gettempdir()) / "obscura"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


TEMP_DIR = get_temp_directory()
