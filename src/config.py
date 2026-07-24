import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    planner_model: str = os.getenv("PLANNER_MODEL", "openrouter/nousresearch/hermes-4")
    executor_model: str = os.getenv("EXECUTOR_MODEL", "openrouter/laguna/laguna-s-2.1")
    max_tokens: int = int(os.getenv("MAX_TOKENS", "4096"))
    temperature: float = float(os.getenv("TEMPERATURE", "0.2"))

config = Config()
