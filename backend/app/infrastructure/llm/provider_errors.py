"""Exception types and helpers for LLM/embedding provider resilience."""


class RetryableError(Exception):
    """Error that can be retried (e.g., transient network/rate-limit issues)."""


class NonRetryableError(Exception):
    """Error that should not be retried (e.g., invalid auth, bad request)."""


def classify_provider_error(exc: Exception) -> Exception:
    """Classify a raw provider exception as retryable or non-retryable.

    This is intentionally generic so it works across OpenAI and Google SDKs
    without taking a hard dependency on every exception type.
    """
    retryable_status_codes = {429, 500, 502, 503, 504}
    non_retryable_status_codes = {400, 401, 403, 404}

    status_code = None
    if hasattr(exc, "status_code"):
        status_code = exc.status_code
    elif hasattr(exc, "code"):
        status_code = exc.code
    elif hasattr(exc, "status"):
        status_code = exc.status

    if status_code is not None:
        if status_code in retryable_status_codes:
            return RetryableError(str(exc))
        if status_code in non_retryable_status_codes:
            return NonRetryableError(str(exc))

    name = type(exc).__name__
    retryable_names = {
        "APIConnectionError",
        "APITimeoutError",
        "RateLimitError",
        "InternalServerError",
        "ServiceUnavailableError",
        "APIError",
    }
    non_retryable_names = {
        "AuthenticationError",
        "BadRequestError",
        "PermissionDeniedError",
        "NotFoundError",
    }

    if name in retryable_names:
        return RetryableError(str(exc))
    if name in non_retryable_names:
        return NonRetryableError(str(exc))

    # Default: treat unknown errors as retryable; the resilient wrapper will
    # eventually give up after max_retries.
    return RetryableError(str(exc))
