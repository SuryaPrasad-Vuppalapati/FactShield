from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Global rate limit: 20 API requests per minute per IP
limiter = Limiter(key_func=get_remote_address, default_limits=["20/minute"])
