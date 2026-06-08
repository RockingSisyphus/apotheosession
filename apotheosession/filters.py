_ENV_CONTEXT_MARKERS = ["<environment_context>", "<InstructionsForCodex>"]


def is_environment_context(text: str) -> bool:
    return any(marker in text for marker in _ENV_CONTEXT_MARKERS)


def is_user_message_text(text: str) -> bool:
    return not is_environment_context(text)
