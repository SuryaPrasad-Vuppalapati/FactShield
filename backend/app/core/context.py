from contextvars import ContextVar

# Context variable to hold the user's specific Hugging Face Token per request
user_hf_token: ContextVar[str | None] = ContextVar("user_hf_token", default=None)
