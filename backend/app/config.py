import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Smart Sales Assistant Configuration
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "3072"))
KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", "knowledge")
MAX_RESPONSE_LENGTH = int(os.getenv("MAX_RESPONSE_LENGTH", "200"))
DEFAULT_TONE = os.getenv("DEFAULT_TONE", "professional")

# Vexa API Configuration
VEXA_API_KEY = os.getenv("VEXA_API_KEY", "ugDGwpFdV5kT3CGKxqGQeKOBmfQ0bJsCHgKuWZ2u")
VEXA_BASE_URL = os.getenv("VEXA_BASE_URL", "https://gateway.dev.vexa.ai")