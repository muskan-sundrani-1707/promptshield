"""
TARGET AI = the chatbot being tested.
It receives ONLY (system prompt + user input). It knows nothing about PromptShield.
"""
from app.services.llm_providers import get_provider


def ask_target(system_prompt: str, user_message: str,
               provider: str, model: str, temperature: float = 0.0) -> str:
    """Send one user message to the target chatbot and return its ACTUAL reply."""
    llm = get_provider(provider, model)
    return llm.chat(system_prompt, user_message, temperature=temperature)